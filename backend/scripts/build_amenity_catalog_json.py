"""Build structured danang_amenity_catalog_v1.json for Spring Boot AmenityCatalogService.

Reads:
- .scratch/tinix-integration/step19-4-1c/amenity_scores_by_area.csv
- .scratch/tinix-integration/step19-4-1c/poi_coverage_analysis.csv
- .scratch/tinix-integration/step19-4-1c/spatial_analysis_metrics.json

Outputs:
- backend/src/main/resources/amenity/danang_amenity_catalog_v1.json
- .scratch/tinix-integration/step19-4-1d/danang_amenity_catalog_v1.json
"""
import csv
import os
import json
import re
import unicodedata
from pathlib import Path

ROOT = Path(os.environ.get("SMARTPROP_ROOT", Path(__file__).resolve().parents[2]))
STEP_1C = ROOT / ".scratch/tinix-integration/step19-4-1c"
STEP_1D = ROOT / ".scratch/tinix-integration/step19-4-1d"
RES_DIR = ROOT / "backend/src/main/resources/amenity"

score_csv = STEP_1C / "amenity_scores_by_area.csv"
cov_csv = STEP_1C / "poi_coverage_analysis.csv"
metrics_json = STEP_1C / "spatial_analysis_metrics.json"

with open(score_csv, encoding="utf-8") as f:
    score_rows = list(csv.DictReader(f))

with open(cov_csv, encoding="utf-8") as f:
    cov_rows = list(csv.DictReader(f))

cov_map = {r["area_name"]: r for r in cov_rows}

def slugify(text):
    text = text.replace("đ", "d").replace("Đ", "d")
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")
    text = re.sub(r"[^\w\s-]", "", text).strip().lower()
    return re.sub(r"[-\s]+", "-", text)

catalog_areas = []

for s in score_rows:
    area_name = s["area_name"]
    level = s["area_level"]
    parent_dist = s["parent_district"]
    cov = cov_map.get(area_name, {})

    # Generate unique areaId
    clean_slug = slugify(area_name)
    area_id = f"{level.lower()}-{clean_slug}"

    # Parse key evidence POIs into structured objects
    ev_raw = s.get("key_evidence_pois", "")
    evidence_items = []
    if ev_raw:
        parts = [p.strip() for p in ev_raw.split("|") if p.strip()]
        for p in parts:
            m = re.match(r"^(.*?)\s*\(([A-Z_]+)\)$", p)
            if m:
                poi_name, poi_cat = m.group(1).strip(), m.group(2).strip()
                basis = "DIRECT_WARD_EVIDENCE" if level == "WARD" and "Thừa hưởng" not in poi_name else ("CORRIDOR_DIRECT" if level == "CORRIDOR" else "DISTRICT_FACILITY")
                evidence_items.append({
                    "name": poi_name,
                    "category": poi_cat,
                    "attributionBasis": basis
                })
            else:
                basis = "DISTRICT_SHARED_AMENITY" if "Thừa hưởng" in p else "AREA_GENERAL"
                evidence_items.append({
                    "name": p,
                    "category": "SHARED",
                    "attributionBasis": basis
                })

    area_km2 = None
    try:
        area_km2 = float(cov.get("area_km2", 0))
    except (ValueError, TypeError):
        pass

    density = None
    try:
        density = float(cov.get("density_per_km2", 0))
    except (ValueError, TypeError):
        pass

    area_obj = {
        "areaId": area_id,
        "areaLevel": level,
        "areaName": area_name,
        "parentDistrict": parent_dist,
        "livingScore": float(s["living_score"]),
        "categoryScores": {
            "essentials": float(s["essentials_score"]),
            "education": float(s["education_score"]),
            "healthcare": float(s["healthcare_score"]),
            "transit": float(s["transit_score"]),
            "recreation": float(s["recreation_score"]),
        },
        "confidence": float(s["confidence"]),
        "diversityIndex": float(s.get("diversity_index", 0.5)),
        "sampleListingCount": int(s.get("sample_listing_count", 0)),
        "poiCounts": {
            "total": int(cov.get("total_pois", 0)),
            "school": int(cov.get("school_cnt", 0)),
            "hospital": int(cov.get("hospital_cnt", 0)),
            "pharmacy": int(cov.get("pharmacy_cnt", 0)),
            "market": int(cov.get("market_cnt", 0)),
            "supermarket": int(cov.get("supermarket_cnt", 0)),
            "park": int(cov.get("park_cnt", 0)),
            "beach": int(cov.get("beach_cnt", 0)),
            "transit": int(cov.get("transport_cnt", 0)),
        },
        "areaKm2": area_km2,
        "densityPerKm2": density,
        "completenessTier": cov.get("completeness_tier", "MEDIUM"),
        "hasCriticalGaps": cov.get("has_critical_amenity_gaps", "NO"),
        "poiEvidence": evidence_items,
        "amenitySummary": s.get("amenity_summary", ""),
        "sources": [
            "OpenStreetMap Overpass API (ODbL 1.0)",
            "Geoapify Places API (ODbL 1.0 via Geoapify)",
            "SmartProp Curated Anchor Facilities"
        ],
        "dataLimitations": [
            "0 bản ghi TiniX AI có tọa độ GPS số nhà; SmartProp không tính khoảng cách mét từ từng bất động sản.",
            "Điểm tiện ích phản ánh hạ tầng đã được số hóa; khu vực thiếu POI không đồng nghĩa ngoài thực tế không có tiện ích dân sinh.",
            "Phường/xã kế thừa các tiện ích cấp vùng của quận chủ quản (bệnh viện đa khoa, bến xe, chợ đầu mối trong bán kính 1-2km)."
        ]
    }
    catalog_areas.append(area_obj)

catalog_payload = {
    "catalogVersion": "DANANG_AMENITY_CATALOG_V1_2026_11_03",
    "jurisdiction": "Thành phố Đà Nẵng",
    "totalEffectivePois": 1323,
    "totalAreasAnalyzed": len(catalog_areas),
    "countsByLevel": {
        "DISTRICT": sum(1 for a in catalog_areas if a["areaLevel"] == "DISTRICT"),
        "WARD": sum(1 for a in catalog_areas if a["areaLevel"] == "WARD"),
        "CORRIDOR": sum(1 for a in catalog_areas if a["areaLevel"] == "CORRIDOR"),
    },
    "livingPurposeWeights": {
        "essentials": 0.25,
        "education": 0.20,
        "healthcare": 0.20,
        "transit": 0.15,
        "recreation": 0.20,
    },
    "areas": catalog_areas
}

# Write to both target locations
catalog_json_str = json.dumps(catalog_payload, indent=2, ensure_ascii=False)
(RES_DIR / "danang_amenity_catalog_v1.json").write_text(catalog_json_str, encoding="utf-8")
(STEP_1D / "danang_amenity_catalog_v1.json").write_text(catalog_json_str, encoding="utf-8")

print(f"Generated danang_amenity_catalog_v1.json successfully: {len(catalog_areas)} areas saved to {RES_DIR} and {STEP_1D}.")
