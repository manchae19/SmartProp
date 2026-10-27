"""Finite, cached address lookup for the existing 80 candidates; never ML approval.

Nominatim policy: one machine, one thread, >=1.1 s between requests, cache all
responses, stop on service errors. Not an app geocoder or scheduled batch job.
Google Maps URLs are navigation links only; no Google content is downloaded.
"""
import argparse
import hashlib
import html
import json
import math
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, urlsplit
from urllib.request import Request, urlopen

from training_v3_common import BASE, read, sha, verify, write_csv, normalized

ROOT = BASE / 'processed/geospatial_v1/address_pilot'
ENDPOINT = 'https://nominatim.openstreetmap.org/search'
POLICY = 'https://operations.osmfoundation.org/policies/nominatim/'
ATTRIBUTION = '© OpenStreetMap contributors; ODbL 1.0; https://www.openstreetmap.org/copyright'
UA = 'SmartProp-AddressPilot/1.0 (+https://github.com/manchae19/SmartProp; finite-80-record-research)'


def now():
    return datetime.now(timezone.utc).isoformat()


def digest(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True).encode()).hexdigest()


def save(path, value):
    """Atomic checkpoint replacement; old frozen runs are never overwritten."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + '.tmp')
    temporary.write_text(json.dumps(value, ensure_ascii=False, indent=2, allow_nan=False), encoding='utf-8')
    temporary.replace(path)


def load(path):
    return json.loads(path.read_text(encoding='utf-8'))


def street_name(value):
    return re.sub(r'^(?:duong|pho)\s+', '', normalized(value)).strip(' ,')


def query_params(row):
    # Structured source street only, never title, price, names, telephone or house pins.
    # Legacy ward/district names are retained for review, not silently remapped.
    street = re.sub(r'^(?:đường|phố)\s+', '', row['street_raw'].strip(), flags=re.I)
    if not street or len(street) > 150:
        raise ValueError('Missing/invalid street: ' + row['record_key'])
    return dict(street=street, city='Đà Nẵng', countrycodes='vn', format='jsonv2',
                addressdetails=1, limit=5, **{'accept-language': 'vi'})


def prepare(root):
    source_root = BASE / 'processed/geospatial_v1/candidate_review'
    source = source_root / load(source_root / 'latest.json')['run']
    rows = read(source / 'reviewed_80.csv')
    if len(rows) != 80 or len({r['record_key'] for r in rows}) != 80:
        raise ValueError('This pilot is restricted to the reviewed 80 unique IDs')
    source_manifest = load(source / 'manifest.json')
    verify(source_manifest['input_sha256'])
    protected = dict(source_manifest['input_sha256'])
    protected[(source / 'reviewed_80.csv').relative_to(BASE).as_posix()] = sha(source / 'reviewed_80.csv')
    queue = []
    rows.sort(key=lambda r: (-int(r['shared_pin_distinct_streets']), r['record_key']))
    for row in rows:
        params = query_params(row)
        address = ', '.join([row['street_raw'], row['ward_raw'], row['district_raw'], 'Đà Nẵng', 'Việt Nam'])
        queue.append(dict(record_key=row['record_key'], v3_cohort=row['v3_cohort'],
            street_raw=row['street_raw'], ward_raw=row['ward_raw'], district_raw=row['district_raw'],
            address_query=address, query_id=digest(params), params_json=json.dumps(params, ensure_ascii=False, sort_keys=True),
            priority=1 if int(row['shared_pin_distinct_streets']) > 1 else 2,
            exact_house_number_verified=False, detail_url=row['detail_url'],
            google_maps_url='https://www.google.com/maps/search/?' + urlencode({'api': 1, 'query': address})))
    root.mkdir(parents=True, exist_ok=True)
    path = root / 'queue.csv'
    if path.exists():
        manifest = load(root / 'input_manifest.json')
        if manifest['protected_sha256'] != protected or sha(path) != manifest['queue_sha256']:
            raise ValueError('Queue or frozen inputs changed; use a new output directory')
    else:
        write_csv(path, queue, list(queue[0]))
        save(root / 'input_manifest.json', dict(created_at_utc=now(), source_run=str(source.relative_to(BASE)),
            queue_sha256=sha(path), protected_sha256=protected, records=80,
            unique_queries=len({r['query_id'] for r in queue}), policy_url=POLICY))
    return read(path)


def validate_results(value):
    if not isinstance(value, list) or len(value) > 5:
        raise ValueError('Unexpected geocoder response')
    for row in value:
        lat, lon = float(row['lat']), float(row['lon'])
        if not math.isfinite(lat) or not math.isfinite(lon) or not -90 <= lat <= 90 or not -180 <= lon <= 180:
            raise ValueError('Invalid returned coordinates')
        if not isinstance(row.get('address', {}), dict):
            raise ValueError('Invalid returned address')
    return value


def fetch(params, endpoint):
    url = endpoint + '?' + urlencode(params)
    evidence = dict(request_url=url, endpoint=endpoint, params=params, fetched_at_utc=now(), attribution=ATTRIBUTION)
    try:
        with urlopen(Request(url, headers={'User-Agent': UA, 'Accept': 'application/json'}), timeout=30) as response:
            body = response.read(1_000_001)
            evidence.update(http_status=response.status, response_url=response.url)
        if len(body) > 1_000_000:
            raise ValueError('Response too large')
        evidence.update(state='ok', results=validate_results(json.loads(body)), response_sha256=hashlib.sha256(body).hexdigest(),
                        response_body_utf8=body.decode('utf-8'))
    except HTTPError as error:
        evidence.update(state='service_error', http_status=error.code, error=str(error),
                        error_body=error.read(4000).decode('utf-8', errors='replace'))
    except (URLError, TimeoutError, OSError, ValueError, KeyError, TypeError) as error:
        evidence.update(state='service_error', error=str(error))
    return evidence


def cache_path(root, endpoint, query_id):
    return root / 'cache' / digest(endpoint)[:16] / (query_id + '.json')


def cached(root, endpoint, row):
    path = cache_path(root, endpoint, row['query_id'])
    if not path.exists():
        return None
    value = load(path)
    if value['endpoint'] != endpoint or value['params'] != json.loads(row['params_json']):
        raise ValueError('Cache query mismatch')
    if value['state'] == 'ok':
        raw = value['response_body_utf8']
        if hashlib.sha256(raw.encode()).hexdigest() != value['response_sha256']:
            raise ValueError('Cache response hash mismatch')
        if validate_results(json.loads(raw)) != value['results']:
            raise ValueError('Cache results changed')
    return value


def assess(row, result):
    address = result.get('address', {})
    road = address.get('road') or address.get('pedestrian') or address.get('residential') or ''
    road_match = bool(road) and street_name(road) == street_name(row['street_raw'])
    region_match = 'da nang' in normalized(result.get('display_name', '')) and address.get('country_code') == 'vn'
    flags = ['missing_verified_house_number', 'manual_ward_district_check_required']
    if not road_match:
        flags.append('returned_road_does_not_match')
    if not region_match:
        flags.append('returned_region_does_not_match')
    return dict(road_name_matches=road_match, region_matches=region_match,
        precision='street_reference' if road_match and region_match else 'unresolved_candidate',
        review_flags=';'.join(flags), location_verified=False, model_feature_approved=False,
        returned_road=road, candidate_latitude=result['lat'], candidate_longitude=result['lon'],
        osm_type=result.get('osm_type', ''), osm_id=result.get('osm_id', ''),
        display_name=result.get('display_name', ''), result_type=result.get('addresstype', result.get('type', '')))


def report(root, endpoint, queue):
    checkpoints, candidates, cache_hashes = [], [], {}
    for row in queue:
        value = cached(root, endpoint, row)
        if value:
            path = cache_path(root, endpoint, row['query_id'])
            cache_hashes[path.relative_to(root).as_posix()] = sha(path)
        results = value.get('results', []) if value else []
        state = ('not_requested' if value is None else 'service_error' if value['state'] != 'ok'
                 else 'candidates_returned' if results else 'no_result')
        plausible = 0
        for rank, result in enumerate(results, 1):
            assessment = assess(row, result)
            plausible += assessment['precision'] == 'street_reference'
            candidates.append(dict(record_key=row['record_key'], query_id=row['query_id'], rank=rank,
                **assessment, evidence_file=cache_path(root, endpoint, row['query_id']).relative_to(root).as_posix()))
        checkpoints.append(dict(record_key=row['record_key'], priority=row['priority'],
            address_query=row['address_query'], query_id=row['query_id'], state=state,
            http_status=value.get('http_status', '') if value else '', candidate_count=len(results),
            street_reference_count=plausible, location_verified=False, model_feature_approved=False,
            google_maps_url=row['google_maps_url']))
    states = Counter(r['state'] for r in checkpoints)
    summary = dict(records=len(queue), unique_queries=len({r['query_id'] for r in queue}),
        unique_queries_attempted=len(cache_hashes), states=dict(states),
        records_with_street_reference=sum(r['street_reference_count'] > 0 for r in checkpoints),
        candidate_rows=len(candidates), property_locations_verified=0, approved_model_features=0,
        google_content_downloaded=False, attribution=ATTRIBUTION, endpoint=endpoint)
    fingerprint = digest(dict(queue=sha(root/'queue.csv'), cache=cache_hashes, code=sha(Path(__file__)), endpoint=endpoint))[:16]
    run = root / 'runs' / fingerprint
    if not run.exists():
        run.mkdir(parents=True)
        write_csv(run / 'checkpoint.csv', checkpoints, list(checkpoints[0]))
        fields = list(candidates[0]) if candidates else ['record_key', 'query_id', 'rank', 'precision', 'location_verified', 'model_feature_approved']
        write_csv(run / 'candidates_DO_NOT_TRAIN.csv', candidates, fields)
        save(run / 'summary.json', summary)
        rows_html = ''.join('<tr><td>'+html.escape(r['record_key'])+'</td><td>'+html.escape(r['address_query'])+
            '</td><td>'+html.escape(r['state'])+'</td><td><a target="_blank" rel="noopener noreferrer" href="'+
            html.escape(r['google_maps_url'], quote=True)+'">Tìm địa chỉ trên Google Maps</a></td></tr>' for r in checkpoints)
        (run / 'review.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>SmartProp — Đối chiếu địa chỉ</title>'
            '<style>body{font:16px system-ui;margin:32px}td,th{padding:12px;border:1px solid #ddd;text-align:left}table{border-collapse:collapse}a{color:#075bbb}</style>'
            '<h1>Đối chiếu 80 địa chỉ SmartProp</h1><p>Liên kết Google chỉ để xem địa chỉ. Kết quả từ tên đường chưa xác minh căn nhà; '
            'không dùng bảng này làm đầu vào mô hình. Không sao chép tọa độ Google vào nguồn OSM.</p><table><tr><th>ID</th><th>Địa chỉ nguồn</th><th>Trạng thái Nominatim</th><th>Đối chiếu</th></tr>'+
            rows_html+'</table><p>'+html.escape(ATTRIBUTION)+'</p></html>', encoding='utf-8')
        text = (f'# Thử tìm vị trí từ địa chỉ: 80 tin\n\n{len(queue)} ID; {len(cache_hashes)}/{summary["unique_queries"]} truy vấn duy nhất đã thử. '
            f'{summary["records_with_street_reference"]} tin có ứng viên khớp tên đường và vùng Đà Nẵng; **0 căn nhà được xác minh, 0 đặc trưng được duyệt để train**.\n\n'
            f'Trạng thái theo ID: `{dict(states)}`. Một truy vấn có thể dùng chung nhiều ID; không cộng số ID thành số yêu cầu mạng.\n\n'
            '[Mở 80 liên kết Google Maps](review.html), [checkpoint](checkpoint.csv), [ứng viên OSM — không train](candidates_DO_NOT_TRAIN.csv), [số liệu](summary.json). '
            'Không tải nội dung/tọa độ Google; các liên kết dùng đúng địa chỉ nguồn, không tự thêm số nhà.\n\n'
            'Truy vấn OSM chỉ gửi tên đường và Đà Nẵng; không gửi giá, tiêu đề, tên người đăng, số điện thoại hoặc pin nguồn. '
            'Tên phường/quận cũ giữ trong hàng chờ để kiểm tra thủ công, không tự ánh xạ. Không suy ra chiều rộng hẻm, ô tô vào được hoặc khoảng cách từ căn nhà. '
            'Một kết quả khớp đường vẫn có thể là đoạn đường/địa điểm đại diện. Không chọn kết quả đầu tiên làm vị trí tài sản.\n\n'
            'Đợt hữu hạn 80 ID trên một máy, một luồng, cách yêu cầu ít nhất 1,1 giây, cache cả phản hồi rỗng/lỗi; dừng ở lỗi dịch vụ. '
            'Không chạy định kỳ hoặc mở rộng hàng nghìn địa chỉ bằng dịch vụ công cộng. '
            f'[Chính sách Nominatim]({POLICY}).\n\n{ATTRIBUTION}. Giữ bằng chứng và nghĩa vụ ODbL khi phân phối dữ liệu phái sinh. '
            'Chưa chỉnh raw, nhãn, split, coordinate_review hoặc model v3.\n')
        (run / 'README.md').write_text(text, encoding='utf-8')
        save(run / 'manifest.json', dict(created_at_utc=now(), queue_sha256=sha(root/'queue.csv'), cache_sha256=cache_hashes,
            code_sha256=sha(Path(__file__)), output_sha256={p.name:sha(p) for p in run.iterdir() if p.is_file()}))
    else:
        verify(load(run/'manifest.json')['output_sha256'], base=run)
    save(root / 'latest.json', dict(run=run.relative_to(root).as_posix()))
    (root / 'README.md').write_text((run/'README.md').read_text(encoding='utf-8').replace('](review.html)', f']({run.relative_to(root).as_posix()}/review.html)').replace('](checkpoint.csv)', f']({run.relative_to(root).as_posix()}/checkpoint.csv)').replace('](candidates_DO_NOT_TRAIN.csv)', f']({run.relative_to(root).as_posix()}/candidates_DO_NOT_TRAIN.csv)').replace('](summary.json)', f']({run.relative_to(root).as_posix()}/summary.json)'), encoding='utf-8')
    return run, summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=['prepare', 'fetch', 'report'])
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--endpoint', default=ENDPOINT, help='Configurable provider; use one endpoint per batch')
    args = parser.parse_args()
    parsed = urlsplit(args.endpoint)
    if parsed.scheme != 'https' or not parsed.netloc or parsed.query or parsed.fragment or parsed.username:
        parser.error('Endpoint must be an HTTPS search URL without query/credentials')
    queue = prepare(args.output_dir)
    request_count = 0
    last_request = None
    try:
        if args.command == 'fetch':
            for row in queue:
                value = cached(args.output_dir, args.endpoint, row)
                if value is None:
                    if last_request is not None:
                        time.sleep(max(0, 1.1 - (time.monotonic() - last_request)))
                    last_request = time.monotonic()
                    value = fetch(json.loads(row['params_json']), args.endpoint)
                    save(cache_path(args.output_dir, args.endpoint, row['query_id']), value)
                    request_count += 1
                    print(f'{request_count}: {row["record_key"]}: {value["state"]}, results={len(value.get("results", []))}', flush=True)
                if value['state'] != 'ok':
                    print('Stopped at cached service error; no automatic retries or provider switching.', flush=True)
                    break
    except KeyboardInterrupt:
        print('Interrupted; completed responses preserved for resume.', flush=True)
    finally:
        verify(load(args.output_dir/'input_manifest.json')['protected_sha256'])
        run, summary = report(args.output_dir, args.endpoint, queue)
        save(args.output_dir/'verification.json', dict(verified_at_utc=now(), protected_input_sha256_verified=True,
            queue_sha256_verified=sha(args.output_dir/'queue.csv') == load(args.output_dir/'input_manifest.json')['queue_sha256'],
            network_requests_this_invocation=request_count, run=run.relative_to(args.output_dir).as_posix()))
        print(json.dumps(summary, ensure_ascii=False, indent=2))
        print(run)


if __name__ == '__main__':
    main()
