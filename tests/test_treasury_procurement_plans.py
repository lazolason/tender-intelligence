from datetime import date
from pathlib import Path
import sqlite3

import pytest

import sync_procurement_plans
from scrapers.treasury_procurement_plans import parse_procurement_plans_html
from sync_dashboard import load_planned_opportunities
from utils.db_writer import DatabaseWriter


def _fixture_html():
    return (Path(__file__).parent / "fixtures" / "treasury_procurement_plans.html").read_text(
        encoding="utf-8"
    )


def test_procurement_plan_fixture_is_normalized_and_classified():
    plans = parse_procurement_plans_html(_fixture_html(), today=date(2026, 4, 15))

    assert len(plans) == 3
    mexel = plans[0]
    assert mexel["external_id"].startswith("TPP-")
    assert mexel["category"] == "MEXEL"
    assert mexel["planned_advert_date"] == "2026-07-01"
    assert mexel["planned_closing_date"] == "2026-08-01"
    assert mexel["lifecycle_stage"] == "DUE_SOON"
    assert plans[1]["category"] == "EXCLUDED"
    assert plans[2]["category"] == "PHAKATHI"
    assert plans[2]["planned_advert_date"] is None


def test_planned_opportunity_upsert_refreshes_without_duplicates(tmp_path, monkeypatch):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    relevant = [
        plan
        for plan in parse_procurement_plans_html(_fixture_html(), today=date(2026, 4, 15))
        if plan["category"] in {"MEXEL", "PHAKATHI"}
    ]

    assert writer.upsert_planned_opportunities(relevant) == 2
    relevant[0]["description"] = "Updated cooling water treatment scope"
    assert writer.upsert_planned_opportunities(relevant) == 2

    monkeypatch.setattr("sync_dashboard.DB_PATH", str(db_path))
    loaded = load_planned_opportunities()

    assert len(loaded) == 2
    assert loaded[0]["description"] == "Updated cooling water treatment scope"
    assert loaded[0]["company"] == "Mexel"
    assert isinstance(loaded[0]["matched_keywords"], list)


def test_parser_maps_columns_by_header_instead_of_position():
    html = """
    <table id="DataTable">
      <thead><tr>
        <th>Envisaged award date</th><th>Department</th>
        <th>Envisaged closing date</th><th>Description of goods, services and works</th>
        <th>Envisaged advert date</th>
      </tr></thead>
      <tbody><tr>
        <td>2027/03/01 00:00:00</td><td>Eskom</td>
        <td>2027/02/01 00:00:00</td><td>Cooling water treatment chemicals</td>
        <td>2027/01/01 00:00:00</td>
      </tr></tbody>
    </table>
    """

    plans = parse_procurement_plans_html(html, today=date(2026, 4, 15))

    assert plans[0]["institution"] == "Eskom"
    assert plans[0]["description"] == "Cooling water treatment chemicals"
    assert plans[0]["planned_advert_date"] == "2027-01-01"
    assert plans[0]["planned_award_date"] == "2027-03-01"


def test_parser_fails_closed_when_required_column_is_missing():
    html = """
    <table><thead><tr><th>Department</th><th>Description</th></tr></thead>
    <tbody><tr><td>Eskom</td><td>Cooling water treatment</td></tr></tbody></table>
    """
    with pytest.raises(ValueError, match="missing columns"):
        parse_procurement_plans_html(html)


def test_complete_snapshot_retires_and_reactivates_plans(tmp_path, monkeypatch):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    source = "National Treasury Procurement Plans"
    plans = [
        plan
        for plan in parse_procurement_plans_html(_fixture_html(), today=date(2026, 4, 15))
        if plan["category"] in {"MEXEL", "PHAKATHI"}
    ]

    first = writer.reconcile_planned_opportunities(plans, source=source)
    assert first["inserted"] == 2
    second = writer.reconcile_planned_opportunities(plans[:1], source=source)
    assert second["unchanged"] == 1
    assert second["retired"] == 1

    monkeypatch.setattr("sync_dashboard.DB_PATH", str(db_path))
    assert len(load_planned_opportunities()) == 1
    with sqlite3.connect(db_path) as conn:
        retired = conn.execute(
            "SELECT is_active, lifecycle_stage, retired_at FROM planned_opportunities "
            "WHERE external_id = ?",
            (plans[1]["external_id"],),
        ).fetchone()
    assert retired[0] == 0
    assert retired[1] == "RETIRED"
    assert retired[2]

    third = writer.reconcile_planned_opportunities(plans, source=source)
    assert third["reactivated"] == 1
    assert third["retired"] == 0
    assert len(load_planned_opportunities()) == 2


def test_sync_refuses_truncated_snapshot_before_database_reconciliation(tmp_path, monkeypatch):
    monkeypatch.setattr(
        sync_procurement_plans,
        "load_and_validate_config",
        lambda: {
            "procurement_plans": {
                "enabled": True,
                "relevant_only": True,
                "minimum_snapshot_rows": 100,
            }
        },
    )
    monkeypatch.setattr(
        sync_procurement_plans,
        "scrape_treasury_procurement_plans",
        lambda **_kwargs: parse_procurement_plans_html(_fixture_html()),
    )
    monkeypatch.setenv("DB_PATH", str(tmp_path / "must-not-be-created.db"))

    with pytest.raises(ValueError, match="expected at least 100"):
        sync_procurement_plans.sync_procurement_plans()

    assert not (tmp_path / "must-not-be-created.db").exists()
