"""High-recall retrieval separate from shortlist qualification.

Every captured notice remains searchable. Broad signals create review candidates;
absence of a keyword is unassessed, not evidence of irrelevance.
"""
from datetime import datetime, timezone
from pathlib import Path
import json

from classify_engine import classify_tender, clean, keyword_hits

CAPABILITY_TERMS = {
    'Cooling-water process': ['chemical', 'chemicals', 'chemistry', 'water conditioning', 'non oxidising', 'non oxidizing', 'microbiological control', 'cooling', 'coolant', 'condenser', 'heat exchanger', 'chiller', 'heat rejection', 'biofouling', 'biological fouling', 'biofilm', 'macrofouling', 'legionella', 'surfactant', 'surface active', 'dispersant', 'biocide', 'biocidal', 'water conditioning', 'scale inhibitor', 'antiscalant', 'water treatment'],
    'Water and steam-cycle chemistry': ['odacon', 'reicon', 'film forming', 'filming amine', 'amine treatment', 'corrosion inhibitor', 'corrosion control', 'boiler', 'feed water', 'feedwater', 'condensate', 'steam cycle', 'steam circuit', 'lay up', 'preservation', 'oxygen scavenger', 'alkaliser', 'alkalizer', 'deoxygenation'],
    'Process dosing and instrumentation': ['dosing', 'metering', 'injection', 'instrumentation', 'flow meter', 'flow meters', 'flowmeter', 'flowmeters', 'flow measurement', 'density meter', 'conductivity', 'analyser', 'analyzer', 'transmitter', 'telemetry', 'process control', 'scada', 'historian', 'pressure sensor', 'level sensor', 'temperature sensor', 'online monitoring', 'on line monitoring'],
    'Monitor and display supply': ['monitor', 'monitors', 'display', 'displays', 'touch panel', 'touch panels', 'touchscreen', 'touch screen', 'interactive panel', 'interactive panels', 'smart board', 'smartboard', 'interactive whiteboard', 'interactive whiteboards', 'video wall'],
}


def assess_discovery(tender):
    title = tender.get('title', '')
    description = tender.get('description', '')
    classification = classify_tender(title, description)
    attachment_names = ' '.join(str(item.get('name', '')) for item in (tender.get('attachments') or []))
    text = clean(title + ' ' + description + ' ' + attachment_names)
    signals = {name: keyword_hits(text, words) for name, words in CAPABILITY_TERMS.items()}
    signals = {name: words for name, words in signals.items() if words}
    process_lot = keyword_hits(clean(title), ['dosing', 'chemical', 'monitoring', 'instrumentation', 'flow meters'])
    explicit_notice = classification['reason'].startswith('Excluded: notice')
    clear_works = classification['reason'].startswith('Excluded: works scope') and not process_lot
    unrelated = keyword_hits(clean(title), ['chemical toilets', 'physical security', 'security guarding', 'haemoglobinopathy', 'patient monitor', 'vital signs monitor', 'spatial transformation', 'billing software', 'roof repair'])
    if explicit_notice or clear_works or unrelated:
        tier = 'clearly_excluded'
        reason = 'Clearly unrelated scope: ' + unrelated[0] if unrelated else classification['reason']
    elif classification['portfolios']:
        tier = 'strong_candidate'
        reason = 'Current capability rules match; specification and eligibility still require review'
    elif signals:
        tier = 'possible_candidate'
        reason = 'Broad capability or attachment-name signal; retain for review'
    else:
        tier = 'unassessed'
        reason = 'No positive signal in available listing; still searchable, attachments may contain relevant scope'
    return {'tier': tier, 'signals': signals, 'reason': reason}


def discovery_index(tenders):
    notices = []
    seen = set()
    for tender in tenders:
        # Do not merge identical reference numbers belonging to different buyers.
        identity = (tender.get('source', ''), tender.get('source_id') or tender.get('ref', ''), tender.get('client', ''), tender.get('title', ''))
        if identity in seen:
            continue
        seen.add(identity)
        fields = ['ref', 'title', 'description', 'client', 'source', 'url', 'closing_date', 'attachments', 'capture_group']
        row = {field: tender.get(field, [] if field == 'attachments' else '') for field in fields}
        row['discovery'] = assess_discovery(tender)
        notices.append(row)
    return {'checked_at': datetime.now(timezone.utc).isoformat(), 'notice_count': len(notices), 'notices': notices}


def write_discovery_index(tenders, path, source_health=None):
    payload = discovery_index(tenders)
    path = Path(path)
    # A failed supplementary source must not silently erase its prior notices.
    if source_health is not None and path.exists():
        try:
            previous = json.loads(path.read_text())
        except (OSError, ValueError):
            previous = {}
        healthy = {item['source'] for item in source_health if item.get('status') == 'success'}
        present = {(row.get('source'), row.get('ref'), row.get('client')) for row in payload['notices']}
        for row in previous.get('notices', []):
            identity = (row.get('source'), row.get('ref'), row.get('client'))
            if row.get('capture_group') not in healthy and identity not in present:
                payload['notices'].append({**row, 'capture_state': 'stale_source_failure'})
        payload['notice_count'] = len(payload['notices'])
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix('.tmp')
    temporary.write_text(json.dumps(payload, indent=2) + '\n')
    temporary.replace(path)
    return payload
