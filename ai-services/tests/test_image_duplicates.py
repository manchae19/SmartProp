import io

from PIL import Image, ImageDraw, ImageEnhance
import unittest

from app.imagecheck.hashing import fingerprint, hamming
from app.imagecheck.index import IndexedImage
from app.imagecheck.service import DuplicateImageService


def image_bytes(image):
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def base_image():
    image = Image.new("RGB", (160, 120), (30, 80, 140))
    draw = ImageDraw.Draw(image)
    draw.rectangle((15, 20, 90, 100), fill=(220, 180, 40))
    draw.ellipse((95, 25, 145, 90), fill=(230, 230, 220))
    return image


class ImageFingerprintTests(unittest.TestCase):
    def test_resize_and_brightness_are_near_duplicates(self):
        original = fingerprint(image_bytes(base_image()))
        resized = fingerprint(image_bytes(base_image().resize((80, 60))))
        bright = fingerprint(image_bytes(ImageEnhance.Brightness(base_image()).enhance(1.25)))
        self.assertNotEqual(original.sha256, resized.sha256)
        self.assertLessEqual(hamming(original.dhash, resized.dhash), 12)
        self.assertLessEqual(hamming(original.phash, resized.phash), 20)
        self.assertLessEqual(hamming(original.dhash, bright.dhash), 12)

    def test_different_image_is_not_an_exact_hash(self):
        other = Image.new("RGB", (160, 120), (210, 210, 210))
        ImageDraw.Draw(other).polygon(((0, 120), (80, 0), (160, 120)), fill=(10, 20, 30))
        left = fingerprint(image_bytes(base_image()))
        right = fingerprint(image_bytes(other))
        self.assertNotEqual(left.sha256, right.sha256)
        self.assertNotEqual((left.dhash, left.phash), (right.dhash, right.phash))

    def test_exact_bytes_have_same_sha(self):
        data = image_bytes(base_image())
        self.assertEqual(fingerprint(data).sha256, fingerprint(data).sha256)

    def test_service_classifies_exact_and_different_without_claiming_theft(self):
        data = image_bytes(base_image())
        reference = IndexedImage("property-1", "image-1", "SP001", "Fixture",
                                 "Hải Châu", "Nam Dương", "/api/v1/properties/property-1/images/image-1/content",
                                 fingerprint(data))

        class FakeIndex:
            def get(self, exclude_property_id=None):
                return [reference]

            def status(self):
                return {"count": 1, "cached": True, "lastError": None}

        exact = DuplicateImageService(FakeIndex()).check(data)
        self.assertEqual(exact["status"], "EXACT_DUPLICATE")
        self.assertEqual(exact["matches"][0]["method"], "SHA256")
        self.assertTrue(any("không phải kết luận" in item for item in exact["limitations"]))

        other = Image.new("RGB", (160, 120), (255, 255, 255))
        ImageDraw.Draw(other).ellipse((20, 20, 140, 100), fill=(0, 0, 0))
        different = DuplicateImageService(FakeIndex()).check(image_bytes(other))
        self.assertNotEqual(different["status"], "EXACT_DUPLICATE")


class BatchScanTests(unittest.TestCase):
    def test_scan_excludes_current_listing_and_detects_cross_listing(self):
        data = image_bytes(base_image())
        reference = IndexedImage("property-2", "image-2", "SP002", "Other",
                                 "Hải Châu", "Nam Dương", "/api/v1/properties/property-2/images/image-2/content",
                                 fingerprint(data))
        own = IndexedImage("property-1", "own-image", "SP001", "Own",
                           "Hải Châu", "Nam Dương", "/api/v1/properties/property-1/images/own/content",
                           fingerprint(data))

        class FakeIndex:
            def get(self, exclude_property_id=None):
                return [item for item in [reference, own] if item.property_id != exclude_property_id]

            def status(self):
                return {"count": 2, "cached": True, "lastError": None}

        result = DuplicateImageService(FakeIndex()).scan("property-1", [("new-image", data)])
        self.assertEqual(result["status"], "COMPLETED")
        self.assertEqual(result["images"][0]["classification"], "EXACT_DUPLICATE")
        self.assertEqual(result["images"][0]["matches"][0]["propertyId"], "property-2")
        self.assertTrue(all(item["propertyId"] != "property-1" for item in result["images"][0]["matches"]))

    def test_scan_detects_intra_listing_without_cross_listing_alert(self):
        data = image_bytes(base_image())

        class EmptyIndex:
            def get(self, exclude_property_id=None):
                return []

            def status(self):
                return {"count": 0, "cached": True, "lastError": None}

        result = DuplicateImageService(EmptyIndex()).scan("property-1", [
            ("image-a", data),
            ("image-b", image_bytes(base_image().resize((80, 60)))),
        ])
        self.assertEqual(result["images"][0]["classification"], "INTRA_DUPLICATE")
        self.assertEqual(result["images"][0]["matches"], [])
        self.assertGreaterEqual(len(result["images"][0]["intraMatches"]), 1)


if __name__ == "__main__":
    unittest.main()
