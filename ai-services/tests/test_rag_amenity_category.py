"""Amenity category relevance: intent -> hard filter -> retrieval -> generation -> citations.

Regression for the defect where "Cẩm Lệ có trường học nào?" cited HOSPITAL evidence.
Fixtures are isolated; live acceptance is recorded separately in the report.
"""
import unittest
from unittest.mock import Mock

from app.rag.intent import poi_categories
from app.rag.knowledge import document
from app.rag.orchestrator import ChatOrchestrator
from app.rag.schemas import ChatRequest
from app.rag.validator import validate_generated_relevance
from app.rag.config import GroundingError


SCHOOL = {"areaId": "district-cam-le", "district": "Cẩm Lệ", "name": "Trường Tiểu học Ông Ích Đường",
          "category": "SCHOOL", "attributionBasis": "DISTRICT_FACILITY"}
HOSPITAL = {"areaId": "district-cam-le", "district": "Cẩm Lệ", "name": "Trung tâm Y tế Quận Cẩm Lệ",
            "category": "HOSPITAL", "attributionBasis": "DISTRICT_FACILITY"}


def poi(meta, text=None):
    return document("poi-evidence:" + meta["name"][:12].replace(" ", "-"),
                    text or "Bằng chứng tiện ích %s, loại %s, trong hồ sơ Cẩm Lệ." % (meta["name"], meta["category"]),
                    "http://127.0.0.1:8080/api/v1/amenities/district-cam-le", "UNIT", "POI_EVIDENCE", meta)


class AmenityCategoryTests(unittest.TestCase):
    def service(self, documents, retrieved=None, answer=None):
        backend, repository, knowledge, retriever, model = [Mock() for _ in range(5)]
        knowledge.load.return_value = {"summary": {"catalogVersion": "UNIT"}, "contentHash": "unit", "documents": documents}
        backend.amenity_summary.return_value = {"catalogVersion": "UNIT"}
        backend.settings.backend_url = "http://127.0.0.1:8080"
        backend.recommend.return_value = {"mode": "SAFE", "method": "HEURISTIC_V1_1", "topProperties": [],
                                          "eligibleCandidateCount": 0, "topAreas": [], "warnings": []}
        backend.amenity_map.return_value = {"version": "POI_MAP_V1", "visibility": "PUBLIC", "district": "Cẩm Lệ",
            "category": "SCHOOL", "items": [{"id": "map-school-1", "name": "Trường Tiểu học Ông Ích Đường",
            "category": "SCHOOL", "district": "Cẩm Lệ", "latitude": 15.9994179, "longitude": 108.1830286,
            "reviewStatus": "VALID", "sourceName": "openstreetmap_overpass",
            "sourceUrl": "https://www.openstreetmap.org/way/1326043721", "observedAt": "2026-11-02"}]}
        retriever.search.return_value = retrieved if retrieved is not None else documents
        model.output_kind = "grounded_answer"
        model.answer.return_value = Mock(raw=answer, metrics={"eval_count": 10})
        return ChatOrchestrator(backend, repository, knowledge, retriever, model), backend, retriever, model

    def test_explicit_categories_are_extracted_deterministically(self):
        self.assertEqual(poi_categories("Cẩm Lệ có trường học nào?"), ("SCHOOL",))
        self.assertEqual(poi_categories("Hải Châu có bệnh viện nào?"), ("HOSPITAL",))
        self.assertEqual(poi_categories("Ngũ Hành Sơn có bãi biển nào?"), ("BEACH",))
        self.assertEqual(poi_categories("Sơn Trà có những tiện ích gì?"), ())
        self.assertEqual(poi_categories("Tôi có 10 tỷ, gợi ý BĐS phù hợp."), ())
        # Market phrases and non-POI words must not create a category.
        self.assertEqual(poi_categories("Tôi có 2 tỷ, muốn mua nhà để cho thuê."), ())
        self.assertEqual(poi_categories("Trường hợp này có nhà không?"), ())

    def test_retriever_receives_category_hard_filter(self):
        docs = [poi(SCHOOL), poi(HOSPITAL)]
        service, backend, retriever, model = self.service(docs, retrieved=docs)
        service.chat(ChatRequest(question="Cẩm Lệ có trường học nào?"))
        self.assertEqual(retriever.search.call_args.kwargs["categories"], ("SCHOOL",))
        self.assertEqual(retriever.search.call_args.kwargs["district"], "Cẩm Lệ")

    def test_hospital_evidence_cannot_answer_a_school_question(self):
        hospital = poi(HOSPITAL)
        # FAISS wrongly returns only HOSPITAL evidence: it must be discarded, not cited.
        service, backend, retriever, model = self.service([hospital], retrieved=[hospital])
        result = service.chat(ChatRequest(question="Cẩm Lệ có trường học nào?"))
        self.assertEqual(result.mode, "SAFE")
        cited = {c.sourceId for c in result.citations}
        self.assertNotIn(hospital["sourceId"], cited)
        self.assertNotIn("HOSPITAL", result.answer)
        self.assertNotIn("Trung tâm Y tế", result.answer)
        for c in result.citations:
            self.assertEqual(c.kind, "POI_EVIDENCE")
        self.assertTrue(result.answer.strip())

    def test_map_api_evidence_is_used_when_faiss_lacks_category(self):
        hospital = poi(HOSPITAL)
        service, backend, retriever, model = self.service([hospital], retrieved=[hospital])
        result = service.chat(ChatRequest(question="Cẩm Lệ có trường học nào?"))
        backend.amenity_map.assert_called_with("Cẩm Lệ", "SCHOOL")
        self.assertTrue(result.citations)
        for c in result.citations:
            self.assertTrue(c.sourceId.startswith("poi-map:"))
            self.assertEqual(c.kind, "POI_EVIDENCE")
        self.assertNotIn("HOSPITAL", result.answer)

    def test_generation_citing_wrong_category_is_rejected(self):
        school, hospital = poi(SCHOOL), poi(HOSPITAL)
        facts = {"f0": {"text": hospital["text"], "sourceId": hospital["sourceId"],
                        "category": "HOSPITAL", "district": "Cẩm Lệ"}}
        sentences = [{"factId": "f0", "text": hospital["text"], "sourceId": hospital["sourceId"]}]
        with self.assertRaises(GroundingError):
            validate_generated_relevance(sentences, facts, ("SCHOOL",), "Cẩm Lệ")
        facts["f0"].update({"category": "SCHOOL"})
        self.assertEqual(validate_generated_relevance(sentences, facts, ("SCHOOL",), "Cẩm Lệ"), sentences)

    def test_validator_rejects_wrong_district(self):
        facts = {"f0": {"category": "SCHOOL", "district": "Hải Châu"}}
        with self.assertRaises(GroundingError):
            validate_generated_relevance([{"factId": "f0"}], facts, ("SCHOOL",), "Cẩm Lệ")

    def test_no_category_question_keeps_mixed_evidence(self):
        docs = [poi(SCHOOL), poi(HOSPITAL)]
        service, backend, retriever, model = self.service(docs, retrieved=docs)
        service.chat(ChatRequest(question="Sơn Trà có những tiện ích gì?"))
        self.assertIsNone(retriever.search.call_args.kwargs["categories"])
        backend.amenity_map.assert_not_called()

    def test_insufficient_evidence_never_substitutes_other_category(self):
        service, backend, retriever, model = self.service([poi(HOSPITAL)], retrieved=[poi(HOSPITAL)])
        backend.amenity_map.return_value = {"items": []}
        result = service.chat(ChatRequest(question="Cẩm Lệ có trường học nào?"))
        self.assertEqual(result.generationMode, "EVIDENCE_ONLY")
        self.assertEqual(result.citations, [])
        self.assertEqual(result.evidence["responseKind"], "INSUFFICIENT_AMENITY_EVIDENCE")
        self.assertNotIn("HOSPITAL", result.answer)
        self.assertIn("trường học", result.answer)
        model.answer.assert_not_called()


if __name__ == "__main__":
    unittest.main()
