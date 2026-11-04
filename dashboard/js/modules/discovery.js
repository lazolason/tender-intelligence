import { escapeHtml, safeHttpUrl } from '../utils/helpers.js';

export function searchCapturedNotices(notices, query = '', tier = 'all') {
    const normalize = (value) => String(value).toLowerCase().replace(/[^a-z0-9]+/g, ' ').trim();
    const tokens = normalize(query).split(/\s+/).filter(Boolean);
    return notices.filter((row) => {
        if (tier !== 'all' && row.discovery?.tier !== tier) return false;
        const text = [row.ref, row.title, row.description, row.client, row.source,
            ...(row.attachments || []).map((item) => item.name)].join(' ');
        const searchable = normalize(text);
        return tokens.every((token) => searchable.includes(token));
    });
}

export function bindDiscovery() {
    const button = document.getElementById('loadDiscovery');
    const query = document.getElementById('discoverySearch');
    const tier = document.getElementById('discoveryTier');
    const results = document.getElementById('discoveryResults');
    const status = document.getElementById('discoveryStatus');
    if (!button || !query || !tier || !results || !status) return;
    let notices = null;
    function render() {
        if (!notices) return;
        const matches = searchCapturedNotices(notices, query.value, tier.value);
        status.textContent = `${matches.length} of ${notices.length} captured notices; showing up to 50. This is source coverage, not all tenders everywhere.`;
        results.innerHTML = matches.slice(0, 50).map((row) => {
            const url = safeHttpUrl(row.url);
            const label = `${row.ref || ''} — ${row.title || 'Untitled'}`;
            const link = url ? `<a href="${escapeHtml(url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(label)}</a>` : escapeHtml(label);
            const date = row.closing_date || 'Date unverified';
            return `<p>${link}<br><small>${escapeHtml(row.client || '')} · ${escapeHtml(row.source || '')} · closes ${escapeHtml(date)} · ${escapeHtml((row.discovery?.tier || 'unassessed').replaceAll('_', ' '))}${row.capture_state === 'stale_source_failure' ? ' · retained from failed source; verify currency' : ''}</small></p>`;
        }).join('') || '<p>No matches in captured notices. Try fewer terms; absence here does not establish that no tender exists.</p>';
    }
    button.addEventListener('click', async () => {
        button.disabled = true;
        status.textContent = 'Loading captured notices…';
        try {
            const response = await fetch('/public/discovery-index.json', { cache: 'no-store' });
            if (!response.ok) throw new Error(`HTTP ${response.status}`);
            const payload = await response.json();
            if (!Array.isArray(payload.notices)) throw new Error('Invalid discovery index');
            notices = payload.notices;
            render();
        } catch (error) {
            status.textContent = `Captured-notice index unavailable: ${error.message}. Previous results retained; refresh source capture.`;
        } finally {
            button.disabled = false;
        }
    });
    query.addEventListener('input', render);
    tier.addEventListener('change', render);
}
