import math
import unittest

from app.models.xgboost.predictor_v1_3 import PredictorV1_3


class ValuationShapContractTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictorV1_3()

    def test_missing_ward_and_street_are_labelled_as_missing(self):
        result = self.predictor.predict_from_v6_payload({
            "category": "Nhà ở",
            "area_sqm": 100,
            "location_feature": "Hải Châu",
            "rooms": 4,
            "floors": 3,
            "access_type": "frontage",
            "house_subtype": "villa",
        })
        factors = {factor["feature_name"]: factor for factor in result["shap_explanation"]["top_factors"]}
        self.assertIn("ward", factors)
        self.assertIn("đang thiếu", factors["ward"]["label"])
        self.assertIn("không có trong input", factors["raw_street_name"]["label"])
        self.assertGreater(result["predicted_asking_price_vnd"], 0)
        # A frontage access type is not a measurement, so the widths stay missing.
        self.assertIsNone(result["features_used"]["road_width"])
        self.assertIsNone(result["features_used"]["frontage_width"])
        self.assertIn("không phải địa chỉ thực", factors["ward"]["context_note"])
        shap = result["shap_explanation"]
        expected_base = math.expm1(float(shap["base_value_log"]))
        self.assertLessEqual(abs(expected_base - float(shap["base_price_vnd"])) / max(1.0, expected_base), 1e-3)
        ratio = float(result["predicted_asking_price_vnd"]) / float(result["naive_price_vnd"])
        self.assertAlmostEqual(ratio, float(result["calibration_factor"]), delta=0.0002)

    def test_no_access_does_not_invent_road_or_frontage(self):
        result = self.predictor.predict_from_v6_payload({
            "category": "Nhà ở",
            "area_sqm": 60,
            "location_feature": "Hải Châu",
        })
        self.assertIsNone(result["features_used"]["road_width"])
        self.assertIsNone(result["features_used"]["frontage_width"])
        self.assertTrue(result["missing_features"])


if __name__ == "__main__":
    unittest.main()
