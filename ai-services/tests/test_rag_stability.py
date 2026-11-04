"""Regression for the reproduced strict 503; all fixtures are isolated from live data."""
import json
import unittest
from unittest.mock import Mock, patch

from app.rag.config import GroundingError, RagUnavailable, Settings
from app.rag.diagnostics import request_trace, traced, reason
from app.rag.ollama_llm import OllamaQwen, normalize_ranked_output, ranked_slots
from app.rag.validator import validate_generated_answer


class StabilityTests(unittest.TestCase):
    def setUp(self):
        self.facts = {f"f{i}": {"sourceId": f"recommendation:unit:{i}", "text": f"Bằng chứng kiểm thử cô lập {i}."} for i in range(4)}

    def test_api_order_is_structural_not_model_selected(self):
        slots = ranked_slots(self.facts)
        self.assertEqual(slots, ["f0", "f1", "f2"])
        # JSON object field order is irrelevant; authoritative slots restore API order.
        raw = json.dumps({"sentences": {key: self.facts[key]["text"] for key in reversed(slots)}})
        result = validate_generated_answer(normalize_ranked_output(raw, slots), self.facts, list(self.facts))
        self.assertEqual([s["factId"] for s in result], slots)

    def test_missing_extra_or_nonobject_slots_fail_closed(self):
        for raw in ['{"sentences":{"f1":"unit"}}', '{"sentences":{"f0":"unit","extra":"unit"}}', '{"sentences":[]}', 'invalid']:
            with self.assertRaises(RagUnavailable):
                normalize_ranked_output(raw, ["f0"])

    def test_reshaping_never_corrects_invented_text(self):
        for text in ["Giá mới 999 đồng.", "已经确认", self.facts["f1"]["text"], ["wrong type"]]:
            raw = normalize_ranked_output(json.dumps({"sentences": {"f0": text}}), ["f0"])
            with self.assertRaises(GroundingError):
                validate_generated_answer(raw, self.facts, list(self.facts))

    def test_adapter_requires_each_ranked_text_and_preserves_generation_metrics(self):
        model = OllamaQwen(Settings(ollama_keep_alive_seconds=0))
        response = Mock()
        response.json.return_value = {"model": model.model_id, "done": True, "done_reason": "stop", "eval_count": 42,
            "message": {"content": json.dumps({"sentences": {k: self.facts[k]["text"] for k in ["f2", "f1", "f0"]}})}}
        client = Mock();client.__enter__ = Mock(return_value=client);client.__exit__ = Mock(return_value=False);client.post.return_value = response
        with patch.object(model, "status", return_value={"digest": "unit-digest"}), patch("app.rag.ollama_llm.httpx.Client", return_value=client):
            output = model.answer("fixture", self.facts)
        schema = client.post.call_args.kwargs["json"]["format"]["properties"]["sentences"]
        self.assertEqual(client.post.call_args.kwargs["json"]["keep_alive"], 0)
        self.assertEqual(schema["required"], ["f0", "f1", "f2"])
        self.assertFalse(schema["additionalProperties"])
        for key in schema["required"]:
            self.assertEqual(schema["properties"][key]["enum"], [self.facts[key]["text"]])
        self.assertEqual(output.metrics["eval_count"], 42)
        self.assertEqual(output.metrics["outputFormat"], "RANKED_PROPERTY_SLOTS_V1")
        self.assertEqual(len(validate_generated_answer(output.raw, self.facts, list(self.facts))), 3)

    def test_diagnostics_correlate_stages_without_exception_secrets(self):
        def failure():
            raise RagUnavailable("password=fixture-private-value") from TimeoutError("private URL")
        with self.assertLogs("uvicorn.error", level="INFO") as logs:
            with request_trace("/chat", True):
                with self.assertRaises(RagUnavailable):
                    traced("ollama_generation", failure)
        content="\n".join(logs.output)
        self.assertIn("TimeoutError", content)
        self.assertIn("requestId", content)
        self.assertNotIn("fixture-private-value", content)
        self.assertNotIn("private URL", content)
        self.assertIn("request_end", content)

    def test_retention_bounded_and_unknown_exception_codes_not_logged(self):
        self.assertEqual(Settings().ollama_keep_alive_seconds, 300)
        for invalid in [-1, 301, True, 1.5]:
            with self.assertRaises(ValueError):
                Settings(ollama_keep_alive_seconds=invalid)
        self.assertEqual(reason(RagUnavailable("UPPERCASE_PRIVATE_SECRET")), "RagUnavailable")
        self.assertEqual(reason(GroundingError("GENERATED_RANKING_DRIFT")), "GENERATED_RANKING_DRIFT")
