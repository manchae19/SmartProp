import unittest

import test_rag_multiturn as fixtures
from app.rag.money import format_vnd
from app.rag.personalization import area_spec, apply_area, matches_area
from app.rag.schemas import ChatRequest


class AreaSemanticsTests(unittest.TestCase):
    def test_strict_minimum_excludes_equal_area(self):
        self.assertEqual(area_spec("Tìm nhà trên 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": True, "maxAreaExclusive": False,
        })

    def test_inclusive_minimum_from(self):
        self.assertEqual(area_spec("Tìm nhà từ 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_strict_maximum_below(self):
        self.assertEqual(area_spec("Tìm nhà dưới 80m²"), {
            "minAreaSqm": None, "maxAreaSqm": "80",
            "minAreaExclusive": False, "maxAreaExclusive": True,
        })

    def test_inclusive_maximum_at_most(self):
        self.assertEqual(area_spec("Tìm nhà tối đa 80m²"), {
            "minAreaSqm": None, "maxAreaSqm": "80",
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_no_operator_keeps_legacy_inclusive_minimum(self):
        self.assertEqual(area_spec("Tìm nhà 80m² tại Cẩm Lệ"), {
            "minAreaSqm": "80", "maxAreaSqm": None,
            "minAreaExclusive": False, "maxAreaExclusive": False,
        })

    def test_apply_replaces_old_area_constraint(self):
        criteria = {"minAreaSqm": "50", "minAreaExclusive": True}
        self.assertTrue(apply_area(criteria, "Tìm nhà dưới 80m²"))
        self.assertNotIn("minAreaSqm", criteria)
        self.assertEqual(criteria["maxAreaSqm"], "80")
        self.assertTrue(criteria["maxAreaExclusive"])

    def test_range_and_non_area_values(self):
        spec = area_spec("Nhà từ 70 đến 90 m², hẻm 5m")
        self.assertTrue(matches_area("70", spec))
        self.assertTrue(matches_area("90", spec))
        self.assertFalse(matches_area("90.01", spec))
        self.assertFalse(matches_area(None, spec))
        for text in ("Hẻm 5m", "80", "Nhà -80 m²", "90 đến 70 m²"):
            with self.subTest(text=text):
                self.assertIsNone(area_spec(text))

    def test_structured_area_range_is_validated(self):
        for fields in ({"minAreaSqm": 90, "maxAreaSqm": 80},
                       {"minAreaSqm": 80, "maxAreaSqm": 80, "maxAreaExclusive": True},
                       {"maxAreaExclusive": True}):
            with self.subTest(fields=fields), self.assertRaises(ValueError):
                ChatRequest(question="Tìm nhà", **fields)

    def test_personalized_search_updates_and_carries_area_with_district_and_ward(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        account = {"subject": "1", "enabled": True, "district": "Cẩm Lệ", "selectedNeeds": []}
        first = bot.chat(ChatRequest(question="Tìm nhà trên 80 m² dưới 3 tỷ tại Cẩm Lệ",
                                     district="Cẩm Lệ", ward="Hòa Thọ Đông"), account=account)
        sent = backend.recommend.call_args.args[0]
        self.assertEqual(sent["minAreaSqm"], "80")
        self.assertTrue(sent["minAreaExclusive"])
        self.assertEqual(sent["district"], "Cẩm Lệ")
        self.assertEqual(sent["ward"], "Hòa Thọ Đông")

        session = first.evidence["session"]["id"]
        bot.chat(ChatRequest(question="Diện tích dưới 70 m²", sessionId=session), account=account)
        sent = backend.recommend.call_args.args[0]
        self.assertNotIn("minAreaSqm", sent)
        self.assertEqual(sent["maxAreaSqm"], "70")
        self.assertTrue(sent["maxAreaExclusive"])
        self.assertEqual(sent["ward"], "Hòa Thọ Đông")

        response = bot.chat(ChatRequest(question="Tìm kỹ hơn", sessionId=session), account=account)
        self.assertEqual(response.evidence["session"]["context"]["criteria"]["maxAreaSqm"], "70")

    def test_address_search_keeps_ward_and_excludes_equal_area(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        address = "300 Dũng Sĩ Thanh Khê"
        base = {"priceVnd": 2000000000, "areaSqm": 79, "address": address, "title": "Nhà thử",
                "propertyType": "HOUSE", "district": "Thanh Khê", "ward": "Thanh Khê Tây"}
        backend.search_by_address.return_value = {"total": 3, "items": [
            dict(base, id="property:match"), dict(base, id="property:equal", areaSqm=80),
            dict(base, id="property:wrong-ward", ward="Thanh Khê Đông"),
        ]}
        reply = bot.chat(ChatRequest(question="Tìm nhà ở 300 Dũng Sĩ Thanh Khê dưới 80 m²",
                                     district="Thanh Khê", ward="Thanh Khê Tây"))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:match"])
        self.assertEqual(len(reply.citations), 1)
        self.assertIn("1 tin", reply.answer)

        empty = bot.chat(ChatRequest(question="Tìm nhà ở 300 Dũng Sĩ Thanh Khê dưới 70 m²",
                                     district="Thanh Khê", ward="Thanh Khê Tây",
                                     sessionId=reply.evidence["session"]["id"]))
        self.assertEqual(empty.evidence["responseKind"], "ADDRESS_NO_RESULTS")
        self.assertEqual(empty.evidence["session"]["context"]["lastPropertyIds"], [])
        self.assertTrue(empty.evidence["session"]["context"]["lastSearchEmpty"])

    def test_invalid_area_does_not_search_with_previous_bounds(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        first = bot.chat(ChatRequest(question="Tìm nhà dưới 90 m² dưới 3 tỷ tại Cẩm Lệ"))
        self.assertEqual(backend.recommend.call_count, 1)
        reply = bot.chat(ChatRequest(question="Diện tích từ 100 đến 80 m²", sessionId=first.evidence["session"]["id"]))
        self.assertEqual(reply.evidence["clarification"], "AREA_RANGE_INVALID")
        self.assertEqual(backend.recommend.call_count, 1)
        self.assertEqual(reply.evidence["session"]["context"]["criteria"]["maxAreaSqm"], "90")

    def test_vnd_budget_is_grouped_without_rounding(self):
        self.assertEqual(format_vnd("50000000000"), "50.000.000.000 đồng")
        self.assertEqual(format_vnd("5500000000"), "5.500.000.000 đồng")
        self.assertEqual(format_vnd("5500000000.50"), "5.500.000.000,5 đồng")


if __name__ == "__main__":
    unittest.main()
