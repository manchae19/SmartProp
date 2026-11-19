"""Security, Authorization, Circuit Breaker, and Privacy tests for Step 21.0B."""
import json
import os
import time
import unittest
from pathlib import Path
from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from main import app
from app.core.shadow_manager import ShadowTelemetryManager

VALID_KEY = "fixture-only-internal-token-000000000000000000"
VALID_HEADER = {"X-Internal-Token": VALID_KEY}
VALID_BEARER = {"Authorization": f"Bearer {VALID_KEY}"}
INVALID_HEADER = {"X-Internal-Token": "hacker-attempting-unauthorized-access"}


class TestSecurityAudit(unittest.TestCase):
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
        self.client.post("/api/internal/v1_3/shadow/reset", headers=VALID_HEADER)
        if hasattr(app.state, "shadow_manager") and app.state.shadow_manager:
            app.state.shadow_manager.reset_stats()

    # 1. Unauthenticated Access Rejection (401)
    def test_missing_auth_rejected_401(self):
        """Endpoints must reject unauthenticated requests with 401."""
        endpoints = [
            ("GET", "/api/internal/v1_3/model/info"),
            ("GET", "/api/internal/v1_3/shadow/stats"),
            ("POST", "/api/internal/v1_3/shadow/toggle", {"enabled": True}),
            ("POST", "/api/internal/v1_3/shadow/reset", {}),
            ("POST", "/api/internal/v1_3/predict", {"area": 80.0, "normalized_type": "HOUSE", "district": "Hải Châu"}),
        ]
        for method, path, *body in endpoints:
            with self.subTest(method=method, path=path):
                if method == "GET":
                    resp = self.client.get(path)
                else:
                    resp = self.client.post(path, json=body[0] if body else {})
                self.assertEqual(
                    resp.status_code, 401,
                    f"Path {path} did not reject unauthenticated access (got {resp.status_code})"
                )

    # 2. Invalid Token Rejection (403)
    def test_invalid_token_rejected_403(self):
        resp = self.client.get("/api/internal/v1_3/model/info", headers=INVALID_HEADER)
        self.assertEqual(resp.status_code, 403)
        self.assertIn("Forbidden", resp.json()["detail"])

        resp_toggle = self.client.post(
            "/api/internal/v1_3/shadow/toggle",
            json={"enabled": True},
            headers=INVALID_HEADER
        )
        self.assertEqual(resp_toggle.status_code, 403)

    # 3. Valid Credentials Accepted (X-Internal-Token & Bearer)
    def test_valid_credentials_accepted(self):
        # Via X-Internal-Token
        r1 = self.client.get("/api/internal/v1_3/model/info", headers=VALID_HEADER)
        self.assertEqual(r1.status_code, 200)

        # Via Authorization: Bearer
        r2 = self.client.get("/api/internal/v1_3/model/info", headers=VALID_BEARER)
        self.assertEqual(r2.status_code, 200)

    # 4. Default OFF Verification
    def test_shadow_mode_default_off(self):
        clean_state = Path(".scratch/shadow_telemetry/temp_clean_state.json")
        if clean_state.exists():
            clean_state.unlink()
        clean_mgr = ShadowTelemetryManager(enabled=None, state_file_path=clean_state)
        # Without env var SMARTPROP_SHADOW_MODE_ENABLED=true, it MUST be False
        if "SMARTPROP_SHADOW_MODE_ENABLED" not in os.environ:
            self.assertFalse(clean_mgr.is_enabled())
        if clean_state.exists():
            clean_state.unlink()

    # 5. Concurrency Queue Backpressure (Task Dropping under Saturation)
    def test_queue_backpressure_bound(self):
        """Verify that saturating the queue drops excess tasks without crashing."""
        mgr = ShadowTelemetryManager(enabled=True, max_workers=1, max_queue_depth=3)
        mock_predictor = MagicMock()
        import time
        # Slow predictor to build queue
        mock_predictor.predict_from_v6_payload.side_effect = lambda payload: (time.sleep(0.1), {"predicted_asking_price_vnd": 5e9})[1]

        v6_payload = {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Hải Châu"}
        v6_resp = {"predicted_asking_price_vnd": 5e9}

        # Dispatch 10 tasks rapidly into queue of capacity 3
        for _ in range(10):
            mgr.record_shadow_evaluation(mock_predictor, v6_payload, v6_resp, 2.0)

        stats = mgr.get_summary_statistics()
        self.assertGreater(stats["queue_status"]["dropped_queue_full"], 0)
        mgr._executor.shutdown(wait=False)

    # 6. Circuit Breaker Trigger on Consecutive Failures
    def test_circuit_breaker_tripping(self):
        """5 consecutive failures must trip circuit breaker into OPEN state."""
        mgr = ShadowTelemetryManager(enabled=True, max_workers=2)
        mock_broken = MagicMock()
        mock_broken.predict_from_v6_payload.side_effect = RuntimeError("Repeated database failure")

        v6_payload = {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Hải Châu"}
        v6_resp = {"predicted_asking_price_vnd": 5e9}

        # Dispatch 6 failures
        for _ in range(6):
            mgr.record_shadow_evaluation(mock_broken, v6_payload, v6_resp, 2.0)
            time.sleep(0.02)  # small pause to let thread execute

        time.sleep(0.1)  # allow workers to finish
        stats = mgr.get_summary_statistics()
        self.assertTrue(stats["circuit_breaker"]["is_open"])
        self.assertFalse(mgr.is_enabled())  # Disabled while circuit is open
        mgr._executor.shutdown(wait=False)

    # 7. Zero-PII Telemetry Verification
    def test_telemetry_zero_pii(self):
        """Verify that sensitive user data (title, description, phone numbers) are stripped."""
        self.client.post("/api/internal/v1_3/shadow/toggle", json={"enabled": True}, headers=VALID_HEADER)

        sensitive_payload = {
            "category": "Nhà ở",
            "area_sqm": 85.0,
            "location_feature": "Hải Châu",
            "ward": "Hải Châu 1",
            "rooms": 3,
            "floors": 2.0,
            "title": "Bán nhà chính chủ số 123 đường Lê Lợi, liên hệ Anh Tuấn 0905123456",
            "description": "Nhà đẹp, sổ đỏ chính chủ tên Nguyễn Văn Tuấn, giá chốt 10 tỷ không thương lượng."
        }
        resp = self.client.post("/predict", json=sensitive_payload)
        self.assertEqual(resp.status_code, 200)

        # Allow async worker thread to complete execution
        time.sleep(0.15)

        # Inspect events buffer directly
        mgr = app.state.shadow_manager
        self.assertGreater(len(mgr.events_buffer), 0)
        last_event = mgr.events_buffer[-1]

        # Assert zero PII
        self.assertNotIn("title", last_event)
        self.assertNotIn("description", last_event)
        self.assertNotIn("0905123456", str(last_event))
        self.assertNotIn("Nguyễn Văn Tuấn", str(last_event))
        self.assertNotIn("123 đường Lê Lợi", str(last_event))


if __name__ == "__main__":
    unittest.main()
