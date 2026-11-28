/**
 * WP-04 B6 — real-runtime browser workflows (no interception, no credential injection).
 *
 * Auth goes through the actual /login UI; the app never reads tokens from localStorage (auth/api.js
 * removes legacy keys). Fixture credentials come from the process environment.
 *
 *   WP04_APP=http://127.0.0.1:5180 WP04_API=http://127.0.0.1:8080 \
 *   WP04_FIXTURE_EMAIL=... WP04_FIXTURE_PASSWORD=... \
 *   node tests/wp04/browser/runtime-surfaces.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PW = process.env.PLAYWRIGHT_PATH || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = process.env.WP04_APP || "";
const API = process.env.WP04_API || "";
const EMAIL = process.env.WP04_FIXTURE_EMAIL || "";
const PASSWORD = process.env.WP04_FIXTURE_PASSWORD || "";
const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "..", "docs", "ai", "browser", "wp04");

const results = [];
const record = (name, ok, detail = "") =>
  results.push({ name, ok: Boolean(ok), detail: String(detail).slice(0, 240) });

const LOOPBACK = /^http:\/\/127\.0\.0\.1:\d{2,5}$/;

function preflight() {
  for (const [label, value] of [["WP04_APP", APP], ["WP04_API", API]]) {
    record(`${label} is loopback`, LOOPBACK.test(value), value);
  }
  record("fixture credentials provided", Boolean(EMAIL && PASSWORD));
}

/** Event-driven wait for a specific request, resolved with its response. */
function expectCall(page, matcher, action, timeout = 30000) {
  const response = page.waitForResponse(
    (r) => matcher(r.url()) && r.request().method() === "POST",
    { timeout },
  );
  return action().then(() => response);
}

async function login(page) {
  await page.goto(`${APP}/login?next=%2Fpost`, { waitUntil: "domcontentloaded", timeout: 25000 });
  await page.locator("#email-input").fill(EMAIL);
  await page.locator("#password-input").fill(PASSWORD);
  const login = expectCall(page, (url) => url.includes("/auth/login"), async () => {
    await page.getByRole("button", { name: /Đăng nhập/i }).first().click({ timeout: 15000 });
  });
  const response = await login;
  record("login response 200", response.status() === 200, response.status());
  await page.waitForFunction(() => !location.pathname.startsWith("/login"), { timeout: 25000 });
  await page.waitForTimeout(600);
  // The SPA authenticates with a Bearer token it keeps in memory, so a bare fetch would 401.
  // Confirm the session through the rendered UI instead.
  const signOutVisible = await page.getByRole("button", { name: /Đăng xuất|Tài khoản/i }).count();
  record("session confirmed in the UI", signOutVisible > 0, signOutVisible);
}

async function assertExplanation(page, tag) {
  const panel = page.locator('[data-testid="valuation-explanation-panel"]').first();
  await panel.waitFor({ state: "visible", timeout: 25000 });
  record(`${tag} explanation panel visible`, true);
  record(`${tag} AVAILABLE`,
    (await panel.getAttribute("data-explanation-status")) === "AVAILABLE",
    await panel.getAttribute("data-explanation-status"));
  const price = await page.locator('[data-testid="explanation-price"]').first().innerText();
  record(`${tag} price text`, /tỷ|₫/.test(price), price.slice(0, 32));

  const summary = panel.locator("summary").first();
  record(`${tag} technical section exists`, (await summary.count()) === 1);
  if (await summary.count()) {
    await summary.click({ timeout: 10000 });
    await page.waitForTimeout(400);
    record(`${tag} waterfall rows`, (await panel.locator('[data-testid="explanation-waterfall"]').count()) === 1);
    record(`${tag} six factor rows`, (await panel.locator("[data-row^='step-']").count()) === 6,
      await panel.locator("[data-row^='step-']").count());
    record(`${tag} 22 provenance entries`, (await panel.locator("[data-provenance]").count()) === 22,
      await panel.locator("[data-provenance]").count());
    record(`${tag} calibration bridge`, (await panel.locator('[data-testid="explanation-calibration"]').count()) === 1);
  }
  const body = await page.locator("body").innerText();
  record(`${tag} no NaN/Infinity`, !/NaN|Infinity/.test(body));
}

async function standalone(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 1100 } });
  const errors = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)));
  const tag = `standalone@${width}`;
  try {
    await page.goto(`${APP}/valuation`, { waitUntil: "domcontentloaded", timeout: 25000 });
    await page.waitForResponse((r) => r.url().includes("/model/options"), { timeout: 20000 });
    await page.getByPlaceholder("Ví dụ: 80").first().fill("100");
    const category = page.locator("select").first();
    await category.selectOption({ label: "Nhà ở" });
    const location = page.locator("select").nth(1);
    await location.selectOption({ label: "Cẩm Lệ" });
    const response = await expectCall(page, (url) => url.includes("/api/ai/predict"), async () => {
      await page.getByRole("button", { name: /Ước tính giá rao/ }).first().click({ timeout: 15000 });
    });
    record(`${tag} predict 200`, response.status() === 200, response.status());
    const body = await response.json();
    record(`${tag} model v1.3`, body.model_version === "v1.3", body.model_version);
    record(`${tag} positive integer price`, Number.isInteger(body.predicted_asking_price_vnd)
      && body.predicted_asking_price_vnd > 0, body.predicted_asking_price_vnd);
    await page.locator('[data-testid="estimated-price"]').first().waitFor({ timeout: 20000 });
    record(`${tag} estimated price visible`, true);
    await assertExplanation(page, tag);
    record(`${tag} no overflow`, await page.evaluate(() =>
      document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
    record(`${tag} no page error`, errors.length === 0, errors.join(" | "));
    if (width === 390) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: join(shots, "real-standalone-390.png") });
    }
  } catch (error) {
    record(`${tag} workflow`, false, String(error.message || error).split("\n")[0].slice(0, 180));
  } finally {
    await page.close();
  }
}

async function posting(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 1200 } });
  const tag = `posting@${width}`;
  try {
    await login(page);
    // The access token lives in memory only, so a full page load would drop the session and
    // redirect to /login. Navigate inside the SPA instead.
    const postLink = page.getByRole("link", { name: /Đăng tin|Đăng bán|Đăng bài/i }).first();
    if (await postLink.count()) {
      await postLink.click({ timeout: 15000 });
    } else {
      await page.getByRole("button", { name: /Đăng tin|Đăng bán/i }).first().click({ timeout: 15000 });
    }
    await page.waitForTimeout(1500);
    record(`${tag} reached posting workflow`, !page.url().includes("/login"), page.url());
    const start = page.getByRole("button", { name: /Đăng bán/i }).first();
    if (await start.count()) await start.click({ timeout: 10000 });
    await page.locator("#post-propertyType").selectOption({ index: 1 });
    await page.locator("#post-title").fill("WP04 runtime fixture");
    await page.locator("#post-area").fill("80");
    await page.locator("#post-price").fill("5000000000");
    const summary = page.locator(".valuation-optional summary").first();
    await summary.click({ timeout: 10000 });
    await page.waitForTimeout(1500);
    const locationSelect = page.locator('[data-testid="valuation-location"]');
    const optionLabels = await locationSelect.locator("option").allInnerTexts();
    const camLe = optionLabels.find((label) => /Cẩm Lệ/.test(label)) ? "Cẩm Lệ" : null;
    if (camLe) await locationSelect.selectOption({ label: camLe });
    else await locationSelect.selectOption({ index: 1 });
    const response = await expectCall(page,
      (url) => url.includes("/api/v1/properties/valuation-preview"), async () => {
        await page.locator('[data-testid="valuation-preview"]').click({ timeout: 15000 });
      });
    record(`${tag} preview 200`, response.status() === 200, response.status());
    const body = await response.json();
    record(`${tag} available`, body.available === true, body.available);
    record(`${tag} positive price`, Number.isInteger(Number(body.predictedAskingPriceVnd))
      && Number(body.predictedAskingPriceVnd) > 0, body.predictedAskingPriceVnd);
    record(`${tag} explanation AVAILABLE`, body.explanation?.status === "AVAILABLE",
      body.explanation?.status);
    record(`${tag} adjusted price matches`, String(body.predictedAskingPriceVnd)
      === String(body.explanation?.calibration?.adjusted_price_vnd),
    `${body.predictedAskingPriceVnd}/${body.explanation?.calibration?.adjusted_price_vnd}`);
    await assertExplanation(page, tag);
    record(`${tag} no overflow`, await page.evaluate(() =>
      document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
  } catch (error) {
    record(`${tag} workflow`, false, String(error.message || error).split("\n")[0].slice(0, 180));
  } finally {
    await page.close();
  }
}

async function advisor(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 1200 } });
  const tag = `advisor@${width}`;
  try {
    await login(page);
    await page.goto(`${APP}/advisor/analysis`, { waitUntil: "domcontentloaded", timeout: 25000 });
    await page.getByRole("heading", { name: /Tư vấn bất động sản đa bằng chứng/ })
      .first().waitFor({ timeout: 20000 });
    record(`${tag} unified advisor heading`, true);
    await page.getByLabel(/Ngân sách mục tiêu/).first().fill("7000000000");
    await page.getByLabel(/Loại bất động sản/).first().selectOption({ label: "Nhà ở" }).catch(() => {});
    await page.getByLabel(/Quận\/Huyện|Khu vực/).first().fill("Cẩm Lệ").catch(() => {});
    const response = await expectCall(page, (url) => url.includes("/api/v1/advisor/consult"), async () => {
      await page.locator(".advisor-page form").first().evaluate((form) => form.requestSubmit());
    }, 45000);
    record(`${tag} consult 200`, response.status() === 200, response.status());
    const body = await response.json();
    record(`${tag} SAFE mode`, body.mode === "SAFE", body.mode);
    record(`${tag} has recommendation`, (body.recommendedProperties || []).length > 0,
      (body.recommendedProperties || []).length);
    await page.waitForTimeout(1500);
    await assertExplanation(page, tag);
    const text = await page.locator("body").innerText();
    record(`${tag} comparable evidence shown`, /tương đồng|Comparable/i.test(text));
    const researchFlags = JSON.stringify(body).match(/"researchReference":true|"includeResearch":true/g) || [];
    record(`${tag} no research disclosure`, researchFlags.length === 0, researchFlags.join(","));
    record(`${tag} no overflow`, await page.evaluate(() =>
      document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
    if (width === 390) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: join(shots, "real-advisor-390.png") });
    }
  } catch (error) {
    record(`${tag} workflow`, false, String(error.message || error).split("\n")[0].slice(0, 180));
  } finally {
    await page.close();
  }
}

async function main() {
  preflight();
  if (results.some((r) => !r.ok)) {
    console.log("preflight failed; refusing to run");
    for (const item of results) if (!item.ok) console.log(`FAIL ${item.name} — ${item.detail}`);
    process.exit(2);
  }
  const require = createRequire(import.meta.url);
  const playwright = require(PW);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });
  try {
    await standalone(browser, 1280);
    await posting(browser, 1280);
    await advisor(browser, 1280);
    for (const width of [320, 390, 768, 1440]) {
      await standalone(browser, width);
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((item) => !item.ok);
  const outDir = join(here, "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "wp04-runtime-browser.json"), JSON.stringify({
    app: APP, api: API, at: new Date().toISOString(),
    total: results.length, passed: results.length - failed.length,
    failed: failed.length, results,
  }, null, 2));
  for (const item of results) if (!item.ok) console.log(`FAIL  ${item.name} — ${item.detail}`);
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error("FATAL", error);
  process.exit(2);
});
