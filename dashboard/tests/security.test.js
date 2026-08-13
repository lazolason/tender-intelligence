import { beforeAll, describe, expect, it, vi } from 'vitest';

import { safeHttpUrl } from '../js/utils/helpers.js';

let createTenderListItem;

beforeAll(async () => {
  window.__TI_DISABLE_AUTO_INIT__ = true;
  ({ createTenderListItem } = await import('../js/bridge.js'));
});

describe('dashboard untrusted-data hardening', () => {
  it('accepts only HTTP and HTTPS links', () => {
    expect(safeHttpUrl('https://example.com/tender')).toBe('https://example.com/tender');
    expect(safeHttpUrl('/relative', 'https://dashboard.example')).toBe('https://dashboard.example/relative');
    expect(safeHttpUrl('javascript:alert(1)')).toBe('');
    expect(safeHttpUrl('data:text/html,<script>alert(1)</script>')).toBe('');
    expect(safeHttpUrl('file:///etc/passwd')).toBe('');
  });

  it('renders malicious tender fields as text and drops unsafe links', () => {
    const openSpy = vi.spyOn(window, 'open').mockImplementation(() => null);
    const item = createTenderListItem({
      ref: '<img src=x onerror=alert(1)>',
      title: '<script>window.__xss = true</script>',
      client: '"><svg onload=alert(1)>',
      category: 'Mexel',
      company: 'Mexel',
      source: '<iframe srcdoc="bad"></iframe>',
      priority: 'HIGH',
      closing_date: '2099-01-01',
      matched_keywords: ['<img src=x onerror=alert(1)>'],
      url: 'javascript:alert(document.domain)',
    });

    expect(item.querySelector('script')).toBeNull();
    expect(item.querySelector('img')).toBeNull();
    expect(item.querySelector('svg')).toBeNull();
    expect(item.querySelector('iframe')).toBeNull();
    expect(item.querySelector('a.view-btn')).toBeNull();
    expect(item.textContent).toContain('<script>window.__xss = true</script>');

    item.click();
    expect(openSpy).not.toHaveBeenCalled();
    expect(window.__xss).toBeUndefined();
  });
});
