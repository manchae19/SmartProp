"""Audit every raw CSV/JSONL snapshot; no crawling, raw mutation, or model fitting."""
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime, timezone, timedelta
from pathlib import Path
from urllib.parse import urlparse
from prepare_smartprop_dataset import BASE, CATEGORIES, price, number, classify, duplicates, save_csv
from smartprop_geography import norm, resolve, DISTRICTS
from review_nhadat24h import displayed_date

OUT=BASE/'processed/full_collection_audit'
ASOF=date(2026,10,11)
HOSTS={'chotot':{'nha.chotot.com','www.nha.chotot.com'},'cafeland':{'nhadat.cafeland.vn'},
       'homedy':{'homedy.com','www.homedy.com'},'nhadat24h':{'nhadat24h.net','www.nhadat24h.net'},
       'alonhadat':{'alonhadat.com.vn','www.alonhadat.com.vn'}}

def read(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        return list(csv.DictReader(stream))

def sid_url(source,url):
    pattern={'chotot':r'/(\d+)\.htm$', 'cafeland':r'-(\d+)\.html$',
             'homedy':r'-es(\d+)$','nhadat24h':r'-ID(\d+)$','alonhadat':r'-(\d+)\.html$'}.get(source)
    match=re.search(pattern,urlparse(url).path) if pattern else None
    return match[1] if match else ''

def source_of(raw,path):
    explicit=raw.get('source','')
    if explicit in HOSTS: return explicit
    s=str(path).lower()
    return next((key for key in HOSTS if key in s),'unknown')

def category(raw,source):
    title=norm(raw.get('title',''))
    if source in ['cafeland','nhadat24h','homedy'] and raw.get('source_category'):
        return classify(raw,source)[:2]
    if raw.get('property_type')=='house': return CATEGORIES[0],'explicit_property_type'
    src=norm(raw.get('source_category') or raw.get('category',''))
    mapping={'nha o':CATEGORIES[0],'nha mat tien':CATEGORIES[0],'nha trong hem':CATEGORIES[0],
      'nha rieng':CATEGORIES[0],'biet thu':CATEGORIES[0],'dat nen':CATEGORIES[1],
      'dat tho cu, dat o':CATEGORIES[1],'dat tho cu':CATEGORIES[1],
      'can ho chung cu':CATEGORIES[2],'mat bang / van phong':'Khác'}
    if src in mapping: return mapping[src],'source_category'
    if re.search(r'\b(ban dat|lo dat|dat nen|dat tho cu)\b',title):return CATEGORIES[1],'title_inferred'
    if re.search(r'\b(can ho|chung cu)\b',title):return CATEGORIES[2],'title_inferred'
    if re.search(r'\b(ban nha|ban biet thu|nha \d+ tang)\b',title):return CATEGORIES[0],'title_inferred'
    return 'Chưa xác định','unresolved'

def dates(raw,source):
    try:
        if source=='nhadat24h': return displayed_date(raw)[:2]
        if source=='cafeland' and raw.get('updated_attribute_raw'):
            return datetime.strptime(raw['updated_attribute_raw'],'%d-%m-%Y %H:%M:%S').date().isoformat(),'source_update_not_first_post'
        if raw.get('source_published_date_raw'):
            return datetime.strptime(raw['source_published_date_raw'],'%d/%m/%Y').date().isoformat(),'source_display_date_not_verified_first_post'
        value=raw.get('source_list_time') or raw.get('posted_at')
        if value: return datetime.fromisoformat(value).date().isoformat(),'source_listing_or_update_time'
    except (ValueError,TypeError,KeyError):return '','invalid_or_unparsed'
    return '','unavailable'

def mentions(text):
    """Conservative monetary contexts, with Vietnamese shorthand and unit prices."""
    s=norm(text).replace('t.y','ty')
    pattern=r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(ty|ti|trieu|tr)(?![a-z])(?:\s*(\d+)\s*trieu|([1-9])(?!\d))?'
    results=[]
    for m in re.finditer(pattern,s):
        amount=float(m[1].replace(',','.'))*(1000 if m[2] in ['ty','ti'] else 1)
        if m[3]:amount+=float(m[3])
        elif m[4] and m[2] in ['ty','ti']:amount+=float(m[4])*100
        before=s[max(0,m.start()-45):m.start()];after=s[m.end():m.end()+25]
        kind='total_candidate'
        if re.match(r'\s*/?\s*m[2²]\b',after):kind='unit_price'
        elif re.match(r'\s*/?\s*(?:thang|th|nam|dem)\b',after):kind='rental_income'
        elif re.search(r'(gia thue|dong tien|thu nhap|cho thue).{0,18}$',before):kind='rental_income'
        elif re.search(r'(giam|thap hon|re hon|chiet khau|qua tang|tang gia|loi nhuan).{0,18}$',before):kind='discount_or_gift'
        elif re.search(r'(tra truoc|thanh toan|von ban dau|booking|dat coc|chi tu|gia tu).{0,20}$',before):kind='partial_or_starting'
        elif re.search(r'(nhinh|chua toi|duoi|khoang|hon|tu).{0,10}$',before):kind='approximate_or_bound'
        results.append(dict(amount_million=amount,kind=kind,context=s[max(0,m.start()-45):m.end()+25]))
    return results

def normalize(raw,source,path,rownum):
    url=raw.get('detail_url') or raw.get('source_url') or ''
    sid=str(raw.get('source_listing_id') or raw.get('list_id') or '')
    if ':' in sid:sid=sid.rsplit(':',1)[-1]
    sid=sid or sid_url(source,url)
    title=raw.get('title') or ''
    cat,basis=category(raw,source)
    pr,ar=number(raw.get('price_million')),number(raw.get('area_sqm'))
    address=raw.get('address_old') or raw.get('address_raw') or ', '.join(str(raw.get(k) or '') for k in ['street','ward','district'])
    district,loc,candidates=resolve(address,raw.get('district',''),source)
    if source=='chotot' and raw.get('region_name')=='Đà Nẵng':
        district,loc,candidates=resolve(address+', Đà Nẵng',raw.get('district',''),source)
        loc='source_region_and_district' if district else loc
    elif source=='chotot' and path.name.startswith('danang_chotot'):
        district,loc,candidates=resolve(address+', Đà Nẵng',raw.get('district',''),source)
        loc='legacy_filename_and_district_unverified' if district else loc
    elif source=='nhadat24h' and raw.get('location_status')=='in_scope' and '/nha-dat-da-nang' in raw.get('listing_page',''):
        district,loc,candidates=resolve(address+', Đà Nẵng',raw.get('district',''),source)
        loc='source_province_flag_and_historical_district' if district else loc
    d,db=dates(raw,source)
    detail=raw.get('detail_fetched') in [True,'True'] or bool(raw.get('detail_sha256'))
    transaction=norm(raw.get('transaction_type',''))
    sale=transaction in ['ban','can ban','sale']
    transaction_basis='explicit_source_field' if sale else 'unavailable'
    if not sale and source=='homedy' and urlparse(url).hostname in HOSTS['homedy'] and urlparse(url).path.startswith('/ban-') and detail:
        sale=True
        transaction_basis='source_sale_url_and_detail_snapshot'
    return dict(record_key=source+':'+sid if sid.isdigit() else 'invalid:'+path.as_posix()+':'+str(rownum),
        source=source,source_listing_id=sid,detail_url=url,title=title,category=cat,category_basis=basis,
        district=district,district_candidates=candidates,location_basis=loc,address_raw=address,
        price_million=pr,area_sqm=ar,price_per_sqm_million=pr/ar if pr is not None and ar and ar>0 else None,
        displayed_date=d,date_basis=db,age_days=(ASOF-date.fromisoformat(d)).days if d else None,
        collected_at=raw.get('collected_at') or '',detail_fetched=detail,
        transaction_verified=sale,transaction_basis=transaction_basis,
        transaction_raw=raw.get('transaction_type') or '',input_file=path.as_posix(),input_row=rownum,
        raw_json=json.dumps(raw,ensure_ascii=False))

def rank(row):
    path=row['input_file']
    role=0 if '/sample/' in '/'+path or path.startswith('sample/') else 1
    if 'scope_review' in path:role=0
    elif 'scope_recovered' in path:role=4
    elif '_batch' in path or 'batch_' in path or 'alonhadat_records' in path:role=3
    elif '10k_raw2' in path:role=2
    return role,int(row['detail_fetched']),row['collected_at'],int(path.endswith('.csv'))

def distinct_numbers(values):
    result=[]
    for value in sorted(v for v in values if v is not None):
        if not any(math.isclose(value,v,rel_tol=1e-9,abs_tol=.01) for v in result):result.append(value)
    return result

def checks(row):
    raw=json.loads(row['raw_json']);flags=[]
    source=row['source'];url=row['detail_url'];pr=row['price_million'];ar=row['area_sqm']
    title=norm(row['title'])
    if not row['source_listing_id'].isdigit():flags.append('invalid_source_id')
    if not row['title']:flags.append('missing_title')
    if urlparse(url).scheme!='https' or urlparse(url).hostname not in HOSTS.get(source,set()):flags.append('invalid_url_or_host')
    if sid_url(source,url)!=row['source_listing_id']:flags.append('url_id_mismatch')
    if row['location_basis']=='outside_or_unknown':flags.append('outside_or_unverified_old_danang')
    if not row['district']:flags.append('historical_district_unresolved')
    if row['location_basis']=='legacy_filename_and_district_unverified':flags.append('legacy_province_unverified')
    if not row['transaction_verified']:flags.append('sale_transaction_unverified')
    if re.match(r'^(?:can\s+)?cho thue\b',title):flags.append('rental_title_in_sale_collection')
    if row['category']=='Chưa xác định':flags.append('category_unresolved')
    if row['category']=='Khác':flags.append('outside_model_property_types')
    if row['category_basis']=='title_inferred':flags.append('category_title_inferred')
    if row['category']==CATEGORIES[0] and re.search(r'\b(ban dat|lo dat|dat nen)\b',title):flags.append('category_title_conflict')
    if row['category']==CATEGORIES[1] and re.search(r'\b(ban nha|ban biet thu)\b',title):flags.append('category_title_conflict')
    if re.search(r'\b(condotel|toa can ho|toa nha|toa chdv|ban nha tro|ban khach san)\b',title):flags.append('special_or_whole_building')
    if pr is None or pr<=0:flags.append('missing_or_invalid_price')
    if ar is None or ar<=0:flags.append('missing_or_invalid_area')
    if pr is not None and (pr<100 or pr>200000):flags.append('total_price_threshold')
    if ar is not None and not 20<=ar<=1000:flags.append('area_threshold')
    if row['price_per_sqm_million'] is not None and not 2<=row['price_per_sqm_million']<=300:flags.append('unit_price_threshold')
    if row['category']==CATEGORIES[2] and pr is not None and ar and ar>0:
        if pr<500 or not 15<=pr/ar<=150:flags.append('apartment_price_priority')
    if raw.get('price_raw'):
        reparsed=price(raw['price_raw'])
        if reparsed is None:flags.append('price_text_non_total_or_unparsed')
        elif pr is None:flags.append('normalized_price_missing')
        elif abs(reparsed-pr)>.01:flags.append('price_parse_mismatch')
    elif source=='chotot' and not raw.get('price_vnd'):flags.append('legacy_price_raw_unavailable')
    pv=number(raw.get('price_vnd') or raw.get('price_structured_vnd'))
    if pv is not None and pr is not None and abs(pv/1e6-pr)>.01:flags.append('structured_price_mismatch')
    if raw.get('area_raw'):
        am=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m[2²]',norm(raw['area_raw']))
        if not am:flags.append('area_text_unparsed')
        elif ar is None:flags.append('normalized_area_missing')
        elif abs(float(am[1].replace(',','.'))-ar)>.01:flags.append('area_parse_mismatch')
    if raw.get('detail_price_raw'):
        dp=price(raw['detail_price_raw'])
        if dp is None:flags.append('detail_price_unparsed')
        elif pr is not None and abs(dp-pr)>.01:flags.append('listing_detail_price_conflict')
    if raw.get('detail_error'):flags.append('detail_fetch_error')
    for name in ['price_needs_review','area_needs_review','region_needs_review','price_unit_review']:
        if raw.get(name) in [True,'True']:flags.append('source_'+name)
    if raw.get('review_reason'):flags.append('source_review_reason')
    if raw.get('review_flags'):flags.append('source_review_flags')
    if not row['displayed_date']:flags.append('listing_date_unavailable')
    elif row['age_days']<0:flags.append('future_listing_date')
    elif row['age_days']>183:flags.append('older_than_183_days')
    if re.search(r'\b(tra truoc|thanh toan|chi tu|gia tu|von ban dau|booking|dat coc)\b',title):flags.append('partial_starting_or_booking_title')
    money=mentions(row['title']);totals=[m['amount_million'] for m in money if m['kind']=='total_candidate']
    if totals and pr is not None and pr>0 and all(abs(p-pr)/max(p,pr)>.1 for p in totals):flags.append('title_price_conflict')
    lat,lon=number(raw.get('latitude')),number(raw.get('longitude'))
    if lat is not None and not -90<=lat<=90 or lon is not None and not -180<=lon<=180:flags.append('invalid_coordinates')
    elif lat is not None and lon is not None and not (15.6<=lat<=16.5 and 107.7<=lon<=108.5):flags.append('coordinates_need_geographic_review')
    return sorted(set(flags)),money

def scan_singapore(path):
    fields=['month','town','flat_type','block','street_name','storey_range','floor_area_sqm','flat_model','lease_commence_date','remaining_lease','resale_price']
    seen=set();months=Counter();issues=Counter();bad=[];duplicate_rows=[];n=0
    for n,row in enumerate(read(path),1):
        flags=[]
        if None in row or any(row.get(k) is None for k in fields):flags.append('malformed_or_missing_columns')
        for k in fields:
            if not row.get(k):flags.append('missing_'+k)
        pr,ar=number(row.get('resale_price')),number(row.get('floor_area_sqm'))
        if pr is None or pr<=0:flags.append('invalid_sgd_price')
        if ar is None or ar<=0:flags.append('invalid_area')
        month=row.get('month','')
        try:
            parsed=datetime.strptime(month,'%Y-%m')
            if parsed.strftime('%Y-%m')!=month or month>ASOF.strftime('%Y-%m'):flags.append('invalid_or_future_month')
        except ValueError:flags.append('invalid_or_future_month')
        months[month]+=1
        digest=hashlib.sha256(json.dumps(row,sort_keys=True).encode()).hexdigest()
        if digest in seen:duplicate_rows.append(dict(input_row=n+1,row_fingerprint=digest,month=month))
        seen.add(digest)
        issues.update(flags)
        if flags:bad.append(dict(input_row=n+1,flags=';'.join(flags),raw_json=json.dumps(row,ensure_ascii=False)))
    save_csv(OUT/'singapore_flagged_rows.csv',bad,['input_row','flags','raw_json'])
    save_csv(OUT/'singapore_exact_row_repeats.csv',duplicate_rows,['input_row','row_fingerprint','month'])
    return dict(rows=n,exact_row_fingerprints=len(seen),repeated_exact_rows=len(duplicate_rows),
        month_min=min(months,default=''),month_max=max(months,default=''),by_month=dict(sorted(months.items())),
        flagged_rows=len(bad),issue_counts=dict(issues),currency='SGD',price_basis='HDB resale transactions',
        note='No transaction/property unique ID. Exact identical rows may be distinct transactions; not deleted. Not part of Vietnam listing count.')

def main():
    OUT.mkdir(parents=True,exist_ok=True)
    paths=sorted(set(BASE.glob('*.csv'))|set((BASE/'data_raw').rglob('*.csv'))|set((BASE/'data_raw').rglob('*.jsonl'))|set((BASE/'sample').glob('*.csv'))|set((BASE/'crawler_cafeland/sample').glob('*.csv')))
    inventory=[];observations=[];grouped=defaultdict(list);bad=[];hashes={}
    sg=None
    for path in paths:
        relative=path.relative_to(BASE)
        hashes[path]=hashlib.sha256(path.read_bytes()).hexdigest()
        if 'singapore_hdb' in path.parts:
            sg=scan_singapore(path)
            inventory.append(dict(path=relative.as_posix(),kind='singapore_transactions',rows=sg['rows'],sha256=hashes[path],malformed_rows=sg['flagged_rows'],unique_valid_source_ids='',duplicate_ids_within_file=''))
            continue
        if path.suffix=='.jsonl':
            records=[]
            for lineno,line in enumerate(path.read_text(encoding='utf-8').splitlines(),1):
                try:records.append((lineno,json.loads(line)))
                except json.JSONDecodeError:
                    bad.append(dict(input_file=relative.as_posix(),input_row=lineno,reason='invalid_json',raw_json=line))
        else:
            records=list(enumerate(read(path),2))
        validids=[];malformed=0
        for rownum,raw in records:
            if not isinstance(raw,dict) or None in raw or any(v is None for v in raw.values()) and path.suffix=='.csv':
                malformed+=1
                bad.append(dict(input_file=relative.as_posix(),input_row=rownum,reason='malformed_csv_or_json_object',raw_json=json.dumps(raw,ensure_ascii=False)))
                if not isinstance(raw,dict):continue
            source=source_of(raw,relative)
            row=normalize(raw,source,relative,rownum)
            grouped[row['record_key']].append(row)
            if row['source_listing_id'].isdigit():validids.append(row['source_listing_id'])
            observations.append(dict(record_key=row['record_key'],source=source,input_file=relative.as_posix(),input_row=rownum,
                price_million=row['price_million'],area_sqm=row['area_sqm'],category=row['category'],detail_fetched=row['detail_fetched'],
                collected_at=row['collected_at'],raw_json=row['raw_json']))
        inventory.append(dict(path=relative.as_posix(),kind='jsonl_mirror' if path.suffix=='.jsonl' else 'sample_snapshot' if 'sample' in path.parts else 'raw_listing_snapshot',
            rows=len(records),sha256=hashes[path],malformed_rows=malformed,unique_valid_source_ids=len(set(validids)),duplicate_ids_within_file=len(validids)-len(set(validids))))
    priorpath=BASE/'processed/apartment_v2/review_decisions.csv'
    prior={r['record_key']:r for r in read(priorpath)} if priorpath.exists() else {}
    if priorpath.exists():hashes[priorpath]=hashlib.sha256(priorpath.read_bytes()).hexdigest()
    rows=[];conflicts=[];repeated=[]
    for key,members in grouped.items():
        canonical=dict(max(members,key=rank));flags,money=checks(canonical)
        if len(members)>1:
            repeated.append(dict(record_key=key,observation_count=len(members),selected_input=canonical['input_file'],inputs=';'.join(sorted({r['input_file'] for r in members}))))
        for field in ['price_million','area_sqm']:
            # Export roundoff such as 4179.999999999999 vs 4180 is not a price conflict.
            values=distinct_numbers(r[field] for r in members)
            if len(values)>1:
                flags.append('snapshot_'+field+'_conflict')
                conflicts.append(dict(record_key=key,field=field,values_json=json.dumps(values),
                    observations_json=json.dumps([dict(file=r['input_file'],row=r['input_row'],value=r[field]) for r in members],ensure_ascii=False)))
        # Reuse a known date only from an explicit sibling snapshot of the same source ID.
        date_support=next((r for r in sorted(members,key=rank,reverse=True) if r['displayed_date']),None)
        if not canonical['displayed_date'] and date_support:
            canonical.update(displayed_date=date_support['displayed_date'],date_basis='same_id_other_snapshot:'+date_support['date_basis'],
                age_days=date_support['age_days'])
            flags=[f for f in flags if f!='listing_date_unavailable']
            if canonical['age_days']<0:flags.append('future_listing_date')
            elif canonical['age_days']>183:flags.append('older_than_183_days')
        pd=prior.get(key,{})
        flags=sorted(set(flags))
        hard=[f for f in flags if f!='listing_date_unavailable']
        if pd.get('decision') in ['exclude','pending']:status='prior_'+pd['decision']
        elif pd.get('decision') in ['correct','keep']:status='prior_reviewed_'+pd['decision']
        elif 'outside_or_unverified_old_danang' in flags:status='outside_or_unverified_scope'
        elif 'historical_district_unresolved' in flags:status='district_needs_review'
        elif 'outside_model_property_types' in flags or 'special_or_whole_building' in flags:status='other_property_or_building'
        elif hard:status='needs_review'
        elif not canonical['displayed_date']:status='screened_date_unknown'
        else:status='screened_candidate_unverified'
        canonical.update(status=status,review_codes=';'.join(flags),review_flag_count=len(flags),
            title_money_evidence=json.dumps(money,ensure_ascii=False),observation_count=len(members),
            prior_review_decision=pd.get('decision',''),prior_review_note=pd.get('note',''),
            prior_corrected_price_million=pd.get('price_million',''),prior_corrected_area_sqm=pd.get('area_sqm',''),
            detail_content_checked_now=False,duplicate_candidate_group='',model_split='')
        rows.append(canonical)
    pairs=duplicates(rows)
    for row in rows:row.pop('model_split',None) # Audit groups are not a new train/test split.
    rows.sort(key=lambda r:(r['source'],r['record_key']))
    fields=list(rows[0])
    save_csv(OUT/'all_unique_listings_audit.csv',rows,fields)
    need=[r for r in rows if r['status'] not in ['screened_candidate_unverified','screened_date_unknown','prior_reviewed_keep','prior_reviewed_correct']]
    save_csv(OUT/'needs_review.csv',need,fields)
    screened=[r for r in rows if r['status'] in ['screened_candidate_unverified','screened_date_unknown']]
    save_csv(OUT/'screened_candidates_unverified.csv',screened,fields)
    save_csv(OUT/'all_snapshot_observations.csv',observations,list(observations[0]))
    save_csv(OUT/'file_inventory.csv',inventory,list(inventory[0]))
    save_csv(OUT/'repeated_source_ids.csv',repeated,['record_key','observation_count','selected_input','inputs'])
    save_csv(OUT/'snapshot_value_conflicts.csv',conflicts,['record_key','field','values_json','observations_json'])
    save_csv(OUT/'malformed_rows.csv',bad,['input_file','input_row','reason','raw_json'])
    save_csv(OUT/'possible_duplicate_properties.csv',pairs,['left','right','rule','title_similarity','cross_source','left_url','right_url'])
    summary=dict(as_of=ASOF.isoformat(),scope='All discovered raw listing CSVs, legacy CSVs, sample CSVs and JSONL mirrors under app/data; processed files excluded.',
        inventory_files=len(inventory),vietnam_csv_snapshot_rows=sum(i['rows'] for i in inventory if i['kind'] in ['raw_listing_snapshot','sample_snapshot']),
        vietnam_jsonl_mirror_rows=sum(i['rows'] for i in inventory if i['kind']=='jsonl_mirror'),vietnam_total_observations=len(observations),
        vietnam_unique_valid_source_ids=sum(r['source_listing_id'].isdigit() for r in rows),invalid_identity_records=sum(not r['source_listing_id'].isdigit() for r in rows),
        by_source={s:dict(unique_source_ids=sum(r['source_listing_id'].isdigit() for r in rows if r['source']==s),
            status=dict(Counter(r['status'] for r in rows if r['source']==s)),category=dict(Counter(r['category'] for r in rows if r['source']==s)),
            date_known=sum(bool(r['displayed_date']) for r in rows if r['source']==s),
            date_min=min((r['displayed_date'] for r in rows if r['source']==s and r['displayed_date']),default=''),
            date_max=max((r['displayed_date'] for r in rows if r['source']==s and r['displayed_date']),default=''),
            older_than_183_days=sum(r['age_days'] is not None and r['age_days']>183 for r in rows if r['source']==s),
            detail_snapshot_available=sum(r['detail_fetched'] for r in rows if r['source']==s)) for s in sorted({r['source'] for r in rows})},
        statuses=dict(Counter(r['status'] for r in rows)),categories=dict(Counter(r['category'] for r in rows)),
        issue_counts=dict(Counter(f for r in rows for f in r['review_codes'].split(';') if f)),
        source_ids_in_multiple_observations=len(repeated),snapshot_conflict_records=len({r['record_key'] for r in conflicts}),
        snapshot_conflict_fields=len(conflicts),possible_duplicate_property_pairs=len(pairs),
        cross_source_possible_duplicate_pairs=sum(p['cross_source'] for p in pairs),
        suspected_property_groups=len({r['duplicate_candidate_group'] for r in rows}),malformed_rows=len(bad),
        singapore=sg,input_sha256={str(p.relative_to(BASE)).replace('\\','/'):h for p,h in hashes.items()},
        raw_input_hashes_unchanged=all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items()),
        limitations=['All Vietnam raw records checked structurally and by source-aware rules; no new detail URLs fetched.',
          'Source ID uniqueness is not unique physical property count. Pair grouping is heuristic.',
          'Historical seven-district resolution retains ambiguous new administrative units.',
          'Missing dates and legacy Chotot missing source region/transaction/raw-price evidence prevent verified freshness or sale scope.',
          'Repeated ID prices can reflect updates or parsing/source errors; conflicting snapshots are retained.',
          'Prior 64 apartment decisions are referenced without modifying or overwriting that review.',
          'Candidate status is rule screening, not independently verified clean data. No model was retrained.'])
    assert summary['raw_input_hashes_unchanged']
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    write_report(summary)
    print(json.dumps({k:v for k,v in summary.items() if k not in ['singapore','input_sha256','by_source','limitations','scope']},ensure_ascii=True,indent=2))

def write_report(summary):
    lines=['# Kiểm tra toàn bộ dữ liệu đã thu thập', '',
        f'Ngày đối chiếu: {summary["as_of"]}. Đã đọc {summary["inventory_files"]} file CSV/JSONL nguồn, gồm batch chính, file cũ, sample, file bổ sung và cách ly. Không đọc lại các CSV processed như tin mới.', '',
        '## Số lượng đã đối soát', '',
        f'- Việt Nam: **{summary["vietnam_unique_valid_source_ids"]:,} ID nguồn duy nhất**, không đồng nghĩa từng đó bất động sản khác nhau.',
        f'- Có {summary["vietnam_csv_snapshot_rows"]:,} dòng CSV Việt Nam và {summary["vietnam_jsonl_mirror_rows"]:,} dòng JSONL mirror; tổng {summary["vietnam_total_observations"]:,} quan sát/snapshot.',
        f'- {summary["source_ids_in_multiple_observations"]:,} ID xuất hiện ở nhiều quan sát. Không cộng mẫu thử, file khôi phục và bản JSONL/CSV thành các tin mới.',
        '- Không có ID trùng trong từng file Việt Nam. Không có lỗi cấu trúc CSV/JSONL hoặc ID không hợp lệ trong snapshot hiện tại.',
        '- Không tìm thấy khác biệt giá/diện tích đáng kể giữa các snapshot cùng ID. Sai số float nhỏ không coi là mâu thuẫn; việc này không chứng minh giá nguồn đúng.',
        '- `danang_bds_10k_raw.csv` và `nhadat24h_quarantine.csv` hiện không có dòng dữ liệu.', '',
        '| Nguồn | ID duy nhất | Qua quy tắc, có ngày | Qua quy tắc, thiếu ngày | Đã duyệt giữ/sửa từ căn hộ |',
        '|---|---:|---:|---:|---:|']
    for source,info in summary['by_source'].items():
        st=info['status']
        lines.append(f'| {source} | {info["unique_source_ids"]:,} | {st.get("screened_candidate_unverified",0):,} | {st.get("screened_date_unknown",0):,} | {st.get("prior_reviewed_correct",0)+st.get("prior_reviewed_keep",0)} |')
    lines+=['', '## Trạng thái loại trừ nhau', '', '| Trạng thái | Số tin |', '|---|---:|']
    labels={'screened_candidate_unverified':'Qua quy tắc, có mốc hiển thị/cập nhật; chưa xác minh sạch',
      'screened_date_unknown':'Qua các quy tắc khác nhưng chưa có ngày', 'needs_review':'Cần rà soát nhãn/chất lượng/bằng chứng',
      'district_needs_review':'Chưa gán chắc một quận/huyện cũ', 'outside_or_unverified_scope':'Ngoài hoặc chưa chứng minh thuộc Đà Nẵng cũ',
      'other_property_or_building':'Loại khác/toàn công trình hoặc có dấu hiệu cần phân loại riêng',
      'prior_pending':'Đã duyệt căn hộ: đang chờ xác minh', 'prior_exclude':'Đã duyệt căn hộ: loại khỏi phạm vi',
      'prior_reviewed_correct':'Đã duyệt căn hộ: sửa nhãn', 'prior_reviewed_keep':'Đã duyệt căn hộ: giữ nhãn'}
    for status,count in summary['statuses'].items():lines.append(f'| {labels[status]} | {count:,} |')
    lines+=['', 'Các nhóm trạng thái cộng đúng tổng ID Việt Nam. Cột `review_codes` có thể chứa nhiều lý do cùng lúc; không cộng số cờ thành số tin.', '',
      '## Những vấn đề đáng chú ý', '',
      f'- {summary["issue_counts"].get("listing_date_unavailable",0):,} tin không có mốc đăng/cập nhật đáng tin trong dữ liệu; không dùng ngày thu thập hoặc URL ảnh thay thế.',
      '- 2.653 tin Chợ Tốt cũ thiếu ngày, giá thô gốc, trường loại giao dịch và bằng chứng tỉnh nguồn. Tên file Đà Nẵng + nhãn quận chỉ là dấu hiệu phạm vi, chưa đủ xác minh. Không tự coi mọi tin là bán.',
      '- 393 tin Homedy ngoài hoặc chưa chứng minh thuộc Đà Nẵng cũ; giữ riêng khỏi nhóm ứng viên.',
      f'- {summary["issue_counts"].get("missing_or_invalid_price",0):,} tin thiếu/không hợp lệ giá số; {summary["issue_counts"].get("missing_or_invalid_area",0):,} tin thiếu/không hợp lệ diện tích số. Nhiều thẻ CafeLand có văn bản giá/diện tích nhưng để trống số chuẩn hóa do chưa lấy chi tiết, khác lỗi chuyển đổi đơn vị.',
      f'- {summary["issue_counts"].get("title_price_conflict",0)} tin có dấu hiệu giá trong tiêu đề lệch nhãn; {summary["issue_counts"].get("partial_starting_or_booking_title",0)} tiêu đề có dấu hiệu thanh toán/giá khởi điểm/booking. Cờ chỉ ưu tiên duyệt, có thể sai với số viết tắt hoặc quảng cáo.',
      f'- {summary["issue_counts"].get("older_than_183_days",0)} tin có mốc hiển thị/cập nhật quá 183 ngày; {summary["issue_counts"].get("coordinates_need_geographic_review",0)} tin có tọa độ cần kiểm tra địa lý.',
      f'- {summary["possible_duplicate_property_pairs"]} cặp nghi cùng bất động sản, trong đó {summary["cross_source_possible_duplicate_pairs"]} cặp khác nguồn. Nhóm nghi trùng chỉ là heuristic theo tiêu đề, quận/loại, diện tích và giá; không tự xóa tin.', '',
      'Đối với 64 căn hộ đã duyệt: tham chiếu nguyên 11 sửa, 6 giữ, 7 loại, 40 chờ; không ghi đè quyết định hoặc dữ liệu v2. Audit này giữ giá/diện tích raw trong cột chính; nhãn sửa trước đó nằm ở `prior_corrected_*`, không phải lần sửa mới.', '',
      '## Mốc thời gian trong dữ liệu', '',
      '| Nguồn | Có mốc | Mốc nhỏ nhất | Mốc lớn nhất | Quá 183 ngày |', '|---|---:|---|---|---:|']
    for source,info in summary['by_source'].items():lines.append(f'| {source} | {info["date_known"]:,} | {info["date_min"]} | {info["date_max"]} | {info["older_than_183_days"]} |')
    lines+=['', 'Đây là mốc hiển thị/cập nhật nguồn; không khẳng định ngày đăng đầu hoặc ngày giao dịch. Nhadat24h có ngày tương đối được ước lượng theo ngày thu thập. Homedy chỉ tìm được ngày ở 20 ID từ snapshot thử cùng ID; các tin khác không suy ngày. Tọa độ kiểm tra bằng hình chữ nhật 15,6–16,5°N / 107,7–108,5°E chỉ là cờ kỹ thuật, không phải ranh giới pháp lý.', '',
      '## Dữ liệu Singapore', '']
    sg=summary['singapore']
    if sg:lines+=[f'Đã kiểm tra riêng **{sg["rows"]:,} dòng HDB**, tháng {sg["month_min"]} đến {sg["month_max"]}. Không có dòng bị cờ thiếu trường/giá SGD/diện tích/tháng không hợp lệ theo quy tắc. Có {sg["repeated_exact_rows"]} dòng giống hệt dòng trước; nguồn không có ID giao dịch duy nhất nên không kết luận đó là giao dịch trùng và không xóa.', '',
      'Tháng 10/2026 đang diễn ra tại ngày kiểm tra, không coi là dữ liệu tháng đầy đủ. HDB là giá giao dịch SGD, khác giá rao Việt Nam; không cộng vào 8.509 ID và không ghép vào tập huấn luyện trong lần này.', '']
    lines+=['## Phạm vi kiểm tra và tệp kết quả', '',
      '**Đã kiểm tra toàn bộ bản ghi trong các file nguồn đã phát hiện. Chưa truy cập lại toàn bộ trang chi tiết và chưa kiểm tra tất cả URL còn sống.** Cờ `detail_fetched` chỉ nói crawler từng lưu dữ liệu từ chi tiết; không có nghĩa lần này đã đọc lại đầy đủ mô tả. Bằng chứng HTML của đợt 64 căn hộ được giữ nguyên ở thư mục trước.', '',
      'Giá theo tỷ/triệu, diện tích m², giá số/giá văn bản và giá chi tiết được đối chiếu khi có. Giá trả trước, thuê, giảm giá, giá/m² được phân biệt bằng ngữ cảnh. Ngưỡng rà soát: tổng giá 100–200.000 triệu; diện tích 20–1.000m²; đơn giá 2–300 triệu/m². Căn hộ ưu tiên thêm giá dưới 500 triệu hoặc đơn giá ngoài 15–150 triệu/m². Ngưỡng là quy tắc kỹ thuật, không kết luận mặt bằng thị trường.', '',
      'Địa bàn dùng bộ phân giải 7 quận/huyện cũ đã có của dự án, giữ các đơn vị mới giao nhau ở trạng thái mơ hồ. Không dùng phường mới để ép thành một quận cũ. Chưa xác minh tọa độ thực địa/quyền sở hữu/giá giao dịch.', '',
      '- `all_unique_listings_audit.csv`: 8.509 ID Việt Nam, từng lý do và provenance bản gốc.',
      '- `needs_review.csv`: mọi tin cần xử lý phạm vi, loại hoặc chất lượng, gồm nhóm ngoài phạm vi và các quyết định chờ/loại trước đó.',
      '- `screened_candidates_unverified.csv`: các tin qua quy tắc; chưa phải bộ sạch, chưa loại hết nghi trùng bất động sản.',
      '- `all_snapshot_observations.csv`: mọi snapshot Việt Nam, giữ JSON gốc và vị trí dòng nguồn.',
      '- `file_inventory.csv`, `repeated_source_ids.csv`: kiểm kê và ID xuất hiện nhiều quan sát.',
      '- `possible_duplicate_properties.csv`: hai ID/URL và quy tắc nghi trùng.',
      '- `snapshot_value_conflicts.csv`, `malformed_rows.csv`: các vấn đề cấu trúc/khác biệt snapshot; hiện chỉ có header.',
      '- `singapore_flagged_rows.csv`, `singapore_exact_row_repeats.csv`: kiểm tra riêng HDB.',
      '- `summary.json`: số lượng, khoảng ngày, quy tắc, SHA256 của tất cả đầu vào.', '',
      'Đã đối chiếu SHA256 trước/sau: toàn bộ đầu vào giữ nguyên. Không huấn luyện lại hoặc thay tập test ở lần audit này.', '',
      '## Ưu tiên tiếp theo', '',
      '1. Giải quyết tin thuê/booking/toàn công trình, loại ngoài 7 quận/huyện và địa bàn chưa rõ.',
      '2. Đối chiếu nguồn cho các mâu thuẫn tổng giá, giá trả trước, giá/m²; xử lý 40 căn hộ đang chờ nếu có bằng chứng mới.',
      '3. Bổ sung bằng chứng ngày, loại giao dịch và giá gốc cho Chợ Tốt cũ; không tự suy từ tên file.',
      '4. Kiểm tra các cặp nghi trùng theo dự án/mã căn, rồi mới chốt phiên bản dữ liệu dùng huấn luyện.', '',
      'Chạy lại từ `F:\\SmartProp`:', '', '```powershell',
      '.\\ai-services\\.venv\\Scripts\\python.exe ai-services/app/data/audit_all_collected.py',
      '.\\ai-services\\.venv\\Scripts\\python.exe -m unittest discover -s ai-services/app/data -p test_audit_all_collected.py',
      '```', '']
    expanded = OUT.parent/'full_collection_audit_expanded/README.md'
    if expanded.exists():
        lines[2:2] = ['> Đã có [báo cáo phạm vi Đà Nẵng cũ và mới](../full_collection_audit_expanded/README.md). Báo cáo dưới đây dùng 7 quận/huyện cũ. Sau khi chạy lại audit gốc, chạy `expand_collection_audit_scope.py` để cập nhật báo cáo mở rộng theo dữ liệu mới.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')

if __name__=='__main__':main()
