"""Schema translation adapter between SmartProp V6 requests and XGBoost V1.3.

Provides bidirectional mapping and field normalization for shadow evaluation
and internal testing.
"""
import os
import re
import unicodedata
from typing import Any, Dict

DA_NANG_DISTRICTS = [
    "Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn",
    "Cẩm Lệ", "Liên Chiểu", "Hòa Vang"
]

DISTRICT_CANONICAL = {
    unicodedata.normalize("NFC", d).casefold(): d for d in DA_NANG_DISTRICTS
}
# Also support unaccented variations
DISTRICT_SEARCH = [
    (re.compile(r"hai\s*chau|h\u1ea3i\s*ch\u00e2u", re.IGNORECASE), "Hải Châu"),
    (re.compile(r"thanh\s*khe|thanh\s*kh\u00ea", re.IGNORECASE), "Thanh Khê"),
    (re.compile(r"son\s*tra|s\u01a1n\s*tr\u00e0", re.IGNORECASE), "Sơn Trà"),
    (re.compile(r"ngu\s*hanh\s*son|ng\u0169\s*h\u00e0nh\s*s\u01a1n", re.IGNORECASE), "Ngũ Hành Sơn"),
    (re.compile(r"cam\s*le|c\u1ea9m\s*l\u1ec7", re.IGNORECASE), "Cẩm Lệ"),
    (re.compile(r"lien\s*chieu|li\u00ean\s*chi\u1ec3u", re.IGNORECASE), "Liên Chiểu"),
    (re.compile(r"hoa\s*vang|h\u00f2a\s*vang", re.IGNORECASE), "Hòa Vang"),
]


def canonical_district(value, vocabulary=None):
    """NFC + trim + casefold, then require an EXACT match against the model vocabulary.

    The vocabulary comes from the loaded artifact, so this cannot drift from what the
    model actually supports. Unknown input stays unknown: there is no default district.
    """
    cleaned = unicodedata.normalize("NFC", str(value or "")).strip()
    if not cleaned:
        return None
    if vocabulary:
        folded = cleaned.casefold()
        for entry in vocabulary:
            if unicodedata.normalize("NFC", str(entry)).casefold() == folded:
                return str(entry)
        return None
    return cleaned


def resolve_district(location_feature: str, ward: str | None = None, vocabulary=None) -> str | None:
    """Resolve the district from the validated location field ONLY.

    `ward` is deliberately NOT used to decide the district: a ward name must never be
    able to move a property into a different district. The parameter is kept for call
    compatibility and ignored.

    Returns None when the district cannot be resolved. There is no "safe default":
    silently pricing an unknown location as Hải Châu is exactly the bug this prevents.
    """
    if vocabulary:
        return canonical_district(location_feature, vocabulary)

    # Legacy research path (no artifact vocabulary supplied): district-only regex list,
    # still never falls back to a default district.
    normalized = unicodedata.normalize("NFC", str(location_feature or "")).strip()
    if not normalized:
        return None
    folded = normalized.casefold()
    for key, canonical in DISTRICT_CANONICAL.items():
        if key in folded:
            return canonical
    for pattern, canonical in DISTRICT_SEARCH:
        if pattern.search(normalized):
            return canonical
    return None


def real_feature_input_enabled() -> bool:
    """Real measurements are the default; legacy synthesis must be opted into.

    The legacy adapter invented road_width/frontage_width from access_type
    (frontage -> 10m/5m, alley -> 3m/4m). Those numbers were never measured, so
    serving them as model input misrepresents the property. Production now keeps
    unknown dimensions missing and lets the model's has_* indicators carry the
    absence. Set SMARTPROP_V1_3_REAL_FEATURES=false only to reproduce historical
    research runs.
    """
    return os.environ.get("SMARTPROP_V1_3_REAL_FEATURES", "true").strip().lower() in {"1", "true", "yes", "on"}


def map_v6_to_v1_3(v6_request: Dict[str, Any], use_real_features: bool | None = None,
                   district_vocabulary=None) -> Dict[str, Any]:
    """Convert a SmartProp V6 ValuationRequest dictionary into V1.3 format.

    use_real_features=False preserves the legacy behavior byte-for-byte (including
    synthetic road/frontage defaults). True passes only user/verified measurements and
    leaves unknown fields missing. It never invents dimensions.
    """
    if use_real_features is None:
        use_real_features = real_feature_input_enabled()
    category = v6_request.get("category", "")
    subtype = v6_request.get("house_subtype")

    # 1. Normalize Property Type
    if subtype == "villa":
        norm_type = "VILLA"
    elif category == "Nhà ở":
        norm_type = "HOUSE"
    elif category == "Đất nền":
        norm_type = "LAND"
    elif category == "Căn hộ chung cư":
        norm_type = "APARTMENT"
    else:
        norm_type = "HOUSE"

    # 2. Extract District from location_feature
    loc_feature = v6_request.get("location_feature", "")
    ward_val = v6_request.get("ward")
    # The district is decided by the validated location field alone. `ward` is a separate
    # feature and is never allowed to override it.
    district = resolve_district(loc_feature, vocabulary=district_vocabulary)
    if district_vocabulary is not None and district is None:
        raise ValueError(
            "unsupported_location: địa bàn không được mô hình hỗ trợ: " + str(loc_feature)
        )

    # Clean ward string if needed
    cleaned_ward = ward_val
    if cleaned_ward:
        cleaned_ward = re.sub(r"^(phường|xã|thị trấn)\s+", "", str(cleaned_ward), flags=re.IGNORECASE).strip()
        if cleaned_ward.lower() in ("không xác định", "đang cập nhật", "none", "nan", ""):
            cleaned_ward = None

    # 3. Build V1.3 record. Legacy mode intentionally ignores the new optional fields.
    record = {
        "area": float(v6_request.get("area_sqm", 0.0)),
        "normalized_type": norm_type,
        "district": district,
        "ward": cleaned_ward,
        "street_name": None if not use_real_features else v6_request.get("street_name"),
        "project_name": None if not use_real_features else v6_request.get("project_name"),
        "floor_count": v6_request.get("floors"),
        "bedroom_count": v6_request.get("rooms"),
        "bathroom_count": None if not use_real_features else v6_request.get("bathrooms"),
        "house_direction": None if not use_real_features else v6_request.get("house_direction"),
        "balcony_direction": None if not use_real_features else v6_request.get("balcony_direction"),
    }

    # 4. Legacy: synthesize physical metrics from access. Real mode: preserve only explicit measurements.
    access = v6_request.get("access_type")
    if use_real_features:
        record["road_width"] = v6_request.get("road_width_m")
        record["frontage_width"] = v6_request.get("frontage_width_m")
        record["road_width_source"] = (
            v6_request.get("road_width_source") or ("user" if record["road_width"] is not None else None)
        )
        record["frontage_width_source"] = (
            v6_request.get("frontage_width_source") or ("user" if record["frontage_width"] is not None else None)
        )
    else:
        if access == "frontage":
            record["road_width"] = 10.0
            record["frontage_width"] = 5.0
            record["road_width_source"] = "assumed"
            record["frontage_width_source"] = "assumed"
        elif access == "alley":
            record["road_width"] = 3.0
            record["frontage_width"] = 4.0
            record["road_width_source"] = "assumed"
            record["frontage_width_source"] = "assumed"
        else:
            record["road_width_source"] = None
            record["frontage_width_source"] = None

    return record
