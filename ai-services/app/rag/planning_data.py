"""Offline reviewed planning data. Never imported by public chat in M0–M1."""
import hashlib
import json
import math
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlsplit
from typing import Any, Literal
from pydantic import BaseModel, ConfigDict, Field, model_validator

FORMAT = "SMARTPROP_PLANNING_SNAPSHOT_V1"
LEGAL = {"HISTORICAL_APPLICATION_WINDOW_PUBLISHED", "LISTED_AS_PROJECT_AREA_IN_PROGRESS_AT_PUBLICATION", "INVESTMENT_POLICY_APPLICATION_INTAKE_NOTICE", "PREPARATION_REPORTED_START_DATE_PROJECTED", "PLANNING_AMENDMENT_PUBLIC_CONSULTATION", "PLANNING_NOTICE_ATTACHMENT_UNVERIFIED", "PUBLIC_CONSULTATION_NOT_AMENDMENT_APPROVAL", "AUCTION_2026_CATALOG_NOT_AUCTION_OPENING", "PUBLIC_CONSULTATION_DOCUMENT_READ", "STARTING_PRICE_APPROVAL_REPORTED_NOT_AUCTION_RESULT", "PLANNING_APPROVAL_DOCUMENT_READ", "LAND_ALLOCATION_DOCUMENT_READ"}

def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False).encode()).hexdigest()

def stamp(value):
    dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if dt.tzinfo is None: raise ValueError("Timezone required")
    return dt

def fold(value):
    return " ".join(unicodedata.normalize("NFD", value.lower().replace("đ", "d")).encode("ascii", "ignore").decode().split())

class Strict(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)

class Source(Strict):
    id: str
    url: str
    title: str = Field(min_length=1)
    sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    checked_at: str
    document_date: str | None = None
    publication_date: str | None = None
    @model_validator(mode="after")
    def valid(self):
        u = urlsplit(self.url)
        if u.scheme != "https" or not u.hostname or not (u.hostname.endswith(".danang.gov.vn") or u.hostname in {"danang.gov.vn", "cttdt.danangportal.gov.vn"} or (u.hostname=="drive.google.com" and re.fullmatch(r"/file/d/[A-Za-z0-9_-]+/view",u.path) and not u.query)) or u.username or u.password or u.port not in (None,443) or u.fragment: raise ValueError("Unapproved source URL")
        checked = stamp(self.checked_at)
        if checked > datetime.now(timezone.utc): raise ValueError("Future check")
        for v in [self.document_date, self.publication_date]:
            if v:
                if not re.fullmatch(r"[0-9]{4}-[0-9]{2}-[0-9]{2}(?:T.*)?",v):raise ValueError("Invalid evidence date")
                dt=datetime.fromisoformat(v)
                if "T" in v and dt.tzinfo is None:raise ValueError("Timezone required")
                if dt.date()>checked.date():raise ValueError("Future evidence date")
        return self

class Fact(Strict):
    value: Any
    source_ids: list[str] = Field(min_length=1)
    basis: str = Field(min_length=1)
    scope: str = Field(min_length=1)

class Record(Strict):
    id: str = Field(pattern=r"^HX-(?:RE|LAND)-[0-9]{3,}$")
    revision: int = Field(ge=1)
    kind: str
    parent_ids: list[str]
    facts: dict[str, Fact]
    source_ids: list[str] = Field(min_length=1)
    input_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    @model_validator(mode="after")
    def valid(self):
        for k,f in self.facts.items():
            if not set(f.source_ids) <= set(self.source_ids): raise ValueError("Unknown fact source")
            if k == "legal_event_status" and f.value not in LEGAL: raise ValueError("Unknown legal event")
            if "area" in k and f.value is not None:
                if isinstance(f.value,bool) or not isinstance(f.value,(int,float)) or not math.isfinite(f.value) or f.value <= 0: raise ValueError("Invalid area")
            if k in {"latitude","longitude","geometry"} and f.value is not None: raise ValueError("Geometry not reviewed in V1")
        return self

class Decision(Strict):
    approval: Literal["PENDING","APPROVED","REJECTED"] = "PENDING"
    permission: Literal["UNKNOWN","PERMITTED","DENIED"] = "UNKNOWN"
    permission_basis: str | None = None
    verification: Literal["UNREVIEWED","SOURCE_CHECKED","BLOCKED"] = "UNREVIEWED"
    reviewer: str | None = None
    reviewed_at: str | None = None
    review_due_at: str | None = None
    value_hash: str = Field(pattern=r"^[a-f0-9]{64}$")
    def allowed(self, value_hash):
        if value_hash != self.value_hash: raise ValueError("Review hash mismatch")
        if self.approval != "APPROVED" or self.permission != "PERMITTED" or self.verification != "SOURCE_CHECKED": return False
        if not all([self.permission_basis, self.reviewer, self.reviewed_at, self.review_due_at]): raise ValueError("Incomplete approval")
        reviewed, due = stamp(self.reviewed_at), stamp(self.review_due_at)
        now = datetime.now(timezone.utc)
        if reviewed > now or due <= reviewed: raise ValueError("Invalid review dates")
        return now < due

def load_json(path):
    path=Path(path)
    if path.stat().st_size > 8*1024*1024: raise ValueError("File too large")
    return json.loads(path.read_text(encoding="utf-8"), parse_constant=lambda _: (_ for _ in ()).throw(ValueError("Nonfinite JSON")))

def validate_bundle(bundle):
    if bundle.get("format") != "SMARTPROP_PLANNING_REVIEW_V1": raise ValueError("Unknown bundle")
    records = [Record.model_validate(r) for r in bundle["records"]]
    sources = [Source.model_validate(s) for s in bundle["sources"]]
    if len(records)>2000 or len(sources)>5000: raise ValueError("Too many records")
    if len({r.id for r in records}) != len(records) or len({s.id for s in sources}) != len(sources): raise ValueError("Duplicate IDs")
    ids={s.id for s in sources};rids={r.id for r in records}
    for r in records:
        if not set(r.source_ids)<=ids or not set(r.parent_ids)<=rids: raise ValueError("Broken relationship")
    return records,sources

def initial_review(bundle):
    records,sources=validate_bundle(bundle)
    return {"format":"SMARTPROP_PLANNING_REVIEW_MANIFEST_V1", "bundle_hash":digest(bundle), "sources":{s.id:Decision(value_hash=digest(s.model_dump())).model_dump() for s in sources}, "records":{r.id:{"record":Decision(value_hash=digest(r.model_dump())).model_dump(),"fields":{k:Decision(value_hash=digest(f.model_dump())).model_dump() for k,f in r.facts.items()}} for r in records}}

def build_snapshot(bundle,review):
    records,sources=validate_bundle(bundle)
    if review.get("format")!="SMARTPROP_PLANNING_REVIEW_MANIFEST_V1" or review.get("bundle_hash")!=digest(bundle): raise ValueError("Review bundle mismatch")
    if set(review["records"]) != {r.id for r in records}: raise ValueError("Review ID mismatch")
    if set(review.get("sources",{}))!={s.id for s in sources}:raise ValueError("Review source mismatch")
    source_decisions={s.id:Decision.model_validate(review["sources"][s.id]) for s in sources}
    allowed_sources={s.id for s in sources if source_decisions[s.id].allowed(digest(s.model_dump()))}
    published=[];blocked=[];due=[]
    for r in records:
        entry=review["records"][r.id]
        if set(entry["fields"])!=set(r.facts):raise ValueError("Review field mismatch")
        record_decision=Decision.model_validate(entry["record"])
        fields={k:Decision.model_validate(entry["fields"][k]) for k in r.facts}
        record_allowed=record_decision.allowed(digest(r.model_dump()))
        approved={k:f.model_dump() for k,f in r.facts.items() if fields[k].allowed(digest(f.model_dump())) and set(f.source_ids)<=allowed_sources}
        if not record_allowed or not {"name","legal_event_status"}<=set(approved):blocked.append(r.id);continue
        used={s for f in approved.values() for s in f["source_ids"]}
        published.append({"id":r.id,"revision":r.revision,"kind":r.kind,"parent_ids":r.parent_ids,"facts":approved,"sources":[s.model_dump() for s in sources if s.id in used]})
        due.extend([source_decisions[s].review_due_at for s in used])
        due.extend([record_decision.review_due_at]+[fields[k].review_due_at for k in approved])
    report={"total":len(records),"published":len(published),"blocked":blocked,"feature_enabled":bool(published)}
    if not published:return None,report
    result={"format":FORMAT,"created_at":datetime.now(timezone.utc).isoformat(),"review_due_at":min(due,key=stamp),"records":published}
    result["content_hash"]=digest(result)
    return result,report

class PlanningLookup:
    """Read only a reviewed publication snapshot; opt-in and fail closed."""
    def __init__(self,path=None,*,enabled=False):self.path=path;self.enabled=enabled
    def query(self,operation,*,project=None,phase=None,lot=None,year=None,document_number=None):
        if operation not in {"PROJECT_LIST","AUCTION_CATALOG","PLANNING_STATUS","LOT_LOOKUP"}:raise ValueError("Unknown operation")
        if not self.enabled:return {"status":"DISABLED","items":[]}
        data=load_json(self.path);hash=data.pop("content_hash",None)
        if data.get("format")!=FORMAT or hash!=digest(data) or stamp(data["review_due_at"])<=datetime.now(timezone.utc):raise ValueError("Invalid or expired snapshot")
        rows=data["records"]
        if not isinstance(rows,list) or len(rows)>2000:raise ValueError("Invalid snapshot rows")
        seen=set()
        for row in rows:
            if row["id"] in seen:raise ValueError("Duplicate snapshot row")
            seen.add(row["id"])
            sources=[Source.model_validate(s) for s in row["sources"]]
            ids=[s.id for s in sources]
            r=Record(id=row["id"],revision=row["revision"],kind=row["kind"],parent_ids=row["parent_ids"],facts=row["facts"],source_ids=ids,input_sha256="0"*64)
            if not {"name","legal_event_status"}<=set(r.facts):raise ValueError("Missing public fields")

        def value(r,k):return r["facts"].get(k,{}).get("value")
        if operation=="PROJECT_LIST":rows=[r for r in rows if r["kind"]=="PROJECT_PROFILE"]
        if operation=="AUCTION_CATALOG":
            if year!=2026:return {"status":"OUTSIDE_COVERAGE","items":[]}
            rows=[r for r in rows if r["kind"]=="AUCTION_LAND_CATALOG"]
        if operation=="PLANNING_STATUS":rows=[r for r in rows if r["kind"]!="PROJECT_PROFILE"]
        if operation=="LOT_LOOKUP" and not lot:return {"status":"NEEDS_CLARIFICATION","items":[]}
        for key,criterion in [("name",project),("phase",phase),("lot_code",lot),("document_number",document_number)]:
            if criterion is not None:
                if not isinstance(criterion,str) or not 1<=len(criterion)<=200:raise ValueError("Invalid query")
                def matches(row):
                    actual=value(row,key)
                    if actual is None:return False
                    actual,expected=fold(str(actual)),fold(criterion)
                    if key=="name":return expected in actual
                    if key=="document_number":return actual==expected or actual.split("/")[0]==expected
                    return actual==expected
                rows=[r for r in rows if matches(r)]
        status="NEEDS_CLARIFICATION" if operation=="LOT_LOOKUP" and len(rows)>1 and (not project or not phase) else "OK" if rows else "NO_MATCHES"
        return {"status":status,"items":rows[:100],"total":len(rows),"truncated":len(rows)>100,"snapshot_hash":hash}
