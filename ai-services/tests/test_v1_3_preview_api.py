import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_ROOT))

from fastapi.testclient import TestClient
from main import app

class TestValuationShapAndPreview(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_v6_predict_includes_shap_explanation(self):
        payload = {
            "category": "Nhà ở",
            "area_sqm": 85.0,
            "location_feature": "Hải Châu",
            "ward": "Hải Châu 1",
            "rooms": 3,
            "floors": 2.0,
            "access_type": "frontage"
        }
        res = self.client.post("/predict", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertIn("shap_explanation", data)
        shap = data["shap_explanation"]
        self.assertIsNotNone(shap)
        self.assertIn("base_value_log", shap)
        self.assertIn("base_price_vnd", shap)
        self.assertIn("top_factors", shap)
        self.assertGreater(len(shap["top_factors"]), 0)
        # Check factor structure
        first = shap["top_factors"][0]
        self.assertIn("label", first)
        self.assertIn("shap_value", first)
        self.assertIn("impact_pct", first)
        self.assertIn("direction", first)
        self.assertIn("valuation_timestamp", data)

    def test_v1_3_preview_endpoint(self):
        payload = {
            "category": "Nhà ở",
            "area_sqm": 85.0,
            "location_feature": "Hải Châu",
            "ward": "Hải Châu 1",
            "rooms": 3,
            "floors": 2.0,
            "access_type": "frontage"
        }
        res = self.client.post("/predict/v1_3_preview", json=payload)
        self.assertEqual(res.status_code, 200)
        data = res.json()
        self.assertTrue(data.get("is_preview"))
        self.assertEqual(data.get("model_version"), "v1.3")
        self.assertEqual(data.get("status"), "PREVIEW_EXPERIMENTAL")
        self.assertIn("predicted_asking_price_vnd", data)
        self.assertIn("calibration_factor", data)
        self.assertIn("shap_explanation", data)
        self.assertIn("disclaimer", data)
        self.assertIn("Multi-Source", data["disclaimer"])

    def test_v1_3_preview_real_optional_fields_and_invalid_dimensions(self):
        payload = {
            "category": "Nhà ở", "area_sqm": 85.0, "location_feature": "Hải Châu",
            "road_width_m": 7.5, "frontage_width_m": 4.5,
            "street_name": "Nguyễn Văn Linh", "bathrooms": 2,
        }
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            res = self.client.post("/predict/v1_3_preview", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        used = res.json()["features_used"]
        self.assertEqual(used["road_width"], 7.5)
        self.assertEqual(used["frontage_width"], 4.5)
        self.assertEqual(used["street_name"], "Nguyễn Văn Linh")
        self.assertEqual(used["road_width_source"], "user")
        for field, value in (("road_width_m", 0), ("road_width_m", -1),
                             ("frontage_width_m", 0), ("frontage_width_m", 501)):
            res = self.client.post("/predict/v1_3_preview", json={**payload, field: value})
            self.assertEqual(res.status_code, 422, res.text)

    def test_v1_3_preview_only_one_dimension_is_preserved_without_other_default(self):
        base = {"category": "Nhà ở", "area_sqm": 85.0, "location_feature": "Hải Châu"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            road_only = self.client.post("/predict/v1_3_preview", json={**base, "road_width_m": 7.0})
            frontage_only = self.client.post("/predict/v1_3_preview", json={**base, "frontage_width_m": 5.0})
        self.assertEqual(road_only.status_code, 200, road_only.text)
        self.assertEqual(frontage_only.status_code, 200, frontage_only.text)
        road_used = road_only.json()["features_used"]
        frontage_used = frontage_only.json()["features_used"]
        self.assertEqual(road_used["road_width"], 7.0)
        self.assertIsNone(road_used["frontage_width"])
        self.assertEqual(frontage_used["frontage_width"], 5.0)
        self.assertIsNone(frontage_used["road_width"])

    def test_v1_3_preview_no_dimension_is_not_fabricated(self):
        payload = {"category": "Nhà ở", "area_sqm": 85.0, "location_feature": "Hải Châu",
                   "access_type": "alley"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            res = self.client.post("/predict/v1_3_preview", json=payload)
        self.assertEqual(res.status_code, 200, res.text)
        used = res.json()["features_used"]
        self.assertIsNone(used["road_width"])
        self.assertIsNone(used["frontage_width"])
        self.assertIn("road_width", res.json()["missing_features"])

if __name__ == "__main__":
    unittest.main()

