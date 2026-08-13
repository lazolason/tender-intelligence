#!/usr/bin/env python3
"""
Restore the SQLite tenders table from the current dashboard snapshot.

This is a recovery tool for cases where the dashboard JSON is newer or more
complete than the local SQLite database. It replaces the `tenders` table
contents, clears dependent `classifications`, and preserves other tables such
as `bid_outcomes`, `bid_notes`, and `pdf_analysis`.
"""

import argparse
import json
import os
import sqlite3
from datetime import datetime

from utils.backup_database import backup_database
from utils.db_writer import DatabaseWriter


PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DEFAULT_DB_PATH = os.path.join(PROJECT_DIR, "data", "tenders.db")
DEFAULT_SNAPSHOT_PATH = os.path.join(PROJECT_DIR, "dashboard", "tenders.json")


def _load_snapshot(snapshot_path: str) -> tuple[dict, list[dict]]:
    with open(snapshot_path, "r", encoding="utf-8") as file_obj:
        payload = json.load(file_obj)

    if isinstance(payload, dict):
        meta = payload.get("meta", {}) or {}
        tenders = payload.get("tenders", []) or []
    elif isinstance(payload, list):
        meta = {}
        tenders = payload
    else:
        raise ValueError(f"Unsupported snapshot payload type: {type(payload).__name__}")

    if not isinstance(tenders, list):
        raise ValueError("Snapshot tenders payload must be a list")

    return meta, tenders


def _normalize_category(value: str) -> str:
    raw = (value or "").strip()
    if not raw:
        return "Unknown"
    if raw.lower() == "mexel":
        return "MEXEL"
    return raw


def _normalize_priority(value: str) -> str:
    raw = (value or "").strip().upper()
    return raw if raw in {"HIGH", "MEDIUM", "LOW"} else "LOW"


def _normalize_keywords(value) -> str:
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return ", ".join(str(item).strip() for item in value if str(item).strip())
    return ""


def restore_snapshot(snapshot_path: str, db_path: str, backup: bool = True) -> int:
    meta, tenders = _load_snapshot(snapshot_path)
    DatabaseWriter(db_path)

    if backup:
        if not backup_database():
            raise RuntimeError("Database backup failed; refusing to continue")

    restored_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    restore_note = f"Restored from dashboard snapshot ({os.path.basename(snapshot_path)}) on {restored_at}"
    classification_reason = (
        f"Restored from dashboard snapshot dated {meta.get('last_sync') or restored_at}"
    )

    rows = []
    for tender in tenders:
        ref = str(tender.get("ref") or "").strip().upper()
        title = str(tender.get("title") or "").strip()
        if not ref or not title:
            continue

        score = tender.get("score")
        try:
            composite_score = float(score) if score not in (None, "") else None
        except (TypeError, ValueError):
            composite_score = None

        rows.append(
            (
                ref,
                title,
                str(tender.get("description") or title).strip(),
                str(tender.get("client") or "").strip(),
                str(tender.get("source") or "").strip(),
                str(tender.get("url") or "").strip(),
                str(tender.get("closing_date") or "").strip(),
                _normalize_category(str(tender.get("category") or "")),
                classification_reason,
                composite_score,
                _normalize_priority(str(tender.get("priority") or "")),
                "Restored from dashboard snapshot",
                "New",
                "Open",
                restore_note,
                _normalize_keywords(tender.get("matched_keywords")),
            )
        )

    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute("PRAGMA busy_timeout = 10000")
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("DELETE FROM classifications")
        conn.execute("DELETE FROM tenders")
        conn.executemany(
            """
            INSERT INTO tenders (
                ref,
                title,
                description,
                client,
                source,
                url,
                closing_date,
                category,
                classification_reason,
                composite_score,
                priority,
                recommendation,
                stage,
                status,
                notes,
                matched_keywords
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            rows,
        )

    return len(rows)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Restore SQLite tenders from the current dashboard snapshot."
    )
    parser.add_argument(
        "--snapshot",
        default=DEFAULT_SNAPSHOT_PATH,
        help="Path to dashboard snapshot JSON (default: dashboard/tenders.json)",
    )
    parser.add_argument(
        "--db-path",
        default=DEFAULT_DB_PATH,
        help="Path to SQLite database (default: data/tenders.db)",
    )
    parser.add_argument(
        "--no-backup",
        action="store_true",
        help="Skip creating a database backup before restore",
    )
    args = parser.parse_args()

    restored = restore_snapshot(
        snapshot_path=args.snapshot,
        db_path=args.db_path,
        backup=not args.no_backup,
    )
    print(f"✅ Restored {restored} tenders from {args.snapshot} into {args.db_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
