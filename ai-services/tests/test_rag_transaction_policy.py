"""Public chat transaction policy at the actual property and recommendation entry points."""
import pytest

from test_rag_address_candidates import ADDRESS, listing, property_ids, search
from test_rag_address_semantics import assert_clarification
from test_rag_nearby import ORIGIN


def session_criteria(packet):
    return packet["evidence"]["session"]["context"]["criteria"]


def no_listing_calls(calls, audit):
    assert not audit["recommendations"] and not calls and not audit["geocodes"] and not audit["details"]


def rental_refusal(result, calls, audit):
    assert_clarification(result, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert session_criteria(result)["purpose"] == "RENTAL"
    no_listing_calls(calls, audit)


def test_structured_rent_cannot_run_recommendation(search):
    audit = {}
    result, calls = search([], prompt="Tìm nhà tại Thanh Khê dưới 10 triệu", purpose="RENTAL", audit=audit)
    rental_refusal(result, calls, audit)


def test_session_rent_cannot_run_recommendation(search):
    audit = {}
    result, calls = search([], prompt="Tìm nhà tại Thanh Khê dưới 10 triệu",
                           prior={"purpose": "RENTAL"}, audit=audit)
    rental_refusal(result, calls, audit)


def test_rent_an_apartment_blocks_address_discovery(search):
    audit = {}
    result, calls = search([listing(1, 79, price=9_000_000)],
                           prompt=f"Thuê chung cư {{relation}} {ADDRESS}, dưới 10 triệu",
                           audit=audit, auto_consent=False)
    rental_refusal(result, calls, audit)


@pytest.mark.parametrize("prompt", [
    "Giá mua nhà ở Thanh Khê là bao nhiêu?",
    "Mua nhà ở Thanh Khê giá bao nhiêu?",
    "Tôi muốn biết giá mua nhà ở Thanh Khê",
    "Giá căn hộ ở Thanh Khê hiện nay?",
])
def test_information_about_purchase_keeps_rent(search, prompt):
    audit = {}
    result, calls = search([], prompt=prompt,
                           prior={"purpose": "RENTAL", "budgetVnd": "10000000"}, audit=audit)
    assert result["evidence"]["responseKind"] == "MARKET_PRICE_EVIDENCE"
    assert session_criteria(result)["purpose"] == "RENTAL"
    assert session_criteria(result)["budgetVnd"] == "10000000"
    assert audit["market"] == 1
    no_listing_calls(calls, audit)


def test_inferred_living_does_not_switch_to_buy(search):
    audit = {}
    result, calls = search([], prompt=f"Tìm nhà để ở {{relation}} {ADDRESS}",
                           prior={"purpose": "RENTAL", "budgetVnd": "10000000"}, audit=audit, auto_consent=False)
    rental_refusal(result, calls, audit)


@pytest.mark.parametrize("prompt", [
    f"Thuê căn hộ {{relation}} {ADDRESS} trên 70 và dưới 80 m², giá 10 triệu mỗi tháng",
    f"Thuê biệt thự {{relation}} {ADDRESS}",
    f"Thuê nhà nguyên căn {{relation}} {ADDRESS}",
    f"Cần thuê phòng trọ {{relation}} {ADDRESS}",
    f"Tìm nhà cho thuê {{relation}} {ADDRESS}",
    f"Thuê nhà phố {{relation}} {ADDRESS}",
    f"Thuê mặt bằng {{relation}} {ADDRESS}",
    "Thue chung cu o Thanh Khe duoi 10 trieu",
    f"Tìm nhà {{relation}} {ADDRESS} dưới 100 triệu mỗi năm",
])
def test_explicit_rental_types_and_periodic_prices(search, prompt):
    audit = {}
    result, calls = search([listing(1, 79)], prompt=prompt, audit=audit, auto_consent=False)
    rental_refusal(result, calls, audit)
    assert "budgetVnd" not in session_criteria(result)


@pytest.mark.parametrize("prompt", [
    "Tìm nhà ở quận Thanh Khê",
    "Tìm nhà dưới 10 triệu",
    "Tìm theo ngân sách đã lưu",
    "Trên 70 và dưới 80 m²",
    "Đổi sang quận Hải Châu",
    "Phường Thanh Khê Đông",
    "Căn thứ nhất giá bao nhiêu?",
    f"Nhà {{relation}} {ADDRESS}",
    "Tìm nhà gần chỗ làm",
])
def test_rent_session_blocks_retrieval_and_criteria_followups(search, prompt):
    audit = {}
    result, calls = search(
        [listing(1, 79)], prompt=prompt, prior={"purpose": "RENTAL", "district": "Thanh Khê", "budgetVnd": "10000000"},
        audit=audit, auto_consent=False,
    )
    rental_refusal(result, calls, audit)
    assert session_criteria(result)["budgetVnd"] == "10000000"


@pytest.mark.parametrize(("pending", "prompt"), [
    ({"nearConsentPending": True, "pendingNearbyAddress": ADDRESS, "nearbySaleVerified": True}, "Đồng ý tìm vị trí"),
    ({"nearbyPoints": [{**ORIGIN, "label": ADDRESS}], "nearbyAddress": ADDRESS, "nearbySaleVerified": True}, f"1. {ADDRESS}"),
])
def test_stored_rent_cancels_purchase_pending_without_a_marker(search, pending, prompt):
    audit = {}
    result, calls = search([], prompt=prompt, prior={"purpose": "RENTAL"}, pending=pending, audit=audit, auto_consent=False)
    rental_refusal(result, calls, audit)


def test_stored_rent_blocks_focused_purchase_detail(search):
    audit = {}
    result, calls = search([], prompt="Diện tích bao nhiêu?", prior={"purpose": "RENTAL"},
                           pending={"focusedPropertyId": 1}, audit=audit)
    rental_refusal(result, calls, audit)


def test_guided_rental_selection_blocks_the_next_listing_turn(search):
    audit = {}
    result, calls = search([], prompt="Tư vấn từng bước", followups=["Thuê để ở", "Tìm ngay"], audit=audit)
    assert_clarification(audit["turns"][0], "LIFESTYLE_INTAKE")
    assert "Thuê để ở" in audit["turns"][0]["evidence"]["quickReplies"]
    rental_refusal(audit["turns"][1], calls, audit)
    rental_refusal(result, calls, audit)


@pytest.mark.parametrize("purchase", [
    "Đổi sang mua",
    "Tôi không thuê nữa, muốn mua nhà",
    "Bây giờ tìm nhà bán giúp tôi",
])
def test_switch_requires_new_purchase_budget_and_invalidates_old_consent(search, purchase):
    audit = {}
    result, calls = search([], prompt=purchase, prior={"purpose": "RENTAL", "budgetVnd": "10000000"},
                           pending={"nearConsentPending": True, "pendingNearbyAddress": ADDRESS, "nearbySaleVerified": True},
                           followups=["Đồng ý tìm vị trí"], audit=audit, auto_consent=False)
    assert_clarification(audit["turns"][0], "PURCHASE_BUDGET_REQUIRED")
    assert_clarification(result, "PURCHASE_BUDGET_REQUIRED")
    assert session_criteria(result)["purpose"] == "LIVING"
    assert "budgetVnd" not in session_criteria(result)
    no_listing_calls(calls, audit)


@pytest.mark.parametrize(("prompt", "criteria", "expected_purpose"), [
    ("Tôi không thuê nữa, muốn mua nhà tại Thanh Khê dưới 3 tỷ", {}, "LIVING"),
    ("Tìm nhà tại Thanh Khê", {"purpose": "LIVING", "budgetVnd": 3000000000}, "LIVING"),
    ("Mua để đầu tư khai thác cho thuê nhà riêng ở Thanh Khê dưới 3 tỷ", {}, "INVESTMENT"),
])
def test_explicit_purchase_uses_new_budget_and_public_recommendation(search, prompt, criteria, expected_purpose):
    audit = {}
    result, calls = search([], prompt=prompt, prior={"purpose": "RENTAL", "budgetVnd": "10000000"},
                           audit=audit, empty_recommendations=True, **criteria)
    assert result["evidence"]["responseKind"] == "NO_MATCHES"
    assert audit["recommendations"] == 1 and not calls and not audit["geocodes"]
    assert audit["recommendation_criteria"][0]["budgetVnd"] == "3000000000"
    assert audit["recommendation_criteria"][0]["purpose"] == expected_purpose
    assert session_criteria(result)["purpose"] == expected_purpose


@pytest.mark.parametrize(("prompt", "purpose"), [
    ("Tôi muốn mua nhà tại Thanh Khê dưới 3 tỷ", "RENTAL"),
    ("Tôi muốn thuê nhà tại Thanh Khê dưới 10 triệu", "LIVING"),
    ("Tôi muốn mua hay muốn thuê nhà tại Thanh Khê", "LIVING"),
])
def test_conflicting_transaction_prompts_instead_of_searching(search, prompt, purpose):
    audit = {}
    result, calls = search([], prompt=prompt, purpose=purpose, prior={"purpose": "RENTAL"}, audit=audit, auto_consent=False)
    assert_clarification(result, "TRANSACTION_INTENT_CONFLICT")
    assert session_criteria(result)["purpose"] == "RENTAL"
    no_listing_calls(calls, audit)


def test_sale_to_rent_never_reuses_purchase_search_or_consent(search):
    audit = {}
    result, calls = search(
        [], prompt=f"Nhà {{relation}} {ADDRESS} dưới 3 tỷ", followups=["Đổi sang thuê", "Đồng ý tìm vị trí"],
        audit=audit, auto_consent=False,
    )
    assert_clarification(audit["turns"][1], "RENTAL_BUDGET_NOT_SUPPORTED")
    assert_clarification(result, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert session_criteria(result) == {"purpose": "RENTAL", "propertyType": "ALL"}
    assert not audit["recommendations"] and not audit["geocodes"]
    assert len(calls) == (0 if audit["turns"][0]["evidence"].get("clarification") == "NEAR_ADDRESS_CONSENT" else 1)
