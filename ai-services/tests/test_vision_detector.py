"""Tests for the YOLOv8 property-image analyser.

These tests use synthetic images so they run without any real photo and without
network access. The detector is exercised for real (the checkpoint is loaded),
which is why the suite is skipped when the weights are absent rather than
silently passing.
"""
from __future__ import annotations

import io
import unittest
from pathlib import Path

import importlib.util
if importlib.util.find_spec("PIL") is None:
    raise unittest.SkipTest("Optional vision dependencies are not installed; use requirements-vision.txt")
from PIL import Image, ImageDraw

from app.vision.classes import (
    BY_COCO_ID,
    EXCLUDED_COCO_NAMES,
    PROPERTY_CLASSES,
    UNSUPPORTED_PROPERTY_OBJECTS,
    class_names,
    group_for,
    label_for,
)
from app.vision.config import InvalidImage, VisionSettings
from app.vision.detector import (
    ALGORITHM_VERSION,
    PropertyVisionDetector,
    _filter_detections,
    _open_bounded,
)

MODEL_DIR = Path(__file__).resolve().parents[1] / "var" / "vision"
HAS_MODEL = (MODEL_DIR / "yolov8n.pt").is_file()


def png_bytes(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def blank(width: int = 320, height: int = 240) -> bytes:
    return png_bytes(Image.new("RGB", (width, height), (235, 235, 235)))


class ClassAllowlistTests(unittest.TestCase):
    def test_every_allowlisted_class_is_a_real_coco_class(self):
        # COCO has exactly 80 classes; an id outside 0..79 cannot exist.
        for item in PROPERTY_CLASSES:
            self.assertGreaterEqual(item.coco_id, 0)
            self.assertLess(item.coco_id, 80)

    def test_allowlist_matches_known_coco_ids(self):
        expected = {
            56: "chair", 57: "couch", 58: "potted plant", 59: "bed",
            60: "dining table", 61: "toilet", 62: "tv", 68: "microwave",
            69: "oven", 71: "sink", 72: "refrigerator", 74: "clock", 75: "vase",
        }
        self.assertEqual({item.coco_id: item.coco_name for item in PROPERTY_CLASSES}, expected)

    def test_no_duplicate_ids_or_names(self):
        ids = [item.coco_id for item in PROPERTY_CLASSES]
        names = [item.coco_name for item in PROPERTY_CLASSES]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertEqual(len(names), len(set(names)))

    def test_allowlist_and_exclusions_do_not_overlap(self):
        allowed = set(class_names())
        self.assertEqual(allowed & set(EXCLUDED_COCO_NAMES), set())

    def test_unsupported_objects_are_not_claimed_as_classes(self):
        # These are the objects a reviewer expects but COCO cannot report.
        allowed = set(class_names())
        for name in ("bathtub", "shower", "wardrobe", "air conditioner"):
            self.assertNotIn(name, allowed)
        self.assertIn("Bồn tắm", UNSUPPORTED_PROPERTY_OBJECTS)

    def test_labels_are_vietnamese_and_groups_are_known(self):
        self.assertEqual(label_for("bed"), "Giường")
        self.assertEqual(group_for("bed"), "bedroom")
        self.assertEqual(group_for("refrigerator"), "kitchen")
        self.assertEqual(group_for("toilet"), "bathroom")
        # Unknown names fall through unchanged rather than inventing a label.
        self.assertEqual(label_for("unicorn"), "unicorn")
        self.assertEqual(group_for("unicorn"), "other")


class BoundsTests(unittest.TestCase):
    def setUp(self):
        self.settings = VisionSettings()

    def test_rejects_empty_payload(self):
        with self.assertRaises(InvalidImage):
            _open_bounded(b"", self.settings)

    def test_rejects_non_image_bytes(self):
        with self.assertRaises(InvalidImage):
            _open_bounded(b"definitely not an image", self.settings)

    def test_rejects_oversized_payload_before_decoding(self):
        with self.assertRaises(InvalidImage):
            _open_bounded(b"\x00" * (self.settings.max_upload_bytes + 1), self.settings)

    def test_rejects_unsupported_format(self):
        buffer = io.BytesIO()
        Image.new("RGB", (64, 64), (10, 10, 10)).save(buffer, format="BMP")
        with self.assertRaises(InvalidImage):
            _open_bounded(buffer.getvalue(), self.settings)

    def test_rejects_image_over_pixel_ceiling(self):
        tight = VisionSettings(max_pixels=1_000_000)
        with self.assertRaises(InvalidImage):
            _open_bounded(blank(1200, 1200), tight)

    def test_rejects_image_over_edge_ceiling(self):
        tight = VisionSettings(max_edge=1000)
        with self.assertRaises(InvalidImage):
            _open_bounded(blank(1200, 100), tight)

    def test_accepts_valid_png_and_reports_format(self):
        image, source_format = _open_bounded(blank(320, 240), self.settings)
        self.assertEqual(source_format, "PNG")
        self.assertEqual((image.width, image.height), (320, 240))

    def test_accepts_jpeg_and_webp(self):
        for fmt in ("JPEG", "WEBP"):
            buffer = io.BytesIO()
            Image.new("RGB", (200, 150), (120, 90, 60)).save(buffer, format=fmt)
            _, source_format = _open_bounded(buffer.getvalue(), self.settings)
            self.assertEqual(source_format, fmt)


class SettingsTests(unittest.TestCase):
    def test_rejects_out_of_range_values(self):
        for kwargs in (
            {"device": "tpu"},
            {"image_size": 100},
            {"confidence_threshold": 0.0},
            {"confidence_threshold": 1.0},
            {"iou_threshold": 1.5},
            {"max_detections": 0},
            {"max_upload_bytes": 10},
            {"max_pixels": 10},
            {"max_edge": 10},
            {"timeout_seconds": 0.1},
            {"max_concurrent": 0},
        ):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError):
                VisionSettings(**kwargs)

    def test_model_path_is_derived_from_directory(self):
        settings = VisionSettings(model_dir=Path("var/vision"), model_file="yolov8n.pt")
        self.assertEqual(settings.model_path, Path("var/vision") / "yolov8n.pt")


class FilterTests(unittest.TestCase):
    """The allowlist filter must drop non-property classes, not relabel them."""

    class _Box:
        def __init__(self, cls_id, conf, xyxy):
            self.cls = _Scalar(cls_id)
            self.conf = _Scalar(conf)
            self.xyxy = [xyxy]

    class _Result:
        def __init__(self, boxes, names):
            self.boxes = boxes
            self.names = names

    def test_drops_classes_outside_the_allowlist(self):
        boxes = [
            FilterTests._Box(0, 0.99, [10, 10, 50, 50]),    # person -> dropped
            FilterTests._Box(59, 0.80, [10, 10, 50, 50]),   # bed -> kept
            FilterTests._Box(2, 0.95, [0, 0, 20, 20]),      # car -> dropped
        ]
        result = _filter_detections([FilterTests._Result(boxes, {})], 100, 100)
        self.assertEqual([item.coco_name for item in result], ["bed"])

    def test_sorts_by_confidence_descending(self):
        boxes = [
            FilterTests._Box(56, 0.40, [0, 0, 10, 10]),
            FilterTests._Box(57, 0.90, [0, 0, 10, 10]),
            FilterTests._Box(59, 0.60, [0, 0, 10, 10]),
        ]
        result = _filter_detections([FilterTests._Result(boxes, {})], 100, 100)
        self.assertEqual([item.coco_name for item in result], ["couch", "bed", "chair"])

    def test_normalises_and_clamps_boxes(self):
        boxes = [FilterTests._Box(59, 0.9, [-5, -5, 150, 150])]
        result = _filter_detections([FilterTests._Result(boxes, {})], 100, 100)
        self.assertEqual(result[0].box, (0.0, 0.0, 1.0, 1.0))
        self.assertEqual(result[0].box_pixels, (0, 0, 100, 100))

    def test_discards_degenerate_boxes(self):
        boxes = [FilterTests._Box(59, 0.9, [50, 50, 50, 50])]
        self.assertEqual(_filter_detections([FilterTests._Result(boxes, {})], 100, 100), [])

    def test_handles_empty_results(self):
        self.assertEqual(_filter_detections([], 100, 100), [])
        self.assertEqual(_filter_detections([FilterTests._Result([], {})], 100, 100), [])


class _Scalar:
    """Mimics a 0-dim torch tensor for the filter tests."""

    def __init__(self, value):
        self._value = value

    def item(self):
        return self._value


@unittest.skipUnless(HAS_MODEL, "yolov8n.pt weights are not present")
class DetectorIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.detector = PropertyVisionDetector(VisionSettings(model_dir=MODEL_DIR))

    def test_model_is_ready(self):
        status = self.detector.status()
        self.assertEqual(status["status"], "ready")
        self.assertEqual(status["algorithmVersion"], ALGORITHM_VERSION)
        self.assertIsNone(status["lastError"])

    def test_blank_image_reports_zero_detections_without_error(self):
        result = self.detector.analyze(blank(640, 480))
        self.assertEqual(result.detections, [])
        self.assertEqual(result.counts_by_label, {})
        self.assertEqual(result.image_format, "PNG")
        self.assertGreater(result.total_ms, 0)

    def test_response_shape_is_stable(self):
        payload = self.detector.analyze(blank(320, 240)).as_dict()
        for key in (
            "status", "algorithmVersion", "modelVersion", "device", "image",
            "detectionCount", "countsByLabel", "detections", "timing",
            "supportedClasses", "unsupportedObjects", "limitations",
        ):
            self.assertIn(key, payload)
        self.assertEqual(payload["status"], "COMPLETED")
        self.assertEqual(payload["detectionCount"], len(payload["detections"]))
        self.assertIn("inferenceMs", payload["timing"])
        self.assertIn("totalMs", payload["timing"])

    def test_every_reported_detection_is_allowlisted(self):
        # A real photo may or may not produce detections; whatever it reports
        # must be inside the allowlist and carry a valid normalised box.
        image = Image.new("RGB", (640, 480), (200, 200, 200))
        draw = ImageDraw.Draw(image)
        draw.rectangle((100, 200, 500, 400), fill=(90, 60, 40))
        result = self.detector.analyze(png_bytes(image))
        allowed = set(class_names())
        for item in result.detections:
            self.assertIn(item.coco_name, allowed)
            self.assertIn(item.coco_id, BY_COCO_ID)
            x1, y1, x2, y2 = item.box
            self.assertTrue(0.0 <= x1 < x2 <= 1.0)
            self.assertTrue(0.0 <= y1 < y2 <= 1.0)
            self.assertTrue(0.0 < item.confidence <= 1.0)

    def test_invalid_bytes_raise_invalid_image(self):
        with self.assertRaises(InvalidImage):
            self.detector.analyze(b"still not an image")


if __name__ == "__main__":
    unittest.main()
