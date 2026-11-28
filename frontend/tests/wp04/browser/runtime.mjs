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

const AI = process.env.WP04_AI_BASE || "";
const PROXY = process.env.WP04_PROXY_BASE || "";
const TIMEOUT_MS = Number(process.env.WP04_RUNTIME_TIMEOUT_MS || 20000);
const LOOPBACK = /^http:\/\/(127\.0\.0\.1|localhost):\d{2,5}(\/[^\s]*)?$/;

function requireEndpoint(name, value) {
  if (!value) {
    check(`${name} configured`, false, `set ${name} to the isolated loopback base URL`);
    return false;
  }
  if (!LOOPBACK.test(value)) {
    check(`${name} is loopback`, false, `${name} must be an explicit 127.0.0.1 origin`);
    return false;
  }
  return true;
}
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
    signal: AbortSignal.timeout(TIMEOUT_MS),
  });
  const text = await response.text();
  let json = null;
  try { json = JSON.parse(text); } catch { /* keep raw */ }
  return { status: response.status, json, text };
}

function verifyContract(name, body, expectedPrice) {
  const tag = `${name}`;
  check(`${tag} HTTP 200`, body.status === 200 && body.json !== null, `status ${body.status}`);
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
  const PROVENANCE_KEYS = ["area", "frontage_sqrt_area_ratio", "floor_count", "bedroom_count",
    "bathroom_count", "has_floor", "has_bedroom", "has_bathroom", "frontage_width", "road_width",
    "has_frontage", "has_road_width", "has_project", "raw_project_name", "has_street", "has_ward",
    "district", "ward", "raw_street_name", "normalized_type", "raw_house_direction",
    "raw_balcony_direction"];
  const provenanceKeys = Object.keys(exp.feature_provenance || {}).sort();
  check(`${tag} exact 22 provenance identities`,
    provenanceKeys.length === PROVENANCE_KEYS.length
      && provenanceKeys.every((key, index) => key === [...PROVENANCE_KEYS].sort()[index]),
    provenanceKeys.join(","));
  const knownStates = ["OBSERVED", "DERIVED", "DEFAULTED", "MISSING", "MISSING_INVALID",
    "NOT_APPLICABLE", "UNKNOWN_CATEGORY", "UNVERIFIED"];
  check(`${tag} every provenance state is recognised`,
    Object.values(exp.feature_provenance || {}).every((state) => knownStates.includes(state)));
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
  const aiOk = requireEndpoint("WP04_AI_BASE", AI);
  const proxyOk = requireEndpoint("WP04_PROXY_BASE", PROXY);
  if (!aiOk || !proxyOk) { report(); return; }
  let health;
  try {
    health = await fetch(`${AI}/health`, { signal: AbortSignal.timeout(TIMEOUT_MS) })
      .then((r) => r.json());
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
      // structural equality of the decoded JSON; raw bytes may legitimately differ
      const structural = (value) => JSON.stringify(value, Object.keys(value || {}).sort());
      check(`${name} proxy preserves the explanation structurally`,
        JSON.stringify(direct.json.explanation) === JSON.stringify(viaProxy.json.explanation),
        "decoded explanation differs across the proxy");
      void structural;
    }
  }

  // invalid input must be rejected by the real service, not silently valued
  const invalid = await post(AI, "/predict", { category: "Nhà ở", location_feature: "Cẩm Lệ",
    area_sqm: 0 });
  check("invalid numeric input is rejected with 4xx",
    invalid.status >= 400 && invalid.status < 500, `status ${invalid.status}`);
  const badLocation = await post(AI, "/predict", { category: "Nhà ở",
    location_feature: "Hà Nội", area_sqm: 100 });
  check("unsupported location is rejected with 4xx",
    badLocation.status >= 400 && badLocation.status < 500, `status ${badLocation.status}`);

  report();
}

function report() {
  const failed = results.filter((item) => !item.ok);
  const outDir = process.env.WP04_OUTPUT_DIR || join(here, "reports");
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
