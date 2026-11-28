/**
 * WP-04 B4/B5 — reusable explanation panel.
 *
 * One component for all three valuation surfaces (standalone, posting preview, unified Advisor).
 * Authored with React.createElement instead of JSX on purpose: the repository test runner is
 * `node --test`, which has no JSX transform, so this keeps the component itself testable and
 * server-renderable without adding a test framework or bundler step.
 *
 * Rules:
 *  - Never fabricates attribution: invalid or unavailable explanations show a Vietnamese state.
 *  - Raw log-space contributions are rendered as-is; only display strings are formatted.
 *  - The waterfall is cumulative: each bar starts at the previous cumulative value.
 *  - Directions are conveyed with text and arrows, not colour alone.
 *  - Calibration is a separate bridge, never another SHAP feature.
 */
import { createElement as h } from "react";

import {
  STATUS,
  directionOf,
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

const WATERFALL_STYLE = {
  width: "100%",
  height: "auto",
  display: "block",
  maxWidth: "100%",
};

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

function statusText(status) {
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
    { className: "flex min-w-0 flex-wrap items-baseline gap-x-3 gap-y-1" },
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
      ? h("span", { className: "min-w-0 text-xs break-words text-brand-navy/60" },
          formatVnd(predictedPriceVnd))
      : null,
    h(
      "span",
      { className: "min-w-0 text-[11px] uppercase tracking-[0.18em] text-brand-navy/50 break-words" },
      `Giá rao bán ước tính · ${modelVersion || "v1.3"}`,
    ),
  );
}

function limitationsList(limitations) {
  if (!limitations || limitations.length === 0) return null;
  return h(
    "ul",
    { className: "mt-3 min-w-0 space-y-1 text-[11px] leading-relaxed text-brand-navy/70" },
    limitations.map((item, index) =>
      h("li", { key: `limitation-${index}`, className: "min-w-0 break-words" }, `• ${item}`),
    ),
  );
}

function groupList(groups) {
  if (!groups || groups.length === 0) return null;
  return h(
    "ul",
    { "data-testid": "explanation-groups", className: "mt-3 min-w-0 space-y-1.5" },
    groups.map((group) =>
      h(
        "li",
        {
          key: group.name,
          "data-group": group.name,
          "data-direction": group.direction,
          className: "flex min-w-0 items-baseline justify-between gap-3 text-xs",
        },
        h("span", { className: "min-w-0 flex-1 break-words" }, group.label),
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
    ["UNVERIFIED", "chưa xác định nguồn"],
  ]
    .filter(([state]) => counts[state])
    .map(([state, label]) => `${counts[state]} ${label}`);

  return h(
    "p",
    {
      "data-testid": "explanation-provenance-summary",
      className: "mt-3 min-w-0 break-words text-[11px] leading-relaxed text-brand-navy/70",
    },
    `Nguồn dữ liệu: ${chips.join(" · ")}.`,
  );
}

/** All 22 production features with their Vietnamese label and provenance state. */
function provenanceRows(provenance) {
  return h(
    "ul",
    { "data-testid": "explanation-provenance", className: "mt-2 min-w-0 space-y-1 text-[11px]" },
    provenance.map((item) =>
      h(
        "li",
        {
          key: item.feature,
          "data-provenance": item.state,
          className: "flex min-w-0 flex-wrap items-baseline gap-x-1.5",
        },
        h("span", { className: "min-w-0 break-words" }, item.label),
        h("span", { className: "shrink-0 text-brand-navy/60" }, `— ${item.state}`),
        item.note ? h("span", { className: "min-w-0 break-words text-brand-navy/55" }, item.note) : null,
      ),
    ),
  );
}

/** Cumulative log-space waterfall: every bar starts where the previous one ended. */
function waterfallSvg(view) {
  const { base, steps, other, margin } = view.waterfall;
  const rows = [
    { key: "base", label: "Base", from: 0, to: base },
    ...steps.map((step) => ({ key: `step-${step.name}`, label: step.label, value: step.value })),
    { key: "other", label: "Khác", value: other },
  ];

  let cursor = base;
  for (const row of rows.slice(1)) {
    row.from = cursor;
    row.to = cursor + row.value;
    cursor = row.to;
  }

  const all = rows.flatMap((row) => [row.from, row.to]);
  const min = Math.min(...all);
  const max = Math.max(...all);
  const span = max - min || 1;
  const rowH = 18;
  const gap = 5;
  const left = 4;
  const width = 100;
  const height = rows.length * (rowH + gap) + 4;
  const x = (value) => left + ((value - min) / span) * width;

  return h(
    "svg",
    {
      viewBox: `0 0 ${width + 8} ${height}`,
      role: "img",
      "aria-label": "Thác nước cộng dồn trong thang log của giá",
      "data-testid": "explanation-waterfall-svg",
      preserveAspectRatio: "none",
      style: WATERFALL_STYLE,
    },
    rows.map((row, index) => {
      const y = index * (rowH + gap) + 2;
      const x1 = x(Math.min(row.from, row.to));
      const x2 = x(Math.max(row.from, row.to));
      const w = Math.max(0.6, x2 - x1);
      const growing = row.to >= row.from;
      return h("rect", {
        key: row.key,
        "data-bar": row.key,
        x: x1,
        y,
        width: w,
        height: rowH,
        rx: 1.5,
        fill: growing ? "#0f766e" : "#b45309",
        opacity: row.key === "base" ? 0.55 : 0.9,
      });
    }),
  );
}

function waterfall(view) {
  if (!view.waterfall) return null;
  const { base, steps, other, total, margin } = view.waterfall;
  let cumulative = base;
  const rows = [
    { key: "base", label: "Giá trị cơ sở", value: base, cumulative: base },
    ...steps.map((step) => {
      cumulative += step.value;
      return { key: `step-${step.name}`, label: step.label, value: step.value, cumulative };
    }),
    { key: "other", label: "Các yếu tố khác", value: other, cumulative: cumulative + other },
  ];
  const residual = Math.abs(margin - total);

  return h(
    "div",
    { className: "mt-3 min-w-0" },
    waterfallSvg(view),
    h(
      "table",
      { "data-testid": "explanation-waterfall", className: "mt-2 w-full table-fixed text-[11px] tabular-nums" },
      h(
        "caption",
        { className: "pb-1 text-left text-brand-navy/60" },
        "Thang log của giá (LOG1P_PRICE_VND) — cộng dồn, không phải VNĐ.",
      ),
      h(
        "thead",
        null,
        h(
          "tr",
          null,
          h("th", { scope: "col", className: "w-2/5 py-0.5 text-left font-normal" }, "Yếu tố"),
          h("th", { scope: "col", className: "py-0.5 text-right font-normal" }, "Đóng góp"),
          h("th", { scope: "col", className: "py-0.5 text-right font-normal" }, "Luỹ kế"),
        ),
      ),
      h(
        "tbody",
        null,
        rows.map((row) =>
          h(
            "tr",
            { key: row.key, "data-row": row.key },
            h("th", { scope: "row", className: "py-0.5 pr-2 text-left font-normal break-words" },
              row.label),
            h("td", { className: "py-0.5 text-right whitespace-nowrap" },
              row.key === "base" ? formatLog(row.value) : `${ARROW[directionOf(row.value)]} ${formatLog(row.value)}`),
            h("td", { className: "py-0.5 text-right whitespace-nowrap" }, formatLog(row.cumulative)),
          ),
        ),
        h(
          "tr",
          { "data-row": "total" },
          h("th", { scope: "row", className: "py-0.5 pr-2 text-left font-normal" }, "Tổng tái lập"),
          h("td", { className: "py-0.5 text-right whitespace-nowrap" }, formatLog(total)),
          h("td", { className: "py-0.5 text-right whitespace-nowrap text-brand-navy/60" }, "—"),
        ),
        h(
          "tr",
          { "data-row": "margin", className: "border-t border-brand-navy/10" },
          h("th", { scope: "row", className: "py-0.5 pr-2 text-left font-bold" }, "Margin dự đoán"),
          h("td", { className: "py-0.5 text-right whitespace-nowrap" }, formatLog(margin)),
          h("td", { className: "py-0.5 text-right whitespace-nowrap text-brand-navy/60" },
            `lệch ${residual.toExponential(1)}`),
        ),
      ),
    ),
  );
}

function calibrationBridge(view) {
  if (!view.calibration) return null;
  return h(
    "dl",
    {
      "data-testid": "explanation-calibration",
      className: "mt-3 grid min-w-0 grid-cols-1 gap-1 text-[11px] sm:grid-cols-2",
    },
    h("dt", { className: "text-brand-navy/60" }, "Giá trước hiệu chỉnh"),
    h("dd", { className: "min-w-0 break-words tabular-nums" }, formatVnd(view.naivePriceVnd)),
    h("dt", { className: "text-brand-navy/60" }, "Chính sách hiệu chỉnh"),
    h("dd", { className: "min-w-0 break-words" }, view.calibration.policy || "—"),
    h("dt", { className: "text-brand-navy/60" }, "Hệ số hiệu chỉnh"),
    h("dd", { className: "min-w-0 break-words tabular-nums" }, `${view.calibration.factor}`),
    h("dt", { className: "text-brand-navy/60" }, "Giá sau hiệu chỉnh"),
    h("dd", { className: "min-w-0 break-words tabular-nums" },
      formatVnd(view.calibration.adjustedPriceVnd)),
    h(
      "p",
      { className: "min-w-0 break-words text-brand-navy/60 sm:col-span-2" },
      "Hiệu chỉnh là một bước riêng, không phải một đóng góp SHAP.",
    ),
  );
}

function technicalSection(view) {
  return h(
    "details",
    { "data-testid": "explanation-technical", className: "mt-4 min-w-0 rounded-lg bg-brand-card/40 p-3" },
    h(
      "summary",
      { className: "cursor-pointer text-xs font-medium focus:outline-none focus-visible:ring-2" },
      "Phân tích kỹ thuật (TreeSHAP, thang log)",
    ),
    h(
      "p",
      { className: "mt-2 min-w-0 break-words text-[11px] text-brand-navy/70" },
      `Không gian đầu ra: ${view.outputSpace} · Phương pháp: ${view.method || "TreeSHAP"}`,
    ),
    waterfall(view),
    calibrationBridge(view),
    provenanceRows(view.provenance),
  );
}

function unavailableBlock(reason, limitations) {
  return h(
    "div",
    { "data-testid": "explanation-unavailable", className: "mt-2 min-w-0" },
    h(
      "p",
      { className: "min-w-0 break-words text-xs leading-relaxed text-brand-navy/75" },
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
      className: `min-w-0 max-w-full rounded-xl bg-white/70 p-4 shadow-sm ${className}`.trim(),
    },
    priceBlock({ predictedPriceVnd, modelVersion }),
    h(
      "p",
      { className: `mt-1 text-[11px] font-medium ${statusTone(status)}` },
      `${ARROW[isAvailable ? "increase" : "neutral"]} ${statusText(status)}`,
    ),

    status === STATUS.ABSENT || status === STATUS.UNAVAILABLE || status === STATUS.NOT_SUPPORTED
      ? unavailableBlock(result.reason, view?.limitations)
      : null,

    status === STATUS.INVALID
      ? h(
          "div",
          { "data-testid": "explanation-invalid", className: "mt-2 min-w-0" },
          h(
            "p",
            { className: "min-w-0 break-words text-xs leading-relaxed text-brand-navy/75" },
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
            className: "mt-2 min-w-0 break-words text-xs leading-relaxed text-brand-navy/75",
          },
          "Chỉ một phần thông tin giải thích là khả dụng cho lần định giá này.",
        )
      : null,

    isAvailable
      ? h(
          "div",
          { className: "min-w-0" },
          groupList(view.groups),
          provenanceSummary(view),
          limitationsList(view.limitations),
          technicalSection(view),
        )
      : null,

    h(
      "p",
      { className: "mt-3 min-w-0 break-words text-[10px] leading-relaxed text-brand-navy/55" },
      "Đây là giải thích hành vi của mô hình với dữ liệu đã nhập — không phải quan hệ nhân quả, "
        + "không phải khoảng tin cậy và không phải kết luận thẩm định giá thị trường.",
    ),
  );
}

export default ValuationExplanationPanel;
