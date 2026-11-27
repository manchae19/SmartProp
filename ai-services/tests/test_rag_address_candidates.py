"""Exercise both public address routes through FastAPI and the paginated listing client."""
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

    def run(rows, constraint, **criteria):
        calls = []

        def public_backend(outbound):
            assert outbound.url.path == "/api/v1/properties"
            assert "Authorization" not in outbound.headers
            params = outbound.url.params
            if is_nearby:
                assert params.get("bbox")
            else:
                assert params["address"] == ADDRESS
            page, size = int(params["page"]), int(params["size"])
            calls.append(dict(params))
            return httpx.Response(200, json={
                "items": rows[page * size:(page + 1) * size],
                "page": page, "size": size,
                "totalElements": len(rows), "totalPages": (len(rows) + size - 1) // size,
            })

        service, backend = nearby.NearbyAnswerTests().service([])
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
                    "question": f"Tìm nhà {relation} {ADDRESS} {constraint}",
                    **criteria,
                })
                assert response.status_code == 200
                if is_nearby:
                    first = response.json()["evidence"]
                    assert first["clarification"] == "NEAR_ADDRESS_CONSENT"
                    session_id = first["session"]["id"]
                    second = client.post("/chat", json={
                        "question": "Đồng ý tìm vị trí", "sessionId": session_id,
                    })
                    assert second.status_code == 200
                    pick = second.json()["evidence"]
                    assert pick["clarification"] == "NEAR_ADDRESS_PICK"
                    response = client.post("/chat", json={
                        "question": pick["quickReplies"][0], "sessionId": session_id,
                    })
                    assert response.status_code == 200
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
