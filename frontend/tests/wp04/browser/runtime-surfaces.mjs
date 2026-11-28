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
import {
  advisorPath, predictPath, prepareAdvisor, preparePosting, prepareStandalone, previewPath, waitResponse,
} from "./workflows.mjs";

const PW = process.env.PLAYWRIGHT_PATH || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = process.env.WP04_APP || "";
const API = process.env.WP04_API || "";
const EMAIL = process.env.WP04_FIXTURE_EMAIL || "";
const PASSWORD = process.env.WP04_FIXTURE_PASSWORD || "";
const here = dirname(fileURLToPath(import.meta.url));
const shots = process.env.WP04_OUTPUT_DIR || join(here, "..", "..", "..", "..", "docs", "ai", "browser", "wp04");

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

async function assertExplanation(page, tag) {
  const panel = page.locator('[data-testid="valuation-explanation-panel"]').first();
  await panel.waitFor({ state: "visible", timeout: 25000 });
  record(`${tag} explanation panel visible`, true);
  record(`${tag} AVAILABLE`,
    (await panel.getAttribute("data-explanation-status")) === "AVAILABLE",
    await panel.getAttribute("data-explanation-status"));
  const price = await page.locator('[data-testid="explanation-price"]').first().innerText();
  const trimmed = price.trim();
  // A placeholder dash is not a price: require at least one digit from the real response.
  const hasDigits = /\d/.test(trimmed);
  const notPlaceholder = trimmed !== "" && trimmed !== "—" && trimmed !== "-";
  record(`${tag} price text`, hasDigits && notPlaceholder, trimmed.slice(0, 40));

  const summary = panel.locator("summary").first();
  record(`${tag} technical section exists`, (await summary.count()) === 1);
  if (await summary.count()) {
    await summary.click({ timeout: 10000 });
    await panel.getByTestId("explanation-waterfall-svg").waitFor();
    record(`${tag} waterfall rows`, (await panel.locator('[data-testid="explanation-waterfall"]').count()) === 1);
    record(`${tag} six factor rows`, (await panel.locator("[data-row^='step-']").count()) === 6,
      await panel.locator("[data-row^='step-']").count());
    record(`${tag} 22 provenance entries`, (await panel.locator("[data-provenance]").count()) === 22,
      await panel.locator("[data-provenance]").count());
    record(`${tag} calibration bridge`, (await panel.locator('[data-testid="explanation-calibration"]').count()) === 1);
    record(`${tag} explanation groups`, (await panel.locator('[data-testid="explanation-groups"]').count()) === 1);
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
    const submit = await prepareStandalone(page, APP);
    const pending = waitResponse(page, predictPath);
    await submit.click();
    const response = await pending;
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
  const errors = [];
  const failed = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)));
  page.on("requestfailed", (r) => failed.push(`${r.method()} ${new URL(r.url()).pathname}`));
  try {
    const submit = await preparePosting(page, APP, EMAIL, PASSWORD);
    const pending = waitResponse(page, previewPath);
    await submit.click();
    const response = await pending;
    record(`${tag} preview 200`, response.status() === 200, response.status());
    const body = await response.json();
    record(`${tag} available`, body.available === true, body.available);
    const price = Number(body.predictedAskingPriceVnd);
    record(`${tag} positive integer price`, Number.isInteger(price) && price > 0,
      body.predictedAskingPriceVnd);
    record(`${tag} explanation AVAILABLE`, body.explanation?.status === "AVAILABLE",
      body.explanation?.status);
    record(`${tag} adjusted price matches`,
      String(body.predictedAskingPriceVnd) === String(body.explanation?.calibration?.adjusted_price_vnd),
      `${body.predictedAskingPriceVnd}/${body.explanation?.calibration?.adjusted_price_vnd}`);
    await assertExplanation(page, tag);
    record(`${tag} no overflow`, await page.evaluate(() =>
      document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
    record(`${tag} no page error`, errors.length === 0, errors.join(" | "));
    const apiFailures = failed.filter((entry) => entry.includes("/api/"));
    record(`${tag} no failed API request`, apiFailures.length === 0, apiFailures.join(" | "));
    if (width === 390) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: join(shots, "real-posting-390.png") });
    }
  } catch (error) {
    record(`${tag} workflow`, false, String(error.message || error).split("\n")[0].slice(0, 180));
  } finally {
    await page.close();
  }
}

async function advisor(browser, width) {
  const page = await browser.newPage({ viewport: { width, height: 1200 } });
  const tag = `advisor@${width}`;
  const errors = [];
  const failed = [];
  page.on("pageerror", (e) => errors.push(String(e).slice(0, 120)));
  page.on("requestfailed", (r) => failed.push(`${r.method()} ${new URL(r.url()).pathname}`));
  try {
    const submit = await prepareAdvisor(page, APP);
    const pending = waitResponse(page, advisorPath);
    await submit.click();
    const response = await pending;
    record(`${tag} consult 200`, response.status() === 200, response.status());
    const body = await response.json();
    const request = JSON.parse(response.request().postData() || "{}");
    record(`${tag} request includeResearch false`, request.includeResearch !== true,
      JSON.stringify({ includeResearch: request.includeResearch }));
    record(`${tag} request propertyType HOUSE`, request.propertyType === "HOUSE", request.propertyType);
    record(`${tag} SAFE mode`, body.mode === "SAFE", body.mode);
    const recommendations = body.recommendedProperties || [];
    record(`${tag} has recommendation`, recommendations.length > 0, recommendations.length);

    const first = recommendations[0] || {};
    const comparable = first.comparableEvidence;
    const valuationComparable = first.valuationComparableEvidence;
    record(`${tag} comparableEvidence section`,
      comparable?.status === "AVAILABLE" || comparable?.candidateCount > 0,
      `${comparable?.status}/${comparable?.candidateCount}`);
    record(`${tag} valuationComparableEvidence section`,
      valuationComparable?.status === "AVAILABLE" || valuationComparable?.candidateCount > 0,
      `${valuationComparable?.status}/${valuationComparable?.candidateCount}`);
    const coverage = [
      ...(comparable?.comparables || []),
      ...(valuationComparable?.comparables || []),
    ].some((item) => item.featureCoverage !== undefined && item.featureCoverage !== null);
    record(`${tag} featureCoverage present`, coverage);

    await page.locator("[data-advisor-property]").first().waitFor();
    const text = await page.locator("body").innerText();
    record(`${tag} price headline shown`, /tỷ/.test(text));
    record(`${tag} heading: Tin tương đồng theo giá rao`, /Tin tương đồng theo giá rao/i.test(text));
    record(`${tag} heading: Đối chiếu định giá bằng tin đăng`, /Đối chiếu định giá bằng tin đăng/i.test(text));
    await assertExplanation(page, tag);
    record(`${tag} no research disclosure`, !/(TINIX_RESEARCH|includeResearch":true)/.test(text));
    record(`${tag} no overflow`, await page.evaluate(() =>
      document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1));
    record(`${tag} no page error`, errors.length === 0, errors.join(" | "));
    const apiFailures = failed.filter((entry) => entry.includes("/api/"));
    record(`${tag} no failed API request`, apiFailures.length === 0, apiFailures.join(" | "));
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
  const surfaceArg = process.argv.find((a) => a.startsWith("--surfaces="));
  const widthArg = process.argv.find((a) => a.startsWith("--widths="));
  const surfaces = surfaceArg ? surfaceArg.split("=")[1].split(",") : ["standalone", "posting", "advisor"];
  const widths = widthArg
    ? widthArg.split("=")[1].split(",").map(Number)
    : [1280, 320, 390, 768, 1440];
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });
  try {
    for (const surface of surfaces) {
      for (const width of widths) {
        if (surface === "standalone") await standalone(browser, width);
        if (surface === "posting") await posting(browser, width);
        if (surface === "advisor") await advisor(browser, width);
      }
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((item) => !item.ok);
  const outDir = process.env.WP04_OUTPUT_DIR || join(here, "reports");
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
