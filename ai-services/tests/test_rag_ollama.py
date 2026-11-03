"""Grounded-answer and versioned-index safety; fixtures never enter live services."""
import json
import os
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

from app.rag.config import GroundingError, RagUnavailable, Settings
from app.rag.embedding import E5Embedding
from app.rag.gis import gis_evidence
from app.rag.index_store import IndexStore
from app.rag.knowledge import KnowledgeStore
from app.rag.ollama_llm import OllamaQwen
from app.rag.validator import validate_generated_answer


class OllamaSafetyTests(unittest.TestCase):
    def setUp(self):
        self.facts = {"f0": {"text": "Giá rao 10 đồng, diện tích 1 m² (fixture kiểm thử cô lập).", "sourceId": "unit:0"},
                      "f1": {"text": "Bằng chứng tiện ích kiểm thử cô lập.", "sourceId": "unit:1"}}

    def test_actual_text_is_required_not_only_fact_ids(self):
        with self.assertRaises(GroundingError):
            validate_generated_answer('{"factIds":["f0"]}', self.facts, ["f0"])
        raw = json.dumps({"sentences": [{"factId": "f0", "text": self.facts["f0"]["text"]}]})
        self.assertEqual(validate_generated_answer(raw, self.facts, ["f0"])[0]["text"], self.facts["f0"]["text"])

    def test_new_numbers_approval_chinese_and_mismatched_citation_blocked(self):
        for text in [self.facts["f0"]["text"].replace("10", "11"), "Đã xác minh và công nhận công khai.", "预算", self.facts["f1"]["text"]]:
            raw = json.dumps({"sentences": [{"factId": "f0", "text": text}]}, ensure_ascii=False)
            with self.assertRaises(GroundingError):
                validate_generated_answer(raw, self.facts, ["f0"])

    def test_cannot_skip_top_recommendation_or_duplicate_claim(self):
        for items in [[{"factId": "f1", "text": self.facts["f1"]["text"]}],
                      [{"factId": "f0", "text": self.facts["f0"]["text"]}] * 2]:
            with self.assertRaises(GroundingError):
                validate_generated_answer(json.dumps({"sentences": items}), self.facts, ["f0"])

    def test_remote_or_credentialed_ollama_target_rejected(self):
        for url in ["https://example.com", "http://localhost:11434", "http://127.0.0.1:11434/?x=1", "http://u:p@127.0.0.1:11434"]:
            with self.assertRaises(ValueError):
                Settings(ollama_url=url)

    def test_ollama_timeout_becomes_unavailable(self):
        with patch("app.rag.ollama_llm.httpx.Client", side_effect=TimeoutError):
            with self.assertRaises(RagUnavailable):
                OllamaQwen(Settings()).answer("câu hỏi", self.facts)

    def test_gis_never_infers_research_coordinates(self):
        properties = [{"id": "tinix:unit", "source": {"kind": "TINIX_AI", "recordKey": "unit"}}]
        result = gis_evidence([{"id": "unit", "latitude": 16, "longitude": 108}], properties, [])
        self.assertEqual(result["features"], [])
        self.assertFalse(result["propertyPoiDistancesComputed"])

    def test_gis_rejects_invalid_coords_and_labels_source(self):
        prop = [{"id": "property:unit", "source": {"kind": "PROPERTY", "recordKey": "unit"}}]
        self.assertFalse(gis_evidence([{"id": "unit", "latitude": 0, "longitude": 0}], prop, [])["features"])
        valid = gis_evidence([{"id": "unit", "coordinate_srid": 4326, "latitude": 16, "longitude": 108}], prop, [])["features"][0]
        self.assertEqual(valid["properties"]["verification"], "SOURCE_COORDINATES_NOT_SURVEY_VERIFIED")


@unittest.skipUnless(os.getenv("RAG_TEST_ARTIFACTS"), "Requires explicit real corpus/index artifacts")
class RealIndexSafetyTests(unittest.TestCase):
    def setUp(self):
        self.root = Path(os.environ["RAG_TEST_ARTIFACTS"])
        self.docs = KnowledgeStore(self.root / "public-corpus.json").load()["documents"]

    def test_real_versioned_index_roundtrip(self):
        vectors, manifest = IndexStore(self.root / "faiss", E5Embedding()).load(self.docs)
        self.assertEqual(vectors.shape, (326, 384))
        self.assertEqual(len({d["sourceId"] for d in manifest["documents"]}), 326)

    def test_corrupt_copy_rejected_without_touching_real_index(self):
        with tempfile.TemporaryDirectory() as tmp:
            for file in (self.root / "faiss").iterdir():
                shutil.copy2(file, Path(tmp) / file.name)
            file = next(Path(tmp).glob("*.faiss"))
            raw = bytearray(file.read_bytes());raw[-1] ^= 1;file.write_bytes(raw)
            with self.assertRaises(RagUnavailable):
                IndexStore(tmp, E5Embedding()).load(self.docs)

    def test_revision_or_acl_change_cannot_reuse_index(self):
        with self.assertRaises(RagUnavailable):
            IndexStore(self.root / "faiss", E5Embedding(revision="different")).load(self.docs)
        changed = [{**self.docs[0], "scope": "INTERNAL_RESEARCH"}] + self.docs[1:]
        with self.assertRaises(GroundingError):
            IndexStore(self.root / "faiss", E5Embedding()).load(changed)
