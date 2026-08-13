import sqlite3
from concurrent.futures import ThreadPoolExecutor

from utils.db_writer import DatabaseWriter


def _tender(**overrides):
    item = {
        "ref": "UP-001",
        "title": "Cooling water treatment chemicals",
        "description": "Chemical dosing for condenser cooling water",
        "client": "Eskom",
        "source": "Eskom",
        "url": "https://example.com/original",
        "closing_date": "2099-05-01",
    }
    item.update(overrides)
    return item


def _row(db_path):
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        return dict(conn.execute("SELECT * FROM tenders WHERE ref = 'UP-001'").fetchone())


def test_upsert_inserts_then_refreshes_changed_scraped_fields(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))

    action, original_scores, _ = writer.upsert_tender_with_scoring(_tender())
    assert action == "inserted"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tenders SET stage = 'Bid Preparation', status = 'Watching', "
            "next_action = 'Call client', notes = 'Analyst note', "
            "updated_at = '2000-01-01 00:00:00', last_seen_at = '2000-01-01 00:00:00' "
            "WHERE ref = 'UP-001'"
        )

    action, refreshed_scores, classification = writer.upsert_tender_with_scoring(
        _tender(
            ref=" up-001 ",
            title="Boiler water treatment and chemical dosing",
            description="Supply boiler treatment chemicals and dosing equipment",
            url="https://example.com/revised",
            closing_date="2099-06-15",
        )
    )

    assert action == "updated"
    assert original_scores
    assert refreshed_scores
    assert classification["category"] in {"MEXEL", "PHAKATHI"}
    row = _row(db_path)
    assert row["category"] == classification["category"]
    assert row["title"] == "Boiler water treatment and chemical dosing"
    assert row["url"] == "https://example.com/revised"
    assert row["closing_date"] == "2099-06-15"
    assert row["stage"] == "Bid Preparation"
    assert row["status"] == "Watching"
    assert row["next_action"] == "Call client"
    assert row["notes"] == "Analyst note"
    assert row["updated_at"] != "2000-01-01 00:00:00"
    assert row["last_seen_at"] != "2000-01-01 00:00:00"


def test_unchanged_upsert_only_refreshes_last_seen_and_does_not_duplicate_audit(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    assert writer.upsert_tender_with_scoring(_tender())[0] == "inserted"

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE tenders SET updated_at = '2000-01-01 00:00:00', "
            "last_seen_at = '2000-01-01 00:00:00' WHERE ref = 'UP-001'"
        )

    action, scores, classification = writer.upsert_tender_with_scoring(_tender())

    assert action == "unchanged"
    assert scores["priority"] in {"HIGH", "MEDIUM", "LOW"}
    assert classification["category"] == "MEXEL"
    row = _row(db_path)
    assert row["updated_at"] == "2000-01-01 00:00:00"
    assert row["last_seen_at"] != "2000-01-01 00:00:00"
    with sqlite3.connect(db_path) as conn:
        audit_count = conn.execute("SELECT COUNT(*) FROM classifications").fetchone()[0]
        tender_count = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
    assert audit_count == 1
    assert tender_count == 1


def test_concurrent_upserts_create_one_row(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))

    with ThreadPoolExecutor(max_workers=6) as pool:
        actions = list(pool.map(lambda _index: writer.upsert_tender_with_scoring(_tender())[0], range(12)))

    assert actions.count("inserted") == 1
    assert set(actions) <= {"inserted", "unchanged"}
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0] == 1


def test_compatibility_wrapper_returns_false_for_updates_but_still_refreshes(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    assert writer.add_tender_with_scoring(_tender())[0] is True

    was_added, scores, classification = writer.add_tender_with_scoring(
        _tender(url="https://example.com/changed")
    )

    assert was_added is False
    assert scores
    assert classification
    assert _row(db_path)["url"] == "https://example.com/changed"
