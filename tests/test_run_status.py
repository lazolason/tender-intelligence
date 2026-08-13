import json
from datetime import datetime

from utils.run_status import inspect_daily_run_status


def test_inspect_daily_run_status_reports_fresh_success(tmp_path):
    status_path = tmp_path / "last_daily_run.json"
    status_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-04-06T08:00:00",
                "scan": {"status": "success", "total_scraped": 12, "new_added": 3},
                "sync": {"status": "success"},
                "email": {"status": "sent"},
            }
        ),
        encoding="utf-8",
    )

    info = inspect_daily_run_status(
        str(status_path),
        now=datetime(2026, 4, 6, 12, 0, 0),
        stale_hours=36,
    )

    assert info["exists"] is True
    assert info["stale"] is False
    assert info["scan_status"] == "success"
    assert info["sync_status"] == "success"
    assert info["email_status"] == "sent"
    assert info["scan_total_scraped"] == 12
    assert info["scan_new_added"] == 3


def test_inspect_daily_run_status_reports_stale_run(tmp_path):
    status_path = tmp_path / "last_daily_run.json"
    status_path.write_text(
        json.dumps(
            {
                "timestamp": "2026-04-04T00:00:00",
                "scan": {"status": "error"},
                "sync": {"status": "failed"},
                "email": {"status": "error"},
            }
        ),
        encoding="utf-8",
    )

    info = inspect_daily_run_status(
        str(status_path),
        now=datetime(2026, 4, 6, 12, 0, 0),
        stale_hours=24,
    )

    assert info["stale"] is True
    assert info["scan_status"] == "error"
    assert info["sync_status"] == "failed"
