"""Unit tests for XGBoost V1.3 components (Schema, Features, Calibration, Limits)."""
import unittest

from app.models.xgboost.features_v1_3 import (
    clean_category,
    clean_numeric,
)
from app.models.xgboost.predictor_v1_3 import (
    PredictorV1_3,
    band_of,
)
from app.models.xgboost.adapter_v1_3 import resolve_district, map_v6_to_v1_3


class TestV1_3Unit(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictorV1_3()

    def test_predictor_loaded_and_schema_valid(self):
        info = self.predictor.info()
        self.assertEqual(info["model_version"], "v1.3")
        self.assertEqual(info["status"], "READY")
        self.assertEqual(info["calibration_policy"], "duan_by_band")
        self.assertIn("hải châu", [d.lower() for d in info["supported_districts"]])
        self.assertIn("house", [t.lower() for t in info["supported_types"]])

    def test_band_classification(self):
        self.assertEqual(band_of(1.5e9), "<2B")
        self.assertEqual(band_of(2.5e9), "2-3B")
        self.assertEqual(band_of(4.2e9), "3-5B")
        self.assertEqual(band_of(7.8e9), "5-10B")
        self.assertEqual(band_of(15e9), "10-20B")
        self.assertEqual(band_of(35e9), ">20B")

    def test_clean_category_normalization(self):
        self.assertEqual(clean_category("  Hải Châu  "), "hải châu")
        self.assertEqual(clean_category(None), "__MISSING__")
        self.assertEqual(clean_category("NaN"), "__MISSING__")
        self.assertEqual(clean_category(""), "__MISSING__")

    def test_clean_numeric_bounds(self):
        self.assertEqual(clean_numeric("100.5", "area"), 100.5)
        self.assertTrue(clean_numeric("-5", "area") != clean_numeric("-5", "area"))  # NaN
        self.assertTrue(clean_numeric("60000", "area") != clean_numeric("60000", "area"))  # NaN
        self.assertEqual(clean_numeric("3", "bedroom_count"), 3.0)

    def test_district_resolver(self):
        self.assertEqual(resolve_district("Đường 2/9, quận Hải Châu"), "Hải Châu")
        self.assertEqual(resolve_district("quận Ngũ Hành Sơn"), "Ngũ Hành Sơn")
        self.assertEqual(resolve_district("Sơn Trà"), "Sơn Trà")
        self.assertEqual(resolve_district("Khu vực ven biển", "Hòa Hải"), "Hải Châu")  # Fallback

    def test_adapter_v6_mapping(self):
        v6_req = {
            "category": "Nhà ở",
            "house_subtype": "villa",
            "area_sqm": 250.0,
            "location_feature": "quận Sơn Trà",
            "ward": "Phường Phước Mỹ",
            "rooms": 5,
            "floors": 3.0,
            "access_type": "frontage"
        }
        v1_3_rec = map_v6_to_v1_3(v6_req)
        self.assertEqual(v1_3_rec["normalized_type"], "VILLA")
        self.assertEqual(v1_3_rec["district"], "Sơn Trà")
        self.assertEqual(v1_3_rec["ward"], "Phước Mỹ")
        self.assertEqual(v1_3_rec["bedroom_count"], 5)
        self.assertEqual(v1_3_rec["floor_count"], 3.0)
        self.assertEqual(v1_3_rec["road_width"], 10.0)
        self.assertEqual(v1_3_rec["frontage_width"], 5.0)

    def test_predict_standard_house(self):
        sample = {
            "area": 90.0,
            "normalized_type": "HOUSE",
            "district": "Hải Châu",
            "ward": "Thạch Thang",
            "bedroom_count": 3,
            "floor_count": 3.0,
            "road_width": 7.5,
            "frontage_width": 4.5,
        }
        res = self.predictor.predict(sample)
        self.assertGreater(res["predicted_asking_price_vnd"], 1_000_000_000)
        self.assertTrue(res["price_band"] in ["3-5B", "5-10B", "10-20B"])
        self.assertEqual(res["currency"], "VND")
        self.assertGreater(len(res["warnings"]), 0)

    def test_predict_area_limits(self):
        with self.assertRaises(ValueError):
            self.predictor.predict({"area": 2.0, "normalized_type": "LAND", "district": "Cẩm Lệ"})
        with self.assertRaises(ValueError):
            self.predictor.predict({"area": 60_000.0, "normalized_type": "LAND", "district": "Cẩm Lệ"})


if __name__ == "__main__":
    unittest.main()
