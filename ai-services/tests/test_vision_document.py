"""Tests for the document-likeness pre-check.

The point of these tests is the *negative* case: a real interior photo must
never be flagged as a document, because that would hide legitimate detections.
"""
from __future__ import annotations

import unittest

from PIL import Image, ImageDraw

from app.vision.document import classify_document


def blank_page(width: int = 400, height: int = 520) -> Image.Image:
    """A flat near-white page, like a scanned certificate."""
    return Image.new("RGB", (width, height), (246, 244, 238))


def interior_photo(width: int = 400, height: int = 300) -> Image.Image:
    """A synthetic room: coloured walls, furniture, shadows."""
    image = Image.new("RGB", (width, height), (120, 96, 78))
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, width, height // 2), fill=(196, 188, 172))   # wall
    draw.rectangle((0, height // 2, width, height), fill=(88, 72, 60))  # floor
    draw.rectangle((40, 150, 200, 260), fill=(52, 60, 78))             # sofa
    draw.rectangle((230, 90, 340, 190), fill=(24, 24, 26))             # tv
    draw.ellipse((300, 200, 360, 250), fill=(150, 40, 40))             # cushion
    return image


class DocumentDetectionTests(unittest.TestCase):
    def test_flat_white_page_is_flagged(self):
        hint = classify_document(blank_page())
        self.assertTrue(hint.likely_document)
        self.assertEqual(hint.reason, "DOCUMENT_LIKE")
        self.assertGreaterEqual(hint.bright_fraction, 0.75)
        self.assertGreaterEqual(hint.low_saturation_fraction, 0.70)
        self.assertLessEqual(hint.contrast, 0.15)

    def test_interior_photo_is_not_flagged(self):
        hint = classify_document(interior_photo())
        self.assertFalse(hint.likely_document)
        self.assertEqual(hint.reason, "PHOTOGRAPH_LIKE")

    def test_bright_but_contrasty_image_is_not_flagged(self):
        # A white wall with a dark furniture silhouette: still mostly bright and
        # unsaturated, but the contrast is far above a flat scan. This is the
        # case that must not be suppressed.
        image = Image.new("RGB", (400, 300), (250, 250, 250))
        draw = ImageDraw.Draw(image)
        draw.rectangle((140, 80, 260, 230), fill=(10, 10, 10))
        hint = classify_document(image)
        self.assertFalse(hint.likely_document)
        self.assertEqual(hint.reason, "BRIGHT_BUT_HAS_CONTRAST")
        self.assertGreater(hint.contrast, 0.15)

    def test_bright_and_colourful_image_is_not_flagged(self):
        image = Image.new("RGB", (400, 300), (255, 240, 120))
        hint = classify_document(image)
        self.assertFalse(hint.likely_document)
        self.assertEqual(hint.reason, "BRIGHT_BUT_COLOURFUL")

    def test_dark_image_is_not_flagged(self):
        hint = classify_document(Image.new("RGB", (300, 300), (20, 20, 24)))
        self.assertFalse(hint.likely_document)

    def test_hint_serialises_for_the_api(self):
        payload = classify_document(blank_page()).as_dict()
        for key in ("likelyDocument", "brightFraction", "lowSaturationFraction", "contrast", "reason"):
            self.assertIn(key, payload)
        self.assertIsInstance(payload["likelyDocument"], bool)

    def test_large_image_is_downscaled_before_measuring(self):
        # The measurement must not depend on the original resolution.
        small = classify_document(blank_page(200, 260))
        large = classify_document(blank_page(2000, 2600))
        self.assertEqual(small.likely_document, large.likely_document)
        self.assertAlmostEqual(small.bright_fraction, large.bright_fraction, places=2)

    def test_grayscale_page_is_flagged(self):
        hint = classify_document(Image.new("L", (400, 520), 250).convert("RGB"))
        self.assertTrue(hint.likely_document)


if __name__ == "__main__":
    unittest.main()
