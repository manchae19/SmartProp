/**
 * WP-04 B5 — browser harness for the Advisor evidence panel.
 *
 * Mounts the real component with the committed V1.3 fixtures so a runner can assert six factors,
 * 22 provenance rows, the waterfall, the calibration bridge, legacy SHAP isolation and the two
 * independent Comparable sections. Test-only; not part of the app bundle.
 *
 *   /tests/wp04/surfaces/index.html?case=advisor-available|advisor-legacy|advisor-unavailable|advisor-malformed
 */
import { StrictMode, createElement as h } from "react";
import { createRoot } from "react-dom/client";

import AdvisorEvidencePanel from "../../../src/features/prediction/AdvisorEvidencePanel.jsx";
import samples from "../fixtures/explanation-samples.json";

const params = new URLSearchParams(window.location.search);
const requested = params.get("case") || "advisor-available";
const clone = (value) => JSON.parse(JSON.stringify(value));

const comparable = {
  status: "OK",
  candidateCount: 3,
  searchStage: "DISTRICT",
  comparables: [{
    candidateId: "c1", sourceKind: "SMARTPROP", district: "Cẩm Lệ", propertyType: "HOUSE",
    areaSqm: 100, askingPriceVnd: 5600000000, similarityScore: 92, featureCoverage: 0.74,
  }],
};

const valuationComparables = {
  status: "OK",
  candidateCount: 4,
  searchStage: "DISTRICT",
  comparables: [{
    candidateId: "v1", sourceKind: "EXTERNAL_LISTING", district: "Cẩm Lệ",
    propertyType: "HOUSE", areaSqm: 98, askingPriceVnd: 5450000000, featureCoverage: 0.61,
  }],
};

function valuationFor(name) {
  const base = {
    status: "AVAILABLE",
    available: true,
    reason: null,
    modelVersion: "v1.3",
    modelRun: "tinix_xgboost_v1_3_integrated",
    predictedAskingPriceVnd: samples.HOUSE.predicted_asking_price_vnd,
    askingVsEstimatePct: null,
    priceBasis: "Giá rao bán ước tính.",
    featuresUsed: { area: 100 },
    missingFeatures: [],
    warnings: [],
    shapExplanation: {
      baseValueLog: 22.8891, basePriceVnd: 8722132856, topFactors: [],
      method: "TreeSHAP", summaryVi: "…",
    },
  };
  if (name === "advisor-available") {
    return { ...base, explanation: clone(samples.HOUSE.explanation) };
  }
  if (name === "advisor-legacy") {
    return { ...base, explanation: undefined };
  }
  if (name === "advisor-unavailable") {
    const explanation = clone(samples.HOUSE.explanation);
    explanation.status = "UNAVAILABLE";
    explanation.factors = null;
    explanation.limitations = ["Không tạo được giải thích SHAP (RuntimeError)"];
    return { ...base, explanation };
  }
  const explanation = clone(samples.HOUSE.explanation);
  explanation.factors[0].contribution_log_raw = "NaN";
  return { ...base, explanation };
}

function App() {
  return h(
    "main",
    null,
    h(AdvisorEvidencePanel, {
      valuation: valuationFor(requested),
      comparable,
      valuationComparables,
      mode: "SAFE",
    }),
  );
}

window.addEventListener("error", (event) => {
  const node = document.createElement("p");
  node.dataset.jsError = "true";
  node.textContent = `JS ERROR: ${event.message}`;
  document.getElementById("root").prepend(node);
});

createRoot(document.getElementById("root")).render(h(StrictMode, null, h(App)));
requestAnimationFrame(() => {
  document.documentElement.dataset.case = requested;
  document.documentElement.dataset.rendered = "true";
});
