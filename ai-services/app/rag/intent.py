"""Small explicit routing rules, not inferred geography or a trained intent model."""
import re
import unicodedata
from decimal import Decimal
from .money import recurring_amounts


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
    "MALL": "trung tâm thương mại",
}

CATEGORY_ORDER = tuple(CATEGORY_LABELS)

_CATEGORY_TERMS = (
    ("HOSPITAL", ("benh vien", "co so y te", "phong kham", "trung tam y te", "benh xa", "hospital")),
    ("SCHOOL", ("truong hoc", "school", "truong", "giao duc", "mam non", "nha tre", "tieu hoc", "trung hoc", "dai hoc")),
    ("PHARMACY", ("nha thuoc", "hieu thuoc", "quay thuoc")),
    ("MARKET", ("cho",)),
    ("SUPERMARKET", ("sieu thi", "supermarket")),
    ("MALL", ("trung tam thuong mai", "tttm", "shopping mall", "shopping center", "mall")),
    ("PARK", ("cong vien", "vuon hoa", "park")),
    ("BEACH", ("bai bien",)),
    ("PUBLIC_TRANSPORT", ("giao thong cong cong", "ben xe", "tram xe", "xe buyt", "tram buyt", "bus", "bus stop", "bus station", "phuong tien cong cong")),
)


def fold(text):
    """Lowercase, strip Vietnamese diacritics; the only text normalisation used for routing."""
    return "".join(c for c in unicodedata.normalize("NFD", text.lower().replace("đ", "d")) if not unicodedata.combining(c))


def _has(value, term):
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", value) is not None


LISTING_TYPES = r"(?:nha|chung cu|can ho|biet thu|phong tro|mat bang|bat dong san|bds|dat nen)"
_LISTING_OBJECT = rf"(?:tin\s+)?{LISTING_TYPES}(?:\s+(?:pho|rieng|nguyen can))?\b"
_PURCHASE_ACTION = re.compile(
    rf"^mua\b|\b(?:tim|muon|can|doi sang|chuyen sang|bat dau)\s+mua\b"
    rf"|\b(?:tim|muon|can|goi y|de xuat|xem)\s+{_LISTING_OBJECT}\s+(?:rao\s+)?ban\b"
)
_RENT_ACTION = re.compile(
    rf"\b(?:tim|muon|can|doi sang|chuyen sang)\s+thue\b"
    rf"|(?<!gia )(?<!gia cho )\bthue\s+{LISTING_TYPES}\b"
    rf"|\b{LISTING_TYPES}(?:\s+(?:pho|rieng|nguyen can))?\s+(?:de |cho )?thue\b"
    r"|\bgia (?:cho )?thue\s+(?:\d|[^.!?]*?\b(?:duoi|tren|toi da|tu)\s+\d)"
    r"|^thue\s+(?:de o\b|(?:duoi|tren|toi da|tu)\s+\d|\d)"
)
_ACTION_PREFIX = r"(?:(?:muon|can|tim|dinh|nen|tiep tuc)\s+)*"
_TRANSACTION_ACTION = (
    rf"{_ACTION_PREFIX}(?:(mua|thue)\b|{_LISTING_OBJECT}\s+(?:rao\s+|cho\s+)?(ban|thue)\b"
    rf"|tim\s+{_LISTING_OBJECT}(?!\s+(?:thuoc|hang|khoa|kho|may|sach|tre)\b))"
)
_NEGATED_TRANSACTION = re.compile(rf"\b(?:khong|chua)\s+(?:con\s+)?{_TRANSACTION_ACTION}")
_STOP_LISTING = re.compile(
    rf"\b(?:tam\s+dung|dung|ngung|huy(?:\s+bo)?|thoi)\s+(?:viec\s+)?"
    rf"(?:tim\s+(?:kiem(?:\s+(?:{_LISTING_OBJECT}|mua\b|thue\b))?|mua\b|thue\b|{_LISTING_OBJECT})"
    rf"|mua\s+{_LISTING_OBJECT})"
)
_HYPOTHETICAL_TRANSACTION = re.compile(rf"^(?:neu(?:\s+nhu)?|gia su)\s+(?:(?:toi|minh)\s+)?{_TRANSACTION_ACTION}")
_CLAUSE_BREAK = re.compile(r",(?=\s|[^\d])|[;!?]|\.(?=\s|$)|\b(?:nhung|ma|thay vao do)\b")
NO_LISTING_ACTION = frozenset({"CONFLICT", "PURCHASE_DECLINED", "RENT_DECLINED", "RECURRING_AMOUNT_CLARIFICATION"})
_LET_PURPOSE = re.compile(
    rf"\b(?:de|roi)\s+(?:(?:dau tu|khai thac)\s+){{0,2}}cho thue\b"
    rf"|\b(mua\s+{LISTING_TYPES}(?:\s+(?:pho|rieng|nguyen can))?(?:\s+dau tu)?)\s+cho thue\b"
)
_RENTAL_INCOME = re.compile(r"\b(?:doanh thu|thu nhap|dong tien|loi nhuan)(?:\s+tu)?(?:\s+cho thue)?\b")
_INCOME_LABEL = re.compile(r"\s*(?:(?:du kien|ky vong|uoc tinh|khoang|la|dat|tu)\s*)*[:=]?\s*$")


def purchase_price_question(value):
    """Recognize purchase-price information requests in folded text."""
    value = " ".join(value.split())
    if not re.search(r"\bmua\b", value):
        return False
    if re.search(r"\b(?:tim mua|doi sang mua|chuyen sang mua)\b", value):
        return False
    return bool(re.search(
        r"\bbiet gia mua\b|\bgia(?:\s+(?:la|khoang|tam))*\s+bao nhieu\b"
        r"|\b(?:can|mat|ton)(?:\s+(?:la|khoang|tam))*\s+bao nhieu(?:\s+tien)?\b", value
    ) or re.search(r"\bgia mua\b", value) and re.search(r"\bbao nhieu\b", value))


def transaction_information(value):
    if re.search(r"\bso sanh\b", value) and re.search(r"\b(?:mua|ban)\b", value) and re.search(r"\bthue\b", value):
        return "PRICE_COMPARISON"
    if purchase_price_question(value):
        return "PURCHASE_PRICE"
    if (_RENTAL_INCOME.search(value) and re.search(r"\b(?:thue|cho thue)\b", value)
            and not _PURCHASE_ACTION.search(value)):
        return "RENTAL_INCOME"
    return None


def _transaction_clauses(value):
    """Separate declined/conditional actions from independently stated actions."""
    return [clause.strip() for clause in _CLAUSE_BREAK.split(value) if clause.strip()]


def buy_to_let(value):
    return any(_PURCHASE_ACTION.search(clause) and _LET_PURPOSE.search(clause)
               for clause in _transaction_clauses(value)
               if not _NEGATED_TRANSACTION.search(clause) and not _STOP_LISTING.search(clause)
               and not _HYPOTHETICAL_TRANSACTION.match(clause))


def listing_transaction(question):
    """Explicit listing action, excluding informational price questions."""
    text = re.sub(r"\bthuế\b", "tax", unicodedata.normalize("NFC", question.lower()))
    value = " ".join(fold(text).split())
    clauses = _transaction_clauses(value)
    declined = {match[1] or match[2] or "mua" for match in _NEGATED_TRANSACTION.finditer(value)}
    canceled = any(_STOP_LISTING.search(clause) for clause in clauses)
    affirmative = [clause for clause in clauses
                   if not _NEGATED_TRANSACTION.search(clause) and not _STOP_LISTING.search(clause)
                   and not _HYPOTHETICAL_TRANSACTION.match(clause)]
    buy = any(_PURCHASE_ACTION.search(clause) for clause in affirmative)
    if (canceled or declined & {"mua", "ban"}) and not buy and not any(
        _RENT_ACTION.search(clause) for clause in affirmative
    ):
        return "PURCHASE_DECLINED"
    if transaction_information(value):
        return None
    if any(_HYPOTHETICAL_TRANSACTION.match(clause) for clause in clauses):
        return "CONFLICT"
    value = ", ".join(affirmative)
    investment = buy_to_let(value)
    rent_text = _RENTAL_INCOME.sub(" ", _LET_PURPOSE.sub(r"\1 ", value)) if investment else value
    rent = bool(_RENT_ACTION.search(rent_text))
    for amount in recurring_amounts(value):
        if investment and any(_INCOME_LABEL.fullmatch(value[label.end():amount.start()])
                              for label in _RENTAL_INCOME.finditer(value, 0, amount.start())):
            continue
        if amount["bare"] and (buy or not rent):
            return "RECURRING_AMOUNT_CLARIFICATION"
        rent = True
    if buy:
        return "CONFLICT" if rent else "SALE"
    if rent:
        return "RENT"
    return "RENT_DECLINED" if declined else None


def effective_listing_transaction(text, structured_purpose, saved_purpose):
    """Return the transaction and whether the caller selected it on this turn."""
    if text in NO_LISTING_ACTION:
        return text, False
    structured = None if structured_purpose is None else "RENT" if structured_purpose == "RENTAL" else "SALE"
    if text and structured and text != structured:
        return "CONFLICT", True
    selected = text or structured
    return selected or ("RENT" if saved_purpose == "RENTAL" else "SALE"), selected is not None


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
    if poi_categories(question):
        return True
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


def empty_search_answer(criteria, *, area=None):
    whole, _, fraction = format(Decimal(str(criteria["budgetVnd"])), "f").partition(".")
    amount = f"{int(whole):,}".replace(",", ".")
    fraction = fraction.rstrip("0")
    if fraction:
        amount += "," + fraction
    location = ", ".join(criteria[k] for k in ("ward", "district") if criteria.get(k))
    kinds={"ALL":"mọi loại bất động sản","HOUSE":"nhà phố/nhà riêng","APARTMENT":"căn hộ","LAND":"đất nền","VILLA":"biệt thự","ROOM":"phòng trọ","COMMERCIAL":"mặt bằng"}
    filters=" Loại đang lọc: "+kinds.get(criteria.get("propertyType","ALL"),"chưa rõ")+"."
    if area:filters+=" Tiêu chí "+area+"."
    if criteria.get("minPriceVnd"):filters+=" Giá tối thiểu: "+str(criteria["minPriceVnd"])+" đồng."
    return (f"Chưa tìm thấy bất động sản đủ điều kiện công khai trong ngân sách {amount} đồng"
            + (f" tại {location}" if location else "")
            + "."+filters+" Đây là kết quả trên dữ liệu hiện có, không phải kết luận về toàn bộ thị trường.\n"
            "Bạn có thể nới ngân sách, mở rộng khu vực, giảm diện tích tối thiểu hoặc đổi loại bất động sản; "
            "hệ thống không tự bỏ qua ngân sách. Bạn muốn tìm nhà ở, căn hộ hay đất nền, và tại địa bàn nào? "
            "Bạn có thể yêu cầu đổi loại nhà hoặc mở rộng khu vực và giữ ngân sách hiện tại, hoặc chọn “Tìm bằng bộ lọc”.")


def insufficient_amenity_answer(district, categories):
    labels = " và ".join(CATEGORY_LABELS.get(c, c) for c in categories)
    where = f" tại {district}" if district else ""
    return (f"Chưa có bằng chứng tiện ích {labels}{where} đủ điều kiện công khai trong kho tri thức hiện tại. "
            "Hệ thống không dùng loại tiện ích khác để thay thế và không suy đoán tên, vị trí hay khoảng cách. "
            "Bạn có thể xem bản đồ tiện ích đã kiểm chứng bên dưới hoặc hỏi lại với địa bàn khác.")

def asks_market_trend(question):
    """Market questions are answered from aggregates, never from the property intake."""
    value = fold(question)
    return any(_has(value, term) for term in (
        "xu huong", "thi truong", "dien bien gia", "gia thi truong",
        "bao cao thi truong", "tong quan thi truong", "thi truong bat dong san",
    ))
