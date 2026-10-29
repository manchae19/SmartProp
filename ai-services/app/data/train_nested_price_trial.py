"""Fit or replay a preregistered nested CV study on clean train only."""
import argparse
from collections import Counter
from contextlib import contextmanager
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import platform
import uuid

import numpy as np
import xgboost as xgb
import measure_training_learning_curve as frozen_context
import nested_price_trial as trial
import property_text_features_v6 as feature
import training_v3_common as data
from market_observations import canonical

BASE=data.BASE
OUT=BASE/'processed/nested_price_trial'
PROTOCOL_FILE=BASE/'NESTED_PRICE_TRIAL_PROTOCOL.md'
CURRENT=BASE/'processed/property_source_adjudication/runs/4fd1c013b621ac45'


def context():
    rows,features,inputs,protected=frozen_context.context()
    list(trial.partition(rows,3,trial.PROTOCOL['outer_salt']))
    manifest=json.loads((CURRENT/'manifest.json').read_text(encoding='utf8'))
    data.verify(manifest['output_sha256'],CURRENT)
    for relative,expected in manifest['protected_sha256'].items():
        if data.sha(BASE/relative)!=expected:raise ValueError('Protected source review input changed')
    paths=[Path(__file__),Path(trial.__file__),PROTOCOL_FILE,CURRENT/'manifest.json',
           CURRENT/'experiment_reservation.json',CURRENT/'fresh_evaluation_RESERVED_DO_NOT_TRAIN.csv']
    inputs.update({str(p):data.sha(p) for p in paths})
    protected.update({str(CURRENT/name):sha for name,sha in manifest['output_sha256'].items()})
    return rows,features,inputs,protected


def versions():
    return dict(python=platform.python_version(),numpy=np.__version__,xgboost=xgb.__version__)


def fingerprint(inputs):
    return hashlib.sha256(canonical(dict(inputs=inputs,protocol=trial.PROTOCOL,versions=versions())).encode()).hexdigest()[:16]


def check_unchanged(inputs,protected):
    for path,expected in {**inputs,**protected}.items():
        if data.sha(path)!=expected:raise ValueError('Trial input changed: '+path)
    current={str(p) for p in (BASE/'processed/evaluation_ledger').glob('*.json')}
    recorded={p for p in protected if 'evaluation_ledger' in p}
    if current!=recorded:raise ValueError('Evaluation ledger inventory changed')


@contextmanager
def writer_lock(root):
    root.mkdir(parents=True,exist_ok=True)
    path=root/'writer.lock';token=uuid.uuid4().hex
    created=None;published=False
    try:
        try:stream=path.open('x',encoding='utf8')
        except FileExistsError as exc:raise ValueError('Another trial writer owns the lock') from exc
        with stream:
            created=os.fstat(stream.fileno())
            json.dump(dict(pid=os.getpid(),owner=token),stream)
        published=True
        yield
    finally:
        if created is not None:
            try:
                current=path.stat()
                if (current.st_dev,current.st_ino)==(created.st_dev,created.st_ino):
                    try:owned=json.loads(path.read_text(encoding='utf8')).get('owner')==token
                    except json.JSONDecodeError:owned=not published
                    if owned:path.unlink()
            except FileNotFoundError:pass


class ModelArtifacts:
    def __init__(self,directory,features,verify=False):
        self.directory=directory;self.features=features;self.verify=verify
        self.records=[];self.predictions=[]
        self.saved=json.loads((directory/'models.json').read_text(encoding='utf8')) if verify else []

    def evaluate(self,key,arm,fit,held,*,category,phase,outer_fold=-1,inner_fold=-1):
        spec=feature.feature_spec(fit,category,'all')
        schema=dict(arm=arm,features=spec,params=trial.params(arm),rounds=trial.PROTOCOL['rounds'],
                    target='natural_log_price_per_sqm' if arm=='log_unit_squared' else 'natural_log_total_price')
        record=dict(key=key,arm=arm,category=category,phase=phase,outer_fold=outer_fold,inner_fold=inner_fold,
            train_keys=[r['record_key'] for r in fit],held_keys=[r['record_key'] for r in held],
            model='models/'+key+'.json',schema='models/'+key+'_schema.json')
        if self.verify:
            if len(self.records)>=len(self.saved) or self.saved[len(self.records)]!=record:raise ValueError('Nested model membership/selection differs')
            if json.loads((self.directory/record['schema']).read_text(encoding='utf8'))!=schema:raise ValueError('Subset-only vocabulary/schema differs')
            booster=xgb.Booster();booster.load_model(self.directory/record['model'])
            booster.set_param(dict(nthread=4,device='cpu'))
            objective=json.loads(booster.save_config())['learner']['objective']['name']
            if objective!=trial.params(arm)['objective'] or booster.num_boosted_rounds()!=trial.PROTOCOL['rounds']:
                raise ValueError('Model objective/rounds differ')
        else:
            matrix=xgb.DMatrix(feature.encode(fit,self.features,spec),label=trial.labels(fit,arm),feature_names=spec['feature_names'],nthread=4)
            booster=xgb.train(trial.params(arm),matrix,num_boost_round=trial.PROTOCOL['rounds'])
            (self.directory/'models').mkdir(exist_ok=True)
            booster.save_model(self.directory/record['model']);data.write_json(self.directory/record['schema'],schema)
        matrix=xgb.DMatrix(feature.encode(held,self.features,spec),feature_names=spec['feature_names'],nthread=4)
        predicted=trial.inverse(booster.predict(matrix),held,arm)
        self.records.append(record)
        self.predictions += [dict(model_key=key,phase=phase,record_key=r['record_key'],
            actual_million=float(r['price_million']),predicted_million=float(p)) for r,p in zip(held,predicted)]
        if not self.verify:print(json.dumps(dict(model=key,phase=phase,fit_groups=len(fit),held_groups=len(held))),flush=True)
        return predicted

    def finish(self):
        if self.verify and self.records!=self.saved:raise ValueError('Unexpected/missing model records')


def inner_selection(rows,store,*,category,cat_index,outer_fold,folds,salt,phase):
    scores=[]
    for fold,fit,held in trial.partition(rows,folds,salt):
        for arm in trial.ARMS:
            key=f'cat{cat_index}_{phase}{outer_fold}_fold{fold}_{arm}'
            predicted=store.evaluate(key,arm,fit,held,category=category,phase=phase,outer_fold=outer_fold,inner_fold=fold)
            error=np.abs(np.asarray([float(r['price_million']) for r in held])-predicted)
            scores.append(dict(category=category,phase=phase,outer_fold=outer_fold,inner_fold=fold,arm=arm,
                               n=len(held),absolute_error_sum=float(error.sum())))
    selected,maes=trial.choose(scores)
    return selected,maes,scores


def study(rows,features,store):
    outer_predictions=[];inner_scores=[];selections=[]
    for cat_index,category in enumerate(data.CATEGORIES,1):
        category_rows=[r for r in rows if r['category']==category]
        for outer,fit,held in trial.partition(category_rows,trial.PROTOCOL['outer_folds'],trial.PROTOCOL['outer_salt']):
            selected,maes,scores=inner_selection(fit,store,category=category,cat_index=cat_index,outer_fold=outer,
                folds=trial.PROTOCOL['inner_folds'],salt=trial.PROTOCOL['inner_salt']+str(outer)+'/',phase='inner')
            inner_scores+=scores
            selections.append(dict(category=category,outer_fold=outer,selected_arm=selected,inner_mae_million=maes))
            control=store.evaluate(f'cat{cat_index}_outer{outer}_{trial.CONTROL}',trial.CONTROL,fit,held,
                category=category,phase='outer',outer_fold=outer)
            chosen=control if selected==trial.CONTROL else store.evaluate(f'cat{cat_index}_outer{outer}_{selected}',selected,fit,held,
                category=category,phase='outer',outer_fold=outer)
            simple=trial.median_baseline(fit,held)
            for method,predicted in [('control',control),('selected',chosen),('median_unit_location',simple)]:
                outer_predictions += [dict(category=category,outer_fold=outer,method=method,record_key=r['record_key'],
                    pipeline_group=r['pipeline_group'],actual_million=float(r['price_million']),predicted_million=float(p)) for r,p in zip(held,predicted)]
    metrics,fold_metrics=trial.evaluate(outer_predictions)
    gate=trial.nomination_gate(metrics,fold_metrics)
    final=[];final_scores=[]
    if gate['passed']:
        for cat_index,category in enumerate(data.CATEGORIES,1):
            part=sorted([r for r in rows if r['category']==category],key=lambda r:r['record_key'])
            selected,maes,scores=inner_selection(part,store,category=category,cat_index=cat_index,outer_fold=-1,
                folds=3,salt=trial.PROTOCOL['final_salt'],phase='final_selection')
            final_scores+=scores
            # These predictions are training replay only, never a test metric.
            store.evaluate(f'cat{cat_index}_final_{selected}',selected,part,part[:20],category=category,phase='final_training_replay')
            final.append(dict(category=category,arm=selected,cv_mae_million=maes,model=f'models/cat{cat_index}_final_{selected}.json'))
    store.finish()
    priorities=trial.collection_priorities(rows,features,outer_predictions)
    summary=dict(train_groups=len(rows),category_counts=dict(Counter(r['category'] for r in rows)),
        models=len(store.records),model_prediction_rows=len(store.predictions),outer_prediction_rows=len(outer_predictions),
        selected_arm_counts=dict(Counter(r['selected_arm'] for r in selections)),
        gate_passed=gate['passed'],candidate_final_models=len(final),
        decision='offline_candidate_requires_fresh_review' if final else 'keep_v6_no_candidate_promotion',
        train_only=True,dev_validation_scored=False,pilot_scored=False,new_snapshots_used=False,
        production_model_changed=False,forecast=False,
        limitation='Exploratory internal nested CV on previously studied training data; not independent external validation.')
    tables=dict(inner_scores=inner_scores,outer_predictions=outer_predictions,metrics=metrics,fold_metrics=fold_metrics,
                collection_priorities=priorities,final_selection_scores=final_scores,model_predictions=store.predictions)
    objects=dict(summary=summary,selections=selections,nomination_gate=gate,final_candidates=final,models=store.records)
    return tables,objects


def csv_table(rows):
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ['category','arm','n']
    table=[{k:json.dumps(row.get(k),ensure_ascii=False,sort_keys=True) if isinstance(row.get(k),(dict,list))
            else '' if row.get(k) is None else str(row.get(k)) for k in fields} for row in rows]
    return fields,table


def compare_csv(actual,expected):
    numeric={'actual_million','predicted_million','absolute_error_sum','mae_million','rmse_million',
             'mape_pct','median_ape_pct','within_20pct','r2','within20_pct'}
    if len(actual)!=len(expected):raise ValueError('Prediction/table row count differs')
    for old,new in zip(actual,expected):
        if old.keys()!=new.keys():raise ValueError('Prediction/table fields differ')
        for key,value in new.items():
            if old[key]==value:continue
            if key not in numeric:raise ValueError('Prediction/table identity differs: '+key)
            try:
                a,b=float(old[key]),float(value)
            except (TypeError,ValueError):raise ValueError('Prediction/table identity differs: '+key) from None
            if not math_isclose(a,b):raise ValueError('Prediction/table numeric value differs: '+key)


def math_isclose(a,b):
    return np.isfinite(a) and np.isfinite(b) and abs(a-b)<=1e-8+1e-9*max(abs(a),abs(b))


def verify(directory):
    rows,features,inputs,protected=context()
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf8'))
    if manifest['input_sha256']!=inputs or manifest['protected_sha256']!=protected:raise ValueError('Trial source identity differs')
    if directory.name!=fingerprint(inputs):raise ValueError('Trial fingerprint differs')
    if manifest['output_sha256']!=data.outputs(directory):raise ValueError('Trial output inventory/hash differs')
    if json.loads((directory/'protocol.json').read_text(encoding='utf8'))!=dict(trial.PROTOCOL,versions=versions()):raise ValueError('Trial protocol differs')
    store=ModelArtifacts(directory,features,verify=True)
    tables,objects=study(rows,features,store)
    for name,expected in tables.items():compare_csv(data.read(directory/(name+'.csv')),csv_table(expected)[1])
    for name,expected in objects.items():
        if json.loads((directory/(name+'.json')).read_text(encoding='utf8'))!=expected:raise ValueError('Trial JSON/metric/selection differs: '+name)
    check_unchanged(inputs,protected)
    receipt=dict(verified=True,run_id=directory.name,models=len(store.records),predictions=len(store.predictions),
        no_new_fitting=True,source_manifest_sha256=data.sha(directory/'manifest.json'),
        verified_at_utc=datetime.now(timezone.utc).isoformat())
    print(json.dumps(receipt,ensure_ascii=False,indent=2))
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    if args.verify:
        verify(OUT/json.loads((OUT/'latest.json').read_text(encoding='utf8'))['run']);return
    with writer_lock(OUT):
        rows,features,inputs,protected=context();run_id=fingerprint(inputs);target=OUT/'runs'/run_id
        if target.exists():verify(target);return
        stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
        data.write_json(stage/'protocol.json',dict(trial.PROTOCOL,versions=versions()))
        data.write_json(stage/'input_lock.json',dict(input_sha256=inputs,protected_sha256=protected))
        store=ModelArtifacts(stage,features)
        tables,objects=study(rows,features,store)
        for name,values in tables.items():
            fields,table=csv_table(values);data.write_csv(stage/(name+'.csv'),table,fields)
        for name,value in objects.items():data.write_json(stage/(name+'.json'),value)
        (stage/'README.md').write_text('# Thử cách học giá, chỉ trong train\n\n'
            '3 outer folds / 2 inner folds theo nhóm; 3 arm cố định, 300 rounds, vocabulary fit-only. '
            'Kết quả là kiểm chứng nội bộ trên train đã từng nghiên cứu, không phải benchmark độc lập. '
            'Không chấm 299 validation/pilot/5 nhóm mới hoặc thay model v6. '
            'Xem nomination_gate.json, metrics.csv và collection_priorities.csv trước khi diễn giải.\n',encoding='utf8')
        check_unchanged(inputs,protected)
        data.write_json(stage/'manifest.json',dict(input_sha256=inputs,protected_sha256=protected,output_sha256=data.outputs(stage)))
        stage.rename(target)
        receipt=verify(target)
        data.write_json(OUT/'verification.json',receipt)
        data.write_json(OUT/'latest.json',dict(run='runs/'+run_id))
        print(json.dumps(objects['summary'],ensure_ascii=False,indent=2));print(target)


if __name__=='__main__':main()
