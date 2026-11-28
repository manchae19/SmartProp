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
  const group = payload.factors[0].group;
  payload.factors[0].contribution_log_raw = 0;
  payload.factors[0].contribution_log_display = 0;
  payload.factors[0].direction = "NEUTRAL";
  payload.factors[0].multiplicative_factor = 1;
  // "other" absorbs the removed mass, so group totals and additivity stay consistent
  payload.other_contribution_log += removed;
  void group;
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
  // shifting the margin alone leaves groups and contributions self-consistent, so this exercises
  // the additivity check rather than the group-total check
  payload.predicted_margin_log += 0.5;
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.equal(result.view, null);
  assert.match(result.reason, /kiểm chứng/);
});

test("breaking the group totals is refused with the group rule", () => {
  const payload = house();
  payload.other_contribution_log += 0.5;
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /Tổng theo nhóm/);
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

// ---------------------------------------------------------------- provenance identity
test("all 22 provenance rows carry a feature label and a state label", () => {
  const view = validateExplanation(house()).view;
  assert.equal(view.provenance.length, 22);
  const names = view.provenance.map((item) => item.featureName);
  assert.equal(new Set(names).size, 22, "each feature appears exactly once");
  for (const item of view.provenance) {
    assert.ok(item.featureLabel, `missing feature label for ${item.featureName}`);
    assert.ok(item.stateLabel, `missing state label for ${item.featureName}`);
    assert.notEqual(item.featureLabel, item.stateLabel);
  }
  const area = view.provenance.find((item) => item.featureName === "area");
  assert.equal(area.featureLabel, "Diện tích");
  assert.equal(area.stateLabel, "Bạn đã cung cấp");
});

test("derived indicators read as system-computed, not as physical observations", () => {
  const view = validateExplanation(house()).view;
  const indicator = view.provenance.find((item) => item.featureName === "has_frontage");
  assert.ok(indicator);
  assert.equal(indicator.state, "DERIVED");
  assert.match(indicator.stateLabel, /Hệ thống tính ra|Chưa cung cấp|Không áp dụng/);
  assert.match(indicator.note, /không phải thông tin xác minh trực tiếp/);
});

test("UNVERIFIED appears in the flagged list and the summary", () => {
  const payload = house();
  payload.feature_provenance.ward = "UNVERIFIED";
  const factor = payload.factors.find((item) => item.feature_name === "ward");
  if (factor) factor.input_state = "UNVERIFIED";
  const view = validateExplanation(payload).view;
  assert.ok(view, "explanation should still validate");
  assert.ok(view.flagged.some((item) => item.state === "UNVERIFIED"));
  assert.ok(summarizeProvenance(view.provenance).UNVERIFIED >= 1);
});

test("missing provenance entries are rejected instead of invented", () => {
  const payload = house();
  delete payload.feature_provenance.ward;
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /Nguồn gốc/);
});

test("unknown feature name and duplicated factor are rejected", () => {
  const unknown = house();
  unknown.factors[0].feature_name = "not_a_feature";
  assert.equal(validateExplanation(unknown).status, STATUS.INVALID);

  const duplicate = house();
  duplicate.factors[1].feature_name = duplicate.factors[0].feature_name;
  const result = validateExplanation(duplicate);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /lặp/);
});

test("wrong method, target or output space is rejected", () => {
  for (const [field, value] of [["method", "SHAP_LINEAR"], ["target", "RENT_VND"],
    ["output_space", "RAW_VND"]]) {
    const payload = house();
    payload[field] = value;
    assert.equal(validateExplanation(payload).status, STATUS.INVALID, field);
  }
});

test("internal statuses are never accepted from upstream", () => {
  for (const status of ["ABSENT", "INVALID", ""]) {
    const payload = house();
    payload.status = status;
    assert.equal(validateExplanation(payload).status, STATUS.INVALID, status);
  }
});

test("malformed group values are rejected, not dropped", () => {
  const payload = house();
  payload.grouped_contributions.AREA = "n/a";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /nhóm/);
});

test("unknown group key is rejected", () => {
  const payload = house();
  payload.grouped_contributions.MYSTERY = 1;
  assert.equal(validateExplanation(payload).status, STATUS.INVALID);
});

test("calibration price mismatch is surfaced, not silently accepted", () => {
  const payload = house();
  const view = validateExplanation(payload, { priceVnd: 1 }).view;
  assert.ok(view);
  assert.equal(view.priceConsistent, false);
  const ok = validateExplanation(payload, {
    priceVnd: payload.calibration.adjusted_price_vnd,
  }).view;
  assert.equal(ok.priceConsistent, true);
});

// ---------------------------------------------------------------- exact V1.3 contract
test("exactly six factors are required for AVAILABLE", () => {
  const short = house();
  short.factors = short.factors.slice(0, 5);
  const result = validateExplanation(short);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /đúng 6 yếu tố/);
});

test("base and naive prices are mandatory", () => {
  for (const field of ["base_price_vnd", "naive_price_vnd"]) {
    const payload = house();
    delete payload[field];
    assert.equal(validateExplanation(payload).status, STATUS.INVALID, field);
  }
  const missingAdjusted = house();
  delete missingAdjusted.calibration.adjusted_price_vnd;
  assert.equal(validateExplanation(missingAdjusted).status, STATUS.INVALID);
});

test("unsupported calibration policy is rejected", () => {
  const payload = house();
  payload.calibration.policy = "magic_factor";
  const result = validateExplanation(payload);
  assert.equal(result.status, STATUS.INVALID);
  assert.match(result.reason, /Chính sách/);
});

test("non-finite intermediate sums are rejected", () => {
  const payload = house();
  payload.grouped_contributions.AREA = Infinity;
  assert.equal(validateExplanation(payload).status, STATUS.INVALID);
});
