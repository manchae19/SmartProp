"""Detect document-like photos before running object detection.

A property listing often includes a scan of the land certificate (sổ đỏ), a
contract, or an ID page. YOLOv8 has no "document" class, so it does the only
thing it can: it finds round shapes and calls them clocks. That produced a real
false positive in the MVP (a red seal read as three clocks).

This module answers a narrower question than "is this a legal document?":

    Does this image look like a flat, bright, low-saturation scan
    rather than a photograph of a room?

It is a **presentation hint**, not a legal verdict. The caller must never use it
to claim a document is fake, invalid, or unverified. Its only job is to let the
UI say "this looks like a document, so object detection is not meaningful here"
instead of showing three phantom clocks.

Design constraints:

* **Cheap.** Runs on a downscaled copy, no model, no extra dependency.
* **Conservative.** A real interior photo must never be flagged. The thresholds
  below were checked against all 44 real listing images in the repository: only
  the two copies of the same land certificate were flagged.
* **Never suppresses detection by itself.** It returns a hint; the detector
  still runs and still reports what it saw. The UI decides how to present it.
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from PIL import Image

# Analysis runs on a small copy; document-ness is a global property.
_SAMPLE_EDGE = 256

# A scanned page is mostly near-white, mostly unsaturated, and has low local
# contrast. All three must hold, which is what keeps bright interiors out.
_BRIGHT_VALUE = 0.85
_BRIGHT_FRACTION = 0.75
_LOW_SATURATION = 0.12
_LOW_SATURATION_FRACTION = 0.70
_MAX_CONTRAST = 0.15


@dataclass(frozen=True)
class DocumentHint:
    """Result of the document-likeness check."""

    likely_document: bool
    bright_fraction: float
    low_saturation_fraction: float
    contrast: float
    reason: str

    def as_dict(self) -> dict:
        return {
            "likelyDocument": self.likely_document,
            "brightFraction": round(self.bright_fraction, 4),
            "lowSaturationFraction": round(self.low_saturation_fraction, 4),
            "contrast": round(self.contrast, 4),
            "reason": self.reason,
        }


def _measure(image: Image.Image) -> tuple[float, float, float]:
    """Return (bright fraction, low-saturation fraction, contrast)."""
    small = image.convert("RGB")
    if max(small.width, small.height) > _SAMPLE_EDGE:
        small = small.copy()
        small.thumbnail((_SAMPLE_EDGE, _SAMPLE_EDGE), Image.Resampling.BILINEAR)

    pixels = np.asarray(small, dtype=np.float32) / 255.0
    high = pixels.max(axis=2)
    low = pixels.min(axis=2)
    # HSV saturation, guarded against a zero denominator.
    saturation = np.where(high > 0, (high - low) / np.maximum(high, 1e-6), 0.0)
    gray = pixels.mean(axis=2)

    bright_fraction = float((high > _BRIGHT_VALUE).mean())
    low_saturation_fraction = float((saturation < _LOW_SATURATION).mean())
    contrast = float(gray.std())
    return bright_fraction, low_saturation_fraction, contrast


def classify_document(image: Image.Image) -> DocumentHint:
    """Decide whether an image looks like a flat document scan.

    Returns a hint only. The caller keeps full responsibility for how it is
    worded to a user; nothing here asserts anything about legality.
    """
    bright, low_sat, contrast = _measure(image)

    is_document = (
        bright >= _BRIGHT_FRACTION
        and low_sat >= _LOW_SATURATION_FRACTION
        and contrast <= _MAX_CONTRAST
    )

    if is_document:
        reason = "DOCUMENT_LIKE"
    elif bright >= _BRIGHT_FRACTION and low_sat >= _LOW_SATURATION_FRACTION:
        reason = "BRIGHT_BUT_HAS_CONTRAST"
    elif bright >= _BRIGHT_FRACTION:
        reason = "BRIGHT_BUT_COLOURFUL"
    else:
        reason = "PHOTOGRAPH_LIKE"

    return DocumentHint(
        likely_document=is_document,
        bright_fraction=bright,
        low_saturation_fraction=low_sat,
        contrast=contrast,
        reason=reason,
    )
