"""Resolve named wards only against source-backed catalog entries; no inferred boundaries."""
import re
from .intent import fold

def key(value):
    return re.sub(r"^(?:phuong|xa|ward)\s+", "", " ".join(fold(value or "").split()))


_LISTING_PLACE = re.compile(
    r"\b(?:(?P<level>quan|huyen|phuong|xa)\s+(?!(?:tam|trong|hoi)\b)"
    r"|(?:chi\s+(?:o|tai|thuoc)|(?:doi|chuyen)\s+sang)\s+(?!(?:quan|huyen|phuong|xa)\b))"
)
_LISTING_LOCATION_EDIT = re.compile(
    r"^(?:chi\s+(?:o|tai|thuoc)|(?:doi|chuyen)\s+(?:sang|quan|phuong)|quan|huyen|phuong|xa)\b"
)


def is_listing_location_edit(question):
    return bool(_LISTING_LOCATION_EDIT.match(fold(question).strip()))


def listing_location_text(outside_address):
    # A restrictive clause identifies the target area even when a postal
    # district was also written next to the reference street.
    value = " ".join(fold(outside_address).split())
    target = re.search(r"\bchi\s+(?:o|tai|thuoc)\b", value)
    return value[target.start():] if target else value


def listing_location_mentions(question):
    return list(_LISTING_PLACE.finditer(" ".join(fold(question).split())))


def listing_location(question, districts, areas):
    """Resolve only explicitly marked listing locations from the public names."""
    value = " ".join(fold(question).split())
    district_labels = {key(name): name for name in districts}
    ward_labels = {}
    for area in areas:
        if isinstance(area, dict) and area.get("areaLevel") == "WARD" and area.get("parentDistrict"):
            name = (area.get("areaName") or "").split(",", 1)[0].strip()
            if name:
                ward_labels.setdefault(key(name), set()).add((name, area["parentDistrict"]))
    found = {}
    for mention in listing_location_mentions(question):
        is_ward = mention["level"] in ("phuong", "xa")
        labels = ward_labels if is_ward else district_labels
        following = value[mention.end():]
        name = next((label for label in sorted(labels, key=len, reverse=True)
                     if re.match(re.escape(label) + r"(?!\w)", following)), None)
        if name is None:
            return None
        suffix = following[len(name):].lstrip()
        if suffix and not re.match(
            r"(?:[,.;!?]|(?:va\s+(?=dien tich|ngan sach|gia|quan|phuong)|quan|huyen|phuong|xa|"
            r"dien tich|ngan sach|gia|gan|cho thue|thi sao|nhe|chi|duoi|tren|nho hon|be hon|lon hon|"
            r"toi da|toi thieu|khong qua|it nhat|it hon|tu|tim|nha|can ho)\b)", suffix
        ):
            return None
        if is_ward:
            if len(ward_labels[name]) != 1:
                return None
            ward, district = next(iter(ward_labels[name]))
            resolved = {"ward": ward, "district": district}
        else:
            resolved = {"district": district_labels[name]}
        if any(field in found and key(found[field]) != key(label) for field, label in resolved.items()):
            return None
        found.update(resolved)
    return found


def amenity_locality(question,documents):
    q=fold(question)
    wards={}
    for d in documents:
        m=d.get("metadata",{})
        if d.get("kind")!="AREA_AMENITY" or m.get("areaLevel")!="WARD":continue
        name=key(m.get("areaName"))
        if name and re.search(r"(?<!\w)"+re.escape(name)+r"(?!\w)",q):
            wards[(name,m.get("district"))]={"ward":m.get("areaName"),"district":m.get("district"),"areaId":m.get("areaId")}
    if len(wards)==1:return next(iter(wards.values()))
    if len(wards)>1:return {"unresolved":True}
    if re.search(r"\b(?:phuong|xa|duong|kiet|hem)\s+",q):return {"unresolved":True}
    place=re.search(r"\b(?:gan|tai|o|khu vuc)\s+(.+?)(?:[,?!.]|$)",q)
    if place:
        phrase=place[1].strip()
        relative=re.match(r"(?:day|do|nay|khu nay|khu do|khu vuc nay|khu vuc do|nha|can|truong|benh vien|sieu thi|cho|cong vien)\b",phrase)
        districts={fold(d.get("metadata",{}).get("district") or "") for d in documents}
        known=any(n and re.search(r"(?<!\w)"+re.escape(n)+r"(?!\w)",phrase) for n in districts)
        city=bool(re.search(r"\b(?:da nang|toan thanh pho)\b",phrase))
        if not relative and not known and not city:return {"unresolved":True}
    return None
