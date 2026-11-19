"""Finding a house by its street address.

The house number is part of the address, never a budget, and the street is kept whole
so "Dũng Sĩ Thanh Khê" is not reduced to a district. Three intents must stay apart:
at the address, near the address, and an amenity question that happens to name one.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag import address_search as addr
from app.rag.schemas import ChatRequest
from app.rag.tools import GroundingError, UpstreamError


def listing(pid, price, address, title="Nhà"):
    item = fixtures.prop(pid, price, 80)
    item["address"] = address
    item["title"] = title
    return item


class ParsingTests(unittest.TestCase):
    def test_house_number_and_street_are_kept_together(self):
        self.assertEqual(addr.address_in("Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê"),
                         "300 Dũng Sĩ Thanh Khê")

    def test_without_diacritics(self):
        self.assertEqual(addr.address_in("Tôi muốn tìm nhà ở 300 dung si thanh khe"),
                         "300 dung si thanh khe")

    def test_extra_spaces_and_case(self):
        self.assertEqual(addr.address_in("tìm nhà ở  300   DŨNG SĨ THANH KHÊ"),
                         "300 DŨNG SĨ THANH KHÊ")

    def test_a_budget_is_not_an_address(self):
        for text in ("Tôi có 3 tỷ, tìm nhà ở Đà Nẵng", "tìm nhà 2 tỷ", "nhà 3 phòng ngủ",
                     "tìm nhà 300 triệu"):
            self.assertIsNone(addr.address_in(text), text)

    def test_three_intents_stay_apart(self):
        self.assertEqual(addr.intent("Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê"), "AT_ADDRESS")
        self.assertEqual(addr.intent("Tìm nhà gần 300 Dũng Sĩ Thanh Khê"), "NEAR_ADDRESS")
        self.assertIsNone(addr.intent("Gần 300 Dũng Sĩ Thanh Khê có bệnh viện nào?"))

    def test_house_number_must_match_exactly(self):
        wanted = "300 Dũng Sĩ Thanh Khê"
        self.assertTrue(addr.matches("300 Dũng Sĩ Thanh Khê, Thanh Khê Tây", wanted))
        self.assertTrue(addr.matches("300 dung si thanh khe", wanted))
        self.assertFalse(addr.matches("30 Dũng Sĩ Thanh Khê", wanted))
        self.assertFalse(addr.matches("3000 Dũng Sĩ Thanh Khê", wanted))
        self.assertFalse(addr.matches("300 Nguyễn Văn Linh", wanted))
        self.assertFalse(addr.matches("Đường Dũng Sĩ Thanh Khê", wanted))


class AddressAnswerTests(unittest.TestCase):
    def service(self, items, total=None):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop("property:a", 2000000000, 90)])
        b.search_by_address.return_value = {
            "address": "300 Dũng Sĩ Thanh Khê",
            "total": total if total is not None else len(items),
            "items": items}
        return s, b

    def ask(self, s, question, sid=None):
        return s.chat(ChatRequest(question=question, sessionId=sid, requireGeneration=False))

    def test_matching_listing_is_returned_as_a_card(self):
        s, b = self.service([listing("property:x", 2500000000, "300 Dũng Sĩ Thanh Khê, Thanh Khê Tây")])
        reply = self.ask(s, "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê")
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:x"])
        self.assertEqual(reply.recommendedProperties[0]["priceVnd"], 2500000000)
        self.assertIn("300 Dũng Sĩ Thanh Khê", reply.answer)

    def test_a_different_house_number_is_not_a_match(self):
        s, b = self.service([listing("property:x", 2500000000, "30 Dũng Sĩ Thanh Khê"),
                             listing("property:y", 2600000000, "3000 Dũng Sĩ Thanh Khê")])
        reply = self.ask(s, "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê")
        self.assertEqual(reply.recommendedProperties, [])
        self.assertEqual(reply.evidence.get("responseKind"), "NO_MATCHES")

    def test_a_different_street_in_the_same_district_is_not_a_match(self):
        s, b = self.service([listing("property:x", 2500000000, "300 Nguyễn Văn Linh, Thanh Khê")])
        reply = self.ask(s, "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê")
        self.assertEqual(reply.recommendedProperties, [])

    def test_no_match_names_the_address_and_offers_nearby(self):
        s, b = self.service([])
        reply = self.ask(s, "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê")
        self.assertIn("Chưa tìm thấy tin nhà tại 300 Dũng Sĩ Thanh Khê", reply.answer)
        replies = reply.evidence.get("quickReplies") or []
        self.assertTrue(any("gần" in r for r in replies), replies)
        # Nearby is only offered, never run automatically.
        b.geocode_workplace.assert_not_called()

    def test_service_failure_is_reported_not_guessed(self):
        s, b = self.service([])
        b.search_by_address.side_effect = UpstreamError(502)
        reply = self.ask(s, "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê")
        self.assertEqual(reply.evidence.get("clarification"), "ADDRESS_SEARCH_UNAVAILABLE")
        self.assertEqual(reply.recommendedProperties, [])

    def test_an_amenity_question_keeps_its_own_path(self):
        s, b = self.service([])
        reply = self.ask(s, "Gần 300 Dũng Sĩ Thanh Khê có bệnh viện nào?")
        b.search_by_address.assert_not_called()
        self.assertIsNotNone(reply.evidence.get("amenityIntent"))

    def test_near_address_labels_the_result_as_nearby(self):
        s, b = self.service([])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "300 Dũng Sĩ Thanh Khê", "latitude": 16.06,
             "longitude": 108.22, "approximate": False}]
        b.search_nearby.return_value = {"bbox": "x", "radiusMeters": 1000, "items": []}
        first = self.ask(s, "Tìm nhà gần 300 Dũng Sĩ Thanh Khê")
        sid = first.evidence["session"]["id"]
        second = self.ask(s, "Đồng ý tìm vị trí", sid)
        pick = (second.evidence.get("quickReplies") or [None])[0]
        reply = self.ask(s, pick, sid) if pick else second
        self.assertTrue(reply.evidence.get("nearAddress"))
        notes = " ".join(reply.dataLimitations)
        self.assertIn("bán kính 1 km", notes)
        b.search_by_address.assert_not_called()


if __name__ == "__main__":
    unittest.main()
