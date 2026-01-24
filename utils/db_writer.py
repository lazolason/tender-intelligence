# ==========================================================
# SQLITE DATABASE WRITER UTILITY
# Replaces excel_writer.py
# ==========================================================

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
        if not os.path.exists(os.path.dirname(self.db_path)):
            os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
            
        # Re-run schema in case table doesn't exist (idempotent)
        schema_path = os.path.join(os.path.dirname(os.path.dirname(self.db_path)), "schema.sql")
        if os.path.exists(schema_path):
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
            
            with sqlite3.connect(self.db_path) as conn:
                conn.executescript(schema_sql)

    def get_existing_references(self) -> set:
        """Get set of existing tender reference numbers."""
        with sqlite3.connect(self.db_path) as conn:
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

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            
            columns = [
                "ref", "title", "description", "client", "source", "url",
                "closing_date", "category", "classification_reason",
                "fit_score", "industry_score", "mexel_suitability",
                "composite_score", "priority", "recommendation",
                "stage", "status", "next_action", "notes"
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

    def add_tender_with_scoring(self, tender_data: Dict[str, Any]) -> Tuple[bool, Dict[str, Any], Dict[str, Any]]:
        """
        Full pipeline: Classify -> Score -> Write to DB.
        
        Args:
            tender_data: Dict with 'ref', 'title', 'description', 'client', 'source', 'url', 'closing_date'
            
        Returns:
            (was_added, scores, classification)
        """
        # 1. Duplicate Check
        ref = str(tender_data.get("ref", "")).strip().upper()
        if ref and ref != "NA":
            if ref in self.get_existing_references():
                return False, {}, {}

        # 2. Classify
        classification = classify_tender(tender_data["title"], tender_data["description"])
        category = classification["category"]
        reason = classification["reason"]

        # 3. Score
        scores = score_tender(
            title=tender_data["title"],
            description=tender_data["description"],
            client=tender_data["client"],
            closing_date=tender_data["closing_date"],
            category=category
        )

        # 4. Prepare DB record
        db_record = tender_data.copy()
        db_record.update({
            "category": category,
            "classification_reason": reason,
            "fit_score": scores["fit_score"],
            "industry_score": scores["industry_score"], # This is a float in scoring_engine
            "mexel_suitability": scores["mexel_suitability"],
            "composite_score": scores["composite_score"],
            "priority": scores["priority"],
            "recommendation": scores["recommendation"],
            "next_action": "Review" if scores["priority"] == "LOW" else "Prepare Bid" if scores["priority"] == "MEDIUM" else "URGENT BID",
            "notes": f"{reason}\n[Score: {scores['composite_score']}/10]\n{scores['recommendation']}"
        })

        # 5. Write
        was_added = self.write_tender(db_record)
        return was_added, scores, classification

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregate statistics from the database."""
        with sqlite3.connect(self.db_path) as conn:
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
        with sqlite3.connect(self.db_path) as conn:
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
