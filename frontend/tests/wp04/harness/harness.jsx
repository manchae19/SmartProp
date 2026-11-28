/**
 * WP-04 B4 browser harness.
 *
 * Renders the real component with real V1.3 explanation payloads so a headless browser can
 * capture the states required by the review. Not shipped in the app bundle.
 *
 *   /tests/wp04/harness/?state=available|technical|missing|unavailable|malformed|legacy
 */
import "../../../src/styles/style.css";
import "../../../src/styles/interface.css";
import { StrictMode, createElement as h } from "react";
import { createRoot } from "react-dom/client";

import { ValuationExplanationPanel } from "../../../src/features/prediction/ValuationExplanationPanel.js";
import samples from "../fixtures/explanation-samples.json";

const state = new URLSearchParams(window.location.search).get("state") || "available";
const house = samples.HOUSE;

function payloadFor(name) {
  const clone = JSON.parse(JSON.stringify(house.explanation));
  switch (name) {
    case "unavailable":
      clone.status = "UNAVAILABLE";
      clone.limitations = ["Không tạo được giải thích SHAP (RuntimeError)"];
      return clone;
    case "partial":
      clone.status = "PARTIAL";
      return clone;
    case "malformed":
      return { explanation_version: "9.9", status: "AVAILABLE" };
    case "legacy":
      return undefined;
    default:
      return clone;
  }
}

function App() {
  return h(
    "main",
    null,
    h(ValuationExplanationPanel, {
      explanation: payloadFor(state),
      predictedPriceVnd: house.predicted_asking_price_vnd,
      modelVersion: "v1.3",
      surface: "standalone",
    }),
  );
}

window.addEventListener("error", (event) => {
  const node = document.createElement("p");
  node.className = "error";
  node.textContent = `JS ERROR: ${event.message}`;
  document.getElementById("root").prepend(node);
});

createRoot(document.getElementById("root")).render(
  h(StrictMode, null, h(App)),
);

// Screenshot helper: expand the technical section when asked, then report state on <html>.
requestAnimationFrame(() => {
  const details = document.querySelector("details");
  if (details) {
    details.open = state === "technical" || state === "available";
  }
  document.documentElement.dataset.state = state;
  document.documentElement.dataset.overflow =
    String(document.documentElement.scrollWidth > document.documentElement.clientWidth);
  document.documentElement.dataset.rendered = "true";
});
