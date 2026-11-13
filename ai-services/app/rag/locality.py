"""Resolve named wards only against source-backed catalog entries; no inferred boundaries."""
import re
from .intent import fold

def key(value):
    return re.sub(r"^(?:phuong|xa|ward)\s+", "", fold(value or "")).strip()

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
