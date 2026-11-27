"""Exercise money and location isolation through the public POST /chat route."""
from concurrent.futures import ThreadPoolExecutor
from threading import Event

import pytest
from fastapi.testclient import TestClient

from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.money import UNITS, parse_budget, recurring_amounts
from test_rag_address_candidates import ADDRESS, assert_frontend_contract, search
from test_rag_commute_matrix_status import Base, cell
from test_rag_transaction_policy import no_listing_calls, session_criteria


def test_review_recurring_shorthand_is_not_purchase_budget(search):
    audit = {}
    result, calls = search([], prompt="Tìm nhà ở Thanh Khê dưới 10tr/tháng", audit=audit)
    assert result["evidence"].get("clarification") == "RENTAL_BUDGET_NOT_SUPPORTED"
    assert session_criteria(result)["purpose"] == "RENTAL"
    no_listing_calls(calls, audit)


def test_review_conditional_price_question_cannot_switch_rent(search):
    audit = {}
    result, calls = search([], prompt="Tôi muốn mua nhà ở Thanh Khê thì giá khoảng bao nhiêu?",
                           prior={"purpose": "RENTAL", "budgetVnd": "10000000"},
                           followups=["Tìm nhà tại Thanh Khê dưới 10 triệu"], audit=audit)
    first = audit["turns"][0]
    assert session_criteria(first) == {"purpose": "RENTAL", "budgetVnd": "10000000"}
    assert first["evidence"]["responseKind"] == "MARKET_PRICE_EVIDENCE"
    assert result["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
    no_listing_calls(calls, audit)


@pytest.mark.parametrize("unit", UNITS)
@pytest.mark.parametrize("period", ["/tháng", "/năm", "/ngày", " theo tháng", " theo năm",
                                    " theo ngày", " mỗi tháng", " một tháng", " hàng tháng"])
def test_every_budget_unit_shares_periodic_recognition(unit, period):
    amount = f"10{unit}{period}"
    assert len(list(recurring_amounts(amount))) == 1
    assert parse_budget(amount).maximum is None
    assert parse_budget(f"Ngân sách mua 3 tỷ, doanh thu {amount}").maximum == 3_000_000_000


@pytest.mark.parametrize("amount", [
    "dưới 10tr/tháng", "dưới 10 tr/tháng", "10 triệu mỗi tháng", "800k/ngày",
    "120tr/năm", "10.000.000đ/tháng", "10,5tr/tháng", "8–10tr/tháng",
    "8tr - 10tr/tháng", "1 tỷ 200 tr/năm", "duoi 10tr moi thang",
])
@pytest.mark.parametrize("target", ["ở Thanh Khê", f"{{relation}} {ADDRESS}"])
def test_recurring_budget_is_never_used_for_any_purchase_search(search, amount, target):
    audit = {}
    result, calls = search([], prompt=f"Tìm nhà {target} {amount}", audit=audit, auto_consent=False)
    assert result["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
    assert session_criteria(result)["purpose"] == "RENTAL"
    assert "budgetVnd" not in session_criteria(result)
    no_listing_calls(calls, audit)


@pytest.mark.parametrize(("purpose", "saved", "clarification", "expected_budget"), [
    ("LIVING", {"purpose": "LIVING", "budgetVnd": "3000000000"}, "TRANSACTION_INTENT_CONFLICT", "3000000000"),
    (None, {"purpose": "RENTAL", "budgetVnd": "9000000"}, "RENTAL_BUDGET_NOT_SUPPORTED", "9000000"),
    (None, {"purpose": "LIVING", "budgetVnd": "3000000000"}, "RENTAL_BUDGET_NOT_SUPPORTED", None),
])
def test_recurring_budget_blocks_structured_and_saved_purchase(search, purpose, saved, clarification, expected_budget):
    audit = {}
    structured = {"purpose": purpose, "budgetVnd": 4_000_000_000} if purpose else {}
    result, calls = search([], prompt=f"Tìm nhà {{relation}} {ADDRESS} dưới 10tr/tháng",
                           prior=saved, audit=audit, auto_consent=False, **structured)
    assert result["evidence"]["clarification"] == clarification
    assert session_criteria(result).get("budgetVnd") == expected_budget
    assert session_criteria(result)["purpose"] == (purpose or "RENTAL")
    no_listing_calls(calls, audit)


@pytest.mark.parametrize(("prompt", "clarification"), [
    ("Tôi muốn mua nhà thì giá khoảng bao nhiêu?", None),
    ("Tôi muốn mua chung cư thì giá tầm bao nhiêu?", None),
    ("Nếu mua nhà ở Thanh Khê thì cần bao nhiêu tiền?", None),
    ("Giá mua nhà tại Thanh Khê là bao nhiêu?", None),
    ("Mua nhà ở Thanh Khê giá khoảng bao nhiêu?", None),
    ("So sánh giá mua và thuê", "MARKET_SCOPE"),
    ("Doanh thu cho thuê nhà ở Thanh Khê có thể đạt 10tr/tháng không?", "RENTAL_INCOME_INFORMATION"),
])
@pytest.mark.parametrize("prior", [
    None, {"purpose": "RENTAL", "budgetVnd": "10000000"}, {"purpose": "LIVING", "budgetVnd": "3000000000"},
])
def test_transaction_information_preserves_session_and_skips_listing_tools(search, prompt, clarification, prior):
    audit = {}
    pending = {"nearConsentPending": True, "pendingNearbyAddress": ADDRESS, "nearbySaleVerified": True} if prior else None
    result, calls = search([], prompt=prompt, prior=prior, pending=pending, audit=audit, auto_consent=False)
    assert session_criteria(result) == (prior or {})
    if clarification:
        assert result["evidence"]["clarification"] == clarification
        assert audit["market"] == 0
    else:
        assert result["evidence"]["responseKind"] == "MARKET_PRICE_EVIDENCE"
        assert audit["market"] == 1
    no_listing_calls(calls, audit)


def test_purchase_price_inquiry_overrides_prior_rental_market_scope_only(search):
    audit = {}
    prior = {"purpose": "RENTAL", "budgetVnd": "10000000"}
    result, calls = search([], prompt="Giá thuê nhà ở Thanh Khê là bao nhiêu?",
                           followups=["Nếu mua nhà ở Thanh Khê thì cần bao nhiêu tiền?"],
                           prior=prior, audit=audit, auto_consent=False)
    assert audit["turns"][0]["evidence"]["clarification"] == "MARKET_SCOPE"
    assert result["evidence"]["responseKind"] == "MARKET_PRICE_EVIDENCE"
    assert session_criteria(result) == prior
    assert audit["market"] == 1
    no_listing_calls(calls, audit)


@pytest.mark.parametrize("prompt", [
    "Tôi không muốn mua nhà ở 300 Dũng Sĩ Thanh Khê.",
    "Tôi chưa muốn mua.",
    "Tôi muốn mua hay thuê nhà ở 300 Dũng Sĩ Thanh Khê?",
    "Nếu mua nhà ở 300 Dũng Sĩ Thanh Khê thì sao?",
])
@pytest.mark.parametrize("prior", [None, {"purpose": "RENTAL"}, {"purpose": "LIVING", "budgetVnd": "3000000000"}])
def test_negation_and_ambiguity_cannot_authorize_purchase(search, prompt, prior):
    audit = {}
    result, calls = search([], prompt=prompt, prior=prior, audit=audit, auto_consent=False)
    clarification = "TRANSACTION_INTENT_CONFLICT" if "hay" in prompt or prompt.startswith("Nếu") else "PURCHASE_DECLINED"
    assert result["evidence"]["clarification"] == clarification
    assert session_criteria(result) == (prior or {})
    no_listing_calls(calls, audit)


@pytest.mark.parametrize(("prompt", "purpose", "clarification"), [
    ("Mua nhà cho thuê ở Thanh Khê, ngân sách 3 tỷ", "INVESTMENT", None),
    ("Mua nhà để đầu tư khai thác cho thuê ở Thanh Khê dưới 3 tỷ", "INVESTMENT", None),
    ("Mua nhà để cho thuê, doanh thu kỳ vọng 10tr/tháng, ngân sách mua 3 tỷ", "INVESTMENT", None),
    ("Mua nhà để cho thuê, doanh thu kỳ vọng 10tr/tháng", "INVESTMENT", "PURCHASE_BUDGET_REQUIRED"),
    ("Mua nhà ở Thanh Khê dưới 10tr/tháng", "RENTAL", "TRANSACTION_INTENT_CONFLICT"),
    ("Tôi không thuê nữa, muốn mua", "LIVING", "PURCHASE_BUDGET_REQUIRED"),
    ("Tìm nhà bán với ngân sách 3 tỷ ở Thanh Khê", "LIVING", None),
])
def test_sale_switches_and_buy_to_let_require_a_total_purchase_budget(search, prompt, purpose, clarification):
    audit = {}
    result, calls = search([], prompt=prompt, prior={"purpose": "RENTAL", "budgetVnd": "10000000"},
                           audit=audit, empty_recommendations=True, auto_consent=False)
    assert session_criteria(result)["purpose"] == purpose
    if clarification:
        assert result["evidence"]["clarification"] == clarification
        assert session_criteria(result).get("budgetVnd") != "10000000" or purpose == "RENTAL"
        no_listing_calls(calls, audit)
    else:
        assert result["evidence"]["responseKind"] == "NO_MATCHES"
        assert audit["recommendations"] == 1
        assert audit["recommendation_criteria"][0]["budgetVnd"] == "3000000000"
        assert audit["recommendation_criteria"][0]["purpose"] == purpose
        assert not calls and not audit["geocodes"]


WORK_SEARCH = "Tìm nhà gần chỗ làm ở Thanh Khê dưới 3 tỷ"
WORK_ADDRESS = "123 Nguyễn Văn Linh, Hải Châu, Đà Nẵng"


@pytest.fixture
def workplace_chat():
    service, backend = Base().service([cell("a", 600)], names="a")
    with TestClient(create_chat_app(Settings(), service)) as client:
        def ask(question, prior=None, **criteria):
            if prior:
                criteria["sessionId"] = prior["evidence"]["session"]["id"]
            response = client.post("/chat", json={"question": question, **criteria})
            assert response.status_code == 200
            return response.json()
        yield ask, backend


def confirm_workplace(ask, pending):
    prompt = ask("Nhập địa điểm khác", pending)
    assert prompt["evidence"]["clarification"] == "COMMUTE_ADDRESS_CONSENT"
    return ask(WORK_ADDRESS, prompt)


def test_review_confirmed_workplace_requires_new_consent_after_switch(workplace_chat):
    ask, backend = workplace_chat
    initial = ask(WORK_SEARCH)
    assert initial["evidence"]["clarification"] == "COMMUTE_DESTINATION_REQUIRED"
    confirmed = confirm_workplace(ask, initial)
    backend.geocode_workplace.assert_called_once_with(WORK_ADDRESS)
    backend.commute_matrix.assert_called_once()
    backend.reset_mock()
    rent = ask("Đổi sang thuê", confirmed)
    assert rent["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
    buy = ask("Đổi sang mua", rent)
    assert buy["evidence"]["clarification"] == "PURCHASE_BUDGET_REQUIRED"
    retry = ask(WORK_SEARCH, buy)
    assert retry["evidence"].get("clarification") == "COMMUTE_DESTINATION_REQUIRED"
    backend.geocode_workplace.assert_not_called()
    backend.commute_matrix.assert_not_called()
    backend.recommend.assert_not_called()
    confirm_workplace(ask, retry)
    backend.geocode_workplace.assert_called_once_with(WORK_ADDRESS)
    backend.commute_matrix.assert_called_once()
    backend.recommend.assert_called_once()


@pytest.mark.parametrize("location_state", ["awaiting_address", "awaiting_candidate", "confirmed"])
def test_stale_workplace_replies_cannot_restore_old_location(workplace_chat, location_state):
    ask, backend = workplace_chat
    first = ask(WORK_SEARCH)
    pending = ask("Nhập địa điểm khác", first)
    if location_state == "awaiting_candidate":
        backend.geocode_workplace.return_value *= 2
        pending = ask(WORK_ADDRESS, pending)
        assert pending["evidence"]["clarification"] == "COMMUTE_PICK_CANDIDATE"
    elif location_state == "confirmed":
        pending = ask(WORK_ADDRESS, pending)
        backend.commute_matrix.assert_called_once()
    backend.reset_mock()
    rent = ask("Đổi sang thuê", pending)
    stale = ask("1. Công ty" if location_state != "awaiting_address" else WORK_ADDRESS, rent)
    assert session_criteria(stale)["purpose"] == "RENTAL"
    buy = ask("Đổi sang mua", stale)
    stale = ask("Đồng ý", buy)
    assert stale["evidence"]["clarification"] == "PURCHASE_BUDGET_REQUIRED"
    ask("Ngân sách 3 tỷ", stale)
    ask("1. Công ty", stale)
    backend.geocode_workplace.assert_not_called()
    backend.commute_matrix.assert_not_called()
    backend.recommend.assert_not_called()


def test_same_transaction_and_different_session_workplace_contract(workplace_chat):
    ask, backend = workplace_chat
    original = confirm_workplace(ask, ask(WORK_SEARCH))
    backend.reset_mock()
    same = ask(WORK_SEARCH, original)
    assert same["recommendedProperties"]
    backend.geocode_workplace.assert_not_called()
    backend.commute_matrix.assert_called_once()
    backend.reset_mock()
    other = ask(WORK_SEARCH)
    assert other["evidence"]["clarification"] == "COMMUTE_DESTINATION_REQUIRED"
    assert other["evidence"]["session"]["id"] != original["evidence"]["session"]["id"]
    backend.geocode_workplace.assert_not_called()
    backend.commute_matrix.assert_not_called()
    backend.recommend.assert_not_called()


def test_inflight_geocoder_cannot_restore_location_after_public_transaction_switch():
    service, backend = Base().service([cell("a", 600)], names="a")
    provider_started, finish_geocode = Event(), Event()

    def slow_geocode(address):
        assert address == WORK_ADDRESS
        provider_started.set()
        assert finish_geocode.wait(5)
        return backend.geocode_workplace.return_value

    backend.geocode_workplace.side_effect = slow_geocode
    with TestClient(create_chat_app(Settings(), service)) as client, ThreadPoolExecutor() as worker:
        initial = client.post("/chat", json={"question": WORK_SEARCH}).json()
        sid = initial["evidence"]["session"]["id"]

        def post(question):
            return client.post("/chat", json={"question": question, "sessionId": sid})

        assert post("Nhập địa điểm khác").json()["evidence"]["clarification"] == "COMMUTE_ADDRESS_CONSENT"
        previous = worker.submit(post, WORK_ADDRESS)
        try:
            assert provider_started.wait(5)
            concurrent = post("Đổi sang thuê")
            assert concurrent.status_code == 429
        finally:
            finish_geocode.set()
        assert previous.result(5).status_code == 200
        backend.reset_mock()
        assert post("Đổi sang thuê").json()["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
        assert post("Đổi sang mua").json()["evidence"]["clarification"] == "PURCHASE_BUDGET_REQUIRED"
        assert post(WORK_SEARCH).json()["evidence"]["clarification"] == "COMMUTE_DESTINATION_REQUIRED"
        backend.geocode_workplace.assert_not_called()
        backend.commute_matrix.assert_not_called()
        backend.recommend.assert_not_called()


@pytest.mark.parametrize("search", ["nearby"], indirect=True)
def test_nearby_consent_from_an_old_transaction_cannot_open_discovery(search):
    audit = {}
    result, calls = search([], prompt=f"Tìm nhà gần {ADDRESS} dưới 3 tỷ",
                           followups=["Đổi sang thuê", "Đồng ý tìm vị trí", "Đổi sang mua",
                                      "Ngân sách 3 tỷ", "Đồng ý tìm vị trí", f"1. {ADDRESS}",
                                      f"Tìm nhà gần {ADDRESS} dưới 3 tỷ"],
                           auto_consent=False, audit=audit)
    assert audit["turns"][0]["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
    assert audit["turns"][2]["evidence"]["clarification"] == "RENTAL_BUDGET_NOT_SUPPORTED"
    assert result["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
    no_listing_calls(calls, audit)


@pytest.mark.parametrize(("prompt", "code", "purpose", "budget"), [
    ("Tôi chưa muốn mua.", "PURCHASE_DECLINED", "RENTAL", "10000000"),
    ("So sánh giá mua và thuê.", "MARKET_SCOPE", "RENTAL", "10000000"),
    ("Doanh thu cho thuê là bao nhiêu?", "RENTAL_INCOME_INFORMATION", "RENTAL", "10000000"),
    ("Mua nhà cho thuê, doanh thu 10tr/tháng", "PURCHASE_BUDGET_REQUIRED", "INVESTMENT", None),
])
def test_transaction_clarifications_use_production_frontend(search, prompt, code, purpose, budget):
    packet, _ = search([], prompt=prompt, prior={"purpose": "RENTAL", "budgetVnd": "10000000"})
    expected = {"cards": 0, "empty": False, "clarification": code, "purpose": purpose}
    if budget is not None:
        expected["budget"] = budget
    assert_frontend_contract(packet, expected)
