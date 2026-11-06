import pytest
from utils.discovery import assess_discovery, discovery_index

# Historical and user-reviewed scopes; these are retrieval checks, not live adverts
# or evidence of eligibility. Actual recall against an independent feed is unmeasured.
RELEVANT = [
    ('MWP3022CX', 'Supply and delivery of 86-inch Interactive LED Touch Panels for Eskom RT&D'),
    ('OLT2105326', 'Dosing and Monitoring of Mexel 432 at Tutuka Power Station'),
    ('CHEM-1', 'ODACON corrosion inhibitor for boiler feedwater'),
    ('CHEM-2', 'Surface-active emulsion for industrial cooling circuits'),
    ('CHEM-3', 'Biocidal properties and surfactant treatment for cooling water'),
    ('CHEM-4', 'Film forming amines for condensate preservation'),
    ('CHEM-5', 'Amine treatment of steam circuit'),
    ('CHEM-6', 'Online chemical dosing and water quality monitoring'),
    ('INST-1', 'Supply conductivity analyser and pressure transmitters'),
    ('INST-2', 'Supply metering equipment and telemetry'),
    ('DISP-1', 'Supply interactive whiteboards'),
    ('DISP-2', 'Supply smartboards and video wall'),
    ('COOL-1', 'Biological fouling control in condenser circuit'),
    ('COOL-2', 'Supply dispersant for process water conditioning'),
    ('COOL-3', 'Legionella and microbiological control for cooling towers'),
    ('OPAQUE-1', 'Supply of process chemical consumables'),
]


@pytest.mark.parametrize('ref,title', RELEVANT)
def test_known_relevant_scope_is_not_lost_at_retrieval(ref, title):
    result = assess_discovery({'ref': ref, 'title': title})
    assert result['tier'] in {'strong_candidate', 'possible_candidate'}


def test_attachment_name_preserves_opaque_procurement_for_review():
    row = {'title': 'Supply and delivery of equipment', 'attachments': [{'name': 'Condensate treatment Scope.pdf'}]}
    assert assess_discovery(row)['tier'] == 'possible_candidate'


def test_unknown_scope_is_searchable_not_declared_irrelevant():
    rows = [{'ref': 'UNKNOWN', 'title': 'Lot 7 procurement', 'source': 'Test'}]
    index = discovery_index(rows)
    assert index['notice_count'] == 1
    assert index['notices'][0]['discovery']['tier'] == 'unassessed'


def test_clear_works_stay_searchable_without_shortlisting():
    row = {'ref': 'MECH', 'title': 'Duvha cooling water treatment plant refurbishment'}
    index = discovery_index([row])
    assert index['notices'][0]['discovery']['tier'] == 'clearly_excluded'


def test_references_shared_by_buyers_are_not_dropped():
    index = discovery_index([{'ref': 'RFQ-1', 'client': buyer, 'source': 'eTenders', 'title': 'Supply monitor'} for buyer in ['Buyer A', 'Buyer B']])
    assert index['notice_count'] == 2


def test_process_supply_lot_in_broader_works_stays_in_review():
    row = {'title': 'Supply of chemical dosing equipment for plant refurbishment'}
    assert assess_discovery(row)['tier'] == 'possible_candidate'


def test_source_failure_preserves_previously_captured_notices(tmp_path):
    from utils.discovery import write_discovery_index
    path = tmp_path / 'index.json'
    old = {'ref': 'WATER-1', 'title': 'Dosing equipment', 'source': 'Board', 'client': 'Buyer', 'capture_group': 'Water Boards'}
    write_discovery_index([old], path)
    result = write_discovery_index([], path, [{'source': 'Water Boards', 'status': 'failed'}])
    assert result['notices'][0]['capture_state'] == 'stale_source_failure'
    # A complete successful response is allowed to replace a stale listing.
    result = write_discovery_index([], path, [{'source': 'Water Boards', 'status': 'success'}])
    assert result['notices'] == []


def test_obviously_unrelated_chemical_scope_does_not_fill_review_queue():
    row = {'title': 'Hiring and servicing of mobile chemical toilets'}
    assert assess_discovery(row)['tier'] == 'clearly_excluded'
    assert discovery_index([row])['notice_count'] == 1
