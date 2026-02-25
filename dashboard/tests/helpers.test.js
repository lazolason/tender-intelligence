/**
 * Tests for helper utility functions
 */

import { describe, it, expect } from 'vitest';
import { escapeHtml, normalizeText, debounce, throttle, delay } from '../js/utils/helpers.js';

describe('Helper Functions', () => {
  describe('escapeHtml', () => {
    it('should escape HTML special characters', () => {
      expect(escapeHtml('<script>alert("xss")</script>')).toBe('&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;');
    });

    it('should handle null and undefined', () => {
      expect(escapeHtml(null)).toBe('');
      expect(escapeHtml(undefined)).toBe('');
    });

    it('should handle numbers', () => {
      expect(escapeHtml(123)).toBe('123');
    });
  });

  describe('normalizeText', () => {
    it('should trim and lowercase text', () => {
      expect(normalizeText('  HELLO  WORLD  ')).toBe('hello world');
    });

    it('should handle empty strings', () => {
      expect(normalizeText('')).toBe('');
      expect(normalizeText(null)).toBe('');
    });

    it('should collapse multiple spaces', () => {
      expect(normalizeText('hello     world')).toBe('hello world');
    });
  });

  describe('debounce', () => {
    it('should debounce function calls', async () => {
      let callCount = 0;
      const debouncedFn = debounce(() => {
        callCount++;
      }, 100);

      debouncedFn();
      debouncedFn();
      debouncedFn();

      expect(callCount).toBe(0);

      await new Promise(resolve => setTimeout(resolve, 150));
      expect(callCount).toBe(1);
    });
  });

  describe('throttle', () => {
    it('should throttle function calls', async () => {
      let callCount = 0;
      const throttledFn = throttle(() => {
        callCount++;
      }, 100);

      throttledFn();
      throttledFn();
      throttledFn();

      expect(callCount).toBe(1);

      await new Promise(resolve => setTimeout(resolve, 150));
      throttledFn();
      expect(callCount).toBe(2);
    });
  });

  describe('delay', () => {
    it('should delay execution', async () => {
      const start = Date.now();
      await delay(100);
      const elapsed = Date.now() - start;
      expect(elapsed).toBeGreaterThanOrEqual(100);
      expect(elapsed).toBeLessThan(150);
    });
  });
});
