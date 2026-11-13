"""Deterministic follow-up parsing. Never infers facts; only classifies the turn.

Every decision here is a routing decision over the *question text plus stored criteria*.
No model is consulted, so a follow-up can never invent a budget or a property.
"""
import re
from decimal import Decimal

from .intent import fold, poi_categories
from .money import parse_budget

# Word ordinals only. A bare digit must NEVER be read as an ordinal: "2 tỷ" is a
# budget, not "căn thứ hai". Numeric ordinals need an explicit property noun prefix,
# handled by _numeric_ordinal() below.
ORDINALS = {
    "dau tien": 1, "thu nhat": 1,
    "thu hai": 2,
    "thu ba": 3,
    "thu tu": 4,
    "thu nam": 5,
    "thu sau": 6,
}
ORDINAL_WORDS = {"nhat": 1, "mot": 1, "hai": 2, "ba": 3, "bon": 4, "tu": 4, "nam": 5, "sau": 6}
PROPERTY_NOUNS = ("can", "can ho", "bds", "bat dong san", "nha", "lua chon", "phuong an", "option")
MAX_ORDINAL = 10

# A change of search criteria (budget / district / purpose / type / area).
CHANGE_TERMS = ("tang", "giam", "neu", "doi", "thay", "chuyen", "sang", "len", "xuong",
                "con ", "khac", "mo rong", "thu hep", "dieu chinh")
# Questions that only ask about what was already found.
ANALYTIC_TERMS = ("vi sao", "tai sao", "phu hop khong", "co phu hop", "danh gia", "so sanh",
                  "xep hang", "diem", "chi tiet", "gia bao nhieu", "dien tich", "phap ly")
MAP_TERMS = ("ban do", "hien thi", "xem tren ban do", "chi duong", "vi tri")
CLARIFY_TERMS = ("cai nao", "can nao", "cho nao", "o dau", "cai do", "can do", "nhu the nao")

PRONOUNS = ("can nay", "can do", "can thu", "bat dong san nay", "bds nay", "nha nay",
            "cai nay", "cai do", "no ", "chung", "cac can", "nhung can", "can thu hai")


def _has(value, term):
    return re.search(r"(?<!\w)" + re.escape(term) + r"(?!\w)", value) is not None


def budget_from_followup(question):
    """Compatibility entry point; both first turns and follow-ups use the same parser."""
    parsed = parse_budget(question)
    return parsed.maximum if parsed.status == "VALID" else None


def ordinal_reference(question):
    """"căn thứ hai" -> 2, "căn 2" -> 2. "2 tỷ" -> None.

    An ordinal only exists when it is attached to a property noun, so amounts,
    areas and prices can never be mistaken for a position in the result list.
    """
    value = fold(question)
    numeric = re.search(
        r"(?:can|can ho|bds|bat dong san|nha|lua chon|phuong an)\s+(?:so\s+)?(?:thu\s+)?(\d{1,2})(?![\d.,]|\s*(?:ty|ti|trieu|m2|m\b|phong|pn))",
        value)
    if numeric:
        index = int(numeric.group(1))
        return index if 1 <= index <= MAX_ORDINAL else None
    for phrase, index in sorted(ORDINALS.items(), key=lambda kv: -len(kv[0])):
        # Require the ordinal phrase to follow a property noun ("căn thứ hai").
        if re.search(r"(?:can|bds|bat dong san|nha|lua chon|phuong an)\s+" + re.escape(phrase) + r"(?!\w)", value):
            return index
    asked = re.search(r"\bthu\s+(\d{1,2})\b", value)
    if asked and re.search(r"(?:can|bds|bat dong san|nha|lua chon|phuong an)", value):
        index = int(asked.group(1))
        return index if 1 <= index <= MAX_ORDINAL else None
    return None


def is_map_request(question):
    value = fold(question)
    return any(_has(value, term) for term in MAP_TERMS) and not poi_categories(question)


def is_analytic(question):
    value = fold(question)
    return any(_has(value, term) for term in ANALYTIC_TERMS)


def is_clarification_needed(question):
    """A pronoun-only question with no resolvable target must ask, not guess."""
    value = fold(question)
    return any(_has(value, term) for term in CLARIFY_TERMS)


def changes_search(question):
    value = fold(question)
    if budget_from_followup(question) is not None:
        return True
    if any(_has(value, term.strip()) for term in CHANGE_TERMS):
        return True
    return False


def detect_property_type(question):
    value = fold(question)
    # "nha thuoc", "nha hang", "nha khoa", "nha kho" ... are POIs, not residential types.
    value = re.sub(r"(?<!\w)nha\s+(?:thuoc|hang|khoa|kho|nghi|may|tro|xe|hat|sach|bep|go)\b", " ", value)
    mapping = (("can ho", "APARTMENT"), ("chung cu", "APARTMENT"), ("nha pho", "HOUSE"),
               ("nha rieng", "HOUSE"), ("biet thu", "VILLA"), ("dat nen", "LAND"),
               ("phong tro", "ROOM"), ("mat bang", "COMMERCIAL"), ("shophouse", "COMMERCIAL"))
    # Generic 'nha' means a home search, not an explicit HOUSE-only restriction.
    hits = [code for term, code in mapping if _has(value, term.strip())]
    kinds = {h for h in hits}
    # A specific type wins over the generic "nha"; two different specific types mean
    # the request is ambiguous and no type may be assumed.
    specific = kinds - {"HOUSE"} | ({"HOUSE"} if "nha pho" in value or "nha rieng" in value else set())
    specific = {k for k in specific if k != "HOUSE"} or kinds
    if len(specific) != 1:
        return None
    if any(_has(value, t) for t in ("dat ",)) and "LAND" in kinds:
        return "LAND"
    return next(iter(specific))


def detect_purpose(question):
    value = fold(question)
    if any(_has(value, t) for t in ("dau tu", "sinh loi", "tang gia")):
        return "INVESTMENT"
    if any(_has(value, t) for t in ("cho thue", "thu nhap cho thue")):
        return "RENTAL"
    if any(_has(value, t) for t in ("de o", "sinh song", "o that")):
        return "LIVING"
    return None


def detect_district(question, known):
    value = fold(question)
    for name in known:
        if _has(value, fold(name)):
            return name
    return None


def classification(question, context):
    """Tool intent is explicit; a remembered budget never selects a tool."""
    value = fold(question)
    categories = poi_categories(question)
    parsed = parse_budget(question)
    ordinal = ordinal_reference(question)
    pronoun = any(_has(value, term.strip()) for term in PRONOUNS)
    reference = ordinal is not None or pronoun
    has_history = bool(context and (context.last_property_ids or context.last_criteria))
    state = getattr(context,"needs",{}) if context else {}
    pending = state.get("pending")
    housing = r"(?:nha|can ho|chung cu|bat dong san|bds|dat nen|biet thu|phong tro|mat bang)"
    housing_value=re.sub(r"\b(?:nha thuoc|nha hang|nha khoa|nha kho|nha may|nha sach|nha tre)\b"," ",value)
    explicit_search = bool(re.search(r"\b(?:tim|mua|thue|goi y|de xuat|muon)\b.{0,55}\b"+housing+r"\b|\bco\s+"+housing+r"\b.{0,60}\b(?:nao|khong|phu hop)\b|\b(?:tim lai|tim tiep|xem goi y ngay|tim ngay|xem ket qua|bat dau tu van|tu van tung buoc|huong dan tung buoc|bo qua)\b",housing_value))
    priority_edit=bool(re.search(r"\b(?:uu tien|quan trong nhat|tim ky hon|bo uu tien|xoa uu tien)\b",value))
    knowledge=bool(re.search(r"\b(?:la gi|thu tuc|quy trinh|thue phi|thue truoc ba|hop dong|so do|so hong|lai suat|vay ngan hang|can luu y|kien thuc)\b",value)) and not explicit_search and not reference
    owned_budget=bool(re.search(r"\b(?:toi co|minh co|ngan sach|tai chinh|toi da|gioi han)\b",value))
    budget_edit=parsed.status!="NOT_MENTIONED" and (not reference or owned_budget or explicit_search)
    place_question=bool(categories) and not explicit_search and not reference and not priority_edit and pending!="priorities"
    # A concrete area question wins over an optional pending preference question.
    if categories and re.search(r"\b(?:o|tai|khu vuc)\b.{0,50}\b(?:co|nao)\b",value) and not explicit_search and not reference:
        place_question=True
    kind=detect_property_type(question)
    if re.search(r"\b(?:tat ca loai|moi loai|khong gioi han loai)\b",value):kind="ALL"
    purpose=detect_purpose(question)
    refinement=bool(re.search(r"\b(?:tim ky hon|goi y khac|lua chon khac|mo rong|thu hep|giu ngan sach)\b",value)) or priority_edit
    pending_search=bool(pending) and not reference
    if knowledge:intent="KNOWLEDGE"
    elif place_question:intent="AREA_AMENITIES"
    elif explicit_search or pending_search or refinement:intent="REFINE_SEARCH" if has_history else "SEARCH"
    elif reference or (is_analytic(question) and has_history):intent="PROPERTY_FOLLOWUP"
    elif budget_edit or kind is not None or purpose is not None:intent="UPDATE_CRITERIA"
    else:intent="CLARIFY"
    search_change=intent in ("SEARCH","REFINE_SEARCH")
    return {"categories":categories,"budgetChange":budget_edit and parsed.status=="VALID",
            "budgetMentioned":budget_edit,"budgetStatus":parsed.status if budget_edit else "NOT_MENTIONED",
            "ordinal":ordinal,"mapRequest":is_map_request(question),"analytic":is_analytic(question),
            "clarify":is_clarification_needed(question),"searchChange":search_change,
            "propertyType":kind,"purpose":purpose,"hasHistory":has_history,
            "needsPropertyReference":bool(intent=="PROPERTY_FOLLOWUP" and ordinal is None and not (is_map_request(question) and any(_has(value,t) for t in ("chung","cac can","nhung can")))),
            "intent":intent}
