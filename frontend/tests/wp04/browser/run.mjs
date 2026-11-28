/**
 * WP-04 B4/B5 — true-viewport browser validation.
 *
 * Runs the real component through Chromium with a real CSS viewport (Playwright sets the viewport,
 * so there is no headless minimum-width clamp). Each scenario opens the technical section *before*
 * measuring, then checks geometry with ranges, computed styles and nonzero dimensions — never
 * document.scrollWidth alone.
 *
 *   node tests/wp04/browser/run.mjs            # all cases at all widths
 *   node tests/wp04/browser/run.mjs --case=missing --width=390
 *
 * Requires a dev server (same CSS pipeline as production) and no new dependency: Playwright is
 * loaded from the workspace copy and launched against the installed system Chrome.
 */
import { mkdirSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const PLAYWRIGHT = process.env.PLAYWRIGHT_PATH
  || "F:/SmartProp/frontend/vue.ui/node_modules/playwright";
const CHROME = process.env.CHROME
  || "C:/Program Files/Google/Chrome/Application/chrome.exe";
const BASE = process.env.WP04_HARNESS || "http://127.0.0.1:5199/tests/wp04/harness/";

const CASES = ["house", "land", "apartment", "villa", "missing", "unverified",
  "partial", "unavailable", "not-supported", "legacy", "malformed"];
const WIDTHS = [320, 390, 768, 1440];

const here = dirname(fileURLToPath(import.meta.url));
const results = [];
const shots = process.env.WP04_OUTPUT_DIR || join(here, "..", "..", "..", "docs", "ai", "browser", "wp04");

function record(name, ok, detail = "") {
  results.push({ name, ok: Boolean(ok), detail: String(detail).slice(0, 220) });
}

/** Geometry probe executed in the page after the technical section is open. */
function probe() {
  const section = document.querySelector('[data-testid="valuation-explanation-panel"]');
  if (!section) return { error: "panel missing" };
  const sectionRect = section.getBoundingClientRect();
  const within = (rect) => rect.width > 0
    && rect.right <= sectionRect.right + 1
    && rect.left >= sectionRect.left - 1;

  const boxes = (selector) => Array.from(document.querySelectorAll(selector)).map((node) => {
    const rect = node.getBoundingClientRect();
    const style = getComputedStyle(node);
    return {
      text: (node.textContent || "").trim().slice(0, 40),
      width: Math.round(rect.width),
      height: Math.round(rect.height),
      visible: style.display !== "none" && style.visibility !== "hidden"
        && rect.width > 0 && rect.height > 0,
      inside: within(rect),
    };
  });

  const textOverflow = Array.from(section.querySelectorAll("p, li, td, th, dd, dt, span"))
    .filter((node) => node.childNodes.length === 1 && node.firstChild.nodeType === 3)
    .map((node) => {
      const range = document.createRange();
      range.selectNodeContents(node);
      const rect = range.getBoundingClientRect();
      return {
        text: (node.textContent || "").trim().slice(0, 40),
        right: Math.round(rect.right),
        clipped: rect.right > sectionRect.right + 1,
      };
    })
    .filter((item) => item.text.length > 0);

  const summary = section.querySelector("summary");
  let focusVisible = null;
  if (summary) {
    const active = document.activeElement;
    const style = active ? getComputedStyle(active) : null;
    focusVisible = active === summary
      && summary.matches(":focus-visible")
      && style !== null
      && (style.outlineStyle !== "none" || style.boxShadow !== "none" || style.outlineWidth !== "0px");
  }

  return {
    viewportWidth: window.innerWidth,
    sectionWidth: Math.round(sectionRect.width),
    sectionScrollWidth: section.scrollWidth,
    docScrollWidth: document.documentElement.scrollWidth,
    docClientWidth: document.documentElement.clientWidth,
    status: section.dataset.explanationStatus,
    groups: boxes("[data-direction]"),
    provenance: boxes("[data-provenance]"),
    waterfallRows: boxes("[data-testid='explanation-waterfall'] tr"),
    calibration: boxes("[data-testid='explanation-calibration'] dd"),
    waterfallSvg: boxes("[data-testid='explanation-waterfall-svg']").length,
    clippedText: textOverflow.filter((item) => item.clipped),
    focusVisible,
    jsError: Boolean(document.querySelector("[data-js-error]")),
    bodyHasNaN: /NaN|Infinity/.test(document.body.innerText || ""),
  };
}

async function runCase(browser, name, width) {
  const page = await browser.newPage({ viewport: { width, height: 1200 } });
  try {
    await page.goto(`${BASE}?case=${name}`, { waitUntil: "domcontentloaded" });
    await page.waitForSelector('[data-testid="valuation-explanation-panel"]', { timeout: 8000 });
    await page.waitForFunction(() => document.documentElement.dataset.rendered === "true");

    // open the technical section first: measuring a collapsed panel proved nothing before
    const summary = page.locator("summary");
    if (await summary.count()) {
      await summary.first().click();
      await page.waitForTimeout(250);
    }
    await page.evaluate(() => document.fonts?.ready);

    // reach the disclosure control with the keyboard so :focus-visible applies
    await page.keyboard.press("Tab");
    for (let step = 0; step < 25; step += 1) {
      const onSummary = await page.evaluate(() => document.activeElement?.tagName === "SUMMARY");
      if (onSummary) break;
      await page.keyboard.press("Tab");
    }
    await page.waitForTimeout(120);

    const p = await page.evaluate(probe);
    const tag = `${name}@${width}`;

    if (p.error) {
      record(`${tag} panel renders`, false, p.error);
      return;
    }
    record(`${tag} real viewport applied`, p.viewportWidth === width, `${p.viewportWidth}`);
    record(`${tag} no document overflow`, p.docScrollWidth <= p.docClientWidth + 1,
      `${p.docScrollWidth}/${p.docClientWidth}`);
    record(`${tag} section does not scroll internally`, p.sectionScrollWidth <= p.sectionWidth + 1,
      `${p.sectionScrollWidth}/${p.sectionWidth}`);
    record(`${tag} no clipped text`, p.clippedText.length === 0,
      p.clippedText.map((item) => item.text).join(" | "));
    record(`${tag} no JS error`, !p.jsError);
    record(`${tag} no NaN/Infinity`, !p.bodyHasNaN);

    const available = ["house", "land", "apartment", "villa", "missing", "unverified"]
      .includes(name);
    if (available) {
      record(`${tag} status is AVAILABLE`, p.status === "AVAILABLE", p.status);
      record(`${tag} 22 provenance rows`, p.provenance.length === 22, p.provenance.length);
      record(`${tag} provenance rows visible and inside`,
        p.provenance.every((row) => row.visible && row.inside),
        p.provenance.filter((row) => !row.visible || !row.inside).length);
      record(`${tag} group values visible and inside`,
        p.groups.length > 0 && p.groups.every((row) => row.visible && row.inside),
        p.groups.length);
      record(`${tag} waterfall rows visible`, p.waterfallRows.length >= 4, p.waterfallRows.length);
      record(`${tag} waterfall svg rendered`, p.waterfallSvg === 1, p.waterfallSvg);
      record(`${tag} calibration values visible`,
        p.calibration.length >= 4 && p.calibration.every((row) => row.visible && row.inside),
        p.calibration.length);
      record(`${tag} keyboard focus is visible`, p.focusVisible === true, p.focusVisible);
    } else if (name === "partial") {
      record(`${tag} status is PARTIAL`, p.status === "PARTIAL", p.status);
    } else if (name === "unavailable") {
      record(`${tag} status is UNAVAILABLE`, p.status === "UNAVAILABLE", p.status);
      record(`${tag} no waterfall for unavailable`, p.waterfallRows.length === 0,
        p.waterfallRows.length);
    } else if (name === "not-supported") {
      record(`${tag} status is NOT_SUPPORTED`, p.status === "NOT_SUPPORTED", p.status);
    } else if (name === "legacy") {
      record(`${tag} status is ABSENT`, p.status === "ABSENT", p.status);
    } else if (name === "malformed") {
      record(`${tag} status is INVALID`, p.status === "INVALID", p.status);
      record(`${tag} no fabricated waterfall`, p.waterfallRows.length === 0, p.waterfallRows.length);
    }

    if (width === 390 && ["house", "missing", "unavailable", "malformed"].includes(name)) {
      mkdirSync(shots, { recursive: true });
      await page.screenshot({ path: join(shots, `panel-${name}-390.png`) });
    }
  } finally {
    await page.close();
  }
}

async function main() {
  const caseArg = process.argv.find((a) => a.startsWith("--case="));
  const widthArg = process.argv.find((a) => a.startsWith("--width="));
  const cases = caseArg ? [caseArg.split("=")[1]] : CASES;
  const widths = widthArg ? [Number(widthArg.split("=")[1])] : WIDTHS;

  const require = createRequire(import.meta.url);
  const playwright = require(PLAYWRIGHT);
  const browser = await playwright.chromium.launch({ headless: true, executablePath: CHROME });

  try {
    for (const name of cases) {
      for (const width of widths) {
        try {
          await runCase(browser, name, width);
        } catch (error) {
          record(`${name}@${width} crashed`, false, String(error.message || error).slice(0, 160));
        }
      }
    }
  } finally {
    await browser.close();
  }

  const failed = results.filter((item) => !item.ok);
  const outDir = process.env.WP04_OUTPUT_DIR || join(here, "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "wp04-browser.json"), JSON.stringify({
    base: BASE, at: new Date().toISOString(), cases, widths,
    total: results.length, passed: results.length - failed.length, failed: failed.length,
    results,
  }, null, 2));

  for (const item of results) {
    if (!item.ok) console.log(`FAIL  ${item.name} — ${item.detail}`);
  }
  console.log(`\n${results.length - failed.length}/${results.length} checks passed`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  console.error("FATAL", error);
  process.exit(2);
});
