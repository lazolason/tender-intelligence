/**
 * Tender classification, filtering, and rendering
 */

import { state, teamMembers, tenderLifecycleStatuses, tenderFinalStatuses, ITEM_HEIGHT, CHUNK_SIZE, BUFFER } from './config.js';
import { escapeHtml, formatNiceDateTime, parseFlexibleDate, formatBytes } from '../utils/helpers.js';
import { getTenderAssignment, getTenderCurrentStatus, isTenderWatchlisted, toggleWatchlist, getTenderStatusHistory } from './storage.js';

/**
 * Get company from tender
 * @param {Object} t - Tender object
 * @returns {string}
 */
export function getCompany(t) {
    return (t.company || t.category || "").trim();
}

/**
 * Get priority from tender
 * @param {Object} t - Tender object
 * @returns {string}
 */
export function getPriority(t) {
    return (t.priority || t.scores?.priority || "").toUpperCase();
}

/**
 * Get tender company scope
 * @param {Object} tender - Tender object
 * @returns {string}
 */
export function getTenderCompanyScope(tender) {
    const t = tender || {};
    const raw = (t.company || t.company_scope || t.scope || t.category || '').toString().trim();
    const norm = raw.toLowerCase();
    if (norm === 'tes') return 'TES';
    if (norm === 'phakathi') return 'Phakathi';
    if (norm === 'both' || norm === 'tes + phakathi' || norm === 'tes/phakathi') return 'Both';

    try {
        const relevance = classifyTender(t)?.relevance;
        if (relevance === 'TES' || relevance === 'Phakathi' || relevance === 'Both') return relevance;
    } catch (e) {}

    const scores = t.scores || {};
    const tesSuit = Number(scores.tes_suitability);
    const phSuit = Number(scores.phakathi_suitability);
    const hasTes = Number.isFinite(tesSuit) && tesSuit > 0;
    const hasPh = Number.isFinite(phSuit) && phSuit > 0;
    if (hasTes && hasPh) return 'Both';
    if (hasTes) return 'TES';
    if (hasPh) return 'Phakathi';

    return 'Unknown';
}

/**
 * Check if tender is active
 * @param {Object} t - Tender object
 * @returns {boolean}
 */
export function isTenderActive(t) {
    const days = getDaysUntil(t?.closing_date);
    return days === null || days >= 0;
}

/**
 * Calculate days until closing date
 * @param {string} dateStr - Date string
 * @returns {number|null}
 */
export function getDaysUntil(dateStr) {
    const closing = parseFlexibleDate(dateStr);
    if (!closing) return null;
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    closing.setHours(0, 0, 0, 0);
    return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
}

/**
 * Get countdown HTML for date
 * @param {string} dateStr - Date string
 * @returns {string}
 */
export function getCountdownHtml(dateStr) {
    const days = getDaysUntil(dateStr);
    if (days === null) return '<span class="countdown normal">📅 TBC</span>';
    if (days < 0) return '<span class="countdown closed">CLOSED</span>';
    if (days === 0) return '<span class="countdown urgent">🔴 TODAY!</span>';
    if (days === 1) return '<span class="countdown urgent">🔴 TOMORROW!</span>';
    if (days <= 3) return `<span class="countdown urgent">⚠️ ${days} days</span>`;
    if (days <= 7) return `<span class="countdown warning">📅 ${days} days</span>`;
    return `<span class="countdown normal">📅 ${days} days</span>`;
}

/**
 * Classify tender
 * @param {Object} tender - Tender object
 * @returns {Object}
 */
export function classifyTender(tender) {
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

/**
 * Compute bid decision
 * @param {Object} tender - Tender object
 * @returns {Object}
 */
export function computeDecision(tender) {
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

/**
 * Generate AI insight for tender
 * @param {Object} tender - Tender object
 * @returns {string}
 */
export function generateAIInsight(tender) {
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
        relevanceText = 'This tender aligns with Phakathi\'s mechanical/electrical offering based on installation, maintenance, pumps, or fabrication scope.';
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

/**
 * Get status meta for status
 * @param {string} status - Status value
 * @returns {Object}
 */
export function getStatusMeta(status) {
    const s = (status || '').toString().trim();
    return tenderLifecycleStatuses.find((x) => x.value === s) || tenderLifecycleStatuses[0];
}

/**
 * Get filtered tenders for export
 * @returns {Array}
 */
export function getFilteredTendersForExport() {
    const filter = state.currentFilter;
    let filtered = state.tenders
        .filter((t) => !isTenderHidden(t?.ref))
        .filter((t) => getDaysUntil(t?.closing_date) === null || getDaysUntil(t?.closing_date) >= 0);

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

    // Apply advanced filters (intersection)
    if (window.advancedFilters && typeof window.advancedFilters.applyFilters === 'function') {
        filtered = window.advancedFilters.applyFilters(filtered);
    }

    // Apply smart search (intersection)
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

/**
 * Smart search tenders
 * @param {string} query - Search query
 * @param {Array} tenders - Tenders to search
 * @returns {Array}
 */
export function smartSearchTenders(query, tenders) {
    // When called from UI (no `tenders` passed), update state + rerender.
    if (typeof tenders === 'undefined') {
        state.searchQuery = (query || '').toString().trim();
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

/**
 * Normalize attachments
 * @param {Object} tender - Tender object
 * @returns {Array}
 */
export function normalizeAttachments(tender) {
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

/**
 * Get attachment icon
 * @param {string} ext - File extension
 * @returns {string}
 */
export function getAttachmentIcon(ext) {
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

/**
 * Reset tender infinite list
 */
export function resetTenderInfiniteList() {
    state.visibleTenderCount = CHUNK_SIZE;
    state.totalMatchingCount = 0;
    state.loadingMore = false;
    state.watchlistAddedBy = state.watchlistAddedBy || '';
    const container = document.getElementById('tenderTableScroll');
    if (container) container.scrollTop = 0;
}

/**
 * Update tender load progress
 * @param {number} visible - Visible count
 * @param {number} total - Total count
 */
export function updateTenderLoadProgress(visible, total) {
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

/**
 * Show tender skeleton loading
 * @param {number} count - Number of skeleton rows
 */
export function showTenderSkeleton(count = 8) {
    const tbody = document.getElementById('tenderList') || document.getElementById('tender-table-body');
    if (!tbody) return;
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
        </tr>
      `
    );
    tbody.innerHTML = rows.join('');
}
