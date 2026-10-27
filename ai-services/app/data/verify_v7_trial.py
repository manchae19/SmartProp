"""Verify saved fixed-trial outputs and metrics; no training or new selection."""
import json
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as data
import train_v7_trial as job


def verify(run=None):
    if run is None:run=job.latest(job.OUT)
    run=Path(run);manifest=json.loads((run/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest['input_sha256'].items():
        if data.sha(job.BASE.parents[2]/name)!=digest:raise ValueError('Changed input: '+name)
    for name,digest in manifest['output_sha256'].items():
        if data.sha(run/name)!=digest:raise ValueError('Changed output: '+name)
    report=json.loads((run/'metrics.json').read_text(encoding='utf8'))
    prepared_key=next(k for k in manifest['input_sha256'] if '/v7_trial_preparation/' in k and k.endswith('/manifest.json'))
    prepared=(job.BASE.parents[2]/prepared_key).parent
    val=data.read(prepared/'validation.csv')
    lookup={}
    for config,filename in zip(job.CONFIGS,['features_control.csv','features_masked.csv']):
        values={r['record_key']:r for r in data.read(prepared/filename)}
        for category,info in report['configurations'][config]['categories'].items():
            model=xgb.Booster();model.load_model(run/info['model_file'])
            spec=json.loads((run/info['schema_file']).read_text(encoding='utf8'))
            selected=[r for r in val if r['category']==category]
            matrix=xgb.DMatrix(job.features.encode(selected,values,spec),feature_names=spec['feature_names'])
            predictions=np.exp(np.clip(model.predict(matrix),-20,30))
            lookup.update({(config,r['record_key']):float(p) for r,p in zip(selected,predictions)})
    for row in data.read(run/'validation_predictions.csv'):
        np.testing.assert_allclose(float(row['predicted_million']),lookup[row['config'],row['record_key']],rtol=1e-7,atol=1e-6)
    validation_rows=data.read(run/'validation_predictions.csv')
    if {(r['config'],r['record_key']) for r in validation_rows}!=set(lookup):raise ValueError('Missing validation prediction keys')
    labels={r['record_key']:r for r in val}
    for row in validation_rows:
        if row['category']!=labels[row['record_key']]['category'] or float(row['actual_million'])!=float(labels[row['record_key']]['price_million']):raise ValueError('Validation labels differ from source')
    cohort_key=next(k for k in manifest['input_sha256'] if '/apartment_extension_review/' in k and k.endswith('/collection_holdout.csv'))
    raw=data.read(job.BASE.parents[2]/cohort_key)
    held,control,masked=job.holdout_features(raw)
    collection_lookup={}
    for config in ['frozen_v6',*job.CONFIGS]:
        if config=='frozen_v6':
            folder=job.BASE.parents[1]/'artifacts/v6/models/all'
            model_path=folder/'category_3_xgboost.json';schema_path=folder/'category_3_schema.json'
        else:
            info=report['configurations'][config]['categories'][data.CATEGORIES[2]]
            model_path=run/info['model_file'];schema_path=run/info['schema_file']
        model=xgb.Booster();model.load_model(model_path)
        spec=json.loads(schema_path.read_text(encoding='utf8'))
        values=masked if config=='mask_conflicting_bedrooms' else control
        matrix=xgb.DMatrix(job.features.encode(held,values,spec),feature_names=spec['feature_names'])
        prediction=np.exp(np.clip(model.predict(matrix),-20,30))
        collection_lookup.update({(config,r['record_key']):float(p) for r,p in zip(held,prediction)})
    for row in data.read(run/'collection_predictions.csv'):
        np.testing.assert_allclose(float(row['predicted_million']),collection_lookup[row['config'],row['record_key']],rtol=1e-7,atol=1e-6)
    collection_rows=data.read(run/'collection_predictions.csv')
    if {(r['config'],r['record_key']) for r in collection_rows}!=set(collection_lookup):raise ValueError('Missing collection prediction keys')
    actual={r['record_key']:r for r in raw}
    for row in collection_rows:
        if row['category']!=actual[row['record_key']]['category'] or float(row['actual_million'])!=float(actual[row['record_key']]['price_million']):raise ValueError('Collection labels differ from source')
    for filename,section in [('validation_predictions.csv','configurations'),('collection_predictions.csv','collection')]:
        rows=data.read(run/filename)
        for config in {r['config'] for r in rows}:
            selected=[r for r in rows if r['config']==config]
            score=data.scores([float(r['actual_million']) for r in selected],[float(r['predicted_million']) for r in selected])
            expected=report[section][config]['aggregate_validation'] if section=='configurations' else report[section][config]
            for key,value in score.items():
                if value is None:
                    if expected[key] is not None:raise ValueError('Metric differs')
                else:np.testing.assert_allclose(value,expected[key],rtol=1e-10,atol=1e-10)
            if len(selected)!=len({r['record_key'] for r in selected}):raise ValueError('Repeated prediction IDs')
    receipt=json.loads((job.BASE/manifest['receipt_file']).read_text(encoding='utf8'))
    if receipt['status']!='evaluated' or receipt['metrics_sha256']!=data.sha(run/'metrics.json'):raise ValueError('Evaluation receipt mismatch')
    cohort_file=next(k for k in manifest['input_sha256'] if '/apartment_extension_review/' in k and k.endswith('/cohort_lock.json'))
    if receipt['trial_run']!=run.name or receipt['cohort_lock_sha256']!=data.sha(job.BASE.parents[2]/cohort_file) or set(receipt['members'])!=set(actual):raise ValueError('Evaluation receipt identity mismatch')
    train=data.read(prepared/'train.csv')
    collection=data.read(run/'collection_predictions.csv')
    if {r['record_key'] for r in train}&{r['record_key'] for r in collection}:raise ValueError('Holdout leaked into train')
    print(json.dumps(dict(verified=True,run=run.name,train=2213,validation=299,collection=report['collection_n'],
        validation_predictions=len(data.read(run/'validation_predictions.csv')),collection_predictions=len(collection),production_model_changed=False)))


if __name__=='__main__':verify()
