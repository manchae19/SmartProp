/**
 * WP-04 B6 — real runtime HTTP validation (no mocks).
 *
 * Talks to a running FastAPI V1.3 and to the same service through the Vite /api/ai proxy, then
 * asserts the explanation contract end to end. Spring Boot / Advisor paths are reported separately
 * because they need an isolated database and are not reachable from this runner.
 *
 *   node tests/wp04/browser/runtime.mjs
 *
 * Env: WP04_AI_BASE (default http://127.0.0.1:8000),
 *      WP04_PROXY_BASE (default http://127.0.0.1:5199/api/ai)
 */
import { mkdirSync, readFileSync, writeFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const AI = process.env.WP04_AI_BASE || "http://127.0.0.1:8000";
const PROXY = process.env.WP04_PROXY_BASE || "http://127.0.0.1:5199/api/ai";
const here = dirname(fileURLToPath(import.meta.url));
const fixtures = JSON.parse(readFileSync(
  join(here, "..", "fixtures", "explanation-samples.json"), "utf8"));

const results = [];
function check(name, ok, detail = "") {
  results.push({ name, ok: Boolean(ok), detail: String(detail).slice(0, 220) });
}

const CASES = {
  HOUSE: { category: "Nhà ở", location_feature: "Cẩm Lệ", area_sqm: 100.0, rooms: 3 },
  LAND: { category: "Đất nền", location_feature: "Cẩm Lệ", area_sqm: 120.0,
    road_width_m: 5.5, frontage_width_m: 6.0 },
  APARTMENT: { category: "Căn hộ chung cư", location_feature: "Hải Châu", area_sqm: 75.0,
    rooms: 2 },
  VILLA: { category: "Nhà ở", location_feature: "Sơn Trà", area_sqm: 150.0,
    house_subtype: "villa", floors: 3, rooms: 4 },
};

async function post(base, path, body) {
  const response = await fetch(`${base}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", Accept: "application/json" },
    body: JSON.stringify(body),
  });
  const text = await response.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* keep raw */ }
  return { status: response.status, json, text };
}

function verifyContract(name, body, expectedPrice) {
  const tag = `${name}`;
  check(`${tag} HTTP 200`, body.json !== null, body.status);
  if (!body.json) return;
  const data = body.json;

  check(`${tag} model_version v1.3`, data.model_version === "v1.3", data.model_version);
  const price = data.predicted_asking_price_vnd;
  check(`${tag} positive integer price`,
    Number.isInteger(price) && price > 0, price);
  check(`${tag} price matches the pinned fixture`, price === expectedPrice,
    `${price} vs ${expectedPrice}`);

  const exp = data.explanation;
  check(`${tag} explanation present`, !!exp);
  if (!exp) return;

  check(`${tag} status AVAILABLE`, exp.status === "AVAILABLE", exp.status);
  check(`${tag} version 1.0`, exp.explanation_version === "1.0", exp.explanation_version);
  check(`${tag} method`, exp.method === "XGBOOST_NATIVE_TREESHAP", exp.method);
  check(`${tag} target`, exp.target === "ASKING_PRICE_VND", exp.target);
  check(`${tag} output space`, exp.output_space === "LOG1P_PRICE_VND", exp.output_space);
  check(`${tag} exactly 6 factors`, Array.isArray(exp.factors) && exp.factors.length === 6,
    exp.factors?.length);
  check(`${tag} 22 provenance features`, Object.keys(exp.feature_provenance || {}).length === 22);
  check(`${tag} calibration policy`, exp.calibration?.policy === "duan_by_band",
    exp.calibration?.policy);
  check(`${tag} calibration price equals the prediction`,
    exp.calibration?.adjusted_price_vnd === price,
    `${exp.calibration?.adjusted_price_vnd} vs ${price}`);
  check(`${tag} base and naive prices present`,
    Number.isFinite(exp.base_price_vnd) && Number.isFinite(exp.naive_price_vnd));

  const topSum = exp.factors.reduce((total, f) => total + f.contribution_log_raw, 0);
  const rebuilt = exp.base_value_log + topSum + exp.other_contribution_log;
  const tolerance = 1e-5 * Math.max(1, Math.abs(exp.predicted_margin_log));
  check(`${tag} additivity within 1e-5`, Math.abs(rebuilt - exp.predicted_margin_log) <= tolerance,
    `${rebuilt} vs ${exp.predicted_margin_log}`);

  const grouped = Object.values(exp.grouped_contributions || {}).reduce((a, b) => a + b, 0);
  check(`${tag} grouped total matches contributions`,
    Math.abs(grouped - (topSum + exp.other_contribution_log)) <= tolerance,
    `${grouped} vs ${topSum + exp.other_contribution_log}`);
}

async function main() {
  let health;
  try {
    health = await fetch(`${AI}/health`).then((r) => r.json());
  } catch (error) {
    check("FastAPI reachable", false, String(error.message || error));
    report();
    return;
  }
  check("FastAPI health ok", health.status === "ok", JSON.stringify(health));
  check("model_version is v1.3", health.model_version === "v1.3", health.model_version);
  check("model_ready true", health.model_ready === true, health.model_ready);

  for (const [name, payload] of Object.entries(CASES)) {
    const expected = fixtures[name].predicted_asking_price_vnd;
    const direct = await post(AI, "/predict", payload);
    verifyContract(`${name} direct`, direct, expected);

    const viaProxy = await post(PROXY, "/predict", payload);
    verifyContract(`${name} via vite proxy`, viaProxy, expected);

    if (direct.json && viaProxy.json) {
      check(`${name} proxy returns the same prediction`,
        direct.json.predicted_asking_price_vnd === viaProxy.json.predicted_asking_price_vnd);
      check(`${name} proxy preserves the explanation contract`,
        JSON.stringify(direct.json.explanation) === JSON.stringify(viaProxy.json.explanation),
        "explanation differs across the proxy");
    }
  }

  // invalid input must be rejected by the real service, not silently valued
  const invalid = await post(AI, "/predict", { category: "Nhà ở", location_feature: "Cẩm Lệ",
    area_sqm: 0 });
  check("invalid numeric input is rejected", invalid.status >= 400, invalid.status);
  const badLocation = await post(AI, "/predict", { category: "Nhà ở",
    location_feature: "Hà Nội", area_sqm: 100 });
  check("unsupported location is rejected", badLocation.status >= 400, badLocation.status);

  report();
}

function report() {
  const failed = results.filter((item) => !item.ok);
  const outDir = join(here, "reports");
  mkdirSync(outDir, { recursive: true });
  writeFileSync(join(outDir, "wp04-runtime.json"), JSON.stringify({
    ai: AI, proxy: PROXY, at: new Date().toISOString(),
    total: results.length, passed: results.length - failed.length, failed: failed.length,
    notRun: [
      { gate: "WP04_REAL_FASTAPI_TOMCAT_PREVIEW_HTTP_PASS",
        reason: "requires an isolated MySQL instance plus Spring Boot; not started in this run" },
      { gate: "WP04_REAL_FASTAPI_TOMCAT_ADVISOR_HTTP_PASS",
        reason: "requires an isolated MySQL instance plus an authenticated synthetic session" },
      { gate: "WP04_RUNTIME_FAILURE_ISOLATION_PASS",
        reason: "partially covered: real 4xx rejections asserted; injected SHAP failure is covered by component tests only" },
    ],
    results,
  }, null, 2));

  for (const item of results) {
    if (!item.ok) console.log(`FAIL  ${item.name} — ${item.detail}`);
  }
  console.log(`\n${results.length - failed.length}/${results.length} runtime checks passed`);
  process.exit(failed.length === 0 ? 0 : 1);
}

main().catch((error) => {
  check("runtime harness crashed", false, String(error.message || error));
  report();
});
