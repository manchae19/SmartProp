"""Integration and resilience tests for Shadow Mode evaluation."""
import time
import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app

AUTH_HEADER = {"X-Internal-Token": "smartprop-internal-shadow-key"}


class TestShadowMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.client_cm = TestClient(app)
        cls.client = cls.client_cm.__enter__()

    @classmethod
    def tearDownClass(cls):
        cls.client_cm.__exit__(None, None, None)

    def setUp(self):
        # Reset stats before each test
        self.client.post("/api/internal/v1_3/shadow/reset", headers=AUTH_HEADER)
        if hasattr(app.state, "shadow_manager") and app.state.shadow_manager:
            app.state.shadow_manager.reset_stats()

    def test_shadow_disabled_by_default(self):
        self.client.post("/api/internal/v1_3/shadow/toggle", json={"enabled": False}, headers=AUTH_HEADER)
        payload = {
            "category": "Nhà ở",
            "area_sqm": 85.0,
            "location_feature": "Hải Châu",
            "rooms": 3,
            "floors": 2.0
        }
        resp = self.client.post("/predict", json=payload)
        self.assertEqual(resp.status_code, 200)

        # Allow worker thread to complete execution
        time.sleep(0.1)

        stats = self.client.get("/api/internal/v1_3/shadow/stats", headers=AUTH_HEADER).json()
        self.assertFalse(stats["shadow_enabled"])
        self.assertEqual(stats["total_requests"], 0)

    def test_shadow_enabled_records_telemetry(self):
        self.client.post("/api/internal/v1_3/shadow/toggle", json={"enabled": True}, headers=AUTH_HEADER)
        payload = {
            "category": "Nhà ở",
            "area_sqm": 85.0,
            "location_feature": "Hải Châu",
            "ward": "Hải Châu 1",
            "rooms": 3,
            "floors": 2.0,
            "access_type": "frontage"
        }
        resp = self.client.post("/predict", json=payload)
        self.assertEqual(resp.status_code, 200)

        # Allow worker thread to complete execution
        time.sleep(0.1)

        stats = self.client.get("/api/internal/v1_3/shadow/stats", headers=AUTH_HEADER).json()
        self.assertTrue(stats["shadow_enabled"])
        self.assertEqual(stats["total_requests"], 1)
        self.assertEqual(stats["shadow_runs"], 1)
        self.assertEqual(stats["shadow_errors"], 0)
        self.assertIn("divergence", stats)
        self.assertIn("latency", stats)

    def test_shadow_error_isolation_resilience(self):
        """A critical error in V1.3 must not take the service down.

        V1.3 is now the primary model, so a fault surfaces as an error response on
        that one request while the service keeps answering health and options. Shadow
        telemetry only runs when the optional V6 model is loaded, so it records
        nothing here.
        """
        self.client.post("/api/internal/v1_3/shadow/toggle", json={"enabled": True}, headers=AUTH_HEADER)

        # Inject a buggy mock into predictor_v1_3 temporarily
        original_predictor = app.state.predictor_v1_3
        mock_broken = MagicMock()
        mock_broken.predict_from_v6_payload.side_effect = RuntimeError("Simulated GPU/Memory fault in V1.3")
        app.state.predictor_v1_3 = mock_broken

        try:
            payload = {
                "category": "Nhà ở",
                "area_sqm": 90.0,
                "location_feature": "Sơn Trà",
                "rooms": 4
            }
            # The failing request reports the fault instead of crashing the process.
            resp = self.client.post("/predict", json=payload)
            self.assertGreaterEqual(resp.status_code, 500)

            # The service itself stays up and keeps answering.
            self.assertEqual(self.client.get("/health").status_code, 200)
            self.assertEqual(self.client.get("/model/options").status_code, 200)

            # Without the optional V6 model there is no shadow comparison to record.
            stats = self.client.get("/api/internal/v1_3/shadow/stats", headers=AUTH_HEADER).json()
            self.assertEqual(stats["shadow_errors"], 0)
        finally:
            app.state.predictor_v1_3 = original_predictor


if __name__ == "__main__":
    unittest.main()
