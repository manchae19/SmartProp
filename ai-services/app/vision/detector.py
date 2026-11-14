"""YOLOv8n inference for property photos.

Design constraints that shaped this module:

* **CPU only.** The MVP runs on the same 16 GB machine that already hosts
  XGBoost, RAG and MySQL. A GPU path exists in the settings but is not used.
* **One model, loaded once.** Weights are resolved at construction time and
  never re-fetched per request; a missing checkpoint is a startup error, not a
  silent download.
* **Allowlist filtering happens after inference.** The model predicts all 80
  COCO classes; we keep only the property-relevant ones so the response never
  claims to have looked for a bathtub.
* **No pixel is decoded before its size is checked.** A 40-megapixel ceiling and
  a 12 000-pixel edge ceiling are enforced from the image header, which blocks
  decompression bombs without loading them.

Third-party component: Ultralytics YOLOv8 (``ultralytics`` 8.4.212) with the
stock COCO-pretrained ``yolov8n.pt`` checkpoint, used as published — no
retraining. License **AGPL-3.0**; see ``ai-services/docs/YOLOV8_LICENSE_NOTICE.md``.
"""
from __future__ import annotations

import hashlib
import io
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps, UnidentifiedImageError

from .classes import (
    BY_COCO_ID,
    PROPERTY_CLASSES,
    UNSUPPORTED_PROPERTY_OBJECTS,
    group_for,
    label_for,
)
from .config import InvalidImage, VisionSettings, VisionUnavailable
from .document import DocumentHint, classify_document

SUPPORTED_FORMATS = {"JPEG", "PNG", "WEBP"}
ALGORITHM_VERSION = "yolov8n-property-v1"

# Ultralytics replaces ``PIL.Image.open`` with a wrapper that imports optional
# HEIF support at call time. We keep the stock opener so decoding never depends
# on a plugin we do not ship, and so a missing optional dependency cannot turn a
# valid JPEG into a 500.
_ORIGINAL_IMAGE_OPEN = Image.open


@dataclass(frozen=True)
class Detection:
    """One detected object, already filtered to the property allowlist."""

    coco_id: int
    coco_name: str
    label_vi: str
    group: str
    confidence: float
    # Normalised 0..1 coordinates so the UI can scale to any rendered size.
    box: tuple[float, float, float, float]
    # Pixel coordinates in the original image, for exact overlay rendering.
    box_pixels: tuple[int, int, int, int]

    def as_dict(self) -> dict[str, Any]:
        return {
            "cocoId": self.coco_id,
            "cocoName": self.coco_name,
            "label": self.label_vi,
            "group": self.group,
            "confidence": round(self.confidence, 4),
            "box": [round(value, 5) for value in self.box],
            "boxPixels": list(self.box_pixels),
        }


@dataclass(frozen=True)
class AnalysisResult:
    """Full response for one analysed image."""

    detections: list[Detection]
    width: int
    height: int
    image_format: str
    sha256: str
    inference_ms: float
    total_ms: float
    model_version: str
    device: str
    counts_by_label: dict[str, int] = field(default_factory=dict)
    document_hint: "DocumentHint | None" = None

    def as_dict(self) -> dict[str, Any]:
        return {
            "status": "COMPLETED",
            "algorithmVersion": ALGORITHM_VERSION,
            "modelVersion": self.model_version,
            "device": self.device,
            "image": {
                "width": self.width,
                "height": self.height,
                "format": self.image_format,
                "sha256": self.sha256,
            },
            "detectionCount": len(self.detections),
            "countsByLabel": self.counts_by_label,
            "detections": [item.as_dict() for item in self.detections],
            "documentHint": self.document_hint.as_dict() if self.document_hint else None,
            "timing": {
                "inferenceMs": round(self.inference_ms, 2),
                "totalMs": round(self.total_ms, 2),
            },
            "supportedClasses": [item.coco_name for item in PROPERTY_CLASSES],
            "unsupportedObjects": list(UNSUPPORTED_PROPERTY_OBJECTS),
            "limitations": _limitations(),
        }


def _limitations() -> list[str]:
    return [
        "Mô hình chỉ nhận diện các lớp COCO có trong danh sách hỗ trợ; vật dụng khác không được báo cáo.",
        "Đây là nhận diện đối tượng, không phải thẩm định chất lượng, diện tích hay pháp lý bất động sản.",
        "Không suy ra số phòng, công năng sử dụng hoặc giá trị tài sản từ các đối tượng phát hiện.",
        "Ảnh giấy tờ có thể sinh nhận diện sai (ví dụ con dấu tròn bị nhận thành đồng hồ); hãy xem cảnh báo loại ảnh.",
        "Ảnh chỉ xử lý trong bộ nhớ; không lưu tệp, không ghi cơ sở dữ liệu.",
    ]


def _open_bounded(data: bytes, settings: VisionSettings) -> tuple[Image.Image, str]:
    """Decode an image only after its declared dimensions pass the ceilings.

    Returns the decoded image plus its source format. The format is captured
    before ``exif_transpose`` because that call returns a new image object which
    no longer carries the original ``format`` attribute.
    """
    if not data:
        raise InvalidImage("Ảnh rỗng.")
    if len(data) > settings.max_upload_bytes:
        raise InvalidImage("Ảnh vượt quá giới hạn dung lượng.")
    try:
        image = _ORIGINAL_IMAGE_OPEN(io.BytesIO(data))
        source_format = (image.format or "UNKNOWN").upper()
        if image.format not in SUPPORTED_FORMATS:
            raise InvalidImage("Chỉ hỗ trợ JPEG, PNG hoặc WebP.")
        # Header check first: this is what stops a decompression bomb.
        if image.width <= 0 or image.height <= 0:
            raise InvalidImage("Kích thước ảnh không hợp lệ.")
        if image.width > settings.max_edge or image.height > settings.max_edge:
            raise InvalidImage("Cạnh ảnh vượt quá giới hạn.")
        if image.width * image.height > settings.max_pixels:
            raise InvalidImage("Ảnh có quá nhiều điểm ảnh.")
        image = ImageOps.exif_transpose(image)
        if image.width > settings.max_edge or image.height > settings.max_edge:
            raise InvalidImage("Cạnh ảnh vượt quá giới hạn sau khi xoay.")
        if image.width * image.height > settings.max_pixels:
            raise InvalidImage("Ảnh có quá nhiều điểm ảnh sau khi xoay.")
        image.load()
    except InvalidImage:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImage("Tệp không phải ảnh hợp lệ.") from exc
    return image, source_format


class PropertyVisionDetector:
    """Thread-safe wrapper around one YOLOv8 checkpoint."""

    def __init__(self, settings: VisionSettings | None = None) -> None:
        self.settings = settings or VisionSettings.from_env()
        self._lock = threading.Lock()
        self._model = None
        self._model_version = "unloaded"
        self._load_error: str | None = None
        self._load()

    # -- lifecycle ---------------------------------------------------------
    def _load(self) -> None:
        path = self.settings.model_path
        if not path.is_file():
            self._load_error = f"MODEL_MISSING:{path.name}"
            return
        try:
            from ultralytics import YOLO  # imported lazily so health works without torch

            model = YOLO(str(path))
            model.to(self.settings.device)
            self._model = model
            self._model_version = _checkpoint_version(path)
            self._load_error = None
        except Exception as exc:  # noqa: BLE001 - surfaced through health, never raised at import
            self._load_error = f"MODEL_LOAD_FAILED:{type(exc).__name__}"
            self._model = None

    @property
    def ready(self) -> bool:
        return self._model is not None

    def status(self) -> dict[str, Any]:
        return {
            "status": "ready" if self.ready else "unavailable",
            "modelVersion": self._model_version,
            "algorithmVersion": ALGORITHM_VERSION,
            "device": self.settings.device,
            "imageSize": self.settings.image_size,
            "confidenceThreshold": self.settings.confidence_threshold,
            "supportedClassCount": len(PROPERTY_CLASSES),
            "lastError": self._load_error,
        }

    # -- inference ---------------------------------------------------------
    def analyze(self, data: bytes) -> AnalysisResult:
        if self._model is None:
            raise VisionUnavailable(self._load_error or "MODEL_UNAVAILABLE")

        started = time.perf_counter()
        image, source_format = _open_bounded(data, self.settings)
        width, height = image.width, image.height
        digest = hashlib.sha256(data).hexdigest()

        # Cheap pre-check: a flat scan is not a room, so the UI needs to know
        # that before it renders "3 clocks" from a red seal. Detection still
        # runs — this only annotates the result, it never suppresses it.
        document_hint = classify_document(image)

        # Ultralytics accepts a PIL image directly; no temp file is written.
        rgb = image.convert("RGB")
        with self._lock:
            inference_started = time.perf_counter()
            results = self._model.predict(
                source=rgb,
                imgsz=self.settings.image_size,
                conf=self.settings.confidence_threshold,
                iou=self.settings.iou_threshold,
                max_det=self.settings.max_detections,
                device=self.settings.device,
                verbose=False,
            )
            inference_ms = (time.perf_counter() - inference_started) * 1000.0

        detections = _filter_detections(results, width, height)
        counts: dict[str, int] = {}
        for item in detections:
            counts[item.label_vi] = counts.get(item.label_vi, 0) + 1

        return AnalysisResult(
            detections=detections,
            width=width,
            height=height,
            image_format=source_format,
            sha256=digest,
            inference_ms=inference_ms,
            total_ms=(time.perf_counter() - started) * 1000.0,
            model_version=self._model_version,
            device=self.settings.device,
            counts_by_label=counts,
            document_hint=document_hint,
        )


def _scalar(value: Any) -> float:
    """Read a 0-dim tensor, a numpy scalar or a plain number as a float."""
    return float(value.item() if hasattr(value, "item") else value)


def _row(value: Any) -> list[float]:
    """Read a 1-D tensor or a plain sequence as a list of floats."""
    return [float(item) for item in (value.tolist() if hasattr(value, "tolist") else value)]


def _filter_detections(results: Any, width: int, height: int) -> list[Detection]:
    """Keep only allowlisted COCO classes, highest confidence first."""
    if not results:
        return []
    boxes = getattr(results[0], "boxes", None)
    if boxes is None or len(boxes) == 0:
        return []

    kept: list[Detection] = []
    for box in boxes:
        coco_id = int(_scalar(box.cls))
        spec = BY_COCO_ID.get(coco_id)
        if spec is None:
            # Not a property class: drop it rather than relabel it.
            continue
        confidence = _scalar(box.conf)
        x1, y1, x2, y2 = _row(box.xyxy[0])
        # Clamp to the frame; a box slightly outside is a rounding artefact.
        x1, x2 = max(0.0, min(x1, width)), max(0.0, min(x2, width))
        y1, y2 = max(0.0, min(y1, height)), max(0.0, min(y2, height))
        if x2 <= x1 or y2 <= y1:
            continue
        kept.append(
            Detection(
                coco_id=coco_id,
                coco_name=spec.coco_name,
                label_vi=spec.label_vi,
                group=spec.group,
                confidence=confidence,
                box=(x1 / width, y1 / height, x2 / width, y2 / height),
                box_pixels=(round(x1), round(y1), round(x2), round(y2)),
            )
        )
    kept.sort(key=lambda item: item.confidence, reverse=True)
    return kept


def _checkpoint_version(path: Path) -> str:
    """Stable identifier for the loaded weights: name plus content hash prefix."""
    try:
        digest = hashlib.sha256(path.read_bytes()).hexdigest()[:12]
    except OSError:
        return path.stem
    return f"{path.stem}@{digest}"


def class_catalog() -> list[dict[str, Any]]:
    """Public description of what this service can and cannot report."""
    return [
        {
            "cocoId": item.coco_id,
            "cocoName": item.coco_name,
            "label": item.label_vi,
            "group": item.group,
        }
        for item in PROPERTY_CLASSES
    ]


def label_of(coco_name: str) -> str:
    return label_for(coco_name)


def group_of(coco_name: str) -> str:
    return group_for(coco_name)
