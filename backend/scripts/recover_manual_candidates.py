"""Step18.4.1: batch evidence recovery; writes new audit files, never MySQL.

No network requests, Flyway, import SQL or model fitting. Cached HTML is read
once per source key; every resolution is traceable and stays UNVERIFIED.
"""
import argparse,contextlib,copy,csv,hashlib,io,json,re,subprocess
from collections import Counter,defaultdict
from decimal import Decimal
from pathlib import Path
import final_review_recovered as review
import recovery_source_rules as rules

ROOT=review.ROOT;PREVIOUS=review.OUT;OUT=ROOT/'.scratch/hybrid-full-audit/step18-4-1'
DECISIONS=['AUTO_RECOVERED_READY','NEEDS_MANUAL_REVIEW','NEEDS_SOURCE_EVIDENCE','BLOCKED']

def issue_categories(code):
    code=code.upper();result=set()
    if any(s in code for s in ['PRICE','PARTIAL','STRUCTURED_AND_DISPLAYED']):result.add('PRICE_CONFLICT')
    if any(s in code for s in ['AREA','DIMENSION']):result.add('AREA_CONFLICT')
    if any(s in code for s in ['LOCATION','DISTRICT','PROVINCE','SCOPE','GEOGRAPH']):result.add('LOCATION_CONFLICT')
    if any(s in code for s in ['CATEGORY','ASSET_TYPE','SPECIAL_OR_WHOLE','MIXED_LAND','TRANSACTION','NON_MODEL']):result.add('CATEGORY_CONFLICT')
    if any(s in code for s in ['DUPLICATE','FINGERPRINT','REPEATED_SOURCE','EXISTING_KEY']):result.add('DUPLICATE_RISK')
    if 'HOLDOUT' in code:result.add('HOLDOUT_RISK')
    if any(s in code for s in ['SOURCE','EVIDENCE','PENDING','HASH','HTML','IDENTITY','PROJECT']):result.add('SOURCE_EVIDENCE_CONFLICT')
    if 'MULTIPLE_ASSETS' in code:result|={'PRICE_CONFLICT','AREA_CONFLICT'}
    return result or {'OTHER'}

def write_csv(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader();w.writerows(rows)

def mysql_data():
    client,identity=review.prior.read_local()
    names=client.query("SELECT table_name FROM information_schema.tables WHERE table_schema='smartprop' AND table_type='BASE TABLE' ORDER BY table_name").splitlines()
    if len(names)!=48 or any(not re.fullmatch(r'[A-Za-z0-9_]+',n) for n in names):raise RuntimeError('Unexpected schema')
    sql='CHECKSUM TABLE '+','.join('`'+n+'`' for n in names)+' EXTENDED';before=client.query(sql)
    db=client.objects("""SELECT JSON_OBJECT('record_key',record_key,'source',source,'source_listing_id',source_listing_id,
      'detail_url',detail_url,'title',title,'category',category,'district',district,'address_raw',address_raw,
      'price_million',CAST(price_million AS CHAR),'area_sqm',CAST(area_sqm AS CHAR),'duplicate_group',duplicate_group,
      'quality_status',quality_status,'quality_issues',quality_issues,'verification_status',verification_status,
      'is_protected_holdout',is_protected_holdout,'is_duplicate',is_duplicate,'transaction_type',transaction_type)
      FROM external_listings ORDER BY record_key""")
    internal=client.objects("""SELECT JSON_OBJECT('record_key',CONCAT('property:',id),'title',title,'category',property_type,
      'district',district,'address_raw',address,'price',CAST(price AS CHAR),'area_sqm',CAST(area_sqm AS CHAR)) FROM properties ORDER BY id""")
    if len(db)!=3204 or len(internal)!=16 or sum(bool(r['is_protected_holdout']) for r in db)!=983:raise RuntimeError('Source inventory changed')
    return client,identity,db,internal,sql,before

def main():
    argparse.ArgumentParser(description=__doc__).parse_args();OUT.mkdir(parents=True,exist_ok=True)
    if subprocess.check_output(['git','branch','--show-current'],cwd=ROOT,text=True).strip()!='backend-huy-latest':raise RuntimeError('Wrong branch')
    read=review.prior.rows
    target=read(PREVIOUS/'needs_manual_review.csv');old_ready=read(PREVIOUS/'ready_for_internal_import.csv');old_blocked=read(PREVIOUS/'blocked.csv')
    assert len(target)==len({r['record_key'] for r in target})==257 and len(old_ready)==17 and len(old_blocked)==1
    stage={r['record_key']:r for r in read(review.BEFORE/'prepared_unverified.csv')}
    originals={r['record_key']:r for r in read(ROOT/'ai-services/app/data/processed/remaining_diversity_review/runs/518bbc989587326c/all_listings_after_review.csv')}
    recovered={r['record_key']:r for r in read(ROOT/'.scratch/hybrid-full-audit/step18-2/recovered_hybrid_candidates.csv')}
    base=ROOT/'ai-services/app/data/processed/collection_source_review'
    parsed=json.loads((base/'parsed_evidence.json').read_text(encoding='utf8'));manifest=json.loads((base/'fetch_manifest.json').read_text(encoding='utf8'))
    client,identity,db,internal,checksum_sql,before=mysql_data()
    held_groups={r['duplicate_group'] for r in db if r['is_protected_holdout'] and r['duplicate_group']}
    held_keys={r['record_key'] for r in db if r['is_protected_holdout'] or r['duplicate_group'] in held_groups}
    held_keys.update(k for k,r in originals.items() if review.prior.truth(r.get('protected_holdout')))
    held_pipeline={r['pipeline_group'] for k,r in originals.items() if k in held_keys and r.get('pipeline_group')}
    held_keys.update(k for k,r in originals.items() if r.get('pipeline_group') in held_pipeline)
    # Previous holdout quarantine is never silently removed, even though it is
    # a suspected link rather than a declared split membership.
    quarantined={r['record_key'] for r in old_blocked};protected=held_keys|quarantined
    existing_keys={r['record_key'] for r in db};existing_pairs={review.source_pair(r['source'],r['source_listing_id']) for r in db}
    pair_counts=Counter(review.source_pair(r['source'],r['source_listing_id']) for r in target)
    facts={};disk_reads=0
    for old in target:
        key=old['record_key'];row=dict(stage[key]);orig=originals[key];rec=recovered[key]
        path=(ROOT/row['evidence_path']).resolve();hard=set();source=set()
        if key in existing_keys or review.source_pair(row['source'],row['source_listing_id']) in existing_pairs:hard.add('SOURCE_ID_ALREADY_EXISTS')
        if pair_counts[review.source_pair(row['source'],row['source_listing_id'])]>1 or key!=row['source']+':'+row['source_listing_id']:hard.add('INVALID_OR_REPEATED_CANONICAL_SOURCE_ID')
        if row['verification_status']!='UNVERIFIED' or row['transaction_type']!='SALE':hard.add('TRANSACTION_OR_VERIFICATION_VIOLATION')
        if key in protected or row['pipeline_group'] in held_pipeline:hard.add('PROTECTED_HOLDOUT_ID_OR_GROUP')
        e={};result=None
        if path.is_relative_to((base/'detail_cache').resolve()) and path.is_file():
            body=path.read_bytes();disk_reads+=1;sha=hashlib.sha256(body).hexdigest()
            if sha!=row['evidence_sha256'] or sha!=parsed.get(key,{}).get('detail_sha256') or sha!=manifest.get(key,{}).get('sha256'):hard.add('EVIDENCE_HASH_MISMATCH')
            e=review.source_rules.parse_detail(rec,manifest.get(key,{}),body)
            if not all(e.get(f) for f in ['identity_verified','structure_verified','sale_verified']):source.add('SOURCE_IDENTITY_STRUCTURE_SALE_INCOMPLETE')
            if e.get('flags'):source.update(str(f).upper() for f in e['flags'])
            if not hard and not source:
                # Review the already evidenced18.3 labels, preserving earlier
                # workflow flags. Do not revert its category/district to raw CSV.
                baseline=dict(orig);baseline.update(row)
                result=rules.resolve_source(baseline,e)
        else:source.add('HTML_SOURCE_EVIDENCE_MISSING')
        if result:
            values=dict(row);values.update({k:result['values'][k] for k in ['price_million','area_sqm','category','district']})
            assert values['category']==row['category'] and values['district']==row['district']
            values['price_vnd']=str(review.prior.decimal(values['price_million'])*1000000)
            flags={str(f).upper() for f in result['remaining_flags']}
        else:
            values=dict(row);flags=set()
            result=dict(resolved_flags=[],changes=[],rules=[],area_facts=[],money_facts=[],source_values={})
        if 'EXPLICIT_ASSET_OUTSIDE_SUPPORTED_SCOPE' in flags or 'EXPLICIT_NON_MODEL_ASSET' in flags:
            hard|=flags&{'EXPLICIT_ASSET_OUTSIDE_SUPPORTED_SCOPE','EXPLICIT_NON_MODEL_ASSET'}
        if not flags and source:flags|=source
        for field,limit,scale in [('price_million',Decimal('999999999999.99'),2),('area_sqm',Decimal('99999999.99'),2)]:
            value=review.prior.decimal(values[field])
            if value<=0 or value>limit or value!=value.quantize(Decimal(1).scaleb(-scale)):hard.add('INVALID_MYSQL_DECIMAL_LABEL')
        if review.prior.decimal(values['price_vnd'])>Decimal('999999999999999'):hard.add('HYBRID_MAX_BUDGET_EXCEEDED')
        # A prior duplicate risk needs identity reconciliation, not a numerical
        # edit which merely makes its old fuzzy match disappear.
        if 'POSSIBLE_EXISTING_OR_QUARANTINED_SOURCE_DUPLICATE' in old['reason_code']:flags.add('POSSIBLE_EXISTING_OR_QUARANTINED_SOURCE_DUPLICATE')
        facts[key]=dict(old=old,row=row,values=values,source=e,result=result,flags=flags,hard=hard,source_missing=source,links=[])
    normalized=[dict(r) for r in stage.values()]
    for row in normalized:
        if row['record_key'] in facts:row.update(facts[row['record_key']]['values'])
    # Reuse existing quality gate on copies only; independent SALE/identity tests
    # above prevent its SALE default from becoming recovery evidence.
    quality=copy.deepcopy(db+normalized)
    with contextlib.redirect_stdout(io.StringIO()):gate_groups=review.prior.legacy.run_quality_gate(quality)
    gated={r['record_key']:r for r in quality}
    pool={k:review.prepared_item(r,parsed.get(k),k in protected) for k,r in originals.items()}
    for row in db:
        row=dict(row,pipeline_group=originals.get(row['record_key'],{}).get('pipeline_group',''))
        pool[row['record_key']]=review.prepared_item(row,parsed.get(row['record_key']),row['record_key'] in protected)
    for row in internal:pool[row['record_key']]=review.prepared_item(row,platform=True)
    for row in normalized:pool[row['record_key']]=review.prepared_item(row,parsed.get(row['record_key']),row['record_key'] in protected)
    peers=defaultdict(list);seen=set()
    for row in db:
        if row['record_key'] in protected or row['quality_status']!='VALID' or row['transaction_type']!='SALE':continue
        group=row['duplicate_group'] or row['record_key']
        if group in seen:continue
        seen.add(group);p=pool[row['record_key']]
        if min(p['price'],p['area'])>0:peers[(p['category'],p['district'])].append(p['price']/p['area'])
    stage_keys=set(stage);links=[];all_stage_rows=normalized
    by_bucket=defaultdict(list)
    for p in pool.values():by_bucket[(p['category'],p['district'])].append(p)
    for key,a in facts.items():
        item=pool[key];unit=item['price']/item['area'] if item['area']>0 else Decimal(0)
        a['flags'].update(review.peer_outlier(unit,peers[(item['category'],item['district'])]) if unit>0 else ['INVALID_PRICE_OR_AREA'])
        q=gated[key]
        if q['quality_status']=='REJECTED' or set(q['quality_issues'])-{'NEAR_DUPLICATE','MISSING_DISTRICT'}:a['flags'].add('QUALITY_GATE_BLOCKED')
        candidates={p['key']:p for p in by_bucket[(item['category'],item['district'])]}
        for p in pool.values():
            if item['url'] and item['url']==p['url'] or item['pipeline_group'] and item['pipeline_group']==p['pipeline_group']:candidates[p['key']]=p
        for other in candidates.values():
            matches=review.match_rules(item,other)
            # Keep historical links even if the recovered numerical label moved.
            if a['result']['changes']:
                matches=list(set(matches)|set(review.match_rules(review.prepared_item(a['row'],parsed.get(key)),other)))
            if (other['holdout'] and other['key']!=key and item['category']==other['category'] and item['district']==other['district']
                and min(item['area'],other['area'])>0 and abs(item['area']-other['area'])/max(item['area'],other['area'])<=Decimal('.01')
                and item['description_hash'] and item['description_hash']==other['description_hash']):matches.append('HOLDOUT_EXACT_LONG_DESCRIPTION_AREA1_PRICE_CHANGE_RETAINED')
            if not matches:continue
            link=dict(record_key=key,matched_key=other['key'],rules='|'.join(sorted(set(matches))),protected_risk=other['holdout'],platform=other['platform'],physical_identity_proven=False)
            links.append(link);a['links'].append(link)
            if other['holdout']:a['hard'].add('UNRESOLVED_HOLDOUT_LINK')
            elif other['key'] not in stage_keys:a['flags'].add('POSSIBLE_EXISTING_OR_QUARANTINED_SOURCE_DUPLICATE')
    known=defaultdict(list)
    for row in normalized:
        if row['duplicate_group']:known[row['duplicate_group']].append(row['record_key'])
        if row['pipeline_group']:known['pipeline:'+row['pipeline_group']].append(row['record_key'])
    component=review.prior.merged_groups(stage_keys,list(known.values())+[[l['record_key'],l['matched_key']] for l in links if l['matched_key'] in stage_keys]
        +[g['members'] for g in gate_groups])
    previous_impacts=[]
    for key,a in facts.items():
        if any(s in protected or s in facts and facts[s]['hard']&{'UNRESOLVED_HOLDOUT_LINK','PROTECTED_HOLDOUT_ID_OR_GROUP'} for s in component[key]):a['hard'].add('HOLDOUT_RISK_IN_FINAL_CLUSTER')
    for row in old_ready:
        members=component[row['record_key']]
        if any(k in facts and facts[k]['hard'] for k in members):previous_impacts.append(dict(record_key=row['record_key'],issue='NEW_CLUSTER_RISK_REQUIRES_SEPARATE_REVIEW',linked_keys='|'.join(sorted(members)),previous_decision_unchanged=True))
    audit=[];distributions=[]
    for key,a in sorted(facts.items()):
        flags=a['flags']|a['hard']|a['source_missing'];value=a['values']
        source_only={'PRIOR_PENDING_REQUIRES_EXPLICIT_RESOLUTION','SOURCE_IDENTITY_STRUCTURE_SALE_INCOMPLETE','HTML_SOURCE_EVIDENCE_MISSING','SOURCE_LOCATION_CORROBORATION_MISSING'}
        if a['hard']:decision='BLOCKED'
        elif flags and flags<=source_only:decision='NEEDS_SOURCE_EVIDENCE'
        elif flags:decision='NEEDS_MANUAL_REVIEW'
        else:decision='AUTO_RECOVERED_READY'
        cluster='recovery18_4_1_'+review.digest('|'.join(sorted(component[key])))[:24]
        old_values={f:a['row'].get(f,'') for f in ['price_million','price_vnd','area_sqm','category','district','transaction_type','verification_status','latitude','longitude']}
        new_values={f:value.get(f,'') for f in old_values}
        new_values['verification_status']='UNVERIFIED';new_values['latitude']=old_values['latitude'];new_values['longitude']=old_values['longitude']
        q=gated[key];has_group=len(component[key])>1 or bool(a['row']['duplicate_group'])
        issues=sorted(set(q['quality_issues'])|({'NEAR_DUPLICATE'} if has_group else set()))
        new_values.update(quality_status='NEEDS_REVIEW' if issues else 'VALID',quality_issues=issues,duplicate_group=cluster if has_group else None)
        codes=sorted(flags) or ['PASSED_RECOVERED_TECHNICAL_INTERNAL_ONLY']
        audit.append(dict(record_key=key,source=value['source'],source_listing_id=value['source_listing_id'],detail_url=value['detail_url'],
            decision=decision,reason_codes='|'.join(codes),original_reason_codes=a['old']['reason_code'],
            evidence_reference=a['row']['evidence_path']+'#sha256='+a['row']['evidence_sha256'],
            original_values=json.dumps(old_values,ensure_ascii=False,sort_keys=True),recovered_values=json.dumps(new_values,ensure_ascii=False,sort_keys=True),
            recovery_rule='|'.join(a['result']['rules']) or 'NO_EVIDENCE_BACKED_CHANGE',
            field_changes=json.dumps(a['result']['changes'],ensure_ascii=False),resolved_flags='|'.join(a['result']['resolved_flags']),
            quality_gate_result='PASS_INTERNAL_ONLY' if decision=='AUTO_RECOVERED_READY' else 'NOT_ADMITTED',
            duplicate_status='SUSPECTED_CLUSTER_NOT_PHYSICAL_PROOF' if has_group else 'NO_LINK_FOUND_NOT_PHYSICAL_VERIFICATION',
            holdout_status='QUARANTINED_RISK' if any('HOLDOUT' in c for c in codes) else 'NO_LINK_FOUND_UNDER_RULES',
            suspected_cluster=cluster,cluster_members='|'.join(sorted(component[key])),
            source_fact_details=json.dumps(dict(area_facts=a['result']['area_facts'],money_facts=a['result']['money_facts'],raw=a['result']['source_values']),ensure_ascii=False),
            verification_status='UNVERIFIED',latitude=value.get('latitude',''),longitude=value.get('longitude','')))
    for phase in ['BEFORE','AFTER']:
        counts=Counter();occurrences=Counter()
        for row in audit:
            codes=row['original_reason_codes' if phase=='BEFORE' else 'reason_codes'].split('|')
            codes=[c for c in codes if not c.startswith('PASSED_')]
            categories=set()
            for code in codes:
                mapped=issue_categories(code);categories|=mapped;occurrences.update(mapped)
            counts.update(categories)
        for cat in ['PRICE_CONFLICT','AREA_CONFLICT','LOCATION_CONFLICT','CATEGORY_CONFLICT','DUPLICATE_RISK','HOLDOUT_RISK','SOURCE_EVIDENCE_CONFLICT','OTHER']:
            distributions.append(dict(phase=phase,issue_category=cat,unique_records=counts[cat],flag_occurrences=occurrences[cat],categories_overlap=True))
    names=['auto_recovered_ready.csv','needs_manual_review_remaining.csv','needs_source_evidence.csv','blocked.csv']
    for name,decision in zip(names,DECISIONS):write_csv(OUT/name,[r for r in audit if r['decision']==decision],list(audit[0]))
    write_csv(OUT/'recovery_audit.csv',audit,list(audit[0]));write_csv(OUT/'issue_distribution.csv',distributions,list(distributions[0]))
    review.prior.write_csv(OUT/'duplicate_holdout_links.csv',links)
    write_csv(OUT/'previous_decisions_new_findings.csv',previous_impacts,['record_key','issue','linked_keys','previous_decision_unchanged'])
    ready=[r for r in audit if r['decision']=='AUTO_RECOVERED_READY'];ready_keys={r['record_key'] for r in ready}
    proposed_keys=ready_keys|{r['record_key'] for r in old_ready}
    fixture=[]
    for row in normalized:
        key=row['record_key'];eligible=key in proposed_keys
        if key in ready_keys:new=json.loads(next(r['recovered_values'] for r in ready if r['record_key']==key))
        else:new=dict(row,quality_issues=json.loads(row['quality_issues']))
        cluster='recovery18_4_1_'+review.digest('|'.join(sorted(component[key])))[:24]
        group=cluster if len(component[key])>1 or row['duplicate_group'] else None
        issues=sorted(set(new['quality_issues'])|({'NEAR_DUPLICATE'} if group else set()))
        fixture.append(dict(recordKey=key,source=row['source'],category=new['category'],district=new['district'],
            priceVnd=str(review.prior.decimal(new['price_million'])*1000000),areaSqm=new['area_sqm'],
            qualityStatus='NEEDS_REVIEW' if issues else 'VALID',qualityIssues=issues,verificationStatus='UNVERIFIED',
            duplicateGroup=group,holdoutRisk=key in protected or key in facts and any('HOLDOUT' in f for f in facts[key]['hard']),
            decision='PREVIOUS_READY_UNCHANGED' if key in {r['record_key'] for r in old_ready} else next(r['decision'] for r in audit if r['record_key']==key) if key in facts else 'PREVIOUS_BLOCKED_UNCHANGED',
            admitted=eligible,latitude=None,longitude=None))
    assert len(audit)==257 and len({r['record_key'] for r in audit})==257
    assert not any(r['admitted'] and r['holdoutRisk'] for r in fixture)
    (OUT/'offline_candidates.json').write_text(json.dumps(fixture,ensure_ascii=False,indent=2),encoding='utf8')
    after=client.query(checksum_sql)
    summary=dict(identity=identity,total_reviewed=257,decisions={d:sum(r['decision']==d for r in audit) for d in DECISIONS},
        records_with_field_recovery=sum(bool(a['result']['changes']) for a in facts.values()),field_recovery_events=sum(len(a['result']['changes']) for a in facts.values()),
        records_with_rule_resolution=sum(bool(a['result']['resolved_flags']) for a in facts.values()),
        ready_added=len(ready),previous_ready_unchanged=17,combined_proposed=len(proposed_keys),
        added_suspected_clusters=len({tuple(sorted(component[k])) for k in ready_keys}),
        combined_suspected_clusters=len({tuple(sorted(component[k])) for k in proposed_keys}),
        previous_ready_new_findings=len(previous_impacts),original_holdout_blocked_unchanged=1,
        mysql_external=3204,mysql_holdouts=983,full_pipeline_holdouts=sum(review.prior.truth(r.get('protected_holdout')) for r in originals.values()),
        new_holdout_risk_records=sum(r['holdout_status']=='QUARANTINED_RISK' for r in audit),
        html_disk_reads=disk_reads,source_parser_calls=disk_reads,cached_parse_records=len(facts),external_website_requests=0,
        all_48_table_checksums_before=before,all_48_table_checksums_after=after,all_48_tables_unchanged=before==after,
        mysql_writes=0,import_executed=False,all_new_candidates_unverified=True,physical_unique_assets='UNKNOWN',
        ready_source_counts=dict(Counter(r['source'] for r in ready)))
    (OUT/'recovery-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    if before!=after:raise RuntimeError('Concurrent database change; review checksums before continuing')
    print(json.dumps({k:v for k,v in summary.items() if not k.startswith('all_48_table_checksums')},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
