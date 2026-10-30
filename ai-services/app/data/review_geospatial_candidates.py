"""Review the fixed 80 coordinate candidates using saved source evidence only.

Claims from titles are NOT verified geography and are not joined to model inputs.
"""
import hashlib
import json
import re
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import geospatial_enrichment as geo

OUT = geo.OUT / 'candidate_review'


def access_claims(title):
    """Narrow Vietnamese claim extraction; do not infer widths from parcel frontage."""
    text = geo.normalized(title)
    # Kiệt as part of a person's street name does not mean an alley.
    masked = re.sub(r'\b(?:vo van kiet|ly thuong kiet)\b', ' street_name ', text)
    alley = bool(re.search(r'\b(?:kiet|hem)\b', masked))
    negated = bool(re.search(r'\b(?:khong|chua)(?:\s+phai)?\s+(?:nha\s+)?(?:trong\s+)?(?:kiet|hem)\b',masked))
    frontage, nearby = False, False
    for match in re.finditer(r'\bmat (?:tien|pho)\b', masked):
        before = masked[max(0,match.start()-30):match.start()]
        if re.search(r'\b(?:sat|gan|cach|sau lung)\s+(?:voi\s+)?$',before):
            nearby = True
        elif re.search(r'\b(?:khong|chua)(?:\s+phai)?\s+$',before):
            negated = True
        else:
            frontage = True
    kind = ('needs_review' if negated or (alley and frontage) else
            'alley_claim' if alley else 'frontage_claim' if frontage else 'unknown')
    # "m2" can mean square metres; leave this shorthand ambiguous rather than invent a width.
    number = r'(\d{1,2}(?:[.,]\d+)?)\s*m([013-9])?(?![\d²])'
    widths = []
    for match in re.finditer(r'\b(?:kiet|hem)(?:\s+(?:rong|nhua|be tong|thong))*\s*'+number,masked):
        value = float(match[1].replace(',','.')) + (int(match[2])/10 if match[2] else 0)
        if .5 <= value <= 20:
            widths.append(value)
    road_widths = []
    for match in re.finditer(r'\bduong(?:\s+rong)?\s*'+number,masked):
        value = float(match[1].replace(',','.')) + (int(match[2])/10 if match[2] else 0)
        if .5 <= value <= 100:
            road_widths.append(value)
    car_negative = bool(re.search(r'\b(?:khong|chua)(?:\s+phai)?\s+(?:kiet\s+|hem\s+)?(?:oto|o to)\b|\b(?:oto|o to)\s+(?:khong|chua)\b',masked))
    car_pattern = r'\b(?:kiet|hem)\s+(?:oto|o to)\b|\b(?:oto|o to)\s+(?:do cua|vao nha|vao duoc|vao tan|den cua)\b'
    car_positive = any(not re.search(r'\b(?:khong|chua)(?:\s+phai)?\s+$',
        masked[max(0,m.start()-25):m.start()]) for m in re.finditer(car_pattern,masked))
    car_relation = bool(re.search(r'\b(?:cach|gan)\b.{0,25}\b(?:oto|o to)\b',masked))
    car = ('needs_review' if car_negative and (car_positive or negated) else 'no_access_claim' if car_negative
           else 'access_claim' if car_positive and not car_relation else 'unknown')
    hints = []
    if re.search(r'\b(?:benh vien|cong vien|truong hoc|cho|ben xe|cang|cau)\b',text):
        hints.append('amenity_or_landmark_mention_not_measured')
    if re.search(r'\b(?:day tro|toa spa|toa nha|shophouse|can ho)\b',text):
        hints.append('property_use_or_category_needs_context')
    if re.search(r'\bmt\b',text):
        hints.append('MT_abbreviation_not_auto_classified')
    if nearby:
        hints.append('near_frontage_not_frontage')
    if kind == 'needs_review' or car == 'needs_review' or len(set(widths))>1:
        hints.append('ambiguous_or_conflicting_claims')
    # Width and vehicle statements remain source claims, not verified measurements.
    return dict(access_type_claim=kind,
        alley_width_claim_m=sorted(set(widths)),road_width_claim_m=sorted(set(road_widths)),
        car_access_claim=car,flags=hints)


def street_key(value):
    return re.sub(r'^(?:duong|pho)\s+','',geo.normalized(value)).strip(' ,')


def coordinate_clusters(rows):
    clusters = defaultdict(list)
    for row in rows:
        raw = json.loads(row['raw_json']); pair, _ = geo.coordinate(raw)
        if pair:
            clusters[pair].append((row,raw))
    return clusters


def raw_snapshots(pipeline_manifest):
    return {k:v for k,v in pipeline_manifest['input_sha256'].items()
            if k.endswith(('.csv','.jsonl')) and not k.startswith('processed/')}


def run():
    audit_root = geo.OUT / json.loads((geo.OUT/'latest_audit.json').read_text())['run']
    audit_manifest = json.loads((audit_root/'manifest.json').read_text())
    geo.existing_verified(audit_root,audit_manifest['input_sha256'])
    geo.assert_hashes(audit_manifest['input_sha256'])
    candidates = geo.read(audit_root/'coordinate_review_template.csv')
    keys = {r['record_key'] for r in candidates}
    if len(keys) != 80 or len(candidates) != len(keys):
        raise ValueError('Expected the approved fixed cohort of 80 unique IDs')
    pipeline = geo.latest('collection_pipeline')
    manifest = json.loads((pipeline/'manifest.json').read_text())
    raws = raw_snapshots(manifest)
    geo.assert_hashes(raws)
    geo.assert_hashes(manifest['output_sha256'])
    saved_details = geo.BASE/'processed/collection_source_review/parsed_evidence.json'
    old_details = geo.BASE/'processed/training_source_review/evidence.json'
    paths = [Path(__file__),Path(geo.__file__),audit_root/'manifest.json',
        audit_root/'location_audit.csv',audit_root/'coordinate_review_template.csv',
        pipeline/'all_listings.csv',pipeline/'manifest.json',saved_details,old_details,
        geo.OUT/'coordinate_review.csv'] + [geo.BASE/p for p in raws] + geo.frozen_paths()
    inputs = geo.hash_inputs(paths)
    code = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    final = OUT/'runs'/code
    if geo.existing_verified(final,inputs):
        geo.write_json(OUT/'latest.json',{'run':final.relative_to(OUT).as_posix()})
        return final
    before = geo.artifact_stats()
    # geo's original protection excludes the complete geospatial subtree, including this review.
    all_rows = geo.read(pipeline/'all_listings.csv')
    selected = {r['record_key']:r for r in all_rows if r['record_key'] in keys}
    audit = {r['record_key']:r for r in geo.read(audit_root/'location_audit.csv')}
    if set(selected) != keys or any(r['pipeline_status']!='eligible' for r in selected.values()):
        raise ValueError('Candidate membership/status mismatch')
    details = json.loads(saved_details.read_text())
    old = {r['record_key']:r for r in json.loads(old_details.read_text())}
    snapshots = defaultdict(list)
    # Scan all source snapshots for ID-specific additional text, never borrow another ID's description.
    for relative in raws:
        path = geo.BASE/relative
        observations = geo.read(path) if path.suffix=='.csv' else [json.loads(line)
            for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        for index, raw in enumerate(observations,2 if path.suffix=='.csv' else 1):
            if raw.get('source')!='chotot' and 'chotot' not in relative:
                continue
            sid = str(raw.get('source_listing_id') or raw.get('list_id') or '').removeprefix('chotot:')
            key = 'chotot:'+sid
            if key in keys:
                snapshots[key].append((relative,index,raw))
    clusters = coordinate_clusters(all_rows)
    reviews, evidence, cluster_rows = [], [], []
    for key in sorted(keys):
        row = selected[key]; raw = json.loads(row['raw_json']); pair, _ = geo.coordinate(raw)
        if not pair or row['source']!='chotot':
            raise ValueError('Unexpected coordinate source')
        entries = snapshots[key]
        titles = {str(r.get('title') or '') for _,_,r in entries}
        coords = {geo.coordinate(r)[0] for _,_,r in entries if geo.coordinate(r)[0]}
        if not entries or not titles:
            raise ValueError('No source snapshot evidence for '+key)
        source_values = [r.get('source_values') for _,_,r in entries if r.get('source_values')]
        source_pair_matches = all(geo.coordinate(r)[0]==pair for r in source_values) if source_values else False
        detail = details.get(key) or old.get(key)
        description = (detail or {}).get('description') or ''
        raw_descriptions = [r.get('description') or r.get('body') for _,_,r in entries
                            if r.get('description') or r.get('body')]
        # This fixed review expects listing titles only; new detail sources need a new explicit parser.
        if description or raw_descriptions:
            raise ValueError('Additional detailed text found; review parser policy before using it')
        claim = access_claims(raw['title'])
        group = clusters[pair]
        streets = sorted({street_key(r.get('street','')) for _,r in group} - {''})
        wards = sorted({geo.normalized(r.get('ward','')) for _,r in group} - {''})
        districts = sorted({geo.normalized(r.get('district','')) for _,r in group} - {''})
        flags = list(claim['flags'])
        if len(titles)>1 or len(coords)>1 or not source_pair_matches:
            flags.append('source_snapshot_disagreement')
        if len(streets)>1:
            flags.append('shared_pin_multiple_source_streets')
        if len(wards)>1 or len(districts)>1:
            flags.append('shared_pin_multiple_source_areas')
        title = geo.normalized(raw['title'])
        street = street_key(raw.get('street',''))
        origin = row['input_file']+'#row='+row['input_row']
        review = dict(record_key=key,source=row['source'],v3_cohort=audit[key]['v3_cohort'],
            pipeline_group=row['pipeline_group'],detail_url=row['detail_url'],
            latitude=pair[0],longitude=pair[1],street_raw=raw.get('street',''),
            ward_raw=raw.get('ward',''),district_raw=raw.get('district',''),
            location_review_status='insufficient_property_level_evidence',
            location_verified=False,reuse_for_ml_verified=False,
            exact_house_number_verified=False,source_snapshot_count=len(entries),
            source_coordinates_consistent=len(coords)==1 and pair in coords and source_pair_matches,
            detail_description_available=False,
            exact_source_street_mentioned_in_title=bool(street and street in title),
            shared_pin_ids=len(group),shared_pin_distinct_streets=len(streets),
            shared_pin_distinct_wards=len(wards),shared_pin_distinct_districts=len(districts),
            access_type_claim=claim['access_type_claim'],
            alley_width_claim_m=';'.join(str(v) for v in claim['alley_width_claim_m']),
            road_width_claim_m=';'.join(str(v) for v in claim['road_width_claim_m']),
            car_access_claim=claim['car_access_claim'],
            claim_verification_status='source_title_claim_only',
            model_feature_approved=False,review_flags=';'.join(flags),
            evidence_ref=origin,title_evidence=raw['title'],
            next_evidence_needed='Property-level address/pin and independent reuse evidence; full listing detail for access claims')
        reviews.append(review)
        for relative,index,observation in entries:
            evidence.append(dict(record_key=key,file=relative,input_row=index,
                file_sha256=raws[relative],evidence_kind='same_source_listing_snapshot',
                field='title',value=observation.get('title',''),
                independent_location_confirmation=False))
        evidence.append(dict(record_key=key,file=row['input_file'],input_row=row['input_row'],
            file_sha256=raws[row['input_file']],evidence_kind='source_structured_location',
            field='street_ward_district_lat_lon',
            value=json.dumps({k:raw.get(k,'') for k in ['street','ward','district','latitude','longitude']},ensure_ascii=False),
            independent_location_confirmation=False))
    for pair,group in sorted(clusters.items()):
        chosen = sorted(r['record_key'] for r,_ in group if r['record_key'] in keys)
        if not chosen:
            continue
        cluster_rows.append(dict(latitude=pair[0],longitude=pair[1],all_collection_ids=len(group),
            candidate_ids=';'.join(chosen),
            streets=json.dumps(sorted({r.get('street','') for _,r in group} - {''}),ensure_ascii=False),
            wards=json.dumps(sorted({r.get('ward','') for _,r in group} - {''}),ensure_ascii=False),
            districts=json.dumps(sorted({r.get('district','') for _,r in group} - {''}),ensure_ascii=False)))
    summary = dict(created_at=geo.now(),reviewed_ids=len(reviews),
        cohorts=dict(Counter(r['v3_cohort'] for r in reviews)),
        access_type_claims=dict(Counter(r['access_type_claim'] for r in reviews)),
        alley_width_claims=sum(bool(r['alley_width_claim_m']) for r in reviews),
        road_width_claims=sum(bool(r['road_width_claim_m']) for r in reviews),
        car_access_claims=dict(Counter(r['car_access_claim'] for r in reviews)),
        shared_pin_multiple_streets=sum('shared_pin_multiple_source_streets' in r['review_flags'] for r in reviews),
        shared_pin_multiple_areas=sum('shared_pin_multiple_source_areas' in r['review_flags'] for r in reviews),
        all_source_snapshots_scanned=len(raws),matching_snapshot_rows=sum(len(v) for v in snapshots.values()),
        description_available=0,verified_property_locations=0,approved_model_features=0,
        network_requests=0,model_training_performed=False,
        policy='Evidence review only; no automatic location, category, label or split corrections.')
    OUT.mkdir(parents=True,exist_ok=True)
    stage = OUT/('stage_'+uuid.uuid4().hex)
    stage.mkdir()
    geo.write_csv(stage/'reviewed_80.csv',reviews,list(reviews[0]))
    geo.write_csv(stage/'evidence.csv',evidence,list(evidence[0]))
    geo.write_csv(stage/'coordinate_clusters.csv',cluster_rows,list(cluster_rows[0]))
    geo.write_json(stage/'summary.json',summary)
    report = ['# Rà soát 80 tin có tọa độ', '',
        f"Đã rà soát {len(reviews)} ID: 67 train, 6 validation, 7 reserved. "
        'Reserved chỉ kiểm tra bằng chứng vị trí/đường tiếp cận, không phân tích nhãn giá hoặc dự đoán và không đưa vào model.', '',
        '## Bằng chứng kiệt/hẻm từ tiêu đề', '', '| Loại lời khai | Số tin |', '| --- | ---: |']
    report.extend(f'| {kind} | {count} |' for kind,count in summary['access_type_claims'].items())
    report += ['',f"Có {summary['alley_width_claims']} tin nêu chiều rộng kiệt/hẻm; "
        f"{summary['road_width_claims']} tin nêu chiều rộng đường. "
        f"Có {summary['car_access_claims'].get('access_claim',0)} tin nêu kiệt/hẻm ô tô hoặc ô tô đến cửa. "
        'Không suy ra chiều rộng hẻm từ ngang nhà, số kiệt, diện tích hay số tầng. '
        '“Sát mặt tiền” không được coi là nhà mặt tiền; MT viết tắt giữ tín hiệu chờ xem thêm.', '',
        '## Vị trí chưa đủ xác minh', '',
        f"{summary['shared_pin_multiple_streets']}/80 tin dùng điểm tọa độ còn xuất hiện với nhiều tên đường nguồn "
        'trong toàn bộ collection. Đây là nghi vấn điểm đại diện hoặc dữ liệu nguồn không chính xác, '
        'không tự chứng minh căn nhà nằm sai địa chỉ hoặc tin trùng. Không ép tên phường mới/cũ thành cùng một địa chỉ.', '',
        'Cả 80 tin không có số nhà được xác minh hoặc bằng chứng độc lập xác nhận vị trí đúng tài sản. '
        'CSV và JSONL là hai bản lưu của cùng API, không phải hai nguồn xác minh độc lập. '
        'Các cache chi tiết đã lưu không có mô tả của 80 ID này; không mượn mô tả tin khác.', '',
        '**0 vị trí được nâng thành đã xác minh; 0 đặc trưng được tự duyệt để train.** '
        'V3 vẫn sử dụng được; đây là kiểm tra bổ sung, không phải điều kiện chạy v3. '
        'Không sửa nhãn, tọa độ, phân nhóm, tập giữ riêng hoặc model. Bản làm việc coordinate_review.csv giữ nguyên.', '',
        '## Tệp kết quả', '',
        '- `reviewed_80.csv`: mỗi ID một dòng, lời khai, các tín hiệu và bằng chứng tiêu đề gốc.',
        '- `evidence.csv`: tham chiếu file, dòng, trường và SHA-256, không tự coi nguồn là xác minh độc lập.',
        '- `coordinate_clusters.csv`: các điểm chung và danh sách đường/phường khai báo để đối chiếu.', '',
        'Các tệp có tiêu đề chứa giá chỉ dùng để xem bằng chứng, **không nhập toàn bộ vào XGBoost**. '
        'Đặc trưng mới chỉ được chọn rõ ràng sau khi xác minh và tạo phiên bản riêng. '
        '“Gần bệnh viện/công viên” là lời khai chưa đo, không chuyển thành khoảng cách mét.', '',
        'Bước tiếp cần nội dung chi tiết/địa chỉ cấp tài sản và nguồn định vị được phép sử dụng. '
        'Không thể chứng minh tọa độ đúng căn nhà chỉ bằng tên đường/phường và một điểm API.', '']
    (stage/'README.md').write_text('\n'.join(report),encoding='utf-8')
    geo.assert_hashes(inputs)
    if geo.artifact_stats()!=before:
        raise ValueError('Other processed artifacts changed')
    geo.finish(stage,inputs,dict(complete=True,raw_data_unchanged=True,
        frozen_v3_unchanged=True,coordinate_working_review_unchanged=True))
    final.parent.mkdir(exist_ok=True)
    stage.rename(final)
    geo.write_json(OUT/'latest.json',{'run':final.relative_to(OUT).as_posix()})
    (OUT/'README.md').write_text('# Rà soát vị trí và kiệt/hẻm\n\n'
        f'[Báo cáo 80 tin đã chốt]({final.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')
    return final


if __name__ == '__main__':
    print(run())
