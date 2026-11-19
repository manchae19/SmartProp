"""Explicit offline intake. Dry-run by default; never approves source permissions."""
import argparse
import hashlib
import json
from pathlib import Path
from app.rag.planning_data import Source, Record, Fact, digest, load_json, initial_review, build_snapshot

def prepare(project_dir,land_dir):
    project_dir,land_dir=Path(project_dir),Path(land_dir)
    projects=load_json(project_dir/"records.json");lands=load_json(land_dir/"records.json")
    ps=load_json(project_dir/"sources.json");ls=load_json(land_dir/"sources.json")
    sources={};records=[]
    def source(id,url,title,sha,checked,doc=None,pub=None):
        item=Source(id=id,url=url,title=title,sha256=sha,checked_at=checked,document_date=doc,publication_date=pub)
        if id in sources and sources[id]!=item.model_dump():raise ValueError("Source collision")
        sources[id]=item.model_dump();return id
    for s in ps:source("project:"+s["source_id"],s["requested_url"],s["publisher"],s["sha256"],s["fetched_at"],pub=s.get("published_at"))
    input_hash=hashlib.sha256((project_dir/"records.json").read_bytes()).hexdigest()
    for p in projects:
        ids=["project:"+s for s in p["source_ids"]]
        def fact(v,b="SOURCE_REPORTED",scope="PROJECT",ids=ids):return Fact(value=v,source_ids=ids,basis=b,scope=scope)
        facts={"name":fact(p["name"]),"legal_event_status":fact(p["normalized"]["reported_status"],"HISTORICAL_PUBLICATION_NOT_CURRENT_LEGAL_STATUS")}
        for a in p["assertions"]:
            key=a["field"]
            if key in facts:raise ValueError("Repeated assertion field")
            facts[key]=Fact(value=a["value"],source_ids=["project:"+a["source_id"]],basis=a["basis"],scope="COMBINED_SITES" if "COMBINED" in a["basis"] else "PROJECT_ASSERTION")
        records.append(Record(id=p["id"],revision=p["revision"],kind="PROJECT_PROFILE",parent_ids=[],facts=facts,source_ids=ids,input_sha256=input_hash).model_dump())
    input_hash=hashlib.sha256((land_dir/"records.json").read_bytes()).hexdigest()
    for p in lands:
        id="land:"+p["source_id"]
        source(id,p["source_url"],p["source_title"],p["source_sha256"],p["checked_at"],p["document_date"],p["publication_date"])
        fields=["name","lot_code","phase","area_sqm","land_use_reported","planning_scale","legal_event_status","document_number","document_date","publication_date"]
        facts={k:Fact(value=p[k],source_ids=[id],basis=p["area_basis"] if k=="area_sqm" else "SOURCE_REPORTED",scope="PROJECT_PHASE_LOT" if p["lot_code"] else "DOCUMENT_SCOPE").model_dump() for k in fields}
        records.append(Record(id=p["id"],revision=p["revision"],kind=p["record_kind"],parent_ids=p["related_existing_record_ids"],facts=facts,source_ids=[id],input_sha256=input_hash).model_dump())
    return {"format":"SMARTPROP_PLANNING_REVIEW_V1","records":records,"sources":list(sources.values())}

def write(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    tmp=path.with_suffix(path.suffix+".tmp");tmp.write_text(json.dumps(value,ensure_ascii=False,indent=2)+"\n",encoding="utf-8");tmp.replace(path)

def main():
    parser=argparse.ArgumentParser();parser.add_argument("--projects",required=True);parser.add_argument("--land",required=True);parser.add_argument("--review-dir",required=True);parser.add_argument("--initialize-review",action="store_true");parser.add_argument("--snapshot");parser.add_argument("--write",action="store_true");args=parser.parse_args()
    bundle=prepare(args.projects,args.land);folder=Path(args.review_dir)
    if args.initialize_review:
        if folder.exists():raise ValueError("Refuse overwrite of existing review")
        write(folder/"normalized.json",bundle);write(folder/"review-manifest.json",initial_review(bundle))
        write(folder/"record.schema.json",Record.model_json_schema());write(folder/"source.schema.json",Source.model_json_schema())
    stored=load_json(folder/"normalized.json")
    if digest(stored)!=digest(bundle):raise ValueError("Inputs changed: new review required")
    result,report=build_snapshot(stored,load_json(folder/"review-manifest.json"))
    report["dry_run"]=not args.write;report["snapshot_written"]=False
    if args.write and result:
        if not args.snapshot:raise ValueError("Snapshot output required")
        write(args.snapshot,result);report["snapshot_written"]=True
    # No approved records means no empty or publicly enabled snapshot is produced.
    write(folder/"validation-report.json",report);print(json.dumps({k:v for k,v in report.items() if k!="blocked"},ensure_ascii=False))
if __name__=="__main__":main()
