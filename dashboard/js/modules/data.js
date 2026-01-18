/**
 * Data loading and caching for Tender Intelligence Dashboard
 */

import { config, state } from './config.js';
import { delay } from '../utils/helpers.js';

/**
 * Validate payload shape
 * @param {Object|Array} payload - Payload to validate
 * @returns {Object}
 */
export function validatePayloadShape(payload) {
    const tenderList = Array.isArray(payload) ? payload : (payload?.tenders || payload?.data || []);
    if (!Array.isArray(tenderList)) throw new Error("Invalid payload: tenders must be an array");
    const meta = (!Array.isArray(payload) && payload?.meta) ? payload.meta : {};
    return { tenderList, meta };
}

/**
 * Read cached payload from localStorage
 * @returns {Object|null}
 */
export function readCachedPayload() {
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

/**
 * Write payload to cache
 * @param {Object|Array} payload - Payload to cache
 * @param {string} storedAtOverride - Optional override timestamp
 */
export function writeCachedPayload(payload, storedAtOverride) {
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

/**
 * Clear cached payload
 */
export function clearCachedPayload() {
    try {
        localStorage.removeItem(config.cacheKey);
    } catch {
        // ignore
    }
}

/**
 * Load tender payload with caching
 * @param {Object} options - Options object
 * @param {boolean} options.forceRefresh - Force refresh from network
 * @returns {Promise<Object>}
 */
export async function loadTenderPayload({ forceRefresh } = {}) {
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

/**
 * Fetch tender chunk (for pagination)
 * @param {Array} items - Items to fetch from
 * @param {number} offset - Offset
 * @param {number} chunkSize - Chunk size
 * @returns {Promise<Array>}
 */
export async function fetchTenderChunk(items, offset, chunkSize) {
    const list = Array.isArray(items) ? items : [];
    const start = Math.max(0, offset | 0);
    const end = Math.min(list.length, start + (chunkSize | 0));
    await delay(10); // Small delay for UI responsiveness
    return list.slice(start, end);
}

/**
 * Normalize tender object
 * @param {Object} t - Tender object
 * @returns {Object}
 */
export function normalizeTender(t) {
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

/**
 * Apply tender payload to state
 * @param {Object} params - Parameters
 * @param {Array} params.tenders - Tenders array
 * @param {Array} params.loadedTenders - Loaded tenders
 * @param {Object} params.meta - Meta object
 * @param {string} params.source - Data source
 * @param {string} params.storedAt - Storage timestamp
 * @param {Error} params.error - Error object
 */
export function applyTenderPayload({ tenders, loadedTenders, meta, source, storedAt, error }) {
    const effectiveMeta = meta || {};

    const list = Array.isArray(loadedTenders) ? loadedTenders : (Array.isArray(tenders) ? tenders : []);
    state.tenders = list.map(normalizeTender);
    window.tendersData = state.tenders;
    window.dashboardMeta = effectiveMeta;

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
        count: state.tenders.length,
        updated,
        error: error || (level === "warn" && source === "seed" ? "No live data available yet (showing seed)." : "")
    });
}

/**
 * Set data status indicator
 * @param {Object} params - Parameters
 * @param {string} params.level - Status level ('ok', 'warn', 'err')
 * @param {string} params.source - Data source
 * @param {number} params.count - Record count
 * @param {string} params.updated - Updated timestamp
 * @param {Error} params.error - Error object
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

/**
 * Refresh dashboard data
 * @returns {Promise<void>}
 */
export async function refreshDashboardData() {
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

/**
 * Enqueue offline action
 * @param {Object} action - Action to enqueue
 */
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

/**
 * Flush offline queue
 * @returns {Promise<void>}
 */
export async function flushOfflineQueue() {
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
