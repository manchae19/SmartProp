"""PR #43 targeted unit, security, and multi-turn regression tests:
- P1-01: Negation-safe, ambiguity-fail-closed, criteria-scoped explicit over-budget consent
- P1-02: Actual dataset mode isolation (`PUBLIC_APPROVED` blocked fail-closed; `SYNTHETIC_DEMO`
  isolated behind loopback + `RAG_DEMO_KEY` / `X-SmartProp-Demo-Key` across both `/land/*` and `/chat`
  while preserving authorized local mentor demo and keeping public chat on real SmartProp listings)
- Hòa Xuân land routes, overview grounding, synthetic demo provenance, and multi-turn `PURCHASE_DECLINED`
  cancellation & domain transitions
"""
import hashlib
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
from app.rag.api import create_chat_app
from app.rag.buyer_search import parse_over_budget_consent
from app.rag.config import Settings
from app.rag.land_chat import LandAdvisor, accept_rewrite, colloquial
from app.rag.schemas import ChatRequest, ChatResponse
import test_rag_multiturn as fixtures


LAND_UUID_1 = "11111111-2222-3333-4444-555555555555"
PROP_UUID_1 = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
PROP_UUID_OVER = "cccccccc-bbbb-cccc-dddd-eeeeeeeeeeee"
DEMO_KEY = "pr43-test-internal-demo-key-2026"


def _make_land_row(code="DN-QH-0001", price=2_500_000_000, area=100.0):
    return {
        "id": code,
        "displayName": f"Ô quy hoạch thử nghiệm {code}",
        "displayNumber": int(code.split("-")[-1]),
        "computedAreaSqm": area,
        "priceDescription": f"{price / 1e9:.2f}".replace(".", ",") + " tỷ (giá giả lập demo — không phải giá thị trường)",
        "purposeGroup": "housing",
        "planningLabel": "Đất ở đô thị",
        "planningCode": "ODT",
        "planningCategory": "RESIDENTIAL_PLANNING",
        "pointOnSurface": [108.215, 16.005],
        "demoPriceVnd": price,
        "demoUnitPriceVndPerSqm": int(price / area),
        "effectivePriceClass": "DEMO",
        "addressEvidence": {"location": "Hòa Xuân, Đà Nẵng"},
        "demoPresentation": {
            "landType": "Nhóm quy hoạch tham khảo: đất ở (giả định demo, chưa xác minh địa chính)",
            "ownershipDocument": "Giả định kịch bản demo (sổ đỏ) — chưa có giấy chứng nhận thực tế được xác minh",
            "recovery": "Chưa xác minh quy hoạch thu hồi/giải tỏa (giả định kịch bản demo — không xác nhận không vướng quy hoạch)",
            "dispute": "Chưa xác minh",
            "mortgage": "Chưa xác minh",
            "compensation": "Chưa xác minh",
        },
        "floodDisplay": {
            "display": "Chưa có bản ghi ngập trùng tuyến đường nguồn (giả định kịch bản demo — không xác nhận an toàn ngập)",
            "relation": "USER_APPROVED_DEMO_SCENARIO",
            "isDemoAssumption": True,
        },
        "floodEvidence": {"items": [{"id": "FL-01", "location_text": "Đường 29/3", "publication_date": "2025"}]},
        "geometry": {"type": "Polygon", "coordinates": [[[108.21, 16.0], [108.22, 16.0], [108.22, 16.01], [108.21, 16.0]]]},
        "sourceFile": "/private/internal/path.geojson",
        "reviewFlags": ["INTERNAL_REVIEW_NOTE"],
    }


class FakeLandEngine:
    def __init__(self, count=1, base_price=2_500_000_000):
        self.converse_calls = 0
        self.rows = {}
        self.original = []
        self.activeids = set()
        for idx in range(1, count + 1):
            code = f"DN-QH-{idx:04d}"
            price = base_price + (idx - 1) * 50_000_000
            row = _make_land_row(code, price=price)
            self.rows[code] = row
            self.original.append({"id": code, "planningCode": "ODT", "planningCategory": "RESIDENTIAL_PLANNING", "computedAreaSqm": 100.0})
            self.activeids.add(code)
        self.pricedbyid = dict(self.rows)
        self.byid = dict(self.rows)
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
        if code == "DN-QH-0001":
            return LAND_UUID_1
        if code in self.rows:
            n = int(code.split("-")[-1])
            return f"11111111-2222-3333-4444-{n:012d}"
        return None

    def code_for(self, value):
        if value in self.rows:
            return value
        if value == LAND_UUID_1:
            return "DN-QH-0001"
        return None

    def resolve(self, code):
        return self.rows.get(code)

    def health(self):
        return {"status": "DEMO_ONLY", "records": len(self.rows)}

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
        self.converse_calls += 1
        if "khong hieu" in question.lower():
            return {"answer": "Tôi chưa hiểu yêu cầu này.", "rows": []}, state or {}
        row = self.rows["DN-QH-0001"]
        return {
            "answer": "Tìm thấy 1 ô quy hoạch tham khảo (không phải thửa địa chính chính thức).",
            "rows": [row],
            "start": 1,
            "total": len(self.rows),
            "filters": {"maxPrice": 3_000_000_000},
        }, {"lastDomain": "plot", "visibleIds": ["DN-QH-0001"], "seen": ["DN-QH-0001"], "selected": "DN-QH-0001"}


def _seed_verified_dataset(raw_root: Path, proc_root: Path, *, version="HX-LAND-DEMO-20261126",
                           public_approved=False, contains_synthetic=True, demo_approved=True, rights_ref=None):
    sources = []
    for rel in land_paths.REQUIRED_RAW_FILES:
        f = raw_root / rel
        f.parent.mkdir(parents=True, exist_ok=True)
        if rel.endswith("afternoon-import-20261125/manifest.json"):
            payload = {"version": "IMPORT-20261125", "source": "guland"}
        elif rel.endswith("flood-catalog-full.json"):
            payload = {"commit": "abc1234", "records": []}
        elif rel.endswith("plans.json") or rel.endswith("cells.json"):
            payload = []
        else:
            payload = {"ok": True}
        raw_bytes = json.dumps(payload).encode("utf-8")
        f.write_bytes(raw_bytes)
        sources.append({"path": rel, "bytes": len(raw_bytes), "sha256": hashlib.sha256(raw_bytes).hexdigest()})
    proc_root.mkdir(parents=True, exist_ok=True)
    manifest = {
        "version": version,
        "demoOnly": contains_synthetic,
        "containsSyntheticData": contains_synthetic,
        "publicApproved": public_approved,
        "demoApproved": demo_approved,
        "rightsApprovalRef": rights_ref,
        "sources": sources,
    }
    (proc_root / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")


class Pr43LandAndRagTests(unittest.TestCase):
    def test_p1_02_dataset_mode_governance_blocks_public_approved_and_requires_demo_key(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            proc_dir = Path(tmp) / "proc"
            _seed_verified_dataset(raw_dir, proc_dir)

            env_base = {
                "SMARTPROP_LAND_DATA_DIR": str(raw_dir),
                "SMARTPROP_LAND_PROCESSED_DIR": str(proc_dir),
                "SMARTPROP_LAND_DATA_VERSION": "HX-LAND-DEMO-20261126",
            }
            # 1. Disabled by default even when dataset files exist:
            with patch.dict(os.environ, env_base, clear=False):
                os.environ.pop("RAG_LAND_ENABLED", None)
                os.environ.pop("RAG_LAND_DEMO_ENABLED", None)
                os.environ.pop("RAG_DEMO_KEY", None)
                status = land_paths.verify_land_dataset()
                self.assertFalse(status["ok"])
                self.assertEqual(status["mode"], "DISABLED")
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")
                self.assertFalse(land_paths.land_enabled())

            # 2. Missing raw directory fails closed:
            with patch.dict(os.environ, {
                "SMARTPROP_LAND_DATA_DIR": str(Path(tmp) / "missing-raw"),
                "SMARTPROP_LAND_PROCESSED_DIR": str(proc_dir),
                "RAG_LAND_ENABLED": "true",
                "RAG_LAND_DEMO_ENABLED": "true",
                "RAG_DEMO_KEY": DEMO_KEY,
            }):
                missing = land_paths.verify_land_dataset()
                self.assertFalse(missing["ok"])
                self.assertEqual(missing["reasons"][0], "MISSING_RAW_FILES")
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")

            # 3. Demo-only without RAG_LAND_DEMO_ENABLED fails closed:
            with patch.dict(os.environ, {**env_base, "RAG_LAND_ENABLED": "true", "RAG_LAND_DEMO_ENABLED": "false", "RAG_DEMO_KEY": DEMO_KEY}):
                self.assertEqual(land_paths.verify_land_dataset()["reasons"], ["DATASET_USAGE_NOT_APPROVED"])
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")

            # 4. Demo-only with flags + dataset, WITHOUT RAG_DEMO_KEY, stays DISABLED at runtime:
            with patch.dict(os.environ, {**env_base, "RAG_LAND_ENABLED": "true", "RAG_LAND_DEMO_ENABLED": "true"}):
                os.environ.pop("RAG_DEMO_KEY", None)
                self.assertEqual(land_paths.verify_land_dataset()["mode"], "SYNTHETIC_DEMO")
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")
                self.assertFalse(land_paths.land_enabled())

            # 5. Demo-only WITH RAG_DEMO_KEY arms isolated SYNTHETIC_DEMO mode:
            with patch.dict(os.environ, {**env_base, "RAG_LAND_ENABLED": "true", "RAG_LAND_DEMO_ENABLED": "true", "RAG_DEMO_KEY": DEMO_KEY}):
                self.assertEqual(land_paths.land_runtime_mode(), "SYNTHETIC_DEMO")
                self.assertTrue(land_paths.land_enabled())

            # 6. Unsupported PUBLIC_APPROVED manifest MUST fail closed (current engine synthesizes demo prices/assumptions):
            pub_proc = Path(tmp) / "proc-public"
            _seed_verified_dataset(
                raw_dir, pub_proc, public_approved=True, contains_synthetic=False,
                demo_approved=False, rights_ref="APPROVAL-REF-001",
            )
            with patch.dict(os.environ, {
                "SMARTPROP_LAND_DATA_DIR": str(raw_dir),
                "SMARTPROP_LAND_PROCESSED_DIR": str(pub_proc),
                "SMARTPROP_LAND_DATA_VERSION": "HX-LAND-DEMO-20261126",
                "RAG_LAND_ENABLED": "true",
                "RAG_LAND_DEMO_ENABLED": "false",
                "RAG_DEMO_KEY": DEMO_KEY,
            }):
                pub_status = land_paths.verify_land_dataset()
                self.assertFalse(pub_status["ok"])
                self.assertEqual(pub_status["mode"], "UNSUPPORTED_PUBLIC_APPROVED")
                self.assertEqual(pub_status["reasons"], ["PUBLIC_APPROVED_ENGINE_NOT_IMPLEMENTED"])
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")
                self.assertFalse(land_paths.land_enabled())

            # 7. Invalid/tampered raw file hash fails closed:
            (raw_dir / "outputs/plot-display-labels.json").write_text('{"tampered":true}', encoding="utf-8")
            with patch.dict(os.environ, {**env_base, "RAG_LAND_ENABLED": "true", "RAG_LAND_DEMO_ENABLED": "true", "RAG_DEMO_KEY": DEMO_KEY}):
                tampered = land_paths.verify_land_dataset()
                self.assertFalse(tampered["ok"])
                self.assertEqual(tampered["reasons"][0], "RAW_FILE_HASH_MISMATCH")
                self.assertEqual(land_paths.land_runtime_mode(), "DISABLED")

    def test_p1_02_runtime_boundary_isolates_public_chat_and_direct_land_api_from_synthetic_demo(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            proc_dir = Path(tmp) / "proc"
            _seed_verified_dataset(raw_dir, proc_dir)

            bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
            fake_engine = FakeLandEngine(count=1, base_price=2_500_000_000)
            bot.land_advisor = LandAdvisor(Settings(demo_key=DEMO_KEY), enabled=True, engine=fake_engine)
            backend._call = MagicMock(return_value={
                "items": [{
                    "id": PROP_UUID_1, "status": "PUBLISHED", "transactionType": "SALE",
                    "priceUnit": "TOTAL", "currency": "VND", "price": "2400000000",
                    "areaSqm": 100, "propertyType": "LAND", "landUseType": "RESIDENTIAL",
                    "district": "Cẩm Lệ", "ward": "Hòa Xuân", "title": "Đất nền Hòa Xuân thật",
                }],
                "totalPages": 1,
            })

            env_armed = {
                "SMARTPROP_LAND_DATA_DIR": str(raw_dir),
                "SMARTPROP_LAND_PROCESSED_DIR": str(proc_dir),
                "SMARTPROP_LAND_DATA_VERSION": "HX-LAND-DEMO-20261126",
                "RAG_LAND_ENABLED": "true",
                "RAG_LAND_DEMO_ENABLED": "true",
                "RAG_DEMO_KEY": DEMO_KEY,
            }
            with patch.dict(os.environ, env_armed), patch.object(land_api, "_engine", return_value=fake_engine):
                app = create_chat_app(Settings(demo_key=DEMO_KEY), orchestrator=bot)
                client = TestClient(app, client=("127.0.0.1", 50000))

                # A. Direct /land/* requests without X-SmartProp-Demo-Key, with wrong key, or via public X-Forwarded-For -> 403!
                self.assertEqual(client.get(f"/land/records/{LAND_UUID_1}").status_code, 403)
                self.assertEqual(client.get("/land/health").status_code, 403)
                self.assertEqual(client.get(f"/land/records/{LAND_UUID_1}", headers={"X-SmartProp-Demo-Key": "wrong-key-value-12345"}).status_code, 403)
                self.assertEqual(
                    client.get(
                        f"/land/records/{LAND_UUID_1}",
                        headers={"X-SmartProp-Demo-Key": DEMO_KEY, "X-Forwarded-For": "203.0.113.42"},
                    ).status_code,
                    403,
                )

                # B. Public /chat request (no demo key) MUST NOT leak synthetic LAND_DATA or invoke LandAdvisor!
                pub_chat = client.post("/chat", json={"question": "Tìm đất ở Hòa Xuân dưới 3 tỷ"})
                self.assertEqual(pub_chat.status_code, 200)
                pub_body = pub_chat.json()
                self.assertEqual(pub_body["evidence"]["responseKind"], "BUYER_SEARCH")
                pub_rows = pub_body["evidence"]["buyerSearch"]["rows"]
                self.assertEqual([r["source"] for r in pub_rows], ["SMARTPROP"])
                self.assertNotIn("LAND_DATA", json.dumps(pub_body))
                self.assertIsNone(pub_body["evidence"].get("land"))

                # Public /chat land-specific prompt ("Xem thửa Guland") without demo key never invokes LandAdvisor:
                fake_engine.converse_calls = 0
                pub_guland = client.post("/chat", json={"question": "Xem thửa Guland"})
                self.assertEqual(pub_guland.status_code, 200)
                self.assertIsNone(pub_guland.json()["evidence"].get("land"))
                self.assertEqual(fake_engine.converse_calls, 0)

                # Proxied external client even WITH demo key header (e.g. misconfigured upstream) is rejected as non-demo:
                proxied_chat = client.post(
                    "/chat",
                    json={"question": "Tìm đất ở Hòa Xuân dưới 3 tỷ"},
                    headers={"X-SmartProp-Demo-Key": DEMO_KEY, "X-Forwarded-For": "198.51.100.7"},
                )
                self.assertEqual([r["source"] for r in proxied_chat.json()["evidence"]["buyerSearch"]["rows"]], ["SMARTPROP"])

                # C. Authorized loopback local mentor demo (127.0.0.1 + valid X-SmartProp-Demo-Key, no external XFF) succeeds:
                demo_record = client.get(f"/land/records/{LAND_UUID_1}", headers={"X-SmartProp-Demo-Key": DEMO_KEY})
                self.assertEqual(demo_record.status_code, 200)
                self.assertEqual(demo_record.json()["sourceCode"], "DN-QH-0001")

                demo_chat = client.post(
                    "/chat",
                    json={"question": "Tìm đất ở Hòa Xuân dưới 3 tỷ"},
                    headers={"X-SmartProp-Demo-Key": DEMO_KEY},
                )
                self.assertEqual(demo_chat.status_code, 200)
                demo_sources = {r["source"] for r in demo_chat.json()["evidence"]["buyerSearch"]["rows"]}
                self.assertEqual(demo_sources, {"SMARTPROP", "LAND_DATA"})

                # Session isolation: public caller presenting demo sessionId cannot read demo session state:
                demo_sid = demo_chat.json()["evidence"]["session"]["id"]
                hijack = client.post("/chat", json={"question": "Xem kết quả khác", "sessionId": demo_sid})
                self.assertEqual(hijack.json()["evidence"].get("clarification"), "NO_PENDING_LISTING_STEP")

    def test_p1_01_over_budget_consent_negation_ambiguity_withdrawal_and_criteria_scope(self):
        # Unit-level parser checks across positive, negated, withdrawn, and ambiguous forms:
        for negated in (
            "Tìm đất Hòa Xuân dưới 3 tỷ, không chấp nhận vượt ngân sách.",
            "Tìm đất ở Hòa Xuân dưới 3 tỷ, không đồng ý vượt ngân sách",
            "Tìm đất Hòa Xuân dưới 3 tỷ, không cho xem tham khảo vượt ngân sách",
            "Tìm đất Hòa Xuân dưới 3 tỷ, đừng vượt ngân sách",
            "Tìm đất Hòa Xuân dưới 3 tỷ, tuyệt đối dưới ngân sách",
            "Bỏ tham khảo vượt ngân sách",
            "Hủy nhóm vượt ngân sách",
            "Chưa chấp nhận vượt ngân sách",
        ):
            self.assertEqual(parse_over_budget_consent(negated), "DENY", f"Must deny: {negated}")

        for ambiguous in (
            "Tìm đất Hòa Xuân dưới 3 tỷ, có nên chấp nhận vượt ngân sách không?",
            "Tìm đất Hòa Xuân dưới 3 tỷ, có thể vượt ngân sách",
            "Tìm đất Hòa Xuân dưới 3 tỷ, nếu vượt ngân sách thì sao",
            "Tìm đất Hòa Xuân dưới 3 tỷ, phân vân vượt ngân sách",
            "Chấp nhận vượt ngân sách nhưng không vượt ngân sách",
        ):
            self.assertEqual(parse_over_budget_consent(ambiguous), "AMBIGUOUS", f"Must mark ambiguous: {ambiguous}")

        for positive in (
            "Tìm đất ở Hòa Xuân dưới 3 tỷ, chấp nhận vượt ngân sách",
            "Tìm đất ở Hòa Xuân dưới 3 tỷ, đồng ý xem tham khảo vượt ngân sách",
            "Cho xem tham khảo vượt ngân sách",
        ):
            self.assertEqual(parse_over_budget_consent(positive), "GRANT", f"Must grant: {positive}")

        # End-to-end orchestrator + buyer_search verification with both SmartProp (2.9B & 3.2B) and Land (3.1B):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        bot.land_advisor = LandAdvisor(Settings(demo_key=DEMO_KEY), enabled=True, engine=FakeLandEngine(count=1, base_price=3_100_000_000))

        def fake_backend_get(method, url):
            items = [
                {
                    "id": PROP_UUID_1, "status": "PUBLISHED", "transactionType": "SALE",
                    "priceUnit": "TOTAL", "currency": "VND", "price": "2900000000",
                    "areaSqm": 100, "propertyType": "LAND", "landUseType": "RESIDENTIAL",
                    "district": "Cẩm Lệ", "ward": "Hòa Xuân", "title": "Đất Hòa Xuân 2,9 tỷ",
                },
                {
                    "id": PROP_UUID_OVER, "status": "PUBLISHED", "transactionType": "SALE",
                    "priceUnit": "TOTAL", "currency": "VND", "price": "3200000000",
                    "areaSqm": 105, "propertyType": "LAND", "landUseType": "RESIDENTIAL",
                    "district": "Cẩm Lệ", "ward": "Hòa Xuân", "title": "Đất Hòa Xuân 3,2 tỷ",
                },
            ]
            if "maxPrice=3000000000" in url or "maxPrice=2950000000" in url:
                items = [x for x in items if int(x["price"]) <= (2950000000 if "2950000000" in url else 3000000000)]
            return {"items": items, "totalPages": 1}

        backend._call = MagicMock(side_effect=fake_backend_get)

        # 1. Exact reproduction prompt (negated consent): ceiling stays 3B, 0 over-budget cards across SmartProp & Land!
        repro = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, không chấp nhận vượt ngân sách."),
            allow_demo=True,
        )
        self.assertEqual(repro.evidence["responseKind"], "BUYER_SEARCH")
        repro_rows = repro.evidence["buyerSearch"]["rows"]
        self.assertEqual([r["price"] for r in repro_rows], [2_900_000_000])
        self.assertTrue(all(r["overBudgetVnd"] == 0 for r in repro_rows))
        self.assertEqual(str(repro.evidence["session"]["context"]["criteria"]["budgetVnd"]), "3000000000")

        # 2. Ambiguous consent fails closed (0 over-budget cards, saved budget stays 3B):
        ambig = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, có thể vượt ngân sách"),
            allow_demo=True,
        )
        self.assertEqual([r["price"] for r in ambig.evidence["buyerSearch"]["rows"]], [2_900_000_000])
        self.assertTrue(all(r["overBudgetVnd"] == 0 for r in ambig.evidence["buyerSearch"]["rows"]))
        self.assertEqual(str(ambig.evidence["session"]["context"]["criteria"]["budgetVnd"]), "3000000000")

        # 3. Positive consent grants <= +15% reference items while saved budget remains 3B:
        granted = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, đồng ý xem tham khảo vượt ngân sách"),
            allow_demo=True,
        )
        sid = granted.evidence["session"]["id"]
        granted_prices = [r["price"] for r in granted.evidence["buyerSearch"]["rows"]]
        self.assertEqual(granted_prices, [2_900_000_000, 3_100_000_000, 3_200_000_000])
        self.assertEqual(str(granted.evidence["session"]["context"]["criteria"]["budgetVnd"]), "3000000000")

        # 4. Consent withdrawal on active session immediately drops over-budget cards while keeping saved budget 3B:
        withdrawn = bot.chat(
            ChatRequest(question="Không chấp nhận vượt ngân sách", sessionId=sid),
            allow_demo=True,
        )
        self.assertEqual([r["price"] for r in withdrawn.evidence["buyerSearch"]["rows"]], [2_900_000_000])
        self.assertTrue(all(r["overBudgetVnd"] == 0 for r in withdrawn.evidence["buyerSearch"]["rows"]))
        self.assertEqual(str(withdrawn.evidence["session"]["context"]["criteria"]["budgetVnd"]), "3000000000")

        # 5. Re-grant consent, then change search criteria (budget, type, area, location) -> consent MUST NOT carry over!
        regranted = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, chấp nhận vượt ngân sách", sessionId=sid),
            allow_demo=True,
        )
        self.assertEqual(len(regranted.evidence["buyerSearch"]["rows"]), 3)

        # Criterion change A — area added without re-consenting -> fail closed to <= 3B:
        area_changed = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ diện tích trên 90 m2", sessionId=sid),
            allow_demo=True,
        )
        self.assertEqual([r["price"] for r in area_changed.evidence["buyerSearch"]["rows"]], [2_900_000_000])
        self.assertTrue(all(r["overBudgetVnd"] == 0 for r in area_changed.evidence["buyerSearch"]["rows"]))

        # Re-grant, then Criterion change B — type changed to Đất ở without re-consenting -> fail closed to <= 3B:
        bot.chat(ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, chấp nhận vượt ngân sách", sessionId=sid), allow_demo=True)
        type_changed = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 3 tỷ", sessionId=sid), allow_demo=True)
        self.assertEqual([r["price"] for r in type_changed.evidence["buyerSearch"]["rows"]], [2_900_000_000])

        # Re-grant, then Criterion change C — budget changed to 2,95 tỷ without re-consenting -> fail closed to <= 2.95B:
        sid2 = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, chấp nhận vượt ngân sách"),
            allow_demo=True,
        ).evidence["session"]["id"]
        budget_changed = bot.chat(ChatRequest(question="Tìm đất Hòa Xuân dưới 2,95 tỷ", sessionId=sid2), allow_demo=True)
        self.assertEqual([r["price"] for r in budget_changed.evidence["buyerSearch"]["rows"]], [2_900_000_000])
        self.assertEqual(str(budget_changed.evidence["session"]["context"]["criteria"]["budgetVnd"]), "2950000000")

        # Re-grant, then Criterion change D — location changed to Đà Nẵng without re-consenting -> fail closed to <= 3B:
        sid3 = bot.chat(
            ChatRequest(question="Tìm đất Hòa Xuân dưới 3 tỷ, chấp nhận vượt ngân sách"),
            allow_demo=True,
        ).evidence["session"]["id"]
        loc_changed = bot.chat(ChatRequest(question="Tìm đất ở Đà Nẵng dưới 3 tỷ", sessionId=sid3), allow_demo=True)
        self.assertTrue(all(r["price"] <= 3_000_000_000 and r["overBudgetVnd"] == 0 for r in loc_changed.evidence["buyerSearch"]["rows"]))

    def test_demo_documents_never_emit_source_free_legal_or_flood_safety_claims(self):
        with tempfile.TemporaryDirectory() as tmp:
            raw_dir = Path(tmp) / "raw"
            (raw_dir / "outputs/hoa-xuan-enriched-20261122").mkdir(parents=True, exist_ok=True)
            (raw_dir / "outputs/hoa-xuan-enriched-20261122/plans.json").write_text('[{"id":"P1","name":"Khu đô thị Hòa Xuân"}]', encoding="utf-8")
            (raw_dir / "outputs/hoa-xuan-enriched-20261122/cells.json").write_text('[{"id":"DN-QH-0001","sourcePlanIds":["P1"]}]', encoding="utf-8")
            import importlib
            with patch.object(land_paths, "DATA_ROOT", raw_dir):
                import app.land.demo_documents as demo_docs
                importlib.reload(demo_docs)
                for sample in (
                    {"id": "DN-QH-0001", "planningCategory": "RESIDENTIAL_PLANNING", "purposeGroup": "housing"},
                    {"id": "DN-QH-0002", "planningCategory": "RESIDENTIAL_PLANNING", "purposeGroup": "housing", "sourceLot": True},
                    {"id": "DN-QH-0003", "planningCategory": "AGRICULTURAL_PLANNING", "purposeGroup": "agriculture"},
                ):
                    annotated = demo_docs.annotate(sample)
                    serialized = json.dumps(annotated, ensure_ascii=False)
                    self.assertNotIn("Được cấp sổ", serialized)
                    self.assertNotIn("Không ngập úng", serialized)
                    self.assertNotIn("chưa nằm trong đất quy hoạch của nhà nước", serialized)
                    self.assertFalse(annotated["floodDisplay"]["verifiedForThisParcel"])
                    self.assertTrue(annotated["demoPresentation"]["isDemoScenario"])
                    self.assertIn("giả định", annotated["demoPresentation"]["ownershipDocument"].lower())

    def test_chat_app_works_and_omits_land_routes_when_land_disabled(self):
        bot, _, _, _ = fixtures.MultiTurnTests().service(props=[])
        with patch("app.land.paths.land_runtime_mode", return_value="DISABLED"):
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
        with patch("app.land.paths.land_runtime_mode", return_value="DISABLED"), \
             patch.dict(os.environ, {"RAG_ALLOWED_ORIGINS": "http://127.0.0.1:5173"}):
            client = TestClient(create_chat_app(Settings(), orchestrator=bot))
            forbidden = client.post("/chat", json={"question": "Xin chào"}, headers={"Origin": "https://evil.example"})
            self.assertEqual(forbidden.status_code, 403)
            allowed = client.post("/chat", json={"question": "Xin chào"}, headers={"Origin": "http://127.0.0.1:5173"})
            self.assertEqual(allowed.status_code, 200)
            server_to_server = client.post("/chat", json={"question": "Xin chào"})
            self.assertEqual(server_to_server.status_code, 200)

    def test_land_router_validates_ids_exposes_governance_and_strips_private_keys(self):
        fake = FakeLandEngine()
        app = FastAPI()
        with patch.object(land_api, "_engine", return_value=fake), \
             patch("app.land.api.land_runtime_mode", return_value="SYNTHETIC_DEMO"):
            app.include_router(land_api.create_land_router(expected_demo_key=DEMO_KEY))
            client = TestClient(app, client=("127.0.0.1", 50000))
            headers = {"X-SmartProp-Demo-Key": DEMO_KEY}

            ok = client.get(f"/land/records/{LAND_UUID_1}", headers=headers)
            self.assertEqual(ok.status_code, 200)
            body = ok.json()
            self.assertEqual(body["sourceCode"], "DN-QH-0001")
            self.assertTrue(body["demoOnly"])
            self.assertFalse(body["governance"]["publicApproved"])
            self.assertFalse(body["governance"]["officialCadastralParcel"])
            self.assertFalse(body["governance"]["marketOrTransactionValue"])
            self.assertEqual(body["governance"]["excludedFrom"], ["VALUATION", "COMPARABLE", "MARKET"])
            self.assertFalse(body["documents"]["verifiedForThisParcel"])
            self.assertFalse(body["flood"]["verifiedForThisParcel"])
            self.assertIn("không phải giá thị trường", body["price"]["evidence"][0]["label"].lower())
            self.assertNotIn("sourceFile", json.dumps(body))
            self.assertNotIn("reviewFlags", json.dumps(body))

            for bad in ("../etc/passwd", "DN-QH-0001;DROP", "unknown-id", "a" * 81):
                self.assertIn(client.get(f"/land/records/{bad}", headers=headers).status_code, (404, 422))

            neighbors = client.get("/land/neighbors", params={"id": "DN-QH-0001"}, headers=headers)
            self.assertEqual(neighbors.status_code, 200)
            props = neighbors.json()["features"][0]["properties"]
            self.assertNotIn("geometry", props)
            self.assertNotIn("sourceFile", props)
            self.assertNotIn("reviewFlags", props)
            self.assertEqual(props["landId"], LAND_UUID_1)

            too_many = ",".join(f"FL-{i}" for i in range(201))
            self.assertEqual(client.get("/land/flood-map", params={"ids": too_many}, headers=headers).status_code, 400)

    def test_overview_service_grounds_sentences_and_rejects_tampered_disk_cache(self):
        fake = FakeLandEngine()
        with patch.object(land_api, "_engine", return_value=fake), tempfile.TemporaryDirectory() as cache_dir:
            record = land_api.record_view("DN-QH-0001")
            svc = land_overview.OverviewService(generator=lambda groups: [0] * len(groups), cache_dir=cache_dir)
            first = svc.get(record)
            self.assertFalse(first["cached"])
            self.assertIn(first["generationMode"], ("TEMPLATE", "OLLAMA_GROUNDED_CHOICES"))
            self.assertIn("giả lập", first["text"].lower())

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
        self.assertFalse(accept_rewrite("tìm đất ở Hòa Xuân", "Tìm đất ở dưới 3 tỷ"))
        self.assertFalse(accept_rewrite("tìm đất 3 tỷ", "Xem thửa Guland"))
        self.assertFalse(accept_rewrite("lô này sổ đỏ thế nào", "Tìm đất ở"))
        self.assertFalse(accept_rewrite("lô thứ 2", "Xem lô đất 2"))

        advisor = LandAdvisor(Settings(), enabled=True, engine=FakeLandEngine())
        self.assertFalse(advisor.wants("Tìm đất nền tại Sơn Trà dưới 4 tỷ", None))
        self.assertFalse(advisor.wants("Tìm căn hộ 2 phòng ngủ dưới 3 tỷ tại Hải Châu", None))
        self.assertTrue(advisor.wants("Tìm đất ở Hòa Xuân dưới 3 tỷ", None))

    def test_hard_budget_enforced_across_smartprop_and_land_without_15pct_expansion(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service(props=[])
        bot.land_advisor = LandAdvisor(Settings(demo_key=DEMO_KEY), enabled=True, engine=FakeLandEngine(count=1))
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

        # 1. Below 2.4B (in demo mode): 2.5B land cell MUST NOT be included via automatic +15% expansion!
        below = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 2,4 tỷ"), allow_demo=True)
        self.assertEqual(below.evidence["responseKind"], "BUYER_SEARCH")
        rows = below.evidence["buyerSearch"]["rows"]
        self.assertEqual([r["source"] for r in rows], ["SMARTPROP"])
        self.assertTrue(all(r["price"] <= 2_400_000_000 for r in rows))
        self.assertTrue(all(r["overBudgetVnd"] == 0 for r in rows))
        self.assertNotIn("0905123456", rows[0]["title"])
        self.assertEqual(str(below.evidence["session"]["context"]["criteria"]["budgetVnd"]), "2400000000")

        # 2. Explicit range 2.4B–2.5B includes both SmartProp (2.4B) and Land (2.5B) when allow_demo=True:
        ranged = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân từ 2,4 đến 2,5 tỷ"), allow_demo=True)
        self.assertEqual({r["source"] for r in ranged.evidence["buyerSearch"]["rows"]}, {"SMARTPROP", "LAND_DATA"})
        self.assertTrue(all(2_400_000_000 <= r["price"] <= 2_500_000_000 for r in ranged.evidence["buyerSearch"]["rows"]))

        # 3. Exact price 2.5B ("đúng 2,5 tỷ") returns only exact 2.5B item:
        exact = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân đúng 2,5 tỷ"), allow_demo=True)
        self.assertEqual([r["price"] for r in exact.evidence["buyerSearch"]["rows"]], [2_500_000_000])

        # 4. Unsupported locality outside Đà Nẵng is never substituted:
        outside = bot.chat(ChatRequest(question="Tìm đất ở Hội An dưới 3 tỷ"), allow_demo=True)
        self.assertEqual(outside.evidence["buyerSearch"]["rows"], [])
        self.assertIn("không thay thế", outside.answer.lower())

        # 5. PR #45 rental rejection invariant intercepts rental land queries:
        rental = bot.chat(ChatRequest(question="Tôi muốn thuê đất ở Hòa Xuân giá 10 triệu/tháng"), allow_demo=True)
        self.assertEqual(rental.evidence.get("clarification"), "RENTAL_BUDGET_NOT_SUPPORTED")

    def test_purchase_declined_retires_buyer_land_and_blocks_all_stale_actions(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service()
        fake_engine = FakeLandEngine(count=6)
        bot.land_advisor = LandAdvisor(Settings(demo_key=DEMO_KEY), enabled=True, engine=fake_engine)
        backend._call = MagicMock(return_value={
            "items": [{
                "id": PROP_UUID_1, "status": "PUBLISHED", "transactionType": "SALE",
                "priceUnit": "TOTAL", "currency": "VND", "price": "2400000000",
                "areaSqm": 100, "propertyType": "LAND", "landUseType": "RESIDENTIAL",
                "district": "Cẩm Lệ", "ward": "Hòa Xuân", "title": "Đất nền Hòa Xuân",
            }],
            "totalPages": 1,
        })

        def setup_canceled_session():
            first = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 3 tỷ"), allow_demo=True)
            s_id = first.evidence["session"]["id"]
            self.assertEqual(first.evidence["responseKind"], "BUYER_SEARCH")
            self.assertEqual(len(first.evidence["buyerSearch"]["rows"]), 5)
            self.assertIn("Xem kết quả khác", first.evidence["quickReplies"])
            canceled = bot.chat(ChatRequest(question="Tôi không muốn tìm mua nữa", sessionId=s_id), allow_demo=True)
            self.assertEqual(canceled.evidence.get("clarification"), "PURCHASE_DECLINED")
            self.assertEqual(canceled.recommendedProperties, [])
            needs = bot.sessions._items[("PUBLIC_DEMO", s_id)].needs
            self.assertFalse(needs["buyerSearch"]["active"])
            self.assertFalse(needs["buyerSearch"]["pagingActive"])
            self.assertIsNone(needs["buyerSearch"]["pending"])
            self.assertIsNone(needs["land"]["lastDomain"])
            self.assertNotIn("listOwner", needs)
            backend._call.reset_mock()
            backend.recommend.reset_mock()
            fake_engine.converse_calls = 0
            return s_id

        for stale in (
            "Xem kết quả khác",
            "Xem thêm",
            "Còn lô nào khác không",
            "Tìm lại theo bộ lọc",
            "Đất ở",
            "Đất nông nghiệp",
            "Nhà",
            "Căn hộ",
            "Tất cả",
            "Hòa Xuân",
            "Đà Nẵng",
            "Cẩm Lệ",
            "2,5 tỷ",
            "Dưới 2,5 tỷ",
        ):
            sid = setup_canceled_session()
            res = bot.chat(ChatRequest(question=stale, sessionId=sid), allow_demo=True)
            self.assertEqual(res.evidence["session"]["id"], sid, f"Session rolled over on stale: {stale}")
            self.assertEqual(res.evidence.get("clarification"), "NO_PENDING_LISTING_STEP", f"Failed on stale: {stale}")
            self.assertEqual(res.recommendedProperties, [], f"Property cards leaked on stale: {stale}")
            self.assertIsNone(res.evidence.get("buyerSearch"), f"buyerSearch leaked on stale: {stale}")
            self.assertIsNone(res.evidence.get("land"), f"land leaked on stale: {stale}")
            self.assertEqual(backend._call.call_count, 0, f"backend._call invoked on stale: {stale}")
            self.assertEqual(backend.recommend.call_count, 0, f"backend.recommend invoked on stale: {stale}")
            self.assertEqual(fake_engine.converse_calls, 0, f"land converse invoked on stale: {stale}")

        sid = setup_canceled_session()
        fresh = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 2,6 tỷ", sessionId=sid), allow_demo=True)
        self.assertEqual(fresh.evidence["responseKind"], "BUYER_SEARCH")
        self.assertGreater(len(fresh.evidence["buyerSearch"]["rows"]), 0)
        self.assertTrue(all(r["price"] <= 2_600_000_000 for r in fresh.evidence["buyerSearch"]["rows"]))

    def test_transitions_from_land_search_to_rental_amenities_and_house_recommendation(self):
        bot, backend, _, _ = fixtures.MultiTurnTests().service()
        fake_engine = FakeLandEngine(count=6)
        bot.land_advisor = LandAdvisor(Settings(demo_key=DEMO_KEY), enabled=True, engine=fake_engine)
        backend._call = MagicMock(return_value={"items": [], "totalPages": 1})

        s1 = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 3 tỷ"), allow_demo=True)
        sid_rent = s1.evidence["session"]["id"]
        rent = bot.chat(ChatRequest(question="Đổi sang thuê nhà ở Hải Châu", sessionId=sid_rent), allow_demo=True)
        self.assertEqual(rent.evidence.get("clarification"), "RENTAL_BUDGET_NOT_SUPPORTED")
        backend._call.reset_mock()
        backend.recommend.reset_mock()
        fake_engine.converse_calls = 0
        stale_after_rent = bot.chat(ChatRequest(question="Xem kết quả khác", sessionId=sid_rent), allow_demo=True)
        self.assertEqual(stale_after_rent.evidence.get("clarification"), "RENTAL_BUDGET_NOT_SUPPORTED")
        self.assertEqual(stale_after_rent.recommendedProperties, [])
        self.assertIsNone(stale_after_rent.evidence.get("buyerSearch"))
        self.assertIsNone(stale_after_rent.evidence.get("land"))
        self.assertEqual(backend._call.call_count, 0)
        self.assertEqual(backend.recommend.call_count, 0)
        self.assertEqual(fake_engine.converse_calls, 0)

        s2 = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 3 tỷ"), allow_demo=True)
        sid_am = s2.evidence["session"]["id"]
        am = bot.chat(ChatRequest(question="Ở Hải Châu có bệnh viện nào?", sessionId=sid_am), allow_demo=True)
        self.assertIn(am.evidence["responseKind"], ("AREA_AMENITIES", "INSUFFICIENT_AMENITY_EVIDENCE"))
        backend._call.reset_mock()
        more_am = bot.chat(ChatRequest(question="Xem thêm", sessionId=sid_am), allow_demo=True)
        self.assertEqual(more_am.evidence["responseKind"], "AMENITY_PAGE_UNAVAILABLE")
        stale_buyer_am = bot.chat(ChatRequest(question="Xem kết quả khác", sessionId=sid_am), allow_demo=True)
        self.assertEqual(stale_buyer_am.evidence.get("clarification"), "NO_PENDING_LISTING_STEP")
        self.assertEqual(backend._call.call_count, 0)

        s3 = bot.chat(ChatRequest(question="Tìm đất ở Hòa Xuân dưới 3 tỷ"), allow_demo=True)
        sid_house = s3.evidence["session"]["id"]
        backend._call.reset_mock()
        backend.recommend.reset_mock()
        house = bot.chat(ChatRequest(question="Tìm nhà ở Thanh Khê dưới 3 tỷ", sessionId=sid_house), allow_demo=True)
        self.assertIsNone(house.evidence.get("buyerSearch"))
        self.assertIsNone(house.evidence.get("land"))
        self.assertEqual(backend.recommend.call_count, 1)
        self.assertGreater(len(house.recommendedProperties), 0)
        backend.recommend.reset_mock()
        stale_after_house = bot.chat(ChatRequest(question="Xem kết quả khác", sessionId=sid_house), allow_demo=True)
        self.assertEqual(stale_after_house.evidence.get("clarification"), "NO_PENDING_LISTING_STEP")
        self.assertEqual(backend.recommend.call_count, 0)

    def test_budget_and_query_rules_edge_cases(self):
        self.assertEqual(budget_rules.budget_band("từ 2 đến 3 tỷ"), {"minPrice": 2_000_000_000, "maxPrice": 3_000_000_000})
        self.assertEqual(budget_rules.budget_band("Tìm đất Hòa Xuân 3 tỷ, đừng vượt ngân sách"), {"maxPrice": 3_000_000_000})
        self.assertEqual(query_rules.area_filter("ngang 5m dài 20m"), {"minArea": 100.0, "maxArea": 100.0})
        with self.assertRaises(ValueError):
            query_rules.area_filter("từ 120 đến 80 m2")


if __name__ == "__main__":
    unittest.main()
