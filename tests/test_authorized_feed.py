import json
import sqlite3

import pytest

from utils.authorized_feed import AuthorizedFeedError, ingest_authorized_feed
from utils.config_validator import validate_config


def _config(inbox, *, enabled=True, sources=None, max_bytes=100_000):
    return {
        "authorized_feeds": {
            "enabled": enabled,
            "inbox_dir": str(inbox),
            "max_file_bytes": max_bytes,
            "max_records": 100,
            "sources": sources if sources is not None else [
                {
                    "id": "licensed_vendor",
                    "label": "Licensed Vendor Export",
                    "enabled": True,
                    "format": "json",
                    "kind": "live_tenders",
                }
            ],
        }
    }


def _records():
    return [
        {
            "ref": "VENDOR-001",
            "title": "Cooling water treatment chemicals",
            "description": "Chemical dosing for cooling tower and condenser water",
            "client": "Eskom",
            "source": "Spoofed Source",
            "closing_date": "2099-05-01",
            "url": "https://vendor.example/tenders/1",
        },
        {
            "ref": "VENDOR-BAD",
            "title": "",
            "description": "Missing title",
            "client": "Eskom",
            "closing_date": "2099-05-01",
        },
        {
            "ref": "VENDOR-EXCLUDED",
            "title": "Supply of office stationery",
            "description": "Pens, paper and filing cabinets",
            "client": "Eskom",
            "closing_date": "2099-05-01",
        },
    ]


def test_authorized_feed_dry_run_then_import_is_validated_audited_and_idempotent(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    feed_path = inbox / "export.json"
    feed_path.write_text(json.dumps({"records": _records()}), encoding="utf-8")
    db_path = tmp_path / "tenders.db"
    config = _config(inbox)

    dry_run = ingest_authorized_feed(
        config=config,
        source_id="licensed_vendor",
        file_path="export.json",
        db_path=str(db_path),
        dry_run=True,
    )
    assert dry_run["status"] == "SUCCESS"
    assert dry_run["total"] == 3
    assert dry_run["valid"] == 2
    assert dry_run["invalid"] == 1
    assert dry_run["excluded"] == 1
    assert dry_run["ready"] == 1
    assert dry_run["inserted"] == 0

    imported = ingest_authorized_feed(
        config=config,
        source_id="licensed_vendor",
        file_path=str(feed_path),
        db_path=str(db_path),
    )
    assert imported["status"] == "SUCCESS"
    assert imported["inserted"] == 1
    assert imported["updated"] == 0

    duplicate = ingest_authorized_feed(
        config=config,
        source_id="licensed_vendor",
        file_path="export.json",
        db_path=str(db_path),
    )
    assert duplicate["status"] == "duplicate"

    with sqlite3.connect(db_path) as conn:
        tender = conn.execute(
            "SELECT ref, source, title FROM tenders"
        ).fetchone()
        runs = conn.execute(
            "SELECT dry_run, status, records_total, records_valid, records_invalid, "
            "records_excluded, records_inserted, error_type "
            "FROM authorized_feed_runs ORDER BY dry_run DESC"
        ).fetchall()
    assert tender == (
        "AF-LICENSED-VENDOR-VENDOR-001",
        "Authorized Feed: Licensed Vendor Export",
        "Cooling water treatment chemicals",
    )
    assert len(runs) == 2
    assert all(row[1] == "SUCCESS" for row in runs)
    assert all(row[7] is None for row in runs)


def test_authorized_feed_rejects_disabled_unknown_and_unconfined_sources(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "export.json").write_text("[]", encoding="utf-8")
    outside = tmp_path / "outside.json"
    outside.write_text("[]", encoding="utf-8")
    db_path = tmp_path / "tenders.db"

    with pytest.raises(AuthorizedFeedError, match="disabled"):
        ingest_authorized_feed(
            config=_config(inbox, enabled=False),
            source_id="licensed_vendor",
            file_path="export.json",
            db_path=str(db_path),
        )
    with pytest.raises(AuthorizedFeedError, match="not explicitly enabled"):
        ingest_authorized_feed(
            config=_config(inbox),
            source_id="unknown_vendor",
            file_path="export.json",
            db_path=str(db_path),
        )
    with pytest.raises(AuthorizedFeedError, match="inside the configured inbox"):
        ingest_authorized_feed(
            config=_config(inbox),
            source_id="licensed_vendor",
            file_path=str(outside),
            db_path=str(db_path),
        )
    assert not db_path.exists()


def test_authorized_feed_rejects_symlinks_oversized_files_and_wrong_extension(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    target = inbox / "target.json"
    target.write_text("[]", encoding="utf-8")
    link = inbox / "link.json"
    link.symlink_to(target)
    wrong = inbox / "feed.csv"
    wrong.write_text("ref,title\n1,test", encoding="utf-8")
    db_path = tmp_path / "tenders.db"

    with pytest.raises(AuthorizedFeedError, match="Symbolic-link"):
        ingest_authorized_feed(
            config=_config(inbox), source_id="licensed_vendor",
            file_path="link.json", db_path=str(db_path),
        )
    with pytest.raises(AuthorizedFeedError, match="extension"):
        ingest_authorized_feed(
            config=_config(inbox), source_id="licensed_vendor",
            file_path="feed.csv", db_path=str(db_path),
        )
    with pytest.raises(AuthorizedFeedError, match="byte limit"):
        ingest_authorized_feed(
            config=_config(inbox, max_bytes=1), source_id="licensed_vendor",
            file_path="target.json", db_path=str(db_path),
        )


def test_authorized_csv_field_mapping(tmp_path):
    inbox = tmp_path / "inbox"
    inbox.mkdir()
    (inbox / "vendor.csv").write_text(
        "opportunity_id,subject,scope,buyer,deadline,link\n"
        "ABC-9,Cooling tower chemical treatment,Chemical dosing for condenser water,Eskom,2099-06-01,https://vendor.example/9\n",
        encoding="utf-8",
    )
    source = {
        "id": "csv_vendor",
        "label": "Approved CSV Vendor",
        "enabled": True,
        "format": "csv",
        "kind": "live_tenders",
        "field_map": {
            "ref": "opportunity_id", "title": "subject", "description": "scope",
            "client": "buyer", "closing_date": "deadline", "url": "link",
        },
    }
    db_path = tmp_path / "tenders.db"

    result = ingest_authorized_feed(
        config=_config(inbox, sources=[source]),
        source_id="csv_vendor",
        file_path="vendor.csv",
        db_path=str(db_path),
    )

    assert result["inserted"] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT ref FROM tenders").fetchone()[0] == "AF-CSV-VENDOR-ABC-9"


def test_authorized_feed_configuration_validation_rejects_unsafe_definitions():
    base = {
        "paths": {"active_tenders": "x", "output_dir": "x", "log_file": "x"},
        "scrapers": {"enable_selenium": False, "timeout": 10},
        "classification": {},
        "scoring": {"fit_weight": 0.6, "industry_weight": 0.4},
    }
    config = {
        **base,
        "authorized_feeds": {
            "enabled": True,
            "max_file_bytes": -1,
            "max_records": 0,
            "sources": [
                {"id": "same", "label": "", "format": "xml", "kind": "planned"},
                {"id": "same", "label": "Duplicate", "format": "json"},
            ],
        },
    }

    valid, errors = validate_config(config)

    assert valid is False
    assert any("max_file_bytes" in error for error in errors)
    assert any("max_records" in error for error in errors)
    assert any("Duplicate" in error for error in errors)
    assert any("format" in error for error in errors)
    assert any("kind" in error for error in errors)
    assert any("label" in error for error in errors)
