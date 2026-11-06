import { escapeHtml, safeHttpUrl } from '../utils/helpers.js';

export function renderCoverage(meta = {}) {
    const health = document.getElementById('sourceHealth');
    const review = document.getElementById('opportunityReview');
    const count = document.getElementById('coverageCount');
    const sources = Array.isArray(meta.source_health) ? meta.source_health : [];
    const queue = Array.isArray(meta.review_queue) ? meta.review_queue : [];
    if (count) count.textContent = `(${queue.length} to review)`;
    if (health) health.innerHTML = sources.length ? sources.map((item) => {
        const timestamp = Date.parse(item.checked_at || '');
        const stale = !Number.isFinite(timestamp) || Date.now() - timestamp > 36 * 3600000;
        return `<p><strong>${escapeHtml(item.source || 'Unknown source')}</strong>: ${escapeHtml(item.status || 'unknown')} · ${Number(item.records) || 0} records${stale ? ' · stale/unverified' : ''}<br><small>${escapeHtml(item.checked_at || 'No check time')} ${escapeHtml(item.error || '')}</small></p>`;
    }).join('') : '<p>Source health unavailable. A loaded snapshot does not confirm feed health.</p>';
    if (review) review.innerHTML = queue.length ? '<h3>Needs specification / eligibility review</h3><p>These are candidates, not confirmed bid qualifications.</p>' + queue.slice(0, 50).map((item) => {
        const url = safeHttpUrl(item.url);
        const label = `${item.ref || ''} — ${item.title || ''}`;
        const title = url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>` : escapeHtml(label);
        return `<p>${title}<br><small>${escapeHtml(item.reason || '')} ${escapeHtml((item.limitations || []).join('; '))}</small></p>`;
    }).join('') + (queue.length > 50 ? '<p>Showing the first 50; full queue is in the snapshot export.</p>' : '') : '<p>No review queue supplied for this snapshot.</p>';
}
