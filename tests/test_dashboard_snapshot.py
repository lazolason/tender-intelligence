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
                "meta": {
                    "last_sync": "2026-04-01 10:00",
                    "snapshot_origin": "static_scrape",
                },
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
    assert info["snapshot_origin"] == "static_scrape"
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
    assert payload["meta"]["snapshot_origin"] == "static_scrape"
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


def test_stored_category_is_trusted_over_name_based_reclassification(tmp_path, monkeypatch):
    """Database inputs are already filtered; re-classifying them only removes rows.

    On 2026-11-03 this double classification cut 87 stored tenders to 4 before
    date validation, so a dashboard that should show ~32 showed 1.
    """
    input_path = tmp_path / "scrape.json"
    input_path.write_text(
        json.dumps({
            "tenders": [
                {
                    "ref": "SNAP-STORED",
                    "title": "Appointment of a panel of service providers for road construction and civil works",
                    "description": "Panel appointment for road and civil works",
                    "client": "City of Cape Town",
                    "source": "City of Cape Town",
                    "url": "https://example.com/stored",
                    "closing_date": "2099-05-01",
                    # Would be EXCLUDED by the current phrase rules.
                    "category": "PHAKATHI",
                },
                {
                    "ref": "SNAP-EXCLUDED",
                    "title": "Supply of cleaning material",
                    "description": "Cleaning material",
                    "client": "Eskom",
                    "source": "Eskom",
                    "url": "https://example.com/excluded",
                    "closing_date": "2099-05-01",
                    "category": "EXCLUDED",
                },
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("tools.build_dashboard_snapshot._load_planned_opportunities", lambda: [])

    payload = build_snapshot_from_inputs([str(input_path)], limit=200)
    refs = [item["ref"] for item in payload["tenders"]]

    assert refs == ["SNAP-STORED"]
    assert payload["tenders"][0]["category"] == "PHAKATHI"


def test_records_without_category_are_still_classified(tmp_path, monkeypatch):
    """Raw scrape inputs (no stored category) must keep being classified."""
    input_path = tmp_path / "scrape.json"
    input_path.write_text(
        json.dumps({
            "tenders": [
                {
                    "ref": "SNAP-NOCAT",
                    "title": "Cooling water treatment chemicals",
                    "description": "Condenser chemical dosing and treatment",
                    "client": "Eskom",
                    "source": "Eskom",
                    "url": "https://example.com/nocat",
                    "closing_date": "2099-05-01",
                }
            ]
        }),
        encoding="utf-8",
    )
    monkeypatch.setattr("tools.build_dashboard_snapshot._load_planned_opportunities", lambda: [])

    payload = build_snapshot_from_inputs([str(input_path)], limit=200)
    assert [item["ref"] for item in payload["tenders"]] == ["SNAP-NOCAT"]
    assert payload["tenders"][0]["category"] == "MEXEL"
