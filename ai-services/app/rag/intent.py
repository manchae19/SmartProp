"""Small explicit routing rules, not inferred geography or a trained intent model."""
import re
import unicodedata
from decimal import Decimal


# Fixed, deterministic vocabulary. Every category the public map can publish.
CATEGORY_LABELS = {
    "SCHOOL": "trường học",
    "HOSPITAL": "cơ sở y tế",
    "PHARMACY": "nhà thuốc",
    "MARKET": "chợ",
    "SUPERMARKET": "siêu thị",
    "PARK": "công viên",
    "BEACH": "bãi biển",
    "PUBLIC_TRANSPORT": "giao thông công cộng",
}

CATEGORY_ORDER = tuple(CATEGORY_LABELS)

_CATEGORY_TERMS = (
    ("HOSPITAL", ("benh vien", "co so y te", "phong kham", "trung tam y te")),
    ("SCHOOL", ("truong hoc", "truong", "giao duc", "mam non", "tieu hoc", "trung hoc", "dai hoc")),
    ("PHARMACY", ("nha thuoc", "hieu thuoc", "quay thuoc")),
    ("MARKET", ("cho",)),
    ("SUPERMARKET", ("sieu thi",)),
    ("PARK", ("cong vien",)),
    ("BEACH", ("bai bien",)),
    ("PUBLIC_TRANSPORT", ("giao thong cong cong", "ben xe", "tram xe", "xe buyt")),
)


def fold(text):
    """Lowercase, strip Vietnamese diacritics; the only text normalisation used for routing."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if not unicodedata.combining(c))


def _has(value, term):
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", value) is not None


def _market_request(value):
    """'cho thuê', 'cho tôi', 'cho mình' are not market requests."""
    if re.search(r"(?<!\w)(?:gan cho|cac cho|cho nao)(?!\w)", value):
        return True
    return re.search(r"(?<!\w)cho(?!\w)(?!\s+(?:thue|toi|minh|ban|gia dinh|nguoi|con|vo|chong)(?!\w))", value) is not None


def poi_categories(question):
    """Explicit POI categories named by the question, in a fixed order.

    An empty tuple means "no category named": the caller must not narrow the evidence set
    and must not assume a category. This is a routing rule, never a model inference.
    """
    value = fold(question)
    # "thị trường" is a market metaphor and "trường hợp" is not a school.
    value = re.sub(r"(?<!\w)thi truong(?!\w)", " ", value)
    value = re.sub(r"(?<!\w)truong hop(?!\w)", " ", value)
    found = set()
    for category, terms in _CATEGORY_TERMS:
        hit = _market_request(value) if category == "MARKET" else any(_has(value, term) for term in terms)
        if hit:
            found.add(category)
    return tuple(c for c in CATEGORY_ORDER if c in found)


def asks_for_amenities(question):
    if re.search(r"(?<!\w)chợ(?!\w)", question.lower()):
        return True
    value = fold(question)
    value = re.sub(r"(?<!\w)thi truong(?!\w)", "", value)
    terms = ("tien ich", "benh vien", "y te", "truong", "giao duc",
             "sieu thi", "cong vien", "bai bien", "giao thong", "ben xe", "tram xe", "tram buyt", "phuong tien cong cong")
    if any(_has(value, term) for term in terms):
        return True
    # "cho thuê", "cho tôi" and "cho mình" are not requests about markets.
    return _market_request(value)


def empty_search_answer(criteria):
    whole, _, fraction = format(Decimal(str(criteria["budgetVnd"])), "f").partition(".")
    amount = f"{int(whole):,}".replace(",", ".")
    fraction = fraction.rstrip("0")
    if fraction:
        amount += "," + fraction
    location = ", ".join(criteria[k] for k in ("ward", "district") if criteria.get(k))
    return (f"Chưa tìm thấy bất động sản đủ điều kiện công khai trong ngân sách {amount} đồng"
            + (f" tại {location}" if location else "")
            + ". Đây là kết quả trên dữ liệu hiện có, không phải kết luận về toàn bộ thị trường.\n"
            "Bạn muốn tìm nhà ở, căn hộ hay đất nền, và tại địa bàn nào? "
            "Hãy nhắc lại ngân sách trong câu hỏi tiếp theo, hoặc chọn “Tìm bằng bộ lọc”.")


def insufficient_amenity_answer(district, categories):
    labels = " và ".join(CATEGORY_LABELS.get(c, c) for c in categories)
    where = f" tại {district}" if district else ""
    return (f"Chưa có bằng chứng tiện ích {labels}{where} đủ điều kiện công khai trong kho tri thức hiện tại. "
            "Hệ thống không dùng loại tiện ích khác để thay thế và không suy đoán tên, vị trí hay khoảng cách. "
            "Bạn có thể xem bản đồ tiện ích đã kiểm chứng bên dưới hoặc hỏi lại với địa bàn khác.")