"""Scraper for planned procurements published by South Africa's eTenders portal."""

from __future__ import annotations

import hashlib
import logging
from datetime import date, datetime
from typing import Any, Dict, Iterable, List, Optional

import requests
from bs4 import BeautifulSoup

from classify_engine import classify_tender, clean, keyword_present
from keyword_rules import STRONG_MATCH_KEYWORDS
from utils.retry_tools import secure_request_kwargs, validate_outbound_url


logger = logging.getLogger(__name__)

PROCUREMENT_PLANS_URL = "https://www.etenders.gov.za/Home/ProcurementPlans"
MAX_RESPONSE_BYTES = 20 * 1024 * 1024

_HEADER_ALIASES = {
    "institution": {"department", "institution", "organ of state"},
    "description": {
        "description",
        "description of goods, services and works",
        "procurement description",
    },
    "planned_advert_date": {"envisaged advert date", "planned advert date"},
    "planned_closing_date": {"envisaged closing date", "planned closing date"},
    "planned_award_date": {"envisaged award date", "planned award date"},
}


def _normalize_header(value: str) -> str:
    return " ".join((value or "").casefold().split())


def _column_indexes(table) -> Dict[str, int]:
    headers = [_normalize_header(cell.get_text(" ", strip=True)) for cell in table.select("thead th")]
    if not headers:
        raise ValueError("Procurement plans table has no column headers")
    indexes = {}
    for field, aliases in _HEADER_ALIASES.items():
        for index, header in enumerate(headers):
            if header in aliases:
                indexes[field] = index
                break
    missing = sorted(set(_HEADER_ALIASES) - set(indexes))
    if missing:
        raise ValueError(f"Procurement plans table missing columns: {', '.join(missing)}")
    return indexes


def _normalize_date(value: str) -> Optional[str]:
    text = (value or "").strip()
    if not text:
        return None
    for fmt in (
        "%Y/%m/%d %H:%M:%S",
        "%Y-%m-%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y-%m-%d",
    ):
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    logger.debug("Unrecognized procurement-plan date: %s", text)
    return None


def _external_id(institution: str, description: str) -> str:
    # Dates are deliberately excluded because Treasury may revise its schedule.
    identity = "\x1f".join(
        (
            institution.strip().casefold(),
            description.strip().casefold(),
        )
    )
    return "TPP-" + hashlib.sha256(identity.encode("utf-8")).hexdigest()[:24].upper()


def _lifecycle_stage(advert_date: Optional[str], *, today: Optional[date] = None) -> str:
    if not advert_date:
        return "PLANNED"
    today = today or date.today()
    planned = date.fromisoformat(advert_date)
    days = (planned - today).days
    if days < -30:
        return "OVERDUE"
    if days <= 90:
        return "DUE_SOON"
    return "PLANNED"


def parse_procurement_plans_html(
    html: str,
    *,
    source_url: str = PROCUREMENT_PLANS_URL,
    today: Optional[date] = None,
) -> List[Dict[str, Any]]:
    """Parse the server-rendered procurement-plan table into normalized records."""
    soup = BeautifulSoup(html or "", "html.parser")
    table = soup.select_one("table#DataTable") or soup.find("table")
    if table is None:
        raise ValueError("Procurement plans table not found")

    indexes = _column_indexes(table)
    plans: List[Dict[str, Any]] = []
    seen = set()
    for row in table.select("tbody tr"):
        cells = [cell.get_text(" ", strip=True) for cell in row.find_all("td")]
        if len(cells) <= max(indexes.values()):
            continue

        institution = cells[indexes["institution"]]
        description = cells[indexes["description"]]
        advert_raw = cells[indexes["planned_advert_date"]]
        closing_raw = cells[indexes["planned_closing_date"]]
        award_raw = cells[indexes["planned_award_date"]]
        if not institution or not description:
            continue

        advert_date = _normalize_date(advert_raw)
        closing_date = _normalize_date(closing_raw)
        award_date = _normalize_date(award_raw)
        external_id = _external_id(institution, description)
        if external_id in seen:
            continue
        seen.add(external_id)

        classification = classify_tender(description, f"{institution} {description}")
        plans.append(
            {
                "external_id": external_id,
                "institution": institution,
                "description": description,
                "planned_advert_date": advert_date,
                "planned_closing_date": closing_date,
                "planned_award_date": award_date,
                "category": classification.get("category", "EXCLUDED"),
                "classification_reason": classification.get("reason", ""),
                "matched_keywords": sorted(
                    set(classification.get("matched_keywords", [])),
                    key=str.casefold,
                ),
                "lifecycle_stage": _lifecycle_stage(advert_date, today=today),
                "source": "National Treasury Procurement Plans",
                "source_url": source_url,
            }
        )

    if not plans:
        raise ValueError("Procurement plans table contained no usable rows")
    return plans


def _download_html(
    url: str,
    *,
    timeout: int,
    max_response_bytes: int = MAX_RESPONSE_BYTES,
    session: Optional[requests.Session] = None,
) -> str:
    validate_outbound_url(url)
    client = session or requests.Session()
    request_kwargs = secure_request_kwargs({
        "headers": {"User-Agent": "TenderIntelligence/3.0 (+procurement-plans)"},
        "timeout": timeout,
        "stream": True,
        "allow_redirects": True,
    })
    with client.get(url, **request_kwargs) as response:
        validate_outbound_url(response.url)
        response.raise_for_status()
        content_length = response.headers.get("Content-Length")
        if content_length and int(content_length) > max_response_bytes:
            raise ValueError(
                f"Procurement plans response exceeds {max_response_bytes} bytes"
            )
        chunks = []
        total = 0
        for chunk in response.iter_content(chunk_size=64 * 1024):
            if not chunk:
                continue
            total += len(chunk)
            if total > max_response_bytes:
                raise ValueError(
                    f"Procurement plans response exceeds {max_response_bytes} bytes"
                )
            chunks.append(chunk)
        encoding = response.encoding or "utf-8"
        return b"".join(chunks).decode(encoding, errors="replace")


def is_relevant_plan(plan: Dict[str, Any]) -> bool:
    """Apply a stricter discovery gate than the general tender classifier."""
    text = clean(f"{plan.get('institution', '')} {plan.get('description', '')}")
    if plan.get("category") == "PHAKATHI":
        phakathi_signals = (
            "huawei", "reicon", "odacon", "scada", "ot networking", "ot network",
            "operational technology", "industrial networking", "plc programming",
            "hmi programming", "boiler chemistry", "boiler water", "boiler protection",
            "boiler treatment", "boiler preservation", "boiler lay up", "steam drum",
            "steam circuit", "flow accelerated corrosion",
        )
        return any(keyword_present(text, keyword) for keyword in phakathi_signals)
    if plan.get("category") != "MEXEL":
        return False

    if any(keyword_present(text, keyword) for keyword in STRONG_MATCH_KEYWORDS):
        return True

    thermal_systems = (
        "condenser",
        "cooling tower",
        "cooling water",
        "cooling system",
        "heat exchanger",
        "chiller",
        "cooling coil",
        "furnace cooling",
        "compressor cooling",
        "reverse osmosis",
        "ro system",
        "crac",
        "crah",
        "precision cooling",
        "close control cooling",
        "mission critical cooling",
    )
    if any(keyword_present(text, keyword) for keyword in thermal_systems):
        return True

    has_data_centre = any(
        keyword_present(text, keyword)
        for keyword in ("data center", "data centre", "server room", "computer room")
    )
    if has_data_centre and any(
        keyword_present(text, keyword)
        for keyword in ("hvac", "cooling", "chiller", "thermal", "heat transfer")
    ):
        return True

    has_boiler = keyword_present(text, "boiler")
    return has_boiler and any(
        keyword_present(text, keyword)
        for keyword in ("water treatment", "chemical", "dosing", "chemistry", "efficiency")
    )


def scrape_treasury_procurement_plans(
    *,
    url: str = PROCUREMENT_PLANS_URL,
    timeout: int = 60,
    relevant_only: bool = True,
    session: Optional[requests.Session] = None,
) -> List[Dict[str, Any]]:
    """Download and parse Treasury plans, optionally retaining matched companies only."""
    html = _download_html(url, timeout=timeout, session=session)
    plans = parse_procurement_plans_html(html, source_url=url)
    if relevant_only:
        plans = [plan for plan in plans if is_relevant_plan(plan)]
    logger.info("Treasury procurement plans: %d relevant records", len(plans))
    return plans
