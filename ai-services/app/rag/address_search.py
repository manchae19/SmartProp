"""Recognising a street address in a chat question.

Three intents share the same address text but must not share a code path:

    "Tôi muốn tìm nhà ở 300 Dũng Sĩ Thanh Khê"        -> AT_ADDRESS
    "Tìm nhà gần 300 Dũng Sĩ Thanh Khê"               -> NEAR_ADDRESS
    "Gần 300 Dũng Sĩ Thanh Khê có bệnh viện nào?"     -> amenity path (not ours)

The house number is part of the address, never a budget. "300" alone is not money,
and the street name is kept whole so "Dũng Sĩ Thanh Khê" is not cut down to a district.
"""
import re
import unicodedata

# A house number followed by a street name. The number must start a token, so "3000"
# and "30" never match "300", and the street must carry at least one letter.
_ADDRESS = re.compile(
    r"(?<![\w.,])(\d{1,5}[a-zA-Z]?)\s+"
    r"((?:[^\W\d_]+\s*){1,6}?)"
    r"(?=\s*(?:,|\.|$|\b(?:co|khong|nao|giup|tim|gia|va|o|tai|gan)\b))",
    re.UNICODE,
)

# Words that look like a street but are really a search filter.
_NOT_STREET = {
    "ty", "trieu", "phong", "ngu", "pn", "wc", "m2", "met", "vuong", "tang", "lau",
    "can", "nha", "dat", "chung", "cu", "biet", "thu", "mat", "tien", "hem", "kiet",
}

_AT = re.compile(r"\b(?:o|tai|tren|thuoc|xem)\b")
_NEAR = re.compile(r"\b(?:gan|quanh|ke|sat)\b")
_HOUSE = re.compile(r"\b(?:nha|can ho|chung cu|nha pho|nha rieng|biet thu|dat nen|bat dong san)\b")
_AMENITY = re.compile(
    r"\b(?:benh vien|truong|tieu hoc|trung hoc|dai hoc|sieu thi|nha thuoc|"
    r"cong vien|bai bien|xe buyt|ben xe|phong kham|y te|giao duc|sieu thi)\b")


def fold(text):
    """Lowercase, strip Vietnamese diacritics, collapse whitespace."""
    value = unicodedata.normalize("NFD", str(text or ""))
    value = "".join(ch for ch in value if unicodedata.category(ch) != "Mn")
    value = value.replace("đ", "d").replace("Đ", "D")
    return re.sub(r"\s+", " ", value.lower()).strip()


def _clean_street(raw):
    words = [w for w in re.split(r"\s+", raw.strip()) if w]
    kept = []
    for word in words:
        if fold(word) in _NOT_STREET:
            break
        kept.append(word)
    return " ".join(kept).strip(" ,.")


def address_in(question):
    """The address the user typed, with its house number, or None.

    Returns the text as written (diacritics preserved) so it can be echoed back and
    sent to the backend filter unchanged.
    """
    text = str(question or "")
    for match in _ADDRESS.finditer(text):
        number, street = match.group(1), _clean_street(match.group(2))
        if not street or len(street) < 3:
            continue
        if not re.search(r"[^\W\d_]", street, re.UNICODE):
            continue
        return f"{number} {street}".strip()
    return None


def intent(question):
    """AT_ADDRESS, NEAR_ADDRESS, or None when this is not an address lookup."""
    folded = fold(question)
    address = address_in(question)
    if address is None:
        return None
    # An amenity question keeps its own path even when it names an address.
    if _AMENITY.search(folded):
        return None
    if _NEAR.search(folded):
        return "NEAR_ADDRESS"
    if _AT.search(folded) or _HOUSE.search(folded):
        return "AT_ADDRESS"
    return None


def house_number(address):
    match = re.match(r"\s*(\d{1,5}[a-zA-Z]?)", str(address or ""))
    return match.group(1) if match else None


def street_of(address):
    match = re.match(r"\s*\d{1,5}[a-zA-Z]?\s+(.*)$", str(address or ""))
    return match.group(1).strip() if match else ""


def matches(address, wanted):
    """True when a listing address carries the same house number and street.

    Diacritics, case and spacing are ignored; the house number must be equal, so
    "30" and "3000" never match "300".
    """
    left, right = fold(address), fold(wanted)
    if not left or not right:
        return False
    number = house_number(wanted)
    street = fold(street_of(wanted))
    if number is None or not street:
        return False
    if house_number(left) != fold(number):
        return False
    return street in left
