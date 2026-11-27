"""A saved purchase budget never authorizes an unrelated current turn."""
import pytest
from fastapi.testclient import TestClient
import test_rag_multiturn as fixtures

from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.money import parse_budget, recurring_amounts
from test_rag_address_candidates import ADDRESS, assert_frontend_contract
from test_rag_transaction_policy import session_criteria


SALE_START = "Tìm mua nhà ở Thanh Khê, ngân sách 3 tỷ"
SALE_CRITERIA = {"purpose": "LIVING", "budgetVnd": "3000000000", "district": "Thanh Khê"}
UPSTREAM = ("recommend", "search_by_address", "search_nearby", "property_detail",
            "geocode_workplace", "commute", "commute_matrix")


@pytest.fixture
def chat():
    service, backend, _, _ = fixtures.MultiTurnTests().service(props=[fixtures.prop("property:a", 2_000_000_000, 90)])
    with TestClient(create_chat_app(Settings(), service)) as client:
        def ask(question, prior=None, **criteria):
            if prior:
                criteria["sessionId"] = prior["evidence"]["session"]["id"]
            response = client.post("/chat", json={"question": question, **criteria})
            assert response.status_code == 200, response.text
            return response.json()
        yield ask, service, backend


def listing_calls(backend):
    return {name: getattr(backend, name).call_count for name in UPSTREAM if getattr(backend, name).called}


def start_sale(ask, backend):
    first = ask(SALE_START)
    assert SALE_CRITERIA.items() <= session_criteria(first).items()
    backend.recommend.assert_called_once()
    assert first["recommendedProperties"]
    backend.reset_mock()
    return first


def assert_blocked(result, backend, code):
    assert result["evidence"]["responseKind"] == "CLARIFICATION_REQUIRED"
    assert result["evidence"]["clarification"] == code
    assert result["recommendedProperties"] == []
    assert listing_calls(backend) == {}


@pytest.mark.parametrize(("question", "code"), [
    ("Tôi không muốn tìm mua nhà ở Thanh Khê nữa.", "PURCHASE_DECLINED"),
    ("Nếu tôi muốn mua nhà ở Thanh Khê thì sao?", "TRANSACTION_INTENT_CONFLICT"),
    ("Tìm nhà ở Thanh Khê dưới 10.000.000/tháng", "RECURRING_AMOUNT_CLARIFICATION"),
])
def test_exact_review_blockers(chat, question, code):
    ask, _, backend = chat
    first = start_sale(ask, backend)
    result = ask(question, first)
    calls = listing_calls(backend)
    assert not calls, (
        calls, backend.recommend.call_args.args[0].get("budgetVnd") if backend.recommend.called else None,
        [card["id"] for card in result["recommendedProperties"]],
    )
    assert_blocked(result, backend, code)
    assert session_criteria(result) == session_criteria(first)


@pytest.mark.parametrize(("question", "purpose", "code"), [
    ("Không muốn mua.", None, "PURCHASE_DECLINED"),
    ("Khong muon tim mua nha.", "LIVING", "PURCHASE_DECLINED"),
    ("Không cần tìm mua nữa.", "LIVING", "PURCHASE_DECLINED"),
    ("Tôi không muốn tìm nhà bán ở Thanh Khê.", "LIVING", "PURCHASE_DECLINED"),
    ("Tôi không muốn tìm nhà ở Thanh Khê nữa.", "LIVING", "PURCHASE_DECLINED"),
    ("Chưa muốn tìm mua.", "RENTAL", "PURCHASE_DECLINED"),
    ("Nếu tôi mua thì sao?", None, "TRANSACTION_INTENT_CONFLICT"),
    ("Neu toi muon mua nha thi sao?", "LIVING", "TRANSACTION_INTENT_CONFLICT"),
    ("Nếu tôi muốn tìm mua nhà thì cần làm gì?", "RENTAL", "TRANSACTION_INTENT_CONFLICT"),
    ("Giả sử tôi muốn mua nhà thì sao?", "LIVING", "TRANSACTION_INTENT_CONFLICT"),
    ("Giả sử tôi muốn tìm nhà bán thì sao?", "LIVING", "TRANSACTION_INTENT_CONFLICT"),
    ("Tôi không muốn thuê nhà ở Thanh Khê.", "LIVING", "RENT_DECLINED"),
])
def test_non_affirmative_preserves_saved_criteria(chat, question, purpose, code):
    ask, _, backend = chat
    prior = None
    if purpose == "LIVING":
        prior = start_sale(ask, backend)
    elif purpose == "RENTAL":
        prior = ask("Tìm nhà cho thuê ở Thanh Khê dưới 10 triệu/tháng")
    result = ask(question, prior)
    assert_blocked(result, backend, code)
    assert session_criteria(result) == (session_criteria(prior) if prior else {})


@pytest.mark.parametrize(("target", "purpose"), [
    (f"ở {ADDRESS}", "LIVING"), (f"gần {ADDRESS}", "RENTAL"), ("gần chỗ làm", "LIVING"),
])
def test_decline_blocks_all_discovery_paths_despite_structured_purpose(chat, target, purpose):
    ask, _, backend = chat
    prior = start_sale(ask, backend)
    focus = {"propertyId": "11111111-1111-1111-1111-111111111111"} if target == "gần chỗ làm" else {}
    result = ask(f"Tôi không muốn tìm mua nhà {target} nữa", prior, purpose=purpose, **focus)
    assert_blocked(result, backend, "PURCHASE_DECLINED")
    assert session_criteria(result) == session_criteria(prior)


@pytest.mark.parametrize("declined", [True, False])
def test_decline_cancels_pending_purchase_consent_but_hypothetical_preserves_it(chat, declined):
    ask, _, backend = chat
    backend.geocode_workplace.return_value = [{"label": ADDRESS, "latitude": 16.06, "longitude": 108.22}]
    first = start_sale(ask, backend)
    pending = ask(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", first)
    assert pending["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
    if declined:
        result = ask("Tôi không muốn tìm mua nữa.", pending)
        assert_blocked(result, backend, "PURCHASE_DECLINED")
        followup = ask("Đồng ý tìm vị trí", result)
        assert listing_calls(backend) == {}
        assert followup["recommendedProperties"] == []
        assert ask(f"Tìm nhà gần {ADDRESS}", result)["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
    else:
        result = ask("Nếu tôi muốn tìm mua nhà thì sao?", pending)
        assert_blocked(result, backend, "TRANSACTION_INTENT_CONFLICT")
        assert ask("Đồng ý tìm vị trí", result)["evidence"]["clarification"] == "NEAR_ADDRESS_PICK"
        assert listing_calls(backend) == {"geocode_workplace": 1}
    assert session_criteria(result) == session_criteria(pending)


@pytest.mark.parametrize(("question", "rent_first", "purchase_purpose"), [
    ("Tôi không thuê nữa, muốn mua nhà tại Thanh Khê dưới 3 tỷ.", True, "LIVING"),
    ("Tôi không muốn thuê, tôi muốn mua nhà tại Thanh Khê dưới 3 tỷ.", True, "LIVING"),
    ("Tôi không muốn mua, hãy tìm nhà thuê.", False, "RENTAL"),
    (SALE_START, False, "LIVING"),
    ("Mua nhà để cho thuê ở Thanh Khê dưới 3 tỷ.", False, "INVESTMENT"),
    ("Mua nhà cho thuê ở Thanh Khê dưới 3 tỷ.", False, "INVESTMENT"),
])
def test_affirmative_clause_can_switch_without_using_negated_clause(chat, question, rent_first, purchase_purpose):
    ask, _, backend = chat
    first = ask("Đổi sang thuê") if rent_first else start_sale(ask, backend)
    result = ask(question, first)
    assert session_criteria(result)["purpose"] == purchase_purpose
    if purchase_purpose == "RENTAL":
        assert_blocked(result, backend, "RENTAL_BUDGET_NOT_SUPPORTED")
        assert "budgetVnd" not in session_criteria(result)
    else:
        assert listing_calls(backend) == {"recommend": 1}
        assert result["recommendedProperties"]
        assert backend.recommend.call_args.args[0]["budgetVnd"] == "3000000000"


@pytest.mark.parametrize(("question", "expected"), [
    ("Còn ở Sơn Trà?", {"district": "Sơn Trà", "budgetVnd": "3000000000"}),
    ("Diện tích từ 80 đến 100 m².", {"minAreaSqm": "80", "maxAreaSqm": "100"}),
    ("Giảm ngân sách xuống 2 tỷ.", {"district": "Thanh Khê", "budgetVnd": "2000000000"}),
    ("Xem thêm căn khác.", {"district": "Thanh Khê", "budgetVnd": "3000000000"}),
])
def test_valid_stored_purchase_followups_keep_working(chat, question, expected):
    ask, _, backend = chat
    first = start_sale(ask, backend)
    result = ask(question, first)
    actual = {key: str(value) for key, value in session_criteria(result).items()}
    assert expected.items() <= actual.items()
    assert listing_calls(backend) == {"recommend": 1}
    assert result["recommendedProperties"]


@pytest.mark.parametrize(("amount", "prior"), [
    ("10.000.000/tháng", "SALE"), ("10000000/tháng", None), ("10 000 000/tháng", "RENT"),
    ("10,000,000/tháng", "SALE"), ("800000/ngày", None), ("120000000/năm", "SALE"),
    ("10.000.000 mỗi tháng", "SALE"), ("10.000.000 một tháng", None),
    ("10.000.000 theo tháng", "RENT"), ("8.000.000–10.000.000/tháng", "SALE"),
    ("800000 den 1000000/ngay", None), ("10 000 000 mỗi tháng", "SALE"),
])
def test_numeric_recurring_never_uses_saved_purchase_amount(chat, amount, prior):
    ask, _, backend = chat
    first = start_sale(ask, backend) if prior == "SALE" else ask("Đổi sang thuê") if prior == "RENT" else None
    result = ask(f"Tìm nhà ở Thanh Khê dưới {amount}", first)
    assert_blocked(result, backend, "RECURRING_AMOUNT_CLARIFICATION")
    assert session_criteria(result) == (session_criteria(first) if first else {})


@pytest.mark.parametrize(("question", "fields", "code"), [
    ("Tìm nhà ở Thanh Khê dưới 10000000/tháng", {"purpose": "LIVING", "budgetVnd": 3_000_000_000},
     "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm mua nhà ở Thanh Khê dưới 10.000.000/tháng", {}, "RECURRING_AMOUNT_CLARIFICATION"),
    ("10 000 000 theo tháng", {}, "RECURRING_AMOUNT_CLARIFICATION"),
    ("Mua nhà đầu tư cho thuê, doanh thu 10.000.000/tháng", {}, "PURCHASE_BUDGET_REQUIRED"),
    ("Doanh thu cho thuê 10.000.000/tháng có hợp lý không?", {}, "RENTAL_INCOME_INFORMATION"),
])
def test_numeric_recurring_requires_budget_or_clarification(chat, question, fields, code):
    ask, _, backend = chat
    first = start_sale(ask, backend)
    assert_blocked(ask(question, first, **fields), backend, code)


def test_buy_to_let_uses_explicit_total_instead_of_numeric_rental_income(chat):
    ask, _, backend = chat
    first = start_sale(ask, backend)
    result = ask("Mua nhà đầu tư cho thuê, ngân sách 3 tỷ, doanh thu 10.000.000/tháng", first)
    assert listing_calls(backend) == {"recommend": 1}
    assert result["recommendedProperties"]
    assert session_criteria(result)["purpose"] == "INVESTMENT"
    assert backend.recommend.call_args.args[0]["budgetVnd"] == "3000000000"


@pytest.mark.parametrize("text", [
    "80 m² mỗi tháng", "300 Dũng Sĩ Thanh Khê", "2 km/ngày", "15 phút/ngày",
    "2 phòng/tháng", "ngày 15/03/2026", "ngày 10/tháng 11/2026", "2 lần/tháng",
])
def test_nonmonetary_numbers_are_not_recurring_money(text):
    assert not list(recurring_amounts(text))


@pytest.mark.parametrize("text", ["2 tỷ 500 triệu/năm", "8tr–10tr/tháng", "8–10tr/tháng",
                                  "8.000.000–10.000.000/tháng", "8.000.000 den 10.000.000/thang"])
def test_recurring_ranges_and_composites_leave_no_purchase_budget(text):
    assert len(list(recurring_amounts(text))) == 1
    assert parse_budget(text).maximum is None
    assert parse_budget(f"Ngân sách mua 3 tỷ; doanh thu {text}").maximum == 3_000_000_000


@pytest.mark.parametrize(("question", "code"), [
    ("Tôi không muốn tìm mua nữa", "PURCHASE_DECLINED"),
    ("Nếu tôi muốn tìm mua nhà thì sao?", "TRANSACTION_INTENT_CONFLICT"),
    ("Tìm nhà dưới 10.000.000/tháng", "RECURRING_AMOUNT_CLARIFICATION"),
])
def test_current_turn_clarification_in_production_frontend(chat, question, code):
    ask, _, backend = chat
    first = start_sale(ask, backend)
    packet = ask(question, first)
    assert_frontend_contract(packet, {"cards": 0, "empty": False, "clarification": code,
                                      "purpose": "LIVING", "budget": "3000000000"})
