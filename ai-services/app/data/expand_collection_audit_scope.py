"""Re-screen the saved collection audit for old/new Da Nang; preserve raw and old audit."""
import hashlib
import json
import re
from collections import Counter
from audit_all_collected import BASE, OUT as ORIGINAL, read, save_csv
from smartprop_geography import norm

OUT = BASE / 'processed/full_collection_audit_expanded'
REFERENCE = 'https://baochinhphu.vn/nghi-quyet-cua-quoc-hoi-ve-sap-xep-don-vi-hanh-chinh-cap-tinh-102250612191145158.htm'


def geographic_scope(row):
    # Province must be the final address component, never a street/title substring.
    tail = norm(row['address_raw'].rsplit(',', 1)[-1])
    tail = re.sub(r'^(?:thanh pho|tp\.?|tinh)\s+', '', tail)
    if tail == 'da nang':
        return 'accepted_address', 'explicit_da_nang_address'
    if tail == 'quang nam':
        return 'accepted_address', 'explicit_former_quang_nam_address'
    if row['location_basis'] == 'legacy_filename_and_district_unverified':
        return 'unverified', 'legacy_filename_only'
    if row['location_basis'] in ['source_region_and_district', 'source_province_flag_and_historical_district']:
        return 'accepted_source_region', row['location_basis']
    return 'outside_or_unverified', 'no_accepted_province_evidence'


def rescreen(row):
    row = dict(row)
    scope, basis = geographic_scope(row)
    accepted = scope.startswith('accepted_')
    original_flags = set(filter(None, row['review_codes'].split(';')))
    flags = set(original_flags)
    # A historical district is optional under the expanded scope. Preserve it as metadata.
    flags.discard('historical_district_unresolved')
    flags.discard('outside_or_unverified_old_danang')
    if accepted:
        flags.discard('source_region_needs_review')
    elif scope == 'outside_or_unverified':
        flags.add('outside_or_unverified_expanded_danang')
    # Do not clear legacy evidence gaps, price/area flags or prior review decisions.
    decision = row['prior_review_decision']
    if decision in ['pending', 'exclude']:
        status = 'prior_' + decision
    elif decision in ['correct', 'keep']:
        status = 'prior_reviewed_' + decision
    elif 'outside_or_unverified_expanded_danang' in flags:
        status = 'outside_or_unverified_scope'
    elif {'outside_model_property_types', 'special_or_whole_building'} & flags:
        status = 'other_property_or_building'
    elif flags - {'listing_date_unavailable'}:
        status = 'needs_review'
    elif not row['displayed_date']:
        status = 'screened_date_unknown'
    else:
        status = 'screened_candidate_unverified'
    row.update(previous_status=row['status'], previous_review_codes=row['review_codes'],
               geographic_scope_status=scope, geographic_scope_basis=basis,
               historical_district_status='resolved' if row['district'] else 'unresolved_optional',
               waived_scope_review_codes=';'.join(sorted(original_flags - flags)),
               status=status, review_codes=';'.join(sorted(flags)), review_flag_count=len(flags))
    return row


def main():
    old_summary = json.loads((ORIGINAL / 'summary.json').read_text(encoding='utf-8'))
    # Reject a stale original audit, rather than silently presenting old counts as current.
    for relative, digest in old_summary['input_sha256'].items():
        if hashlib.sha256((BASE / relative).read_bytes()).hexdigest() != digest:
            raise RuntimeError('Source changed; run audit_all_collected.py first: ' + relative)
    inputs = [ORIGINAL / 'summary.json', ORIGINAL / 'all_unique_listings_audit.csv']
    frozen = {p: hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    rows = [rescreen(r) for r in read(inputs[1])]
    OUT.mkdir(parents=True, exist_ok=True)
    fields = list(rows[0])
    save_csv(OUT / 'all_unique_listings_audit.csv', rows, fields)
    screened = [r for r in rows if r['status'] in ['screened_candidate_unverified', 'screened_date_unknown']]
    need = [r for r in rows if r['status'] not in ['screened_candidate_unverified', 'screened_date_unknown', 'prior_reviewed_correct', 'prior_reviewed_keep']]
    changed = [r for r in rows if r['status'] != r['previous_status']]
    save_csv(OUT / 'screened_candidates_unverified.csv', screened, fields)
    save_csv(OUT / 'needs_review.csv', need, fields)
    save_csv(OUT / 'status_changes.csv', changed, fields)
    summary = dict(as_of=old_summary['as_of'], geographic_scope='Old Da Nang plus former Quang Nam (new Da Nang)',
                   reference=REFERENCE, unique_source_ids=len(rows), screened_candidates=len(screened),
                   needs_review=len(need), statuses=dict(Counter(r['status'] for r in rows)),
                   geographic_evidence=dict(Counter(r['geographic_scope_status'] for r in rows)),
                   historical_district_unresolved_optional=sum(not r['district'] for r in rows),
                   changed_status_records=len(changed),
                   status_transitions=dict(Counter(r['previous_status']+' -> '+r['status'] for r in changed)),
                   by_source={s:dict(Counter(r['status'] for r in rows if r['source']==s)) for s in sorted({r['source'] for r in rows})},
                   issue_counts=dict(Counter(f for r in rows for f in r['review_codes'].split(';') if f)),
                   original_summary='processed/full_collection_audit/summary.json',
                   original_audit_sha256={p.name:h for p,h in frozen.items()},
                   raw_input_hashes_unchanged=all(hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h for p,h in old_summary['input_sha256'].items()))
    assert len({r['record_key'] for r in rows}) == len(rows)
    assert sum(summary['statuses'].values()) == len(rows)
    assert summary['raw_input_hashes_unchanged']
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in frozen.items())
    (OUT / 'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# Rà soát toàn bộ dữ liệu — chấp nhận Đà Nẵng cũ và mới', '',
             'Phạm vi theo yêu cầu: toàn bộ Đà Nẵng cũ và địa bàn Quảng Nam cũ thuộc Đà Nẵng mới. '
             f'Căn cứ sáp nhập: [Nghị quyết 202/2025/QH15]({REFERENCE}).', '',
             f'Đối chiếu dữ liệu ngày {summary["as_of"]}. Tổng **{len(rows):,} ID nguồn Việt Nam**, '
             f'**{len(screened):,} ứng viên qua quy tắc**, **{len(need):,} tin cần xử lý**, '
             'và 17 tin đã duyệt giữ/sửa từ đợt căn hộ trước. Ứng viên chưa phải dữ liệu đã xác minh sạch.', '',
             f'Có **{len(changed):,} tin đổi trạng thái** khi mở rộng phạm vi. Không còn bắt buộc gán một quận/huyện cũ. '
             'Cột `district` và `district_candidates` giữ nguyên; không ép Hội An, Điện Bàn hoặc phường giao ranh vào một quận cũ.', '',
             '| Trạng thái | Số tin |', '|---|---:|']
    for status,count in summary['statuses'].items(): lines.append(f'| {status} | {count:,} |')
    lines += ['', '| Thay đổi | Số tin |', '|---|---:|']
    for transition,count in summary['status_transitions'].items(): lines.append(f'| {transition} | {count:,} |')
    lines += ['', '## Cách xét địa bàn', '',
              '- Chấp nhận thành phần tỉnh/thành cuối địa chỉ là Đà Nẵng hoặc Quảng Nam; tên đường chứa “Quảng Nam” không đủ bằng chứng.',
              '- Chấp nhận trường tỉnh nguồn đã có bằng chứng trong audit cũ. Tin Chợ Tốt cũ chỉ có tên file và nhãn quận vẫn cần xác minh tỉnh.',
              '- Cờ chưa gán quận cũ được chuyển thành thông tin tùy chọn. Cờ phạm vi cũ được bỏ; cờ vùng từ crawler chỉ bỏ khi địa chỉ chứng minh thuộc phạm vi mới.',
              '- Giữ các cờ giá, diện tích, loại giao dịch, ngày, nội dung, trùng lặp và quyết định duyệt căn hộ trước. Tin ở tỉnh khác vẫn cần cách ly khỏi tập ứng viên.',
              '- Bốn cờ tọa độ từ audit cũ thuộc các tin gắn quận cũ; vẫn giữ để kiểm tra vị trí. Chưa kiểm tra ranh giới tọa độ của toàn bộ thành phố mới và chưa xác minh địa chỉ thực địa.', '',
              '## Tệp kết quả', '',
              '- `all_unique_listings_audit.csv`: mọi ID, địa bàn mới và trạng thái cũ để đối chiếu.',
              '- `screened_candidates_unverified.csv`: ứng viên qua quy tắc, gồm tin thiếu ngày được đánh dấu riêng.',
              '- `needs_review.csv`: các tin còn cần xử lý, gồm tin chờ/loại từ quyết định trước.',
              '- `status_changes.csv`: các tin đổi trạng thái; `waived_scope_review_codes` ghi rõ cờ được bỏ.',
              '- `summary.json`: tổng hợp và hash đầu vào.', '',
              'Kiểm kê snapshot, kiểm tra Singapore và danh sách nghi trùng vẫn ở [audit gốc](../full_collection_audit/README.md). '
              'Nhóm nghi trùng cũ chỉ so theo quận/loại và chưa bao phủ đầy đủ các địa bàn mới; không coi là đã loại trùng bất động sản. '
              'Singapore giữ riêng, không cộng vào số tin Việt Nam. Không truy cập lại URL, không sửa raw, không huấn luyện lại hoặc đổi tập test.', '',
              'Chạy lại sau khi audit gốc đã cập nhật:', '', '```powershell',
              '.\\ai-services\\.venv\\Scripts\\python.exe ai-services/app/data/expand_collection_audit_scope.py', '```', '']
    (OUT / 'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    main()
