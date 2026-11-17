"""Ranking a search result by the trip to work, not just a focused listing.

The limit has to survive the turns that confirm the workplace, and it must not leak
into a later plain budget search.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest


class SearchRankingTests(unittest.TestCase):
    def service(self):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[fixtures.prop("property:a", 2000000000, 90),
                   fixtures.prop("property:b", 2100000000, 80),
                   fixtures.prop("property:c", 1800000000, 70)])
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "Công ty", "latitude": 16.06, "longitude": 108.22,
             "approximate": False}]
        b.commute_matrix.return_value = {
            "provider": "OPENROUTESERVICE", "mode": "drive",
            "cells": [
                {"propertyId": "a", "status": "OK", "distanceMeters": 1000.0, "durationSeconds": 600.0},
                {"propertyId": "b", "status": "OK", "distanceMeters": 2000.0, "durationSeconds": 300.0},
                {"propertyId": "c", "status": "OK", "distanceMeters": 3000.0, "durationSeconds": 2400.0},
            ]}
        return s, b

    def ask(self, s, question, sid=None):
        return s.chat(ChatRequest(question=question,
                                  sessionId=sid if sid else None,
                                  requireGeneration=False))

    def to_search(self, s, question):
        """Walk through intake and destination confirmation, return the final reply."""
        first = self.ask(s, question)
        sid = first.evidence["session"]["id"]
        second = self.ask(s, "Toàn Đà Nẵng", sid)
        if second.evidence.get("clarification") == "COMMUTE_DESTINATION_REQUIRED":
            third = self.ask(s, "Nhập địa điểm khác", sid)
            return sid, self.ask(s, "123 Nguyễn Văn Linh", sid)
        return sid, second

    def test_search_asks_for_the_workplace_before_ranking(self):
        s, b = self.service()
        reply = self.ask(s, "Tôi có tối đa 3 tỷ, hãy tìm nhà đi ô tô đến chỗ làm trong tối đa 25 phút.")
        sid = reply.evidence["session"]["id"]
        after_intake = self.ask(s, "Toàn Đà Nẵng", sid)
        self.assertEqual(after_intake.evidence.get("clarification"), "COMMUTE_DESTINATION_REQUIRED")
        b.commute_matrix.assert_not_called()

    def test_limit_survives_the_intake_and_the_address_turn(self):
        s, b = self.service()
        sid, final = self.to_search(
            s, "Tôi có tối đa 3 tỷ, hãy tìm nhà đi ô tô đến chỗ làm trong tối đa 25 phút.")
        b.commute_matrix.assert_called_once()
        props = [p["id"] for p in final.recommendedProperties]
        # 2400 s exceeds the 1500 s hard cap, so listing c is dropped.
        self.assertNotIn("c", props)
        self.assertEqual(len(props), 2)

    def test_hard_limit_orders_the_survivors_by_travel_time(self):
        s, b = self.service()
        _, final = self.to_search(
            s, "Tôi có tối đa 3 tỷ, hãy tìm nhà đi ô tô đến chỗ làm trong tối đa 25 phút.")
        props = [p["id"] for p in final.recommendedProperties]
        self.assertEqual(props, ["property:b", "property:a"])  # 300 s before 600 s

    def test_note_names_the_real_vendor_and_scope(self):
        s, b = self.service()
        _, final = self.to_search(
            s, "Tôi có tối đa 3 tỷ, hãy tìm nhà đi ô tô đến chỗ làm trong tối đa 25 phút.")
        notes = [n for n in final.dataLimitations if "Xếp hạng" in n]
        self.assertTrue(notes)
        self.assertIn("openrouteservice", notes[0])
        self.assertIn("2/3", notes[0])

    def test_a_later_plain_search_is_not_ranked_again(self):
        s, b = self.service()
        sid, _ = self.to_search(
            s, "Tôi có tối đa 3 tỷ, hãy tìm nhà đi ô tô đến chỗ làm trong tối đa 25 phút.")
        self.ask(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn", sid)
        # The matrix ran once for the commute question and never for the plain one.
        self.assertEqual(b.commute_matrix.call_count, 1)

    def test_soft_limit_keeps_every_listing(self):
        s, b = self.service()
        sid = self.ask(
            s, "Tôi có 3 tỷ, tìm nhà gần chỗ làm").evidence["session"]["id"]
        self.ask(s, "Toàn Đà Nẵng", sid)
        third = self.ask(s, "Nhập địa điểm khác", sid)
        final = self.ask(s, "123 Nguyễn Văn Linh", sid if third else sid)
        props = [p["id"] for p in final.recommendedProperties]
        self.assertEqual(len(props), 3)
        self.assertEqual(props[0], "property:b")  # fastest first


if __name__ == "__main__":
    unittest.main()
