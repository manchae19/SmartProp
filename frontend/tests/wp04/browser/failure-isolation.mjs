import assert from "node:assert/strict";
import { readFileSync, writeFileSync } from "node:fs";
import { createRequire } from "node:module";
import { join } from "node:path";
import {
  advisorPath, deferred, matches, predictPath, prepareAdvisor, preparePosting, prepareStandalone,
  previewPath, waitResponse,
} from "./workflows.mjs";

const APP = process.env.WP04_APP;
const AI = process.env.WP04_AI;
const RUNTIME = process.env.WP04_RUNTIME_FILE;
const EMAIL = process.env.WP04_FIXTURE_EMAIL;
const PASSWORD = process.env.WP04_FIXTURE_PASSWORD;
const require = createRequire(import.meta.url);
const { chromium } = require(process.env.PLAYWRIGHT_PATH || "playwright");
const results = [];
const statusPanel = (scope) => scope.getByTestId("valuation-explanation-panel");
const valuationResult = (page) => page.getByTestId("valuation-result");
const format = (digits) => new Intl.NumberFormat("vi-VN").format(BigInt(digits));

function proofPrice(value) {
  const digits = String(value).replace(/\.0+$/, "");
  assert.match(digits, /^[1-9]\d*$/, "Expected positive authoritative price");
  return digits;
}

async function assertStandalonePrice(page, payload) {
  const result = valuationResult(page);
  await result.waitFor();
  const digits = proofPrice(payload.predicted_asking_price_vnd);
  const billions = BigInt(digits) >= 1000000000n;
  const short = new Intl.NumberFormat("vi-VN", { maximumFractionDigits: 2 })
    .format(Number(digits) / (billions ? 1e9 : 1e6)) + (billions ? " tỷ đồng" : " triệu đồng");
  assert.equal(await result.getByTestId("estimated-price").innerText(), short);
  await result.getByText(format(digits) + " đồng · Tổng giá bất động sản", { exact: true }).waitFor();
}

async function assertPanel(scope, status) {
  const panel = statusPanel(scope);
  await panel.waitFor();
  assert.equal(await panel.getAttribute("data-explanation-status"), status);
  if (status !== "AVAILABLE") {
    assert.equal(await panel.locator("[data-row^='step-'], [data-provenance]").count(), 0);
    assert.equal(await panel.getByTestId("explanation-waterfall").count(), 0);
    assert.equal(await panel.getByTestId("explanation-waterfall-svg").count(), 0);
    return;
  }
  await panel.locator("summary").click();
  await panel.getByTestId("explanation-waterfall-svg").waitFor();
  assert.equal(await panel.locator("[data-row^='step-']").count(), 6);
}

function assertPredictionInput(data, area) {
  assert.equal(data.category, "Nhà ở");
  assert.equal(data.location_feature.toLocaleLowerCase("vi"), "cẩm lệ");
  assert.equal(data.area_sqm, area);
}

async function onlyPost(page, path, handle) {
  const requests = [];
  await page.route("**" + path, async (route) => {
    if (route.request().method() !== "POST") return route.continue();
    requests.push(route.request().postDataJSON());
    await handle(route);
  });
  return requests;
}

function unavailable(explanation) {
  return { explanation_version: explanation.explanation_version, status: "UNAVAILABLE",
    limitations: ["Fixture explanation unavailable"] };
}

function record(name, classification, detail = "") {
  results.push({ name, classification, ok: !detail, detail });
  console.log((detail ? "FAIL " : "PASS ") + name + (detail ? " — " + detail : ""));
}

async function scenario(browser, name, classification, run) {
  const page = await browser.newPage({ viewport: { width: 1280, height: 1100 } });
  try {
    const value = await run(page);
    record(name, classification);
    return value;
  } catch (error) {
    record(name, classification, String(error.message).split("\n")[0]);
  } finally {
    await page.close();
  }
}

async function standalone(page, expected, override) {
  const calls = await onlyPost(page, predictPath, override
    ? (route) => route.fulfill({ status: 200, json: override })
    : (route) => route.continue());
  const submit = await prepareStandalone(page, APP);
  const response = waitResponse(page, predictPath);
  await submit.click();
  const reply = await response;
  assert.equal(reply.status(), 200);
  const payload = await reply.json();
  assert.equal(payload.model_version, "v1.3");
  assert.deepEqual(calls.length, 1);
  assertPredictionInput(calls[0], 100);
  if (override) assert.deepEqual(payload, override);
  await assertStandalonePrice(page, payload);
  await assertPanel(valuationResult(page), expected);
  return payload;
}

async function stale(page) {
  const arrived = deferred();
  const released = deferred();
  const drained = deferred();
  const calls = await onlyPost(page, predictPath, async (route) => {
    if (route.request().postDataJSON().area_sqm !== 100) return route.continue();
    const real = await route.fetch();
    arrived.resolve(real);
    try {
      await released.promise;
      await route.fulfill({ response: real });
      drained.resolve(null);
    } catch (error) {
      drained.resolve(error);
    }
  });
  try {
    const submit = await prepareStandalone(page, APP);
    await submit.click();
    const old = await Promise.race([arrived.promise, new Promise((_, reject) => {
      AbortSignal.timeout(30000).addEventListener("abort", () => reject(Error("First predict request was not intercepted")), { once: true });
    })]);
    assert.equal(old.status(), 200);
    const oldPayload = await old.json();
    await page.getByPlaceholder("Ví dụ: 80").first().fill("110");
    released.resolve();
    const discharge = await drained.promise;
    if (discharge) assert.match(String(discharge), /abort|handled|closed|request/i);
    await page.evaluate(() => new Promise((resolve) => requestAnimationFrame(() => requestAnimationFrame(resolve))));
    assert.equal(await valuationResult(page).count(), 0, "Obsolete prediction appeared after the edit");
    assert.equal(await page.getByTestId("estimated-price").count(), 0);
    const current = waitResponse(page, predictPath);
    await submit.click();
    const reply = await current;
    assert.equal(reply.status(), 200);
    assert.equal(calls.length, 2);
    assertPredictionInput(calls[0], 100);
    assertPredictionInput(calls[1], 110);
    const payload = await reply.json();
    assert.notEqual(payload.predicted_asking_price_vnd, oldPayload.predicted_asking_price_vnd);
    await assertStandalonePrice(page, payload);
    await assertPanel(valuationResult(page), "AVAILABLE");
  } finally {
    released.resolve();
  }
}

async function posting(page) {
  const calls = await onlyPost(page, previewPath, async (route) => {
    const real = await route.fetch();
    const payload = await real.json();
    payload.explanation = { status: "AVAILABLE", factors: [] };
    await route.fulfill({ response: real, json: payload });
  });
  const submit = await preparePosting(page, APP, EMAIL, PASSWORD);
  const response = waitResponse(page, previewPath);
  await submit.click();
  const reply = await response;
  assert.equal(reply.status(), 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].areaSqm, 80);
  const payload = await reply.json();
  assert.equal(payload.available, true);
  assert.equal(payload.modelVersion, "v1.3");
  await page.getByText(format(proofPrice(payload.predictedAskingPriceVnd)) + " ₫", {
    exact: true,
  }).and(page.getByTestId("valuation-price")).waitFor();
  assert.equal(await page.locator("#post-price").inputValue(), "5000000000");
  await assertPanel(page.getByTestId("valuation-panel"), "INVALID");
}

async function advisor(page) {
  const calls = await onlyPost(page, advisorPath, async (route) => {
    const real = await route.fetch();
    const payload = await real.json();
    for (const item of payload.recommendedProperties ?? []) {
      if (item.valuationEvidence?.available) {
        item.valuationEvidence.explanation = unavailable(item.valuationEvidence.explanation);
      }
    }
    await route.fulfill({ response: real, json: payload });
  });
  const submit = await prepareAdvisor(page, APP);
  const response = waitResponse(page, advisorPath);
  await submit.click();
  const reply = await response;
  assert.equal(reply.status(), 200);
  assert.equal(calls.length, 1);
  assert.equal(calls[0].propertyType, "HOUSE");
  assert.notEqual(calls[0].includeResearch, true);
  const payload = await reply.json();
  assert.equal(payload.mode, "SAFE");
  const index = payload.recommendedProperties.findIndex((item) => item.valuationEvidence?.available
    && item.comparableEvidence?.candidateCount > 0 && item.valuationComparableEvidence?.candidateCount > 0);
  assert.ok(index >= 0, "Expected one recommendation with valuation and both Comparable sections");
  const item = payload.recommendedProperties[index];
  const property = page.locator("[data-advisor-property]").nth(index);
  await property.getByText(item.title, { exact: true }).first().waitFor();
  const evidence = property.locator("[data-advisor-evidence]");
  assert.equal(await evidence.locator(".ev-price").getAttribute("title"),
    format(proofPrice(item.valuationEvidence.predictedAskingPriceVnd)) + " ₫");
  await evidence.getByText("Tin tương đồng theo giá rao", { exact: true }).waitFor();
  await evidence.getByText("Đối chiếu định giá bằng tin đăng", { exact: true }).waitFor();
  assert.equal(await evidence.locator("[data-comparable-evidence]").count(), 2);
  await assertPanel(evidence, "UNAVAILABLE");
}

function runtime() {
  const state = JSON.parse(readFileSync(RUNTIME, "utf8"));
  assert.equal(state.stack.react, APP);
  assert.equal(state.stack.valuation, AI);
  assert.match(state.root, /[\\/]wp04-owned-[^\\/]+$/);
  return state;
}

async function runtimeState(state) {
  const deadline = Date.now() + 60000;
  do {
    const current = runtime();
    assert.notEqual(current.state, "failed");
    if (current.state === state) return current;
    await new Promise((resolve) => setTimeout(resolve, 100));
  } while (Date.now() < deadline);
  throw Error("Expected owned fixture state " + state);
}

async function outage(page) {
  const submit = await prepareStandalone(page, APP);
  const before = runtime();
  assert.equal(before.state, "ready");
  writeFileSync(join(before.root, "PAUSE_VALUATION"), "", { flag: "wx" });
  try {
    await runtimeState("valuation-offline");
    await assert.rejects(fetch(AI + "/model/options", { signal: AbortSignal.timeout(4000) }));
    const response = waitResponse(page, predictPath);
    await submit.click();
    assert.ok((await response).status() >= 500);
    await page.getByRole("alert").waitFor();
    assert.equal(await valuationResult(page).count(), 0);
    assert.equal(await page.getByTestId("estimated-price").count(), 0);

    const advisorSubmit = await prepareAdvisor(page, APP);
    const partialReply = waitResponse(page, advisorPath);
    await advisorSubmit.click();
    const reply = await partialReply;
    assert.equal(reply.status(), 200);
    const partial = await reply.json();
    assert.equal(partial.mode, "SAFE");
    assert.equal(partial.serviceStatus.valuationService, "UNAVAILABLE");
    assert.equal(partial.serviceStatus.partialResult, true);
    assert.ok(partial.recommendedProperties.length > 0);
    assert.ok(partial.recommendedProperties.every((item) => !item.valuationEvidence?.available
      && item.valuationEvidence?.predictedAskingPriceVnd == null));
    await page.locator("[data-advisor-property]").first().waitFor();
    assert.equal(await page.locator("[data-valuation-evidence]").count(), 0);
  } finally {
    writeFileSync(join(before.root, "RESTORE_VALUATION"), "", { flag: "wx" });
    const recovered = await runtimeState("valuation-recovered");
    assert.notEqual(recovered.pids.valuation_recovered, before.pids.valuation.pid);
  }
  await standalone(page, "AVAILABLE");
}

async function main() {
  assert.match(APP, /^http:\/\/127\.0\.0\.1:\d{5}$/);
  const browser = await chromium.launch({ headless: true, executablePath: process.env.CHROME });
  try {
    const baseline = await scenario(browser, "unmodified real V1.3 positive control", "REAL_HTTP",
      (page) => standalone(page, "AVAILABLE"));
    assert.ok(baseline, "Positive control is required to construct mutation cases");
    const mutations = [
      ["missing explanation", "ABSENT", (p) => delete p.explanation],
      ["unavailable explanation", "UNAVAILABLE", (p) => { p.explanation = unavailable(p.explanation); }],
      ["malformed explanation", "INVALID", (p) => { p.explanation = { status: "AVAILABLE", factors: [] }; }],
      ["invalid adjusted price", "INVALID", (p) => { p.explanation.calibration.adjusted_price_vnd = 0; }],
      ["one-VND mismatch", "INCONSISTENT", (p) => { p.explanation.calibration.adjusted_price_vnd =
        Number(p.explanation.calibration.adjusted_price_vnd) + 1; }],
      ["reconstruction mismatch", "INVALID", (p) => { p.explanation.predicted_margin_log += 0.5; }],
    ];
    for (const [name, expected, mutate] of mutations) {
      const payload = structuredClone(baseline);
      mutate(payload);
      await scenario(browser, "standalone: " + name + " -> " + expected, "MOCKED_RESPONSE",
        (page) => standalone(page, expected, payload));
    }
    await scenario(browser, "stale prediction discarded after input edit", "HELD_REAL_RESPONSE", stale);
    await scenario(browser, "posting: invalid explanation preserves authoritative preview", "MOCKED_RESPONSE", posting);
    await scenario(browser, "Advisor: unavailable explanation preserves recommendation and both Comparable sections",
      "MOCKED_RESPONSE", advisor);
    await scenario(browser, "owned FastAPI outage, no fabricated price, and recovery", "REAL_PROCESS_OUTAGE", outage);
  } finally {
    await browser.close();
    writeFileSync(process.env.WP04_FAILURE_REPORT, JSON.stringify(results, null, 2) + "\n");
    process.exitCode = results.length === 11 && results.every((item) => item.ok) ? 0 : 1;
  }
}

main().catch((error) => { console.error(error.message); process.exitCode = 1; });
