"""Build a conservative, grouped experimental dataset from expanded-audit candidates."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from audit_all_collected import BASE, read, number, price, save_csv
from smartprop_geography import norm
from prepare_smartprop_dataset import CATEGORIES

INPUT = BASE/'processed/full_collection_audit_expanded'
OUT = BASE/'processed/training_v1'
SEED = 'smartprop-expanded-training-v1'


def extra_checks(row):
    raw = json.loads(row['raw_json'])
    flags = []
    p, a = number(row['price_million']), number(row['area_sqm'])
    if p is None or a is None or p <= 0 or a <= 0:
        return ['invalid_numeric_target_or_area']
    if not 100 <= p <= 200000 or not 20 <= a <= 1000 or not 2 <= p/a <= 300:
        flags.append('numeric_threshold')
    if row['category'] not in CATEGORIES:
        flags.append('unsupported_category')
    if row['transaction_verified'] != 'True':
        flags.append('sale_not_supported')
    if not row['geographic_scope_status'].startswith('accepted_'):
        flags.append('geography_not_supported')
    for k in ['price_raw', 'detail_price_raw']:
        if raw.get(k):
            parsed = price(raw[k])
            if parsed is None or abs(parsed-p) > .01:
                flags.append(k+'_not_confirmed_total')
    for k in ['category_needs_review']:
        if raw.get(k) in [True, 'True']:
            flags.append('source_'+k)
    if raw.get('date_needs_review') in [True,'True'] and row['date_basis'] != 'source_update_not_first_post':
        flags.append('source_date_needs_review')
    title = norm(row['title'])
    if re.search(r'\b(mot so can|nhieu can|\d+ can nha|\d+ lo dat|ban ca day)\b', title):
        flags.append('multiple_properties_in_title')
    if re.search(r'\b(booking|dat coc|tra truoc|gia tu|chi tu|cho thue)\b', title):
        flags.append('transaction_or_partial_price_title')
    if row['category']=='Nhà ở' and re.match(r'^(?:\W*|can\s+)?(?:ban\s+)?dat\b', title):
        flags.append('land_title_house_label')
    totals = [m['amount_million'] for m in json.loads(row['title_money_evidence']) if m['kind']=='total_candidate']
    if totals and max(totals)-min(totals) > .1*max(totals):
        flags.append('multiple_different_total_prices_in_title')
    return sorted(set(flags))


def group_records(rows, prior_pairs):
    """Group across all audit records so excluded bridge records cannot leak holdouts."""
    bykey = {r['record_key']:r for r in rows}
    parent = {k:k for k in bykey}
    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]]
            k = parent[k]
        return k
    pairs = []
    seen = set()
    def link(left, right, rule, similarity=1):
        pair = tuple(sorted([left,right]))
        if pair in seen or left not in parent or right not in parent:
            return
        seen.add(pair)
        parent[find(right)] = find(left)
        pairs.append(dict(left=left,right=right,rule=rule,title_similarity=round(similarity,4)))
    for pair in prior_pairs:
        link(pair['left'],pair['right'],'original_audit:'+pair['rule'],float(pair['title_similarity']))
    titles = defaultdict(list)
    blocks = defaultdict(list)
    for row in rows:
        row['_title'] = re.sub(r'\W+',' ',norm(row['title'])).strip()
        row['_tokens'] = set(row['_title'].split())
        if len(row['_tokens']) < 6:
            continue
        titles[row['_title']].append(row)
        if number(row['area_sqm']) and number(row['price_million']):
            blocks[row['category']].append(row)
    for members in titles.values():
        for row in members[1:]:
            link(members[0]['record_key'],row['record_key'],'exact_title_across_locations')
    for members in blocks.values():
        members.sort(key=lambda r:float(r['area_sqm']))
        for i,a in enumerate(members):
            for b in members[i+1:]:
                if float(b['area_sqm']) > float(a['area_sqm'])/.99:
                    break
                pa,pb = float(a['price_million']),float(b['price_million'])
                if abs(pa-pb)/max(pa,pb) > .05:
                    continue
                sa,sb = a['_tokens'],b['_tokens']
                if len(sa&sb)<8 or len(sa&sb)/len(sa|sb)<.65:
                    continue
                sim = SequenceMatcher(None,a['_title'],b['_title'],autojunk=False).ratio()
                if sim >= .88:
                    link(a['record_key'],b['record_key'],'similar_title_area_1pct_price_5pct_across_locations',sim)
    groups = defaultdict(list)
    for key in parent:
        groups[find(key)].append(key)
    membership = {}
    for keys in groups.values():
        gid = 'property_candidate:'+hashlib.sha256('|'.join(sorted(keys)).encode()).hexdigest()[:20]
        for key in keys:
            membership[key] = gid
    for row in rows:
        row.pop('_title',None)
        row.pop('_tokens',None)
    return membership,pairs


def split_for(group):
    bucket = int(hashlib.sha256((SEED+':'+group).encode()).hexdigest()[:8],16)%100
    return 'train' if bucket<80 else 'validation' if bucket<90 else 'test'


def main():
    original = BASE/'processed/full_collection_audit'
    inputs = [INPUT/'all_unique_listings_audit.csv', INPUT/'summary.json',
              original/'possible_duplicate_properties.csv',original/'summary.json']
    old = json.loads(inputs[-1].read_text(encoding='utf-8'))
    hashes = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    for path,digest in old['input_sha256'].items():
        assert hashlib.sha256((BASE/path).read_bytes()).hexdigest()==digest, 'Stale audit: '+path
    expanded = json.loads(inputs[1].read_text(encoding='utf-8'))
    for name,digest in expanded['original_audit_sha256'].items():
        assert hashlib.sha256((original/name).read_bytes()).hexdigest()==digest, 'Stale expanded audit'
    rows = read(inputs[0])
    membership,pairs = group_records(rows,read(inputs[2]))
    allgroups = defaultdict(list)
    for row in rows:
        allgroups[membership[row['record_key']]].append(row)
    candidates = [dict(r) for r in rows if r['status'] in ['screened_candidate_unverified','screened_date_unknown']]
    grouped = defaultdict(list)
    for row in candidates:
        gid = membership[row['record_key']]
        issues = extra_checks(row)
        members = allgroups[gid]
        if any(m['prior_review_decision'] in ['pending','exclude','correct'] for m in members):
            issues.append('linked_to_prior_pending_excluded_or_corrected_label')
        values = [m for m in members if number(m['price_million']) and number(m['area_sqm'])]
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            v = [float(m[field]) for m in values]
            if v and (max(v)-min(v))/max(v)>tolerance:
                issues.append('duplicate_group_'+field+'_conflict')
        if len({m['category'] for m in members})>1:
            issues.append('duplicate_group_category_conflict')
        if len({m['district'] for m in members if m['district']})>1:
            issues.append('duplicate_group_historical_location_conflict')
        row.update(duplicate_candidate_group=gid,model_split=split_for(gid),
                   v1_review_codes=';'.join(sorted(set(issues))),v1_disposition='',representative_key='',
                   label_quality='automatically_screened_unverified',
                   location_feature=row['district'] or 'new_unit:'+norm(row['address_raw'].split(',')[0]))
        grouped[gid].append(row)
    mainrows,unknown,removed,quarantined = [],[],[],[]
    for gid,members in grouped.items():
        valid = [r for r in members if not r['v1_review_codes']]
        # If any candidate in a group needs label review, hold out the entire group.
        if len(valid)!=len(members):
            for r in members:
                r['v1_disposition']='quarantined'
                if not r['v1_review_codes']:r['v1_review_codes']='linked_candidate_needs_review'
                quarantined.append(r)
            continue
        rep = max(valid,key=lambda r:(bool(r['displayed_date']),r['detail_fetched']=='True',r['collected_at'],r['record_key']))
        for r in members:
            r['representative_key']=rep['record_key']
            if r is rep:
                r['v1_disposition']='main' if r['displayed_date'] else 'unknown_date_experiment'
                (mainrows if r['displayed_date'] else unknown).append(r)
            else:
                r['v1_disposition']='suppressed_possible_duplicate'
                removed.append(r)
    OUT.mkdir(parents=True,exist_ok=True)
    fields = list(candidates[0])
    for name,subset in [('candidate_decisions',candidates),('main_dataset',mainrows),
                        ('unknown_date_experiment',unknown),('quarantined',quarantined),('suppressed_duplicates',removed)]:
        save_csv(OUT/(name+'.csv'),subset,fields)
    for split in ['train','validation','test']:
        save_csv(OUT/(split+'.csv'),[r for r in mainrows if r['model_split']==split],fields)
    save_csv(OUT/'possible_duplicate_pairs.csv',pairs,['left','right','rule','title_similarity'])
    groupfields = ['record_key','duplicate_candidate_group','model_split','candidate']
    candidatekeys = {r['record_key'] for r in candidates}
    save_csv(OUT/'all_collection_group_assignments.csv',[dict(record_key=r['record_key'],
        duplicate_candidate_group=membership[r['record_key']],model_split=split_for(membership[r['record_key']]),
        candidate=r['record_key'] in candidatekeys) for r in rows],groupfields)
    assert len(mainrows)+len(unknown)+len(removed)+len(quarantined)==len(candidates)
    assert len({r['duplicate_candidate_group'] for r in mainrows+unknown})==len(mainrows+unknown)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    assert all(hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h for p,h in old['input_sha256'].items())
    summary = dict(input_candidates=len(candidates),main_records=len(mainrows),unknown_date_records=len(unknown),
        quarantined_records=len(quarantined),suppressed_duplicate_records=len(removed),
        dispositions=dict(Counter(r['v1_disposition'] for r in candidates)),
        quarantine_reasons=dict(Counter(f for r in quarantined for f in r['v1_review_codes'].split(';'))),
        main_by_category={c:dict(Counter(r['model_split'] for r in mainrows if r['category']==c)) for c in CATEGORIES},
        main_by_source=dict(Counter(r['source'] for r in mainrows)),split_seed=SEED,
        split_counts=dict(Counter(r['model_split'] for r in mainrows)),suspected_pairs=len(pairs),
        source_sha256={str(p.relative_to(BASE)).replace('\\','/'):h for p,h in hashes.items()},raw_hashes_unchanged=True)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines = ['# Bộ dữ liệu huấn luyện v1 — thử nghiệm', '',
        f'Từ {len(candidates):,} ứng viên: **{len(mainrows):,} tin tập chính có ngày**, **{len(unknown):,} tin thiếu ngày giữ riêng**, '
        f'**{len(quarantined):,} tin cách ly**, **{len(removed):,} tin nghi trùng không dùng làm đại diện**.', '',
        'Giá mục tiêu là giá rao bán toàn bộ, đơn vị triệu VND; diện tích m². Nhãn được đối chiếu với các trường raw hiện có, '
        'chưa xác minh lại toàn bộ trang chi tiết và chưa phải giá giao dịch. Nhiều raw không lưu mô tả đầy đủ nên chưa kiểm tra được mọi điều kiện trong nội dung.', '',
        '| Loại | Train | Validation | Test |','|---|---:|---:|---:|']
    for c,counts in summary['main_by_category'].items():
        lines.append(f'| {c} | {counts.get("train",0)} | {counts.get("validation",0)} | {counts.get("test",0)} |')
    lines += ['', '## Quy tắc lựa chọn', '',
        '- Chỉ xét 2.780 ứng viên của audit mở rộng; không tự nhập 17 nhãn duyệt trước vào bộ này.',
        '- Đối chiếu lại giá thô/giá chi tiết, giá dương và diện tích hợp lệ, loại bán, địa bàn, cờ loại/ngày nguồn, nhiều tài sản hoặc nhiều tổng giá trong tiêu đề. CafeLand luôn bật cờ ngày khi lưu ngày cập nhật: giữ nếu đã phân tích được mốc này, không coi đó là ngày đăng đầu.',
        '- Giữ nguyên các ngưỡng audit. Không cắt ngoại lệ theo phân phối toàn bộ dữ liệu hoặc dùng test để chọn ngưỡng.',
        '- Gom nghi trùng trên toàn bộ 8.509 ID, gồm liên kết audit cũ, tiêu đề chuẩn hóa trùng (ít nhất 6 từ khác nhau), hoặc tiêu đề tương tự ≥0,88 với giao token ≥0,65/8 từ, diện tích lệch ≤1%, giá lệch ≤5%. Không giới hạn quận để bỏ sót ít hơn khi địa bàn đổi tên.',
        '- Liên kết nghi trùng có thể gom nhầm hoặc bỏ sót. Nhóm có mâu thuẫn giá/diện tích/loại/quận cũ, hoặc liên kết với nhãn đã sửa/chờ/loại được cách ly để duyệt.',
        '- Mỗi nhóm giữ một đại diện: ưu tiên có ngày, có snapshot chi tiết, thời điểm thu thập mới hơn, sau đó ID. Các thành viên vẫn có trong nhật ký, không xóa raw.',
        '- Nhóm được chia cố định bằng SHA256, ngưỡng 80/10/10; không phân tầng nên tỷ lệ thực tế dao động. Đây là đánh giá ngẫu nhiên theo nhóm, chưa phải dự báo thời gian tương lai.',
        '- Tập thiếu ngày không trộn vào tập chính; nếu thử nghiệm bổ sung, chỉ dùng các hàng có model_split=train để giữ nguyên holdout chính.',
        '- district giữ nhãn lịch sử; location_feature dùng quận cũ nếu có, nếu không dùng đơn vị địa chỉ mới. Không ép phường mới vào quận cũ.', '',
        '## Sử dụng', '',
        '`train.csv`, `validation.csv`, `test.csv` là đầu vào tập chính. Chỉ chọn biến đầu vào có sẵn tại thời điểm dự đoán. '
        '**Không dùng price_per_sqm_million, tiêu đề/mô tả chứa giá, raw_json, mã nhóm hay các cờ kiểm tra giá làm đặc trưng**, vì có thể tiết lộ nhãn. '
        'Mọi encoder, chuẩn hóa và chọn mô hình phải học trên train, chọn bằng validation; test dùng báo cáo cuối.', '',
        '`candidate_decisions.csv` đối soát mọi ứng viên; `quarantined.csv` ghi lý do cách ly; `suppressed_duplicates.csv` ghi ID đại diện. '
        '`possible_duplicate_pairs.csv` và `all_collection_group_assignments.csv` giữ bằng chứng gom nhóm trên toàn bộ bộ sưu tập.', '',
        'Dữ liệu gốc và các bộ baseline/apartment/Singapore trước được giữ nguyên. Bộ v1 có split riêng, không so trực tiếp sai số với test cũ.', '',
        'Chạy lại: `python ai-services/app/data/build_training_v1.py`. Sau đó chạy `python ai-services/app/data/train_training_v1.py` để cập nhật mô hình cơ sở.', '',
        'Xem [kết quả mô hình cơ sở](BASELINE.md). Nếu xây lại dữ liệu, phải chạy lại mô hình để chỉ số khớp hash đầu vào.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
