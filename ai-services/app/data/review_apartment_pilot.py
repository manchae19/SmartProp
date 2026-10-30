"""Offline source review and leakage quarantine for the bounded apartment pilot."""
import csv
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from difflib import SequenceMatcher
import hashlib
import json
from pathlib import Path
import re

import collect_apartment_pilot as collector
from build_training_v1 import group_records
from review_apartment_labels import AREA, money_mentions
from remaining_diversity_rules import shorthand
from smartprop_geography import norm, resolve, DISTRICTS

BASE=collector.BASE
RAW=collector.OUT
OUT=BASE/'processed/apartment_pilot_review'
EVIDENCE=BASE/'processed/collection_source_review/parsed_evidence.json'
CATALOG=BASE.parent/'core/location_catalog_v6.json'
PROTOCOL=BASE/'APARTMENT_PILOT_PROTOCOL.md'
PREPARED=BASE/'processed/training_next_preparation/runs/4fdb8ef79db89b16'
MIN_GROUPS=20
FOOTER=re.compile(r'\b(?:quy khach|lien he|hotline|zalo|lh\s*:|tu van bat dong san|nhan ky gui)\b')


def read_csv(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:return list(csv.DictReader(stream))


def subject(text):
    text=norm(text)
    # A source category/address echo is metadata, not independent seller proof.
    if 'thong tin chi tiet' in text:text=text.split('thong tin chi tiet',1)[1]
    return FOOTER.split(re.sub(r'^thong tin mo ta\s*','',text))[0].strip()


def location(row,catalog):
    district,basis,_=resolve(row['address_raw'],source='cafeland')
    if district in catalog['legacy']:return district,basis
    parts=row['source_location_parts']
    key='new_unit:'+re.sub(r'^(?:phuong|xa)\s+','',norm(parts[0])) if parts else ''
    if key in catalog['expanded']:return key,'reviewed_catalog_key_without_old_district_inference'
    return '',basis


def quality(row,catalog):
    flags=set(row['source_evidence_flags']);resolutions=[]
    p,a=row['price_million'],row['area_sqm']
    key,basis=location(row,catalog)
    if not key:flags.add('location_not_in_reviewed_catalog')
    if row['transaction_type']!='sale' or row['currency']!='VND':flags.add('sale_currency_unverified')
    if row['source_category']!='ban-can-ho-chung-cu':flags.add('not_source_apartment_sale')
    if p is not None and p<500:flags.add('low_total_price_review')
    if a is not None and not 25<=a<=200:flags.add('area_band_review')
    if p is not None and a is not None and a>0 and not 15<=p/a<=150:flags.add('unit_price_band_review')
    local_date=datetime.fromisoformat(row['collected_at']).astimezone(timezone(timedelta(hours=7))).date()
    try:
        age=(local_date-datetime.strptime(row['source_published_date'],'%Y-%m-%d').date()).days
        if not 0<=age<=183:flags.add('source_date_outside_pilot_window')
    except ValueError:age=None;flags.add('source_date_unavailable')
    title,body=norm(row['title']),subject(row['description'])
    text=title+' '+body
    if len(body.split())<15:flags.add('description_insufficient')
    if not re.search(r'\b(?:can ho|chung cu|studio)\b',body):flags.add('apartment_not_supported_by_seller_description')
    if re.search(r'\b(?:booking|dat coc|tra truoc|chi tu|gia tu|nhan giu cho|thanh toan|tts\s*\d)\b',text):flags.add('partial_starting_or_booking_price')
    if re.search(r'\b(?:gio hang|quy can|bang gia|nhieu can|cac can|dien tich da dang|[2-9]\d* can (?:ho|nha))\b',text):flags.add('multiple_units_or_inventory')
    if re.search(r'\b(?:condotel|can ho dich vu|officetel|shophouse)\b',text):flags.add('nonstandard_apartment_review')
    if re.search(r'\b(?:toa (?:nha )?can ho|toa nha|ban khach san|day tro)\b',title):flags.add('whole_building_title')
    if re.search(r'\b(?:ban toa (?:nha |can ho)|dien tich dat|\d+\s*(?:can )?phong (?:khep|kep) kin|day (?:nha )?tro)\b',body):flags.add('whole_building_or_land_area_in_seller_description')
    if re.search(r'\b(?:dang thi cong|dang xay|du kien ban giao|chuan bi ra mat|sap mo ban)\b',body):flags.add('construction_or_future_offer_review')
    if re.match(r'^(?:can\s+)?cho thue\b',title):flags.add('rental_title')
    if re.search(r'\b(?:tp\.?|thanh pho|tinh)\s+(?:hue|ha noi|ho chi minh|nha trang|quy nhon|quang ngai|binh dinh)\b',text):flags.add('content_outside_da_nang_requires_review')
    if re.search(r'\d+[.,]x|\d+\s*(?:ty|ti)\s*\d*x|\d+\s*trieu\s*x',text):flags.add('masked_price_requires_review')
    rooms={int(m[1]) for m in re.finditer(r'(?<![\w.,])(\d{1,2})\s*(?:pn\b|phong ngu\b)',text)}
    if row.get('rooms'):rooms.add(int(row['rooms']))
    if len(rooms)>1:flags.add('bedroom_claims_conflict')
    body_price_proof=body_area_proof=False
    for label,value in [('title',title),('description',body)]:
        checked,fix=shorthand(value,p) if p is not None else (value,[])
        resolutions.extend(fix)
        if p is not None:
            totals=[m['amount_million'] for m in money_mentions(checked) if m['kind']=='total_candidate']
            if any(abs(v-p)/max(v,p)>.01 for v in totals):flags.add(label+'_total_price_conflict')
            if label=='description':body_price_proof=any(abs(v-p)/max(v,p)<=.01 for v in totals)
        if a is not None and a>0:
            areas=[float(m[1].replace(',','.')) for m in AREA.finditer(value)]
            if any(abs(v-a)/max(v,a)>.01 for v in areas):flags.add(label+'_area_conflict')
            if label=='description':body_area_proof=any(abs(v-a)/max(v,a)<=.01 for v in areas)
    if not body_price_proof or not body_area_proof:flags.add('single_unit_price_area_not_corroborated_in_seller_description')
    # A directly stated historical district must agree with the source locality.
    for district in DISTRICTS:
        prefix='huyen' if district=='Hòa Vang' else 'quan'
        if re.search(r'\b'+prefix+' '+norm(district)+r'\b',body):
            if key in catalog['legacy'] and key!=district:flags.add('source_seller_historical_district_conflict')
    return dict(review_codes=sorted(flags),location_feature=key,location_basis=basis,
                source_age_days=age,resolutions=resolutions)


def title_key(text):return re.sub(r'\W+',' ',norm(text)).strip()


def shingles(text):
    words=subject(text).split()
    if len(words)<50 or len(set(words))<30:return set()
    return {' '.join(words[i:i+5]) for i in range(len(words)-4)}


def extra_pairs(new,history,evidence):
    """Conservative candidate links; no assumption that one ID is one property."""
    pairs=[];seen=set()
    def link(a,b,rule,sim):
        pair=tuple(sorted((a,b)))
        if a==b or (pair,rule) in seen:return
        seen.add((pair,rule));pairs.append(dict(left=a,right=b,rule=rule,title_similarity=sim))
    old_groups=defaultdict(list)
    for row in history:
        if row.get('pipeline_group'):old_groups[row['pipeline_group']].append(row['record_key'])
    for members in old_groups.values():
        for key in members[1:]:link(members[0],key,'preserve_historical_group',1)
    allrows=history+new
    titles={r['record_key']:title_key(r['title']) for r in allrows}
    tokens={k:set(v.split()) for k,v in titles.items()}
    for i,a in enumerate(new):
        ak=a['record_key'];at=tokens[ak]
        for b in history+new[:i]:
            bk=b['record_key'];bt=tokens[bk]
            if len(at&bt)<8 or len(at&bt)/max(1,len(at|bt))<.75:continue
            try:aa,ba=float(a['area_sqm']),float(b['area_sqm'])
            except (TypeError,ValueError):continue
            if min(aa,ba)<=0 or abs(aa-ba)/max(aa,ba)>.02:continue
            sim=SequenceMatcher(None,titles[ak],titles[bk],autojunk=False).ratio()
            if sim>=.90:link(ak,bk,'similar_title_area_2pct_regardless_of_price',sim)
    # Index only new text: bounded memory even when the historic archive grows.
    new_sets={r['record_key']:shingles(r['description']) for r in new}
    inverted=defaultdict(set)
    for key,values in new_sets.items():
        for value in values:inverted[value].add(key)
    bodies={k:v.get('asset_description',v.get('description','')) for k,v in evidence.items() if v.get('identity_verified')}
    bodies.update({r['record_key']:r['description'] for r in new})
    for key,body in bodies.items():
        values=shingles(body)
        counts=Counter(candidate for value in values for candidate in inverted.get(value,()))
        for candidate,overlap in counts.items():
            other=new_sets[candidate]
            if key==candidate or overlap<25:continue
            containment=overlap/min(len(values),len(other))
            similarity=overlap/len(values|other)
            if containment>=.8 and similarity>=.5:link(key,candidate,'long_seller_prose_near_duplicate_or_template',similarity)
    return pairs


def decide(rows,history,evidence,catalog):
    results={r['record_key']:dict(r,**quality(r,catalog)) for r in rows}
    membership,pairs=group_records([dict(r) for r in history+rows],extra_pairs(rows,history,evidence))
    historical_groups={membership[r['record_key']] for r in history}
    groups=defaultdict(list)
    for key,row in results.items():groups[membership[key]].append(row)
    for gid,members in groups.items():
        issues=set()
        if gid in historical_groups:issues.add('linked_to_historical_collection')
        if any(r['review_codes'] for r in members):issues.add('group_contains_unresolved_source_evidence')
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            values=[float(r[field]) for r in members if r[field] is not None]
            if values and max(values)>0 and (max(values)-min(values))/max(values)>tolerance:issues.add('group_'+field+'_conflict')
        if len({r['location_feature'] for r in members if r['location_feature']})>1:issues.add('group_location_conflict')
        rep=min(r['record_key'] for r in members)
        for row in members:
            row.update(property_candidate_group=gid,representative_key=rep,
                       group_review_codes=sorted(issues),training_allowed=False,
                       cohort_split='quarantine' if issues else 'collection_holdout' if row['record_key']==rep else 'suppressed_duplicate',
                       label_quality='automatically_screened_asking_price_unverified')
    return sorted(results.values(),key=lambda r:r['record_key']),pairs


def replay(raw):
    rows=[json.loads(line) for line in (raw/'records.jsonl').read_text(encoding='utf8').splitlines() if line]
    if len(rows)!=len({r['record_key'] for r in rows}):raise ValueError('Duplicate IDs in pilot')
    for row in rows:
        path=(raw/row['detail_file']).resolve()
        if path!=raw.resolve()/'detail_cache'/(row['source_listing_id']+'.html'):raise ValueError('Unexpected cache path')
        body=path.read_bytes()
        if hashlib.sha256(body).hexdigest()!=row['response_sha256']:raise ValueError('Detail hash changed: '+row['record_key'])
        if collector.parse_detail(body,row,row['collected_at'])!=row:raise ValueError('Cached detail replay changed: '+row['record_key'])
    exported=read_csv(raw/'apartment_records.csv')
    fields=list(exported[0]) if exported else []
    def scalar(value):
        return json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else '' if value is None else str(value)
    if exported!=[{k:scalar(row.get(k)) for k in fields} for row in rows]:raise ValueError('Raw CSV differs from durable JSONL log')
    return rows


def write_csv(path,rows,fields):
    with path.open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        writer.writerows({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()} for row in rows)


def protected_inputs():
    manifest=PREPARED/'manifest.json'
    saved=json.loads(manifest.read_text(encoding='utf8'))
    protected={BASE.parents[2]/name:digest for name,digest in saved['input_sha256'].items()}
    protected.update({PREPARED/name:digest for name,digest in saved['output_sha256'].items()})
    for path,digest in protected.items():
        if collector.sha(path)!=digest:raise ValueError('Protected v6/prepared data changed: '+str(path))
    return [manifest,*protected]


def inputs():
    paths=[RAW/name for name in ['records.jsonl','apartment_records.csv','checkpoint.json','policy.json','latest_run.json','robots.txt']]
    paths += [collector.HISTORY,EVIDENCE,CATALOG,PROTOCOL,Path(__file__),Path(collector.__file__),Path(collector.cafe.__file__)]
    paths += [BASE/name for name in ['build_training_v1.py','audit_all_collected.py','prepare_smartprop_dataset.py',
               'review_apartment_labels.py','remaining_diversity_rules.py','smartprop_geography.py','verify_apartment_pilot.py']]
    paths += protected_inputs()
    return {p.relative_to(BASE.parents[2]).as_posix():collector.sha(p) for p in paths}


def main():
    digests=inputs()
    policy=json.loads((RAW/'policy.json').read_text(encoding='utf8'))
    if policy['history_sha256']!=collector.sha(collector.HISTORY):raise ValueError('Collection history changed')
    rows=replay(RAW);history=read_csv(collector.HISTORY)
    old_keys={r['record_key'] for r in history}
    if old_keys&{r['record_key'] for r in rows}:raise ValueError('Historical IDs in pilot')
    if len(old_keys)!=len(history):raise ValueError('Duplicate historical keys')
    evidence=json.loads(EVIDENCE.read_text(encoding='utf8'))
    evidence={k:v for k,v in evidence.items() if k in old_keys}
    catalog=json.loads(CATALOG.read_text(encoding='utf8'))
    results,pairs=decide(rows,history,evidence,catalog)
    eligible=[r for r in results if r['cohort_split']=='collection_holdout']
    review=[r for r in results if r['cohort_split']=='quarantine']
    duplicates=[r for r in results if r['cohort_split']=='suppressed_duplicate']
    run_id=hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest()[:16]
    run=OUT/'runs'/run_id
    if run.exists():raise ValueError('Immutable run exists; use verifier: '+str(run))
    run.mkdir(parents=True)
    fields=list(dict.fromkeys(key for row in results for key in row)) if results else ['record_key','cohort_split']
    for name,subset in [('all_decisions.csv',results),('collection_holdout.csv',eligible),('needs_review.csv',review),('suppressed_duplicates.csv',duplicates)]:write_csv(run/name,subset,fields)
    lock=dict(protocol_sha256=collector.sha(PROTOCOL),model_predictions_read=False,
              training_allowed=False,minimum_groups=MIN_GROUPS,
              members=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in eligible])
    (run/'cohort_lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),encoding='utf8')
    new_keys={r['record_key'] for r in rows}
    relevant_pairs=[p for p in pairs if p['left'] in new_keys or p['right'] in new_keys]
    (run/'duplicate_links.json').write_text(json.dumps(relevant_pairs,ensure_ascii=False,indent=2),encoding='utf8')
    summary=dict(run_id=run_id,total_raw=len(rows),historical_collection=len(history),unique_new_ids=len(new_keys),
        historical_id_overlap=0,cache_replay_verified=len(rows),source_dates=dict(Counter(r['source_published_date'][:7] for r in rows)),
        source_date_min=min((r['source_published_date'] for r in rows if r['source_published_date']),default=''),
        source_date_max=max((r['source_published_date'] for r in rows if r['source_published_date']),default=''),
        collection_holdout=len(eligible),needs_review=len(review),suppressed_duplicates=len(duplicates),
        linked_to_history=sum('linked_to_historical_collection' in r['group_review_codes'] for r in results),
        rule_counts=dict(Counter(c for r in results for c in r['review_codes'])),
        group_rule_counts=dict(Counter(c for r in results for c in r['group_review_codes'])),
        historical_verified_description_coverage=sum(bool(v.get('identity_verified') and v.get('description')) for v in evidence.values()),
        minimum_groups=MIN_GROUPS,evaluation_gate_passed=len(eligible)>=MIN_GROUPS,
        v7_training_started=False,model_predictions_read=False,production_model_changed=False,old_splits_changed=False,
        input_sha256=digests,
        limitation='Candidate grouping cannot prove distinct physical apartments. Same-source asking-price snapshot is not an independent transaction benchmark. All new eligible groups remain held out.')
    (run/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    document=f'''# Rà soát lô thử căn hộ — {run_id}

Đã thu **{len(rows)} ID mới**, đối chiếu **{len(history):,} tin cũ**; trùng ID: **0**.
Đã kiểm tra checksum và phân tích lại **{len(rows)} trang chi tiết** từ cache, không gọi mạng hoặc mô hình.

| Kết quả | Số tin |
|---|---:|
| Qua quy tắc, khóa riêng để kiểm chứng | {len(eligible)} |
| Cần rà soát/cách ly | {len(review)} |
| Tin phụ nghi trùng trong nhóm đã qua quy tắc | {len(duplicates)} |
| Tổng | {len(rows)} |

**Không có tin mới nào được thêm vào train.** Có {summary['linked_to_history']} tin nghi liên quan nhóm cũ,
đã cách ly cùng các trường hợp nhãn chưa rõ. Đây là các nhóm nghi trùng, không phải xác nhận cùng tài sản.
Ngày nguồn: **{summary['source_date_min']} → {summary['source_date_max']}**; có thể là ngày cập nhật/đăng lại.
Thời điểm thu thập nằm ở cột `collected_at`, không dùng thay ngày đăng.

Mốc cân nhắc kiểm chứng: **{MIN_GROUPS} nhóm**, hiện có **{len(eligible)}**.
Chưa huấn luyện v7, chưa chạy dự đoán trên lô mới. Model/API v6 và các tập cũ giữ nguyên.
Quy trình: `ai-services/app/data/APARTMENT_PILOT_PROTOCOL.md`.

- `all_decisions.csv`: đủ từng tin, lý do, khóa nhóm và đường dẫn cache.
- `needs_review.csv`: xử lý theo bằng chứng, không tự điền diện tích/giá từ tiêu đề.
- `collection_holdout.csv` và `cohort_lock.json`: khóa ứng viên, cấm đưa vào train.
- `duplicate_links.json`: bằng chứng liên kết với dữ liệu cũ hoặc trong lô.
- `summary.json`: số liệu và checksum nguồn/quy tắc.

Bằng chứng mô tả lịch sử có xác minh danh tính phủ **{summary['historical_verified_description_coverage']}/{len(history)}** tin.
Các tin còn lại vẫn được so tiêu đề/diện tích/giá và nhóm cũ, nhưng không có đủ mô tả để loại trừ trùng ẩn.
Không có cờ không có nghĩa nhãn đã được xác minh thực địa. Không phải bộ kiểm chứng giá giao dịch.
Cache HTML và mô tả giữ cục bộ; không đưa dữ liệu người đăng lên GitHub.
'''
    (run/'README.md').write_text(document,encoding='utf8')
    hashes={p.name:collector.sha(p) for p in run.iterdir() if p.is_file()}
    (run/'manifest.json').write_text(json.dumps(hashes,indent=2),encoding='utf8')
    if inputs()!=digests:raise ValueError('Input changed during review; do not use this run')
    collector.atomic(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},ensure_ascii=True,indent=2))


if __name__=='__main__':main()
