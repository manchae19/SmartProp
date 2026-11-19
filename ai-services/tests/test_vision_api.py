"""HTTP-level tests for the YOLOv8 image-analysis router.

The router is mounted on a throwaway FastAPI app so these tests never touch the
running 18001/8001 services. A stub detector keeps the suite fast; the real
model is covered by ``test_vision_detector``.
"""
from __future__ import annotations

import io
import unittest
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
import importlib.util
if importlib.util.find_spec("PIL") is None:
    raise unittest.SkipTest("Optional vision dependencies are not installed; use requirements-vision.txt")
from PIL import Image

from app.vision.api import create_vision_router
from app.vision.config import VisionSettings
from app.vision.detector import AnalysisResult, Detection

MODEL_DIR = Path(__file__).resolve().parents[1] / "var" / "vision"


def png_bytes(width: int = 64, height: int = 48) -> bytes:
    buffer = io.BytesIO()
    Image.new("RGB", (width, height), (200, 200, 200)).save(buffer, format="PNG")
    return buffer.getvalue()


class StubDetector:
    """Minimal stand-in so the router can be tested without loading torch."""

    def __init__(self, *, ready: bool = True, detections: list[Detection] | None = None):
        self._ready = ready
        self._detections = detections or []
        self.calls = 0

    @property
    def ready(self) -> bool:
        return self._ready

    def status(self) -> dict:
        return {
            "status": "ready" if self._ready else "unavailable",
            "modelVersion": "stub@000000000000",
            "algorithmVersion": "yolov8n-property-v1",
            "device": "cpu",
            "imageSize": 640,
            "confidenceThreshold": 0.25,
            "supportedClassCount": 13,
            "lastError": None if self._ready else "MODEL_MISSING:yolov8n.pt",
        }

    def analyze(self, data: bytes) -> AnalysisResult:
        self.calls += 1
        if not self._ready:
            from app.vision.config import VisionUnavailable

            raise VisionUnavailable("MODEL_MISSING")
        if not data:
            from app.vision.config import InvalidImage

            raise InvalidImage("Ảnh rỗng.")
        return AnalysisResult(
            detections=self._detections,
            width=64,
            height=48,
            image_format="PNG",
            sha256="0" * 64,
            inference_ms=1.5,
            total_ms=2.5,
            model_version="stub@000000000000",
            device="cpu",
            counts_by_label={item.label_vi: 1 for item in self._detections},
        )


def build_client(detector: StubDetector, settings: VisionSettings | None = None) -> TestClient:
    app = FastAPI()
    app.include_router(create_vision_router(settings or VisionSettings(), detector))
    return TestClient(app)


class HealthTests(unittest.TestCase):
    def test_health_reports_ready_and_limits(self):
        response = build_client(StubDetector()).get("/image-analysis/health")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "ready")
        self.assertEqual(body["supportedClassCount"], 13)
        self.assertIn("maxUploadBytes", body)
        self.assertIn("maxPixels", body)
        self.assertIn("timeoutSeconds", body)

    def test_health_reports_unavailable_without_raising(self):
        response = build_client(StubDetector(ready=False)).get("/image-analysis/health")
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["status"], "unavailable")
        self.assertIn("MODEL_MISSING", response.json()["lastError"])

    def test_classes_endpoint_lists_allowlist_and_unsupported(self):
        response = build_client(StubDetector()).get("/image-analysis/classes")
        self.assertEqual(response.status_code, 200)
        body = response.json()
        names = [item["cocoName"] for item in body["supportedClasses"]]
        self.assertIn("bed", names)
        self.assertIn("toilet", names)
        self.assertNotIn("person", names)
        self.assertIn("Bồn tắm", body["unsupportedObjects"])


class AnalyzeTests(unittest.TestCase):
    def test_analyze_returns_detections(self):
        detection = Detection(
            coco_id=59, coco_name="bed", label_vi="Giường", group="bedroom",
            confidence=0.91, box=(0.1, 0.2, 0.6, 0.8), box_pixels=(6, 10, 38, 38),
        )
        client = build_client(StubDetector(detections=[detection]))
        response = client.post(
            "/image-analysis/analyze",
            content=png_bytes(),
            headers={"content-type": "image/png"},
        )
        self.assertEqual(response.status_code, 200)
        body = response.json()
        self.assertEqual(body["status"], "COMPLETED")
        self.assertEqual(body["detectionCount"], 1)
        self.assertEqual(body["detections"][0]["cocoName"], "bed")
        self.assertEqual(body["detections"][0]["label"], "Giường")
        self.assertEqual(body["countsByLabel"], {"Giường": 1})

    def test_analyze_with_no_detections_is_a_success_not_an_error(self):
        client = build_client(StubDetector(detections=[]))
        response = client.post(
            "/image-analysis/analyze",
            content=png_bytes(),
            headers={"content-type": "image/png"},
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()["detectionCount"], 0)
        self.assertEqual(response.json()["detections"], [])

    def test_rejects_unsupported_content_type(self):
        client = build_client(StubDetector())
        response = client.post(
            "/image-analysis/analyze",
            content=b"{}",
            headers={"content-type": "application/json"},
        )
        self.assertEqual(response.status_code, 415)

    def test_rejects_empty_body(self):
        client = build_client(StubDetector())
        response = client.post(
            "/image-analysis/analyze",
            content=b"",
            headers={"content-type": "image/png"},
        )
        self.assertEqual(response.status_code, 400)

    def test_rejects_oversized_declared_length(self):
        client = build_client(StubDetector())
        response = client.post(
            "/image-analysis/analyze",
            content=png_bytes(),
            headers={"content-type": "image/png", "content-length": str(9 * 1024 * 1024)},
        )
        self.assertEqual(response.status_code, 413)

    def test_returns_503_when_model_unavailable(self):
        client = build_client(StubDetector(ready=False))
        response = client.post(
            "/image-analysis/analyze",
            content=png_bytes(),
            headers={"content-type": "image/png"},
        )
        self.assertEqual(response.status_code, 503)

    def test_accepts_jpeg_and_webp_content_types(self):
        client = build_client(StubDetector())
        for content_type in ("image/jpeg", "image/jpg", "image/webp"):
            with self.subTest(content_type=content_type):
                response = client.post(
                    "/image-analysis/analyze",
                    content=png_bytes(),
                    headers={"content-type": content_type},
                )
                self.assertEqual(response.status_code, 200)


class IsolationTests(unittest.TestCase):
    def test_router_does_not_shadow_duplicate_routes(self):
        # The vision router must live under /image-analysis, never /image-duplicates.
        # Inspect the router itself: newer Starlette wraps included routers, so
        # walking ``app.routes`` no longer exposes plain ``path`` attributes.
        router = create_vision_router(VisionSettings(), StubDetector())
        paths = {route.path for route in router.routes}
        self.assertTrue(paths)
        for path in paths:
            self.assertTrue(
                path.startswith("/image-analysis"),
                f"vision route escaped its prefix: {path}",
            )
            self.assertFalse(path.startswith("/image-duplicates"))

    def test_vision_and_duplicate_routers_can_coexist(self):
        # Both routers mounted on one app must keep their own prefixes.
        from app.imagecheck.api import create_image_router

        app = FastAPI()
        app.include_router(create_image_router())
        app.include_router(create_vision_router(VisionSettings(), StubDetector()))
        client = TestClient(app)
        self.assertEqual(client.get("/image-analysis/health").status_code, 200)
        # The duplicate router keeps its own health path untouched.
        self.assertEqual(client.get("/image-duplicates/health").status_code, 200)


if __name__ == "__main__":
    unittest.main()
