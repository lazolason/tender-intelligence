/**
 * Hybrid dashboard bridge.
 *
 * Keeps the existing dashboard markup and interaction model, but moves the
 * application logic out of `index.html` and onto shared ES-module helpers.
 */

import { state } from './modules/config.js';
import { loadTenderPayload, applyTenderPayload } from './modules/data.js';
import { getCountdownHtml, getDaysUntil, getPriority, isTenderActive } from './modules/tender.js';
import {
    describeActiveEmptyState,
    getFilteredActiveTenders,
    getRecentMatchedTenders,
    normalizeCompanyLabel,
} from './modules/dashboardSummary.js';
import { escapeHtml, safeHttpUrl } from './utils/helpers.js';

const ITEMS_PER_PAGE = 20;

function resolveApiBaseUrl() {
    if (window.TI_API_BASE) return window.TI_API_BASE;
    const current = new URL(window.location.href);
    if (current.port === '8000') {
        current.port = '5001';
        return current.origin;
    }
    return current.origin;
}

const API_BASE_URL = resolveApiBaseUrl();

let displayedCount = 0;
let plannedFilter = 'all';

function parseTimestamp(value) {
    if (!value) return Number.NaN;
    const raw = String(value).trim();
    if (!raw) return Number.NaN;
    const normalized = raw.includes('T') ? raw : raw.replace(' ', 'T');
    const parsed = Date.parse(normalized);
    return Number.isFinite(parsed) ? parsed : Number.NaN;
}

function updateHeader(meta = {}) {
    const lastSyncEl = document.getElementById('lastSync');
    const winRateBadge = document.getElementById('winRateBadge');
    const sourceStats = document.getElementById('sourceStats');
    const totalCount = document.getElementById('totalCount');
    const activeCount = state.tenders.filter(isTenderActive).length;
    const lastSyncRaw = meta.last_sync || '--';
    const lastSyncTs = parseTimestamp(meta.last_sync || meta.last_update);
    const ageHours = Number.isFinite(lastSyncTs) ? (Date.now() - lastSyncTs) / 3600000 : Number.NaN;
    const isStale = Number.isFinite(ageHours) && ageHours > 48;

    if (lastSyncEl) {
        lastSyncEl.textContent = `🔄 Last synced: ${lastSyncRaw}`;
        lastSyncEl.style.color = isStale ? '#feca57' : '';
        lastSyncEl.style.borderColor = isStale ? 'rgba(254,202,87,0.45)' : '';
    }

    const bidStats = meta.bid_statistics || {};
    if (winRateBadge) {
        if (typeof bidStats.win_rate === 'number' && typeof bidStats.total_bids === 'number') {
            winRateBadge.textContent = `🏆 Win Rate: ${bidStats.win_rate}% (${bidStats.wins || 0}/${bidStats.total_bids} bids)`;
            winRateBadge.style.display = 'inline-block';
        } else {
            winRateBadge.style.display = 'none';
        }
    }

    if (sourceStats) {
        const staleSuffix = isStale ? ` • Snapshot stale (${Math.floor(ageHours)}h old)` : '';
        sourceStats.textContent = `📊 Active Tenders: ${activeCount} • Snapshot Matches: ${state.tenders.length}${staleSuffix}`;
        sourceStats.style.color = isStale ? '#feca57' : '';
        sourceStats.style.borderColor = isStale ? 'rgba(254,202,87,0.45)' : '';
    }

    if (totalCount) {
        totalCount.textContent = String(state.tenders.length);
    }
}

function updateStats() {
    const active = state.tenders.filter(isTenderActive);
    const statTotal = document.getElementById('statTotal');
    const statHigh = document.getElementById('statHigh');
    const statMedium = document.getElementById('statMedium');
    const statLow = document.getElementById('statLow');
    const statMexel = document.getElementById('statMexel');
    const statPhakathi = document.getElementById('statPhakathi');

    if (statTotal) statTotal.textContent = String(active.length);
    if (statHigh) statHigh.textContent = String(active.filter((t) => getPriority(t) === 'HIGH').length);
    if (statMedium) statMedium.textContent = String(active.filter((t) => getPriority(t) === 'MEDIUM').length);
    if (statLow) statLow.textContent = String(active.filter((t) => getPriority(t) === 'LOW').length);
    if (statMexel) {
        statMexel.textContent = String(
            active.filter((t) => normalizeCompanyLabel(t).toLowerCase() === 'mexel').length
        );
    }
    if (statPhakathi) {
        statPhakathi.textContent = String(
            active.filter((t) => normalizeCompanyLabel(t).toLowerCase() === 'phakathi').length
        );
    }
}

function getFilteredTenders() {
    return getFilteredActiveTenders(state.tenders, {
        filter: state.currentFilter || 'all',
        searchQuery: state.searchQuery || '',
    });
}

export function createTenderListItem(tender) {
    const li = document.createElement('li');
    const days = getDaysUntil(tender?.closing_date);
    const urgency =
        days !== null && days <= 3 && days >= 0 ? 'urgent' : days !== null && days <= 7 && days >= 0 ? 'warning' : '';
    const company = normalizeCompanyLabel(tender);
    const companyClass = company.toUpperCase().replace(/[^A-Z0-9_-]/g, '-');
    const keywords = Array.isArray(tender?.matched_keywords) ? tender.matched_keywords : [];
    const hasIntel = Boolean(tender?.pdf_analysis);
    const isDuplicate =
        Array.isArray(tender?.duplicate_refs) && tender.duplicate_refs.length > 0;
    const safeUrl = safeHttpUrl(tender?.url);
    const score =
        tender?.score ??
        tender?.scores?.composite ??
        tender?.scores?.composite_score ??
        tender?.composite_score ??
        '–';

    li.className = `tender-item ${urgency}`.trim();
    li.innerHTML = `
        <div class="tender-content">
            <div class="tender-info">
                <div class="tender-header">
                    <span class="tender-ref">${escapeHtml(tender?.ref || 'NA')}</span>
                    <span class="company-badge company-${escapeHtml(companyClass)}">${escapeHtml(company)}</span>
                    ${getCountdownHtml(tender?.closing_date)}
                    ${hasIntel ? '<span class="intel-badge">📄 Intel</span>' : ''}
                    ${isDuplicate ? '<span class="intel-badge" style="color:#feca57; border-color:#feca57;">🔗 Duplicate</span>' : ''}
                </div>
                <div class="tender-title">${escapeHtml(tender?.title || 'Untitled tender')}</div>
                <div class="keyword-container">
                    ${keywords.map((keyword) => `<span class="keyword-tag">${escapeHtml(keyword)}</span>`).join('')}
                </div>
                <div class="tender-meta">
                    <span>📍 ${escapeHtml(tender?.client || 'Unknown')}</span>
                    <span>📁 ${escapeHtml(tender?.category || 'Unknown')}</span>
                    <span>🔗 ${escapeHtml(tender?.source || 'Unknown')}</span>
                </div>
            </div>
            <div class="tender-right">
                <span class="priority-badge priority-${escapeHtml(getPriority(tender) || 'LOW')}">${escapeHtml(getPriority(tender) || 'LOW')}</span>
                <div class="score">${escapeHtml(String(score))}</div>
                <div style="display:flex; gap:8px;">
                    <button class="ai-btn tender-summary-btn" type="button">📄 Summary</button>
                    ${
                        safeUrl
                            ? `<a href="${escapeHtml(safeUrl)}" target="_blank" rel="noopener noreferrer" class="view-btn">View ↗</a>`
                            : ''
                    }
                </div>
            </div>
        </div>
    `;

    li.addEventListener('click', () => {
        if (safeUrl) window.open(safeUrl, '_blank', 'noopener,noreferrer');
    });

    li.querySelector('.tender-summary-btn')?.addEventListener('click', (event) => {
        event.stopPropagation();
        openSummaryModal(tender);
    });

    li.querySelector('.view-btn')?.addEventListener('click', (event) => {
        event.stopPropagation();
    });

    return li;
}

function renderRecentMatches() {
    const section = document.getElementById('recentMatchesSection');
    const list = document.getElementById('recentTenderList');
    const count = document.getElementById('recentMatchesCount');
    if (!section || !list || !count) return;

    const recent = getRecentMatchedTenders(state.tenders, { limit: 6 });
    list.innerHTML = '';
    count.textContent = String(recent.length);

    if (!recent.length) {
        section.hidden = true;
        return;
    }

    recent.forEach((tender) => {
        list.appendChild(createTenderListItem(tender));
    });
    section.hidden = false;
}

function updateEmptyState(filtered) {
    const panel = document.getElementById('activeEmptyState');
    const title = document.getElementById('activeEmptyStateTitle');
    const message = document.getElementById('activeEmptyStateMessage');
    const recentSection = document.getElementById('recentMatchesSection');
    if (!panel || !title || !message || !recentSection) return;

    if (filtered.length > 0) {
        panel.hidden = true;
        recentSection.hidden = true;
        return;
    }

    const emptyState = describeActiveEmptyState(state.tenders, {
        filter: state.currentFilter || 'all',
        searchQuery: state.searchQuery || '',
    });

    title.textContent = emptyState.title;
    message.textContent = emptyState.message;
    panel.hidden = false;
    recentSection.hidden = !emptyState.showRecentMatches;
}

function renderTenders({ append = false } = {}) {
    const list = document.getElementById('tenderList');
    if (!list) return;

    const filtered = getFilteredTenders();
    const start = append ? displayedCount : 0;
    const end = Math.min(start + ITEMS_PER_PAGE, filtered.length);

    if (!append) {
        displayedCount = 0;
        list.innerHTML = '';
    }

    filtered.slice(start, end).forEach((tender) => {
        list.appendChild(createTenderListItem(tender));
    });

    displayedCount = end;
    window.lastFiltered = filtered;

    const displayedCountEl = document.getElementById('displayedCount');
    const remainingCountEl = document.getElementById('remainingCount');
    const loadMoreContainer = document.getElementById('loadMoreContainer');

    if (displayedCountEl) displayedCountEl.textContent = String(filtered.length);
    if (remainingCountEl) remainingCountEl.textContent = String(Math.max(0, filtered.length - end));
    if (loadMoreContainer) {
        loadMoreContainer.style.display = end < filtered.length ? 'block' : 'none';
    }

    updateEmptyState(filtered);
    renderRecentMatches();
}

function renderIntel(intel) {
    const summaryText = document.getElementById('summaryText');
    if (!summaryText) return;

    const requirements = Array.isArray(intel?.requirements) ? intel.requirements : [];
    const values = Array.isArray(intel?.values) ? intel.values : [];
    const contact = intel?.contact || {};

    let html = `<p style="color:#8fa5ff; font-size:0.9rem; margin-bottom:15px;">Analyzed ${escapeHtml(String(intel?.page_count || 0))} pages (${escapeHtml(String(intel?.word_count || 0))} words)</p>`;
    if (requirements.length) {
        html += `<h4 style="color:#fff; margin:10px 0;">📋 Requirements</h4><ul class="req-list">${requirements
            .map((requirement) => `<li class="req-item">${escapeHtml(requirement)}</li>`)
            .join('')}</ul>`;
    }
    if (values.length) {
        html += `<h4 style="color:#fff; margin:10px 0;">💰 Estimates</h4><ul class="req-list">${values
            .map((value) => {
                const formatted = escapeHtml(value?.formatted || '–');
                const context = escapeHtml(value?.context || '');
                return `<li class="req-item"><strong>${formatted}</strong>${context ? `: ${context}` : ''}</li>`;
            })
            .join('')}</ul>`;
    }
    if (contact && (contact.email || contact.phone)) {
        html += `
            <div style="background:rgba(102,126,234,0.1); padding:15px; border-radius:12px; margin-top:15px;">
                <h4 style="color:#48dbfb;">📞 Contact</h4>
                <p>${escapeHtml(contact.email || '--')} | ${escapeHtml(contact.phone || '--')}</p>
            </div>
        `;
    }

    summaryText.innerHTML = html;
}

function openSummaryModal(tender) {
    if (!tender) return;

    window.__currentTender = tender;
    const summaryModal = document.getElementById('summaryModal');
    const modalTitle = document.getElementById('modalTitle');
    const modalSubtitle = document.getElementById('modalSubtitle');
    const summaryText = document.getElementById('summaryText');

    if (modalTitle) modalTitle.textContent = tender?.title || 'Tender';
    if (modalSubtitle) {
        modalSubtitle.textContent = `${tender?.ref || 'NA'} | ${tender?.client || 'Unknown client'}`;
    }

    if (tender?.pdf_analysis) {
        renderIntel(tender.pdf_analysis);
    } else if (summaryText) {
        summaryText.textContent =
            tender?.description ||
            'No detailed summary available yet. Run PDF analysis to extract more intelligence.';
    }

    summaryModal?.classList.add('active');
}

function closeSummaryModal() {
    document.getElementById('summaryModal')?.classList.remove('active');
}

async function updateTenderOutcome() {
    const outcomeSelect = document.getElementById('outcomeSelect');
    const updateOutcomeBtn = document.getElementById('updateOutcomeBtn');
    const outcome = outcomeSelect?.value || '';
    const tender = window.__currentTender;

    if (!outcome) {
        window.alert('Select an outcome');
        return;
    }
    if (!tender?.ref || !updateOutcomeBtn) return;

    updateOutcomeBtn.disabled = true;
    try {
        const response = await fetch(`${API_BASE_URL}/api/bids`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ ref: tender.ref, outcome, submitted: true }),
        });
        if (!response.ok) {
            throw new Error(`API returned ${response.status}`);
        }
        updateOutcomeBtn.textContent = '✅ Updated';
        window.setTimeout(() => {
            updateOutcomeBtn.disabled = false;
            updateOutcomeBtn.textContent = 'Update';
            closeSummaryModal();
        }, 1500);
    } catch (error) {
        window.alert('API Error');
        console.error('Failed to update tender outcome:', error);
        updateOutcomeBtn.disabled = false;
    }
}

async function copySummary() {
    const copyBtn = document.getElementById('copySummaryBtn');
    const text = document.getElementById('summaryText')?.textContent || '';
    if (!copyBtn || !text) return;

    try {
        await navigator.clipboard.writeText(text);
        copyBtn.textContent = '✅ Copied';
        window.setTimeout(() => {
            copyBtn.textContent = '📋 Copy';
        }, 2000);
    } catch (error) {
        console.error('Failed to copy summary text:', error);
    }
}

function renderPlannedOpportunities() {
    const list = document.getElementById('plannedOpportunityList');
    const count = document.getElementById('plannedCount');
    const empty = document.getElementById('plannedEmptyState');
    if (!list || !count || !empty) return;

    const plans = Array.isArray(state.plannedOpportunities) ? state.plannedOpportunities : [];
    const filtered = plans.filter((plan) => {
        if (plannedFilter === 'all') return true;
        if (plannedFilter === 'MEXEL' || plannedFilter === 'PHAKATHI') {
            return String(plan?.category || '').toUpperCase() === plannedFilter;
        }
        return String(plan?.lifecycle_stage || '').toUpperCase() === plannedFilter;
    });

    list.innerHTML = '';
    count.textContent = String(filtered.length);
    empty.hidden = filtered.length > 0;

    filtered.forEach((plan) => {
        const card = document.createElement('article');
        const stage = String(plan?.lifecycle_stage || 'PLANNED').toUpperCase();
        card.className = `pipeline-card ${stage === 'DUE_SOON' ? 'due-soon' : stage === 'OVERDUE' ? 'overdue' : ''}`;

        const heading = document.createElement('h3');
        heading.textContent = plan?.description || 'Planned procurement';
        card.appendChild(heading);

        const meta = document.createElement('div');
        meta.className = 'pipeline-meta';
        const values = [
            `🏛️ ${plan?.institution || 'Unknown institution'}`,
            `📅 Advert: ${plan?.planned_advert_date || 'TBC'}`,
            `🏷️ ${plan?.company || plan?.category || 'Review'}`,
            `📍 ${stage.replace('_', ' ')}`,
        ];
        values.forEach((value) => {
            const span = document.createElement('span');
            span.textContent = value;
            meta.appendChild(span);
        });
        card.appendChild(meta);

        if (plan?.source_url) {
            try {
                const url = new URL(plan.source_url, window.location.origin);
                if (url.protocol === 'http:' || url.protocol === 'https:') {
                    const actions = document.createElement('div');
                    actions.className = 'pipeline-actions';
                    const link = document.createElement('a');
                    link.className = 'view-btn';
                    link.href = url.href;
                    link.target = '_blank';
                    link.rel = 'noopener noreferrer';
                    link.textContent = 'View Treasury plan ↗';
                    actions.appendChild(link);
                    card.appendChild(actions);
                }
            } catch {
                // Ignore malformed source URLs.
            }
        }
        list.appendChild(card);
    });
}

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach((content) => content.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.classList.toggle('active', button.dataset.tab === tabId);
    });

    document.getElementById(tabId)?.classList.add('active');
    if (tabId === 'calendar') {
        renderCalendar();
    } else if (tabId === 'pipeline') {
        renderPlannedOpportunities();
    }
}

function renderCalendar() {
    const grid = document.getElementById('calendarGrid');
    const monthLabel = document.getElementById('calendarMonth');
    if (!grid || !monthLabel) return;

    const year = state.currentMonth.getFullYear();
    const month = state.currentMonth.getMonth();
    monthLabel.textContent = state.currentMonth.toLocaleDateString('en-ZA', {
        month: 'long',
        year: 'numeric',
    });

    const firstDay = new Date(year, month, 1).getDay();
    const daysInMonth = new Date(year, month + 1, 0).getDate();
    const tendersByDate = {};

    state.tenders.forEach((tender) => {
        const dateKey = tender?.closing_date;
        if (!dateKey) return;
        tendersByDate[dateKey] = tendersByDate[dateKey] || [];
        tendersByDate[dateKey].push(tender);
    });

    grid.innerHTML = '';
    for (let i = 0; i < firstDay; i += 1) {
        const spacer = document.createElement('div');
        spacer.className = 'calendar-day other-month';
        grid.appendChild(spacer);
    }

    for (let day = 1; day <= daysInMonth; day += 1) {
        const dateKey = `${year}-${String(month + 1).padStart(2, '0')}-${String(day).padStart(2, '0')}`;
        const count = (tendersByDate[dateKey] || []).length;
        const cell = document.createElement('div');
        cell.className = `calendar-day ${count ? 'has-tenders' : ''}`.trim();
        cell.textContent = String(day);
        if (count) {
            const badge = document.createElement('span');
            badge.className = 'tender-count';
            badge.textContent = String(count);
            cell.appendChild(badge);
        }
        cell.addEventListener('click', () => showDay(dateKey));
        grid.appendChild(cell);
    }
}

function showDay(dateKey) {
    const dayTenders = state.tenders.filter((tender) => tender?.closing_date === dateKey);
    const container = document.getElementById('dayTenders');
    if (!container) return;

    if (dayTenders.length === 0) {
        container.innerHTML = '';
        return;
    }

    container.innerHTML = `<h3>Closing ${escapeHtml(dateKey)}</h3>`;
    dayTenders.forEach((tender) => {
        const card = document.createElement('div');
        card.style.cssText =
            'padding:10px; background:rgba(255,255,255,0.05); margin-top:10px; border-radius:8px;';
        card.innerHTML = `<strong>${escapeHtml(tender?.ref || 'NA')}</strong>: ${escapeHtml(tender?.title || 'Untitled tender')}`;
        container.appendChild(card);
    });
}

function changeMonth(delta) {
    state.currentMonth.setMonth(state.currentMonth.getMonth() + delta);
    renderCalendar();
}

function searchTenders() {
    state.searchQuery = (document.getElementById('searchBox')?.value || '').trim();
    renderTenders();
}

function filterTenders(filter) {
    state.currentFilter = filter;
    displayedCount = 0;
    document.querySelectorAll('.filter-tab').forEach((button) => {
        button.classList.toggle('active', button.dataset.filter === filter);
    });
    renderTenders();
}

function loadMore() {
    renderTenders({ append: true });
}

function bindUI() {
    document.querySelectorAll('.tab-btn').forEach((button) => {
        button.addEventListener('click', () => showTab(button.dataset.tab || 'dashboard'));
    });

    document.querySelectorAll('.filter-tab[data-filter]').forEach((button) => {
        button.addEventListener('click', () => filterTenders(button.dataset.filter || 'all'));
    });
    document.querySelectorAll('[data-plan-filter]').forEach((button) => {
        button.addEventListener('click', () => {
            plannedFilter = button.dataset.planFilter || 'all';
            document.querySelectorAll('[data-plan-filter]').forEach((item) => item.classList.remove('active'));
            button.classList.add('active');
            renderPlannedOpportunities();
        });
    });

    document.getElementById('searchBox')?.addEventListener('input', searchTenders);
    document.getElementById('loadMoreBtn')?.addEventListener('click', loadMore);
    document.getElementById('prevMonthBtn')?.addEventListener('click', () => changeMonth(-1));
    document.getElementById('nextMonthBtn')?.addEventListener('click', () => changeMonth(1));
    document.getElementById('summaryModalClose')?.addEventListener('click', closeSummaryModal);
    document.getElementById('updateOutcomeBtn')?.addEventListener('click', updateTenderOutcome);
    document.getElementById('copySummaryBtn')?.addEventListener('click', copySummary);

    window.addEventListener('click', (event) => {
        if (event.target?.id === 'summaryModal') closeSummaryModal();
    });
    window.addEventListener('keydown', (event) => {
        if (event.key === 'Escape') closeSummaryModal();
    });
}

async function init() {
    bindUI();

    try {
        const payload = await loadTenderPayload();
        applyTenderPayload(payload);
        updateHeader(payload?.meta || window.dashboardMeta || {});
        updateStats();
        renderTenders();
        renderPlannedOpportunities();
    } catch (error) {
        console.error('Error loading tenders:', error);
        document.getElementById('tenderList').innerHTML =
            '<li class="empty-state">Error loading data. Run sync_dashboard.py first.</li>';
    }
}

window.searchTenders = searchTenders;
window.filterTenders = filterTenders;
window.showTab = showTab;
window.changeMonth = changeMonth;
window.showDay = showDay;
window.loadMore = loadMore;
window.openSummaryModal = openSummaryModal;
window.closeSummaryModal = closeSummaryModal;
window.updateTenderOutcome = updateTenderOutcome;
window.copySummary = copySummary;

if (!window.__TI_DISABLE_AUTO_INIT__) {
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', init, { once: true });
    } else {
        init();
    }
}
