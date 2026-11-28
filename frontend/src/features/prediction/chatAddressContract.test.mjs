import assert from 'node:assert/strict';
import test from 'node:test';
import { publicChatResponse } from './chat.js';
import { chatPresentation } from './chatPresentation.js';

function packet({ nearby = false, incomplete = false } = {}) {
  return {
    mode: 'SAFE', generationMode: 'EVIDENCE_ONLY', retrievalMode: 'TOOL_EVIDENCE_ONLY',
    answer: incomplete ? 'Vẫn còn trang chưa kiểm tra.' : 'Chưa tìm thấy tin theo địa chỉ.',
    recommendedProperties: [], citations: [], dataLimitations: [],
    evidence: {
      addressQuery: '300 Dũng Sĩ Thanh Khê', addressSearchComplete: !incomplete,
      ...(nearby ? { nearAddress: true, radiusMeters: 1000 } : {}),
      responseKind: incomplete ? 'CLARIFICATION_REQUIRED' : 'NO_MATCHES',
      clarification: incomplete ? 'ADDRESS_SEARCH_INCOMPLETE' : nearby ? 'ADDRESS_NEARBY_EMPTY' : 'ADDRESS_NO_MATCH',
      recommendationMethod: nearby ? 'NEARBY_DISTANCE' : 'ADDRESS_FILTER',
      recommendationSearch: { performed: true, resultCount: 0, sourcePath: '/api/v1/properties', criteriaHash: 'a'.repeat(64) },
      generation: { accepted: false, reason: incomplete ? 'NOT_NEEDED_FOR_INCOMPLETE_SEARCH' : 'NOT_NEEDED_FOR_EMPTY_SEARCH' },
      criteria: { propertyType: 'ALL' }, retrievedSourceIds: [], semanticRetrieval: { indexVersion: null, hits: [] },
    },
  };
}

test('exhausted address and nearby searches render without a budget', () => {
  for (const nearby of [false, true]) {
    const data = packet({ nearby });
    assert.equal(publicChatResponse(data), data);
    const view = chatPresentation(data);
    assert.equal(view.summary, data.answer);
    assert.equal(view.noMatches, true);
  }
});

test('incomplete discovery renders the search limitation', () => {
  const data = packet({ nearby: true, incomplete: true });
  assert.equal(chatPresentation(data).summary, data.answer);
  assert.equal(chatPresentation(data).noMatches, false);
});

test('source, outcome and evidence must belong to the same search', () => {
  const reject = data => assert.throws(() => publicChatResponse(data), { code: 'UNSAFE_CHAT_RESPONSE' });
  for (const change of [
    e => { e.recommendationSearch.sourcePath = '/api/v1/recommendations'; },
    e => { e.clarification = 'ADDRESS_NEARBY_EMPTY'; },
    e => { e.addressSearchComplete = false; },
    e => { e.recommendationSearch.criteriaHash = 'missing'; },
    e => { e.retrievedSourceIds.push('unrelated'); },
    e => { delete e.semanticRetrieval; },
    e => { e.criteria.budgetVnd = 'not a number'; },
  ]) {
    const data = packet();
    change(data.evidence);
    reject(data);
  }
});
