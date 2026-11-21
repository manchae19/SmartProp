import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient

from main import create_app


BASE = {
    "category": "Nhà ở",
    "area_sqm": 80,
    "location_feature": "Hải Châu",
}


class V13CapabilityTests(unittest.TestCase):
    def test_v6_stays_available_when_v13_artifacts_missing(self):
        with tempfile.TemporaryDirectory() as tmp:
            app = create_app(v1_3_model_dir=Path(tmp) / "missing")
            with TestClient(app) as client:
                self.assertEqual(client.get("/health").status_code, 200)
                opts = client.get("/model/options")
                self.assertEqual(opts.status_code, 200)
                self.assertFalse(opts.json()["v1_3"]["available"])
                self.assertEqual(opts.json()["v1_3"]["status"], "UNAVAILABLE")
                self.assertEqual(client.post("/predict/v1_3_preview", json=BASE).status_code, 503)

    def test_flag_off_is_reported_and_no_optional_inputs(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "false"}
        ):
            app = create_app(v1_3_model_dir=Path(tmp) / "missing")
            with TestClient(app) as client:
                cap = client.get("/model/options").json()["v1_3"]
                self.assertFalse(cap["real_features_enabled"])
                self.assertEqual(cap["optional_inputs"], [])

    def test_flag_on_is_reported_without_inventing_fields(self):
        with tempfile.TemporaryDirectory() as tmp, patch.dict(
            os.environ, {"SMARTPROP_V1_3_REAL_FEATURES": "true"}
        ):
            app = create_app(v1_3_model_dir=Path(tmp) / "missing")
            with TestClient(app) as client:
                cap = client.get("/model/options").json()["v1_3"]
                self.assertTrue(cap["real_features_enabled"])
                self.assertEqual(cap["optional_inputs"], [])

    @unittest.skipUnless(os.environ.get("SMARTPROP_V1_3_MODEL_DIR"), "V1.3 artifact path not provided")
    def test_v13_available_when_artifacts_are_configured(self):
        app = create_app(v1_3_model_dir=os.environ["SMARTPROP_V1_3_MODEL_DIR"])
        with TestClient(app) as client:
            cap = client.get("/model/options").json()["v1_3"]
            self.assertTrue(cap["available"])
            # V1.3 is the primary model now, not an experimental preview.
            self.assertEqual(cap["status"], "PRIMARY")


if __name__ == "__main__":
    unittest.main()
