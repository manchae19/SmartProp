"""Integration tests for FastAPI endpoints (V1.3 Internal API & V6 Public API)."""
import unittest

from fastapi.testclient import TestClient

from main import app

AUTH_HEADER = {"X-Internal-Token": "smartprop-internal-shadow-key"}


class TestV1_3APIIntegration(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_v6_health_endpoint(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["model_version"], "v6")
        self.assertTrue(data["model_ready"])

    def test_v1_3_health_endpoint(self):
        resp = self.client.get("/api/internal/v1_3/health")
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["model_version"], "v1.3")
        self.assertTrue(data["model_ready"])

    def test_v1_3_info_endpoint(self):
        resp = self.client.get("/api/internal/v1_3/model/info", headers=AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertEqual(data["model_version"], "v1.3")
        self.assertIn("house", [t.lower() for t in data["supported_types"]])

    def test_v1_3_direct_predict(self):
        payload = {
            "area": 105.0,
            "normalized_type": "HOUSE",
            "district": "Sơn Trà",
            "ward": "An Hải Bắc",
            "bedroom_count": 3,
            "floor_count": 2.0,
            "road_width": 10.0,
            "frontage_width": 5.0
        }
        resp = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["predicted_asking_price_vnd"], 0)
        self.assertIn("price_band", data)
        self.assertEqual(data["currency"], "VND")
        self.assertGreaterEqual(len(data["warnings"]), 2)

    def test_v1_3_adapted_v6_predict(self):
        payload = {
            "category": "Căn hộ chung cư",
            "area_sqm": 65.0,
            "location_feature": "Sơn Trà",
            "ward": "Phước Mỹ",
            "rooms": 2
        }
        resp = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(resp.status_code, 200)
        data = resp.json()
        self.assertGreater(data["predicted_asking_price_vnd"], 0)
        self.assertEqual(data["features_used"]["normalized_type"], "APARTMENT")

    def test_v1_3_validation_error_negative_area(self):
        payload = {
            "area": -10.0,
            "normalized_type": "LAND",
            "district": "Liên Chiểu"
        }
        resp = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(resp.status_code, 422)

    def test_v1_3_validation_error_missing_district(self):
        payload = {
            "area": 100.0,
            "normalized_type": "LAND"
        }
        resp = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(resp.status_code, 422)


if __name__ == "__main__":
    unittest.main()
