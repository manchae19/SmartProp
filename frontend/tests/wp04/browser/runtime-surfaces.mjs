/**
 * WP-04 B6 — real-runtime browser interactions (no interception).
 *
 * Drives the actual Vite app at WP04_APP against the real Spring Boot (8080) and FastAPI (8000)
 * instances, with a real BROKER JWT from /api/v1/auth/login. Every successful response used for
 * assertion is a genuine network response.
 *
 *   WP04_APP=http://127.0.0.1:5180 node tests/wp04/browser/runtime-surfaces.mjs
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PW = process.env.PLAYWRIGHT_PATH || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const APP = process.env.WP04_APP || "http://127.0.0.1:5180";
const API = process.env.WP04_API || "http://127.0.0.1:8080";
const here = dirname(fileURLToPath(import.meta.url));
const shots = join(here, "..", "..", "..", "docs", "ai", "browser", "wp04");

const results = [];
const record = (name, ok, detail = "") =>
  results.push({ name, ok: Boolean(ok), detail: String(detail).slice(0, 220) });

async function brokerToken() {
  const response = await fetch(`${API}/api/v1/auth/login`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ email: "wp04.broker@fixture.invalid", password: "Wp04Fixture!2026" }),
  });
  if (!response.ok) throw new Error(`login failed: ${response.status}`);
  return (await response.json()).accessToken;
}

async function assertPanel(page, tag) {
  const panel = page.locator('[data-testid="valuation-explanation-panel"]');
  await panel.first().waitFor({ timeout: 20000 });
  const count = await panel.count();
  record(`${tag} explanation panel present`, count >= 1, count);
  const status = await panel.first().getAttribute("data-explanation-status");
  record(`${tag} explanation AVAILABLE`, status === "AVAILABLE", status);
  const price = await page.locator('[data-testid="explanation-price"]').first().innerText();
  record(`${tag} price is rendered`, /tỷ|₫/.test(price), price.slice(0, 40));

  const summary = panel.first().locator("summary");
  if (await summary.count()) {
    await summary.first().click();
    await page.waitForTimeout(300);
    record(`${tag} waterfall opens`, (await panel.first().locator('[data-testid="explanation-waterfall"]').count()) === 1);
    record(`${tag} six contribution rows`,
      (await panel.first().locator("[data-row^='step-']").count()) === 6,
      await panel.first().locator("[data-row^='step-']").count());
    record(`${tag} 22 provenance entries`,
      (await panel.first().locator("[data-provenance]").count()) === 22,
      await panel.first().locator("[data-provenance]").count());
    record(`${tag} calibration bridge visible`,
      (await panel.first().locator('[data-testid="explanation-calibration"]').count()) === 1);
    record(`${tag} waterfall geometry rendered`,
      (await panel.first().locator('[data-testid="explanation-waterfall-svg"]').count()) === 1);
  }

  const body = await page.locator("body").innerText();
  record(`${tag} no NaN/Infinity`, !/NaN|Infinity/.test(body));
}

async function valuationSurface(browser, token) {
  for (const width of [320, 390, 768, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1100 } });
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 100)));
    const api = [];
    page.on("response", (r) => {
      if (r.url().includes("/api/")) api.push(`${r.status()} ${new URL(r.url()).pathname}`);
    });
    await page.addInitScript((t) => {
      localStorage.setItem("token", t);
      localStorage.setItem("role", "BROKER");
    }, token);
    try {
      await page.goto(`${APP}/valuation`, { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(1800);
      const selects = page.locator("select");
      await selects.first().selectOption({ index: 1 }).catch(() => {});
      const numberInput = page.locator('input[type="number"]').first();
      await numberInput.fill("100").catch(() => {});
      const submit = page.getByRole("button", { name: /Ước tính giá rao/ });
      await submit.first().click({ timeout: 8000 });
      await page.waitForTimeout(2500);

      const predict = api.filter((entry) => entry.includes("/api/ai/predict"));
      record(`valuation@${width} real predict call`, predict.some((entry) => entry.startsWith("200")),
        predict.join(","));
      await assertPanel(page, `valuation@${width}`);
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
      record(`valuation@${width} no horizontal overflow`, overflow);
      record(`valuation@${width} no console error`, errors.length === 0, errors.join(" | "));
      if (width === 390) {
        mkdirSync(shots, { recursive: true });
        await page.screenshot({ path: join(shots, "runtime-valuation-390.png"), fullPage: false });
      }
    } catch (error) {
      record(`valuation@${width} interaction`, false, String(error.message || error).slice(0, 160));
    } finally {
      await page.close();
    }
  }
}

async function advisorSurface(browser, token) {
  for (const width of [390, 1440]) {
    const page = await browser.newPage({ viewport: { width, height: 1200 } });
    const errors = [];
    page.on("pageerror", (e) => errors.push(String(e).slice(0, 100)));
    const api = [];
    page.on("response", (r) => {
      if (r.url().includes("/api/")) api.push(`${r.status()} ${new URL(r.url()).pathname}`);
    });
    await page.addInitScript((t) => {
      localStorage.setItem("token", t);
      localStorage.setItem("role", "BROKER");
    }, token);
    try {
      await page.goto(`${APP}/advisor`, { waitUntil: "domcontentloaded", timeout: 20000 });
      await page.waitForTimeout(1800);
      await page.locator('input[name="budget"]').fill("7000000000").catch(() => {});
      await page.locator('input[name="district"]').fill("Cẩm Lệ").catch(() => {});
      await page.locator('input[name="minAreaSqm"]').fill("60").catch(() => {});
      await page.getByRole("button", { name: /Tìm gợi ý phù hợp/ }).first().click({ timeout: 8000 });
      await page.waitForTimeout(4000);

      const consult = api.filter((entry) => entry.includes("/advisor/consult"));
      record(`advisor@${width} real consult call`, consult.some((entry) => entry.startsWith("200")),
        consult.join(","));
      await assertPanel(page, `advisor@${width}`);
      const text = await page.locator("body").innerText();
      record(`advisor@${width} shows comparable evidence`, /tương đồng|Comparable/i.test(text));
      record(`advisor@${width} no NaN/Infinity`, !/NaN|Infinity/.test(text));
      const overflow = await page.evaluate(() => document.documentElement.scrollWidth <= document.documentElement.clientWidth + 1);
      record(`advisor@${width} no horizontal overflow`, overflow);
      record(`advisor@${width} no console error`, errors.length === 0, errors.join(" | "));
      if (width === 390) {
        mkdirSync(shots, { recursive: true });
        await page.screenshot({ path: join(shots, "runtime-advisor-390.png"), fullPage: false });
      }
    } catch (error) {
      record(`advisor@${width} interaction`, false, String(error.message || error).slice(0, 160));
    } finally {
      await page.close();
    }
  }
}

async function postingSurface(browser, token) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  try {
    await page.addInitScript((t) => {
      localStorage.setItem("token", t);
      localStorage.setItem("role", "BROKER");
    }, token);
    await page.goto(`${APP}/post/step-4`, { waitUntil: "domcontentloaded", timeout: 20000 });
    await page.waitForTimeout(2500);
    const text = await page.locator("body").innerText();
    record("posting route renders", text.length > 50);
    record("posting preview interaction", false,
      "posting draft state is not reachable from a cold route without a persisted draft", true);
  } catch (error) {
    record("posting route", false, String(error.message || error).slice(0, 160));
  } finally {
    await page.close();
  }
}

async function main() {
  const require = createRequire(import.meta.url);
  const playwright = require(PW);
  let token;
  try {
    token = await brokerToken();
    record("real broker login", true);
  } catch (error) {
    record("real broker login", false, String(error.message || error));
  }
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });
  try {
    if (token) {
      await valuationSurface(browser, token);
      await advisorSurface(browser, token);
      await postingSurface(browser, token);
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((item) => !item.ok && !item.skipped);
  const skipped = results.filter((item) => item.skipped);
  const outDir = join(here, "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "wp04-runtime-browser.json"), JSON.stringify({
    app: APP, api: API, at: new Date().toISOString(),
    total: results.length,
    passed: results.length - failed.length - skipped.length,
    failed: failed.length, skipped: skipped.length, results,
  }, null, 2));
  for (const item of results) {
    if (!item.ok) console.log(`${item.skipped ? "SKIP" : "FAIL"}  ${item.name} — ${item.detail}`);
  }
  console.log(`\n${results.length - failed.length - skipped.length} passed, ${failed.length} failed, ${skipped.length} skipped`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error("FATAL", error);
  process.exit(2);
});
