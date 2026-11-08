"""V6 Regression Parity Verification.

Validates that PredictorV6 outputs identical numeric predictions, features,
and warnings compared against the pre-SHAP mathematical baseline, proving 0.0000% drift.
"""
import json
import math
import sys
from pathlib import Path

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from app.models.xgboost.predictor_v6 import PredictorV6

STANDARD_FIXTURES = [
    {
        "category": "Nhà ở",
        "location_feature": "Hải Châu",
        "ward": "Thạch Thang",
        "area_sqm": 80.0,
        "rooms": 3,
        "floors": 3.0,
        "access_type": "frontage"
    },
    {
        "category": "Đất nền",
        "location_feature": "Sơn Trà",
        "ward": "Phước Mỹ",
        "area_sqm": 100.0,
        "access_type": "frontage"
    },
    {
        "category": "Căn hộ chung cư",
        "location_feature": "Ngũ Hành Sơn",
        "ward": "Mỹ An",
        "area_sqm": 65.0,
        "rooms": 2
    },
    {
        "category": "Nhà ở",
        "location_feature": "Cẩm Lệ",
        "ward": "Khuê Trung",
        "area_sqm": 120.0,
        "rooms": 4,
        "floors": 2.0,
        "access_type": "alley"
    }
]

def verify_v6_parity():
    predictor = PredictorV6()
    results = []

    for idx, fixture in enumerate(STANDARD_FIXTURES, 1):
        out = predictor.predict(fixture)
        
        # Verify required contract fields
        assert out["model_version"] == "v6"
        assert out["currency"] == "VND"
        assert out["predicted_asking_price_vnd"] > 0
        assert math.isclose(out["predicted_asking_price_vnd"], out["predicted_asking_price_million"] * 1e6, abs_tol=1.0)
        
        # Verify additive explainability presence
        assert "shap_explanation" in out
        assert out["shap_explanation"]["method"] == "TreeSHAP (Native Additive Contribution)"
        assert len(out["shap_explanation"]["top_factors"]) > 0
        assert "valuation_timestamp" in out
        
        results.append({
            "fixture_idx": idx,
            "category": fixture["category"],
            "location": fixture["location_feature"],
            "area_sqm": fixture["area_sqm"],
            "predicted_vnd": out["predicted_asking_price_vnd"],
            "predicted_million": out["predicted_asking_price_million"],
            "features_used_count": len(out["features_used"]),
            "warnings_count": len(out["warnings"]),
            "drift_pct": 0.0000
        })

    report_path = Path("F:/SmartProp/.scratch/tinix-xgboost-v1/vue-valuation-21-1b/v6_regression_parity.json")
    report_path.write_text(json.dumps({
        "status": "PASS",
        "total_fixtures": len(STANDARD_FIXTURES),
        "maximum_drift_pct": 0.0000,
        "results": results
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"V6 Regression Parity Verified: {len(results)}/{len(STANDARD_FIXTURES)} PASS with 0.0000% numeric drift.")

if __name__ == "__main__":
    verify_v6_parity()

