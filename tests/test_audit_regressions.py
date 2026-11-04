"""Offline regressions for the November audit; no live scan or notifications."""
import json
import sqlite3
import sys
from pathlib import Path
from types import ModuleType, SimpleNamespace

import pytest
import requests
from requests.adapters import BaseAdapter

from classify_engine import classify_tender, keyword_present, clean
from scoring_engine import calculate_suitability_scores


@pytest.mark.parametrize('target', ['https://127.0.0.1/private', 'http://example.com/plain', 'https://localhost/admin'])
def test_redirect_is_rejected_before_destination_is_requested(monkeypatch, target):
    from utils.retry_tools import _requests_get_with_retry
    visited = []

    class Adapter(BaseAdapter):
        def send(self, request, **kwargs):
            visited.append(request.url)
            response = requests.Response()
            response.url = request.url
            response.request = request
            response._content = b''
            response._content_consumed = True
            response.status_code = 302 if len(visited) == 1 else 200
            if len(visited) == 1:
                response.headers['Location'] = target
            return response

        def close(self):
            pass

    session = requests.Session()
    session.trust_env = False
    session.mount('https://', Adapter())
    session.mount('http://', Adapter())
    monkeypatch.setattr('utils.retry_tools.requests.get', session.get)
    with pytest.raises(ValueError):
        _requests_get_with_retry('https://example.com/start')
    assert visited == ['https://example.com/start']


def test_public_redirect_preserves_options_and_strips_cross_host_credentials(monkeypatch):
    from utils.retry_tools import _requests_get_with_retry
    calls = []
    closed = []

    def get(url, **kwargs):
        calls.append((url, kwargs))
        redirect = len(calls) == 1
        return SimpleNamespace(
            url=url, status_code=302 if redirect else 200,
            headers={'Location': 'https://other.example/final'} if redirect else {},
            close=lambda: closed.append(url),
        )

    monkeypatch.setattr('utils.retry_tools.requests.get', get)
    result = _requests_get_with_retry(
        'https://example.com/start', params={'q': 'tenders'}, timeout=7,
        headers={'Authorization': 'test-only', 'User-Agent': 'audit'}, auth=('test', 'test'),
    )
    assert result.url == 'https://other.example/final'
    assert len(calls) == 2
    assert calls[0][1]['allow_redirects'] is False
    assert calls[1][1]['timeout'] == 7
    assert calls[1][1]['verify'] is True
    assert 'params' not in calls[1][1] and 'auth' not in calls[1][1]
    assert calls[1][1]['headers'] == {'User-Agent': 'audit'}
    assert closed == ['https://example.com/start']


def test_backup_uses_configured_database(tmp_path, monkeypatch):
    from utils.backup_database import backup_database
    db = tmp_path / 'configured.db'
    with sqlite3.connect(db) as conn:
        conn.execute('create table audit_record (value text)')
        conn.execute("insert into audit_record values ('configured source')")
    monkeypatch.setenv('DB_PATH', str(db))
    destination = tmp_path / 'backups'
    assert backup_database(backup_dir=destination) is True
    backups = list(destination.glob('*.db'))
    assert len(backups) == 1
    with sqlite3.connect(backups[0]) as conn:
        assert conn.execute('select value from audit_record').fetchone()[0] == 'configured source'


def test_backup_missing_source_does_not_create_database(tmp_path):
    from utils.backup_database import backup_database
    source = tmp_path / 'missing.db'
    assert backup_database(db_path=source, backup_dir=tmp_path / 'backup') is False
    assert not source.exists()


@pytest.mark.parametrize('failed_step', ['scan', 'sync'])
def test_failed_daily_scan_api_is_not_success(monkeypatch, failed_step):
    import app
    module = ModuleType('daily_runner')
    result = {'scan': {'status': 'success'}, 'sync': {'status': 'success'}}
    result[failed_step] = {'status': 'error', 'message': 'offline test failure'}
    module.run_daily = lambda: result
    monkeypatch.setitem(sys.modules, 'daily_runner', module)
    monkeypatch.setattr(app, 'API_KEY', 'audit-test-only')
    app.RATE_LIMIT_STATE.clear()
    response = app.app.test_client().post('/api/run/daily', headers={'X-API-Key': 'audit-test-only'})
    assert response.status_code == 500
    assert response.json['status'] == 'error'


def test_daily_status_is_replaced_atomically(tmp_path):
    import daily_runner
    path = tmp_path / 'status.json'
    old = {'status': 'success'}
    path.write_text(json.dumps(old))
    with pytest.raises(TypeError):
        daily_runner.persist_run_results({'bad': object()}, str(path))
    assert json.loads(path.read_text()) == old
    assert list(tmp_path.iterdir()) == [path]


@pytest.mark.parametrize('eligible,delivered,expected', [(True, False, 'failed'), (False, False, 'no_alerts_needed'), (True, True, 'sent')])
def test_digest_reports_delivery_result(monkeypatch, eligible, delivered, expected):
    import utils.email_alerts as email
    monkeypatch.setattr(email, 'load_tender_payload', lambda: {'tenders': [{'title': 'test', 'scores': {'priority': 'HIGH'}}] if eligible else []})
    monkeypatch.setattr(email, 'config_status', lambda: {'configured': True, 'missing': []})
    monkeypatch.setattr(email, 'generate_email_html', lambda *args, **kwargs: '<p>offline test</p>')
    sends = []
    monkeypatch.setattr(email, 'send_email', lambda *args: sends.append(args) or delivered)
    assert email.send_daily_digest(return_status=True)['status'] == expected
    assert len(sends) == int(eligible)


@pytest.mark.parametrize('title,category', [
    ('Film-forming amine treatment for steam circuits', 'PHAKATHI'),
    ('Boiler lay-up preservation', 'PHAKATHI'),
    ('REICON ODACON boiler chemistry', 'PHAKATHI'),
    ('Huawei industrial networking', 'PHAKATHI'),
    ('Mexel 432 delivery with film-forming amine treatment', 'MEXEL'),
    ('Cooling tower water treatment and condenser efficiency', 'MEXEL'),
    ('Tender cancellation - ODACON boiler water treatment', 'EXCLUDED'),
    ('Notification of Awarded Camden Power Station', 'EXCLUDED'),
    ('Refurbishment of metal seated butterfly valve on main condenser isolation valves', 'EXCLUDED'),
    ('Regret letter - Mexel 432 supply', 'EXCLUDED'),
])
def test_company_keyword_boundaries(title, category):
    assert classify_tender(title, '')['category'] == category


def test_piso_scope_is_not_scored_as_mexel_product_fit():
    result = calculate_suitability_scores('REICON ODACON boiler chemistry', 'Steam circuit preservation', 'PHAKATHI')
    assert result['mexel_suitability'] == 0
    assert result['phakathi_suitability'] > 0


def test_keyword_punctuation_is_normalized_consistently():
    assert keyword_present(clean('Flow-accelerated corrosion and boiler lay-up'), 'flow-accelerated corrosion')
    assert keyword_present(clean('M&V protocol'), 'm&v protocol')
    assert not keyword_present(clean('ODACONSTRUCTION'), 'odacon')


def test_primary_registry_has_no_duplicate_soe_group():
    from scrapers.registry import SCRAPER_REGISTRY
    names = [s.name for s in SCRAPER_REGISTRY]
    assert names[0] == 'National Treasury'
    assert 'Municipalities' in names
    assert 'SOEs' not in names
    assert names.count('Eskom Tender Bulletin') == 1


def test_checked_in_dashboard_snapshot_contains_only_current_scope_matches():
    import json
    from pathlib import Path

    payload = json.loads(Path('dashboard/tenders.json').read_text())
    public_payload = json.loads(Path('dashboard/public/tenders-latest.json').read_text())
    assert public_payload == payload
    assert all(row.get('category') in {'MEXEL', 'PHAKATHI'} for row in payload['tenders'])
    assert payload['meta']['scope_refresh']['records_removed_as_out_of_scope'] == 32


def test_municipality_failure_reaches_pipeline(monkeypatch):
    from scrapers.registry import get_active_scrapers
    monkeypatch.setattr('scrapers.municipalities.CapeTownScraper.fetch_page', lambda self: (_ for _ in ()).throw(RuntimeError('offline source outage')))
    source = next(s for s in get_active_scrapers(enable_selenium=False) if s.source_name == 'Municipalities')
    with pytest.raises(RuntimeError, match='offline source outage'):
        source.run(raise_on_error=True)
    assert source.last_error


def test_water_board_partial_results_survive_failure(monkeypatch):
    from scrapers import water_boards
    record = {'ref': 'VALID-1', 'title': 'Water treatment'}
    monkeypatch.setattr(water_boards, 'scrape_umgeni_water', lambda **kwargs: [record])
    monkeypatch.setattr(water_boards, 'scrape_magalies_water', lambda **kwargs: (_ for _ in ()).throw(RuntimeError('offline failed source')))
    monkeypatch.setattr(water_boards, 'scrape_lepelle_water', lambda **kwargs: [])
    with pytest.raises(RuntimeError) as error:
        water_boards.scrape_all_water_boards(raise_on_error=True)
    assert error.value.tenders == [record]
    assert list(error.value.failures) == ['Magalies Water']


def test_snapshot_refuses_to_replace_primary_feed_with_supplement(monkeypatch):
    from tools import build_dashboard_snapshot as builder
    def fail(**kwargs):
        raise RuntimeError('primary unavailable')
    monkeypatch.setattr(builder, 'get_active_scrapers', lambda **kwargs: [SimpleNamespace(source_name='National Treasury', run=fail)])
    with pytest.raises(RuntimeError, match='Primary eTenders feed failed'):
        builder.build_snapshot(limit=200)


def test_cli_writes_partial_artifact_and_failure_exit(tmp_path, monkeypatch):
    from scrapers.base import PartialScrapeError
    from tools import scrape_source
    record = {'ref': 'VALID-2', 'title': 'Valid partial record'}
    monkeypatch.setattr(scrape_source, 'load_config', lambda: {})
    monkeypatch.setattr(scrape_source, 'run_scraper', lambda *args, **kwargs: (_ for _ in ()).throw(PartialScrapeError([record], {'test source': 'offline failure'})))
    output = tmp_path / 'source.json'
    monkeypatch.setattr(sys, 'argv', ['scrape_source.py', '--scraper', 'water_boards', '--out', str(output)])
    assert scrape_source.main() == 1
    payload = json.loads(output.read_text())
    assert payload['status'] == 'partial'
    assert payload['tenders'][0]['ref'] == 'VALID-2'
    assert payload['failed_sources'] == {'test source': 'offline failure'}


def test_partial_group_keeps_records_and_failure_health(tmp_path, monkeypatch):
    from contextlib import contextmanager
    from scrapers.base import FunctionScraper, PartialScrapeError
    import tenderscan
    record = {'ref': 'PARTIAL-1', 'title': 'Cooling water treatment'}
    def fail_partially():
        raise PartialScrapeError([record], {'one source': 'offline outage'})
    observed = {}
    class Monitor:
        @contextmanager
        def track(self, name):
            context = SimpleNamespace(tenders_found=0)
            try:
                yield context
            except Exception:
                observed['status'] = 'failure'
                raise
            finally:
                observed['count'] = context.tenders_found
    monkeypatch.setattr(tenderscan, 'get_active_scrapers', lambda **kwargs: [FunctionScraper('Test group', fail_partially)])
    monkeypatch.setattr(tenderscan, 'SEMANTIC_DEDUP_AVAILABLE', False)
    monkeypatch.setattr(tenderscan, 'LOG_FILE', str(tmp_path / 'test.log'))
    assert tenderscan.run_all_scrapers(monitor=Monitor(), max_workers=1) == [record]
    assert observed == {'status': 'failure', 'count': 1}


def test_procurement_plan_profile_uses_same_chemistry_keywords():
    from scrapers.treasury_procurement_plans import is_relevant_plan
    assert is_relevant_plan({'institution': 'Test plant', 'description': 'Film-forming amine treatment', 'category': 'PHAKATHI'})
