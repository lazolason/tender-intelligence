const config = {
    cacheKey: "ti_dashboard_payload_v1",
    cacheTtlMs: 60 * 60 * 1000, // 1 hour
    tenderJsonUrls: [
        "/tenders.json",
        "/public/build/tenders.json",
        "/public/tenders-latest.json",
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
};

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
    const status = t.status || getCountdownHtml(t.closing_date) || '-';
    const link = t.url ? `<a href="${t.url}" target="_blank" rel="noopener" class="view-btn" style="padding: 6px 15px; font-size: 0.8rem;" onclick="event.stopPropagation()">Open ↗</a>` : '-';
    const decision = computeDecision(t);
    const scopeClass = relevance === 'OutOfScope' ? 'scope-pill-out' : relevance === 'TES' ? 'scope-pill-tes' : relevance === 'Phakathi' ? 'scope-pill-phakathi' : relevance === 'Both' ? 'scope-pill-both' : 'scope-pill-out';
    const scopeText = relevance === 'OutOfScope' ? 'Not in scope' : relevance === 'TES' ? 'TES' : relevance === 'Phakathi' ? 'Phakathi' : relevance === 'Both' ? 'TES + Phakathi' : 'Review';
    const decisionPill = `<span class="decision-pill ${decision.className}">${decision.label}<span class="reason"> · ${decision.reason}</span><span class="confidence"> · ${decision.confidence}%</span></span>`;
    const categoryTags = (categories || []).map(c => `<span class="category-tag">${c}</span>`).join('');

    const row = document.createElement('tr');
    row.style = "border-bottom: 1px solid rgba(255,255,255,0.05); transition: background 0.2s; cursor: pointer;";
    row.onclick = () => openTenderModal(idx);
    row.title = "Click to view tender details";
    row.onmouseover = () => row.style.background = 'rgba(255,255,255,0.05)';
    row.onmouseout = () => row.style.background = 'transparent';
    row.innerHTML = `
        <td style="padding: 15px;">
            <div style="font-weight: 600; color: #fff; margin-bottom: 4px;">${title}</div>
            <div style="font-size: 0.8rem; color: #667eea;">${t.ref || '-'}</div>
            <div style="margin-top:4px;">${categoryTags}</div>
        </td>
        <td style="padding: 15px; color: #ccc;">${source}</td>
        <td style="padding: 15px; color: #ccc;">${company}</td>
        <td style="padding: 15px; color: #ccc;">${priority}</td>
        <td style="padding: 15px; color: #ccc;">${closeDate}</td>
        <td style="padding: 15px; font-weight: bold; color: #fff;">${fitScore}</td>
        <td style="padding: 15px; color: #ccc;">${revenueScore}</td>
        <td style="padding: 15px; color: #ccc;">${riskScore}</td>
        <td style="padding: 15px;">${status}</td>
        <td style="padding: 15px;"><span class="scope-pill ${scopeClass}">${scopeText}</span></td>
        <td style="padding: 15px;">${decisionPill}</td>
        <td style="padding: 15px;">${link}</td>
    `;
    return row;
}


function renderTenders() {
    const list = document.getElementById('tender-table-body') || document.getElementById('tenderList');
    if (!list) {
        const table = document.querySelector('#dashboard table');
        if (table) {
            const list = document.createElement('tbody');
            list.id = 'tender-table-body';
            table.appendChild(list);
        } else {
            return;
        }
    }
    
    const filter = state.currentFilter;
    let filtered = state.tenders.filter(t => getDaysUntil(t.closing_date) === null || getDaysUntil(t.closing_date) >= 0);

    if (filter === 'TES' || filter === 'Phakathi' || filter === 'Both') {
        filtered = filtered.filter(t => getCompany(t) === filter);
    } else if (filter === 'HIGH' || filter === 'MEDIUM' || filter === 'LOW') {
        filtered = filtered.filter(t => getPriority(t) === filter);
    }

    // Sort by closing date (urgent first)
    filtered.sort((a, b) => {
        const daysA = getDaysUntil(a.closing_date) ?? 999;
        const daysB = getDaysUntil(b.closing_date) ?? 999;
        return daysA - daysB;
    });

    const hideOut = document.getElementById('hide-out-of-scope');
    const hideOutOfScope = hideOut && hideOut.checked;

    const classified = filtered
        .map(t => ({ tender: t, classification: classifyTender(t) }))
        .filter(item => !(hideOutOfScope && item.classification.relevance === 'OutOfScope'));

    list.innerHTML = ''; // Clear the list

    if (classified.length === 0) {
        list.innerHTML = '<tr><td colspan="12" class="empty-state" style="text-align:center; padding: 40px;"><h3>No tenders found</h3><p>Try a different filter...</p></td></tr>';
        return;
    }

    state.currentTenders = classified.map(item => item.tender);
    classified.forEach((item, idx) => {
        list.appendChild(createTenderRow(item, idx));
    });
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
    state.currentFilter = filter;
    document.querySelectorAll('.filter-tab').forEach(tab => {
        tab.classList.remove('active');
        if (tab.textContent.toLowerCase().includes(filter.toLowerCase()) ||
            (filter === 'all' && tab.textContent.includes('All')) ||
            (filter === 'HIGH' && tab.textContent.includes('Urgent'))) {
            tab.classList.add('active');
        }
    });
    renderTenders();
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

function writeCachedPayload(payload) {
    try {
        const { meta } = validatePayloadShape(payload);
        localStorage.setItem(
            config.cacheKey,
            JSON.stringify({
                payload,
                storedAt: new Date().toISOString(),
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
        clearCachedPayload();
    }

    let lastErr;
    for (const url of config.tenderJsonUrls) {
        try {
            const res = await fetch(url + "?ts=" + Date.now(), { cache: "no-store" });
            if (!res.ok) throw new Error(`${url} -> ${res.status}`);
            const payload = await res.json();
            const { tenderList, meta } = validatePayloadShape(payload);
            writeCachedPayload(payload);
            return { tenders: tenderList, meta: meta || {}, source: url };
        } catch (e) {
            lastErr = e;
        }
    }

    if (!forceRefresh) {
        const cached = readCachedPayload();
        if (cached) {
            return { tenders: cached.tenders, meta: cached.meta, source: "localStorage", storedAt: cached.storedAt };
        }
    }

    const { tenderList, meta } = validatePayloadShape(config.seedPayload);
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

function openTenderModal(index) {
    const tender = state.currentTenders[index];
    const backdrop = document.getElementById('tender-modal-backdrop');
    if (!tender || !backdrop) return;

    const scores = tender.scores || {};
    const getScoreVal = (keys) => {
        for (const k of keys) {
            if (tender[k] !== undefined && tender[k] !== null) return tender[k];
            if (scores[k] !== undefined && scores[k] !== null) return scores[k];
        }
        return '-';
    };

    const getVal = (val) => (val !== undefined && val !== null && val !== '' ? val : '-');
    const days = getDaysUntil(tender.closing_date);
    let daysText = '-';
    if (days !== null) {
        daysText = days < 0 ? 'Closed' : `${days} day${days === 1 ? '' : 's'} remaining`;
    }

    document.getElementById('modal-tender-title').textContent = getVal(tender.title);
    document.getElementById('modal-tender-source').textContent = getVal(tender.source);
    document.getElementById('modal-tender-company').textContent = getVal(getCompany(tender));
    document.getElementById('modal-tender-priority').textContent = getVal(tender.priority);
    document.getElementById('modal-tender-close-date').textContent = getVal(tender.closing_date);
    document.getElementById('modal-tender-days-remaining').textContent = daysText;
    document.getElementById('modal-fit-score').textContent = getScoreVal(['score', 'fit', 'fit_score']);
    document.getElementById('modal-revenue-score').textContent = getScoreVal(['revenue_score', 'revenue']);
    document.getElementById('modal-suitability-score').textContent = getScoreVal(['suitability_score', 'suitability', 'industry', 'industry_score', 'composite', 'composite_score']);
    document.getElementById('modal-risk-score').textContent = getScoreVal(['risk_score', 'risk']);
    document.getElementById('modal-tender-description').textContent = getVal(tender.description || tender.long_description);
    document.getElementById('modal-tender-notes').textContent = getVal(tender.notes || tender.category || tender.reason);
    document.getElementById('modal-tender-ai-insight').textContent = generateAIInsight(tender);
    const decision = computeDecision(tender);
    const aiInsightEl = document.getElementById('modal-tender-ai-insight');
    if (aiInsightEl) {
        const existingRec = aiInsightEl.parentNode.querySelector('.ai-recommendation-container');
        if (existingRec) existingRec.remove();
        aiInsightEl.insertAdjacentHTML('afterend', `<div class="ai-recommendation-container" style="margin-top:8px;">AI Recommendation: <span class="decision-pill ${decision.className}" style="padding:4px 8px; font-size:0.75rem;">${decision.label}<span class="reason"> · ${decision.reason}</span><span class="confidence"> · ${decision.confidence}%</span></span></div>`);
    }
    const recoEl = document.getElementById('modal-tender-ai-reco');
    if (recoEl && decision) {
        recoEl.textContent = `${decision.label} — ${decision.confidence}% confidence. ${decision.reason}`;
    }

    const openBtn = document.getElementById('modal-open-link');
    if (openBtn) {
        openBtn.onclick = () => {
            if (tender.url) window.open(tender.url, '_blank');
        };
    }

    backdrop.classList.remove('hidden');
}

function closeTenderModal() {
    const backdrop = document.getElementById('tender-modal-backdrop');
    if (!backdrop) return;
    backdrop.classList.add('hidden');
}

function showTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById(tabId).classList.add('active');
    event.target.classList.add('active');

    if (tabId === 'calendar') renderCalendar();
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

function changeMonth(delta) {
    state.currentMonth.setMonth(state.currentMonth.getMonth() + delta);
    renderCalendar();
}

function applyTenderPayload({ loadedTenders, meta, source, storedAt, error }) {
    const effectiveMeta = meta || {};

    state.tenders = loadedTenders.map(normalizeTender);
    window.tendersData = state.tenders;
    window.dashboardMeta = effectiveMeta;

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
}

function refreshDashboardData() {
    const btn = document.getElementById("refresh-data-btn");
    if (btn) {
        btn.disabled = true;
        btn.textContent = "Refreshing…";
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

function init() {
    const modalCloseBtn = document.getElementById('modal-close-btn');
    if (modalCloseBtn) modalCloseBtn.addEventListener('click', closeTenderModal);

    const modalBackdrop = document.getElementById('tender-modal-backdrop');
    if (modalBackdrop) {
        modalBackdrop.addEventListener('click', (e) => {
            if (e.target === modalBackdrop) closeTenderModal();
        });
    }

    document.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') closeTenderModal();
    });

    const hideOutCheckbox = document.getElementById('hide-out-of-scope');
    if (hideOutCheckbox) {
        hideOutCheckbox.checked = false;
        hideOutCheckbox.addEventListener('change', () => renderTenders());
    }

    const exportPdfBtn = document.getElementById("export-pdf-btn");
    if (exportPdfBtn) exportPdfBtn.addEventListener("click", () => window.print());

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

    const lastSyncText = document.querySelector('.last-sync')?.textContent || '';
    const splitSync = lastSyncText.split('|');
    const parsedLastSync = splitSync[0]?.replace('🔄', '').trim() || '';
    const parsedNextRun = splitSync[1]?.replace('Next run:', '').trim() || 'Daily 08:00';
    const initialMeta = { last_sync: parsedLastSync || 'Last sync: –', next_run: parsedNextRun || 'Daily 08:00' };
    const initialSummary = getKpiSummary();
    updatePrintHeader(initialMeta, initialSummary);

    window.addEventListener("beforeprint", () => {
        const metaNow = window.dashboardMeta || initialMeta;
        updatePrintHeader(metaNow, getKpiSummary());
    });

    setDataStatus({ level: "warn", source: "initial", count: "–", updated: "–", error: "" });

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