"""Evidence-limited category review of the 434 flagged v1 candidates; never edits v1."""
import hashlib
import json
import re
from collections import Counter, defaultdict
from audit_all_collected import BASE, read, save_csv
from smartprop_geography import norm

V1 = BASE/'processed/training_v1'
OUT = BASE/'processed/training_category_review'


def decide(row):
    raw = json.loads(row['raw_json'])
    source = norm(raw.get('source_category',''))
    title = norm(row['title'])
    # CafeLand may prepend its category to the actual headline.
    title = re.sub(r'^ban nha rieng\s*:\s*','',title)
    if re.search(r'\b(shop khoi de|shophouse|day tro|nha tro|toa can ho|khach san|homestay|condotel)\b',title):
        return 'exclude','Khác','commercial_or_whole_building_title','Tiêu đề nêu loại thương mại/lưu trú hoặc toàn công trình; không thuộc nhà/đất/căn hộ thông thường.'
    if re.search(r'\b(dat co nha|dat tang|tang \d*\s*nha|san nha|quy dat|dat vang|dat va nha|nha va dat)\b',title):
        return 'pending','','mixed_land_and_existing_building','Có dấu hiệu đất kèm công trình; cần mô tả chi tiết để xác định đối tượng định giá.'
    if re.search(r'\b(quy can|bang hang|mot so can|nhieu can|mo ban|quy song lap|\d+ can nha|nha \d+ can)\b',title):
        return 'pending','','multiple_properties_or_project_ad','Chưa chứng minh đây là một tài sản riêng lẻ có nhãn giá toàn bộ.'
    if re.search(r'\b(\d+\s*%\s*von|von \d+\s*%|thanh toan|tra truoc|booking|dat coc)\b',title):
        return 'pending','','partial_payment_context','Cần kiểm tra điều kiện thanh toán và tổng giá trước khi sử dụng nhãn.'
    land = bool(re.search(r'\b(ban dat|lo dat|cap dat|dat nen|dat tho cu)\b',title) or re.match(r'^\W*dat\b',title))
    house = bool(re.search(r'\b(ban nha|can ban nha|nha (?:moi |dep )?\d+\s*tang|nha (?:c4|cap 4|me lung|gac lung)|ban biet thu|biet thu \d+ tang|nha pho lien ke|ban nha lien ke)\b',title))
    if land and house:
        return 'pending','','mixed_explicit_house_land','Tiêu đề có cả tín hiệu nhà và đất; không tự chọn một nhãn.'
    if land:
        if source in ['nha mat pho','nha trong ngo','nha biet thu, lien ke']:
            return 'pending','','land_title_conflicts_with_house_source','Tiêu đề nêu đất nhưng danh mục nguồn nêu nhà; cần chi tiết để giải quyết mâu thuẫn.'
        if row['category']=='Đất nền' and source in ['nha dat tho cu','dat tho cu, dat o']:
            return 'keep','Đất nền','explicit_land_with_broad_or_land_source','Tiêu đề nêu đất; danh mục là nhà đất tổng hợp hoặc đất ở, không có tín hiệu nhà được phát hiện.'
    if house:
        if row['category']=='Nhà ở' and source in ['nha dat tho cu','nha mat pho','nha trong ngo','nha biet thu, lien ke','ban-nha-rieng','ban-nha-pho-du-an']:
            return 'keep','Nhà ở','explicit_house_with_compatible_source','Tiêu đề nêu nhà/công trình nhà ở; phù hợp danh mục nhà hoặc nhà đất tổng hợp.'
    return 'pending','','insufficient_specific_property_evidence','Tiêu đề/danh mục chưa đủ rõ để bỏ cờ; cần trang chi tiết hoặc bằng chứng bổ sung.'


def main():
    inputs = [V1/'candidate_decisions.csv',V1/'all_collection_group_assignments.csv',V1/'summary.json',
              V1/'main_dataset.csv',V1/'train.csv',V1/'validation.csv',V1/'test.csv']
    frozen = {p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    v1summary = json.loads((V1/'summary.json').read_text(encoding='utf-8'))
    for rel,h in v1summary['source_sha256'].items():
        assert hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==h,'Stale v1: '+rel
    candidates = read(inputs[0])
    target = [r for r in candidates if 'source_category_needs_review' in r['v1_review_codes'].split(';')]
    decisions = []
    for row in target:
        decision,category,rule,note = decide(row)
        raw = json.loads(row['raw_json'])
        remaining = set(filter(None,row['v1_review_codes'].split(';')))-{'source_category_needs_review'}
        # Extra financial/transaction cues surfaced by this review remain a gate.
        if re.search(r'\b(\d+\s*%\s*von|von \d+\s*%|tra truoc|thanh toan|booking|dat coc)\b',norm(row['title'])):
            remaining.add('partial_payment_context')
        decisions.append(dict(record_key=row['record_key'],source=row['source'],detail_url=row['detail_url'],
            title=row['title'],source_category=raw.get('source_category',''),raw_category=raw.get('category',''),
            audit_category=row['category'],decision=decision,reviewed_category=category,
            rule=rule,note=note,evidence_kind='saved_source_fields_and_title_only',
            independently_verified=False,new_detail_fetched=False,
            evidence_sha256=hashlib.sha256(row['raw_json'].encode()).hexdigest(),
            input_file=row['input_file'],input_row=row['input_row'],
            remaining_review_codes=';'.join(sorted(remaining)),duplicate_candidate_group=row['duplicate_candidate_group'],
            frozen_model_split=row['model_split'],ready_for_group_check=decision=='keep' and not remaining))
    bykey = {r['record_key']:r for r in decisions}
    groups = defaultdict(list)
    for row in candidates:groups[row['duplicate_candidate_group']].append(row)
    eligible = []
    for row in decisions:
        blockers = []
        for member in groups[row['duplicate_candidate_group']]:
            d = bykey.get(member['record_key'])
            if d:
                if d['decision']!='keep' or d['remaining_review_codes']:
                    blockers.append(member['record_key'])
            elif member['v1_disposition']=='quarantined':
                blockers.append(member['record_key'])
        row['group_blocking_ids']=';'.join(sorted(blockers))
        row['eligible_after_category_review']=bool(row['ready_for_group_check'] and not blockers)
        if row['eligible_after_category_review']:eligible.append(row)
    OUT.mkdir(parents=True,exist_ok=True)
    fields = list(decisions[0])
    save_csv(OUT/'review_decisions.csv',decisions,fields)
    save_csv(OUT/'pending.csv',[r for r in decisions if r['decision']=='pending'],fields)
    save_csv(OUT/'excluded.csv',[r for r in decisions if r['decision']=='exclude'],fields)
    save_csv(OUT/'eligible_for_next_version.csv',eligible,fields)
    summary = dict(reviewed_records=len(decisions),decisions=dict(Counter(r['decision'] for r in decisions)),
        rules=dict(Counter(r['rule'] for r in decisions)),
        by_source={s:dict(Counter(r['decision'] for r in decisions if r['source']==s)) for s in sorted({r['source'] for r in decisions})},
        eligible_records=len(eligible),eligible_groups=len({r['duplicate_candidate_group'] for r in eligible}),
        eligible_by_frozen_split=dict(Counter(r['frozen_model_split'] for r in eligible)),
        input_sha256={p.relative_to(BASE).as_posix():h for p,h in frozen.items()},
        v1_unchanged=all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in frozen.items()),
        evidence='Rule-assisted review of saved title and source category; no new detail downloads or manual verification.')
    assert summary['v1_unchanged']
    assert len(decisions)==len({r['record_key'] for r in decisions})==len(target)
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Rà soát loại bất động sản trong nhóm cách ly v1','',
        f'Đã xét **{len(decisions)} tin** có cờ loại nguồn. Quyết định dựa trên tiêu đề và danh mục đã lưu, '
        'có quy tắc và dấu vết từng tin; chưa phải xác minh độc lập từ trang chi tiết.', '',
        '| Nguồn | Giữ nhãn theo bằng chứng hiện có | Loại | Chờ |','|---|---:|---:|---:|']
    for source,counts in summary['by_source'].items():
        lines.append(f'| {source} | {counts.get("keep",0)} | {counts.get("exclude",0)} | {counts.get("pending",0)} |')
    lines+=['',f'**{len(eligible)} tin trong {summary["eligible_groups"]} nhóm** đủ điều kiện xem xét cho phiên bản tiếp theo sau kiểm tra các cờ còn lại và thành viên cùng nhóm. '
        'Giữ nhãn loại không đồng nghĩa đã duyệt sạch giá hoặc diện tích. Chưa bổ sung tin vào dữ liệu huấn luyện.', '',
        '## Quyết định và giới hạn','',
        '- Giữ khi tiêu đề nêu rõ đất/nhà và danh mục nguồn là loại phù hợp hoặc nhóm nhà đất tổng hợp. Đây là phân giải lại cờ bằng quy tắc, không gán nhãn thủ công.',
        '- Chờ khi đất nằm trong danh mục nhà, đất có nhà/tặng nhà, quảng cáo nhiều tài sản/dự án, giá theo vốn ban đầu, hoặc tiêu đề không đủ rõ.',
        '- Loại loại thương mại/lưu trú/toàn công trình rõ trong tiêu đề, ví dụ shop khối đế và dãy trọ. Raw và quyết định v1 vẫn giữ nguyên.',
        '- Không bỏ cờ giá, diện tích, nhiều tài sản hoặc mâu thuẫn trong nhóm nghi trùng. Mọi tin vẫn giữ nhóm và split v1.',
        '- Không có thay đổi nhãn nào được gọi là xác minh thực địa hay kiểm tra trang chi tiết mới. Có thể còn tín hiệu chưa thể phát hiện bằng tiêu đề.', '',
        '## Tệp kết quả','',
        '- `review_decisions.csv`: mọi tin, quyết định giữ/loại/chờ, bằng chứng, quy tắc và hash.',
        '- `pending.csv`: các tin cần mô tả/trang chi tiết để quyết định.',
        '- `excluded.csv`: loại khỏi mục tiêu nhà/đất/căn hộ thông thường.',
        '- `eligible_for_next_version.csv`: đã giải quyết cờ loại và không còn cờ/nhóm chặn; vẫn là nhãn sàng lọc tự động.',
        '- `summary.json`: tổng hợp, hash và kiểm tra v1 giữ nguyên.', '',
        'Bước tiếp theo: đối chiếu chi tiết nhóm chờ; khi tạo v2, ưu tiên chỉ bổ sung nhóm train. '
        'Giữ nguyên ID, nhãn và nhóm trong validation/test v1 để so sánh công bằng. Nhóm vốn thuộc holdout nhưng chưa dùng trong v1 phải giữ dự phòng, không chuyển sang train.', '',
        'Chạy lại: `python ai-services/app/data/review_training_categories.py`.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
