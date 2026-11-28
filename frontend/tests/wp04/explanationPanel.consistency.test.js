import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { dirname, join } from "node:path";
import { test } from "node:test";
import { fileURLToPath } from "node:url";

import { renderToStaticMarkup } from "react-dom/server";

import { ValuationExplanationPanel } from "../../src/features/prediction/ValuationExplanationPanel.js";
import { evidenceSections, legacyImpactIsPercentage } from "../../src/features/prediction/advisorEvidenceModel.js";

const here = dirname(fileURLToPath(import.meta.url));
const samples = JSON.parse(readFileSync(join(here, "fixtures/explanation-samples.json"), "utf8"));

const clone = (value) => JSON.parse(JSON.stringify(value));
const render = (props) => renderToStaticMarkup(ValuationExplanationPanel(props));
const price = samples.HOUSE.predicted_asking_price_vnd;

// ---------------------------------------------------------------- price consistency
test("matching authoritative price keeps the explanation visible", () => {
  const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: price });
  assert.match(html, /data-explanation-status="AVAILABLE"/);
  assert.match(html, /data-testid="explanation-waterfall"/);
});

test("explanation from another prediction shows the inconsistent state only", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: price + 1_000_000,
  });
  assert.match(html, /data-explanation-status="INCONSISTENT"/);
  assert.match(html, /data-testid="explanation-inconsistent"/);
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
  assert.doesNotMatch(html, /data-testid="explanation-groups"/);
  // the authoritative price is still rendered
  assert.match(html, /data-testid="explanation-price"/);
});

test("inconsistent state never fabricates factors", () => {
  const payload = clone(samples.HOUSE.explanation);
  const html = render({ explanation: payload, predictedPriceVnd: 123 });
  assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
  assert.doesNotMatch(html, /data-provenance=/);
});

test("numeric-string price from Spring matches the explanation", () => {
  const html = render({
    explanation: samples.HOUSE.explanation,
    predictedPriceVnd: String(price),
  });
  assert.match(html, /data-explanation-status="AVAILABLE"/);
});

test("a supplied but unusable price blocks attribution", () => {
  for (const bad of ["0x1f", 0, -5, Number.NaN, Infinity, "abc"]) {
    const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: bad });
    assert.match(html, /data-explanation-status="INCONSISTENT"/, String(bad));
    assert.doesNotMatch(html, /data-testid="explanation-waterfall"/);
  }
});

test("an absent price is not treated as a mismatch", () => {
  for (const absent of [null, undefined, ""]) {
    const html = render({ explanation: samples.HOUSE.explanation, predictedPriceVnd: absent });
    assert.match(html, /data-explanation-status="AVAILABLE"/, String(absent));
  }
});

// ---------------------------------------------------------------- advisor sections
test("legacy-only response shows the legacy toggle and content when opened", () => {
  const sections = evidenceSections({ explanation: undefined, shap: { topFactors: [] }, openShap: true });
  assert.deepEqual(sections, {
    showExplanation: false,
    showLegacyShapToggle: true,
    showLegacyShapContent: true,
  });
});

test("new explanation replaces legacy SHAP completely", () => {
  const sections = evidenceSections({
    explanation: samples.HOUSE.explanation, shap: { topFactors: [] }, openShap: true,
  });
  assert.equal(sections.showExplanation, true);
  assert.equal(sections.showLegacyShapToggle, false);
  assert.equal(sections.showLegacyShapContent, false, "openShap must not leak stale legacy content");
});

test("returning to a legacy response keeps its own behaviour", () => {
  const sections = evidenceSections({ explanation: null, shap: { topFactors: [] }, openShap: false });
  assert.equal(sections.showLegacyShapToggle, true);
  assert.equal(sections.showLegacyShapContent, false, "collapsed by default");
});

test("no explanation and no legacy payload renders neither section", () => {
  const sections = evidenceSections({});
  assert.equal(sections.showExplanation, false);
  assert.equal(sections.showLegacyShapToggle, false);
  assert.equal(sections.showLegacyShapContent, false);
});

test("legacy impact values are never treated as a price percentage", () => {
  assert.equal(legacyImpactIsPercentage(), false);
});

// ---------------------------------------------------------------- full contract, four types
for (const type of ["HOUSE", "LAND", "APARTMENT", "VILLA"]) {
  test(`committed ${type} fixture renders the full contract`, () => {
    const sample = samples[type];
    const html = render({
      explanation: sample.explanation,
      predictedPriceVnd: sample.predicted_asking_price_vnd,
      modelVersion: "v1.3",
    });
    assert.match(html, /data-explanation-status="AVAILABLE"/);
    assert.match(html, /LOG1P_PRICE_VND/);
    assert.match(html, /data-testid="explanation-waterfall"/);
    assert.match(html, /data-testid="explanation-calibration"/);
    assert.equal((html.match(/data-provenance=/g) || []).length, 22);
    assert.doesNotMatch(html, /NaN|Infinity/);
  });
}
