import { it, expect } from 'vitest';
import { renderCoverage } from '../js/modules/coverage.js';

it('shows failed sources, review candidates and escapes untrusted document metadata', () => {
    document.body.innerHTML = '<div id="sourceHealth"></div><div id="opportunityReview"></div><span id="coverageCount"></span>';
    renderCoverage({ source_health: [{ source: 'Water Boards', status: 'partial', records: 4, error: '<img onerror=alert(1)>' }], review_queue: [{ ref: 'A', title: '<script>bad</script>', url: 'javascript:alert(1)', reason: 'Needs review', limitations: ['Unread PDF'] }] });
    expect(document.getElementById('sourceHealth').textContent).toContain('partial');
    expect(document.getElementById('opportunityReview').textContent).toContain('Unread PDF');
    expect(document.querySelector('script, img, a')).toBeNull();
    expect(document.getElementById('coverageCount').textContent).toBe('(1 to review)');
});
