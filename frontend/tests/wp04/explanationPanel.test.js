import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { renderToStaticMarkup } from "react-dom/server";

import { ValuationExplanationPanel } from "../../src/features/prediction/ValuationExplanationPanel.js";

const here = dirname(fileURLToPath(import.meta.url));
const samples = JSON.parse(
  readFileSync(join(here, "fixtures/explanation-samples.json"), "utf8"),
);

const clone = (value) => JSON.parse(JSON.stringify(value));
const render = (props) => renderToStaticMarkup(ValuationExplanationPanel(props));

// ---------------------------------------------------------------- 1-5 real payloads
for (const name of ["HOUSE", "LAND", "APARTMENT", "VILLA"]) {
  test(`renders real ${name} explanation`, () => {
    const html = render({
      explanation: samples[name].explanation,
      predictedPriceVnd: samples[name].predicted_asking_price_vnd,
      modelVersion: "v1.3",
    });
    assert.match(html, /data-explanation-status="AVAILABLE"/);
    assert.match(html, /Giải thích đầy đủ/);
    assert.match(html, /data-testid="explanation-price"/);
    assert.match(html, /Giá rao bán ước tính/);
    assert.match(html, /data-testid="explanation-groups"/);
    assert.match(html, /data-testid="explanation-provenance-summary"|Nguồn dữ liệu/);
    assert.doesNotMatch(html, /NaN|Infinity|undefined/);
  });
}

// ---------------------------------------------------------------- 10 groups + directions
test("groups render label, arrow and signed value (not colour only)", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.match(html, /data-group="AREA"/);
  assert.match(html, /(↑|↓|•)\s-?\d/);
  assert.match(html, /Diện tích|Vị trí|Kết cấu/);
});

// ---------------------------------------------------------------- 9 waterfall + 23 details
test("technical section is collapsed by default and keyboard accessible", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.match(html, /<details[^>]*data-testid="explanation-technical"/);
  assert.doesNotMatch(html, /<details[^>]*\sopen/, "technical section starts collapsed");
  assert.match(html, /<summary[^>]*>/);
  assert.match(html, /LOG1P_PRICE_VND/);
  assert.match(html, /data-testid="explanation-waterfall"/);
  assert.match(html, /không phải VNĐ/);
});

test("waterfall contains base, factors, other and margin rows", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  for (const row of ["base", "other", "total", "margin"]) {
    assert.match(html, new RegExp(`data-row="${row}"`));
  }
  assert.match(html, /data-row="step-/);
});

// ---------------------------------------------------------------- 11 calibration bridge
test("calibration bridge is separate from the SHAP waterfall", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.match(html, /data-testid="explanation-calibration"/);
  assert.match(html, /Hệ số hiệu chỉnh/);
  assert.match(html, /không phải một đóng góp SHAP/);
});

// ---------------------------------------------------------------- 13 absent
test("absent explanation keeps the price visible", () => {
  const html = render({ explanation: null, predictedPriceVnd: 4059447662 });
  assert.match(html, /data-explanation-status="ABSENT"/);
  assert.match(html, /Không có phần giải thích/);
  assert.match(html, /4,06 tỷ|4\.06 tỷ/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});

// ---------------------------------------------------------------- 14 legacy
test("legacy valuation without explanation still renders", () => {
  // A legacy response simply has no `explanation` field at all.
  const html = render({ explanation: undefined, predictedPriceVnd: 4059447662 });
  assert.match(html, /data-explanation-status="ABSENT"/);
  assert.match(html, /4059447662|4,06 tỷ/);
  assert.doesNotMatch(html, /impact_pct|% giá/);
});

// ---------------------------------------------------------------- 15-17 statuses
test("PARTIAL renders a partial notice without fabricated factors", () => {
  const payload = clone(samples.HOUSE.explanation);
  payload.status = "PARTIAL";
  const html = render({ explanation: payload, predictedPriceVnd: 4059447662 });
  assert.match(html, /data-explanation-status="PARTIAL"/);
  assert.match(html, /data-testid="explanation-partial"/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});

for (const status of ["UNAVAILABLE", "NOT_SUPPORTED"]) {
  test(`${status} state is explicit and keeps the price`, () => {
    const payload = clone(samples.HOUSE.explanation);
    payload.status = status;
    payload.limitations = ["Không tạo được giải thích SHAP (RuntimeError)"];
    const html = render({ explanation: payload, predictedPriceVnd: 4059447662 });
    assert.match(html, new RegExp(`data-explanation-status="${status}"`));
    assert.match(html, /data-testid="explanation-unavailable"/);
    assert.match(html, /Giá dự đoán vẫn có hiệu lực/);
    assert.doesNotMatch(html, /data-testid="explanation-groups"/);
  });
}

// ---------------------------------------------------------------- 18-21 invalid
test("malformed or unsupported explanation is isolated, never fabricated", () => {
  const cases = [
    "text",
    42,
    [],
    { status: "AVAILABLE" },
    { ...clone(samples.HOUSE.explanation), explanation_version: "9.9" },
    { ...clone(samples.HOUSE.explanation), output_space: "RAW_VND" },
  ];
  for (const explanation of cases) {
    const html = render({ explanation, predictedPriceVnd: 4059447662 });
    assert.match(html, /data-explanation-status="INVALID"/);
    assert.match(html, /Giá dự đoán vẫn có hiệu lực|không hiển thị đóng góp/);
    assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
    assert.doesNotMatch(html, /NaN|Infinity/);
  }
});

test("invalid reconstruction hides the waterfall but keeps the price", () => {
  const payload = clone(samples.HOUSE.explanation);
  payload.other_contribution_log += 0.5;
  const html = render({ explanation: payload, predictedPriceVnd: 4059447662 });
  assert.match(html, /data-explanation-status="INVALID"/);
  assert.match(html, /Không thể hiển thị phần giải thích/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});

// ---------------------------------------------------------------- 12 provenance
test("provenance summary uses counts, not invented values", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.match(html, /Nguồn dữ liệu:/);
  assert.doesNotMatch(html, /đã xác minh|verified/);
});

// ---------------------------------------------------------------- 24 responsive + a11y
test("layout is responsive and accessible", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.match(html, /sm:grid-cols-2|sm:table-cell/);
  assert.match(html, /aria-label="Giải thích kết quả định giá/);
  assert.match(html, /lang="vi"/);
  assert.match(html, /break-words/);
  assert.match(html, /scope="row"/);
});

test("no causal or confidence language is rendered", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
  });
  assert.doesNotMatch(html, /độ tin cậy|confidence|chắc chắn làm giá|xác suất/i);
  assert.match(html, /không phải quan hệ nhân quả/);
});

test("a shap-only object is not mistaken for an explanation", () => {
  const html = render({
    explanation: { shap_explanation: { top_factors: [] } },
    predictedPriceVnd: 4059447662,
  });
  assert.match(html, /data-explanation-status="INVALID"/);
  assert.match(html, /Không thể hiển thị phần giải thích/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});
