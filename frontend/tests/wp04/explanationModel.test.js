import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import {
  STATUS,
  directionOf,
  formatLog,
  formatVnd,
  summarizeProvenance,
  validateExplanation,
} from "../../src/features/prediction/explanationModel.js";

const here = dirname(fileURLToPath(import.meta.url));
const samples = JSON.parse(
  readFileSync(join(here, "fixtures/explanation-samples.json"), "utf8"),
);

const clone = (value) => JSON.parse(JSON.stringify(value));
const house = () => clone(samples.HOUSE.explanation);

// ---------------------------------------------------------------- 1-5 real payloads
for (const name of ["HOUSE", "LAND", "APARTMENT", "VILLA"]) {
  test(`real ${name} explanation validates as AVAILABLE`, () => {
    const result = validateExplanation(samples[name].explanation);
    assert.equal(result.status, STATUS.AVAILABLE);
    assert.ok(result.view.factors.length > 0);
    assert.equal(result.view.provenance.length, 22, "all 22 features carry provenance");
    assert.equal(result.view.outputSpace, "LOG1P_PRICE_VND");
  });
}

// ---------------------------------------------------------------- 6-8 directions
test("positive and negative contributions keep their signed direction", () => {
  const view = validateExplanation(house()).view;
  const positives = view.factors.filter((factor) => factor.raw > 0);
  const negatives = view.factors.filter((factor) => factor.raw < 0);
  assert.ok(positives.length > 0, "a real payload has at least one positive factor");
  assert.ok(negatives.length > 0, "a real payload has at least one negative factor");
  for (const factor of view.factors) {
    assert.equal(factor.direction, directionOf(factor.raw));
  }
});

test("zero contribution is neutral, not an increase", () => {
  const payload = house();
  const removed = payload.factors[0].contribution_log_raw;
  payload.factors[0].contribution_log_raw = 0;
  payload.factors[0].contribution_log_display = 0;
  // move the removed mass into "other" so the reconstruction stays valid
  payload.other_contribution_log += removed;
  const view = validateExplanation(payload).view;
  assert.ok(view, "a neutral factor must still validate");
  assert.equal(view.factors[0].direction, "neutral");
  assert.equal(view.factors[0].directionLabel, "không đổi");
});

// ---------------------------------------------------------------- 9 reconstruction
test("top-K plus other reconstructs the margin", () => {
  for (const name of ["HOUSE", "LAND", "APARTMENT", "VILLA"]) {
    const view = validateExplanation(samples[name].explanation).view;
    const sum = view.factors.reduce((total, factor) => total + factor.raw, 0);
    const rebuilt = view.base + sum + view.other;
    assert.ok(
      Math.abs(rebuilt - view.margin) <= 1e-5 * Math.max(1, Math.abs(view.margin)),
      `${name} reconstruction failed`,
    );
    assert.equal(view.waterfall.total, rebuilt);
  }
});

test("invalid reconstruction is refused instead of displayed", () => {
  const payload = house();
  payload.other_contribution_log += 0.5; // breaks additivity
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.equal(result.view, null);
  assert.match(result.reason, /kiểm chứng/);
});

// ---------------------------------------------------------------- 10 groups
test("grouped contributions are signed and sorted by magnitude", () => {
  const view = validateExplanation(house()).view;
  assert.ok(view.groups.length > 0);
  for (const group of view.groups) {
    assert.equal(group.direction, directionOf(group.value));
    assert.equal(typeof group.label, "string");
  }
  const magnitudes = view.groups.map((group) => Math.abs(group.value));
  assert.deepEqual(magnitudes, [...magnitudes].sort((a, b) => b - a));
});

// ---------------------------------------------------------------- 11 calibration
test("calibration factor different from 1 is surfaced separately", () => {
  const view = validateExplanation(house()).view;
  assert.notEqual(view.calibration.factor, 1);
  assert.equal(view.calibration.adjustedPriceVnd, samples.HOUSE.predicted_asking_price_vnd);
  assert.ok(view.naivePriceVnd > 0);
});

// ---------------------------------------------------------------- 12 provenance
test("provenance summarisation counts every state once", () => {
  const view = validateExplanation(house()).view;
  const counts = summarizeProvenance(view.provenance);
  const total = Object.values(counts).reduce((sum, value) => sum + value, 0);
  assert.equal(total, 22);
  assert.ok(counts.OBSERVED > 0);
  assert.ok(counts.MISSING || counts.NOT_APPLICABLE || counts.UNKNOWN_CATEGORY);
});

// ---------------------------------------------------------------- 13-14 absent / legacy
test("missing explanation is ABSENT, not an error", () => {
  for (const raw of [null, undefined]) {
    const result = validateExplanation(raw);
    assert.equal(result.status, STATUS.ABSENT);
    assert.equal(result.view, null);
  }
});

test("legacy response without explanation stays usable", () => {
  const legacy = { predicted_asking_price_vnd: 4059447662, shap_explanation: null };
  const result = validateExplanation(legacy.explanation);
  assert.equal(result.status, STATUS.ABSENT);
  assert.ok(legacy.predicted_asking_price_vnd > 0);
});

// ---------------------------------------------------------------- 15-19 statuses
test("PARTIAL keeps the panel usable without factors", () => {
  const payload = house();
  payload.status = "PARTIAL";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.PARTIAL);
  assert.equal(result.view.factors.length, 0);
});

for (const status of ["UNAVAILABLE", "NOT_SUPPORTED"]) {
  test(`${status} shows a reason and no attribution`, () => {
    const payload = house();
    payload.status = status;
    payload.limitations = ["Không tạo được giải thích SHAP (RuntimeError)"];
    const result = validateExplanation(payload);
    assert.equal(result.status, status);
    assert.equal(result.view.factors.length, 0);
    assert.match(result.reason, /SHAP/);
  });
}

test("unknown version is rejected, never upgraded", () => {
  const payload = house();
  payload.explanation_version = "2.0";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /Phiên bản/);
});

test("unknown status is rejected", () => {
  const payload = house();
  payload.status = "PROBABLY_FINE";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
});

test("malformed shapes are rejected", () => {
  for (const raw of ["text", 42, [], { status: "AVAILABLE" }]) {
    const result = validateExplanation(raw);
    assert.equal(result.status, STATUS.INVALID);
  }
});

test("wrong output space is rejected", () => {
  const payload = house();
  payload.output_space = "RAW_VND";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /Không gian đầu ra/);
});

// ---------------------------------------------------------------- 20-21 numerics
test("invalid numeric input is rejected, never replaced by zero", () => {
  for (const bad of ["12", null, Number.NaN, Infinity]) {
    const payload = house();
    payload.factors[0].contribution_log_raw = bad;
    const result = validateExplanation(payload);
    assert.equal(result.status, STATUS.INVALID, `accepted ${String(bad)}`);
  }
});

test("missing nested fields are rejected", () => {
  for (const key of ["calibration", "grouped_contributions", "feature_provenance", "factors"]) {
    const payload = house();
    delete payload[key];
    assert.equal(validateExplanation(payload).status, STATUS.INVALID, `accepted without ${key}`);
  }
});

// ---------------------------------------------------------------- formatting
test("formatting never renders NaN or Infinity", () => {
  for (const value of [Number.NaN, Infinity, -Infinity, undefined, null]) {
    assert.equal(formatVnd(value), "—");
    assert.equal(formatLog(value), "—");
  }
  assert.match(formatVnd(4059447662), /₫/);
});

test("raw contribution is not overwritten by the display value", () => {
  const payload = house();
  payload.factors[0].contribution_log_display = 0.1234;
  const view = validateExplanation(payload).view;
  assert.equal(view.factors[0].raw, payload.factors[0].contribution_log_raw);
  assert.notEqual(view.factors[0].raw, 0.1234);
});
