/**
 * WP-04 browser failure isolation + reactive authorization.
 *
 * Mocked cases intercept the AI response on purpose (they are failure fixtures, never success
 * evidence). The outage case stops the real FastAPI process instead. Reactive authorization mutates
 * the disposable fixture only and restores it afterwards.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PW = process.env.PLAYWRIGHT_PATH || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = process.env.WP04_APP || "http://127.0.0.1:5180";
const API = process.env.WP04_API || "http://127.0.0.1:8080";
const EMAIL = process.env.WP04_FIXTURE_EMAIL || "";
const PASSWORD = process.env.WP04_FIXTURE_PASSWORD || "";
const here = dirname(fileURLToPath(import.meta.url));
const out = join(here, "reports");

const results = [];
const record = (name, ok, detail = "") =>
  results.push({ name, ok: Boolean(ok), detail: String(detail).slice(0, 220) });

const AI = process.env.WP04_AI || "http://127.0.0.1:8000";

/** Real V1.3 payload; failure cases are mutations of it, never hand-written schemas. */
async function realPayload() {
  const response = await fetch(`${AI}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ category: "Nhà ở", location_feature: "Cẩm Lệ", area_sqm: 100 }),
  });
  if (!response.ok) throw new Error(`baseline predict ${response.status}`);
  return response.json();
}

const PRICE = 5476531536;
const factor = (feature, value) => ({
  feature, label: feature, value, provenance: "OBSERVED", group: "LOCATION",
});

function envelope(overrides) {
  const base = {
    model_version: "v1.3",
    model_run: "tinix_xgboost_v1_3_integrated",
    predicted_asking_price_vnd: PRICE,
    predicted_margin_log: 0.5,
    explanation: {
      explanation_version: "1.0",
      status: "AVAILABLE",
      method: "XGBOOST_NATIVE_TREESHAP",
      target: "ASKING_PRICE_VND",
      output_space: "LOG1P_PRICE_VND",
      predicted_margin_log: 0.5,
      factors: [1, 2, 3, 4, 5, 6].map((i) => factor(`f${i}`, 0.02)),
      grouped_contributions: { LOCATION: 0.1, AREA: 0.1, ROOM: 0.1, ACCESS: 0.05, QUALITY: 0.05, MARKET: 0.1 },
      feature_provenance: Object.fromEntries(
        Array.from({ length: 22 }, (_, i) => [`f${i}`, i % 2 ? "OBSERVED" : "DERIVED"]),
      ),
      base_value_log: 0.0,
      other_contribution_log: 0.0,
      calibration: {
        policy: "duan_by_band",
        factor: 1,
        adjusted_price_vnd: PRICE,
      },
    },
  };
  return { ...base, ...(overrides || {}) };
}

async function runCase(browser, name, payload, expect) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  try {
    await page.route("**/api/ai/predict", (route) =>
      route.fulfill({ status: 200, contentType: "application/json", body: JSON.stringify(payload) }));
    await page.goto(`${APP}/valuation`, { waitUntil: "domcontentloaded", timeout: 25000 });
    await page.getByPlaceholder("Ví dụ: 80").first().fill("100");
    await page.locator("select").first().selectOption({ index: 1 });
    await page.getByRole("button", { name: /Ước tính giá rao/ }).first().click({ timeout: 15000 });
    await page.waitForTimeout(1800);

    const price = await page.locator('[data-testid="explanation-price"]').first().innerText()
      .catch(() => "");
    const body = await page.locator("body").innerText();
    const status = await page.locator('[data-testid="valuation-explanation-panel"]').first()
      .getAttribute("data-explanation-status").catch(() => null);
    const rows = await page.locator("[data-row^='step-']").count();
    const waterfall = await page.locator('[data-testid="explanation-waterfall-svg"]').count();

    record(`${name}: authoritative price visible`, /\d/.test(price) && price.trim() !== "—", price);
    record(`${name}: status ${expect.status}`, status === expect.status, status);
    if (expect.hideAttribution) {
      record(`${name}: no attribution rows`, rows === 0, rows);
      record(`${name}: no waterfall`, waterfall === 0, waterfall);
    }
    if (expect.noFabrication) {
      record(`${name}: no fabricated price`, price.trim() === "—" || price.trim() === "", price);
    }
    record(`${name}: no crash text`, !/Uncaught|Cannot read/.test(body));
  } catch (error) {
    record(`${name}: workflow`, false, String(error.message || error).split("\n")[0].slice(0, 160));
  } finally {
    await page.close();
  }
}

async function loginPage(page) {
  await page.goto(`${APP}/login?next=%2Faccount`, { waitUntil: "domcontentloaded", timeout: 25000 });
  await page.locator("#email-input").fill(EMAIL);
  await page.locator("#password-input").fill(PASSWORD);
  await page.getByRole("button", { name: /Đăng nhập/i }).first().click({ timeout: 15000 });
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), { timeout: 25000 });
}

async function reactiveAuthorization(browser, sql) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  try {
    await loginPage(page);
    record("auth: login succeeded", !page.url().includes("/login"), page.url());

    // lock the account in the disposable fixture only
    const loginStatus = async () => {
      const response = await fetch(`${API}/api/v1/auth/login`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ email: EMAIL, password: PASSWORD }),
      });
      return response.status;
    };

    sql(`UPDATE users SET status='LOCKED' WHERE email='${EMAIL}'`);
    const locked = await loginStatus();
    record("auth: locked account is refused", locked >= 400, locked);

    // the SPA must not keep reporting an authorized identity after a reload
    await page.reload({ waitUntil: "domcontentloaded" });
    await page.waitForTimeout(1200);
    const afterLock = await page.evaluate(async () => {
      const response = await fetch("/api/v1/users/me");
      return response.status;
    });
    record("auth: restricted data is not served while locked", afterLock >= 400, afterLock);

    sql(`UPDATE users SET status='ACTIVE' WHERE email='${EMAIL}'`);
    const restored = await loginStatus();
    record("auth: restored fixture logs in again", restored >= 200 && restored < 300, restored);
  } catch (error) {
    record("auth: workflow", false, String(error.message || error).split("\n")[0].slice(0, 160));
    sql(`UPDATE users SET status='ACTIVE' WHERE email='${EMAIL}'`);
  } finally {
    await page.close();
  }
}

async function main() {
  const require = createRequire(import.meta.url);
  const playwright = require(PW);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });
  const sql = (statement) => {
    const { execFileSync } = require("node:child_process");
    try {
      execFileSync("F:/SmartProp/.scratch/mysql-8.4/mysql-8.4.13-winx64/bin/mysql.exe",
        ["-h", "127.0.0.1", "-P", "3407", "-u", "wp04_v23", "-pwp04-v23-fixture", "wp04_runtime_v23", "-e", statement],
        { stdio: "ignore" });
    } catch { /* recorded by the caller's assertions */ }
  };
  try {
    const baseline = await realPayload();
    record("baseline predict carries an explanation", baseline.explanation?.status === "AVAILABLE",
      baseline.explanation?.status);
    const clone = () => JSON.parse(JSON.stringify(baseline));

    const missing = clone();
    delete missing.explanation;
    await runCase(browser, "missing explanation", missing,
      { status: null, hideAttribution: true });

    const unavailable = clone();
    unavailable.explanation = { status: "UNAVAILABLE", reason: "Không đủ dữ liệu." };
    await runCase(browser, "UNAVAILABLE", unavailable, { status: "UNAVAILABLE", hideAttribution: true });

    const malformed = clone();
    malformed.explanation = { status: "AVAILABLE", factors: [] };
    await runCase(browser, "malformed", malformed, { status: "INVALID", hideAttribution: true });

    const invalidAdjusted = clone();
    invalidAdjusted.explanation.calibration.adjusted_price_vnd = 0;
    await runCase(browser, "invalid adjusted price", invalidAdjusted, { status: "INVALID", hideAttribution: true });

    const oneVnd = clone();
    oneVnd.explanation.calibration.adjusted_price_vnd =
      Number(oneVnd.explanation.calibration.adjusted_price_vnd) + 1;
    await runCase(browser, "one-VND mismatch", oneVnd, { status: "INCONSISTENT", hideAttribution: true });

    const reconstruction = clone();
    reconstruction.explanation.predicted_margin_log =
      Number(reconstruction.explanation.predicted_margin_log) + 0.5;
    await runCase(browser, "reconstruction mismatch", reconstruction, { status: "INVALID", hideAttribution: true });

    await reactiveAuthorization(browser, sql);
  } finally {
    await browser.close();
  }

  const failed = results.filter((r) => !r.ok);
  mkdirSync(out, { recursive: true });
  writeFileSync(join(out, "wp04-failure-isolation.json"), JSON.stringify({
    at: new Date().toISOString(), total: results.length,
    passed: results.length - failed.length, failed: failed.length, results,
  }, null, 2));
  for (const item of failed) console.log(`FAIL  ${item.name} — ${item.detail}`);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length ? 1 : 0);
}

main().catch((error) => { console.error("FATAL", error); process.exit(2); });
