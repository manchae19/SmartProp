/**
 * WP-04 B4/B5 — explanation contract model.
 *
 * Pure logic: validates the backend explanation object and turns it into a stable view model.
 * No React, no browser APIs, so it can be tested with `node --test` and reused by any panel.
 *
 * Rules enforced here:
 *  - Unknown version / method / target / output space is never silently upgraded to AVAILABLE.
 *  - ABSENT and INVALID are frontend-internal states and are never accepted from upstream.
 *  - Raw contributions are never replaced by the rounded display values.
 *  - Missing numbers are never turned into 0.
 *  - Malformed group values are rejected, never silently dropped.
 *  - The waterfall must reconstruct the margin within the backend tolerance, or it is refused.
 */

export const SUPPORTED_VERSIONS = ["1.0"];
export const SUPPORTED_METHOD = "XGBOOST_NATIVE_TREESHAP";
export const SUPPORTED_TARGET = "ASKING_PRICE_VND";
export const SUPPORTED_OUTPUT_SPACE = "LOG1P_PRICE_VND";
export const RECONSTRUCTION_TOLERANCE = 1e-5;
export const GROUP_TOTAL_TOLERANCE = 1e-5;
export const TOP_K = 6;
// backend contract: explanation_v1_3 always emits TOP_K factors and the policy that
// calibration.json actually declares
export const SUPPORTED_CALIBRATION_POLICIES = ["duan_by_band"];

export const STATUS = {
  ABSENT: "ABSENT",
  AVAILABLE: "AVAILABLE",
  PARTIAL: "PARTIAL",
  UNAVAILABLE: "UNAVAILABLE",
  NOT_SUPPORTED: "NOT_SUPPORTED",
  INVALID: "INVALID",
};

/** Statuses the backend is allowed to send. ABSENT/INVALID are frontend-only. */
export const UPSTREAM_STATUSES = [
  STATUS.AVAILABLE,
  STATUS.PARTIAL,
  STATUS.UNAVAILABLE,
  STATUS.NOT_SUPPORTED,
];

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

/** Mirrors ai-services explanation_v1_3.FEATURE_GROUPS — production feature -> group. */
export const FEATURE_GROUPS = {
  area: "AREA",
  frontage_sqrt_area_ratio: "AREA",
  floor_count: "STRUCTURE",
  bedroom_count: "STRUCTURE",
  bathroom_count: "STRUCTURE",
  has_floor: "STRUCTURE",
  has_bedroom: "STRUCTURE",
  has_bathroom: "STRUCTURE",
  frontage_width: "ACCESS",
  road_width: "ACCESS",
  has_frontage: "ACCESS",
  has_road_width: "ACCESS",
  has_project: "PROJECT",
  raw_project_name: "PROJECT",
  has_street: "LOCATION",
  has_ward: "LOCATION",
  district: "LOCATION",
  ward: "LOCATION",
  raw_street_name: "LOCATION",
  normalized_type: "PROPERTY_TYPE",
  raw_house_direction: "DIRECTION",
  raw_balcony_direction: "DIRECTION",
};

export const FEATURE_LABELS = {
  area: "Diện tích",
  floor_count: "Số tầng",
  frontage_width: "Chiều rộng mặt tiền",
  road_width: "Chiều rộng đường",
  bedroom_count: "Số phòng ngủ",
  bathroom_count: "Số phòng tắm",
  has_floor: "Cờ có số tầng",
  has_frontage: "Cờ có mặt tiền",
  has_road_width: "Cờ có chiều rộng đường",
  has_bedroom: "Cờ có phòng ngủ",
  has_bathroom: "Cờ có phòng tắm",
  has_project: "Cờ có dự án",
  has_street: "Cờ có tuyến đường",
  has_ward: "Cờ có phường/xã",
  frontage_sqrt_area_ratio: "Tỉ lệ mặt tiền trên căn bậc hai diện tích",
  normalized_type: "Loại bất động sản",
  district: "Quận/Huyện",
  ward: "Phường/Xã",
  raw_street_name: "Tuyến đường",
  raw_project_name: "Dự án",
  raw_house_direction: "Hướng nhà",
  raw_balcony_direction: "Hướng ban công",
};

export const EXPECTED_FEATURES = Object.keys(FEATURE_LABELS);

export const PROVENANCE_LABELS = {
  OBSERVED: { label: "Bạn đã cung cấp", note: "Thông tin do người dùng nhập." },
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

export const FLAGGED_STATES = [
  "MISSING",
  "MISSING_INVALID",
  "UNKNOWN_CATEGORY",
  "NOT_APPLICABLE",
  "DEFAULTED",
  "UNVERIFIED",
];

const isObject = (value) => value !== null && typeof value === "object" && !Array.isArray(value);
const isFiniteNumber = (value) => typeof value === "number" && Number.isFinite(value);
const isText = (value) => typeof value === "string";
const isPositiveFinite = (value) => isFiniteNumber(value) && value > 0;
const isNonNegativeFinite = (value) => isFiniteNumber(value) && value >= 0;

/**
 * Accept the price shapes the two backends really produce: FastAPI sends a JSON number, Spring
 * Boot serialises BigInteger as a numeric string. Anything else (null, "", NaN, Infinity,
 * negative) is rejected instead of being coerced to 0.
 */
/**
 * Canonical VND digits for an authoritative prediction.
 *
 * FastAPI sends a positive JSON integer; Spring serialises BigInteger as a positive decimal
 * string. Anything else - zero, negative, fractional, hexadecimal, scientific notation, empty
 * string, object, NaN/Infinity - is not a price. Integers beyond the JavaScript safe range stay
 * exact as digit strings so they are compared precisely instead of being rounded.
 */
export function vndDigits(value) {
  if (typeof value === "number") {
    if (!Number.isSafeInteger(value) || value <= 0) return null;
    return String(value);
  }
  if (typeof value === "string") {
    const text = value.trim();
    if (/^[1-9]\d{0,29}$/.test(text)) return text;
    // An exact integer serialised with a zero fraction is the same value; any nonzero
    // fraction, exponent, sign or separator is rejected.
    const exact = /^([1-9]\d{0,29})\.0+$/.exec(text);
    return exact ? exact[1] : null;
  }
  return null;
}

/** Numeric form, only when it can be represented exactly. */
export function normalizeVnd(value) {
  const digits = vndDigits(value);
  if (digits === null) return null;
  const asNumber = Number(digits);
  return Number.isSafeInteger(asNumber) ? asNumber : null;
}

/** Exact comparison of two price representations. */
export function sameVnd(left, right) {
  const a = vndDigits(left);
  const b = vndDigits(right);
  return a !== null && b !== null && a === b;
}

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

function textList(value) {
  if (value === undefined || value === null) return [];
  if (!Array.isArray(value)) return null;
  if (!value.every(isText)) return null;
  return value;
}

function provenanceEntries(raw) {
  const map = raw.feature_provenance;
  if (!isObject(map)) return null;
  const keys = Object.keys(map);
  if (keys.length !== EXPECTED_FEATURES.length) return null;
  for (const feature of EXPECTED_FEATURES) {
    if (!Object.prototype.hasOwnProperty.call(map, feature)) return null;
  }
  if (keys.some((key) => !EXPECTED_FEATURES.includes(key))) return null;
  if (keys.some((key) => !Object.prototype.hasOwnProperty.call(PROVENANCE_LABELS, map[key]))) {
    return null;
  }
  return keys.map((feature) => ({
    // feature identity and provenance state stay in separate fields on purpose: the previous
    // version spread the state labels over the feature label and lost the feature identity.
    featureName: feature,
    featureLabel: FEATURE_LABELS[feature],
    state: map[feature],
    stateLabel: PROVENANCE_LABELS[map[feature]].label,
    note: PROVENANCE_LABELS[map[feature]].note,
  }));
}

function validateGroups(raw, topSum) {
  const groups = raw.grouped_contributions;
  const keys = Object.keys(groups);
  if (keys.length === 0) return { ok: false, reason: "Thiếu tổng hợp theo nhóm." };
  for (const key of keys) {
    if (!Object.prototype.hasOwnProperty.call(GROUP_LABELS, key)) {
      return { ok: false, reason: `Nhóm không xác định: ${key}.` };
    }
    if (!isFiniteNumber(groups[key])) {
      return { ok: false, reason: `Giá trị nhóm "${key}" không hợp lệ.` };
    }
  }
  const groupedSum = keys.reduce((total, key) => total + groups[key], 0);
  const expected = topSum + raw.other_contribution_log;
  const tolerance = GROUP_TOTAL_TOLERANCE * Math.max(1, Math.abs(expected));
  if (Math.abs(groupedSum - expected) > tolerance) {
    return { ok: false, reason: "Tổng theo nhóm không khớp với các đóng góp." };
  }
  return { ok: true, groupedSum };
}

function validateFactors(raw, provenanceByName) {
  const factors = raw.factors;
  if (!Array.isArray(factors) || factors.length === 0) {
    return { ok: false, reason: "Danh sách yếu tố ảnh hưởng trống." };
  }
  if (factors.length !== TOP_K) {
    return { ok: false, reason: `Cần đúng ${TOP_K} yếu tố ảnh hưởng, nhận ${factors.length}.` };
  }

  const seen = new Set();
  const out = [];
  for (const factor of factors) {
    if (!isObject(factor)) return { ok: false, reason: "Yếu tố ảnh hưởng không đúng định dạng." };
    const name = factor.feature_name;
    if (!isText(name) || !Object.prototype.hasOwnProperty.call(FEATURE_LABELS, name)) {
      return { ok: false, reason: `Tên đặc trưng không xác định: ${String(name)}.` };
    }
    if (seen.has(name)) return { ok: false, reason: `Đặc trưng bị lặp: ${name}.` };
    seen.add(name);

    if (!isFiniteNumber(factor.contribution_log_raw)) {
      return { ok: false, reason: `Đóng góp của "${name}" không phải số hợp lệ.` };
    }
    const display = factor.contribution_log_display === undefined
      ? factor.contribution_log_raw
      : factor.contribution_log_display;
    if (!isFiniteNumber(display)) {
      return { ok: false, reason: `Giá trị hiển thị của "${name}" không hợp lệ.` };
    }
    if (factor.multiplicative_factor !== undefined
        && !isPositiveFinite(factor.multiplicative_factor)) {
      return { ok: false, reason: `Hệ số nhân của "${name}" không hợp lệ.` };
    }
    const expectedDirection = directionOf(factor.contribution_log_raw);
    if (factor.direction !== undefined) {
      const expected = expectedDirection === "increase" ? "INCREASE"
        : expectedDirection === "decrease" ? "DECREASE" : "NEUTRAL";
      if (factor.direction !== expected) {
        return { ok: false, reason: `Hướng đóng góp của "${name}" không khớp dấu.` };
      }
    }
    const expectedGroup = FEATURE_GROUPS[name];
    if (factor.group !== undefined && factor.group !== expectedGroup) {
      return { ok: false, reason: `Nhóm của "${name}" không khớp lược đồ.` };
    }
    const state = factor.input_state;
    if (!isText(state) || !Object.prototype.hasOwnProperty.call(PROVENANCE_LABELS, state)) {
      return { ok: false, reason: `Nguồn gốc của "${name}" không hợp lệ.` };
    }
    const provenanceState = provenanceByName.get(name);
    if (!provenanceState) {
      return { ok: false, reason: `Thiếu nguồn gốc cho "${name}".` };
    }
    if (provenanceState !== state) {
      return { ok: false, reason: `Nguồn gốc của "${name}" không nhất quán.` };
    }
    for (const field of ["label_vi", "context_note_vi"]) {
      if (factor[field] !== undefined && !isText(factor[field])) {
        return { ok: false, reason: `Trường ${field} của "${name}" không phải văn bản.` };
      }
    }

    out.push({
      featureName: name,
      featureLabel: FEATURE_LABELS[name],
      label: isText(factor.label_vi) && factor.label_vi ? factor.label_vi : FEATURE_LABELS[name],
      raw: factor.contribution_log_raw,
      display,
      multiplicative: isFiniteNumber(factor.multiplicative_factor)
        ? factor.multiplicative_factor : null,
      direction: expectedDirection,
      directionLabel: directionLabel(factor.contribution_log_raw),
      group: expectedGroup,
      groupLabel: GROUP_LABELS[expectedGroup],
      inputState: state,
      provenance: PROVENANCE_LABELS[state],
      note: isText(factor.context_note_vi) ? factor.context_note_vi : "",
    });
  }
  return { ok: true, factors: out };
}

/**
 * Validate a raw explanation object.
 * Returns { status, reason?, view? } where view is ready for rendering.
 */
export function validateExplanation(raw, options = {}) {
  if (raw === null || raw === undefined) {
    return {
      status: STATUS.ABSENT,
      reason: "Không có phần giải thích cho lần định giá này.",
      view: null,
    };
  }
  if (!isObject(raw)) {
    return invalid("Dữ liệu giải thích không đúng định dạng.");
  }

  if (!isText(raw.explanation_version) || !SUPPORTED_VERSIONS.includes(raw.explanation_version)) {
    return invalid(`Phiên bản giải thích không được hỗ trợ (${String(raw.explanation_version)}).`);
  }
  if (!UPSTREAM_STATUSES.includes(raw.status)) {
    return invalid(`Trạng thái giải thích không hợp lệ (${String(raw.status)}).`);
  }

  const limitations = textList(raw.limitations);
  if (limitations === null) return invalid("Danh sách hạn chế không hợp lệ.");

  if (raw.status === STATUS.UNAVAILABLE || raw.status === STATUS.NOT_SUPPORTED) {
    return {
      status: raw.status,
      reason: limitations[0] || "Mô hình không cung cấp được giải thích cho lần định giá này.",
      view: {
        status: raw.status,
        limitations,
        points: [],
        groups: [],
        factors: [],
        provenance: [],
        priceConsistent: true,
      },
    };
  }

  // ---- shared header validation for AVAILABLE and PARTIAL
  if (raw.method !== SUPPORTED_METHOD) {
    return invalid(`Phương pháp giải thích không được hỗ trợ (${String(raw.method)}).`);
  }
  if (raw.target !== SUPPORTED_TARGET) {
    return invalid(`Mục tiêu giải thích không được hỗ trợ (${String(raw.target)}).`);
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

  if (raw.status === STATUS.PARTIAL) {
    const provenance = provenanceEntries(raw);
    return {
      status: STATUS.PARTIAL,
      reason: "Chỉ một phần giải thích cho lần định giá này.",
      view: {
        status: STATUS.PARTIAL,
        limitations,
        points: [],
        groups: [],
        factors: [],
        provenance: provenance || [],
        margin: raw.predicted_margin_log,
        base: raw.base_value_log,
        priceConsistent: true,
      },
    };
  }

  // ---- AVAILABLE: everything below is required
  const calibration = raw.calibration;
  if (!isObject(calibration)) return invalid("Thiếu thông tin hiệu chỉnh giá.");
  if (!isPositiveFinite(calibration.factor)) {
    return invalid("Hệ số hiệu chỉnh không hợp lệ.");
  }
  if (!isText(calibration.policy) || !calibration.policy.trim()) {
    return invalid("Chính sách hiệu chỉnh không hợp lệ.");
  }
  if (!SUPPORTED_CALIBRATION_POLICIES.includes(calibration.policy)) {
    return invalid(`Chính sách hiệu chỉnh không được hỗ trợ (${calibration.policy}).`);
  }
  // The adjusted price is an authoritative VND amount: it must satisfy the same exact-integer
  // contract as the prediction, otherwise an invalid value would make adjustedDigits null and
  // silently bypass the consistency comparison.
  if (vndDigits(calibration.adjusted_price_vnd) === null) {
    return invalid("Giá sau hiệu chỉnh không hợp lệ.");
  }
  // V1.3 always emits both prices; a payload without them is not a complete explanation
  for (const [key, value] of [["base_price_vnd", raw.base_price_vnd],
    ["naive_price_vnd", raw.naive_price_vnd]]) {
    if (!isNonNegativeFinite(value)) {
      return invalid(`Giá trị ${key} không hợp lệ.`);
    }
  }
  if (!isFiniteNumber(raw.other_contribution_log)) {
    return invalid("Thiếu đóng góp của các yếu tố còn lại.");
  }
  if (!isObject(raw.grouped_contributions)) return invalid("Thiếu tổng hợp theo nhóm.");

  const provenance = provenanceEntries(raw);
  if (!provenance) {
    return invalid("Nguồn gốc đặc trưng không đầy đủ hoặc không hợp lệ.");
  }
  const provenanceByName = new Map(provenance.map((item) => [item.featureName, item.state]));

  const factorResult = validateFactors(raw, provenanceByName);
  if (!factorResult.ok) return invalid(factorResult.reason);
  const factors = factorResult.factors;

  const topSum = factors.reduce((total, factor) => total + factor.raw, 0);
  if (!Number.isFinite(topSum)) return invalid("Tổng đóng góp không hữu hạn.");

  const groupResult = validateGroups(raw, topSum);
  if (!groupResult.ok) return invalid(groupResult.reason);

  const reconstructed = raw.base_value_log + topSum + raw.other_contribution_log;
  if (!Number.isFinite(reconstructed)) return invalid("Không thể tính lại kết quả.");
  const tolerance = RECONSTRUCTION_TOLERANCE * Math.max(1, Math.abs(raw.predicted_margin_log));
  if (Math.abs(raw.predicted_margin_log - reconstructed) > tolerance) {
    return invalid("Không thể kiểm chứng lại kết quả từ các đóng góp.");
  }

  // optional consistency check against the authoritative prediction being displayed
  // Exact integer equality: the same VND price must be the same integer, and one VND apart is a
  // different prediction. Digit comparison keeps large values exact.
  const suppliedDigits = options.priceVnd === undefined || options.priceVnd === null
    ? null : vndDigits(options.priceVnd);
  const adjustedDigits = vndDigits(calibration.adjusted_price_vnd);
  // A supplied point price that cannot be normalised is not verifiable, so it must never be
  // reported as consistent.
  const suppliedUnusable = options.priceVnd !== undefined && options.priceVnd !== null
    && suppliedDigits === null;
  const priceConsistent = suppliedUnusable
    ? false
    : !(suppliedDigits !== null && adjustedDigits !== null
      && suppliedDigits !== adjustedDigits);

  const groups = Object.entries(raw.grouped_contributions)
    .map(([name, value]) => ({
      name,
      label: GROUP_LABELS[name],
      value,
      direction: directionOf(value),
      directionLabel: directionLabel(value),
    }))
    .sort((a, b) => Math.abs(b.value) - Math.abs(a.value));

  const flagged = provenance.filter((item) => FLAGGED_STATES.includes(item.state));

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
        policy: calibration.policy,
        factor: calibration.factor,
        adjustedPriceVnd: calibration.adjusted_price_vnd,
      },
      factors,
      groups,
      other: raw.other_contribution_log,
      provenance,
      flagged,
      limitations,
      priceConsistent,
      waterfall: {
        base: raw.base_value_log,
        steps: factors.map((factor) => ({
          name: factor.featureName,
          label: factor.featureLabel,
          value: factor.raw,
        })),
        other: raw.other_contribution_log,
        total: reconstructed,
        margin: raw.predicted_margin_log,
        residual: Math.abs(raw.predicted_margin_log - reconstructed),
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
