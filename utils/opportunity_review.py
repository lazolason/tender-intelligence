"""Bounded document evidence and a review queue; never executes document content."""
from datetime import datetime, timezone
from io import BytesIO
from pathlib import Path
from urllib.parse import urlparse
import json
import time

from classify_engine import classify_tender
from utils.retry_tools import guarded_request
from utils.discovery import assess_discovery

DOCUMENT_HOSTS = {"www.etenders.gov.za", "etenders.gov.za", "tenderbulletin.eskom.co.za", "www.eskom.co.za", "eskom.co.za"}


def document_text(url, *, max_bytes=8_000_000):
    if urlparse(url).scheme != "https" or urlparse(url).hostname not in DOCUMENT_HOSTS:
        raise ValueError("Document host is not an approved official source")
    response = guarded_request(url, timeout=6, stream=True, allow_redirects=False)
    try:
        response.raise_for_status()
        if response.is_redirect:
            raise ValueError("Document redirect requires review")
        content = bytearray()
        for chunk in response.iter_content(65536):
            content.extend(chunk)
            if len(content) > max_bytes:
                raise ValueError("Document exceeds size limit")
        if not content.startswith(b'%PDF'):
            raise ValueError("Document is not a PDF; archive/other format requires review")
        from pypdf import PdfReader
        reader = PdfReader(BytesIO(content))
        text = '\n'.join((page.extract_text() or '') for page in reader.pages[:30])[:40000]
        if not text.strip():
            raise ValueError("No readable PDF text; OCR/manual review required")
        return text
    finally:
        response.close()


def prepare_opportunities(tenders, *, fetch_text=document_text, document_budget=20, time_budget=60):
    """Enrich likely/ambiguous scope before classification. Unread docs stay visible."""
    prepared, queue = [], []
    deadline = time.monotonic() + time_budget
    ordered = sorted(tenders, key=lambda tender: not bool(classify_tender(tender.get('title', ''), tender.get('description', ''))['portfolios']))
    for original in ordered:
        tender = dict(original)
        title, description = tender.get('title', ''), tender.get('description', '')
        discovery = assess_discovery(tender)
        documents = tender.get('attachments') or []
        # Explicit notices/works stay excluded, even when annexures mention brands.
        scope_excluded = discovery['tier'] == 'clearly_excluded'
        evidence, errors = [], []
        if not scope_excluded and discovery['tier'] in ('strong_candidate', 'possible_candidate'):
            def rank(document):
                name = str(document.get('name', '')).lower()
                if any(word in name for word in ['scope', 'specification', 'technical']):
                    return 0
                if 'invitation' in name:
                    return 1
                return 2
            ranked = sorted(documents, key=rank)
            for document in ranked[:3]:
                if document_budget <= 0 or time.monotonic() >= deadline:
                    errors.append('Document-check budget reached; manual review needed')
                    break
                document_budget -= 1
                try:
                    text = fetch_text(document['url'])
                    evidence.append({'name': document.get('name', ''), 'url': document['url'], 'characters': len(text)})
                    description += '\n[Official attachment scope; candidate evidence only]\n' + text[:12000]
                except Exception as exc:
                    errors.append(str(exc)[:200])
            if len(documents) > 3:
                errors.append('Additional attachments not analysed')
            final = classify_tender(title, description)
            reason = ('Specification/eligibility check required' if final['portfolios'] else 'Possible scope; listing/document evidence insufficient')
            if not documents:
                errors.append('No attachment links supplied by source')
            queue.append({'ref': tender.get('ref', ''), 'client': tender.get('client', ''), 'source': tender.get('source', ''), 'title': title, 'url': tender.get('url', ''), 'portfolios': final['portfolios'], 'discovery': discovery, 'reason': reason, 'documents_checked': evidence, 'limitations': errors})
            tender['review_status'] = 'needs_review'
            tender['document_evidence'] = evidence
        tender['description'] = description
        prepared.append(tender)
    return prepared, queue


def write_review_state(output_dir, queue, source_health=None):
    path = Path(output_dir) / 'opportunity_review.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    state = {'checked_at': datetime.now(timezone.utc).isoformat(), 'review_queue': queue, 'source_health': source_health or []}
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(state, indent=2) + '\n')
    temp.replace(path)
    return state


def read_review_state(output_dir):
    try:
        value = json.loads((Path(output_dir) / 'opportunity_review.json').read_text())
        return value if isinstance(value, dict) else {}
    except (OSError, ValueError):
        return {}
