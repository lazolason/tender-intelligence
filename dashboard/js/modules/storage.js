/**
 * LocalStorage operations for Tender Intelligence Dashboard
 */

// Persistent storage helper (backs onto localStorage)
const storage = {
    get: (key) => {
        try {
            const raw = localStorage.getItem(key);
            return raw ? JSON.parse(raw) : null;
        } catch {
            return null;
        }
    },
    set: (key, value) => {
        try {
            localStorage.setItem(key, JSON.stringify(value));
            return true;
        } catch {
            return false;
        }
    },
    remove: (key) => {
        try {
            localStorage.removeItem(key);
            return true;
        } catch {
            return false;
        }
    }
};

/**
 * Get assignment key for tender
 * @param {string} tenderRef - Tender reference
 * @returns {string|null}
 */
export function getAssignmentKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `assignment:${ref}` : null;
}

/**
 * Get tender assignment
 * @param {string} tenderRef - Tender reference
 * @returns {Object|null}
 */
export function getTenderAssignment(tenderRef) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return null;
    const value = storage.get(key);
    if (!value || typeof value !== 'object') return null;
    const assignedTo = (value.assignedTo || '').toString().trim();
    if (!assignedTo) return null;
    return {
        assignedTo,
        assignedDate: (value.assignedDate || '').toString().trim() || null,
        status: (value.status || '').toString().trim() || 'Not Started'
    };
}

/**
 * Set tender assignment
 * @param {string} tenderRef - Tender reference
 * @param {string} assignedTo - Assigned user
 * @param {string} status - Assignment status
 * @returns {boolean}
 */
export function setTenderAssignment(tenderRef, assignedTo, status = 'Not Started') {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    const name = (assignedTo || '').toString().trim();
    if (!name) return false;
    const date = new Date().toISOString().split('T')[0];
    const ok = storage.set(key, { assignedTo: name, assignedDate: date, status: status || 'Not Started' });
    return ok;
}

/**
 * Update tender assignment status
 * @param {string} tenderRef - Tender reference
 * @param {string} status - New status
 * @returns {boolean}
 */
export function updateTenderAssignmentStatus(tenderRef, status) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    const existing = getTenderAssignment(tenderRef);
    if (!existing) return false;
    const next = { ...existing, status: (status || '').toString().trim() || existing.status };
    return storage.set(key, next);
}

/**
 * Clear tender assignment
 * @param {string} tenderRef - Tender reference
 * @returns {boolean}
 */
export function clearTenderAssignment(tenderRef) {
    const key = getAssignmentKey(tenderRef);
    if (!key) return false;
    return storage.remove(key);
}

/**
 * Get status history key for tender
 * @param {string} tenderRef - Tender reference
 * @returns {string|null}
 */
export function getTenderStatusHistoryKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `status_history:${ref}` : null;
}

/**
 * Get tender status history
 * @param {string} tenderRef - Tender reference
 * @returns {Array}
 */
export function getTenderStatusHistory(tenderRef) {
    const key = getTenderStatusHistoryKey(tenderRef);
    if (!key) return [];
    const value = storage.get(key);
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

/**
 * Add tender status history entry
 * @param {string} tenderRef - Tender reference
 * @param {string} status - Status
 * @param {string} changedBy - User who changed status
 * @param {string} notes - Optional notes
 * @returns {boolean}
 */
export function addTenderStatusHistory(tenderRef, status, changedBy, notes) {
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
    return storage.set(key, history);
}

/**
 * Get tender current status
 * @param {string} tenderRef - Tender reference
 * @returns {string}
 */
export function getTenderCurrentStatus(tenderRef) {
    const history = getTenderStatusHistory(tenderRef);
    if (history.length > 0) return history[history.length - 1].status || 'Not Started';
    const assignment = getTenderAssignment(tenderRef);
    return assignment?.status || 'Not Started';
}

/**
 * Get comments key for tender
 * @param {string} tenderRef - Tender reference
 * @returns {string|null}
 */
export function getCommentsKey(tenderRef) {
    const ref = (tenderRef || '').toString().trim();
    return ref ? `comments:${ref}` : null;
}

/**
 * Get tender comments
 * @param {string} tenderRef - Tender reference
 * @returns {Array}
 */
export function getTenderComments(tenderRef) {
    const key = getCommentsKey(tenderRef);
    if (!key) return [];
    const value = storage.get(key);
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

/**
 * Save tender comments
 * @param {string} tenderRef - Tender reference
 * @param {Array} comments - Comments array
 * @returns {boolean}
 */
export function saveTenderComments(tenderRef, comments) {
    const key = getCommentsKey(tenderRef);
    if (!key) return false;
    return storage.set(key, Array.isArray(comments) ? comments : []);
}

/**
 * Get mentions key for user
 * @param {string} username - Username
 * @returns {string|null}
 */
export function getMentionsKey(username) {
    const u = (username || '').toString().trim();
    return u ? `mentions:${u}` : null;
}

/**
 * Get mentions store for user
 * @param {string} username - Username
 * @returns {Object}
 */
export function getMentionsStore(username) {
    const key = getMentionsKey(username);
    if (!key) return {};
    const v = storage.get(key);
    return v && typeof v === 'object' ? v : {};
}

/**
 * Add mentions for users
 * @param {Array} users - Usernames to mention
 * @param {string} tenderRef - Tender reference
 * @param {Object} options - Options object
 */
export function addMentionsForUsers(users, tenderRef, { commentId, from, timestamp } = {}) {
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
        storage.set(key, store);
    });
}

/**
 * Get unread mention count for tender
 * @param {string} tenderRef - Tender reference
 * @param {string} username - Username
 * @returns {number}
 */
export function getUnreadMentionCount(tenderRef, username) {
    const store = getMentionsStore(username);
    const ref = (tenderRef || '').toString().trim();
    const arr = store?.[ref];
    return Array.isArray(arr) ? arr.length : 0;
}

/**
 * Clear mentions for tender
 * @param {string} tenderRef - Tender reference
 * @param {string} username - Username
 * @returns {boolean}
 */
export function clearMentionsForTender(tenderRef, username) {
    const key = getMentionsKey(username);
    if (!key) return false;
    const store = getMentionsStore(username);
    const ref = (tenderRef || '').toString().trim();
    if (!ref) return false;
    if (store[ref]) delete store[ref];
    return storage.set(key, store);
}

/**
 * Get current username
 * @returns {string|null}
 */
export function getCurrentUsername() {
    try {
        return (localStorage.getItem('ti_username') || '').trim() || null;
    } catch {
        return null;
    }
}

/**
 * Ensure username is set
 * @returns {string|null}
 */
export function ensureUsername() {
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

/**
 * Get watchlist mode
 * @returns {string}
 */
export function getWatchlistMode() {
    try {
        const raw = (localStorage.getItem('ti_watchlist_mode') || '').trim();
        return raw === 'personal' ? 'personal' : 'shared';
    } catch {
        return 'shared';
    }
}

/**
 * Set watchlist mode
 * @param {string} mode - Mode ('personal' or 'shared')
 */
export function setWatchlistMode(mode) {
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
}

/**
 * Normalize watchlist entries
 * @param {Array} entries - Raw entries
 * @returns {Array}
 */
export function normalizeWatchlistEntries(entries) {
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

/**
 * Get shared watchlist
 * @returns {Array}
 */
export function getSharedWatchlist() {
    return normalizeWatchlistEntries(storage.get('watchlist'));
}

/**
 * Set shared watchlist
 * @param {Array} entries - Watchlist entries
 * @returns {boolean}
 */
export function setSharedWatchlist(entries) {
    return storage.set('watchlist', normalizeWatchlistEntries(entries));
}

/**
 * Get personal watchlist for user
 * @param {string} username - Username
 * @returns {Array}
 */
export function getPersonalWatchlist(username) {
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

/**
 * Set personal watchlist for user
 * @param {string} username - Username
 * @param {Array} entries - Watchlist entries
 * @returns {boolean}
 */
export function setPersonalWatchlist(username, entries) {
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

/**
 * Get active watchlist
 * @returns {Array}
 */
export function getActiveWatchlist() {
    const mode = getWatchlistMode();
    if (mode === 'personal') {
        const user = getCurrentUsername();
        return user ? getPersonalWatchlist(user) : [];
    }
    return getSharedWatchlist();
}

/**
 * Set active watchlist
 * @param {Array} entries - Watchlist entries
 * @returns {boolean}
 */
export function setActiveWatchlist(entries) {
    const mode = getWatchlistMode();
    if (mode === 'personal') {
        const user = getCurrentUsername();
        return user ? setPersonalWatchlist(user, entries) : false;
    }
    return setSharedWatchlist(entries);
}

/**
 * Get hidden tender refs
 * @returns {Set}
 */
export function getHiddenTenderRefs() {
    try {
        const raw = localStorage.getItem('ti_hidden_tenders');
        const arr = raw ? JSON.parse(raw) : [];
        return new Set(Array.isArray(arr) ? arr.map((x) => String(x)) : []);
    } catch {
        return new Set();
    }
}

/**
 * Set hidden tender refs
 * @param {Set} refSet - Set of references
 * @returns {boolean}
 */
export function setHiddenTenderRefs(refSet) {
    try {
        const arr = Array.from(refSet || []);
        localStorage.setItem('ti_hidden_tenders', JSON.stringify(arr));
        return true;
    } catch {
        return false;
    }
}

/**
 * Check if tender is hidden
 * @param {string} ref - Tender reference
 * @returns {boolean}
 */
export function isTenderHidden(ref) {
    const r = (ref || '').toString().trim();
    if (!r) return false;
    return getHiddenTenderRefs().has(r);
}

/**
 * Hide tender
 * @param {string} ref - Tender reference
 * @returns {boolean}
 */
export function hideTender(ref) {
    const r = (ref || '').toString().trim();
    if (!r) return false;
    const set = getHiddenTenderRefs();
    set.add(r);
    return setHiddenTenderRefs(set);
}

/**
 * Unhide tender
 * @param {string} ref - Tender reference
 * @returns {boolean}
 */
export function unhideTender(ref) {
    const r = (ref || '').toString().trim();
    if (!r) return false;
    const set = getHiddenTenderRefs();
    set.delete(r);
    return setHiddenTenderRefs(set);
}

/**
 * Check if tender is watchlisted
 * @param {string} ref - Tender reference
 * @returns {boolean}
 */
export function isTenderWatchlisted(ref) {
    const r = (ref || '').toString().trim();
    if (!r) return false;
    return getActiveWatchlist().some((e) => e.tender_ref === r);
}

/**
 * Toggle watchlist for tender
 * @param {string} ref - Tender reference
 * @returns {boolean}
 */
export function toggleWatchlist(ref) {
    const tenderRef = (ref || '').toString().trim();
    if (!tenderRef) return false;

    const list = getActiveWatchlist();
    const idx = list.findIndex((e) => e.tender_ref === tenderRef);
    if (idx >= 0) {
        list.splice(idx, 1);
        const ok = setActiveWatchlist(list);
        return ok;
    }

    let actor = getCurrentUsername();
    if (!actor) actor = ensureUsername();
    if (!actor) return false;

    list.push({
        tender_ref: tenderRef,
        addedBy: actor,
        addedDate: new Date().toISOString().split('T')[0],
    });
    const ok = setActiveWatchlist(list);
    return ok;
}

/**
 * Get preferred view mode
 * @returns {string}
 */
export function getPreferredViewMode() {
    const saved = (localStorage.getItem('preferredView') || '').toString().trim().toLowerCase();
    return ['detailed', 'compact', 'card'].includes(saved) ? saved : 'detailed';
}

/**
 * Set preferred view mode
 * @param {string} mode - View mode
 */
export function setPreferredViewMode(mode) {
    localStorage.setItem('preferredView', mode);
}
