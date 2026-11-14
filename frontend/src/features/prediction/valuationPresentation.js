const RAW_FEATURE_LABELS = {
  subtype_villa: "Loại nhà: Biệt thự",
  house_subtype_villa: "Loại nhà: Biệt thự",
  subtype_house_c4: "Loại nhà: Nhà cấp 4",
  house_subtype_house_c4: "Loại nhà: Nhà cấp 4",
  subtype_house: "Loại nhà",
  access_alley: "Lối vào kiệt/hẻm",
  access_frontage: "Lối vào mặt tiền",
  ward: "Phường/Xã",
  raw_street_name: "Tên tuyến đường",
  street_name: "Tên tuyến đường",
  road_width: "Độ rộng đường vào",
  frontage_width: "Bề ngang mặt tiền",
  area: "Diện tích đất/sàn",
  area_sqm: "Diện tích",
  normalized_type: "Loại tài sản",
  district: "Quận/Huyện",
  raw_project_name: "Dự án bất động sản",
  project_name: "Dự án bất động sản",
  raw_bedroom_count: "Số phòng ngủ",
  raw_bathroom_count: "Số phòng tắm",
  bathroom_count: "Số phòng tắm",
  raw_floor_count: "Số tầng",
  floor_count: "Số tầng",
  rooms: "Số phòng ngủ",
  floors_claim: "Số tầng nhà",
  location_feature: "Địa bàn",
};

const MISSING_FEATURE_LABELS = {
  ward_source: "Phường/xã theo tin",
  bedroom_count: "Số phòng ngủ",
  bathroom_count: "Số phòng tắm",
  floor_count: "Số tầng",
  road_width: "Độ rộng đường vào",
  frontage_width: "Bề ngang mặt tiền",
  street_name: "Tên tuyến đường",
  project_name: "Dự án bất động sản",
};

function isMissing(value) {
  return value === null || value === undefined || String(value).trim() === "";
}

export function featureLabel(featureName, fallback = "") {
  return RAW_FEATURE_LABELS[featureName] || (fallback || featureName || "Đặc trưng");
}

export function shapFactorLabel(factor, featuresUsed = {}) {
  const name = factor?.feature_name || "";
  let label = featureLabel(name, factor?.label);
  if (name === "ward" && isMissing(featuresUsed.ward)) label += " (đang thiếu)";
  if (name === "raw_street_name" && isMissing(featuresUsed.street_name)) label += " (không có trong input)";
  if (name === "access_alley" && featuresUsed.access_type === "frontage") label += " (không áp dụng cho input)";
  if ((name === "road_width" || name === "frontage_width") && !isMissing(featuresUsed[name])
      && !["user", "verified"].includes(featuresUsed[`${name}_source`])) {
    label += " (suy ra từ lối vào)";
  }
  return label;
}

export function normalizeShapFactors(explanation, featuresUsed = {}) {
  const factors = explanation?.top_factors;
  if (!Array.isArray(factors)) return [];
  return factors.filter((factor) => factor && Number.isFinite(Number(factor.shap_value)) && Number.isFinite(Number(factor.impact_pct)))
    .map((factor) => ({
      ...factor,
      displayLabel: shapFactorLabel(factor, featuresUsed),
      displayImpact: `${Number(factor.impact_pct) > 0 ? "+" : ""}${Number(factor.impact_pct).toFixed(2)}%`,
      direction: Number(factor.shap_value) >= 0 ? "increase" : "decrease",
    }));
}

export function missingFeatureLabels(features = []) {
  if (!Array.isArray(features)) return [];
  return [...new Set(features.map((name) => MISSING_FEATURE_LABELS[name] || name))];
}

export function v13AssumptionNotes(featuresUsed = {}) {
  const notes = [];
  const realSource = (value) => ["user", "verified"].includes(value);
  if (!isMissing(featuresUsed.road_width) && !realSource(featuresUsed.road_width_source)) {
    notes.push(`Độ rộng đường ${Number(featuresUsed.road_width).toLocaleString("vi-VN")} m được suy ra từ lối vào, không phải số đo thực tế.`);
  }
  if (!isMissing(featuresUsed.frontage_width) && !realSource(featuresUsed.frontage_width_source)) {
    notes.push(`Bề ngang mặt tiền ${Number(featuresUsed.frontage_width).toLocaleString("vi-VN")} m được suy ra từ lối vào, không phải số đo thực tế.`);
  }
  if (isMissing(featuresUsed.ward)) {
    notes.push("Phường/xã chưa được cung cấp; mô hình dùng trạng thái thiếu, không tự suy ra phường.");
  }
  return notes;
}
