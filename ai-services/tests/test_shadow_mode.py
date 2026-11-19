"""Integration and resilience tests for Shadow Mode evaluation."""
import time
import unittest
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app

AUTH_HEADER = {"X-Internal-Token": "fixture-only-internal-token-000000000000000000"}


class TestShadowMode(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        from unittest.mock import patch
        cls.credentials = patch.dict("os.environ", {"SMARTPROP_INTERNAL_KEY":"fixture-only-internal-token-000000000000000000","SMARTPROP_INTERNAL_ADMIN_KEY":"fixture-only-internal-token-000000000000000000"})
        cls.credentials.start()
        cls.addClassCleanup(cls.credentials.stop)
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
        """Simulate a critical error in V1.3; assert V6 request still succeeds 100%."""
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
            # The client call must NOT fail (must return 200 OK)
            resp = self.client.post("/predict", json=payload)
            self.assertEqual(resp.status_code, 200)
            data = resp.json()
            self.assertEqual(data["model_version"], "v6")

            # Shadow stats should record the error
            stats = self.client.get("/api/internal/v1_3/shadow/stats", headers=AUTH_HEADER).json()
            self.assertEqual(stats["shadow_errors"], 1)
            self.assertIn("Simulated GPU/Memory fault", stats["last_error"])
        finally:
            app.state.predictor_v1_3 = original_predictor


if __name__ == "__main__":
    unittest.main()
