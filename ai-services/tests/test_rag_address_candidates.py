"""Exercise both public address routes through FastAPI and the paginated listing client."""
import json
from decimal import Decimal
from pathlib import Path
import shutil
import subprocess

import httpx
import pytest
from fastapi.testclient import TestClient

import test_rag_nearby as nearby
from app.rag import tools as tools_module
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.tools import BackendTools


ADDRESS = "300 Dũng Sĩ Thanh Khê"


def listing(index, area, meters=None, **overrides):
    return {
        "id": f"aaaaaaaa-bbbb-cccc-dddd-{index:012d}",
        "title": "Tin thử", "address": ADDRESS, "status": "PUBLISHED",
        "transactionType": "SALE", "currency": "VND", "priceUnit": "TOTAL",
        "price": 2_000_000_000, "areaSqm": area, "propertyType": "HOUSE",
        "district": "Thanh Khê", "ward": "Thanh Khê Tây",
        "latitude": nearby.ORIGIN["latitude"] + (meters or index * 10) / 111_194.9,
        "longitude": nearby.ORIGIN["longitude"],
        **overrides,
    }


@pytest.fixture(params=["address", "nearby"])
def search(request):
    is_nearby = request.param == "nearby"

    def run(rows, constraint="", *, prompt=None, followups=(), expected_address=ADDRESS,
            upstream_filters=False, continue_session=True, auto_consent=True,
            prior=None, pending=None, audit=None, **criteria):
        calls = []

        def public_backend(outbound):
            assert outbound.url.path == "/api/v1/properties"
            assert "Authorization" not in outbound.headers
            params = outbound.url.params
            if is_nearby:
                assert params.get("bbox")
            else:
                assert params["address"] == expected_address
            page, size = int(params["page"]), int(params["size"])
            calls.append(dict(params))
            candidates = rows
            if upstream_filters:
                for bound, compare in (
                    ("minArea", lambda area, limit: area > limit),
                    ("maxArea", lambda area, limit: area < limit),
                ):
                    if params.get(bound + "Exclusive") == "true":
                        candidates = [row for row in candidates if compare(Decimal(str(row["areaSqm"])), Decimal(params[bound]))]
            return httpx.Response(200, json={
                "items": candidates[page * size:(page + 1) * size],
                "page": page, "size": size,
                "totalElements": len(candidates), "totalPages": (len(candidates) + size - 1) // size,
            })

        service, backend = nearby.NearbyAnswerTests().service([])
        if prior is not None:
            context, prior_id, _ = service.sessions.begin(None, scope="PUBLIC")
            service.sessions.record(context, criteria=prior, property_ids=[], area_ids=[], evidence_ids=[])
            context.needs.update(pending or {})
            criteria["sessionId"] = prior_id
        backend.amenity_areas.return_value = [
            {"areaLevel": "WARD", "areaName": name, "parentDistrict": "Thanh Khê"}
            for name in ("Thanh Khê Đông, Thanh Khê", "Thanh Khê Tây, Thanh Khê")
        ]
        settings = Settings()
        tools = BackendTools(settings)
        tools.close()
        with httpx.Client(base_url="http://127.0.0.1", transport=httpx.MockTransport(public_backend)) as upstream:
            tools.client = upstream
            backend.search_by_address.side_effect = tools.search_by_address
            backend.search_nearby.side_effect = tools.search_nearby
            with TestClient(create_chat_app(settings, service)) as client:
                relation = "gần" if is_nearby else "ở"
                response = client.post("/chat", json={
                    "question": (prompt or f"Tìm nhà {{relation}} {ADDRESS} {constraint}").replace("{relation}", relation),
                    **criteria,
                })
                assert response.status_code == 200
                turns = [response.json()]
                if auto_consent and response.json()["evidence"].get("clarification") == "NEAR_ADDRESS_CONSENT":
                    assert is_nearby
                    backend.geocode_workplace.assert_not_called()
                    first = response.json()["evidence"]
                    session_id = first["session"]["id"]
                    second = client.post("/chat", json={
                        "question": "Đồng ý tìm vị trí", "sessionId": session_id,
                    })
                    assert second.status_code == 200
                    turns.append(second.json())
                    backend.geocode_workplace.assert_called_once_with(expected_address)
                    pick = second.json()["evidence"]
                    assert pick["clarification"] == "NEAR_ADDRESS_PICK"
                    response = client.post("/chat", json={
                        "question": pick["quickReplies"][0], "sessionId": session_id,
                    })
                    assert response.status_code == 200
                    turns.append(response.json())
                for question in followups:
                    payload = {"question": question}
                    if continue_session:
                        payload["sessionId"] = response.json()["evidence"]["session"]["id"]
                    response = client.post("/chat", json=payload)
                    assert response.status_code == 200
                    turns.append(response.json())
        if audit is not None:
            audit.update(turns=turns, geocodes=[call.args[0] for call in backend.geocode_workplace.call_args_list],
                         recommendations=backend.recommend.call_count)
        return response.json(), calls

    return run


def property_ids(response):
    return [card["id"] for card in response["recommendedProperties"]]


def test_matching_fourth_listing_survives_the_limit(search):
    rows = [listing(i, area) for i, area in enumerate((95, 90, 80, 79), 1)]
    result, calls = search(rows, "dưới 80 m²")
    assert property_ids(result) == [rows[3]["id"]]
    assert result["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert result["evidence"]["addressSearchComplete"]
    assert calls[0]["maxArea"] == "80"


@pytest.mark.parametrize(("constraint", "wanted", "bounds"), [
    ("tối đa 80 m²", [69, 70, 79, 80], {"maxArea": "80"}),
    ("trên 80 m²", [81, 85], {"minArea": "80"}),
    ("diện tích 70–80 m²", [70, 79, 80], {"minArea": "70", "maxArea": "80"}),
    ("trên 100 m²", [], {"minArea": "100"}),
])
def test_area_comparison_preserves_order_and_caps_cards(search, constraint, wanted, bounds):
    rows = [listing(i, area) for i, area in enumerate((85, 69, 81, 80, 79, 70), 1)]
    result, calls = search(rows, constraint)
    assert property_ids(result) == [row["id"] for row in rows if row["areaSqm"] in wanted][:3]
    assert {key: calls[0][key] for key in bounds} == bounds
    assert result["evidence"]["addressSearchComplete"]
    if not wanted:
        assert result["evidence"]["responseKind"] in {"NO_MATCHES", "ADDRESS_NO_RESULTS"}
        assert result["evidence"]["session"]["context"]["lastSearchEmpty"]


def test_inclusive_maximum_keeps_both_the_boundary_and_the_smaller_listing(search):
    rows = [listing(i, area) for i, area in enumerate((95, 90, 80, 79), 1)]
    result, _ = search(rows, "tối đa 80 m²")
    assert property_ids(result) == [rows[2]["id"], rows[3]["id"]]


def test_matching_listing_on_next_page(search):
    rows = [listing(i, 80) for i in range(1, 51)] + [listing(51, 79, meters=200)]
    result, calls = search(rows, "dưới 80 m²")
    assert property_ids(result) == [rows[-1]["id"]]
    assert [call["page"] for call in calls] == ["0", "1"]
    assert calls[0]["size"] == "50"


def test_filters_and_public_eligibility_precede_ranking_and_the_limit(search):
    rows = [
        listing(1, 79, price=3_010_000_000), listing(2, 79, price=1_990_000_000),
        listing(3, 79, propertyType="APARTMENT"),
        listing(4, 79, district="Hải Châu"), listing(5, 79, ward="Thanh Khê Đông"),
        listing(6, 79, status="DRAFT"), listing(7, 79, expiresAt="2000-01-01T00:00:00Z"),
        listing(8, 79, status="PRIVATE"), listing(9, 79, deletedAt="2000-01-01T00:00:00Z"),
        listing(10, 79, transactionType="RENT"),
        listing(11, 79, ward="Thanh  Khê Tây", ownerId="synthetic-private-owner"),
        listing(12, 77, meters=105, price=3_000_000_000),
    ]
    result, calls = search(rows, "dưới 80 m²", minPriceVnd=2_000_000_000, budgetVnd=3_000_000_000,
                           propertyType="HOUSE", district="Thanh Khê", ward="Thanh Khê Tây")
    cards = result["recommendedProperties"]
    expected = [rows[10]["id"], rows[11]["id"]]
    if "bbox" in calls[0]:
        expected.reverse()
        assert [card["distanceMeters"] for card in cards] == [105.0, 110.0]
    assert property_ids(result) == expected
    assert all("ownerId" not in card for card in cards)
    assert all(citation["scope"] == "PUBLIC" for citation in result["citations"])
    assert len(result["citations"]) == 2
    assert calls[0]["minPrice"] == "2000000000"
    assert calls[0]["maxPrice"] == "3000000000"
    assert calls[0]["propertyType"] == "HOUSE"
    assert calls[0]["transactionType"] == "SALE"


def test_partial_scan_cannot_report_no_matches(search, monkeypatch):
    monkeypatch.setattr(tools_module, "NEARBY_MAX_PAGES", 1)
    rows = [listing(i, 80) for i in range(1, 51)] + [listing(51, 79)]
    result, calls = search(rows, "dưới 80 m²")
    assert len(calls) == 1
    assert property_ids(result) == []
    assert result["evidence"]["clarification"] == "ADDRESS_SEARCH_INCOMPLETE"
    assert not result["evidence"]["addressSearchComplete"]
    assert not result["evidence"]["session"]["context"]["lastSearchEmpty"]
    assert "Vẫn còn trang chưa kiểm tra" in result["answer"]


@pytest.mark.parametrize(("constraint", "areas", "strict_flag"), [
    ("dưới 80 m²", [79, 79.99], "maxAreaExclusive"),
    ("nhỏ hơn 80 m²", [79, 79.99], "maxAreaExclusive"),
    ("bé hơn 80 m²", [79, 79.99], "maxAreaExclusive"),
    ("ít hơn 80 m²", [79, 79.99], "maxAreaExclusive"),
    ("trên 80 m²", [80.01, 81], "minAreaExclusive"),
    ("lớn hơn 80 m²", [80.01, 81], "minAreaExclusive"),
    ("tối đa 80 m²", [79, 79.99, 80], None),
    ("không quá 80 m²", [79, 79.99, 80], None),
    ("tối thiểu 80 m²", [80, 80.01, 81], None),
    ("ít nhất 80 m²", [80, 80.01, 81], None),
    ("từ 70 đến 80 m²", [79, 79.99, 80], None),
    ("nho hon 80,01 m2", [79, 79.99, 80], "maxAreaExclusive"),
])
def test_comparison_matrix_in_short_questions(search, constraint, areas, strict_flag):
    rows = [listing(i, area) for i, area in enumerate((69.99, 79, 79.99, 80, 80.01, 81), 1)]
    # Put below-range 69.99 outside the default 1 km radius for this shared matrix.
    rows[0]["address"] = "3000 Dũng Sĩ Thanh Khê"
    rows[0]["latitude"] += 0.05
    result, calls = search(rows, prompt=f"Nhà {{relation}} {ADDRESS} {constraint}")
    assert [p["areaSqm"] for p in result["recommendedProperties"]] == areas
    for flag in ("minAreaExclusive", "maxAreaExclusive"):
        assert calls[0].get(flag) == ("true" if flag == strict_flag else None)


@pytest.mark.parametrize("constraint", ["từ 81 đến 79 m²", "từ 70 đến 80 m² và trên 90 m²"])
def test_contradictory_area_stops_before_geocode_or_search(search, constraint):
    result, calls = search([listing(1, 80)], prompt=f"Nhà {{relation}} {ADDRESS} {constraint}")
    assert result["evidence"]["clarification"] == "AREA_RANGE_INVALID"
    assert calls == []


@pytest.mark.parametrize("separator", [" ", ", "])
@pytest.mark.parametrize("area_label", ["", "diện tích "])
def test_street_is_sent_to_the_public_api_or_geocoder(search, separator, area_label):
    result, calls = search([listing(1, 79)], prompt=f"Tìm nhà {{relation}} {ADDRESS}{separator}{area_label}dưới 80 m²")
    assert property_ids(result) == [listing(1, 79)["id"]]
    assert calls[0]["maxAreaExclusive"] == "true"


def test_natural_district_is_not_the_district_in_the_street_name(search):
    rows = [listing(1, 79), listing(2, 79, district="Hải Châu", ward="Bình Hiên")]
    result, _ = search(rows, "chỉ ở quận Hải Châu")
    assert property_ids(result) == [rows[1]["id"]]
    assert result["evidence"]["session"]["context"]["criteria"]["district"] == "Hải Châu"


def test_only_in_clause_distinguishes_target_from_postal_district(search):
    rows = [listing(1, 79), listing(2, 79, district="Hải Châu")]
    result, _ = search(rows, "quận Thanh Khê, chỉ ở quận Hải Châu")
    assert property_ids(result) == [rows[1]["id"]]


def test_street_number_and_budget_are_not_area_filters(search):
    result, calls = search([listing(1, 79)], "giá dưới 3 tỷ")
    assert property_ids(result) == [listing(1, 79)["id"]]
    assert calls[0]["maxPrice"] == "3000000000"
    assert "minArea" not in calls[0] and "maxArea" not in calls[0]


def test_natural_ward_uses_exact_normalized_scope(search):
    rows = [listing(1, 79), listing(2, 79, ward="Thanh  Khê Đông")]
    result, _ = search(rows, "phường Thanh Khê Đông")
    assert property_ids(result) == [rows[1]["id"]]


def test_location_followup_clears_stale_ward_and_keeps_confirmed_nearby_origin(search):
    rows = [listing(1, 79), listing(2, 79, ward="Thanh Khê Đông"),
            listing(3, 79, district="Hải Châu", ward="Bình Hiên")]
    result, calls = search(rows, "phường Thanh Khê Tây",
                           followups=["Chỉ ở quận Hải Châu", "Phường Thanh Khê Đông"])
    assert len(calls) == 3
    assert property_ids(result) == [rows[1]["id"]]
    assert result["evidence"]["session"]["context"]["criteria"]["district"] == "Thanh Khê"


def test_ward_is_cleared_when_district_changes(search):
    rows = [listing(1, 79), listing(2, 79, district="Hải Châu", ward="Bình Hiên")]
    result, _ = search(rows, "phường Thanh Khê Tây", followups=["Chuyển sang quận Hải Châu"])
    assert property_ids(result) == [rows[1]["id"]]
    assert "ward" not in result["evidence"]["session"]["context"]["criteria"]


def test_location_followup_cannot_reuse_another_sessions_address(search):
    rows = [listing(1, 79)]
    result, calls = search(rows, "dưới 80 m²", followups=["Chỉ ở quận Hải Châu"], continue_session=False)
    assert len(calls) == 1
    assert "addressQuery" not in result["evidence"]
    assert property_ids(result) == []


@pytest.mark.parametrize("location", ["quận Hải Châu hoặc Thanh Khê", "quận Hải Châu phường Thanh Khê Đông"])
def test_ambiguous_or_conflicting_location_is_clarified(search, location):
    result, calls = search([listing(1, 79)], location)
    assert result["evidence"]["clarification"] == "LISTING_LOCALITY_UNRESOLVED"
    assert calls == []


def test_unmatched_location_does_not_broaden_the_search(search):
    result, calls = search([listing(1, 79)], "chỉ ở quận Hải Châu")
    assert property_ids(result) == []
    assert len(calls) == 1
    assert result["evidence"]["criteria"]["district"] == "Hải Châu"


@pytest.mark.parametrize("prompt", [
    f"Nhà {{relation}} {ADDRESS} giá thuê dưới 10 triệu mỗi tháng",
    f"Tìm thuê nhà {{relation}} {ADDRESS} dưới 10 triệu/tháng",
    f"Nhà {{relation}} {ADDRESS} giá thuê dưới 10 triệu",
])
def test_rental_budget_never_queries_sale_listings(search, prompt):
    result, calls = search([listing(1, 79, price=9_000_000)], prompt=prompt)
    assert result["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
    assert calls == []


@pytest.mark.parametrize(("constraint", "area"), [
    ("dưới 80 m²", 79),
    ("trên 80 m²", 81),
])
def test_search_passes_strict_bounds_to_pre_paginate_upstream(search, constraint, area):
    # The real MySQL specification is verified by PropertyStrictAreaIT. Here we
    # enforce the outbound parameter and simulate that API filtering before the page.
    rows = [listing(i, 80) for i in range(1, 1001)] + [listing(1001, area, meters=200)]
    result, calls = search(rows, constraint, upstream_filters=True)
    assert [p["areaSqm"] for p in result["recommendedProperties"]] == [area]
    assert len(calls) == 1


def assert_frontend_contract(packet, expected):
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is required for live Python-to-frontend contract coverage")
    frontend = Path(__file__).resolve().parents[2] / "frontend"
    result = subprocess.run([node, "--input-type=module", "-e", """
      import assert from 'node:assert/strict';
      import { readFileSync } from 'node:fs';
      import { publicChatResponse } from './src/features/prediction/chat.js';
      import { chatPresentation } from './src/features/prediction/chatPresentation.js';
      const {packet, expected} = JSON.parse(readFileSync(0, 'utf8'));
      assert.equal(publicChatResponse(packet), packet);
      const view = chatPresentation(packet);
      assert.equal(view.cards.length, expected.cards);
      assert.equal(view.noMatches, expected.empty);
      if (expected.incomplete) assert.match(view.summary, /trang chưa kiểm tra|trong phần đã đọc/u);
      if (expected.address && !expected.cards && !expected.incomplete) {
        assert.equal(view.summary, packet.answer);
        assert(!view.summary.includes('undefined'));
      }
      const rejects = value => assert.throws(() => publicChatResponse(value), {code:'UNSAFE_CHAT_RESPONSE'});
      if (!expected.cards) {
        for (const patch of [
          {sourcePath: '/api/v1/sources/private'},
          {sourcePath: expected.address ? '/api/v1/recommendations' : '/api/v1/properties'},
          {criteriaHash: 'bad'}, {resultCount: 1}, {performed:false},
        ]) {
          const copy = structuredClone(packet);
          Object.assign(copy.evidence.recommendationSearch, patch);
          rejects(copy);
        }
        for (const key of ['recommendationSearch', 'generation', 'criteria']) {
          const copy = structuredClone(packet);
          delete copy.evidence[key];
          rejects(copy);
        }
        if (expected.address) {
          const copy = structuredClone(packet);
          copy.evidence.addressSearchComplete = !copy.evidence.addressSearchComplete;
          rejects(copy);
        }
        const copy = structuredClone(packet);
        copy.evidence.criteria.budgetVnd = 'invalid';
        rejects(copy);
      } else {
        const copy = structuredClone(packet);
        copy.citations[0].url = '/api/v1/properties/private';
        rejects(copy);
      }
    """], cwd=frontend, input=json.dumps({"packet": packet, "expected": expected}).encode(),
        capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr.decode("utf-8", "replace")


@pytest.mark.parametrize(("state", "cards"), [("found", 1), ("empty", 0), ("partial", 0), ("partial_found", 1)])
def test_public_chat_packet_in_production_frontend(search, monkeypatch, state, cards):
    rows = [listing(1, 79)] if state == "found" else []
    if state.startswith("partial"):
        monkeypatch.setattr(tools_module, "NEARBY_MAX_PAGES", 1)
        rows = [listing(i, 80) for i in range(1, 51)] + [listing(51, 79)]
        if cards:
            rows[0]["areaSqm"] = 79
    packet, _ = search(rows, "dưới 80 m²")
    assert_frontend_contract(packet, {
        "address": True, "cards": cards, "empty": state == "empty", "incomplete": state.startswith("partial"),
    })


def test_recommendation_empty_packet_in_production_frontend():
    import test_rag_multiturn as fixtures
    service, _, _, _ = fixtures.MultiTurnTests().service(props=[])
    with TestClient(create_chat_app(Settings(), service)) as client:
        response = client.post("/chat", json={"question": "Tìm căn hộ ở Cẩm Lệ dưới 3 tỷ"})
        assert response.status_code == 200
    packet = response.json()
    assert packet["evidence"]["recommendationSearch"]["sourcePath"] == "/api/v1/recommendations"
    assert_frontend_contract(packet, {"address": False, "cards": 0, "empty": True})
