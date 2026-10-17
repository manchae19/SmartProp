"""Freeze source-scope/duplicate screening and cohort before scoring v6 pilot."""
import csv
import hashlib
import json
import uuid
from collections import Counter,defaultdict
from pathlib import Path
import training_v3_common as c
import audit_reserved_holdout as history
import holdout_screening_rules as rules

OUT=c.PROCESSED/'v6_holdout_pilot/screening'
META=['record_key','source','category','pipeline_group','pipeline_status','title','address_raw','location_feature','area_sqm']


def main():
    audit=history.latest(history.OUT)
    am=json.loads((audit/'manifest.json').read_text(encoding='utf-8'))
    c.verify(am['output_sha256'],audit);c.verify(am['protected_sha256'])
    proof=json.loads((history.OUT/'verification.json').read_text(encoding='utf-8'))
    assert proof['verified'] and proof['run']==audit.relative_to(history.OUT).as_posix()
    original_protocol=json.loads((audit/'locked_candidate_protocol.json').read_text(encoding='utf-8'))
    candidates=c.read(audit/'candidate_registry.csv');ids={r['record_key'] for r in candidates}
    assert len(candidates)==len(ids)==133
    model=c.BASE/original_protocol['model_run']
    assert c.sha(model/'manifest.json')==original_protocol['model_manifest_sha256']
    assert c.sha(c.BASE/'property_text_features_v6.py')==original_protocol['feature_extractor_sha256']
    feature_root=history.latest(c.PROCESSED/'property_features_v6')
    data=c.BASE/json.loads((feature_root/'summary.json').read_text(encoding='utf-8'))['dataset_run']
    source=c.PROCESSED/'collection_source_review'
    paths=[Path(__file__),Path(rules.__file__),Path(c.__file__),audit/'manifest.json',audit/'candidate_registry.csv',
        audit/'locked_candidate_protocol.json',history.OUT/'verification.json',data/'manifest.json',data/'all_listings_after_review.csv',
        source/'parsed_evidence.json',source/'fetch_manifest.json',model/'manifest.json',model/'selection.json',c.BASE/'property_text_features_v6.py']
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    source_frozen=json.loads((source/'review_manifest.json').read_text(encoding='utf-8'))
    for path in [source/'parsed_evidence.json',source/'fetch_manifest.json']:
        assert c.sha(path)==source_frozen['output_sha256'][path.relative_to(c.BASE).as_posix()]
    inputs[(source/'review_manifest.json').relative_to(c.BASE).as_posix()]=c.sha(source/'review_manifest.json')
    # Persist the precise QA/evaluation policy before reading candidate text or labels.
    policy=dict(screening=rules.POLICY,original_candidate_protocol_sha256=c.sha(audit/'locked_candidate_protocol.json'),
        selected_arm=original_protocol['selected_arm'],model_run=original_protocol['model_run'],
        model_manifest_sha256=original_protocol['model_manifest_sha256'],
        feature_extractor_sha256=original_protocol['feature_extractor_sha256'],
        price_band_limits_million=[2000,5000,10000,20000],
        evaluate='All candidates passing the fixed source/duplicate rules; no residual-based exclusions',
        target='Frozen total asking price, million VND; no relabeling',
        test_type='one_time_archival_pilot_not_prospective_or_verified_transaction_test',
        model_fit_allowed=False,automatic_deployment=False)
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    c.write_json(stage/'pre_score_policy.json',policy)
    with (data/'all_listings_after_review.csv').open(encoding='utf-8-sig',newline='') as stream:
        allrows={r['record_key']:{f:r.get(f,'') for f in META} for r in csv.DictReader(stream)}
    parsed=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    checked=set()
    for key in ids:
        e=parsed.get(key,{})
        if e.get('identity_verified'):
            f=fetch.get(key,{})
            if f.get('http_status')!=200 or e.get('detail_sha256')!=f.get('sha256'):raise ValueError('Candidate source mismatch: '+key)
            path=source/'detail_cache'/f['file']
            assert c.sha(path)==f['sha256'];checked.add(path)
            inputs[path.relative_to(c.BASE).as_posix()]=f['sha256']
    signatures=defaultdict(set);titles=defaultdict(set)
    for key,row in allrows.items():
        signature=rules.body_signature(parsed.get(key))
        if signature:signatures[signature].add(key)
        signature=rules.title_signature(row)
        if signature:titles[signature].add(key)
    decisions=[];links=[]
    for candidate in candidates:
        key=candidate['record_key'];row=allrows[key]
        assert row['pipeline_status']=='eligible'
        flags=rules.scope_flags(row,parsed.get(key))
        matching=set()
        signature=rules.body_signature(parsed.get(key))
        if signature:
            matching.update((other,'exact_long_masked_seller_body') for other in signatures[signature] if allrows[other]['pipeline_group']!=row['pipeline_group'])
        signature=rules.title_signature(row)
        if signature:
            matching.update((other,'exact_long_masked_title_same_category_location_area') for other in titles[signature]
                if allrows[other]['pipeline_group']!=row['pipeline_group'] and allrows[other]['category']==row['category']
                and allrows[other]['location_feature']==row['location_feature'] and allrows[other]['area_sqm']==row['area_sqm'])
        for other,rule in sorted(matching):links.append(dict(record_key=key,other_record_key=other,rule=rule,other_is_candidate=other in ids))
        if matching:flags.append(dict(rule='cross_group_duplicate_candidate',source='frozen_title_or_parsed_body',quote='See duplicate_links.csv'))
        decisions.append(dict(record_key=key,source=row['source'],category=row['category'],pipeline_group=row['pipeline_group'],
            screening_status='needs_review' if flags else 'included',
            reason_codes=';'.join(sorted({f['rule'] for f in flags})),
            evidence_json=json.dumps(flags,ensure_ascii=False),
            saved_body_identity_verified=bool(parsed.get(key,{}).get('identity_verified')),price_or_prediction_used=False))
    included=[r for r in decisions if r['screening_status']=='included']
    c.write_csv(stage/'screening_decisions.csv',decisions,list(decisions[0]))
    c.write_csv(stage/'included_registry.csv',included,list(decisions[0]))
    c.write_csv(stage/'duplicate_links.csv',links,['record_key','other_record_key','rule','other_is_candidate'])
    summary=dict(candidate_ids=133,included_ids=len(included),needs_review_ids=len(decisions)-len(included),
        by_category=dict(Counter(r['category'] for r in included)),reason_counts=dict(Counter(code for r in decisions for code in r['reason_codes'].split(';') if code)),
        candidate_html_snapshots_sha256_verified=len(checked),model_run=original_protocol['model_run'],
        dataset_run=data.relative_to(c.BASE).as_posix(),history_audit_run=audit.relative_to(c.BASE).as_posix(),
        numeric_targets_used_in_screening=False,predictions_computed=False,independent_physical_identity_certified=False)
    c.write_json(stage/'summary.json',summary)
    c.write_json(stage/'locked_cohort.json',dict(included_ids=sorted(r['record_key'] for r in included),
        included_registry_sha256=c.sha(stage/'included_registry.csv'),screening_decisions_sha256=c.sha(stage/'screening_decisions.csv'),
        policy_sha256=c.sha(stage/'pre_score_policy.json'),model_manifest_sha256=original_protocol['model_manifest_sha256'],
        actually_scored=0,cohort_locked_before_prediction=True))
    code=hashlib.sha256(json.dumps(dict(inputs=inputs,policy=policy),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/code
    if target.exists():raise ValueError('Screening already exists; use its frozen cohort, do not rescreen')
    (stage/'README.md').write_text('# Sàng lọc trước khi chấm pilot v6\n\n'
        f'133 ứng viên: {len(included)} giữ để chấm, {133-len(included)} chờ đối chiếu nguồn/trùng. '
        'Luật được lưu trước khi đọc nội dung; giá số và dự đoán không tham gia sàng lọc. '
        'Dùng nguyên nhãn và model v6 đã khóa. Nội dung trùng là dấu hiệu nghi trùng, chưa chứng minh tài sản vật lý. '
        'Tin không có mô tả đã xác minh chỉ được kiểm tra theo tiêu đề và bộ lọc collection trước đó; có thể còn thiếu thông tin.\n\n'
        '[Quyết định từng ID](screening_decisions.csv), [liên kết nghi trùng](duplicate_links.csv), '
        '[cohort đã khóa](locked_cohort.json), [policy trước chấm](pre_score_policy.json), [số liệu](summary.json).\n',encoding='utf-8')
    c.verify(inputs);c.verify(am['protected_sha256'])
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=am['protected_sha256'],output_sha256=c.outputs(stage)))
    stage.rename(target)
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True);print(target,flush=True)


if __name__=='__main__':main()
