#!/usr/bin/env python3
import argparse
import json
import os
import sys
from datetime import datetime, timedelta

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
    args = parser.parse_args()

    payload = build_snapshot(limit=args.limit)
    if not payload.get("tenders") and os.path.exists(args.out):
        # Avoid wiping the dashboard if scrapes return nothing.
        # Keep the previous snapshot unchanged so the workflow does not commit churn.
        return

    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=4)


if __name__ == "__main__":
    main()
