"""An ordinal must follow the saved order even when the new result set is partial.

The reference list is what the previous turn showed. If a different listing vanishes
or the query returns them out of order, "căn thứ hai" still means the second item of
that saved list. If the asked listing itself is gone, say so — never shift the index.
"""
import unittest

import test_rag_multiturn as fixtures
from app.rag.schemas import ChatRequest
from app.rag.tools import GroundingError, UpstreamError


def prop(key, price, score):
    return fixtures.prop(key, price, score)


def recommendation(props):
    return {"mode": "SAFE", "method": "HEURISTIC_V1_1", "topProperties": props,
            "eligibleCandidateCount": len(props), "topAreas": [], "warnings": []}


class PartialUniverseTests(unittest.TestCase):
    def service(self):
        s, b, _, _ = fixtures.MultiTurnTests().service(
            props=[prop("property:a", 2000000000, 90),
                   prop("property:b", 2100000000, 80),
                   prop("property:c", 1800000000, 70)])
        return s, b

    def first_list(self):
        s, b = self.service()
        first = s.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ.",
                                   requireGeneration=False))
        sid = first.evidence["session"]["id"]
        shown = [p["id"] for p in first.recommendedProperties]
        return s, b, sid, shown

    def test_baseline_list_is_three(self):
        _, _, _, shown = self.first_list()
        self.assertEqual(shown, ["property:a", "property:b", "property:c"])

    def test_reordered_partial_result_still_follows_the_saved_order(self):
        s, b, sid, shown = self.first_list()
        # The next query returns C then B — a different order and a missing A.
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:b", 2100000000, 80)])
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], [shown[1]])

    def test_partial_result_does_not_make_a_valid_index_invalid(self):
        s, b, sid, shown = self.first_list()
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:b", 2100000000, 80)])
        reply = s.chat(ChatRequest(question="Căn thứ ba giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        # Index 3 existed in the saved list, so it must not become "out of range".
        self.assertNotEqual(reply.evidence.get("clarification"), "PROPERTY_INDEX_OUT_OF_RANGE")

    def test_removed_target_is_reported_not_substituted(self):
        s, b, sid, shown = self.first_list()
        # B disappears from the new result set AND the detail route says it is gone.
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:a", 2000000000, 90)])
        b.property_detail.side_effect = GroundingError("PROPERTY_NOT_PUBLIC")
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        ids = [p["id"] for p in reply.recommendedProperties]
        # The refusal is the contract; the exact code is not.
        self.assertEqual(reply.evidence.get("responseKind"), "CLARIFICATION_REQUIRED")
        self.assertEqual(ids, [], "không được thay bằng căn khác")

    def test_missing_from_recommendation_but_still_public_is_served(self):
        s, b, sid, shown = self.first_list()
        # B is absent from the fresh result set, yet its detail route still serves it.
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:a", 2000000000, 90)])
        b.property_detail.return_value = prop("property:b", 2100000000, 80)
        # The SQL cross-check reads the same public rows; keep it consistent.
        s.repository.lookup.side_effect = None
        s.repository.lookup.return_value = [
            {"id": "b", "price": 2100000000, "area_sqm": 80},
            {"id": "c", "price": 1800000000, "area_sqm": 80},
            {"id": "a", "price": 2000000000, "area_sqm": 80},
        ]
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], [shown[1]])
        self.assertEqual(reply.recommendedProperties[0].get("priceVnd"), 2100000000.0)

    def test_detail_lookup_failure_keeps_the_reference_list(self):
        s, b, sid, shown = self.first_list()
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:a", 2000000000, 90)])
        b.property_detail.side_effect = UpstreamError(502)
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual(reply.evidence.get("responseKind"), "CLARIFICATION_REQUIRED")
        self.assertEqual(reply.recommendedProperties, [])
        # The saved list survives, so the same question still resolves afterwards.
        b.property_detail.side_effect = None
        b.property_detail.reset_mock(return_value=True, side_effect=True)
        b.property_detail.return_value = prop("property:b", 2100000000, 80)
        # The SQL cross-check reads the same public rows; keep it consistent.
        s.repository.lookup.side_effect = None
        s.repository.lookup.return_value = [
            {"id": "b", "price": 2100000000, "area_sqm": 80},
            {"id": "c", "price": 1800000000, "area_sqm": 80},
            {"id": "a", "price": 2000000000, "area_sqm": 80},
        ]
        again = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in again.recommendedProperties], [shown[1]])

    def test_out_of_range_keeps_the_referenced_list(self):
        s, b, sid, shown = self.first_list()
        s.chat(ChatRequest(question="Căn thứ chín giá bao nhiêu?", sessionId=sid,
                           requireGeneration=False))
        # The saved list must survive the rejected question.
        reply = s.chat(ChatRequest(question="Căn thứ hai giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], [shown[1]])

    def test_narrowed_answer_keeps_the_full_list_referable(self):
        s, b, sid, shown = self.first_list()
        s.chat(ChatRequest(question="Căn thứ hai có phù hợp không?", sessionId=sid,
                           requireGeneration=False))
        reply = s.chat(ChatRequest(question="Căn thứ nhất thì sao?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], [shown[0]])

    def test_new_criteria_use_the_new_order(self):
        s, b, sid, shown = self.first_list()
        b.recommend.return_value = recommendation(
            [prop("property:c", 1800000000, 70), prop("property:b", 2100000000, 80),
             prop("property:a", 2000000000, 90)])
        s.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Sơn Trà.", sessionId=sid,
                           requireGeneration=False))
        reply = s.chat(ChatRequest(question="Căn thứ nhất giá bao nhiêu?", sessionId=sid,
                                   requireGeneration=False))
        self.assertEqual([p["id"] for p in reply.recommendedProperties], ["property:c"])


if __name__ == "__main__":
    unittest.main()
