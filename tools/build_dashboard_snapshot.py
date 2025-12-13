#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender
from scoring_engine import score_tender
from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import (
    scrape_rand_water,
    scrape_transnet,
    scrape_eskom,
    scrape_sanral,
    scrape_umgeni_water,
    scrape_sasol,
    scrape_sanedi,
    scrape_anglo_american,
    scrape_harmony_gold,
    scrape_seriti,
    scrape_exxaro,
)


def _now_sast_str() -> str:
    try:
        from zoneinfo import ZoneInfo  # py3.9+

        return datetime.now(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        # Fallback: assume SAST = UTC+2 (no DST)
        return (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")


def _today_sast_date_str() -> str:
    try:
        from zoneinfo import ZoneInfo  # py3.9+

        return datetime.now(ZoneInfo("Africa/Johannesburg")).date().isoformat()
    except Exception:
        return (datetime.utcnow() + timedelta(hours=2)).date().isoformat()


def _identity(t: dict) -> str:
    ref = (t.get("ref") or "").strip().lower()
    if ref:
        return f"ref::{ref}"
    title = (t.get("title") or "").strip().lower()
    if title:
        return f"title::{title}"
    try:
        return json.dumps(t, sort_keys=True, default=str)
    except Exception:
        return str(t)


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def validate_payload(payload: Any) -> Tuple[List[dict], Dict[str, Any]]:
    if isinstance(payload, list):
        tenders = payload
        meta: Dict[str, Any] = {}
    elif isinstance(payload, dict):
        tenders = payload.get("tenders") or payload.get("data") or []
        meta = payload.get("meta") or {}
    else:
        raise ValueError("payload must be a list or object")

    if not isinstance(tenders, list):
        raise ValueError("tenders must be an array")
    if meta and not isinstance(meta, dict):
        raise ValueError("meta must be an object when present")

    for i, t in enumerate(tenders[:200]):
        if not isinstance(t, dict):
            raise ValueError(f"tender at index {i} must be an object")
        title = t.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"tender[{i}].title must be a string when present")
        scores = t.get("scores")
        if scores is not None and not isinstance(scores, dict):
            raise ValueError(f"tender[{i}].scores must be an object when present")

    return tenders, meta


def atomic_write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def build_summary(meta: Dict[str, Any], tenders: List[dict]) -> Dict[str, Any]:
    by_company: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    by_source: Dict[str, int] = {}

    scored_rows = []
    for t in tenders:
        company = (t.get("category") or t.get("company") or "Unknown") or "Unknown"
        by_company[company] = by_company.get(company, 0) + 1

        source = (t.get("source") or "Unknown") or "Unknown"
        by_source[source] = by_source.get(source, 0) + 1

        scores = t.get("scores") or {}
        priority = (scores.get("priority") or t.get("priority") or "UNKNOWN") or "UNKNOWN"
        priority = str(priority).upper()
        by_priority[priority] = by_priority.get(priority, 0) + 1

        fit = _as_number(scores.get("fit"))
        revenue = _as_number(scores.get("revenue"))
        risk = _as_number(scores.get("risk"))
        suitability = _as_number(scores.get("industry")) or _as_number(scores.get("composite"))
        scored_rows.append(
            (
                fit if fit is not None else -1.0,
                revenue if revenue is not None else -1.0,
                {
                    "title": t.get("title") or "-",
                    "source": source,
                    "company": company,
                    "priority": priority,
                    "close_date": t.get("closing_date") or t.get("close_date") or "-",
                    "fit": fit,
                    "revenue": revenue,
                    "risk": risk,
                    "suitability": suitability,
                    "url": t.get("url") or "",
                },
            )
        )

    scored_rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = [row for _, __, row in scored_rows[:10]]

    return {
        "generated_at": meta.get("last_sync") or _now_sast_str(),
        "next_run": meta.get("next_run") or "Daily 08:00",
        "counts": {
            "total": len(tenders),
            "by_company": dict(sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_priority": dict(sorted(by_priority.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "top": top,
    }


def build_snapshot(limit: int) -> dict:
    all_tenders = []

    # Keep to non-Selenium sources for CI stability
    all_tenders.extend(scrape_all_municipalities())
    soe_scrapers = [
        scrape_rand_water,
        scrape_transnet,
        scrape_eskom,
        scrape_sanral,
        scrape_umgeni_water,
        scrape_sasol,
        scrape_sanedi,
        scrape_anglo_american,
        scrape_harmony_gold,
        scrape_seriti,
        scrape_exxaro,
    ]
    for scraper in soe_scrapers:
        try:
            all_tenders.extend(scraper())
        except Exception:
            continue

    merged = []
    seen = set()
    for tender in all_tenders:
        ident = _identity(tender)
        if ident in seen:
            continue
        seen.add(ident)

        title = tender.get("title", "") or ""
        description = tender.get("description", title) or ""
        client = tender.get("client", "") or ""
        closing_date = tender.get("closing_date", "") or ""

        classification = classify_tender(title, description)
        category = classification.get("category", tender.get("category", "Unknown"))
        if category == "EXCLUDED":
            continue

        tender["category"] = category
        tender["reason"] = classification.get("reason", tender.get("reason", ""))
        tender["short_title"] = classification.get("short_title", tender.get("short_title", ""))

        tender["scores"] = score_tender(
            title=title,
            description=description,
            client=client,
            closing_date=closing_date,
            category=category,
        )

        merged.append(tender)
        if len(merged) >= limit:
            break

    meta = {
        "last_sync": _now_sast_str(),
        "next_run": "Daily 08:00",
    }

    return {"meta": meta, "tenders": merged}


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Vercel dashboard tenders.json snapshot")
    parser.add_argument("--out", default="vercel-dashboard/tenders.json", help="Output path for tenders.json")
    parser.add_argument("--limit", type=int, default=200, help="Max tenders to keep in snapshot")
    parser.add_argument(
        "--public-dir",
        default="vercel-dashboard/public",
        help="Directory for versioned dashboard artifacts (tenders-latest.json, tenders-YYYY-MM-DD.json, summary.json)",
    )
    args = parser.parse_args()

    payload = build_snapshot(limit=args.limit)
    tenders, meta = validate_payload(payload)
    if not tenders and os.path.exists(args.out):
        # Avoid wiping the dashboard if scrapes return nothing.
        # Keep the previous snapshot unchanged so the workflow does not commit churn.
        return

    atomic_write_json(args.out, payload)

    public_dir = os.path.abspath(args.public_dir)
    os.makedirs(public_dir, exist_ok=True)

    # Versioned artifacts for debugging + historical reference.
    latest_path = os.path.join(public_dir, "tenders-latest.json")
    dated_path = os.path.join(public_dir, f"tenders-{_today_sast_date_str()}.json")
    atomic_write_json(latest_path, payload)
    atomic_write_json(dated_path, payload)

    summary = build_summary(meta=meta, tenders=tenders)
    atomic_write_json(os.path.join(public_dir, "summary.json"), summary)


if __name__ == "__main__":
    main()
