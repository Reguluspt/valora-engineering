import test from 'node:test';
import assert from 'node:assert/strict';
import { amount, suggestedPrice, nextViewed, warnings, previewTotal, extractLinks, sourcePriorityEligible, classifyIdentityChange } from '../src/logic.mjs';

test('unknown price remains unknown instead of zero', () => {
  assert.equal(amount(null, 3), null);
  assert.equal(suggestedPrice(null, 5), null);
  assert.equal(suggestedPrice(100000000, null), null);
  assert.equal(suggestedPrice(100000000, 5, false), null);
});

test('survey + transport percent derives suggestion but does not decide human price', () => {
  assert.equal(suggestedPrice(100000000, 5), 105000000);
  assert.equal(amount(105000000, 2), 210000000);
});

test('leaving an asset marks viewed only for the previous asset', () => {
  const before = [{ id: 'A', viewed: false }, { id: 'B', viewed: false }];
  assert.deepEqual(nextViewed(before, 'A').map(x => x.viewed), [true, false]);
  assert.equal(before[0].viewed, false);
});

test('summary counts independent overlapping warnings and known total only', () => {
  const assets = [
    { id:'A', viewed:false, proposed:100, qty:2, sources:[], needsRecheck:true, match:'none' },
    { id:'B', viewed:true, proposed:null, qty:4, sources:[{links:['https://example.org'], images:[]}], needsRecheck:false, match:'high' },
  ];
  assert.deepEqual(warnings(assets), {unviewed:1,missingPrice:1,missingEvidence:1,recheck:1});
  assert.equal(previewTotal(assets), 200);
});

test('links deduplicate and maintain only URLs', () => {
  assert.deepEqual(extractLinks('Nguồn https://example.com/a, tham khảo https://example.com/a và https://x.vn'), ['https://example.com/a', 'https://x.vn']);
});

test('source auto-fill demonstration cannot bypass match gate', () => {
  assert.equal(sourcePriorityEligible({match:'similar',sources:[{}]}), false);
  assert.equal(sourcePriorityEligible({match:'high',sources:[{}]}), true);
  assert.equal(sourcePriorityEligible({match:'high',sources:[]}), false);
});

test('identity classification notices material editing', () => {
  assert.equal(classifyIdentityChange('15 kW', '22 kW'), true);
  assert.equal(classifyIdentityChange('Model X100', ' model x100 '), false);
});
