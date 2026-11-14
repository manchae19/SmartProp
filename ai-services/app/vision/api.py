"""FastAPI router for YOLOv8 property-image analysis.

Mounted on its own path prefix so it can never shadow the duplicate-image
routes. The router owns no global state beyond the detector instance it is
given, which keeps it testable without a running server.
"""
from __future__ import annotations

import threading
import time
from collections import deque
from typing import Any

from fastapi import APIRouter, HTTPException, Request as StarletteRequest
from starlette.concurrency import run_in_threadpool

from .classes import PROPERTY_CLASSES, UNSUPPORTED_PROPERTY_OBJECTS
from .config import InvalidImage, VisionSettings, VisionUnavailable
from .detector import ALGORITHM_VERSION, PropertyVisionDetector, class_catalog

ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_RATE_LIMIT = (20, 60.0)  # 20 analyses per minute per client


def create_vision_router(
    settings: VisionSettings | None = None,
    detector: PropertyVisionDetector | None = None,
) -> APIRouter:
    settings = settings or VisionSettings.from_env()
    detector = detector or PropertyVisionDetector(settings)
    router = APIRouter(prefix="/image-analysis", tags=["image-analysis"])

    slots = threading.BoundedSemaphore(settings.max_concurrent)
    rate_lock = threading.Lock()
    rate: dict[str, deque[float]] = {}

    def _rate_limit(request: StarletteRequest) -> None:
        limit, window = _RATE_LIMIT
        host = request.client.host if request.client else "unknown"
        now = time.monotonic()
        with rate_lock:
            bucket = rate.setdefault(host, deque())
            while bucket and bucket[0] <= now - window:
                bucket.popleft()
            if len(bucket) >= limit:
                raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu; vui lòng thử lại sau.")
            bucket.append(now)
            if len(rate) > 2000:
                rate.pop(next(iter(rate)))

    @router.get("/health")
    def health() -> dict[str, Any]:
        status = detector.status()
        return {
            **status,
            "maxUploadBytes": settings.max_upload_bytes,
            "maxPixels": settings.max_pixels,
            "maxEdge": settings.max_edge,
            "timeoutSeconds": settings.timeout_seconds,
        }

    @router.get("/classes")
    def classes() -> dict[str, Any]:
        return {
            "algorithmVersion": ALGORITHM_VERSION,
            "supportedClasses": class_catalog(),
            "unsupportedObjects": list(UNSUPPORTED_PROPERTY_OBJECTS),
            "note": "Chỉ các lớp COCO trong danh sách này được báo cáo; vật dụng khác không được nhận diện.",
        }

    @router.post("/analyze")
    async def analyze(request: StarletteRequest) -> dict[str, Any]:
        _rate_limit(request)
        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Chỉ hỗ trợ JPEG, PNG hoặc WebP.")

        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > settings.max_upload_bytes:
            raise HTTPException(status_code=413, detail="Ảnh vượt quá giới hạn dung lượng.")

        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > settings.max_upload_bytes:
                raise HTTPException(status_code=413, detail="Ảnh vượt quá giới hạn dung lượng.")
        if not body:
            raise HTTPException(status_code=400, detail="Ảnh rỗng.")

        if not slots.acquire(blocking=False):
            raise HTTPException(status_code=503, detail="Hệ thống đang phân tích ảnh khác; vui lòng thử lại.")
        try:
            result = await run_in_threadpool(detector.analyze, bytes(body))
        except InvalidImage as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except VisionUnavailable as exc:
            raise HTTPException(status_code=503, detail="Mô hình nhận diện chưa sẵn sàng.") from exc
        finally:
            slots.release()

        return result.as_dict()

    return router
