"""Mandatory address criteria and transaction state, through POST /chat."""
import unicodedata

import pytest

from test_rag_address_candidates import ADDRESS, listing, property_ids, search
from test_rag_nearby import ORIGIN


def assert_clarification(packet, code):
    assert packet["evidence"]["responseKind"] == "CLARIFICATION_REQUIRED"
    assert packet["evidence"]["clarification"] == code
    assert not property_ids(packet)


@pytest.mark.parametrize("prompt", [
    f"Thuê nhà {{relation}} {ADDRESS}, dưới 10 triệu",
    f"Tôi muốn thuê nhà {{relation}} {ADDRESS} dưới 10 triệu",
    f"Tôi thuê nhà {{relation}} {ADDRESS}",
    f"Tìm bất động sản cho thuê {{relation}} {ADDRESS}",
    f"Nhà cho thuê {{relation}} {ADDRESS}",
    "Giá thuê dưới 10 triệu",
    "Thuê dưới 10 triệu mỗi tháng",
])
def test_rental_never_searches_or_prompts_for_consent(search, prompt):
    audit = {}
    packet, calls = search([listing(1, 79, price=9_000_000)], prompt=prompt, audit=audit, auto_consent=False)
    assert_clarification(packet, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert packet["evidence"]["session"]["context"]["criteria"] == {"purpose": "RENTAL"}
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


@pytest.mark.parametrize("pending,followup", [
    ({"nearConsentPending": True, "pendingNearbyAddress": ADDRESS}, "Đồng ý tìm vị trí"),
    ({"nearbyPoints": [{**ORIGIN, "label": ADDRESS}], "nearbyAddress": ADDRESS}, f"1. {ADDRESS}"),
])
@pytest.mark.parametrize(("purpose", "clarification"), [
    ("RENTAL", "RENTAL_BUDGET_NOT_SUPPORTED"),
    ("LIVING", "NEAR_ADDRESS_RESTART"),
])
def test_pending_stages_need_a_verified_purchase(search, pending, followup, purpose, clarification):
    audit = {}
    packet, calls = search([listing(1, 79)], prompt=followup, prior={"purpose": purpose},
                           pending=pending, audit=audit, auto_consent=False)
    assert_clarification(packet, clarification)
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


def test_rejected_rental_cannot_resume_at_consent_or_pick(search):
    audit = {}
    _, calls = search([listing(1, 79)], prompt=f"Tìm bất động sản cho thuê {{relation}} {ADDRESS}",
                      followups=["Đồng ý tìm vị trí", f"1. {ADDRESS}", "Tìm ngay"],
                      audit=audit, auto_consent=False)
    for packet in audit["turns"]:
        assert_clarification(packet, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


def test_stored_rental_purpose_applies_to_a_neutral_address_request(search):
    audit = {}
    packet, calls = search([listing(1, 79)], prompt=f"Nhà {{relation}} {ADDRESS}",
                           prior={"purpose": "RENTAL"}, audit=audit, auto_consent=False)
    assert_clarification(packet, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


def test_request_purpose_rental_applies_to_a_neutral_address_request(search):
    audit = {}
    packet, calls = search([listing(1, 79)], prompt=f"Nhà {{relation}} {ADDRESS}",
                           purpose="RENTAL", audit=audit, auto_consent=False)
    assert_clarification(packet, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


def test_purchase_can_switch_to_rental(search):
    audit = {}
    packet, calls = search([listing(1, 79)], constraint="dưới 80 m²", followups=["Đổi sang thuê"],
                           audit=audit)
    assert audit["turns"][0 if not audit["geocodes"] else 2]["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert_clarification(packet, "RENTAL_BUDGET_NOT_SUPPORTED")
    assert len(calls) == 1 and calls[0]["transactionType"] == "SALE"
    assert len(audit["geocodes"]) <= 1 and not audit["recommendations"]


@pytest.mark.parametrize("prefix", ["Tìm mua nhà", "Không thuê, tôi muốn mua nhà", "Mua nhà để cho thuê"])
def test_explicit_purchase_overrides_rental_state(search, prefix):
    audit = {}
    row = listing(1, 79)
    packet, calls = search([row], prompt=f"{prefix} {{relation}} {ADDRESS}, dưới 3 tỷ",
                           prior={"purpose": "RENTAL"}, audit=audit)
    assert packet["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert property_ids(packet) == [row["id"]]
    assert len(calls) == 1 and calls[0]["transactionType"] == "SALE" and calls[0]["maxPrice"] == "3000000000"
    assert packet["evidence"]["session"]["context"]["criteria"]["purpose"] == "LIVING"
    assert not audit["recommendations"]


@pytest.mark.parametrize("search", ["nearby"], indirect=True)
def test_rental_to_purchase_restores_fresh_nearby_consent(search):
    audit = {}
    row = listing(1, 79)
    packet, calls = search(
        [row], prompt=f"Nhà cho thuê {{relation}} {ADDRESS} dưới 10 triệu",
        prior={"purpose": "RENTAL", "budgetVnd": "10000000"},
        followups=["Đổi sang mua", f"Nhà gần {ADDRESS} thuộc phường Thanh Khê Tây trên 70 và dưới 80 m²",
                   "Đồng ý tìm vị trí", f"1. {ADDRESS}"],
        audit=audit, auto_consent=False,
    )
    assert_clarification(audit["turns"][0], "RENTAL_BUDGET_NOT_SUPPORTED")
    assert audit["turns"][1]["evidence"]["responseKind"] == "CRITERIA_UPDATED"
    assert_clarification(audit["turns"][2], "NEAR_ADDRESS_CONSENT")
    assert_clarification(audit["turns"][3], "NEAR_ADDRESS_PICK")
    assert property_ids(packet) == [row["id"]]
    assert packet["evidence"]["session"]["context"]["criteria"]["ward"] == "Thanh Khê Tây"
    assert len(calls) == 1 and calls[0]["transactionType"] == "SALE"
    assert "maxPrice" not in calls[0]
    assert (calls[0]["minArea"], calls[0]["maxArea"]) == ("70", "80")
    assert audit["geocodes"] == [ADDRESS] and not audit["recommendations"]



@pytest.mark.parametrize(("constraint", "criteria"), [
    ("dưới 80 và trên 90 m²", {}),
    ("trên 90 và dưới 80 m²", {}),
    ("trên 80 và tối đa 80 m²", {}),
    ("dưới 80 hoặc trên 90 m²", {}),
    ("dưới 80 và 90 m²", {}),
    ("dưới 80.123 và trên 70 m²", {}),
    ("ngân sách dưới 80 và trên 70 m²", {}),
    ("dưới 80 và trên 90 m²", {"minAreaSqm": 70}),
    ("dưới 80 m²", {"minAreaSqm": 80}),
])
def test_invalid_area_preserves_prior_but_never_uses_it_for_retrieval(search, constraint, criteria):
    audit = {}
    packet, calls = search([listing(1, 79)], constraint, prior={"minAreaSqm": "69", "purpose": "LIVING"},
                           audit=audit, auto_consent=False, **criteria)
    assert_clarification(packet, "AREA_RANGE_INVALID")
    assert packet["evidence"]["session"]["context"]["criteria"]["minAreaSqm"] == "69"
    assert not calls and not audit["recommendations"] and not audit["geocodes"]


@pytest.mark.parametrize(("clause", "bounds", "areas"), [
    ("trên 70 và dưới 80 m²", ("70", "80", True, True), [70.5, 79, 79.5]),
    ("dưới 80 và trên 70 m2", ("70", "80", True, True), [70.5, 79, 79.5]),
    ("tối thiểu 70 và tối đa 80 mét vuông", ("70", "80", False, False), [70, 70.5, 79]),
    ("tu 70 den 80 m2", ("70", "80", False, False), [70, 70.5, 79]),
    ("trên 70 m² và dưới 80 m²", ("70", "80", True, True), [70.5, 79, 79.5]),
    ("tối thiểu 70, trên 70 và tối đa 79,5 m²", ("70", "79.5", True, False), [70.5, 79, 79.5]),
])
def test_shared_unit_and_other_filters(search, clause, bounds, areas):
    audit = {}
    rows = [listing(i, area) for i, area in enumerate((69, 70, 70.5, 79, 79.5, 80, 90, 95), 1)]
    rows += [listing(20, 79, meters=1, price=3_100_000_000), listing(21, 79, meters=1, district="Hải Châu")]
    prompt = f"Tìm mua nhà {{relation}} {ADDRESS} thuộc quận Thanh Khê {clause}, ngân sách 3 tỷ, 2 phòng, hẻm 5m"
    packet, calls = search(rows, prompt=prompt, audit=audit)
    assert packet["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert [p["areaSqm"] for p in packet["recommendedProperties"]] == areas
    low, high, strict_low, strict_high = bounds
    assert len(calls) == 1
    params = calls[0]
    assert (params["minArea"], params["maxArea"], params["maxPrice"]) == (low, high, "3000000000")
    assert (params.get("minAreaExclusive") == "true", params.get("maxAreaExclusive") == "true") == (strict_low, strict_high)
    assert params["transactionType"] == "SALE" and not audit["recommendations"]
    criteria = packet["evidence"]["session"]["context"]["criteria"]
    assert criteria["district"] == "Thanh Khê"
    assert (criteria["minAreaSqm"], criteria["maxAreaSqm"]) == (low, high)


def test_compatible_structured_and_text_bounds_intersect(search):
    rows = [listing(1, 70), listing(2, 79.5), listing(3, 80), listing(4, 81)]
    packet, calls = search(rows, "trên 70 và dưới 81 m²", maxAreaSqm=80)
    assert packet["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert property_ids(packet) == [rows[1]["id"], rows[2]["id"]]
    assert calls[0]["maxArea"] == "80" and "maxAreaExclusive" not in calls[0]
    assert calls[0]["minArea"] == "70" and calls[0]["minAreaExclusive"] == "true"


@pytest.mark.parametrize(("boundary", "label", "expected"), [
    (" thuộc quận Thanh Khê", ADDRESS, {"district": "Thanh Khê"}),
    (", thuộc huyện Thanh Khê", ADDRESS, {"district": "Thanh Khê"}),
    (" thuoc phuong Thanh Khe Tay", "300 Dung Si Thanh Khe", {"ward": "Thanh Khê Tây"}),
    (" thuộc xã Thanh Khê Tây", ADDRESS, {"ward": "Thanh Khê Tây"}),
    (", nằm trong quận Thanh Khê dưới 80 m²", ADDRESS, {"district": "Thanh Khê", "maxAreaSqm": "80"}),
    (" chỉ thuộc quận Thanh Khê", "300 Hoàng Phương Dung", {"district": "Thanh Khê"}),
    (" chỉ ở quận Thanh Khê", ADDRESS, {"district": "Thanh Khê"}),
])
def test_location_boundaries_preserve_exact_street(search, boundary, label, expected):
    audit = {}
    row = listing(1, 79, address=label)
    prompt = f"Tìm nhà {{relation}} {unicodedata.normalize('NFD', label)}{boundary}"
    packet, calls = search([row], prompt=prompt, expected_address=label, audit=audit)
    assert packet["evidence"]["responseKind"] == "PROPERTY_LIST"
    assert property_ids(packet) == [row["id"]]
    assert len(calls) == 1 and (audit["geocodes"] == [label] if "bbox" in calls[0] else calls[0]["address"] == label)
    assert expected.items() <= packet["evidence"]["session"]["context"]["criteria"].items()


def test_conflicting_geography_at_new_address_has_no_side_effects(search):
    audit = {}
    packet, calls = search([listing(1, 79)], "thuộc quận Hải Châu phường Thanh Khê Tây",
                           audit=audit, auto_consent=False)
    assert_clarification(packet, "LISTING_LOCALITY_UNRESOLVED")
    assert not calls and not audit["recommendations"] and not audit["geocodes"]
