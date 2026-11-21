"""Contract tests for the public valuation endpoint, now served by V1.3.

The public /predict route used to answer with V6 and this file compared it against
the internal V1.3 route. V1.3 is now the only model that produces new results, so
the contract checks the public route on its own terms and keeps the schema,
validation and explanation checks that still carry value.
"""
import unittest

from fastapi.testclient import TestClient

from main import app

AUTH_HEADER = {"X-Internal-Token": "smartprop-internal-shadow-key"}


class TestV13Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_contract_all_property_categories(self):
        """Every supported category executes and answers with a V1.3 price."""
        cases = [
            (
                "Nhà phố thông thường",
                {
                    "category": "Nhà ở",
                    "area_sqm": 80.0,
                    "location_feature": "Hải Châu",
                    "ward": "Hải Châu 1",
                    "rooms": 3,
                    "floors": 3.0,
                    "access_type": "frontage"
                }
            ),
            (
                "Đất nền khu đô thị",
                {
                    "category": "Đất nền",
                    "area_sqm": 100.0,
                    "location_feature": "Liên Chiểu",
                    "ward": "Hòa Khánh Bắc",
                    "access_type": "alley"
                }
            ),
            (
                "Căn hộ cao cấp",
                {
                    "category": "Căn hộ chung cư",
                    "area_sqm": 55.0,
                    "location_feature": "Sơn Trà",
                    "ward": "An Hải Bắc",
                    "rooms": 2
                }
            ),
            (
                "Biệt thự ven biển",
                {
                    "category": "Nhà ở",
                    "house_subtype": "villa",
                    "area_sqm": 350.0,
                    "location_feature": "Ngũ Hành Sơn",
                    "ward": "Khuê Mỹ",
                    "rooms": 6,
                    "floors": 3.0,
                    "access_type": "frontage"
                }
            )
        ]

        for case_name, payload in cases:
            with self.subTest(case=case_name):
                resp = self.client.post("/predict", json=payload)
                self.assertEqual(resp.status_code, 200, f"V1.3 failed for {case_name}: {resp.text}")
                data = resp.json()
                self.assertEqual(data["model_version"], "v1.3")
                self.assertGreater(data["predicted_asking_price_vnd"], 0)
                self.assertIn("price_band", data)
                self.assertIn("calibration_policy", data)
                self.assertIsInstance(data["features_used"], dict)

                # The internal route must answer the same model version.
                internal = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
                self.assertEqual(internal.status_code, 200, f"internal failed for {case_name}: {internal.text}")
                self.assertEqual(internal.json()["model_version"], "v1.3")

    def test_contract_missing_ward(self):
        """An omitted ward stays missing instead of being invented."""
        payload = {
            "category": "Nhà ở",
            "area_sqm": 90.0,
            "location_feature": "Cẩm Lệ",
            "rooms": 3,
            "floors": 2.0,
        }
        resp = self.client.post("/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["model_version"], "v1.3")

        internal = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(internal.status_code, 200)
        self.assertIsNone(internal.json()["features_used"]["ward"])

    def test_optional_measurements_reach_the_model(self):
        """A bathroom count the user entered is visible in the model's own features."""
        payload = {
            "category": "Nhà ở",
            "area_sqm": 80.0,
            "location_feature": "Hải Châu",
            "rooms": 3,
            "bathrooms": 2,
        }
        resp = self.client.post("/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        self.assertEqual(resp.json()["features_used"]["bathroom_count"], 2)

    def test_an_omitted_measurement_is_not_defaulted(self):
        """Road width and frontage stay null when the user did not enter them."""
        payload = {
            "category": "Nhà ở",
            "area_sqm": 80.0,
            "location_feature": "Hải Châu",
            "rooms": 3,
        }
        resp = self.client.post("/predict", json=payload)
        self.assertEqual(resp.status_code, 200)
        features = resp.json()["features_used"]
        self.assertIsNone(features["road_width"])
        self.assertIsNone(features["frontage_width"])

    def test_health_reports_v13(self):
        resp = self.client.get("/health")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["model_version"], "v1.3")
        self.assertTrue(body["model_ready"])

    def test_options_come_from_v13(self):
        resp = self.client.get("/model/options")
        self.assertEqual(resp.status_code, 200)
        body = resp.json()
        self.assertEqual(body["model_version"], "v1.3")
        categories = {item["category"] for item in body["categories"]}
        self.assertEqual(categories, {"Nhà ở", "Đất nền", "Căn hộ chung cư"})
        for item in body["categories"]:
            self.assertTrue(item["locations"], item["category"])


if __name__ == "__main__":
    unittest.main()
