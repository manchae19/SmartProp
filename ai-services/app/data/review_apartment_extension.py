"""Corrected text boundary for dedup on both sides; immutable earlier runs."""
from collections import Counter
import hashlib
import json
from pathlib import Path

import apartment_followup_rules as rules
import collect_apartment_extension as collector
import review_apartment_followup as previous

BASE=previous.BASE
OUT=BASE/'processed/apartment_extension_review'
PROTOCOL=BASE/'APARTMENT_EXTENSION_PROTOCOL.md'
PRIOR=previous.OUT/'runs/1bb003196b4b5b94'


def dedup_text(text):
    # v1 no longer sees the misleading phrase as a boundary. This is only
    # internal matching text; original source wording is restored in outputs.
    return rules.subject(text).replace('thong tin chi tiet',' ')


def evaluate(rows,new,history,evidence,catalog,prior):
    originals={r['record_key']:r for r in rows+new}
    prepared=lambda values:[dict(r,description=dedup_text(r['description'])) for r in values]
    historical_evidence={k:dict(v,description=dedup_text(v.get('description','')),
        **({'asset_description':dedup_text(v['asset_description'])} if 'asset_description' in v else {})) for k,v in evidence.items()}
    adapted_prior=[dict(r,cohort_split='quarantine' if r['cohort_split']=='needs_evidence' else r['cohort_split']) for r in prior]
    decisions,links=previous.evaluate(prepared(rows),prepared(new),history,historical_evidence,catalog,adapted_prior)
    for row in decisions:
        original=originals[row['record_key']];quality=rules.quality(original,catalog)
        if quality['review_codes']!=row['review_codes']:raise ValueError('Boundary adapter changed source quality')
        row.update(quality)
        row['description']=original['description']
        row['dedup_boundary_version']='seller_subject_v2_both_new_and_history'
    return decisions,links


def extension_rows():
    import collect_apartment_topup
    all_rows=[]
    for output in [collector.OUT,collect_apartment_topup.OUT]:
        if not (output/'records.jsonl').exists():continue
        rows=collector.load_rows(output)
        for row in rows:
            path=(output/row['detail_file']).resolve()
            if path!=output.resolve()/'detail_cache'/(row['source_listing_id']+'.html'):raise ValueError('Invalid cache path')
            body=path.read_bytes()
            if hashlib.sha256(body).hexdigest()!=row['response_sha256'] or collector.source.parse_detail(body,row,row['collected_at'])!=row:
                raise ValueError('New source cache replay differs')
        csv=previous.old.read_csv(output/'apartment_records.csv')
        fields=list(csv[0]) if csv else []
        if csv!=[{k:previous.scalar(r.get(k)) for k in fields} for r in rows]:raise ValueError('New CSV/log mismatch')
        all_rows.extend(rows)
    return all_rows


def inputs():
    import collect_apartment_topup
    for output in [collector.OUT,collect_apartment_topup.OUT]:
        if (output/'collector.lock').exists():raise ValueError('Collection still running')
    paths=[BASE.parents[2]/name for name in previous.inputs()]
    paths += [PROTOCOL,Path(__file__),BASE/'verify_apartment_extension.py',Path(collector.__file__)]
    paths += list(PRIOR.glob('*'))
    paths += [collector.OUT/name for name in ['records.jsonl','apartment_records.csv','policy.json','checkpoint.json','latest_run.json','robots.txt']]
    paths += [Path(collect_apartment_topup.__file__),collector.OUT/'collector_used.py']
    if (collect_apartment_topup.OUT/'records.jsonl').exists():
        paths += [collect_apartment_topup.OUT/name for name in ['records.jsonl','apartment_records.csv','policy.json','checkpoint.json','latest_run.json','robots.txt']]
        paths += [collect_apartment_topup.OUT/'runner_used.py',collect_apartment_topup.OUT/'review_used_before_evaluation.py']
    paths += list((BASE/'processed/evaluation_ledger').glob('*.json'))
    return {p.relative_to(BASE.parents[2]).as_posix():collector.source.sha(p) for p in paths if p.is_file()}


def artifacts():
    import verify_apartment_followup
    verify_apartment_followup.verify()
    old,new_old,history,evidence,catalog,_=previous.context()
    existing=old+new_old;new=extension_rows();prior=previous.old.read_csv(PRIOR/'all_decisions.csv')
    decisions,links=evaluate(existing,new,history,evidence,catalog,prior)
    cohort=[r for r in decisions if r['cohort_split']=='collection_holdout']
    prior_keys={r['record_key'] for r in prior if r['cohort_split']=='collection_holdout'}
    now_keys={r['record_key'] for r in cohort}
    new_keys={r['record_key'] for r in new}
    summary=dict(total_raw=len(decisions),new_raw=len(new),previous_raw=len(existing),historical=len(history),
        historical_id_overlap=0,collection_holdout=len(cohort),outcomes=dict(Counter(r['cohort_split'] for r in decisions)),
        new_outcomes=dict(Counter(r['cohort_split'] for r in decisions if r['record_key'] in new_keys)),
        prior_locked_preserved=len(prior_keys&now_keys),prior_locked_new_risk_keys=sorted(prior_keys-now_keys),
        minimum_groups=previous.old.MIN_GROUPS,missing_groups=max(0,previous.old.MIN_GROUPS-len(cohort)),
        evaluation_gate_passed=len(cohort)>=previous.old.MIN_GROUPS,model_predictions_run=0,training_started=False,
        source_numbers_changed=0,old_splits_changed=False,production_model_changed=False,
        collection_run=json.loads((collector.OUT/'latest_run.json').read_text(encoding='utf8')),
        limitation='Asking-price source review. Candidate text groups cannot prove physical independence. The minimum is not statistical assurance.')
    evaluated=set()
    for receipt in (BASE/'processed/evaluation_ledger').glob('*.json'):
        used=json.loads(receipt.read_text(encoding='utf8'))
        evaluated.update(r['record_key'] if isinstance(r,dict) else r for r in used['members'])
    summary['previously_evaluated_members']=len(now_keys&evaluated)
    summary['fresh_for_new_evaluation']=not bool(now_keys&evaluated)
    return decisions,cohort,links,summary


def main():
    digests=inputs();decisions,cohort,links,summary=artifacts()
    run_id=hashlib.sha256(json.dumps(digests,sort_keys=True).encode()).hexdigest()[:16]
    run=OUT/'runs'/run_id
    if run.exists():raise ValueError('Immutable run exists; use verifier')
    run.mkdir(parents=True)
    fields=list(dict.fromkeys(k for r in decisions for k in r))
    for name,subset in [('all_decisions.csv',decisions),('collection_holdout.csv',cohort),
                        ('needs_evidence.csv',[r for r in decisions if r['cohort_split']=='needs_evidence']),
                        ('excluded_scope.csv',[r for r in decisions if r['cohort_split']=='excluded_scope'])]:
        previous.old.write_csv(run/name,subset,fields)
    keys={r['record_key'] for r in decisions}
    (run/'duplicate_links.json').write_text(json.dumps([p for p in links if p['left'] in keys or p['right'] in keys],ensure_ascii=False,indent=2),encoding='utf8')
    lock=dict(training_allowed=False,model_predictions_read=False,protocol_sha256=collector.source.sha(PROTOCOL),
        prior_lock_sha256=collector.source.sha(PRIOR/'cohort_lock.json'),
        members=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in cohort])
    (run/'cohort_lock.json').write_text(json.dumps(lock,ensure_ascii=False,indent=2),encoding='utf8')
    summary.update(run_id=run_id,input_sha256=digests)
    (run/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    text=f'''# Kiểm chứng mở rộng sau review — {run_id}

Đã sửa so trùng mô tả cho cả dữ liệu mới và lịch sử. Không thay raw hoặc run trước.
Thu thêm **{summary['new_raw']} tin**, tổng các lô mới **{summary['total_raw']}**;
đối chiếu **{summary['historical']}** tin lịch sử, không trùng ID.

Nhóm kiểm chứng hiện **{len(cohort)}**, còn thiếu **{summary['missing_groups']}** so với mốc thực hành 20.
Giữ được **{summary['prior_locked_preserved']}/13** nhóm trước sau rà soát lại rò rỉ.
Nhóm có rủi ro mới: {summary['prior_locked_new_risk_keys']}.

Kết quả toàn lô: `{summary['outcomes']}`.
Kết quả tin bổ sung: `{summary['new_outcomes']}`.
Trạng thái thu thập: **{summary['collection_run']['status']}**.

Lượt rà soát này không chạy dự đoán hoặc train; không thêm cohort vào train.
2.213 train/299 validation, model/API v6 và database giữ nguyên. Mốc 20 không bảo đảm
độ chính xác hoặc tính độc lập tài sản; đây vẫn là nhãn giá rao nguồn.

`collection_holdout.csv` và `cohort_lock.json` là bản khóa hiện hành.
`all_decisions.csv`, `needs_evidence.csv`, `excluded_scope.csv`, `duplicate_links.json`
giữ quyết định và liên kết. Cache/CSV chỉ giữ trên máy.

Lượt review này không fit/chấm mô hình. Theo ledger, **{summary['previously_evaluated_members']}**
thành viên cohort đã được đánh giá ở bước sau. Cohort còn mới để đánh giá cấu
hình khác: **{summary['fresh_for_new_evaluation']}**. Dùng kết quả model đã lưu,
không chấm lại để lựa chọn cấu hình.
'''
    (run/'README.md').write_text(text,encoding='utf8')
    (run/'manifest.json').write_text(json.dumps({p.name:collector.source.sha(p) for p in run.iterdir() if p.is_file()},indent=2),encoding='utf8')
    if inputs()!=digests:raise ValueError('Inputs changed during review')
    collector.source.atomic(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
