"""Multi-turn conversation context: bounded memory, criteria merge, re-query, isolation.

Isolated fixtures only. Live multi-turn acceptance is recorded in the step report.
"""
import unittest
from unittest.mock import Mock

from app.rag.config import RagUnavailable
from app.rag.followup import (budget_from_followup, ordinal_reference, detect_purpose,
                              detect_property_type)
from app.rag.knowledge import document
from app.rag.orchestrator import ChatOrchestrator
from app.rag.schemas import ChatRequest
from app.rag.session import SessionStore


def poi(name, district="Hải Châu", category="HOSPITAL"):
    return document("poi-evidence:" + name[:10], "Bằng chứng tiện ích %s, loại %s, tại %s." % (name, category, district),
                    "http://127.0.0.1:8080/api/v1/amenities/x", "UNIT", "POI_EVIDENCE",
                    {"areaId": "a", "district": district, "name": name, "category": category,
                     "attributionBasis": "TEST_ONLY"})


def area(name, district):
    return document("amenity:" + name, "Khu vực %s (DISTRICT); điểm tiện ích 80/100." % name,
                    "http://127.0.0.1:8080/api/v1/amenities/x", "UNIT", "AREA_AMENITY",
                    {"areaId": name, "district": district, "areaLevel": "DISTRICT", "areaName": name})


DISTRICTS = ["Cẩm Lệ", "Hải Châu", "Sơn Trà"]


def prop(pid, price, score):
    return {"id": pid, "priceVnd": price, "areaSqm": 80, "score": score, "district": "Cẩm Lệ", "ward": None,
            "source": {"kind": "PROPERTY", "recordKey": pid.replace("property:", ""), "name": "Unit"},
            "qualityStatus": "PLATFORM_PUBLISHED", "verificationStatus": "PLATFORM_PUBLISHED",
            "explanations": [], "warnings": [], "scoreBreakdown": {"budgetFit": 80, "areaFit": 90,
            "propertyTypeFit": 100, "amenityFit": 60}}


class MultiTurnTests(unittest.TestCase):
    def service(self, documents=None, props=None):
        backend, repository, knowledge, retriever, model = [Mock() for _ in range(5)]
        base = [area(d, d) for d in DISTRICTS] + [poi("Fixture Hospital")]
        docs = base + list(documents or [])
        knowledge.load.return_value = {"summary": {"catalogVersion": "UNIT"}, "contentHash": "unit", "documents": docs}
        backend.amenity_summary.return_value = {"catalogVersion": "UNIT"}
        backend.settings.backend_url = "http://127.0.0.1:8080"
        backend.amenity_map.return_value = {"items": []}
        # Address lookups are opt-in per test; the default is "nothing found".
        backend.search_by_address.return_value = {"address": "", "total": 0, "items": []}
        backend.recommend.return_value = {"mode": "SAFE", "method": "HEURISTIC_V1_1",
            "topProperties": props if props is not None else [prop("property:a", 2000000000, 90),
                                                             prop("property:b", 2500000000, 85)],
            "eligibleCandidateCount": 2, "topAreas": [], "warnings": []}
        # SQL cross-check must agree with the API facts, exactly like production.
        def lookup(ids):
            by_id = {p["source"]["recordKey"]: p for p in backend.recommend.return_value["topProperties"]}
            return [{"id": i, "price": by_id[i]["priceVnd"], "area_sqm": by_id[i]["areaSqm"]}
                    for i in ids if i in by_id]
        repository.lookup.side_effect = lookup
        retriever.search.return_value = docs
        model.output_kind = "grounded_answer"

        def answer(question, facts):
            first = next(iter(facts.items()))
            return Mock(raw='{"sentences":[{"factId":"%s","text":%s}]}' % (first[0], __import__("json").dumps(first[1]["text"], ensure_ascii=False)),
                        metrics={"eval_count": 5})
        model.answer.side_effect = answer
        return ChatOrchestrator(backend, repository, knowledge, retriever, model), backend, retriever, model

    # ---- parsing -------------------------------------------------------
    def test_followup_parsers_do_not_misread_amounts(self):
        self.assertEqual(budget_from_followup("Nếu tăng ngân sách lên 6 tỷ thì sao?"), 6000000000)
        self.assertIsNone(ordinal_reference("Nếu tăng ngân sách lên 6 tỷ thì sao?"))
        self.assertEqual(ordinal_reference("Căn thứ hai có phù hợp không?"), 2)
        self.assertEqual(ordinal_reference("căn 3 thế nào"), 3)
        self.assertIsNone(ordinal_reference("Ngân sách 2 tỷ"))
        self.assertEqual(detect_purpose("tôi muốn đầu tư"), "INVESTMENT")
        self.assertEqual(detect_property_type("tìm căn hộ"), "APARTMENT")
        self.assertIsNone(detect_property_type("muốn mua nhà ở Hải Châu"))
        self.assertEqual(detect_property_type("muốn mua nhà riêng ở Hải Châu"), "HOUSE")
        self.assertEqual(detect_property_type("tìm nhà phố"), "HOUSE")
        # Non-residential "nhà X" compounds must not become a property type.
        for q in ("có nhà thuốc nào", "nhà hàng gần đây", "tìm nhà kho", "nha khoa"):
            self.assertIsNone(detect_property_type(q), q)

    # ---- session store -------------------------------------------------
    def test_session_is_bounded_and_expires(self):
        clock = [1000.0]
        store = SessionStore(ttl=60, max_sessions=2, clock=lambda: clock[0])
        a, id_a, resumed = store.begin(None, scope="PUBLIC")
        self.assertFalse(resumed)
        again, id_again, resumed_again = store.begin(id_a, scope="PUBLIC")
        self.assertTrue(resumed_again)
        self.assertEqual(id_again, id_a)
        self.assertEqual(again.turns, 2)
        clock[0] += 61
        self.assertEqual(store.size(), 0)
        _, id_new, resumed_new = store.begin(id_a, scope="PUBLIC")
        self.assertFalse(resumed_new, "expired session must not resume")
        self.assertNotEqual(id_new, id_a)

    def test_session_capacity_is_capped(self):
        clock = [1000.0]
        store = SessionStore(ttl=600, max_sessions=3, clock=lambda: clock[0])
        ids = []
        for i in range(6):
            clock[0] += 1
            _, sid, _ = store.begin(None, scope="PUBLIC")
            ids.append(sid)
        self.assertLessEqual(store.size(), 3)

    def test_research_and_public_namespaces_never_cross(self):
        store = SessionStore(ttl=600, clock=lambda: 1000.0)
        _, public_id, _ = store.begin(None, scope="PUBLIC")
        # Same identifier presented under the research scope must NOT resume public state.
        research, research_id, resumed = store.begin(public_id, scope="INTERNAL_RESEARCH")
        self.assertFalse(resumed)
        self.assertNotEqual(research_id, public_id)
        found, _, resumed_public = store.begin(public_id, scope="PUBLIC")
        self.assertTrue(resumed_public)
        found.record = None
        with self.assertRaises(ValueError):
            store.begin(None, scope="CLIENT_SUPPLIED")

    # ---- criteria merge ------------------------------------------------
    def test_budget_change_requeries_and_keeps_other_criteria(self):
        service, backend, retriever, model = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, muốn mua căn hộ ở Cẩm Lệ.",
                                         purpose="INVESTMENT"))
        sid = first.evidence["session"]["id"]
        self.assertEqual(backend.recommend.call_count, 1)
        second = service.chat(ChatRequest(question="Nếu tăng ngân sách lên 6 tỷ thì sao?", sessionId=sid))
        self.assertEqual(backend.recommend.call_count, 2, "budget change must re-query the API")
        criteria = backend.recommend.call_args.args[0]
        self.assertEqual(str(criteria["budgetVnd"]), "6000000000")
        self.assertEqual(criteria["district"], "Cẩm Lệ", "district must be retained")
        self.assertEqual(criteria["purpose"], "INVESTMENT", "purchase purpose must be retained")
        self.assertEqual(criteria["propertyType"], "APARTMENT", "type must be retained")
        self.assertEqual(second.evidence["session"]["context"]["criteria"]["budgetVnd"], "6000000000")

    def test_district_change_requeries_with_new_district(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 3 tỷ, tìm nhà ở Cẩm Lệ.", ward="Hòa Thọ Đông"))
        sid = first.evidence["session"]["id"]
        service.chat(ChatRequest(question="Chuyển sang Hải Châu thì sao?", sessionId=sid))
        self.assertEqual(backend.recommend.call_count, 2)
        self.assertEqual(backend.recommend.call_args.args[0]["district"], "Hải Châu")
        self.assertNotIn("ward", backend.recommend.call_args.args[0])
        self.assertEqual(str(backend.recommend.call_args.args[0]["budgetVnd"]), "3000000000")

    def test_expanding_to_all_districts_removes_location_without_reusing_it(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tìm căn hộ ở Cẩm Lệ dưới 3 tỷ", ward="Hòa Thọ Đông"))
        sid = first.evidence["session"]["id"]
        response = service.chat(ChatRequest(question="Toàn Đà Nẵng", sessionId=sid))
        sent = backend.recommend.call_args.args[0]
        self.assertNotIn("district", sent)
        self.assertNotIn("ward", sent)
        self.assertEqual(sent["budgetVnd"], "3000000000")
        self.assertNotIn("district", response.evidence["session"]["context"]["criteria"])

    def test_new_search_does_not_replay_stored_list(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        backend.recommend.return_value = {**backend.recommend.return_value, "topProperties": [prop("property:z", 1900000000, 70)]}
        second = service.chat(ChatRequest(question="Tôi có 5 tỷ, tìm nhà ở Sơn Trà.", sessionId=sid))
        self.assertEqual(backend.recommend.call_count, 2)
        self.assertEqual([p["id"] for p in second.recommendedProperties], ["property:z"])
        self.assertEqual(second.evidence["session"]["context"]["lastPropertyIds"], ["property:z"])

    # ---- references ----------------------------------------------------
    def test_ordinal_reference_narrows_to_one_verified_property(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        second = service.chat(ChatRequest(question="Căn thứ hai có phù hợp không?", sessionId=sid))
        self.assertEqual(len(second.recommendedProperties), 1)
        self.assertEqual(second.recommendedProperties[0]["id"], "property:b")
        self.assertEqual(second.evidence["session"]["context"]["referencedPropertyId"],
                         "recommendation:property:b")
        # The full list survives for later turns.
        self.assertEqual(second.evidence["session"]["context"]["lastPropertyIds"],
                         ["property:a", "property:b"])

    def test_third_turn_can_still_reference_from_saved_list(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        service.chat(ChatRequest(question="Căn thứ hai có phù hợp không?", sessionId=sid))
        backend.recommend.reset_mock()
        third = service.chat(ChatRequest(question="Căn thứ nhất thì sao?", sessionId=sid))
        self.assertEqual(third.recommendedProperties[0]["id"], "property:a")

    def test_narrowed_property_stays_referable_as_can_nay(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        second = service.chat(ChatRequest(question="Căn thứ hai có phù hợp không?", sessionId=sid))
        self.assertEqual(second.recommendedProperties[0]["id"], "property:b")
        third = service.chat(ChatRequest(question="Vì sao căn này được xếp hạng cao?", sessionId=sid))
        self.assertEqual(third.evidence.get("responseKind"), None)
        self.assertEqual([p["id"] for p in third.recommendedProperties], ["property:b"])

    def test_out_of_range_reference_asks_instead_of_guessing(self):
        service, backend, _, model = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        answer = service.chat(ChatRequest(question="Căn thứ năm có phù hợp không?", sessionId=sid))
        self.assertEqual(answer.evidence["responseKind"], "CLARIFICATION_REQUIRED")
        self.assertFalse(answer.recommendedProperties)
        self.assertIn("không có", answer.answer.lower())

    def test_vague_reference_with_many_candidates_asks_for_clarification(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        answer = service.chat(ChatRequest(question="Căn này có phù hợp không?", sessionId=sid))
        self.assertEqual(answer.evidence["responseKind"], "CLARIFICATION_REQUIRED")
        self.assertEqual(answer.evidence["clarification"], "AMBIGUOUS_PROPERTY_REFERENCE")
        self.assertFalse(answer.recommendedProperties)

    def test_strict_mode_refuses_ambiguous_reference(self):
        service, backend, _, _ = self.service()
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        with self.assertRaises(RagUnavailable):
            service.chat(ChatRequest(question="Căn này có phù hợp không?", sessionId=sid,
                                     requireGeneration=True))

    # ---- amenities -----------------------------------------------------
    def test_amenity_followup_reuses_district_and_skips_recommendation(self):
        service, backend, _, _ = self.service([poi("Fixture Hospital", "Cẩm Lệ")])
        first = service.chat(ChatRequest(question="Tôi có 2 tỷ, tìm nhà ở Cẩm Lệ."))
        sid = first.evidence["session"]["id"]
        backend.recommend.reset_mock()
        answer = service.chat(ChatRequest(question="Có bệnh viện nào trong khu vực đó?", sessionId=sid))
        backend.recommend.assert_not_called()
        self.assertEqual(answer.evidence["amenityIntent"]["district"], "Cẩm Lệ")
        self.assertEqual(answer.evidence["amenityIntent"]["categories"], ["HOSPITAL"])

    def test_turn_cap_retires_a_long_conversation(self):
        """A conversation must not grow context without bound."""
        from app.rag.session import MAX_TURNS, SessionStore
        store = SessionStore()
        ctx, sid, _ = store.begin(None, scope="PUBLIC")
        for _ in range(MAX_TURNS - 1):
            again, same, resumed = store.begin(sid, scope="PUBLIC")
            self.assertTrue(resumed)
            self.assertEqual(same, sid)
        self.assertEqual(again.turns, MAX_TURNS)
        # The next turn retires the exhausted thread and issues a brand new id.
        fresh, new_id, resumed = store.begin(sid, scope="PUBLIC")
        self.assertFalse(resumed)
        self.assertNotEqual(new_id, sid)
        self.assertEqual(fresh.turns, 1)
        self.assertEqual(store.size(), 1)

    def test_reset_clears_context(self):
        store = SessionStore(ttl=600, clock=lambda: 1000.0)
        ctx, sid, _ = store.begin(None, scope="PUBLIC")
        self.assertTrue(store.reset(sid, scope="PUBLIC"))
        self.assertFalse(store.reset(sid, scope="PUBLIC"))
        _, sid2, resumed = store.begin(sid, scope="PUBLIC")
        self.assertFalse(resumed)
        self.assertNotEqual(sid, sid2)


if __name__ == "__main__":
    unittest.main()
