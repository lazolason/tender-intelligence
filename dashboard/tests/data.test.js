import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';

import { config } from '../js/modules/config.js';
import { clearCachedPayload, loadTenderPayload } from '../js/modules/data.js';

describe('dashboard data loading', () => {
  const originalUrls = [...config.tenderJsonUrls];

  beforeEach(() => {
    clearCachedPayload();
  });

  afterEach(() => {
    config.tenderJsonUrls = [...originalUrls];
    vi.restoreAllMocks();
    clearCachedPayload();
  });

  it('chooses the freshest live payload instead of the first successful one', async () => {
    const stalePayload = {
      meta: { last_sync: '2026-01-22 10:06' },
      tenders: [{ ref: 'OLD-1' }, { ref: 'OLD-2' }],
    };
    const freshPayload = {
      meta: { last_sync: '2026-04-06 12:27' },
      tenders: [{ ref: 'NEW-1' }, { ref: 'NEW-2' }, { ref: 'NEW-3' }],
      planned_opportunities: [{ external_id: 'TPP-1', category: 'MEXEL' }],
    };

    config.tenderJsonUrls = ['/stale.json', '/fresh.json'];
    global.fetch = vi.fn((url) => {
      if (String(url).startsWith('/stale.json')) {
        return Promise.resolve({
          ok: true,
          json: async () => stalePayload,
          headers: { get: () => null },
        });
      }
      if (String(url).startsWith('/fresh.json')) {
        return Promise.resolve({
          ok: true,
          json: async () => freshPayload,
          headers: { get: () => null },
        });
      }
      return Promise.reject(new Error(`Unexpected URL: ${url}`));
    });

    const result = await loadTenderPayload({ forceRefresh: true });

    expect(global.fetch).toHaveBeenCalledTimes(2);
    expect(result.meta.last_sync).toBe('2026-04-06 12:27');
    expect(result.tenders).toHaveLength(3);
    expect(result.tenders[0].ref).toBe('NEW-1');
    expect(result.plannedOpportunities).toHaveLength(1);
    expect(result.plannedOpportunities[0].external_id).toBe('TPP-1');
  });
});
