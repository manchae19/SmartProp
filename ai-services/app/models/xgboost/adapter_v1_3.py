"""Schema translation adapter between SmartProp V6 requests and XGBoost V1.3.

Provides bidirectional mapping and field normalization for shadow evaluation
and internal testing.
"""
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


def resolve_district(location_feature: str, ward: str | None = None) -> str:
    """Extract and canonicalize Da Nang district name from location text."""
    combined = f"{location_feature or ''} {ward or ''}".strip()
    norm = unicodedata.normalize("NFC", combined).casefold()

    # Exact direct match
    for key, canonical in DISTRICT_CANONICAL.items():
        if key in norm:
            return canonical

    # Regex search with diacritic fallback
    for pattern, canonical in DISTRICT_SEARCH:
        if pattern.search(combined):
            return canonical

    # Safe default within Da Nang core
    return "Hải Châu"


def map_v6_to_v1_3(v6_request: Dict[str, Any]) -> Dict[str, Any]:
    """Convert a SmartProp V6 ValuationRequest dictionary into V1.3 format."""
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
    district = resolve_district(loc_feature, ward_val)

    # Clean ward string if needed
    cleaned_ward = ward_val
    if cleaned_ward:
        cleaned_ward = re.sub(r"^(phường|xã|thị trấn)\s+", "", str(cleaned_ward), flags=re.IGNORECASE).strip()
        if cleaned_ward.lower() in ("không xác định", "đang cập nhật", "none", "nan", ""):
            cleaned_ward = None

    # 3. Build V1.3 record
    record = {
        "area": float(v6_request.get("area_sqm", 0.0)),
        "normalized_type": norm_type,
        "district": district,
        "ward": cleaned_ward,
        "street_name": v6_request.get("street_name"),
        "project_name": v6_request.get("project_name"),
        "floor_count": v6_request.get("floors"),
        "bedroom_count": v6_request.get("rooms"),
        "bathroom_count": v6_request.get("bathrooms"),
        "house_direction": v6_request.get("house_direction"),
        "balcony_direction": v6_request.get("balcony_direction"),
    }

    # 4. Map access type to physical metrics
    access = v6_request.get("access_type")
    if access == "frontage":
        record["road_width"] = 10.0
        record["frontage_width"] = 5.0
    elif access == "alley":
        record["road_width"] = 3.0
        record["frontage_width"] = 4.0

    return record
