"""Reference identity: the same tender must not be stored twice.

eTenders lists the City of Cape Town tender "92S/2026/27"; the City's own portal
lists it as "092S/2026/27". Dedupe compared raw refs, so both would be inserted.
"""
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import tenderscan
from utils.db_writer import DatabaseWriter
from utils.text_utils import normalize_ref


def test_zero_padding_is_stripped_from_leading_number():
    assert normalize_ref("092S/2026/27") == "92S/2026/27"
    assert normalize_ref("92S/2026/27") == "92S/2026/27"
    assert normalize_ref("  092s/2026/27 ") == "92S/2026/27"


def test_refs_with_letter_prefix_are_untouched():
    # Only a leading numeric run is normalised, so identifiers stay intact.
    assert normalize_ref("CTICC 009/2027") == "CTICC 009/2027"
    assert normalize_ref("LNW04/26/27") == "LNW04/26/27"
    assert normalize_ref("") == ""


def test_tender_identity_collapses_padding_variants():
    a = {"ref": "092S/2026/27", "title": "Supply of cooling water treatment chemicals"}
    b = {"ref": "92S/2026/27", "title": "Supply of cooling water treatment chemicals"}
    assert tenderscan._tender_identity(a) == tenderscan._tender_identity(b)


def test_database_upsert_treats_padding_variants_as_one_tender(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))

    base = {
        "title": "Supply and delivery of cooling water treatment chemicals",
        "description": "Chemical dosing for condenser cooling water treatment",
        "client": "City of Cape Town",
        "source": "City of Cape Town",
        "closing_date": "2099-01-01",
    }

    first, _, _ = writer.upsert_tender_with_scoring({**base, "ref": "092S/2026/27"})
    second, _, _ = writer.upsert_tender_with_scoring({**base, "ref": "92S/2026/27"})

    assert first == "inserted"
    assert second in ("updated", "unchanged")

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM tenders").fetchone()[0]
        ref = conn.execute("SELECT ref FROM tenders").fetchone()[0]
    assert count == 1
    assert ref == "92S/2026/27"
