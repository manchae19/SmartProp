"""An ordinal must refer to the cards on screen, not to a wider re-searched set."""
import unittest

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest


def cell(pid, seconds):
    return {"propertyId": pid, "status": "OK", "distanceMeters": seconds * 10.0,
            "durationSeconds": seconds}


class VisibleOrdinalTests(unittest.TestCase):
    def service(self, cells):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop("property:a", 2000000000, 90),
                   fixtures.prop("property:b", 2100000000, 80),
                   fixtures.prop("property:c", 1800000000, 70)])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "Công ty", "latitude": 16.06, "longitude": 108.22,
             "approximate": False}]
        b.commute_matrix.return_value = {"provider": "OPENROUTESERVICE", "mode": "drive",
                                         "cells": cells}
        return s, b

    def three_minute_session(self):
        """2 cards survive a 3 minute cap out of 3 candidates."""
        s, b = self.service([cell("a", 60.0), cell("b", 120.0), cell("c", 400.0)])
        first = s.chat(ChatRequest(
            question="Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 3 phút.",
            requireGeneration=False))
        sid = first.evidence["session"]["id"]
        s.chat(ChatRequest(question="Toàn Đà Nẵng", sessionId=sid, requireGeneration=False))
        s.chat(ChatRequest(question="Nhập địa điểm khác", sessionId=sid, requireGeneration=False))
        shown = s.chat(ChatRequest(question="123 Nguyễn Văn Linh", sessionId=sid,
                                   requireGeneration=False))
        return s, sid, shown

    def test_the_filtered_list_is_what_was_shown(self):
        _, _, shown = self.three_minute_session()
        self.assertEqual([p["id"] for p in shown.recommendedProperties],
                         ["property:a", "property:b"])

    def test_second_card_resolves_to_the_second_shown(self):
        s, sid, shown = self.three_minute_session()
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties],
                         [shown.recommendedProperties[1]["id"]])
        self.assertEqual(reply.recommendedProperties[0].get("priceVnd"),
                         shown.recommendedProperties[1].get("priceVnd"))

    def test_third_card_is_out_of_range_when_only_two_were_shown(self):
        s, sid, _ = self.three_minute_session()
        reply = s.chat(ChatRequest(question="Căn thứ ba giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual(reply.evidence.get("clarification"), "PROPERTY_INDEX_OUT_OF_RANGE")
        self.assertEqual(reply.recommendedProperties, [])

    def test_out_of_range_does_not_substitute_the_dropped_listing(self):
        s, sid, _ = self.three_minute_session()
        reply = s.chat(ChatRequest(question="Căn thứ ba giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        ids = [p["id"] for p in reply.recommendedProperties]
        self.assertNotIn("property:c", ids, "tin bị loại không được thay vào vị trí thứ ba")

    def test_an_explicit_new_budget_uses_the_new_list(self):
        s, sid, _ = self.three_minute_session()
        # A fresh budget question starts a new search; the intake asks where first.
        first = s.chat(ChatRequest(question="Tôi có 3 tỷ, tìm giúp tôi vài căn",
                                   sessionId=sid, requireGeneration=False))
        self.assertEqual(first.evidence.get("clarification"), "LIFESTYLE_INTAKE")
        reply = s.chat(ChatRequest(question="Toàn Đà Nẵng", sessionId=sid,
                                   requireGeneration=False))
        # The intake may ask a second question; answer it the same way a user would.
        if reply.evidence.get("clarification") == "LIFESTYLE_INTAKE":
            reply = s.chat(ChatRequest(question="Bỏ qua, xem nhà trong ngân sách",
                                       sessionId=sid, requireGeneration=False))
        self.assertGreaterEqual(len(reply.recommendedProperties), 1)


if __name__ == "__main__":
    unittest.main()
