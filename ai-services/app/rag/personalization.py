"""Explicit lifestyle preferences and single-question intake; memory-only, no inferred family traits."""
import re
from decimal import Decimal
from .intent import fold, poi_categories, CATEGORY_LABELS

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
SKIP_RE = re.compile(r"\b(?:xem goi y ngay|tim ngay|bo qua|khong can hoi them|giu tieu chi)\b")

def area_sqm(question):
    value = fold(question).replace(",", ".")
    match = re.search(r"(?<![\w.])(\d{1,5}(?:\.\d{1,2})?)\s*(?:m2|m²|met vuong|m\b)", value)
    if not match:
        match = re.fullmatch(r"\s*(\d{1,5}(?:\.\d{1,2})?)\s*", value)
    if not match:
        return None
    area = Decimal(match.group(1))
    return area if 0 < area <= 1000000 else None


def area_spec(question):
    """Return explicit area constraints without changing the legacy default.

    `minAreaSqm` remains inclusive when no operator is present (old API behavior).
    """
    value = fold(question).replace(",", ".")
    match = re.search(r"(?<![\w.])(\d{1,5}(?:\.\d{1,2})?)\s*(?:m2|m²|met vuong|m\b)", value)
    if not match:
        match = re.fullmatch(r"\s*(\d{1,5}(?:\.\d{1,2})?)\s*", value)
    if not match:
        return None
    area = Decimal(match.group(1))
    if not 0 < area <= 1000000:
        return None
    before = value[max(0, match.start() - 32):match.start()].strip()
    after = value[match.end():match.end() + 32].strip()
    if re.search(r"\b(?:tren|hon|lon hon|cao hon|nhieu hon)\s*$", before):
        return {"maxAreaSqm": None, "minAreaSqm": str(area), "minAreaExclusive": True,
                "maxAreaExclusive": False}
    if re.search(r"\b(?:duoi|nho hon|thap hon|it hon)\s*$", before):
        return {"maxAreaSqm": str(area), "minAreaSqm": None, "minAreaExclusive": False,
                "maxAreaExclusive": True}
    if re.search(r"\b(?:toi da|khong qua|khong vuot)\s*$", before) or after.startswith("tro xuong"):
        return {"maxAreaSqm": str(area), "minAreaSqm": None, "minAreaExclusive": False,
                "maxAreaExclusive": False}
    if re.search(r"\b(?:tu|toi thieu|it nhat|khong duoi)\s*$", before) or after.startswith("tro len"):
        return {"maxAreaSqm": None, "minAreaSqm": str(area), "minAreaExclusive": False,
                "maxAreaExclusive": False}
    return {"maxAreaSqm": None, "minAreaSqm": str(area), "minAreaExclusive": False,
            "maxAreaExclusive": False}


def apply_area(criteria, question):
    spec = area_spec(question)
    if spec is None:
        return False
    criteria.pop("minAreaSqm", None)
    criteria.pop("maxAreaSqm", None)
    criteria.pop("minAreaExclusive", None)
    criteria.pop("maxAreaExclusive", None)
    for key, value in spec.items():
        if value is not None:
            criteria[key] = value
    return True

def format_vnd(value):
    amount = Decimal(str(value))
    if not amount.is_finite() or amount <= 0:
        return "không hợp lệ"
    whole, _, fraction = format(amount, "f").partition(".")
    grouped = f"{int(whole):,}".replace(",", ".")
    fraction = fraction.rstrip("0")
    return f"{grouped},{fraction} VND" if fraction else f"{grouped} VND"


def family_status(value):
    if "da lap gia dinh" in value or "da ket hon" in value or "married" in value:
        return "MARRIED"
    if "chua lap gia dinh" in value or "chua ket hon" in value or "doc than" in value or "single" in value:
        return "SINGLE"
    return None

def has_children(value):
    if re.search(r"\b(?:co|dang co)\s+(?:con|tre)", value) or "co tre nho" in value:
        return True
    if "chua co con" in value or "khong co con" in value or "chua co tre" in value:
        return False
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
    cats = list(poi_categories(expanded))
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
    skip = bool(SKIP_RE.search(value))
    skip_all = bool(re.search(r"\b(?:xem goi y ngay|tim ngay)\b", value))
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
    search = housing_search(question) or bool(turn.get("budgetChange") and not cats) or refine or skip
    update = bool(cats and (explicit_priority or pending == "priorities" or (search and not turn.get("analytic"))))
    removal = bool(re.search(r"\b(?:bo uu tien|khong uu tien|xoa uu tien)\b", value))
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
            if apply_area(criteria, question):
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
            apply_area(criteria, question)
            if not any(key in criteria for key in ("minAreaSqm", "maxAreaSqm")) and not skip:
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
    apply_area(criteria, question)
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
        summary.append("Giá mua tối đa: " + format_vnd(criteria["budgetVnd"]))
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
    return {"summary": summary, "priorities": ordered, "pending": state.get("pending"), "limitations": limits,
            "schoolLevelRequested": state.get("schoolLevel")}