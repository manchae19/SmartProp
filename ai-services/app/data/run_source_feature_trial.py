"""Fit/replay two fixed feature arms using only the clean historical train."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import uuid

import numpy as np
import xgboost as xgb
import source_asset_features as feature
import train_nested_price_trial as previous
from source_feature_io import atomic_json, writer_lock

data = previous.data
trial = previous.trial
BASE = data.BASE
OUT = BASE / 'processed/source_feature_trial'
PROTOCOL = BASE / 'SOURCE_FEATURE_TRIAL_PROTOCOL.md'
POLICY = dict(arms=['v6_all', 'source_enriched'], folds=3, salt='source-feature-v1/fold/', rounds=300,
    params=trial.params(trial.CONTROL), gate=trial.PROTOCOL['final_gate'], min_street_fit_groups=feature.MIN_STREET_FIT_GROUPS,
    train_only=True, new_batch_used=False, external_cohorts_scored=False, automatic_promotion=False)


def context():
    rows, base_values, inputs, protected = previous.context()
    history = BASE / 'processed/remaining_diversity_review/runs/1d45c8941172a52d/all_listings_after_review.csv'
    origins = {r['record_key']: r for r in data.read(history)}
    extras, proofs = {}, []
    for r in rows:
        values, evidence = feature.original_features(r, origins[r['record_key']])
        extras[r['record_key']] = values
        proofs += [dict(record_key=r['record_key'], category=r['category'], **p) for p in evidence]
    if sum(bool(v['street_raw']) for v in extras.values()) != 424:
        raise ValueError('Original street-hint cohort differs')
    paths = [Path(__file__), Path(feature.__file__), Path(feature.claims.__file__),
        BASE/'source_feature_io.py', PROTOCOL, history]
    inputs.update({str(p.resolve()): data.sha(p) for p in paths})
    return rows, base_values, extras, proofs, inputs, protected


def membership(rows):
    result = []
    for category in data.CATEGORIES:
        part = [r for r in rows if r['category'] == category]
        for fold, fit, held in trial.partition(part, POLICY['folds'], POLICY['salt']):
            result += [dict(category=category, fold=fold, role=role, record_key=r['record_key'], pipeline_group=r['pipeline_group'])
                       for role, members in [('fit', fit), ('held', held)] for r in members]
    return result


class Store:
    def __init__(self, root, base_values, extras, verify=False):
        self.root, self.base_values, self.extras, self.verify = root, base_values, extras, verify
        self.records = []
        self.saved = json.loads((root/'models.json').read_text(encoding='utf8')) if verify else []

    def evaluate(self, key, arm, category, fold, fit, held):
        spec = feature.feature_spec(fit, self.base_values, self.extras, category, arm)
        record = dict(key=key, arm=arm, category=category, fold=fold, model='models/'+key+'.json',
            schema='models/'+key+'_schema.json', fit_keys=[r['record_key'] for r in fit], held_keys=[r['record_key'] for r in held])
        matrix = xgb.DMatrix(feature.encode(held, self.base_values, self.extras, spec),
                             feature_names=spec['feature_names'], nthread=4)
        if self.verify:
            if len(self.records) >= len(self.saved) or self.saved[len(self.records)] != record:
                raise ValueError('Model membership differs')
            if json.loads((self.root/record['schema']).read_text(encoding='utf8')) != spec:
                raise ValueError('Fit-only feature vocabulary differs')
            booster = xgb.Booster()
            booster.load_model(self.root/record['model'])
            booster.set_param(dict(nthread=4, device='cpu'))
            if booster.num_boosted_rounds() != POLICY['rounds']:
                raise ValueError('Model rounds differ')
            if json.loads(booster.save_config())['learner']['objective']['name'] != POLICY['params']['objective']:
                raise ValueError('Model objective differs')
        else:
            fit_matrix = xgb.DMatrix(feature.encode(fit, self.base_values, self.extras, spec),
                label=np.log([float(r['price_million']) for r in fit]), feature_names=spec['feature_names'], nthread=4)
            booster = xgb.train(POLICY['params'], fit_matrix, num_boost_round=POLICY['rounds'])
            (self.root/'models').mkdir(exist_ok=True)
            booster.save_model(self.root/record['model'])
            atomic_json(self.root/record['schema'], spec)
            print(json.dumps(dict(model=key, fit=len(fit), held=len(held), features=len(spec['feature_names']))), flush=True)
        self.records.append(record)
        return np.exp(np.clip(booster.predict(matrix).astype(float), -20, 30))


def study(rows, store):
    predictions = []
    for i, category in enumerate(data.CATEGORIES):
        part = [r for r in rows if r['category'] == category]
        for fold, fit, held in trial.partition(part, POLICY['folds'], POLICY['salt']):
            for method, arm in [('control', 'v6_all'), ('selected', 'source_enriched'), ('median_unit_location', None)]:
                p = (trial.median_baseline(fit, held) if arm is None else
                     store.evaluate(f'cat{i}_fold{fold}_{arm}', arm, category, fold, fit, held))
                predictions += [dict(category=category, outer_fold=fold, method=method,
                    record_key=r['record_key'], pipeline_group=r['pipeline_group'],
                    actual_million=float(r['price_million']), predicted_million=float(value)) for r, value in zip(held, p)]
    if store.verify and store.records != store.saved:
        raise ValueError('Unexpected model records')
    metrics, folds = trial.evaluate(predictions)
    gate = trial.nomination_gate(metrics, folds)
    return dict(predictions=predictions, metrics=metrics, fold_metrics=folds), dict(
        models=store.records, nomination_gate=gate,
        summary=dict(train_groups=len(rows), category_groups=dict(Counter(r['category'] for r in rows)),
            models=len(store.records), prediction_rows=len(predictions), gate_passed=gate['passed'],
            release_changed=False, external_scored=False, final_models_fitted=0,
            decision='research_candidate_needs_new_test' if gate['passed'] else 'keep_v6_no_nomination'))


def evidence_tables(rows, extras, proofs):
    features = [dict(record_key=r['record_key'], category=r['category'], **extras[r['record_key']]) for r in rows]
    coverage = [dict(category=cat, field=f, groups=sum(r['category']==cat for r in rows),
        present=sum(bool(str(extras[r['record_key']][f])) for r in rows if r['category']==cat))
        for cat in data.CATEGORIES for f in feature.FIELDS]
    return dict(features=features, evidence=proofs, coverage=coverage,
                street_review=[r for r in features if r['street_raw']], fold_membership=membership(rows))


def write_tables(root, tables):
    for name, rows in tables.items():
        fields, values = previous.csv_table(rows)
        data.write_csv(root/(name+'.csv'), values, fields)


def run_id(inputs):
    obj = dict(inputs=inputs, policy=POLICY, versions=previous.versions())
    return hashlib.sha256(previous.canonical(obj).encode()).hexdigest()[:16]


def verify(root):
    rows, base_values, extras, proofs, inputs, protected = context()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf8'))
    if root.name != run_id(inputs) or manifest['input_sha256'] != inputs or manifest['protected_sha256'] != protected:
        raise ValueError('Trial provenance differs')
    if manifest['output_sha256'] != data.outputs(root):
        raise ValueError('Trial output inventory/hash differs')
    if json.loads((root/'policy.json').read_text(encoding='utf8')) != dict(POLICY, versions=previous.versions()):
        raise ValueError('Trial policy differs')
    store = Store(root, base_values, extras, verify=True)
    tables, objects = study(rows, store)
    tables.update(evidence_tables(rows, extras, proofs))
    for name, values in tables.items():
        previous.compare_csv(data.read(root/(name+'.csv')), previous.csv_table(values)[1])
    for name, value in objects.items():
        if json.loads((root/(name+'.json')).read_text(encoding='utf8')) != value:
            raise ValueError('Trial metrics/decision differs: '+name)
    previous.check_unchanged(inputs, protected)
    return dict(verified=True, run_id=root.name, models=len(store.records), no_new_fitting=True,
                manifest_sha256=data.sha(root/'manifest.json'))


def run():
    with writer_lock(OUT):
        rows, base_values, extras, proofs, inputs, protected = context()
        target = OUT/'runs'/run_id(inputs)
        if target.exists():
            return verify(target)
        stage = OUT/'runs'/('.building_'+uuid.uuid4().hex)
        stage.mkdir(parents=True)
        # Materialize the complete split and feature provenance before first fit.
        write_tables(stage, evidence_tables(rows, extras, proofs))
        atomic_json(stage/'policy.json', dict(POLICY, versions=previous.versions()))
        atomic_json(stage/'input_lock.json', dict(input_sha256=inputs, protected_sha256=protected))
        store = Store(stage, base_values, extras)
        tables, objects = study(rows, store)
        write_tables(stage, tables)
        for name, value in objects.items():
            atomic_json(stage/(name+'.json'), value)
        previous.check_unchanged(inputs, protected)
        atomic_json(stage/'manifest.json', dict(input_sha256=inputs, protected_sha256=protected, output_sha256=data.outputs(stage)))
        stage.rename(target)
        result = verify(target)
        atomic_json(OUT/'latest.json', dict(run='runs/'+target.name))
        return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    root = OUT/json.loads((OUT/'latest.json').read_text(encoding='utf8'))['run'] if args.verify else None
    print(json.dumps(verify(root) if args.verify else run(), ensure_ascii=False, indent=2))
