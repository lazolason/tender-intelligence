"""Refresh public-source snapshot and review evidence without database writes or sends."""
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone, date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from scrapers.registry import get_active_scrapers
from scrapers.base import PartialScrapeError
from classify_engine import classify_tender, PORTFOLIO_FIELDS
from scoring_engine import score_tender
from utils.opportunity_review import prepare_opportunities, write_review_state
from utils.text_utils import normalize_ref
from sync_dashboard import load_config


def collect(scraper):
    try:
        rows = scraper.run(raise_on_error=True)
        return rows, {'source': scraper.source_name, 'status': 'success', 'records': len(rows)}
    except PartialScrapeError as exc:
        return exc.tenders, {'source': scraper.source_name, 'status': 'partial', 'records': len(exc.tenders), 'error': str(exc)[:500]}
    except Exception as exc:
        return [], {'source': scraper.source_name, 'status': 'failed', 'records': 0, 'error': str(exc)[:500]}


def refresh(root):
    now = datetime.now(timezone.utc).isoformat()
    rows, health = [], []
    with ThreadPoolExecutor(max_workers=4) as executor:
        jobs = [executor.submit(collect, scraper) for scraper in get_active_scrapers(enable_selenium=False)]
        for job in as_completed(jobs):
            found, state = job.result()
            rows.extend(found)
            health.append({**state, 'checked_at': now})
    # Never replace the snapshot when the primary feed is incomplete.
    if not any(item['source'] == 'National Treasury' and item['status'] == 'success' for item in health):
        raise RuntimeError('Primary eTenders feed incomplete; previous snapshot retained')
    unique = {}
    for tender in rows:
        ref = normalize_ref(tender.get('ref', ''))
        if not ref or str(tender.get('closing_date', ''))[:10] < date.today().isoformat():
            continue
        if ref not in unique or len(tender.get('description', '')) > len(unique[ref].get('description', '')):
            unique[ref] = {**tender, 'ref': ref}
    prepared, queue = prepare_opportunities(list(unique.values()))
    state = write_review_state(Path(load_config().get('paths', {}).get('output_dir', root / 'output')), queue, health)
    existing = json.loads((root / 'dashboard/tenders.json').read_text())
    matches = []
    for tender in prepared:
        classification = classify_tender(tender['title'], tender.get('description', ''))
        if classification['category'] == 'EXCLUDED':
            continue
        scores = score_tender(title=tender['title'], description=tender.get('description', ''), client=tender.get('client', ''), closing_date=tender.get('closing_date', ''), category=classification['category'])
        tender.update(classification)
        tender.update({key: classification[key] for key in PORTFOLIO_FIELDS})
        tender.update(company=' / '.join(classification['companies']), priority=scores['priority'], score=scores['composite_score'])
        matches.append(tender)
    meta = {**existing['meta'], **state, 'last_sync': now, 'last_update': now, 'tender_count': len(matches), 'snapshot_origin': 'public_source_refresh_without_database_write', 'source_records': len(rows)}
    meta.pop('scope_refresh', None)
    payload = {'meta': meta, 'tenders': matches, 'planned_opportunities': existing.get('planned_opportunities', [])}
    for destination in ['dashboard/tenders.json', 'dashboard/public/tenders-latest.json']:
        path = root / destination
        temp = path.with_suffix('.tmp')
        temp.write_text(json.dumps(payload, indent=2) + '\n')
        temp.replace(path)
    print(json.dumps({'sources': health, 'matched_candidates': len(matches), 'review_queue': len(queue)}))


if __name__ == '__main__':
    refresh(Path(__file__).resolve().parents[1])
