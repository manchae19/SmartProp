"""Contract tests validating schema alignment and behavioral parity between V6 and V1.3."""
import unittest

from fastapi.testclient import TestClient

from main import app

AUTH_HEADER = {"X-Internal-Token": "smartprop-internal-shadow-key"}


class TestV6V1_3Contract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def test_contract_all_property_categories(self):
        """Verify that all 4 supported categories execute successfully through both endpoints."""
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
                # 1. Call V6
                resp_v6 = self.client.post("/predict", json=payload)
                self.assertEqual(resp_v6.status_code, 200, f"V6 failed for {case_name}: {resp_v6.text}")
                data_v6 = resp_v6.json()
                self.assertEqual(data_v6["model_version"], "v6")
                self.assertGreater(data_v6["predicted_asking_price_vnd"], 0)

                # 2. Call V1.3 via adapter
                resp_v1_3 = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
                self.assertEqual(resp_v1_3.status_code, 200, f"V1.3 failed for {case_name}: {resp_v1_3.text}")
                data_v1_3 = resp_v1_3.json()
                self.assertEqual(data_v1_3["model_version"], "v1.3")
                self.assertGreater(data_v1_3["predicted_asking_price_vnd"], 0)

                # Check monetary scale sanity (within 0.3x - 3.0x of each other)
                ratio = data_v1_3["predicted_asking_price_vnd"] / data_v6["predicted_asking_price_vnd"]
                self.assertTrue(0.3 <= ratio <= 3.0, f"Divergence too wide for {case_name}: ratio={ratio:.2f}")

    def test_contract_missing_ward(self):
        """Verify behavior when ward is omitted or unknown."""
        payload = {
            "category": "Nhà ở",
            "area_sqm": 90.0,
            "location_feature": "Cẩm Lệ",
            "rooms": 3,
            "floors": 2.0,
        }
        resp_v6 = self.client.post("/predict", json=payload)
        self.assertEqual(resp_v6.status_code, 200)

        resp_v1_3 = self.client.post("/api/internal/v1_3/predict", json=payload, headers=AUTH_HEADER)
        self.assertEqual(resp_v1_3.status_code, 200)
        data_v1_3 = resp_v1_3.json()
        self.assertIsNone(data_v1_3["features_used"]["ward"])


if __name__ == "__main__":
    unittest.main()
