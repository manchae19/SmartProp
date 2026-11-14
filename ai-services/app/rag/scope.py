"""Conservative domain boundary; neither user statements nor history add verified knowledge."""
import re
import unicodedata
OUTSIDE="Tôi chưa thể trả lời câu hỏi này của bạn vì dữ liệu nằm ngoài phạm vi hỗ trợ hiện tại của tôi. Tôi có thể hỗ trợ thông tin tin đăng, phân tích sơ bộ từ nội dung người đăng cung cấp, tìm bất động sản và tiện ích tại địa bàn SmartProp hỗ trợ."

def domain_reply(question, turn):
    text="".join(c for c in unicodedata.normalize("NFD",question.lower().replace("đ","d")) if not unicodedata.combining(c))
    unrelated=re.search(r"\b(?:thoi tiet|du bao mua|bong da|ty so tran|nau an|cong thuc nau|chua benh|chan doan|dieu tri|mua co phieu|bitcoin|tien ao|viet code|lap trinh|chinh tri|tu vi|xem boi)\b",text)
    housing=re.search(r"\b(?:bat dong san|nha|can ho|dat|tin dang|gia|ngan sach|ty|trieu|thue|mua|dau tu|phap ly|quy hoach|tien ich|truong|benh vien|sieu thi|khu vuc|vi tri|can nay|can do|can thu|dien tich|phong ngu|hai chau|son tra|da nang|thanh khe|cam le|hoa vang|lien chieu|ngu hanh son)\b",text)
    if unrelated or turn["intent"]=="CLARIFY" and not housing and len(text.split())>3:
        return OUTSIDE
    return None
