"""Explicit lifestyle preferences and single-question intake; memory-only, no inferred family traits."""
import re
from decimal import Decimal
from .intent import fold, poi_categories, CATEGORY_LABELS
from .money import format_vnd

PRIORITY_CHOICES = ["Trường học", "Chợ / siêu thị", "Y tế", "Công viên", "Giao thông công cộng", "Xem gợi ý ngay"]
PURPOSE_CHOICES = ["Mua để ở", "Mua đầu tư", "Thuê để ở", "Bỏ qua"]
PROPERTY_TYPE_CHOICES = ["Nhà phố", "Căn hộ", "Đất nền", "Biệt thự", "Phòng trọ", "Mặt bằng", "Tất cả"]
AREA_CHOICES = ["30 m²", "50 m²", "80 m²", "100 m²", "Bỏ qua"]
FAMILY_CHOICES = ["Đã lập gia đình", "Chưa lập gia đình", "Bỏ qua"]
CHILDREN_CHOICES = ["Có trẻ nhỏ", "Chưa có trẻ nhỏ", "Bỏ qua"]
CHILDREN_NEEDS_CHOICES = ["Có, ưu tiên trường học và công viên", "Không cần", "Bỏ qua"]
AGE_CHOICES = ["Dưới 25", "25–34", "35–44", "45–54", "55 trở lên", "Không muốn cung cấp"]
GUIDED_RE = re.compile(r"\b(?:tu van tung buoc|bat dau tu van|tu van theo tung buoc|huong dan tung buoc)\b")
HOUSEHOLD_RE = re.compile(r"\b(?:tu van theo ho gia dinh|ho gia dinh|con nho|tre nho)\b")
SKIP_RE = re.compile(r"\b(?:bo qua|khong can hoi them|giu tieu chi)\b")

AREA_LIMIT = Decimal("1000000")
_AREA_NUMBER = r"([+-]?\d+(?:\.\d+)*)"
# Only square-metre units count. A bare "m" is a width or a distance ("hẻm 5m",
# "mặt tiền 5m", "cách 500m") and must never become an area filter.
_AREA_UNIT = r"\s*(?:m2|m²|met vuong|m vuong)(?!\w)"
_AREA_RANGE = re.compile(r"(?<![\w.+-])(?:tu\s*)?" + _AREA_NUMBER + r"(?:" + _AREA_UNIT + r")?\s*(?:den|toi|-|~)\s*"
                         + _AREA_NUMBER + _AREA_UNIT)
_AREA_VALUE = re.compile(r"(?<![\w.+-])" + _AREA_NUMBER + _AREA_UNIT)
AREA_COMPARISON = (r"(?:nho hon|thap hon|it hon|be hon|lon hon|cao hon|nhieu hon|rong hon|"
                   r"toi da|khong qua|khong vuot|nhieu nhat|toi thieu|it nhat|duoi|tren|hon|tu)")
_AREA_TERM = rf"(?:{AREA_COMPARISON}\s+)?{_AREA_NUMBER}(?:{_AREA_UNIT})?"
_SHARED_AREA = re.compile(
    rf"\b(?={AREA_COMPARISON}\s+)(?:{_AREA_TERM}\s*(?:\b(?:va|hoac|hay)\b|[,;])\s*)+"
    rf"(?:{AREA_COMPARISON}\s+)?{_AREA_NUMBER}{_AREA_UNIT}"
)
_AREA_TERM_PARTS = re.compile(rf"(?:(?P<operator>{AREA_COMPARISON})\s+)?(?P<number>{_AREA_NUMBER})(?:{_AREA_UNIT})?")
_AREA_MENTION = re.compile(r"\d+(?:[.,]\d+)*" + _AREA_UNIT)
_NON_AREA_PREFIX = re.compile(
    r"\b(?:ngan sach|gia(?: mua| ban| thue)?|khoang cach|chieu rong|mat tien|so phong)\s*$"
)


def _area(raw):
    if not re.fullmatch(r"\d{1,7}(?:\.\d{1,2})?", raw):
        return None
    value = Decimal(raw)
    return value if 0 < value <= AREA_LIMIT else None


def _plain(value):
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _constrain(spec, side, area, exclusive=False):
    bound, flag = side + "AreaSqm", side + "AreaExclusive"
    previous = Decimal(spec[bound]) if spec.get(bound) is not None else None
    if previous is None or (area > previous if side == "min" else area < previous):
        spec.update({bound: _plain(area), flag: exclusive})
    elif area == previous and exclusive:
        spec[flag] = True


def _valid_area_bounds(spec):
    low, high = spec.get("minAreaSqm"), spec.get("maxAreaSqm")
    if low is None or high is None:
        return True
    low, high = Decimal(low), Decimal(high)
    return low < high or (low == high and not (spec.get("minAreaExclusive") or spec.get("maxAreaExclusive")))


def area_spec(question, *, allow_bare=False):
    """Explicit floor/ceiling area constraints stated in one message, or None.

    "trên/hơn X" is a strict floor, "dưới/nhỏ hơn X" a strict ceiling, "tối đa/không quá
    X" an inclusive ceiling and "từ/tối thiểu X" or a bare "X m²" an inclusive floor (the
    legacy meaning). "từ A đến B m²" is an inclusive range. A bare number counts only when
    the caller is answering an explicit area question (`allow_bare`).
    """
    value = re.sub(r"(?<=\d),(?=\d)", ".", fold(question)).replace("–", "-").replace("—", "-")
    spec = {"minAreaSqm": None, "maxAreaSqm": None, "minAreaExclusive": False, "maxAreaExclusive": False}

    # Only a contiguous chain of comparators can borrow its final area unit.
    # A price, room count or linear measurement interrupts that chain.
    for shared in reversed(list(_SHARED_AREA.finditer(value))):
        parts = list(_AREA_TERM_PARTS.finditer(shared[0]))
        if _NON_AREA_PREFIX.search(value[:shared.start()]) or re.search(r"\b(?:hoac|hay)\b", shared[0]) or any(
            not part["operator"] or _area(part["number"]) is None for part in parts
        ):
            return None
        expanded = " va ".join(f"{part['operator']} {part['number']} m2" for part in parts)
        value = value[:shared.start()] + expanded + value[shared.end():]

    ranges = list(_AREA_RANGE.finditer(value))
    for ranged in ranges:
        low, high = _area(ranged[1]), _area(ranged[2])
        if low is None or high is None or low > high:
            return None
        _constrain(spec, "min", low)
        _constrain(spec, "max", high)
    value = _AREA_RANGE.sub(lambda match: " " * len(match[0]), value)
    found = bool(ranges)
    for match in _AREA_VALUE.finditer(value):
        area = _area(match.group(1))
        if area is None:
            return None
        before = value[max(0, match.start() - 32):match.start()].strip()
        after = value[match.end():match.end() + 32].strip()
        if re.search(r"\b(?:duoi|nho hon|thap hon|it hon|be hon)\s*$", before):
            _constrain(spec, "max", area, True)
        elif re.search(r"\b(?:toi da|khong qua|khong vuot|nhieu nhat)\s*$", before) or after.startswith("tro xuong"):
            _constrain(spec, "max", area)
        elif re.search(r"\b(?:tren|hon|lon hon|cao hon|nhieu hon|rong hon)\s*$", before):
            _constrain(spec, "min", area, True)
        else:
            _constrain(spec, "min", area)
        found = True
    if not found and allow_bare:
        bare = re.fullmatch(r"\s*" + _AREA_NUMBER + r"\s*", value)
        area = _area(bare.group(1)) if bare else None
        if area is None:
            return None
        spec.update(minAreaSqm=_plain(area))
        found = True
    return spec if found and _valid_area_bounds(spec) else None


AREA_KEYS = ("minAreaSqm", "maxAreaSqm", "minAreaExclusive", "maxAreaExclusive")


def invalid_area_text(question):
    return bool(_AREA_MENTION.search(fold(question)) and area_spec(question) is None)


def apply_area(criteria, question, *, allow_bare=False):
    """Replace the whole area constraint when the message states a new one."""
    spec = area_spec(question, allow_bare=allow_bare)
    if spec is None:
        return False
    for key in AREA_KEYS:
        criteria.pop(key, None)
    for key, value in spec.items():
        # The Backend request uses primitive booleans; send a flag only when it is set.
        if value is not None and value is not False:
            criteria[key] = value
    return True


def merge_area(criteria, prior, question, *, allow_bare=False):
    """New bounds replace the prior group. Text and structured bounds on one turn intersect."""
    spec = area_spec(question, allow_bare=allow_bare)
    if spec is None and _AREA_MENTION.search(fold(question)):
        return False
    bounds = {key: criteria[key] for key in AREA_KEYS if key in criteria}
    if spec:
        for side in ("min", "max"):
            if (area := spec[side + "AreaSqm"]) is not None:
                _constrain(bounds, side, Decimal(area), spec[side + "AreaExclusive"])
        if not _valid_area_bounds(bounds):
            return False
    elif not bounds:
        bounds = {key: prior[key] for key in AREA_KEYS if key in prior}
    criteria.update(bounds)
    for key in ("minAreaSqm", "maxAreaSqm"):
        if key in criteria:
            criteria[key] = str(criteria[key])
    return True


def matches_area(area, criteria):
    if not any(criteria.get(key) is not None for key in ("minAreaSqm", "maxAreaSqm")):
        return True
    if area is None:
        return False
    area = Decimal(str(area))
    if not area.is_finite() or area <= 0:
        return False
    for key, exclusive, sign in (("minAreaSqm", "minAreaExclusive", 1),
                                 ("maxAreaSqm", "maxAreaExclusive", -1)):
        if criteria.get(key) is not None:
            difference = sign * (area - Decimal(str(criteria[key])))
            if difference < 0 or (difference == 0 and criteria.get(exclusive)):
                return False
    return True


def describe_area(criteria):
    low, high = criteria.get("minAreaSqm"), criteria.get("maxAreaSqm")
    if low and high:
        if criteria.get("minAreaExclusive") or criteria.get("maxAreaExclusive"):
            minimum = "trên" if criteria.get("minAreaExclusive") else "từ"
            maximum = "dưới" if criteria.get("maxAreaExclusive") else "tối đa"
            return f"diện tích {minimum} {low} đến {maximum} {high} m²"
        return f"diện tích từ {low} đến {high} m²"
    if low:
        return ("diện tích trên " if criteria.get("minAreaExclusive") else "diện tích từ ") + f"{low} m²"
    if high:
        return ("diện tích dưới " if criteria.get("maxAreaExclusive") else "diện tích tối đa ") + f"{high} m²"
    return None

def family_status(value):
    if "da lap gia dinh" in value or "da ket hon" in value or "married" in value:
        return "MARRIED"
    if "chua lap gia dinh" in value or "chua ket hon" in value or "doc than" in value or "single" in value:
        return "SINGLE"
    return None

def has_children(value):
    if any(term in value for term in ("chua co con", "khong co con", "chua co tre", "khong co tre")):
        return False
    if re.search(r"\b(?:co|dang co)\s+(?:con|tre)", value) or "co tre nho" in value:
        return True
    return None

def age_group(value):
    if "khong muon" in value or "prefer" in value:
        return "PREFER_NOT_TO_SAY"
    if "duoi 25" in value:
        return "UNDER_25"
    if re.search(r"25\s*[-–]\s*34", value):
        return "AGE_25_34"
    if re.search(r"35\s*[-–]\s*44", value):
        return "AGE_35_44"
    if re.search(r"45\s*[-–]\s*54", value):
        return "AGE_45_54"
    if "55" in value and ("tro len" in value or "+" in value):
        return "AGE_55_PLUS"
    return None

def add_household_school(state, criteria):
    priorities = list(state.get("priorities", []))
    for category in ("PARK", "SCHOOL"):
        if category not in priorities:
            priorities.insert(0, category)
    state["priorities"] = priorities[:4]
    criteria["amenityPriorities"] = list(state["priorities"])

def housing_search(question):
    value = fold(question)
    return bool(re.search(r"\b(?:can ho|chung cu|nha pho|nha rieng|bat dong san|biet thu|dat nen|tim nha|mua nha)\b", value))

def preferences(question):
    value = fold(question)
    # Generic health choice has no more specific provider category than HOSPITAL.
    expanded = question + (" bệnh viện" if re.search(r"\by te\b", value) else "")
    cats = [c for c in poi_categories(expanded) if c != "MALL"]
    positions = {}
    terms = {"SCHOOL": ["truong", "tieu hoc", "giao duc"], "SUPERMARKET": ["sieu thi"],
             "MARKET": ["cho"], "HOSPITAL": ["benh vien", "y te", "phong kham"],
             "PHARMACY": ["nha thuoc"], "PARK": ["cong vien"], "BEACH": ["bai bien"],
             "PUBLIC_TRANSPORT": ["xe buyt", "ben xe", "giao thong cong cong"]}
    for c in cats:
        positions[c] = min((m.start() for term in terms[c] for m in re.finditer(r"\b"+term+r"\b", value)), default=9999)
    ordered = sorted(cats, key=lambda c: positions[c])
    # A clearly marked primary preference takes precedence over mention order.
    main = re.search(r"(?:uu tien chinh|quan trong nhat)\s+(.+?)(?:[,;.]|$)", value)
    if main:
        primary = set(poi_categories(main.group(1)))
        ordered.sort(key=lambda c: (c not in primary, positions[c]))
    return ordered[:4]

def intake(context, question, criteria, turn, *, explicit_district=None):
    value = fold(question)
    state = context.needs
    pending = state.get("pending")
    skip_all = bool(re.search(r"\b(?:xem goi y ngay|tim ngay)\b", value))
    skip = skip_all or bool(pending and SKIP_RE.search(value))
    refine = "tim ky hon" in value
    explicit_priority = bool(re.search(r"\b(?:uu tien|quan trong|thi tot|gan truong|gan sieu thi)\b", value))
    guided = bool(state.get("guided") or GUIDED_RE.search(value))
    if guided:
        state["guided"] = True
    household = bool(state.get("householdMode") or HOUSEHOLD_RE.search(value))
    if household:
        state["householdMode"] = True
        guided = True
    cats = preferences(question)
    search = bool(turn.get("searchChange")) or (housing_search(question) and not turn.get("ordinal") and not turn.get("needsPropertyReference")) or refine or skip
    update = bool(cats and (explicit_priority or pending == "priorities" or (search and not turn.get("analytic"))))
    removal = bool(re.search(r"\b(?:bo uu tien|khong uu tien|xoa uu tien|bo dieu kien gan)\b", value))
    active = search or update or removal or bool(pending) or guided
    # Explicit amenity questions continue along the existing POI path.
    if cats and not update and not search and not removal and not guided:
        return {"search": False, "question": None, "choices": []}
    if not active:
        return {"search": False, "question": None, "choices": []}
    state["active"] = True
    if explicit_district or "da nang" in value:
        state["locationKnown"] = True
    if re.search(r"\b(?:tp\.? hcm|ho chi minh|ha noi|ha phong)\b", value):
        state["pending"] = "location"
        return {"search": True, "question": "SmartProp hiện hỗ trợ Đà Nẵng. Bạn muốn chọn khu vực nào tại Đà Nẵng?", "choices": ["Toàn Đà Nẵng"]}
    if "toan da nang" in value or "tat ca khu vuc" in value:
        criteria.pop("district", None)
        criteria.pop("ward", None)
        state["locationKnown"] = True
    if skip and pending == "location":
        state["locationKnown"] = True
        state["pending"] = None
    if pending == "budget" and criteria.get("budgetVnd"):
        state["pending"] = None
    if pending == "location" and (state.get("locationKnown") or criteria.get("district") or skip):
        state["pending"] = None
    if explicit_priority and not cats and not removal:
        state["unmappedPreference"] = question[:160]
    if pending == "priorities" and not cats and not skip and not refine:
        state["unmappedPreference"] = question[:160]
    if removal:
        selected = state.get("priorities", [])
        state["priorities"] = [c for c in selected if c not in cats] if cats else []
    elif update:
        state.pop("unmappedPreference", None)
        if ("them " in value or " hon " in value) and state.get("priorities"):
            state["priorities"] = list(dict.fromkeys((cats+state["priorities"]) if " hon " in value else (state["priorities"]+cats)))[:4]
        else:
            state["priorities"] = cats
        state["askedPriorities"] = True
        state.pop("profileLabels", None)
        state["profileUsed"] = False
    if "tieu hoc" in value and update:
        state["schoolLevel"] = "tiểu học"
    if update and "SCHOOL" not in state.get("priorities", []):
        state.pop("schoolLevel", None)
    if state.get("priorities"):
        criteria["amenityPriorities"] = list(state["priorities"])
    else:
        criteria.pop("amenityPriorities", None)

    if guided:
        # Guided mode: purpose → budget → district → type → min area → optional household → priorities.
        if pending == "purpose":
            if turn.get("purpose"):
                criteria["purpose"] = turn["purpose"]
                state["purposeAsked"] = True
                state["pending"] = None
            elif skip:
                state["purposeAsked"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Bạn muốn mua để ở, mua đầu tư, hay thuê để ở?", "choices": PURPOSE_CHOICES}
        elif pending == "property_type":
            if turn.get("propertyType"):
                criteria["propertyType"] = turn["propertyType"]
                state["typeAsked"] = True
                state["pending"] = None
            elif skip or "tat ca" in value:
                criteria["propertyType"] = "ALL"
                state["typeAsked"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Bạn muốn tìm loại bất động sản nào?", "choices": PROPERTY_TYPE_CHOICES}
        elif pending == "min_area":
            if any(criteria.get(key) is not None for key in ("minAreaSqm", "maxAreaSqm")):
                state["areaAsked"] = True
                state["pending"] = None
            elif skip:
                state["areaAsked"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Diện tích tối thiểu bạn cần là bao nhiêu m²? Nhập số hoặc chọn bên dưới.", "choices": AREA_CHOICES}
        elif pending == "family":
            status = family_status(value)
            if status:
                state["familyStatus"] = status
                state["familyStatusProvided"] = True
                state["pending"] = None
            elif skip:
                state["familyStatusProvided"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Tình trạng gia đình của bạn? (tùy chọn, có thể bỏ qua)", "choices": FAMILY_CHOICES}
        elif pending == "children":
            children = has_children(value)
            if children is not None:
                state["householdProfile"] = children
                state["childrenAnswered"] = True
                if children:
                    add_household_school(state, criteria)
                state["pending"] = None
            elif skip:
                state["householdProfile"] = False
                state["childrenAnswered"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Bạn có trẻ nhỏ cần gần trường học không? (tùy chọn)", "choices": CHILDREN_CHOICES}
        elif pending == "age":
            age = age_group(value)
            if age:
                state["ageGroup"] = age
                state["ageGroupProvided"] = True
                state["pending"] = None
            elif skip:
                state["ageGroupProvided"] = True
                state["pending"] = None
            else:
                return {"search": True, "question": "Bạn muốn chia sẻ nhóm tuổi để gợi ý phù hợp hơn không? (tùy chọn)", "choices": AGE_CHOICES}
        elif pending == "children_needs":
            if skip or "khong can" in value:
                state["childrenNeedsConfirmation"] = False
                state["pending"] = None
            elif any(term in value for term in ("co", "uu tien", "truong", "cong vien")):
                add_household_school(state, criteria)
                state["childrenNeedsConfirmation"] = False
                state["pending"] = None
            else:
                return {"search": True, "question": "Hồ sơ cho biết bạn có trẻ nhỏ. Bạn có muốn ưu tiên trường học và công viên không?", "choices": CHILDREN_NEEDS_CHOICES}

        # "Bỏ qua" skips only the current question; "Xem gợi ý ngay" skips the remaining intake.
        if skip_all:
            skip = True
        elif skip:
            skip = False
        if not state.get("purposeAsked"):
            if turn.get("purpose"):
                criteria["purpose"] = turn["purpose"]
                state["purposeAsked"] = True
            elif not skip:
                state["purposeAsked"] = True
                state["pending"] = "purpose"
                return {"search": True, "question": "Bạn muốn mua để ở, mua đầu tư, hay thuê để ở?", "choices": PURPOSE_CHOICES}
            else:
                state["purposeAsked"] = True
        if not criteria.get("budgetVnd"):
            state["pending"] = "budget"
            return {"search": True, "question": "Bạn muốn giới hạn tổng giá mua tối đa khoảng bao nhiêu? Tôi sẽ không tìm vượt mức bạn nhập.", "choices": ["2 tỷ", "3 tỷ", "5 tỷ", "10 tỷ", "Bỏ qua"]}
        if not state.get("locationKnown") and not criteria.get("district") and not skip:
            state["pending"] = "location"
            return {"search": True, "question": "Bạn muốn tìm ở khu vực nào tại Đà Nẵng?", "choices": ["Toàn Đà Nẵng", "Hải Châu", "Sơn Trà", "Cẩm Lệ", "Xem gợi ý ngay"]}
        if not state.get("typeAsked"):
            if turn.get("propertyType"):
                criteria["propertyType"] = turn["propertyType"]
                state["typeAsked"] = True
            elif criteria.get("propertyType", "ALL") == "ALL" and not skip:
                state["typeAsked"] = True
                state["pending"] = "property_type"
                return {"search": True, "question": "Bạn muốn tìm loại bất động sản nào?", "choices": PROPERTY_TYPE_CHOICES}
            else:
                state["typeAsked"] = True
        if not state.get("areaAsked"):
            if not any(criteria.get(key) is not None for key in ("minAreaSqm", "maxAreaSqm")) and not skip:
                state["areaAsked"] = True
                state["pending"] = "min_area"
                return {"search": True, "question": "Diện tích tối thiểu bạn cần là bao nhiêu m²? Nhập số hoặc chọn bên dưới.", "choices": AREA_CHOICES}
            state["areaAsked"] = True
        if context.scope.startswith("ACCOUNT:") and state.get("profileUsed") and state.get("childrenNeedsConfirmation"):
            state["pending"] = "children_needs"
            return {"search": True, "question": "Hồ sơ cho biết bạn có trẻ nhỏ. Bạn có muốn ưu tiên trường học và công viên không?", "choices": CHILDREN_NEEDS_CHOICES}
        if household and context.scope.startswith("ACCOUNT:") and state.get("profileUsed"):
            if not state.get("familyStatusProvided"):
                state["pending"] = "family"
                return {"search": True, "question": "Tình trạng gia đình của bạn? (tùy chọn, có thể bỏ qua)", "choices": FAMILY_CHOICES}
            if state.get("householdProfile") is None and not state.get("childrenAnswered"):
                state["pending"] = "children"
                return {"search": True, "question": "Bạn có trẻ nhỏ cần gần trường học không? (tùy chọn)", "choices": CHILDREN_CHOICES}
            if not state.get("ageGroupProvided"):
                state["pending"] = "age"
                return {"search": True, "question": "Bạn muốn chia sẻ nhóm tuổi để gợi ý phù hợp hơn không? (tùy chọn)", "choices": AGE_CHOICES}
        if not state.get("askedPriorities") and not skip:
            state["askedPriorities"] = True
            state["pending"] = "priorities"
            return {"search": True, "question": "Điều gì quan trọng nhất với bạn khi chọn vị trí nhà?", "choices": PRIORITY_CHOICES}
        state["pending"] = None
        return {"search": True, "question": None, "choices": []}

    # Free-form mode keeps the existing behaviour for backward compatibility.
    if not criteria.get("budgetVnd"):
        state["pending"] = "budget"
        return {"search": True, "question": "Bạn muốn giới hạn tổng giá mua tối đa khoảng bao nhiêu? Tôi sẽ không tìm vượt mức bạn nhập.", "choices": []}
    if not state.get("locationKnown") and not criteria.get("district") and criteria.get("propertyType", "ALL") != "ALL" and not skip:
        state["pending"] = "location"
        return {"search": True, "question": "Bạn muốn tìm ở khu vực nào tại Đà Nẵng, hoặc thường xuyên cần đến đâu?", "choices": ["Toàn Đà Nẵng", "Hải Châu", "Sơn Trà", "Cẩm Lệ", "Xem gợi ý ngay"]}
    family = "gia dinh" in value
    if refine or ((family or pending == "location") and not state.get("askedPriorities") and not update and not skip):
        state["askedPriorities"] = True
        state["pending"] = "priorities"
        return {"search": True, "question": "Điều gì quan trọng nhất với bạn khi chọn vị trí nhà?", "choices": PRIORITY_CHOICES}
    state["pending"] = None
    return {"search": True, "question": None, "choices": []}

def projection(context, criteria):
    state = context.needs
    ordered = list(state.get("priorities", []))
    types = {"APARTMENT": "Căn hộ", "HOUSE": "Nhà ở", "LAND": "Đất nền", "VILLA": "Biệt thự", "ALL": "Mọi loại nhà"}
    summary = []
    if criteria.get("budgetVnd"):
        summary.append("Giá mua tối đa: " + format_vnd(criteria["budgetVnd"]) + " (không tự nâng)")
        if criteria.get("minPriceVnd"):
            summary.append("Giá mua tối thiểu: " + format_vnd(criteria["minPriceVnd"]))
    if area := describe_area(criteria):
        summary.append(area)
    summary.append(types.get(criteria.get("propertyType", "ALL"), criteria.get("propertyType", "ALL")))
    summary.append("Khu vực: " + (criteria.get("district") or "Đà Nẵng") + (", " + criteria["ward"] if criteria.get("ward") else ""))
    if state.get("profileUsed"):
        summary.append("Đang dùng nhu cầu đã lưu: " + ", ".join(state.get("profileLabels", []))[:220])
    if ordered:
        summary.append("Ưu tiên chính: " + CATEGORY_LABELS[ordered[0]])
        if len(ordered)>1:
            summary.append("Ưu tiên tiếp theo: " + ", ".join(CATEGORY_LABELS[c] for c in ordered[1:]))
    limits = []
    if state.get("profilePriorityLimit"):
        limits.append("Đã lưu mọi lựa chọn; lượt tìm hiện tại chỉ chấm tối đa 4 nhóm có dữ liệu, ưu tiên mục được chọn là quan trọng nhất.")
    if state.get("unsupportedProfileNeeds"):
        limits.append("Đã lưu nhưng chưa dùng chấm điểm vì chưa có dữ liệu phù hợp: " + ", ".join(state["unsupportedProfileNeeds"]))
    if state.get("profileUsed"):
        limits.append("Thay đổi ưu tiên trong chat chỉ áp dụng cho phiên này; hồ sơ chỉ đổi khi bạn lưu tại Tài khoản.")
    if state.get("unmappedPreference"):
        summary.append("Nhu cầu bổ sung: " + state["unmappedPreference"] )
        limits.append("Nhu cầu bổ sung đã ghi nhận nhưng chưa có dữ liệu chấm điểm tương ứng; chưa áp dụng vào thứ tự kết quả.")
    if ordered:
        limits.append("Ưu tiên dùng để xếp hạng theo bằng chứng cấp khu vực, không phải điều kiện bắt buộc hoặc khoảng cách từ từng căn nhà.")
    if "HOSPITAL" in ordered:
        limits.append("Nguồn y tế ở mức nhóm HOSPITAL; chưa xác minh riêng phòng khám hoặc khoảng cách từ căn nhà.")
    if "SCHOOL" in ordered:
        limits.append("Nguồn SCHOOL chỉ xác nhận trường học nói chung; chưa xác nhận trường tiểu học hoặc trường phù hợp cụ thể.")
    if any(c in ordered for c in ("SUPERMARKET", "MARKET")):
        limits.append("Điểm chợ/siêu thị dựa trên nhóm nhu yếu phẩm ở khu vực khi có bằng chứng tương ứng, không phải điểm hay khoảng cách đến siêu thị riêng.")
    return {"fromProfile": bool(state.get("profileUsed")), "summary": summary, "priorities": ordered, "pending": state.get("pending"), "limitations": limits,
            "schoolLevelRequested": state.get("schoolLevel")}
