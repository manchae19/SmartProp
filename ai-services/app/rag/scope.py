"""Conservative domain boundary; neither user statements nor history add verified knowledge."""
import re
import unicodedata

from . import commute_destination
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
    # Courtesy and capability questions get a direct answer instead of the generic clarifier.
    short=text.strip(" ?!.")
    if re.fullmatch(r"(?:xin chao|chao(?: ban)?|hello|hi|alo)(?: ban)?",short):
        return "Chào bạn! Tôi có thể tìm nhà/căn hộ đang đăng bán trên SmartProp theo ngân sách và khu vực, tra đất Hòa Xuân theo giá/diện tích, xem nguồn nguy cơ ngập Đà Nẵng, hoặc phân tích một tin đăng cụ thể."
    if re.fullmatch(r"(?:cam on|thank(?:s| you)?)(?: ban| nhieu)?",short):
        return "Rất vui được hỗ trợ bạn. Khi cần, bạn cứ hỏi tiếp về tin đăng hoặc lô đất đang xem."
    if re.search(r"\bban (?:lam duoc gi|co the lam gi|giup duoc gi)\b|\bhuong dan su dung\b|\bchuc nang\b",text):
        return ("Tôi hỗ trợ: tìm nhà/căn hộ đang bán trên SmartProp theo ngân sách, khu vực, diện tích; tra đất ở và đất nông nghiệp Hòa Xuân "
                "(giá, diện tích, hồ sơ, so sánh, bản đồ); tra danh mục nguy cơ ngập Đà Nẵng; phân tích một tin đăng. Ví dụ: “Tìm căn hộ dưới 3 tỷ ở Sơn Trà” hoặc “Tìm đất khoảng 2 tỷ”.")
    if re.search(r"\bnhan vien\b|\bgap .*tu van\b|\bnguoi that\b",text):
        return "Tôi chưa kết nối trực tiếp với nhân viên tư vấn. Bạn có thể nhắn người đăng tin ở trang chi tiết tin, hoặc lưu mã lô/tin để hỏi thêm."
    unrelated=re.search(r"\b(?:thoi tiet|du bao mua|bong da|ty so tran|nau an|cong thuc nau|chua benh|chan doan|dieu tri|mua co phieu|bitcoin|tien ao|viet code|lap trinh|chinh tri|tu vi|xem boi)\b",text)
    housing=re.search(r"\b(?:bat dong san|nha|can ho|dat|tin dang|gia|ngan sach|ty|trieu|thue|mua|dau tu|phap ly|quy hoach|tien ich|truong|benh vien|sieu thi|khu vuc|vi tri|can nay|can do|can thu|dien tich|phong ngu|hai chau|son tra|da nang|thanh khe|cam le|hoa vang|lien chieu|ngu hanh son)\b",text)
    if unrelated or turn["intent"]=="CLARIFY" and not housing and len(text.split())>3:
        return OUTSIDE
    return None
