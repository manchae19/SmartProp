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
