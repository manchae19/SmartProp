import sys
import unittest
from pathlib import Path

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

if __name__ == "__main__":
    unittest.main()

