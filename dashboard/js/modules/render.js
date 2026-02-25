/**
 * Tender rendering and virtual scrolling
 */

import { state, ITEM_HEIGHT, CHUNK_SIZE, BUFFER } from './config.js';
import {
    getVirtualScrollContainer,
    getVirtualScrollTbody,
    setVirtualScrollTbody,
    setVirtualScrollContainer,
    getVirtualLastKey,
    setVirtualLastKey,
    updateVisibleItems
} from './config.js';
import {
    getCompany,
    getPriority,
    getCountdownHtml,
    classifyTender,
    computeDecision,
    getStatusMeta
} from './tender.js';
import { escapeHtml } from '../utils/helpers.js';
import { getTenderAssignment, getTenderCurrentStatus, isTenderWatchlisted, toggleWatchlist, getCurrentUsername, getUnreadMentionCount, clearTenderAssignment, setTenderAssignment } from './storage.js';
import { teamMembers } from './config.js';

/**
 * Create tender row element
 * @param {Object} item - Item with tender and classification
 * @param {number} _idx - Index
 * @returns {HTMLElement}
 */
export function createTenderRow(item, _idx) {
    const t = item.tender;
    const scores = t.scores || {};
    const { relevance, categories } = item.classification;
    const title = t.title || '-';
    const source = t.source || '-';
    const company = getCompany(t) || '-';
    const priority = getPriority(t) || '-';
    const closeDate = t.closing_date || '-';
    const fitScore = (t.score ?? scores.fit ?? scores.fit_score ?? '-') || '-';
    const countdownStatus = t.status || getCountdownHtml(t.closing_date) || '-';
    const link = t.url ? `<a href="${t.url}" target="_blank" rel="noopener" class="view-btn" style="padding: 6px 15px; font-size: 0.8rem;" onclick="event.stopPropagation()">Open ↗</a>` : '-';
    const decision = computeDecision(t);
    const scopeClass = relevance === 'OutOfScope' ? 'scope-pill-out' : relevance === 'Mexel' ? 'scope-pill-mexel' : 'scope-pill-out';
    const scopeText = relevance === 'OutOfScope' ? 'Not in scope' : relevance === 'Mexel' ? 'Mexel' : 'Review';
    const decisionPill = `<span class="decision-pill ${decision.className}">${decision.label}<span class="reason"> · ${decision.reason}</span><span class="confidence"> · ${decision.confidence}%</span></span>`;
    const categoryTags = (categories || []).map(c => `<span class="category-tag">${c}</span>`).join('');
    const assignment = getTenderAssignment(t.ref);
    const assignedLabel = assignment?.assignedTo ? `👤 ${escapeHtml(assignment.assignedTo)}` : '';
    const user = getCurrentUsername();
    const mentionCount = user ? getUnreadMentionCount(t.ref, user) : 0;
    const assignOptions = [
        `<option value="" ${assignment ? '' : 'selected'} disabled>Assign to…</option>`,
        `<option value="__unassigned__">Unassigned</option>`,
        ...teamMembers.map((m) => `<option value="${escapeHtml(m)}"${assignment?.assignedTo === m ? ' selected' : ''}>${escapeHtml(m)}</option>`)
    ].join('');
    const lifecycleStatus = getTenderCurrentStatus(t.ref);
    const statusMeta = getStatusMeta(lifecycleStatus);
    const statusBadge = `<span class="status-badge status-${statusMeta.color}">${escapeHtml(statusMeta.icon)} ${escapeHtml(statusMeta.value)}</span>`;
    const priorityRaw = (priority || '').toString().toUpperCase();
    const priorityBadge = ['HIGH', 'MEDIUM', 'LOW'].includes(priorityRaw)
        ? `<span class="priority-badge priority-${priorityRaw}">${escapeHtml(priorityRaw)}</span>`
        : `<span class="priority-badge priority-LOW">LOW</span>`;
    const watchlisted = isTenderWatchlisted(t.ref);
    const starBtn = `
        <button type="button" class="watchlist-star ${watchlisted ? 'active' : ''}" data-ref="${escapeHtml(t.ref || '')}" aria-label="Toggle watchlist" title="Toggle watchlist">
            ${watchlisted ? '★' : '☆'}
        </button>
    `;

    const row = document.createElement('tr');
    row.classList.add('tender-row');
    if (['HIGH', 'MEDIUM', 'LOW'].includes(priorityRaw)) row.classList.add(`priority-row-${priorityRaw}`);
    row.dataset.ref = (t.ref || '').toString();
    row.style = "border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; cursor: pointer;";
    row.onclick = () => openTenderModal(t);
    row.title = "Click to view tender details";
    row.onmouseover = () => row.style.background = 'rgba(255,255,255,0.05)';
    row.onmouseout = () => row.style.background = 'transparent';
    row.innerHTML = `
        <td style="padding: 15px;">
            <div class="tender-title-row">
                <div style="font-weight: 600; color: #fff; margin-bottom: 4px;">${title}</div>
                ${starBtn}
            </div>
            <div style="font-size: 0.8rem; color: #667eea;">${t.ref || '-'}</div>
            <div style="margin-top:4px;">${categoryTags}</div>
            <div class="assignment-inline">
                <span class="assignment-indicator">${assignedLabel}</span>
                <span class="mention-pill ${mentionCount ? '' : 'hidden'}" title="Unread mentions">@${mentionCount}</span>
                <select class="assignment-select" data-ref="${escapeHtml(t.ref || '')}" aria-label="Assign tender">
                    ${assignOptions}
                </select>
            </div>
        </td>
        <td style="padding: 15px; color: #ccc;">${source}</td>
        <td style="padding: 15px; color: #ccc;">${company}</td>
        <td style="padding: 15px; color: #ccc;">
            <div class="priority-status-cell">
                ${priorityBadge}
                ${statusBadge}
            </div>
        </td>
        <td style="padding: 15px; color: #ccc;">${closeDate}</td>
        <td style="padding: 15px; font-weight: bold; color: #fff;">${fitScore}</td>
        <td style="padding: 15px;">${countdownStatus}</td>
        <td style="padding: 15px;"><span class="scope-pill ${scopeClass}">${scopeText}</span></td>
        <td style="padding: 15px;">${decisionPill}</td>
        <td style="padding: 15px;">${link}</td>
    `;

    const select = row.querySelector('.assignment-select');
    if (select) {
        select.addEventListener('click', (e) => e.stopPropagation());
        select.addEventListener('change', (e) => {
            e.stopPropagation();
            const ref = select.getAttribute('data-ref') || t.ref;
            const value = (select.value || '').toString();
            if (value === '__unassigned__') {
                clearTenderAssignment(ref);
            } else if (value && value !== '') {
                setTenderAssignment(ref, value, 'In Progress');
            }
            requestRenderTenders();
        });
    }

    const star = row.querySelector('.watchlist-star');
    if (star) {
        star.addEventListener('click', (e) => {
            e.stopPropagation();
            const ref = star.getAttribute('data-ref') || t.ref;
            toggleWatchlist(ref);
            requestRenderTenders();
        });
    }
    return row;
}

/**
 * Create tender card element
 * @param {Object} item - Item with tender and classification
 * @param {number} _idx - Index
 * @returns {HTMLElement}
 */
export function createTenderCard(item, _idx) {
    const t = item.tender;
    const scores = t.scores || {};
    const title = t.title || '-';
    const source = t.source || '-';
    const company = getCompany(t) || '-';
    const priority = getPriority(t) || '-';
    const closeDate = t.closing_date || '-';
    const countdownStatus = t.status || getCountdownHtml(t.closing_date) || '-';
    const decision = computeDecision(t);
    const url = t.url || '';

    const card = document.createElement('div');
    card.className = 'tender-card';
    card.dataset.ref = (t.ref || '').toString();
    card.addEventListener('click', () => openTenderModal(t));

    const priorityBadge = `<span class="priority priority-${priority}">${priority}</span>`;
    const decisionPill = `<span class="decision-pill ${decision.className}">${decision.label}<span class="reason"> · ${decision.reason}</span><span class="confidence"> · ${decision.confidence}%</span></span>`;
    const categoryTags = (item.classification?.categories || []).map(c => `<span class="category-tag">${c}</span>`).join('');

    const starActive = isTenderWatchlisted(t.ref);
    const starBtn = `<button class="watchlist-star ${starActive ? 'active' : ''}" data-ref="${escapeHtml(t.ref || '')}" type="button" aria-label="Toggle watchlist">★</button>`;
    const openLink = url ? `<a class="tender-card-open" href="${url}" target="_blank" rel="noopener noreferrer" onclick="event.stopPropagation()">Open ↗</a>` : '';

    card.innerHTML = `
        <div class="tender-title-row" style="align-items: flex-start;">
            <div style="flex: 1; min-width: 0;">
                <div class="tender-card-title">${escapeHtml(title)}</div>
                <div class="tender-card-ref">${escapeHtml(t.ref || '-')}</div>
            </div>
            <div style="display:flex; flex-direction: column; gap: 8px; align-items: flex-end;">
                ${starBtn}
                ${priorityBadge}
            </div>
        </div>
        <div style="margin-top: 8px;">${categoryTags}</div>
        <div class="tender-card-meta">
            <span>${escapeHtml(source)}</span>
            <span>·</span>
            <span>${escapeHtml(company)}</span>
            <span>·</span>
            <span>Closes: ${escapeHtml(closeDate)}</span>
        </div>
        <div style="margin-top: 10px;">${countdownStatus}</div>
        <div style="margin-top: 10px;">${decisionPill}</div>
        <div class="tender-card-actions">
            <div style="color: var(--text-secondary); font-size: 0.85rem;">
                Fit <strong>${escapeHtml(String(scores.fit ?? t.score ?? '-'))}</strong>
            </div>
            <div style="display:flex; gap: 12px; align-items:center;">
                ${openLink}
            </div>
        </div>
    `;

    const star = card.querySelector('.watchlist-star');
    if (star) {
        star.addEventListener('click', (e) => {
            e.stopPropagation();
            const ref = star.getAttribute('data-ref') || t.ref;
            toggleWatchlist(ref);
            requestRenderTenders();
        });
    }

    return card;
}

/**
 * Render tender cards
 * @param {Array} classified - Classified tenders
 * @param {number} _totalCount - Total count
 */
export function renderTenderCards(classified, _totalCount) {
    const grid = document.getElementById('tenderCardGrid');
    if (!grid) return;
    grid.innerHTML = '';
    const items = Array.isArray(classified) ? classified : [];
    items.forEach((item, idx) => grid.appendChild(createTenderCard(item, idx)));
}

/**
 * Render virtual list
 * @param {Array} filteredItems - Filtered items
 */
export function renderVirtualList(filteredItems) {
    const items = Array.isArray(filteredItems) ? filteredItems : [];
    const container = getVirtualScrollContainer();
    const tbody = getVirtualScrollTbody();
    
    if (!container || !tbody) return;

    updateVisibleItems();
    const VISIBLE_ITEMS = getVisibleItemsCount();

    // Clamp scrollTop when list shrinks
    const maxScrollTop = Math.max(0, items.length * ITEM_HEIGHT - container.clientHeight);
    if (container.scrollTop > maxScrollTop) container.scrollTop = maxScrollTop;

    const scrollTop = container.scrollTop;
    const visibleStart = Math.floor(scrollTop / ITEM_HEIGHT);
    const startIndex = Math.max(0, visibleStart - BUFFER);
    const endIndex = Math.min(items.length, visibleStart + VISIBLE_ITEMS + BUFFER);
    const topSpacer = startIndex * ITEM_HEIGHT;
    const bottomSpacer = Math.max(0, (items.length - endIndex) * ITEM_HEIGHT);

    const key = `${items.length}:${startIndex}:${endIndex}:${topSpacer}:${bottomSpacer}`;
    if (key === getVirtualLastKey()) return;
    setVirtualLastKey(key);

    tbody.innerHTML = '';

    if (items.length === 0) {
        tbody.innerHTML =
            '<tr><td colspan="12" class="empty-state" style="text-align:center; padding: 40px;"><h3>No tenders found</h3><p>Try a different filter...</p></td></tr>';
        return;
    }

    if (topSpacer > 0) {
        const topRow = document.createElement('tr');
        topRow.className = 'virtual-spacer';
        topRow.style.height = `${topSpacer}px`;
        topRow.innerHTML = '<td colspan="12"></td>';
        tbody.appendChild(topRow);
    }

    const slice = items.slice(startIndex, endIndex);
    slice.forEach((item, idx) => {
        tbody.appendChild(createTenderRow(item, startIndex + idx));
    });

    if (bottomSpacer > 0) {
        const bottomRow = document.createElement('tr');
        bottomRow.className = 'virtual-spacer';
        bottomRow.style.height = `${bottomSpacer}px`;
        bottomRow.innerHTML = '<td colspan="12"></td>';
        tbody.appendChild(bottomRow);
    }
}

/**
 * Render tenders
 */
export function renderTenders() {
    const list = document.getElementById('tender-table-body') || document.getElementById('tenderList');
    if (!list) return;
    
    const filter = state.currentFilter;
    let filtered = state.tenders
        .filter((t) => !isTenderHidden(t?.ref))
        .filter((t) => getDaysUntil(t.closing_date) === null || getDaysUntil(t.closing_date) >= 0);

    if (filter === 'Mexel') {
        filtered = filtered.filter(t => getCompany(t) === filter);
    } else if (filter === 'HIGH' || filter === 'MEDIUM' || filter === 'LOW') {
        filtered = filtered.filter(t => getPriority(t) === filter);
    } else if (filter === 'WATCHLIST') {
        const list = getActiveWatchlist();
        const userFilter = (state.watchlistAddedBy || '').toString().trim();
        const selected = userFilter ? list.filter((e) => e.addedBy === userFilter) : list;
        const refs = new Set(selected.map((e) => e.tender_ref));
        filtered = filtered.filter((t) => refs.has((t?.ref || '').toString().trim()));
    } else if (filter === 'ACTIVE_BIDS') {
        filtered = filtered.filter((t) => {
            const s = getTenderCurrentStatus(t.ref);
            return s === 'In Progress' || s === 'Awaiting Review';
        });
    } else if (filter === 'COMPLETED') {
        filtered = filtered.filter((t) => {
            const s = getTenderCurrentStatus(t.ref);
            return s === 'Won' || s === 'Lost';
        });
    } else if (filter === 'ASSIGNED_TO_ME') {
        const user = getCurrentUsername();
        filtered = user ? filtered.filter((t) => getTenderAssignment(t.ref)?.assignedTo === user) : [];
    } else if (filter === 'UNASSIGNED') {
        filtered = filtered.filter((t) => !getTenderAssignment(t.ref));
    }

    // Apply advanced filters (intersection)
    if (window.advancedFilters && typeof window.advancedFilters.applyFilters === 'function') {
        filtered = window.advancedFilters.applyFilters(filtered);
    }

    // Apply smart search (intersection)
    if (state.searchQuery && typeof smartSearchTenders === 'function') {
        filtered = smartSearchTenders(state.searchQuery, filtered);
    }

    // Sort by closing date (urgent first)
    filtered.sort((a, b) => {
        const daysA = getDaysUntil(a.closing_date) ?? 999;
        const daysB = getDaysUntil(b.closing_date) ?? 999;
        return daysA - daysB;
    });

    const hideOut = document.getElementById('hide-out-of-scope');
    const hideOutOfScope = hideOut && hideOut.checked;

    const classifiedAll = filtered
        .map(t => ({ tender: t, classification: classifyTender(t) }))
        .filter(item => !(hideOutOfScope && item.classification.relevance === 'OutOfScope'));

    state.totalMatchingCount = classifiedAll.length;
    const visibleCount = Math.min(state.visibleTenderCount || CHUNK_SIZE, classifiedAll.length);
    const classified = classifiedAll.slice(0, visibleCount);

    const countEl = document.getElementById('tenderResultsCount');
    if (countEl) {
        const q = (state.searchQuery || '').trim();
        const suffix = q ? ` (query: "${q}")` : '';
        const totalSnapshot = state.tenders.length;
        const totalSuffix = totalSnapshot !== classifiedAll.length ? ` active (of ${totalSnapshot} total)` : '';
        countEl.textContent = `Showing ${classified.length} of ${classifiedAll.length}${totalSuffix}${suffix}`;
    }

    updateWatchlistBadges();
    updateWatchlistToolbar();
    updateTenderLoadProgress(classified.length, classifiedAll.length);

    state.currentTenders = classified.map(item => item.tender);
    window.__virtualListItems = classified;
    setVirtualScrollContainer(document.getElementById('tenderTableScroll'));
    setVirtualScrollTbody(list);
    setVirtualLastKey('');
    
    if (state.viewMode === 'card' && !state.forceFullRender) {
        renderTenderCards(classified, classifiedAll.length);
        return;
    }

    if (getVirtualScrollContainer() && !state.forceFullRender) {
        renderVirtualList(classified);
    } else {
        list.innerHTML = '';
        classified.forEach((item, idx) => list.appendChild(createTenderRow(item, idx)));
    }
}

/**
 * Request render tenders (debounced)
 */
export function requestRenderTenders() {
    if (typeof debouncedRenderTenders === 'function') debouncedRenderTenders();
    else renderTenders();
}
