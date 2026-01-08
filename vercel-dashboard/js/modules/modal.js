/**
 * Tender detail modal and related functionality
 */

import { teamMembers, tenderLifecycleStatuses, tenderFinalStatuses } from './config.js';
import {
    escapeHtml,
    formatNiceDateTime,
    formatBytes,
    newId,
    relativeTime,
    hashColorForUser,
    initials,
    renderMarkdownLite
} from '../utils/helpers.js';
import {
    getTenderAssignment,
    setTenderAssignment,
    clearTenderAssignment,
    getTenderStatusHistory,
    addTenderStatusHistory,
    getTenderCurrentStatus,
    setTenderLifecycleStatus,
    getTenderComments,
    saveTenderComments,
    getCurrentUsername,
    ensureUsername,
    getMentionsStore,
    addMentionsForUsers,
    clearMentionsForTender,
    getUnreadMentionCount
} from './storage.js';
import {
    getCompany,
    getPriority,
    classifyTender,
    computeDecision,
    getCountdownHtml,
    normalizeAttachments,
    getAttachmentIcon,
    getStatusMeta
} from './tender.js';

/**
 * Open tender detail modal
 * @param {Object} tender - Tender object
 */
export function openTenderModal(tender) {
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
        similarEl.innerHTML = `<p style="color:#888;">Open the "Similar" tab to calculate matches.</p>`;
    }

    const discussionEl = document.getElementById('tenderDetailDiscussion');
    if (discussionEl) {
        discussionEl.innerHTML = `<p style="color:#888;">Open the "Discussion" tab to view and post comments.</p>`;
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

/**
 * Close tender detail modal
 */
export function closeTenderModal() {
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

/**
 * Set tender detail tab
 * @param {string} tab - Tab ID
 */
export function setTenderDetailTab(tab) {
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

/**
 * Render tender status timeline
 * @param {string} tenderRef - Tender reference
 * @returns {string}
 */
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

/**
 * Render discussion tab
 * @param {Object} tender - Tender object
 */
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

/**
 * Parse mentions from text
 * @param {string} text - Text to parse
 * @returns {Array}
 */
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

/**
 * Update mention badges for tender
 * @param {Object} tender - Tender object
 */
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
