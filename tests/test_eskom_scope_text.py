from scrapers.eskom_direct import _scrape_eskom_tenders_api


def test_eskom_preserves_scope_after_old_truncation_limits(monkeypatch):
    title = 'General equipment supply ' + ('x ' * 70) + 'online monitoring'
    scope = ('General specification. ' * 40) + 'Cooling water chemical dosing and monitoring'
    class Response:
        def raise_for_status(self):
            pass
        def json(self):
            return [{'PUBLISH': 'Y', 'TENDER_ID': 123, 'REFERENCE': 'SCOPE-123', 'HEADER_DESC': title, 'SCOPE_DETAILS': scope}]
    monkeypatch.setattr('scrapers.eskom_direct.guarded_request', lambda *a, **kw: Response())
    record = _scrape_eskom_tenders_api(100)[0]
    assert record['title'] == title
    assert record['description'] == scope
    assert record['category'] == 'MEXEL'


def test_eskom_default_does_not_stop_at_fifty_records(monkeypatch):
    from scrapers.eskom_direct import scrape_eskom_tenders
    records = [{'ref': str(i)} for i in range(75)]
    monkeypatch.setattr('scrapers.eskom_direct._scrape_eskom_tenders_api', lambda max_tenders, timeout: records[:max_tenders])
    assert len(scrape_eskom_tenders()) == 75
