"""Conservative domain boundary; neither user statements nor history add verified knowledge."""
import re
import unicodedata

from . import commute_destination
from .money import recurring_amounts
OUTSIDE="Tôi chưa thể trả lời câu hỏi này của bạn vì dữ liệu nằm ngoài phạm vi hỗ trợ hiện tại của tôi. Tôi có thể hỗ trợ thông tin tin đăng, phân tích sơ bộ từ nội dung người đăng cung cấp, tìm bất động sản và tiện ích tại địa bàn SmartProp hỗ trợ."

# The three replies the commute question offers. Matched on folded text so the
# comparison does not depend on how the client renders diacritics.
def _commute_choice(question):
    """True when the reply is one of the three the commute question offers."""
    return (commute_destination.wants_saved(question)
            or commute_destination.wants_new(question)
            or commute_destination.wants_skip(question))


def domain_reply(question, turn, pending=None):
    """Return the out-of-scope message, or None when the question is in scope.

    `pending` names the clarification the session is waiting on. While the advisor is
    waiting for a commute destination, the official replies ("Dùng nơi làm việc đã lưu",
    "Nhập địa điểm khác", "Bỏ qua") are part of the flow and must reach the state machine
    even though they carry no housing keyword.
    """
    text="".join(c for c in unicodedata.normalize("NFD",question.lower().replace("đ","d")) if not unicodedata.combining(c))
    if pending == "COMMUTE_DESTINATION_REQUIRED" and _commute_choice(question):
        return None
    unrelated=re.search(r"\b(?:thoi tiet|du bao mua|bong da|ty so tran|nau an|cong thuc nau|chua benh|chan doan|dieu tri|mua co phieu|bitcoin|tien ao|viet code|lap trinh|chinh tri|tu vi|xem boi)\b",text)
    housing=re.search(r"\b(?:bat dong san|nha|can ho|dat|tin dang|gia|ngan sach|ty|trieu|thue|mua|dau tu|phap ly|quy hoach|tien ich|truong|benh vien|sieu thi|khu vuc|vi tri|can nay|can do|can thu|dien tich|phong ngu|hai chau|son tra|da nang|thanh khe|cam le|hoa vang|lien chieu|ngu hanh son)\b",text)
    if unrelated or (turn["intent"] == "CLARIFY" and not housing and len(text.split()) > 3
                     and not any(recurring_amounts(text))):
        return OUTSIDE
    return None
