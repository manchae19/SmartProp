/**
 * WP-04 B4 — reusable explanation panel.
 *
 * One component for all three valuation surfaces (standalone, posting preview, unified Advisor).
 * Authored with React.createElement instead of JSX on purpose: the repository test runner is
 * `node --test`, which has no JSX transform, so this keeps the component itself testable and
 * server-renderable without adding a test framework or bundler step.
 *
 * Rules:
 *  - Never fabricates attribution: invalid or unavailable explanations show a Vietnamese state.
 *  - Raw log-space contributions are rendered as-is; only display strings are formatted.
 *  - Directions are conveyed with text and arrows, not colour alone.
 *  - Calibration is a separate bridge, never another SHAP feature.
 */
import { createElement as h } from "react";

import {
  STATUS,
  formatBillion,
  formatLog,
  formatVnd,
  summarizeProvenance,
  validateExplanation,
} from "./explanationModel.js";

const SURFACE_LABEL = {
  standalone: "Định giá độc lập",
  preview: "Xem trước giá tin đăng",
  advisor: "Tư vấn tổng hợp",
};

const ARROW = { increase: "↑", decrease: "↓", neutral: "•" };

function statusTone(status) {
  switch (status) {
    case STATUS.AVAILABLE:
      return "text-emerald-700";
    case STATUS.PARTIAL:
      return "text-amber-700";
    default:
      return "text-brand-navy/60";
  }
}

function statusText(status, reason) {
  switch (status) {
    case STATUS.AVAILABLE:
      return "Giải thích đầy đủ";
    case STATUS.PARTIAL:
      return "Giải thích một phần";
    case STATUS.UNAVAILABLE:
      return "Chưa có giải thích";
    case STATUS.NOT_SUPPORTED:
      return "Mô hình không hỗ trợ giải thích";
    case STATUS.ABSENT:
      return "Không có phần giải thích";
    default:
      return "Giải thích không dùng được";
  }
}

function priceBlock({ predictedPriceVnd, modelVersion }) {
  const hasPrice = typeof predictedPriceVnd === "number" && Number.isFinite(predictedPriceVnd);
  return h(
    "div",
    { className: "flex flex-wrap items-baseline gap-x-3 gap-y-1" },
    h(
      "p",
      {
        "data-testid": "explanation-price",
        "aria-live": "polite",
        className: "text-lg font-light break-words",
      },
      hasPrice ? formatBillion(predictedPriceVnd) : "—",
    ),
    hasPrice
      ? h("span", { className: "text-xs text-brand-navy/60" }, formatVnd(predictedPriceVnd))
      : null,
    h(
      "span",
      { className: "text-[11px] uppercase tracking-[0.18em] text-brand-navy/50" },
      `Giá rao bán ước tính · ${modelVersion || "v1.3"}`,
    ),
  );
}

function limitationsList(limitations) {
  if (!limitations || limitations.length === 0) return null;
  return h(
    "ul",
    { className: "mt-3 space-y-1 text-[11px] leading-relaxed text-brand-navy/70" },
    limitations.map((item, index) =>
      h("li", { key: `limitation-${index}`, className: "break-words" }, `• ${item}`),
    ),
  );
}

function groupList(groups) {
  if (!groups || groups.length === 0) return null;
  return h(
    "ul",
    { "data-testid": "explanation-groups", className: "mt-3 space-y-1.5" },
    groups.map((group) =>
      h(
        "li",
        {
          key: group.name,
          "data-group": group.name,
          "data-direction": group.direction,
          className: "flex items-center justify-between gap-3 text-xs",
        },
        h("span", { className: "min-w-0 flex-1 truncate" }, group.label),
        h(
          "span",
          { className: `shrink-0 tabular-nums ${statusTone(STATUS.AVAILABLE)}` },
          `${ARROW[group.direction]} ${formatLog(group.value)}`,
        ),
      ),
    ),
  );
}

function provenanceSummary(view) {
  if (!view.flagged || view.flagged.length === 0) return null;
  const counts = summarizeProvenance(view.provenance);
  const chips = [
    ["MISSING", "chưa cung cấp"],
    ["MISSING_INVALID", "không hợp lệ"],
    ["UNKNOWN_CATEGORY", "chưa có trong danh mục"],
    ["NOT_APPLICABLE", "không áp dụng"],
    ["DEFAULTED", "giả định"],
  ]
    .filter(([state]) => counts[state])
    .map(([state, label]) => `${counts[state]} ${label}`);

  return h(
    "p",
    {
      "data-testid": "explanation-provenance-summary",
      className: "mt-3 text-[11px] leading-relaxed text-brand-navy/70 break-words",
    },
    `Nguồn dữ liệu: ${chips.join(" · ")}.`,
  );
}

function waterfall(view) {
  if (!view.waterfall) return null;
  const { base, steps, other, total, margin } = view.waterfall;
  const rows = [
    ["Giá trị cơ sở (base)", base, "base"],
    ...steps.map((step) => [step.label, step.value, `step-${step.name}`]),
    ["Các yếu tố khác", other, "other"],
    ["Tổng tái lập", total, "total"],
    ["Margin dự đoán", margin, "margin"],
  ];
  const widest = rows.reduce((max, [, value]) => Math.max(max, Math.abs(value) || 0), 1);

  return h(
    "table",
    { "data-testid": "explanation-waterfall", className: "mt-3 w-full table-fixed text-[11px] tabular-nums" },
    h(
      "caption",
      { className: "pb-1 text-left text-brand-navy/60" },
      "Thang log của giá (LOG1P_PRICE_VND) — không phải VNĐ và không phải quan hệ nhân quả.",
    ),
    h(
      "tbody",
      null,
      rows.map(([label, value, key]) => {
        const width = Math.min(100, (Math.abs(value) / widest) * 100);
        return h(
          "tr",
          { key, "data-row": key, className: "align-middle" },
          h("th", { scope: "row", className: "py-0.5 pr-2 text-left font-normal" }, label),
          h(
            "td",
            { className: "w-24 py-0.5 pr-2 text-right whitespace-nowrap" },
            formatLog(value),
          ),
          h(
            "td",
            { className: "hidden w-1/3 py-0.5 sm:table-cell" },
            h("span", {
              "aria-hidden": "true",
              className: "block h-1.5 rounded bg-brand-navy/25",
              style: { width: `${Math.max(2, width)}%` },
            }),
          ),
        );
      }),
    ),
  );
}

function calibrationBridge(view) {
  if (!view.calibration) return null;
  return h(
    "dl",
    {
      "data-testid": "explanation-calibration",
      className: "mt-3 grid grid-cols-1 gap-1 text-[11px] sm:grid-cols-2",
    },
    h("dt", { className: "text-brand-navy/60" }, "Giá trước hiệu chỉnh"),
    h("dd", { className: "tabular-nums" }, formatVnd(view.naivePriceVnd)),
    h("dt", { className: "text-brand-navy/60" }, "Chính sách hiệu chỉnh"),
    h("dd", null, view.calibration.policy || "—"),
    h("dt", { className: "text-brand-navy/60" }, "Hệ số hiệu chỉnh"),
    h("dd", { className: "tabular-nums" }, `${view.calibration.factor}`),
    h("dt", { className: "text-brand-navy/60" }, "Giá sau hiệu chỉnh"),
    h("dd", { className: "tabular-nums" }, formatVnd(view.calibration.adjustedPriceVnd)),
    h(
      "p",
      { className: "sm:col-span-2 text-brand-navy/60" },
      "Hiệu chỉnh là một bước riêng, không phải một đóng góp SHAP.",
    ),
  );
}

function technicalSection(view) {
  return h(
    "details",
    { "data-testid": "explanation-technical", className: "mt-4 rounded-lg bg-brand-card/40 p-3" },
    h(
      "summary",
      { className: "cursor-pointer text-xs font-medium focus:outline-none" },
      "Phân tích kỹ thuật (TreeSHAP, thang log)",
    ),
    h(
      "p",
      { className: "mt-2 text-[11px] text-brand-navy/70" },
      `Không gian đầu ra: ${view.outputSpace} · Phương pháp: ${view.method || "TreeSHAP"}`,
    ),
    waterfall(view),
    calibrationBridge(view),
  );
}

function unavailableBlock(status, reason, limitations) {
  return h(
    "div",
    { "data-testid": "explanation-unavailable", className: "mt-2" },
    h(
      "p",
      { className: "text-xs leading-relaxed text-brand-navy/75 break-words" },
      reason || "Mô hình không cung cấp được giải thích cho lần định giá này.",
    ),
    h(
      "p",
      { className: "mt-1 text-[11px] text-brand-navy/60" },
      "Giá dự đoán vẫn có hiệu lực; chỉ phần giải thích là không khả dụng.",
    ),
    limitationsList(limitations),
  );
}

export function ValuationExplanationPanel({
  explanation,
  predictedPriceVnd,
  modelVersion = "v1.3",
  surface = "standalone",
  className = "",
}) {
  const result = validateExplanation(explanation);
  const status = result.status;
  const isAvailable = status === STATUS.AVAILABLE;
  const view = result.view;

  return h(
    "section",
    {
      "data-ui-view": "ValuationExplanationPanel",
      "data-testid": "valuation-explanation-panel",
      "data-explanation-status": status,
      "aria-label": `Giải thích kết quả định giá — ${SURFACE_LABEL[surface] || surface}`,
      lang: "vi",
      className: `w-full max-w-full min-w-0 overflow-hidden rounded-xl bg-white/70 p-4 shadow-sm ${className}`.trim(),
    },
    priceBlock({ predictedPriceVnd, modelVersion }),
    h(
      "p",
      { className: `mt-1 text-[11px] font-medium ${statusTone(status)}` },
      `${ARROW[isAvailable ? "increase" : "neutral"]} ${statusText(status, result.reason)}`,
    ),

    status === STATUS.ABSENT || status === STATUS.UNAVAILABLE || status === STATUS.NOT_SUPPORTED
      ? unavailableBlock(status, result.reason, view?.limitations)
      : null,

    status === STATUS.INVALID
      ? h(
          "div",
          { "data-testid": "explanation-invalid", className: "mt-2" },
          h(
            "p",
            { className: "text-xs leading-relaxed text-brand-navy/75 break-words" },
            `Không thể hiển thị phần giải thích: ${result.reason}`,
          ),
          h(
            "p",
            { className: "mt-1 text-[11px] text-brand-navy/60" },
            "Hệ thống không hiển thị đóng góp nào khi dữ liệu giải thích không hợp lệ.",
          ),
          limitationsList(view?.limitations),
        )
      : null,

    status === STATUS.PARTIAL
      ? h(
          "p",
          {
            "data-testid": "explanation-partial",
            className: "mt-2 text-xs leading-relaxed text-brand-navy/75",
          },
          "Chỉ một phần thông tin giải thích là khả dụng cho lần định giá này.",
        )
      : null,

    isAvailable
      ? h(
          "div",
          null,
          groupList(view.groups),
          provenanceSummary(view),
          limitationsList(view.limitations),
          technicalSection(view),
        )
      : null,

    h(
      "p",
      { className: "mt-3 text-[10px] leading-relaxed text-brand-navy/55" },
      "Đây là giải thích hành vi của mô hình với dữ liệu đã nhập — không phải quan hệ nhân quả, "
        + "không phải khoảng tin cậy và không phải kết luận thẩm định giá thị trường.",
    ),
  );
}

export default ValuationExplanationPanel;
