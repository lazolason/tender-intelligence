import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import {
  describeActiveEmptyState,
  getFilteredActiveTenders,
  getRecentMatchedTenders,
} from '../js/modules/dashboardSummary.js';

describe('dashboard summary helpers', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    vi.setSystemTime(new Date('2026-04-06T12:00:00Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  const tenders = [
    {
      ref: 'ACTIVE-001',
      title: 'Active Mexel Tender',
      description: 'Cooling water treatment chemicals',
      category: 'MEXEL',
      priority: 'HIGH',
      closing_date: '2026-04-20',
    },
    {
      ref: 'CLOSED-001',
      title: 'Closed Mexel Tender',
      description: 'Boiler water treatment services',
      category: 'MEXEL',
      priority: 'MEDIUM',
      closing_date: '2026-03-31',
    },
    {
      ref: 'CLOSED-002',
      title: 'Older Closed Tender',
      description: 'Cooling tower treatment',
      category: 'MEXEL',
      priority: 'LOW',
      closing_date: '2026-03-20',
    },
  ];

  it('filters active tenders by current dashboard view', () => {
    const filtered = getFilteredActiveTenders(tenders, { filter: 'HIGH', searchQuery: 'active' });
    expect(filtered).toHaveLength(1);
    expect(filtered[0].ref).toBe('ACTIVE-001');
  });

  it('describes the no-active state when all snapshot tenders are closed', () => {
    const emptyState = describeActiveEmptyState(tenders.slice(1), { filter: 'all', searchQuery: '' });

    expect(emptyState.title).toContain('No currently open');
    expect(emptyState.showRecentMatches).toBe(true);
  });

  it('returns recent matches ordered by most recent close first', () => {
    const recent = getRecentMatchedTenders(tenders, { limit: 2 });

    expect(recent).toHaveLength(2);
    expect(recent[0].ref).toBe('CLOSED-001');
    expect(recent[1].ref).toBe('CLOSED-002');
  });
});
