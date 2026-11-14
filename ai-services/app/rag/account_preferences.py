"""Server-read, consent-gated profile defaults. No biography is sent to the model."""
from hashlib import sha256
from .intent import fold
import json

MAPPING = {
    "MARKET": "MARKET", "SUPERMARKET": "SUPERMARKET",
    "KINDERGARTEN": "SCHOOL", "PRIMARY_SCHOOL": "SCHOOL", "SECONDARY_SCHOOL": "SCHOOL",
    "HOSPITAL": "HOSPITAL", "CLINIC": "HOSPITAL", "PHARMACY": "PHARMACY",
    "PARK": "PARK", "PUBLIC_TRANSPORT": "PUBLIC_TRANSPORT",
}
LABELS = {
    "MARKET":"Chợ","SUPERMARKET":"Siêu thị","MALL":"Trung tâm thương mại",
    "CONVENIENCE_STORE":"Cửa hàng tiện lợi","GYM":"Phòng gym","SPORTS_FIELD":"Sân thể thao",
    "POOL":"Hồ bơi","PARK":"Công viên / đường đi bộ","RESTAURANT":"Quán ăn / nhà hàng","CAFE":"Quán cà phê",
    "KINDERGARTEN":"Trường mầm non","PRIMARY_SCHOOL":"Trường tiểu học","SECONDARY_SCHOOL":"Trường trung học",
    "PLAYGROUND":"Khu vui chơi trẻ em","HOSPITAL":"Bệnh viện","CLINIC":"Phòng khám",
    "PHARMACY":"Nhà thuốc","WORKPLACE":"Gần nơi làm việc","PUBLIC_TRANSPORT":"Phương tiện công cộng",
}

def fingerprint(profile):
    return sha256(json.dumps(profile,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

def seed(context, profile, names):
    if not profile or not profile.get("enabled"):
        return
    selected=[n for n in profile.get("selectedNeeds",[]) if n in LABELS][:19]
    raw_children = profile.get("hasChildren")
    child_count = profile.get("childrenCount")
    children = bool(raw_children) or (isinstance(child_count, int) and child_count > 0)
    household_known = raw_children is not None or child_count is not None
    primary=profile.get("primaryNeed")
    if primary in selected:
        selected.remove(primary)
        selected.insert(0,primary)
    all_priorities=list(dict.fromkeys(MAPPING[n] for n in selected if n in MAPPING))
    priorities=all_priorities[:4]
    district=profile.get("district")
    # Account district is an untrusted string, accept only the current supported catalog.
    if district in names:
        context.last_criteria={"district":district}
    state=context.needs
    state["active"]=True
    state["locationKnown"]=district in names or fold(district or "") in ("da nang","thanh pho da nang")
    state["profilePriorityLimit"]=len(all_priorities)>4
    state["profileUsed"]=True
    state["profileLabels"]=[LABELS[n] for n in selected]
    state["unsupportedProfileNeeds"]=[LABELS[n] for n in selected if n not in MAPPING]
    state["priorities"]=priorities
    state["askedPriorities"]=bool(selected)
    state["householdProfile"]=children if household_known else None
    state["childrenNeedsConfirmation"]=children and not any(n in selected for n in ("KINDERGARTEN", "PRIMARY_SCHOOL", "SECONDARY_SCHOOL", "PARK"))
    state["familyStatusProvided"]=bool(profile.get("familyStatus"))
    state["ageGroupProvided"]=bool(profile.get("ageGroup"))
    if "PRIMARY_SCHOOL" in selected:
        state["schoolLevel"]="tiểu học"
