"""Deterministic follow-up parsing. Never infers facts; only classifies the turn.

Every decision here is a routing decision over the *question text plus stored criteria*.
No model is consulted, so a follow-up can never invent a budget or a property.
"""
import re
from decimal import Decimal

from .intent import fold, poi_categories

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
    """Only an explicit single amount; identical grammar rules to first-turn parsing."""
    lowered = question.lower()
    if len(re.findall(r"tỷ|\bty\b|triệu|\btrieu\b", lowered)) != 1:
        return None
    values = re.findall(r"(?<![\w.,])([0-9]+(?:[.,][0-9]+)?)\s*(tỷ|ty|triệu|trieu)\b(?!\s*\d)", lowered)
    if len(values) != 1:
        return None
    value, unit = values[0]
    amount = Decimal(value.replace(",", ".")) * (10 ** 9 if unit in ("tỷ", "ty") else 10 ** 6)
    return amount if 1 <= amount <= 999999999999999 else None


def ordinal_reference(question):
    """"căn thứ hai" -> 2, "căn 2" -> 2. "2 tỷ" -> None.

    An ordinal only exists when it is attached to a property noun, so amounts,
    areas and prices can never be mistaken for a position in the result list.
    """
    value = fold(question)
    numeric = re.search(
        r"(?:can|can ho|bds|bat dong san|nha|lua chon|phuong an)\s+(?:so\s+)?(?:thu\s+)?(\d{1,2})(?!\s*(?:ty|trieu|m2|m\b|phong|pn))",
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
    # A bare "nhà" only names the type when the turn is clearly about acquiring property.
    if re.search(r"(?<!\w)nha(?!\w)", value) and any(
            _has(value, t) for t in ("mua", "tim", "can", "thue", "o", "gia", "ngan sach")):
        mapping = mapping + (("nha", "HOUSE"),)
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
    """Classify one turn. `context` may be None on the first turn."""
    categories = poi_categories(question)
    has_budget = budget_from_followup(question) is not None
    ordinal = ordinal_reference(question)
    has_history = bool(context and (context.last_property_ids or context.last_criteria))
    asks_property = bool(categories) is False and not is_map_request(question)
    return {
        "categories": categories,
        "budgetChange": has_budget,
        "ordinal": ordinal,
        "mapRequest": is_map_request(question),
        "analytic": is_analytic(question),
        "clarify": is_clarification_needed(question),
        "searchChange": changes_search(question),
        "propertyType": detect_property_type(question),
        "purpose": detect_purpose(question),
        "hasHistory": has_history,
        "needsPropertyReference": bool(has_history and asks_property and ordinal is None
                                       and not categories and not has_budget and is_analytic(question)),
    }
