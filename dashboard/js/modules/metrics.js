/**
 * Dashboard metrics and statistics
 */

import { isTenderActive, getPriority, getTenderCompanyScope } from './tender.js';
import { setTextById } from '../utils/helpers.js';

/**
 * Compute dashboard metrics
 * @param {Array} tenders - Tenders array
 * @returns {Object}
 */
export function computeDashboardMetrics(tenders) {
    const list = Array.isArray(tenders) ? tenders : [];
    const totalCount = list.length;

    const active = list.filter(isTenderActive);
    const activeCount = active.length;

    let mexelFitCount = 0;
    let highPriorityCount = 0;

    const byPriorityActive = { HIGH: 0, MEDIUM: 0, LOW: 0, OTHER: 0 };
    const bySource = {};
    const bySourceActive = {};

    for (const t of list) {
        const src = (t?.source || 'Unknown').toString().trim() || 'Unknown';
        bySource[src] = (bySource[src] || 0) + 1;
    }

    for (const t of active) {
        const src = (t?.source || 'Unknown').toString().trim() || 'Unknown';
        bySourceActive[src] = (bySourceActive[src] || 0) + 1;

        const pr = getPriority(t);
        if (pr === 'HIGH') {
            byPriorityActive.HIGH += 1;
            highPriorityCount += 1;
        } else if (pr === 'MEDIUM') {
            byPriorityActive.MEDIUM += 1;
        } else if (pr === 'LOW') {
            byPriorityActive.LOW += 1;
        } else {
            byPriorityActive.OTHER += 1;
        }

        const scope = getTenderCompanyScope(t);
        if (scope === 'Mexel') mexelFitCount += 1;
    }

    return {
        totalCount,
        activeCount,
        mexelFitCount,
        highPriorityCount,
        byPriorityActive,
        bySource,
        bySourceActive,
    };
}

/**
 * Update priority mix bar
 * @param {Object} byPriorityActive - Priority counts
 * @param {number} activeTotal - Active total count
 */
export function updatePriorityMixBar(byPriorityActive, activeTotal) {
    const highEl = document.getElementById('priorityMixHigh');
    const medEl = document.getElementById('priorityMixMedium');
    const lowEl = document.getElementById('priorityMixLow');
    if (!highEl || !medEl || !lowEl) return;

    const total = Math.max(0, Number(activeTotal) || 0);
    const high = Number(byPriorityActive?.HIGH) || 0;
    const med = Number(byPriorityActive?.MEDIUM) || 0;
    const low = Number(byPriorityActive?.LOW) || 0;

    const pct = (n) => (total > 0 ? (n / total) * 100 : 0);
    const highPct = pct(high);
    const medPct = pct(med);
    const lowPct = Math.max(0, 100 - highPct - medPct);

    highEl.style.width = `${highPct}%`;
    medEl.style.width = `${medPct}%`;
    lowEl.style.width = `${lowPct}%`;

    highEl.title = `High (${high})`;
    medEl.title = `Medium (${med})`;
    lowEl.title = `Low (${low})`;
}

/**
 * Update dashboard stats UI
 * @param {Object} metrics - Metrics object
 */
export function updateDashboardStatsUI(metrics) {
    if (!metrics) return;
    setTextById('kpiTotalTenders', metrics.totalCount);
    setTextById('kpiMexelFit', metrics.mexelFitCount);
    setTextById('kpiHighPriority', metrics.highPriorityCount);

    setTextById('pipelineTotalActive', metrics.activeCount);
    setTextById('pipelineMexelActive', metrics.mexelFitCount);

    updatePriorityMixBar(metrics.byPriorityActive, metrics.activeCount);
}

/**
 * Render dashboard source health
 * @param {Array} tenders - Tenders array
 * @param {Object} metrics - Metrics object
 */
export function renderDashboardSourceHealth(tenders, metrics) {
    const container = document.getElementById('dashboardSourceHealth');
    if (!container) return;

    const list = Array.isArray(tenders) ? tenders : [];
    const bySource = metrics?.bySource || {};
    const bySourceActive = metrics?.bySourceActive || {};

    const entries = Object.entries(bySource).sort((a, b) => (b[1] || 0) - (a[1] || 0));
    if (entries.length === 0) {
        container.innerHTML = '<div class="company-card" style="text-align:center; color:#888;">No source data available</div>';
        return;
    }

    const activeBySourceDaysMin = {};
    const activeUrgentBySource = {};
    for (const t of list.filter(isTenderActive)) {
        const src = (t?.source || 'Unknown').toString().trim() || 'Unknown';
        const days = getDaysUntil(t?.closing_date);
        if (days !== null && Number.isFinite(days)) {
            const cur = activeBySourceDaysMin[src];
            if (typeof cur === 'undefined' || days < cur) activeBySourceDaysMin[src] = days;
            if (days <= 3) activeUrgentBySource[src] = (activeUrgentBySource[src] || 0) + 1;
        }
    }

    const top = entries.slice(0, 6);
    container.innerHTML = top
        .map(([name, count], idx) => {
            const activeCount = bySourceActive[name] || 0;
            const soonest = typeof activeBySourceDaysMin[name] === 'number' ? `${activeBySourceDaysMin[name]} day${activeBySourceDaysMin[name] === 1 ? '' : 's'}` : '–';
            const urgent = activeUrgentBySource[name] || 0;

            const accent = idx === 0 ? '#48dbfb' : idx === 1 ? '#667eea' : idx === 2 ? '#feca57' : '#a29bfe';
            const border = idx === 0 ? 'rgba(72,219,251,0.35)' : idx === 1 ? 'rgba(102,126,234,0.35)' : idx === 2 ? 'rgba(254,202,87,0.35)' : 'rgba(162,155,254,0.28)';

            return `
                <div class="company-card" style="border-color: ${border};">
                    <div class="company-name" style="color: ${accent};">${escapeHtml(name)}</div>
                    <div class="company-focus">Active tenders: <span style="color:${accent}; font-weight:700;">${activeCount}</span></div>
                    <div class="company-keywords">
                        <span class="keyword">In snapshot: ${count}</span>
                        <span class="keyword">Urgent (≤3d): ${urgent}</span>
                        <span class="keyword">Next close: ${soonest}</span>
                    </div>
                </div>
            `;
        })
        .join('');
}

/**
 * Render automation logs
 * @param {Object} meta - Meta object
 * @param {string} source - Data source
 * @param {Object} metrics - Metrics object
 */
export function renderAutomationLogs(meta, source, metrics) {
    const list = document.getElementById('automationLogList');
    if (!list) return;

    const lastSync = meta?.last_sync || '–';
    const nextRun = meta?.next_run || '–';
    const build = meta?.build_id || meta?.build_sha || '–';
    const records = metrics?.totalCount ?? '–';
    const active = metrics?.activeCount ?? '–';

    const statusLabel = source === 'seed' ? 'Fallback' : source === 'localStorage' ? 'Cached' : 'Live';
    const notes = source ? `Source: ${source}` : '';

    list.innerHTML = `
        <li class="tender-item">
            <div class="tender-content">
                <div class="tender-info">
                    <div class="tender-title">${escapeHtml(lastSync)} • Dashboard snapshot • Records: ${escapeHtml(String(records))} (${escapeHtml(String(active))} active)</div>
                    <div class="tender-meta">
                        <span>Status: ${escapeHtml(statusLabel)}</span>
                        <span>Build: ${escapeHtml(build)}</span>
                        ${notes ? `<span>${escapeHtml(notes)}</span>` : ''}
                    </div>
                </div>
            </div>
        </li>
        <li class="tender-item">
            <div class="tender-content">
                <div class="tender-info">
                    <div class="tender-title">Next scheduled run • ${escapeHtml(nextRun)}</div>
                    <div class="tender-meta">
                        <span>Tip: use "Refresh data" to bypass cache</span>
                    </div>
                </div>
            </div>
        </li>
    `;
}

/**
 * Update footer
 * @param {Object} meta - Meta object
 * @param {string} source - Data source
 * @param {Object} metrics - Metrics object
 */
export function updateFooter(meta, source, metrics) {
    const line2 = document.getElementById('footerLine2');
    const line3 = document.getElementById('footerLine3');
    if (line2) {
        const lastSync = meta?.last_sync || '–';
        const nextRun = meta?.next_run || '–';
        const records = metrics?.totalCount ?? '–';
        const active = metrics?.activeCount ?? '–';
        line2.textContent = `Last sync: ${lastSync} | Next run: ${nextRun} | Records: ${records} (${active} active)`;
    }
    if (line3) {
        const build = meta?.build_id || meta?.build_sha || '–';
        const srcText = source ? ` | Source: ${source}` : '';
        line3.textContent = `Build: ${build}${srcText}`;
    }
}

/**
 * Get days until closing date
 * @param {string} dateStr - Date string
 * @returns {number|null}
 */
function getDaysUntil(dateStr) {
    const closing = parseFlexibleDate(dateStr);
    if (!closing) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    closing.setHours(0, 0, 0, 0);
    return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
}

/**
 * Parse flexible date
 * @param {string} dateStr - Date string
 * @returns {Date|null}
 */
function parseFlexibleDate(dateStr) {
    if (!dateStr) return null;
    const raw = (dateStr || '').toString().trim();

    // ISO-ish / YYYY-MM-DD / YYYY-MM-DDTHH:mm
    if (/^\d{4}-\d{2}-\d{2}/.test(raw)) {
        const d = new Date(raw);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    // DD/MM/YYYY (common in ZA feeds)
    const dmY = raw.match(/^(\d{1,2})\/(\d{1,2})\/(\d{4})(?:\s+(\d{1,2}):(\d{2}))?$/);
    if (dmY) {
        const day = Number(dmY[1]);
        const month = Number(dmY[2]);
        const year = Number(dmY[3]);
        const hour = dmY[4] ? Number(dmY[4]) : 0;
        const minute = dmY[5] ? Number(dmY[5]) : 0;
        const d = new Date(year, month - 1, day, hour, minute, 0, 0);
        return Number.isNaN(d.getTime()) ? null : d;
    }

    const d = new Date(raw);
    return Number.isNaN(d.getTime()) ? null : d;
}

/**
 * Escape HTML
 * @param {string} value - Value to escape
 * @returns {string}
 */
function escapeHtml(value) {
    const s = (value ?? '').toString();
    return s
        .replace(/&/g, '&')
        .replace(/</g, '<')
        .replace(/>/g, '>')
        .replace(/"/g, '"')
        .replace(/'/g, '&#039;');
}
