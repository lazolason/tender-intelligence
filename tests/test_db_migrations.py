import os
import sqlite3

from utils.db_writer import DatabaseWriter


def test_database_writer_applies_pending_schema_migrations(tmp_path):
    db_path = tmp_path / "legacy.db"

    with sqlite3.connect(db_path) as conn:
        conn.executescript(
            """
            CREATE TABLE tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                ref TEXT UNIQUE NOT NULL,
                title TEXT NOT NULL,
                description TEXT,
                client TEXT,
                source TEXT,
                url TEXT,
                closing_date TEXT,
                category TEXT,
                classification_reason TEXT,
                fit_score REAL,
                industry_score REAL,
                mexel_suitability REAL,
                composite_score REAL,
                priority TEXT,
                recommendation TEXT,
                stage TEXT DEFAULT 'New',
                status TEXT DEFAULT 'Open',
                next_action TEXT,
                notes TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE scraper_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                source TEXT,
                run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                tenders_found INTEGER,
                tenders_new INTEGER,
                status TEXT,
                error_message TEXT
            );
            """
        )

    writer = DatabaseWriter(str(db_path))
    assert os.path.exists(writer.db_path)

    with sqlite3.connect(db_path) as conn:
        tender_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(tenders)").fetchall()
        }
        scraper_run_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(scraper_runs)").fetchall()
        }
        planned_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(planned_opportunities)").fetchall()
        }
        match_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(planned_opportunity_matches)").fetchall()
        }
        feed_run_columns = {
            row[1] for row in conn.execute("PRAGMA table_info(authorized_feed_runs)").fetchall()
        }
        applied_versions = conn.execute(
            "SELECT version FROM schema_migrations ORDER BY version"
        ).fetchall()

    assert {"matched_keywords", "last_seen_at"} <= tender_columns
    assert {"started_at", "finished_at", "duration_seconds"} <= scraper_run_columns
    assert {
        "external_id",
        "planned_advert_date",
        "lifecycle_stage",
        "last_seen_at",
        "is_active",
        "retired_at",
    } <= planned_columns
    assert {"external_id", "tender_ref", "match_score", "evidence"} <= match_columns
    assert {"source_id", "file_sha256", "status", "records_inserted"} <= feed_run_columns
    assert [row[0] for row in applied_versions] == [1, 2, 3, 4, 5, 6, 7, 8]
