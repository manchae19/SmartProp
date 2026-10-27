"""Reload v4 artifacts and reconcile every validation prediction and comparison."""
import json
import numpy as np
import xgboost as xgb
import training_v3_common as c
import train_training_v3 as v3
import train_reviewed_collection_v4 as v4


def main():
    run=v4.last(v4.OUT)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256'])
    c.verify(manifest['output_sha256'],run)
    report=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
    data=c.BASE/report['dataset_run']/'training_inputs'
    val=c.read(data/'validation.csv')
    predictions=c.read(run/'validation_predictions.csv')
    models=json.loads((run/'baseline_models.json').read_text(encoding='utf-8'))
    assert len(val)==299 and len(predictions)==897
    keys={(r['record_key'],r['model']) for r in predictions}
    assert len(keys)==897
    assert {r['record_key'] for r in predictions}=={r['record_key'] for r in val}
    assert report['test_evaluated'] is False and report['automatic_deployment'] is False
    assert report['train_n']==2110
    chosen=[]
    for index,category in enumerate(c.CATEGORIES,1):
        subset=[r for r in val if r['category']==category]
        y=np.asarray([float(r['price_million']) for r in subset])
        spec=json.loads((run/f'category_{index}_schema.json').read_text(encoding='utf-8'))
        dm=xgb.DMatrix(c.encode(subset,spec),feature_names=spec['feature_names'])
        model=xgb.Booster();model.load_model(run/f'category_{index}_xgboost.json')
        actual=v3.get_baseline_predictions(subset,models[category])
        actual[v3.FAMILIES[2]]=np.exp(np.clip(model.predict(dm),-20,30))
        selected=report['categories'][category]['selected_by_validation_mae']
        for family,values in actual.items():
            saved={r['record_key']:r for r in predictions if r['category']==category and r['model']==family}
            np.testing.assert_allclose(values,[float(saved[r['record_key']]['predicted_million']) for r in subset],rtol=1e-6,atol=1e-5)
            scores=c.scores(y,values)
            for field,value in scores.items():
                expected=report['categories'][category]['validation'][family][field]
                if value is not None:
                    np.testing.assert_allclose(value,expected,rtol=1e-6,atol=1e-5)
            for row in subset:
                assert float(saved[row['record_key']]['actual_million'])==float(row['price_million'])
                assert saved[row['record_key']]['selected']==str(family==selected)
        chosen.extend((float(y[i]),float(actual[selected][i])) for i in range(len(subset)))
        assert selected==min(v3.FAMILIES,key=lambda f:report['categories'][category]['validation'][f]['mae_million'])
    scores=c.scores([p[0] for p in chosen],[p[1] for p in chosen])
    for field,value in scores.items():
        if value is not None:
            np.testing.assert_allclose(value,report['aggregate_selected_validation'][field],rtol=1e-6,atol=1e-5)
    prior=v4.last(c.PROCESSED/'models_v3_validation')
    old=json.loads((prior/'metrics.json').read_text(encoding='utf-8'))
    for row in c.read(run/'v3_v4_same_family_comparison.csv'):
        cat,family=row['category'],row['model']
        a=old['categories'][cat]['validation'][family]['mae_million']
        b=report['categories'][cat]['validation'][family]['mae_million']
        np.testing.assert_allclose([float(row['v3_mae_million']),float(row['v4_mae_million']),float(row['mae_change_pct'])],
                                  [a,b,100*(b/a-1)],rtol=1e-10)
    result=dict(verified=True,run=run.relative_to(v4.OUT).as_posix(),train=2110,validation=299,
        prediction_rows=897,all_models_reloaded=True,metrics_and_v3_comparison_verified=True,
        original_v3_outputs_sha256_unchanged=True,test_evaluated=False,automatic_deployment=False)
    c.write_json(v4.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
