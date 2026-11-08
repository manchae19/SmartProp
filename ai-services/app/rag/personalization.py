"""Explicit lifestyle preferences and single-question intake; memory-only, no inferred family traits."""
import re
from .intent import fold, poi_categories, CATEGORY_LABELS

PRIORITY_CHOICES = ["Trường học", "Chợ / siêu thị", "Y tế", "Công viên", "Xem gợi ý ngay"]

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
    skip = bool(re.search(r"\b(?:xem goi y ngay|tim ngay|bo qua|khong can hoi them|giu tieu chi)\b", value))
    refine = "tim ky hon" in value
    explicit_priority = bool(re.search(r"\b(?:uu tien|quan trong|thi tot|gan truong|gan sieu thi)\b", value))
    cats = preferences(question)
    search = housing_search(question) or bool(turn.get("budgetChange") and not cats) or refine or skip
    update = bool(cats and (explicit_priority or pending == "priorities" or (search and not turn.get("analytic"))))
    removal = bool(re.search(r"\b(?:bo uu tien|khong uu tien|xoa uu tien)\b", value))
    active = search or update or removal or bool(pending)
    # Explicit amenity questions continue along the existing POI path.
    if cats and not update and not search and not removal:
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
        budget = str(criteria["budgetVnd"])
        summary.append("Giá mua tối đa: " + budget + " VND (không tự nâng)")
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