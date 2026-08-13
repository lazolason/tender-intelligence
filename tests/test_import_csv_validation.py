import csv
import sqlite3

import import_csv


def test_csv_import_rejects_invalid_rows_before_persistence(tmp_path, monkeypatch):
    csv_path = tmp_path / "tenders.csv"
    with csv_path.open("w", encoding="utf-8", newline="") as file_obj:
        writer = csv.DictWriter(
            file_obj,
            fieldnames=["ref", "title", "description", "client", "closing_date", "source"],
        )
        writer.writeheader()
        writer.writerow({
            "ref": "CSV-VALID",
            "title": "Cooling water treatment chemicals",
            "description": "Condenser chemical dosing and treatment",
            "client": "Eskom",
            "closing_date": "2099-05-01",
            "source": "Licensed Private Feed",
        })
        writer.writerow({
            "ref": "CSV-INVALID",
            "title": "",
            "description": "Missing title",
            "client": "Eskom",
            "closing_date": "2099-05-01",
            "source": "Licensed Private Feed",
        })

    db_path = tmp_path / "tenders.db"
    monkeypatch.setattr(import_csv, "DB_PATH", str(db_path))
    monkeypatch.setattr(import_csv, "ACTIVE_TENDERS_DIR", str(tmp_path / "folders"))
    monkeypatch.setattr(import_csv, "create_tender_folder", lambda **_kwargs: None)

    added, skipped, _results = import_csv.import_from_csv(str(csv_path))

    assert added == 1
    assert skipped == 1
    with sqlite3.connect(db_path) as conn:
        refs = [row[0] for row in conn.execute("SELECT ref FROM tenders")]
    assert refs == ["CSV-VALID"]
