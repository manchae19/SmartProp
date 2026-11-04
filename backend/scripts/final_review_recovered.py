"""Step18.4 final review: Local SELECT/SHOW/CHECKSUM only; no import execution.

CSV outputs contain IDs, numeric labels, evidence references and fingerprints;
no contact fields, full descriptions or private account/session details.
"""
import argparse
import csv
import hashlib
import json
import math
import re
import statistics
import subprocess
import sys
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
from urllib.parse import urlsplit,urlunsplit,parse_qsl,urlencode

import prepare_recovered_external as prior

ROOT=prior.ROOT
BEFORE=ROOT/'.scratch/hybrid-full-audit/step18-3'
OUT=ROOT/'.scratch/hybrid-full-audit/step18-4'
sys.path.insert(0,str(ROOT/'ai-services/app/data'))
import review_source_details as source_rules
import audit_all_collected as source_audit

CATEGORY={'HOUSE':'Nhà ở','LAND':'Đất nền','APARTMENT':'Căn hộ chung cư'}
SUPPORTED_DISTRICTS={prior.norm(x) for x in ['Hải Châu','Thanh Khê','Sơn Trà','Ngũ Hành Sơn','Liên Chiểu','Cẩm Lệ','Hòa Vang']}
DECISIONS=['READY_FOR_INTERNAL_IMPORT','NEEDS_MANUAL_REVIEW','BLOCKED','NEEDS_SOURCE_VERIFICATION']

def digest(value):
    return hashlib.sha256(value.encode('utf8')).hexdigest()

def normalized_url(value):
    u=urlsplit(value or '')
    if u.scheme not in {'https','http'} or not u.hostname or u.username or u.password or u.port not in {None,80,443}:
        raise ValueError('Non-source URL')
    host=u.hostname.lower().removeprefix('www.')
    path=re.sub(r'%([0-9a-fA-F]{2})',lambda m: chr(int(m[1],16)) if chr(int(m[1],16)) in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-._~' else '%'+m[1].upper(),u.path)
    query=[(k,v) for k,v in parse_qsl(u.query,keep_blank_values=True) if not k.lower().startswith('utm_') and k.lower() not in {'fbclid','gclid','ref','referrer'}]
    return urlunsplit(('https',host,path.rstrip('/') or '/',urlencode(sorted(query)),''))

def source_pair(source,sid):
    return str(source or '').strip().casefold(),str(sid or '').strip()

def specific_address(value,district):
    address=prior.norm(prior.legacy.clean_address(value))
    for part in [prior.norm(district),'da nang','quang nam']:
        address=address.replace(part,' ')
    tokens=[t for t in address.split() if t not in {'duong','phuong','quan','huyen','xa','thanh','pho','tp','ban','nha','rieng','dat','nen'}]
    # A ward/district alone cannot establish an asset fingerprint.
    if len(tokens)<3 or not re.search(r'\b(duong|so|kiet|hem)\b',prior.norm(value)):
        return ''
    return ' '.join(tokens)

def prepared_item(row, evidence=None, holdout=False, platform=False):
    category=CATEGORY.get(row.get('category'),row.get('category'))
    price=prior.decimal(row.get('price_vnd',row.get('price','0')))
    if not price:price=prior.decimal(row.get('price_million'))*1000000
    address=row.get('address_raw') or row.get('address') or ''
    result=dict(key=row['record_key'],category=category,district=prior.norm(row.get('district')),price=price,
        area=prior.decimal(row.get('area_sqm')),holdout=holdout,platform=platform,
        title_tokens=set(prior.legacy.tokenize(prior.norm(row.get('title')))),
        address=specific_address(address,row.get('district')),
        pipeline_group=row.get('pipeline_group') or '',group=row.get('duplicate_group') or '')
    description=prior.norm((evidence or {}).get('description',''))
    words=description.split()
    result['description_hash']=digest(description) if len(words)>=80 and len(set(words))>=35 else ''
    result['fingerprint']=digest('|'.join([category or '',result['district'],result['address'],str(price.normalize()),str(result['area'].normalize())])) if result['address'] and price>0 and result['area']>0 else ''
    try:result['url']=normalized_url(row.get('detail_url'))
    except ValueError:result['url']=''
    return result

def match_rules(left,right):
    """Conservative review links only, not physical identity proof."""
    if left['key']==right['key']:return []
    rules=[]
    if left['url'] and left['url']==right['url']:rules.append('NORMALIZED_SOURCE_URL')
    if left['pipeline_group'] and left['pipeline_group']==right['pipeline_group']:rules.append('PIPELINE_GROUP')
    if left['fingerprint'] and left['fingerprint']==right['fingerprint']:rules.append('EXACT_FEATURE_FINGERPRINT')
    if left['category']!=right['category'] or left['district']!=right['district']:return rules
    if min(left['price'],right['price'],left['area'],right['area'])<=0:return rules
    price_diff=abs(left['price']-right['price'])/max(left['price'],right['price'])
    area_diff=abs(left['area']-right['area'])/max(left['area'],right['area'])
    if price_diff<=Decimal('.05') and area_diff<=Decimal('.01') and left['description_hash'] and left['description_hash']==right['description_hash']:
        rules.append('EXACT_LONG_DESCRIPTION_PRICE5_AREA1')
    if price_diff>Decimal('.10') or area_diff>Decimal('.03'):return rules
    titles=left['title_tokens']|right['title_tokens']
    jac=len(left['title_tokens']&right['title_tokens'])/len(titles) if titles else 0
    if left['address'] and left['address']==right['address'] and (jac>=.2 or price_diff<=Decimal('.05') and area_diff<=Decimal('.01')):
        rules.append('NORMALIZED_ADDRESS_PRICE10_AREA3')
    if min(len(left['title_tokens']),len(right['title_tokens']))>=5 and jac>=.65:
        rules.append('TITLE_SIMILARITY65_PRICE10_AREA3')
    return rules

def peer_outlier(unit_price, peers):
    flags=[]
    if unit_price<Decimal('1000000'):flags.append('UNIT_PRICE_BELOW_INTERNAL_REVIEW_BAND')
    if unit_price>Decimal('500000000'):flags.append('UNIT_PRICE_ABOVE_INTERNAL_REVIEW_BAND')
    if len(peers)>=20:
        logs=[math.log(float(x)) for x in peers if x>0]
        q1,_,q3=statistics.quantiles(logs,n=4,method='inclusive')
        spread=q3-q1
        if spread>0 and not q1-3*spread<=math.log(float(unit_price))<=q3+3*spread:
            flags.append('UNIT_PRICE_LOG_IQR_OUTLIER')
    return flags

def classify(blocked,manual,source):
    if blocked:return 'BLOCKED'
    if manual:return 'NEEDS_MANUAL_REVIEW'
    if source:return 'NEEDS_SOURCE_VERIFICATION'
    return 'READY_FOR_INTERNAL_IMPORT'

def main():
    argparse.ArgumentParser(description=__doc__).parse_args()
    OUT.mkdir(parents=True,exist_ok=True)
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='backend-huy-latest':raise RuntimeError('Wrong branch')
    stage=prior.rows(BEFORE/'prepared_unverified.csv')
    recovered={r['record_key']:r for r in prior.rows(ROOT/'.scratch/hybrid-full-audit/step18-2/recovered_hybrid_candidates.csv')}
    originals={r['record_key']:r for r in prior.rows(ROOT/'ai-services/app/data/processed/remaining_diversity_review/runs/518bbc989587326c/all_listings_after_review.csv')}
    parsed=json.loads((ROOT/'ai-services/app/data/processed/collection_source_review/parsed_evidence.json').read_text(encoding='utf8'))
    manifest=json.loads((ROOT/'ai-services/app/data/processed/collection_source_review/fetch_manifest.json').read_text(encoding='utf8'))
    assert len(stage)==len({r['record_key'] for r in stage})==275
    client,identity=prior.read_local()
    names=client.query("SELECT table_name FROM information_schema.tables WHERE table_schema='smartprop' AND table_type='BASE TABLE' ORDER BY table_name").splitlines()
    if len(names)!=48 or any(not re.fullmatch(r'[A-Za-z0-9_]+',s) for s in names):raise RuntimeError('Unexpected schema')
    checksum_sql='CHECKSUM TABLE '+','.join('`'+s+'`' for s in names)+' EXTENDED'
    before=client.query(checksum_sql)
    db=client.objects("""SELECT JSON_OBJECT('record_key',record_key,'source',source,'source_listing_id',source_listing_id,
     'detail_url',detail_url,'title',title,'category',category,'district',district,'address_raw',address_raw,
     'price_million',CAST(price_million AS CHAR),'area_sqm',CAST(area_sqm AS CHAR),'duplicate_group',duplicate_group,
     'quality_status',quality_status,'quality_issues',quality_issues,'verification_status',verification_status,
     'is_protected_holdout',is_protected_holdout,'is_duplicate',is_duplicate,'transaction_type',transaction_type)
     FROM external_listings ORDER BY record_key""")
    internal=client.objects("""SELECT JSON_OBJECT('record_key',CONCAT('property:',id),'title',title,'category',property_type,
     'district',district,'address_raw',address,'price',CAST(price AS CHAR),'area_sqm',CAST(area_sqm AS CHAR)) FROM properties ORDER BY id""")
    if len(db)!=3204 or sum(bool(r['is_protected_holdout']) for r in db)!=983 or len(internal)!=16:raise RuntimeError('Unexpected source inventory')
    unique_indexes=client.objects("""SELECT JSON_OBJECT('table',table_name,'name',index_name,'columns',GROUP_CONCAT(column_name ORDER BY seq_in_index))
     FROM information_schema.statistics WHERE table_schema='smartprop' AND table_name IN ('external_listings','external_duplicate_groups') AND non_unique=0
     GROUP BY table_name,index_name ORDER BY table_name,index_name""")
    source_duplicates=client.objects("""SELECT JSON_OBJECT('source',source,'source_listing_id',source_listing_id,'count',COUNT(*))
     FROM external_listings GROUP BY source,source_listing_id HAVING COUNT(*)>1""")
    if source_duplicates:raise RuntimeError('Pre-existing source identity duplicates require review')
    for table in ['external_listings','external_duplicate_groups']:
        (OUT/(table+'-schema-readonly.txt')).write_text(client.query('SHOW CREATE TABLE '+table),encoding='utf8')
    old_keys={r['record_key'] for r in db};old_pairs={source_pair(r['source'],r['source_listing_id']) for r in db}
    held_db_groups={r['duplicate_group'] for r in db if r['is_protected_holdout'] and r['duplicate_group']}
    held_keys={r['record_key'] for r in db if r['is_protected_holdout'] or r['duplicate_group'] in held_db_groups}
    held_keys.update(k for k,r in originals.items() if prior.truth(r.get('protected_holdout')))
    held_pipeline={r['pipeline_group'] for k,r in originals.items() if k in held_keys and r.get('pipeline_group')}
    held_keys.update(k for k,r in originals.items() if r.get('pipeline_group') in held_pipeline)
    held_pairs={source_pair(r.get('source'),r.get('source_listing_id')) for k,r in originals.items() if k in held_keys}
    held_pairs.update(source_pair(r['source'],r['source_listing_id']) for r in db if r['record_key'] in held_keys)
    pool={}
    for key,row in originals.items():pool[key]=prepared_item(row,parsed.get(key),key in held_keys)
    for row in db:
        row=dict(row,pipeline_group=originals.get(row['record_key'],{}).get('pipeline_group',''))
        pool[row['record_key']]=prepared_item(row,parsed.get(row['record_key']),row['record_key'] in held_keys)
    for row in internal:pool[row['record_key']]=prepared_item(row,platform=True)
    items={r['record_key']:prepared_item(dict(r,title=recovered[r['record_key']]['title']),parsed.get(r['record_key'])) for r in stage}
    buckets=defaultdict(list)
    for p in pool.values():buckets[(p['category'],p['district'])].append(p)
    peers=defaultdict(list);seen=set()
    for row in db:
        if row['is_protected_holdout'] or row['duplicate_group'] in held_db_groups or row['quality_status']!='VALID' or row['transaction_type']!='SALE':continue
        group=row['duplicate_group'] or row['record_key']
        if group in seen:continue
        seen.add(group);item=pool[row['record_key']]
        if item['area']>0 and item['price']>0:peers[(item['category'],item['district'])].append(item['price']/item['area'])
    links=[];analyses={};stage_keys=set(items)
    stage_urls=Counter(p['url'] for p in items.values() if p['url'])
    stage_pairs=Counter(source_pair(r['source'],r['source_listing_id']) for r in stage)
    for row in stage:
        key=row['record_key'];original=originals.get(key,{});item=items[key];rec=recovered[key]
        blocked=[];manual=[];source=[];refs=[row['evidence_path']+'#sha256='+row['evidence_sha256']]
        expected=source_pair(row['source'],row['source_listing_id'])
        if row['source'] not in {'cafeland','homedy','nhadat24h','alonhadat'} or not re.fullmatch(r'[1-9]\d*',row['source_listing_id']) or key!=row['source']+':'+row['source_listing_id']:
            blocked.append('INVALID_CANONICAL_SOURCE_ID')
        if key in old_keys or expected in old_pairs or stage_pairs[expected]>1:blocked.append('SOURCE_ID_ALREADY_EXISTS_OR_REPEATED')
        try:
            url=normalized_url(row['detail_url'])
            if urlsplit(row['detail_url']).hostname not in source_audit.HOSTS.get(row['source'],set()):blocked.append('UNEXPECTED_SOURCE_HOST')
            if source_audit.sid_url(row['source'],row['detail_url'])!=row['source_listing_id']:blocked.append('SOURCE_URL_ID_MISMATCH')
        except (ValueError,KeyError):url='';blocked.append('INVALID_SOURCE_URL')
        if url and stage_urls[url]>1:manual.append('REPEATED_SOURCE_URL_IN_STAGE')
        for issue in prior.evidence_reasons(rec,parsed,manifest):
            if issue in {'EVIDENCE_HASH_MISMATCH','PROTECTED_HOLDOUT','PRICE_UNIT_OR_RANGE','UNSUPPORTED_CATEGORY'}:blocked.append(issue)
            else:source.append(issue)
        path=(ROOT/row['evidence_path']).resolve()
        live_evidence={}
        if path.is_relative_to((ROOT/'ai-services/app/data/processed/collection_source_review/detail_cache').resolve()) and path.is_file():
            live_evidence=source_rules.parse_detail(rec,manifest.get(key,{}),path.read_bytes())
            if hashlib.sha256(path.read_bytes()).hexdigest()!=row['evidence_sha256']:blocked.append('STAGED_EVIDENCE_HASH_MISMATCH')
            if not all(live_evidence.get(f) for f in ['identity_verified','structure_verified','sale_verified']):source.append('REPARSE_IDENTITY_STRUCTURE_SALE_UNCONFIRMED')
            else:
                decision,category,flags=source_rules.decide(original,live_evidence)
                if decision=='exclude':blocked.append('EXPLICIT_NON_MODEL_OR_COMMERCIAL_ASSET')
                for flag in flags:
                    if flag in {'prior_pending_requires_explicit_resolution','current_province_not_verified','current_sale_not_verified','source_identity_not_verified','source_structure_incomplete'}:source.append(flag.upper())
                    else:manual.append(flag.upper())
                if category!=row['category']:manual.append('ASSET_CATEGORY_NOT_CONFIRMED')
        else:source.append('SOURCE_HTML_MISSING')
        if min(item['price'],item['area'])<=0:blocked.append('INVALID_PRICE_OR_AREA')
        if (prior.decimal(row['price_vnd'])!=prior.decimal(rec['normalized_price_vnd'])
            or prior.decimal(row['price_million'])!=prior.decimal(rec['normalized_price_million'])
            or prior.decimal(row['area_sqm'])!=prior.decimal(rec['normalized_area_sqm'])
            or row['category']!=rec['normalized_category'] or row['district']!=rec['normalized_district']
            or row['detail_url']!=rec['detail_url']):blocked.append('STAGED_LABELS_DIFFER_FROM_RECOVERY_EVIDENCE')
        if item['price']>Decimal('999999999999999') or item['area']>Decimal('1000000'):blocked.append('HYBRID_NUMERIC_RANGE_VIOLATION')
        if row['transaction_type']!='SALE' or row['verification_status']!='UNVERIFIED':blocked.append('INVALID_TRANSACTION_OR_VERIFICATION_STATUS')
        if prior.norm(row['district']) not in SUPPORTED_DISTRICTS:source.append('GEOGRAPHIC_SCOPE_REQUIRES_REVIEW')
        if key in held_keys or expected in held_pairs or row['pipeline_group'] in held_pipeline or prior.truth(row['protected_holdout']) or prior.truth(row['original_pipeline_protected_holdout']):blocked.append('PROTECTED_HOLDOUT_ID_OR_GROUP')
        try:
            issues=json.loads(row['quality_issues'])
            if row['quality_status'] not in {'VALID','NEEDS_REVIEW'} or not isinstance(issues,list) or set(issues)-{'NEAR_DUPLICATE','MISSING_DISTRICT'}:blocked.append('HYBRID_QUALITY_GATE_VIOLATION')
        except (TypeError,ValueError):blocked.append('INVALID_QUALITY_METADATA')
        unit=item['price']/item['area'] if item['area']>0 else Decimal(0)
        if unit>0:manual.extend(peer_outlier(unit,peers[(item['category'],item['district'])]))
        match_keys=[];holdout_matches=[];platform_matches=[]
        # Global URL/identity/pipeline checks, plus feature matching in comparable buckets.
        comparable={p['key']:p for p in buckets[(item['category'],item['district'])]}
        for p in pool.values():
            if item['url'] and item['url']==p['url'] or item['pipeline_group'] and item['pipeline_group']==p['pipeline_group']:
                comparable[p['key']]=p
        for other in comparable.values():
            rules=match_rules(item,other)
            if not rules:continue
            links.append(dict(record_key=key,matched_key=other['key'],rules='|'.join(rules),protected_risk=other['holdout'],platform=other['platform'],matching_is_physical_proof=False))
            if other['key'] in stage_keys:match_keys.append(other['key'])
            elif other['holdout']:
                holdout_matches.append(other['key']);blocked.append('POSSIBLE_HOLDOUT_'+rules[0])
            elif other['platform']:
                platform_matches.append(other['key']);manual.append('POSSIBLE_INTERNAL_PROPERTY_DUPLICATE')
            else:manual.append('POSSIBLE_EXISTING_OR_QUARANTINED_SOURCE_DUPLICATE')
        analyses[key]=dict(row=row,blocked=set(blocked),manual=set(manual),source=set(source),refs=refs,
            unit=unit,fingerprint=item['fingerprint'],stage_matches=match_keys,holdout_matches=holdout_matches,platform_matches=platform_matches,
            source_flags=sorted(set(manual+source)),peer_count=len(peers[(item['category'],item['district'])]))
    # Preserve 18.3 clusters and add stronger review links; propagate holdout risk.
    known=defaultdict(list)
    for row in stage:
        if row['duplicate_group']:known[row['duplicate_group']].append(row['record_key'])
        if row['pipeline_group']:known['pipeline:'+row['pipeline_group']].append(row['record_key'])
    components=prior.merged_groups(stage_keys,list(known.values())+[[k]+a['stage_matches'] for k,a in analyses.items()])
    for key,a in analyses.items():
        if any(analyses[s]['holdout_matches'] or any('HOLDOUT' in x for x in analyses[s]['blocked']) for s in components[key]):a['blocked'].add('HOLDOUT_RISK_IN_FINAL_CLUSTER')
    output=[]
    for key in sorted(analyses):
        a=analyses[key];row=a['row'];decision=classify(a['blocked'],a['manual'],a['source'])
        reasons=sorted(a['blocked'])+sorted(a['manual'])+sorted(a['source'])
        cluster='review18_4_'+digest('|'.join(sorted(components[key])))[:24]
        output.append(dict(record_key=key,source=row['source'],source_listing_id=row['source_listing_id'],detail_url=row['detail_url'],
            category=row['category'],district=row['district'],price_vnd=row['price_vnd'],price_million=row['price_million'],area_sqm=row['area_sqm'],
            derived_price_per_sqm_vnd=format(a['unit'].quantize(Decimal('.01')),'f'),unit_price_peer_count=a['peer_count'],
            transaction_type=row['transaction_type'],verification_status='UNVERIFIED',quality_status=row['quality_status'],quality_issues=row['quality_issues'],
            protected_holdout=key in held_keys,possible_holdout_keys='|'.join(sorted(a['holdout_matches'])),
            possible_internal_keys='|'.join(sorted(a['platform_matches'])),previous_duplicate_group=row['duplicate_group'],pipeline_group=row['pipeline_group'],
            final_suspected_cluster=cluster,cluster_members='|'.join(sorted(components[key])),fingerprint_sha256=a['fingerprint'],
            decision=decision,reason_code='|'.join(reasons) if reasons else 'PASSED_FINAL_TECHNICAL_REVIEW_UNVERIFIED_ONLY',
            evidence_reference='|'.join(a['refs']),source_fetched_at_utc=row['evidence_fetched_at_utc'],
            assigned_split=row['assigned_split'],reserved_splits=row['reserved_splits'],training_allowed=row['training_allowed'],
            physical_identity_verified=False,current_sale_owner_legal_verified=False))
    for name,decision in [('ready_for_internal_import.csv',DECISIONS[0]),('needs_manual_review.csv',DECISIONS[1]),('blocked.csv',DECISIONS[2]),('needs_source_verification.csv',DECISIONS[3])]:
        rows=[r for r in output if r['decision']==decision]
        with (OUT/name).open('w',encoding='utf-8-sig',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=list(output[0]));writer.writeheader();writer.writerows(rows)
    prior.write_csv(OUT/'final_review_audit.csv',output);prior.write_csv(OUT/'duplicate_review_links.csv',links)
    ready={r['record_key'] for r in output if r['decision']==DECISIONS[0]}
    ready_clusters={r['final_suspected_cluster'] for r in output if r['record_key'] in ready}
    after=client.query(checksum_sql)
    input_manifest={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in list(BEFORE.glob('*')) if p.is_file()}
    summary=dict(status='READ_ONLY_REVIEW_COMPLETE',identity=identity,source_count=275,decisions={d:sum(r['decision']==d for r in output) for d in DECISIONS},
        total_suspected_clusters=len({r['final_suspected_cluster'] for r in output}),previous_suspected_clusters=227,
        ready_suspected_clusters=len(ready_clusters),ready_listings=len(ready),direct_holdout=sum(r['record_key'] in held_keys for r in output),
        possible_holdout_listings=sum(bool(a['holdout_matches']) for a in analyses.values()),blocked_holdout_cluster_listings=sum('HOLDOUT_RISK_IN_FINAL_CLUSTER' in a['blocked'] for a in analyses.values()),
        possible_internal_duplicate_listings=sum(bool(a['platform_matches']) for a in analyses.values()),
        normalized_url_holdout_links=sum('NORMALIZED_SOURCE_URL' in r['rules'] and r['protected_risk'] for r in links),
        fingerprint_holdout_links=sum('EXACT_FEATURE_FINGERPRINT' in r['rules'] and r['protected_risk'] for r in links),
        match_rules=dict(Counter(rule for r in links for rule in r['rules'].split('|'))),
        source_html_available=sum((ROOT/r['evidence_path']).is_file() for r in stage),
        fingerprint_coverage=sum(bool(a['fingerprint']) for a in analyses.values()),
        ready_fingerprint_coverage=sum(bool(analyses[k]['fingerprint']) for k in ready),
        unique_source_pairs=len(stage_pairs),new_source_pairs=sum(source_pair(r['source'],r['source_listing_id']) not in old_pairs for r in stage),
        reason_counts_overlap=dict(Counter(code for r in output for code in r['reason_code'].split('|'))),
        possible_duplicates_outside_stage=[dict(record_key=r['record_key'],matched_key=r['matched_key'],rules=r['rules']) for r in links if r['matched_key'] not in stage_keys],
        mysql_external_count=len(db),mysql_holdout_count=983,full_pipeline_holdout_count=sum(prior.truth(r.get('protected_holdout')) for r in originals.values()),
        protected_keys_with_group_expansion=len(held_keys),unique_indexes=unique_indexes,preexisting_source_pair_duplicates=source_duplicates,
        full_table_checksums_before=before,full_table_checksums_after=after,all_48_tables_unchanged=before==after,
        source_price_area_fabricated=False,mysql_writes=0,import_executed=False,physical_unique_assets='UNKNOWN')
    (OUT/'audit-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    (OUT/'input-manifest.json').write_text(json.dumps(input_manifest,ensure_ascii=False,indent=2),encoding='utf8')
    if before!=after:raise RuntimeError('Database changed concurrently; inspect before/after checksums; no writes by audit')
    print(json.dumps({k:v for k,v in summary.items() if not k.startswith('full_table')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
