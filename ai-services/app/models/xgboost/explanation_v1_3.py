"""WP-04 — additive explanation contract for XGBoost V1.3 (reviewed).

Built from SHAP values the predictor already computed: the model is never run a second time and
the prediction is never changed. Everything is validated before being reported as AVAILABLE;
any inconsistency downgrades the explanation to UNAVAILABLE while the price stays valid.

Scale: contributions are in **log1p price** space. Not VND, not a percentage, not causal.
A VND waterfall can be derived from ordered contributions with
    p_k = (p_{k-1} + 1) * exp(phi_k) - 1
but it is order dependent and is not a native SHAP attribution in VND.
"""
import math
from typing import Any, Dict, Iterable, List, Optional, Sequence

EXPLANATION_VERSION = "1.0"
TOP_K = 6
ADDITIVITY_REL_TOL = 1e-5

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

NOT_APPLICABLE = {
    "LAND": {"bedroom_count", "has_bedroom", "floor_count", "has_floor",
             "bathroom_count", "has_bathroom", "raw_house_direction"},
    "APARTMENT": {"floor_count", "has_floor", "frontage_width", "has_frontage",
                  "road_width", "has_road_width", "raw_house_direction"},
}

NOTE_VI = {
    "OBSERVED": "Thông tin do người dùng cung cấp.",
    "DERIVED": "Đặc điểm này được hệ thống tính từ dữ liệu đầu vào, không phải thông tin xác minh trực tiếp.",
    "DEFAULTED": "Giá trị này do hệ thống giả định, không phải số liệu người dùng cung cấp.",
    "MISSING": "Thông tin này chưa được cung cấp; mô hình dùng cơ chế xử lý dữ liệu thiếu.",
    "MISSING_INVALID": "Giá trị đã nhập không hợp lệ nên không được sử dụng; mô hình xử lý như dữ liệu thiếu.",
    "NOT_APPLICABLE": "Đặc điểm này không áp dụng cho loại bất động sản đang định giá.",
    "UNKNOWN_CATEGORY": "Giá trị này chưa có trong danh mục mô hình đã học nên được xử lý là chưa xác định.",
    "UNVERIFIED": "Chưa đủ căn cứ để xác định nguồn gốc của đặc điểm này.",
}


def is_missing(value: Any) -> bool:
    """Missing detection that also covers numpy/pandas scalars (np.float32 NaN, pd.NA)."""
    if value is None:
        return True
    if isinstance(value, str):
        return value == "__MISSING__"
    try:
        if value != value:            # NaN of any dtype, including numpy.float32
            return True
    except (TypeError, ValueError):    # pd.NA raises here
        return True
    try:
        return bool(value is None)
    except Exception:                  # noqa: BLE001
        return False


def is_finite_number(value: Any) -> bool:
    try:
        return math.isfinite(float(value))
    except (TypeError, ValueError):
        return False


def classify_provenance(feature: str, encoded_value: Any, provided: Iterable[str],
                        model_type: str, defaulted: Iterable[str] = (),
                        raw_present: bool = True) -> str:
    """State from the ACTUAL encoded value. Unknown provenance is never silently DERIVED."""
    provided = set(provided or ())
    defaulted = set(defaulted or ())
    if is_missing(encoded_value):
        if feature in NOT_APPLICABLE.get(model_type, set()):
            return "NOT_APPLICABLE"
        if feature in DERIVED_FEATURES:
            return "DERIVED"
        source = FEATURE_SOURCE.get(feature)
        if source and raw_present and source in provided:
            return "MISSING_INVALID"      # caller sent a value, adapter rejected it
        return "MISSING"
    if encoded_value == "__UNKNOWN__":
        return "UNKNOWN_CATEGORY"
    if feature in DEFAULTED_FEATURES or feature in defaulted:
        return "DEFAULTED"
    if feature in DERIVED_FEATURES:
        return "DERIVED"
    source = FEATURE_SOURCE.get(feature)
    if source and source in provided:
        return "OBSERVED"
    if source:
        return "UNVERIFIED"               # adapter filled it, source not documented
    return "UNVERIFIED"


DEFAULTED_FEATURES: set = set()           # replaced per call when adapter reports assumptions


def validate_explanation(*, features: Sequence[str], contributions: Sequence[float],
                         base_log: float, margin_log: float, calibration_factor: float,
                         groups: Dict[str, float], ordered: Sequence[str]) -> List[str]:
    """Return the list of problems. Empty list means the explanation is trustworthy."""
    problems: List[str] = []
    if len(contributions) != len(features):
        problems.append(f"dimension mismatch: {len(contributions)} != {len(features)}")
        return problems
    if len(set(features)) != len(features):
        problems.append("duplicate feature names")
    if list(ordered) != list(features):
        problems.append("feature order differs from active schema")
    for value in contributions:
        if not is_finite_number(value):
            problems.append("non-finite contribution")
            break
    for name, value in (("base_log", base_log), ("margin_log", margin_log),
                        ("calibration_factor", calibration_factor)):
        if not is_finite_number(value):
            problems.append(f"non-finite {name}")
    missing_groups = [f for f in features if f not in FEATURE_GROUPS]
    if missing_groups:
        problems.append(f"missing group mapping: {missing_groups}")
    if abs(sum(groups.values()) - sum(contributions)) > 1e-6 * max(1.0, abs(sum(contributions))):
        problems.append("group totals do not reproduce the contribution sum")
    expected = margin_log - base_log
    if abs(sum(contributions) - expected) > ADDITIVITY_REL_TOL * max(1.0, abs(expected)):
        problems.append("base + contributions do not reproduce the margin")
    return problems


def build_explanation(*, features: Sequence[str], contributions: Sequence[float],
                      base_log: float, margin_log: float, naive_price_vnd: int,
                      calibration_policy: str, calibration_factor: float,
                      calibrated_price_vnd: int, encoded_row: Dict[str, Any],
                      provided: Sequence[str], model_type: str,
                      defaulted: Sequence[str] = (),
                      raw_invalid: Sequence[str] = (),
                      warnings: Optional[List[str]] = None) -> Dict[str, Any]:
    values = [float(c) for c in contributions]
    pairs = list(zip(features, values))
    ranked = sorted(pairs, key=lambda item: (-abs(item[1]), item[0]))
    top = ranked[:TOP_K]

    groups: Dict[str, float] = {}
    for name, value in pairs:
        group = FEATURE_GROUPS.get(name)
        if group:
            groups[group] = groups.get(group, 0.0) + value

    problems = validate_explanation(
        features=list(features), contributions=values, base_log=base_log,
        margin_log=margin_log, calibration_factor=calibration_factor,
        groups=groups, ordered=list(encoded_row.keys()))
    if problems:
        return unavailable_explanation("Không thể xác thực giải thích: " + "; ".join(problems[:3]))

    defaulted = set(defaulted or ())
    raw_invalid = set(raw_invalid or ())
    provided = set(provided or ())

    # Provenance for EVERY feature, not only the top-K ones.
    provenance = {}
    for name in features:
        state = classify_provenance(
            name, encoded_row.get(name), provided, model_type, defaulted,
            raw_present=name not in raw_invalid)
        provenance[name] = state

    factors = []
    for name, value in top:
        state = provenance[name]
        factors.append({
            "feature_name": name,
            "label_vi": LABELS_VI.get(name, name),
            "input_state": state,
            "contribution_log_raw": value,
            "contribution_log_display": round(value, 4),
            "multiplicative_factor": round(math.exp(value), 6),
            "direction": "INCREASE" if value > 0 else ("DECREASE" if value < 0 else "NEUTRAL"),
            "group": FEATURE_GROUPS.get(name, "OTHER"),
            "context_note_vi": NOTE_VI.get(state, ""),
        })

    top_sum = sum(v for _n, v in top)
    limitations = list(warnings or [])
    flagged = sorted({s for s in provenance.values()
                      if s in ("MISSING", "MISSING_INVALID", "NOT_APPLICABLE",
                               "UNKNOWN_CATEGORY", "DEFAULTED", "UNVERIFIED")})
    if flagged:
        limitations.append(
            "Một số đặc điểm chưa được cung cấp, không áp dụng hoặc do hệ thống giả định; "
            "kết quả có thể bị ảnh hưởng bởi cơ chế xử lý dữ liệu thiếu.")
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
        "base_price_vnd": int(round(math.exp(float(base_log)) - 1.0)),
        "naive_price_vnd": int(naive_price_vnd),
        "calibration": {"policy": calibration_policy, "factor": float(calibration_factor),
                        "adjusted_price_vnd": int(calibrated_price_vnd)},
        "factors": factors,
        "other_contribution_log": float(sum(values) - top_sum),
        "grouped_contributions": {k: v for k, v in sorted(groups.items())},
        "feature_provenance": provenance,
        "limitations": limitations,
    }


def unavailable_explanation(reason: str) -> Dict[str, Any]:
    return {
        "explanation_version": EXPLANATION_VERSION,
        "status": "UNAVAILABLE",
        "method": "XGBOOST_NATIVE_TREESHAP",
        "target": "ASKING_PRICE_VND",
        "output_space": "LOG1P_PRICE_VND",
        "predicted_margin_log": None, "base_value_log": None, "base_price_vnd": None,
        "naive_price_vnd": None, "calibration": None, "factors": None,
        "other_contribution_log": None, "grouped_contributions": None,
        "feature_provenance": None, "limitations": [reason],
    }
