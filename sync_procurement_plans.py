#!/usr/bin/env python3
"""Refresh Treasury procurement plans in SQLite for early-warning intelligence."""

from __future__ import annotations

import os
from typing import Any, Dict

from dotenv import load_dotenv

from scrapers.treasury_procurement_plans import (
    is_relevant_plan,
    scrape_treasury_procurement_plans,
)
from utils.config_validator import load_and_validate_config
from utils.db_writer import DatabaseWriter
from utils.procurement_plan_linker import link_planned_opportunities


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(PROJECT_DIR, ".env"))


def sync_procurement_plans() -> Dict[str, Any]:
    config = load_and_validate_config()
    plan_config = config.get("procurement_plans", {}) or {}
    db_path = os.getenv("DB_PATH", os.path.join(PROJECT_DIR, "data", "tenders.db"))
    if not bool(plan_config.get("enabled", True)):
        return {"status": "disabled", "fetched": 0, "persisted": 0}

    # Fetch the complete snapshot first. Reconciliation must never infer removals
    # from a pre-filtered or suspiciously small source response.
    all_plans = scrape_treasury_procurement_plans(
        timeout=int(plan_config.get("timeout", 60)),
        relevant_only=False,
    )
    minimum_rows = int(plan_config.get("minimum_snapshot_rows", 100))
    if len(all_plans) < minimum_rows:
        raise ValueError(
            f"Treasury snapshot has {len(all_plans)} rows; expected at least {minimum_rows}"
        )

    relevant_only = bool(plan_config.get("relevant_only", True))
    plans = [plan for plan in all_plans if is_relevant_plan(plan)] if relevant_only else all_plans
    source = "National Treasury Procurement Plans"
    writer = DatabaseWriter(db_path)
    reconciliation = writer.reconcile_planned_opportunities(plans, source=source)
    linkage = link_planned_opportunities(
        db_path,
        minimum_score=float(plan_config.get("link_minimum_score", 0.86)),
        ambiguity_margin=float(plan_config.get("link_ambiguity_margin", 0.08)),
    )
    return {
        "status": "success",
        "fetched": len(plans),
        "raw_fetched": len(all_plans),
        "persisted": reconciliation["persisted"],
        "relevant_only": relevant_only,
        "reconciliation": reconciliation,
        "linkage": linkage,
    }


if __name__ == "__main__":
    result = sync_procurement_plans()
    print(
        "Treasury procurement plans refreshed: "
        f"{result['persisted']} persisted from {result['fetched']} fetched"
    )
