"""Score the prelocked archival pilot once, using frozen v6 inference artifacts."""
import csv
import hashlib
import json
import uuid
from collections import Counter
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as c
import audit_reserved_holdout as history
import prepare_v6_holdout_pilot as screening
import build_property_features_v6 as builder
import property_text_features_v6 as extractor

OUT=c.PROCESSED/'v6_holdout_pilot/evaluation'


def latest(root):return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def price_band(value):
    for limit,label in zip([2000,5000,10000,20000],['<2 tỷ','2–<5 tỷ','5–<10 tỷ','10–<20 tỷ']):
        if value<limit:return label
    return '≥20 tỷ'


def main():
    if (OUT/'latest.json').exists():
        run=latest(OUT);m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['input_sha256']);c.verify(m['protected_sha256']);c.verify(m['output_sha256'],run)
        print('Pilot already scored; frozen outputs verified, no new prediction: '+str(run));return
    if (OUT/'evaluation_state.json').exists():raise ValueError('Pilot already started; inspect the existing stage, do not start another scoring run')
    qa=latest(screening.OUT)
    qm=json.loads((qa/'manifest.json').read_text(encoding='utf-8'))
    c.verify(qm['input_sha256']);c.verify(qm['protected_sha256']);c.verify(qm['output_sha256'],qa)
    policy=json.loads((qa/'pre_score_policy.json').read_text(encoding='utf-8'))
    lock=json.loads((qa/'locked_cohort.json').read_text(encoding='utf-8'))
    qs=json.loads((qa/'summary.json').read_text(encoding='utf-8'))
    included=c.read(qa/'included_registry.csv');ids={r['record_key'] for r in included}
    assert ids==set(lock['included_ids']) and len(ids)==len(included)==qs['included_ids']
    assert c.sha(qa/'included_registry.csv')==lock['included_registry_sha256']
    assert c.sha(qa/'pre_score_policy.json')==lock['policy_sha256'] and lock['cohort_locked_before_prediction']
    assert not policy['model_fit_allowed'] and policy['price_band_limits_million']==[2000,5000,10000,20000]
    model=c.BASE/policy['model_run'];model_manifest=json.loads((model/'manifest.json').read_text(encoding='utf-8'))
    assert c.sha(model/'manifest.json')==lock['model_manifest_sha256']==policy['model_manifest_sha256']
    assert c.sha(Path(extractor.__file__))==policy['feature_extractor_sha256']
    selection=json.loads((model/'selection.json').read_text(encoding='utf-8'));assert selection['best_global_arm']==policy['selected_arm']=='all'
    feature_run=c.BASE/selection['features_run']
    feature_manifest=json.loads((feature_run/'manifest.json').read_text(encoding='utf-8'))
    for module in [extractor,builder,c]:
        path=Path(module.__file__);relative=path.relative_to(c.BASE).as_posix()
        assert c.sha(path)==feature_manifest['input_sha256'][relative]
    paths=[Path(__file__),Path(c.__file__),Path(extractor.__file__),Path(builder.__file__),qa/'manifest.json',qa/'locked_cohort.json',
        qa/'included_registry.csv',qa/'pre_score_policy.json',qa/'screening_decisions.csv',model/'manifest.json',model/'selection.json',feature_run/'manifest.json']
    data=c.BASE/qs['dataset_run'];source=c.PROCESSED/'collection_source_review'
    paths+=[data/'manifest.json',data/'all_listings_after_review.csv',source/'parsed_evidence.json',source/'fetch_manifest.json']
    for info in selection['category_artifacts'].values():paths += [model/info['model_file'],model/info['schema_file']]
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    protected=dict(qm['protected_sha256'])
    protected.update({(qa/p).relative_to(c.BASE).as_posix():sha for p,sha in qm['output_sha256'].items()})
    OUT.mkdir(parents=True,exist_ok=True)
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    c.write_json(stage/'evaluation_protocol.json',dict(policy,screening_run=qa.relative_to(c.BASE).as_posix(),
        locked_cohort_sha256=c.sha(qa/'locked_cohort.json'),included_ids=sorted(ids),
        numeric_labels_changed=False,training_performed=False))
    c.write_json(OUT/'evaluation_state.json',dict(status='started',stage=stage.relative_to(OUT).as_posix(),
        locked_cohort_sha256=c.sha(qa/'locked_cohort.json'),model_manifest_sha256=lock['model_manifest_sha256']))
    # Candidate prices are used only after policy, cohort, model, and extractor
    # are fixed. No further exclusion or fitting is permitted below this point.
    with (data/'all_listings_after_review.csv').open(encoding='utf-8-sig',newline='') as stream:
        original={r['record_key']:r for r in csv.DictReader(stream) if r['record_key'] in ids}
    assert len(original)==len(ids)
    rows=[c.model_row(original[key],'test') for key in sorted(ids)]
    assert all(original[r['record_key']]['pipeline_status']=='eligible' for r in rows)
    assert not ({r['record_key'] for r in c.read(feature_run/'train.csv')}|{r['record_key'] for r in c.read(feature_run/'validation.csv')})&ids
    parsed=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    feature_rows={};evidence=[];checked=set()
    for row in rows:
        key=row['record_key'];e=parsed.get(key);f=fetch.get(key,{})
        body,state=builder.admit_body(row,e,f)
        if body:
            path=source/'detail_cache'/f['file']
            if path not in checked:
                assert c.sha(path)==f['sha256'];inputs[path.relative_to(c.BASE).as_posix()]=f['sha256'];checked.add(path)
        values,claims=extractor.extract(row,original[key],body,e['detail_sha256'] if body else '')
        feature_rows[key]=dict(record_key=key,**values,body_state=state)
        for claim in claims:evidence.append(dict(record_key=key,**claim))
    predictions=[];categories={};coverage=[]
    for category,info in selection['category_artifacts'].items():
        subset=[r for r in rows if r['category']==category]
        if not subset:continue
        spec=json.loads((model/info['schema_file']).read_text(encoding='utf-8'))
        assert spec['category']==category and spec['arm']=='all'
        X=extractor.encode(subset,feature_rows,spec)
        assert not np.isinf(X).any()
        dm=xgb.DMatrix(X,feature_names=spec['feature_names'])
        booster=xgb.Booster();booster.load_model(model/info['model_file'])
        pred=np.exp(np.clip(booster.predict(dm),-20,30))
        actual=np.asarray([float(r['price_million']) for r in subset])
        assert np.isfinite(actual).all() and (actual>0).all()
        categories[category]=dict(metrics=c.scores(actual,pred),small_sample=len(subset)<10)
        for row,p,a in zip(subset,pred,actual):
            p=float(p);a=float(a)
            predictions.append(dict(record_key=row['record_key'],category=category,source=row['source'],pipeline_group=row['pipeline_group'],
                actual_million=a,predicted_million=p,absolute_error_million=abs(a-p),ape_pct=100*abs(a-p)/a,
                price_band=price_band(a),location_feature=row['location_feature']))
        for field in extractor.FEATURES:
            count=sum(str(feature_rows[r['record_key']][field])!='' for r in subset)
            coverage.append(dict(category=category,feature=field,n=len(subset),available=count,available_pct=100*count/len(subset)))
    assert len(predictions)==len(ids)==len({r['record_key'] for r in predictions})
    aggregate=c.scores([r['actual_million'] for r in predictions],[r['predicted_million'] for r in predictions])
    segments=[]
    for dimension in ['price_band','source','location_feature']:
        for value in sorted({r[dimension] for r in predictions}):
            subset=[r for r in predictions if r[dimension]==value]
            segments.append(dict(dimension=dimension,segment=value,**c.scores([r['actual_million'] for r in subset],[r['predicted_million'] for r in subset]),small_sample=len(subset)<10))
    report=dict(screening_run=qa.relative_to(c.BASE).as_posix(),dataset_run=data.relative_to(c.BASE).as_posix(),model_run=model.relative_to(c.BASE).as_posix(),
        selected_arm='all',candidate_ids=133,scored_ids=len(predictions),held_for_review=133-len(predictions),
        categories=categories,aggregate=aggregate,source_counts=dict(Counter(r['source'] for r in predictions)),
        pilot_used_for_future_tuning_allowed=False,test_kind=policy['test_type'],independent_physical_identity_certified=False,
        validation_reference=json.loads((model/'metrics.json').read_text(encoding='utf-8'))['arms']['all']['aggregate_validation'],
        source_body_snapshots_sha256_verified=len(checked),training_performed=False,numeric_labels_changed=False,
        automatic_deployment=False,new_network_requests=0)
    c.write_json(stage/'metrics.json',report)
    c.write_csv(stage/'pilot_inputs.csv',rows,c.FIELDS)
    c.write_csv(stage/'pilot_predictions.csv',predictions,list(predictions[0]))
    c.write_csv(stage/'segments.csv',segments,list(segments[0]))
    c.write_csv(stage/'feature_coverage.csv',coverage,list(coverage[0]))
    flat=list(feature_rows.values());c.write_csv(stage/'features.csv',flat,list(flat[0]))
    c.write_csv(stage/'feature_evidence_DO_NOT_TRAIN.csv',evidence,list(evidence[0]))
    c.write_csv(stage/'evaluation_exposure_registry.csv',[dict(record_key=r['record_key'],pipeline_group=r['pipeline_group'],role='v6_archival_pilot_scored') for r in rows],['record_key','pipeline_group','role'])
    (stage/'README.md').write_text('\n'.join([
        '# Pilot kiểm chứng v6 trên dữ liệu lưu trữ','',
        f'Đã chấm **{len(predictions)} tin** thuộc 133 ứng viên; {133-len(predictions)} tin chờ rà soát do nghi trùng được giữ ngoài '
        'trước khi dự đoán. Model/schema/extractor/cohort đã khóa trước khi chấm; giữ nguyên mọi nhãn, không fit/tuning.','',
        '| Loại | Số tin | MAE (triệu VND) | MAPE | Sai số ≤20% |','|---|---:|---:|---:|---:|',
        *[f'| {category} | {x["metrics"]["n"]} | {x["metrics"]["mae_million"]:,.2f} | {x["metrics"]["mape_pct"]:.2f}% | {x["metrics"]["within_20pct"]:.2f}% |' for category,x in categories.items()],
        f'| Tổng | {aggregate["n"]} | {aggregate["mae_million"]:,.2f} | {aggregate["mape_pct"]:.2f}% | {aggregate["within_20pct"]:.2f}% |','',
        'Đây là pilot lưu trữ chưa thấy lịch sử model-use theo các artifact đã kiểm kê, không phải test theo thời gian tương lai '
        'hoặc giá giao dịch được xác minh. Nhóm căn hộ 8 tin là mẫu nhỏ. Trùng tài sản ẩn và sai nhãn chưa biết vẫn có thể tồn tại; '
        'tin không có body phù hợp dùng tiêu đề/trường cấu trúc theo đúng quy tắc v6.','',
        '132 tin này từ nay đã được chấm; nếu dùng kết quả để sửa model/luật trích, phải xem chúng là dữ liệu phát triển '
        'và cần tập kiểm chứng mới. Không chọn lại model dựa trên pilot này, không tự triển khai. '
        'Validation cũ và pilot khác ID/phân bố nên không diễn giải chênh lệch metric như so sánh cùng tập.','',
        '[Metrics](metrics.json), [dự đoán từng ID](pilot_predictions.csv), [phân nhóm](segments.csv), '
        '[độ phủ feature](feature_coverage.csv), [dấu vết đã chấm](evaluation_exposure_registry.csv), '
        '[giao thức đánh giá](evaluation_protocol.json). Mọi outcome trong cohort đã khóa đều được giữ.','']),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    code=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    target=OUT/'runs'/code;stage.rename(target)
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    c.write_json(OUT/'evaluation_state.json',dict(status='complete',run=target.relative_to(OUT).as_posix(),scored_ids=len(predictions),
        locked_cohort_sha256=c.sha(qa/'locked_cohort.json'),model_manifest_sha256=lock['model_manifest_sha256']))
    print(json.dumps(report,ensure_ascii=False,indent=2),flush=True);print(target,flush=True)


if __name__=='__main__':main()
