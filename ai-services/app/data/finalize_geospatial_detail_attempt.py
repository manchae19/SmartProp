"""Freeze an honest per-ID checkpoint after a bounded source-access assessment.

Do not turn a source-level block into 80 individual failed HTTP requests.
"""
import argparse
import hashlib
import json
from collections import Counter
from pathlib import Path

import geospatial_enrichment as geo

ROOT = geo.OUT/'detail_review'


def checkpoint(queue, probes):
    if len(queue)!=80 or len({r['record_key'] for r in queue})!=80:
        raise ValueError('Expected 80 unique candidate IDs')
    keys = {r['record_key'] for r in queue}
    if not probes or not set(probes)<=keys:
        raise ValueError('Probe membership is missing or unexpected')
    for key,meta in probes.items():
        row = next(r for r in queue if r['record_key']==key)
        if meta.get('requested_url')!=row['detail_url']:
            raise ValueError('Probe URL mismatch')
    blocked = next((m for m in probes.values() if m.get('state')=='blocked'),None)
    result = []
    for row in queue:
        meta = probes.get(row['record_key'])
        direct = bool(meta and 'http_status' in meta)
        state = (meta['state'] if meta else
                 'not_requested_source_access_blocked' if blocked else 'not_requested_pending')
        result.append(dict(record_key=row['record_key'],source=row['source'],
            detail_url=row['detail_url'],v3_cohort=row['v3_cohort'],pipeline_group=row['pipeline_group'],
            priority=row['priority'],state=state,individually_requested=direct,
            http_status=meta.get('http_status','') if meta else '',
            response_url=meta.get('response_url','') if meta else '',
            fetched_at_utc=meta.get('fetched_at_utc','') if meta else '',
            detail_sha256=meta.get('sha256','') if meta else '',
            source_block_probe_url=blocked['requested_url'] if blocked else '',
            source_identity_verified=False,detail_description_available=False,
            location_verified=False,model_feature_approved=False,
            note=('Actual individual source probe; no verified listing content extracted.' if direct else
                  'This URL was not requested. Source-level access block; not an individual 403.' if blocked else
                  'This URL was not requested; pending further fetching.')))
    return result


def run(probe_dir):
    input_path = ROOT/'input_manifest.json'
    queue_path = ROOT/'queue.csv'
    inputs = json.loads(input_path.read_text())
    if geo.sha(queue_path)!=inputs['queue_sha256']:
        raise ValueError('Queue changed')
    review = geo.BASE/inputs['source_review_run']
    if geo.sha(review/'manifest.json')!=inputs['source_review_manifest_sha256']:
        raise ValueError('Candidate review changed')
    review_manifest = json.loads((review/'manifest.json').read_text())
    geo.assert_hashes(review_manifest['input_sha256'])
    geo.existing_verified(review,review_manifest['input_sha256'])
    queue = geo.read(queue_path)
    probe_path = probe_dir/'fetch_manifest.json'
    probes = json.loads(probe_path.read_text())
    if not any(m.get('state')=='blocked' for m in probes.values()):
        raise ValueError('No source-level block. Continue detail fetching; do not finalize a blocked report.')
    paths = [Path(__file__),Path(geo.__file__),geo.BASE/'check_pending_sources.py',
             input_path,queue_path,review/'manifest.json',probe_path] + geo.frozen_paths()
    for meta in probes.values():
        if meta.get('file'):
            file = probe_dir/'detail_cache'/meta['file']
            if geo.sha(file)!=meta.get('sha256'):
                raise ValueError('Probe cache SHA mismatch')
            paths.append(file)
    paths += list(probe_dir.glob('*_robots.txt'))
    hashes = geo.hash_inputs(paths)
    code = hashlib.sha256(json.dumps(hashes,sort_keys=True).encode()).hexdigest()[:16]
    out = ROOT/'runs'/code
    if geo.existing_verified(out,hashes):
        geo.write_json(ROOT/'latest.json',{'run':out.relative_to(ROOT).as_posix()})
        return out
    before = geo.artifact_stats()
    results = checkpoint(queue,probes)
    # This stage only freezes source access. It never parses blocked HTML as an ad.
    counts = Counter(r['state'] for r in results)
    summary = dict(created_at=geo.now(),queued_ids=len(queue),priority_1_ids=sum(r['priority']=='1' for r in queue),
        actual_individual_detail_requests=sum(r['individually_requested'] for r in results),
        individual_http_403=sum(r['http_status']==403 for r in results),
        not_individually_requested=sum(not r['individually_requested'] for r in results),
        state_counts=dict(counts),verified_detail_descriptions=0,verified_property_locations=0,
        model_training_performed=False,old_data_and_models_unchanged=True,
        note='Source-level block preserved. Remaining URLs have not been individually checked.')
    out.mkdir(parents=True)
    geo.write_csv(out/'checkpoint.csv',results,list(results[0]))
    geo.write_json(out/'checkpoint.json',{r['record_key']:r for r in results})
    geo.write_json(out/'summary.json',summary)
    (out/'README.md').write_text('# Lấy chi tiết 80 tin: trạng thái truy cập nguồn\n\n'
        f"Hàng chờ {len(queue)} ID, ưu tiên 30 tin có điểm tọa độ dùng với nhiều tên đường. "
        f"Đã gửi {summary['actual_individual_detail_requests']} yêu cầu chi tiết thực tế; "
        f"{summary['individual_http_403']} trả HTTP 403. "
        f"{summary['not_individually_requested']} URL còn lại chưa được yêu cầu, không được báo là 403 riêng từng tin.\n\n"
        'Chưa lấy được mô tả chi tiết đã xác minh hoặc địa chỉ cấp tài sản. '
        'Không dùng nội dung trang chặn làm nội dung tin đăng; không suy tọa độ đúng căn nhà từ tên đường/phường. '
        'Dữ liệu gốc, nhãn, tập giữ riêng, bản làm việc tọa độ và model v3 giữ nguyên.\n\n'
        '- `checkpoint.csv` / `checkpoint.json`: trạng thái chính xác của từng ID, lý do chưa tải và tham chiếu probe.\n'
        '- `summary.json`: số yêu cầu thực tế và số URL chưa kiểm tra.\n'
        '- Mẫu phản hồi HTTP và robots nằm trong thư mục source_access riêng, được ghi SHA-256 trong manifest.\n\n'
        'Chạy lại finalizer cùng probe chỉ xác minh kết quả cũ, không gửi mạng hoặc ghi đè bằng chứng. '
        'Muốn kiểm tra truy cập ở thời điểm khác, tạo thư mục probe mới rồi dùng `--probe-dir`; '
        'không xóa checkpoint cũ. Nếu nguồn cho phép truy cập trở lại, cần lấy phần còn lại và xác minh ID '
        'trước khi trích địa chỉ/mô tả. Checkpoint nguồn bị chặn không có nghĩa tải 80 tin đã hoàn thành.\n\n'
        'Để tiếp tục hiện tại cần nguồn chi tiết có quyền truy cập: bản xuất được phép của nguồn '
        'hoặc bằng chứng người đăng cung cấp. Không bỏ qua chặn truy cập bằng đổi danh tính hoặc giải CAPTCHA. '
        'V3 hiện tại vẫn là mô hình cơ sở đã huấn luyện; chưa có model vị trí mới.\n',encoding='utf-8')
    geo.assert_hashes(hashes)
    if geo.artifact_stats()!=before:
        raise ValueError('Unrelated processed artifacts changed')
    geo.finish(out,hashes,dict(complete=True,source_access_only=True,
        all_80_details_downloaded=False,other_processed_stats_unchanged=True))
    geo.write_json(ROOT/'latest.json',{'run':out.relative_to(ROOT).as_posix()})
    (ROOT/'README.md').write_text('# Chi tiết địa chỉ/kiệt hẻm của 80 tin\n\n'
        f'[Kết quả kiểm tra nguồn và checkpoint]({out.relative_to(ROOT).as_posix()}/README.md).\n\n'
        'Nguồn chặn truy cập: 1 URL được yêu cầu trả 403, 79 URL chưa yêu cầu. '
        'Chưa lấy được 80 mô tả chi tiết. Các kết quả rà soát tiêu đề trước đó giữ nguyên.\n',encoding='utf-8')
    return out


if __name__=='__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--probe-dir',type=Path,default=ROOT/'source_access')
    print(run(parser.parse_args().probe_dir))
