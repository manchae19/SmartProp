"""Answers about the single listing the user is currently looking at.

Every fact comes from the public property API or the public POI/commute endpoints.
Nothing is inferred: a missing value is reported as missing, and a straight-line
distance is always labelled as such.
"""
import re
import unicodedata
from decimal import Decimal

from .config import GroundingError
from .money import format_vnd

PRICE = re.compile(r"\b(?:gia|bao nhieu|gia bao nhieu|gia rao|gia ban)\b")
AMENITY = re.compile(r"\b(?:benh vien|y te|truong|truong hoc|cho|sieu thi|cong vien|tien ich|gan gi)\b")
COMMUTE = re.compile(r"\b(?:di lam|di den cho lam|thoi gian di|mat bao lau|bao xa|commute|cho lam)\b")
AREA = re.compile(r"\b(?:dien tich|bao nhieu m2|may m2)\b")

AMENITY_CATEGORIES = {
    "benh vien": "HOSPITAL", "y te": "HOSPITAL", "clinic": "CLINIC",
    "truong": "SCHOOL", "truong hoc": "SCHOOL",
    "cho": "MARKET", "sieu thi": "SUPERMARKET",
    "cong vien": "PARK",
}


def fold(text):
    return "".join(c for c in unicodedata.normalize("NFD", (text or "").lower().replace("đ", "d"))
                   if not unicodedata.combining(c))


def focused_intent(question):
    """Which fact about the focused listing the user asked for, or None."""
    text = fold(question)
    if COMMUTE.search(text):
        return "COMMUTE"
    # Area is checked before price: "diện tích bao nhiêu" contains "bao nhiêu".
    if AREA.search(text):
        return "AREA"
    if PRICE.search(text):
        return "PRICE"
    if AMENITY.search(text):
        return "AMENITY"
    return None


def amenity_category(question):
    text = fold(question)
    for phrase, category in AMENITY_CATEGORIES.items():
        if re.search(r"(?<!\w)" + re.escape(phrase) + r"(?!\w)", text):
            return category
    return None


def _price_line(property_detail):
    price = Decimal(str(property_detail["priceVnd"]))
    parts = [f"Giá rao của tin này là {format_vnd(price)}"]
    area = property_detail.get("areaSqm")
    if area:
        per_sqm = (price / Decimal(str(area))).quantize(Decimal("1"))
        parts.append(f"tương đương khoảng {format_vnd(per_sqm)}/m² cho {area:g} m²")
    return ", ".join(parts) + "."


def _location_line(property_detail):
    bits = [b for b in (property_detail.get("ward"), property_detail.get("district")) if b]
    return ("Vị trí: " + ", ".join(bits) + ".") if bits else "Tin này chưa có thông tin phường/quận."


def price_answer(property_detail):
    return " ".join([_price_line(property_detail), _location_line(property_detail)])


def area_answer(property_detail):
    area = property_detail.get("areaSqm")
    if not area:
        return "Tin này chưa có dữ liệu diện tích."
    return f"Diện tích của tin này là {area:g} m². {_location_line(property_detail)}"


def amenity_answer(property_detail, pois, category):
    """`pois` is the public POI list; distance is straight-line, never travel time."""
    if not pois:
        return ("Chưa có dữ liệu tiện ích cho tin này trong bán kính tra cứu. "
                "Hệ thống không suy đoán tiện ích gần nhất khi chưa có bằng chứng.")
    wanted = [p for p in pois if category is None or p["category"] == category]
    if not wanted:
        label = category or "tiện ích"
        return (f"Chưa có dữ liệu {label} cho tin này trong bán kính tra cứu. "
                "Hệ thống không suy đoán khi chưa có bằng chứng.")
    wanted = sorted(wanted, key=lambda p: p["distanceMeters"])[:3]
    lines = [f"- {p['name']} ({p['category']}), khoảng {p['distanceMeters']:.0f} m" for p in wanted]
    return ("Các tiện ích gần nhất theo dữ liệu SmartProp (khoảng cách đường chim bay, "
            "không phải thời gian di chuyển):\n" + "\n".join(lines))


VENDOR_LABELS = {"OPENROUTESERVICE": "openrouteservice (HeiGIT)", "GEOAPIFY": "Geoapify"}


def commute_answer(property_detail, commute, mode, threshold_minutes=None):
    if commute is None:
        return "Chưa tính được thời gian đi làm cho tin này."
    minutes = commute["durationSeconds"] / 60.0
    km = commute["distanceMeters"] / 1000.0
    vehicle = "đi bộ" if mode == "walk" else "ô tô"
    # Name the vendor that actually produced the number; never a hardcoded brand.
    vendor = VENDOR_LABELS.get(commute.get("provider") or "", "dịch vụ tính tuyến")
    line = (f"Từ tin này tới điểm làm việc bạn đã xác nhận: khoảng {km:.1f} km, "
            f"ước tính {minutes:.0f} phút bằng {vehicle} "
            f"(thời gian di chuyển ước tính theo {vendor}).")
    if threshold_minutes is not None:
        verdict = "trong mốc" if minutes <= threshold_minutes else "vượt mốc"
        line += f" Tuyến này {verdict} {threshold_minutes} phút."
    return line


def commute_threshold(question):
    """A '25 phút' style threshold the user set, or None."""
    match = re.search(r"(\d{1,3})\s*phut", fold(question))
    if not match:
        return None
    value = int(match.group(1))
    return value if 1 <= value <= 180 else None


def wants_commute(question):
    return bool(COMMUTE.search(fold(question)))
