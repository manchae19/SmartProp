"""Versioned listing collector retaining optional location text when supplied.

No detail API, no blocked-page bypass, no geocoding, no automatic ML approval.
Legacy collector/raw files remain unchanged. Default action is offline import.
"""
import argparse
import csv
import json
import os
import time
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

import collect_chotot_incremental as legacy
from training_v3_common import BASE, sha

EXTRA = {
    'description_raw': ['body','description'],
    'address_detail_raw': ['full_address','address','address_raw'],
    'house_number_source': ['house_number','street_number'],
    'alley_number_source': ['alley_number'],
    'alley_width_source': ['alley_width_m','alley_width'],
    'road_width_source': ['road_width_m','road_width'],
}
OUT = BASE/'data_raw/chotot_locations_v2'


def capture(item, record, evidence):
    sid=str(record.get('source_listing_id',''))
    if not sid.isdigit() or record.get('source')!='chotot':
        raise ValueError('Missing Chotot listing identity')
    declared=item.get('list_id',item.get('source_listing_id'))
    if declared is not None and str(declared)!=sid:
        raise ValueError('Input and normalized listing ID mismatch')
    url=str(record.get('source_url',''))
    parsed=urlsplit(url)
    if parsed.hostname not in {'nha.chotot.com','www.nhatot.com','nhatot.com'} or not parsed.path.endswith('/'+sid+'.htm'):
        raise ValueError('Listing URL identity mismatch')
    result=dict(record)
    sources={}
    for field,aliases in EXTRA.items():
        found={k:item[k] for k in aliases if k in item and isinstance(item[k],(str,int,float)) and not isinstance(item[k],bool)}
        # Retain original text and conflicting alternatives, never invent a
        # description from title or a full address by joining street/ward.
        sources[field]=found
        result[field]=next((str(v) for v in found.values() if str(v).strip()),'')
    result.update(location_capture_version=2,source_location_fields=sources,
        location_field_evidence={field:evidence for field in EXTRA},
        description_status='available' if result['description_raw'] else 'not_provided_or_empty',
        address_detail_status='source_claim_unverified' if result['address_detail_raw'] else 'not_provided_or_empty',
        location_verified=False,reuse_for_ml_verified=False,model_feature_approved=False,
        capture_evidence=evidence,captured_at=legacy.now(),text_is_model_feature=False)
    return result


def commit(out,state):
    # One atomic authoritative checkpoint includes data and cursor together.
    # Interrupted CSV export is rebuilt from this checkpoint on next invocation.
    legacy.atomic_json(out/'checkpoint_v2.json',state)
    fields=list(legacy.FIELDS)+list(EXTRA)+['location_capture_version','description_status',
        'address_detail_status','location_verified','reuse_for_ml_verified','model_feature_approved',
        'captured_at','text_is_model_feature']
    temp=out/'records.csv.tmp'
    with temp.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fields,extrasaction='ignore');writer.writeheader()
        for record in state['records'].values():
            writer.writerow({k:';'.join(v) if k=='review_flags' and isinstance(v,list) else v for k,v in record.items()})
    temp.replace(out/'records.csv')
    temp=out/'records.jsonl.tmp'
    with temp.open('w',encoding='utf-8') as stream:
        for record in state['records'].values():
            stream.write(json.dumps(record,ensure_ascii=False,allow_nan=False)+'\n')
    temp.replace(out/'records.jsonl')


def ingest(state,item,evidence,normalized=False):
    if normalized:
        record=dict(item)
    else:
        record,reason=legacy.normalize(item,legacy.now())
        if record is None:
            return 'rejected_'+reason
    result=capture(item,record,evidence)
    key='chotot:'+str(result['source_listing_id'])
    previous=state['records'].get(key)
    if previous:
        # Duplicate pages cannot erase a previously supplied description/address.
        for field in EXTRA:
            if not result[field] and previous.get(field):
                result[field]=previous[field]
                result['source_location_fields'][field]=previous['source_location_fields'][field]
                result['location_field_evidence'][field]=previous['location_field_evidence'][field]
        result['description_status']='available' if result['description_raw'] else 'not_provided_or_empty'
        result['address_detail_status']='source_claim_unverified' if result['address_detail_raw'] else 'not_provided_or_empty'
        previous_events=list(previous.get('capture_history',[]))
        if previous.get('capture_evidence') not in previous_events:
            previous_events.append(previous['capture_evidence'])
        result['capture_history']=previous_events
    state['records'][key]=result
    return 'updated' if previous else 'added'


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['import','collect'])
    parser.add_argument('--input',type=Path,help='API JSON {ads: [...]} or JSONL archive')
    parser.add_argument('--normalized-input',action='store_true',help='Existing normalized JSONL; missing text stays missing')
    parser.add_argument('--output',type=Path,default=OUT)
    parser.add_argument('--max-pages',type=int,default=1)
    parser.add_argument('--max-new',type=int,default=20)
    parser.add_argument('--delay',type=float,default=3)
    args=parser.parse_args()
    if not 1<=args.max_pages<=5 or not 1<=args.max_new<=100 or args.delay<3:
        parser.error('max-pages 1..5, max-new 1..100, delay >=3 s')
    # Never write over the legacy collector or any old raw directory.
    out=args.output.resolve()
    for protected in [BASE/'data_raw/chotot_incremental',BASE/'processed/training_v3',BASE/'processed/models_v3_validation']:
        if out==protected or protected in out.parents:
            parser.error('Use a separate v2 output directory')
    if args.input and (out==args.input.resolve().parent or out in args.input.resolve().parents):
        parser.error('Input must be outside output directory')
    out.mkdir(parents=True,exist_ok=True)
    if not (out/'checkpoint_v2.json').exists() and any((out/name).exists() for name in ['records.csv','records.jsonl']):
        parser.error('Existing records belong to a different collector; choose a new output directory')
    lock=out/'collector_v2.lock'
    descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    os.close(descriptor)
    try:
        execute(out,args)
    finally:
        lock.unlink()


def execute(out,args):
    checkpoint=out/'checkpoint_v2.json'
    state=json.loads(checkpoint.read_text()) if checkpoint.exists() else dict(version=2,records={},next_offset=0)
    if state.get('version')!=2:
        raise ValueError('Checkpoint schema mismatch')
    counts=Counter()
    if args.mode=='import':
        if not args.input:
            raise ValueError('--input required for offline import')
        digest=sha(args.input)
        content=args.input.read_text(encoding='utf-8-sig')
        if args.input.suffix.lower()=='.jsonl':
            items=[json.loads(line) for line in content.splitlines() if line.strip()]
        else:
            data=json.loads(content);items=data.get('ads',[]) if isinstance(data,dict) else data
        if not isinstance(items,list):
            raise ValueError('Expected listing array or API ads array')
        for index,item in enumerate(items,1):
            evidence=dict(file=str(args.input.resolve()),file_sha256=digest,item_index=index,mode='offline_import')
            counts[ingest(state,item,evidence,args.normalized_input)]+=1
        if sha(args.input)!=digest:
            raise ValueError('Input changed during import')
        commit(out,state)
    else:
        # Use only the same public listing feed as legacy, never alternate
        # detail endpoints. Do not invoke while source access is blocked.
        try:
            for page in range(args.max_pages):
                params=dict(region_v2=3017,cg=1020,st='s',limit=50,o=state['next_offset'],w=1)
                data=legacy.fetch(params)
                evidence=dict(endpoint=legacy.API,query=params,fetched_at=legacy.now(),mode='public_listing_feed')
                complete=True
                for item in data['ads']:
                    result=ingest(state,item,evidence)
                    counts[result]+=1
                    if counts['added']>=args.max_new:
                        complete=False;break
                if complete:
                    state['next_offset']+=50
                commit(out,state)
                if not data['ads'] or not complete:
                    break
                time.sleep(args.delay)
        except BaseException:
            commit(out,state)
            raise
    summary=dict(version=2,unique_ids=len(state['records']),changes=dict(counts),
        descriptions=sum(bool(r['description_raw']) for r in state['records'].values()),
        source_address_claims=sum(bool(r['address_detail_raw']) for r in state['records'].values()),
        verified_property_locations=0,approved_model_features=0,mode=args.mode,
        original_raw_and_model_modified=False,detail_endpoints_requested=False)
    legacy.atomic_json(out/'summary.json',summary)
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
