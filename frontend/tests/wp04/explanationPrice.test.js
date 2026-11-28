import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { renderToStaticMarkup } from "react-dom/server";

import {
  STATUS,
  normalizeVnd,
  sameVnd,
  validateExplanation,
  vndDigits,
} from "../../src/features/prediction/explanationModel.js";
import { ValuationExplanationPanel } from "../../src/features/prediction/ValuationExplanationPanel.js";

const here = dirname(fileURLToPath(import.meta.url));
const samples = JSON.parse(readFileSync(join(here, "fixtures/explanation-samples.json"), "utf8"));
const clone = (value) => JSON.parse(JSON.stringify(value));
const render = (props) => renderToStaticMarkup(ValuationExplanationPanel(props));
const renderedPrice = (html) => {
  const match = /data-testid="explanation-price"[^>]*>([^<]*)</.exec(html);
  return match ? match[1].trim() : "";
};
const house = () => clone(samples.HOUSE.explanation);

// ---------------------------------------------------------------- normalizeVnd
test("normalizeVnd accepts positive integers and Spring decimal strings", () => {
  assert.equal(normalizeVnd(5749775772), 5749775772);
  assert.equal(normalizeVnd("5749775772"), 5749775772);
  assert.equal(normalizeVnd(" 5749775772 "), 5749775772, "surrounding whitespace is tolerated");
  // Spring's BigInteger.toString() never emits leading zeros, so they are not a price
  assert.equal(normalizeVnd("0005749775772"), null);
});

test("normalizeVnd rejects every non-price representation", () => {
  for (const bad of [0, -1, -5749775772, 1.5, Number.NaN, Infinity, -Infinity,
    "", "   ", "0", "-5", "1.5", "0x15", "1e9", "5,749", "abc", null, undefined,
    {}, [], true, false, 2 ** 60]) {
    assert.equal(normalizeVnd(bad), null, `accepted ${String(bad)}`);
    assert.equal(vndDigits(bad), null, `digits accepted ${String(bad)}`);
  }
});

test("large prices stay exact instead of being rounded", () => {
  const big = "9007199254740993";          // 2^53 + 1, not representable as a double
  assert.equal(vndDigits(big), big);
  assert.equal(normalizeVnd(big), null, "cannot be represented exactly as a JS number");
  assert.equal(sameVnd(big, big), true);
  assert.equal(sameVnd(big, "9007199254740992"), false, "neighbours stay distinguishable");
});

test("sameVnd compares digit strings, not coerced numbers", () => {
  assert.equal(sameVnd(5749775772, "5749775772"), true);
  assert.equal(sameVnd(5749775772, 5749775773), false, "one VND apart is different");
  assert.equal(sameVnd("0x15", 21), false, "hex is not a price even if Number() agrees");
});

// ---------------------------------------------------------------- component consistency
const price = samples.HOUSE.predicted_asking_price_vnd;

test("matching numeric price keeps attribution", () => {
  const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: price });
  assert.match(html, /data-explanation-status="AVAILABLE"/);
  assert.match(html, /data-testid="explanation-waterfall"/);
});

test("matching Spring decimal string keeps attribution", () => {
  const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: String(price) });
  assert.match(html, /data-explanation-status="AVAILABLE"/);
});

test("one VND apart is a mismatch", () => {
  const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: price + 1 });
  assert.match(html, /data-explanation-status="INCONSISTENT"/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});

test("supplied but invalid prices are inconsistent, not silently absent", () => {
  for (const bad of ["0x15", "1e9", "1.5", "0", "-5749775772", 0, -1, 1.5, Number.NaN,
    Infinity, {}, []]) {
    const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: bad });
    assert.match(html, /data-explanation-status="INCONSISTENT"/, String(bad));
    assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
  }
});

test("a malformed value cannot pass just because Number() would coerce to the price", () => {
  const payload = clone(samples.HOUSE.explanation);
  payload.calibration.adjusted_price_vnd = 21;
  const html = render({ explanation: payload, predictedPriceVnd: "0x15" });   // Number("0x15") === 21
  assert.match(html, /data-explanation-status="INCONSISTENT"/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
});

test("missing price is not a mismatch", () => {
  for (const missing of [undefined, null, ""]) {
    const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: missing });
    assert.match(html, /data-explanation-status="AVAILABLE"/, String(missing));
  }
});

test("validator uses exact equality, no relative tolerance", () => {
  const payload = clone(samples.HOUSE.explanation);
  const view = validateExplanation(payload, { priceVnd: price + 1 }).view;
  assert.equal(view.priceConsistent, false);
  const ok = validateExplanation(payload, { priceVnd: price }).view;
  assert.equal(ok.priceConsistent, true);
  // a 0.0001% difference must still be a mismatch: prices are integers
  const tiny = validateExplanation(payload, { priceVnd: price + 1 }).view;
  assert.equal(tiny.priceConsistent, false);
});

test("every committed fixture matches its own authoritative price", () => {
  for (const type of ["HOUSE", "LAND", "APARTMENT", "VILLA"]) {
    const sample = samples[type];
    const result = validateExplanation(sample.explanation, {
      priceVnd: sample.predicted_asking_price_vnd,
    });
    assert.equal(result.status, STATUS.AVAILABLE, type);
    assert.equal(result.view.priceConsistent, true, type);
  }
});

// ---------------------------------------------------------------- adjusted price contract
test("adjusted_price_vnd must be a valid authoritative VND value", () => {
  for (const bad of [0, -1, 1.5, Number.NaN, Infinity, "abc", "0x15", "", null, {}, [], true]) {
    const payload = house();
    payload.calibration.adjusted_price_vnd = bad;
    const result = validateExplanation(payload);
    assert.equal(result.status, STATUS.INVALID, `accepted adjusted price ${String(bad)}`);
    assert.match(result.reason, /Giá sau hiệu chỉnh/);
  }
});

test("a canonical digit string adjusted price is accepted and compared exactly", () => {
  const payload = house();
  payload.calibration.adjusted_price_vnd = String(payload.calibration.adjusted_price_vnd);
  const ok = validateExplanation(payload, { priceVnd: price }).view;
  assert.ok(ok);
  assert.equal(ok.priceConsistent, true);

  const mismatch = validateExplanation(payload, { priceVnd: price + 1 }).view;
  assert.equal(mismatch.priceConsistent, false, "one VND apart is still a mismatch");
});

test("an invalid adjusted price cannot silently bypass consistency", () => {
  const payload = house();
  payload.calibration.adjusted_price_vnd = Number.NaN;
  const result = validateExplanation(payload, { priceVnd: price });
  assert.equal(result.status, STATUS.INVALID, "must reject instead of returning null digits");
});

// ---------------------------------------------------------------- rendered price text
test("the panel renders a valid numeric point price", () => {
  const html = render({ predictedPriceVnd: 5476531536, modelVersion: "v1.3", explanation: house() });
  assert.match(renderedPrice(html), /\d/);
  assert.notEqual(renderedPrice(html), "—");
});

test("the panel renders a Spring decimal string without losing the integer", () => {
  const html = render({ predictedPriceVnd: "5476531536.00", modelVersion: "v1.3", explanation: house() });
  assert.match(renderedPrice(html), /\d/);
});

test("a long canonical digit string renders exactly", () => {
  const html = render({
    predictedPriceVnd: "123456789012345", modelVersion: "v1.3", explanation: house(),
  });
  const text = renderedPrice(html);
  // 123456789012345 VND keeps its integer part exactly: 123.456 tỷ in vi-VN grouping
  assert.match(text, /123[\.\s]?456/, text);
  assert.equal(text.includes("—"), false, text);
});

test("invalid point prices render the placeholder, never a fabricated number", () => {
  for (const bad of [0, -1, 1.5, "abc", "0", null, undefined, {}, true, Number.NaN]) {
    const html = render({ predictedPriceVnd: bad, modelVersion: "v1.3", explanation: house() });
    assert.equal(renderedPrice(html), "—", `rendered a price for ${String(bad)}`);
  }
});

test("a one-VND mismatch keeps the authoritative price visible and flags inconsistency", () => {
  const payload = house();
  payload.calibration.adjusted_price_vnd = 5476531537;
  const html = render({ predictedPriceVnd: 5476531536, modelVersion: "v1.3", explanation: payload });
  assert.match(renderedPrice(html), /\d/);
  assert.match(html, /data-explanation-status="INCONSISTENT"/);
});

test("an UNAVAILABLE explanation still shows a valid point price", () => {
  const html = render({
    predictedPriceVnd: 5476531536,
    modelVersion: "v1.3",
    explanation: { status: "UNAVAILABLE", reason: "Không đủ dữ liệu." },
  });
  assert.match(html, /5,4[0-9]?\s*tỷ/);
});
