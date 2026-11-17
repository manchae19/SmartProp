"""Personalized suggestion list: profile priorities, chat override, and the
three-card limit that keeps the ordinals the user cites aligned with the screen.
"""
import unittest
from fastapi.testclient import TestClient
import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.tools import BackendTools
import httpx


class SuggestionLimitTests(unittest.TestCase):
    """The advisor renders three cards, so the search asks for and stores three."""

    def service(self, props):
        return fixtures.MultiTurnTests().service(props=props)

    def profile(self, **kw):
        return {"subject": "1", "enabled": True, "district": "Cẩm Lệ",
                "selectedNeeds": ["HOSPITAL"], "primaryNeed": "HOSPITAL", **kw}

    def send(self, s, q, p=None, previous=None):
        return s.chat(ChatRequest(question=q,
                                  sessionId=previous.evidence["session"]["id"] if previous else None),
                      account=p) if p else s.chat(ChatRequest(
                          question=q, sessionId=previous.evidence["session"]["id"] if previous else None))

    def test_saved_hospital_priority_is_sent_and_list_is_capped(self):
        props = [fixtures.prop(f"property:p{i}", 2000000000 - i * 1000000, 90 - i) for i in range(6)]
        s, b, _, _ = self.service(props)
        reply = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn", self.profile())
        criteria = b.recommend.call_args.args[0]
        self.assertEqual(criteria["amenityPriorities"], ["HOSPITAL"])
        self.assertEqual(criteria["limit"], 3)
        self.assertEqual(criteria["budgetVnd"], "3000000000")
        # Six candidates came back; only the three the UI can show are kept.
        self.assertEqual(len(reply.recommendedProperties), 3)

    def test_chat_override_switches_to_school_and_keeps_budget(self):
        props = [fixtures.prop(f"property:p{i}", 2000000000, 90 - i) for i in range(3)]
        s, b, _, _ = self.service(props)
        profile = self.profile()
        first = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn", profile)
        self.assertEqual(b.recommend.call_args.args[0]["amenityPriorities"], ["HOSPITAL"])
        self.send(s, "Lần này tôi ưu tiên gần trường", profile, first)
        criteria = b.recommend.call_args.args[0]
        self.assertEqual(criteria["amenityPriorities"][0], "SCHOOL")
        self.assertEqual(criteria["budgetVnd"], "3000000000")
        # The saved profile itself is never rewritten by a chat turn.
        self.assertEqual(profile["primaryNeed"], "HOSPITAL")
        self.assertEqual(profile["selectedNeeds"], ["HOSPITAL"])

    def test_ordinal_refers_to_the_stored_list(self):
        props = [fixtures.prop(f"property:p{i}", 2000000000, 90 - i) for i in range(3)]
        s, b, _, _ = self.service(props)
        first = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn")
        self.assertEqual([p["id"] for p in first.recommendedProperties],
                         ["property:p0", "property:p1", "property:p2"])
        second = first.recommendedProperties[1]
        reply = self.send(s, "Căn thứ hai giá bao nhiêu?", None, first)
        # The ordinal resolves against the stored three-item list, so the visible
        # second card is the one named — never a property the user cannot see.
        self.assertEqual([p["id"] for p in reply.recommendedProperties],
                         [second["id"]])
        self.assertIn("2000000000", reply.answer)

    def test_ordinal_out_of_range_is_reported_not_substituted(self):
        s, b, _, _ = self.service([fixtures.prop("property:only", 2000000000, 90)])
        first = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn")
        self.assertEqual(len(first.recommendedProperties), 1)
        reply = self.send(s, "Căn thứ hai giá bao nhiêu?", None, first)
        self.assertEqual(reply.evidence["responseKind"], "CLARIFICATION_REQUIRED")
        self.assertIn("thứ 2", reply.answer)
        self.assertEqual(reply.recommendedProperties, [])

    def test_empty_result_is_no_matches(self):
        s, b, _, _ = self.service([])
        reply = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn")
        self.assertEqual(reply.evidence["responseKind"], "NO_MATCHES")
        self.assertEqual(reply.recommendedProperties, [])

    def test_guest_without_priority_still_searches(self):
        s, b, _, _ = self.service([fixtures.prop("property:a", 2000000000, 90)])
        reply = self.send(s, "Tôi có 3 tỷ, tìm giúp tôi vài căn")
        criteria = b.recommend.call_args.args[0]
        self.assertNotIn("amenityPriorities", criteria)
        self.assertEqual(criteria["limit"], 3)
        self.assertEqual(len(reply.recommendedProperties), 1)


if __name__ == "__main__":
    unittest.main()
