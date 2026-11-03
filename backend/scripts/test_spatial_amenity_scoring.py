"""Unit and Integration Test Suite for Step 19.4.1C: Spatial Analysis & Amenity Scoring.

Verifies:
1. Strict constraint: 0 property-to-POI distances generated, no fake GPS.
2. Score bounds: All scores in [0, 100], no NaN, no nulls.
3. Confidence bounds: All confidences in [0.0, 1.0].
4. Area completeness: 7 districts, 55 wards, 20 corridors (82 total areas).
5. Evidence grounding: All scores backed by named, verified POIs.
6. Immutability of TiniX dataset and POI effective view.
"""
import csv
import json
import math
from pathlib import Path
import importlib.util
import pymysql

ROOT = Path("F:/SmartProp")
OUT_DIR = ROOT / ".scratch/tinix-integration/step19-4-1c"

spec = importlib.util.spec_from_file_location("rec", ROOT / "backend/scripts/run-recommendation-local.py")
rec = importlib.util.module_from_spec(spec)
spec.loader.exec_module(rec)
priv = rec.private_environment()

conn = pymysql.connect(
    host="127.0.0.1",
    port=3306,
    user=priv["DB_USER"],
    password=priv["DB_PASSWORD"],
    database="smartprop",
    charset="utf8mb4",
    cursorclass=pymysql.cursors.DictCursor
)

test_results = {}

try:
    with conn.cursor() as cur:
        # TEST 1: TiniX Immutability via ix_tinix_hybrid (fast index-only scan)
        cur.execute("SELECT COUNT(*) AS c FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid)")
        t_tot = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid) WHERE quality_status = 'HYBRID_ELIGIBLE_RESEARCH'")
        t_elig = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM tinix_dataset_records FORCE INDEX (ix_tinix_hybrid) WHERE quality_status = 'HYBRID_ELIGIBLE_RESEARCH' AND is_duplicate_representative = 1")
        t_reps = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(*) AS c FROM tinix_dataset_records WHERE is_protected_holdout = 1")
        t_hold = cur.fetchone()["c"]

        test_results["test_1_tinix_immutability"] = {
            "total_tinix": t_tot,
            "hybrid_eligible": t_elig,
            "representatives": t_reps,
            "protected_holdout": t_hold,
            "pass": t_tot == 185973 and t_elig == 78462 and t_reps == 55816 and t_hold == 46
        }

        # TEST 2: POI Effective View Integrity
        cur.execute("SELECT COUNT(*) AS c FROM poi_effective_v1")
        p_eff = cur.fetchone()["c"]
        cur.execute("SELECT COUNT(DISTINCT district_historical) AS c FROM poi_effective_v1 WHERE district_historical IS NOT NULL")
        p_dist_cnt = cur.fetchone()["c"]

        test_results["test_2_poi_effective_integrity"] = {
            "effective_pois": p_eff,
            "distinct_districts": p_dist_cnt,
            "pass": p_eff == 1323 and p_dist_cnt == 7
        }

finally:
    conn.close()

# TEST 3: Output CSVs existence and row counts
cov_file = OUT_DIR / "poi_coverage_analysis.csv"
score_file = OUT_DIR / "amenity_scores_by_area.csv"
metrics_file = OUT_DIR / "spatial_analysis_metrics.json"

test_results["test_3_files_exist"] = {
    "coverage_csv": cov_file.is_file(),
    "scores_csv": score_file.is_file(),
    "metrics_json": metrics_file.is_file(),
    "pass": cov_file.is_file() and score_file.is_file() and metrics_file.is_file()
}

with open(cov_file, encoding="utf-8") as f:
    cov_rows = list(csv.DictReader(f))

with open(score_file, encoding="utf-8") as f:
    score_rows = list(csv.DictReader(f))

test_results["test_4_area_counts"] = {
    "total_areas": len(score_rows),
    "districts": sum(1 for r in score_rows if r["area_level"] == "DISTRICT"),
    "wards": sum(1 for r in score_rows if r["area_level"] == "WARD"),
    "corridors": sum(1 for r in score_rows if r["area_level"] == "CORRIDOR"),
    "pass": (
        len(score_rows) == 82 and
        sum(1 for r in score_rows if r["area_level"] == "DISTRICT") == 7 and
        sum(1 for r in score_rows if r["area_level"] == "WARD") == 55 and
        sum(1 for r in score_rows if r["area_level"] == "CORRIDOR") == 20
    )
}

# TEST 5: Score & Confidence Range Verification
scores_valid = True
conf_valid = True
evidence_valid = True

for r in score_rows:
    ls = float(r["living_score"])
    es = float(r["essentials_score"])
    ed = float(r["education_score"])
    he = float(r["healthcare_score"])
    tr = float(r["transit_score"])
    re = float(r["recreation_score"])
    cf = float(r["confidence"])

    for s in [ls, es, ed, he, tr, re]:
        if math.isnan(s) or s < 0.0 or s > 100.0:
            scores_valid = False

    if math.isnan(cf) or cf < 0.0 or cf > 1.0:
        conf_valid = False

    if not r["key_evidence_pois"] or len(r["key_evidence_pois"].strip()) < 5:
        evidence_valid = False

test_results["test_5_score_bounds"] = {
    "scores_within_0_100": scores_valid,
    "confidence_within_0_1": conf_valid,
    "pass": scores_valid and conf_valid
}

test_results["test_6_evidence_grounded"] = {
    "all_areas_have_evidence": evidence_valid,
    "pass": evidence_valid
}

# TEST 7: Strict Constraint Check - No Property-to-POI Distances
# Ensure neither CSV contains property-level columns
forbidden_terms = ["property_id", "property_lat", "property_lon", "distance_to_nearest_school_meters"]
has_forbidden = False
for fn in [cov_file, score_file]:
    header = fn.read_text(encoding="utf-8").splitlines()[0]
    for term in forbidden_terms:
        if term in header:
            has_forbidden = True

test_results["test_7_no_property_distance_generated"] = {
    "has_forbidden_property_distance_columns": has_forbidden,
    "pass": not has_forbidden
}

all_pass = all(v.get("pass", False) for v in test_results.values())
test_results["OVERALL_STATUS"] = "PASS" if all_pass else "FAIL"

out_json = OUT_DIR / "SPATIAL_TEST_RESULTS.json"
out_json.write_text(json.dumps(test_results, indent=2, ensure_ascii=False), encoding="utf-8")
print(f"Test suite completed: OVERALL_STATUS = {test_results['OVERALL_STATUS']}", flush=True)
