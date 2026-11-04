"""API contract and replay against the already exposed v6 validation results."""
import json
import math
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))

from fastapi.testclient import TestClient
from main import create_app
from app.core.model_registry import DATA_DIR, V6_MANIFEST_SHA256, V6_MODEL_DIR, V6_RUN
from app.models.xgboost.predictor_v6 import ModelArtifactError


class ApiTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.app = create_app()
        cls.client = TestClient(cls.app)
        cls.client.__enter__()
        cls.options = cls.client.get("/model/options").json()
        cls.locations = {
            item["category"]: item["locations"][0]
            for item in cls.options["categories"]
        }

    @classmethod
    def tearDownClass(cls):
        cls.client.__exit__(None, None, None)

    def payload(self, category="Nhà ở", **values):
        return dict(category=category, area_sqm=80,
                    location_feature=self.locations[category], **values)

    def test_health_and_schema(self):
        self.assertEqual(self.client.get("/health").json(), {
            "status": "ok", "model_version": "v6", "model_ready": True,
        })
        self.assertEqual(self.options["model_run"], V6_RUN)
        self.assertEqual(set(self.locations), {"Nhà ở", "Đất nền", "Căn hộ chung cư"})
        self.assertEqual(self.client.get("/docs").status_code, 200)
        self.assertIn("/predict", self.client.get("/openapi.json").json()["paths"])

    def test_location_options_have_reviewed_accented_labels(self):
        labels = self.options.get("location_labels", {})
        self.assertEqual(labels.get("new_unit:hoa xuan"), "Hòa Xuân (địa bàn mở rộng)")
        bad = "new_unit:ban nha rieng duong nguyen duy hieu - phuong cam chau"
        for category in self.options["categories"]:
            self.assertNotIn(bad, category["locations"])
            self.assertTrue(all(code in labels for code in category["locations"]))

    def test_bad_location_is_blocked_but_valid_model_code_and_price_are_unchanged(self):
        bad = self.payload() | {"location_feature": "new_unit:ban nha rieng duong nguyen duy hieu - phuong cam chau"}
        self.assertEqual(self.client.post("/predict", json=bad).status_code, 422)
        payload = self.payload() | dict(location_feature="new_unit:hoa xuan", area_sqm=200,
                                       rooms=3, floors=2, access_type="alley", house_subtype="house_c4")
        response = self.client.post("/predict", json=payload)
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["features_used"]["location_feature"], "new_unit:hoa xuan")
        self.assertEqual(response.json()["predicted_asking_price_vnd"], 4283741699)

    def test_all_categories_and_missing_fields(self):
        expected = {
            "Nhà ở": {"ward_source", "rooms", "floors", "access_type", "house_subtype"},
            "Đất nền": {"ward_source", "access_type"},
            "Căn hộ chung cư": {"ward_source", "rooms"},
        }
        for category, missing in expected.items():
            with self.subTest(category=category):
                response = self.client.post("/predict", json=self.payload(category))
                self.assertEqual(response.status_code, 200, response.text)
                result = response.json()
                self.assertEqual(result["category"], category)
                self.assertEqual(set(result["missing_features"]), missing)
                self.assertGreater(result["predicted_asking_price_million"], 0)
                self.assertEqual(result["predicted_asking_price_vnd"],
                                 round(result["predicted_asking_price_million"] * 1_000_000))
                self.assertEqual(result["currency"], "VND")

    def test_declared_features_and_model_reused(self):
        predictor = self.app.state.predictor
        response = self.client.post("/predict", json=self.payload(
            rooms=3, floors=2, access_type="alley", house_subtype="house_c4"))
        self.assertEqual(response.status_code, 200, response.text)
        used = response.json()["features_used"]
        self.assertEqual((used["rooms"], used["floors"], used["access_type"], used["house_subtype"]),
                         (3, 2, "alley", "house_c4"))
        self.assertIs(self.app.state.predictor, predictor)

    def test_title_description_extraction_and_conflict(self):
        response = self.client.post("/predict", json=self.payload(
            title="Bán nhà 3 tầng trong kiệt, 4 PN", description="Nhà cấp 4"))
        self.assertEqual(response.status_code, 200, response.text)
        used = response.json()["features_used"]
        self.assertEqual((used["rooms"], used["floors"], used["access_type"], used["house_subtype"]),
                         (4, 3, "alley", "house_c4"))

        response = self.client.post("/predict", json=self.payload(
            rooms=2, floors=2, access_type="alley", house_subtype="house_c4",
            title="Biệt thự 4 PN, nhà 3 tầng mặt tiền"))
        self.assertEqual(response.status_code, 200, response.text)
        result = response.json()
        self.assertEqual(result["features_used"]["rooms"], 2)
        for name in ("floors", "access_type", "house_subtype"):
            self.assertIsNone(result["features_used"][name])
        self.assertTrue(result["warnings"])

    def test_street_names_and_future_building_not_inferred(self):
        response = self.client.post("/predict", json=self.payload(
            title="Bán nhà Võ Văn Kiệt", description="Dự kiến nhà 5 tầng. Gần mặt tiền đường lớn."))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertIsNone(response.json()["features_used"]["access_type"])
        self.assertIsNone(response.json()["features_used"]["floors"])

    def test_unseen_ward_is_explicitly_unknown(self):
        response = self.client.post("/predict", json=self.payload(ward="Phường Chưa Có Trong Model"))
        self.assertEqual(response.status_code, 200, response.text)
        self.assertEqual(response.json()["features_used"]["ward_source"], "chua co trong model")
        self.assertTrue(response.json()["warnings"])

    def test_invalid_numeric_and_target_fields_rejected(self):
        changes = [
            {"area_sqm": 0}, {"area_sqm": 19.99}, {"area_sqm": 1001},
            {"area_sqm": True}, {"area_sqm": "80"}, {"area_sqm": None},
            {"rooms": 0}, {"rooms": 31}, {"rooms": 2.5}, {"rooms": True},
            {"floors": 0}, {"floors": 21}, {"floors": False},
            {"access_type": "unknown"}, {"house_subtype": "apartment"},
            {"price_million": 5000}, {"price_per_sqm": 60},
            {"location_feature": "outside-model"}, {"location_feature": ""},
            {"title": "x" * 501}, {"description": "x" * 8001},
        ]
        for change in changes:
            with self.subTest(change=change):
                response = self.client.post("/predict", json=self.payload() | change)
                self.assertEqual(response.status_code, 422, response.text)

    def test_nonfinite_numbers_rejected(self):
        for field in ("area_sqm", "floors"):
            for value in (math.nan, math.inf, -math.inf):
                with self.subTest(field=field, value=value):
                    response = self.client.post(
                        "/predict", content=json.dumps(self.payload() | {field: value}),
                        headers={"Content-Type": "application/json"})
                    self.assertEqual(response.status_code, 422, response.text)

    def test_inapplicable_features_rejected(self):
        cases = [
            ("Đất nền", {"rooms": 2}), ("Đất nền", {"floors": 2}),
            ("Đất nền", {"house_subtype": "villa"}),
            ("Căn hộ chung cư", {"floors": 15}),
            ("Căn hộ chung cư", {"access_type": "frontage"}),
            ("Căn hộ chung cư", {"house_subtype": "villa"}),
        ]
        for category, values in cases:
            with self.subTest(category=category, values=values):
                response = self.client.post("/predict", json=self.payload(category, **values))
                self.assertEqual(response.status_code, 422, response.text)

    def test_missing_fields_unknown_category_and_malformed_json_rejected(self):
        for payload in ({}, self.payload() | {"category": "Khách sạn"}):
            with self.subTest(payload=payload):
                self.assertEqual(self.client.post("/predict", json=payload).status_code, 422)
        response = self.client.post("/predict", content="{bad json", headers={"Content-Type": "application/json"})
        self.assertEqual(response.status_code, 422)

    def test_not_ready_returns_503(self):
        # Without lifespan/startup, no model should be silently constructed per request.
        client = TestClient(create_app())
        try:
            self.assertEqual(client.get("/health").status_code, 503)
            self.assertEqual(client.post("/predict", json=self.payload()).status_code, 503)
        finally:
            client.close()

    def test_all_299_saved_validation_predictions_replayed_through_api(self):
        fixture_path = SERVICE_DIR / "tests/fixtures/v6_validation_parity.json"
        fixture = json.loads(fixture_path.read_text(encoding="utf-8"))
        self.assertEqual(fixture["model_run"], V6_RUN)
        self.assertEqual(fixture["model_manifest_sha256"], V6_MANIFEST_SHA256)
        self.assertEqual(len(fixture["cases"]), 299)
        self.assertEqual({case["case"] for case in fixture["cases"]}, set(range(1, 300)))
        for case in fixture["cases"]:
            with self.subTest(case=case["case"]):
                response = self.client.post("/predict", json=case["request"])
                self.assertEqual(response.status_code, 200, response.text)
                actual = response.json()["predicted_asking_price_million"]
                expected = case["expected_asking_price_million"]
                self.assertTrue(math.isclose(actual, expected, rel_tol=1e-6, abs_tol=1e-5), (actual, expected))


class ArtifactTests(unittest.TestCase):
    @staticmethod
    def copy_compact_release(root):
        for name in ("manifest.json", "selection.json"):
            shutil.copy2(V6_MODEL_DIR / name, root / name)
        selection = json.loads((root / "selection.json").read_text(encoding="utf-8"))
        for info in selection["category_artifacts"].values():
            for name in (info["model_file"], info["schema_file"]):
                (root / name).parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(V6_MODEL_DIR / name, root / name)
        return selection

    def test_missing_manifest_stops_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ModelArtifactError), TestClient(create_app(directory)):
                pass

    def test_tampered_manifest_stops_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            (Path(directory) / "manifest.json").write_text("{}", encoding="utf-8")
            with self.assertRaises(ModelArtifactError), TestClient(create_app(directory)):
                pass

    def test_tampered_selected_model_stops_startup(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            selection = self.copy_compact_release(root)
            info = next(iter(selection["category_artifacts"].values()))
            (root / info["model_file"]).write_text("tampered", encoding="utf-8")
            with self.assertRaises(ModelArtifactError), TestClient(create_app(root)):
                pass

    def test_compact_relocated_release_loads_without_history_files(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            self.copy_compact_release(root)
            with TestClient(create_app(root)) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                options = client.get("/model/options").json()
                category = options["categories"][0]
                response = client.post("/predict", json=dict(
                    category=category["category"], area_sqm=80, location_feature=category["locations"][0]))
                self.assertEqual(response.status_code, 200, response.text)

    def test_tampered_feature_code_stops_startup(self):
        # Change only a temporary copy; frozen repository sources remain intact.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            for name in ("training_v3_common.py", "property_text_features_v6.py"):
                shutil.copy2(DATA_DIR / name, root / name)
            with (root / "property_text_features_v6.py").open("a", encoding="utf-8") as stream:
                stream.write("\n# changed\n")
            with patch("app.models.xgboost.predictor_v6.DATA_DIR", root):
                with self.assertRaisesRegex(ModelArtifactError, "property_text_features_v6.py"):
                    with TestClient(create_app()):
                        pass


if __name__ == "__main__":
    unittest.main()
