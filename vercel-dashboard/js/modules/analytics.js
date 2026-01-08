/**
 * Analytics and charting for Tender Intelligence Dashboard
 */

import { state, setAnalyticsInitialized, getAnalyticsInitTimer, setAnalyticsInitTimer } from './config.js';
import { setTextOrDash, setNumberOrDash } from '../utils/helpers.js';

/**
 * Tender Analytics Class
 */
export class TenderAnalytics {
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

    /**
     * Get ISO week from date
     * @param {Date} date - Date object
     * @returns {Object}
     */
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

    /**
     * Get top source
     * @returns {string}
     */
    getTopSource() {
        const entries = Object.entries(this.bySource).sort((a, b) => b[1] - a[1]);
        return entries[0]?.[0] || '–';
    }

    /**
     * Get average tenders per week
     * @returns {number}
     */
    getAvgTendersPerWeek() {
        if (!this.byWeek.length) return 0;
        const total = this.byWeek.reduce((sum, w) => sum + (w.count || 0), 0);
        return Math.round(total / this.byWeek.length);
    }

    /**
     * Get most active day
     * @returns {string}
     */
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

    /**
     * Get top keywords
     * @param {number} limit - Limit number of keywords
     * @returns {Array}
     */
    getTopKeywords(limit = 20) {
        return Object.entries(this.keywords)
            .sort((a, b) => b[1] - a[1])
            .slice(0, limit);
    }

    /**
     * Get tenders this month
     * @returns {number}
     */
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

/**
 * Get chart theme
 * @returns {Object}
 */
function getChartTheme() {
    return {
        text: '#fff',
        grid: 'rgba(255,255,255,0.1)'
    };
}

/**
 * Get chart animation
 * @returns {Object}
 */
function getChartAnimation() {
    return { duration: 1000, easing: 'easeInOutQuart' };
}

/**
 * Get last N days series
 * @param {Object} tendersByDate - Tenders by date
 * @param {number} days - Number of days
 * @returns {Object}
 */
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

/**
 * Render trend chart
 * @param {Object} tendersByDate - Tenders by date
 */
export function renderTrendChart(tendersByDate) {
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

/**
 * Render source pie chart
 * @param {Object} bySource - Tenders by source
 */
export function renderSourcePieChart(bySource) {
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

/**
 * Render priority bar chart
 * @param {Object} byPriority - Tenders by priority
 */
export function renderPriorityBarChart(byPriority) {
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

/**
 * Render keyword cloud
 * @param {Array} keywords - Keywords array
 */
export function renderKeywordCloud(keywords) {
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

/**
 * Set chart fallback message
 * @param {string} message - Fallback message
 */
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

/**
 * Initialize analytics
 */
export function initializeAnalytics() {
    if (isAnalyticsInitialized()) return;
    if (!state.tenders || state.tenders.length === 0) {
        setNumberOrDash('analytics-total-month', NaN);
        setNumberOrDash('analytics-avg-per-week', NaN);
        setTextOrDash('analytics-top-source', '');
        setTextOrDash('analytics-most-active-day', '');
        return;
    }

    setAnalyticsInitialized(true);

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
