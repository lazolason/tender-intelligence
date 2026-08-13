import json
from datetime import datetime

from sync_dashboard import write_dashboard_payload
from tools.build_dashboard_snapshot import build_snapshot_from_inputs
from utils.dashboard_snapshot import inspect_dashboard_snapshot, parse_snapshot_timestamp


def test_parse_snapshot_timestamp_handles_repo_formats():
    assert parse_snapshot_timestamp("2026-04-06 12:27") == datetime(2026, 4, 6, 12, 27)
    assert parse_snapshot_timestamp("2026-04-06T12:27:00") == datetime(2026, 4, 6, 12, 27)


def test_inspect_dashboard_snapshot_reports_stale_status(tmp_path):
    snapshot_path = tmp_path / "tenders.json"
    snapshot_path.write_text(
        json.dumps(
            {
                "meta": {"last_sync": "2026-04-01 10:00"},
                "tenders": [{"ref": "T1"}, {"ref": "T2"}],
            }
        ),
        encoding="utf-8",
    )

    info = inspect_dashboard_snapshot(
        str(snapshot_path),
        now=datetime(2026, 4, 6, 12, 0),
        stale_hours=24,
    )

    assert info["exists"] is True
    assert info["record_count"] == 2
    assert info["stale"] is True
    assert info["age_hours"] == 122.0


def test_static_snapshot_uses_canonical_validation(tmp_path, monkeypatch):
    input_path = tmp_path / "scrape.json"
    input_path.write_text(
        json.dumps({
            "tenders": [
                {
                    "ref": "SNAP-VALID",
                    "title": "Cooling water treatment chemicals",
                    "description": "Condenser chemical dosing and treatment",
                    "client": "Eskom",
                    "source": "Private Test Source",
                    "url": "https://example.com/tender",
                    "closing_date": "2099-05-01",
                },
                {
                    "ref": "SNAP-INVALID",
                    "title": "Cooling water treatment chemicals",
                    "description": "Condenser chemical dosing and treatment",
                    "client": "Eskom",
                    "source": "",
                    "url": "https://example.com/tender",
                    "closing_date": "2099-05-01",
                },
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("tools.build_dashboard_snapshot._load_planned_opportunities", lambda: [])

    payload = build_snapshot_from_inputs([str(input_path)], limit=200)

    assert [item["ref"] for item in payload["tenders"]] == ["SNAP-VALID"]
    assert payload["meta"]["validation"]["valid"] == 1
    assert payload["meta"]["validation"]["invalid"] == 1
    assert payload["meta"]["validation"]["error_counts"] == {"Missing source": 1}


def test_write_dashboard_payload_updates_all_targets(tmp_path):
    payload = {
        "meta": {"last_sync": "2026-04-06 12:27"},
        "tenders": [{"ref": "ABC-1", "title": "Example tender"}],
    }
    out_a = tmp_path / "dashboard" / "tenders.json"
    out_b = tmp_path / "dashboard" / "public" / "tenders-latest.json"

    written_paths = write_dashboard_payload(
        payload,
        output_paths=[str(out_a), str(out_b)],
    )

    assert written_paths == [str(out_a), str(out_b)]
    assert json.loads(out_a.read_text(encoding="utf-8")) == payload
    assert json.loads(out_b.read_text(encoding="utf-8")) == payload
