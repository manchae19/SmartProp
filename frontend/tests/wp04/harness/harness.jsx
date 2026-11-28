/**
 * WP-04 B4/B5 browser harness.
 *
 * Renders the real component with real V1.3 explanation payloads so a browser runner can inspect
 * layout, provenance and failure states. Not shipped in the app bundle.
 *
 *   /tests/wp04/harness/?case=house|land|apartment|villa|missing|unverified|partial|
 *                        unavailable|not-supported|legacy|malformed
 */
import { StrictMode, createElement as h } from "react";
import { createRoot } from "react-dom/client";

import { ValuationExplanationPanel } from "../../../src/features/prediction/ValuationExplanationPanel.js";
import samples from "../fixtures/explanation-samples.json";

const params = new URLSearchParams(window.location.search);
const requested = params.get("case") || "house";

const clone = (value) => JSON.parse(JSON.stringify(value));

function payloadFor(name) {
  switch (name) {
    case "land":
      return samples.LAND.explanation;
    case "apartment":
      return samples.APARTMENT.explanation;
    case "villa":
      return samples.VILLA.explanation;
    case "missing": {
      // feature-rich payload where most inputs are absent
      const payload = clone(samples.HOUSE.explanation);
      for (const feature of Object.keys(payload.feature_provenance)) {
        payload.feature_provenance[feature] = "MISSING";
      }
      payload.factors = payload.factors.map((factor) => ({ ...factor, input_state: "MISSING" }));
      payload.limitations = [
        "Nhiều thông tin chưa được cung cấp. Mô hình vẫn tạo kết quả nhưng dùng cơ chế xử lý "
          + "dữ liệu thiếu, nên độ chính xác của phần giải thích có thể bị ảnh hưởng đáng kể.",
        "Đây là giải thích hành vi của mô hình với dữ liệu đã nhập, không phải quan hệ nhân quả "
          + "và không phải khoảng tin cậy.",
      ];
      return payload;
    }
    case "unverified": {
      const payload = clone(samples.HOUSE.explanation);
      payload.feature_provenance.ward = "UNVERIFIED";
      payload.feature_provenance.area = "VERIFIED_LOOKING";
      delete payload.feature_provenance.area ? null : null;
      payload.feature_provenance.area = "OBSERVED";
      const wardFactor = payload.factors.find((f) => f.feature_name === "ward");
      if (wardFactor) wardFactor.input_state = "UNVERIFIED";
      const factor = payload.factors[0];
      payload.feature_provenance[factor.feature_name] = "UNVERIFIED";
      factor.input_state = "UNVERIFIED";
      return payload;
    }
    case "partial":
      return { ...clone(samples.HOUSE.explanation), status: "PARTIAL" };
    case "unavailable": {
      const payload = clone(samples.HOUSE.explanation);
      payload.status = "UNAVAILABLE";
      payload.factors = null;
      payload.limitations = ["Không tạo được giải thích SHAP (RuntimeError)"];
      return payload;
    }
    case "not-supported": {
      const payload = clone(samples.HOUSE.explanation);
      payload.status = "NOT_SUPPORTED";
      payload.factors = null;
      payload.limitations = ["Mô hình không hỗ trợ giải thích."];
      return payload;
    }
    case "legacy":
      return undefined;
    case "malformed": {
      const payload = clone(samples.HOUSE.explanation);
      payload.factors = [{ feature_name: "area", contribution_log_raw: "NaN" }];
      return payload;
    }
    default:
      return samples.HOUSE.explanation;
  }
}

const priceFor = (name) => {
  const map = { land: "LAND", apartment: "APARTMENT", villa: "VILLA" };
  return samples[map[name] || "HOUSE"].predicted_asking_price_vnd;
};

function App() {
  return h(
    "main",
    null,
    h(ValuationExplanationPanel, {
      explanation: payloadFor(requested),
      predictedPriceVnd: priceFor(requested),
      modelVersion: "v1.3",
      surface: "standalone",
    }),
  );
}

window.addEventListener("error", (event) => {
  const node = document.createElement("p");
  node.className = "error";
  node.dataset.jsError = "true";
  node.textContent = `JS ERROR: ${event.message}`;
  document.getElementById("root").prepend(node);
});

createRoot(document.getElementById("root")).render(h(StrictMode, null, h(App)));

requestAnimationFrame(() => {
  document.documentElement.dataset.case = requested;
  document.documentElement.dataset.rendered = "true";
});
