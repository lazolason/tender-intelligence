"""
SQLite schema migration helpers.

The project historically relied on replaying ``schema.sql``. That remains the
bootstrap path for new databases, while this module handles ordered additive
changes for existing databases that may have drifted behind the current schema.
"""

from __future__ import annotations

import logging
import sqlite3
from dataclasses import dataclass
from typing import Callable, Iterable, List


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Migration:
    version: int
    name: str
    apply: Callable[[sqlite3.Connection], None]


def _table_exists(conn: sqlite3.Connection, table_name: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
        (table_name,),
    )
    return cursor.fetchone() is not None


def _column_exists(conn: sqlite3.Connection, table_name: str, column_name: str) -> bool:
    if not _table_exists(conn, table_name):
        return False
    cursor = conn.execute(f"PRAGMA table_info({table_name})")
    return any(row[1] == column_name for row in cursor.fetchall())


def _index_exists(conn: sqlite3.Connection, index_name: str) -> bool:
    cursor = conn.execute(
        "SELECT 1 FROM sqlite_master WHERE type = 'index' AND name = ?",
        (index_name,),
    )
    return cursor.fetchone() is not None


def _ensure_schema_migrations_table(conn: sqlite3.Connection) -> None:
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS schema_migrations (
            version INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
        """
    )


def _add_tender_matched_keywords(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "tenders") and not _column_exists(
        conn, "tenders", "matched_keywords"
    ):
        conn.execute("ALTER TABLE tenders ADD COLUMN matched_keywords TEXT")


def _extend_scraper_runs_runtime_metadata(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "scraper_runs"):
        return

    for column_name, column_type in (
        ("started_at", "TEXT"),
        ("finished_at", "TEXT"),
        ("duration_seconds", "REAL"),
    ):
        if not _column_exists(conn, "scraper_runs", column_name):
            conn.execute(
                f"ALTER TABLE scraper_runs ADD COLUMN {column_name} {column_type}"
            )


def _add_runtime_indexes(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "scraper_runs") and not _index_exists(
        conn, "idx_scraper_runs_source_run_date"
    ):
        conn.execute(
            """
            CREATE INDEX idx_scraper_runs_source_run_date
            ON scraper_runs(source, run_date DESC)
            """
        )


def _add_tender_last_seen_at(conn: sqlite3.Connection) -> None:
    if _table_exists(conn, "tenders") and not _column_exists(
        conn, "tenders", "last_seen_at"
    ):
        conn.execute("ALTER TABLE tenders ADD COLUMN last_seen_at TIMESTAMP")
        conn.execute(
            "UPDATE tenders SET last_seen_at = COALESCE(updated_at, created_at, CURRENT_TIMESTAMP)"
        )
    if _table_exists(conn, "tenders") and not _index_exists(
        conn, "idx_tenders_last_seen_at"
    ):
        conn.execute(
            "CREATE INDEX idx_tenders_last_seen_at ON tenders(last_seen_at)"
        )


def _add_authorized_feed_runs(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS authorized_feed_runs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            source_id TEXT NOT NULL,
            file_name TEXT NOT NULL,
            file_sha256 TEXT NOT NULL,
            dry_run INTEGER NOT NULL DEFAULT 0,
            status TEXT NOT NULL,
            records_total INTEGER NOT NULL DEFAULT 0,
            records_valid INTEGER NOT NULL DEFAULT 0,
            records_invalid INTEGER NOT NULL DEFAULT 0,
            records_excluded INTEGER NOT NULL DEFAULT 0,
            records_inserted INTEGER NOT NULL DEFAULT 0,
            records_updated INTEGER NOT NULL DEFAULT 0,
            records_unchanged INTEGER NOT NULL DEFAULT 0,
            error_type TEXT,
            started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            finished_at TIMESTAMP,
            UNIQUE(source_id, file_sha256, dry_run)
        );
        CREATE INDEX IF NOT EXISTS idx_authorized_feed_runs_source_started
            ON authorized_feed_runs(source_id, started_at DESC);
        """
    )


def _add_planned_opportunity_matches(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS planned_opportunity_matches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT NOT NULL UNIQUE,
            tender_ref TEXT NOT NULL,
            match_score REAL NOT NULL,
            match_method TEXT NOT NULL,
            evidence TEXT NOT NULL,
            matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (external_id) REFERENCES planned_opportunities(external_id),
            FOREIGN KEY (tender_ref) REFERENCES tenders(ref)
        );
        CREATE INDEX IF NOT EXISTS idx_planned_matches_tender_ref
            ON planned_opportunity_matches(tender_ref);
        """
    )


def _add_planned_opportunity_reconciliation(conn: sqlite3.Connection) -> None:
    if not _table_exists(conn, "planned_opportunities"):
        return
    if not _column_exists(conn, "planned_opportunities", "is_active"):
        conn.execute(
            "ALTER TABLE planned_opportunities "
            "ADD COLUMN is_active INTEGER NOT NULL DEFAULT 1"
        )
    if not _column_exists(conn, "planned_opportunities", "retired_at"):
        conn.execute(
            "ALTER TABLE planned_opportunities ADD COLUMN retired_at TIMESTAMP"
        )
    if not _index_exists(conn, "idx_planned_opportunities_source_active"):
        conn.execute(
            "CREATE INDEX idx_planned_opportunities_source_active "
            "ON planned_opportunities(source, is_active)"
        )


def _add_planned_opportunities(conn: sqlite3.Connection) -> None:
    conn.executescript(
        """
        CREATE TABLE IF NOT EXISTS planned_opportunities (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            external_id TEXT UNIQUE NOT NULL,
            institution TEXT NOT NULL,
            description TEXT NOT NULL,
            planned_advert_date TEXT,
            planned_closing_date TEXT,
            planned_award_date TEXT,
            category TEXT,
            classification_reason TEXT,
            matched_keywords TEXT,
            lifecycle_stage TEXT NOT NULL DEFAULT 'PLANNED',
            source TEXT NOT NULL,
            source_url TEXT,
            matched_tender_ref TEXT,
            first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (matched_tender_ref) REFERENCES tenders(ref)
        );
        CREATE INDEX IF NOT EXISTS idx_planned_opportunities_advert_date
            ON planned_opportunities(planned_advert_date);
        CREATE INDEX IF NOT EXISTS idx_planned_opportunities_category_stage
            ON planned_opportunities(category, lifecycle_stage);
        """
    )


MIGRATIONS: List[Migration] = [
    Migration(1, "add_tender_matched_keywords", _add_tender_matched_keywords),
    Migration(
        2,
        "extend_scraper_runs_runtime_metadata",
        _extend_scraper_runs_runtime_metadata,
    ),
    Migration(3, "add_runtime_indexes", _add_runtime_indexes),
    Migration(4, "add_planned_opportunities", _add_planned_opportunities),
    Migration(5, "add_tender_last_seen_at", _add_tender_last_seen_at),
    Migration(
        6,
        "add_planned_opportunity_reconciliation",
        _add_planned_opportunity_reconciliation,
    ),
    Migration(7, "add_planned_opportunity_matches", _add_planned_opportunity_matches),
    Migration(8, "add_authorized_feed_runs", _add_authorized_feed_runs),
]


def get_schema_version(conn: sqlite3.Connection) -> int:
    _ensure_schema_migrations_table(conn)
    cursor = conn.execute("SELECT COALESCE(MAX(version), 0) FROM schema_migrations")
    row = cursor.fetchone()
    return int(row[0] or 0) if row else 0


def get_pending_migrations(conn: sqlite3.Connection) -> List[Migration]:
    _ensure_schema_migrations_table(conn)
    cursor = conn.execute("SELECT version FROM schema_migrations")
    applied_versions = {int(row[0]) for row in cursor.fetchall()}
    return [migration for migration in MIGRATIONS if migration.version not in applied_versions]


def run_migrations(conn: sqlite3.Connection) -> List[Migration]:
    """
    Apply all unapplied migrations in version order.

    Returns:
        List of migrations applied during this call.
    """
    applied: List[Migration] = []
    _ensure_schema_migrations_table(conn)

    for migration in get_pending_migrations(conn):
        logger.info("Applying schema migration %s (%s)", migration.version, migration.name)
        migration.apply(conn)
        conn.execute(
            "INSERT INTO schema_migrations (version, name) VALUES (?, ?)",
            (migration.version, migration.name),
        )
        applied.append(migration)

    return applied
