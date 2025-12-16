const config = {
    cacheKey: "ti_dashboard_payload_v1",
    cacheTtlMs: 60 * 60 * 1000, // 1 hour
    tenderJsonUrls: [
        "/public/tenders-latest.json",
        "/public/build/tenders.json",
        "/tenders.json",
        "./tenders.json",
        "./public/build/tenders.json",
        "./public/tenders-latest.json",
        "/vercel-dashboard/tenders.json",
        "/vercel-dashboard/public/build/tenders.json",
        "/vercel-dashboard/public/tenders-latest.json",
        "../tenders.json"
    ],
    seedPayload: {
        meta: {
            last_sync: null,
            next_run: "Daily 08:00"
        },
        tenders: []
    }
};

const state = {
    tenders: [],
    currentTenders: [],
    currentFilter: 'all',
    currentMonth: new Date(),
    searchQuery: '',
    watchlistAddedBy: '',
    viewMode: 'detailed',
    forceFullRender: false,
};

const ITEM_HEIGHT = 150;
let VISIBLE_ITEMS = Math.ceil(window.innerHeight / ITEM_HEIGHT);
const BUFFER = 5;
let virtualScrollContainer = null;
let virtualScrollTbody = null;
let virtualLastKey = '';

const CHUNK_SIZE = 50;

function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

function debounce(func, delayMs) {
    let timeout;
    return function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delayMs);
    };
}

function throttle(func, limitMs) {
    let inThrottle = false;
    return function throttled(...args) {
        if (inThrottle) return;
        func.apply(this, args);
        inThrottle = true;
        setTimeout(() => {
            inThrottle = false;
        }, limitMs);
    };
}

function initThemeToggle() {
    const themeToggle = document.getElementById('themeToggle');
    if (!themeToggle) return;

    const icon = themeToggle.querySelector('.theme-icon') || themeToggle;
    const currentTheme = (localStorage.getItem('theme') || document.documentElement.getAttribute('data-theme') || 'dark').toLowerCase();
    document.documentElement.setAttribute('data-theme', currentTheme);
    icon.textContent = currentTheme === 'dark' ? '🌙' : '☀️';

    themeToggle.addEventListener('click', () => {
        const theme = (document.documentElement.getAttribute('data-theme') || 'dark').toLowerCase();
        const newTheme = theme === 'dark' ? 'light' : 'dark';
        document.documentElement.setAttribute('data-theme', newTheme);
        localStorage.setItem('theme', newTheme);
        icon.textContent = newTheme === 'dark' ? '🌙' : '☀️';
    });
}

function initPwaInstallPrompt() {
    const installBtn = document.getElementById('installBtn');
    if (!installBtn) return;

    let deferredPrompt = null;

    const hideBtn = () => {
        installBtn.style.display = 'none';
    };

    const showBtn = () => {
        installBtn.style.display = 'inline-flex';
    };

    hideBtn();

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        deferredPrompt = e;
        showBtn();
    });

    window.addEventListener('appinstalled', () => {
        deferredPrompt = null;
        hideBtn();
    });

    installBtn.addEventListener('click', async () => {
        if (!deferredPrompt) return;
        try {
            deferredPrompt.prompt();
            await deferredPrompt.userChoice;
        } catch (err) {
            console.warn('Install prompt failed:', err);
        } finally {
            deferredPrompt = null;
            hideBtn();
        }
    });
}

const VIEW_MODES = ['detailed', 'compact', 'card'];

function getPreferredViewMode() {
    const saved = (localStorage.getItem('preferredView') || '').toString().trim().toLowerCase();
    return VIEW_MODES.includes(saved) ? saved : 'detailed';
}

function applyViewMode(view) {
    const mode = VIEW_MODES.includes(view) ? view : 'detailed';
    state.viewMode = mode;

    const scroll = document.getElementById('tenderTableScroll');
    if (scroll) {
        scroll.classList.remove('view-detailed', 'view-compact', 'view-card');
        scroll.classList.add(`view-${mode}`);
    }

    const list = document.getElementById('tenderList');
    if (list) list.className = `tender-list view-${mode}`;

    document.querySelectorAll('.view-toggle .view-btn').forEach((btn) => {
        const isActive = (btn.dataset?.view || '').toLowerCase() === mode;
        btn.classList.toggle('active', isActive);
    });
}

function initViewToggle() {
    const buttons = Array.from(document.querySelectorAll('.view-toggle .view-btn'));
    if (buttons.length === 0) return;

    applyViewMode(getPreferredViewMode());

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const view = (btn.dataset?.view || '').toLowerCase();
            const mode = VIEW_MODES.includes(view) ? view : 'detailed';
            localStorage.setItem('preferredView', mode);
            applyViewMode(mode);
            resetTenderInfiniteList();
            requestRenderTenders();
        });
    });
}

function getFilteredTendersForExport() {
    const filter = state.currentFilter;
    let filtered = state.tenders.filter((t) => getDaysUntil(t?.closing_date) === null || getDaysUntil(t?.closing_date) >= 0);

    if (filter === 'TES' || filter === 'Phakathi' || filter === 'Both') {
        filtered = filtered.filter((t) => getCompany(t) === filter);
    } else if (filter === 'HIGH' || filter === 'MEDIUM' || filter === 'LOW') {
        filtered = filtered.filter((t) => getPriority(t) === filter);
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

    if (window.advancedFilters && typeof window.advancedFilters.applyFilters === 'function') {
        filtered = window.advancedFilters.applyFilters(filtered);
    }

    if (state.searchQuery && typeof smartSearchTenders === 'function') {
        filtered = smartSearchTenders(state.searchQuery, filtered);
    }

    filtered.sort((a, b) => {
        const daysA = getDaysUntil(a.closing_date) ?? 999;
        const daysB = getDaysUntil(b.closing_date) ?? 999;
        return daysA - daysB;
    });

    const hideOut = document.getElementById('hide-out-of-scope');
    const hideOutOfScope = hideOut && hideOut.checked;
    if (hideOutOfScope) {
        filtered = filtered.filter((t) => {
            try {
                return classifyTender(t)?.relevance !== 'OutOfScope';
            } catch (e) {
                return true;
            }
        });
    }

    return filtered;
}

function printTenders() {
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
    applyViewMode('detailed');

    try {
        const all = getFilteredTendersForExport();
        state.visibleTenderCount = all.length;
        renderTenders();
    } catch (e) {}

    const restore = () => {
        window.removeEventListener('afterprint', restore);
        state.forceFullRender = prev.forceFullRender;
        state.visibleTenderCount = prev.visibleTenderCount;
        applyViewMode(prev.viewMode || 'detailed');
        renderTenders();
        const container = document.getElementById('tenderTableScroll');
        if (container && typeof prev.scrollTop === 'number') container.scrollTop = prev.scrollTop;
    };

    window.addEventListener('afterprint', restore);
    setTimeout(() => window.print(), 60);
}
window.printTenders = printTenders;

function exportToCSV() {
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

    const escapeCell = (cell) => `"${String(cell ?? '').replace(/\"/g, '""')}"`;
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
}
window.exportToCSV = exportToCSV;

function exportToExcel() {
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
}
window.exportToExcel = exportToExcel;

function exportToPDF() {
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
}
window.exportToPDF = exportToPDF;

let debouncedRenderTenders = null;
function requestRenderTenders() {
    if (typeof debouncedRenderTenders === 'function') debouncedRenderTenders();
    else renderTenders();
}
window.requestRenderTenders = requestRenderTenders;

async function fetchTenderChunk(items, offset, chunkSize) {
    const list = Array.isArray(items) ? items : [];
    const start = Math.max(0, offset | 0);
    const end = Math.min(list.length, start + (chunkSize | 0));
    return list.slice(start, end);
}

function resetTenderInfiniteList() {
    state.visibleTenderCount = CHUNK_SIZE;
    state.totalMatchingCount = 0;
    state.loadingMore = false;
    state.watchlistAddedBy = state.watchlistAddedBy || '';
    if (virtualScrollContainer) virtualScrollContainer.scrollTop = 0;
    virtualLastKey = '';
}

function updateTenderLoadProgress(visible, total) {
    const wrap = document.getElementById('tenderLoadProgress');
    const text = document.getElementById('tenderLoadProgressText');
    const fill = document.getElementById('tenderLoadProgressFill');
    if (!wrap || !text || !fill) return;

    const v = typeof visible === 'number' ? visible : 0;
    const t = typeof total === 'number' ? total : 0;
    const active = t > 0 && v < t;
    wrap.classList.toggle('hidden', !active);
    if (!active) return;
    text.textContent = `Loading ${v} of ${t} tenders…`;
    fill.style.width = `${Math.max(0, Math.min(100, Math.round((v / t) * 100)))}%`;
}

function showTenderSkeleton(count = 8) {
    if (!virtualScrollTbody) return;
    const rows = Array.from({ length: count }).map(
        () => `
        <tr>
          <td style="padding: 15px;">
            <div class="skeleton-bar" style="width: 75%; height: 14px;"></div>
            <div class="skeleton-bar" style="width: 35%; margin-top: 10px;"></div>
            <div class="skeleton-bar" style="width: 55%; margin-top: 10px;"></div>
          </td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 60%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 50%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 70%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 60%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 40%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 40%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 40%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 60%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 55%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 80%;"></div></td>
          <td style="padding: 15px;"><div class="skeleton-bar" style="width: 45%;"></div></td>
        </tr>
      `
    );
    virtualScrollTbody.innerHTML = rows.join('');
}

async function loadMoreTenders() {
    if (state.loadingMore) return;
    if (state.visibleTenderCount >= state.totalMatchingCount) return;
    state.loadingMore = true;
    updateTenderLoadProgress(state.visibleTenderCount, state.totalMatchingCount);
    await delay(100);
    state.visibleTenderCount = Math.min(state.totalMatchingCount, state.visibleTenderCount + CHUNK_SIZE);
    state.loadingMore = false;
    renderTenders();
}

async function loadTendersChunked() {
    const total = state.totalMatchingCount || state.tenders.length || 0;
    while (state.visibleTenderCount < total) {
        await loadMoreTenders();
        await delay(100);
    }
}

function renderVirtualList(filteredItems) {
    const items = Array.isArray(filteredItems) ? filteredItems : [];
    if (!virtualScrollContainer || !virtualScrollTbody) return;

    VISIBLE_ITEMS = Math.ceil((virtualScrollContainer.clientHeight || window.innerHeight) / ITEM_HEIGHT);

    // Clamp scrollTop when list shrinks
    const maxScrollTop = Math.max(0, items.length * ITEM_HEIGHT - virtualScrollContainer.clientHeight);
    if (virtualScrollContainer.scrollTop > maxScrollTop) virtualScrollContainer.scrollTop = maxScrollTop;

    const scrollTop = virtualScrollContainer.scrollTop;
    const visibleStart = Math.floor(scrollTop / ITEM_HEIGHT);
    const startIndex = Math.max(0, visibleStart - BUFFER);
    const endIndex = Math.min(items.length, visibleStart + VISIBLE_ITEMS + BUFFER);
    const topSpacer = startIndex * ITEM_HEIGHT;
    const bottomSpacer = Math.max(0, (items.length - endIndex) * ITEM_HEIGHT);

    const key = `${items.length}:${startIndex}:${endIndex}:${topSpacer}:${bottomSpacer}`;
    if (key === virtualLastKey) return;
    virtualLastKey = key;

    virtualScrollTbody.innerHTML = '';

    if (items.length === 0) {
        virtualScrollTbody.innerHTML =
            '<tr><td colspan="12" class="empty-state" style="text-align:center; padding: 40px;"><h3>No tenders found</h3><p>Try a different filter...</p></td></tr>';
        return;
    }

    if (topSpacer > 0) {
        const topRow = document.createElement('tr');
        topRow.className = 'virtual-spacer';
        topRow.style.height = `${topSpacer}px`;
        topRow.innerHTML = '<td colspan="12"></td>';
        virtualScrollTbody.appendChild(topRow);
    }

    const slice = items.slice(startIndex, endIndex);
    slice.forEach((item, idx) => {
        virtualScrollTbody.appendChild(createTenderRow(item, startIndex + idx));
    });

    if (bottomSpacer > 0) {
        const bottomRow = document.createElement('tr');
        bottomRow.className = 'virtual-spacer';
        bottomRow.style.height = `${bottomSpacer}px`;
        bottomRow.innerHTML = '<td colspan="12"></td>';
        virtualScrollTbody.appendChild(bottomRow);
    }
}

const teamMembers = ['Lazola Sonqishe', 'John Doe', 'Jane Smith', 'TES Team', 'Phakathi Team'];

const tenderLifecycleStatuses = [
    { value: 'Not Started', color: 'gray', icon: '⏳' },
    { value: 'Qualified', color: 'blue', icon: '✅' },
    { value: 'In Progress', color: 'yellow', icon: '🛠️' },
    { value: 'Awaiting Review', color: 'orange', icon: '🧾' },
    { value: 'Submitted', color: 'purple', icon: '📨' },
    { value: 'Won', color: 'green', icon: '🏆' },
    { value: 'Lost', color: 'red', icon: '❌' },
    { value: 'Withdrawn', color: 'gray', icon: '🚫' },
];

const tenderFinalStatuses = new Set(['Won', 'Lost']);

let initialMeta = { last_sync: null, next_run: 'Daily 08:00' };

let analyticsInitialized = false;
let analyticsInitTimer = null;

// Persistent storage helper (backs onto localStorage)
window.storage =
    window.storage ||
    (() => {
        const safeGet = (key) => {
            try {
                const raw = localStorage.getItem(key);
                return raw ? JSON.parse(raw) : null;
            } catch {
                return null;
            }
        };
        const safeSet = (key, value) => {
            try {
                localStorage.setItem(key, JSON.stringify(value));
                return true;
            } catch {
                return false;
            }
        };
        const safeRemove = (key) => {
            try {
                localStorage.removeItem(key);
                return true;
            } catch {
                return false;
            }
        };
        return { get: safeGet, set: safeSet, remove: safeRemove };
    })();

function getAssignmentKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `assignment:${ref}` : null;
}

function getTenderAssignment(tenderRef) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return null;
    const value = window.storage.get(key);
    if (!value || typeof value !== 'object') return null;
    const assignedTo = (value.assignedTo || '').toString().trim();
    if (!assignedTo) return null;
    return {
        assignedTo,
        assignedDate: (value.assignedDate || '').toString().trim() || null,
        status: (value.status || '').toString().trim() || 'Not Started'
    };
}

function setTenderAssignment(tenderRef, assignedTo, status = 'Not Started') {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    const name = (assignedTo || '').toString().trim();
    if (!name) return false;
    const date = new Date().toISOString().split('T')[0];
    const ok = window.storage.set(key, { assignedTo: name, assignedDate: date, status: status || 'Not Started' });

    // Seed status history if missing
    const history = getTenderStatusHistory(tenderRef);
    if (history.length === 0) {
        addTenderStatusHistory(tenderRef, status || 'Not Started', getCurrentUsername() || name, 'Assignment created');
    }
    return ok;
}

function updateTenderAssignmentStatus(tenderRef, status) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    const existing = getTenderAssignment(tenderRef);
    if (!existing) return false;
    const next = { ...existing, status: (status || '').toString().trim() || existing.status };
    return window.storage.set(key, next);
}

function clearTenderAssignment(tenderRef) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    return window.storage.remove(key);
}

function getTenderStatusHistoryKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `status_history:${ref}` : null;
}

function getTenderStatusHistory(tenderRef) {
    const key = getTenderStatusHistoryKey(tenderRef);
    if (!key) return [];
    const value = window.storage.get(key);
    if (!Array.isArray(value)) return [];
    return value
        .filter((e) => e && typeof e === 'object')
        .map((e) => ({
            status: (e.status || '').toString(),
            changedBy: (e.changedBy || '').toString(),
            changedDate: (e.changedDate || '').toString(),
            notes: (e.notes || '').toString(),
        }))
        .filter((e) => e.status);
}

function addTenderStatusHistory(tenderRef, status, changedBy, notes) {
    const key = getTenderStatusHistoryKey(tenderRef);
    if (!key) return false;
    const entry = {
        status: (status || '').toString().trim(),
        changedBy: (changedBy || '').toString().trim() || 'Unknown',
        changedDate: new Date().toISOString(),
        notes: (notes || '').toString().trim(),
    };
    if (!entry.status) return false;
    const history = getTenderStatusHistory(tenderRef);
    history.push(entry);
    return window.storage.set(key, history);
}

function getTenderCurrentStatus(tenderRef) {
    const history = getTenderStatusHistory(tenderRef);
    if (history.length > 0) return history[history.length - 1].status || 'Not Started';
    const assignment = getTenderAssignment(tenderRef);
    return assignment?.status || 'Not Started';
}

function getStatusMeta(status) {
    const s = (status || '').toString().trim();
    return tenderLifecycleStatuses.find((x) => x.value === s) || tenderLifecycleStatuses[0];
}

function setTenderLifecycleStatus(tenderRef, status, { notes, changedBy } = {}) {
    const ref = (tenderRef || '').toString().trim();
    if (!ref) return false;

    const desired = (status || '').toString().trim();
    const meta = getStatusMeta(desired);
    const nextStatus = meta.value;
    const actor = (changedBy || '').toString().trim() || getCurrentUsername() || 'Unknown';
    const ok = addTenderStatusHistory(ref, nextStatus, actor, notes || '');

    // Keep assignment record in sync if present
    const assignment = getTenderAssignment(ref);
    if (assignment) updateTenderAssignmentStatus(ref, nextStatus);

    return ok;
}

function getCommentsKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `comments:${ref}` : null;
}

function getTenderComments(tenderRef) {
    const key = getCommentsKey(tenderRef);
    if (!key) return [];
    const value = window.storage.get(key);
    if (!Array.isArray(value)) return [];
    return value
        .filter((c) => c && typeof c === 'object')
        .map((c) => ({
            id: (c.id || '').toString(),
            author: (c.author || '').toString(),
            text: (c.text || '').toString(),
            timestamp: (c.timestamp || '').toString(),
            attachments: Array.isArray(c.attachments) ? c.attachments : [],
            replies: Array.isArray(c.replies) ? c.replies : [],
        }))
        .filter((c) => c.id && c.author && c.timestamp);
}

function saveTenderComments(tenderRef, comments) {
    const key = getCommentsKey(tenderRef);
    if (!key) return false;
    return window.storage.set(key, Array.isArray(comments) ? comments : []);
}

function newId() {
    try {
        return crypto.randomUUID();
    } catch {
        return `c_${Math.random().toString(16).slice(2)}_${Date.now()}`;
    }
}

function relativeTime(isoTs) {
    const d = isoTs ? new Date(isoTs) : null;
    if (!d || Number.isNaN(d.getTime())) return '–';
    const diffMs = Date.now() - d.getTime();
    const diffSec = Math.floor(diffMs / 1000);
    if (diffSec < 10) return 'just now';
    if (diffSec < 60) return `${diffSec}s ago`;
    const diffMin = Math.floor(diffSec / 60);
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    const diffDay = Math.floor(diffHr / 24);
    if (diffDay < 7) return `${diffDay}d ago`;
    return formatNiceDateTime(isoTs);
}

function hashColorForUser(name) {
    const s = (name || '').toString();
    let hash = 0;
    for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
    const hue = hash % 360;
    return `hsl(${hue} 70% 60% / 0.22)`;
}

function initials(name) {
    const parts = (name || '').toString().trim().split(/\s+/).filter(Boolean);
    const a = parts[0]?.[0] || '?';
    const b = parts.length > 1 ? parts[parts.length - 1][0] : '';
    return (a + b).toUpperCase();
}

function parseMentions(text) {
    const t = (text || '').toString();
    if (!t.includes('@')) return [];
    const lowered = t.toLowerCase();
    return teamMembers.filter((m) => {
        const token = `@${m.toLowerCase()}`;
        if (lowered.includes(token)) return true;
        const first = m.split(/\s+/)[0]?.toLowerCase();
        return first ? lowered.includes(`@${first}`) : false;
    });
}

function getMentionsKey(username) {
    const u = (username || '').toString().trim();
    return u ? `mentions:${u}` : null;
}

function getMentionsStore(username) {
    const key = getMentionsKey(username);
    if (!key) return {};
    const v = window.storage.get(key);
    return v && typeof v === 'object' ? v : {};
}

function addMentionsForUsers(users, tenderRef, { commentId, from, timestamp } = {}) {
    const ts = timestamp || new Date().toISOString();
    (users || []).forEach((u) => {
        const key = getMentionsKey(u);
        if (!key) return;
        const store = getMentionsStore(u);
        const ref = (tenderRef || '').toString().trim();
        if (!ref) return;
        if (!Array.isArray(store[ref])) store[ref] = [];
        store[ref].push({
            tenderRef: ref,
            commentId: (commentId || '').toString(),
            from: (from || '').toString(),
            timestamp: ts,
        });
        window.storage.set(key, store);
    });
}

function getUnreadMentionCount(tenderRef, username) {
    const store = getMentionsStore(username);
    const ref = (tenderRef || '').toString().trim();
    const arr = store?.[ref];
    return Array.isArray(arr) ? arr.length : 0;
}

function clearMentionsForTender(tenderRef, username) {
    const key = getMentionsKey(username);
    if (!key) return false;
    const store = getMentionsStore(username);
    const ref = (tenderRef || '').toString().trim();
    if (!ref) return false;
    if (store[ref]) delete store[ref];
    return window.storage.set(key, store);
}

function renderMarkdownLite(text) {
    const escaped = escapeHtml(text || '');
    return escaped
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br/>');
}

function updateMentionBadgesForTender(tender) {
    const badge = document.getElementById('discussionMentionBadge');
    if (!badge) return;
    const user = getCurrentUsername();
    const ref = (tender?.ref || '').toString().trim();
    if (!user || !ref) {
        badge.classList.add('hidden');
        badge.textContent = '0';
        return;
    }
    const count = getUnreadMentionCount(ref, user);
    badge.textContent = String(count);
    badge.classList.toggle('hidden', count === 0);
}

function getCurrentUsername() {
    try {
        return (localStorage.getItem('ti_username') || '').trim() || null;
    } catch {
        return null;
    }
}

function ensureUsername() {
    const existing = getCurrentUsername();
    if (existing) return existing;
    const name = prompt('Enter your name (used for "Assigned to Me"):', '');
    const trimmed = (name || '').toString().trim();
    if (!trimmed) return null;
    try {
        localStorage.setItem('ti_username', trimmed);
    } catch {
        // ignore
    }
    return trimmed;
}

function getWatchlistMode() {
    try {
        const raw = (localStorage.getItem('ti_watchlist_mode') || '').trim();
        return raw === 'personal' ? 'personal' : 'shared';
    } catch {
        return 'shared';
    }
}

function setWatchlistMode(mode) {
    const next = mode === 'personal' ? 'personal' : 'shared';
    if (next === 'personal' && !getCurrentUsername()) {
        const user = ensureUsername();
        if (!user) return;
    }
    try {
        localStorage.setItem('ti_watchlist_mode', next);
    } catch {
        // ignore
    }
    updateWatchlistBadges();
    updateWatchlistToolbar();
    requestRenderTenders();
}

function normalizeWatchlistEntries(entries) {
    const list = Array.isArray(entries) ? entries : [];
    return list
        .filter((e) => e && typeof e === 'object')
        .map((e) => ({
            tender_ref: (e.tender_ref || e.tenderRef || '').toString().trim(),
            addedBy: (e.addedBy || '').toString().trim(),
            addedDate: (e.addedDate || '').toString().trim(),
        }))
        .filter((e) => e.tender_ref);
}

function getSharedWatchlist() {
    return normalizeWatchlistEntries(window.storage.get('watchlist'));
}

function setSharedWatchlist(entries) {
    return window.storage.set('watchlist', normalizeWatchlistEntries(entries));
}

function getPersonalWatchlist(username) {
    const user = (username || '').toString().trim();
    if (!user) return [];
    const key = `watchlist_personal:${user}`;
    try {
        const raw = localStorage.getItem(key);
        return normalizeWatchlistEntries(raw ? JSON.parse(raw) : []);
    } catch {
        return [];
    }
}

function setPersonalWatchlist(username, entries) {
    const user = (username || '').toString().trim();
    if (!user) return false;
    const key = `watchlist_personal:${user}`;
    try {
        localStorage.setItem(key, JSON.stringify(normalizeWatchlistEntries(entries)));
        return true;
    } catch {
        return false;
    }
}

function getActiveWatchlist() {
    const mode = getWatchlistMode();
    if (mode === 'personal') {
        const user = getCurrentUsername();
        return user ? getPersonalWatchlist(user) : [];
    }
    return getSharedWatchlist();
}

function setActiveWatchlist(entries) {
    const mode = getWatchlistMode();
    if (mode === 'personal') {
        const user = getCurrentUsername();
        return user ? setPersonalWatchlist(user, entries) : false;
    }
    return setSharedWatchlist(entries);
}

function isTenderWatchlisted(ref) {
    const r = (ref || '').toString().trim();
    if (!r) return false;
    return getActiveWatchlist().some((e) => e.tender_ref === r);
}

function toggleWatchlist(ref) {
    const tenderRef = (ref || '').toString().trim();
    if (!tenderRef) return false;

    const list = getActiveWatchlist();
    const idx = list.findIndex((e) => e.tender_ref === tenderRef);
    if (idx >= 0) {
        list.splice(idx, 1);
        const ok = setActiveWatchlist(list);
        updateWatchlistBadges();
        updateWatchlistToolbar();
        return ok;
    }

    const mode = getWatchlistMode();
    let actor = getCurrentUsername();
    if (!actor) actor = ensureUsername();
    if (!actor) return false;

    list.push({
        tender_ref: tenderRef,
        addedBy: actor,
        addedDate: new Date().toISOString().split('T')[0],
    });
    const ok = setActiveWatchlist(list);
    updateWatchlistBadges();
    updateWatchlistToolbar();
    return ok;
}

function addAllHighPriorityToWatchlist() {
    let actor = getCurrentUsername();
    if (!actor) actor = ensureUsername();
    if (!actor) return;

    const mode = getWatchlistMode();
    const list = getActiveWatchlist();
    const refs = new Set(list.map((e) => e.tender_ref));

    const highRefs = (state.tenders || [])
        .filter((t) => getPriority(t) === 'HIGH')
        .map((t) => (t?.ref || '').toString().trim())
        .filter(Boolean);

    let added = 0;
    highRefs.forEach((ref) => {
        if (refs.has(ref)) return;
        refs.add(ref);
        list.push({ tender_ref: ref, addedBy: actor, addedDate: new Date().toISOString().split('T')[0] });
        added += 1;
    });

    setActiveWatchlist(list);
    updateWatchlistBadges();
    updateWatchlistToolbar();
    requestRenderTenders();

    console.info(`[Tender Intelligence] Added ${added} HIGH priority tenders to ${mode} watchlist.`);
}

function exportWatchlistCsv() {
    const mode = getWatchlistMode();
    const list = getActiveWatchlist();
    const userFilter = (state.watchlistAddedBy || '').toString().trim();
    const filtered = userFilter ? list.filter((e) => e.addedBy === userFilter) : list;

    const byRef = new Map((state.tenders || []).map((t) => [t.ref, t]));
    const rows = filtered.map((e) => {
        const t = byRef.get(e.tender_ref) || {};
        return {
            tender_ref: e.tender_ref,
            title: t.title || '',
            source: t.source || '',
            client: t.client || '',
            closing_date: t.closing_date || '',
            priority: getPriority(t) || '',
            addedBy: e.addedBy || '',
            addedDate: e.addedDate || '',
            url: t.url || '',
        };
    });

    const header = ['tender_ref', 'title', 'source', 'client', 'closing_date', 'priority', 'addedBy', 'addedDate', 'url'];
    const escapeCsv = (v) => {
        const s = (v ?? '').toString();
        if (/[",\n]/.test(s)) return `"${s.replace(/"/g, '""')}"`;
        return s;
    };
    const csv = [header.join(','), ...rows.map((r) => header.map((k) => escapeCsv(r[k])).join(','))].join('\n');

    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `watchlist-${mode}-${new Date().toISOString().split('T')[0]}.csv`;
    document.body.appendChild(a);
    a.click();
    a.remove();
    URL.revokeObjectURL(url);
}

function updateWatchlistBadges() {
    const list = getActiveWatchlist();
    const count = list.length;

    const navBadge = document.getElementById('watchlistNavBadge');
    if (navBadge) {
        navBadge.textContent = String(count);
        navBadge.classList.toggle('hidden', count === 0);
    }

    const filterBadge = document.getElementById('watchlistFilterBadge');
    if (filterBadge) {
        filterBadge.textContent = String(count);
        filterBadge.classList.toggle('hidden', count === 0);
    }
}

function updateWatchlistToolbar() {
    const modeSelect = document.getElementById('watchlistModeSelect');
    if (modeSelect) modeSelect.value = getWatchlistMode();

    const userSelect = document.getElementById('watchlistUserFilter');
    if (userSelect) {
        const isWatchlistView = state.currentFilter === 'WATCHLIST';
        userSelect.disabled = !isWatchlistView;
        userSelect.style.opacity = isWatchlistView ? '1' : '0.6';

        const list = getActiveWatchlist();
        const users = Array.from(new Set(list.map((e) => e.addedBy).filter(Boolean))).sort((a, b) => a.localeCompare(b));
        const current = (state.watchlistAddedBy || '').toString();
        userSelect.innerHTML = `<option value="">All users</option>${users
            .map((u) => `<option value="${escapeHtml(u)}"${u === current ? ' selected' : ''}>${escapeHtml(u)}</option>`)
            .join('')}`;
    }
}

function getCompany(t) {
    return (t.company || t.category || "").trim();
}

function getPriority(t) {
    return (t.priority || t.scores?.priority || "").toUpperCase();
}

function normalizeTender(t) {
    const company = (t.company || t.category || "").trim();
    const scores = t.scores || {
        fit: t.score ?? t.fit ?? t.fit_score,
        revenue: t.revenue_score ?? t.revenue,
        risk: t.risk_score ?? t.risk,
        suitability: t.suitability_score ?? t.suitability ?? t.industry ?? t.composite
    };

    return {
        ...t,
        company,
        priority: (t.priority || "").toUpperCase(),
        scores
    };
}

// Calculate days until closing
function getDaysUntil(dateStr) {
    if (!dateStr) return null;
    const closing = new Date(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    closing.setHours(0, 0, 0, 0);
    return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
}

function getCountdownHtml(dateStr) {
    const days = getDaysUntil(dateStr);
    if (days === null) return '<span class="countdown normal">📅 TBC</span>';
    if (days < 0) return '<span class="countdown closed">CLOSED</span>';
    if (days === 0) return '<span class="countdown urgent">🔴 TODAY!</span>';
    if (days === 1) return '<span class="countdown urgent">🔴 TOMORROW!</span>';
    if (days <= 3) return `<span class="countdown urgent">⚠️ ${days} days</span>`;
    if (days <= 7) return `<span class="countdown warning">📅 ${days} days</span>`;
    return `<span class="countdown normal">📅 ${days} days</span>`;
}

function createTenderRow(item, idx) {
    const t = item.tender;
    const scores = t.scores || {};
    const { relevance, categories, bidDecision } = item.classification;
    const title = t.title || '-';
    const source = t.source || '-';
    const company = getCompany(t) || '-';
    const priority = getPriority(t) || '-';
    const closeDate = t.closing_date || '-';
    const fitScore = (t.score ?? scores.fit ?? scores.fit_score ?? '-') || '-';
    const revenueScore = (t.revenue_score ?? scores.revenue ?? scores.revenue_score ?? '-') || '-';
    const riskScore = (t.risk_score ?? scores.risk ?? scores.risk_score ?? '-') || '-';
    const countdownStatus = t.status || getCountdownHtml(t.closing_date) || '-';
    const link = t.url ? `<a href="${t.url}" target="_blank" rel="noopener" class="view-btn" style="padding: 6px 15px; font-size: 0.8rem;" onclick="event.stopPropagation()">Open ↗</a>` : '-';
    const decision = computeDecision(t);
    const scopeClass = relevance === 'OutOfScope' ? 'scope-pill-out' : relevance === 'TES' ? 'scope-pill-tes' : relevance === 'Phakathi' ? 'scope-pill-phakathi' : relevance === 'Both' ? 'scope-pill-both' : 'scope-pill-out';
    const scopeText = relevance === 'OutOfScope' ? 'Not in scope' : relevance === 'TES' ? 'TES' : relevance === 'Phakathi' ? 'Phakathi' : relevance === 'Both' ? 'TES + Phakathi' : 'Review';
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
        <td style="padding: 15px; color: #ccc;">${revenueScore}</td>
        <td style="padding: 15px; color: #ccc;">${riskScore}</td>
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

function createTenderCard(item, idx) {
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
    card.addEventListener('click', () => openTenderModal(t));

    const priorityBadge = `<span class="priority priority-${priority}">${priority}</span>`;
    const decisionPill = `<span class="decision-pill ${decision.className}">${decision.label}<span class="reason"> · ${decision.reason}</span><span class="confidence"> · ${decision.confidence}%</span></span>`;
    const categoryTags = (item.classification?.categories || []).map(c => `<span class="category-tag">${c}</span>`).join('');

    const starActive = isWatchlisted(t.ref);
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

function renderTenderCards(classified, totalCount) {
    const grid = document.getElementById('tenderCardGrid');
    if (!grid) return;
    grid.innerHTML = '';
    const items = Array.isArray(classified) ? classified : [];
    items.forEach((item, idx) => grid.appendChild(createTenderCard(item, idx)));
}


function renderTenders() {
    const list = document.getElementById('tender-table-body') || document.getElementById('tenderList');
    if (!list) return;
    
    const filter = state.currentFilter;
    let filtered = state.tenders.filter(t => getDaysUntil(t.closing_date) === null || getDaysUntil(t.closing_date) >= 0);

		    if (filter === 'TES' || filter === 'Phakathi' || filter === 'Both') {
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
        countEl.textContent = `Showing ${classified.length} of ${classifiedAll.length}${suffix}`;
    }

	    updateWatchlistBadges();
	    updateWatchlistToolbar();
        updateTenderLoadProgress(classified.length, classifiedAll.length);

	    state.currentTenders = classified.map(item => item.tender);
	    window.__virtualListItems = classified;
	    virtualScrollContainer = virtualScrollContainer || document.getElementById('tenderTableScroll');
	    virtualScrollTbody = list;
	    virtualLastKey = '';
	    if (state.viewMode === 'card' && !state.forceFullRender) {
	        renderTenderCards(classified, classifiedAll.length);
	        return;
	    }

	    if (virtualScrollContainer && !state.forceFullRender) renderVirtualList(classified);
	    else {
	        list.innerHTML = '';
	        classified.forEach((item, idx) => list.appendChild(createTenderRow(item, idx)));
	    }
}

function renderScraperHealth(scraperData) {
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
}

function filterTenders(filter) {
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
}

function smartSearchTenders(query, tenders) {
    // When called from the UI (no `tenders` passed), update state + rerender.
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
        companyTes: /\btes\b/i,
        companyPhakathi: /\bphakathi\b/i,
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
    const matchCompany = patterns.companyTes.test(q) ? 'TES' : patterns.companyPhakathi.test(q) ? 'Phakathi' : null;

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
}

// Backwards compatible alias (older templates may call this name)
function searchTenders() {
    const box = document.getElementById('tenderSearchBox');
    smartSearchTenders(box ? box.value : '');
}

function updateNextRunCountdown() {
    const el = document.getElementById('next-run-countdown');
    if (!el) return;

    const now = new Date();
    const nextRun = new Date(now);
    nextRun.setHours(8, 0, 0, 0);

    if (now >= nextRun) {
        nextRun.setDate(nextRun.getDate() + 1);
    }

    const diffMs = nextRun - now;
    const diffMinutes = Math.max(0, Math.floor(diffMs / (1000 * 60)));
    const hours = Math.floor(diffMinutes / 60);
    const minutes = diffMinutes % 60;

    const text = hours > 0 ? `Next run in ${hours}h ${minutes}m` : `Next run in ${minutes}m`;
    el.textContent = text;
}

function classifyTender(tender) {
    const desc = (tender.description || tender.long_description || "").toLowerCase();

    const civilKeywords = [
        "construction", "civil", "upgrade", "water upgrade", "corridors of freedom",
        "pumpstation", "pump station", "reticulation", "sewer", "roads",
        "earthworks", "structural", "tower", "towers", "reservoir",
        "building", "infrastructure"
    ];

    const tesKeywords = [
        "chemical", "chemicals", "dosing", "chlorine", "hypochlorite", "biocide",
        "surfactant", "dispersant", "amine", "cooling", "cooling tower",
        "boiler", "steam", "ro", "reverse osmosis", "filtration",
        "water treatment plant", "softener"
    ];

    const phakathiKeywords = [
        "pumps", "pump", "valves", "fabrication", "mechanical", "electrical",
        "switchgear", "motors", "install", "installation",
        "maintenance", "commissioning", "steelwork"
    ];

    const categories = [];

    const hasCivil = civilKeywords.some(k => desc.includes(k));
    const hasTES = tesKeywords.some(k => desc.includes(k));
    const hasPhakathi = phakathiKeywords.some(k => desc.includes(k));

    let relevance = "Unknown";
    if (hasTES && hasPhakathi) {
        relevance = "Both";
    } else if (hasTES) {
        relevance = "TES";
    } else if (hasPhakathi) {
        relevance = "Phakathi";
    } else if (hasCivil) {
        relevance = "OutOfScope";
    }

    if (hasTES) categories.push("Chemical/Water");
    if (hasPhakathi) categories.push("Mechanical/Electrical");
    if (relevance === "OutOfScope" && hasCivil) categories.push("Civil/Infrastructure");

    const priority = (tender.priority || "").toUpperCase();
    const fit = typeof tender.fit_score === "number" ? tender.fit_score : null;

    let bidDecision = "REVIEW";
    if (relevance === "OutOfScope") {
        bidDecision = "NO_BID";
    } else if ((relevance === "TES" || relevance === "Phakathi" || relevance === "Both") && fit !== null && fit >= 5 && priority !== "LOW") {
        bidDecision = "BID";
    }

    return { relevance, categories, bidDecision };
}

function computeDecision(tender) {
    const scores = tender.scores || {};
    const fit = typeof scores.fit === 'number' ? scores.fit : 0;
    const suitability = typeof scores.suitability === 'number'
        ? scores.suitability
        : (typeof scores.industry === 'number'
            ? scores.industry
            : (typeof scores.composite === 'number' ? scores.composite : 0));

    const priority = (tender.priority || scores.priority || 'LOW').toUpperCase();
    const scopeLabel = (tender.scope || tender.company_scope || tender.category || '').toString().toLowerCase();
    const notes = (tender.notes || '').toString().toLowerCase();
    const insight = (tender.ai_insight || tender.aiInsight || '').toString().toLowerCase();

    const outOfScopeSignals = [
        scopeLabel.includes('out of scope'),
        scopeLabel.includes('out-of-scope'),
        scopeLabel.includes('civil'),
        scopeLabel.includes('infrastructure'),
        insight.includes('outside our scope'),
        insight.includes('outside scope')
    ];

    const textBlob = [
        tender.title || '',
        tender.description || '',
        tender.category || '',
        notes,
        insight
    ].join(' ').toLowerCase();

    const civilSignals = [
        'civil',
        'construction',
        'infrastructure',
        'pumpstation',
        'pump station',
        'earthworks',
        'building',
        'upgrade',
        'roads',
        'stormwater'
    ];

    const isCivil = civilSignals.some(sig => textBlob.includes(sig));
    const isOutOfScope = outOfScopeSignals.some(Boolean) || isCivil;

    const isHighPriority = priority === 'HIGH';
    const isMediumPriority = priority === 'MEDIUM';

    function makeDecision(label, className, reason, confidence) {
        let level = 'medium';
        if (confidence >= 85) level = 'high';
        else if (confidence < 60) level = 'low';
        return { label, className, reason, confidence, level };
    }

    const avgScore = (fit + suitability) / 2;

    if (isOutOfScope) {
        return makeDecision('No-Bid', 'nobid', 'Outside TES / Phakathi scope (civil / infrastructure)', 96);
    }
    if (fit >= 7 && suitability >= 6 && (isHighPriority || isMediumPriority)) {
        let conf = Math.round(70 + avgScore * 3);
        if (conf > 98) conf = 98;
        return makeDecision('Bid', 'bid', 'Strong technical and strategic fit', conf);
    }
    if (fit <= 3 || suitability <= 3) {
        let conf = Math.round(75 + (3 - Math.min(fit, suitability)) * 5);
        if (conf > 95) conf = 95;
        return makeDecision('No-Bid', 'nobid', 'Weak fit / unsuitable opportunity', conf);
    }

    let conf = Math.round(55 + avgScore * 2);
    if (conf > 80) conf = 80;
    return makeDecision('Consider', 'consider', 'Needs human review (mixed or unclear scope)', conf);
}

function updatePrintHeader(meta, tendersSummary) {
    const lastSyncSpan = document.getElementById("print-last-sync");
    const nextRunSpan = document.getElementById("print-next-run");
    const totalSpan = document.getElementById("print-total-tenders");
    const tesSpan = document.getElementById("print-tes-tenders");
    const pakatiSpan = document.getElementById("print-phakathi-tenders");

    if (lastSyncSpan && meta && meta.last_sync) {
        lastSyncSpan.textContent = "Last sync: " + meta.last_sync;
    }
    if (nextRunSpan && meta && meta.next_run) {
        nextRunSpan.textContent = "Next run: " + meta.next_run;
    }

    if (tendersSummary) {
        if (totalSpan) totalSpan.textContent = String(tendersSummary.total || "0");
        if (tesSpan) tesSpan.textContent = String(tendersSummary.tes || "0");
        if (pakatiSpan) pakatiSpan.textContent = String(tendersSummary.phakathi || "0");
    }
}

function getKpiSummary() {
    const totalKpi = document.querySelector(".stat-value.total");
    const tesKpi = document.querySelector(".stat-value.tes-color");
    const pakatiKpi = document.querySelector(".stat-value.phakathi-color");
    return {
        total: totalKpi ? totalKpi.textContent.trim() : "0",
        tes: tesKpi ? tesKpi.textContent.trim() : "0",
        phakathi: pakatiKpi ? pakatiKpi.textContent.trim() : "0"
    };
}

function setDataStatus({ level, source, count, updated, error }) {
    const pill = document.getElementById("data-status-pill");
    const sourceEl = document.getElementById("data-status-source");
    const countEl = document.getElementById("data-status-count");
    const updatedEl = document.getElementById("data-status-updated");
    const errorEl = document.getElementById("data-status-error");

    if (pill) {
        pill.classList.remove("ok", "warn", "err");
        if (level) pill.classList.add(level);
        pill.textContent = level === "ok" ? "Data: live" : level === "warn" ? "Data: cached" : "Data: error";
    }
    if (sourceEl) sourceEl.textContent = source || "–";
    if (countEl) countEl.textContent = typeof count === "number" ? String(count) : (count ?? "–");
    if (updatedEl) updatedEl.textContent = updated || "–";
    if (errorEl) {
        if (error) {
            errorEl.textContent = `Error: ${error.message || error}`;
        } else {
            errorEl.textContent = "";
        }
    }
}

function updateOfflineIndicator() {
    const pill = document.getElementById('offlinePill');
    if (!pill) return;
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    pill.classList.toggle('hidden', !offline);
}

function enqueueOfflineAction(action) {
    try {
        const key = 'ti_offline_queue';
        const raw = localStorage.getItem(key);
        const queue = raw ? JSON.parse(raw) : [];
        const next = Array.isArray(queue) ? queue : [];
        next.push({ ...action, createdAt: new Date().toISOString() });
        localStorage.setItem(key, JSON.stringify(next));
    } catch {
        // ignore
    }
}

async function flushOfflineQueue() {
    let queue = [];
    try {
        const key = 'ti_offline_queue';
        const raw = localStorage.getItem(key);
        queue = raw ? JSON.parse(raw) : [];
        localStorage.setItem(key, JSON.stringify([]));
    } catch {
        queue = [];
    }
    if (!Array.isArray(queue) || queue.length === 0) return;
    for (const item of queue) {
        if (item?.type === 'refresh') {
            try {
                await refreshDashboardData();
            } catch {
                // ignore
            }
        }
    }
}

function validatePayloadShape(payload) {
    const tenderList = Array.isArray(payload) ? payload : (payload?.tenders || payload?.data || []);
    if (!Array.isArray(tenderList)) throw new Error("Invalid payload: tenders must be an array");
    const meta = (!Array.isArray(payload) && payload?.meta) ? payload.meta : {};
    return { tenderList, meta };
}

function readCachedPayload() {
    try {
        const raw = localStorage.getItem(config.cacheKey);
        if (!raw) return null;
        const cached = JSON.parse(raw);
        if (!cached || typeof cached !== "object") return null;
        const storedAtMs = cached?.storedAt ? Date.parse(cached.storedAt) : NaN;
        if (!Number.isFinite(storedAtMs)) return null;
        const age = Date.now() - storedAtMs;
        if (age > config.cacheTtlMs) {
            localStorage.removeItem(config.cacheKey);
            console.info("[Tender Intelligence] Cache expired (age ms):", age);
            return null;
        }
        const payload = cached.payload;
        const { tenderList, meta } = validatePayloadShape(payload);
        return {
            tenders: tenderList,
            meta: meta || {},
            storedAt: cached.storedAt || null,
            buildId: cached?.buildId || meta?.build_id || null,
            buildSha: cached?.buildSha || meta?.build_sha || null
        };
    } catch {
        return null;
    }
}

function writeCachedPayload(payload, storedAtOverride) {
    try {
        const { meta } = validatePayloadShape(payload);
        localStorage.setItem(
            config.cacheKey,
            JSON.stringify({
                payload,
                storedAt: storedAtOverride || new Date().toISOString(),
                buildId: meta?.build_id || null,
                buildSha: meta?.build_sha || null
            })
        );
    } catch {
        // ignore storage failures
    }
}

function clearCachedPayload() {
    try {
        localStorage.removeItem(config.cacheKey);
    } catch {
        // ignore
    }
}

async function loadTenderPayload({ forceRefresh } = {}) {
    if (forceRefresh) {
        console.info("[Tender Intelligence] Manual refresh requested; clearing cache and refetching.");
        clearCachedPayload();
    }

    let lastErr;
    for (const url of config.tenderJsonUrls) {
        try {
            console.info("[Tender Intelligence] Fetching data from:", url);
            const res = await fetch(url + "?ts=" + Date.now(), { cache: "no-store" });
            if (!res.ok) throw new Error(`${url} -> ${res.status}`);
            const payload = await res.json();
            const { tenderList, meta } = validatePayloadShape(payload);
            const swCacheTime = res.headers.get('x-sw-cache-time');
            writeCachedPayload(payload, swCacheTime || undefined);
            console.info(
                "[Tender Intelligence] Using live payload:",
                url,
                "records=",
                tenderList.length,
                "build=",
                meta?.build_id || meta?.last_sync || "–"
            );
            return { tenders: tenderList, meta: meta || {}, source: swCacheTime ? "serviceWorkerCache" : url, storedAt: swCacheTime || null };
        } catch (e) {
            lastErr = e;
            console.warn("[Tender Intelligence] Fetch failed:", url, e?.message || e);
        }
    }

    if (!forceRefresh) {
        const cached = readCachedPayload();
        if (cached) {
            console.info(
                "[Tender Intelligence] Using cached payload:",
                "records=",
                cached.tenders.length,
                "build=",
                cached.buildId || cached.storedAt || "–"
            );
            return { tenders: cached.tenders, meta: cached.meta, source: "localStorage", storedAt: cached.storedAt };
        }
    }

    const { tenderList, meta } = validatePayloadShape(config.seedPayload);
    console.warn("[Tender Intelligence] Using seed payload (no live data and cache missing/expired).", lastErr?.message || lastErr);
    return { tenders: tenderList, meta, source: "seed", error: lastErr };
}

function generateAIInsight(tender) {
    const scores = tender.scores || {};
    const company = (tender.company || "").toUpperCase();
    const priority = (tender.priority || "").toUpperCase();

    const getVal = (keys) => {
        for (const k of keys) {
            if (Number.isFinite(tender[k])) return tender[k];
            if (Number.isFinite(scores[k])) return scores[k];
        }
        return null;
    };

    const fitScore = getVal(['fit_score', 'score', 'fit']);
    const revenueScore = getVal(['revenue_score', 'revenue']);
    const riskScore = getVal(['risk_score', 'risk']);

    const { relevance, bidDecision } = classifyTender(tender);

    if (relevance === 'OutOfScope') {
        const rel = 'This tender is a civil/infrastructure upgrade. Neither TES nor Phakathi operate in this category.';
        const opp = 'Opportunity evaluation: outside our scope; deprioritise unless strategy changes.';
        const act = 'Recommended action: NO BID — mark as not relevant and exclude from pursuit.';
        return `${rel}\n${opp}\n${act}`;
    }

    let relevanceText = 'Relevance unclear; tender should be manually reviewed.';
    if (relevance === 'Both' || company === 'BOTH') {
        relevanceText = 'Both TES and Phakathi may participate given mixed scope indicators.';
    } else if (relevance === 'TES' || company === 'TES') {
        relevanceText = 'The scope indicates strong relevance for TES due to water treatment chemicals, cooling, dosing, RO, or boiler references.';
    } else if (relevance === 'Phakathi' || company === 'PHAKATHI') {
        relevanceText = 'This tender aligns with Phakathi’s mechanical/electrical offering based on installation, maintenance, pumps, or fabrication scope.';
    }

    const oppLines = [];
    const priorityText = priority ? `Priority: ${priority.toLowerCase()}.` : '';
    if (priorityText) oppLines.push(priorityText);
    if (priority === 'HIGH') oppLines.push('Time-sensitive tender requiring urgent attention.');
    if (fitScore !== null && fitScore >= 5) oppLines.push('Strong match to internal capability scoring.');
    if (revenueScore !== null && revenueScore >= 5) oppLines.push('Revenue potential appears attractive.');
    if (riskScore !== null && riskScore >= 60) oppLines.push('Potential risk due to unclear scope, competition, or contractual complexity.');
    const opportunity = oppLines.length ? oppLines.join(' ') : 'Opportunity signal is moderate; further validation needed.';

    let action = 'Recommended next step: review historical awards, confirm volume requirements, and prepare pricing scenarios.';
    if (relevance === 'Phakathi' || company === 'PHAKATHI') {
        action = 'Recommended action: request technical drawings, verify site conditions, and assess fabrication or installation lead times.';
    }
    if (relevance === 'Both' || company === 'BOTH') {
        action = 'Recommended action: split review between TES and Phakathi leads, confirm scope boundaries, and price jointly if feasible.';
    }
    if (bidDecision === 'NO_BID') {
        action = 'Recommended action: NO BID — outside target scope.';
    }

    return `${relevanceText}\n${opportunity}\n${action}`;
}

function escapeHtml(value) {
    const s = (value ?? '').toString();
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

function formatBytes(bytes) {
    const n = typeof bytes === 'number' ? bytes : Number(bytes);
    if (!Number.isFinite(n) || n <= 0) return '–';
    const units = ['B', 'KB', 'MB', 'GB'];
    const idx = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)));
    const val = n / 1024 ** idx;
    return `${val.toFixed(val >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

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

function formatNiceDateTime(dateStr, timeStr) {
    const hasTimeInDate = typeof dateStr === 'string' && /T\d{2}:\d{2}/.test(dateStr);
    const d = parseFlexibleDate(dateStr);
    if (!d) return '–';

    if (timeStr && !hasTimeInDate) {
        const t = timeStr.toString().trim();
        const m = t.match(/^(\d{1,2}):(\d{2})/);
        if (m) d.setHours(Number(m[1]), Number(m[2]), 0, 0);
    }

    const optsDate = { weekday: 'long', day: '2-digit', month: 'long', year: 'numeric' };
    const optsTime = { hour: '2-digit', minute: '2-digit' };
    const datePart = d.toLocaleDateString(undefined, optsDate);
    const shouldShowTime = hasTimeInDate || Boolean(timeStr);
    if (!shouldShowTime) return datePart;
    return `${datePart} at ${d.toLocaleTimeString(undefined, optsTime)}`;
}

function normalizeAttachments(tender) {
    const items = [];
    const rawList = tender?.attachments || tender?.files || tender?.documents || [];

    const pushItem = (name, url, size) => {
        if (!url) return;
        let safeUrl = url.toString();
        try {
            safeUrl = encodeURI(safeUrl);
        } catch {
            // ignore
        }
        const fileName =
            name ||
            safeUrl.split('?')[0].split('#')[0].split('/').filter(Boolean).slice(-1)[0] ||
            'Document';
        const ext = (fileName.split('.').pop() || '').toLowerCase();
        items.push({ name: fileName, url: safeUrl, size, ext });
    };

    if (Array.isArray(rawList)) {
        rawList.forEach((a) => {
            if (!a) return;
            if (typeof a === 'string') {
                pushItem(null, a, null);
                return;
            }
            if (typeof a === 'object') {
                pushItem(a.name || a.filename || a.title, a.url || a.href || a.link, a.size || a.bytes || null);
            }
        });
    }

    // If tender.url is a direct document link (commonly PDF), include as main document
    const url = tender?.url;
    if (url && typeof url === 'string') {
        const isDoc = /\.(pdf|doc|docx|xls|xlsx|zip)(\?|#|$)/i.test(url);
        const already = items.some((it) => it.url === url);
        if (isDoc && !already) pushItem('Main Document', url, null);
    }

    return items;
}

function getAttachmentIcon(ext) {
    switch ((ext || '').toLowerCase()) {
        case 'pdf':
            return '📄';
        case 'doc':
        case 'docx':
            return '📝';
        case 'xls':
        case 'xlsx':
            return '📊';
        case 'zip':
            return '🗜️';
        default:
            return '📎';
    }
}

function tenderKeywordSet(tender) {
    const stop = new Set([
        'tender',
        'supply',
        'services',
        'provision',
        'water',
        'system',
        'treatment',
        'request',
        'quotation',
        'proposal',
        'rfq',
        'bid'
    ]);
    const text = `${tender?.title || ''} ${tender?.description || tender?.long_description || ''}`.toLowerCase();
    const tokens = text
        .split(/[^a-z0-9]+/i)
        .map((w) => w.trim())
        .filter((w) => w.length > 4 && !stop.has(w));
    return new Set(tokens);
}

const tenderKeywordCache = new Map(); // key -> Set(keywords)

function getTenderCacheKey(t) {
    const ref = (t?.ref || '').toString().trim();
    if (ref) return `ref:${ref}`;
    const url = (t?.url || '').toString().trim();
    if (url) return `url:${url}`;
    const title = (t?.title || '').toString().trim();
    return `title:${title}`;
}

function getTenderKeywordsCached(tender) {
    const key = getTenderCacheKey(tender);
    if (!key) return new Set();
    const cached = tenderKeywordCache.get(key);
    if (cached) return cached;
    const computed = tenderKeywordSet(tender);
    tenderKeywordCache.set(key, computed);
    return computed;
}

function getCommonKeywords(setA, setB, limit = 8) {
    const common = [];
    const [small, large] = setA.size <= setB.size ? [setA, setB] : [setB, setA];
    small.forEach((w) => {
        if (large.has(w)) common.push(w);
    });
    common.sort();
    return common.slice(0, limit);
}

function calculateSimilarity(tender1, tender2) {
    const a = getTenderKeywordsCached(tender1);
    const b = getTenderKeywordsCached(tender2);
    if (a.size === 0 && b.size === 0) return 0;

    let intersection = 0;
    const [small, large] = a.size <= b.size ? [a, b] : [b, a];
    small.forEach((w) => {
        if (large.has(w)) intersection += 1;
    });
    const union = a.size + b.size - intersection;
    let score = union === 0 ? 0 : intersection / union;

    const norm = (v) => (v || '').toString().trim().toLowerCase();
    if (norm(tender1?.category) && norm(tender1?.category) === norm(tender2?.category)) score += 0.05;
    if (norm(tender1?.source) && norm(tender1?.source) === norm(tender2?.source)) score += 0.05;
    if (norm(tender1?.client) && norm(tender1?.client) === norm(tender2?.client)) score += 0.05;

    if (score < 0) score = 0;
    if (score > 1) score = 1;
    return score;
}

function findSimilarTenders(tender, allTenders, limit = 5) {
    const items = Array.isArray(allTenders) ? allTenders : [];
    const baseKey = getTenderCacheKey(tender);
    const baseSet = getTenderKeywordsCached(tender);

    const scored = [];
    items.forEach((t) => {
        if (!t || typeof t !== 'object') return;
        if (getTenderCacheKey(t) === baseKey) return;
        const score = calculateSimilarity(tender, t);
        if (score <= 0) return;
        const otherSet = getTenderKeywordsCached(t);
        const keywords = getCommonKeywords(baseSet, otherSet, 8);
        scored.push({ tender: t, score, keywords });
    });

    scored.sort((a, b) => b.score - a.score);
    return scored.slice(0, limit);
}

function renderSimilarTendersTab(currentTender) {
    const similarEl = document.getElementById('tenderDetailSimilar');
    if (!similarEl || !currentTender) return;

    const results = findSimilarTenders(currentTender, state.tenders, 5);
    if (results.length === 0) {
        similarEl.innerHTML = `<p style="color:#888;">No similar tenders found yet.</p>`;
        return;
    }

    const norm = (v) => (v || '').toString().trim().toLowerCase();
    similarEl.innerHTML = `
        <div class="tender-similar-list">
            ${results
                .map(({ tender: t, score, keywords }) => {
                    const pct = Math.round(score * 100);
                    const whyBits = [];
                    if (keywords.length) whyBits.push(`Shared keywords: ${keywords.map(escapeHtml).join(', ')}`);
                    if (norm(currentTender.category) && norm(currentTender.category) === norm(t.category)) whyBits.push('Same category');
                    if (norm(currentTender.source) && norm(currentTender.source) === norm(t.source)) whyBits.push('Same source');
                    if (norm(currentTender.client) && norm(currentTender.client) === norm(t.client)) whyBits.push('Same client');

                    return `
                        <button type="button" class="tender-similar-item" data-ref="${escapeHtml(t.ref || '')}">
                            <div class="tender-similar-left">
                                <div class="tender-similar-ref">${escapeHtml(t.ref || '–')}</div>
                                <div class="tender-similar-title">${escapeHtml(t.title || '–')}</div>
                                <div class="tender-similar-why">${whyBits.length ? whyBits.join(' · ') : 'Similar keywords and metadata'}</div>
                            </div>
                            <div class="tender-similar-score">${pct}% match</div>
                        </button>
                    `;
                })
                .join('')}
        </div>
    `;

    similarEl.querySelectorAll('.tender-similar-item').forEach((btn) => {
        btn.addEventListener('click', () => {
            const refToOpen = btn.getAttribute('data-ref');
            const next = state.tenders.find((t) => (t?.ref || '') === refToOpen);
            if (next) openTenderModal(next);
        });
    });
}

function renderTenderStatusTimeline(tenderRef) {
    const history = getTenderStatusHistory(tenderRef);
    if (history.length === 0) {
        return `<div class="status-timeline-empty">No status updates yet.</div>`;
    }

    return `
        <div class="status-timeline">
            ${history
                .slice()
                .reverse()
                .map((e) => {
                    const meta = getStatusMeta(e.status);
                    const when = e.changedDate ? formatNiceDateTime(e.changedDate) : '–';
                    const who = e.changedBy ? escapeHtml(e.changedBy) : 'Unknown';
                    const notes = e.notes ? `<div class="status-timeline-notes">${escapeHtml(e.notes)}</div>` : '';
                    return `
                        <div class="status-timeline-item">
                            <div class="status-timeline-badge status-${meta.color}">${escapeHtml(meta.icon)} ${escapeHtml(meta.value)}</div>
                            <div class="status-timeline-meta">by <strong>${who}</strong> · ${escapeHtml(when)}</div>
                            ${notes}
                        </div>
                    `;
                })
                .join('')}
        </div>
    `;
}

function renderDiscussionTab(tender) {
    const discussionEl = document.getElementById('tenderDetailDiscussion');
    if (!discussionEl || !tender) return;

    const ref = (tender.ref || '').toString().trim();
    const user = getCurrentUsername();

    const comments = getTenderComments(ref).slice().sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp));

    const renderAttachments = (attachments) => {
        const list = Array.isArray(attachments) ? attachments : [];
        if (!list.length) return '';
        return `
            <div class="comment-attachments">
                ${list
                    .map((f) => {
                        const name = escapeHtml(f?.name || 'File');
                        const type = escapeHtml(f?.type || '');
                        const size = f?.size ? formatBytes(f.size) : '';
                        const url = escapeHtml(f?.dataUrl || '');
                        const label = [type, size].filter(Boolean).join(' · ');
                        return `
                            <a class="comment-attachment" href="${url}" download="${name}">
                                📎 ${name}${label ? `<span class="comment-attachment-meta">(${escapeHtml(label)})</span>` : ''}
                            </a>
                        `;
                    })
                    .join('')}
            </div>
        `;
    };

    const renderCommentNode = (node, depth = 0) => {
        const author = node.author || 'Unknown';
        const isOwn = user && author === user;
        const bg = hashColorForUser(author);
        const tsRel = relativeTime(node.timestamp);
        const tsFull = escapeHtml(formatNiceDateTime(node.timestamp));
        const replies = Array.isArray(node.replies) ? node.replies : [];

        return `
            <div class="comment-item" data-id="${escapeHtml(node.id)}" style="margin-left:${depth * 18}px">
                <div class="comment-avatar" style="background:${bg}">${escapeHtml(initials(author))}</div>
                <div class="comment-body">
                    <div class="comment-header">
                        <div class="comment-author">${escapeHtml(author)}</div>
                        <div class="comment-time" title="${tsFull}">${escapeHtml(tsRel)}</div>
                    </div>
                    <div class="comment-text">${renderMarkdownLite(node.text)}</div>
                    ${renderAttachments(node.attachments)}
                    <div class="comment-actions">
                        <button type="button" class="comment-action-btn" data-action="reply" data-id="${escapeHtml(node.id)}">Reply</button>
                        ${
                            isOwn
                                ? `<button type="button" class="comment-action-btn" data-action="edit" data-id="${escapeHtml(node.id)}">Edit</button>
                                   <button type="button" class="comment-action-btn danger" data-action="delete" data-id="${escapeHtml(node.id)}">Delete</button>`
                                : ''
                        }
                    </div>
                    <div class="comment-editor hidden" data-editor-for="${escapeHtml(node.id)}"></div>
                    <div class="comment-replies">
                        ${replies
                            .slice()
                            .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
                            .map((r) => renderCommentNode(r, depth + 1))
                            .join('')}
                    </div>
                </div>
            </div>
        `;
    };

    discussionEl.innerHTML = `
        <div class="discussion">
            <div class="discussion-form">
                <div class="discussion-form-header">Add a comment</div>
                <textarea id="commentText" class="discussion-textarea" rows="3" placeholder="Add a comment... (mention with @)"></textarea>
                <div class="discussion-form-row">
                    <label class="discussion-attach-btn">
                        📎 Attach files
                        <input id="commentFiles" type="file" multiple class="hidden" />
                    </label>
                    <div id="commentFilesPreview" class="discussion-files-preview"></div>
                    <button id="postCommentBtn" type="button" class="quick-filter-btn">Post</button>
                </div>
                <div class="discussion-hint">Markdown lite: **bold**, *italic*, \`code\`</div>
            </div>

            <div class="discussion-list">
                ${comments.length ? comments.map((c) => renderCommentNode(c, 0)).join('') : '<div class="discussion-empty">No comments yet.</div>'}
            </div>
        </div>
    `;

    const postBtn = document.getElementById('postCommentBtn');
    const textEl = document.getElementById('commentText');
    const filesEl = document.getElementById('commentFiles');
    const previewEl = document.getElementById('commentFilesPreview');

    let pendingFiles = [];

    const refreshPreview = () => {
        if (!previewEl) return;
        previewEl.innerHTML = pendingFiles
            .map((f, idx) => `<span class="discussion-file-chip" data-idx="${idx}">${escapeHtml(f.name)}</span>`)
            .join('');
        previewEl.querySelectorAll('.discussion-file-chip').forEach((chip) => {
            chip.addEventListener('click', () => {
                const idx = Number(chip.getAttribute('data-idx'));
                if (!Number.isFinite(idx)) return;
                pendingFiles = pendingFiles.filter((_, i) => i !== idx);
                refreshPreview();
            });
        });
    };

    if (filesEl) {
        filesEl.addEventListener('change', async () => {
            const files = Array.from(filesEl.files || []);
            const maxBytes = 2 * 1024 * 1024;
            const next = [];
            for (const file of files) {
                if (file.size > maxBytes) continue;
                const dataUrl = await new Promise((resolve) => {
                    const reader = new FileReader();
                    reader.onload = () => resolve(reader.result);
                    reader.onerror = () => resolve(null);
                    reader.readAsDataURL(file);
                });
                if (!dataUrl) continue;
                next.push({ name: file.name, type: file.type, size: file.size, dataUrl });
            }
            pendingFiles = pendingFiles.concat(next);
            refreshPreview();
            filesEl.value = '';
        });
    }

    const rerender = () => renderDiscussionTab(tender);

    if (postBtn && textEl) {
        postBtn.addEventListener('click', () => {
            const author = ensureUsername();
            if (!author) return;
            const text = (textEl.value || '').toString().trim();
            if (!text && pendingFiles.length === 0) return;

            const newComment = {
                id: newId(),
                author,
                text,
                timestamp: new Date().toISOString(),
                attachments: pendingFiles,
                replies: [],
            };

            const nextComments = getTenderComments(ref);
            nextComments.push(newComment);
            saveTenderComments(ref, nextComments);

            const mentioned = parseMentions(text).filter((m) => m !== author);
            if (mentioned.length) addMentionsForUsers(mentioned, ref, { commentId: newComment.id, from: author, timestamp: newComment.timestamp });

            pendingFiles = [];
            rerender();
        });
    }

    const findNodeById = (nodes, id) => {
        for (const n of nodes) {
            if (n.id === id) return n;
            const replies = Array.isArray(n.replies) ? n.replies : [];
            const found = findNodeById(replies, id);
            if (found) return found;
        }
        return null;
    };

    const removeNodeById = (nodes, id) => {
        for (let i = 0; i < nodes.length; i++) {
            const n = nodes[i];
            if (n.id === id) {
                nodes.splice(i, 1);
                return true;
            }
            const replies = Array.isArray(n.replies) ? n.replies : [];
            if (removeNodeById(replies, id)) return true;
        }
        return false;
    };

    discussionEl.querySelectorAll('.comment-action-btn').forEach((btn) => {
        btn.addEventListener('click', () => {
            const action = btn.getAttribute('data-action');
            const id = btn.getAttribute('data-id');
            if (!action || !id) return;

            const author = ensureUsername();
            if (!author) return;

            const all = getTenderComments(ref);
            const node = findNodeById(all, id);
            if (!node) return;
            const isOwn = node.author === author;

            const editor = discussionEl.querySelector(`[data-editor-for="${CSS.escape(id)}"]`);
            if (!editor) return;

            if (action === 'reply') {
                editor.classList.remove('hidden');
                editor.innerHTML = `
                    <textarea class="discussion-textarea" rows="2" placeholder="Write a reply..."></textarea>
                    <div class="comment-editor-actions">
                        <button type="button" class="quick-filter-btn" data-reply-submit="1">Reply</button>
                        <button type="button" class="quick-filter-btn secondary" data-reply-cancel="1">Cancel</button>
                    </div>
                `;
                const ta = editor.querySelector('textarea');
                ta?.focus();
                editor.querySelector('[data-reply-cancel]')?.addEventListener('click', () => rerender());
                editor.querySelector('[data-reply-submit]')?.addEventListener('click', () => {
                    const text = (ta?.value || '').toString().trim();
                    if (!text) return;
                    const reply = { id: newId(), author, text, timestamp: new Date().toISOString(), attachments: [], replies: [] };
                    node.replies = Array.isArray(node.replies) ? node.replies : [];
                    node.replies.push(reply);
                    saveTenderComments(ref, all);

                    const mentioned = parseMentions(text).filter((m) => m !== author);
                    if (mentioned.length) addMentionsForUsers(mentioned, ref, { commentId: reply.id, from: author, timestamp: reply.timestamp });

                    rerender();
                });
                return;
            }

            if (action === 'edit') {
                if (!isOwn) return;
                editor.classList.remove('hidden');
                editor.innerHTML = `
                    <textarea class="discussion-textarea" rows="3">${escapeHtml(node.text)}</textarea>
                    <div class="comment-editor-actions">
                        <button type="button" class="quick-filter-btn" data-edit-save="1">Save</button>
                        <button type="button" class="quick-filter-btn secondary" data-edit-cancel="1">Cancel</button>
                    </div>
                `;
                const ta = editor.querySelector('textarea');
                editor.querySelector('[data-edit-cancel]')?.addEventListener('click', () => rerender());
                editor.querySelector('[data-edit-save]')?.addEventListener('click', () => {
                    const text = (ta?.value || '').toString().trim();
                    node.text = text;
                    saveTenderComments(ref, all);
                    rerender();
                });
                return;
            }

            if (action === 'delete') {
                if (!isOwn) return;
                const ok = confirm('Delete this comment?');
                if (!ok) return;
                removeNodeById(all, id);
                saveTenderComments(ref, all);
                rerender();
            }
        });
    });
}

function openTenderModal(tender) {
    const overlay = document.getElementById('tenderDetailOverlay');
    if (!overlay || !tender) return;

    window.__currentTenderDetail = tender;

    const refEl = document.getElementById('tenderDetailRef');
    const titleEl = document.getElementById('tenderDetailTitle');
    const overviewEl = document.getElementById('tenderDetailOverview');
    const detailsEl = document.getElementById('tenderDetailDetails');
    const attachmentsEl = document.getElementById('tenderDetailAttachments');
    const similarEl = document.getElementById('tenderDetailSimilar');

    const ref = tender.ref || '–';
    const title = tender.title || '–';
    if (refEl) refEl.textContent = ref;
    if (titleEl) titleEl.textContent = title;

    const priorityRaw = (tender.priority || tender.scores?.priority || 'LOW').toString().toUpperCase();
    const priority = ['HIGH', 'MEDIUM', 'LOW'].includes(priorityRaw) ? priorityRaw : 'LOW';
    const countdownHtml = getCountdownHtml(tender.closing_date);

    // Load stored note/assignee
    let storedNote = '';
    let storedAssignee = '';
    try {
        storedNote = localStorage.getItem(`ti_tender_note::${ref}`) || '';
        storedAssignee = localStorage.getItem(`ti_tender_assignee::${ref}`) || '';
    } catch {
        // ignore
    }

    // Back-compat: migrate old assignee storage into assignment:{ref}
    let assignment = getTenderAssignment(ref);
    if (!assignment && storedAssignee) {
        setTenderAssignment(ref, storedAssignee, 'In Progress');
        assignment = getTenderAssignment(ref);
        try {
            localStorage.removeItem(`ti_tender_assignee::${ref}`);
        } catch {
            // ignore
        }
    }

    const kv = (k, v) => `<div class="tender-detail-kv"><div class="k">${escapeHtml(k)}</div><div class="v">${v || '–'}</div></div>`;
    if (overviewEl) {
        const tesScore = tender?.scores?.tes_suitability ?? tender?.scores?.tes_score ?? null;
        const phakScore = tender?.scores?.phakathi_suitability ?? tender?.scores?.phakathi_score ?? null;
        const composite = tender?.scores?.composite_score ?? tender?.scores?.composite ?? null;

        const contactRaw = tender.contact || tender.contacts || tender.contact_info || '';
        const contact = contactRaw ? escapeHtml(contactRaw) : '–';

        const assignmentSummary = assignment
            ? `Assigned to <strong>${escapeHtml(assignment.assignedTo)}</strong> on <strong>${escapeHtml(
                  assignment.assignedDate ? formatNiceDateTime(assignment.assignedDate) : '–'
              )}</strong>`
            : 'Unassigned';

        const assignmentSelectOptions = [
            `<option value="" disabled ${assignment ? '' : 'selected'}>Select assignee…</option>`,
            `<option value="__unassigned__">Unassigned</option>`,
            ...teamMembers.map((m) => `<option value="${escapeHtml(m)}"${assignment?.assignedTo === m ? ' selected' : ''}>${escapeHtml(m)}</option>`)
        ].join('');

        const currentStatus = getTenderCurrentStatus(ref);
        const statusOptions = tenderLifecycleStatuses
            .map((s) => `<option value="${escapeHtml(s.value)}"${currentStatus === s.value ? ' selected' : ''}>${escapeHtml(s.value)}</option>`)
            .join('');

        overviewEl.innerHTML = `
            <div class="tender-detail-overview">
                <div class="tender-detail-overview-top">
                    <div class="tender-detail-overview-title">${escapeHtml(title)}</div>
                    <div class="tender-detail-overview-badges">
                        <span class="priority-badge priority-${priority}">${escapeHtml(priority)}</span>
                        ${countdownHtml}
                    </div>
                </div>

                <div class="tender-detail-score-grid">
                    <div class="tender-score-card">
                        <div class="tender-score-label">TES score</div>
                        <div class="tender-score-value">${Number.isFinite(Number(tesScore)) ? escapeHtml(String(tesScore)) : '–'}</div>
                    </div>
                    <div class="tender-score-card">
                        <div class="tender-score-label">Phakathi score</div>
                        <div class="tender-score-value">${Number.isFinite(Number(phakScore)) ? escapeHtml(String(phakScore)) : '–'}</div>
                    </div>
                    <div class="tender-score-card">
                        <div class="tender-score-label">Composite</div>
                        <div class="tender-score-value">${Number.isFinite(Number(composite)) ? escapeHtml(String(composite)) : '–'}</div>
                    </div>
                </div>

                <div class="tender-detail-overview-meta">
                    ${kv('Client', escapeHtml(tender.client || '–'))}
                    ${kv('Source', escapeHtml(tender.source || '–'))}
                    ${kv('Company', escapeHtml(getCompany(tender) || '–'))}
                    ${kv('Closing', escapeHtml(formatNiceDateTime(tender.closing_date, tender.closing_time)))}
                    ${kv('Contact', contact)}
                </div>

                <div class="tender-detail-section-title">Assignment</div>
                <div class="tender-assignment-box">
                    <div id="tenderAssignmentSummary" class="tender-assignment-summary">${assignmentSummary}</div>
                    <div class="tender-assignment-actions">
                        <button id="tenderAssignmentChangeBtn" type="button" class="quick-filter-btn">Change assignment</button>
                    </div>
                    <div id="tenderAssignmentControls" class="tender-assignment-controls hidden">
                        <select id="tenderAssignmentSelect" class="assignment-select">
                            ${assignmentSelectOptions}
                        </select>
                    </div>
                </div>

                <div class="tender-detail-section-title">Status</div>
                <div class="tender-status-box">
                    <div class="tender-status-actions">
                        <select id="tenderLifecycleStatus" class="assignment-select tender-status-select">
                            ${statusOptions}
                        </select>
                        <button id="tenderStatusUpdateBtn" type="button" class="quick-filter-btn">Update Status</button>
                    </div>
                    <textarea id="tenderStatusNotes" class="tender-status-notes" rows="2" placeholder="Optional notes (e.g., pricing started, reviewer assigned)"></textarea>
                    <div id="tenderStatusTimeline">${renderTenderStatusTimeline(ref)}</div>
                </div>

                <div class="tender-detail-section-title">Description</div>
                <div class="tender-detail-description">${escapeHtml(tender.description || tender.long_description || '–')}</div>
            </div>
        `;

        const changeBtn = document.getElementById('tenderAssignmentChangeBtn');
        const controls = document.getElementById('tenderAssignmentControls');
        const assignSelect = document.getElementById('tenderAssignmentSelect');
        const summaryEl = document.getElementById('tenderAssignmentSummary');
        const lifecycleSelect = document.getElementById('tenderLifecycleStatus');
        const lifecycleBtn = document.getElementById('tenderStatusUpdateBtn');
        const lifecycleNotes = document.getElementById('tenderStatusNotes');
        const timelineMount = document.getElementById('tenderStatusTimeline');

        const refreshAssignmentSummary = () => {
            const a = getTenderAssignment(ref);
            if (!summaryEl) return;
            if (!a) {
                summaryEl.innerHTML = 'Unassigned';
                return;
            }
            summaryEl.innerHTML = `Assigned to <strong>${escapeHtml(a.assignedTo)}</strong> on <strong>${escapeHtml(
                a.assignedDate ? formatNiceDateTime(a.assignedDate) : '–'
            )}</strong>`;
        };

        if (changeBtn && controls) {
            changeBtn.addEventListener('click', () => {
                controls.classList.toggle('hidden');
                assignSelect?.focus();
            });
        }

        if (assignSelect) {
            assignSelect.addEventListener('click', (e) => e.stopPropagation());
            assignSelect.addEventListener('change', () => {
                const val = (assignSelect.value || '').toString();
                if (val === '__unassigned__') {
                    clearTenderAssignment(ref);
                } else if (val) {
                    setTenderAssignment(ref, val, getTenderCurrentStatus(ref) || 'Not Started');
                }
                refreshAssignmentSummary();
                requestRenderTenders();
            });
        }

        const refreshTimeline = () => {
            if (timelineMount) timelineMount.innerHTML = renderTenderStatusTimeline(ref);
        };

        if (lifecycleSelect && lifecycleBtn) {
            lifecycleSelect.addEventListener('click', (e) => e.stopPropagation());
            lifecycleBtn.addEventListener('click', () => {
                const nextStatus = (lifecycleSelect.value || '').toString();
                const notes = (lifecycleNotes?.value || '').toString();
                const actor = ensureUsername() || getCurrentUsername() || 'Unknown';
                if (tenderFinalStatuses.has(nextStatus)) {
                    const ok = confirm(`Confirm setting tender status to "${nextStatus}"?`);
                    if (!ok) return;
                }
                setTenderLifecycleStatus(ref, nextStatus, { notes, changedBy: actor });
                if (lifecycleNotes) lifecycleNotes.value = '';
                refreshTimeline();
                requestRenderTenders();
            });
        }
    }

    if (detailsEl) {
        const pick = (keys) => {
            for (const k of keys) {
                const v = tender?.[k];
                if (v !== undefined && v !== null && String(v).trim() !== '') return v;
            }
            return null;
        };

        const published = pick(['published_date', 'published', 'publish_date', 'date_published', 'issue_date', 'created_at']);
        const closing = pick(['closing_date', 'close_date', 'closing']);
        const closingTime = pick(['closing_time', 'close_time']);
        const estValue = pick(['estimated_value', 'est_value', 'value', 'budget', 'estimatedValue']);
        const briefing = pick(['briefing_session', 'briefing', 'briefing_date']);
        const compulsory = pick(['compulsory', 'briefing_compulsory', 'is_compulsory']);
        const compulsoryText =
            compulsory === true ? 'Compulsory' : compulsory === false ? 'Non-compulsory' : compulsory ? String(compulsory) : '–';

        const row = (k, v) => kv(k, escapeHtml(v ?? '–'));
        let sourceUrl = tender.url || '';
        if (sourceUrl) {
            try {
                sourceUrl = encodeURI(sourceUrl);
            } catch {
                // ignore
            }
        }
        detailsEl.innerHTML = `
            <div class="tender-detail-kv-grid">
                ${row('Reference Number', tender.ref || '–')}
                ${row('Category', tender.category || '–')}
                ${row('Published Date', published ? formatNiceDateTime(published) : '–')}
                ${row('Closing Date & Time', closing ? formatNiceDateTime(closing, closingTime) : '–')}
                ${row('Estimated Value', estValue || '–')}
                ${row('Briefing Session', briefing ? formatNiceDateTime(briefing) : '–')}
                ${row('Compulsory/Non-compulsory', compulsoryText)}
                ${row('Notes', storedNote || tender.notes || tender.reason || '–')}
                ${kv(
                    'Source link',
                    sourceUrl
                        ? `<a href="${escapeHtml(sourceUrl)}" target="_blank" rel="noopener" style="color:#48dbfb;">Open ↗</a>`
                        : '–'
                )}
            </div>
        `;
    }

    if (attachmentsEl) {
        const attachments = normalizeAttachments(tender);
        if (attachments.length === 0) {
            attachmentsEl.innerHTML = `<p style="color:#888;">No documents listed for this tender.</p>`;
        } else {
            attachmentsEl.innerHTML = `
                <div class="tender-attachments-list">
                    ${attachments
                        .map((a, i) => {
                            const icon = getAttachmentIcon(a.ext);
                            const size = a.size ? formatBytes(a.size) : '–';
                            const displayName = a.name === 'Main Document' ? '📄 Main Document' : escapeHtml(a.name);
                            return `
                                <div class="tender-attachment-item">
                                    <div class="tender-attachment-left">
                                        <div class="tender-attachment-icon">${icon}</div>
                                        <div class="tender-attachment-meta">
                                            <div class="tender-attachment-name">${displayName}</div>
                                            <div class="tender-attachment-sub">${escapeHtml((a.ext || 'file').toUpperCase())} · <span id="attachmentSize_${i}">${escapeHtml(size)}</span></div>
                                        </div>
                                    </div>
                                    <div class="tender-attachment-actions">
                                        <a class="quick-filter-btn" href="${escapeHtml(a.url)}" target="_blank" rel="noopener">View</a>
                                        <a class="quick-filter-btn" href="${escapeHtml(a.url)}" download>Download</a>
                                    </div>
                                </div>
                            `;
                        })
                        .join('')}
                </div>
            `;

            // Best-effort: attempt to fetch Content-Length for unknown sizes
            attachments.forEach((a, i) => {
                if (!a?.url || a.size) return;
                try {
                    fetch(a.url, { method: 'HEAD' })
                        .then((res) => {
                            const len = res.headers.get('content-length');
                            const sizeEl = document.getElementById(`attachmentSize_${i}`);
                            if (!sizeEl) return;
                            if (len) sizeEl.textContent = formatBytes(Number(len));
                        })
                        .catch(() => {});
                } catch {
                    // ignore
                }
            });
        }
    }

    if (similarEl) {
        similarEl.innerHTML = `<p style="color:#888;">Open the “Similar” tab to calculate matches.</p>`;
    }

    const discussionEl = document.getElementById('tenderDetailDiscussion');
    if (discussionEl) {
        discussionEl.innerHTML = `<p style="color:#888;">Open the “Discussion” tab to view and post comments.</p>`;
    }

    updateMentionBadgesForTender(tender);

    // Wire footer actions
    const viewBtn = document.getElementById('tenderDetailViewSource');
    if (viewBtn) {
        viewBtn.onclick = () => {
            if (!tender.url) return;
            try {
                window.open(encodeURI(tender.url), '_blank', 'noopener');
            } catch {
                window.open(tender.url, '_blank', 'noopener');
            }
        };
    }
    const noteBtn = document.getElementById('tenderDetailAddNote');
    if (noteBtn) {
        noteBtn.onclick = () => {
            const note = prompt('Add a note for this tender:', storedNote || '');
            if (note === null) return;
            try {
                localStorage.setItem(`ti_tender_note::${ref}`, note);
            } catch {
                // ignore
            }
            openTenderModal(tender);
        };
    }
    const assignBtn = document.getElementById('tenderDetailAssign');
    if (assignBtn) {
        assignBtn.onclick = () => {
            setTenderDetailTab('overview');
            const controls = document.getElementById('tenderAssignmentControls');
            const select = document.getElementById('tenderAssignmentSelect');
            controls?.classList.remove('hidden');
            select?.focus();
        };
    }

    // Reset to overview tab on open
    setTenderDetailTab('overview');

    overlay.classList.add('active');
    document.body.classList.add('modal-open');
    const closeBtn = document.getElementById('tenderDetailCloseBtn');
    closeBtn?.focus();
}

function closeTenderModal() {
    const overlay = document.getElementById('tenderDetailOverlay');
    if (!overlay) return;
    overlay.classList.remove('active');
    document.body.classList.remove('modal-open');

    const refEl = document.getElementById('tenderDetailRef');
    const titleEl = document.getElementById('tenderDetailTitle');
    if (refEl) refEl.textContent = '–';
    if (titleEl) titleEl.textContent = 'Tender details';

    const overviewEl = document.getElementById('tenderDetailOverview');
    const detailsEl = document.getElementById('tenderDetailDetails');
    const attachmentsEl = document.getElementById('tenderDetailAttachments');
    const similarEl = document.getElementById('tenderDetailSimilar');
    const discussionEl = document.getElementById('tenderDetailDiscussion');
    if (overviewEl) overviewEl.innerHTML = '';
    if (detailsEl) detailsEl.innerHTML = '';
    if (attachmentsEl) attachmentsEl.innerHTML = '';
    if (similarEl) similarEl.innerHTML = '';
    if (discussionEl) discussionEl.innerHTML = '';

    window.__currentTenderDetail = null;
}

function setTenderDetailTab(tab) {
    const tabs = document.querySelectorAll('.tender-detail-tab');
    const panels = {
        overview: document.getElementById('tenderTabOverview'),
        details: document.getElementById('tenderTabDetails'),
        attachments: document.getElementById('tenderTabAttachments'),
        similar: document.getElementById('tenderTabSimilar'),
        discussion: document.getElementById('tenderTabDiscussion')
    };

    tabs.forEach((btn) => {
        const isActive = btn.getAttribute('data-tab') === tab;
        btn.classList.toggle('active', isActive);
        btn.setAttribute('aria-selected', isActive ? 'true' : 'false');
    });

    Object.entries(panels).forEach(([key, el]) => {
        if (!el) return;
        el.classList.toggle('active', key === tab);
    });

    if (tab === 'similar') {
        try {
            renderSimilarTendersTab(window.__currentTenderDetail);
        } catch (e) {
            console.warn('Failed to render similar tenders:', e);
        }
    }

    if (tab === 'discussion') {
        try {
            const tender = window.__currentTenderDetail;
            const ref = tender?.ref;
            const user = getCurrentUsername();
            if (ref && user) clearMentionsForTender(ref, user);
            renderDiscussionTab(tender);
            updateMentionBadgesForTender(tender);
            requestRenderTenders();
        } catch (e) {
            console.warn('Failed to render discussion:', e);
        }
    }
}

class TenderAnalytics {
    constructor(tenders) {
        const items = Array.isArray(tenders) ? tenders : [];

        this.bySource = {};
        this.byDate = {};
        this.byPriority = { HIGH: 0, MEDIUM: 0, LOW: 0 };
        this.byWeek = [];
        this.keywords = {};

        const byWeekMap = new Map(); // key: `${isoYear}-W${isoWeek}`
        const stopwords = new Set(['tender', 'supply', 'services', 'provision', 'water', 'system', 'treatment']);

        items.forEach((item) => {
            const tender = item?.tender || item;
            if (!tender || typeof tender !== 'object') return;

            const source = (tender.source || 'Unknown').trim();
            this.bySource[source] = (this.bySource[source] || 0) + 1;

            const priority = (tender.priority || tender.scores?.priority || 'LOW').toUpperCase();
            if (this.byPriority[priority] === undefined) this.byPriority[priority] = 0;
            this.byPriority[priority] += 1;

            if (tender.closing_date) {
                const dateStr = tender.closing_date.split('T')[0];
                this.byDate[dateStr] = (this.byDate[dateStr] || 0) + 1;

                const closing = new Date(tender.closing_date);
                if (!Number.isNaN(closing.getTime())) {
                    const { isoYear, isoWeek } = TenderAnalytics.getISOWeek(closing);
                    const key = `${isoYear}-W${isoWeek}`;
                    byWeekMap.set(key, (byWeekMap.get(key) || 0) + 1);
                }
            }

            const text = `${tender.title || ''} ${tender.description || ''}`.toLowerCase();
            text
                .split(/\s+/)
                .map((w) => w.replace(/[^\p{L}\p{N}-]+/gu, ''))
                .filter((w) => w.length > 4 && !stopwords.has(w))
                .forEach((word) => {
                    if (!word) return;
                    this.keywords[word] = (this.keywords[word] || 0) + 1;
                });
        });

        this.byWeek = Array.from(byWeekMap.entries())
            .map(([key, count]) => {
                const weekPart = key.split('W')[1] || '';
                const weekNo = weekPart.replace(/[^0-9]/g, '');
                return { week: `Week ${weekNo || key}`, count };
            })
            .sort((a, b) => {
                const aNum = parseInt(a.week.replace('Week ', ''), 10);
                const bNum = parseInt(b.week.replace('Week ', ''), 10);
                if (Number.isFinite(aNum) && Number.isFinite(bNum)) return aNum - bNum;
                return a.week.localeCompare(b.week);
            });
    }

    static getISOWeek(date) {
        const d = new Date(date);
        d.setHours(0, 0, 0, 0);
        // Thursday in current week decides the year.
        d.setDate(d.getDate() + 3 - ((d.getDay() + 6) % 7));
        const isoYear = d.getFullYear();
        const week1 = new Date(isoYear, 0, 4);
        week1.setHours(0, 0, 0, 0);
        const weekNumber = 1 + Math.round((((d - week1) / 86400000) - 3 + ((week1.getDay() + 6) % 7)) / 7);
        return { isoYear, isoWeek: weekNumber };
    }

    getTopSource() {
        const entries = Object.entries(this.bySource).sort((a, b) => b[1] - a[1]);
        return entries[0]?.[0] || '–';
    }

    getAvgTendersPerWeek() {
        if (!this.byWeek.length) return 0;
        const total = this.byWeek.reduce((sum, w) => sum + (w.count || 0), 0);
        return Math.round(total / this.byWeek.length);
    }

    getMostActiveDay() {
        const dayNames = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat'];
        const dayCounts = { 0: 0, 1: 0, 2: 0, 3: 0, 4: 0, 5: 0, 6: 0 };

        Object.entries(this.byDate).forEach(([dateStr, count]) => {
            const d = new Date(`${dateStr}T00:00:00`);
            if (Number.isNaN(d.getTime())) return;
            dayCounts[d.getDay()] += count;
        });

        const max = Object.entries(dayCounts).reduce((best, [day, count]) => (count > best[1] ? [day, count] : best), ['0', 0]);
        return dayNames[parseInt(max[0], 10)] || '–';
    }

    getTopKeywords(limit = 20) {
        return Object.entries(this.keywords)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit);
    }

    getTendersThisMonth() {
        const now = new Date();
        const currentMonth = now.getMonth();
        const currentYear = now.getFullYear();

        let count = 0;
        Object.entries(this.byDate).forEach(([dateStr, c]) => {
            const d = new Date(`${dateStr}T00:00:00`);
            if (Number.isNaN(d.getTime())) return;
            if (d.getFullYear() === currentYear && d.getMonth() === currentMonth) count += c;
        });
        return count;
    }
}

function formatNumberOrDash(value) {
    if (!Number.isFinite(value)) return '–';
    return new Intl.NumberFormat('en-US').format(value);
}

function setTextOrDash(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const v = (value ?? '').toString().trim();
    el.textContent = v ? v : '–';
}

function setNumberOrDash(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = formatNumberOrDash(value);
}

function setChartFallback(message) {
    const ids = ['trendChart', 'sourceChart', 'priorityChart'];
    ids.forEach((id) => {
        const canvas = document.getElementById(id);
        if (!canvas) return;
        canvas.style.display = 'none';
        const msgId = `${id}-fallback`;
        let msg = document.getElementById(msgId);
        if (!msg) {
            msg = document.createElement('div');
            msg.id = msgId;
            msg.style.color = '#ffb3b3';
            msg.style.fontSize = '0.9rem';
            msg.style.marginTop = '10px';
            canvas.insertAdjacentElement('afterend', msg);
        }
        msg.textContent = message;
    });
}

function getLastNDaysSeries(tendersByDate, days = 30) {
    const byDate = tendersByDate || {};
    const labels = [];
    const values = [];

    const today = new Date();
    today.setHours(0, 0, 0, 0);

    for (let i = days - 1; i >= 0; i--) {
        const d = new Date(today);
        d.setDate(today.getDate() - i);
        const key = d.toISOString().split('T')[0];
        labels.push(key);
        values.push(byDate[key] || 0);
    }

    return { labels, values };
}

function getChartTheme() {
    return {
        text: '#fff',
        grid: 'rgba(255,255,255,0.1)'
    };
}

function getChartAnimation() {
    return { duration: 1000, easing: 'easeInOutQuart' };
}

function renderKeywordCloud(keywords) {
    const container = document.getElementById('analytics-keyword-cloud');
    if (!container) return;

    const tuples = Array.isArray(keywords) ? keywords : [];
    container.innerHTML = '';

    if (tuples.length === 0) {
        const empty = document.createElement('div');
        empty.style.color = '#888';
        empty.textContent = 'No keyword data available.';
        container.appendChild(empty);
        return;
    }

    const counts = tuples.map(([, c]) => c).filter((c) => Number.isFinite(c));
    const max = Math.max(...counts, 1);
    const min = Math.min(...counts, max);
    const range = max - min || 1;

    const start = { r: 0x66, g: 0x7e, b: 0xea }; // #667eea
    const end = { r: 0x76, g: 0x4b, b: 0xa2 }; // #764ba2
    const lerp = (a, b, t) => Math.round(a + (b - a) * t);
    const toHex = (n) => n.toString(16).padStart(2, '0');
    const lerpColor = (t) => {
        const r = lerp(start.r, end.r, t);
        const g = lerp(start.g, end.g, t);
        const b = lerp(start.b, end.b, t);
        return `#${toHex(r)}${toHex(g)}${toHex(b)}`;
    };

    const clamp01 = (n) => Math.max(0, Math.min(1, n));
    const toSize = (t) => 0.8 + t * (2.5 - 0.8);
    const toOpacity = (t) => 0.4 + t * (1.0 - 0.4);

    const goToDashboardAndFilter = (word) => {
        const dashBtn = Array.from(document.querySelectorAll('.tab-btn')).find((b) =>
            (b.getAttribute('onclick') || '').includes("showTab('dashboard')")
        );
        if (dashBtn) dashBtn.click();

        const searchBox = document.getElementById('tenderSearchBox');
        if (searchBox) searchBox.value = word;
        if (typeof smartSearchTenders === 'function') smartSearchTenders(word);

        const list = document.getElementById('tenderList') || document.getElementById('tender-table-body');
        if (list) {
            list.scrollIntoView({ behavior: 'smooth', block: 'start' });
        } else {
            const section = document.querySelector('.active-tenders-section');
            section?.scrollIntoView({ behavior: 'smooth', block: 'start' });
        }
    };

    tuples.forEach(([word, count]) => {
        const c = Number.isFinite(count) ? count : 0;
        const t = clamp01((c - min) / range);

        const span = document.createElement('span');
        span.className = 'keyword-cloud-word';
        span.textContent = word;
        span.style.fontSize = `${toSize(t)}rem`;
        span.style.opacity = String(toOpacity(t));
        span.style.color = lerpColor(t);
        span.title = `${word} (${c})`;

        span.addEventListener('click', () => goToDashboardAndFilter(word));
        container.appendChild(span);
    });
}

function renderTrendChart(tendersByDate) {
    const canvas = document.getElementById('trendChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const { labels, values } = getLastNDaysSeries(tendersByDate, 30);
    const ctx = canvas.getContext('2d');
    const theme = getChartTheme();

    const gradient = ctx.createLinearGradient(0, 0, 0, canvas.height || 400);
    gradient.addColorStop(0, 'rgba(102,126,234,0.45)');
    gradient.addColorStop(1, 'rgba(118,75,162,0.05)');

    const lineGradient = ctx.createLinearGradient(0, 0, canvas.width || 400, 0);
    lineGradient.addColorStop(0, '#667eea');
    lineGradient.addColorStop(1, '#764ba2');

    window.__analyticsCharts = window.__analyticsCharts || {};
    const existing = window.__analyticsCharts.trend;
    if (existing) {
        existing.data.labels = labels;
        existing.data.datasets[0].data = values;
        existing.update();
        return;
    }

    window.__analyticsCharts.trend = new Chart(canvas, {
        type: 'line',
        data: {
            labels,
            datasets: [
                {
                    label: 'Tenders',
                    data: values,
                    borderColor: lineGradient,
                    backgroundColor: gradient,
                    fill: true,
                    tension: 0.35,
                    pointRadius: 2,
                    pointHoverRadius: 4,
                }
            ]
        },
        options: {
            responsive: true,
            animation: getChartAnimation(),
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true }
            },
            scales: {
                x: {
                    ticks: {
                        color: theme.text,
                        maxRotation: 0,
                        autoSkip: true,
                        callback: (value, index) => {
                            const label = labels[index] || '';
                            return label.slice(5); // MM-DD
                        }
                    },
                    grid: { color: theme.grid }
                },
                y: {
                    beginAtZero: true,
                    ticks: { color: theme.text, precision: 0 },
                    grid: { color: theme.grid }
                }
            }
        }
    });
}

function renderSourcePieChart(bySource) {
    const canvas = document.getElementById('sourceChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const theme = getChartTheme();
    const entries = Object.entries(bySource || {}).sort((a, b) => b[1] - a[1]);
    const top = entries.slice(0, 8);
    const other = entries.slice(8).reduce((sum, [, c]) => sum + c, 0);
    if (other > 0) top.push(['Other', other]);

    const labels = top.map(([k]) => k);
    const data = top.map(([, v]) => v);
    const total = data.reduce((a, b) => a + b, 0) || 1;

    const palette = [
        '#667eea',
        '#48dbfb',
        '#a29bfe',
        '#764ba2',
        '#5f27cd',
        '#54a0ff',
        '#c8d6e5',
        'rgba(255,255,255,0.35)'
    ];

    const percentLabelsPlugin = {
        id: 'percentLabels',
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            ctx.save();
            ctx.fillStyle = '#fff';
            ctx.font = '12px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif';
            meta.data.forEach((arc, i) => {
                const value = chart.data.datasets[0].data[i] || 0;
                const pct = Math.round((value / total) * 100);
                if (pct < 6) return; // skip tiny slices
                const pos = arc.tooltipPosition();
                ctx.fillText(`${pct}%`, pos.x - 10, pos.y + 4);
            });
            ctx.restore();
        }
    };

    window.__analyticsCharts = window.__analyticsCharts || {};
    const existing = window.__analyticsCharts.source;
    if (existing) {
        existing.data.labels = labels;
        existing.data.datasets[0].data = data;
        existing.update();
        return;
    }

    window.__analyticsCharts.source = new Chart(canvas, {
        type: 'pie',
        data: {
            labels,
            datasets: [
                {
                    data,
                    backgroundColor: labels.map((_, idx) => palette[idx % palette.length]),
                    borderColor: 'rgba(0,0,0,0)',
                    borderWidth: 0
                }
            ]
        },
        options: {
            responsive: true,
            animation: getChartAnimation(),
            plugins: {
                legend: {
                    position: 'right',
                    labels: { color: theme.text }
                },
                tooltip: {
                    callbacks: {
                        label: (ctx) => {
                            const v = ctx.parsed || 0;
                            const pct = Math.round((v / total) * 100);
                            return `${ctx.label}: ${v} (${pct}%)`;
                        }
                    }
                }
            }
        },
        plugins: [percentLabelsPlugin]
    });
}

function renderPriorityBarChart(byPriority) {
    const canvas = document.getElementById('priorityChart');
    if (!canvas || typeof Chart === 'undefined') return;

    const theme = getChartTheme();
    const pri = byPriority || { HIGH: 0, MEDIUM: 0, LOW: 0 };
    const labels = ['HIGH', 'MEDIUM', 'LOW'];
    const data = [pri.HIGH || 0, pri.MEDIUM || 0, pri.LOW || 0];

    const countLabelsPlugin = {
        id: 'countLabels',
        afterDatasetsDraw(chart) {
            const { ctx } = chart;
            const meta = chart.getDatasetMeta(0);
            ctx.save();
            ctx.fillStyle = '#fff';
            ctx.font = '12px -apple-system, BlinkMacSystemFont, Segoe UI, Roboto, sans-serif';
            meta.data.forEach((bar, i) => {
                const value = chart.data.datasets[0].data[i] || 0;
                const pos = bar.tooltipPosition();
                ctx.fillText(String(value), pos.x + 8, pos.y + 4);
            });
            ctx.restore();
        }
    };

    window.__analyticsCharts = window.__analyticsCharts || {};
    const existing = window.__analyticsCharts.priority;
    if (existing) {
        existing.data.labels = labels;
        existing.data.datasets[0].data = data;
        existing.update();
        return;
    }

    window.__analyticsCharts.priority = new Chart(canvas, {
        type: 'bar',
        data: {
            labels,
            datasets: [
                {
                    label: 'Count',
                    data,
                    backgroundColor: ['#ff6b6b', '#feca57', '#48dbfb'],
                    borderRadius: 10,
                    borderSkipped: false
                }
            ]
        },
        options: {
            indexAxis: 'y',
            responsive: true,
            animation: getChartAnimation(),
            plugins: {
                legend: { display: false },
                tooltip: { enabled: true }
            },
            scales: {
                x: {
                    beginAtZero: true,
                    ticks: { color: theme.text, precision: 0 },
                    grid: { color: theme.grid }
                },
                y: {
                    ticks: { color: theme.text },
                    grid: { color: theme.grid }
                }
            }
        },
        plugins: [countLabelsPlugin]
    });
}

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');

    if (tabId === 'calendar') renderCalendar();
    if (tabId === 'analytics') {
        if (analyticsInitTimer) clearTimeout(analyticsInitTimer);
        analyticsInitTimer = setTimeout(() => {
            initializeAnalytics();
        }, 150);
    }
    if (tabId === 'sources') renderScraperHealth(typeof globalData !== 'undefined' ? globalData.scraperHealth : {});
}

function renderCalendar() {
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
}

function showDayTenders(dateStr) {
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
}

function initializeAnalytics() {
    if (analyticsInitialized) return;
    if (!state.tenders || state.tenders.length === 0) {
        setNumberOrDash('analytics-total-month', NaN);
        setNumberOrDash('analytics-avg-per-week', NaN);
        setTextOrDash('analytics-top-source', '');
        setTextOrDash('analytics-most-active-day', '');
        return;
    }

    analyticsInitialized = true;

    const signature = JSON.stringify({
        count: state.tenders.length,
        lastSync: window.dashboardMeta?.last_sync || window.dashboardMeta?.build_id || ''
    });

    try {
        sessionStorage.setItem('ti_analytics_signature', signature);
    } catch {
        // ignore session storage failures
    }

    const analytics = new TenderAnalytics(state.tenders);

    // Update stat cards
    setNumberOrDash('analytics-total-month', analytics.getTendersThisMonth());
    setNumberOrDash('analytics-avg-per-week', analytics.getAvgTendersPerWeek());
    setTextOrDash('analytics-top-source', analytics.getTopSource());
    setTextOrDash('analytics-most-active-day', analytics.getMostActiveDay());

    // Render keyword cloud
    try {
        renderKeywordCloud(analytics.getTopKeywords(40));
    } catch (err) {
        console.error('Keyword cloud render failed:', err);
    }

    // Render charts with error handling
    try {
        if (typeof Chart === 'undefined') {
            setChartFallback('Charts unavailable (Chart.js failed to load).');
            console.warn('Chart.js not loaded; analytics charts skipped.');
            return;
        }
        renderTrendChart(analytics.byDate);
        renderSourcePieChart(analytics.bySource);
        renderPriorityBarChart(analytics.byPriority);
    } catch (err) {
        console.error('Analytics chart render failed:', err);
        setChartFallback('Charts unavailable (render error).');
    }
}

function changeMonth(delta) {
    state.currentMonth.setMonth(state.currentMonth.getMonth() + delta);
    renderCalendar();
}

function applyTenderPayload({ loadedTenders, meta, source, storedAt, error }) {
    const effectiveMeta = meta || {};

    state.tenders = loadedTenders.map(normalizeTender);
    resetTenderInfiniteList();
    window.tendersData = state.tenders;
    window.dashboardMeta = effectiveMeta;
    analyticsInitialized = false;
    
    // Store allTenders globally for notifications
    window.allTenders = state.tenders;

    const lastSyncEl = document.getElementById("last-sync-text");
    const nextRunEl = document.getElementById("next-run-text");

    if (lastSyncEl && effectiveMeta.last_sync) {
        lastSyncEl.textContent = effectiveMeta.last_sync;
    }
    if (nextRunEl && effectiveMeta.next_run) {
        nextRunEl.textContent = effectiveMeta.next_run;
    }

    const updated = effectiveMeta.build_id || effectiveMeta.last_sync || storedAt || "–";
    const level = source === "localStorage" || source === "seed" ? "warn" : "ok";
    setDataStatus({
        level,
        source: source || "unknown",
        count: loadedTenders.length,
        updated,
        error: error || (level === "warn" && source === "seed" ? "No live data available yet (showing seed)." : "")
    });

    renderTenders();
    updatePrintHeader(effectiveMeta || initialMeta, getKpiSummary());
    
	    // Dispatch event for notifications system
	    window.dispatchEvent(
	        new CustomEvent('tendersLoaded', {
	            detail: {
	                tenders: state.tenders
	            }
	        })
	    );
	}

function refreshDashboardData() {
    const btn = document.getElementById("refresh-data-btn");
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Refreshing…";
    }

    if (typeof navigator !== 'undefined' && navigator.onLine === false) {
        enqueueOfflineAction({ type: 'refresh' });
    }

    return loadTenderPayload({ forceRefresh: true })
        .then(applyTenderPayload)
        .catch(err => {
            console.error("Error refreshing tenders:", err);
            setDataStatus({ level: "err", source: "error", count: 0, updated: "–", error: err });
        })
        .finally(() => {
            if (btn) {
                btn.disabled = false;
                btn.textContent = "Refresh data";
            }
        });
}

// ====================================
// Advanced Filters Integration
// ====================================
let advancedFiltersInstance = null;

function toggleAdvancedFilters() {
    const panel = document.getElementById('advancedFiltersPanel');
    if (panel) {
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
        
        // Initialize filters if first time opening
        if (panel.style.display === 'block' && !advancedFiltersInstance) {
            initializeAdvancedFilters();
        }
    }
}

function initializeAdvancedFilters() {
    if (!window.AdvancedFilters) return;
    
    advancedFiltersInstance = new window.AdvancedFilters();
    advancedFiltersInstance.setTenders(state.currentTenders.map((t, idx) => ({
        tender: t,
        classification: classifyTender(t)
    })));
    
    // Set up callback for filter changes
    advancedFiltersInstance.onFilterChange = (filteredTenders) => {
        renderFilteredTenders(filteredTenders);
        updateActiveFilterCount();
    };
    
    // Set up event listeners
    const searchBox = document.getElementById('advancedSearchBox');
    if (searchBox) {
        searchBox.addEventListener('input', (e) => {
            if (window.SmartSearch && e.target.value.trim()) {
                const smartFiltered = window.SmartSearch.applySmartFilters(
                    advancedFiltersInstance.allTenders,
                    e.target.value
                );
                renderFilteredTenders(smartFiltered);
            } else {
                advancedFiltersInstance.setSearchTerm(e.target.value);
            }
        });
    }
    
    const dateStart = document.getElementById('dateStart');
    const dateEnd = document.getElementById('dateEnd');
    if (dateStart && dateEnd) {
        dateStart.addEventListener('change', () => {
            advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
        });
        dateEnd.addEventListener('change', () => {
            advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
        });
    }
    
    // Load saved searches into dropdown
    const savedSelect = document.getElementById('savedSearchSelect');
    if (savedSelect) {
        updateSavedSearchesDropdown();
        savedSelect.addEventListener('change', (e) => {
            if (e.target.value) {
                advancedFiltersInstance.loadSearch(e.target.value);
                renderFilteredTenders(advancedFiltersInstance.getFilteredTenders());
                updateActiveFilterCount();
            }
        });
    }
}

function setQuickDateFilter(type) {
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
    
    if (advancedFiltersInstance) {
        advancedFiltersInstance.setDateRange(dateStart.value, dateEnd.value);
    }
}

function saveCurrentSearch() {
    if (!advancedFiltersInstance) return;
    
    const name = prompt('Enter a name for this search:');
    if (name) {
        advancedFiltersInstance.saveSearch(name);
        updateSavedSearchesDropdown();
        alert('Search saved successfully!');
    }
}

function deleteSavedSearch() {
    const savedSelect = document.getElementById('savedSearchSelect');
    if (!savedSelect || !savedSelect.value) {
        alert('Please select a saved search to delete');
        return;
    }
    
    if (confirm(`Delete saved search "${savedSelect.value}"?`)) {
        advancedFiltersInstance.deleteSavedSearch(savedSelect.value);
        updateSavedSearchesDropdown();
        savedSelect.value = '';
    }
}

function updateSavedSearchesDropdown() {
    const savedSelect = document.getElementById('savedSearchSelect');
    if (!savedSelect || !advancedFiltersInstance) return;
    
    const searches = advancedFiltersInstance.activeFilters.savedSearches;
    savedSelect.innerHTML = '<option value="">-- Select Saved Search --</option>';
    
    searches.forEach(search => {
        const option = document.createElement('option');
        option.value = search.name;
        option.textContent = search.name;
        savedSelect.appendChild(option);
    });
}

function clearAllAdvancedFilters() {
    if (!advancedFiltersInstance) return;
    
    advancedFiltersInstance.clearAllFilters();
    
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
}

function updateActiveFilterCount() {
    const countDiv = document.getElementById('activeFilterCount');
    if (!countDiv || !advancedFiltersInstance) return;
    
    const count = advancedFiltersInstance.getActiveFilterCount();
    countDiv.textContent = count === 0 ? 'No filters active' : `${count} filter${count > 1 ? 's' : ''} active`;
}

function renderFilteredTenders(filteredTenders) {
    const list = document.getElementById('tender-table-body') || document.getElementById('tenderList');
    if (!list) return;

    const raw = Array.isArray(filteredTenders) ? filteredTenders : [];
    const all = raw.map((t) => (t && typeof t === 'object' && 'tender' in t) ? t : ({ tender: t, classification: classifyTender(t) }));
    state.totalMatchingCount = all.length;
    const visibleCount = Math.min(state.visibleTenderCount || CHUNK_SIZE, all.length);
    window.__virtualListItems = all.slice(0, visibleCount);
    virtualScrollContainer = virtualScrollContainer || document.getElementById('tenderTableScroll');
    virtualScrollTbody = list;
    virtualLastKey = '';
    updateTenderLoadProgress(window.__virtualListItems.length, all.length);

    const countEl = document.getElementById('tenderResultsCount');
    if (countEl) {
        countEl.textContent = `Showing ${window.__virtualListItems.length} of ${all.length}`;
    }

    if (state.viewMode === 'card' && !state.forceFullRender) {
        renderTenderCards(window.__virtualListItems, all.length);
        return;
    }

    if (virtualScrollContainer && !state.forceFullRender) renderVirtualList(window.__virtualListItems);
    else {
        list.innerHTML = '';
        window.__virtualListItems.forEach((item, idx) => list.appendChild(createTenderRow(item, idx)));
    }
}

function init() {
    initThemeToggle();
    initPwaInstallPrompt();
    initViewToggle();

    debouncedRenderTenders = debounce(renderTenders, 150);
    window.debouncedRenderTenders = debouncedRenderTenders;

    virtualScrollContainer = document.getElementById('tenderTableScroll');
    virtualScrollTbody = document.getElementById('tenderList') || document.getElementById('tender-table-body');
    if (virtualScrollContainer) {
        const handleScroll = () => {
            if (state.viewMode !== 'card') renderVirtualList(window.__virtualListItems || []);
            const container = virtualScrollContainer;
            if (!container) return;
            const nearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - ITEM_HEIGHT * 2;
            if (nearBottom) void loadMoreTenders();
        };
        virtualScrollContainer.addEventListener('scroll', throttle(handleScroll, 100));
    }
    window.addEventListener('resize', throttle(() => {
        VISIBLE_ITEMS = Math.ceil(window.innerHeight / ITEM_HEIGHT);
        virtualLastKey = '';
        if (state.viewMode !== 'card') renderVirtualList(window.__virtualListItems || []);
    }, 200));

    // Image lazy-loading (supports data-src + blur placeholder)
    const setupLazyImages = () => {
        const images = Array.from(document.querySelectorAll('img'));
        images.forEach((img) => {
            if (!img.hasAttribute('loading')) img.setAttribute('loading', 'lazy');
            img.classList.add('img-lazy');

            const markLoaded = () => {
                img.classList.add('img-lazy-loaded');
                img.classList.remove('img-lazy');
            };
            if (img.complete && img.naturalWidth > 0) markLoaded();
            img.addEventListener('load', markLoaded, { once: true });
        });

        const lazyTargets = images.filter((img) => img.dataset && img.dataset.src && !img.dataset._lazyBound);
        if (lazyTargets.length === 0) return;

        const loadImg = (img) => {
            const src = img.dataset.src;
            if (!src) return;
            img.dataset._lazyBound = '1';
            img.src = src;
        };

        if (!('IntersectionObserver' in window)) {
            lazyTargets.forEach(loadImg);
            return;
        }

        const io = new IntersectionObserver(
            (entries) => {
                entries.forEach((entry) => {
                    if (!entry.isIntersecting) return;
                    const img = entry.target;
                    io.unobserve(img);
                    loadImg(img);
                });
            },
            { rootMargin: '200px 0px', threshold: 0.01 }
        );

        lazyTargets.forEach((img) => io.observe(img));
    };
    setupLazyImages();

    const tenderDetailCloseBtn = document.getElementById('tenderDetailCloseBtn');
    if (tenderDetailCloseBtn) tenderDetailCloseBtn.addEventListener('click', closeTenderModal);

    const tenderDetailOverlay = document.getElementById('tenderDetailOverlay');
    if (tenderDetailOverlay) {
        tenderDetailOverlay.addEventListener('click', (e) => {
            if (e.target === tenderDetailOverlay) closeTenderModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key !== 'Escape') return;
        const overlay = document.getElementById('tenderDetailOverlay');
        if (overlay?.classList.contains('active')) closeTenderModal();
    });

    document.querySelectorAll('.tender-detail-tab').forEach((btn) => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            if (tab) setTenderDetailTab(tab);
        });
    });

    const hideOutCheckbox = document.getElementById('hide-out-of-scope');
    if (hideOutCheckbox) {
        hideOutCheckbox.checked = false;
        hideOutCheckbox.addEventListener('change', () => requestRenderTenders());
    }

	    const exportPdfBtn = document.getElementById("export-pdf-btn");
	    if (exportPdfBtn) exportPdfBtn.addEventListener("click", () => {
	        if (typeof window.exportToPDF === 'function') window.exportToPDF();
	        else window.print();
	    });

    const exportEmailBtn = document.getElementById("export-email-btn");
    if (exportEmailBtn) {
        exportEmailBtn.addEventListener("click", () => {
            const summary = getKpiSummary();
            const subject = encodeURIComponent("Tender Intelligence – Daily Summary");
            const bodyLines = [
                "Tender Intelligence – Daily Summary",
                "",
                `Total tenders today: ${summary.total}`,
                `TES-fit tenders: ${summary.tes}`,
                `Phakathi-fit tenders: ${summary.phakathi}`,
                "",
                "Sent from the Tender Intelligence dashboard."
            ];
            const body = encodeURIComponent(bodyLines.join("\n"));
            window.location.href = `mailto:?subject=${subject}&body=${body}`;
        });
    }
    
    const refreshBtn = document.getElementById("refresh-data-btn");
    if (refreshBtn) refreshBtn.addEventListener("click", refreshDashboardData);

    const watchlistModeSelect = document.getElementById('watchlistModeSelect');
    if (watchlistModeSelect) {
        watchlistModeSelect.value = getWatchlistMode();
        watchlistModeSelect.addEventListener('change', () => setWatchlistMode(watchlistModeSelect.value));
    }

    const watchlistAddHighBtn = document.getElementById('watchlistAddHighBtn');
    if (watchlistAddHighBtn) watchlistAddHighBtn.addEventListener('click', addAllHighPriorityToWatchlist);

    const watchlistExportBtn = document.getElementById('watchlistExportBtn');
    if (watchlistExportBtn) watchlistExportBtn.addEventListener('click', exportWatchlistCsv);

    const watchlistUserFilter = document.getElementById('watchlistUserFilter');
    if (watchlistUserFilter) {
        watchlistUserFilter.addEventListener('change', () => {
            state.watchlistAddedBy = watchlistUserFilter.value || '';
            requestRenderTenders();
        });
    }

    const lastSyncText = document.querySelector('.last-sync')?.textContent || '';
    const splitSync = lastSyncText.split('|');
    const parsedLastSync = splitSync[0]?.replace('🔄', '').trim() || '';
    const parsedNextRun = splitSync[1]?.replace('Next run:', '').trim() || 'Daily 08:00';
    initialMeta = { last_sync: parsedLastSync || 'Last sync: –', next_run: parsedNextRun || 'Daily 08:00' };
    const initialSummary = getKpiSummary();
    updatePrintHeader(initialMeta, initialSummary);

    window.addEventListener("beforeprint", () => {
        const metaNow = window.dashboardMeta || initialMeta;
        updatePrintHeader(metaNow, getKpiSummary());
    });

    setDataStatus({ level: "warn", source: "initial", count: "–", updated: "–", error: "" });

    updateWatchlistBadges();
    updateWatchlistToolbar();
    updateOfflineIndicator();

    window.addEventListener('offline', () => updateOfflineIndicator());
    window.addEventListener('online', () => {
        updateOfflineIndicator();
        void flushOfflineQueue();
    });

    showTenderSkeleton(8);

    loadTenderPayload()
        .then(applyTenderPayload)
        .catch(err => {
            console.error("Error fetching tenders:", err);
            setDataStatus({ level: "err", source: "error", count: 0, updated: "–", error: err });
        });

    updateNextRunCountdown();
    setInterval(updateNextRunCountdown, 60000);
}

init();
