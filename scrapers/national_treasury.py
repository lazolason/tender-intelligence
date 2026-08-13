"""Public National Treasury eTenders live-opportunity scraper."""

from __future__ import annotations

import os
import sys
from typing import Any

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.retry_tools import safe_get
from utils.text_cleaner import clean_text


DEFAULT_LISTING_URL = "https://www.etenders.gov.za/Home/opportunities"
DEFAULT_API_URL = "https://www.etenders.gov.za/Home/PaginatedTenderOpportunities"


class NationalTreasuryScraper:
    """Read currently advertised tenders from the portal's public listing feed."""

    def __init__(
        self,
        url: str = DEFAULT_LISTING_URL,
        user_agent: str = "Mozilla/5.0",
        timeout: int = 30,
        *,
        api_url: str = DEFAULT_API_URL,
        page_size: int = 500,
        max_records: int = 10_000,
    ):
        self.listing_url = url or DEFAULT_LISTING_URL
        self.api_url = api_url or DEFAULT_API_URL
        self.timeout = max(1, int(timeout))
        self.page_size = max(1, min(int(page_size), 500))
        self.max_records = max(1, int(max_records))
        self.headers = {
            "User-Agent": user_agent or "Mozilla/5.0",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Referer": self.listing_url,
        }

    @staticmethod
    def _validate_page(payload: Any) -> tuple[list[dict], int]:
        if not isinstance(payload, dict):
            raise ValueError("National Treasury response must be an object")

        rows = payload.get("data")
        total = payload.get("recordsFiltered", payload.get("recordsTotal"))
        if not isinstance(rows, list):
            raise ValueError("National Treasury response is missing the data array")
        if not isinstance(total, int) or isinstance(total, bool) or total < 0:
            raise ValueError("National Treasury response has an invalid record count")
        if any(not isinstance(row, dict) for row in rows):
            raise ValueError("National Treasury response contains a non-object row")
        return rows, total

    def fetch_page(self, *, start: int = 0) -> dict:
        params = {
            "draw": (start // self.page_size) + 1,
            "start": start,
            "length": self.page_size,
            "status": 1,
            "search[value]": "",
            "search[regex]": "false",
        }
        response = safe_get(
            self.api_url,
            headers=self.headers,
            params=params,
            timeout=self.timeout,
        )
        if response is None:
            raise RuntimeError("National Treasury listing request failed")
        response.raise_for_status()
        try:
            payload = response.json()
        except ValueError as exc:
            raise ValueError("National Treasury listing returned invalid JSON") from exc
        self._validate_page(payload)
        return payload

    def fetch_all(self) -> list[dict]:
        rows: list[dict] = []
        expected_total: int | None = None

        while expected_total is None or len(rows) < expected_total:
            payload = self.fetch_page(start=len(rows))
            page_rows, page_total = self._validate_page(payload)

            if expected_total is None:
                expected_total = page_total
                if expected_total > self.max_records:
                    raise ValueError(
                        f"National Treasury record count {expected_total} exceeds safety limit "
                        f"{self.max_records}"
                    )
            elif page_total != expected_total:
                raise ValueError("National Treasury record count changed during pagination")

            if not page_rows and len(rows) < expected_total:
                raise ValueError("National Treasury pagination ended before the advertised total")
            rows.extend(page_rows)
            if len(rows) > expected_total:
                raise ValueError("National Treasury returned more rows than advertised")

        return rows

    @staticmethod
    def _iso_date(value: Any) -> str:
        text = str(value or "").strip()
        if not text or text.startswith("0001-01-01"):
            return ""
        return text.split("T", 1)[0][:10]

    def parse_tenders(self, data: Any) -> list[dict]:
        if isinstance(data, dict):
            items, _ = self._validate_page(data)
        elif isinstance(data, list) and all(isinstance(item, dict) for item in data):
            items = data
        else:
            raise ValueError("National Treasury tender data has an invalid structure")

        tenders = []
        for item in items:
            ref = clean_text(str(item.get("tender_No") or item.get("tenderNumber") or ""))
            full_title = clean_text(str(item.get("description") or item.get("title") or ""))
            title = full_title[:500]
            client = clean_text(
                str(
                    item.get("organ_of_State")
                    or item.get("department")
                    or item.get("Department")
                    or "National Treasury"
                )
            )
            if not ref or not title:
                continue

            detail_parts = [
                full_title,
                f"Reference: {ref}",
                clean_text(str(item.get("category") or "")),
                clean_text(str(item.get("type") or "")),
                clean_text(str(item.get("conditions") or "")),
            ]
            tenders.append(
                {
                    "ref": ref,
                    "title": title,
                    "description": " | ".join(part for part in detail_parts if part),
                    "client": client,
                    "source": "National Treasury",
                    "ref_is_authoritative": True,
                    "url": self.listing_url,
                    "closing_date": self._iso_date(
                        item.get("closing_Date", item.get("closingDate"))
                    ),
                    "published_date": self._iso_date(
                        item.get("date_Published", item.get("datePublished"))
                    ),
                }
            )
        return tenders

    def run(self) -> list[dict]:
        return self.parse_tenders(self.fetch_all())
