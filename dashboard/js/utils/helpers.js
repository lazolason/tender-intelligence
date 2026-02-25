/**
 * Utility helper functions for Tender Intelligence Dashboard
 */

/**
 * Delay execution for specified milliseconds
 * @param {number} ms - Milliseconds to delay
 * @returns {Promise<void>}
 */
export function delay(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
}

/**
 * Create a debounced function
 * @param {Function} func - Function to debounce
 * @param {number} delayMs - Delay in milliseconds
 * @returns {Function}
 */
export function debounce(func, delayMs) {
    let timeout;
    return function debounced(...args) {
        clearTimeout(timeout);
        timeout = setTimeout(() => func.apply(this, args), delayMs);
    };
}

/**
 * Create a throttled function
 * @param {Function} func - Function to throttle
 * @param {number} limitMs - Limit in milliseconds
 * @returns {Function}
 */
export function throttle(func, limitMs) {
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

/**
 * Escape HTML to prevent XSS
 * @param {string} value - Value to escape
 * @returns {string}
 */
export function escapeHtml(value) {
    const s = (value ?? '').toString();
    return s
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')
        .replace(/"/g, '&quot;')
        .replace(/'/g, '&#039;');
}

/**
 * Normalize text for matching/search
 * @param {string} value - Input value
 * @returns {string}
 */
export function normalizeText(value) {
    return (value ?? '').toString().trim().toLowerCase().replace(/\s+/g, ' ');
}

/**
 * Format bytes to human readable string
 * @param {number} bytes - Bytes to format
 * @returns {string}
 */
export function formatBytes(bytes) {
    const n = typeof bytes === 'number' ? bytes : Number(bytes);
    if (!Number.isFinite(n) || n <= 0) return '–';
    const units = ['B', 'KB', 'MB', 'GB'];
    const idx = Math.min(units.length - 1, Math.floor(Math.log(n) / Math.log(1024)));
    const val = n / 1024 ** idx;
    return `${val.toFixed(val >= 10 || idx === 0 ? 0 : 1)} ${units[idx]}`;
}

/**
 * Generate a unique ID
 * @returns {string}
 */
export function newId() {
    try {
        return crypto.randomUUID();
    } catch {
        return `c_${Math.random().toString(16).slice(2)}_${Date.now()}`;
    }
}

/**
 * Get initials from a name
 * @param {string} name - Full name
 * @returns {string}
 */
export function initials(name) {
    const parts = (name || '').toString().trim().split(/\s+/).filter(Boolean);
    const a = parts[0]?.[0] || '?';
    const b = parts.length > 1 ? parts[parts.length - 1][0] : '';
    return (a + b).toUpperCase();
}

/**
 * Generate hash color for user avatar
 * @param {string} name - User name
 * @returns {string}
 */
export function hashColorForUser(name) {
    const s = (name || '').toString();
    let hash = 0;
    for (let i = 0; i < s.length; i++) hash = (hash * 31 + s.charCodeAt(i)) >>> 0;
    const hue = hash % 360;
    return `hsl(${hue} 70% 60% / 0.22)`;
}

/**
 * Format relative time
 * @param {string} isoTs - ISO timestamp
 * @returns {string}
 */
export function relativeTime(isoTs) {
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

/**
 * Parse flexible date format
 * @param {string} dateStr - Date string
 * @returns {Date|null}
 */
export function parseFlexibleDate(dateStr) {
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
 * Format nice date time
 * @param {string} dateStr - Date string
 * @param {string} timeStr - Optional time string
 * @returns {string}
 */
export function formatNiceDateTime(dateStr, timeStr) {
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

/**
 * Format number or return dash
 * @param {number} value - Number to format
 * @returns {string}
 */
export function formatNumberOrDash(value) {
    if (!Number.isFinite(value)) return '–';
    return new Intl.NumberFormat('en-US').format(value);
}

/**
 * Set text content or dash
 * @param {string} id - Element ID
 * @param {string} value - Value to set
 */
export function setTextOrDash(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    const v = (value ?? '').toString().trim();
    el.textContent = v ? v : '–';
}

/**
 * Set number or dash
 * @param {string} id - Element ID
 * @param {number} value - Number to set
 */
export function setNumberOrDash(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = formatNumberOrDash(value);
}

/**
 * Set text by ID
 * @param {string} id - Element ID
 * @param {string} value - Value to set
 */
export function setTextById(id, value) {
    const el = document.getElementById(id);
    if (!el) return;
    el.textContent = value === null || typeof value === 'undefined' ? '–' : String(value);
}

/**
 * Render markdown lite
 * @param {string} text - Text to render
 * @returns {string}
 */
export function renderMarkdownLite(text) {
    const escaped = escapeHtml(text || '');
    return escaped
        .replace(/`([^`]+)`/g, '<code>$1</code>')
        .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
        .replace(/\*([^*]+)\*/g, '<em>$1</em>')
        .replace(/\n/g, '<br/>');
}
