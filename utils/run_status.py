"""
Helpers for inspecting persisted automation run status artifacts.
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from typing import Any, Dict

from utils.dashboard_snapshot import (
    compute_snapshot_freshness_hours,
    parse_snapshot_timestamp,
)


DEFAULT_RUN_STALE_HOURS = 36.0


def daily_run_outcome(results: Dict[str, Any]) -> str:
    """Distinguish a completed workflow from failed core or auxiliary steps."""
    for name in ("scan", "sync"):
        step = results.get(name)
        if not isinstance(step, dict) or step.get("status") != "success":
            return "error"
    if results["scan"].get("failed_sources_count", 0):
        return "partial"
    for name in ("email", "procurement_plans", "backup"):
        step = results.get(name) or {}
        if step.get("status") in {"error", "failed", "failure"}:
            return "partial"
    return "success"


def inspect_daily_run_status(
    path: str,
    *,
    stale_hours: float = DEFAULT_RUN_STALE_HOURS,
    now: datetime | None = None,
) -> Dict[str, Any]:
    """
    Inspect the persisted daily runner summary and return health metadata.
    """
    info: Dict[str, Any] = {
        "path": path,
        "exists": os.path.exists(path),
        "stale_threshold_hours": stale_hours,
    }

    if not info["exists"]:
        return info

    try:
        with open(path, "r", encoding="utf-8") as file_obj:
            payload = json.load(file_obj)
    except Exception as exc:
        info["error"] = str(exc)
        return info

    if not isinstance(payload, dict):
        info["error"] = "Daily run status must be an object"
        return info

    timestamp = payload.get("timestamp")
    parsed_timestamp = parse_snapshot_timestamp(timestamp)
    age_hours = compute_snapshot_freshness_hours(parsed_timestamp, now=now)

    scan = payload.get("scan") or {}
    sync = payload.get("sync") or {}
    email = payload.get("email") or {}

    info.update(
        {
            "timestamp": timestamp,
            "age_hours": age_hours,
            "stale": bool(age_hours is not None and age_hours > stale_hours),
            "scan_status": scan.get("status"),
            "sync_status": sync.get("status"),
            "email_status": email.get("status"),
            "scan_total_scraped": scan.get("total_scraped"),
            "scan_new_added": scan.get("new_added"),
        }
    )
    return info
