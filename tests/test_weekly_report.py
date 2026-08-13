import sqlite3
from datetime import datetime, timedelta

import weekly_report


def _create_tender_db(path):
    with sqlite3.connect(path) as conn:
        conn.execute(
            """
            CREATE TABLE tenders (
                ref TEXT,
                title TEXT,
                client TEXT,
                category TEXT,
                source TEXT,
                composite_score REAL,
                priority TEXT,
                closing_date TEXT,
                status TEXT,
                created_at TEXT
            )
            """
        )
        conn.executemany(
            "INSERT INTO tenders VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    "MEX-1",
                    "Cooling treatment",
                    "Eskom",
                    "MEXEL",
                    "Eskom",
                    8.5,
                    "HIGH",
                    (datetime.now() + timedelta(days=3)).date().isoformat(),
                    "Open",
                    datetime.now().isoformat(),
                ),
                (
                    "PHA-1",
                    "Boiler controls",
                    "Client",
                    "PHAKATHI",
                    "Treasury",
                    5.0,
                    "MEDIUM",
                    None,
                    "Open",
                    datetime.now().isoformat(),
                ),
                (
                    "NO-1",
                    "Out of scope",
                    "Client",
                    "EXCLUDED",
                    "Other",
                    1.0,
                    "LOW",
                    None,
                    "Open",
                    datetime.now().isoformat(),
                ),
            ],
        )


def test_weekly_stats_follow_dashboard_category_filter(tmp_path, monkeypatch):
    db_path = tmp_path / "tenders.db"
    _create_tender_db(db_path)
    monkeypatch.setattr(weekly_report, "DB_PATH", str(db_path))
    monkeypatch.setattr(weekly_report, "DASHBOARD_SHOW_ALL", False)
    monkeypatch.setattr(weekly_report, "MEXEL_ONLY", False)

    stats = weekly_report.get_weekly_stats()

    assert stats["total"] == 2
    assert stats["by_type"] == {"MEXEL": 1, "PHAKATHI": 1}
    assert "EXCLUDED" not in stats["by_type"]

    monkeypatch.setattr(weekly_report, "MEXEL_ONLY", True)
    assert weekly_report.get_weekly_stats()["total"] == 1

    monkeypatch.setattr(weekly_report, "DASHBOARD_SHOW_ALL", True)
    assert weekly_report.get_weekly_stats()["total"] == 3


def test_weekly_html_escapes_tender_and_health_fields(monkeypatch):
    stats = weekly_report._default_weekly_stats()
    stats.update(
        {
            "total": 1,
            "by_type": {"<img src=x onerror=alert(1)>": 1},
            "by_priority": {"HIGH": 1, "MEDIUM": 0, "LOW": 0},
            "closing_soon": [
                {
                    "ref": "<script>alert(1)</script>",
                    "title": "Cooling <b>tower</b>",
                    "client": "A&B",
                    "days_left": 1,
                    "priority": "HIGH",
                }
            ],
            "high_priority": [],
            "top_sources": {"Source <svg/onload=alert(1)>": 1},
        }
    )
    monkeypatch.setattr(
        weekly_report,
        "_load_scraper_health",
        lambda: {"Bad <script>": {"status": "<b>failed</b>", "consecutive_failures": 3}},
    )

    html = weekly_report.generate_weekly_html(stats)

    assert "<script>alert(1)</script>" not in html
    assert "<img src=x onerror=alert(1)>" not in html
    assert "<svg/onload=alert(1)>" not in html
    assert "&lt;script&gt;alert(1)&lt;/script&gt;" in html
    assert "A&amp;B" in html
    assert "&lt;b&gt;failed&lt;/b&gt;" in html
