from utils.opportunity_review import prepare_opportunities, document_text
from classify_engine import classify_tender
import pytest


def test_attachment_scope_can_rescue_ambiguous_listing():
    tender = {'ref': 'DOC-1', 'title': 'Online monitoring equipment', 'description': 'See specification', 'attachments': [{'name': 'Scope.pdf', 'url': 'https://www.etenders.gov.za/scope.pdf'}]}
    rows, queue = prepare_opportunities([tender], fetch_text=lambda url: 'Cooling water chemical dosing and monitoring')
    assert classify_tender(rows[0]['title'], rows[0]['description'])['portfolios'] == ['MEXEL', 'PHAKATHI']
    assert queue[0]['documents_checked'][0]['characters'] > 0
    assert rows[0]['review_status'] == 'needs_review'


def test_failed_or_budgeted_documents_are_not_silent_rejections():
    tender = {'ref': 'DOC-2', 'title': 'Boiler equipment', 'attachments': [{'name': 'Scope.zip', 'url': 'https://www.etenders.gov.za/scope.zip'}]}
    _, queue = prepare_opportunities([tender], document_budget=0)
    assert 'budget' in queue[0]['limitations'][0]


def test_works_and_notices_do_not_download_annexures():
    def fail(url):
        raise AssertionError('Should not fetch excluded works')
    rows, queue = prepare_opportunities([{'title': 'Boiler refurbishment', 'attachments': [{'name': 'ODACON.pdf', 'url': 'https://www.etenders.gov.za/a.pdf'}]}], fetch_text=fail)
    assert not queue
    assert classify_tender(rows[0]['title'], '')['category'] == 'EXCLUDED'


def test_document_fetch_refuses_unapproved_host_before_network():
    with pytest.raises(ValueError, match='approved official'):
        document_text('https://127.0.0.1/internal.pdf')


def test_download_size_limit_is_enforced_and_response_closed(monkeypatch):
    class Response:
        is_redirect = False
        closed = False
        def raise_for_status(self):
            pass
        def iter_content(self, size):
            yield b'%PDF' + b'x' * 30
        def close(self):
            self.closed = True
    response = Response()
    monkeypatch.setattr('utils.opportunity_review.guarded_request', lambda *a, **kw: response)
    with pytest.raises(ValueError, match='size limit'):
        document_text('https://www.etenders.gov.za/doc.pdf', max_bytes=10)
    assert response.closed
