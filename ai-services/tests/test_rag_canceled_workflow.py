"""A saved budget is usable after cancellation only on an authorized turn."""
import pytest
from fastapi.testclient import TestClient

import test_chat_checkpoints as checkpoints
import test_rag_multiturn as fixtures
from app.rag.api import create_chat_app
from app.rag.config import Settings
from app.rag.money import parse_budget, recurring_amounts
from test_chat_market_g1 import snapshot
from test_rag_address_candidates import ADDRESS, assert_frontend_contract
from test_rag_transaction_current_turn import SALE_START, assert_blocked, chat, listing_calls, start_sale
from test_rag_transaction_policy import session_criteria


CANCEL = "Tôi không muốn tìm mua nữa."
STOP = "Tôi muốn dừng tìm mua nhà ở Thanh Khê."
RECURRING = "Tìm nhà ở Thanh Khê dưới 10.000.000/tháng 2 phòng ngủ"
STALE = "NO_PENDING_LISTING_STEP"


def public_needs(service, packet):
    sid = packet["evidence"]["session"]["id"]
    return service.sessions._items[("PUBLIC", sid)].needs


def assert_preserved(result, prior, backend, code):
    assert_blocked(result, backend, code)
    assert session_criteria(result) == session_criteria(prior)


@pytest.mark.parametrize(("stage", "stale", "state_key"), [
    ("nearby_consent", "Bỏ qua", "nearConsentPending"),
    ("nearby_selection", f"1. {ADDRESS}", "nearbyPoints"),
    ("commute", "Đồng ý", "commuteStage"),
    ("commute", "Nhập địa điểm khác", "commuteStage"),
    ("guided", "Bỏ qua", "pending"),
])
def test_canceled_workflow_rejects_late_control(chat, stage, stale, state_key):
    ask, service, backend = chat
    initial = start_sale(ask, backend)
    if stage.startswith("nearby"):
        pending = ask(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", initial)
        assert pending["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
        if stage == "nearby_selection":
            backend.geocode_workplace.return_value = [{"label": ADDRESS, "latitude": 16.06, "longitude": 108.22}]
            pending = ask("Đồng ý tìm vị trí", pending)
            assert pending["evidence"]["clarification"] == "NEAR_ADDRESS_PICK"
    elif stage == "commute":
        initial = ask("Tìm nhà gần chỗ làm ở Thanh Khê", initial)
        assert initial["evidence"]["clarification"] == "COMMUTE_DESTINATION_REQUIRED"
        pending = ask("Nhập địa điểm khác", initial)
        assert pending["evidence"]["clarification"] == "COMMUTE_ADDRESS_CONSENT"
    else:
        pending = ask("Tư vấn từng bước", initial)
        assert pending["evidence"]["needs"]["pending"] == "purpose"
    assert public_needs(service, pending).get(state_key)
    preserved = session_criteria(pending)
    backend.reset_mock()

    canceled = ask(CANCEL, pending)
    assert_preserved(canceled, pending, backend, "PURCHASE_DECLINED")
    assert state_key not in public_needs(service, canceled)
    skipped = ask(stale, canceled)
    assert_preserved(skipped, canceled, backend, STALE)
    assert session_criteria(skipped) == preserved
    assert state_key not in public_needs(service, skipped)


@pytest.mark.parametrize("command", [
    STOP, "Tôi muốn dừng tìm mua nhà.", "Thôi, dừng tìm nhà.", "Hủy tìm kiếm bất động sản.",
    "Tôi muốn ngừng tìm mua.", "Không tìm mua nhà nữa.", "Tạm dừng tìm nhà ở Thanh Khê.",
])
def test_cancellation_is_not_affirmative_search(chat, command):
    ask, _, backend = chat
    initial = start_sale(ask, backend)
    assert_preserved(ask(command, initial), initial, backend, "PURCHASE_DECLINED")


@pytest.mark.parametrize("saved", [False, True])
def test_plain_skip_does_not_open_a_workflow(chat, saved):
    ask, service, backend = chat
    initial = start_sale(ask, backend) if saved else None
    result = ask("Bỏ qua", initial)
    assert_blocked(result, backend, STALE)
    assert session_criteria(result) == (session_criteria(initial) if initial else {})
    assert not public_needs(service, result).get("pending")


def test_skip_is_valid_during_guided_optional_step(chat):
    ask, service, backend = chat
    initial = start_sale(ask, backend)
    step = ask("Tư vấn từng bước", initial)
    assert step["evidence"]["needs"]["pending"] == "purpose"
    reply = ask("Bỏ qua", step)
    assert reply["evidence"]["needs"]["pending"] == "property_type"
    assert not reply["recommendedProperties"] and not listing_calls(backend)
    assert public_needs(service, reply)["purposeAsked"] is True


def test_rejecting_pending_nearby_location_does_not_cancel_saved_criteria(chat):
    ask, service, backend = chat
    initial = start_sale(ask, backend)
    pending = ask(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", initial)
    reply = ask("Bỏ qua", pending)
    assert reply["evidence"]["responseKind"] == "CRITERIA_UPDATED"
    assert not reply["recommendedProperties"] and not listing_calls(backend)
    assert not public_needs(service, reply).get("nearConsentPending")
    assert session_criteria(reply) == session_criteria(pending)


def test_pending_consent_cannot_switch_transaction_via_json(chat):
    ask, service, backend = chat
    initial = start_sale(ask, backend)
    pending = ask(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", initial)
    reply = ask("Đồng ý tìm vị trí", pending, purpose="RENTAL")
    assert_preserved(reply, pending, backend, "TRANSACTION_INTENT_CONFLICT")
    assert public_needs(service, reply)["nearConsentPending"] is True


def test_explicit_cancel_precedes_price_comparison_in_same_turn(chat):
    ask, service, backend = chat
    initial = start_sale(ask, backend)
    pending = ask(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", initial)
    reply = ask("Dừng tìm mua nhà. So sánh giá mua và thuê.", pending)
    assert_preserved(reply, pending, backend, "PURCHASE_DECLINED")
    assert "nearConsentPending" not in public_needs(service, reply)


@pytest.mark.parametrize(("new_command", "expected_purpose"), [
    ("Tìm mua nhà ở Thanh Khê.", "LIVING"),
    ("Tôi muốn tìm mua lại nhà ở Thanh Khê.", "LIVING"),
    ("Bỏ qua trường học, vẫn tìm mua nhà.", "LIVING"),
    ("Dừng tìm nhà ở Sơn Trà, vẫn tìm mua nhà ở Thanh Khê.", "LIVING"),
    ("Tìm theo ngân sách", "LIVING"),
    ("Xem gợi ý ngay", "LIVING"),
    ("Tôi không muốn mua, hãy tìm nhà thuê.", "RENTAL"),
])
def test_explicit_later_action_uses_saved_criteria_after_cancel(chat, new_command, expected_purpose):
    ask, _, backend = chat
    initial = start_sale(ask, backend)
    canceled = ask(CANCEL, initial)
    result = ask(new_command, canceled)
    assert session_criteria(result)["purpose"] == expected_purpose
    if expected_purpose == "RENTAL":
        assert_blocked(result, backend, "RENTAL_BUDGET_NOT_SUPPORTED")
    else:
        assert listing_calls(backend) == {"recommend": 1}
        assert result["recommendedProperties"]
        assert backend.recommend.call_args.args[0]["budgetVnd"] == "3000000000"


def test_removing_proximity_preference_preserves_the_purchase_workflow(chat):
    ask, _, backend = chat
    first = ask(f"{SALE_START}, ưu tiên gần bệnh viện")
    assert backend.recommend.call_args.args[0]["amenityPriorities"] == ["HOSPITAL"]
    backend.reset_mock()
    result = ask("Bỏ điều kiện gần bệnh viện.", first)
    assert listing_calls(backend) == {"recommend": 1}
    assert not backend.recommend.call_args.args[0].get("amenityPriorities")
    assert session_criteria(result) == session_criteria(first)


def test_switch_after_rental_still_requires_new_purchase_budget(chat):
    ask, _, backend = chat
    rented = ask("Thuê nhà ở Thanh Khê dưới 10 triệu/tháng.")
    reply = ask("Tôi không thuê nữa, hãy tìm mua nhà.", rented)
    assert_blocked(reply, backend, "PURCHASE_BUDGET_REQUIRED")
    assert session_criteria(reply)["purpose"] == "LIVING"
    assert "budgetVnd" not in session_criteria(reply)


def test_cancel_retains_state_across_market_question_and_repeat(chat):
    ask, _, backend = chat
    backend.market_summary.return_value = snapshot()
    initial = start_sale(ask, backend)
    canceled = ask(CANCEL, initial)
    market = ask("Giá mua nhà ở Thanh Khê là bao nhiêu?", canceled)
    assert market["evidence"]["responseKind"] == "MARKET_PRICE_EVIDENCE"
    assert session_criteria(market) == session_criteria(initial)
    assert_preserved(ask(CANCEL, market), initial, backend, "PURCHASE_DECLINED")


def test_cancel_in_restored_authenticated_checkpoint():
    checkpoint = checkpoints.CheckpointsTest()
    checkpoint.setUp()
    service, backend, _, _ = fixtures.MultiTurnTests().service()
    backend.settings, backend.client = checkpoint.backend.settings, checkpoint.backend.client
    profile = {"subject": "1", "enabled": True, "district": "Thanh Khê",
               "selectedNeeds": ["HOSPITAL"], "primaryNeed": "HOSPITAL"}
    backend.account_context.return_value = profile

    def send(question, *, session=None):
        payload = {"question": question}
        if session:
            payload["sessionId"] = session
        # Each app invocation has a fresh in-memory store. The mock server stores revisions.
        with TestClient(create_chat_app(Settings(), service)) as client:
            response = client.post("/chat/personalized", json=payload, headers={"Authorization": "Bearer 1"})
        assert response.status_code == 200, response.text
        return response.json()

    try:
        initial = send(SALE_START)
        sid = initial["evidence"]["session"]["id"]
        pending = send(f"Tìm nhà gần {ADDRESS}, ngân sách 3 tỷ", session=sid)
        assert pending["evidence"]["clarification"] == "NEAR_ADDRESS_CONSENT"
        backend.reset_mock()
        assert_preserved(send(CANCEL, session=sid), pending, backend, "PURCHASE_DECLINED")
        assert_preserved(send("Bỏ qua", session=sid), pending, backend, STALE)
        row = checkpoint.rows[("Bearer 1", sid)]
        assert row["revision"] == 4
        assert "nearConsentPending" not in row["checkpoint"]["needs"]
        assert row["checkpoint"]["budget_vnd"] == "3000000000"
        assert profile["selectedNeeds"] == ["HOSPITAL"]
    finally:
        checkpoint.tearDown()


@pytest.mark.parametrize(("text", "setup", "code"), [
    (RECURRING, "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10000000/tháng 2 phòng ngủ", "fresh", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10 000 000/tháng 3 phòng ngủ", "rent", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10,000,000/tháng 100 m²", "structured", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 800000/ngày 2 phòng", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 120000000/năm 3 tầng", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10.000.000 mỗi tháng 2 phòng ngủ", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10.000.000 theo tháng 2 phòng ngủ", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10.000.000/tháng, 2 phòng ngủ", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10.000.000/tháng 12/5 Nguyễn Văn Linh", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tim nha duoi 10.000.000/thang va 2 phong ngu", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà 8.000.000–10.000.000/tháng 2 phòng ngủ", "sale", "RECURRING_AMOUNT_CLARIFICATION"),
    ("Tìm nhà dưới 10 triệu/tháng 2 phòng ngủ", "sale", "RENTAL_BUDGET_NOT_SUPPORTED"),
    ("Tìm nhà dưới 10tr/tháng 3 phòng ngủ", "fresh", "RENTAL_BUDGET_NOT_SUPPORTED"),
    ("Tìm nhà dưới 8 triệu mỗi tháng 100 m²", "rent", "RENTAL_BUDGET_NOT_SUPPORTED"),
])
def test_recurring_amount_with_numeric_property_filter_blocks_sale(chat, text, setup, code):
    ask, _, backend = chat
    initial = start_sale(ask, backend) if setup in ("sale", "structured") else None
    if setup == "rent":
        initial = ask("Đổi sang thuê")
    fields = {"purpose": "LIVING", "budgetVnd": 3_000_000_000} if setup == "structured" else {}
    reply = ask(text, initial, **fields)
    assert_blocked(reply, backend, code)
    if code == "RECURRING_AMOUNT_CLARIFICATION":
        assert session_criteria(reply) == (session_criteria(initial) if initial else {})
    else:
        assert "budgetVnd" not in session_criteria(reply)


def test_buy_to_let_ignores_income_followed_by_rooms(chat):
    ask, _, backend = chat
    initial = start_sale(ask, backend)
    reply = ask("Tìm mua nhà 3 tỷ để cho thuê, thu nhập dự kiến 10 triệu/tháng, 2 phòng ngủ.", initial)
    assert listing_calls(backend) == {"recommend": 1}
    assert reply["recommendedProperties"]
    assert session_criteria(reply)["purpose"] == "INVESTMENT"
    assert backend.recommend.call_args.args[0]["budgetVnd"] == "3000000000"


@pytest.mark.parametrize("text", [
    "Ngày 13 tháng 12", "13/12/2026", "Tháng 12 năm 2026", "Ngày 2 tháng 3",
    "Ngày 10/tháng 11/2026", "10/tháng 11/2026", "10/tháng 11 năm 2026", "13/tháng 12",
    "Diện tích 100 m²", "Nhà 2 phòng ngủ", "Nhà 3 tầng", "12/5 Nguyễn Văn Linh",
    "Đi làm 15 phút/ngày", "Lịch sử giá theo tháng/năm",
])
def test_date_and_nonmoney_are_not_recurring_amounts(text):
    assert not list(recurring_amounts(text))
    assert parse_budget(f"Ngân sách 3 tỷ; {text}").maximum == 3_000_000_000


def test_stale_continuation_packet_in_production_frontend(chat):
    ask, _, backend = chat
    initial = start_sale(ask, backend)
    reply = ask("Bỏ qua", ask(CANCEL, initial))
    assert_frontend_contract(reply, {"cards": 0, "empty": False, "clarification": STALE,
                                     "purpose": "LIVING", "budget": "3000000000"})
