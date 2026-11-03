"""Small explicit routing rule, not inferred geography or a trained intent model."""
import re
import unicodedata
from decimal import Decimal


def asks_for_amenities(question):
    if re.search(r'(?<!\w)chợ(?!\w)', question.lower()):
        return True
    value = ''.join(c for c in unicodedata.normalize('NFD', question.lower().replace('đ', 'd')) if not unicodedata.combining(c))
    value = re.sub(r'(?<!\w)thi truong(?!\w)', '', value)
    terms = ('tien ich', 'benh vien', 'y te', 'truong', 'giao duc',
             'sieu thi', 'cong vien', 'bai bien', 'giao thong', 'ben xe', 'tram xe', 'tram buyt', 'phuong tien cong cong')
    if any(re.search(r'(?<!\w)' + re.escape(term) + r'(?!\w)', value) for term in terms):
        return True
    # "cho thuê", "cho tôi" and "cho mình" are not requests about markets.
    return bool(re.search(r'(?<!\w)(?:gan cho|cac cho|cho nao)(?!\w)', value) or re.search(r'(?<!\w)cho(?!\w)(?!\s+(?:thue|toi|minh|ban|gia dinh|nguoi|con|vo|chong)(?!\w))', value))


def empty_search_answer(criteria):
    whole, _, fraction = format(Decimal(str(criteria['budgetVnd'])), 'f').partition('.')
    amount = f"{int(whole):,}".replace(',', '.')
    fraction = fraction.rstrip('0')
    if fraction:
        amount += ',' + fraction
    location = ', '.join(criteria[k] for k in ('ward', 'district') if criteria.get(k))
    return (f"Chưa tìm thấy bất động sản đủ điều kiện công khai trong ngân sách {amount} đồng"
            + (f" tại {location}" if location else '')
            + ". Đây là kết quả trên dữ liệu hiện có, không phải kết luận về toàn bộ thị trường.\n"
            "Bạn muốn tìm nhà ở, căn hộ hay đất nền, và tại địa bàn nào? "
            "Hãy nhắc lại ngân sách trong câu hỏi tiếp theo, hoặc chọn “Tìm bằng bộ lọc”.")
