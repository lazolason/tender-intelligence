import { it, expect } from 'vitest';
import { searchCapturedNotices } from '../js/modules/discovery.js';

it('finds an unassessed item by attachment name outside the shortlist', () => {
    const rows = [{ ref: 'A', title: 'Supply equipment', discovery: { tier: 'unassessed' }, attachments: [{ name: 'Condensate chemistry.pdf' }] }];
    expect(searchCapturedNotices(rows, 'condensate chemistry')).toEqual(rows);
    expect(searchCapturedNotices(rows, '', 'strong_candidate')).toEqual([]);
    expect(searchCapturedNotices(rows, 'not present')).toEqual([]);
});

it('normalizes punctuation variants when finding display supply', () => {
    const row = { title: '86 inch Interactive LED Touch Panels', attachments: [] };
    expect(searchCapturedNotices([row], '86-inch touch panels')).toEqual([row]);
});
