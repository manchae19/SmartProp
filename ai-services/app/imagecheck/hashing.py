"""Public-image duplicate detection primitives.

This module never writes an uploaded image to disk or to the database. It only
compares an in-memory upload against public SmartProp image metadata.
"""
from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
import hashlib
import math

import numpy as np
from PIL import Image, ImageOps, UnidentifiedImageError


MAX_PIXELS = 40_000_000
MAX_EDGE = 12_000
_HASH_SIZE = 8
_DCT_SIZE = 32


class InvalidImage(ValueError):
    pass


@dataclass(frozen=True)
class Fingerprint:
    sha256: str
    dhash: int
    phash: int
    histogram: np.ndarray
    layout: np.ndarray
    width: int
    height: int
    format: str


def _open(data: bytes) -> Image.Image:
    try:
        image = Image.open(BytesIO(data))
        if image.format not in {"JPEG", "PNG", "WEBP"}:
            raise InvalidImage("UNSUPPORTED_IMAGE_FORMAT")
        # Check dimensions before decoding pixels; this blocks decompression bombs.
        if image.width <= 0 or image.height <= 0 or image.width > MAX_EDGE or image.height > MAX_EDGE:
            raise InvalidImage("IMAGE_DIMENSIONS_INVALID")
        image = ImageOps.exif_transpose(image)
        if image.width <= 0 or image.height <= 0 or image.width > MAX_EDGE or image.height > MAX_EDGE:
            raise InvalidImage("IMAGE_DIMENSIONS_INVALID")
        if image.width * image.height > MAX_PIXELS:
            raise InvalidImage("IMAGE_TOO_LARGE")
        image.load()
    except InvalidImage:
        raise
    except (UnidentifiedImageError, OSError, ValueError) as exc:
        raise InvalidImage("INVALID_IMAGE") from exc
    return image


def _dhash(image: Image.Image) -> int:
    gray = image.convert("L").resize((_HASH_SIZE + 1, _HASH_SIZE), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.int16)
    bits = pixels[:, 1:] >= pixels[:, :-1]
    value = 0
    for bit in bits.flatten():
        value = (value << 1) | int(bit)
    return value


def _phash(image: Image.Image) -> int:
    gray = image.convert("L").resize((_DCT_SIZE, _DCT_SIZE), Image.Resampling.LANCZOS)
    pixels = np.asarray(gray, dtype=np.float64)
    # Orthogonal DCT-II matrix for a small fixed image; no external model required.
    n = _DCT_SIZE
    c = np.empty((n, n), dtype=np.float64)
    for k in range(n):
        scale = math.sqrt(1.0 / n) if k == 0 else math.sqrt(2.0 / n)
        for x in range(n):
            c[k, x] = scale * math.cos(math.pi * (2 * x + 1) * k / (2 * n))
    coefficients = c @ pixels @ c.T
    low = coefficients[:_HASH_SIZE, :_HASH_SIZE].flatten()
    median = np.median(low)
    value = 0
    for bit in (low >= median):
        value = (value << 1) | int(bit)
    return value


def _histogram(image: Image.Image) -> np.ndarray:
    small = image.convert("RGB").resize((32, 32), Image.Resampling.LANCZOS)
    pixels = np.asarray(small, dtype=np.uint8)
    bins = (pixels // 64).astype(np.int16)
    index = bins[:, :, 0] * 16 + bins[:, :, 1] * 4 + bins[:, :, 2]
    values = np.bincount(index.flatten(), minlength=64).astype(np.float64)
    values /= max(1.0, values.sum())
    return values


def _layout(image: Image.Image) -> np.ndarray:
    small = image.convert("L").resize((16, 16), Image.Resampling.LANCZOS)
    values = np.asarray(small, dtype=np.float32).flatten() / 255.0
    norm = float(np.linalg.norm(values))
    return values / norm if norm else values


def fingerprint(data: bytes) -> Fingerprint:
    image = _open(data)
    return Fingerprint(
        sha256=hashlib.sha256(data).hexdigest(),
        dhash=_dhash(image),
        phash=_phash(image),
        histogram=_histogram(image),
        layout=_layout(image),
        width=image.width,
        height=image.height,
        format=(image.format or "UNKNOWN").upper(),
    )


def hamming(left: int, right: int) -> int:
    return (left ^ right).bit_count()


def cosine(left: np.ndarray, right: np.ndarray) -> float:
    denominator = float(np.linalg.norm(left) * np.linalg.norm(right))
    return float(np.dot(left, right) / denominator) if denominator else 0.0
