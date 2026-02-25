/**
 * UI initialization and event handling
 */

import { state, VIEW_MODES } from './config.js';
import { debounce, throttle } from '../utils/helpers.js';
import { getPreferredViewMode, setPreferredViewMode, getWatchlistMode, setWatchlistMode } from './storage.js';
import {
    setVirtualScrollContainer,
    setVirtualScrollTbody,
    updateVisibleItems,
    setVirtualLastKey
} from './config.js';
import {
    renderTenders,
    requestRenderTenders,
    resetTenderInfiniteList,
    showTenderSkeleton
} from './render.js';
import { updateWatchlistBadges, exportWatchlistCsv, addAllHighPriorityToWatchlist } from './storage.js';
import { applyTenderPayload, refreshDashboardData } from './data.js';

/**
 * Initialize theme toggle
 */
export function initThemeToggle() {
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

/**
 * Initialize PWA install prompt
 */
export function initPwaInstallPrompt() {
    const installBtn = document.getElementById('installBtn');
    if (!installBtn) return;

    window.__pwaInstall = window.__pwaInstall || {
        deferredPrompt: null,
        lastBeforeInstallPromptAt: null,
        lastOutcome: null,
    };

    const hideBtn = () => {
        installBtn.style.display = 'none';
    };

    const showBtn = () => {
        installBtn.style.display = 'inline-flex';
    };

    hideBtn();

    window.addEventListener('beforeinstallprompt', (e) => {
        e.preventDefault();
        window.__pwaInstall.deferredPrompt = e;
        window.__pwaInstall.lastBeforeInstallPromptAt = new Date().toISOString();
        showBtn();
    });

    window.addEventListener('appinstalled', () => {
        window.__pwaInstall.deferredPrompt = null;
        hideBtn();
    });

    installBtn.addEventListener('click', async () => {
        const deferredPrompt = window.__pwaInstall?.deferredPrompt;
        if (!deferredPrompt) return;
        try {
            deferredPrompt.prompt();
            const choice = await deferredPrompt.userChoice;
            window.__pwaInstall.lastOutcome = choice?.outcome || null;
        } catch (err) {
            console.warn('Install prompt failed:', err);
        } finally {
            window.__pwaInstall.deferredPrompt = null;
            hideBtn();
        }
    });
}

/**
 * Initialize mobile gestures
 */
export function initMobileGestures() {
    if (typeof Hammer === 'undefined') return;
    const container = document.querySelector('.container');
    if (!container) return;

    const hammer = new Hammer(container);
    hammer.get('swipe').set({ direction: Hammer.DIRECTION_HORIZONTAL, threshold: 12, velocity: 0.2 });

    const tabs = ['dashboard', 'calendar', 'analytics', 'sources'];

    const isSwipeNavAllowed = (target) => {
        const el = target;
        if (!el || !(el instanceof Element)) return true;
        if (document.getElementById('tenderDetailOverlay')?.classList.contains('active')) return false;
        if (el.closest('.multi-select-panel')) return false;
        if (el.closest('.tender-detail-modal')) return false;
        if (el.closest('input, textarea, select, button')) return false;
        if (el.closest('#tenderTableScroll')) return false;
        return true;
    };

    const handleTabSwipe = (direction, e) => {
        if (!isSwipeNavAllowed(e?.target)) return false;
        const current = getCurrentTab();
        const idx = tabs.indexOf(current);
        if (idx < 0) return false;
        if (direction === 'left' && idx < tabs.length - 1) {
            showTab(tabs[idx + 1]);
            return true;
        }
        if (direction === 'right' && idx > 0) {
            showTab(tabs[idx - 1]);
            return true;
        }
        return false;
    };

    hammer.on('swipeleft', (e) => {
        if (typeof handleTenderSwipeLeft === 'function' && handleTenderSwipeLeft(e?.target)) return;
        handleTabSwipe('left', e);
    });
    hammer.on('swiperight', (e) => {
        if (typeof handleTenderSwipeRight === 'function' && handleTenderSwipeRight(e?.target)) return;
        handleTabSwipe('right', e);
    });

    // Pull-to-refresh (mobile)
    let startY = 0;
    let pullDistance = 0;
    let pulling = false;
    let refreshing = false;

    const indicator = document.getElementById('refreshIndicator');
    const indicatorText = document.getElementById('refreshIndicatorText');
    const threshold = 80;

    const getTopScroll = (target) => {
        const table = document.getElementById('tenderTableScroll');
        if (table && (target?.closest?.('#tenderTableScroll') || getCurrentTab() === 'dashboard')) {
            return table.scrollTop || 0;
        }
        return window.scrollY || 0;
    };

    const canStart = (target) => {
        if (refreshing) return false;
        if (document.getElementById('tenderDetailOverlay')?.classList.contains('active')) return false;
        if (target?.closest?.('input, textarea, select')) return false;
        return getTopScroll(target) === 0;
    };

    const setIndicator = (y, text) => {
        if (!indicator) return;
        const clamped = Math.max(0, Math.min(80, y));
        indicator.style.transform = `translateX(-50%) translateY(${clamped - 100}px)`;
        indicator.style.opacity = clamped > 2 ? '1' : '0';
        if (indicatorText && text) indicatorText.textContent = text;
    };

    document.addEventListener(
        'touchstart',
        (e) => {
            const t = e.touches?.[0];
            if (!t) return;
            if (!canStart(e.target)) return;
            pulling = true;
            startY = t.clientY;
            pullDistance = 0;
        },
        { passive: true }
    );

    document.addEventListener(
        'touchmove',
        (e) => {
            if (!pulling || refreshing) return;
            const t = e.touches?.[0];
            if (!t) return;
            pullDistance = t.clientY - startY;
            if (pullDistance <= 0) {
                setIndicator(0, 'Pull to refresh');
                return;
            }
            e.preventDefault();
            const label = pullDistance > threshold ? 'Release to refresh' : 'Pull to refresh';
            setIndicator(pullDistance, label);
        },
        { passive: false }
    );

    document.addEventListener(
        'touchend',
        async () => {
            if (!pulling) return;
            pulling = false;

            if (pullDistance > threshold && !refreshing) {
                refreshing = true;
                setIndicator(80, 'Refreshing…');
                try {
                    if (typeof refreshDashboardData === 'function') await refreshDashboardData();
                    else location.reload();
                } catch {
                    // ignore
                } finally {
                    refreshing = false;
                    pullDistance = 0;
                    setIndicator(0, 'Pull to refresh');
                }
                return;
            }

            pullDistance = 0;
            setIndicator(0, 'Pull to refresh');
        },
        { passive: true }
    );
}

/**
 * Initialize view mode toggle
 */
export function initViewToggle() {
    const buttons = Array.from(document.querySelectorAll('.view-toggle .view-btn'));
    if (buttons.length === 0) return;

    const applyViewMode = (view) => {
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
    };

    applyViewMode(getPreferredViewMode());

    buttons.forEach((btn) => {
        btn.addEventListener('click', () => {
            const view = (btn.dataset?.view || '').toLowerCase();
            const mode = VIEW_MODES.includes(view) ? view : 'detailed';
            setPreferredViewMode(mode);
            applyViewMode(mode);
            resetTenderInfiniteList();
            requestRenderTenders();
        });
    });
}

/**
 * Get current tab
 * @returns {string}
 */
function getCurrentTab() {
    const active = document.querySelector('.tab-content.active');
    return active ? active.id : 'dashboard';
}

/**
 * Show tab
 * @param {string} tabId - Tab ID
 * @param {Event} evt - Event object
 */
export function showTab(tabId, evt) {
    document.querySelectorAll('.tab-content').forEach((t) => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach((b) => b.classList.remove('active'));
    const tabEl = document.getElementById(tabId);
    if (tabEl) tabEl.classList.add('active');

    let btn = null;
    const eventTarget = evt?.target || (typeof event !== 'undefined' ? event?.target : null);
    if (eventTarget && eventTarget.classList && eventTarget.classList.contains('tab-btn')) {
        btn = eventTarget;
    }
    if (!btn) {
        btn = Array.from(document.querySelectorAll('.tab-btn')).find((b) =>
            (b.getAttribute('onclick') || '').includes(`showTab('${tabId}'`)
        );
    }
    if (btn) btn.classList.add('active');

    if (tabId === 'calendar') renderCalendar();
    if (tabId === 'analytics') {
        const timer = getAnalyticsInitTimer();
        if (timer) clearTimeout(timer);
        setAnalyticsInitTimer(setTimeout(() => {
            initializeAnalytics();
        }, 150));
    }
    if (tabId === 'sources') renderScraperHealth(typeof globalData !== 'undefined' ? globalData.scraperHealth : {});
}

/**
 * Initialize UI
 */
export function initUI() {
    initThemeToggle();
    initPwaInstallPrompt();
    initMobileGestures();
    initViewToggle();
    
    // Tab navigation
    document.querySelectorAll('.tab-btn').forEach(btn => {
        btn.addEventListener('click', () => {
            const tab = btn.getAttribute('data-tab');
            if (tab) showTab(tab);
        });
    });
    
    // Filter tabs
    document.querySelectorAll('.filter-tab').forEach(btn => {
        btn.addEventListener('click', () => {
            const filter = btn.getAttribute('data-filter');
            if (filter && typeof window.filterTenders === 'function') {
                window.filterTenders(filter);
            }
        });
    });
    
    // Load more button
    const loadMoreBtn = document.getElementById('loadMoreBtn');
    if (loadMoreBtn) {
        loadMoreBtn.addEventListener('click', () => {
            if (typeof window.loadMoreTenders === 'function') {
                window.loadMoreTenders();
            }
        });
    }
    
    // Calendar navigation
    const prevMonthBtn = document.getElementById('prevMonthBtn');
    const nextMonthBtn = document.getElementById('nextMonthBtn');
    if (prevMonthBtn) {
        prevMonthBtn.addEventListener('click', () => {
            if (typeof window.changeMonth === 'function') {
                window.changeMonth(-1);
            }
        });
    }
    if (nextMonthBtn) {
        nextMonthBtn.addEventListener('click', () => {
            if (typeof window.changeMonth === 'function') {
                window.changeMonth(1);
            }
        });
    }

    const debouncedRenderTenders = debounce(renderTenders, 150);
    window.debouncedRenderTenders = debouncedRenderTenders;

    const container = document.getElementById('tenderTableScroll');
    const tbody = document.getElementById('tenderList') || document.getElementById('tender-table-body');
    setVirtualScrollContainer(container);
    setVirtualScrollTbody(tbody);
    
    if (container) {
        const handleScroll = () => {
            if (state.viewMode !== 'card') renderVirtualList(window.__virtualListItems || []);
            const nearBottom = container.scrollTop + container.clientHeight >= container.scrollHeight - ITEM_HEIGHT * 2;
            if (nearBottom) void loadMoreTenders();
        };
        container.addEventListener('scroll', throttle(handleScroll, 100));
    }
    
    window.addEventListener('resize', throttle(() => {
        updateVisibleItems();
        setVirtualLastKey('');
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
                `Mexel-fit tenders: ${summary.mexel}`,
                "",
                "Sent from Tender Intelligence dashboard."
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
    const initialMeta = { last_sync: parsedLastSync || 'Last sync: –', next_run: parsedNextRun || 'Daily 08:00' };
    setInitialMeta(initialMeta);
    const initialSummary = getKpiSummary();
    updatePrintHeader(initialMeta, initialSummary);

    window.addEventListener("beforeprint", () => {
        const metaNow = window.dashboardMeta || initialMeta;
        updatePrintHeader(metaNow, getKpiSummary());
    });

    updateWatchlistBadges();
    updateOfflineIndicator();

    window.addEventListener('offline', () => updateOfflineIndicator());
    window.addEventListener('online', () => {
        updateOfflineIndicator();
        void syncPendingChanges();
    });

    showTenderSkeleton(8);

    loadTenderPayload()
        .then(payload => {
            applyTenderPayload(payload);
            renderTenders();
        })
        .catch(err => {
            console.error("Error fetching tenders:", err);
            setDataStatus({ level: "err", source: "error", count: 0, updated: "–", error: err });
        });

    updateNextRunCountdown();
    setInterval(updateNextRunCountdown, 60000);
}

/**
 * Update next run countdown
 */
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

/**
 * Update offline indicator
 */
function updateOfflineIndicator() {
    const pill = document.getElementById('offlinePill');
    const offline = typeof navigator !== 'undefined' && navigator.onLine === false;
    if (pill) pill.classList.toggle('hidden', !offline);

    const banner = document.getElementById('offlineIndicator');
    if (banner) banner.style.display = offline ? 'block' : 'none';
}

/**
 * Sync pending changes when online
 */
async function syncPendingChanges() {
    try {
        await flushOfflineQueue();
    } catch {
        // ignore
    }

    let queue = [];
    try {
        queue = JSON.parse(localStorage.getItem('pendingQueue') || '[]');
    } catch {
        queue = [];
    }
    if (!Array.isArray(queue) || queue.length === 0) return;

    for (const action of queue) {
        try {
            await executeAction(action);
        } catch (err) {
            console.warn('Failed to replay queued action:', action, err);
        }
    }

    try {
        localStorage.removeItem('pendingQueue');
    } catch {
        // ignore
    }
}

/**
 * Execute queued action
 * @param {Object} action - Action to execute
 */
async function executeAction(action) {
    const type = (action?.type || action?.action || '').toString();
    if (type === 'refresh') {
        await refreshDashboardData();
        return;
    }
}

/**
 * Get KPI summary
 * @returns {Object}
 */
function getKpiSummary() {
    const totalKpi = document.getElementById('kpiTotalTenders') || document.querySelector(".stat-value.total");
    const mexelKpi = document.getElementById('kpiMexelFit') || document.querySelector(".stat-value.mexel-color");
    return {
        total: totalKpi ? totalKpi.textContent.trim() : "0",
        mexel: mexelKpi ? mexelKpi.textContent.trim() : "0"
    };
}

/**
 * Update print header
 * @param {Object} meta - Meta object
 * @param {Object} tendersSummary - Tenders summary
 */
function updatePrintHeader(meta, tendersSummary) {
    const lastSyncSpan = document.getElementById("print-last-sync");
    const nextRunSpan = document.getElementById("print-next-run");
    const totalSpan = document.getElementById("print-total-tenders");
    const mexelSpan = document.getElementById("print-mexel-tenders");

    if (lastSyncSpan && meta && meta.last_sync) {
        lastSyncSpan.textContent = "Last sync: " + meta.last_sync;
    }
    if (nextRunSpan && meta && meta.next_run) {
        nextRunSpan.textContent = "Next run: " + meta.next_run;
    }

    if (tendersSummary) {
        if (totalSpan) totalSpan.textContent = String(tendersSummary.total || "0");
        if (mexelSpan) mexelSpan.textContent = String(tendersSummary.mexel || "0");
    }
}

/**
 * Set data status
 * @param {Object} params - Status parameters
 */
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
