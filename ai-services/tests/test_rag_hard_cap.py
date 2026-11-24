"""Hard cap edge cases: all over the limit, no route at all, widening, and reuse.

These pin the difference between "measured and too slow" and "could not be measured",
which is the distinction the UI wording must keep.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest


def cell(pid, seconds):
    """Cells are keyed by the bare listing id, which is what the tool sends."""
    return {"propertyId": pid,
            "status": "OK" if seconds is not None else "NO_ROUTE",
            "distanceMeters": None if seconds is None else seconds * 10.0,
            "durationSeconds": seconds}


class Base(unittest.TestCase):
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
        b.property_detail.return_value = {
            "id": "11111111-1111-1111-1111-111111111111", "title": "Căn A",
            "priceVnd": 2000000000.0, "areaSqm": 80.0, "district": "Hải Châu", "ward": "",
            "propertyType": "HOUSE", "transactionType": "SALE", "listingCode": "SP001",
            "contentVersion": 1}
        b.commute.return_value = {"distanceMeters": 900.0, "durationSeconds": 120.0,
                                  "mode": "drive", "provider": "OPENROUTESERVICE"}
        return s, b

    def confirm(self, s, question):
        first = s.chat(ChatRequest(question=question, requireGeneration=False))
        sid = first.evidence["session"]["id"]
        s.chat(ChatRequest(question="Toàn Đà Nẵng", sessionId=sid, requireGeneration=False))
        s.chat(ChatRequest(question="Nhập địa điểm khác", sessionId=sid, requireGeneration=False))
        return sid, s.chat(ChatRequest(question="123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng", sessionId=sid,
                                       requireGeneration=False))


class HardCapTests(Base):
    def three_minute(self, cells):
        s, b = self.service(cells)
        sid, reply = self.confirm(
            s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 3 phút.")
        return s, b, sid, reply

    def test_all_over_the_cap_says_over_not_unknown(self):
        _, _, _, reply = self.three_minute([cell("a", 400.0), cell("b", 500.0)])
        notes = " ".join(reply.dataLimitations)
        self.assertIn("đều vượt mốc", notes)
        self.assertIn("nhanh nhất", notes)
        self.assertNotIn("chưa tính được tuyến cho tin nào", notes)

    def test_no_route_at_all_says_unverified_not_over(self):
        _, _, _, reply = self.three_minute([cell("a", None), cell("b", None)])
        notes = " ".join(reply.dataLimitations)
        self.assertIn("chưa tính được tuyến", notes)
        self.assertNotIn("đều vượt mốc", notes)

    def test_empty_hard_cap_offers_a_way_to_widen(self):
        _, _, _, reply = self.three_minute([cell("a", 400.0), cell("b", 500.0)])
        # A hard cap that empties the list is reported as NO_MATCHES with the scope spelled
        # out, plus a way to widen the search.
        self.assertEqual(reply.evidence.get("responseKind"), "NO_MATCHES")
        notes = " ".join(reply.dataLimitations)
        self.assertIn("đều vượt mốc", notes)
        self.assertTrue(reply.evidence.get("quickReplies"))

    def test_exactly_at_the_cap_is_kept(self):
        _, _, _, reply = self.three_minute([cell("a", 180.0)])
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:a"])

    def test_one_second_over_the_cap_is_dropped(self):
        _, _, _, reply = self.three_minute([cell("a", 180.1)])
        self.assertEqual(reply.recommendedProperties, [])

    def test_the_kept_list_is_ordered_by_travel_time(self):
        _, _, _, reply = self.three_minute(
            [cell("a", 170.0), cell("b", 60.0), cell("c", 100.0)])
        self.assertEqual([p["id"] for p in reply.recommendedProperties],
                         ["property:b", "property:c", "property:a"])

    def test_note_wording_is_an_estimate_not_a_measured_trip(self):
        _, _, _, reply = self.three_minute([cell("a", 60.0), cell("b", 120.0)])
        notes = [n for n in reply.dataLimitations if "Xếp hạng" in n]
        self.assertTrue(notes)
        self.assertIn("thời gian di chuyển ước tính theo", notes[0])
        self.assertNotIn("thời gian đi thực tế", notes[0])

    def test_note_names_the_vendor_from_the_response(self):
        _, _, _, reply = self.three_minute([cell("a", 60.0)])
        notes = [n for n in reply.dataLimitations if "Xếp hạng" in n]
        self.assertIn("openrouteservice", notes[0])


class ReuseTests(Base):
    def test_changing_the_cap_does_not_geocode_again(self):
        s, b = self.service([cell("a", 60.0), cell("b", 120.0)])
        sid, _ = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 25 phút.")
        self.assertEqual(b.geocode_workplace.call_count, 1)
        s.chat(ChatRequest(question="tìm nhà đi làm tối đa 3 phút", sessionId=sid,
                           requireGeneration=False))
        self.assertEqual(b.geocode_workplace.call_count, 1,
                         "đổi mốc không được geocode lại")

    def test_switching_listing_does_not_geocode_again(self):
        s, b = self.service([cell("a", 60.0), cell("b", 120.0)])
        sid, _ = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 25 phút.")
        before = b.geocode_workplace.call_count
        s.chat(ChatRequest(question="Căn này đi làm mất bao lâu?",
                           propertyId="11111111-1111-1111-1111-111111111111",
                           sessionId=sid, requireGeneration=False))
        self.assertEqual(b.geocode_workplace.call_count, before,
                         "chuyển căn không được geocode lại")

    def test_a_new_workplace_restarts_confirmation(self):
        s, b = self.service([cell("a", 60.0), cell("b", 120.0)])
        sid, _ = self.confirm(s, "Tôi có tối đa 3 tỷ, tìm nhà đi làm tối đa 25 phút.")
        reply = s.chat(ChatRequest(question="Nhập địa điểm khác", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual(reply.evidence.get("clarification"), "COMMUTE_ADDRESS_CONSENT")


if __name__ == "__main__":
    unittest.main()
