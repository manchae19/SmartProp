"""Review every pending collection row using saved evidence, without altering old runs."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from pathlib import Path
from difflib import SequenceMatcher
from urllib.parse import urlparse

from lxml import html
import audit_all_collected as audit
import expand_collection_audit_scope as scope
import filter_all_collected as pipeline
import review_apartment_labels as detail_parser
from smartprop_geography import norm

BASE = audit.BASE
ROOT = BASE/'processed/pending_collection_review'
SOURCE = BASE/'processed/collection_pipeline/runs/2026-10-11_c0fd2f0b5f3a8a2a'
from collection_review_rules import area, compatible_category, repair, apply_review_rules


def action_for(row, group_size):
    if row['pipeline_status'] == 'eligible':
        return 'passed_rules', 'Qua các quy tắc hiện tại và kiểm tra nhóm; chưa xác minh giao dịch.'
    if row['pipeline_status'] == 'excluded':
        return 'excluded', 'Giữ khỏi huấn luyện; xem exclusion_codes, không xóa dữ liệu gốc.'
    codes = set(filter(None, row['pipeline_review_codes'].split(';')))
    if codes == {'older_than_183_days'} and group_size == 1:
        return 'historical_candidate', 'Chỉ vướng ngưỡng 183 ngày; giữ riêng cho thử nghiệm lịch sử, không coi tin sai.'
    if codes == {'listing_date_unavailable'} and group_size == 1:
        return 'undated_candidate', 'Các quy tắc khác qua; chưa có ngày nguồn, không dùng ngày thu thập thay thế.'
    if 'saved_source_review_pending' in codes:
        return 'previous_source_review_pending', 'Đã xem nguồn trước đây nhưng còn mơ hồ; giữ quyết định chờ và ghi chú.'
    if 'legacy_province_unverified' in codes:
        return 'legacy_source_evidence_missing', 'Chợ Tốt cũ thiếu tỉnh, loại bán, giá nguồn và ngày; cần nguồn có thể truy cập hoặc dữ liệu thay thế.'
    if codes & {'invalid_numeric_target_or_area', 'missing_or_invalid_price', 'missing_or_invalid_area'}:
        return 'price_or_area_unresolved', 'Cần giá tổng/diện tích rõ; không điền thỏa thuận, khoảng giá, giá trả trước hoặc đơn giá thành giá tổng.'
    if codes & {'category_unresolved', 'unsupported_category', 'category_review_pending',
                'source_category_needs_review', 'category_title_inferred', 'category_title_conflict'}:
        return 'category_needs_source', 'Cần danh mục/hiện trạng tài sản từ trang chi tiết; tiêu đề hay URL ảnh chỉ là gợi ý.'
    if codes & {'partial_starting_or_booking_title', 'transaction_or_partial_price_title',
                'title_price_conflict', 'multiple_properties_in_title'}:
        return 'financial_or_multiple_asset_context', 'Cần xác định một tài sản và tổng giá; không suy nhãn từ tiền trả trước hoặc gói nhiều tài sản.'
    if any(c.startswith('group_') or c == 'linked_group_member_not_eligible' for c in codes):
        return 'duplicate_group_needs_review', 'Cần giải quyết mâu thuẫn/đối tượng trong nhóm; không chuyển thành viên holdout vào train.'
    return 'other_evidence_needed', 'Đối chiếu các mã còn lại và bằng chứng nguồn; giữ ngoài train chính.'


def cached_evidence(rows):
    """Read cached page containers for exact IDs; HTTP 200 alone is insufficient."""
    keys = {r['record_key']: r for r in rows}
    evidence = {}
    locations = [BASE/'processed/apartment_review', BASE/'processed/training_source_review', ROOT/'source_access']
    previous = detail_parser.OUT
    try:
        for location in locations:
            path = location/'fetch_manifest.json'
            manifest = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
            for key, meta in manifest.items():
                if key not in keys:
                    continue
                row = keys[key]
                entry = dict(record_key=key, state=meta.get('state', ''), http_status=meta.get('http_status', ''),
                             cache_location=location.relative_to(BASE).as_posix(),
                             detail_sha256=meta.get('sha256', ''),
                             identity_verified=False, description='', flags='')
                if meta.get('state') == 'blocked' or meta.get('http_status') != 200:
                    evidence[key] = entry
                    continue
                file = location/'detail_cache'/meta['file']
                if pipeline.digest(file) != meta['sha256']:
                    raise RuntimeError('Cached body changed: '+str(file))
                if row['source'] in ('cafeland', 'nhadat24h'):
                    detail_parser.OUT = location
                    current, flags = detail_parser.detail(row, meta)
                    entry.update(state=current['state'], identity_verified=current['state']=='identity_verified',
                                 description=current.get('description', ''), flags=';'.join(flags))
                else:
                    root = html.fromstring(file.read_bytes().decode('utf-8', errors='replace'))
                    headings = [' '.join(h.text_content().split()) for h in root.xpath('//h1')]
                    url = meta.get('response_url', '')
                    valid = (urlparse(url).hostname == urlparse(row['detail_url']).hostname and
                             audit.sid_url(row['source'], url) == row['source_listing_id'] and
                             any(SequenceMatcher(None, norm(h), norm(row['title'])).ratio() >= .8 for h in headings))
                    entry.update(state='identity_verified' if valid else 'identity_unverified', identity_verified=valid)
                    descriptions = [x for x in root.iter() if isinstance(x.tag, str) and
                                    (x.get('itemprop') == 'description' or
                                     'description' in (x.get('class') or '').split())]
                    if valid and descriptions:
                        entry['description'] = ' '.join(descriptions[0].text_content().split())
                # Evidence is scoped to property content; do not extract contact numbers.
                entry['description'] = re.split(r'\bChat\b|Thông tin người đăng|Xem thêm từ khóa', entry['description'])[0]
                evidence[key] = entry
    finally:
        detail_parser.OUT = previous
    return list(evidence.values())


def main():
    ROOT.mkdir(parents=True, exist_ok=True)
    protected = [p for p in (BASE/'processed').rglob('*') if p.is_file() and ROOT not in p.parents]
    frozen = {p.relative_to(BASE).as_posix(): pipeline.digest(p) for p in protected}
    paths = [SOURCE/'needs_review.csv', SOURCE/'all_listings.csv', SOURCE/'duplicate_pairs.csv',
             SOURCE/'expanded_audit/all_unique_listings_audit.csv', Path(__file__).resolve()]
    inputs = {p.relative_to(BASE).as_posix(): pipeline.digest(p) for p in paths}
    for relative in ('apartment_review', 'training_source_review', 'pending_collection_review/source_access'):
        location = BASE/'processed'/relative
        inputs.update({p.relative_to(BASE).as_posix(): pipeline.digest(p)
                       for p in location.rglob('*') if p.is_file() and p.suffix in ('.html', '.json', '.csv')})
    for module in (audit, scope, pipeline, detail_parser):
        p = Path(module.__file__)
        inputs[p.relative_to(BASE).as_posix()] = pipeline.digest(p)
    for name in ('build_training_v1.py', 'review_training_categories.py', 'prepare_smartprop_dataset.py',
                 'review_nhadat24h.py', 'smartprop_geography.py', 'collection_review_rules.py'):
        inputs[name] = pipeline.digest(BASE/name)
    token = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    out = ROOT/'runs'/token
    manifest = out/'manifest.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        for relative, sha in saved['output_sha256'].items():
            assert pipeline.digest(BASE/relative) == sha
        publish(out)
        print('Existing pending review verified: '+str(out))
        return
    out.mkdir(parents=True, exist_ok=True)
    before = {r['record_key']: r for r in audit.read(SOURCE/'all_listings.csv')}
    pending = audit.read(SOURCE/'needs_review.csv')
    pending_keys = {r['record_key'] for r in pending}
    assert len(pending_keys) == len(pending) == 5442
    reviews, _ = pipeline.load_reviews()
    rows, normalization, category_rules = [], [], []
    old_date = audit.ASOF
    audit.ASOF = audit.date.fromisoformat(json.loads((SOURCE/'summary.json').read_text(encoding='utf-8'))['as_of'])
    try:
        for original in audit.read(SOURCE/'expanded_audit/all_unique_listings_audit.csv'):
            key = original['record_key']
            normalized = original
            if key in pending_keys:
                normalized, changes = repair(original)
                normalization.extend(changes)
            row = pipeline.classify(normalized, reviews.get(key))
            if key in pending_keys:
                row, rule = apply_review_rules(row, normalized)
                if rule:
                    category_rules.append(dict(record_key=key, rule=rule, category=row['category'],
                                               source_category=json.loads(normalized['raw_json']).get('source_category', '')))
            row.update(raw_json=original['raw_json'],
                       original_price_million=original['price_million'],
                       original_area_sqm=original['area_sqm'])
            rows.append(row)
    finally:
        audit.ASOF = old_date
    reservation, bridges = pipeline.frozen_groups()
    # Preserve the preceding run's bridges while checking repaired numeric labels.
    pairs = pipeline.finish_groups(rows, audit.read(SOURCE/'duplicate_pairs.csv')+bridges, reservation)
    groups = Counter(r['pipeline_group'] for r in rows)
    changes = []
    reviewed = []
    changes_by_key = defaultdict(list)
    for c in normalization:
        changes_by_key[c['record_key']].append(c['field'])
    rules_by_key = {c['record_key']:c['rule'] for c in category_rules}
    for r in rows:
        prior = before[r['record_key']]
        r.update(previous_pipeline_status=prior['pipeline_status'], previous_pipeline_review_codes=prior['pipeline_review_codes'],
                 normalization_fields=';'.join(changes_by_key[r['record_key']]),
                 additional_category_rule=rules_by_key.get(r['record_key'], ''),
                 reviewed_in_this_batch=r['record_key'] in pending_keys,
                 group_size=groups[r['pipeline_group']])
        action, note = action_for(r, r['group_size'])
        r.update(review_outcome=action, next_action=note)
        if r['record_key'] in pending_keys:
            reviewed.append(r)
        changed = [f for f in ('pipeline_status', 'price_million', 'area_sqm', 'category', 'pipeline_review_codes')
                   if str(prior[f]) != str(r[f]) and not (
                       f in ('price_million', 'area_sqm') and audit.number(prior[f]) == audit.number(r[f]))]
        if changed:
            changes.append(dict(record_key=r['record_key'], fields=';'.join(changed),
                                previous_status=prior['pipeline_status'], status=r['pipeline_status'],
                                previous_codes=prior['pipeline_review_codes'], codes=r['pipeline_review_codes']))
    fields = list(rows[0])
    audit.save_csv(out/'all_listings_after_review.csv', rows, fields)
    audit.save_csv(out/'reviewed_pending.csv', reviewed, fields)
    for name in ('eligible', 'needs_review', 'excluded'):
        audit.save_csv(out/(name+'.csv'), [r for r in rows if r['pipeline_status'] == name], fields)
    for action in ('historical_candidate', 'undated_candidate'):
        audit.save_csv(out/(action+'s.csv'), [r for r in reviewed if r['review_outcome'] == action], fields)
    queue = [r for r in reviewed if r['pipeline_status'] == 'needs_review' and
             r['review_outcome'] not in ('historical_candidate', 'undated_candidate')]
    audit.save_csv(out/'source_check_queue.csv', queue, fields)
    train = [r for r in rows if r['training_allowed']]
    audit.save_csv(out/'train_candidates.csv', train, fields)
    audit.save_csv(out/'normalization_changes.csv', normalization,
                   ['record_key', 'field', 'previous', 'value', 'source_field', 'source_text', 'rule'])
    audit.save_csv(out/'category_resolutions.csv', category_rules, ['record_key', 'rule', 'category', 'source_category'])
    audit.save_csv(out/'status_and_label_changes.csv', changes,
                   ['record_key', 'fields', 'previous_status', 'status', 'previous_codes', 'codes'])
    audit.save_csv(out/'duplicate_pairs.csv', pairs, ['left', 'right', 'rule', 'title_similarity'])
    evidence = cached_evidence(pending)
    audit.save_csv(out/'cached_detail_evidence.csv', evidence,
                   ['record_key', 'state', 'http_status', 'cache_location', 'detail_sha256',
                    'identity_verified', 'description', 'flags'])
    assert len(reviewed) == len({r['record_key'] for r in reviewed}) == 5442
    assert len(rows) == len({r['record_key'] for r in rows}) == 8509
    assert not any(r['protected_holdout'] for r in train)
    assert all(pipeline.digest(BASE/relative) == sha for relative, sha in frozen.items())
    assert all(pipeline.digest(BASE/relative) == sha for relative, sha in inputs.items())
    summary = dict(reviewed_pending=len(reviewed), original_total=len(rows),
                   pending_after_status=dict(Counter(r['pipeline_status'] for r in reviewed)),
                   outcomes=dict(Counter(r['review_outcome'] for r in reviewed)),
                   full_collection_status=dict(Counter(r['pipeline_status'] for r in rows)),
                   by_source={s:dict(Counter(r['review_outcome'] for r in reviewed if r['source']==s))
                              for s in sorted({r['source'] for r in reviewed})},
                   normalized_fields=dict(Counter(r['field'] for r in normalization)),
                   normalized_records=len({r['record_key'] for r in normalization}),
                   category_resolutions=len(category_rules), train_candidates=len(train),
                   affected_previous_nonpending=[r['record_key'] for r in rows
                       if r['record_key'] not in pending_keys and r['pipeline_status'] != before[r['record_key']]['pipeline_status']],
                   source_queue=len(queue), cached_detail_states=dict(Counter(r['state'] for r in evidence)),
                   cached_detail_rows=len(evidence), new_source_probe_requests=5,
                   raw_and_previous_artifacts_unchanged=True, test_replaced=False, model_trained=False,
                   all_urls_refetched=False)
    (out/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    report(out, summary)
    manifest.write_text(json.dumps(dict(input_sha256=inputs, protected_sha256=frozen,
                        output_sha256={p.relative_to(BASE).as_posix(): pipeline.digest(p)
                                       for p in out.rglob('*') if p.is_file()}), indent=2), encoding='utf-8')
    publish(out)
    print(json.dumps(summary, ensure_ascii=False, indent=2))


def report(out, s):
    lines = ['# Rà soát toàn bộ 5.442 tin đang chờ', '',
             '**Đã kiểm tra mọi hàng trong nhóm chờ bằng dữ liệu đã lưu. Chưa mở lại toàn bộ 5.442 URL.** '
             'Giá là giá rao, không phải giá giao dịch đã xác minh.', '',
             '| Kết quả không chồng lặp của nhóm 5.442 | Số tin |', '|---|---:|']
    labels = dict(passed_rules='Qua lọc sau rà soát', excluded='Loại khỏi tập huấn luyện / nghi trùng',
                  historical_candidate='Chỉ cũ hơn ngưỡng 183 ngày, giữ riêng',
                  undated_candidate='Chỉ thiếu ngày, giữ riêng',
                  legacy_source_evidence_missing='Chợ Tốt cũ thiếu bằng chứng nguồn',
                  category_needs_source='Cần nguồn để chốt loại bất động sản',
                  price_or_area_unresolved='Chưa chốt được giá tổng hoặc diện tích',
                  financial_or_multiple_asset_context='Giá có điều kiện / nhiều tài sản',
                  duplicate_group_needs_review='Nhóm nghi trùng còn vướng',
                  previous_source_review_pending='Đã duyệt nguồn trước đây, vẫn chờ',
                  other_evidence_needed='Cần bằng chứng cho các cờ còn lại')
    for name, n in s['outcomes'].items():
        lines.append(f'| {labels[name]} | {n:,} |')
    lines += ['', f'Khôi phục giá số từ chuỗi giá đầy đủ: **{s["normalized_fields"].get("price_million",0):,} tin**; '
              f'diện tích từ chuỗi m²: **{s["normalized_fields"].get("area_sqm",0):,} tin**. '
              f'Có {s["normalized_records"]:,} ID được bổ sung ít nhất một trường. '
              'Chỉ phân tích chuỗi nguồn, không suy nhãn từ mô hình, đơn giá, khoảng giá hoặc tiền trả trước.', '',
              f'Phân giải {s["category_resolutions"]} cờ loại bằng danh mục nguồn cụ thể khi không có tín hiệu đối tượng đối lập. '
              'Danh mục nhà đất tổng hợp, đất có nhà, quảng cáo nhiều tài sản vẫn giữ chờ.', '',
              '## Đọc các nhóm kết quả', '',
              '- `passed_rules`: qua các quy tắc và nhóm sau rà soát; vẫn chưa xác minh độc lập toàn bộ mô tả.',
              '- `excluded`: loại rõ từ danh mục thương mại/lưu trú/nông nghiệp hoặc giữ đại diện nghi trùng khỏi train. Không xóa raw.',
              '- `historical_candidate`: chỉ vướng ngưỡng 183 ngày và nhóm đơn; giữ cho thử nghiệm lịch sử, không kết luận nhãn sai.',
              '- `undated_candidate`: chỉ thiếu ngày và nhóm đơn; giữ riêng, không tự coi ngày thu thập là ngày đăng.',
              '- Những nhóm còn lại: xem `next_action` và các mã lý do từng tin trong `reviewed_pending.csv`.', '',
              '## Bằng chứng và truy cập nguồn', '',
              f'Đọc lại {s["cached_detail_rows"]} trang/cache liên quan tới nhóm chờ: {s["cached_detail_states"]}. '
              'Quyết định chờ trước đây vẫn giữ nguyên. Không coi HTTP 200 là đúng danh tính hoặc nhãn sạch.',
              'Thử 1 URL/nguồn: CafeLand, Nhadat24h, Homedy và Alonhadat trả HTTP 200; Chợ Tốt chuyển sang nhatot.com và trả 403. '
              'Đây chỉ là kiểm tra khả năng truy cập mẫu, không phải kết quả tất cả URL. Không vượt chặn truy cập.',
              'Trang Homedy mẫu không có trường ngày đăng trong vùng nội dung đã kiểm tra; không lấy ngày ảnh, ngày thành lập website hoặc ngày trang liên quan làm ngày tin.', '',
              '## Kết quả toàn bộ bộ sưu tập sau rà soát', '',
              f'{s["full_collection_status"]}. **{s["train_candidates"]:,} ứng viên được phép xét cho train mới**, '
              'không thay thế training_v2. Các tập cũ, 137 tin test, raw và quyết định duyệt giữ nguyên.', '',
              f'Có {len(s["affected_previous_nonpending"])} tin vốn không nằm trong nhóm chờ đổi trạng thái sau khi kiểm tra lại các cầu nối/giá trị mới. '
              'Xem `status_and_label_changes.csv`; không âm thầm sửa tập cũ.', '',
              '## Tệp sử dụng', '',
              '- [reviewed_pending.csv](reviewed_pending.csv): đủ 5.442 ID, trạng thái trước/sau, nhãn, lý do và hướng xử lý.',
              '- [normalization_changes.csv](normalization_changes.csv): từng giá trị khôi phục và chuỗi gốc.',
              '- [source_check_queue.csv](source_check_queue.csv): các tin còn cần bằng chứng chi tiết.',
              '- [historical_candidates.csv](historical_candidates.csv), [undated_candidates.csv](undated_candidates.csv): nhóm thử nghiệm riêng, không trộn train chính.',
              '- [all_listings_after_review.csv](all_listings_after_review.csv): kết quả đủ 8.509 ID; raw_json giữ literal dữ liệu gốc.',
              '- `eligible.csv`, `needs_review.csv`, `excluded.csv`, `train_candidates.csv`: các tập sau rà soát có dấu vết nhóm/holdout.',
              '- `cached_detail_evidence.csv`, `category_resolutions.csv`, `summary.json`, `manifest.json`: bằng chứng và hash.', '',
              'Chạy lại:', '', '```powershell',
              '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/review_pending_collection.py',
              '```', '', 'Cùng đầu vào dùng bản chạy đã xác minh hash; có thay đổi tạo bản chạy mới. Không huấn luyện mô hình trong bước này.', '']
    (out/'README.md').write_text('\n'.join(lines), encoding='utf-8')


def publish(out):
    relative = out.relative_to(ROOT).as_posix()
    (ROOT/'latest.json').write_text(json.dumps(dict(run=relative), indent=2), encoding='utf-8')
    (ROOT/'README.md').write_text('# Rà soát nhóm chờ SmartProp\n\n'
                                 f'[Kết quả mới nhất]({relative}/README.md).\n', encoding='utf-8')


if __name__ == '__main__':
    main()
