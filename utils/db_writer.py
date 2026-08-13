# ==========================================================
# SQLITE DATABASE WRITER UTILITY
# Replaces excel_writer.py
# ==========================================================

import json
import sqlite3
import os
import sys
from datetime import datetime
import logging
from typing import Dict, List, Optional, Tuple, Any

# Ensure parent directory is in path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender
from scoring_engine import score_tender
from utils.db_migrations import get_schema_version, run_migrations

logger = logging.getLogger(__name__)

class DatabaseWriter:
    """
    Manages SQLite database operations for tender storage and scoring.
    """
    
    def __init__(self, db_path: str, log_file_path: str = None) -> None:
        """
        Initialize database writer.
        
        Args:
            db_path: Path to SQLite database file
            log_file_path: Optional path to log file
        """
        self.db_path = db_path
        self.log_file_path = log_file_path
        self._ensure_database()

    def _connect(self) -> sqlite3.Connection:
        """Open a SQLite connection with the runtime pragmas used by the app."""
        conn = sqlite3.connect(self.db_path, timeout=10.0)
        conn.execute("PRAGMA foreign_keys = ON")
        conn.execute("PRAGMA busy_timeout = 10000")
        try:
            conn.execute("PRAGMA journal_mode = WAL")
        except sqlite3.DatabaseError:
            # WAL is a runtime optimization, not a correctness requirement.
            pass
        return conn

    def _log(self, message: str, level: str = "INFO") -> None:
        """Log message to console and optionally to file."""
        if self.log_file_path:
            try:
                from utils.logging_tools import write_log
                write_log(self.log_file_path, message, level)
                return
            except Exception:
                pass
        
        levels = {"INFO": "\033[94mINFO\033[0m", "WARNING": "\033[93mWARNING\033[0m", "ERROR": "\033[91mERROR\033[0m"}
        print(f"{levels.get(level, level)}: {message}")

    def _ensure_database(self) -> None:
        """Ensure the database and schema exist."""
        db_dir = os.path.dirname(self.db_path)
        if db_dir and not os.path.exists(db_dir):
            os.makedirs(db_dir, exist_ok=True)
            
        # Re-run schema in case the DB is new or partially initialized (idempotent).
        schema_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "schema.sql"
        )
        if os.path.exists(schema_path):
            with open(schema_path, 'r', encoding="utf-8") as f:
                schema_sql = f.read()
            
            with self._connect() as conn:
                conn.executescript(schema_sql)
                applied = run_migrations(conn)
                if applied:
                    self._log(
                        "Applied schema migrations: "
                        + ", ".join(f"v{migration.version}" for migration in applied)
                    )
                logger.debug("SQLite schema version: %s", get_schema_version(conn))

    def get_existing_references(self) -> set:
        """Get set of existing tender reference numbers."""
        with self._connect() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT ref FROM tenders")
            return {row[0].strip().upper() for row in cursor.fetchall() if row[0]}

    def write_tender(self, tender_data: Dict[str, Any]) -> bool:
        """
        Write a tender dictionary to the database.
        
        Returns:
            True if added, False if duplicate ref exists.
        """
        ref = str(tender_data.get("ref", "")).strip().upper()
        
        # Guard against duplicates
        if ref and ref != "NA":
            existing = self.get_existing_references()
            if ref in existing:
                return False

        with self._connect() as conn:
            cursor = conn.cursor()
            
            columns = [
                "ref", "title", "description", "client", "source", "url",
                "closing_date", "category", "classification_reason",
                "fit_score", "industry_score", "mexel_suitability",
                "composite_score", "priority", "recommendation",
                "stage", "status", "next_action", "notes", "matched_keywords"
            ]
            
            placeholders = ", ".join(["?" for _ in columns])
            values = [tender_data.get(col) for col in columns]
            
            # Handle defaults if missing
            if not tender_data.get("stage"): values[columns.index("stage")] = "New"
            if not tender_data.get("status"): values[columns.index("status")] = "Open"
            if not tender_data.get("priority"): values[columns.index("priority")] = "MEDIUM"
            
            try:
                cursor.execute(f"INSERT INTO tenders ({', '.join(columns)}) VALUES ({placeholders})", values)
                return True
            except sqlite3.IntegrityError:
                return False

    def upsert_tender_with_scoring(
        self, tender_data: Dict[str, Any]
    ) -> Tuple[str, Dict[str, Any], Dict[str, Any]]:
        """Classify, score, and atomically insert or refresh a tender.

        Returns ``(action, scores, classification)`` where action is one of
        ``inserted``, ``updated``, ``unchanged``, or ``excluded``. Excluded
        classifications never reach persistence. Scraped and derived fields
        refresh on an update; user-managed workflow fields (stage, status,
        next_action, and notes) remain untouched.
        """
        ref = str(tender_data.get("ref", "")).strip().upper()
        if not ref or ref == "NA":
            raise ValueError("A stable tender reference is required for upsert")

        title = tender_data["title"]
        description = tender_data.get("description") or title
        client = tender_data.get("client", "")
        closing_date = tender_data.get("closing_date", "")
        classification = classify_tender(title, description)
        category = classification["category"]
        reason = classification["reason"]
        scores = score_tender(
            title=title,
            description=description,
            client=client,
            closing_date=closing_date,
            category=category,
        )
        matched_keywords = ", ".join(classification.get("matched_keywords", []))

        if category == "EXCLUDED":
            return "excluded", scores, classification

        refreshed = {
            "title": title,
            "description": description,
            "client": client,
            "source": tender_data.get("source", ""),
            "url": tender_data.get("url", ""),
            "closing_date": closing_date,
            "category": category,
            "classification_reason": reason,
            "fit_score": scores["fit_score"],
            "industry_score": scores["industry_score"],
            "mexel_suitability": scores["mexel_suitability"],
            "composite_score": scores["composite_score"],
            "priority": scores["priority"],
            "recommendation": scores["recommendation"],
            "matched_keywords": matched_keywords,
        }
        refresh_columns = list(refreshed)

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            # Serialize the read/compare/write sequence so concurrent runners cannot
            # both decide that the same reference is new.
            conn.execute("BEGIN IMMEDIATE")
            existing = conn.execute(
                f"SELECT id, {', '.join(refresh_columns)} FROM tenders WHERE UPPER(TRIM(ref)) = ?",
                (ref,),
            ).fetchone()

            if existing is None:
                next_action = (
                    "Review" if scores["priority"] == "LOW"
                    else "Prepare Bid" if scores["priority"] == "MEDIUM"
                    else "URGENT BID"
                )
                notes = (
                    f"{reason}\n[Score: {scores['composite_score']}/10]\n"
                    f"{scores['recommendation']}"
                )
                insert_values = {
                    "ref": ref,
                    **refreshed,
                    "stage": tender_data.get("stage") or "New",
                    "status": tender_data.get("status") or "Open",
                    "next_action": tender_data.get("next_action") or next_action,
                    "notes": tender_data.get("notes") or notes,
                }
                columns = list(insert_values)
                conn.execute(
                    f"INSERT INTO tenders ({', '.join(columns)}, last_seen_at) "
                    f"VALUES ({', '.join('?' for _ in columns)}, CURRENT_TIMESTAMP)",
                    [insert_values[column] for column in columns],
                )
                tender_id = conn.execute(
                    "SELECT id FROM tenders WHERE ref = ?", (ref,)
                ).fetchone()[0]
                action = "inserted"
            else:
                tender_id = existing["id"]
                changed = any(existing[column] != refreshed[column] for column in refresh_columns)
                if changed:
                    assignments = ", ".join(f"{column} = ?" for column in refresh_columns)
                    conn.execute(
                        f"UPDATE tenders SET {assignments}, updated_at = CURRENT_TIMESTAMP, "
                        "last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                        [refreshed[column] for column in refresh_columns] + [tender_id],
                    )
                    action = "updated"
                else:
                    conn.execute(
                        "UPDATE tenders SET last_seen_at = CURRENT_TIMESTAMP WHERE id = ?",
                        (tender_id,),
                    )
                    action = "unchanged"

            if action != "unchanged" and matched_keywords:
                conn.execute(
                    "INSERT INTO classifications "
                    "(tender_id, matched_keywords, classification_reason) VALUES (?, ?, ?)",
                    (tender_id, matched_keywords, reason),
                )

        return action, scores, classification

    def add_tender_with_scoring(
        self, tender_data: Dict[str, Any]
    ) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
        """Compatibility wrapper returning True only for a newly inserted tender."""
        action, scores, classification = self.upsert_tender_with_scoring(tender_data)
        return action == "inserted", scores, classification

    @staticmethod
    def _planned_opportunity_values(plan: Dict[str, Any]) -> tuple:
        return (
            plan["external_id"],
            plan["institution"],
            plan["description"],
            plan.get("planned_advert_date"),
            plan.get("planned_closing_date"),
            plan.get("planned_award_date"),
            plan.get("category"),
            plan.get("classification_reason", ""),
            json.dumps(
                sorted(set(plan.get("matched_keywords", [])), key=str.casefold),
                ensure_ascii=False,
            ),
            plan.get("lifecycle_stage", "PLANNED"),
            plan.get("source", "National Treasury Procurement Plans"),
            plan.get("source_url", ""),
        )

    _PLANNED_UPSERT_SQL = """
        INSERT INTO planned_opportunities (
            external_id, institution, description, planned_advert_date,
            planned_closing_date, planned_award_date, category,
            classification_reason, matched_keywords, lifecycle_stage,
            source, source_url, is_active, retired_at, last_seen_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, NULL, CURRENT_TIMESTAMP)
        ON CONFLICT(external_id) DO UPDATE SET
            institution = excluded.institution,
            description = excluded.description,
            planned_advert_date = excluded.planned_advert_date,
            planned_closing_date = excluded.planned_closing_date,
            planned_award_date = excluded.planned_award_date,
            category = excluded.category,
            classification_reason = excluded.classification_reason,
            matched_keywords = excluded.matched_keywords,
            lifecycle_stage = CASE
                WHEN planned_opportunities.matched_tender_ref IS NOT NULL THEN 'MATCHED'
                ELSE excluded.lifecycle_stage
            END,
            source = excluded.source,
            source_url = excluded.source_url,
            is_active = 1,
            retired_at = NULL,
            last_seen_at = CURRENT_TIMESTAMP
    """

    def upsert_planned_opportunities(self, plans: List[Dict[str, Any]]) -> int:
        """Insert or refresh plans without retiring records absent from this batch."""
        if not plans:
            return 0
        values = [self._planned_opportunity_values(plan) for plan in plans]
        with self._connect() as conn:
            conn.executemany(self._PLANNED_UPSERT_SQL, values)
        return len(values)

    def reconcile_planned_opportunities(
        self,
        plans: List[Dict[str, Any]],
        *,
        source: str,
    ) -> Dict[str, int]:
        """Atomically reconcile one complete source snapshot.

        Plans no longer present in the complete snapshot are retained for audit
        but marked inactive. A later appearance reactivates the same record.
        """
        if any(plan.get("source", source) != source for plan in plans):
            raise ValueError("All reconciled plans must belong to the requested source")

        compare_columns = (
            "institution", "description", "planned_advert_date",
            "planned_closing_date", "planned_award_date", "category",
            "classification_reason", "matched_keywords", "lifecycle_stage",
            "source_url",
        )
        incoming = {plan["external_id"]: plan for plan in plans}
        stats = {
            "inserted": 0,
            "updated": 0,
            "unchanged": 0,
            "reactivated": 0,
            "retired": 0,
        }

        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            conn.execute("BEGIN IMMEDIATE")
            existing_rows = conn.execute(
                "SELECT * FROM planned_opportunities WHERE source = ?",
                (source,),
            ).fetchall()
            existing = {row["external_id"]: row for row in existing_rows}

            for external_id, plan in incoming.items():
                row = existing.get(external_id)
                if row is None:
                    stats["inserted"] += 1
                elif not row["is_active"]:
                    stats["reactivated"] += 1
                else:
                    normalized = dict(plan)
                    if row["matched_tender_ref"] is not None:
                        normalized["lifecycle_stage"] = "MATCHED"
                    normalized["matched_keywords"] = json.dumps(
                        sorted(
                            set(plan.get("matched_keywords", [])),
                            key=str.casefold,
                        ),
                        ensure_ascii=False,
                    )
                    if any(row[column] != normalized.get(column) for column in compare_columns):
                        stats["updated"] += 1
                    else:
                        stats["unchanged"] += 1

            retired_ids = [
                external_id
                for external_id, row in existing.items()
                if row["is_active"] and external_id not in incoming
            ]
            if retired_ids:
                conn.executemany(
                    "UPDATE planned_opportunities SET is_active = 0, "
                    "retired_at = CURRENT_TIMESTAMP, lifecycle_stage = 'RETIRED' "
                    "WHERE external_id = ?",
                    [(external_id,) for external_id in retired_ids],
                )
                stats["retired"] = len(retired_ids)

            if plans:
                conn.executemany(
                    self._PLANNED_UPSERT_SQL,
                    [self._planned_opportunity_values(plan) for plan in plans],
                )

        stats["persisted"] = len(plans)
        return stats

    def save_pdf_analysis(self, tender_ref: str, analysis: Dict[str, Any]) -> bool:
        """Save PDF analysis results to the database."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO pdf_analysis 
                    (tender_ref, page_count, word_count, requirements, deadlines, values_extracted, contact_info, full_text)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tender_ref,
                    analysis.get("page_count"),
                    analysis.get("word_count"),
                    json.dumps(analysis.get("requirements", [])),
                    json.dumps(analysis.get("deadlines", [])),
                    json.dumps(analysis.get("values", [])),
                    json.dumps(analysis.get("contact", {})),
                    analysis.get("text", "")
                ))
                return True
        except Exception as e:
            self._log(f"Failed to save PDF analysis for {tender_ref}: {e}", "ERROR")
            return False

    def record_bid_outcome(self, tender_ref: str, company: str, submitted: bool, outcome: str, **kwargs) -> bool:
        """Record a bid outcome (won, lost, etc.)"""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT OR REPLACE INTO bid_outcomes 
                    (tender_ref, company, bid_submitted, bid_amount, outcome, winner_name, winning_amount, bid_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    tender_ref,
                    company,
                    submitted,
                    kwargs.get("bid_amount"),
                    outcome,
                    kwargs.get("winner_name"),
                    kwargs.get("winning_amount"),
                    kwargs.get("bid_date") or datetime.now().strftime("%Y-%m-%d")
                ))
                return True
        except Exception as e:
            self._log(f"Failed to record bid outcome for {tender_ref}: {e}", "ERROR")
            return False

    def add_bid_note(self, tender_ref: str, company: str, note: str) -> bool:
        """Add a note to a bid's history."""
        try:
            with self._connect() as conn:
                cursor = conn.cursor()
                cursor.execute(
                    "INSERT INTO bid_notes (tender_ref, company, note) VALUES (?, ?, ?)",
                    (tender_ref, company, note)
                )
                return True
        except Exception as e:
            self._log(f"Failed to add bid note for {tender_ref}: {e}", "ERROR")
            return False

    def get_recent_tenders(self, limit: int = 200) -> List[Dict[str, Any]]:
        """Fetch the N most recent tenders from the database for deduplication."""
        try:
            with self._connect() as conn:
                conn.row_factory = sqlite3.Row
                cursor = conn.cursor()
                cursor.execute("""
                    SELECT ref, title, description, client, source, url, closing_date, category
                    FROM tenders
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
                return [dict(row) for row in cursor.fetchall()]
        except Exception as e:
            self._log(f"Failed to fetch recent tenders: {e}", "ERROR")
            return []

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics from the database."""
        with self._connect() as conn:
            cursor = conn.cursor()
            
            stats = {
                "total": 0,
                "by_type": {},
                "by_priority": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
                "by_status": {}
            }
            
            # Total
            cursor.execute("SELECT COUNT(*) FROM tenders")
            stats["total"] = cursor.fetchone()[0]
            
            # By Type (Category)
            cursor.execute("SELECT category, COUNT(*) FROM tenders GROUP BY category")
            for cat, count in cursor.fetchall():
                stats["by_type"][cat or "Unknown"] = count
                
            # By Priority
            cursor.execute("SELECT priority, COUNT(*) FROM tenders GROUP BY priority")
            for prio, count in cursor.fetchall():
                if prio in stats["by_priority"]:
                    stats["by_priority"][prio] = count
                    
            # By Status
            cursor.execute("SELECT status, COUNT(*) FROM tenders GROUP BY status")
            for stat, count in cursor.fetchall():
                stats["by_status"][stat or "Unknown"] = count
                
            return stats

    def get_active_mexel_tenders(self, limit: int = 100) -> List[Dict[str, Any]]:
        """Query MEXEL tenders for the dashboard."""
        with self._connect() as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tenders 
                WHERE category = 'MEXEL' 
                ORDER BY created_at DESC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

if __name__ == "__main__":
    # Test
    db_path = "data/tenders.db"
    writer = DatabaseWriter(db_path)
    print(f"Stats: {writer.get_stats()}")
    print(f"Mexel Tenders: {len(writer.get_active_mexel_tenders())}")
