"""Reconcile pre-score QA, frozen labels/features and every pilot prediction."""
import csv
import json
from collections import Counter,defaultdict
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as c
import evaluate_v6_holdout_pilot as job
import holdout_screening_rules as rules
import build_property_features_v6 as builder
import property_text_features_v6 as extractor


def equal_scores(actual,expected):
    for field,value in actual.items():
        if value is None:assert expected[field] is None
        else:np.testing.assert_allclose(value,expected[field],rtol=1e-6,atol=1e-5)


def main():
    run=job.latest(job.OUT)
    m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(m['input_sha256']);c.verify(m['protected_sha256']);c.verify(m['output_sha256'],run)
    report=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
    qa=c.BASE/report['screening_run']
    qm=json.loads((qa/'manifest.json').read_text(encoding='utf-8'))
    c.verify(qm['input_sha256']);c.verify(qm['output_sha256'],qa)
    lock=json.loads((qa/'locked_cohort.json').read_text(encoding='utf-8'))
    policy=json.loads((qa/'pre_score_policy.json').read_text(encoding='utf-8'))
    evaluation_protocol=json.loads((run/'evaluation_protocol.json').read_text(encoding='utf-8'))
    expected_ids=set(lock['included_ids'])
    assert evaluation_protocol['included_ids']==sorted(expected_ids)
    assert evaluation_protocol['locked_cohort_sha256']==c.sha(qa/'locked_cohort.json')
    assert (qa/'locked_cohort.json').stat().st_mtime_ns<=(run/'evaluation_protocol.json').stat().st_mtime_ns
    assert (run/'evaluation_protocol.json').stat().st_mtime_ns<=(run/'pilot_predictions.csv').stat().st_mtime_ns
    data=c.BASE/report['dataset_run'];source=c.PROCESSED/'collection_source_review'
    with (data/'all_listings_after_review.csv').open(encoding='utf-8-sig',newline='') as s:
        metadata={r['record_key']:{f:r.get(f,'') for f in job.screening.META} for r in csv.DictReader(s)}
    parsed=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    decisions=c.read(qa/'screening_decisions.csv')
    assert len(decisions)==len({r['record_key'] for r in decisions})==133
    assert {r['record_key'] for r in decisions if r['screening_status']=='included'}==expected_ids
    signatures=defaultdict(set);titles=defaultdict(set)
    for key,row in metadata.items():
        sig=rules.body_signature(parsed.get(key))
        if sig:signatures[sig].add(key)
        sig=rules.title_signature(row)
        if sig:titles[sig].add(key)
    expected_links=set()
    for d in decisions:
        key=d['record_key'];row=metadata[key]
        assert row['pipeline_status']=='eligible'
        flags=rules.scope_flags(row,parsed.get(key));matching=set()
        sig=rules.body_signature(parsed.get(key))
        if sig:matching.update((other,'exact_long_masked_seller_body') for other in signatures[sig] if metadata[other]['pipeline_group']!=row['pipeline_group'])
        sig=rules.title_signature(row)
        if sig:matching.update((other,'exact_long_masked_title_same_category_location_area') for other in titles[sig]
            if metadata[other]['pipeline_group']!=row['pipeline_group'] and metadata[other]['category']==row['category']
            and metadata[other]['location_feature']==row['location_feature'] and metadata[other]['area_sqm']==row['area_sqm'])
        expected_links.update((key,other,rule) for other,rule in matching)
        reasons={x['rule'] for x in flags}|({'cross_group_duplicate_candidate'} if matching else set())
        assert d['screening_status']==('needs_review' if reasons else 'included')
        assert set(filter(None,d['reason_codes'].split(';')))==reasons
        assert d['price_or_prediction_used']=='False'
    assert {(r['record_key'],r['other_record_key'],r['rule']) for r in c.read(qa/'duplicate_links.csv')}==expected_links
    inputs=c.read(run/'pilot_inputs.csv');bykey={r['record_key']:r for r in inputs}
    assert len(inputs)==len(bykey)==len(expected_ids)==report['scored_ids']
    assert bykey.keys()==expected_ids
    with (data/'all_listings_after_review.csv').open(encoding='utf-8-sig',newline='') as s:
        original={r['record_key']:r for r in csv.DictReader(s) if r['record_key'] in expected_ids}
    for key,row in bykey.items():assert row==c.model_row(original[key],'test')
    sidecar=c.read(run/'features.csv');features={r['record_key']:r for r in sidecar}
    assert len(sidecar)==len(expected_ids) and features.keys()==expected_ids
    for key,row in bykey.items():
        body,state=builder.admit_body(row,parsed.get(key),fetch.get(key,{}))
        expected,_=extractor.extract(row,original[key],body,parsed[key]['detail_sha256'] if body else '')
        assert features[key]['body_state']==state
        for field,value in expected.items():assert features[key][field]==str(value)
        if body:
            relative=(source/'detail_cache'/fetch[key]['file']).relative_to(c.BASE).as_posix()
            assert m['input_sha256'][relative]==parsed[key]['detail_sha256']
    model=c.BASE/report['model_run']
    assert c.sha(model/'manifest.json')==lock['model_manifest_sha256']==policy['model_manifest_sha256']
    assert c.sha(Path(extractor.__file__))==policy['feature_extractor_sha256']
    selection=json.loads((model/'selection.json').read_text(encoding='utf-8'))
    feature_run=c.BASE/selection['features_run']
    trainval={r['record_key'] for split in ['train','validation'] for r in c.read(feature_run/(split+'.csv'))}
    assert not trainval&expected_ids
    predictions=c.read(run/'pilot_predictions.csv');saved={r['record_key']:r for r in predictions}
    assert len(predictions)==len(saved)==len(expected_ids) and saved.keys()==expected_ids
    all_actual=[];all_predicted=[];loaded=0
    for category,info in selection['category_artifacts'].items():
        rows=[r for r in inputs if r['category']==category]
        if not rows:continue
        spec=json.loads((model/info['schema_file']).read_text(encoding='utf-8'))
        assert spec['category']==category and spec['arm']=='all'
        dm=xgb.DMatrix(extractor.encode(rows,features,spec),feature_names=spec['feature_names'])
        booster=xgb.Booster();booster.load_model(model/info['model_file']);loaded+=1
        actual=np.asarray([float(r['price_million']) for r in rows])
        predicted=np.exp(np.clip(booster.predict(dm),-20,30))
        equal_scores(c.scores(actual,predicted),report['categories'][category]['metrics'])
        assert report['categories'][category]['small_sample']==(len(rows)<10)
        for r,a,p in zip(rows,actual,predicted):
            s=saved[r['record_key']]
            assert s['category']==category and s['source']==r['source'] and s['pipeline_group']==r['pipeline_group']
            assert float(s['actual_million'])==float(a) and s['price_band']==job.price_band(a)
            np.testing.assert_allclose([float(s['predicted_million']),float(s['absolute_error_million']),float(s['ape_pct'])],
                                      [p,abs(a-p),100*abs(a-p)/a],rtol=1e-6,atol=1e-5)
        all_actual.extend(actual);all_predicted.extend(predicted)
    equal_scores(c.scores(all_actual,all_predicted),report['aggregate'])
    segments=c.read(run/'segments.csv')
    for row in segments:
        members=[r for r in predictions if r[row['dimension']]==row['segment']]
        scores=c.scores([float(r['actual_million']) for r in members],[float(r['predicted_million']) for r in members])
        for field,value in scores.items():
            if value is None:assert not row[field]
            else:np.testing.assert_allclose(float(row[field]),value,rtol=1e-9)
        assert row['small_sample']==str(len(members)<10)
    for dimension in ['source','location_feature','price_band']:
        assert sum(int(r['n']) for r in segments if r['dimension']==dimension)==len(expected_ids)
    exposure=c.read(run/'evaluation_exposure_registry.csv')
    assert len(exposure)==len(expected_ids) and {r['record_key'] for r in exposure}==expected_ids
    state=json.loads((job.OUT/'evaluation_state.json').read_text(encoding='utf-8'))
    assert state['status']=='complete' and state['run']==run.relative_to(job.OUT).as_posix() and state['scored_ids']==len(expected_ids)
    assert not report['training_performed'] and not report['numeric_labels_changed'] and not report['automatic_deployment']
    assert report['candidate_ids']==133 and report['held_for_review']==133-len(expected_ids)
    result=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),screened_candidate_ids=133,scored_ids=len(expected_ids),
        held_for_review=133-len(expected_ids),screening_rules_and_duplicate_links_replayed=True,
        cohort_and_policy_locked_before_predictions=True,models_reloaded=loaded,all_predictions_and_metrics_verified=True,
        frozen_labels_features_models_and_train_validation_unchanged=True,exposure_registry_persisted=True,
        test_kind=report['test_kind'],independent_physical_identity_certified=False,
        verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
