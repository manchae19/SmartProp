"""Independently reconstruct matrices and reload all fifteen v6 boosters."""
import json
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as c
import train_training_v3 as baseline
import train_property_features_v6 as job
import property_text_features_v6 as features


def equal_scores(actual,expected):
    for field,value in actual.items():
        if value is None:assert expected[field] is None
        else:np.testing.assert_allclose(value,expected[field],rtol=1e-6,atol=1e-5)


def main():
    run=job.latest(job.OUT)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],run)
    report=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
    data=c.BASE/report['feature_run']
    parts={s:c.read(data/(s+'.csv')) for s in ['train','validation']}
    sidecar={r['record_key']:r for r in c.read(data/'features.csv')}
    assert len(parts['train'])==report['train_n']==2214 and len(parts['validation'])==report['validation_n']==299
    assert len(sidecar)==2513
    reserved=c.read(data/'reserved_holdout_registry.csv')
    assert len(reserved)==report['reserved_eligible_n']==684
    assert not({r['record_key'] for r in reserved}&sidecar.keys())
    assert report['protocol']==job.PROTOCOL and list(report['arms'])==job.ARMS
    assert not report['test_evaluated'] and not report['automatic_deployment'] and not report['numeric_labels_changed']
    predictions=c.read(run/'validation_predictions.csv')
    lookup={(r['record_key'],r['arm']):r for r in predictions}
    assert len(predictions)==len(lookup)==1495
    reconstructed={};loaded=0
    v5=job.latest(c.PROCESSED/'models_v5_validation')
    previous={(r['record_key'],r['model']):r for r in c.read(v5/'validation_predictions.csv')}
    for arm in job.ARMS:
        aggregate=[]
        for index,category in enumerate(c.CATEGORIES,1):
            info=report['arms'][arm]['categories'][category]
            train=[r for r in parts['train'] if r['category']==category]
            val=[r for r in parts['validation'] if r['category']==category]
            spec=json.loads((run/info['schema_file']).read_text(encoding='utf-8'))
            assert spec==features.feature_spec(train,category,arm)
            assert len(spec['feature_names'])==info['feature_n']
            assert not any(name in ['price_million','title','description','source','record_key','pipeline_group'] for name in spec['feature_names'])
            X=features.encode(val,sidecar,spec)
            assert not np.isinf(X).any()
            dm=xgb.DMatrix(X,feature_names=spec['feature_names'])
            model=xgb.Booster();model.load_model(run/info['model_file']);loaded+=1
            assert model.num_boosted_rounds()==info['num_trees']==info['best_iteration']+1
            p=np.exp(np.clip(model.predict(dm),-20,30))
            y=np.asarray([float(r['price_million']) for r in val])
            equal_scores(c.scores(y,p),info['validation'])
            assert info['train_n']==len(train) and info['validation_n']==len(val)
            for i,row in enumerate(val):
                saved=lookup[(row['record_key'],arm)]
                assert saved['category']==category and saved['pipeline_group']==row['pipeline_group'] and saved['source']==row['source']
                assert float(saved['actual_million'])==float(y[i])
                np.testing.assert_allclose([float(saved['predicted_million']),float(saved['absolute_error_million']),float(saved['ape_pct'])],
                    [p[i],abs(p[i]-y[i]),100*abs(p[i]-y[i])/y[i]],rtol=1e-6,atol=1e-5)
                if arm=='control':
                    np.testing.assert_allclose(p[i],float(previous[(row['record_key'],baseline.FAMILIES[2])]['predicted_million']),rtol=1e-7,atol=1e-5)
                aggregate.append((y[i],p[i]))
        reconstructed[arm]=c.scores([a for a,b in aggregate],[b for a,b in aggregate])
        equal_scores(reconstructed[arm],report['arms'][arm]['aggregate_validation'])
    equal_scores(reconstructed['control'],report['v5_control'])
    selected=min(job.ARMS,key=lambda a:reconstructed[a]['mae_million'])
    assert report['best_global_arm']==selected
    selection=json.loads((run/'selection.json').read_text(encoding='utf-8'))
    assert selection['best_global_arm']==selected and selection['development_only'] and not selection['automatic_deployment']
    for category in c.CATEGORIES:
        for name in ['model_file','schema_file']:
            assert selection['category_artifacts'][category][name]==report['arms'][selected]['categories'][category][name]
    aggregate_comparison=c.read(run/'arm_comparison.csv')
    assert len(aggregate_comparison)==5 and {r['arm'] for r in aggregate_comparison}==set(job.ARMS)
    for row in aggregate_comparison:
        for field,value in reconstructed[row['arm']].items():
            if value is None:assert not row[field]
            else:np.testing.assert_allclose(float(row[field]),value,rtol=1e-6,atol=1e-5)
        np.testing.assert_allclose(float(row['mae_change_vs_control_pct']),
            100*(reconstructed[row['arm']]['mae_million']/reconstructed['control']['mae_million']-1),rtol=1e-6,atol=1e-5)
    category_comparison=c.read(run/'category_comparison.csv')
    assert len(category_comparison)==len({(r['arm'],r['category']) for r in category_comparison})==15
    for row in category_comparison:
        old=report['arms']['control']['categories'][row['category']]['validation']['mae_million']
        new=report['arms'][row['arm']]['categories'][row['category']]['validation']['mae_million']
        np.testing.assert_allclose([float(row['v5_control_mae_million']),float(row['arm_mae_million']),float(row['mae_change_pct'])],
                                  [old,new,100*(new/old-1)],rtol=1e-10,atol=1e-8)
    for category in ['Đất nền','Căn hộ chung cư']:
        for row in [r for r in parts['validation'] if r['category']==category]:
            key=row['record_key']
            assert lookup[(key,'subtype')]['predicted_million']==lookup[(key,'control')]['predicted_million']
            if category=='Đất nền':assert lookup[(key,'rooms_floors')]['predicted_million']==lookup[(key,'control')]['predicted_million']
            if category=='Căn hộ chung cư':
                assert lookup[(key,'access')]['predicted_million']==lookup[(key,'control')]['predicted_million']
                assert lookup[(key,'all')]['predicted_million']==lookup[(key,'rooms_floors')]['predicted_million']
    errors=c.read(run/'selected_validation_errors.csv')
    assert errors==sorted([r for r in predictions if r['arm']==selected],key=lambda r:float(r['absolute_error_million']),reverse=True)
    v3=job.latest(c.PROCESSED/'models_v3_validation')
    v3_metrics=json.loads((v3/'metrics.json').read_text(encoding='utf-8'))
    equal_scores(report['v3_selected_baseline'],v3_metrics['aggregate_selected_validation'])
    result=dict(verified=True,run=run.relative_to(job.OUT).as_posix(),train=2214,validation=299,reserved_eligible=684,
        models_reloaded=loaded,prediction_rows=1495,best_global_arm=selected,all_metrics_verified=True,
        control_reproduces_v5=True,original_models_features_and_data_sha256_unchanged=True,
        schema_fit_on_train_only=True,test_evaluated=False,automatic_deployment=False,verifier_sha256=c.sha(Path(__file__)))
    c.write_json(job.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
