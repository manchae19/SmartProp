import unittest

from app.models.xgboost.predictor_v6 import PredictorV6


class V6ShapLabelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.predictor = PredictorV6()

    def test_villa_and_unused_alley_labels(self):
        result = self.predictor.predict({
            "category": "Nhà ở",
            "area_sqm": 100,
            "location_feature": "Hải Châu",
            "rooms": 4,
            "floors": 3,
            "access_type": "frontage",
            "house_subtype": "villa",
            "title": "Biệt thự mặt tiền",
            "description": "Biệt thự mặt tiền 4PN",
        })
        labels = {factor["feature_name"]: factor["label"] for factor in result["shap_explanation"]["top_factors"]}
        self.assertEqual(labels.get("subtype_villa"), "Loại nhà: Biệt thự")
        self.assertIn("không áp dụng cho input", labels.get("access_alley", ""))
        self.assertGreater(result["predicted_asking_price_vnd"], 0)


if __name__ == "__main__":
    unittest.main()
