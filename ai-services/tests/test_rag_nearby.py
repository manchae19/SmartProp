"""Nearby listings: real distance decides, not the district.

The bounding box only narrows candidates. Every candidate is measured, anything past
the radius is dropped, and the survivors are ordered nearest first.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag import address_search as addr
from app.rag.geo import haversine_meters
from app.rag.schemas import ChatRequest
from app.rag.tools import GroundingError, UpstreamError

ORIGIN = {"latitude": 16.06, "longitude": 108.22}


def at(pid, price, meters, address="Đường Dũng Sĩ Thanh Khê", status="PUBLISHED"):
    """A listing placed exactly `meters` north of the origin."""
    item = fixtures.prop(pid, price, 80)
    item["address"] = address
    item["latitude"] = ORIGIN["latitude"] + meters / 111_194.9
    item["longitude"] = ORIGIN["longitude"]
    item["status"] = status
    item["title"] = "Nhà thử"
    item["transactionType"] = "SALE"
    item["priceUnit"] = "TOTAL"
    item["currency"] = "VND"
    item["source"] = {"kind": "PROPERTY", "recordKey": pid.replace("property:", ""), "name": "Unit"}
    return item


class DistanceTests(unittest.TestCase):
    def test_haversine_matches_known_distances(self):
        self.assertAlmostEqual(haversine_meters(16.06, 108.22, 16.068993, 108.22), 1000.0, delta=1.0)
        self.assertAlmostEqual(haversine_meters(16.06, 108.22, 16.06, 108.22), 0.0, delta=0.01)

    def test_radius_boundary_is_inclusive(self):
        self.assertLessEqual(haversine_meters(16.06, 108.22, 16.068993, 108.22), 1000.0)
        self.assertGreater(haversine_meters(16.06, 108.22, 16.069002, 108.22), 1000.0)


class NearbyAnswerTests(unittest.TestCase):
    def service(self, items):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop("property:a", 2000000000, 90)])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "300 Dũng Sĩ Thanh Khê", "latitude": ORIGIN["latitude"],
             "longitude": ORIGIN["longitude"], "approximate": False}]
        b.search_nearby.return_value = {"bbox": "x", "radiusMeters": 1000, "items": items}
        return s, b

    def ask(self, s, q, sid=None):
        return s.chat(ChatRequest(question=q, sessionId=sid, requireGeneration=False))

    def nearby(self, s, question="Tìm nhà gần 300 Dũng Sĩ Thanh Khê", sid=None):
        """Walk the consent and candidate steps the advisor now requires."""
        first = self.ask(s, question, sid)
        sid = first.evidence["session"]["id"]
        if first.evidence.get("clarification") == "NEAR_ADDRESS_CONSENT":
            second = self.ask(s, "Đồng ý tìm vị trí", sid)
            if second.evidence.get("clarification") == "NEAR_ADDRESS_PICK":
                pick = (second.evidence.get("quickReplies") or [None])[0]
                if pick:
                    return self.ask(s, pick, sid)
            return second
        return first

    def test_999_and_1000_are_kept_and_1001_is_dropped(self):
        s, b = self.service([at("property:near", 2000000000, 999),
                             at("property:edge", 2100000000, 1000),
                             at("property:far", 2200000000, 1001)])
        reply = self.nearby(s)
        ids = [p["id"] for p in reply.recommendedProperties]
        self.assertEqual(ids, ["property:near", "property:edge"])

    def test_results_are_ordered_nearest_first(self):
        s, b = self.service([at("property:c", 2000000000, 900),
                             at("property:a", 2100000000, 100),
                             at("property:b", 2200000000, 500)])
        reply = self.nearby(s)
        self.assertEqual([p["id"] for p in reply.recommendedProperties],
                         ["property:a", "property:b", "property:c"])
        distances = [p["distanceMeters"] for p in reply.recommendedProperties]
        self.assertEqual(distances, sorted(distances))

    def test_at_most_three_cards_after_sorting(self):
        s, b = self.service([at(f"property:{i}", 2000000000, 100 * (i + 1)) for i in range(6)])
        reply = self.nearby(s)
        self.assertEqual(len(reply.recommendedProperties), 3)
        self.assertEqual([p["id"] for p in reply.recommendedProperties],
                         ["property:0", "property:1", "property:2"])

    def test_wording_names_the_radius_and_straight_line(self):
        s, b = self.service([at("property:a", 2000000000, 400)])
        reply = self.nearby(s)
        notes = " ".join(reply.dataLimitations)
        self.assertIn("bán kính 1 km", notes)
        self.assertIn("đường chim bay", notes)
        self.assertIn("Nhà trong bán kính 1 km", reply.answer)

    def test_nothing_inside_the_radius_is_reported_not_filled(self):
        s, b = self.service([at("property:far", 2000000000, 5000)])
        reply = self.nearby(s)
        self.assertEqual(reply.recommendedProperties, [])
        self.assertIn("Chưa tìm thấy tin nhà trong bán kính 1 km", reply.answer)
        self.assertEqual(reply.evidence.get("clarification"), "ADDRESS_NEARBY_EMPTY")

    def test_a_listing_without_coordinates_is_skipped(self):
        broken = fixtures.prop("property:broken", 2000000000, 80)
        broken["latitude"] = None
        broken["longitude"] = None
        s, b = self.service([broken, at("property:ok", 2100000000, 300)])
        reply = self.nearby(s)
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:ok"])

    def test_budget_is_kept_when_the_user_set_one(self):
        s, b = self.service([at("property:a", 2000000000, 300)])
        first = self.ask(s, "Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ.")
        sid = first.evidence["session"]["id"]
        self.ask(s, "Toàn Đà Nẵng", sid)
        self.ask(s, "Bỏ qua, xem nhà trong ngân sách", sid)
        # Same session: the budget set earlier must reach the nearby search.
        self.nearby(s, sid=sid)
        kwargs = b.search_nearby.call_args.kwargs
        self.assertIsNotNone(kwargs.get("max_price"))

    def test_service_failure_is_reported(self):
        s, b = self.service([])
        b.search_nearby.side_effect = UpstreamError(502)
        reply = self.nearby(s)
        self.assertEqual(reply.evidence.get("clarification"), "ADDRESS_SEARCH_UNAVAILABLE")
        self.assertEqual(reply.recommendedProperties, [])

    def test_the_button_text_uses_the_same_path(self):
        s, b = self.service([at("property:a", 2000000000, 300)])
        reply = self.nearby(s, "Xem nhà gần 300 Dũng Sĩ Thanh Khê")
        self.assertTrue(reply.evidence.get("nearAddress"))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:a"])

    def test_second_card_after_a_nearby_list(self):
        s, b = self.service([at("property:a", 2000000000, 100),
                             at("property:b", 2100000000, 500)])
        first = self.nearby(s)
        sid = first.evidence["session"]["id"]
        shown = [p["id"] for p in first.recommendedProperties]
        b.property_detail.return_value = at("property:b", 2100000000, 500)
        s.repository.lookup.side_effect = None
        s.repository.lookup.return_value = [{"id": "b", "price": 2100000000, "area_sqm": 80}]
        reply = self.ask(s, "Căn thứ hai giá bao nhiêu?", sid)
        self.assertEqual([p["id"] for p in reply.recommendedProperties], [shown[1]])

    def test_an_amenity_question_still_uses_the_poi_path(self):
        s, b = self.service([])
        reply = self.ask(s, "Gần 300 Dũng Sĩ Thanh Khê có bệnh viện nào?")
        b.search_nearby.assert_not_called()
        self.assertIsNotNone(reply.evidence.get("amenityIntent"))


class IntentTests(unittest.TestCase):
    def test_button_and_typed_question_share_the_intent(self):
        for text in ("Xem nhà gần 300 Dũng Sĩ Thanh Khê",
                     "Tìm nhà gần 300 Dũng Sĩ Thanh Khê",
                     "Cho tôi xem nhà gần 300 Dũng Sĩ Thanh Khê"):
            self.assertEqual(addr.intent(text), "NEAR_ADDRESS", text)

    def test_an_amenity_question_is_not_a_nearby_search(self):
        for text in ("Gần 300 Dũng Sĩ Thanh Khê có bệnh viện nào?",
                     "Gần 300 Dũng Sĩ Thanh Khê có chợ nào?"):
            self.assertIsNone(addr.intent(text), text)


if __name__ == "__main__":
    unittest.main()
