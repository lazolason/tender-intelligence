/**
 * Tender Intelligence Dashboard - Main Entry Point
 * Modularized version of the original script.js
 */

// Import all modules
import { state } from './modules/config.js';
import { initThemeToggle, initPwaInstallPrompt, initMobileGestures, initViewToggle, showTab, initUI } from './modules/ui.js';
import { loadTenderPayload, applyTenderPayload, refreshDashboardData } from './modules/data.js';
import { getCompany, getPriority, classifyTender, computeDecision, getDaysUntil, getCountdownHtml, getFilteredTendersForExport, normalizeAttachments, getAttachmentIcon, resetTenderInfiniteList, updateTenderLoadProgress, showTenderSkeleton } from './modules/tender.js';
import { renderTenders, requestRenderTenders, renderVirtualList, createTenderRow, createTenderCard, renderTenderCards } from './modules/render.js';
import { openTenderModal, closeTenderModal, setTenderDetailTab } from './modules/modal.js';
import { TenderAnalytics, renderTrendChart, renderSourcePieChart, renderPriorityBarChart, renderKeywordCloud, initializeAnalytics } from './modules/analytics.js';
import { getTenderAssignment, setTenderAssignment, updateTenderAssignmentStatus, clearTenderAssignment, getTenderCurrentStatus, setTenderLifecycleStatus, getTenderStatusHistory, addTenderStatusHistory, getTenderComments, saveTenderComments, getCurrentUsername, ensureUsername, getWatchlistMode, setWatchlistMode, getActiveWatchlist, setActiveWatchlist, getHiddenTenderRefs, setHiddenTenderRefs, isTenderHidden, hideTender, unhideTender, isTenderWatchlisted, toggleWatchlist, addAllHighPriorityToWatchlist, exportWatchlistCsv, updateWatchlistBadges, updateWatchlistToolbar, getCommentsKey, getMentionsKey, getMentionsStore, addMentionsForUsers, getUnreadMentionCount, clearMentionsForTender, getTenderStatusHistoryKey, getAssignmentKey } from './modules/storage.js';
import { delay, debounce, throttle, escapeHtml, formatBytes, newId, initials, hashColorForUser, relativeTime, parseFlexibleDate, formatNiceDateTime, formatNumberOrDash, setTextOrDash, setNumberOrDash, setTextById, renderMarkdownLite } from './utils/helpers.js';
import { computeDashboardMetrics, updateDashboardStatsUI, renderDashboardSourceHealth, renderAutomationLogs, updateFooter } from './modules/metrics.js';

// Export functions for global access (backward compatibility)
window.getCompany = getCompany;
window.getPriority = getPriority;
window.classifyTender = classifyTender;
window.computeDecision = computeDecision;
window.getDaysUntil = getDaysUntil;
window.getCountdownHtml = getCountdownHtml;
window.getFilteredTendersForExport = getFilteredTendersForExport;
window.normalizeAttachments = normalizeAttachments;
window.getAttachmentIcon = getAttachmentIcon;
window.resetTenderInfiniteList = resetTenderInfiniteList;
window.updateTenderLoadProgress = updateTenderLoadProgress;
window.showTenderSkeleton = showTenderSkeleton;
window.renderTenders = renderTenders;
window.requestRenderTenders = requestRenderTenders;
window.renderVirtualList = renderVirtualList;
window.createTenderRow = createTenderRow;
window.createTenderCard = createTenderCard;
window.renderTenderCards = renderTenderCards;
window.openTenderModal = openTenderModal;
window.closeTenderModal = closeTenderModal;
window.setTenderDetailTab = setTenderDetailTab;
window.TenderAnalytics = TenderAnalytics;
window.renderTrendChart = renderTrendChart;
window.renderSourcePieChart = renderSourcePieChart;
window.renderPriorityBarChart = renderPriorityBarChart;
window.renderKeywordCloud = renderKeywordCloud;
window.initializeAnalytics = initializeAnalytics;
window.getTenderAssignment = getTenderAssignment;
window.setTenderAssignment = setTenderAssignment;
window.updateTenderAssignmentStatus = updateTenderAssignmentStatus;
window.clearTenderAssignment = clearTenderAssignment;
window.getTenderCurrentStatus = getTenderCurrentStatus;
window.setTenderLifecycleStatus = setTenderLifecycleStatus;
window.getTenderStatusHistory = getTenderStatusHistory;
window.addTenderStatusHistory = addTenderStatusHistory;
window.getTenderComments = getTenderComments;
window.saveTenderComments = saveTenderComments;
window.getCurrentUsername = getCurrentUsername;
window.ensureUsername = ensureUsername;
window.getWatchlistMode = getWatchlistMode;
window.setWatchlistMode = setWatchlistMode;
window.getActiveWatchlist = getActiveWatchlist;
window.setActiveWatchlist = setActiveWatchlist;
window.getHiddenTenderRefs = getHiddenTenderRefs;
window.setHiddenTenderRefs = setHiddenTenderRefs;
window.isTenderHidden = isTenderHidden;
window.hideTender = hideTender;
window.unhideTender = unhideTender;
window.isTenderWatchlisted = isTenderWatchlisted;
window.toggleWatchlist = toggleWatchlist;
window.addAllHighPriorityToWatchlist = addAllHighPriorityToWatchlist;
window.exportWatchlistCsv = exportWatchlistCsv;
window.updateWatchlistBadges = updateWatchlistBadges;
window.updateWatchlistToolbar = updateWatchlistToolbar;
window.getCommentsKey = getCommentsKey;
window.getMentionsKey = getMentionsKey;
window.getMentionsStore = getMentionsStore;
window.addMentionsForUsers = addMentionsForUsers;
window.getUnreadMentionCount = getUnreadMentionCount;
window.clearMentionsForTender = clearMentionsForTender;
window.getTenderStatusHistoryKey = getTenderStatusHistoryKey;
window.getAssignmentKey = getAssignmentKey;
window.delay = delay;
window.debounce = debounce;
window.throttle = throttle;
window.escapeHtml = escapeHtml;
window.formatBytes = formatBytes;
window.newId = newId;
window.initials = initials;
window.hashColorForUser = hashColorForUser;
window.relativeTime = relativeTime;
window.parseFlexibleDate = parseFlexibleDate;
window.formatNiceDateTime = formatNiceDateTime;
window.formatNumberOrDash = formatNumberOrDash;
window.setTextOrDash = setTextOrDash;
window.setNumberOrDash = setNumberOrDash;
window.setTextById = setTextById;
window.renderMarkdownLite = renderMarkdownLite;
window.computeDashboardMetrics = computeDashboardMetrics;
window.updateDashboardStatsUI = updateDashboardStatsUI;
window.renderDashboardSourceHealth = renderDashboardSourceHealth;
window.renderAutomationLogs = renderAutomationLogs;
window.updateFooter = updateFooter;
window.showTab = showTab;
window.refreshDashboardData = refreshDashboardData;
window.loadTenderPayload = loadTenderPayload;
window.applyTenderPayload = applyTenderPayload;
window.state = state;

// Export functions for external use
window.exportToCSV = function() {
    const filteredTenders = getFilteredTendersForExport();
    const headers = ['Reference', 'Title', 'Client', 'Priority', 'Score', 'Closing Date', 'URL'];
    const rows = filteredTenders.map((t) => {
        const scores = t.scores || {};
        const score = scores.composite ?? scores.composite_score ?? scores.fit ?? t.score ?? '';
        return [
            t.ref || '',
            t.title || '',
            t.client || '',
            getPriority(t) || '',
            score,
            t.closing_date || '',
            t.url || ''
        ];
    });

    const escapeCell = (cell) => `"${String(cell ?? '').replace(/"/g, '""')}"`;
    let csv = headers.join(',') + '\n';
    rows.forEach((row) => {
        csv += row.map(escapeCell).join(',') + '\n';
    });

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `tenders_${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
};

window.exportToExcel = function() {
    const filteredTenders = getFilteredTendersForExport();
    if (!window.XLSX) {
        alert('Excel export requires SheetJS (XLSX).');
        return;
    }

    const data = filteredTenders.map((t) => {
        const scores = t.scores || {};
        const score = scores.composite ?? scores.composite_score ?? scores.fit ?? t.score ?? '';
        return {
            'Reference': t.ref || '',
            'Title': t.title || '',
            'Client': t.client || '',
            'Priority': getPriority(t) || '',
            'Score': score,
            'Category': getCompany(t) || '',
            'Source': t.source || '',
            'Closing Date': t.closing_date || '',
            'URL': t.url || ''
        };
    });

    const ws = window.XLSX.utils.json_to_sheet(data);
    const wb = window.XLSX.utils.book_new();
    window.XLSX.utils.book_append_sheet(wb, ws, 'Tenders');
    const filename = `tenders_${new Date().toISOString().split('T')[0]}.xlsx`;
    window.XLSX.writeFile(wb, filename);
};

window.exportToPDF = function() {
    const filteredTenders = getFilteredTendersForExport();
    const jspdf = window.jspdf;
    if (!jspdf || !jspdf.jsPDF) {
        alert('PDF export requires jsPDF.');
        return;
    }

    const doc = new jspdf.jsPDF({ unit: 'pt', format: 'a4' });
    const pageWidth = doc.internal.pageSize.getWidth();
    const marginX = 40;
    let y = 50;

    doc.setFontSize(18);
    doc.text('Tender Intelligence Report', marginX, y);
    y += 18;
    doc.setFontSize(10);
    doc.text(`Generated: ${new Date().toLocaleString()}`, marginX, y);
    y += 20;

    const maxTitle = 80;
    const rows = filteredTenders.slice(0, 60);
    rows.forEach((t) => {
        const line = `${t.ref || 'NA'}: ${(t.title || '').substring(0, maxTitle)}${(t.title || '').length > maxTitle ? '…' : ''}`;
        if (y > 780) {
            doc.addPage();
            y = 50;
        }
        doc.text(line, marginX, y, { maxWidth: pageWidth - marginX * 2 });
        y += 14;
    });

    doc.save(`tenders_${new Date().toISOString().split('T')[0]}.pdf`);
};

window.printTenders = function() {
    const options = {
        includeFiltered: true,
        includeAllTabs: false,
        colorMode: 'grayscale',
    };

    try {
        if (options.includeAllTabs === false && typeof showTab === 'function') {
            showTab('dashboard');
        }
    } catch (e) {}

    const prev = {
        viewMode: state.viewMode,
        visibleTenderCount: state.visibleTenderCount,
        forceFullRender: state.forceFullRender,
        scrollTop: (document.getElementById('tenderTableScroll') || {}).scrollTop,
    };

    state.forceFullRender = true;
    const oldViewMode = state.viewMode;
    state.viewMode = 'detailed';

    try {
        const all = getFilteredTendersForExport();
        state.visibleTenderCount = all.length;
        renderTenders();
    } catch (e) {}

    const restore = () => {
        window.removeEventListener('afterprint', restore);
        state.forceFullRender = prev.forceFullRender;
        state.visibleTenderCount = prev.visibleTenderCount;
        state.viewMode = oldViewMode;
        renderTenders();
        const container = document.getElementById('tenderTableScroll');
        if (container && typeof prev.scrollTop === 'number') container.scrollTop = prev.scrollTop;
    };

    window.addEventListener('afterprint', restore);
    setTimeout(() => window.print(), 60);
};

window.filterTenders = function(filter) {
    if (filter === 'ASSIGNED_TO_ME') {
        const user = ensureUsername();
        if (!user) return;
    }

    state.currentFilter = filter;
    resetTenderInfiniteList();
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.textContent.toLowerCase().includes(filter.toLowerCase()) ||
            (filter === 'all' && tab.textContent.includes('All')) ||
            (filter === 'HIGH' && tab.textContent.includes('Urgent')) ||
            (filter === 'WATCHLIST' && tab.textContent.includes('Watchlist')) ||
            (filter === 'ACTIVE_BIDS' && tab.textContent.includes('Active Bids')) ||
            (filter === 'COMPLETED' && tab.textContent.includes('Completed')) ||
            (filter === 'ASSIGNED_TO_ME' && tab.textContent.includes('Assigned to Me')) ||
            (filter === 'UNASSIGNED' && tab.textContent.includes('Unassigned'))) {
            tab.classList.add('active');
        }
    });
    updateWatchlistToolbar();
    requestRenderTenders();
};

window.smartSearchTenders = function(query, tenders) {
    // When called from UI (no `tenders` passed), update state + rerender.
    if (typeof tenders === 'undefined') {
        state.searchQuery = (query || '').toString().trim();
        resetTenderInfiniteList();
        renderTenders();
        return;
    }

    const list = Array.isArray(tenders) ? tenders : state.tenders;
    const q = (query || '').toString().trim().toLowerCase();
    if (!q) return list;

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    const patterns = {
        closesToday: /\b(today|closes today)\b/i,
        nextWeek: /\bnext week\b/i,
        thisWeek: /\bthis week\b|\bweek\b/i,
        urgent: /\burgent\b|\bhigh priority\b/i,
        companyMexel: /\b(mexel|tes)\b/i,
    };

    const sourceKeywords = [
        'eskom',
        'transnet',
        'sanral',
        'treasury',
        'national treasury',
        'rand water',
        'johannesburg water',
        'umgeni',
    ];

    const matchedSources = sourceKeywords.filter((kw) => q.includes(kw));
    const matchCompany = patterns.companyMexel.test(q) ? 'Mexel' : null;

    const hasSmartMatch =
        patterns.closesToday.test(q) ||
        patterns.nextWeek.test(q) ||
        patterns.thisWeek.test(q) ||
        patterns.urgent.test(q) ||
        matchedSources.length > 0 ||
        Boolean(matchCompany);

    const getClosingDays = (t) => getDaysUntil(t?.closing_date);

    if (hasSmartMatch) {
        return list.filter((t) => {
            if (!t) return false;

            // "today" / "closes today"
            if (patterns.closesToday.test(q)) {
                const days = getClosingDays(t);
                if (days !== 0) return false;
            }

            // "next week" -> 7-14 days
            if (patterns.nextWeek.test(q)) {
                const days = getClosingDays(t);
                if (days === null || days < 7 || days > 14) return false;
            } else if (patterns.thisWeek.test(q)) {
                // "this week" / "week" -> next 7 days
                const days = getClosingDays(t);
                if (days === null || days < 0 || days > 7) return false;
            }

            // "urgent" / "high priority"
            if (patterns.urgent.test(q)) {
                if (getPriority(t) !== 'HIGH') return false;
            }

            // Source keywords
            if (matchedSources.length > 0) {
                const src = (t.source || '').toLowerCase();
                const ok = matchedSources.some((kw) => src.includes(kw));
                if (!ok) return false;
            }

            // Company keywords
            if (matchCompany) {
                if (getCompany(t) !== matchCompany) return false;
            }

            return true;
        });
    }

    // Standard text search across fields
    return list.filter((t) => {
        const haystack = [
            t?.ref,
            t?.title,
            t?.description,
            t?.source,
            t?.client,
            t?.category,
        ]
            .map((v) => (v || '').toString().toLowerCase())
            .join(' ');
        return haystack.includes(q);
    });
};

window.searchTenders = function() {
    const box = document.getElementById('tenderSearchBox');
    smartSearchTenders(box ? box.value : '');
};

// Calendar functions
window.renderCalendar = function() {
    const grid = document.getElementById('calendarGrid');
    const monthLabel = document.getElementById('calendarMonth');

    const year = state.currentMonth.getFullYear();
    const month = state.currentMonth.getMonth();

    monthLabel.textContent = state.currentMonth.toLocaleDateString('en-ZA', { month: 'long', year: 'numeric' });

    const firstDay = new Date(year, month, 1);
    const lastDay = new Date(year, month + 1, 0);
    const startDay = firstDay.getDay();
    const daysInMonth = lastDay.getDate();

    const tendersByDate = {};
    state.tenders.forEach(t => {
        if (t.closing_date) {
            const date = t.closing_date;
            if (!tendersByDate[date]) tendersByDate[date] = [];
            tendersByDate[date].push(t);
        }
    });

    let html = '';
    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = 0; i < startDay; i++) {
        const day = new Date(year, month, -(startDay - i - 1));
        html += `<div class="calendar-day other-month">${day.getDate()}</div>`;
    }

    for (let day = 1; day <= daysInMonth; day++) {
        const date = new Date(year, month, day);
        const dateStr = date.toISOString().split('T')[0];
        const isToday = date.getTime() === today.getTime();
        const tendersOnDay = tendersByDate[dateStr] || [];
        const hasTenders = tendersOnDay.length > 0;

        html += `<div class="calendar-day ${isToday ? 'today' : ''} ${hasTenders ? 'has-tenders' : ''}" 
                    onclick="showDayTenders('${dateStr}')" title="${tendersOnDay.length} tender(s)">
                    ${day}
                    ${hasTenders ? `<span class="tender-count">${tendersOnDay.length}</span>` : ''}
                </div>`;
    }

    grid.innerHTML = html;
};

window.showDayTenders = function(dateStr) {
    const container = document.getElementById('dayTenders');
    const dayTenders = state.tenders.filter(t => t.closing_date === dateStr);

    if (dayTenders.length === 0) {
        container.innerHTML = `<p style="color: #888; text-align: center;">No tenders closing on ${dateStr}</p>`;
        return;
    }

    container.innerHTML = `
        <h3 style="margin-bottom: 15px;">📅 Closing on ${new Date(dateStr).toLocaleDateString('en-ZA', { weekday: 'long', day: 'numeric', month: 'long' })}</h3>
        ${dayTenders.map(t => `
            <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin: 10px 0; cursor: pointer;" onclick="window.open('${t.url}', '_blank')">
                <span style="color: #667eea; font-weight: bold;">${t.ref}</span>
                <span class="company-badge company-${getCompany(t)}" style="margin-left: 10px;">${getCompany(t)}</span>
                <div style="color: #ccc; margin-top: 5px;">${t.title}</div>
                <div style="color: #888; font-size: 0.8rem; margin-top: 5px;">📍 ${t.client}</div>
            </div>
        `).join('')}
    `;
};

window.changeMonth = function(delta) {
    state.currentMonth.setMonth(state.currentMonth.getMonth() + delta);
    renderCalendar();
};

// Scraper health
window.renderScraperHealth = function(scraperData) {
    const container = document.getElementById('scraper-health-cards');
    if (!container) return;

    const data = scraperData || (typeof globalData !== 'undefined' ? globalData.scraperHealth : {}) || {};
    const entries = Object.entries(data);
    if (entries.length === 0) {
        container.innerHTML = '<div class="company-card" style="text-align:center; color:#888;">No scraper health data available</div>';
        return;
    }

    container.innerHTML = entries.map(([name, info]) => {
        const status = info?.status || '-';
        const lastRun = info?.lastRun || '-';
        const count = info?.count ?? '-';
        const error = info?.error;
        const statusColor = status === 'Success' ? '#00ff88' : status === 'Partial' ? '#feca57' : '#ff6b6b';
        const shadow = status === 'Success' ? '0 0 12px rgba(0,255,136,0.3)' : status === 'Partial' ? '0 0 12px rgba(254,202,87,0.3)' : '0 0 12px rgba(255,107,107,0.3)';
        return `
            <div class="company-card" style="background: rgba(255,255,255,0.04); border: 1px solid rgba(255,255,255,0.08); border-radius: 16px; padding: 20px; box-shadow:${shadow}; transition: transform 0.2s, box-shadow 0.2s;" onmouseover="this.style.transform='translateY(-3px)';" onmouseout="this.style.transform='none';">
                <div class="company-name" style="color: #fff;">${name}</div>
                <div class="company-focus" style="color:${statusColor}; font-weight:700;">${status}</div>
                <div class="company-keywords" style="margin-top:12px;">
                    <span class="keyword">Last run: ${lastRun}</span>
                    <span class="keyword">Tenders: ${count}</span>
                </div>
                ${status === 'Failed' && error ? `<div style="margin-top:12px; color:#ff6b6b; font-size:0.85rem;">${error}</div>` : ''}
            </div>
        `;
    }).join('');
};

// Advanced filters integration
window.toggleAdvancedFilters = function() {
    const panel = document.getElementById('advancedFiltersPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        
        // Initialize filters if first time opening
        if (panel.style.display === 'block' && !window.advancedFiltersInstance) {
            initializeAdvancedFilters();
        }
    }
};

window.initializeAdvancedFilters = function() {
    if (!window.AdvancedFilters) return;
    
    window.advancedFiltersInstance = new window.AdvancedFilters();
    window.advancedFiltersInstance.setTenders(state.currentTenders.map((t, idx) => ({
        tender: t,
        classification: classifyTender(t)
    })));
    
    // Set up callback for filter changes
    window.advancedFiltersInstance.onFilterChange = (filteredTenders) => {
        renderFilteredTenders(filteredTenders);
        updateActiveFilterCount();
    };
    
    // Set up event listeners
    const searchBox = document.getElementById('advancedSearchBox');
    if (searchBox) {
        searchBox.addEventListener('input', (e) => {
            if (window.SmartSearch && e.target.value.trim()) {
                const smartFiltered = window.SmartSearch.applySmartFilters(
                    window.advancedFiltersInstance.allTenders,
                    e.target.value
                );
                renderFilteredTenders(smartFiltered);
            } else {
                window.advancedFiltersInstance.setSearchTerm(e.target.value);
            }
        });
    }
    
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    if (dateStart && dateEnd) {
        dateStart.addEventListener('change', () => {
            window.advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
        });
        dateEnd.addEventListener('change', () => {
            window.advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
        });
    }
    
    // Load saved searches into dropdown
    const savedSelect = document.getElementById('savedSearchSelect');
    if (savedSelect) {
        updateSavedSearchesDropdown();
        savedSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                window.advancedFiltersInstance.loadSearch(e.target.value);
                renderFilteredTenders(window.advancedFiltersInstance.getFilteredTenders());
                updateActiveFilterCount();
            }
        });
    }
};

window.setQuickDateFilter = function(type) {
    const today = new Date();
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    
    if (!dateStart || !dateEnd) return;
    
    switch(type) {
        case 'thisWeek':
            const endOfWeek = new Date(today);
            endOfWeek.setDate(today.getDate() + (7 - today.getDay()));
            dateStart.value = today.toISOString().split('T')[0];
            dateEnd.value = endOfWeek.toISOString().split('T')[0];
            break;
        case 'nextWeek':
            const nextWeekStart = new Date(today);
            nextWeekStart.setDate(today.getDate() + (7 - today.getDay()) + 1);
            const nextWeekEnd = new Date(nextWeekStart);
            nextWeekEnd.setDate(nextWeekStart.getDate() + 6);
            dateStart.value = nextWeekStart.toISOString().split('T')[0];
            dateEnd.value = nextWeekEnd.toISOString().split('T')[0];
            break;
        case 'thisMonth':
            const endOfMonth = new Date(today.getFullYear(), today.getMonth() + 1, 0);
            dateStart.value = today.toISOString().split('T')[0];
            dateEnd.value = endOfMonth.toISOString().split('T')[0];
            break;
    }
    
    if (window.advancedFiltersInstance) {
        window.advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
    }
};

window.saveCurrentSearch = function() {
    if (!window.advancedFiltersInstance) return;
    
    const name = prompt('Enter a name for this search:');
    if (name) {
        window.advancedFiltersInstance.saveSearch(name);
        updateSavedSearchesDropdown();
        alert('Search saved successfully!');
    }
};

window.deleteSavedSearch = function() {
    const savedSelect = document.getElementById('savedSearchSelect');
    if (!savedSelect || !savedSelect.value) {
        alert('Please select a saved search to delete');
        return;
    }
    
    if (confirm(`Delete saved search "${savedSelect.value}"?`)) {
        window.advancedFiltersInstance.deleteSavedSearch(savedSelect.value);
        updateSavedSearchesDropdown();
        savedSelect.value = '';
    }
};

window.updateSavedSearchesDropdown = function() {
    const savedSelect = document.getElementById('savedSearchSelect');
    if (!savedSelect || !window.advancedFiltersInstance) return;
    
    const searches = window.advancedFiltersInstance.activeFilters.savedSearches;
    savedSelect.innerHTML = '<option value="">-- Select Saved Search --</option>';
    
    searches.forEach(search => {
        const option = document.createElement('option');
        option.value = search.name;
        option.textContent = search.name;
        savedSelect.appendChild(option);
    });
};

window.clearAllAdvancedFilters = function() {
    if (!window.advancedFiltersInstance) return;
    
    window.advancedFiltersInstance.clearAllFilters();
    
    // Clear UI elements
    const searchBox = document.getElementById('advancedSearchBox');
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    const savedSelect = document.getElementById('savedSearchSelect');
    
    if (searchBox) searchBox.value = '';
    if (dateStart) dateStart.value = '';
    if (dateEnd) dateEnd.value = '';
    if (savedSelect) savedSelect.value = '';
    
    requestRenderTenders();
    updateActiveFilterCount();
};

window.updateActiveFilterCount = function() {
    const countDiv = document.getElementById('activeFilterCount');
    if (!countDiv || !window.advancedFiltersInstance) return;
    
    const count = window.advancedFiltersInstance.getActiveFilterCount();
    countDiv.textContent = count === 0 ? 'No filters active' : `${count} filter${count > 1 ? 's' : ''} active`;
};

window.renderFilteredTenders = function(filteredTenders) {
    const list = document.getElementById('tender-table-body') || document.getElementById('tenderList');
    if (!list) return;

    const raw = Array.isArray(filteredTenders) ? filteredTenders : [];
    const all = raw.map((t) => (t && typeof t === 'object' && 'tender' in t) ? t : ({ tender: t, classification: classifyTender(t) }));
    const notHidden = all.filter((item) => !isTenderHidden(item?.tender?.ref));
    const allItems = notHidden;
    state.totalMatchingCount = allItems.length;
    const visibleCount = Math.min(state.visibleTenderCount || CHUNK_SIZE, allItems.length);
    window.__virtualListItems = allItems.slice(0, visibleCount);
    
    const countEl = document.getElementById('tenderResultsCount');
    if (countEl) {
        const totalSnapshot = state.tenders.length;
        const totalSuffix = totalSnapshot !== allItems.length ? ` (of ${totalSnapshot} total)` : '';
        countEl.textContent = `Showing ${window.__virtualListItems.length} of ${allItems.length}${totalSuffix}`;
    }

    if (state.viewMode === 'card' && !state.forceFullRender) {
        renderTenderCards(window.__virtualListItems, all.length);
        return;
    }

    const container = document.getElementById('tenderTableScroll');
    const tbody = list;
    if (container && !state.forceFullRender) {
        renderVirtualList(window.__virtualListItems);
    } else {
        list.innerHTML = '';
        window.__virtualListItems.forEach((item, idx) => list.appendChild(createTenderRow(item, idx)));
    }
};

// Load more tenders
window.loadMoreTenders = function() {
    if (state.loadingMore) return;
    if (state.visibleTenderCount >= state.totalMatchingCount) return;
    state.loadingMore = true;
    updateTenderLoadProgress(state.visibleTenderCount, state.totalMatchingCount);
    delay(100).then(() => {
        state.visibleTenderCount = Math.min(state.totalMatchingCount, state.visibleTenderCount + CHUNK_SIZE);
        state.loadingMore = false;
        renderTenders();
    });
};

// Swipe actions (mobile)
window.handleTenderSwipeLeft = function(target) {
    const el = getSwipeableTenderElement(target);
    if (!el) return false;
    const ref = getRefFromSwipeableElement(el);
    if (!ref) return false;
    // Toggle: if open for same element, close.
    if (window.swipeMenuTargetEl === el && window.swipeMenuEl?.classList.contains('active')) {
        closeSwipeMenu();
        return true;
    }
    showSwipeMenuForElement(el, ref);
    return true;
};

window.handleTenderSwipeRight = function(target) {
    const el = getSwipeableTenderElement(target);
    if (!el) return false;
    if (window.swipeMenuEl?.classList.contains('active')) {
        closeSwipeMenu();
        return true;
    }
    return false;
};

window.getSwipeableTenderElement = function(target) {
    const el = target instanceof Element ? target : null;
    if (!el) return null;
    return el.closest('.tender-row, .tender-card');
};

window.getRefFromSwipeableElement = function(el) {
    if (!el) return null;
    const ref = (el.dataset?.ref || '').toString().trim();
    if (ref) return ref;
    const fromStar = el.querySelector?.('.watchlist-star')?.getAttribute?.('data-ref');
    if (fromStar) return fromStar;
    const fromAssign = el.querySelector?.('.assignment-select')?.getAttribute?.('data-ref');
    if (fromAssign) return fromAssign;
    return null;
};

window.showSwipeMenuForElement = function(el, ref) {
    const menu = ensureSwipeMenu();
    window.swipeMenuTargetEl = el;
    window.swipeMenuRef = (ref || '').toString().trim() || null;
    if (!window.swipeMenuRef) return false;

    // Highlight
    el.classList.add('swiped-left');

    const rect = el.getBoundingClientRect();
    const menuRect = { w: 240, h: 88 };
    const margin = 10;
    const left = Math.max(margin, Math.min(window.innerWidth - menuRect.w - margin, rect.right - menuRect.w));
    const top = Math.max(margin, Math.min(window.innerHeight - menuRect.h - margin, rect.top + rect.height / 2 - menuRect.h / 2));

    menu.style.left = `${left}px`;
    menu.style.top = `${top}px`;
    menu.classList.add('active');
    return true;
};

window.closeSwipeMenu = function() {
    if (window.swipeMenuTargetEl) window.swipeMenuTargetEl.classList.remove('swiped-left');
    window.swipeMenuTargetEl = null;
    window.swipeMenuRef = null;
    if (window.swipeMenuEl) window.swipeMenuEl.classList.remove('active');
};

window.ensureSwipeMenu = function() {
    if (window.swipeMenuEl) return window.swipeMenuEl;
    window.swipeMenuEl = document.createElement('div');
    window.swipeMenuEl.id = 'swipeActionMenu';
    window.swipeMenuEl.className = 'swipe-action-menu';
    window.swipeMenuEl.innerHTML = `
        <div class="swipe-action-title">Tender actions</div>
        <div class="swipe-action-buttons">
            <button type="button" class="swipe-action-btn archive">Archive</button>
            <button type="button" class="swipe-action-btn delete">Delete</button>
        </div>
    `;
    document.body.appendChild(window.swipeMenuEl);

    // Outside click closes
    document.addEventListener('click', (e) => {
        if (!window.swipeMenuEl?.classList.contains('active')) return;
        if (e.target === window.swipeMenuEl || window.swipeMenuEl.contains(e.target)) return;
        closeSwipeMenu();
    });

    window.swipeMenuEl.querySelector('.swipe-action-btn.archive')?.addEventListener('click', (e) => {
        e.preventDefault();
        if (!window.swipeMenuRef) return;
        setTenderLifecycleStatus(window.swipeMenuRef, 'Withdrawn', {
            notes: 'Archived (swipe)',
            changedBy: getCurrentUsername() || 'Unknown',
        });
        closeSwipeMenu();
        requestRenderTenders();
    });

    window.swipeMenuEl.querySelector('.swipe-action-btn.delete')?.addEventListener('click', (e) => {
        e.preventDefault();
        if (!window.swipeMenuRef) return;
        hideTender(window.swipeMenuRef);
        window.lastHiddenRef = window.swipeMenuRef;
        closeSwipeMenu();
        requestRenderTenders();
        showUndoToast(window.lastHiddenRef);
    });

    return window.swipeMenuEl;
};

window.showUndoToast = function(ref) {
    const toast = ensureUndoToast();
    const text = toast.querySelector('#undoToastText');
    if (text) text.textContent = `Tender hidden: ${ref}`;
    toast.classList.add('active');
    if (window.undoTimer) clearTimeout(window.undoTimer);
    window.undoTimer = setTimeout(() => hideUndoToast(), 6000);
};

window.hideUndoToast = function() {
    if (window.undoTimer) {
        clearTimeout(window.undoTimer);
        window.undoTimer = null;
    }
    if (window.undoToastEl) window.undoToastEl.classList.remove('active');
};

window.ensureUndoToast = function() {
    if (window.undoToastEl) return window.undoToastEl;
    window.undoToastEl = document.createElement('div');
    window.undoToastEl.id = 'undoToast';
    window.undoToastEl.className = 'undo-toast';
    window.undoToastEl.innerHTML = `
        <span id="undoToastText">Tender hidden</span>
        <button type="button" id="undoToastBtn">Undo</button>
    `;
    document.body.appendChild(window.undoToastEl);
    window.undoToastEl.querySelector('#undoToastBtn')?.addEventListener('click', () => {
        if (!window.lastHiddenRef) return;
        unhideTender(window.lastHiddenRef);
        window.lastHiddenRef = null;
        hideUndoToast();
        requestRenderTenders();
    });
    return window.undoToastEl;
};

// Offline indicator
window.updateOfflineIndicator = function() {
    const pill = document.getElementById('offlinePill');
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    if (pill) pill.classList.toggle('hidden', !offline);

    const banner = document.getElementById('offlineIndicator');
    if (banner) banner.style.display = offline ? 'block' : 'none';
};

// Can install app
window.canInstallApp = async function() {
    const details = {};
    const reasons = [];

    const ua = (navigator.userAgent || '').toLowerCase();
    const isIOS = /iphone|ipad|ipod/.test(ua);
    const isStandalone =
        (typeof window.matchMedia === 'function' && window.matchMedia('(display-mode: standalone)').matches) ||
        window.navigator.standalone === true;

    details.isSecureContext = Boolean(window.isSecureContext);
    details.isStandalone = Boolean(isStandalone);
    details.isIOS = Boolean(isIOS);
    details.hasServiceWorker = 'serviceWorker' in navigator;
    details.hasManifestLink = Boolean(document.querySelector('link[rel="manifest"]'));
    details.manifestHref = document.querySelector('link[rel="manifest"]')?.href || null;
    details.hasDeferredPrompt = Boolean(window.__pwaInstall?.deferredPrompt);
    details.lastBeforeInstallPromptAt = window.__pwaInstall?.lastBeforeInstallPromptAt || null;
    details.lastInstallOutcome = window.__pwaInstall?.lastOutcome || null;

    if (!details.isSecureContext) reasons.push('not-secure-context');
    if (!details.hasManifestLink) reasons.push('no-manifest-link');
    if (!details.hasServiceWorker) reasons.push('no-service-worker-support');
    if (details.isStandalone) reasons.push('already-installed');

    // Check SW registration/controller (best-effort)
    if (details.hasServiceWorker) {
        try {
            const regs = await navigator.serviceWorker.getRegistrations();
            details.serviceWorkerRegistrations = regs.map((r) => ({ scope: r.scope, active: Boolean(r.active) }));
            details.serviceWorkerController = Boolean(navigator.serviceWorker.controller);
            if (regs.length === 0) reasons.push('no-service-worker-registered');
        } catch (e) {
            details.serviceWorkerError = String(e);
        }
    }

    // Check manifest fetch (best-effort)
    if (details.manifestHref) {
        try {
            const res = await fetch(details.manifestHref, { cache: 'no-store' });
            details.manifestStatus = res.status;
            if (!res.ok) {
                reasons.push('manifest-not-reachable');
            } else {
                const manifest = await res.json();
                details.manifest = {
                    name: manifest?.name || null,
                    short_name: manifest?.short_name || null,
                    start_url: manifest?.start_url || null,
                    display: manifest?.display || null,
                    iconsCount: Array.isArray(manifest?.icons) ? manifest.icons.length : 0,
                };
                if (!Array.isArray(manifest?.icons) || manifest.icons.length === 0) {
                    reasons.push('manifest-missing-icons');
                }
            }
        } catch (e) {
            details.manifestError = String(e);
            reasons.push('manifest-fetch-failed');
        }
    }

    // Installability differs by platform:
    // - Chrome/Edge/etc: requires `beforeinstallprompt` (captured as deferredPrompt)
    // - iOS Safari: no prompt event; user installs via Share → Add to Home Screen
    let canInstall = false;
    let how = null;

    if (isStandalone) {
        canInstall = false;
        how = 'already-installed';
    } else if (isIOS) {
        canInstall = true;
        how = 'ios-add-to-home-screen';
    } else if (details.hasDeferredPrompt) {
        canInstall = true;
        how = 'beforeinstallprompt';
    } else {
        canInstall = false;
        reasons.push('beforeinstallprompt-not-fired-yet');
        how = 'wait-for-beforeinstallprompt';
    }

    return { canInstall, how, reasons: Array.from(new Set(reasons)), details };
};

// Make canInstallApp available globally
window.tiCanInstallApp = window.canInstallApp;
try {
    if (typeof window.canInstallApp === 'undefined') window.canInstallApp = window.canInstallApp;
} catch (e) {}

// Initialize on DOM ready
if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', initUI);
} else {
    initUI();
}
