"""Answers about the single listing the user opened.

These tests pin the wording rules: a missing fact is reported as missing, and a
straight-line distance is never presented as travel time.
"""
import unittest
from decimal import Decimal

from app.rag import focused_property as fp


DETAIL = {
    "id": "41307d0c-77f6-408e-9b87-12a250c73ebe",
    "title": "Bán nhà mặt tiền Ngô Thế Liệu",
    "priceVnd": 5_000_000_000.0,
    "areaSqm": 80.0,
    "district": "Hải Châu",
    "ward": "Phường Bình Hiên",
    "propertyType": "HOUSE",
    "listingCode": "SP001",
}


class IntentTests(unittest.TestCase):
    def test_detects_price_question(self):
        self.assertEqual(fp.focused_intent("Căn này giá bao nhiêu?"), "PRICE")

    def test_detects_amenity_question(self):
        self.assertEqual(fp.focused_intent("Gần bệnh viện nào?"), "AMENITY")

    def test_detects_commute_question(self):
        self.assertEqual(fp.focused_intent("Căn này đi làm mất bao lâu?"), "COMMUTE")

    def test_detects_area_question(self):
        self.assertEqual(fp.focused_intent("Diện tích bao nhiêu m2?"), "AREA")

    def test_returns_none_for_unrelated_question(self):
        self.assertIsNone(fp.focused_intent("Thời tiết hôm nay thế nào?"))


class AmenityCategoryTests(unittest.TestCase):
    def test_maps_hospital(self):
        self.assertEqual(fp.amenity_category("Gần bệnh viện nào?"), "HOSPITAL")

    def test_maps_school(self):
        self.assertEqual(fp.amenity_category("Có trường học gần không?"), "SCHOOL")

    def test_returns_none_without_a_category(self):
        self.assertIsNone(fp.amenity_category("Có tiện ích gì?"))


class PriceAnswerTests(unittest.TestCase):
    def test_states_the_listing_price(self):
        answer = fp.price_answer(DETAIL)
        self.assertIn("5.000.000.000 đồng", answer)
        self.assertIn("Hải Châu", answer)

    def test_includes_price_per_square_metre(self):
        answer = fp.price_answer(DETAIL)
        self.assertIn("/m²", answer)


class AreaAnswerTests(unittest.TestCase):
    def test_reports_the_area(self):
        self.assertIn("80 m²", fp.area_answer(DETAIL))

    def test_reports_missing_area_instead_of_guessing(self):
        answer = fp.area_answer({**DETAIL, "areaSqm": None})
        self.assertIn("chưa có dữ liệu diện tích", answer)


class AmenityAnswerTests(unittest.TestCase):
    def test_labels_distance_as_straight_line(self):
        pois = [{"name": "Bệnh viện Đà Nẵng", "category": "HOSPITAL", "distanceMeters": 850.0}]
        answer = fp.amenity_answer(DETAIL, pois, "HOSPITAL")
        self.assertIn("Bệnh viện Đà Nẵng", answer)
        self.assertIn("đường chim bay", answer)
        self.assertNotIn("phút", answer)

    def test_reports_missing_evidence_instead_of_guessing(self):
        answer = fp.amenity_answer(DETAIL, [], "HOSPITAL")
        self.assertIn("Chưa có dữ liệu", answer)

    def test_reports_when_the_requested_category_is_absent(self):
        pois = [{"name": "Trường A", "category": "SCHOOL", "distanceMeters": 300.0}]
        answer = fp.amenity_answer(DETAIL, pois, "HOSPITAL")
        self.assertIn("Chưa có dữ liệu", answer)

    def test_caps_at_three_nearest(self):
        pois = [{"name": f"BV {i}", "category": "HOSPITAL", "distanceMeters": float(100 * i)} for i in range(1, 7)]
        answer = fp.amenity_answer(DETAIL, pois, "HOSPITAL")
        self.assertEqual(answer.count("- BV"), 3)


class CommuteAnswerTests(unittest.TestCase):
    def test_reports_distance_and_duration(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0}
        answer = fp.commute_answer(DETAIL, commute, "drive")
        self.assertIn("4.2 km", answer)
        self.assertIn("15 phút", answer)
        self.assertIn("ô tô", answer)

    def test_marks_a_route_within_the_threshold(self):
        commute = {"distanceMeters": 4200.0, "durationSeconds": 900.0}
        self.assertIn("trong mốc 25 phút", fp.commute_answer(DETAIL, commute, "drive", 25))

    def test_marks_a_route_over_the_threshold(self):
        commute = {"distanceMeters": 12000.0, "durationSeconds": 2400.0}
        self.assertIn("vượt mốc 25 phút", fp.commute_answer(DETAIL, commute, "drive", 25))

    def test_reports_when_the_route_is_unavailable(self):
        self.assertIn("Chưa tính được", fp.commute_answer(DETAIL, None, "drive"))


class ThresholdTests(unittest.TestCase):
    def test_reads_a_minute_threshold(self):
        self.assertEqual(fp.commute_threshold("Tôi muốn đi làm dưới 25 phút"), 25)

    def test_ignores_an_absurd_threshold(self):
        self.assertIsNone(fp.commute_threshold("dưới 999 phút"))

    def test_returns_none_without_a_threshold(self):
        self.assertIsNone(fp.commute_threshold("Căn này đi làm mất bao lâu?"))


if __name__ == "__main__":
    unittest.main()
