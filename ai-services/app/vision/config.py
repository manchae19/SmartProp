"""Bounded configuration for the YOLOv8 property-image analyser.

Every limit here is a hard ceiling, not a suggestion: the detector runs on CPU
inside the same process that serves the request, so an unbounded image or an
unbounded batch would stall the event loop for every other caller.
"""
from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


class VisionUnavailable(RuntimeError):
    """The detector cannot serve this request (model missing, not loaded)."""


class InvalidImage(ValueError):
    """The uploaded bytes are not a supported, decodable image."""


@dataclass(frozen=True)
class VisionSettings:
    # Weights are resolved from this directory; nothing is downloaded at request time.
    model_dir: Path = Path("var/vision")
    model_file: str = "yolov8n.pt"
    # Inference is CPU-only in this MVP; the checkpoint is small enough for it.
    device: str = "cpu"
    # 640 is the checkpoint's native training size; changing it changes accuracy.
    image_size: int = 640
    confidence_threshold: float = 0.25
    iou_threshold: float = 0.45
    max_detections: int = 100
    # Upload ceilings, checked before any pixel is decoded.
    max_upload_bytes: int = 8 * 1024 * 1024
    max_pixels: int = 40_000_000
    max_edge: int = 12_000
    # Wall-clock ceiling for one inference call.
    timeout_seconds: float = 20.0
    # Concurrency: one CPU-bound inference at a time keeps latency predictable.
    max_concurrent: int = 1

    def __post_init__(self) -> None:
        if self.device not in ("cpu", "cuda"):
            raise ValueError("Vision device must be cpu or cuda")
        if not 320 <= self.image_size <= 1280:
            raise ValueError("Vision image size must be between 320 and 1280")
        if not 0.0 < self.confidence_threshold < 1.0:
            raise ValueError("Vision confidence threshold must be between 0 and 1")
        if not 0.0 < self.iou_threshold < 1.0:
            raise ValueError("Vision IoU threshold must be between 0 and 1")
        if not 1 <= self.max_detections <= 300:
            raise ValueError("Vision max detections must be between 1 and 300")
        if not 1024 <= self.max_upload_bytes <= 32 * 1024 * 1024:
            raise ValueError("Vision upload limit must be between 1 KiB and 32 MiB")
        if not 1_000_000 <= self.max_pixels <= 100_000_000:
            raise ValueError("Vision pixel limit must be between 1 and 100 megapixels")
        if not 1_000 <= self.max_edge <= 20_000:
            raise ValueError("Vision edge limit must be between 1000 and 20000 pixels")
        if not 1.0 <= self.timeout_seconds <= 120.0:
            raise ValueError("Vision timeout must be between 1 and 120 seconds")
        if not 1 <= self.max_concurrent <= 4:
            raise ValueError("Vision concurrency must be between 1 and 4")

    @property
    def model_path(self) -> Path:
        return self.model_dir / self.model_file

    @classmethod
    def from_env(cls) -> "VisionSettings":
        return cls(
            model_dir=Path(os.getenv("VISION_MODEL_DIR", "var/vision")),
            model_file=os.getenv("VISION_MODEL_FILE", "yolov8n.pt"),
            device=os.getenv("VISION_DEVICE", "cpu"),
            image_size=int(os.getenv("VISION_IMAGE_SIZE", "640")),
            confidence_threshold=float(os.getenv("VISION_CONFIDENCE", "0.25")),
            iou_threshold=float(os.getenv("VISION_IOU", "0.45")),
            max_detections=int(os.getenv("VISION_MAX_DETECTIONS", "100")),
            max_upload_bytes=int(os.getenv("VISION_MAX_UPLOAD_BYTES", str(8 * 1024 * 1024))),
            max_pixels=int(os.getenv("VISION_MAX_PIXELS", "40000000")),
            max_edge=int(os.getenv("VISION_MAX_EDGE", "12000")),
            timeout_seconds=float(os.getenv("VISION_TIMEOUT_SECONDS", "20")),
            max_concurrent=int(os.getenv("VISION_MAX_CONCURRENT", "1")),
        )
