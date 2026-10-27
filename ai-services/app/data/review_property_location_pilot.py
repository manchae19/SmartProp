"""Review 20 source-address clues; bounded OSM refinement, no property approval."""
import argparse
import html
import json
import time
from collections import Counter, defaultdict
from pathlib import Path
from urllib.parse import urlencode

import geocode_address_pilot as lookup
from training_v3_common import BASE, read, sha, verify, write_csv, normalized

ROOT = BASE / 'processed/geospatial_v1/property_location_pilot'
# The existing urban pilot envelope, NOT an administrative boundary. Addresses
# in this selected cohort declare old urban districts; never use source pins
# to declare property accuracy or reuse rights.
VIEWBOX = '108.05,16.21,108.31,15.93'
# Individually read source snippets. These are claims, not verified addresses.
# Tuple: ID, source field, literal snippet, clue kind, proposed search street.
CLUES = [
 ('134925160','title_evidence','kiệt 266 Trường Chính','alley_identifier','Kiệt 266 Trường Chinh'),
 ('135139247','title_evidence','KIỆT 196 ÂU CƠ','alley_identifier','Kiệt 196 Âu Cơ'),
 ('135172657','street_raw','Đường Kiệt 59 Trương Chí Cương','alley_identifier','Kiệt 59 Trương Chí Cương'),
 ('135164017','title_evidence','LK4A - 537, Futa Kim Phát','plot_identifier',''),
 ('135153899','title_evidence','NGUYỄN BỈNH KHIÊM Giao An Mỹ 3','intersection_claim',''),
 ('133955557','title_evidence','SAU LƯNG PHẠM HÙNG','landmark_claim',''),
 ('135031965','title_evidence','TRƯỚC BẾN XE','landmark_claim',''),
 ('135150866','title_evidence','cạnh công viên Đầm Sen','landmark_claim',''),
 ('134126599','title_evidence','HOÀ MINH 21','numbered_street',''),
 ('135149346','title_evidence','hẻm 3m','width_claim_not_address',''),
 ('135170423','title_evidence','KIỆT 3M','width_claim_not_address',''),
 ('135092070','title_evidence','Ngang 5m','parcel_width_not_address',''),
 ('135136720','title_evidence','Ngang 6m','parcel_width_not_address',''),
 ('135143693','title_evidence','GẦN BIỂN NGUYỄN TẤT THÀNH','landmark_claim',''),
 ('135150835','title_evidence','MẶT TIỀN LÊ HỮU TRÁC','frontage_claim',''),
 ('135137167','title_evidence','mặt tiền Ngay Hà Huy Tập','frontage_claim',''),
 ('135170873','title_evidence','MẶT TIỀN ĐƯỜNG LÊ TRUNG ĐÌNH','frontage_claim',''),
 ('135127334','title_evidence','mặt tiền đương ngô xuân thu','frontage_claim',''),
 ('135158835','title_evidence','ngay sát Nguyễn Văn Linh,Cầu Rồng','landmark_claim',''),
 ('135165146','title_evidence','sát mặt tiền giao Nguyễn Văn Linh','landmark_claim',''),
]


def build_params(row, search_street):
    params = lookup.query_params(row)
    if search_street:
        params['street'] = search_street
    return dict(params, viewbox=VIEWBOX, bounded=1)


def classification(row, result):
    # Matching the alley name identifies a road, not its entrance or any house.
    assessment = lookup.assess(dict(row, street_raw=row['search_street']), result)
    lat, lon = float(result['lat']), float(result['lon'])
    inside = 15.93 <= lat <= 16.21 and 108.05 <= lon <= 108.31
    kind = ('alley_reference' if row['clue_kind']=='alley_identifier' else 'street_reference')
    assessment.update(inside_pilot_envelope=inside,
        precision=kind if assessment['precision']=='street_reference' and inside else 'unresolved_candidate',
        exact_house_number_verified=False, reuse_for_ml_verified=False)
    return assessment


def inputs_and_rows():
    original = lookup.ROOT / lookup.load(lookup.ROOT/'latest.json')['run']
    verify(lookup.load(original/'manifest.json')['output_sha256'], base=original)
    prior = lookup.load(lookup.ROOT/'input_manifest.json')
    verify(prior['protected_sha256'])
    review = BASE / prior['source_run']
    source = {r['record_key']:r for r in read(review/'reviewed_80.csv')}
    address_queue = {r['record_key']:r for r in read(lookup.ROOT/'queue.csv')}
    eligible = {r['record_key'] for r in read(original/'candidates_DO_NOT_TRAIN.csv') if r['precision']=='street_reference'}
    rows = []
    for sid, field, snippet, kind, street in CLUES:
        key = 'chotot:' + sid
        row = source[key]
        if key not in eligible or row['v3_cohort']!='train':
            raise ValueError('Pilot must contain only matched-road training IDs: '+key)
        if normalized(snippet) not in normalized(row[field]):
            raise ValueError('Manual clue does not match source: '+key)
        params = build_params(row, street)
        flags = ['no_verified_house_number','no_independent_property_evidence','reuse_rights_unverified']
        if sid=='134925160':
            flags.append('title_uses_Truong_Chinh_spelling_variant_review_required')
        if int(row['shared_pin_distinct_streets'])>1:
            flags.append('source_pin_shared_by_multiple_streets')
        rows.append(dict(record_key=key, v3_cohort='train', street_raw=row['street_raw'],
            ward_raw=row['ward_raw'], district_raw=row['district_raw'], source_field=field,
            literal_clue=snippet, clue_kind=kind, search_street=params['street'],
            params_json=json.dumps(params, ensure_ascii=False, sort_keys=True), query_id=lookup.digest(params),
            source_evidence_ref=row['evidence_ref'], source_snapshot_count=row['source_snapshot_count'],
            source_snapshot_is_independent=False, full_description_available=False,
            property_location_verified=False, model_feature_approved=False, review_flags=';'.join(flags),
            google_maps_url='https://www.google.com/maps/search/?'+urlencode({'api':1,'query':', '.join([params['street'],row['ward_raw'],row['district_raw'],'Đà Nẵng, Việt Nam'])}),
            detail_url=row['detail_url']))
    if len(rows)!=20 or len({r['record_key'] for r in rows})!=20:
        raise ValueError('Expected 20 distinct IDs')
    protected = dict(prior['protected_sha256'])
    for path in [original/'manifest.json', original/'candidates_DO_NOT_TRAIN.csv', lookup.ROOT/'queue.csv',
                 Path(lookup.__file__)]:
        protected[path.relative_to(BASE).as_posix()] = sha(path)
    return rows, protected


def prepare():
    rows, protected = inputs_and_rows()
    ROOT.mkdir(parents=True, exist_ok=True)
    if (ROOT/'input_manifest.json').exists():
        before = lookup.load(ROOT/'input_manifest.json')
        if before['protected_sha256']!=protected or sha(ROOT/'queue.csv')!=before['queue_sha256']:
            raise ValueError('Pilot inputs changed; preserve old run and version explicitly')
        if read(ROOT/'queue.csv') != [{k:str(v) for k,v in r.items()} for r in rows]:
            raise ValueError('Manual review changed; preserve old run and version explicitly')
    else:
        write_csv(ROOT/'queue.csv', rows, list(rows[0]))
        lookup.save(ROOT/'input_manifest.json', dict(created_at_utc=lookup.now(),
            queue_sha256=sha(ROOT/'queue.csv'), protected_sha256=protected, selected_records=20,
            selection='Purposive address clues in matched-road train IDs; not representative, no label-based selection',
            pilot_envelope=VIEWBOX, envelope_is_administrative_boundary=False))
    return read(ROOT/'queue.csv')


def report(rows):
    reports, candidates, cache_hashes = [], [], {}
    old_run = lookup.ROOT / lookup.load(lookup.ROOT/'latest.json')['run']
    old = defaultdict(list)
    for r in read(old_run/'candidates_DO_NOT_TRAIN.csv'):
        old[r['record_key']].append(r)
    for row in rows:
        value = lookup.cached(ROOT, lookup.ENDPOINT, row)
        results = value.get('results', []) if value else []
        found = []
        for rank, result in enumerate(results,1):
            assessment = classification(row,result)
            found.append(assessment)
            candidates.append(dict(record_key=row['record_key'], rank=rank, **assessment,
                evidence_file=lookup.cache_path(ROOT,lookup.ENDPOINT,row['query_id']).relative_to(ROOT).as_posix()))
        if value:
            path = lookup.cache_path(ROOT,lookup.ENDPOINT,row['query_id'])
            cache_hashes[path.relative_to(ROOT).as_posix()] = sha(path)
        state = ('not_requested' if not value else 'service_error' if value['state']!='ok'
                 else 'candidates_returned' if results else 'no_result')
        prior_outside = sum(not(15.93<=float(r['candidate_latitude'])<=16.21 and
                               108.05<=float(r['candidate_longitude'])<=108.31) for r in old[row['record_key']])
        reports.append(dict(row, lookup_state=state,
            old_candidate_rows_outside_pilot_envelope=prior_outside,
            returned_candidates=len(results), alley_reference_count=sum(r['precision']=='alley_reference' for r in found),
            street_reference_count=sum(r['precision']=='street_reference' for r in found),
            final_status='insufficient_property_evidence', exact_house_number_verified=False,
            reuse_for_ml_verified=False, next_evidence='Full listing address and property-specific pin from a permitted source; no road-centre substitute'))
    summary = dict(selected_records=20, cohorts=dict(Counter(r['v3_cohort'] for r in rows)),
        clue_types=dict(Counter(r['clue_kind'] for r in rows)), unique_queries=len({r['query_id'] for r in rows}),
        unique_queries_attempted=len(cache_hashes), lookup_states=dict(Counter(r['lookup_state'] for r in reports)),
        records_with_alley_reference=sum(r['alley_reference_count']>0 for r in reports),
        records_with_street_reference=sum(r['street_reference_count']>0 for r in reports),
        records_with_prior_candidates_outside_envelope=sum(r['old_candidate_rows_outside_pilot_envelope']>0 for r in reports),
        exact_property_locations_verified=0, approved_model_features=0,
        source_full_descriptions_available=0, attribution=lookup.ATTRIBUTION)
    code = lookup.digest(dict(queue=sha(ROOT/'queue.csv'), cache=cache_hashes, code=sha(Path(__file__))))[:16]
    run = ROOT/'runs'/code
    if not run.exists():
        run.mkdir(parents=True)
        write_csv(run/'reviewed_20.csv',reports,list(reports[0]))
        write_csv(run/'candidates_DO_NOT_TRAIN.csv',candidates,list(candidates[0]) if candidates else ['record_key','precision'])
        lookup.save(run/'summary.json', summary)
        table=''.join('<tr><td>'+html.escape(r['record_key'])+'</td><td>'+html.escape(r['literal_clue'])+
            '</td><td>'+html.escape(r['clue_kind'])+'</td><td>'+str(r['alley_reference_count'])+' / '+str(r['street_reference_count'])+
            '</td><td><a target="_blank" rel="noopener noreferrer" href="'+html.escape(r['google_maps_url'],quote=True)+
            '">Google Maps</a> · <a target="_blank" rel="noopener noreferrer" href="'+html.escape(r['detail_url'],quote=True)+
            '">Tin gốc</a></td></tr>' for r in reports)
        (run/'review.html').write_text('<!doctype html><html lang="vi"><meta charset="utf-8"><title>SmartProp — Rà soát 20 địa chỉ</title>'
            '<style>body{font:16px system-ui;margin:32px}table{border-collapse:collapse}td,th{border:1px solid #ddd;padding:10px;text-align:left}</style>'
            '<h1>20 tin — bằng chứng vị trí</h1><p>Tất cả chưa xác minh đúng căn nhà. Số kiệt không phải số nhà; '
            'các điểm đường/kiệt chỉ để tham khảo. Chưa có đặc trưng được duyệt train.</p>'
            '<table><tr><th>ID</th><th>Manh mối nguồn</th><th>Loại manh mối</th><th>Ứng viên kiệt / đường</th><th>Đối chiếu</th></tr>'+
            table+'</table><p>'+html.escape(lookup.ATTRIBUTION)+'</p></html>',encoding='utf-8')
        (run/'README.md').write_text(
            '# Rà soát bằng chứng vị trí 20 tin — 13/10/2026\n\n'
            f'Chọn có chủ đích 20 tin train trong nhóm 63 tin khớp tên đường; không phải mẫu đại diện. '
            f'{summary["unique_queries_attempted"]}/{summary["unique_queries"]} truy vấn OSM/Nominatim đã thử, '
            f'{summary["records_with_alley_reference"]} tin có ứng viên khớp kiệt, '
            f'{summary["records_with_street_reference"]} tin có ứng viên khớp đường. '
            '**0 vị trí căn nhà được xác minh, 0 đặc trưng được duyệt train.**\n\n'
            f'{summary["records_with_prior_candidates_outside_envelope"]}/20 tin có ít nhất một ứng viên lần trước ngoài khung đô thị thử nghiệm. '
            'Tên đường/vùng Đà Nẵng trùng chưa xác minh đúng địa chỉ: Âu Cơ trả cả Hội An, Trường Chinh trả cả Quế Sơn. '
            'Khung 108.05–108.31, 15.93–16.21 thu hẹp truy vấn cho cohort khai báo các quận đô thị cũ; '
            'đây không phải ranh giới hành chính hay bằng chứng nguồn pin đúng. Không có kết quả trong khung không chứng minh đường/nhà không tồn tại.\n\n'
            '## Bằng chứng đã đọc\n\n'
            'Có 3 manh mối số kiệt: 266 Trường Chính (tiêu đề khác cách viết Trường Chinh trong trường đường), '
            '196 Âu Cơ và 59 Trương Chí Cương. Đây là số kiệt, không phải số nhà trong kiệt. '
            'LK4A - 537 là mã lô cần xác minh; không tự đổi thành số nhà 537. '
            'Nguyễn Bỉnh Khiêm giao An Mỹ 3 là lời khai góc/giao đường, không xác định đúng thửa. '
            'Hẻm 3m/kiệt 3M là chiều rộng khai báo; ngang 5m/6m là chiều ngang thửa. '
            'Hòa Minh 21 là tên đường có số, không phải số nhà 21. “Sát mặt tiền” không tự thành mặt tiền.\n\n'
            'CSV và JSONL Chợ Tốt là hai bản lưu cùng API, không phải nguồn độc lập. '
            'Đã kiểm tra trường CSV/JSONL/source_values: không có body/description/địa chỉ cấp tài sản mới. '
            'Nguồn chi tiết từng trả HTTP 403/Cloudflare; không thử vượt chặn hoặc mượn mô tả tin khác. '
            'Không yêu cầu người dùng cung cấp số nhà mà chưa có trong dữ liệu; các tin này giữ trạng thái thiếu bằng chứng.\n\n'
            '[Bảng đối chiếu 20 tin](review.html), [20 kết luận và manh mối nguồn](reviewed_20.csv), [ứng viên đường/kiệt — không train](candidates_DO_NOT_TRAIN.csv), '
            '[số liệu](summary.json). Google Maps chỉ là liên kết tìm địa chỉ, không tải dữ liệu Google.\n\n'
            'Tối thiểu 1,1 giây giữa yêu cầu, một luồng/máy, cache, dừng lỗi; chỉ tinh chỉnh đợt 20 tin này, không chạy định kỳ. '
            f'[Chính sách Nominatim]({lookup.POLICY}). {lookup.ATTRIBUTION}.\n\n'
            'Model v3 vẫn dùng được. Muốn bổ sung vị trí cấp nhà cần nguồn tin có địa chỉ/mô tả đủ cụ thể và quyền sử dụng phù hợp; '
            'tìm đúng đường/kiệt không tạo ra dữ liệu số nhà còn thiếu. Raw, nhãn, split, coordinate_review, model giữ nguyên.\n', encoding='utf-8')
        lookup.save(run/'manifest.json',dict(input_sha256=lookup.load(ROOT/'input_manifest.json')['protected_sha256'],
            queue_sha256=sha(ROOT/'queue.csv'), code_sha256=sha(Path(__file__)),cache_sha256=cache_hashes,
            output_sha256={p.name:sha(p) for p in run.iterdir() if p.is_file()}))
    else:
        verify(lookup.load(run/'manifest.json')['output_sha256'],base=run)
    lookup.save(ROOT/'latest.json',dict(run=run.relative_to(ROOT).as_posix()))
    (ROOT/'README.md').write_text('# Rà soát 20 tin có manh mối vị trí\n\n'
        f'[Báo cáo và kết quả]({run.relative_to(ROOT).as_posix()}/README.md).\n',encoding='utf-8')
    return run,summary


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command',choices=['prepare','fetch','report'])
    args=parser.parse_args()
    rows=prepare()
    last=None
    requests=0
    try:
        if args.command=='fetch':
            for row in rows:
                value=lookup.cached(ROOT,lookup.ENDPOINT,row)
                if value is None:
                    if last is not None:
                        time.sleep(max(0,1.1-(time.monotonic()-last)))
                    last=time.monotonic()
                    requests+=1
                    value=lookup.fetch(json.loads(row['params_json']),lookup.ENDPOINT)
                    lookup.save(lookup.cache_path(ROOT,lookup.ENDPOINT,row['query_id']),value)
                    print(f'{row["record_key"]}: {value["state"]}, {len(value.get("results",[]))} results',flush=True)
                if value['state']!='ok':
                    break
    except KeyboardInterrupt:
        print('Interrupted; completed responses retained for resume.',flush=True)
    finally:
        verify(lookup.load(ROOT/'input_manifest.json')['protected_sha256'])
        run,summary=report(rows)
        lookup.save(ROOT/'verification.json',dict(verified_at_utc=lookup.now(),protected_files_unchanged=True,
            network_requests_this_invocation=requests,run=run.relative_to(ROOT).as_posix()))
        print(json.dumps(summary,ensure_ascii=False,indent=2))
        print(run)


if __name__=='__main__':
    main()
