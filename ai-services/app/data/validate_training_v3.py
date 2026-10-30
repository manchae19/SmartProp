"""Independently reconcile v3 cohorts, labels, saved-model predictions and old artifacts."""
import json
from datetime import datetime, timezone

import numpy as np
import xgboost as xgb
import train_smartprop_baseline as baseline
from training_v3_common import (BASE, PROCESSED, CATEGORIES, read, sha, write_json,
                                validate_parts, schema, encode, scores)


def latest(name):
    directory = PROCESSED/name
    return directory/json.loads((directory/'latest.json').read_text())['run']


def main():
    data, models = latest('training_v3'), latest('models_v3_validation')
    dm = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    mm = json.loads((models/'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((data/'summary.json').read_text(encoding='utf-8'))
    report = json.loads((models/'metrics.json').read_text(encoding='utf-8'))
    assert dm['complete'] and mm['complete']
    assert report['dataset_run'] == data.relative_to(BASE).as_posix()
    assert report['test_evaluated'] is False
    pipeline = BASE/summary['pipeline_run']
    pm = json.loads((pipeline/'manifest.json').read_text(encoding='utf-8'))
    # Hash each actual file once, even when multiple manifests protect it.
    expected = {}
    for root, manifest in [(data, dm), (models, mm), (BASE, pm)]:
        for field in ('input_sha256', 'protected_sha256', 'output_sha256'):
            for relative, digest in manifest.get(field, {}).items():
                path = (root if field == 'output_sha256' else BASE)/relative
                path = path.resolve()
                if path in expected and expected[path] != digest:
                    raise ValueError('Conflicting frozen hashes: '+str(path))
                expected[path] = digest
    for path, digest in expected.items():
        if sha(path) != digest:
            raise ValueError('Artifact changed: '+str(path))
    parts = {s:read(data/(s+'.csv')) for s in ('train', 'validation')}
    reserved = read(data/'reserved_holdout_registry.csv')
    registry = read(data/'split_registry.csv')
    validate_parts(parts, {r['pipeline_group'] for r in reserved})
    allrows = read(pipeline/'all_listings.csv')
    bykey = {r['record_key']:r for r in allrows}
    eligible = {r['record_key'] for r in allrows if r['pipeline_status'] == 'eligible'}
    assert len(registry) == len({r['record_key'] for r in registry}) == len(eligible)
    assert {r['record_key'] for r in registry} == eligible
    assert len({r['pipeline_group'] for r in registry}) == len(registry)
    train_keys = {r['record_key'] for r in allrows if r['training_allowed'] == 'True'}
    validation_keys = {r['record_key'] for r in allrows if r['pipeline_status'] == 'eligible'
        and 'validation' in r['reserved_splits'].split(';')
        and 'test' not in r['reserved_splits'].split(';')}
    assert train_keys == {r['record_key'] for r in parts['train']}
    assert validation_keys == {r['record_key'] for r in parts['validation']}
    assert eligible == train_keys | validation_keys | {r['record_key'] for r in reserved}
    all_test_groups = {r['pipeline_group'] for r in allrows if 'test' in r['reserved_splits'].split(';')}
    all_val_groups = {r['pipeline_group'] for r in allrows if 'validation' in r['reserved_splits'].split(';')}
    assert not {r['pipeline_group'] for r in parts['train']} & (all_test_groups | all_val_groups)
    assert not {r['pipeline_group'] for r in parts['validation']} & all_test_groups
    for split, rows in parts.items():
        for row in rows:
            original = bykey[row['record_key']]
            assert original['pipeline_status'] == 'eligible'
            for field in ('price_million', 'area_sqm'):
                assert float(row[field]) == float(original[field])
            for field in ('category', 'pipeline_group', 'location_feature', 'displayed_date'):
                assert row[field] == original[field]
    assert sha(PROCESSED/'training_v1/test.csv') == sha(PROCESSED/'training_v2/test.csv')
    saved = read(models/'validation_predictions.csv')
    assert len(saved) == len(parts['validation'])*3
    lookup = {(r['record_key'],r['model']):r for r in saved}
    assert len(lookup) == len(saved)
    basemodels = json.loads((models/'baseline_models.json').read_text(encoding='utf-8'))
    names = ['location_median_unit_price', 'ridge_log_area_location_alpha_1', 'xgboost_enriched_log']
    selected_actual, selected_predicted = [], []
    for category in CATEGORIES:
        tr = [r for r in parts['train'] if r['category'] == category]
        va = [r for r in parts['validation'] if r['category'] == category]
        info = report['categories'][category]
        assert (info['train_n'], info['validation_n']) == (len(tr), len(va))
        spec = json.loads((models/info['schema_file']).read_text(encoding='utf-8'))
        assert spec == dict(schema(tr), category=category)
        # Independently refit baseline train-only statistics and compare serialized parameters.
        freshly_fit = baseline.fit([dict(r, district=r['location_feature']) for r in tr])
        assert freshly_fit == basemodels[category]
        bpred = baseline.predict([dict(r, district=r['location_feature']) for r in va], basemodels[category])
        booster = xgb.Booster()
        booster.load_model(models/info['xgboost_model_file'])
        assert booster.num_boosted_rounds() == info['xgboost_best_iteration']+1
        assert booster.num_boosted_rounds() == info['xgboost_num_trees']
        assert booster.feature_names == spec['feature_names']
        xp = np.exp(np.clip(booster.predict(xgb.DMatrix(encode(va, spec),
                     feature_names=spec['feature_names'])), -20, 30))
        actual = [float(r['price_million']) for r in va]
        predictions = dict(zip(names, [bpred['district_median_unit_price'],
                                      bpred['log_area_district_ridge_alpha_1'], xp]))
        measured = {}
        for name, values in predictions.items():
            for row, value in zip(va, values):
                s = lookup[(row['record_key'], name)]
                assert float(s['actual_million']) == float(row['price_million'])
                np.testing.assert_allclose(float(s['predicted_million']), value, rtol=1e-6, atol=.001)
                assert s['selected'] == str(name == info['selected_by_validation_mae'])
            measured[name] = scores(actual, values)
            for metric, value in measured[name].items():
                if value is not None:
                    np.testing.assert_allclose(value, info['validation'][name][metric], rtol=1e-6, atol=.001)
        selected = min(names, key=lambda name: measured[name]['mae_million'])
        assert selected == info['selected_by_validation_mae']
        selected_actual.extend(actual)
        selected_predicted.extend(predictions[selected])
    aggregate = scores(selected_actual, selected_predicted)
    for metric, value in aggregate.items():
        if value is not None:
            np.testing.assert_allclose(value, report['aggregate_selected_validation'][metric], rtol=1e-6, atol=.001)
    errors = read(models/'validation_errors.csv')
    assert len(errors) == len(parts['validation'])
    assert {r['record_key'] for r in errors} == validation_keys
    for r in errors:
        s = lookup[(r['record_key'], r['selected_model'])]
        assert s['selected'] == 'True'
        for field in ('actual_million', 'predicted_million', 'absolute_error_million', 'ape_pct'):
            np.testing.assert_allclose(float(r[field]), float(s[field]))
    result = dict(verified=True, checked_at_utc=datetime.now(timezone.utc).isoformat(),
        dataset_run=data.relative_to(BASE).as_posix(), model_run=models.relative_to(BASE).as_posix(),
        hashed_files=len(expected), train_n=len(parts['train']), validation_n=len(parts['validation']),
        reserved_eligible_n=len(reserved), group_overlap=False, labels_match_frozen_pipeline=True,
        old_artifacts_and_raw_unchanged=True, saved_predictions_and_metrics_verified=True,
        old_test_preserved=True, test_evaluated=False)
    write_json(PROCESSED/'models_v3_validation/verification.json', result)
    print(json.dumps(result, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
