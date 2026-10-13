"""Read-only source audit and reproducible OSM proximity features, separate from v3.

No geocoder calls, no edits to raw data, labels, splits or trained models.
"""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlencode
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

import training_v3_common
from training_v3_common import BASE, PROCESSED, read, sha, write_csv, write_json, normalized

OUT = PROCESSED / 'geospatial_v1'
KINDS = {'school': ('amenity', 'school'), 'hospital': ('amenity', 'hospital'),
         'park': ('leisure', 'park')}
RADIUS_M = 3000
ATTRIBUTION = '© OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright'
REVIEW_FIELDS = ['record_key', 'latitude', 'longitude', 'coordinate_origin',
    'precision', 'location_verified', 'reuse_for_ml_verified', 'evidence',
    'reviewed_by', 'reviewed_at']


def now():
    return datetime.now(timezone.utc).isoformat()


def latest(name):
    root = PROCESSED / name
    return root / json.loads((root / 'latest.json').read_text())['run']


def finite(value):
    if value is None or str(value).strip() == '':
        return None
    try:
        result = float(value)
    except (ValueError, TypeError):
        return None
    return result if math.isfinite(result) else None


def coordinate(raw):
    a, b = raw.get('latitude'), raw.get('longitude')
    if a in ('', None) and b in ('', None):
        return None, 'missing'
    if a in ('', None) or b in ('', None):
        return None, 'incomplete'
    lat, lon = finite(a), finite(b)
    if lat is None or lon is None or not -90 <= lat <= 90 or not -180 <= lon <= 180:
        return None, 'invalid'
    if (lat, lon) == (0, 0):
        return None, 'invalid_zero_zero'
    return (lat, lon), 'numeric_valid_precision_unverified'


def distance(a, b):
    """Great-circle metres, NOT distance along a walkable/drivable road."""
    lat1, lat2 = math.radians(a[0]), math.radians(b[0])
    dlat = lat2 - lat1
    dlon = math.radians(b[1] - a[1])
    h = math.sin(dlat/2)**2 + math.cos(lat1)*math.cos(lat2)*math.sin(dlon/2)**2
    return 6371008.8 * 2 * math.asin(math.sqrt(min(1, max(0, h))))


def hash_inputs(paths):
    return {p.relative_to(BASE).as_posix(): sha(p) for p in sorted(set(paths))}


def assert_hashes(values):
    for name, expected in values.items():
        if sha(BASE / name) != expected:
            raise ValueError('Input changed: ' + name)


def artifact_stats():
    return {p.relative_to(BASE).as_posix(): (p.stat().st_size, p.stat().st_mtime_ns)
            for p in PROCESSED.rglob('*') if p.is_file() and OUT not in p.parents}


def frozen_paths():
    """Protect model/data outputs directly; do not rehash unrelated multi-GB HTML."""
    paths = []
    for name in ('training_v3', 'models_v3_validation'):
        root = latest(name)
        paths.append(root / 'manifest.json')
        manifest = json.loads((root / 'manifest.json').read_text())
        for relative, expected in manifest['output_sha256'].items():
            path = root / relative
            if sha(path) != expected:
                raise ValueError('Frozen v3 artifact changed: ' + str(path))
            paths.append(path)
    return paths


def existing_verified(root, inputs):
    if not root.exists():
        return False
    manifest = json.loads((root / 'manifest.json').read_text())
    if manifest['input_sha256'] != inputs:
        raise ValueError('Run input mismatch')
    for name, expected in manifest['output_sha256'].items():
        if sha(root / name) != expected:
            raise ValueError('Run output changed: ' + name)
    return True


def finish(root, inputs, metadata):
    assert_hashes(inputs)
    write_json(root / 'manifest.json', dict(input_sha256=inputs,
        output_sha256={p.name: sha(p) for p in root.iterdir() if p.is_file()}, **metadata))


def address_hints(address, street):
    text = normalized(address)
    # Only a review hint. A number can be a street name, project name or postal code.
    numbered = bool(re.search(r'(?<!\w)\d+[a-z]?(?:/\d+[a-z]?)*(?=\s|,|$)', text))
    return bool(str(address).strip()), bool(str(street).strip()), numbered


def audit():
    pipeline, training = latest('collection_pipeline'), latest('training_v3')
    paths = [Path(__file__), Path(training_v3_common.__file__), pipeline/'manifest.json', pipeline/'all_listings.csv',
             training/'train.csv', training/'validation.csv', training/'reserved_holdout_registry.csv']
    protected = frozen_paths()
    pipeline_manifest = json.loads((pipeline/'manifest.json').read_text())
    expected = pipeline_manifest['output_sha256'][(pipeline/'all_listings.csv').relative_to(BASE).as_posix()]
    if sha(pipeline/'all_listings.csv') != expected:
        raise ValueError('Collection snapshot differs from its manifest')
    inputs = hash_inputs(paths + protected)
    fingerprint = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    root = OUT / 'audit_runs' / fingerprint
    if existing_verified(root, inputs):
        write_json(OUT/'latest_audit.json', {'run': root.relative_to(OUT).as_posix()})
        return root
    stats_before = artifact_stats()
    rows = read(pipeline/'all_listings.csv')
    cohorts = {}
    for split in ('train', 'validation'):
        for row in read(training/(split+'.csv')):
            if row['record_key'] in cohorts:
                raise ValueError('Overlapping v3 cohorts')
            cohorts[row['record_key']] = split
    for row in read(training/'reserved_holdout_registry.csv'):
        cohorts[row['record_key']] = 'reserved'
    if len({r['record_key'] for r in rows}) != len(rows):
        raise ValueError('Repeated collection IDs')
    decoded = {r['record_key']: json.loads(r['raw_json']) for r in rows}
    pairs = Counter(coordinate(raw)[0] for raw in decoded.values() if coordinate(raw)[0])
    records, reviews, geocoding = [], [], []
    counts = Counter()
    for row in rows:
        key = row['record_key']; raw = decoded[key]
        pair, state = coordinate(raw)
        address = raw.get('address_raw') or row.get('address_raw') or ''
        street = raw.get('street') or ''
        has_address, has_street, number_hint = address_hints(address, street)
        cohort = cohorts.get(key, 'outside_v3')
        repeat = pairs[pair] if pair else 0
        # Broad Vietnam plausibility filter only, NOT a Da Nang administrative boundary.
        plausible = bool(pair and 8 <= pair[0] <= 24 and 102 <= pair[1] <= 110)
        record = dict(record_key=key, source=row['source'], category=row['category'],
            pipeline_status=row['pipeline_status'], v3_cohort=cohort,
            pipeline_group=row['pipeline_group'], detail_url=row['detail_url'],
            latitude=pair[0] if pair else '', longitude=pair[1] if pair else '',
            raw_latitude=raw.get('latitude', ''), raw_longitude=raw.get('longitude', ''),
            coordinate_state=state, vietnam_bbox_plausible=plausible,
            coordinate_repeated_ids=repeat, location_verified=False,
            reuse_for_ml_verified=False, address_raw=address, street_raw=street,
            has_address=has_address, has_street=has_street, address_number_hint=number_hint,
            input_file=row['input_file'], input_row=row['input_row'])
        records.append(record)
        for dimension, value in [('source', row['source']), ('v3_cohort', cohort),
                                  ('pipeline_status', row['pipeline_status']), ('all', 'all')]:
            counts[(dimension, value, 'rows')] += 1
            for name, present in [('numeric_coordinates', bool(pair)),
                ('repeated_coordinate', repeat > 1), ('has_address', has_address),
                ('has_street', has_street), ('address_number_hint', number_hint)]:
                counts[(dimension, value, name)] += int(present)
        if row['pipeline_status'] != 'eligible':
            continue
        if pair:
            reviews.append(dict(record_key=key, latitude=pair[0], longitude=pair[1],
                coordinate_origin='listing_source_unverified', precision='unknown',
                location_verified='False', reuse_for_ml_verified='False', evidence='',
                reviewed_by='', reviewed_at=''))
        else:
            geocoding.append({k:record[k] for k in ['record_key','source','category',
                'v3_cohort','pipeline_group','detail_url','address_raw','street_raw',
                'has_street','address_number_hint']})
    summary = dict(created_at=now(), rows=len(rows),
        numeric_coordinates=sum(bool(coordinate(r)[0]) for r in decoded.values()),
        distinct_coordinate_pairs=len(pairs), eligible_coordinate_candidates=len(reviews),
        eligible_needing_location=len(geocoding), verified_coordinates=0,
        approved_for_ml_coordinates=0,
        train_coordinates=sum(r['v3_cohort']=='train' and bool(r['latitude']) for r in records),
        validation_coordinates=sum(r['v3_cohort']=='validation' and bool(r['latitude']) for r in records),
        public_geocoder_requests=0,
        warning='Coordinate presence/repetition and address hints do not verify property precision or reuse rights.')
    root.mkdir(parents=True)
    write_csv(root/'location_audit.csv', records, list(records[0]))
    write_csv(root/'coordinate_review_template.csv', reviews, REVIEW_FIELDS)
    write_csv(root/'geocoding_queue.csv', geocoding, list(geocoding[0]))
    coverage = [dict(dimension=d, value=v, metric=m, count=n)
                for (d,v,m), n in sorted(counts.items())]
    write_csv(root/'coverage.csv', coverage, ['dimension','value','metric','count'])
    write_json(root/'summary.json', summary)
    (root/'README.md').write_text(
        '# Độ phủ vị trí SmartProp\n\n'
        f"Kiểm tra {len(rows):,} ID duy nhất của collection hiện tại. Có {summary['numeric_coordinates']:,} "
        f"cặp tọa độ hợp lệ về số, {len(pairs):,} cặp khác nhau; tất cả còn chưa xác minh độ chính xác "
        'và quyền tái sử dụng để huấn luyện. Điểm lặp không tự chứng minh tin trùng hay vị trí sai.\n\n'
        f"Trong v3: {summary['train_coordinates']} train và {summary['validation_coordinates']} validation có tọa độ. "
        f"Có {len(reviews)} ứng viên tọa độ đủ điều kiện dữ liệu; {len(geocoding):,} tin đủ điều kiện còn cần định vị. "
        'Không lấy lại tin bị loại/chờ duyệt chỉ vì có tọa độ.\n\n'
        '- `location_audit.csv`: toàn bộ ID, địa chỉ nguồn, trạng thái và số ID dùng cùng tọa độ.\n'
        '- `coverage.csv`: độ phủ theo nguồn, cohort và trạng thái dữ liệu.\n'
        '- `coordinate_review_template.csv`: bản mẫu cho các ứng viên có tọa độ; sao chép ra ngoài run trước khi duyệt.\n'
        '- `geocoding_queue.csv`: hàng chờ địa chỉ, không phải địa chỉ đã định vị. Số trong địa chỉ chỉ là tín hiệu.\n\n'
        'Chưa có tọa độ được duyệt dùng ML. Không sửa giá, diện tích, train/validation/test hoặc model v3. '
        'Dữ liệu test giữ riêng; không phân tích giá hay dự đoán của test.\n', encoding='utf-8')
    if artifact_stats() != stats_before:
        raise ValueError('Existing processed artifacts changed during audit')
    finish(root, inputs, dict(other_processed_files_stat_unchanged=True,
                             frozen_v3_outputs_sha256_unchanged=True))
    OUT.mkdir(exist_ok=True)
    write_json(OUT/'latest_audit.json', {'run': root.relative_to(OUT).as_posix()})
    return root


def query_for(bbox):
    south, west, north, east = bbox
    if not (8 <= south < north <= 24 and 102 <= west < east <= 110):
        raise ValueError('Query must be a plausible Vietnam bbox')
    if north-south > 1 or east-west > 1:
        raise ValueError('Use a regional extract for a larger area')
    box = ','.join(str(v) for v in bbox)
    selectors = ''.join(f'nwr["{k}"="{v}"]({box});' for k,v in KINDS.values())
    return '[out:json][timeout:45];(' + selectors + ');out center;'


def parse_osm(data):
    if data.get('remark') or not isinstance(data.get('elements'), list):
        raise ValueError('Incomplete or invalid Overpass response')
    result, seen = [], set()
    for element in data['elements']:
        tags = element.get('tags', {})
        point = element if element.get('type') == 'node' else element.get('center', {})
        pair, _ = coordinate({'latitude':point.get('lat'), 'longitude':point.get('lon')})
        if not pair:
            raise ValueError('OSM matching element lacks a usable representative point')
        key = str(element['type']) + '/' + str(element['id'])
        if key in seen:
            raise ValueError('Repeated OSM element ID')
        seen.add(key)
        for kind, (tag, value) in KINDS.items():
            if tags.get(tag) == value:
                result.append(dict(osm_id=key, kind=kind, latitude=pair[0], longitude=pair[1],
                    name=tags.get('name',''), point_basis='node' if element['type']=='node' else 'bbox_center',
                    ownership=tags.get('ownership','unknown'), access=tags.get('access','unknown')))
    return result


def fetch_osm(bbox, endpoint='https://overpass-api.de/api/interpreter'):
    query = query_for(bbox)
    code = hashlib.sha256(query.encode()).hexdigest()[:16]
    root = OUT/'osm_snapshots'/code
    if root.exists():
        meta = json.loads((root/'metadata.json').read_text())
        if meta['query'] != query or sha(root/'response.json') != meta['response_sha256']:
            raise ValueError('OSM cache changed')
        parse_osm(json.loads((root/'response.json').read_text()))
        return root
    if endpoint not in ('https://overpass-api.de/api/interpreter',
                        'https://overpass.private.coffee/api/interpreter',
                        'https://maps.mail.ru/osm/tools/overpass/api/interpreter'):
        raise ValueError('Use a documented public Overpass instance')
    req = Request(endpoint, data=urlencode({'data':query}).encode(),
        headers={'User-Agent':'SmartProp-research/1.0 (https://github.com/manchae19/SmartProp)',
                 'Content-Type':'application/x-www-form-urlencoded'})
    with urlopen(req, timeout=55) as response:
        payload = response.read(20_000_001)
    if len(payload) > 20_000_000:
        raise ValueError('Response exceeds size limit')
    data = json.loads(payload)
    pois = parse_osm(data)
    root.mkdir(parents=True)
    (root/'response.json').write_bytes(payload)
    write_csv(root/'pois.csv', pois, ['osm_id','kind','latitude','longitude','name',
                                      'point_basis','ownership','access'])
    write_json(root/'metadata.json', dict(query=query, bbox=list(bbox), endpoint=endpoint,
        fetched_at=now(), osm_base_timestamp=data.get('osm3s',{}).get('timestamp_osm_base',''),
        response_sha256=sha(root/'response.json'), attribution=ATTRIBUTION,
        categories=KINDS, poi_counts=dict(Counter(p['kind'] for p in pois)),
        warning='Mapped amenities, not necessarily public-owned or exhaustive; way/relation centres are approximate.'))
    return root


def approved_review(row):
    allowed = {'openstreetmap', 'open_data', 'survey', 'owner_supplied', 'listing_source'}
    pair, _ = coordinate(row)
    # A numeric source pin, street midpoint or neighbourhood centroid is insufficient.
    if (not pair or row.get('coordinate_origin') not in allowed
            or row.get('precision') != 'property'
            or row.get('location_verified') != 'True'
            or row.get('reuse_for_ml_verified') != 'True'
            or not all(row.get(k,'').strip() for k in ('evidence','reviewed_by','reviewed_at'))):
        return False
    try:
        if datetime.fromisoformat(row['reviewed_at']).tzinfo is None:
            return False
    except ValueError:
        return False
    return True


def covered(pair, bbox):
    s,w,n,e = bbox
    lat,lon = pair
    if not s <= lat <= n or not w <= lon <= e:
        return False
    return min(distance(pair,(s,lon)),distance(pair,(n,lon)),
               distance(pair,(lat,w)),distance(pair,(lat,e))) >= RADIUS_M


def proximities(pair, pois, bbox):
    if not covered(pair, bbox):
        return {}, 'outside_full_search_buffer'
    result = {}
    for kind in KINDS:
        candidates = [(distance(pair,(p['latitude'],p['longitude'])),p['osm_id'])
                      for p in pois if p['kind'] == kind]
        nearest = min(candidates) if candidates else None
        # Missing is not zero distance; this means no mapped object within the search cap.
        found = bool(nearest and nearest[0] <= RADIUS_M)
        result[kind+'_distance_m'] = round(nearest[0],2) if found else ''
        result[kind+'_missing_within_3000m'] = not found
        result[kind+'_osm_id'] = nearest[1] if found else ''
    return result, 'computed_straight_line_to_osm_representative_point'


def build_features(audit_root, osm_root, review_path=None):
    audit_manifest = json.loads((audit_root/'manifest.json').read_text())
    existing_verified(audit_root,audit_manifest['input_sha256'])
    records = read(audit_root/'location_audit.csv')
    rows = [r for r in records if r['v3_cohort'] in ('train','validation')]
    reviews = read(review_path) if review_path else []
    bykey = {r['record_key']:r for r in reviews}
    if len(bykey) != len(reviews) or set(bykey) - {r['record_key'] for r in records
                                              if r['pipeline_status']=='eligible'}:
        raise ValueError('Review IDs are repeated, unknown or ineligible')
    metadata = json.loads((osm_root/'metadata.json').read_text())
    if sha(osm_root/'response.json') != metadata['response_sha256']:
        raise ValueError('OSM snapshot changed')
    pois = parse_osm(json.loads((osm_root/'response.json').read_text()))
    paths = [Path(__file__),Path(training_v3_common.__file__),audit_root/'location_audit.csv',audit_root/'manifest.json',
             osm_root/'response.json',osm_root/'metadata.json']
    if review_path:
        paths.append(review_path)
    inputs = hash_inputs(paths)
    code = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    root = OUT/'feature_runs'/code
    if existing_verified(root,inputs):
        write_json(OUT/'latest_features.json',{'run':root.relative_to(OUT).as_posix()})
        return root
    output, preview = [], []
    for row in rows:
        review = bykey.get(row['record_key'],{})
        usable = approved_review(review)
        pair, _ = coordinate(review if usable else row)
        common = {k:row[k] for k in ['record_key','v3_cohort','pipeline_group','source','category']}
        result = dict(common, location_feature_status='location_unverified',
            geospatial_ready=False, latitude='',longitude='',
            **{kind+suffix:'' for kind in KINDS for suffix in
               ('_distance_m','_missing_within_3000m','_osm_id')})
        if usable:
            values, status = proximities(pair,pois,metadata['bbox'])
            result.update(values,location_feature_status=status,
                          geospatial_ready=bool(values),latitude=pair[0],longitude=pair[1])
        elif pair:
            values, status = proximities(pair,pois,metadata['bbox'])
            candidate = dict(common,latitude=pair[0],longitude=pair[1],
                **{kind+suffix:'' for kind in KINDS for suffix in
                   ('_distance_m','_missing_within_3000m','_osm_id')})
            candidate.update(values,preview_status=status,can_train=False)
            preview.append(candidate)
        output.append(result)
    root.mkdir(parents=True)
    write_csv(root/'features.csv',output,list(output[0]))
    preview_fields = list(preview[0]) if preview else list(output[0]) + ['preview_status','can_train']
    write_csv(root/'unverified_preview_DO_NOT_TRAIN.csv',preview,preview_fields)
    summary = dict(created_at=now(),rows=len(output),
        verified_features_ready=sum(r['geospatial_ready'] for r in output),
        unverified_preview_rows=len(preview),train_rows=sum(r['v3_cohort']=='train' for r in output),
        validation_rows=sum(r['v3_cohort']=='validation' for r in output),
        model_training_performed=False,attribution=ATTRIBUTION,
        radius_m=RADIUS_M,distance_method='haversine_to_node_or_bbox_center',
        snapshot_time=metadata['osm_base_timestamp'],
        warning='Current map context is not verified historical context at listing date. '
                'Facilities may be private; coverage is incomplete; no alley-width inference.')
    write_json(root/'summary.json',summary)
    (root/'README.md').write_text('# Đặc trưng khoảng cách thử nghiệm\n\n'
        f"Có {len(output):,} ID train/validation, {summary['verified_features_ready']} ID đủ điều kiện vị trí "
        f"để dùng đặc trưng, {len(preview)} ID chỉ có bản xem thử chưa xác minh.\n\n"
        '`features.csv` giữ đủ cohort và cờ thiếu; không có giá/nhãn. '
        '`unverified_preview_DO_NOT_TRAIN.csv` chỉ phục vụ kiểm tra vị trí, không dùng train/chọn model. '
        'Không đụng tới test.\n\n'
        'Khoảng cách đường chim bay đến điểm node hoặc tâm bounding box của công trình, '
        'không phải khoảng cách đi bộ, lối vào hay chiều rộng hẻm. Chỉ tìm trong 3 km và '
        'yêu cầu đủ vùng đệm; không tìm thấy được ghi thiếu, không ghi 0 m. '
        'Trường/bệnh viện/công viên có thể thuộc tư nhân, chưa xác minh quyền tiếp cận. '
        'OSM có thể thiếu công trình hoặc có nhiều đối tượng cho cùng một cơ sở. '
        'Không tạo biến đếm cơ sở. Bản đồ hiện tại không chứng minh tiện ích tồn tại lúc đăng tin.\n\n'
        + ATTRIBUTION + '\n',encoding='utf-8')
    finish(root,inputs,{'model_training_performed':False})
    write_json(OUT/'latest_features.json',{'run':root.relative_to(OUT).as_posix()})
    return root


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command',required=True)
    sub.add_parser('audit')
    fetch = sub.add_parser('fetch-osm')
    fetch.add_argument('--bbox',type=float,nargs=4,required=True,metavar=('S','W','N','E'))
    fetch.add_argument('--endpoint',default='https://overpass-api.de/api/interpreter',
        choices=['https://overpass-api.de/api/interpreter',
                 'https://overpass.private.coffee/api/interpreter',
                 'https://maps.mail.ru/osm/tools/overpass/api/interpreter'])
    build = sub.add_parser('build-features')
    build.add_argument('--audit-dir',type=Path,required=True)
    build.add_argument('--osm-dir',type=Path,required=True)
    build.add_argument('--reviews',type=Path)
    args = parser.parse_args()
    if args.command == 'audit':
        result = audit()
    elif args.command == 'fetch-osm':
        try:
            result = fetch_osm(args.bbox,args.endpoint)
        except (HTTPError,URLError,TimeoutError) as error:
            raise SystemExit('OSM download failed; no usable snapshot saved: ' + str(error))
    else:
        result = build_features(args.audit_dir,args.osm_dir,args.reviews)
    print(result)


if __name__ == '__main__':
    main()
