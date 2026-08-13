import { getCompany, getDaysUntil, getPriority, isTenderActive } from './tender.js';

export function normalizeCompanyLabel(tender) {
    const value = (getCompany(tender) || '').trim();
    return value || 'Unknown';
}

function matchesFilter(tender, filter) {
    const currentFilter = String(filter || 'all');
    if (currentFilter.toLowerCase() === 'mexel') {
        return normalizeCompanyLabel(tender).toLowerCase() === 'mexel';
    }
    if (currentFilter.toLowerCase() === 'phakathi') {
        return normalizeCompanyLabel(tender).toLowerCase() === 'phakathi';
    }
    if (['HIGH', 'MEDIUM', 'LOW'].includes(currentFilter)) {
        return getPriority(tender) === currentFilter;
    }
    return true;
}

function matchesSearch(tender, searchQuery) {
    const query = String(searchQuery || '').trim().toLowerCase();
    if (!query) return true;
    return [
        tender?.ref,
        tender?.title,
        tender?.description,
        tender?.client,
        tender?.source,
        tender?.category,
    ]
        .map((value) => (value || '').toString().toLowerCase())
        .join(' ')
        .includes(query);
}

function sortByClosingSoonest(a, b) {
    return (getDaysUntil(a?.closing_date) ?? 999) - (getDaysUntil(b?.closing_date) ?? 999);
}

function sortByMostRecentClose(a, b) {
    const aDays = getDaysUntil(a?.closing_date);
    const bDays = getDaysUntil(b?.closing_date);

    if (aDays === null && bDays === null) return 0;
    if (aDays === null) return 1;
    if (bDays === null) return -1;
    return bDays - aDays;
}

export function getFilteredActiveTenders(tenders, { filter = 'all', searchQuery = '' } = {}) {
    return (Array.isArray(tenders) ? tenders : [])
        .filter(isTenderActive)
        .filter((tender) => matchesFilter(tender, filter))
        .filter((tender) => matchesSearch(tender, searchQuery))
        .sort(sortByClosingSoonest);
}

export function getRecentMatchedTenders(tenders, { limit = 6 } = {}) {
    const list = Array.isArray(tenders) ? tenders : [];
    const closed = list.filter((tender) => !isTenderActive(tender)).sort(sortByMostRecentClose);
    const fallback = list
        .filter((tender) => isTenderActive(tender))
        .sort(sortByClosingSoonest);
    return [...closed, ...fallback].slice(0, Math.max(0, limit | 0));
}

export function describeActiveEmptyState(tenders, { filter = 'all', searchQuery = '' } = {}) {
    const allTenders = Array.isArray(tenders) ? tenders : [];
    const activeTenders = allTenders.filter(isTenderActive);
    const filteredActive = getFilteredActiveTenders(allTenders, { filter, searchQuery });
    const hasSearch = Boolean(String(searchQuery || '').trim());
    const normalizedFilter = String(filter || 'all');

    if (allTenders.length === 0) {
        return {
            title: 'No matched tenders in this snapshot',
            message: 'The pipeline is healthy, but the current dashboard snapshot is empty. Run a fresh scan or sync to repopulate it.',
            showRecentMatches: false,
        };
    }

    if (activeTenders.length === 0) {
        return {
            title: 'No currently open MEXEL-matched tenders',
            message: `This snapshot still contains ${allTenders.length} matched tender${allTenders.length === 1 ? '' : 's'}, but all of them are already closed. Recent matches are shown below for reference.`,
            showRecentMatches: true,
        };
    }

    if (filteredActive.length === 0) {
        const qualifier = hasSearch
            ? 'the current search'
            : normalizedFilter !== 'all'
                ? `the "${normalizedFilter}" filter`
                : 'the current dashboard filters';
        return {
            title: 'No active tenders match the current view',
            message: `Open tenders exist in the snapshot, but none match ${qualifier}. Clear the filters or search to see them, and use recent matches below for context.`,
            showRecentMatches: true,
        };
    }

    return {
        title: '',
        message: '',
        showRecentMatches: false,
    };
}
