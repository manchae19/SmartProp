"""Conservative CSV audit. Category suggestions are heuristics, not verified labels."""
import argparse
import csv
import hashlib
import json
import math
import re
import unicodedata
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

DISTRICTS={'quan hai chau','quan thanh khe','quan son tra','quan ngu hanh son',
           'quan lien chieu','quan cam le','huyen hoa vang'}

def norm(s):
    s=' '.join((s or '').lower().split())
    return ''.join(c for c in unicodedata.normalize('NFD',s) if unicodedata.category(c)!='Mn').replace('đ','d')

def number(s):
    try:
        v=float(s)
        return v if math.isfinite(v) else None
    except (ValueError,TypeError): return None

def classify(r):
    s=norm(r['source_category']); t=norm(r['title'])
    if re.search(r'\b(tang nha|dat va nha|nha va dat)\b',t):
        return 'Chưa xác định','mixed_house_land',True
    if s in {'condotel','nhà trọ, phòng trọ'} or s=='nha tro, phong tro':
        return 'Khác','special_property_source',False
    if s in {'dat nong nghiep, dat vuon','dat dich vu, den bu','nha hang, khach san, resort',
             'shophouse','nha xuong, mat bang, kho bai'}:
        return 'Khác','special_property_source',False
    if re.search(r'\b(toa can ho|toa chdv|toa nha|ban khach san|ban nha tro)\b',t):
        return 'Khác','whole_building_or_commercial_title',False
    land=bool(re.search(r'\b(ban dat|lo dat|cap dat|dat nen|dat mat tien|dat tho cu)\b',t)
              or re.match(r'^\W*dat\b',t))
    if land:
        if s=='can ho chung cu': return 'Chưa xác định','source_title_conflict',True
        return 'Đất nền','explicit_land_title',False
    if s=='can ho chung cu': return 'Căn hộ chung cư','source_apartment',False
    if s=='dat nen du an': return 'Đất nền','source_project_land',False
    if s in {'nha mat pho','nha trong ngo','nha biet thu, lien ke'}:
        if re.search(r'\b(dat|\d+ lo)\b',t) and not re.search(r'\b(ban nha|nha \d+\s*tang|ban biet thu|nha mat dat|nha to dat)\b',t):
            return 'Chưa xác định','possible_land_in_house_source',True
        return 'Nhà ở','source_house',False
    if s=='nha dat tho cu':
        if re.search(r'\b(ban nha|nha \d+\s*tang|ban biet thu)\b',t) and not re.search(r'\bdat\b',t):
            return 'Nhà ở','explicit_house_title',False
        return 'Chưa xác định','ambiguous_source_and_title',True
    return 'Chưa xác định','unsupported_source_category',True

def displayed_date(r):
    raw=r.get('posted_at_raw',''); collected=datetime.fromisoformat(r['collected_at'])
    if collected.tzinfo is None: raise ValueError('collected_at must include timezone')
    base=collected.astimezone(timezone(timedelta(hours=7))).date()
    m=re.fullmatch(r'(\d{1,2})/(\d{1,2})/(\d{4}),\s*lúc:\s*\d+ giờ \d+ phút',raw)
    if m:
        try: d=datetime(int(m[3]),int(m[2]),int(m[1])).date()
        except ValueError: return '', 'unparsed', '', 'unknown'
        precision='displayed_calendar_date'
    else:
        m=re.fullmatch(r'(\d+) ngay truoc\.?',norm(raw))
        if not m: return '', 'unparsed', '', 'unknown'
        d=base-timedelta(days=int(m[1])); precision='approximate_relative_day'
    age=(base-d).days
    band='future' if age<0 else '0_to_183_days' if age<=183 else '184_to_366_days' if age<=366 else 'over_366_days'
    return d.isoformat(),precision,age,band

def main(input_path,output_dir):
    with input_path.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f); raw_fields=reader.fieldnames; rows=list(reader)
    original_hash=hashlib.sha256(input_path.read_bytes()).hexdigest()
    extra=['category_suggested','category_rule','category_review_audit','price_million_reparsed',
           'price_per_sqm_million','displayed_date','displayed_date_precision','displayed_age_days',
           'displayed_age_band','duplicate_candidate_group','duplicate_candidate_count',
           'review_reasons','screening_status']
    idcounts=Counter((r['source'],r['source_listing_id']) for r in rows)
    group_rows=defaultdict(list)
    for r in rows:
        reasons=[]
        if not r['source_listing_id'] or idcounts[r['source'],r['source_listing_id']]>1: reasons.append('duplicate_or_missing_source_id')
        if norm(r['district']) not in DISTRICTS or norm(r['district']) not in norm(r['address_raw']): reasons.append('location_conflict')
        if r['source']!='nhadat24h' or r['transaction_type']!='Bán': reasons.append('source_or_transaction_review')
        cat,rule,category_review=classify(r)
        r.update(category_suggested=cat,category_rule=rule,category_review_audit=category_review)
        if category_review: reasons.append('category_ambiguous')
        m=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*(ty|trieu)',norm(r['price_raw']))
        price=float(m[1].replace(',','.'))*(1000 if m[2]=='ty' else 1) if m else None
        area=number(r['area_sqm']); source_price=number(r['price_million'])
        ratio=price/area if price is not None and area is not None and area>0 else None
        if price is None: reasons.append('price_unavailable')
        elif price<100 or (ratio is not None and not 2<=ratio<=300): reasons.append('price_threshold_review')
        if price is not None and (source_price is None or abs(price-source_price)>0.01): reasons.append('price_parse_mismatch')
        if area is None or not 20<=area<=1000: reasons.append('area_threshold_review')
        ma=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m(?:2|²)',norm(r['area_raw']))
        if not ma or area is None or abs(float(ma[1].replace(',','.'))-area)>0.01: reasons.append('area_parse_mismatch')
        d,precision,age,band=displayed_date(r)
        r.update(price_million_reparsed=price if price is not None else '',
                 price_per_sqm_million=ratio if ratio is not None else '',displayed_date=d,
                 displayed_date_precision=precision,displayed_age_days=age,displayed_age_band=band)
        if band in {'unknown','future','over_366_days'}: reasons.append('date_review')
        r['_reasons']=reasons
        if norm(r['title']) and price is not None and area is not None:
            key=(norm(r['title']),norm(r['district']),norm(r['ward']),round(area,4),round(price,4))
            group_rows[key].append(r)
    duplicate_groups=0
    for key,members in group_rows.items():
        if len(members)>1:
            duplicate_groups+=1
            gid='possible:'+hashlib.sha256(json.dumps(key,ensure_ascii=False).encode()).hexdigest()[:16]
            for r in members:
                r['duplicate_candidate_group']=gid; r['duplicate_candidate_count']=len(members)
                r['_reasons'].append('possible_duplicate_title_location_price_area')
    candidates=[]; review=[]; other=[]
    for r in rows:
        r.setdefault('duplicate_candidate_group',''); r.setdefault('duplicate_candidate_count',1)
        reasons=r.pop('_reasons'); r['review_reasons']=';'.join(reasons)
        status='needs_review' if reasons else 'other_property' if r['category_suggested']=='Khác' else 'candidate'
        r['screening_status']=status
        {'candidate':candidates,'needs_review':review,'other_property':other}[status].append(r)
    output_dir.mkdir(parents=True,exist_ok=True)
    fields=raw_fields+extra
    def save(name,data):
        with (output_dir/name).open('w',encoding='utf-8-sig',newline='') as f:
            w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(data)
    save('nhadat24h_audit.csv',rows); save('nhadat24h_candidates.csv',candidates)
    save('nhadat24h_needs_review.csv',review); save('nhadat24h_other_properties.csv',other)
    for name,category in [('houses','Nhà ở'),('apartments','Căn hộ chung cư'),('land','Đất nền')]:
        save('nhadat24h_'+name+'_candidates.csv',[r for r in candidates if r['category_suggested']==category])
    save('nhadat24h_recent_candidates.csv',[r for r in candidates if r['displayed_age_band']=='0_to_183_days'])
    summary={'records':len(rows),'source_sha256':original_hash,'unique_source_ids':len(idcounts),
             'source_missing_price':sum(not r['price_million'] for r in rows),
             'source_price_flags':sum(r['price_needs_review']=='True' for r in rows),
             'source_category_flags':sum(r['category_needs_review']=='True' for r in rows),
             'candidate_records':len(candidates),'needs_review_records':len(review),'other_properties':len(other),
             'candidate_categories':dict(Counter(r['category_suggested'] for r in candidates)),
             'suggested_categories':dict(Counter(r['category_suggested'] for r in rows)),
             'review_reasons':dict(Counter(reason for r in review for reason in r['review_reasons'].split(';'))),
             'age_bands':dict(Counter(r['displayed_age_band'] for r in rows)),
             'date_precision':dict(Counter(r['displayed_date_precision'] for r in rows)),
             'displayed_date_min':min((r['displayed_date'] for r in rows if r['displayed_date']),default=''),
             'displayed_date_max':max((r['displayed_date'] for r in rows if r['displayed_date']),default=''),
             'recent_candidate_records':sum(r['displayed_age_band']=='0_to_183_days' for r in candidates),
             'possible_duplicate_groups':duplicate_groups,
             'district_counts':dict(Counter(r['district'] for r in rows))}
    (output_dir/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    assert len(candidates)+len(review)+len(other)==len(rows)
    assert hashlib.sha256(input_path.read_bytes()).hexdigest()==original_hash
    print(json.dumps(summary,ensure_ascii=False))

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output-dir',type=Path,required=True); a=p.parse_args(); main(a.input,a.output_dir)
