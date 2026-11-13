"""In-memory public property image duplicate index."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
import time
from threading import RLock
from typing import Iterable

import httpx

from app.rag.config import RagUnavailable, Settings
from app.rag.tools import PublishedPropertyRepository
from .hashing import Fingerprint, InvalidImage, fingerprint


MAX_IMAGES = 250
MAX_FETCH_BYTES = 8 * 1024 * 1024
CACHE_SECONDS = 300.0


class ImageIndexUnavailable(RuntimeError):
    pass


@dataclass(frozen=True)
class IndexedImage:
    property_id: str
    image_id: str
    listing_code: str | None
    title: str | None
    district: str | None
    ward: str | None
    url: str
    fingerprint: Fingerprint


class PublicImageIndex:
    def __init__(self, settings: Settings, repository: PublishedPropertyRepository | None = None):
        self.settings = settings
        self.repository = repository or PublishedPropertyRepository(settings)
        self._lock = RLock()
        self._items: list[IndexedImage] = []
        self._built_at = 0.0
        self._last_error: str | None = None

    def _fetch(self, item: dict) -> IndexedImage | None:
        url = str(item.get("url") or "")
        backend_prefix = (self.settings.image_backend_url or self.settings.backend_url).rstrip("/") + "/api/v1/properties/"
        if not (url.startswith(backend_prefix) or url.startswith("https://res.cloudinary.com/")):
            return None
        try:
            with httpx.Client(follow_redirects=False, timeout=4.0) as client:
                response = client.get(url)
                if response.status_code != 200 or len(response.content) > MAX_FETCH_BYTES:
                    return None
                content_type = response.headers.get("content-type", "").split(";")[0].lower()
                if not content_type.startswith("image/"):
                    return None
                return IndexedImage(
                    property_id=item["propertyId"], image_id=item["imageId"],
                    listing_code=item.get("listingCode"), title=item.get("title"),
                    district=item.get("district"), ward=item.get("ward"),
                    url=item.get("publicUrl") or url,
                    fingerprint=fingerprint(response.content),
                )
        except (httpx.HTTPError, InvalidImage, OSError, ValueError):
            return None

    def _build(self) -> None:
        try:
            metadata = self.repository.list_public_images(MAX_IMAGES)
        except RagUnavailable as exc:
            self._last_error = str(exc)
            raise ImageIndexUnavailable("IMAGE_INDEX_UNAVAILABLE") from exc
        if not metadata:
            self._last_error = "NO_PUBLIC_IMAGES"
            raise ImageIndexUnavailable("NO_PUBLIC_IMAGES")
        items: list[IndexedImage] = []
        with ThreadPoolExecutor(max_workers=8) as pool:
            futures = [pool.submit(self._fetch, item) for item in metadata]
            for future in as_completed(futures):
                value = future.result()
                if value is not None:
                    items.append(value)
        if not items:
            self._last_error = "IMAGE_BYTES_UNAVAILABLE"
            raise ImageIndexUnavailable("IMAGE_BYTES_UNAVAILABLE")
        self._items = items
        self._built_at = time.monotonic()
        self._last_error = None

    def get(self, exclude_property_id: str | None = None) -> list[IndexedImage]:
        with self._lock:
            if self._items and time.monotonic() - self._built_at < CACHE_SECONDS:
                items = list(self._items)
            else:
                self._build()
                items = list(self._items)
        if exclude_property_id:
            return [item for item in items if item.property_id != exclude_property_id]
        return items

    def status(self) -> dict:
        return {"count": len(self._items), "cached": bool(self._items),
                "lastError": self._last_error}
