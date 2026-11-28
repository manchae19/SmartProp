/**
 * WP-04 B5 — mocked three-surface browser integration.
 *
 * Uses the committed V1.3 fixtures (never a hand-built one-factor payload) and the real React
 * components. The Advisor surface is mounted with its real props; the standalone and posting
 * routes are exercised by failure-isolation.mjs. Its required route-level results are linked
 * to this component report only after the three cases pass.
 *
 *   WP04_BASE=http://127.0.0.1:5199 node tests/wp04/browser/surfaces.mjs
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLAYWRIGHT = process.env.PLAYWRIGHT_PATH
  || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME
  || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = process.env.WP04_BASE || "http://127.0.0.1:5199";

const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(
  join(here, "..", "fixtures", "explanation-samples.json"), "utf8"));

const results = [];
function record(name, ok, detail = "", status = null) {
  results.push({
    name, ok: Boolean(ok), detail: String(detail).slice(0, 200),
    status: status || (ok ? "PASS" : "FAIL"),
  });
}


const CASES = ["advisor-available", "advisor-legacy", "advisor-unavailable", "advisor-malformed"];

async function main() {
  const require = createRequire(import.meta.url);
  const playwright = require(PLAYWRIGHT);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });

  try {
    for (const name of CASES) {
      const page = await browser.newPage({ viewport: { width: 1280, height: 1000 } });
      try {
        await page.goto(`${BASE}/tests/wp04/surfaces/?case=${name}`,
          { waitUntil: "domcontentloaded", timeout: 15000 });
        await page.waitForSelector("[data-advisor-evidence]", { timeout: 8000 });
        await page.waitForFunction(() => document.documentElement.dataset.rendered === "true");

        const panel = page.locator('[data-testid="valuation-explanation-panel"]');
        const panelCount = await panel.count();
        const comparables = await page.locator("text=/tin tương đồng|Tương đồng/i").count();
        const featureCoverage = await page.locator("text=/Độ phủ/i").count();

        if (name === "advisor-available") {
          record("advisor mounts the explanation panel", panelCount === 1, panelCount);
          if (panelCount === 1) {
            record("advisor panel status is AVAILABLE",
              (await panel.getAttribute("data-explanation-status")) === "AVAILABLE");
            const factors = await panel.locator("[data-row^='step-']").count();
            record("advisor waterfall shows the six contributions", factors === 6, factors);
            const provenance = await panel.locator("[data-provenance]").count();
            record("advisor renders all 22 provenance rows", provenance === 22, provenance);
            record("advisor shows the calibration bridge",
              (await panel.locator('[data-testid="explanation-calibration"]').count()) === 1);
            record("advisor renders the cumulative waterfall svg",
              (await panel.locator('[data-testid="explanation-waterfall-svg"]').count()) === 1);
            record("advisor keeps legacy SHAP hidden",
              (await page.locator("[data-shap-toggle]").count()) === 0);
            record("advisor does not duplicate a legacy SHAP panel",
              (await page.locator("[data-shap-panel]").count()) === 0);
          }
          record("both comparable evidence sections render", comparables >= 2, comparables);
          record("feature coverage is displayed", featureCoverage >= 1, featureCoverage);
        } else if (name === "advisor-legacy") {
          record("legacy response hides the new panel", panelCount === 0, panelCount);
          record("legacy response offers the SHAP toggle",
            (await page.locator("[data-shap-toggle]").count()) === 1);
          record("legacy response has no SHAP panel until opened",
            (await page.locator("[data-shap-panel]").count()) === 0);
        } else if (name === "advisor-unavailable") {
          record("unavailable explanation still renders the panel", panelCount === 1, panelCount);
          if (panelCount === 1) {
            record("unavailable panel reports UNAVAILABLE",
              (await panel.getAttribute("data-explanation-status")) === "UNAVAILABLE");
            record("unavailable panel shows no waterfall",
              (await panel.locator('[data-testid="explanation-waterfall"]').count()) === 0);
          }
        } else {
          record("malformed explanation degrades to INVALID", panelCount === 1, panelCount);
          if (panelCount === 1) {
            record("malformed panel reports INVALID",
              (await panel.getAttribute("data-explanation-status")) === "INVALID");
            record("malformed panel shows no attribution",
              (await panel.locator("[data-provenance]").count()) === 0);
          }
        }
        const jsError = await page.locator("[data-js-error]").count();
        record(`${name} renders without a JS exception`, jsError === 0, jsError);
        const body = await page.locator("body").innerText();
        record(`${name} shows no NaN or Infinity`, !/NaN|Infinity/.test(body));
      } catch (error) {
        record(`${name} interaction`, false, String(error.message || error).slice(0, 160));
      } finally {
        await page.close();
      }
    }

    const routeReport = JSON.parse(readFileSync(process.env.WP04_FAILURE_REPORT, "utf8"));
    for (const [surface, prefix] of [
      ["standalone", "standalone: missing explanation"],
      ["posting", "posting: invalid explanation"],
      ["advisor", "Advisor: unavailable explanation"],
    ]) {
      const evidence = routeReport.filter((item) => item.name.startsWith(prefix)
        && item.classification === "MOCKED_RESPONSE");
      record(surface + " route-level mutation (failure-isolation.mjs)",
        evidence.length === 1 && evidence[0].ok, evidence[0]?.name ?? "Missing executable coverage");
    }

  } finally {
    await browser.close();
  }

  const failed = results.filter((item) => item.status === "FAIL");
  const skipped = results.filter((item) => item.status === "NOT_RUN");
  const passed = results.filter((item) => item.status === "PASS");

  const outDir = process.env.WP04_OUTPUT_DIR || join(here, "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "wp04-surfaces.json"), JSON.stringify({
    base: BASE, at: new Date().toISOString(),
    fixtureSource: "tests/wp04/fixtures/explanation-samples.json",
    totals: { total: results.length, passed: passed.length, failed: failed.length,
      notRun: skipped.length },
    results,
  }, null, 2));

  for (const item of results) {
    if (item.status !== "PASS") {
      console.log(`${item.status}  ${item.name}${item.detail ? ` — ${item.detail}` : ""}`);
    }
  }
  console.log(`\n${passed.length} passed, ${failed.length} failed, ${skipped.length} not run`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error("FATAL", error);
  process.exit(2);
});
