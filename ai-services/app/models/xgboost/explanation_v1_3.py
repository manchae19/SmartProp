"""WP-04 — additive explanation contract for XGBoost V1.3.

Builds the explanation object from values the predictor already computed (native TreeSHAP on
the active booster). It never runs the model a second time and never changes the prediction.

Scale reminder: contributions are in **log1p price** space. They are NOT VND and NOT a
percentage of market price. Group sums are signed; `sum(groups) == sum(all contributions)`.

A separate VND waterfall can be derived from the ordered contributions with
    p_k = (p_{k-1} + 1) * exp(phi_k) - 1
but that is order dependent and is not a native SHAP attribution in VND.
"""
from typing import Any, Dict, List, Optional, Sequence

EXPLANATION_VERSION = "1.0"
TOP_K = 6

FEATURE_GROUPS = {
    "area": "AREA", "frontage_sqrt_area_ratio": "AREA",
    "floor_count": "STRUCTURE", "bedroom_count": "STRUCTURE",
    "bathroom_count": "STRUCTURE", "has_floor": "STRUCTURE",
    "has_bedroom": "STRUCTURE", "has_bathroom": "STRUCTURE",
    "frontage_width": "ACCESS", "road_width": "ACCESS",
    "has_frontage": "ACCESS", "has_road_width": "ACCESS",
    "has_project": "PROJECT", "raw_project_name": "PROJECT",
    "has_street": "LOCATION", "has_ward": "LOCATION", "district": "LOCATION",
    "ward": "LOCATION", "raw_street_name": "LOCATION",
    "normalized_type": "PROPERTY_TYPE",
    "raw_house_direction": "DIRECTION", "raw_balcony_direction": "DIRECTION",
}

LABELS_VI = {
    "area": "Diện tích", "floor_count": "Số tầng", "frontage_width": "Chiều rộng mặt tiền",
    "road_width": "Chiều rộng đường", "bedroom_count": "Số phòng ngủ",
    "bathroom_count": "Số phòng tắm", "has_floor": "Có thông tin số tầng",
    "has_frontage": "Có thông tin mặt tiền", "has_road_width": "Có thông tin đường",
    "has_bedroom": "Có thông tin phòng ngủ", "has_bathroom": "Có thông tin phòng tắm",
    "has_project": "Có thông tin dự án", "has_street": "Có thông tin tuyến đường",
    "has_ward": "Có thông tin phường/xã",
    "frontage_sqrt_area_ratio": "Tỉ lệ mặt tiền trên căn bậc hai diện tích",
    "normalized_type": "Loại bất động sản", "district": "Quận/Huyện", "ward": "Phường/Xã",
    "raw_street_name": "Tuyến đường", "raw_project_name": "Dự án",
    "raw_house_direction": "Hướng nhà", "raw_balcony_direction": "Hướng ban công",
}

FEATURE_SOURCE = {
    "area": "area_sqm", "floor_count": "floors", "frontage_width": "frontage_width_m",
    "road_width": "road_width_m", "bedroom_count": "rooms", "bathroom_count": "bathrooms",
    "normalized_type": "category", "district": "location_feature", "ward": "ward",
    "raw_street_name": "street_name", "raw_project_name": "project_name",
    "raw_house_direction": "house_direction", "raw_balcony_direction": "balcony_direction",
}

DERIVED_FEATURES = {"has_floor", "has_frontage", "has_road_width", "has_bedroom",
                    "has_bathroom", "has_project", "has_street", "has_ward",
                    "frontage_sqrt_area_ratio"}

# Semantic non-applicability per model type.
NOT_APPLICABLE = {
    "LAND": {"bedroom_count", "has_bedroom", "floor_count", "has_floor",
             "bathroom_count", "has_bathroom", "raw_house_direction"},
    "APARTMENT": {"floor_count", "has_floor", "frontage_width", "has_frontage",
                  "road_width", "has_road_width", "raw_house_direction"},
}

NOTE_VI = {
    "OBSERVED": "Thông tin do người dùng cung cấp.",
    "DERIVED": "Đặc điểm này được hệ thống tính từ dữ liệu đầu vào, không phải thông tin xác minh trực tiếp.",
    "DEFAULTED": "Đặc điểm này do hệ thống điền mặc định, không do người dùng cung cấp.",
    "MISSING": "Thông tin này chưa được cung cấp; mô hình dùng cơ chế xử lý dữ liệu thiếu.",
    "NOT_APPLICABLE": "Đặc điểm này không áp dụng cho loại bất động sản đang định giá.",
    "UNKNOWN_CATEGORY": "Giá trị này chưa có trong danh mục mô hình đã học nên được xử lý là chưa xác định.",
    "UNVERIFIED": "Chưa đủ căn cứ để xác định nguồn gốc của đặc điểm này.",
}


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, float) and value != value:      # NaN
        return True
    return value == "__MISSING__"


def classify_provenance(feature: str, encoded_value: Any, provided: Sequence[str],
                        model_type: str) -> str:
    """State from the ACTUAL encoded value plus what the caller actually supplied."""
    if feature in DERIVED_FEATURES:
        return "DERIVED"
    if encoded_value == "__UNKNOWN__":
        return "UNKNOWN_CATEGORY"
    if _is_missing(encoded_value):
        return ("NOT_APPLICABLE" if feature in NOT_APPLICABLE.get(model_type, set())
                else "MISSING")
    source = FEATURE_SOURCE.get(feature)
    if source and source in provided:
        return "OBSERVED"
    if source:
        return "DERIVED"
    return "UNVERIFIED"


def build_explanation(*, features: Sequence[str], contributions: Sequence[float],
                      base_log: float, margin_log: float, naive_price_vnd: int,
                      calibration_policy: str, calibration_factor: float,
                      calibrated_price_vnd: int, encoded_row: Dict[str, Any],
                      provided: Sequence[str], model_type: str,
                      warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    """Full-precision explanation. `contributions` excludes the SHAP bias term."""
    values = [float(c) for c in contributions]
    pairs = list(zip(features, values))
    ranked = sorted(pairs, key=lambda item: (-abs(item[1]), item[0]))
    top = ranked[:TOP_K]
    everything = sum(values)
    top_sum = sum(v for _n, v in top)
    other = everything - top_sum

    factors = []
    for name, value in top:
        state = classify_provenance(name, encoded_row.get(name), provided, model_type)
        factors.append({
            "feature_name": name,
            "label_vi": LABELS_VI.get(name, name),
            "input_state": state,
            "contribution_log_raw": value,
            "contribution_log_display": round(value, 4),
            "multiplicative_factor": round(2.718281828459045 ** value, 6),
            "direction": "INCREASE" if value > 0 else ("DECREASE" if value < 0 else "NEUTRAL"),
            "group": FEATURE_GROUPS.get(name, "OTHER"),
            "context_note_vi": NOTE_VI.get(state, ""),
        })

    grouped: Dict[str, float] = {}
    for name, value in pairs:
        group = FEATURE_GROUPS.get(name)
        if group:
            grouped[group] = grouped.get(group, 0.0) + value

    missing_states = sorted({f["input_state"] for f in factors
                             if f["input_state"] in
                             ("MISSING", "NOT_APPLICABLE", "UNKNOWN_CATEGORY", "UNVERIFIED")})
    limitations = list(warnings or [])
    if missing_states:
        limitations.append(
            "Một số đặc điểm chưa được cung cấp hoặc không áp dụng; kết quả có thể bị ảnh hưởng "
            "bởi cơ chế xử lý dữ liệu thiếu của mô hình.")
    limitations.append(
        "Giải thích này mô tả hành vi của mô hình với dữ liệu đã nhập, không phải quan hệ nhân quả "
        "và không phải khoảng tin cậy.")

    return {
        "explanation_version": EXPLANATION_VERSION,
        "status": "AVAILABLE",
        "method": "XGBOOST_NATIVE_TREESHAP",
        "target": "ASKING_PRICE_VND",
        "output_space": "LOG1P_PRICE_VND",
        "predicted_margin_log": float(margin_log),
        "base_value_log": float(base_log),
        "base_price_vnd": int(round(2.718281828459045 ** float(base_log) - 1.0)),
        "naive_price_vnd": int(naive_price_vnd),
        "calibration": {
            "policy": calibration_policy,
            "factor": float(calibration_factor),
            "adjusted_price_vnd": int(calibrated_price_vnd),
        },
        "factors": factors,
        "other_contribution_log": float(other),
        "grouped_contributions": {k: v for k, v in sorted(grouped.items())},
        "limitations": limitations,
    }


def unavailable_explanation(reason: str) -> Dict[str, Any]:
    """Isolated failure: prediction stays valid, explanation is explicitly absent."""
    return {
        "explanation_version": EXPLANATION_VERSION,
        "status": "UNAVAILABLE",
        "method": "XGBOOST_NATIVE_TREESHAP",
        "target": "ASKING_PRICE_VND",
        "output_space": "LOG1P_PRICE_VND",
        "predicted_margin_log": None,
        "base_value_log": None,
        "base_price_vnd": None,
        "naive_price_vnd": None,
        "calibration": None,
        "factors": None,
        "other_contribution_log": None,
        "grouped_contributions": None,
        "limitations": [reason],
    }
