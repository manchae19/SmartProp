/**
 * PR #43 Reproducible Browser E2E Suite
 *
 * Execution mode: BROWSER_WITH_MOCKED_HTTP (real Vite dev server + real headless Chromium CDP,
 * backed by a deterministic in-process local HTTP upstream; no external network, no MySQL writes,
 * and explicitly distinct from full-stack live-DB/Ollama runtime validation).
 *
 * Run from `frontend/`:
 *   node tests/browser/pr43-land-e2e.mjs
 * Optional env:
 *   WP02_CHROMIUM / CHROMIUM_BIN  Path to Chromium/Chrome/Edge executable (auto-detected if omitted)
 *   ARTIFACT_DIR                  Directory to write optional PNG screenshots
 */
import assert from 'node:assert/strict';
import { spawn } from 'node:child_process';
import { once } from 'node:events';
import { existsSync, mkdtempSync, readdirSync, readFileSync, rmSync, writeFileSync } from 'node:fs';
import http from 'node:http';
import { tmpdir } from 'node:os';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const frontendRoot = path.resolve(__dirname, '../..');

function resolveBrowserBinary() {
  const explicit = process.env.WP02_CHROMIUM || process.env.CHROMIUM_BIN;
  if (explicit && existsSync(explicit)) return explicit;
  const localAppData = process.env.LOCALAPPDATA;
  if (localAppData) {
    const pwDir = path.join(localAppData, 'ms-playwright');
    if (existsSync(pwDir)) {
      for (const entry of readdirSync(pwDir).sort().reverse()) {
        if (!entry.startsWith('chromium-')) continue;
        const candidate = path.join(pwDir, entry, 'chrome-win64', 'chrome.exe');
        if (existsSync(candidate)) return candidate;
      }
    }
  }
  const fallbacks = [
    'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
    'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
    '/usr/bin/chromium',
    '/usr/bin/chromium-browser',
    '/usr/bin/google-chrome',
  ];
  for (const candidate of fallbacks) {
    if (existsSync(candidate)) return candidate;
  }
  throw new Error('No Chromium/Chrome/Edge binary found. Set WP02_CHROMIUM or CHROMIUM_BIN.');
}

const chromium = resolveBrowserBinary();
const artifactDir = process.env.ARTIFACT_DIR || '';
const { createServer: createViteServer } = await import(
  pathToFileURL(path.join(frontendRoot, 'node_modules/vite/dist/node/index.js')).href
);

const LAND_ID = '11111111-2222-3333-4444-555555555555';
const PROP_ID = 'aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee';
const SESSION_ID = 'a1b2c3d4e5f60718293a4b5c6d7e8f90';
const DEMO_KEY = 'pr43-local-mentor-demo-fixture-key';
const wait = ms => new Promise(r => setTimeout(r, ms));

const landRecord = {
  landId: LAND_ID,
  sourceCode: 'DN-QH-0001',
  kind: 'PLANNING_CELL',
  dataVersion: 'HX-LAND-DEMO-20261126',
  demoOnly: true,
  governance: {
    containsSyntheticData: true,
    publicApproved: false,
    officialCadastralParcel: false,
    marketOrTransactionValue: false,
    excludedFrom: ['VALUATION', 'COMPARABLE', 'MARKET'],
  },
  displayName: 'Ô quy hoạch Hòa Xuân B2.12',
  location: 'Hòa Xuân, Cẩm Lệ, Đà Nẵng',
  located: true,
  pointOnSurface: [108.215, 16.005],
  cadastral: {
    areaSqm: 105,
    areaBasis: 'COMPUTED_FROM_PLANNING_CELL',
    planningCellId: 'DN-QH-0001',
    plans: [{ id: 'QH-HX-01', name: 'Phân khu Hòa Xuân' }],
    geometryBasis: 'SOURCE_PLANNING_CELL_NOT_CADASTRAL',
  },
  price: {
    display: '2,50 tỷ (giá giả lập demo — không phải giá thị trường)',
    evidence: [
      {
        type: 'SIMULATED_DEMO',
        label: 'Giá giả lập demo (không phải giá thị trường hay giá giao dịch)',
        valueVnd: 2500000000,
        unitPriceVndPerSqm: 23809524,
        date: null,
        sources: [],
      },
    ],
  },
  documents: {
    demo: true,
    landType: 'Nhóm quy hoạch tham khảo: đất ở (giả định demo, chưa xác minh địa chính)',
    ownershipDocument: 'Giả định kịch bản demo (sổ đỏ) — chưa có giấy chứng nhận thực tế được xác minh',
    recovery: 'Chưa xác minh quy hoạch thu hồi/giải tỏa (giả định kịch bản demo — không xác nhận không vướng quy hoạch)',
    dispute: 'Chưa xác minh',
    mortgage: 'Chưa xác minh',
    compensation: 'Chưa xác minh',
    basis: 'USER_APPROVED_DEMO_SCENARIO',
    verifiedForThisParcel: false,
    sourceLegalStatus: 'UNKNOWN',
  },
  planning: {
    sourceLabel: 'Đất ở đô thị',
    code: 'ODT',
    text: 'Quy hoạch phân khu Hòa Xuân (tham khảo)',
    plans: [{ id: 'QH-HX-01', name: 'Phân khu Hòa Xuân' }],
  },
  flood: {
    display: 'Chưa có bản ghi ngập trùng tuyến đường nguồn (giả định kịch bản demo — không xác nhận an toàn ngập)',
    relation: 'USER_APPROVED_DEMO_SCENARIO',
    detail: 'Đối chiếu danh mục tuyến đường ngập nguồn Đà Nẵng; chưa xác minh an toàn ngập của riêng ô.',
    isDemoAssumption: true,
    verifiedForThisParcel: false,
    records: [{ id: 'FL-01', location_text: 'Đường 29 Tháng 3', publication_date: '2025', source_title: 'Sở Xây dựng Đà Nẵng' }],
  },
  environment: {},
  sources: ['https://danang.gov.vn/quy-hoach'],
};

const landChatRow = {
  id: 'DN-QH-0001',
  landId: LAND_ID,
  sourceCode: 'DN-QH-0001',
  displayName: 'Ô quy hoạch Hòa Xuân B2.12',
  displayNumber: 1,
  computedAreaSqm: 105,
  priceDescription: '2,50 tỷ (giá giả lập demo — không phải giá thị trường)',
  purposeGroup: 'housing',
  planningLabel: 'Đất ở đô thị',
  planningCode: 'ODT',
  pointOnSurface: [108.215, 16.005],
  demoPriceVnd: 2500000000,
  kind: 'PLANNING_CELL',
  location: 'Hòa Xuân, Cẩm Lệ, Đà Nẵng',
  priceType: 'SIMULATED_DEMO',
  located: true,
  demo: {
    landType: landRecord.documents.landType,
    ownershipDocument: landRecord.documents.ownershipDocument,
    recovery: landRecord.documents.recovery,
    dispute: 'Chưa xác minh',
    compensation: 'Chưa xác minh',
  },
  flood: {
    display: landRecord.flood.display,
    relation: 'USER_APPROVED_DEMO_SCENARIO',
    isDemoAssumption: true,
  },
};

const recordedRequests = [];
let sessionCanceled = false;

const upstream = http.createServer(async (req, res) => {
  const url = new URL(req.url, 'http://127.0.0.1');
  const sendJson = (code, body) => {
    res.writeHead(code, { 'Content-Type': 'application/json; charset=utf-8', 'Cache-Control': 'no-store' });
    res.end(JSON.stringify(body));
  };

  if (url.pathname === '/chat/health') {
    recordedRequests.push({ method: req.method, path: url.pathname });
    return sendJson(200, { status: 'ok' });
  }

  if (url.pathname === '/chat' && req.method === 'POST') {
    const chunks = [];
    for await (const c of req) chunks.push(c);
    const body = JSON.parse(Buffer.concat(chunks).toString('utf8') || '{}');
    recordedRequests.push({ method: 'POST', path: '/chat', body });
    const q = (body.question || '').trim().toLowerCase();

    if (q.includes('không muốn tìm mua nữa') || q.includes('dừng tìm mua')) {
      sessionCanceled = true;
      return sendJson(200, {
        answer: 'Tôi đã dừng tìm tin mua. Bạn có thể yêu cầu tìm lại khi cần.',
        mode: 'SAFE',
        generationMode: 'EVIDENCE_ONLY',
        retrievalMode: 'TOOL_EVIDENCE_ONLY',
        citations: [],
        recommendedProperties: [],
        dataLimitations: [],
        evidence: {
          responseKind: 'CLARIFICATION_REQUIRED',
          clarification: 'PURCHASE_DECLINED',
          session: { id: SESSION_ID, turn: 2, context: { criteria: { budgetVnd: '3000000000', purpose: 'LIVING' } } },
        },
      });
    }

    if (sessionCanceled && (q === 'xem kết quả khác' || q === 'xem thêm' || q === 'đất ở' || q === 'hòa xuân' || q === '2,5 tỷ')) {
      return sendJson(200, {
        answer: 'Phiên này không có bước xác nhận phù hợp. Bạn có thể nêu yêu cầu mới.',
        mode: 'SAFE',
        generationMode: 'EVIDENCE_ONLY',
        retrievalMode: 'TOOL_EVIDENCE_ONLY',
        citations: [],
        recommendedProperties: [],
        dataLimitations: [],
        evidence: {
          responseKind: 'CLARIFICATION_REQUIRED',
          clarification: 'NO_PENDING_LISTING_STEP',
          session: { id: SESSION_ID, turn: 3, context: { criteria: { budgetVnd: '3000000000', purpose: 'LIVING' } } },
        },
      });
    }

    sessionCanceled = false;
    return sendJson(200, {
      answer: 'Hiển thị 2 kết quả, giá tăng dần. Kết quả trong ngân sách được hiển thị trước; giá và nguồn được ghi trên từng thẻ.',
      mode: 'SAFE',
      generationMode: 'EVIDENCE_ONLY',
      retrievalMode: 'TOOL_EVIDENCE_ONLY',
      citations: [
        {
          sourceId: 'property:' + PROP_ID,
          url: '/api/v1/properties/' + PROP_ID,
          version: '1',
          contentHash: 'a'.repeat(64),
          scope: 'PUBLIC',
          kind: 'PROPERTY_DETAIL',
          title: 'Đất nền Hòa Xuân đường 7m5',
        },
      ],
      recommendedProperties: [],
      dataLimitations: [
        'Bản demo Hòa Xuân: dữ liệu trình diễn giả lập; không phải xác nhận pháp lý hay giá thị trường.',
      ],
      evidence: {
        responseKind: 'BUYER_SEARCH',
        session: { id: SESSION_ID, turn: 1, context: { criteria: { budgetVnd: '3000000000', purpose: 'LIVING' } } },
        quickReplies: ['Xem kết quả khác'],
        buyerSearch: {
          summary: ['Đất ở', 'Hòa Xuân', 'Ngân sách tối đa: 3.000.000.000 đồng'],
          rows: [
            {
              key: 'PROPERTY:' + PROP_ID,
              source: 'SMARTPROP',
              id: PROP_ID,
              title: 'Đất nền Hòa Xuân đường 7m5',
              location: 'Hòa Xuân, Cẩm Lệ',
              price: 2400000000,
              area: 100,
              overBudgetVnd: 0,
              overBudgetPercent: 0,
              property: {
                id: 'property:' + PROP_ID,
                title: 'Đất nền Hòa Xuân đường 7m5',
                priceVnd: 2400000000,
                areaSqm: 100,
                source: { kind: 'PROPERTY', recordKey: PROP_ID, name: 'SmartProp' },
              },
            },
            {
              key: 'LAND:DN-QH-0001',
              source: 'LAND_DATA',
              id: LAND_ID,
              title: 'Ô quy hoạch Hòa Xuân B2.12',
              location: 'Hòa Xuân, Cẩm Lệ, Đà Nẵng',
              price: 2500000000,
              area: 105,
              overBudgetVnd: 0,
              overBudgetPercent: 0,
              land: landChatRow,
            },
          ],
        },
      },
    });
  }

  recordedRequests.push({ method: req.method, path: url.pathname, search: url.search });

  if (url.pathname.startsWith('/land/')) {
    if (req.headers['x-smartprop-demo-key'] !== DEMO_KEY) {
      return sendJson(403, { detail: 'Hồ sơ đất demo chỉ dành cho môi trường trình diễn nội bộ được cấp phép trên loopback.' });
    }
  }
  if (url.pathname === `/land/records/${LAND_ID}` || url.pathname === '/land/records/DN-QH-0001') {
    return sendJson(200, landRecord);
  }
  if (url.pathname === `/land/records/${LAND_ID}/overview`) {
    return sendJson(200, {
      landId: LAND_ID,
      sourceCode: 'DN-QH-0001',
      dataVersion: 'HX-LAND-DEMO-20261126',
      templateVersion: 'LAND_OVERVIEW_V1',
      text: 'Hồ sơ đặt tại Hòa Xuân, Cẩm Lệ, Đà Nẵng. Diện tích 105 m², tính từ đường bao ô quy hoạch. Đây là ô quy hoạch, chưa xác nhận thửa địa chính hay lô bán riêng. Thuộc tính giả lập chỉ dùng trình diễn, không phải xác nhận thực tế.',
      wordCount: 47,
      generationMode: 'TEMPLATE',
      cached: false,
    });
  }
  if (url.pathname.startsWith('/land/records/')) {
    return sendJson(404, { detail: 'Không tìm thấy hồ sơ đất.' });
  }
  if (url.pathname === '/land/neighbors') {
    return sendJson(200, {
      type: 'FeatureCollection',
      features: [
        {
          type: 'Feature',
          geometry: {
            type: 'Polygon',
            coordinates: [[[108.214, 16.004], [108.216, 16.004], [108.216, 16.006], [108.214, 16.006], [108.214, 16.004]]],
          },
          properties: {
            id: 'DN-QH-0001',
            landId: LAND_ID,
            displayName: 'Ô quy hoạch Hòa Xuân B2.12',
            planningCode: 'ODT',
            planningCategory: 'RESIDENTIAL_PLANNING',
            selected: true,
            color: '#c7a000',
            floodDisplay: { recordIds: ['FL-01'] },
          },
        },
      ],
    });
  }
  if (url.pathname === '/land/planning-cells' || url.pathname === '/land/flood-map') {
    return sendJson(200, { type: 'FeatureCollection', features: [] });
  }
  if (url.pathname === '/api/v1/auth/refresh') {
    return sendJson(401, { code: 'UNAUTHENTICATED', message: 'No session' });
  }
  if (url.pathname === `/api/v1/properties/${PROP_ID}`) {
    return sendJson(200, {
      id: PROP_ID,
      listingCode: 'SP-HX-01',
      title: 'Đất nền Hòa Xuân gần cầu Hòa Xuân',
      description: 'Đất nền đường 7.5m khu Hòa Xuân.',
      propertyType: 'LAND',
      transactionType: 'SALE',
      price: 2400000000,
      currency: 'VND',
      priceUnit: 'TOTAL',
      areaSqm: 100,
      city: 'Đà Nẵng',
      district: 'Cẩm Lệ',
      ward: 'Hòa Xuân',
      address: 'Khu đô thị Hòa Xuân, Cẩm Lệ',
      latitude: 16.005,
      longitude: 108.215,
      status: 'PUBLISHED',
      contentVersion: 1,
      images: [],
      declaredAmenities: [],
      coordinate: {
        coordinateSource: 'UNKNOWN',
        accuracyLevel: 'UNKNOWN',
        verificationStatus: 'UNVERIFIED',
        geographicValidationStatus: 'VERIFIED_EXACT',
        referenceMapEligible: true,
        distanceAnalysisEligible: false,
        parcelAnalysisEligible: false,
      },
    });
  }
  if (url.pathname === `/api/v1/properties/${PROP_ID}/pois`) {
    return sendJson(200, [
      { id: 'poi-1', name: 'Trường Tiểu học Hòa Xuân', category: 'SCHOOL', distanceMeters: 420 },
      { id: 'poi-2', name: 'Siêu thị WinMart+', category: 'SUPERMARKET', distanceMeters: 610 },
    ]);
  }
  if (url.pathname === `/api/v1/properties/${PROP_ID}/nearby`) {
    return sendJson(200, {
      propertyId: PROP_ID,
      location: { latitude: 16.005, longitude: 108.215, accuracy: 'UNKNOWN' },
      radiusMeters: Number(url.searchParams.get('radius') || 1000),
      categories: (url.searchParams.get('categories') || 'education').split(','),
      distanceType: 'STRAIGHT_LINE',
      items: [
        {
          id: 'geoapify:1',
          name: 'Trường Tiểu học Hòa Xuân',
          categoryGroups: ['education'],
          category: 'education',
          latitude: 16.008,
          longitude: 108.216,
          distanceMeters: 420,
          provider: 'GEOAPIFY',
        },
      ],
      fetchedAt: new Date().toISOString(),
      cacheHit: false,
      truncated: false,
      coverage: 'PARTIAL',
      status: 'OK',
      attribution: [{ label: '© OpenStreetMap contributors', url: 'https://www.openstreetmap.org/copyright' }],
    });
  }
  if (url.pathname === '/api/v1/comparables') {
    return sendJson(200, {
      purpose: 'SIMILAR_LISTING',
      mode: 'SAFE',
      cohortStatus: 'SUFFICIENT',
      confidence: 'MEDIUM',
      subject: { district: 'Cẩm Lệ', ward: 'Hòa Xuân', propertyType: 'LAND', areaSqm: 100 },
      items: [],
      summary: { count: 0 },
      warnings: [],
    });
  }
  if (url.pathname.startsWith('/api/v1/image-analysis')) {
    return sendJson(200, { propertyId: PROP_ID, items: [], summary: null });
  }
  return sendJson(404, { code: 'NOT_FOUND', message: 'Not found: ' + url.pathname });
});

console.log('BROWSER_EVIDENCE_MODE=MOCKED_HTTP_VITE_BROWSER_E2E (not full-stack live-DB/Ollama runtime)');

upstream.listen(0, '127.0.0.1');
await once(upstream, 'listening');
const upstreamPort = upstream.address().port;

process.env.SMARTPROP_DEV_API_TARGET = `http://127.0.0.1:${upstreamPort}`;
process.env.SMARTPROP_DEV_CHAT_TARGET = `http://127.0.0.1:${upstreamPort}`;
process.env.SMARTPROP_DEV_AI_TARGET = `http://127.0.0.1:${upstreamPort}`;
process.env.SMARTPROP_DEV_VISION_TARGET = `http://127.0.0.1:${upstreamPort}`;

// Verify unconfigured public boundary blocks /api/land/* with 403 before starting authorized mentor demo Vite:
delete process.env.SMARTPROP_INTERNAL_DEMO_KEY;
delete process.env.RAG_DEMO_KEY;
const publicVite = await createViteServer({
  root: frontendRoot,
  server: { host: '127.0.0.1', port: 0, strictPort: false },
});
await publicVite.listen();
try {
  const publicPort = publicVite.httpServer.address().port;
  const blockedLand = await fetch(`http://127.0.0.1:${publicPort}/api/land/records/${LAND_ID}`);
  assert.equal(blockedLand.status, 403, 'Public Vite boundary without SMARTPROP_INTERNAL_DEMO_KEY must block /api/land/* with 403');
  console.log('PASS 0: Unconfigured public proxy boundary blocks /api/land/* with 403');
} finally {
  await publicVite.close();
}

process.env.SMARTPROP_INTERNAL_DEMO_KEY = DEMO_KEY;
const vite = await createViteServer({
  root: frontendRoot,
  server: { host: '127.0.0.1', port: 0, strictPort: false },
});
await vite.listen();
const vitePort = vite.httpServer.address().port;
const origin = `http://127.0.0.1:${vitePort}`;

const profile = mkdtempSync(path.join(path.resolve(tmpdir()), 'smartprop-pr43-e2e-'));
const chrome = spawn(
  chromium,
  [
    '--headless=new',
    '--disable-gpu',
    '--disable-extensions',
    '--disable-background-networking',
    '--no-first-run',
    '--remote-debugging-port=0',
    '--remote-debugging-address=127.0.0.1',
    '--no-proxy-server',
    '--host-resolver-rules=MAP * ~NOTFOUND, EXCLUDE localhost, EXCLUDE 127.0.0.1',
    '--user-data-dir=' + profile,
    'about:blank',
  ],
  { stdio: ['ignore', 'ignore', 'pipe'], windowsHide: true }
);
let chromeStderr = '';
chrome.stderr.on('data', d => { chromeStderr += d.toString(); });

const exceptions = [];
const consoleErrors = [];
let ws;
let seq = 0;
const pending = new Map();

try {
  let devPort;
  const portFile = path.join(profile, 'DevToolsActivePort');
  for (let i = 0; i < 100 && !devPort; i++) {
    try {
      devPort = Number(readFileSync(portFile, 'utf8').split(/\r?\n/)[0]);
    } catch {}
    if (!devPort) await wait(100);
  }
  assert.ok(devPort, 'Chromium DevTools failed to start: ' + chromeStderr);
  const tabs = await fetch(`http://127.0.0.1:${devPort}/json/list`).then(r => r.json());
  ws = new WebSocket(tabs.find(t => t.type === 'page').webSocketDebuggerUrl);
  await once(ws, 'open');

  ws.onmessage = ev => {
    const msg = JSON.parse(ev.data);
    if (msg.method === 'Runtime.exceptionThrown') {
      exceptions.push(msg.params.exceptionDetails);
    }
    if (msg.method === 'Runtime.consoleAPICalled' && msg.params.type === 'error') {
      const rendered = (msg.params.args || []).map(a => a.value ?? a.description ?? '').join(' ');
      if (!rendered.includes('tile.openstreetmap.org')) consoleErrors.push(rendered);
    }
    if (!msg.id) return;
    const p = pending.get(msg.id);
    pending.delete(msg.id);
    if (msg.error) p.reject(Error(JSON.stringify(msg.error)));
    else p.resolve(msg.result);
  };

  const send = (method, params = {}) =>
    new Promise((resolve, reject) => {
      const id = ++seq;
      pending.set(id, { resolve, reject });
      ws.send(JSON.stringify({ id, method, params }));
    });

  const ev = async expression => {
    const res = await send('Runtime.evaluate', { expression, awaitPromise: true, returnByValue: true });
    if (res.exceptionDetails) throw Error(JSON.stringify(res.exceptionDetails));
    return res.result.value;
  };

  const until = async (expr, label, maxIter = 120) => {
    for (let i = 0; i < maxIter; i++) {
      if (await ev(expr)) return;
      await wait(75);
    }
    const text = await ev('document.body?.innerText || ""');
    throw Error(`Timeout waiting for ${label}\nBody:\n${text.slice(0, 1500)}`);
  };

  const setViewport = (width, height, mobile = false) =>
    send('Emulation.setDeviceMetricsOverride', { width, height, deviceScaleFactor: 1, mobile });

  const screenshot = async name => {
    if (!artifactDir) return;
    const shot = await send('Page.captureScreenshot', { format: 'png' });
    writeFileSync(path.join(artifactDir, name), Buffer.from(shot.data, 'base64'));
  };

  const assertZeroOverflow = async label => {
    for (const [w, h] of [[1440, 900], [768, 1024], [390, 844]]) {
      await setViewport(w, h, w < 768);
      await wait(120);
      const overflow = await ev('document.documentElement.scrollWidth - window.innerWidth');
      assert.ok(overflow <= 2, `${label} horizontal overflow at ${w}px: ${overflow}`);
    }
    await setViewport(1440, 900, false);
  };

  await send('Page.enable');
  await send('Runtime.enable');
  await send('Network.enable');
  await send('Network.setBlockedURLs', { urls: ['https://*'] });

  // 1. /land/:id detail view + visible governance notice + explicit synthetic provenance + responsive 1440/768/390
  await setViewport(1440, 900);
  await send('Page.navigate', { url: `${origin}/land/${LAND_ID}` });
  await until('document.body.innerText.includes("Ô quy hoạch Hòa Xuân B2.12")', 'LandDetailView title');
  await until('document.body.innerText.includes("Tổng quan hồ sơ")', 'LandDetailView overview');
  await until('Boolean(document.querySelector("[data-land-governance-notice]"))', 'LandDetailView governance banner');
  const detailText = await ev('document.body.innerText');
  assert.ok(detailText.includes('không phải thửa địa chính chính thức'), 'Must state planning cell is not official cadastral parcel');
  assert.ok(detailText.includes('không phải giá thị trường'), 'Must state demo price is not market value');
  assert.ok(detailText.includes('chưa có giấy chứng nhận thực tế'), 'Must state no verified certificate');
  assert.ok(detailText.includes('không xác nhận an toàn ngập'), 'Must state parcel is not verified flood-safe');
  assert.ok(!detailText.includes('Được cấp sổ'), 'Must never claim an existing certificate without source');
  assert.ok(!detailText.includes('Không ngập úng'), 'Must never claim parcel is flood-safe without source');
  assert.ok(recordedRequests.some(r => r.path === `/land/records/${LAND_ID}`), 'Expected GET /land/records/:id');
  assert.ok(recordedRequests.some(r => r.path === `/land/records/${LAND_ID}/overview`), 'Expected GET /land/records/:id/overview');
  await screenshot('pr43-land-detail-desktop-1440.png');
  await assertZeroOverflow('LandDetailView');
  console.log('PASS 1: /land/:id governance banner, synthetic disclaimers, request verification, and 1440/768/390 layout');

  // 2. /land/non-existent-record graceful 404 fallback
  await send('Page.navigate', { url: `${origin}/land/non-existent-record` });
  await until('document.body.innerText.includes("Chưa mở được hồ sơ")', 'Missing land 404 heading');
  await until('document.body.innerText.includes("Không tìm thấy hồ sơ đất.")', 'Missing land 404 message');
  assert.equal(await ev('window.location.pathname'), '/land/non-existent-record');
  console.log('PASS 2: /land/non-existent-record graceful 404 UI');

  // 3. /advisor/chat multi-turn: hard-budget BUYER_SEARCH -> PURCHASE_DECLINED -> stale "Xem kết quả khác" rejected
  await send('Page.navigate', { url: `${origin}/advisor/chat` });
  await until('Boolean(document.querySelector("textarea"))', 'ChatAdvisorView textarea');

  const submitChat = text =>
    ev(`(() => {
      const ta = document.querySelector('textarea');
      Object.getOwnPropertyDescriptor(HTMLTextAreaElement.prototype, 'value').set.call(ta, ${JSON.stringify(text)});
      ta.dispatchEvent(new Event('input', { bubbles: true }));
      ta.form.requestSubmit();
    })()`);

  await submitChat('Tìm đất ở Hòa Xuân dưới 3 tỷ');
  await until('document.body.innerText.includes("Tin đăng SmartProp")', 'BUYER_SEARCH SmartProp card');
  await until('document.body.innerText.includes("demo giả lập · không phải thửa địa chính chính thức")', 'BUYER_SEARCH synthetic land label');
  const turn1ChatText = await ev('document.body.innerText');
  assert.ok(!turn1ChatText.includes('Tham khảo vượt ngân sách'), 'Hard budget must not auto-expand +15%');
  const turn1ChatReq = recordedRequests.findLast(r => r.path === '/chat');
  assert.equal(turn1ChatReq.body.question, 'Tìm đất ở Hòa Xuân dưới 3 tỷ');
  await screenshot('pr43-chat-land-desktop-1440.png');

  await submitChat('Tôi không muốn tìm mua nữa');
  await until('document.body.innerText.includes("Tôi đã dừng tìm tin mua")', 'PURCHASE_DECLINED reply');
  const turn2ChatReq = recordedRequests.findLast(r => r.path === '/chat');
  assert.equal(turn2ChatReq.body.sessionId, SESSION_ID, 'Turn 2 must carry opaque sessionId');
  const oldPageButtonDisabled = await ev('Boolean(document.querySelector(".land-pagination button")?.disabled)');
  assert.equal(oldPageButtonDisabled, true, 'Historical pagination button must be disabled after new turn');

  await submitChat('Xem kết quả khác');
  await until('document.body.innerText.includes("Phiên này không có bước xác nhận phù hợp")', 'Stale action rejected');
  const latestAnswerCardCount = await ev(`(() => {
    const answers = [...document.querySelectorAll('[data-chat-answer]')];
    const last = answers.at(-1);
    return last ? last.querySelectorAll('.land-card, [data-chat-property]').length : -1;
  })()`);
  assert.equal(latestAnswerCardCount, 0, 'Zero property or land cards may render after stale action post-cancellation');
  await assertZeroOverflow('ChatAdvisorView');
  console.log('PASS 3: /advisor/chat hard-budget cards, PURCHASE_DECLINED retirement, stale action 0-card rejection, and 1440/768/390 layout');

  // 4. /listing/:id PR43 nearby POIs + estimated-origin notice + PR47 ComparableEvidenceLookup guest RBAC
  await send('Page.navigate', { url: `${origin}/listing/${PROP_ID}` });
  await until('document.body.innerText.includes("Đất nền Hòa Xuân gần cầu Hòa Xuân")', 'ListingDetailView title');
  await until('document.body.innerText.includes("Trường Tiểu học Hòa Xuân")', 'ListingDetailView POI row');
  await until('document.body.innerText.includes("Khoảng cách ước tính từ ghim tin đăng")', 'Estimated-origin map notice');
  await until('document.body.innerText.includes("Đối chiếu tin đăng dành cho tài khoản môi giới hoặc quản trị viên")', 'PR47 ComparableEvidenceLookup guest RBAC');
  await screenshot('pr43-listing-detail-pois-desktop-1440.png');
  await assertZeroOverflow('ListingDetailView');
  console.log('PASS 4: /listing/:id PR43 nearby POIs + estimated-origin notice + PR47 comparables + 1440/768/390 layout');

  // 5. /auth/google/link/complete PR48 route preservation check
  await send('Page.navigate', { url: `${origin}/auth/google/link/complete?status=invalid_state` });
  await until('document.body.innerText.length > 20', 'GoogleLinkCompleteView rendered');
  assert.equal(await ev('window.location.pathname'), '/auth/google/link/complete');
  console.log('PASS 5: /auth/google/link/complete PR48 Google Account Linking route preserved');

  assert.equal(exceptions.length, 0, 'Uncaught browser exceptions: ' + JSON.stringify(exceptions));
  assert.equal(consoleErrors.length, 0, 'Console errors: ' + JSON.stringify(consoleErrors));
  console.log('PR43_REPRODUCIBLE_BROWSER_EVIDENCE_PASS');
} finally {
  try { ws?.close(); } catch {}
  chrome.kill();
  await vite.close();
  await new Promise(r => upstream.close(r));
  try { rmSync(profile, { recursive: true, force: true }); } catch {}
}
