"""Snapshot freshness: meta.last_sync must track the run, not the content.

The no-new-tenders branch used to leave the JSON untouched, so the dashboard
kept reporting the last day something new was found even while the daily job
ran every morning.
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tenderscan


def _prepare(tmp_path, monkeypatch, tenders):
    monkeypatch.setattr(tenderscan, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(tenderscan, "LOG_FILE", str(tmp_path / "scan.log"))
    snapshot = tmp_path / "new_tenders.json"
    snapshot.write_text(json.dumps({
        "meta": {"last_sync": "2020-01-01 08:00", "next_run": "Daily 08:00"},
        "tenders": tenders,
    }))
    return snapshot


def test_empty_run_still_refreshes_last_sync(tmp_path, monkeypatch):
    existing = [{"ref": "REF-1", "title": "Old tender", "category": "MEXEL"}]
    snapshot = _prepare(tmp_path, monkeypatch, existing)

    tenderscan.save_outputs([])

    payload = json.loads(snapshot.read_text())
    assert payload["meta"]["last_sync"] != "2020-01-01 08:00"
    assert payload["meta"]["new_count"] == 0
    assert payload["meta"]["total"] == 1
    # Content is preserved rather than emptied.
    assert [t["ref"] for t in payload["tenders"]] == ["REF-1"]


def test_new_items_are_merged_and_counted(tmp_path, monkeypatch):
    existing = [{"ref": "REF-1", "title": "Old tender", "category": "MEXEL"}]
    snapshot = _prepare(tmp_path, monkeypatch, existing)

    tenderscan.save_outputs([{"ref": "REF-2", "title": "New tender", "category": "MEXEL"}])

    payload = json.loads(snapshot.read_text())
    assert payload["meta"]["new_count"] == 1
    assert {t["ref"] for t in payload["tenders"]} == {"REF-1", "REF-2"}


def test_no_history_initialises_empty_payload(tmp_path, monkeypatch):
    monkeypatch.setattr(tenderscan, "OUTPUT_DIR", str(tmp_path))
    monkeypatch.setattr(tenderscan, "LOG_FILE", str(tmp_path / "scan.log"))

    tenderscan.save_outputs([])

    payload = json.loads((tmp_path / "new_tenders.json").read_text())
    assert payload["tenders"] == []
    assert payload["meta"]["new_count"] == 0
