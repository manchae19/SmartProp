"""Choosing where the user works, inside a real chat turn.

The provider is mocked here; the point is the state machine and the wording, not the
network. Nothing about the profile is written by any of these turns.
"""
import unittest
from unittest.mock import Mock

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest


PID = "11111111-1111-1111-1111-111111111111"


class CommuteDestinationTests(unittest.TestCase):
    def service(self):
        s, b, _, _ = fixtures.MultiTurnTests().service(props=[fixtures.prop("property:a", 2000000000, 90)])
        b.property_detail.return_value = {
            "id": PID, "title": "Căn A", "priceVnd": 2000000000.0, "areaSqm": 80.0,
            "district": "Hải Châu", "ward": "", "propertyType": "HOUSE",
            "transactionType": "SALE", "listingCode": "SP001", "contentVersion": 1}
        b.commute.return_value = {"distanceMeters": 4200.0, "durationSeconds": 900.0,
                                  "mode": "drive", "provider": "GEOAPIFY"}
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "123 Nguyễn Văn Linh", "latitude": 16.06,
             "longitude": 108.22, "approximate": False}]
        return s, b

    def ask(self, s, question, session=None, token=None, account=None):
        request = ChatRequest(question=question,
                              sessionId=session.evidence["session"]["id"] if session else None,
                              propertyId=PID)
        return s.chat(request, token=token, **({"account": account} if account else {}))

    def test_asks_where_work_is_before_any_route(self):
        s, b = self.service()
        reply = self.ask(s, "Căn này đi làm mất bao lâu?")
        self.assertEqual(reply.evidence["clarification"], "COMMUTE_DESTINATION_REQUIRED")
        self.assertEqual(reply.evidence["quickReplies"],
                         ["Dùng nơi làm việc đã lưu", "Nhập địa điểm khác", "Bỏ qua"])
        b.commute.assert_not_called()

    def test_new_address_warns_before_sending_it_to_the_map(self):
        s, b = self.service()
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        reply = self.ask(s, "Nhập địa điểm khác", first)
        self.assertEqual(reply.evidence["clarification"], "COMMUTE_ADDRESS_CONSENT")
        self.assertIn("Geoapify", reply.answer)
        self.assertIn("chuyển tới", reply.answer)
        b.geocode_workplace.assert_not_called()

    def test_typed_address_then_single_candidate_computes_the_route(self):
        s, b = self.service()
        b.geocode_workplace.return_value = [{"id": "p1", "label": "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng",
                                             "latitude": 16.06, "longitude": 108.22, "approximate": False}]
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        second = self.ask(s, "Nhập địa điểm khác", first)
        reply = self.ask(s, "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng", second)
        self.assertEqual(reply.evidence["responseKind"], "FOCUSED_PROPERTY")
        self.assertIn("15 phút", reply.answer)
        self.assertIn("4.2 km", reply.answer)
        b.geocode_workplace.assert_called_once()

    def test_ambiguous_geocode_must_be_confirmed(self):
        s, b = self.service()
        b.geocode_workplace.return_value = [
            {"id": "p1", "label": "Nguyễn Văn Linh, Hải Châu", "latitude": 16.06, "longitude": 108.22, "approximate": False},
            {"id": "p2", "label": "Nguyễn Văn Linh, Thanh Khê", "latitude": 16.07, "longitude": 108.21, "approximate": True},
        ]
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        second = self.ask(s, "Nhập địa điểm khác", first)
        third = self.ask(s, "Nguyễn Văn Linh", second)
        self.assertEqual(third.evidence["clarification"], "COMMUTE_PICK_CANDIDATE")
        self.assertEqual(len(third.evidence["commuteCandidates"]), 2)
        b.commute.assert_not_called()
        reply = self.ask(s, "2. B", third)
        self.assertEqual(reply.evidence["responseKind"], "FOCUSED_PROPERTY")
        b.commute.assert_called_once()

    def test_saved_workplace_requires_an_account(self):
        s, b = self.service()
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        reply = self.ask(s, "Dùng nơi làm việc đã lưu", first)
        self.assertEqual(reply.evidence["clarification"], "COMMUTE_NO_SAVED_WORKPLACE")
        b.saved_workplace.assert_not_called()

    def test_saved_workplace_resolves_for_a_signed_in_user(self):
        s, b = self.service()
        b.saved_workplace.return_value = {"available": True, "reason": "OK",
                                          "points": [{"label": "Công ty", "latitude": 16.05,
                                                      "longitude": 108.20, "approximate": False}]}
        profile = {"subject": "1", "enabled": True, "selectedNeeds": ["HOSPITAL"],
                   "primaryNeed": "HOSPITAL"}
        first = self.ask(s, "Căn này đi làm mất bao lâu?", account=profile)
        reply = self.ask(s, "Dùng nơi làm việc đã lưu", first, token="Bearer unit-test", account=profile)
        # The saved workplace must resolve: the scope filter lets this reply through
        # while the session waits for a commute destination.
        self.assertEqual(reply.evidence["responseKind"], "FOCUSED_PROPERTY")
        b.saved_workplace.assert_called_once()

    def test_skip_clears_the_pending_question(self):
        s, b = self.service()
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        reply = self.ask(s, "Bỏ qua", first)
        # Skipping the commute question must not compute a route.
        b.commute.assert_not_called()
        self.assertNotEqual(reply.evidence.get("responseKind"), "FOCUSED_PROPERTY")

    def test_destination_survives_a_listing_switch(self):
        s, b = self.service()
        b.geocode_workplace.return_value = [{"id": "p1", "label": "Công ty",
                                             "latitude": 16.06, "longitude": 108.22, "approximate": False}]
        first = self.ask(s, "Căn này đi làm mất bao lâu?")
        second = self.ask(s, "Nhập địa điểm khác", first)
        third = self.ask(s, "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng", second)
        self.assertEqual(third.evidence["responseKind"], "FOCUSED_PROPERTY")
        # Asking again does not re-ask for the destination.
        again = self.ask(s, "Căn này đi làm mất bao lâu nữa?", third)
        self.assertEqual(again.evidence["responseKind"], "FOCUSED_PROPERTY")
        self.assertGreaterEqual(b.commute.call_count, 2)


if __name__ == "__main__":
    unittest.main()
