import json

from sync_dashboard import sync
from utils.dashboard_snapshot import inspect_dashboard_snapshot
from utils.db_writer import DatabaseWriter


def test_db_to_dashboard_sync_smoke(tmp_path, monkeypatch):
    db_path = tmp_path / "data" / "tenders.db"
    dashboard_dir = tmp_path / "dashboard"
    dashboard_json = dashboard_dir / "tenders.json"
    public_json = dashboard_dir / "public" / "tenders-latest.json"

    writer = DatabaseWriter(str(db_path))
    was_added, scores, classification = writer.add_tender_with_scoring(
        {
            "ref": "SMOKE-001",
            "title": "Cooling water treatment chemicals",
            "description": "Supply of Mexel-compatible cooling water treatment chemicals",
            "client": "Eskom",
            "source": "National Treasury",
            "url": "https://example.com/tender",
            "closing_date": "2026-04-30",
        }
    )

    assert was_added is True
    assert scores["priority"] in {"HIGH", "MEDIUM", "LOW"}
    assert classification["category"] == "MEXEL"

    monkeypatch.setattr("sync_dashboard.DB_PATH", str(db_path))
    monkeypatch.setattr("sync_dashboard.DASHBOARD_DIR", str(dashboard_dir))
    monkeypatch.setattr("sync_dashboard.TENDERS_DATA_JSON", str(dashboard_json))
    monkeypatch.setattr("sync_dashboard.PUBLIC_TENDERS_JSON", str(public_json))
    monkeypatch.setattr("sync_dashboard.MEXEL_ONLY", False)
    monkeypatch.setattr("sync_dashboard.DASHBOARD_SHOW_ALL", True)

    assert sync() is True

    dashboard_payload = json.loads(dashboard_json.read_text(encoding="utf-8"))
    public_payload = json.loads(public_json.read_text(encoding="utf-8"))

    assert dashboard_payload == public_payload
    assert dashboard_payload["meta"]["tender_count"] == 1
    assert len(dashboard_payload["tenders"]) == 1
    assert dashboard_payload["tenders"][0]["ref"] == "SMOKE-001"
    assert dashboard_payload["tenders"][0]["company"] == "Mexel"

    snapshot_info = inspect_dashboard_snapshot(str(dashboard_json))
    assert snapshot_info["exists"] is True
    assert snapshot_info["record_count"] == 1
    assert snapshot_info["stale"] is False
