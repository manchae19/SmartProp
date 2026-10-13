"""One offline, source-aware collection pipeline. Never modifies existing datasets."""
import argparse
import contextlib
import hashlib
import json
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import audit_all_collected as audit
import expand_collection_audit_scope as expanded
from build_training_v1 import extra_checks, group_records, split_for
from review_training_categories import decide as category_decision
from smartprop_geography import norm
from collection_review_rules import repair, apply_review_rules

BASE = audit.BASE
PROCESSED = BASE / 'processed'
OUT = PROCESSED / 'collection_pipeline'
REVIEW_SPECS = [
    ('apartment_v2/review_decisions.csv', 'apartment_review/detail_cache',
     'apartment_v2/review_queue_before.csv'),
    ('training_source_review/review_decisions.csv', 'training_source_review/detail_cache', None),
]
SOURCE_REVIEW_MANIFEST = PROCESSED/'collection_source_review/review_manifest.json'
if SOURCE_REVIEW_MANIFEST.exists():
    REVIEW_SPECS.append(('collection_source_review/review_decisions.csv',
                         'collection_source_review/detail_cache', None))
# Automatic detail checks resolve only the fields they explicitly verify.
# Financial context, special assets, dates, sale/geography and numeric gates stay.
DETAIL_RESOLVABLE_CODES = {
    'category_title_inferred', 'category_unresolved', 'unsupported_category', 'outside_model_property_types',
    'source_category_needs_review', 'category_review_pending', 'category_title_conflict',
    'land_title_house_label',
    'source_price_needs_review', 'source_area_needs_review', 'source_price_unit_review',
    'price_raw_not_confirmed_total', 'detail_price_raw_not_confirmed_total',
    'price_text_non_total_or_unparsed', 'detail_price_unparsed', 'area_text_unparsed',
}
# Only content/label issues covered by the saved source review may be waived.
# Identity, geography, transaction fields, dates and current numeric gates remain.
CONTENT_CODES = {
    'partial_starting_or_booking_title', 'title_price_conflict',
    'apartment_price_priority', 'source_price_needs_review',
    'source_area_needs_review', 'source_price_unit_review',
    'source_review_reason', 'source_review_flags', 'price_parse_mismatch',
    'area_parse_mismatch', 'listing_detail_price_conflict',
    'price_text_non_total_or_unparsed', 'detail_price_unparsed',
    'area_text_unparsed', 'category_title_conflict', 'category_title_inferred',
    'source_category_needs_review', 'price_raw_not_confirmed_total',
    'detail_price_raw_not_confirmed_total', 'multiple_properties_in_title',
    'transaction_or_partial_price_title', 'land_title_house_label',
    'multiple_different_total_prices_in_title',
}
_DIGEST_CACHE = {}


def digest(path):
    # Large, immutable detail snapshots otherwise get reread for protection,
    # dependencies, reviews and final checks. Rehash whenever file metadata changes.
    path=path.resolve()
    stat=path.stat()
    token=(stat.st_size,stat.st_mtime_ns,stat.st_ctime_ns,stat.st_ino)
    saved=_DIGEST_CACHE.get(path)
    if saved and saved[0]==token:
        return saved[1]
    value=hashlib.sha256(path.read_bytes()).hexdigest()
    after=path.stat()
    if token!=(after.st_size,after.st_mtime_ns,after.st_ctime_ns,after.st_ino):
        raise RuntimeError('Input changed while hashing: '+str(path))
    _DIGEST_CACHE[path]=(token,value)
    return value


def raw_paths():
    return sorted(set(BASE.glob('*.csv')) | set((BASE/'data_raw').rglob('*.csv')) |
                  set((BASE/'data_raw').rglob('*.jsonl')) | set((BASE/'sample').glob('*.csv')) |
                  set((BASE/'crawler_cafeland/sample').glob('*.csv')))


def records(path):
    return audit.read(path) if path.exists() else []


def load_reviews():
    """Validate cached evidence and retain every decision, including stale ones."""
    result, history = {}, []
    if SOURCE_REVIEW_MANIFEST.exists():
        saved=json.loads(SOURCE_REVIEW_MANIFEST.read_text(encoding='utf-8'))
        if not saved.get('complete'):
            raise RuntimeError('Source review is not finalized')
        for relative, expected in saved['output_sha256'].items():
            if digest(BASE/relative)!=expected:
                raise RuntimeError('Frozen source evidence changed: '+relative)
    for relative, cache, originals in REVIEW_SPECS:
        old = {r['record_key']: r for r in records(PROCESSED/originals)} if originals else {}
        for r in records(PROCESSED/relative):
            r = dict(r, decision_file=relative)
            snapshot = PROCESSED/cache/(r['record_key'].replace(':', '_')+'.html')
            r['cache_valid'] = bool(snapshot.exists() and r.get('detail_sha256') and
                                    digest(snapshot) == r['detail_sha256'])
            previous = old.get(r['record_key'], {})
            for field in ('price_million', 'area_sqm'):
                r.setdefault('original_'+field, previous.get(field, ''))
            history.append(r)
            # A newer, explicit source review supersedes the earlier review.
            result[r['record_key']] = r
    return result, history


def classify(row, review=None):
    r = dict(row)
    flags = set(filter(None, r['review_codes'].split(';'))) | set(extra_checks(r))
    r.update(original_price_million=r['price_million'], original_area_sqm=r['area_sqm'],
             original_category=r['category'],
             review_decision='', review_decision_file='', review_note='',
             review_evidence_sha256='', resolved_review_codes='',
             category_review_decision='', category_review_rule='',
             label_quality='automatically_screened_unverified',
             location_feature=r['district'] or 'new_unit:'+norm(r['address_raw'].split(',')[0]))
    resolved = set()
    reviewed = False
    excluded = set()
    if review:
        automatic_detail=review.get('reviewer')=='source_detail_rules_not_manual_verification'
        r.update(review_decision=review['decision'], review_decision_file=review['decision_file'],
                 review_note=review.get('note', ''), review_evidence_sha256=review.get('detail_sha256', ''))
        stale = not review['cache_valid'] or any(
            audit.number(review.get('original_'+f)) is not None and
            audit.number(review.get('original_'+f)) != audit.number(r[f])
            for f in ('price_million', 'area_sqm'))
        if automatic_detail and review['decision']=='pending' and not review.get('detail_sha256'):
            flags.add('source_detail_not_verified')
        elif stale:
            flags.add('saved_review_evidence_stale_or_missing')
        elif review['decision'] == 'exclude':
            excluded.add('saved_source_review_exclude')
        elif review['decision'] == 'pending':
            flags.add('saved_source_review_pending')
        elif review['decision'] in ('keep', 'correct'):
            if automatic_detail and (review.get('category_evidence_validated')!='True' or
                                     review.get('source_identity_verified')!='True' or
                                     review.get('review_codes')):
                raise RuntimeError('Automatic approval lacks complete evidence: '+r['record_key'])
            reviewed = True
            if automatic_detail:
                category=review.get('reviewed_category')
                if category not in audit.CATEGORIES:
                    raise RuntimeError('Unsupported source-reviewed category: '+r['record_key'])
                r.update(category=category, category_basis='identity_verified_source_detail',
                         category_review_decision=review['decision'],
                         category_review_rule='explicit_current_source_category_and_content')
            for field in ('price_million', 'area_sqm'):
                if review['decision'] == 'correct' and review.get(field):
                    r[field] = audit.number(review[field])
            r['label_quality'] = 'saved_source_review_not_independent_transaction_verification'
            allowed_codes=DETAIL_RESOLVABLE_CODES if automatic_detail else CONTENT_CODES
            if automatic_detail and r['category']!='Căn hộ chung cư':
                allowed_codes=allowed_codes | {'apartment_price_priority'}
            resolved = flags & allowed_codes
            flags -= resolved
            if (automatic_detail and r['category']=='Căn hộ chung cư' and
                    (float(r['price_million'])<500 or not 15<=float(r['price_million'])/float(r['area_sqm'])<=150)):
                flags.add('apartment_price_priority')
    # Apply category rules to all relevant records, not only the old 434-row queue.
    if 'source_category_needs_review' in flags and not reviewed:
        d, cat, rule, note = category_decision(r)
        r.update(category_review_decision=d, category_review_rule=rule)
        if d == 'keep' and cat == r['category']:
            flags.remove('source_category_needs_review')
            resolved.add('source_category_needs_review')
        elif d == 'exclude':
            excluded.add('unsupported_property_category_rule')
        else:
            flags.add('category_review_pending')
    p, a = audit.number(r['price_million']), audit.number(r['area_sqm'])
    r['price_per_sqm_million'] = p/a if p is not None and a and a > 0 else ''
    if p is None or a is None or p <= 0 or a <= 0:
        flags.add('invalid_numeric_target_or_area')
    elif not (100 <= p <= 200000 and 20 <= a <= 1000 and 2 <= p/a <= 300):
        flags.add('numeric_threshold')
    # Missing/old dates are review gates, never replaced by collection time.
    if not r['displayed_date']:
        flags.add('listing_date_unavailable')
    tail = re.sub(r'^(?:thanh pho|tp\.?|tinh)\s+', '', norm(r['address_raw'].rsplit(',', 1)[-1]))
    if (r['geographic_scope_status'] == 'outside_or_unverified' and
            tail in {'ha noi', 'ho chi minh', 'binh duong', 'dong nai', 'khanh hoa',
                     'can tho', 'long an', 'ba ria vung tau', 'binh dinh', 'hue',
                     'thua thien hue', 'quang ngai', 'quang tri'}):
        excluded.add('explicit_outside_da_nang_address')
    if r['category'] == 'Khác' and r['category_basis'] == 'source_category':
        excluded.add('outside_model_property_types')
    if 'rental_title_in_sale_collection' in flags:
        excluded.add('explicit_rental_title')
    r.update(pipeline_status='excluded' if excluded else 'needs_review' if flags else 'eligible',
             pipeline_review_codes=';'.join(sorted(flags)),
             exclusion_codes=';'.join(sorted(excluded)),
             resolved_review_codes=';'.join(sorted(resolved)), representative_key='')
    return r


def frozen_groups():
    """Retain original group bridges and reserve every old holdout ID."""
    assignments = records(PROCESSED/'training_v1/all_collection_group_assignments.csv')
    reservation = defaultdict(set)
    groups = defaultdict(list)
    for r in assignments:
        reservation[r['record_key']].add(r['model_split'])
        groups['v1:'+r['duplicate_candidate_group']].append(r['record_key'])
    # Include the apartment experiments predating the full-collection split.
    for relative in ('smartprop_review/baseline_inputs.csv', 'apartment_v2/baseline_inputs.csv',
                     'training_v1/main_dataset.csv', 'training_v2/main_dataset.csv'):
        for r in records(PROCESSED/relative):
            reservation[r['record_key']].add(r['model_split'])
            groups[relative+':'+r['duplicate_candidate_group']].append(r['record_key'])
    pairs = [dict(left=keys[0], right=k, rule='frozen_group_bridge', title_similarity=1)
             for keys in groups.values() for k in keys[1:] if k != keys[0]]
    # The source review discovered this physical-property link beyond title rules.
    pairs.append(dict(left='nhadat24h:4382420', right='nhadat24h:4385371',
                      rule='saved_description_duplicate', title_similarity=1))
    return reservation, pairs


def finish_groups(rows, pairs, reservations):
    membership, links = group_records(rows, pairs)
    groups = defaultdict(list)
    for r in rows:
        r['pipeline_group'] = membership[r['record_key']]
        groups[r['pipeline_group']].append(r)
    for gid, members in groups.items():
        splits = set().union(*(reservations.get(r['record_key'], set()) for r in members))
        holdout = bool(splits & {'validation', 'test'})
        split = 'reserved_holdout' if holdout else 'train' if splits == {'train'} else split_for(gid)
        issues = set()
        values = [r for r in members if audit.number(r['price_million']) and audit.number(r['area_sqm'])]
        for field, tolerance in (('price_million', .05), ('area_sqm', .01)):
            numbers = [float(r[field]) for r in values]
            if numbers and max(numbers) > 0 and (max(numbers)-min(numbers))/max(numbers) > tolerance:
                issues.add('group_'+field+'_conflict')
        if len({r['category'] for r in members}) > 1:
            issues.add('group_category_conflict')
        if len({r['district'] for r in members if r['district']}) > 1:
            issues.add('group_historical_location_conflict')
        if len(members) > 1 and any(r['pipeline_status'] != 'eligible' for r in members):
            issues.add('linked_group_member_not_eligible')
        for r in members:
            r.update(reserved_splits=';'.join(sorted(splits)), assigned_split=split,
                     protected_holdout=holdout, training_allowed=False)
            if r['pipeline_status'] == 'eligible' and issues:
                r['pipeline_status'] = 'needs_review'
                r['pipeline_review_codes'] = ';'.join(sorted(issues))
        eligible = [r for r in members if r['pipeline_status'] == 'eligible']
        if eligible:
            rep = max(eligible, key=lambda r: (bool(r['review_decision']), bool(r['displayed_date']),
                      str(r['detail_fetched']) == 'True', r['collected_at'], r['record_key']))
            for r in eligible:
                r['representative_key'] = rep['record_key']
                if r is not rep:
                    r.update(pipeline_status='excluded', exclusion_codes='suspected_duplicate_suppressed')
                else:
                    r['training_allowed'] = split == 'train' and not holdout
    return links


def run(as_of):
    OUT.mkdir(parents=True, exist_ok=True)
    # Protect ALL previous review/data/model artifacts, including the 137 test rows.
    protected = sorted(p for p in PROCESSED.rglob('*') if p.is_file() and OUT not in p.parents)
    protected_hashes = {p.relative_to(BASE).as_posix(): digest(p) for p in protected}
    scripts = [Path(__file__).resolve(), Path(audit.__file__), Path(expanded.__file__),
               BASE/'build_training_v1.py', BASE/'review_training_categories.py',
               BASE/'prepare_smartprop_dataset.py', BASE/'smartprop_geography.py', BASE/'review_nhadat24h.py',
               BASE/'collection_review_rules.py']
    # Fingerprint raw files plus actual review/split dependencies, not unrelated model outputs.
    dependencies = [PROCESSED/r for r in (
        'apartment_v2/review_decisions.csv', 'apartment_v2/review_queue_before.csv',
        'training_source_review/review_decisions.csv',
        'training_v1/all_collection_group_assignments.csv', 'smartprop_review/baseline_inputs.csv',
        'apartment_v2/baseline_inputs.csv', 'training_v1/main_dataset.csv', 'training_v2/main_dataset.csv')]
    dependencies += [p for _, cache, _ in REVIEW_SPECS for p in (PROCESSED/cache).glob('*.html')]
    if SOURCE_REVIEW_MANIFEST.exists():
        dependencies += [SOURCE_REVIEW_MANIFEST, PROCESSED/'collection_source_review/review_decisions.csv',
                          PROCESSED/'collection_source_review/parsed_evidence.json',
                          PROCESSED/'collection_source_review/description_duplicate_pairs.csv']
    inputs = {p.relative_to(BASE).as_posix(): digest(p) for p in raw_paths()+scripts+dependencies if p.exists()}
    fingerprint = hashlib.sha256(json.dumps(dict(as_of=as_of.isoformat(), inputs=inputs),
                                          sort_keys=True).encode()).hexdigest()
    target = OUT/'runs'/(as_of.isoformat()+'_'+fingerprint[:16])
    manifest = target/'manifest.json'
    if manifest.exists():
        saved = json.loads(manifest.read_text(encoding='utf-8'))
        if saved['fingerprint'] != fingerprint:
            raise RuntimeError('Run fingerprint mismatch')
        for rel, h in saved['output_sha256'].items():
            if digest(BASE/rel) != h:
                raise RuntimeError('Frozen pipeline output changed: '+rel)
        publish(target)
        print('Existing run verified; no re-filtering: '+str(target))
        return
    target.mkdir(parents=True, exist_ok=True)
    previous = audit.OUT, audit.ASOF, expanded.ORIGINAL, expanded.OUT
    try:
        audit.OUT, audit.ASOF = target/'source_audit', as_of
        expanded.ORIGINAL, expanded.OUT = audit.OUT, target/'expanded_audit'
        with (target/'stages.log').open('w', encoding='utf-8') as log, contextlib.redirect_stdout(log):
            audit.main()
            expanded.main()
    finally:
        audit.OUT, audit.ASOF, expanded.ORIGINAL, expanded.OUT = previous
    review_by_key, history = load_reviews()
    rows, normalization = [], []
    previous_date = audit.ASOF
    audit.ASOF = as_of
    try:
        for original in records(target/'expanded_audit/all_unique_listings_audit.csv'):
            normalized, changes = repair(original)
            normalization.extend(changes)
            row = classify(normalized, review_by_key.get(original['record_key']))
            row, rule = apply_review_rules(row, normalized)
            row.update(raw_json=original['raw_json'],
                       original_price_million=original['price_million'],
                       original_area_sqm=original['area_sqm'],
                       normalization_fields=';'.join(c['field'] for c in changes),
                       additional_category_rule=rule)
            rows.append(row)
    finally:
        audit.ASOF = previous_date
    reservations, bridges = frozen_groups()
    if SOURCE_REVIEW_MANIFEST.exists():
        bridges += records(PROCESSED/'collection_source_review/description_duplicate_pairs.csv')
    links = finish_groups(rows, records(target/'source_audit/possible_duplicate_properties.csv')+bridges,
                          reservations)
    fields = list(rows[0])
    audit.save_csv(target/'all_listings.csv', rows, fields)
    for status in ('eligible', 'needs_review', 'excluded'):
        audit.save_csv(target/(status+'.csv'), [r for r in rows if r['pipeline_status'] == status], fields)
    train = [r for r in rows if r['training_allowed']]
    audit.save_csv(target/'train_candidates.csv', train, fields)
    audit.save_csv(target/'duplicate_pairs.csv', links, ['left', 'right', 'rule', 'title_similarity'])
    audit.save_csv(target/'review_history.csv', history, sorted(set().union(*(r.keys() for r in history))))
    audit.save_csv(target/'normalization_changes.csv', normalization,
                   ['record_key', 'field', 'previous', 'value', 'source_field', 'source_text', 'rule'])
    stages = json.loads((target/'source_audit/summary.json').read_text(encoding='utf-8'))
    counts = dict(Counter(r['pipeline_status'] for r in rows))
    assert len(rows) == len({r['record_key'] for r in rows}) == sum(counts.values())
    assert len({r['pipeline_group'] for r in rows if r['pipeline_status'] == 'eligible'}) == counts.get('eligible', 0)
    assert not any(r['protected_holdout'] for r in train)
    assert all(r['displayed_date'] and r['geographic_scope_status'].startswith('accepted_') for r in train)
    assert all(digest(BASE/p) == h for p, h in inputs.items()), 'Input changed during pipeline'
    assert all(digest(BASE/p) == h for p, h in protected_hashes.items()), 'Prior artifact changed'
    summary = dict(as_of=as_of.isoformat(), unique_source_ids=len(rows), statuses=counts,
                   raw_files=stages['inventory_files'], snapshot_observations=stages['vietnam_total_observations'],
                   singapore=stages['singapore'], train_candidates=len(train),
                   eligible_reserved=sum(r['pipeline_status']=='eligible' and not r['training_allowed'] for r in rows),
                   by_source={s:dict(Counter(r['pipeline_status'] for r in rows if r['source']==s))
                              for s in sorted({r['source'] for r in rows})},
                   by_category=dict(Counter(r['category'] for r in train)),
                   review_decisions_loaded=len(history), applied_source_reviews=sum(bool(r['review_decision']) for r in rows),
                   normalization_fields=dict(Counter(c['field'] for c in normalization)),
                   normalized_records=len({c['record_key'] for c in normalization}),
                   review_codes=dict(Counter(c for r in rows for c in r['pipeline_review_codes'].split(';') if c)),
                   exclusions=dict(Counter(c for r in rows for c in r['exclusion_codes'].split(';') if c)),
                   duplicate_pairs=len(links), previous_artifacts_unchanged=True, raw_unchanged=True,
                   test_replaced=False, model_trained=False)
    (target/'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    report(target, summary)
    outputs = {p.relative_to(BASE).as_posix(): digest(p) for p in target.rglob('*') if p.is_file()}
    manifest.write_text(json.dumps(dict(fingerprint=fingerprint, input_sha256=inputs,
                        protected_sha256=protected_hashes, output_sha256=outputs), indent=2), encoding='utf-8')
    publish(target)
    print(json.dumps({k: summary[k] for k in ('unique_source_ids', 'statuses', 'train_candidates',
                                            'eligible_reserved', 'previous_artifacts_unchanged')}, ensure_ascii=False))


def report(target, s):
    lines = ['# Lọc toàn bộ dữ liệu SmartProp', '',
             f'Ngày đối chiếu: {s["as_of"]}. Đọc {s["raw_files"]} file nguồn; '
             f'{s["snapshot_observations"]:,} quan sát Việt Nam → **{s["unique_source_ids"]:,} ID nguồn duy nhất**.', '',
             '| Nhóm không chồng lặp | Số tin |', '|---|---:|']
    for status in ('eligible', 'needs_review', 'excluded'):
        lines.append(f'| [{status}]({status}.csv) | {s["statuses"].get(status, 0):,} |')
    lines += ['', f'**{s["train_candidates"]:,} đại diện đủ điều kiện xét cho train mới** trong '
              '[train_candidates.csv](train_candidates.csv). '
              f'{s["eligible_reserved"]:,} đại diện qua lọc còn lại giữ dự phòng/holdout, không nhập vào train.', '',
              '## Quy trình chung', '',
              '1. Đọc toàn bộ CSV/JSONL raw, file cũ và sample; không cộng file processed thành tin mới. Singapore giữ riêng theo SGD/giao dịch HDB.',
              '2. Gộp cùng source/ID, giữ dấu vết snapshot và mâu thuẫn. Kiểm tra URL/ID, bán hay thuê, nhà/đất/căn hộ, Đà Nẵng cũ hoặc mới, giá tổng và diện tích.',
              '   Khôi phục trường giá/diện tích số còn thiếu khi chuỗi nguồn phân tích đầy đủ được; giữ nhãn gốc và nhật ký normalization_changes.csv. Không suy từ đơn giá, khoảng giá hoặc tiền trả trước.',
              '3. Áp dụng quyết định nguồn đã lưu khi hash HTML và nhãn gốc phù hợp. Lưu cả quyết định cũ, mới, giữ/sửa/chờ/loại; không tự ghi lại các file duyệt.',
              '4. Áp dụng quy tắc loại trên mọi tin có cờ, giữ các cờ giá/diện tích chưa giải quyết. Ngày thiếu, trên 183 ngày và ngoại lệ ngưỡng đi vào cần kiểm tra, không xóa raw.',
              '5. Gom nghi trùng trên toàn bộ ID, kể cả cầu nối nhóm cũ. Nhóm mâu thuẫn hoặc có thành viên chưa đủ điều kiện được cách ly; nhóm qua lọc giữ một đại diện.',
              '6. Giữ mọi ID/nhóm holdout cũ khỏi train; xuất ba nhóm và lý do. Không tạo lại test, không huấn luyện mô hình.', '',
              '## Đọc kết quả', '',
              '- `all_listings.csv`: một hàng/ID; nhãn gốc và nhãn sau duyệt, nhóm, trạng thái, lý do, bằng chứng, khả năng dùng cho train.',
              '- `eligible.csv`: đã qua quy tắc và nhóm; vẫn là giá rao, chưa phải nhãn giao dịch được xác minh độc lập.',
              '- `needs_review.csv`: các bằng chứng còn thiếu/mâu thuẫn. Không suy giá thỏa thuận, giá trả trước hoặc địa bàn từ tên file.',
              '- `excluded.csv`: ngoài phạm vi/loại, đã duyệt loại hoặc đại diện nghi trùng bị giữ khỏi train. Xem `exclusion_codes`; nghi trùng không phải khẳng định cùng tài sản.',
              '- `review_history.csv`, `duplicate_pairs.csv`: quyết định và liên kết nhóm truy vết được.',
              '- `normalization_changes.csv`: từng trường được khôi phục từ chuỗi nguồn; raw_json vẫn giữ literal dữ liệu gốc.',
              '- `source_audit/file_inventory.csv`, `summary.json`, `manifest.json`: kiểm kê và hash tái lập. Các tập/model/report trước và toàn bộ raw được kiểm tra giữ nguyên.', '',
              'Bộ train ứng viên mới chưa thay thế training_v2. Nếu dùng để huấn luyện phiên bản mới, chỉ lấy '
              '`train_candidates.csv`; không dùng raw_json, tiêu đề chứa giá, đơn giá/m², cờ lọc, ID hay nhóm làm đặc trưng. '
              'Cần bộ đánh giá mới được chốt trước khi tối ưu; báo cáo v1/v2 và 137 tin test cũ vẫn giữ nguyên.', '',
              'Chạy từ F:\\SmartProp:', '', '```powershell',
              '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/filter_all_collected.py',
              '```', '', 'Cùng dữ liệu/quyết định/mã/ngày: xác minh hash bản chạy đã có. '
              'Có thay đổi: tự tạo thư mục bản chạy mới, không ghi đè kết quả cũ. Không tải lại trang nguồn.', '']
    (target/'README.md').write_text('\n'.join(lines), encoding='utf-8')


def publish(target):
    relative = target.relative_to(OUT).as_posix()
    (OUT/'latest.json').write_text(json.dumps(dict(run=relative), indent=2), encoding='utf-8')
    (OUT/'README.md').write_text('# Pipeline lọc toàn bộ SmartProp\n\n'
        f'[Mở báo cáo và các CSV của bản chạy mới nhất]({relative}/README.md).\n\n'
        'Lệnh chạy chung từ F:\\SmartProp:\n\n```powershell\n'
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/filter_all_collected.py\n```\n', encoding='utf-8')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--as-of', type=date.fromisoformat,
                        default=datetime.now(ZoneInfo('Asia/Ho_Chi_Minh')).date())
    run(parser.parse_args().as_of)
