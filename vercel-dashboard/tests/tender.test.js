/**
 * Tests for tender-related functions
 */

import { describe, it, expect, beforeEach } from 'vitest';
import { getPriority, classifyTender, computeDecision, getDaysUntil, getCountdownHtml, normalizeAttachments } from '../js/modules/tender.js';

describe('Tender Functions', () => {
  describe('getPriority', () => {
    it('should return HIGH for tenders closing within 3 days', () => {
      const tender = {
        closing_date: new Date(Date.now() + 2 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      expect(getPriority(tender)).toBe('HIGH');
    });

    it('should return MEDIUM for tenders closing within 7 days', () => {
      const tender = {
        closing_date: new Date(Date.now() + 5 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      expect(getPriority(tender)).toBe('MEDIUM');
    });

    it('should return LOW for tenders closing after 7 days', () => {
      const tender = {
        closing_date: new Date(Date.now() + 10 * 24 * 60 * 60 * 1000).toISOString().split('T')[0]
      };
      expect(getPriority(tender)).toBe('LOW');
    });
  });

  describe('classifyTender', () => {
    it('should classify water treatment tenders as TES', () => {
      const tender = {
        description: 'Water treatment plant maintenance',
        title: 'Water treatment services'
      };
      const classification = classifyTender(tender);
      expect(classification.company).toBe('TES');
    });

    it('should classify electrical tenders as Phakathi', () => {
      const tender = {
        description: 'Electrical infrastructure installation',
        title: 'HVAC and electrical systems'
      };
      const classification = classifyTender(tender);
      expect(classification.company).toBe('Phakathi');
    });
  });

  describe('computeDecision', () => {
    it('should return BID for high-scoring tenders', () => {
      const tender = {
        scores: {
          composite: 8.5
        }
      };
      const decision = computeDecision(tender);
      expect(decision).toBe('BID');
    });

    it('should return SKIP for low-scoring tenders', () => {
      const tender = {
        scores: {
          composite: 2.5
        }
      };
      const decision = computeDecision(tender);
      expect(decision).toBe('SKIP');
    });
  });

  describe('getDaysUntil', () => {
    it('should return correct days until closing date', () => {
      const tomorrow = new Date(Date.now() + 24 * 60 * 60 * 1000);
      const days = getDaysUntil(tomorrow.toISOString().split('T')[0]);
      expect(days).toBe(1);
    });

    it('should return null for invalid date', () => {
      const days = getDaysUntil(null);
      expect(days).toBeNull();
    });

    it('should return negative days for past dates', () => {
      const yesterday = new Date(Date.now() - 24 * 60 * 60 * 1000);
      const days = getDaysUntil(yesterday.toISOString().split('T')[0]);
      expect(days).toBeLessThan(0);
    });
  });

  describe('getCountdownHtml', () => {
    it('should return urgent HTML for today', () => {
      const html = getCountdownHtml(new Date().toISOString().split('T')[0]);
      expect(html).toContain('urgent');
      expect(html).toContain('TODAY');
    });

    it('should return warning HTML for 5 days', () => {
      const date = new Date(Date.now() + 5 * 24 * 60 * 60 * 1000);
      const html = getCountdownHtml(date.toISOString().split('T')[0]);
      expect(html).toContain('warning');
    });

    it('should return normal HTML for 10 days', () => {
      const date = new Date(Date.now() + 10 * 24 * 60 * 60 * 1000);
      const html = getCountdownHtml(date.toISOString().split('T')[0]);
      expect(html).toContain('normal');
    });
  });

  describe('normalizeAttachments', () => {
    it('should normalize attachment objects', () => {
      const attachments = [
        { url: 'https://example.com/doc.pdf', name: 'Document' },
        'https://example.com/other.pdf'
      ];
      const normalized = normalizeAttachments(attachments);
      expect(normalized).toHaveLength(2);
      expect(normalized[0]).toHaveProperty('url');
      expect(normalized[0]).toHaveProperty('name');
      expect(normalized[1]).toHaveProperty('url');
    });

    it('should handle empty or null attachments', () => {
      expect(normalizeAttachments(null)).toEqual([]);
      expect(normalizeAttachments([])).toEqual([]);
    });
  });
});
