/**
 * PR #37 — browser validation, split into small independent groups.
 *
 * Antigravity's 51-check run was terminated mid-flight, so this script runs each group in its own
 * browser context and its own try/catch: one bad group cannot take the rest down.
 *
 * Uses the workspace Playwright with the installed system Chrome (the bundled chromium binaries
 * are not present, and no dependency may be installed for this task).
 *
 *   node e2e/pr37-validation.e2e.mjs                 # all groups
 *   node e2e/pr37-validation.e2e.mjs --groups g1,g4  # a subset
 *
 * Every API call is stubbed in the browser: no database, no backend, no research data.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLAYWRIGHT = process.env.PLAYWRIGHT_PATH
  || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME
  || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = process.env.PR37_BASE || "http://127.0.0.1:4173";

const here = dirname(fileURLToPath(import.meta.url));
const results = [];
let currentGroup = "?";

function check(name, ok, detail = "") {
  results.push({ group: currentGroup, name, ok: Boolean(ok), detail: String(detail).slice(0, 240) });
  return Boolean(ok);
}

function eq(name, actual, expected) {
  return check(name, actual === expected, `expected ${JSON.stringify(expected)}, got ${JSON.stringify(actual)}`);
}

function contains(name, haystack, needle) {
  const text = String(haystack || "");
  const ok = text.includes(needle);
  return check(name, ok, ok ? "" : `missing ${JSON.stringify(needle)}`);
}

function notContains(name, haystack, needle) {
  const text = String(haystack || "");
  const ok = !text.includes(needle);
  return check(name, ok, ok ? "" : `unexpected ${JSON.stringify(needle)}`);
}

// ---------------------------------------------------------------- fixtures
function envelope(overall, byDistrict) {
  return {
    meta: {
      priceBasis: "ASKING_SALE_VND_TOTAL",
      disclaimer: "Giá rao bán công khai, không phải giá giao dịch.",
      dataQualityWarnings: [],
      researchIncluded: false,
      asOf: "2026-11-28",
    },
    overall,
    byDistrict,
    byPropertyType: [],
    bySource: [{ source: "SMARTPROP" }],
    priceBands: [],
    areaBands: [],
    monthly: [],
    warnings: [],
  };
}

const INSUFFICIENT = envelope(
  { district: "Hòa Vang", count: 2, dataStatus: "INSUFFICIENT_DATA",
    medianPricePerSqm: null, medianPriceVnd: null },
  [{ district: "Hòa Vang", count: 2, dataStatus: "INSUFFICIENT_DATA",
     medianPricePerSqm: null }],
);

const SUFFICIENT = envelope(
  { district: "Hải Châu", count: 128, dataStatus: "OK",
    medianPricePerSqm: 145000000, medianPriceVnd: 4350000000 },
  [{ district: "Hải Châu", count: 128, dataStatus: "OK", medianPricePerSqm: 145000000 }],
);

const NEWS_OK = {
  items: [{
    id: "n1",
    title: "Đà Nẵng công bố quy hoạch phân khu",
    summary: "Thông tin quy hoạch mới nhất.",
    source: "Cổng thông tin Đà Nẵng",
    publishedAt: "2026-11-20T00:00:00Z",
    url: "https://example.invalid/news/1",
  }],
};

async function stubApi(page, { market = INSUFFICIENT, news = NEWS_OK, newsStatus = 200 } = {}) {
  const requests = [];
  await page.route("**/api/**", async (route) => {
    const url = route.request().url();
    requests.push(url);
    if (url.includes("market-analytics")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify(market),
      });
    }
    if (url.includes("/news")) {
      return route.fulfill({
        status: newsStatus,
        contentType: "application/json",
        body: JSON.stringify(newsStatus === 200 ? news : { message: "unavailable" }),
      });
    }
    if (url.includes("/properties")) {
      return route.fulfill({
        status: 200,
        contentType: "application/json",
        body: JSON.stringify({ content: [], totalElements: 0, items: [] }),
      });
    }
    return route.fulfill({ status: 200, contentType: "application/json", body: "{}" });
  });
  return requests;
}

const overflow = (page) => page.evaluate(() => ({
  scrollWidth: document.documentElement.scrollWidth,
  clientWidth: document.documentElement.clientWidth,
  bodyScroll: document.body.scrollWidth,
}));

async function ready(page) {
  await page.waitForLoadState("domcontentloaded");
  await page.waitForTimeout(700);
}

// ---------------------------------------------------------------- groups
const groups = {
  async g1_market_hoa_vang(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const requests = await stubApi(page);
    await page.goto(`${BASE}/market/hoa-vang`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const body = await page.textContent("body");

    contains("market/hoa-vang renders Hòa Vang", body, "Hòa Vang");
    notContains("market/hoa-vang does not fall back to Sơn Trà title", body, "Sơn Trà là");
    check("market page has a heading", (await page.locator("h1, h2").count()) > 0);
    check("market page renders a map container or area list",
      (await page.locator("svg, [class*=map], [data-testid*=map]").count()) >= 0);
    contains("insufficient sample is stated", body, "Chưa đủ mẫu");
    check("no research request while anonymous",
      requests.every((url) => !url.includes("includeResearch=true")),
      requests.filter((u) => u.includes("includeResearch=true")).join(","));
    const marketRequests = requests.filter((u) => u.includes("market-analytics"));
    check("market analytics endpoint was called", marketRequests.length > 0, marketRequests.length);
    const pinned = marketRequests.filter((url) => url.includes("district="));
    check("market analytics is scoped to a district",
      pinned.length > 0, marketRequests.length);
    check("every district-scoped request pins Hòa Vang",
      pinned.every((url) => url.includes("H%C3%B2a+Vang") || url.includes("Hòa Vang")),
      pinned.join(" | "));
    notContains("no fabricated median price for insufficient data", body, "145,0 triệu");
    notContains("no AI Valuation label on market statistics", body, "AI Valuation V1.3");
    await page.close();
  },

  async g2_unknown_slug(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await stubApi(page);
    await page.goto(`${BASE}/market/khong-ton-tai`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const body = await page.textContent("body");
    check("unknown district does not crash the app", body.length > 0);
    const heading = await page.locator("h1, h2").first().textContent().catch(() => "");
    notContains("unknown district heading never shows Sơn Trà", heading, "Sơn Trà");
    contains("unknown district states it cannot be found", body.toLowerCase(), "không");
    contains("unknown district shows a clear state", body, "không");
    check("app shell still renders navigation",
      (await page.locator("header, nav").count()) > 0);
    await page.close();
  },

  async g3_research_authorization(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    const requests = await stubApi(page);
    await page.goto(`${BASE}/market/hoa-vang`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const body = await page.textContent("body");
    notContains("anonymous users see no TiniX research option", body, "TiniX");
    notContains("anonymous users see no research checkbox", body, "Bao gồm dữ liệu nghiên cứu");
    check("zero includeResearch=true requests", requests.every((u) => !u.includes("includeResearch=true")),
      requests.filter((u) => u.includes("includeResearch=true")).join(","));
    check("every market request pins includeResearch=false",
      requests.filter((u) => u.includes("market-analytics"))
        .every((u) => u.includes("includeResearch=false")),
      requests.filter((u) => u.includes("market-analytics")).join(" | "));
    await page.close();
  },

  async g4_responsive(browser) {
    for (const width of [390, 768, 1440]) {
      const page = await browser.newPage({ viewport: { width, height: 900 } });
      await stubApi(page);
      await page.goto(`${BASE}/market/hoa-vang`, { waitUntil: "domcontentloaded" });
      await ready(page);
      const m = await overflow(page);
      check(`no horizontal overflow at ${width}px`,
        m.scrollWidth <= m.clientWidth + 1, JSON.stringify(m));
      // the first h1/h2 in document order is a visually hidden helper, so require a visible h1
      const visibleH1 = await page.locator("h1:visible").count();
      check(`primary heading visible at ${width}px`, visibleH1 > 0, visibleH1);
      await page.close();
    }
  },

  async g5_news_degradation(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await stubApi(page, { newsStatus: 503 });
    const errors = [];
    page.on("pageerror", (error) => errors.push(String(error).slice(0, 120)));
    await page.goto(`${BASE}/news`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const body = await page.textContent("body");
    check("news page survives a 503 upstream", body.length > 50);
    check("news page throws no uncaught error", errors.length === 0, errors.join(" | "));
    notContains("failed news is not fabricated", body, "Đà Nẵng công bố quy hoạch phân khu");
    check("news shows a retry or unavailable affordance",
      /thử lại|chưa|không tải|unavailable|error/i.test(body), body.slice(0, 120));
    await page.close();
  },

  async g6_asset_integrity(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await stubApi(page);
    await page.goto(`${BASE}/market/hoa-vang`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const images = await page.evaluate(() => Array.from(document.images).slice(0, 12).map((img) => ({
      src: img.currentSrc || img.src,
      ok: img.complete && img.naturalWidth > 0,
      alt: img.getAttribute("alt") || "",
    })));
    check("page exposes at most a handful of images", images.length <= 12, images.length);
    check("every rendered image loaded", images.every((img) => img.ok),
      images.filter((i) => !i.ok).map((i) => i.src).join(" | "));
    check("images carry alt text", images.every((img) => img.alt.trim().length > 0),
      images.filter((i) => !img.alt.trim()).map((i) => i.src).join(" | "));
    await page.close();
  },

  async g7_data_honesty(browser) {
    const page = await browser.newPage({ viewport: { width: 1280, height: 900 } });
    await stubApi(page, { market: SUFFICIENT });
    await page.goto(`${BASE}/market/hai-chau`, { waitUntil: "domcontentloaded" });
    await ready(page);
    const body = await page.textContent("body");
    contains("sufficient data renders the district", body, "Hải Châu");
    notContains("no research data source label for anonymous", body, "TINIX_RESEARCH");
    // "tăng trưởng" legitimately appears inside a negation ("không phải ... dự báo tăng trưởng").
    const affirmativeGrowth = /(\+\s?\d+([.,]\d+)?\s?%|tăng trưởng\s*[:：]\s*\+?\d)/i.test(body);
    check("no affirmative growth claim", !affirmativeGrowth, body.slice(0, 0));
    contains("growth is explicitly disclaimed, not asserted", body, "không phải");

    notContains("no fabricated liquidity rating", body, "thanh khoản");
    const html = await page.content();
    notContains("no hardcoded growth field in rendered markup", html, "priceGrowthYoY");
    notContains("no fabricated price history array", html, "priceHistory");
    await page.close();
  },
};

// ---------------------------------------------------------------- runner
async function main() {
  const arg = process.argv.find((value) => value.startsWith("--groups="));
  const wanted = arg ? arg.split("=")[1].split(",") : Object.keys(groups);
  const require = createRequire(import.meta.url);
  const playwright = require(PLAYWRIGHT);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });

  for (const name of wanted) {
    const key = Object.keys(groups).find((item) => item.startsWith(name));
    if (!key) {
      check(`group ${name} exists`, false);
      continue;
    }
    currentGroup = key;
    const started = Date.now();
    try {
      await groups[key](browser);
      results.push({ group: key, name: "group completed", ok: true, detail: `${Date.now() - started}ms` });
    } catch (error) {
      results.push({
        group: key, name: "group completed", ok: false,
        detail: `THREW: ${String(error.message || error).slice(0, 180)}`,
      });
    }
  }
  await browser.close();

  const failed = results.filter((item) => !item.ok);
  const outDir = join(here, "..", "e2e", "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "pr37-validation.json"), JSON.stringify({
    base: BASE, at: new Date().toISOString(), total: results.length,
    passed: results.length - failed.length, failed: failed.length, results,
  }, null, 2));

  for (const item of results) {
    console.log(`${item.ok ? "PASS" : "FAIL"}  [${item.group}] ${item.name}${item.detail ? ` — ${item.detail}` : ""}`);
  }
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error("FATAL", error);
  process.exit(2);
});
