"""
Helpers for inspecting dashboard snapshot payloads.
"""

from __future__ import annotations

import json
import math
import os
from datetime import datetime
from typing import Any, Dict, Optional


DEFAULT_STALE_HOURS = 48.0


def parse_snapshot_timestamp(value: Any) -> Optional[datetime]:
    """Parse dashboard snapshot timestamps in the formats used by the repo."""
    if value in (None, ""):
        return None

    raw = str(value).strip()
    if not raw:
        return None

    candidates = [raw]
    if " " in raw and "T" not in raw:
        candidates.append(raw.replace(" ", "T"))
    if raw.endswith("Z"):
        candidates.append(raw[:-1] + "+00:00")

    for candidate in candidates:
        try:
            return datetime.fromisoformat(candidate)
        except ValueError:
            continue

    for fmt in ("%Y-%m-%d %H:%M", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(raw, fmt)
        except ValueError:
            continue

    return None


def compute_snapshot_freshness_hours(
    timestamp: Optional[datetime], *, now: Optional[datetime] = None
) -> Optional[float]:
    """Return snapshot age in hours, rounded to two decimals."""
    if timestamp is None:
        return None
    now = now or datetime.now()
    age_hours = (now - timestamp.replace(tzinfo=None)).total_seconds() / 3600
    return round(age_hours, 2)


def inspect_dashboard_snapshot(
    path: str,
    *,
    now: Optional[datetime] = None,
    stale_hours: float = DEFAULT_STALE_HOURS,
) -> Dict[str, Any]:
    """
    Inspect a dashboard snapshot file and return health metadata.
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
        info.update({"error": str(exc)})
        return info

    tenders = payload.get("tenders", []) if isinstance(payload, dict) else []
    meta = payload.get("meta", {}) if isinstance(payload, dict) else {}
    last_sync = meta.get("last_sync") or meta.get("last_update")
    parsed_sync = parse_snapshot_timestamp(last_sync)
    age_hours = compute_snapshot_freshness_hours(parsed_sync, now=now)

    info.update(
        {
            "record_count": len(tenders) if isinstance(tenders, list) else None,
            "snapshot_origin": meta.get("snapshot_origin"),
            "last_sync": last_sync,
            "age_hours": age_hours,
            "stale": bool(age_hours is not None and age_hours > stale_hours),
        }
    )
    return info
