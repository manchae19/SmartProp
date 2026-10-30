"""Separate asking-price baselines by property type, using grouped holdouts."""
import argparse
import csv
import hashlib
import json
from pathlib import Path

import numpy as np

from prepare_smartprop_dataset import CATEGORIES, BASE, save_csv


def metrics(actual, predicted):
    actual, predicted = np.asarray(actual), np.asarray(predicted)
    errors = np.abs(actual - predicted)
    variance = np.sum((actual - actual.mean()) ** 2)
    return dict(n=len(actual), mae_million=float(errors.mean()),
                median_ape_pct=float(np.median(errors / actual) * 100),
                mape_pct=float((errors / actual).mean() * 100),
                r2=float(1 - np.sum((actual-predicted)**2) / variance) if variance > 0 else None)


def fit(train):
    """All encodings, medians and standardization are learned from train only."""
    districts = sorted(set(r['district'] for r in train))
    area = np.log([float(r['area_sqm']) for r in train])
    center, scale = float(area.mean()), max(float(area.std()), 1e-9)
    params = dict(districts=districts, log_area_mean=center, log_area_scale=scale)
    x = design(train, params)
    y = np.log([float(r['price_million']) for r in train])
    penalty = np.eye(x.shape[1])
    penalty[0, 0] = 0
    params['ridge_coefficients'] = np.linalg.solve(x.T @ x + penalty, x.T @ y).tolist()
    units = np.array([float(r['price_million']) / float(r['area_sqm']) for r in train])
    params['global_median_unit_price'] = float(np.median(units))
    params['district_median_unit_price'] = {
        d: float(np.median([units[i] for i, r in enumerate(train) if r['district'] == d]))
        for d in districts}
    return params


def design(rows, params):
    return np.array([[1, (np.log(float(r['area_sqm'])) - params['log_area_mean']) / params['log_area_scale']]
        + [float(r['district'] == d) for d in params['districts']] for r in rows])


def predict(rows, params):
    ridge = np.exp(design(rows, params) @ np.array(params['ridge_coefficients']))
    median = np.array([float(r['area_sqm']) * params['district_median_unit_price'].get(
        r['district'], params['global_median_unit_price']) for r in rows])
    return {'district_median_unit_price': median, 'log_area_district_ridge_alpha_1': ridge}


def main(directory):
    source = directory / 'baseline_inputs.csv'
    with source.open(encoding='utf-8-sig', newline='') as f:
        rows = list(csv.DictReader(f))
    assert len(rows) == len(set(r['record_key'] for r in rows))
    assert len(rows) == len(set(r['duplicate_candidate_group'] for r in rows))
    assert all(r['status'] == 'candidate' for r in rows)
    report = dict(input_sha256=hashlib.sha256(source.read_bytes()).hexdigest(),
        target='total asking price in million VND', features=['area_sqm', 'historical_district'],
        split_method='SHA256 of suspected property group, fixed smartprop-v1 seed, 80/10/10 thresholds',
        limitations=['Heuristic duplicate groups can miss or overgroup properties.',
            'Holdouts are grouped random splits, not a future-time evaluation.',
            'Homedy dates unavailable; date freshness is not verified for those records.',
            'Asking prices and source location labels are not verified transactions or geocoded addresses.',
            'Screened sample may not represent the full market; this is an experimental baseline.'], categories={})
    predictions, models = [], {}
    for category in CATEGORIES:
        parts = {split: [r for r in rows if r['category'] == category and r['model_split'] == split]
                 for split in ['train', 'validation', 'test']}
        if any(len(part) < 5 for part in parts.values()):
            report['categories'][category] = {'status': 'insufficient_data',
                'split_counts': {s:len(part) for s,part in parts.items()}}
            continue
        params = fit(parts['train'])
        models[category] = params
        category_report = dict(split_counts={s:len(part) for s,part in parts.items()}, validation={}, test={})
        by_model = {}
        for split in ['validation', 'test']:
            actual = [float(r['price_million']) for r in parts[split]]
            estimates = predict(parts[split], params)
            for model, values in estimates.items():
                category_report[split][model] = metrics(actual, values)
            by_model[split] = estimates
        selected = min(category_report['validation'], key=lambda m: category_report['validation'][m]['mae_million'])
        category_report['selected_by_validation_mae'] = selected
        category_report['selected_test_metrics'] = category_report['test'][selected]
        category_report['test_by_district'] = {}
        for district in sorted(set(r['district'] for r in parts['test'])):
            indices = [i for i,r in enumerate(parts['test']) if r['district'] == district]
            category_report['test_by_district'][district] = metrics(
                [float(parts['test'][i]['price_million']) for i in indices],
                [by_model['test'][selected][i] for i in indices])
        report['categories'][category] = category_report
        for split in ['validation', 'test']:
            for i, row in enumerate(parts[split]):
                predictions.append(dict(record_key=row['record_key'], source=row['source'],
                    category=category, district=row['district'], split=split,
                    duplicate_candidate_group=row['duplicate_candidate_group'],
                    date_basis=row['date_basis'], actual_million=row['price_million'],
                    median_prediction_million=float(by_model[split]['district_median_unit_price'][i]),
                    ridge_prediction_million=float(by_model[split]['log_area_district_ridge_alpha_1'][i]),
                    selected_model=selected, selected_prediction_million=float(by_model[split][selected][i])))
    (directory / 'baseline_metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (directory / 'baseline_models.json').write_text(json.dumps(models, ensure_ascii=False, indent=2), encoding='utf-8')
    save_csv(directory / 'baseline_holdout_predictions.csv', predictions,
        ['record_key', 'source', 'category', 'district', 'split', 'duplicate_candidate_group',
         'date_basis', 'actual_million', 'median_prediction_million', 'ridge_prediction_million',
         'selected_model', 'selected_prediction_million'])
    print(json.dumps({cat:{'counts':info['split_counts'],
        'selected':info.get('selected_by_validation_mae'), 'test':info.get('selected_test_metrics')}
        for cat,info in report['categories'].items()}, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path, default=BASE / 'processed/smartprop_review')
    main(parser.parse_args().input_dir)
