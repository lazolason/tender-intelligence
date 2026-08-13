#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
from datetime import datetime
from typing import Any, Dict, List, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import yaml

from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import (
    scrape_rand_water,
    scrape_transnet,
    scrape_anglo_american,
    scrape_harmony_gold,
    scrape_seriti,
    scrape_joburg_water,
    scrape_eskom,
)


def atomic_write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def load_config() -> Dict[str, Any]:
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    config_path = os.path.join(repo_root, "config.yaml")
    if not os.path.exists(config_path):
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def normalize_tender(source: str, tender: Dict[str, Any]) -> Dict[str, Any]:
    tender = dict(tender or {})
    tender.setdefault("source", source)
    tender.setdefault("client", tender.get("client") or source)
    tender.setdefault("description", tender.get("description") or tender.get("title") or "")
    tender.setdefault("closing_date", tender.get("closing_date") or "")
    tender.setdefault("url", tender.get("url") or "")
    tender.setdefault("ref", tender.get("ref") or "NA")
    tender.setdefault("title", tender.get("title") or "")
    return tender


def run_scraper(scraper: str, config: Dict[str, Any]) -> List[Dict[str, Any]]:
    scraper = (scraper or "").strip().lower()
    timeout = int(((config.get("scrapers") or {}).get("timeout") or 15))

    if scraper == "municipalities":
        return scrape_all_municipalities(timeout=timeout)

    if scraper == "soes":
        # "SOEs" core (non-Selenium) – exclude Eskom + Johannesburg Water to avoid duplicates
        tenders: List[Dict[str, Any]] = []
        for fn in (
            scrape_rand_water,
            scrape_transnet,
            scrape_anglo_american,
            scrape_harmony_gold,
            scrape_seriti,
        ):
            try:
                tenders.extend(fn())
            except Exception:
                continue
        return tenders

    if scraper == "joburg_water":
        return scrape_joburg_water()

    if scraper == "eskom":
        return scrape_eskom()

    if scraper == "procurement_plans":
        from scrapers.treasury_procurement_plans import scrape_treasury_procurement_plans

        return scrape_treasury_procurement_plans(
            timeout=max(timeout, 60),
            relevant_only=True,
        )

    if scraper == "national_treasury":
        # Prefer non-Selenium API scraper for CI stability
        from scrapers.national_treasury import NationalTreasuryScraper

        user_agent = ((config.get("scrapers") or {}).get("user_agent") or "Mozilla/5.0")
        url = (((config.get("scrapers") or {}).get("urls") or {}).get("national_treasury") or "https://www.etenders.gov.za/")
        nt = NationalTreasuryScraper(url=url, user_agent=user_agent, timeout=timeout)
        tenders = nt.run()
        # Ensure required fields exist
        for t in tenders:
            t.setdefault("source", "National Treasury")
            t.setdefault("url", url)
        return tenders

    raise SystemExit(f"Unknown scraper: {scraper}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one scraper and write results to JSON")
    parser.add_argument(
        "--scraper",
        required=True,
        help="municipalities|soes|national_treasury|procurement_plans|joburg_water|eskom",
    )
    parser.add_argument("--out", required=True, help="Output JSON path")
    args = parser.parse_args()

    started = time.perf_counter()
    now = datetime.utcnow().replace(microsecond=0).isoformat() + "Z"
    config = load_config()
    human_source = args.scraper.replace("_", " ").title()

    payload: Dict[str, Any] = {
        "scraper": args.scraper,
        "source": human_source,
        "last_run": now,
        "status": "failure",
        "tenders_found": 0,
        "duration": 0.0,
        "error": None,
        "tenders": [],
    }

    exit_code = 0
    try:
        tenders = run_scraper(args.scraper, config=config) or []
        normalized = [normalize_tender(payload["source"], t) for t in tenders if isinstance(t, dict)]
        payload["tenders"] = normalized
        payload["tenders_found"] = len(normalized)
        payload["status"] = "success"
    except Exception as exc:
        payload["error"] = str(exc)
        exit_code = 1
    finally:
        payload["duration"] = round(time.perf_counter() - started, 3)
        atomic_write_json(args.out, payload)

    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
