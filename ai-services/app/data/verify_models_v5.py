"""Independently reload v5 models and reconcile paired v3/v4 comparisons."""
import json
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as c
import train_training_v3 as experiment
import train_reviewed_collection_v5 as job


def equal_scores(actual,expected):
    assert actual.keys()==expected.keys()
    for field,value in actual.items():
        if value is None:
            assert expected[field] is None
        else:
            np.testing.assert_allclose(value,expected[field],rtol=1e-6,atol=1e-5)


def main():
    run=job.latest(job.OUT)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],run)
    report=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
    data=c.BASE/report['dataset_run']
    parts={s:c.read(data/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    reserved=c.read(data/'training_inputs/reserved_holdout_registry.csv')
    job.data_job.prior.validate_optional_dates(parts,{r['pipeline_group'] for r in reserved})
    assert len(parts['train'])==report['train_n']==2214
    assert len(parts['validation'])==report['validation_n']==299
    assert len(reserved)==report['reserved_eligible_n']==684
    assert not report['test_evaluated'] and not report['automatic_deployment'] and not report['independent_benchmark']
    assert report['protocol']==job.PROTOCOL
    predictions=c.read(run/'validation_predictions.csv')
    lookup={(r['record_key'],r['model']):r for r in predictions}
    assert len(predictions)==len(lookup)==897
    assert {r['record_key'] for r in predictions}=={r['record_key'] for r in parts['validation']}
    baselines=json.loads((run/'baseline_models.json').read_text(encoding='utf-8'))
    chosen=[]
    for index,category in enumerate(c.CATEGORIES,1):
        train=[r for r in parts['train'] if r['category']==category]
        val=[r for r in parts['validation'] if r['category']==category]
        info=report['categories'][category]
        assert len(train)==info['train_n'] and len(val)==info['validation_n']
        y=np.asarray([float(r['price_million']) for r in val])
        spec=json.loads((run/info['schema_file']).read_text(encoding='utf-8'))
        assert spec==dict(c.schema(train),category=category)
        matrix=xgb.DMatrix(c.encode(val,spec),feature_names=spec['feature_names'])
        booster=xgb.Booster();booster.load_model(run/info['model_file'])
        assert booster.num_boosted_rounds()==info['xgboost_num_trees']==info['xgboost_best_iteration']+1
        actual=experiment.get_baseline_predictions(val,baselines[category])
        actual[experiment.FAMILIES[2]]=np.exp(np.clip(booster.predict(matrix),-20,30))
        scores={f:c.scores(y,values) for f,values in actual.items()}
        selected=min(experiment.FAMILIES,key=lambda f:scores[f]['mae_million'])
        assert selected==info['selected_by_validation_mae']
        equal_scores(scores[selected],info['selected_validation'])
        for family,values in actual.items():
            saved=[lookup[(r['record_key'],family)] for r in val]
            np.testing.assert_allclose(values,[float(r['predicted_million']) for r in saved],rtol=1e-6,atol=1e-5)
            equal_scores(scores[family],info['validation'][family])
            for i,row in enumerate(val):
                p=saved[i]
                assert p['category']==category and p['pipeline_group']==row['pipeline_group']
                assert p['source']==row['source'] and p['location_feature']==row['location_feature']
                assert float(p['actual_million'])==float(y[i])
                assert p['selected']==str(family==selected)
                np.testing.assert_allclose(float(p['absolute_error_million']),abs(values[i]-y[i]),rtol=1e-6,atol=1e-5)
                np.testing.assert_allclose(float(p['ape_pct']),100*abs(values[i]-y[i])/y[i],rtol=1e-6,atol=1e-5)
        chosen.extend((float(y[i]),float(actual[selected][i])) for i in range(len(val)))
    equal_scores(c.scores([a for a,b in chosen],[b for a,b in chosen]),report['aggregate_selected_validation'])
    references={}
    for version,ref in report['references'].items():
        previous=c.BASE/ref['run']
        old=json.loads((previous/'metrics.json').read_text(encoding='utf-8'))
        predictions_old=c.read(previous/'validation_predictions.csv')
        old_lookup={(r['record_key'],r['model']):r for r in predictions_old}
        assert len(old_lookup)==897
        selected_old=[p for p in predictions_old if p['model']==old['categories'][p['category']]['selected_by_validation_mae']]
        equal_scores(c.scores([float(p['actual_million']) for p in selected_old],
                             [float(p['predicted_million']) for p in selected_old]),ref['aggregate_selected_validation'])
        assert ref['train_n']==sum(cat['train_n'] for cat in old['categories'].values())
        for row in parts['validation']:
            for family in experiment.FAMILIES:
                p=old_lookup[(row['record_key'],family)]
                assert p['category']==row['category'] and float(p['actual_million'])==float(row['price_million'])
        references[version]=old
    comparisons=c.read(run/'same_family_comparison.csv')
    assert len(comparisons)==18
    assert len({(r['reference_version'],r['category'],r['model']) for r in comparisons})==18
    for r in comparisons:
        category,family=r['category'],r['model']
        a=references[r['reference_version']]['categories'][category]['validation'][family]['mae_million']
        b=report['categories'][category]['validation'][family]['mae_million']
        assert int(r['validation_n'])==report['categories'][category]['validation_n']
        np.testing.assert_allclose([float(r['reference_mae_million']),float(r['v5_mae_million']),float(r['mae_change_pct'])],
                                  [a,b,100*(b/a-1)],rtol=1e-10,atol=1e-8)
    selected=c.read(run/'selected_family_comparison.csv')
    assert len(selected)==len({(r['reference_version'],r['category']) for r in selected})==6
    for r in selected:
        old=references[r['reference_version']]['categories'][r['category']]
        new=report['categories'][r['category']]
        assert r['reference_model']==old['selected_by_validation_mae'] and r['v5_model']==new['selected_by_validation_mae']
        a=old['selected_validation']['mae_million'];b=new['selected_validation']['mae_million']
        np.testing.assert_allclose([float(r['reference_mae_million']),float(r['v5_mae_million']),float(r['mae_change_pct'])],
                                  [a,b,100*(b/a-1)],rtol=1e-10,atol=1e-8)
    errors=c.read(run/'validation_errors.csv')
    expected=sorted([r for r in predictions if r['selected']=='True'],key=lambda r:float(r['absolute_error_million']),reverse=True)
    assert errors==expected and len(errors)==299
    coverage=experiment.feature_coverage(parts)
    assert c.read(run/'feature_coverage.csv')==[{k:str(v) for k,v in r.items()} for r in coverage]
    result=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),train=2214,validation=299,reserved_eligible=684,
        prediction_rows=897,all_models_reloaded=True,metrics_and_v3_v4_comparisons_verified=True,
        train_only_schemas_verified=True,original_v3_v4_outputs_sha256_unchanged=True,
        test_evaluated=False,automatic_deployment=False,verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
