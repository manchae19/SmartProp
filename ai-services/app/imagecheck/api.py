"""Public duplicate-image API. Uploads are processed in memory only."""
from __future__ import annotations

import base64
import re
import threading
import time
from collections import deque

from fastapi import APIRouter, HTTPException, Request as StarletteRequest
from starlette.concurrency import run_in_threadpool

from app.rag.config import Settings
from .hashing import InvalidImage
from .index import ImageIndexUnavailable, PublicImageIndex
from .service import DuplicateImageService


MAX_UPLOAD_BYTES = 8 * 1024 * 1024
MAX_SCAN_IMAGES = 30
MAX_SCAN_BYTES = 64 * 1024 * 1024
ALLOWED_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}
_CHECK_SLOTS = threading.BoundedSemaphore(4)
_SCAN_SLOTS = threading.BoundedSemaphore(2)
_RATE_LOCK = threading.Lock()
_RATE: dict[tuple[str, str], deque[float]] = {}
_RATE_LIMIT = {"check": (30, 60.0), "scan": (10, 60.0)}


def _rate_limit(request: StarletteRequest, action: str) -> None:
    limit, seconds = _RATE_LIMIT[action]
    host = request.client.host if request.client else "unknown"
    now = time.monotonic()
    key = (host, action)
    with _RATE_LOCK:
        bucket = _RATE.setdefault(key, deque())
        while bucket and bucket[0] <= now - seconds:
            bucket.popleft()
        if len(bucket) >= limit:
            raise HTTPException(status_code=429, detail="Quá nhiều yêu cầu; vui lòng thử lại sau.")
        bucket.append(now)
        if len(_RATE) > 2000:
            _RATE.pop(next(iter(_RATE)))


def create_image_router(settings: Settings | None = None) -> APIRouter:
    settings = settings or Settings.from_env()
    index = PublicImageIndex(settings)
    service = DuplicateImageService(index)
    router = APIRouter(tags=["image-duplicates"])

    @router.get("/image-duplicates/health")
    def health():
        return {"status": "configured", "catalogSource": "BACKEND_PUBLIC_API",
                "index": index.status(), "maxUploadBytes": MAX_UPLOAD_BYTES}

    @router.post("/image-duplicates/check")
    async def check(request: StarletteRequest):
        _rate_limit(request, "check")
        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type not in ALLOWED_TYPES:
            raise HTTPException(status_code=415, detail="Chỉ hỗ trợ JPEG, PNG hoặc WebP.")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_UPLOAD_BYTES:
            raise HTTPException(status_code=413, detail="Ảnh vượt quá 8 MB.")
        body = bytearray()
        async for chunk in request.stream():
            body.extend(chunk)
            if len(body) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh vượt quá 8 MB.")
        if not body:
            raise HTTPException(status_code=400, detail="Ảnh rỗng.")
        if not _CHECK_SLOTS.acquire(blocking=False):
            raise HTTPException(status_code=503, detail="Hệ thống đang kiểm tra nhiều ảnh; vui lòng thử lại.")
        try:
            result = await run_in_threadpool(service.check, bytes(body))
        except InvalidImage as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ImageIndexUnavailable as exc:
            raise HTTPException(status_code=503, detail="Không tải được index ảnh công khai.") from exc
        finally:
            _CHECK_SLOTS.release()
        return result

    @router.post("/image-duplicates/scan")
    async def scan(request: StarletteRequest):
        _rate_limit(request, "scan")
        content_type = request.headers.get("content-type", "").split(";")[0].strip().lower()
        if content_type != "application/json":
            raise HTTPException(status_code=415, detail="Scan yêu cầu JSON.")
        declared = request.headers.get("content-length")
        if declared and declared.isdigit() and int(declared) > MAX_SCAN_BYTES:
            raise HTTPException(status_code=413, detail="Batch ảnh vượt quá giới hạn.")
        try:
            body = await request.json()
        except ValueError as exc:
            raise HTTPException(status_code=400, detail="JSON không hợp lệ.") from exc
        property_id = str((body or {}).get("propertyId") or "")
        if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", property_id):
            raise HTTPException(status_code=422, detail="propertyId không hợp lệ.")
        raw_images = (body or {}).get("images")
        if not isinstance(raw_images, list) or not 1 <= len(raw_images) <= MAX_SCAN_IMAGES:
            raise HTTPException(status_code=422, detail="Cần từ 1 đến 30 ảnh.")
        decoded = []
        total = 0
        for item in raw_images:
            if not isinstance(item, dict):
                raise HTTPException(status_code=422, detail="Ảnh scan không hợp lệ.")
            image_id = str(item.get("imageId") or "")
            if not re.fullmatch(r"[A-Za-z0-9_-]{1,64}", image_id):
                raise HTTPException(status_code=422, detail="imageId không hợp lệ.")
            encoded = item.get("data")
            if not isinstance(encoded, str) or len(encoded) > MAX_UPLOAD_BYTES * 2:
                raise HTTPException(status_code=413, detail="Ảnh vượt quá 8 MB.")
            try:
                data = base64.b64decode(encoded, validate=True)
            except (ValueError, TypeError) as exc:
                raise HTTPException(status_code=422, detail="Dữ liệu base64 không hợp lệ.") from exc
            if not data or len(data) > MAX_UPLOAD_BYTES:
                raise HTTPException(status_code=413, detail="Ảnh vượt quá 8 MB.")
            total += len(data)
            if total > MAX_SCAN_BYTES:
                raise HTTPException(status_code=413, detail="Batch ảnh vượt quá giới hạn.")
            decoded.append((image_id, data))
        if not _SCAN_SLOTS.acquire(blocking=False):
            raise HTTPException(status_code=503, detail="Hệ thống đang quét nhiều ảnh; vui lòng thử lại.")
        try:
            result = await run_in_threadpool(service.scan, property_id, decoded)
        except InvalidImage as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except ImageIndexUnavailable as exc:
            raise HTTPException(status_code=503, detail="Không tải được index ảnh công khai.") from exc
        except ValueError as exc:
            raise HTTPException(status_code=422, detail=str(exc)) from exc
        finally:
            _SCAN_SLOTS.release()
        return result

    return router
