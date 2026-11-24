"""Isolated security/grounding fixtures. Live-data tests are recorded separately, never mocked."""
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from fastapi.testclient import TestClient
from app.rag.api import create_chat_app
from app.rag.config import GroundingError, RagUnavailable, Settings
from app.rag.embedding import E5Embedding
from app.rag.knowledge import KnowledgeStore, build_corpus, digest, document
from app.rag.llm import QwenLLM
from app.rag.orchestrator import ChatOrchestrator, budget_from_question
from app.rag.schemas import ChatRequest
from app.rag.tools import BackendTools, PublishedPropertyRepository, UpstreamError
from app.rag.validator import validate_plan


class RagSecurityTest(unittest.TestCase):
    def test_invalid_qwen_prose_never_reaches_answer(self):
        backend, knowledge, retrieval, llm = Mock(), Mock(), Mock(), Mock()
        knowledge.load.return_value = {"summary": {"catalogVersion": "UNIT_FIXTURE"}, "contentHash": "unit", "documents": []}
        backend.amenity_summary.return_value = {"catalogVersion": "UNIT_FIXTURE"}
        backend.recommend.return_value = {"method": "HEURISTIC_V1_1", "topProperties": [], "topAreas": [], "warnings": []}
        retrieval.search.return_value = []
        llm.plan.return_value = '{"factIds":[],"answer":"đã xác minh, được công nhận công khai, 预算"}'
        result = ChatOrchestrator(backend, Mock(), knowledge, retrieval, llm).chat(ChatRequest(question="kiểm thử tiện ích", budgetVnd=10))
        llm.plan.assert_called_once()
        self.assertEqual(result.generationMode, "EVIDENCE_ONLY")
        self.assertNotIn("预算", result.answer)
        self.assertNotIn("được công nhận công khai", result.answer)

    def test_sql_api_mismatch_blocks_before_llm(self):
        backend, knowledge, repository, llm = Mock(), Mock(), Mock(), Mock()
        knowledge.load.return_value = {"summary": {"catalogVersion": "UNIT_FIXTURE"}, "documents": []}
        backend.amenity_summary.return_value = {"catalogVersion": "UNIT_FIXTURE"}
        backend.recommend.return_value = {"topProperties": [{"id": "property:unit", "priceVnd": 1, "areaSqm": 1, "source": {"kind": "PROPERTY", "recordKey": "unit"}}]}
        repository.lookup.return_value = [{"id": "unit", "price": 2, "area_sqm": 1}]
        with self.assertRaises(GroundingError):
            ChatOrchestrator(backend, repository, knowledge, Mock(), llm).chat(ChatRequest(question="kiểm thử", budgetVnd=10))
        llm.plan.assert_not_called()

    def test_no_download_without_explicit_local_paths(self):
        for operation in [lambda: QwenLLM().plan("kiểm thử", {}), lambda: E5Embedding().encode(["kiểm thử"])]:
            with self.assertRaises(RagUnavailable):
                operation()

    def test_backend_target_cannot_be_client_or_remote_controlled(self):
        # Anything that is not a plain loopback HTTP origin stays rejected. The port is
        # free so a test build can run beside the one already serving 8080.
        for value in ["http://example.com:8080", "http://localhost:8080",
                      "http://127.0.0.1:8080/evil", "http://a:b@127.0.0.1:8080",
                      "https://127.0.0.1:8080", "http://127.0.0.1:8080?x=1",
                      "http://127.0.0.1", "http://10.0.0.5:8080"]:
            with self.assertRaises(ValueError):
                Settings(backend_url=value)

    def test_backend_port_is_configurable_but_stays_loopback(self):
        # The loopback port range is 1024-65535 by design: the running service uses 8080
        # and a test build can sit beside it. Anything outside that range, and every
        # non-loopback or credentialed URL, stays rejected.
        self.assertEqual(Settings(backend_url="http://127.0.0.1:18080").backend_url,
                         "http://127.0.0.1:18080")
        self.assertEqual(Settings().backend_url, "http://127.0.0.1:8080")
        for other in ("http://127.0.0.1:80", "http://127.0.0.1:1023",
                      "http://127.0.0.1:65536",
                      "http://example.com:8080", "http://localhost:8080",
                      "https://127.0.0.1:8080", "http://127.0.0.1:8080/x",
                      "http://a:b@127.0.0.1:8080", "http://127.0.0.1:8080?x=1"):
            with self.assertRaises(ValueError):
                Settings(backend_url=other)

    def test_sql_injection_is_rejected_before_connect(self):
        repository = PublishedPropertyRepository(Settings(sql_enabled=True, db_user="test", db_password="test"))
        with self.assertRaises(GroundingError):
            repository.lookup(["x' OR 1=1 --"])

    def test_sql_no_arbitrary_execute_method(self):
        repository = PublishedPropertyRepository(Settings())
        self.assertFalse(hasattr(repository, "execute"))
        with self.assertRaises(RagUnavailable):
            repository.lookup(["fixture-id"])

    def test_budget_is_not_guessed_from_compounds_or_masks(self):
        self.assertEqual(budget_from_question("Tôi có 2,5 tỷ"), 2500000000)
        # A compound amount is a real budget, not a guess: the parser reads both parts.
        self.assertEqual(budget_from_question("2 tỷ 350 triệu"), 2350000000)
        # Ambiguous or malformed input still yields nothing rather than a guess.
        for question in ["1 tỷ1", "5xx triệu", "2 tỷ hoặc 3 tỷ", "không nêu ngân sách"]:
            self.assertIsNone(budget_from_question(question), question)

    def test_qwen_only_selects_existing_fact_ids(self):
        self.assertEqual(validate_plan('{"factIds":["f0"]}', {"f0"}), ["f0"])
        for raw in ['{"factIds":["fake-property"]}', '{"factIds":["f0","f0"]}',
                    '{"factIds":["f0"],"answer":"được công nhận công khai"}',
                    '{"factIds":[],"price":1800000000}', '{"factIds":["预算"]}', 'Giá 1 tỷ', '```json\n{}\n```']:
            with self.assertRaises(GroundingError):
                validate_plan(raw, {"f0"})

    def test_client_cannot_supply_mode_sources_sql_or_demo_key(self):
        for field in ["mode", "sql", "source", "demoKey", "documents"]:
            with self.assertRaises(ValueError):
                ChatRequest(question="kiểm thử", **{field: "forbidden"})

    def test_public_does_not_forward_authorization(self):
        tools = BackendTools(Settings())
        tools._call = Mock(return_value={"method": "HEURISTIC_V1_1", "mode": "SAFE", "topProperties": []})
        tools.recommend({"budgetVnd": "1000000"}, token="Bearer untrusted")
        self.assertIsNone(tools._call.call_args.args[3])
        tools.close()

    def test_public_rejects_leak_in_areas_even_without_properties(self):
        tools = BackendTools(Settings())
        tools._call = Mock(return_value={"method": "HEURISTIC_V1_1", "mode": "SAFE", "topProperties": [], "topAreas": [{"sources": ["TINIX_AI"]}]})
        with self.assertRaises(GroundingError):
            tools.recommend({"budgetVnd": "1000000"})
        tools.close()

    def test_research_auth_checks_second_factor_even_without_budget(self):
        tools = BackendTools(Settings(research_enabled=True, demo_key="fixture-not-a-real-key"))
        tools._call = Mock(side_effect=[{"enabled": True}, UpstreamError(403)])
        with self.assertRaises(UpstreamError):
            tools.authorize_research("Bearer fixture")
        self.assertIn("/amenities/research/areas", tools._call.call_args.args[1])
        tools.close()

    def test_research_auth_precedes_corpus(self):
        backend, knowledge = Mock(), Mock()
        backend.authorize_research.side_effect = UpstreamError(401)
        service = ChatOrchestrator(backend, Mock(), knowledge, Mock(), Mock())
        with self.assertRaises(UpstreamError):
            service.chat(ChatRequest(question="kiểm thử"), research=True, token="Bearer bad")
        knowledge.load.assert_not_called()

    def test_public_corpus_cannot_mix_research_documents(self):
        from datetime import datetime, timezone
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "corpus.json"
            doc = document("unit-fixture", "Isolated fixture", "http://127.0.0.1:8080/api/v1/amenities/fixture", "test", "AREA_AMENITY", {}, "INTERNAL_RESEARCH")
            corpus = {"format": "SMARTPROP_RAG_PUBLIC_V1", "builtAt": datetime.now(timezone.utc).isoformat(), "documents": [doc], "summary": {}}
            corpus["contentHash"] = digest(corpus)
            path.write_text(json.dumps(corpus), encoding="utf-8")
            with self.assertRaises(GroundingError):
                KnowledgeStore(path).load()

    def test_corpus_collapses_exact_duplicate_api_evidence_without_changing_source(self):
        tools = Mock()
        tools.settings.backend_url = "http://127.0.0.1:8080"
        tools.amenity_summary.return_value = {"totalAreasAnalyzed": 1, "catalogVersion": "UNIT_FIXTURE"}
        tools.amenity_areas.return_value = [{"areaId": "unit-area"}]
        poi = {"name": "Isolated test fixture", "category": "SCHOOL", "attributionBasis": "TEST_ONLY"}
        profile = {"areaId": "unit-area", "areaName": "UNIT_FIXTURE", "areaLevel": "DISTRICT", "parentDistrict": "UNIT_FIXTURE", "livingScore": 10,
                   "poiCounts": {"total": 1}, "poiEvidence": [poi, dict(poi)]}
        tools.amenity_profile.return_value = profile
        with tempfile.TemporaryDirectory() as folder:
            path = Path(folder) / "corpus.json"
            corpus = build_corpus(tools, path)
            self.assertEqual(len(KnowledgeStore(path).load()["documents"]), 2)
            self.assertEqual(corpus["duplicateEvidenceCollapsed"], 1)
            self.assertEqual(len(profile["poiEvidence"]), 2)

    def test_research_endpoint_disabled_by_default(self):
        service = Mock()
        with TestClient(create_chat_app(Settings(), service), client=("127.0.0.1", 12345)) as client:
            result = client.post("/chat/research", json={"question": "kiểm thử"})
            self.assertEqual(result.status_code, 403)
        service.chat.assert_not_called()

    def test_research_endpoint_loopback_and_session_required(self):
        settings = Settings(research_enabled=True, demo_key="fixture-not-a-real-key")
        for host, expected in [("127.0.0.1", 401), ("198.51.100.1", 403)]:
            service = Mock()
            with TestClient(create_chat_app(settings, service), client=(host, 12345)) as client:
                result = client.post("/chat/research", json={"question": "kiểm thử"})
                self.assertEqual(result.status_code, expected)
                self.assertEqual(result.headers["Cache-Control"], "no-store")
            service.chat.assert_not_called()

    def test_strict_generation_returns_503_instead_of_faking_qwen(self):
        service = Mock()
        service.chat.side_effect = RagUnavailable("FULL_RAG_RUNTIME_UNAVAILABLE")
        with TestClient(create_chat_app(Settings(), service)) as client:
            result = client.post("/chat", json={"question": "kiểm thử", "requireGeneration": True})
            self.assertEqual(result.status_code, 503)
            self.assertNotIn("FULL_RAG", result.text)


if __name__ == "__main__":
    unittest.main()
