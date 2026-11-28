/**
 * WP-04 B4 — explanation contract model.
 *
 * Pure logic: validates the backend explanation object and turns it into a stable view model.
 * No React, no browser APIs, so it can be tested with `node --test` and reused by any panel.
 *
 * Rules enforced here:
 *  - Unknown version / status / output space is never silently upgraded to AVAILABLE.
 *  - Raw contributions are never replaced by the rounded display values.
 *  - Missing numbers are never turned into 0.
 *  - The waterfall must reconstruct the margin within the backend tolerance, or it is refused.
 */

export const SUPPORTED_VERSIONS = ["1.0"];
export const SUPPORTED_OUTPUT_SPACE = "LOG1P_PRICE_VND";
export const RECONSTRUCTION_TOLERANCE = 1e-5;

export const STATUS = {
  ABSENT: "ABSENT",
  AVAILABLE: "AVAILABLE",
  PARTIAL: "PARTIAL",
  UNAVAILABLE: "UNAVAILABLE",
  NOT_SUPPORTED: "NOT_SUPPORTED",
  INVALID: "INVALID",
};

export const GROUP_LABELS = {
  LOCATION: "Vị trí",
  AREA: "Diện tích",
  STRUCTURE: "Kết cấu",
  ACCESS: "Đường tiếp cận",
  PROJECT: "Dự án",
  DIRECTION: "Hướng",
  PROPERTY_TYPE: "Loại bất động sản",
  OTHER: "Thuộc tính liên quan",
};

export const PROVENANCE_LABELS = {
  OBSERVED: {
    label: "Bạn đã cung cấp",
    note: "Thông tin do người dùng nhập.",
  },
  DERIVED: {
    label: "Hệ thống tính ra",
    note: "Đặc điểm được tính từ dữ liệu đầu vào, không phải thông tin xác minh trực tiếp.",
  },
  DEFAULTED: {
    label: "Hệ thống giả định",
    note: "Giá trị do hệ thống giả định, không phải số liệu bạn cung cấp.",
  },
  MISSING: {
    label: "Chưa cung cấp",
    note: "Thông tin này chưa được cung cấp; mô hình dùng cơ chế xử lý dữ liệu thiếu.",
  },
  MISSING_INVALID: {
    label: "Giá trị không hợp lệ",
    note: "Giá trị đã nhập không hợp lệ nên không được sử dụng.",
  },
  NOT_APPLICABLE: {
    label: "Không áp dụng",
    note: "Đặc điểm này không áp dụng cho loại bất động sản đang định giá.",
  },
  UNKNOWN_CATEGORY: {
    label: "Chưa có trong danh mục",
    note: "Giá trị chưa có trong danh mục mô hình đã học nên được xử lý là chưa xác định.",
  },
  UNVERIFIED: {
    label: "Chưa xác định nguồn",
    note: "Chưa đủ căn cứ để xác định nguồn gốc của đặc điểm này.",
  },
};

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const isFiniteNumber = (value) => typeof value === "number" && Number.isFinite(value);

export function formatVnd(value) {
  if (!isFiniteNumber(value)) return "—";
  return `${new Intl.NumberFormat("vi-VN").format(Math.round(value))} ₫`;
}

export function formatBillion(value) {
  if (!isFiniteNumber(value)) return "—";
  return `${(value / 1e9).toLocaleString("vi-VN", {
    minimumFractionDigits: 2,
    maximumFractionDigits: 2,
  })} tỷ`;
}

export function formatLog(value) {
  if (!isFiniteNumber(value)) return "—";
  return value.toFixed(4);
}

export function directionOf(value) {
  if (!isFiniteNumber(value) || value === 0) return "neutral";
  return value > 0 ? "increase" : "decrease";
}

export function directionLabel(value) {
  const direction = directionOf(value);
  if (direction === "increase") return "theo hướng tăng";
  if (direction === "decrease") return "theo hướng giảm";
  return "không đổi";
}

function invalid(reason) {
  return { status: STATUS.INVALID, reason, view: null };
}

/**
 * Validate a raw explanation object.
 * Returns { status, reason?, view? } where view is ready for rendering.
 */
export function validateExplanation(raw) {
  if (raw === null || raw === undefined) {
    return {
      status: STATUS.ABSENT,
      reason: "Không có phần giải thích cho lần định giá này.",
      view: null,
    };
  }
  if (typeof raw !== "object" || Array.isArray(raw)) {
    return { status: STATUS.INVALID, reason: "Dữ liệu giải thích không đúng định dạng." };
  }

  const version = raw.explanation_version;
  if (typeof version !== "string" || !SUPPORTED_VERSIONS.includes(version)) {
    return invalid(`Phiên bản giải thích không được hỗ trợ (${String(version)}).`);
  }

  const status = raw.status;
  if (!Object.values(STATUS).includes(status) || status === STATUS.INVALID) {
    return invalid(`Trạng thái giải thích không hợp lệ (${String(status)}).`);
  }

  if (status === STATUS.UNAVAILABLE || status === STATUS.NOT_SUPPORTED) {
    const limitations = Array.isArray(raw.limitations) ? raw.limitations : [];
    return {
      status,
      reason: limitations[0] || "Mô hình không cung cấp được giải thích cho lần định giá này.",
      view: { status, limitations, points: [], groups: [], factors: [], provenance: [] },
    };
  }

  if (raw.output_space !== SUPPORTED_OUTPUT_SPACE) {
    return invalid(`Không gian đầu ra không được hỗ trợ (${String(raw.output_space)}).`);
  }
  if (!isFiniteNumber(raw.predicted_margin_log)) {
    return invalid("Thiếu giá trị margin dự đoán hợp lệ.");
  }
  if (!isFiniteNumber(raw.base_value_log)) {
    return invalid("Thiếu base value hợp lệ.");
  }

  if (status === STATUS.PARTIAL) {
    return {
      status,
      reason: "Chỉ có một phần giải thích cho lần định giá này.",
      view: {
        status,
        limitations: Array.isArray(raw.limitations) ? raw.limitations : [],
        points: [],
        groups: [],
        factors: [],
        provenance: [],
        margin: raw.predicted_margin_log,
        base: raw.base_value_log,
      },
    };
  }

  // ---- AVAILABLE: everything below is required
  if (!isObject(raw.calibration)) return invalid("Thiếu thông tin hiệu chỉnh giá.");
  if (!isFiniteNumber(raw.calibration.factor) || raw.calibration.factor <= 0) {
    return invalid("Hệ số hiệu chỉnh không hợp lệ.");
  }
  if (!isFiniteNumber(raw.other_contribution_log)) {
    return invalid("Thiếu đóng góp của các yếu tố còn lại.");
  }
  if (!isObject(raw.grouped_contributions)) return invalid("Thiếu tổng hợp theo nhóm.");
  if (!isObject(raw.feature_provenance)) return invalid("Thiếu nguồn gốc đặc trưng.");
  if (!Array.isArray(raw.factors) || raw.factors.length === 0) {
    return invalid("Danh sách yếu tố ảnh hưởng trống.");
  }

  const factors = [];
  for (const factor of raw.factors) {
    if (!isObject(factor) || typeof factor.feature_name !== "string") {
      return invalid("Một yếu tố ảnh hưởng có cấu trúc không hợp lệ.");
    }
    if (!isFiniteNumber(factor.contribution_log_raw)) {
      return invalid(`Đóng góp của "${factor.feature_name}" không phải số hợp lệ.`);
    }
    factors.push({
      featureName: factor.feature_name,
      label: factor.label_vi || factor.feature_name,
      // raw value is authoritative; the display value is presentation only
      raw: factor.contribution_log_raw,
      display: isFiniteNumber(factor.contribution_log_display)
        ? factor.contribution_log_display
        : factor.contribution_log_raw,
      direction: directionOf(factor.contribution_log_raw),
      directionLabel: directionLabel(factor.contribution_log_raw),
      group: factor.group || "OTHER",
      groupLabel: GROUP_LABELS[factor.group] || GROUP_LABELS.OTHER,
      inputState: factor.input_state || "UNVERIFIED",
      provenance:
        PROVENANCE_LABELS[factor.input_state] || PROVENANCE_LABELS.UNVERIFIED,
      note: factor.context_note_vi || "",
    });
  }

  const sumFactors = factors.reduce((total, factor) => total + factor.raw, 0);
  const reconstructed = raw.base_value_log + sumFactors + raw.other_contribution_log;
  const tolerance = RECONSTRUCTION_TOLERANCE * Math.max(1, Math.abs(raw.predicted_margin_log));
  if (Math.abs(raw.predicted_margin_log - reconstructed) > tolerance) {
    return invalid("Không thể kiểm chứng lại kết quả từ các đóng góp.");
  }

  const groups = Object.entries(raw.grouped_contributions)
    .filter(([, value]) => isFiniteNumber(value))
    .map(([name, value]) => ({
      name,
      label: GROUP_LABELS[name] || GROUP_LABELS.OTHER,
      value,
      direction: directionOf(value),
      directionLabel: directionLabel(value),
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const provenance = Object.entries(raw.feature_provenance).map(([feature, state]) => ({
    feature,
    state,
    ...(PROVENANCE_LABELS[state] || PROVENANCE_LABELS.UNVERIFIED),
  }));

  const flagged = provenance.filter((item) =>
    ["MISSING", "MISSING_INVALID", "UNKNOWN_CATEGORY", "NOT_APPLICABLE", "DEFAULTED"].includes(
      item.state,
    ),
  );

  return {
    status: STATUS.AVAILABLE,
    view: {
      status: STATUS.AVAILABLE,
      version: raw.explanation_version,
      method: raw.method,
      target: raw.target,
      outputSpace: raw.output_space,
      margin: raw.predicted_margin_log,
      base: raw.base_value_log,
      basePriceVnd: raw.base_price_vnd,
      naivePriceVnd: raw.naive_price_vnd,
      calibration: {
        policy: raw.calibration.policy,
        factor: raw.calibration.factor,
        adjustedPriceVnd: raw.calibration.adjusted_price_vnd,
      },
      factors,
      groups,
      other: raw.other_contribution_log,
      provenance,
      flagged,
      limitations: Array.isArray(raw.limitations) ? raw.limitations : [],
      // waterfall keeps signed log-space contributions; VND is never mixed into this axis
      waterfall: {
        base: raw.base_value_log,
        steps: factors.map((factor) => ({
          name: factor.featureName,
          label: factor.label,
          value: factor.raw,
        })),
        other: raw.other_contribution_log,
        total: reconstructed,
        margin: raw.predicted_margin_log,
      },
    },
  };
}

export function summarizeProvenance(provenance) {
  const counts = {};
  for (const item of provenance) {
    counts[item.state] = (counts[item.state] || 0) + 1;
  }
  return counts;
}
