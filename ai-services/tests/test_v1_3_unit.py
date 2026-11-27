"""Unit tests for XGBoost V1.3 components (Schema, Features, Calibration, Limits)."""
import os
import unittest
from unittest.mock import patch

from app.models.xgboost.features_v1_3 import (
    clean_category,
    clean_numeric,
)
from app.models.xgboost.predictor_v1_3 import (
    PredictorV1_3,
    band_of,
)
from app.models.xgboost.adapter_v1_3 import (
    canonical_district,
    map_v6_to_v1_3,
    resolve_district,
)


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
        # Không còn fallback: địa bàn không nhận diện được phải trả None để tầng API từ chối,
        # thay vì âm thầm định giá như Hải Châu.
        self.assertIsNone(resolve_district("Khu vực ven biển", "Hòa Hải"))

    def test_ward_can_never_override_district(self):
        """P1: ward là feature riêng, không được kéo bất động sản sang quận khác."""
        # Đúng tổ hợp trong finding: Cẩm Lệ + ward Hải Châu 1 phải vẫn là Cẩm Lệ.
        self.assertEqual(resolve_district("Cẩm Lệ", "Hải Châu 1"), "Cẩm Lệ")
        self.assertEqual(resolve_district("Cẩm Lệ", "Phường Hải Châu 1"), "Cẩm Lệ")
        self.assertEqual(resolve_district("Ngũ Hành Sơn", "Hòa Hải"), "Ngũ Hành Sơn")
        # Ward một mình không bao giờ xác định được quận.
        self.assertIsNone(resolve_district("", "Hải Châu 1"))

    def test_district_vocabulary_is_exact_and_unicode_aware(self):
        vocab = ["Cẩm Lệ", "Hải Châu", "Thanh Khê"]
        import unicodedata
        self.assertEqual(canonical_district("Cẩm Lệ", vocab), "Cẩm Lệ")
        self.assertEqual(canonical_district("  cẩm lệ  ", vocab), "Cẩm Lệ")
        self.assertEqual(canonical_district("CẨM LỆ", vocab), "Cẩm Lệ")
        self.assertEqual(canonical_district(unicodedata.normalize("NFD", "Cẩm Lệ"), vocab), "Cẩm Lệ")
        self.assertIsNone(canonical_district("Hà Nội", vocab))
        self.assertIsNone(canonical_district("", vocab))

    def test_unknown_district_is_refused_not_defaulted(self):
        """Adapter phải từ chối, không được biến input lạ thành Hải Châu."""
        with self.assertRaises(ValueError):
            map_v6_to_v1_3(
                {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Hà Nội"},
                district_vocabulary=["Cẩm Lệ", "Hải Châu"],
            )

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
        # A frontage access type is not a measurement: the width stays missing rather
        # than being invented from the access type.
        self.assertIsNone(v1_3_rec["road_width"])
        self.assertIsNone(v1_3_rec["frontage_width"])

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

    def test_real_mode_never_creates_dimensions(self):
        request = {"category": "Nhà ở", "area_sqm": 80, "location_feature": "Hải Châu", "access_type": "alley"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            record = map_v6_to_v1_3(request)
        self.assertIsNone(record["road_width"])
        self.assertIsNone(record["frontage_width"])
        self.assertIsNone(record["road_width_source"])

    def test_real_mode_preserves_explicit_measurements_and_source(self):
        request = {"category": "Nhà ở", "area_sqm": 80, "location_feature": "Hải Châu",
                   "access_type": "alley", "road_width_m": 6.5, "frontage_width_m": 4.2,
                   "street_name": "Nguyễn Văn Linh", "bathrooms": 2,
                   "road_width_source": "verified"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            record = map_v6_to_v1_3(request)
        self.assertEqual(record["road_width"], 6.5)
        self.assertEqual(record["frontage_width"], 4.2)
        self.assertEqual(record["street_name"], "Nguyễn Văn Linh")
        self.assertEqual(record["bathroom_count"], 2)
        self.assertEqual(record["road_width_source"], "verified")
        self.assertEqual(record["frontage_width_source"], "user")

    def test_legacy_mode_keeps_existing_defaults_and_ignores_new_fields(self):
        request = {"category": "Nhà ở", "area_sqm": 80, "location_feature": "Hải Châu",
                   "access_type": "frontage", "road_width_m": 6.5, "frontage_width_m": 4.2,
                   "street_name": "Nguyễn Văn Linh"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "false"}):
            record = map_v6_to_v1_3(request)
        self.assertEqual((record["road_width"], record["frontage_width"]), (10.0, 5.0))
        self.assertIsNone(record["street_name"])
        self.assertEqual(record["road_width_source"], "assumed")

    def test_real_mode_prediction_reports_real_feature_used(self):
        request = {"category": "Nhà ở", "area_sqm": 90, "location_feature": "Hải Châu",
                   "road_width_m": 7.0, "frontage_width_m": 4.5, "street_name": "Tuyến A"}
        with patch.dict(os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}):
            result = self.predictor.predict_from_v6_payload(request)
        self.assertEqual(result["features_used"]["road_width"], 7.0)
        self.assertEqual(result["features_used"]["frontage_width"], 4.5)
        self.assertEqual(result["features_used"]["street_name"], "Tuyến A")
        self.assertEqual(result["features_used"]["road_width_source"], "user")
        self.assertNotIn("road_width", result["missing_features"])


if __name__ == "__main__":
    unittest.main()
