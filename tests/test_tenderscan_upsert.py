import sqlite3

import tenderscan
from utils.db_writer import DatabaseWriter


def _tender(**overrides):
    item = {
        "ref": "SCAN-UP-001",
        "title": "Cooling water treatment chemicals",
        "description": "Chemical dosing for condenser cooling water",
        "client": "Eskom",
        "source": "Eskom",
        "url": "https://example.com/original",
        "closing_date": "2099-05-01",
        "category": "MEXEL",
    }
    item.update(overrides)
    return item


def test_process_tenders_classifies_before_persistence_and_output(tmp_path, monkeypatch):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    monkeypatch.setattr(tenderscan, "db_writer", writer)
    monkeypatch.setattr(tenderscan, "SEMANTIC_DEDUP_AVAILABLE", False)
    monkeypatch.setattr(tenderscan, "PDF_ANALYZER_AVAILABLE", False)
    monkeypatch.setattr(tenderscan, "create_tender_folder", lambda **_kwargs: str(tmp_path))

    relevant = _tender()
    relevant.pop("category")
    excluded = _tender(
        ref="SCAN-OUT-001",
        title="Supply of office chairs",
        description="General office furniture",
    )
    excluded.pop("category")

    added, new_items, stats = tenderscan.process_tenders(
        [relevant, excluded], return_stats=True
    )

    assert added == 1
    assert stats["inserted"] == 1
    assert stats["excluded"] == 1
    assert len(new_items) == 1
    assert new_items[0]["category"] == "MEXEL"
    assert new_items[0]["scores"]["priority"] == "HIGH"
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0] == 1
        assert conn.execute("SELECT category FROM tenders").fetchone()[0] == "MEXEL"


def test_process_tenders_refreshes_existing_exact_reference(tmp_path, monkeypatch):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    monkeypatch.setattr(tenderscan, "db_writer", writer)
    monkeypatch.setattr(tenderscan, "SEMANTIC_DEDUP_AVAILABLE", False)
    monkeypatch.setattr(tenderscan, "PDF_ANALYZER_AVAILABLE", False)
    monkeypatch.setattr(tenderscan, "create_tender_folder", lambda **_kwargs: str(tmp_path))

    added, new_items, first_stats = tenderscan.process_tenders(
        [_tender()], return_stats=True
    )
    assert added == 1
    assert len(new_items) == 1
    assert first_stats["inserted"] == 1

    added, new_items, refresh_stats = tenderscan.process_tenders(
        [_tender(url="https://example.com/revised", closing_date="2099-06-01")],
        return_stats=True,
    )

    assert added == 0
    assert new_items == []
    assert refresh_stats["updated"] == 1
    assert refresh_stats["unchanged"] == 0
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT url, closing_date FROM tenders WHERE ref = 'SCAN-UP-001'"
        ).fetchone()
    assert row == ("https://example.com/revised", "2099-06-01")
