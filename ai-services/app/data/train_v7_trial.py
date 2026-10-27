"""Fixed bedroom-conflict ablation; locked collection is evaluated once."""
import hashlib
import json
import platform
import uuid
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as data
import property_text_features_v6 as features
import train_training_v3 as experiment
import prepare_v7_trial as preparation
import apartment_followup_rules as rules

BASE=preparation.BASE
OUT=BASE/'processed/models_v7_trial'
LEDGER=BASE/'processed/evaluation_ledger'
CONFIGS=['control_clean_v6_all','mask_conflicting_bedrooms']


def latest(root):return root/json.loads((root/'latest.json').read_text(encoding='utf8'))['run']


def holdout_features(rows):
    prepared=[];control={};masked={}
    for raw in rows:
        parts=json.loads(raw['source_location_parts'])
        ward=next((p.split(' ',1)[1] for p in parts if p.startswith(('Phường ','Xã '))),'')
        row=dict(record_key=raw['record_key'],source=raw['source'],category=raw['category'],
            location_feature=raw['location_feature'],ward_source=data.normalized(ward),
            area_sqm=raw['area_sqm'],rooms=raw['rooms'],price_million=raw['price_million'])
        origin=dict(title=raw['title'],raw_json=json.dumps(dict(source_category=raw['source_category'])))
        values,_=features.extract(row,origin,body=rules.subject(raw['description']),body_sha256=raw['response_sha256'])
        control[row['record_key']]=values
        masked[row['record_key']]=dict(values,rooms_completed='' if 'rooms_completed' in values['conflict_fields'].split(';') else values['rooms_completed'])
        prepared.append(row)
    return prepared,control,masked


def main():
    preparation.main()
    prepared=latest(preparation.OUT);cohort=latest(preparation.cohort.OUT)
    ready=json.loads((prepared/'summary.json').read_text(encoding='utf8'))
    if not ready['evaluation_gate_passed']:
        print('No training: corrected holdout gate not met');return
    parts={s:data.read(prepared/(s+'.csv')) for s in ['train','validation']}
    feature_sets={CONFIGS[0]:{r['record_key']:r for r in data.read(prepared/'features_control.csv')},
                  CONFIGS[1]:{r['record_key']:r for r in data.read(prepared/'features_masked.csv')}}
    raw_holdout=data.read(cohort/'collection_holdout.csv')
    holdout,holdout_control,holdout_masked=holdout_features(raw_holdout)
    if any(r['category']!=data.CATEGORIES[2] for r in holdout):raise ValueError('This pilot is apartment-only')
    train_keys={r['record_key'] for r in parts['train']+parts['validation']}
    if train_keys&{r['record_key'] for r in holdout}:raise ValueError('Cohort IDs leaked into training/validation')
    release=BASE.parents[1]/'artifacts/v6'
    paths=[Path(__file__),Path(features.__file__),Path(data.__file__),Path(experiment.__file__),prepared/'manifest.json',prepared/'protocol.json',
        prepared/'train.csv',prepared/'validation.csv',prepared/'features_control.csv',prepared/'features_masked.csv',
        cohort/'manifest.json',cohort/'cohort_lock.json',cohort/'collection_holdout.csv',release/'manifest.json']
    paths+=list((release/'models/all').glob('*.json'))
    hashes={p.relative_to(BASE.parents[2]).as_posix():data.sha(p) for p in paths}
    versions=dict(python=platform.python_version(),numpy=np.__version__,xgboost=xgb.__version__)
    run_id=hashlib.sha256(json.dumps(dict(inputs=hashes,protocol=preparation.PROTOCOL,versions=versions),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/run_id
    if target.exists():
        import verify_v7_trial
        verify_v7_trial.verify(target);print('Existing fixed trial verified');return
    lock_sha=data.sha(cohort/'cohort_lock.json');receipt=LEDGER/(lock_sha+'.json')
    if receipt.exists():raise ValueError('Cohort already evaluated/reserved; do not train another configuration against it')
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    (stage/'protocol.json').write_text(json.dumps(preparation.PROTOCOL,ensure_ascii=False,indent=2),encoding='utf8')
    scores={};validation_predictions=[];models={}
    for config in CONFIGS:
        rows=[];categories={}
        for index,category in enumerate(data.CATEGORIES,1):
            train=[r for r in parts['train'] if r['category']==category];val=[r for r in parts['validation'] if r['category']==category]
            spec=features.feature_spec(train,category,'all')
            X=features.encode(train,feature_sets[config],spec);V=features.encode(val,feature_sets[config],spec)
            dt=xgb.DMatrix(X,label=np.log([float(r['price_million']) for r in train]),feature_names=spec['feature_names'])
            dv=xgb.DMatrix(V,label=np.log([float(r['price_million']) for r in val]),feature_names=spec['feature_names'])
            print(config+': '+category,flush=True)
            trained=xgb.train(experiment.PARAMS,dt,num_boost_round=preparation.PROTOCOL['max_rounds'],evals=[(dv,'validation')],
                custom_metric=experiment.log_mae,early_stopping_rounds=preparation.PROTOCOL['early_stopping_rounds'],verbose_eval=False)
            best=trained[:trained.best_iteration+1]
            folder=stage/'models'/config;folder.mkdir(parents=True,exist_ok=True)
            model_path=folder/f'category_{index}.json';schema_path=folder/f'category_{index}_schema.json'
            best.save_model(model_path);data.write_json(schema_path,spec)
            restored=xgb.Booster();restored.load_model(model_path)
            np.testing.assert_allclose(restored.predict(dv),best.predict(dv),rtol=1e-7,atol=1e-7)
            predictions=np.exp(np.clip(best.predict(dv),-20,30))
            for row,p in zip(val,predictions):rows.append(dict(record_key=row['record_key'],category=category,config=config,split='development_validation',actual_million=float(row['price_million']),predicted_million=float(p)))
            categories[category]=dict(train_n=len(train),validation_n=len(val),best_iteration=trained.best_iteration,
                model_file=model_path.relative_to(stage).as_posix(),schema_file=schema_path.relative_to(stage).as_posix(),
                validation=data.scores([float(r['price_million']) for r in val],predictions))
            models[config,category]=(best,spec)
        scores[config]=dict(categories=categories,aggregate_validation=data.scores([r['actual_million'] for r in rows],[r['predicted_million'] for r in rows]))
        validation_predictions.extend(rows)
    # Reserve the fixed cohort only after fitting/saving both configurations.
    LEDGER.mkdir(exist_ok=True)
    evaluation=dict(cohort_lock_sha256=lock_sha,trial_run=run_id,protocol_sha256=data.sha(stage/'protocol.json'),
        status='evaluation_started',members=[r['record_key'] for r in holdout],fresh_after_this_run=False)
    with receipt.open('x',encoding='utf8') as stream:json.dump(evaluation,stream,ensure_ascii=False,indent=2)
    collection_predictions=[];collection_scores={}
    frozen=xgb.Booster();frozen.load_model(release/'models/all/category_3_xgboost.json')
    frozen_spec=json.loads((release/'models/all/category_3_schema.json').read_text(encoding='utf8'))
    evaluation_models={'frozen_v6':(frozen,frozen_spec,holdout_control),
        CONFIGS[0]:(*models[CONFIGS[0],data.CATEGORIES[2]],holdout_control),
        CONFIGS[1]:(*models[CONFIGS[1],data.CATEGORIES[2]],holdout_masked)}
    for name,(model,spec,values) in evaluation_models.items():
        matrix=xgb.DMatrix(features.encode(holdout,values,spec),feature_names=spec['feature_names'])
        prediction=np.exp(np.clip(model.predict(matrix),-20,30))
        collection_scores[name]=data.scores([float(r['price_million']) for r in holdout],prediction)
        for row,p in zip(holdout,prediction):collection_predictions.append(dict(record_key=row['record_key'],category=row['category'],config=name,split='collection_pilot',actual_million=float(row['price_million']),predicted_million=float(p)))
    data.write_csv(stage/'validation_predictions.csv',validation_predictions,list(validation_predictions[0]))
    data.write_csv(stage/'collection_predictions.csv',collection_predictions,list(collection_predictions[0]))
    data.write_csv(stage/'collection_features_control.csv',[dict(record_key=k,**v) for k,v in holdout_control.items()],['record_key',*next(iter(holdout_control.values()))])
    report=dict(protocol=preparation.PROTOCOL,xgboost_params_used=experiment.PARAMS,versions=versions,train_n=2213,validation_n=299,collection_n=len(holdout),
        configurations=scores,collection=collection_scores,production_model_changed=False,automatic_deployment=False,
        independent_benchmark=False,transaction_prices=False,collection_cohort_reusable_as_fresh=False,
        limitation='Small same-source asking-price pilot, apartment-only. Do not tune on its scores or infer accuracy for houses/land.')
    data.write_json(stage/'metrics.json',report)
    (stage/'README.md').write_text('# Thử nghiệm v7 — số phòng mâu thuẫn để missing\n\n'
        'Hai cấu hình chốt trước điểm số; 2.213 train và 299 validation phát triển. '
        f'Kiểm chứng thăm dò {len(holdout)} nhóm căn hộ, không ghép vào train. '
        'Sau lần này cohort đã chấm, không còn là tập mới cho tối ưu cấu hình. '
        'Model/API v6 giữ nguyên; xem metrics.json.\n',encoding='utf8')
    for path,value in hashes.items():
        if data.sha(BASE.parents[2]/path)!=value:raise ValueError('Input changed during trial')
    data.write_json(stage/'manifest.json',dict(input_sha256=hashes,output_sha256={p.relative_to(stage).as_posix():data.sha(p) for p in stage.rglob('*') if p.is_file()},receipt_file=receipt.relative_to(BASE).as_posix()))
    stage.rename(target)
    evaluation['status']='evaluated';evaluation['metrics_sha256']=data.sha(target/'metrics.json')
    preparation.cohort.collector.source.atomic(receipt,evaluation)
    preparation.cohort.collector.source.atomic(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps(dict(run=run_id,validation={k:v['aggregate_validation'] for k,v in scores.items()},collection=collection_scores),ensure_ascii=False,indent=2))


if __name__=='__main__':main()
