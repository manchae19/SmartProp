import test from 'node:test';
import assert from 'node:assert/strict';

import {
  validLand,
  PRICE_TYPE_LABEL,
  landDisplayValue,
  planningGroup,
  formatVnd,
  formatArea,
  landDetailPath,
} from '../src/features/land/landApi.js';
import { publicChatResponse } from '../src/features/prediction/chat.js';
import { chatPresentation, chatCriteriaSummary } from '../src/features/prediction/chatPresentation.js';
import {
  canShowReferenceMap,
  canAnalyzeDistance,
  canExploreNearby,
} from '../src/features/map/coordinateEligibility.js';
import { publicChatBoundary } from '../build/chatProxy.mjs';

const LAND_UUID = '11111111-2222-3333-4444-555555555555';
const PROP_UUID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';

function sampleLandRow(overrides = {}) {
  return {
    id: 'DN-QH-0001',
    landId: LAND_UUID,
    sourceCode: 'DN-QH-0001',
    displayName: 'Ô quy hoạch Hòa Xuân',
    kind: 'PLANNING_CELL',
    priceType: 'SIMULATED_DEMO',
    computedAreaSqm: 100,
    location: 'Hòa Xuân, Đà Nẵng',
    located: true,
    ...overrides,
  };
}

test('PR43 landApi: synthetic demo labels remain explicit and validLand enforces strict schema', () => {
  assert.equal(PRICE_TYPE_LABEL.SIMULATED_DEMO, 'Giá giả lập (demo · không phải giá thị trường)');
  assert.equal(
    landDisplayValue('Giá mô phỏng (không phải giá thị trường) — giả định demo'),
    'Giá giả lập (demo · không phải giá thị trường) — giả định demo'
  );
  assert.ok(
    landDisplayValue('Giả định kịch bản demo (sổ đỏ) — chưa có giấy chứng nhận thực tế được xác minh').includes('Giả định kịch bản demo'),
    'landDisplayValue must never strip synthetic demo disclaimers'
  );
  assert.equal(planningGroup('QHCX1', ''), 'green');
  assert.equal(planningGroup('QHNN', ''), 'agriculture');
  assert.equal(planningGroup('ODT', 'RESIDENTIAL_PLANNING'), 'housing');
  assert.ok(formatVnd(2_500_000_000).includes('tỷ'));
  assert.ok(formatArea(100).includes('m²'));
  assert.equal(landDetailPath({ landId: LAND_UUID, sourceCode: 'DN-QH-0001' }), `/land/${LAND_UUID}`);

  const valid = {
    version: 'LAND_V1',
    kind: 'LAND_SEARCH',
    rows: [sampleLandRow()],
    floodRecords: [],
    demoOnly: true,
  };
  assert.equal(validLand(valid), true);
  assert.equal(validLand({ ...valid, demoOnly: false }), false, 'non-demo land packet must be rejected');
  assert.equal(validLand({ ...valid, rows: [sampleLandRow({ landId: 'not-a-uuid' })] }), false);
  assert.equal(validLand({ ...valid, rows: [sampleLandRow({ priceType: 'UNKNOWN_PRICE' })] }), false);
});

test('PR43 chat contract: accepts valid LAND_SEARCH and BUYER_SEARCH while blocking leaks and mixed payloads', () => {
  const landPacket = {
    answer: 'Tìm thấy 1 ô quy hoạch tại Hòa Xuân.',
    mode: 'SAFE',
    generationMode: 'EVIDENCE_ONLY',
    retrievalMode: 'TOOL_EVIDENCE_ONLY',
    citations: [],
    recommendedProperties: [],
    dataLimitations: ['Bản demo Hòa Xuân: dữ liệu giả lập.'],
    evidence: {
      responseKind: 'LAND_SEARCH',
      filters: { maxPrice: 3_000_000_000 },
      land: {
        version: 'LAND_V1',
        kind: 'LAND_SEARCH',
        rows: [sampleLandRow()],
        floodRecords: [],
        filters: { maxPrice: 3_000_000_000 },
        areaFilters: { minArea: 80 },
        demoOnly: true,
      },
    },
  };
  const parsedLand = publicChatResponse(landPacket);
  const viewLand = chatPresentation(parsedLand);
  assert.equal(viewLand.summary, landPacket.answer);
  assert.equal(viewLand.cards.length, 0);
  const landSummary = chatCriteriaSummary(parsedLand);
  assert.ok(landSummary.some(s => s.includes('Hòa Xuân')));
  assert.ok(landSummary.some(s => s.includes('Diện tích từ 80 m²')));

  // Mixing citations or recommendedProperties into LAND_SEARCH must fail validation:
  assert.throws(() =>
    publicChatResponse({
      ...landPacket,
      recommendedProperties: [{ id: 'property:' + PROP_UUID }],
    })
  );

  // BUYER_SEARCH validates +15% ceiling and SmartProp/Land rows:
  const buyerPacket = {
    answer: 'Hiển thị 2 kết quả.',
    mode: 'SAFE',
    generationMode: 'EVIDENCE_ONLY',
    retrievalMode: 'TOOL_EVIDENCE_ONLY',
    citations: [
      {
        sourceId: 'property:' + PROP_UUID,
        url: '/api/v1/properties/' + PROP_UUID,
        version: '1',
        contentHash: 'a'.repeat(64),
        scope: 'PUBLIC',
        kind: 'PROPERTY_DETAIL',
        title: 'Đất nền Hòa Xuân',
      },
    ],
    recommendedProperties: [],
    dataLimitations: [],
    evidence: {
      responseKind: 'BUYER_SEARCH',
      buyerSearch: {
        summary: ['Đất ở', 'Hòa Xuân', 'Ngân sách tối đa: 2.500.000.000 đồng'],
        rows: [
          {
            key: 'LAND:DN-QH-0001',
            source: 'LAND_DATA',
            id: LAND_UUID,
            title: 'Ô quy hoạch Hòa Xuân',
            location: 'Hòa Xuân, Đà Nẵng',
            price: 2_600_000_000,
            area: 100,
            overBudgetVnd: 100_000_000,
            overBudgetPercent: 4,
            land: sampleLandRow(),
          },
          {
            key: 'PROPERTY:' + PROP_UUID,
            source: 'SMARTPROP',
            id: PROP_UUID,
            title: 'Đất nền Hòa Xuân',
            location: 'Hòa Xuân, Cẩm Lệ',
            price: 2_400_000_000,
            area: 95,
            overBudgetVnd: 0,
            overBudgetPercent: 0,
            property: {
              id: 'property:' + PROP_UUID,
              title: 'Đất nền Hòa Xuân',
              priceVnd: 2_400_000_000,
              areaSqm: 95,
              source: { kind: 'PROPERTY', recordKey: PROP_UUID, name: 'SmartProp' },
            },
          },
        ],
      },
    },
  };
  const viewBuyer = chatPresentation(buyerPacket);
  assert.equal(viewBuyer.summary, 'Hiển thị 2 kết quả.');
  assert.equal(viewBuyer.cards.length, 0, 'buyerSearch renders dedicated BuyerSearchResults, not duplicate property cards');

  // >15% overBudgetPercent must be rejected:
  const badBuyer = structuredClone(buyerPacket);
  badBuyer.evidence.buyerSearch.rows[0].overBudgetPercent = 15.01;
  assert.throws(() => publicChatResponse(badBuyer));
});

test('PR43 coordinate eligibility: estimated legacy pin enables nearby exploration without widening verified distance eligibility', () => {
  const legacyPin = {
    coordinate: {
      coordinateSource: 'UNKNOWN',
      accuracyLevel: 'UNKNOWN',
      verificationStatus: 'UNVERIFIED',
      geographicValidationStatus: 'VERIFIED_EXACT',
      referenceMapEligible: true,
      distanceAnalysisEligible: false,
      parcelAnalysisEligible: false,
    },
  };
  assert.equal(canShowReferenceMap(legacyPin), true);
  assert.equal(canExploreNearby(legacyPin), true);
  assert.equal(canAnalyzeDistance(legacyPin), false, 'estimated origin must NEVER widen verified distance eligibility');

  const rejectedPin = {
    coordinate: {
      coordinateSource: 'USER_PINNED',
      accuracyLevel: 'STREET',
      verificationStatus: 'REJECTED',
      geographicValidationStatus: 'VERIFIED_EXACT',
      referenceMapEligible: false,
      distanceAnalysisEligible: false,
      parcelAnalysisEligible: false,
    },
  };
  assert.equal(canShowReferenceMap(rejectedPin), false);
  assert.equal(canExploreNearby(rejectedPin), false);
  assert.equal(canAnalyzeDistance(rejectedPin), false);
});

test('PR43 chatProxy boundary: allows GET /api/chat/health and POST /api/chat while blocking unexpected subpaths', () => {
  let middleware;
  publicChatBoundary().configureServer({ middlewares: { use: fn => { middleware = fn; } } });
  const call = (method, url, authorization) => {
    let nextCalled = false;
    const headers = {};
    const res = {
      statusCode: 200,
      setHeader: (k, v) => { headers[k] = v; },
      end: body => { res.body = body; },
    };
    middleware({ method, url, headers: authorization ? { authorization } : {} }, res, () => { nextCalled = true; });
    return { nextCalled, statusCode: res.statusCode };
  };

  assert.deepEqual(call('GET', '/api/chat/health'), { nextCalled: true, statusCode: 200 });
  assert.deepEqual(call('POST', '/api/chat'), { nextCalled: true, statusCode: 200 });
  assert.deepEqual(call('POST', '/api/chat/research'), { nextCalled: false, statusCode: 404 });
  assert.deepEqual(call('GET', '/api/chat/health', 'Basic bad'), { nextCalled: false, statusCode: 401 });
});
