import json
import sqlite3

from utils.db_writer import DatabaseWriter
from utils.procurement_plan_linker import link_planned_opportunities, score_plan_tender


SOURCE = "National Treasury Procurement Plans"


def _plan(external_id="TPP-LINK-1", **overrides):
    plan = {
        "external_id": external_id,
        "institution": "Eskom Holdings",
        "description": "Supply of cooling water treatment chemicals at Matla Power Station",
        "planned_advert_date": "2027-01-01",
        "planned_closing_date": "2027-02-01",
        "planned_award_date": "2027-03-01",
        "category": "MEXEL",
        "classification_reason": "test",
        "matched_keywords": ["cooling water", "chemical"],
        "lifecycle_stage": "PLANNED",
        "source": SOURCE,
        "source_url": "https://www.etenders.gov.za/Home/ProcurementPlans",
    }
    plan.update(overrides)
    return plan


def _insert_tender(db_path, ref="LIVE-001", **overrides):
    tender = {
        "ref": ref,
        "title": "Cooling water treatment chemicals at Matla Power Station",
        "description": "Supply cooling water treatment chemicals for Matla Power Station condensers",
        "client": "Eskom",
        "source": "National Treasury",
        "url": "https://example.com/tender",
        "closing_date": "2027-02-15",
        "category": "MEXEL",
        "status": "Open",
    }
    tender.update(overrides)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO tenders "
            "(ref, title, description, client, source, url, closing_date, category, status) "
            "VALUES (:ref, :title, :description, :client, :source, :url, "
            ":closing_date, :category, :status)",
            tender,
        )


def test_candidate_scoring_requires_category_institution_scope_and_date_guards():
    plan = _plan()
    tender = {
        "ref": "LIVE-001",
        "title": "Cooling water treatment chemicals at Matla Power Station",
        "description": "Chemical treatment for Matla condenser cooling water",
        "client": "Eskom",
        "category": "MEXEL",
        "closing_date": "2027-02-15",
    }

    candidate = score_plan_tender(plan, tender)
    assert candidate is not None
    assert candidate.score >= 0.86
    assert {"cooling", "water", "treatment", "chemicals", "matla"} <= set(candidate.overlap_tokens)

    assert score_plan_tender(plan, {**tender, "category": "PHAKATHI"}) is None
    assert score_plan_tender(plan, {**tender, "client": "Sasol"}) is None
    assert score_plan_tender(plan, {**tender, "title": "Office stationery", "description": "Paper and pens"}) is None
    assert score_plan_tender(plan, {**tender, "closing_date": "2026-12-01"}) is None


def test_linker_persists_high_confidence_match_and_audit(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    writer.reconcile_planned_opportunities([_plan()], source=SOURCE)
    _insert_tender(db_path)

    stats = link_planned_opportunities(str(db_path))

    assert stats["linked"] == 1
    with sqlite3.connect(db_path) as conn:
        plan_row = conn.execute(
            "SELECT matched_tender_ref, lifecycle_stage FROM planned_opportunities"
        ).fetchone()
        audit = conn.execute(
            "SELECT tender_ref, match_score, match_method, evidence "
            "FROM planned_opportunity_matches"
        ).fetchone()
    assert plan_row == ("LIVE-001", "MATCHED")
    assert audit[0] == "LIVE-001"
    assert audit[1] >= 0.86
    assert audit[2] == "conservative_lexical_v1"
    assert "scope_score" in json.loads(audit[3])

    # Source refresh must not move an already-linked plan back to PLANNED.
    refresh = writer.reconcile_planned_opportunities([_plan()], source=SOURCE)
    assert refresh["unchanged"] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT lifecycle_stage FROM planned_opportunities"
        ).fetchone()[0] == "MATCHED"

    assert link_planned_opportunities(str(db_path))["linked"] == 0


def test_linker_rejects_multiple_plans_competing_for_one_tender(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    plans = [
        _plan("TPP-LINK-1"),
        _plan(
            "TPP-LINK-2",
            description="Supply of cooling water treatment chemicals at Matla Power Station condensers",
        ),
    ]
    writer.reconcile_planned_opportunities(plans, source=SOURCE)
    _insert_tender(db_path)

    stats = link_planned_opportunities(str(db_path))

    assert stats["linked"] == 0
    assert stats["tender_conflicts"] == 2


def test_linker_rejects_ambiguous_live_tenders(tmp_path):
    db_path = tmp_path / "tenders.db"
    writer = DatabaseWriter(str(db_path))
    writer.reconcile_planned_opportunities([_plan()], source=SOURCE)
    _insert_tender(db_path, ref="LIVE-001")
    _insert_tender(db_path, ref="LIVE-002")

    stats = link_planned_opportunities(str(db_path))

    assert stats["linked"] == 0
    assert stats["ambiguous"] == 1
    with sqlite3.connect(db_path) as conn:
        assert conn.execute(
            "SELECT matched_tender_ref FROM planned_opportunities"
        ).fetchone()[0] is None
        assert conn.execute(
            "SELECT COUNT(*) FROM planned_opportunity_matches"
        ).fetchone()[0] == 0
