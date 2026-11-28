"""PR #43 targeted unit and contract tests: Hòa Xuân land routes, feature-off/missing-dataset
fail-closed behavior, overview cache grounding, LandAdvisor rewrite grammar, buyer_search
cross-source isolation, and PR #45 transaction invariant preservation.
"""
import json
import os
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.land import api as land_api, budget_rules, overview as land_overview, paths as land_paths, query_rules
from app.rag import buyer_search
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.land_chat import LandAdvisor, accept_rewrite, colloquial
from app.rag.schemas import ChatRequest, ChatResponse
import test_rag_multiturn as fixtures


LAND_UUID_1 = "11111111-2222-3333-4444-555555555555"
PROP_UUID_1 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"


class FakeLandEngine:
    def __init__(self):
        self.rows = {
            "DN-QH-0001": {
                "id": "DN-QH-0001",
                "displayName": "Ô quy hoạch thử nghiệm",
                "displayNumber": 1,
                "computedAreaSqm": 100.0,
                "priceDescription": "2,5 tỷ",
                "purposeGroup": "housing",
                "planningLabel": "Đất ở đô thị",
                "planningCode": "ODT",
                "planningCategory": "RESIDENTIAL_PLANNING",
                "pointOnSurface": [108.215, 16.005],
                "demoPriceVnd": 2_500_000_000,
                "demoUnitPriceVndPerSqm": 25_000_000,
                "effectivePriceClass": "DEMO",
                "addressEvidence": {"location": "Hòa Xuân, Đà Nẵng"},
                "demoPresentation": {
                    "landType": "Đất ở đô thị",
                    "ownershipDocument": "Sổ hồng — giả định demo",
                    "recovery": "Không thuộc diện thu hồi — giả định demo",
                    "dispute": "Không có tranh chấp",
                    "mortgage": "Không thế chấp",
                    "compensation": "Chưa áp dụng",
                },
                "floodDisplay": {
                    "display": "Có tuyến đường tham chiếu ngập gần khu vực",
                    "relation": "ILLUSTRATIVE_CORRIDOR",
                    "isDemoAssumption": True,
                },
                "floodEvidence": {"items": [{"id": "FL-01", "location_text": "Đường 29/3", "publication_date": "2025"}]},
                "geometry": {"type": "Polygon", "coordinates": [[[108.21, 16.0], [108.22, 16.0], [108.22, 16.01], [108.21, 16.0]]]},
                "sourceFile": "/private/internal/path.geojson",
                "reviewFlags": ["INTERNAL_REVIEW_NOTE"],
            }
        }
        self.original = [{"id": "DN-QH-0001", "planningCode": "ODT", "planningCategory": "RESIDENTIAL_PLANNING", "computedAreaSqm": 100.0}]
        self.activeids = {"DN-QH-0001"}
        self.pricedbyid = {"DN-QH-0001": self.rows["DN-QH-0001"]}
        self.byid = self.rows
        self.unified_lots = {}
        self.imported = SimpleNamespace(
            SOURCE_ROWS={},
            EXTRAS={},
            enrich=lambda r: r,
            value=lambda r: r.get("demoPriceVnd"),
        )

    def purpose(self, row):
        return "housing"

    def summary(self, row):
        return row

    def land_id(self, code):
        return LAND_UUID_1 if code == "DN-QH-0001" else None

    def code_for(self, value):
        if value in ("DN-QH-0001", LAND_UUID_1):
            return "DN-QH-0001"
        return None

    def resolve(self, code):
        return self.rows.get(code)

    def health(self):
        return {"status": "ok", "records": 1}

    def neighbors(self, code):
        row = self.rows.get(code)
        if not row:
            return None
        return {
            "type": "FeatureCollection",
            "features": [{
                "type": "Feature",
                "geometry": row["geometry"],
                "properties": {**row, "selected": True, "color": "#c7a000"},
            }],
        }

    def planning_cells(self):
        return {"type": "FeatureCollection", "features": []}

    def flood_map(self, chosen):
        return {"type": "FeatureCollection", "features": [], "chosen": chosen}

    def converse(self, question, state):
        if "khong hieu" in question.lower():
            return {"answer": "Tôi chưa hiểu yêu cầu này.", "rows": []}, state or {}
        row = self.rows["DN-QH-0001"]
        return {
            "answer": "Tìm thấy 1 ô quy hoạch tại Hòa Xuân.",
            "rows": [row],
            "start": 1,
            "total": 1,
            "filters": {"maxPrice": 3_000_000_000},
        }, {"lastDomain": "plot", "visibleIds": ["DN-QH-0001"], "seen": ["DN-QH-0001"], "selected": "DN-QH-0001"}


class Pr43LandAndRagTests(unittest.TestCase):
    def test_land_enabled_fails_closed_when_disabled_or_dataset_missing(self):
        with tempfile.TemporaryDirectory() as empty_dir:
            with patch.dict(os.environ, {"RAG_LAND_ENABLED": "false", "SMARTPROP_LAND_DATA_DIR": empty_dir}):
                self.assertFalse(land_paths.land_enabled())
            with patch.dict(os.environ, {"RAG_LAND_ENABLED": "true", "SMARTPROP_LAND_DATA_DIR": empty_dir}):
                with patch.object(land_paths, "DATA_ROOT", Path(empty_dir)):
                    self.assertFalse(land_paths.land_enabled())

    def test_chat_app_works_and_omits_land_routes_when_land_disabled(self):
        bot, _, _, _ = fixtures.MultiTurnTests().service(props=[])
        with patch("app.land.paths.land_enabled", return_value=False):
            app = create_chat_app(Settings(), orchestrator=bot)
        client = TestClient(app)
        health = client.get("/chat/health")
        self.assertEqual(health.status_code, 200)
        self.assertEqual(health.headers.get("Cache-Control"), "no-store")
        self.assertEqual(health.headers.get("X-Content-Type-Options"), "nosniff")
        self.assertRegex(health.headers.get("X-SmartProp-Chat-Revision", ""), r"^[0-9a-f]{16}$")
        self.assertEqual(client.get("/land/health").status_code, 404)
        self.assertEqual(client.get(f"/land/records/{LAND_UUID_1}").status_code, 404)

    def test_chat_origin_middleware_blocks_untrusted_browser_origin(self):
        bot = MagicMock()
        bot.chat.return_value = ChatResponse(
            answer="Chào bạn!", mode="SAFE", generationMode="EVIDENCE_ONLY",
            retrievalMode="TOOL_EVIDENCE_ONLY", citations=[], recommendedProperties=[],
            evidence={"responseKind": "OUT_OF_SCOPE"}, dataLimitations=[],
        )
        with patch("app.land.paths.land_enabled", return_value=False), \
             patch.dict(os.environ, {"RAG_ALLOWED_ORIGINS": "http://127.0.0.1:5173"}):
            client = TestClient(create_chat_app(Settings(), orchestrator=bot))
            forbidden = client.post("/chat", json={"question": "Xin chào"}, headers={"Origin": "https://evil.example"})
            self.assertEqual(forbidden.status_code, 403)
            allowed = client.post("/chat", json={"question": "Xin chào"}, headers={"Origin": "http://127.0.0.1:5173"})
            self.assertEqual(allowed.status_code, 200)
            server_to_server = client.post("/chat", json={"question": "Xin chào"})
            self.assertEqual(server_to_server.status_code, 200)

    def test_land_router_validates_ids_strips_private_keys_and_bounds_flood_ids(self):
        fake = FakeLandEngine()
        app = FastAPI()
        with patch.object(land_api, "_engine", return_value=fake):
            app.include_router(land_api.create_land_router())
            client = TestClient(app)

            ok = client.get(f"/land/records/{LAND_UUID_1}")
            self.assertEqual(ok.status_code, 200)
            body = ok.json()
            self.assertEqual(body["sourceCode"], "DN-QH-0001")
            self.assertFalse(body["documents"]["verifiedForThisParcel"])
            self.assertFalse(body["flood"]["verifiedForThisParcel"])
            self.assertNotIn("sourceFile", json.dumps(body))
            self.assertNotIn("reviewFlags", json.dumps(body))

            for bad in ("../etc/passwd", "DN-QH-0001;DROP", "unknown-id", "a" * 81):
                self.assertIn(client.get(f"/land/records/{bad}").status_code, (404, 422))

            neighbors = client.get("/land/neighbors", params={"id": "DN-QH-0001"})
            self.assertEqual(neighbors.status_code, 200)
            props = neighbors.json()["features"][0]["properties"]
            self.assertNotIn("geometry", props)
            self.assertNotIn("sourceFile", props)
            self.assertNotIn("reviewFlags", props)
            self.assertEqual(props["landId"], LAND_UUID_1)

            too_many = ",".join(f"FL-{i}" for i in range(201))
            self.assertEqual(client.get("/land/flood-map", params={"ids": too_many}).status_code, 400)

    def test_overview_service_grounds_sentences_and_rejects_tampered_disk_cache(self):
        fake = FakeLandEngine()
        with patch.object(land_api, "_engine", return_value=fake), tempfile.TemporaryDirectory() as cache_dir:
            record = land_api.record_view("DN-QH-0001")
            svc = land_overview.OverviewService(generator=lambda groups: [0] * len(groups), cache_dir=cache_dir)
            first = svc.get(record)
            self.assertFalse(first["cached"])
            self.assertIn(first["generationMode"], ("TEMPLATE", "OLLAMA_GROUNDED_CHOICES"))
            self.assertIn("giả lập", first["text"].lower())

            # Tamper with disk cache text -> read_disk must reject it and regenerate grounded text.
            svc2 = land_overview.OverviewService(generator=lambda groups: None, cache_dir=cache_dir)
            files = list(Path(cache_dir).glob("*.json"))
            self.assertEqual(len(files), 1)
            stored = json.loads(files[0].read_text(encoding="utf-8"))
            stored["result"]["text"] = "Nội dung bị chỉnh sửa trái phép với số liệu bịa đặt 999 tỷ đồng."
            stored["result"]["wordCount"] = len(stored["result"]["text"].split())
            files[0].write_text(json.dumps(stored, ensure_ascii=False), encoding="utf-8")
            recovered = svc2.get(record)
            self.assertNotIn("999 tỷ", recovered["text"])

    def test_land_rewrite_grammar_and_domain_separation(self):
        self.assertEqual(colloquial("Tìm đất dưới 2 tỏi ở euro 2"), "Tìm đất dưới 2 tỷ ở Euro Village 2")
        self.assertTrue(accept_rewrite("có miếng đất nào tầm 3 tỷ không", "Tìm đất ở khoảng 3 tỷ"))
        # Must reject invented numbers, switched Guland family, or dropped legal intent:
        self.assertFalse(accept_rewrite("tìm đất ở Hòa Xuân", "Tìm đất ở dưới 3 tỷ"))
        self.assertFalse(accept_rewrite("tìm đất 3 tỷ", "Xem thửa Guland"))
        self.assertFalse(accept_rewrite("lô này sổ đỏ thế nào", "Tìm đất ở"))
        self.assertFalse(accept_rewrite("lô thứ 2", "Xem lô đất 2"))

        advisor = LandAdvisor(Settings(), enabled=True, engine=FakeLandEngine())
        # Non-Hòa-Xuân SmartProp district stays out of Hòa Xuân land tool:
        self.assertFalse(advisor.wants("Tìm đất nền tại Sơn Trà dưới 4 tỷ", None))
        # House/apartment search stays out of land tool:
        self.assertFalse(advisor.wants("Tìm căn hộ 2 phòng ngủ dưới 3 tỷ tại Hải Châu", None))
        self.assertTrue(advisor.wants("Tìm đất ở Hòa Xuân dưới 3 tỷ", None))

    def test_buyer_search_merges_sources_caps_overbudget_and_preserves_rental_invariants(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        bot.land_advisor = LandAdvisor(Settings(), enabled=True, engine=FakeLandEngine())
        backend._call = MagicMock(return_value={
            "items": [
                {
                    "id": PROP_UUID_1,
                    "status": "PUBLISHED",
                    "transactionType": "SALE",
                    "priceUnit": "TOTAL",
                    "currency": "VND",
                    "price": "2400000000",
                    "areaSqm": 95,
                    "propertyType": "LAND",
                    "landUseType": "RESIDENTIAL",
                    "district": "Cẩm Lệ",
                    "ward": "Hòa Xuân",
                    "title": "Đất nền Hòa Xuân liên hệ 0905123456",
                    "contentVersion": 2,
                },
                {
                    "id": "bbbbbbbb-bbbb-cccc-dddd-eeeeeeeeeeee",
                    "status": "DRAFT",
                    "transactionType": "SALE",
                    "priceUnit": "TOTAL",
                    "currency": "VND",
                    "price": "1900000000",
                    "areaSqm": 90,
                    "propertyType": "LAND",
                    "title": "Tin nháp riêng tư",
                },
            ],
            "totalPages": 1,
        })
        res = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 2,4 tỷ"))
        self.assertEqual(res.evidence["responseKind"], "BUYER_SEARCH")
        rows = res.evidence["buyerSearch"]["rows"]
        sources = {r["source"] for r in rows}
        self.assertEqual(sources, {"SMARTPROP", "LAND_DATA"})
        smartprop_row = next(r for r in rows if r["source"] == "SMARTPROP")
        self.assertNotIn("0905123456", smartprop_row["title"])
        land_row = next(r for r in rows if r["source"] == "LAND_DATA")
        # 2.5B vs 2.4B ceiling is +4.17% (within +15% reference cap), while stored budget stays 2.4B:
        self.assertGreater(land_row["overBudgetVnd"], 0)
        self.assertLessEqual(land_row["overBudgetPercent"], 15)
        self.assertEqual(str(res.evidence["session"]["context"]["criteria"]["budgetVnd"]), "2400000000")

        # Unsupported locality outside Đà Nẵng is never substituted with Đà Nẵng results:
        outside = bot.chat(ChatRequest(question="Tìm đất ở Hội An dưới 3 tỷ"))
        self.assertEqual(outside.evidence["responseKind"], "BUYER_SEARCH")
        self.assertEqual(outside.evidence["buyerSearch"]["rows"], [])
        self.assertIn("không thay thế", outside.answer.lower())

        # PR #45 rental rejection invariant must still intercept rental land queries:
        rental = bot.chat(ChatRequest(question="Tôi muốn thuê đất ở Hòa Xuân giá 10 triệu/tháng"))
        self.assertEqual(rental.evidence.get("clarification"), "RENTAL_BUDGET_NOT_SUPPORTED")

    def test_budget_and_query_rules_edge_cases(self):
        self.assertEqual(budget_rules.budget_band("từ 2 đến 3 tỷ"), {"minPrice": 2_000_000_000, "maxPrice": 3_000_000_000})
        self.assertEqual(query_rules.area_filter("ngang 5m dài 20m"), {"minArea": 100.0, "maxArea": 100.0})
        with self.assertRaises(ValueError):
            query_rules.area_filter("từ 120 đến 80 m2")


if __name__ == "__main__":
    unittest.main()
