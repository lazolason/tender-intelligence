/**
 * Configuration and state management for Tender Intelligence Dashboard
 */

export const config = {
    cacheKey: "ti_dashboard_payload_v1",
    cacheTtlMs: 60 * 60 * 1000, // 1 hour
    tenderJsonUrls: [
        "/tenders.json",
        "./tenders.json",
        "/public/tenders-latest.json",
        "./public/tenders-latest.json"
    ],
    seedPayload: {
        meta: {
            last_sync: null,
            next_run: "Daily 08:00"
        },
        tenders: []
    }
};

export const state = {
    tenders: [],
    plannedOpportunities: [],
    currentTenders: [],
    currentFilter: 'all',
    currentMonth: new Date(),
    searchQuery: '',
    watchlistAddedBy: '',
    viewMode: 'detailed',
    forceFullRender: false,
    visibleTenderCount: 0,
    totalMatchingCount: 0,
    loadingMore: false
};

export const VIEW_MODES = ['detailed', 'compact', 'card'];

export const ITEM_HEIGHT = 150;
export const CHUNK_SIZE = 50;
export const BUFFER = 5;

export const teamMembers = ['Lazola Sonqishe', 'John Doe', 'Jane Smith', 'Mexel Team'];

export const tenderLifecycleStatuses = [
    { value: 'Not Started', color: 'gray', icon: '⏳' },
    { value: 'Qualified', color: 'blue', icon: '✅' },
    { value: 'In Progress', color: 'yellow', icon: '🛠️' },
    { value: 'Awaiting Review', color: 'orange', icon: '🧾' },
    { value: 'Submitted', color: 'purple', icon: '📨' },
    { value: 'Won', color: 'green', icon: '🏆' },
    { value: 'Lost', color: 'red', icon: '❌' },
    { value: 'Withdrawn', color: 'gray', icon: '🚫' },
];

export const tenderFinalStatuses = new Set(['Won', 'Lost']);

// Virtual scrolling state
let VISIBLE_ITEMS = Math.ceil(window.innerHeight / ITEM_HEIGHT);
let virtualScrollContainer = null;
let virtualScrollTbody = null;
let virtualLastKey = '';

export function updateVisibleItems() {
    VISIBLE_ITEMS = Math.ceil((virtualScrollContainer?.clientHeight || window.innerHeight) / ITEM_HEIGHT);
}

export function getVirtualScrollContainer() {
    return virtualScrollContainer;
}

export function setVirtualScrollContainer(container) {
    virtualScrollContainer = container;
}

export function getVirtualScrollTbody() {
    return virtualScrollTbody;
}

export function setVirtualScrollTbody(tbody) {
    virtualScrollTbody = tbody;
}

export function getVirtualLastKey() {
    return virtualLastKey;
}

export function setVirtualLastKey(key) {
    virtualLastKey = key;
}

export function getVisibleItemsCount() {
    return VISIBLE_ITEMS;
}

// Analytics state
let analyticsInitialized = false;
let analyticsInitTimer = null;

export function isAnalyticsInitialized() {
    return analyticsInitialized;
}

export function setAnalyticsInitialized(value) {
    analyticsInitialized = value;
}

export function getAnalyticsInitTimer() {
    return analyticsInitTimer;
}

export function setAnalyticsInitTimer(timer) {
    analyticsInitTimer = timer;
}

// Initial meta data
let initialMeta = { last_sync: null, next_run: 'Daily 08:00' };

export function getInitialMeta() {
    return initialMeta;
}

export function setInitialMeta(meta) {
    initialMeta = meta;
}
