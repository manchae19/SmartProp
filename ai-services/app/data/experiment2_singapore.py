"""Fixed Da Nang apartment holdout: local ridge versus weighted HDB transfer."""
import csv
import hashlib
import json
from collections import Counter
from pathlib import Path
import numpy as np
from prepare_smartprop_dataset import BASE, CATEGORIES, save_csv
from train_smartprop_baseline import fit, design, predict, metrics

RAW = BASE / 'data_raw/singapore_hdb'
OUT = BASE / 'processed/experiment2_singapore'
WEIGHTS = [0.1, 0.25, 0.5, 1.0]

def read(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def fingerprint(row):
    return hashlib.sha256(json.dumps(row, sort_keys=True).encode()).hexdigest()

def select_foreign(rows, fx, limit=3000):
    selected, counts = {}, Counter()
    for row in rows:
        if not '2026-04' <= row['month'] <= '2026-09':
            counts['outside_2026_04_to_09'] += 1
            continue
        try:
            area, price = float(row['floor_area_sqm']), float(row['resale_price'])
            if not np.isfinite([area, price]).all() or not 20 <= area <= 1000 or price <= 0:
                raise ValueError('invalid area/price')
        except (ValueError, TypeError):
            counts['invalid_numeric'] += 1
            continue
        key = fingerprint(row)
        if key in selected:
            counts['exact_row_duplicate'] += 1
            continue
        selected[key] = dict(record_key='hdb:' + key, district=row['town'],
            area_sqm=area, price_million=price * fx / 1e6,
            month=row['month'], resale_price_sgd=price, raw_json=json.dumps(row, sort_keys=True))
    counts['eligible_unique_rows'] = len(selected)
    # Hash order is deterministic and independent of price-based selection.
    result = [selected[k] for k in sorted(selected)[:limit]]
    counts['selected_train_rows'] = len(result)
    return result, dict(counts)

def fit_transfer(local, foreign, weight):
    """Same local ridge, shared area slope, independent SG intercept/town offsets.

    SG total sample weight = weight * local count. Area scaling uses local train
    only. Independent unpenalized SG intercept avoids forcing market price levels
    to match; the only shared property relationship is the area coefficient.
    """
    params = fit(local)
    towns = sorted({r['district'] for r in foreign})
    nbase = 2 + len(params['districts'])
    xlocal = np.pad(design(local, params), ((0, 0), (0, 1 + len(towns))))
    xforeign = np.zeros((len(foreign), xlocal.shape[1]))
    xforeign[:, 1] = [(np.log(r['area_sqm']) - params['log_area_mean']) / params['log_area_scale'] for r in foreign]
    xforeign[:, nbase] = 1
    for index, town in enumerate(towns):
        xforeign[:, nbase + 1 + index] = [r['district'] == town for r in foreign]
    x = np.vstack([xlocal, xforeign])
    y = np.log([float(r['price_million']) for r in local + foreign])
    weights = np.r_[np.ones(len(local)), np.full(len(foreign), weight * len(local)/len(foreign))]
    penalty = np.eye(x.shape[1])
    penalty[0, 0] = penalty[nbase, nbase] = 0
    coefficients = np.linalg.solve(x.T @ (weights[:, None] * x) + penalty, x.T @ (weights * y))
    params['ridge_coefficients'] = coefficients[:nbase].tolist()
    return params, dict(foreign_relative_total_weight=weight, foreign_row_weight=float(weights[-1]),
        towns=towns, singapore_coefficients=coefficients[nbase:].tolist())

def main():
    OUT.mkdir(parents=True, exist_ok=True)
    source = BASE / 'processed/smartprop_review/baseline_inputs.csv'
    before = hashlib.sha256(source.read_bytes()).hexdigest()
    rows = [r for r in read(source) if r['category'] == CATEGORIES[2]]
    parts = {s: [r for r in rows if r['model_split'] == s] for s in ['train', 'validation', 'test']}
    assert all(parts.values())
    groups = {s: {r['duplicate_candidate_group'] for r in rs} for s, rs in parts.items()}
    assert not (groups['train'] & groups['validation'] or groups['train'] & groups['test'] or groups['validation'] & groups['test'])
    provenance = json.loads((RAW / 'provenance.json').read_text(encoding='utf-8'))
    assert hashlib.sha256((RAW / 'resale_flat_prices.csv').read_bytes()).hexdigest() == provenance['raw_sha256']
    foreign, filtering = select_foreign(read(RAW / 'resale_flat_prices.csv'), provenance['vnd_per_sgd'])
    assert foreign
    local = fit(parts['train'])
    ridge = 'log_area_district_ridge_alpha_1'
    actual_val = [float(r['price_million']) for r in parts['validation']]
    candidates, fitted = [], {}
    for weight in WEIGHTS:
        model, details = fit_transfer(parts['train'], foreign, weight)
        val = metrics(actual_val, predict(parts['validation'], model)[ridge])
        candidates.append(dict(weight=weight, validation=val))
        fitted[weight] = (model, details)
    selected = min(candidates, key=lambda r:r['validation']['mae_million'])['weight']
    augmented, details = fitted[selected]
    report = dict(local_input_sha256=before, source_provenance=provenance,
        local_counts={s:len(rs) for s,rs in parts.items()}, foreign_filtering=filtering,
        period=['2026-04', '2026-09'], foreign_max_sample=3000,
        test_ids_sha256=hashlib.sha256('\n'.join(sorted(r['record_key'] for r in parts['test'])).encode()).hexdigest(),
        methodology='Log total-price ridge alpha=1; shared area slope, separate local districts and SG towns/intercepts; SGD converted to million VND. Positive foreign weights selected on Da Nang validation MAE only.',
        tuning=candidates, selected_foreign_weight=selected,
        validation={}, test={})
    predictions = []
    for split in ['validation', 'test']:
        actual = np.array([float(r['price_million']) for r in parts[split]])
        estimates = dict(danang_only_ridge=predict(parts[split], local)[ridge],
            danang_plus_singapore_ridge=predict(parts[split], augmented)[ridge],
            existing_local_median_baseline=predict(parts[split], local)['district_median_unit_price'])
        report[split] = {name:metrics(actual, values) for name,values in estimates.items()}
        for i, row in enumerate(parts[split]):
            predictions.append(dict(record_key=row['record_key'], split=split, district=row['district'],
                actual_million=float(actual[i]), **{name:float(values[i]) for name,values in estimates.items()}))
        if split == 'test':
            delta = np.abs(actual-estimates['danang_plus_singapore_ridge']) - np.abs(actual-estimates['danang_only_ridge'])
            rng = np.random.default_rng(20261011)
            bootstrap = delta[rng.integers(0, len(delta), (10000, len(delta)))].mean(axis=1)
            report['paired_mae_delta_million'] = float(delta.mean())
            report['paired_bootstrap_95pct_interval_million'] = np.quantile(bootstrap, [.025, .975]).tolist()
            report['bootstrap_note'] = 'Exploratory paired resampling of the fixed test rows; does not include model/tuning/data uncertainty.'
    report['mae_improvement_pct'] = 100 * (1 - report['test']['danang_plus_singapore_ridge']['mae_million']/report['test']['danang_only_ridge']['mae_million'])
    assert before == hashlib.sha256(source.read_bytes()).hexdigest()
    save_csv(OUT / 'singapore_train.csv', foreign, list(foreign[0]))
    save_csv(OUT / 'holdout_predictions.csv', predictions, list(predictions[0]))
    (OUT / 'models.json').write_text(json.dumps(dict(local=local, augmented=augmented, transfer=details), ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'metrics.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps({k:v for k,v in report.items() if k not in ['source_provenance','methodology']}, ensure_ascii=True, indent=2))

if __name__ == '__main__':
    main()
