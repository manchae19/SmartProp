"""Evidence decisions for all 90 pending records plus bounded new-source data."""
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path

import apartment_followup_rules as rules
import collect_apartment_followup as collector
import review_apartment_pilot as old
from build_training_v1 import group_records

BASE=old.BASE
PRIOR=old.OUT/'runs/52c6b97aeb3f7227'
OUT=BASE/'processed/apartment_followup_review'
PROTOCOL=BASE/'APARTMENT_FOLLOWUP_PROTOCOL.md'


def read_new():
    log=collector.OUT/'records.jsonl'
    rows=[json.loads(x) for x in log.read_text(encoding='utf8').splitlines() if x] if log.exists() else []
    if len(rows)!=len({r['record_key'] for r in rows}):raise ValueError('Duplicate follow-up IDs')
    for row in rows:
        path=(collector.OUT/row['detail_file']).resolve()
        if path!=collector.OUT.resolve()/'detail_cache'/(row['source_listing_id']+'.html'):raise ValueError('Unexpected detail path')
        body=path.read_bytes()
        if hashlib.sha256(body).hexdigest()!=row['response_sha256'] or collector.parse_detail(body,row,row['collected_at'])!=row:
            raise ValueError('Follow-up detail replay differs: '+row['record_key'])
    csv=old.read_csv(collector.OUT/'apartment_records.csv') if rows else []
    if csv:
        fields=list(csv[0])
        if csv!=[{k:scalar(r.get(k)) for k in fields} for r in rows]:raise ValueError('Follow-up CSV/log mismatch')
    return rows


def scalar(value):
    return json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else '' if value is None else str(value)


def evaluate(rows,new,history,evidence,catalog,prior):
    source_rows=rows+new
    if len({r['record_key'] for r in source_rows+history})!=len(source_rows)+len(history):raise ValueError('Source IDs overlap')
    bykey={r['record_key']:r for r in source_rows}
    evaluated={k:rules.quality(r,catalog) for k,r in bykey.items()}
    exclusions={k:rules.scope_exclusions(r) for k,r in bykey.items()}
    prior_groups=defaultdict(list)
    for row in prior:prior_groups[row['property_candidate_group']].append(row['record_key'])
    pairs=old.extra_pairs(source_rows,history,evidence)
    for members in prior_groups.values():
        pairs.extend(dict(left=members[0],right=k,rule='preserve_frozen_pilot_group',title_similarity=1) for k in members[1:])
    membership,links=group_records([dict(r) for r in history+source_rows],pairs)
    historic_groups={membership[r['record_key']] for r in history}
    groups=defaultdict(list)
    for row in source_rows:groups[membership[row['record_key']]].append(row)
    prior_bykey={r['record_key']:r for r in prior}
    pending={r['record_key'] for r in prior if r['cohort_split']=='quarantine'}
    decisions=[]
    for group,members in groups.items():
        issues=set()
        if group in historic_groups:issues.add('linked_to_historical_collection')
        if any(evaluated[r['record_key']]['review_codes'] or exclusions[r['record_key']][0] for r in members):issues.add('group_contains_unresolved_or_out_of_scope_member')
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            values=[float(r[field]) for r in members if r[field] is not None]
            if values and max(values)>0 and (max(values)-min(values))/max(values)>tolerance:issues.add('group_'+field+'_conflict')
        if len({evaluated[r['record_key']]['location_feature'] for r in members if evaluated[r['record_key']]['location_feature']})>1:issues.add('group_location_conflict')
        # Prefer the already locked member if its group still passes all gates.
        existing=sorted(r['record_key'] for r in members if prior_bykey.get(r['record_key'],{}).get('cohort_split')=='collection_holdout')
        representative=existing[0] if existing else min(r['record_key'] for r in members)
        for row in members:
            key=row['record_key'];review=evaluated[key];excluded,proof=exclusions[key]
            split='excluded_scope' if excluded else 'needs_evidence' if issues else 'collection_holdout' if key==representative else 'suppressed_duplicate'
            original=prior_bykey.get(key,{})
            phase='prior_pending_90' if key in pending else 'original_locked_10' if key in prior_bykey else 'new_source'
            outcome=('recovered_candidate' if split=='collection_holdout' else split) if phase=='prior_pending_90' else split
            decisions.append(dict(row,review_phase=phase,review_outcome=outcome,
                previous_review_codes=json.loads(original['review_codes']) if original else [],
                previous_group_review_codes=json.loads(original['group_review_codes']) if original else [],
                **review,exclusion_codes=excluded,exclusion_evidence=proof,
                property_candidate_group=group,representative_key=representative,
                group_review_codes=sorted(issues),cohort_split=split,training_allowed=False,
                label_quality='source_asking_price_reviewed_by_rules_unverified_physical_property'))
    return sorted(decisions,key=lambda r:r['record_key']),links


def inputs():
    if (collector.OUT/'collector.lock').exists():raise ValueError('Collector still running; review a completed checkpoint')
    paths=[PROTOCOL,Path(__file__),BASE/'apartment_followup_rules.py',BASE/'verify_apartment_followup.py',Path(collector.__file__)]
    paths += [collector.OUT/name for name in ['records.jsonl','apartment_records.csv','policy.json','checkpoint.json','latest_run.json','robots.txt']]
    paths += list(PRIOR.glob('*'))
    paths += [BASE.parents[2]/name for name in old.inputs()]
    return {p.relative_to(BASE.parents[2]).as_posix():old.collector.sha(p) for p in paths if p.is_file()}


def context():
    # Verify the frozen pilot first, including its protected v6/train hashes.
    import verify_apartment_pilot
    verify_apartment_pilot.verify()
    if json.loads((old.OUT/'latest.json').read_text(encoding='utf8'))['run']!='runs/52c6b97aeb3f7227':raise ValueError('Unexpected prior pilot run')
    rows=old.replay(old.RAW);new=read_new();history=old.read_csv(old.collector.HISTORY)
    prior=old.read_csv(PRIOR/'all_decisions.csv')
    evidence=json.loads(old.EVIDENCE.read_text(encoding='utf8'));keys={r['record_key'] for r in history}
    evidence={k:v for k,v in evidence.items() if k in keys}
    catalog=json.loads(old.CATALOG.read_text(encoding='utf8'))
    return rows,new,history,evidence,catalog,prior


def artifacts():
    rows,new,history,evidence,catalog,prior=context()
    decisions,links=evaluate(rows,new,history,evidence,catalog,prior)
    pending=[r for r in decisions if r['review_phase']=='prior_pending_90']
    if len(pending)!=90:raise ValueError('Expected all 90 original pending decisions')
    cohort=[r for r in decisions if r['cohort_split']=='collection_holdout']
    old_locked={r['record_key'] for r in prior if r['cohort_split']=='collection_holdout'}
    current_keys={r['record_key'] for r in cohort}
    summary=dict(total_original=100,pending_reviewed=90,new_source_raw=len(new),total_raw=len(decisions),
        pending_outcomes=dict(Counter(r['review_outcome'] for r in pending)),
        new_source_outcomes=dict(Counter(r['cohort_split'] for r in decisions if r['review_phase']=='new_source')),
        all_outcomes=dict(Counter(r['cohort_split'] for r in decisions)),collection_holdout=len(cohort),
        original_locked_preserved=len(old_locked&current_keys),original_locked_risk_keys=sorted(old_locked-current_keys),
        historic_id_overlap=0,cache_replays=len(decisions),historical_collection=len(history),
        resolved_code_counts=dict(Counter(c for r in pending for c in r['resolved_previous_codes'])),
        remaining_code_counts=dict(Counter(c for r in decisions if r['cohort_split']=='needs_evidence' for c in r['review_codes'])),
        exclusion_code_counts=dict(Counter(c for r in decisions for c in r['exclusion_codes'])),
        minimum_groups=old.MIN_GROUPS,missing_groups=max(0,old.MIN_GROUPS-len(cohort)),evaluation_gate_passed=len(cohort)>=old.MIN_GROUPS,
        numbers_relabelled=0,model_predictions_run=0,training_started=False,model_changed=False,old_splits_changed=False,
        source_new_run=json.loads((collector.OUT/'latest_run.json').read_text(encoding='utf8')),
        limitation='Source-text review, not independently verified transactions. Preserve previous groups; no evidence is invented to reach the cohort target.')
    return decisions,pending,cohort,links,summary


def main():
    digests=inputs();decisions,pending,cohort,links,summary=artifacts()
    run_id=hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest()[:16]
    run=OUT/'runs'/run_id
    if run.exists():raise ValueError('Immutable run exists; run verify_apartment_followup.py')
    run.mkdir(parents=True)
    fields=list(dict.fromkeys(k for row in decisions for k in row))
    subsets={'all_decisions.csv':decisions,'pending_90_decisions.csv':pending,'collection_holdout.csv':cohort,
        'needs_evidence.csv':[r for r in decisions if r['cohort_split']=='needs_evidence'],
        'excluded_scope.csv':[r for r in decisions if r['cohort_split']=='excluded_scope']}
    for name,subset in subsets.items():old.write_csv(run/name,subset,fields)
    old.write_csv(run/'recovered_candidates.csv',[r for r in pending if r['review_outcome']=='recovered_candidate'],fields)
    keys={r['record_key'] for r in decisions}
    (run/'duplicate_links.json').write_text(json.dumps([p for p in links if p['left'] in keys or p['right'] in keys],ensure_ascii=False,indent=2),encoding='utf8')
    evidence={r['record_key']:dict(rules.evidence(r,r),exclusion_evidence=r['exclusion_evidence'],remaining_codes=r['review_codes'],group_codes=r['group_review_codes']) for r in pending}
    (run/'pending_evidence_private.json').write_text(json.dumps(evidence,ensure_ascii=False,indent=2),encoding='utf8')
    lock=dict(protocol_sha256=old.collector.sha(PROTOCOL),prior_lock_sha256=old.collector.sha(PRIOR/'cohort_lock.json'),
        training_allowed=False,model_predictions_read=False,
        members=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in cohort])
    (run/'cohort_lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),encoding='utf8')
    summary.update(run_id=run_id,input_sha256=digests)
    (run/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    counts=summary['pending_outcomes']
    text=f'''# Rà soát tiếp 90 tin căn hộ — {run_id}

Đã đối chiếu **90/90 tin** với cache gốc, lưu quyết định và bằng chứng từng tin.

| Kết quả 90 tin | Số tin |
|---|---:|
| Bổ sung ứng viên kiểm chứng | {counts.get('recovered_candidate',0)} |
| Loại khỏi phạm vi căn hộ bán | {counts.get('excluded_scope',0)} |
| Vẫn cần bằng chứng | {counts.get('needs_evidence',0)} |
| Tin phụ trong nhóm qua rà soát | {counts.get('suppressed_duplicate',0)} |

Không đổi giá/diện tích: xử lý ranh giới mô tả, nhãn giá bán cạnh ngữ cảnh thuê,
“block” không phải “lỗ”, và giá xấp xỉ đứng cạnh giá bán chính xác khớp nhãn.
Giữ cách ly nhóm nghi trùng và mọi mâu thuẫn chưa giải thích được.

Nhadat24h: **{len(decisions)-100} ID mới**, đối chiếu 8.609 ID trước khi tải chi tiết;
trạng thái cuối **{summary['source_new_run']['status']}** (giới hạn 12 trang/30 tin).
Đây là số thực thu, không phải đã thu đủ 30. Xem checkpoint trong batch nguồn.

Tập kiểm chứng mở rộng hiện **{len(cohort)} nhóm**; giữ được **{summary['original_locked_preserved']}/10**
nhóm đã khóa trước đó; còn thiếu **{summary['missing_groups']}** so với mốc thực hành 20.
**Không có tin nào được thêm vào train. Chưa huấn luyện hoặc chấm v7.**
2.213 train + 299 validation, model/API v6 và registry cũ giữ nguyên checksum.
Mốc 20 không bảo đảm độ chính xác/statistical power hoặc tính độc lập tài sản.

- `pending_90_decisions.csv`: đủ 90 quyết định với cờ cũ/cờ giải quyết/cờ còn lại.
- `pending_evidence_private.json`: quote gốc, trích đoạn chuẩn hóa và SHA cache; giữ cục bộ.
- `recovered_candidates.csv`, `excluded_scope.csv`, `needs_evidence.csv`: các danh sách xử lý.
- `collection_holdout.csv`, `cohort_lock.json`: toàn bộ ứng viên khóa riêng, cấm train.
- `duplicate_links.json`: cả liên kết nhóm cũ, không tách nhóm để tăng số lượng.
- `summary.json`, `manifest.json`: số lượng và checksum.

Tin bị loại khỏi phạm vi không bị xóa raw. Tin còn chờ không bị kết luận là sai.
Phụ thuộc nguồn khác/các nhãn nguồn còn thiếu vẫn là giới hạn thực tế; không dùng
giá AI, ngày thu hoặc phần header tự lặp để bù bằng chứng.
'''
    (run/'README.md').write_text(text,encoding='utf8')
    manifest={p.name:old.collector.sha(p) for p in run.iterdir() if p.is_file()}
    (run/'manifest.json').write_text(json.dumps(manifest,indent=2),encoding='utf8')
    if inputs()!=digests:raise ValueError('Inputs changed; do not publish this run')
    old.collector.atomic(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
