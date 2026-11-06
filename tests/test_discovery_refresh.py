import json
import pytest
from tools import refresh_portfolio_snapshot as module


class Source:
    source_name = 'National Treasury'
    def __init__(self, rows):
        self.rows = rows
    def run(self, **kwargs):
        return self.rows


def test_refresh_keeps_shared_refs_and_undated_review_candidates(tmp_path, monkeypatch):
    dashboard = tmp_path / 'dashboard'
    dashboard.mkdir()
    (dashboard / 'tenders.json').write_text(json.dumps({'meta': {}, 'tenders': []}))
    rows = [{'ref': 'RFQ-1', 'title': 'Cooling water chemical dosing', 'client': buyer, 'source': 'National Treasury', 'closing_date': '2099-01-01'} for buyer in ['A', 'B']]
    rows.append({'ref': 'UNDATED', 'title': 'Supply interactive panels', 'client': 'C', 'source': 'National Treasury'})
    monkeypatch.setattr(module, 'get_active_scrapers', lambda **kw: [Source(rows)])
    monkeypatch.setattr(module, 'load_config', lambda: {'paths': {'output_dir': str(tmp_path / 'output')}})
    module.refresh(tmp_path)
    payload = json.loads((dashboard / 'tenders.json').read_text())
    assert {row['client'] for row in payload['tenders']} == {'A', 'B'}
    assert any(row['ref'] == 'UNDATED' for row in payload['meta']['review_queue'])
    captured = json.loads((dashboard / 'public/discovery-index.json').read_text())
    assert captured['notice_count'] == 3


def test_primary_failure_retains_previous_snapshot(tmp_path, monkeypatch):
    dashboard = tmp_path / 'dashboard'
    dashboard.mkdir()
    path = dashboard / 'tenders.json'
    path.write_text('previous snapshot')
    class Failed:
        source_name = 'National Treasury'
        def run(self, **kwargs):
            raise RuntimeError('Source unavailable')
    monkeypatch.setattr(module, 'get_active_scrapers', lambda **kw: [Failed()])
    with pytest.raises(RuntimeError, match='previous snapshot retained'):
        module.refresh(tmp_path)
    assert path.read_text() == 'previous snapshot'
