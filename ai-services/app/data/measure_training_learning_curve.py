"""Fixed train-only grouped learning curve; no release/pilot/dev-val scoring."""
import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import platform
import uuid

import numpy as np
import xgboost as xgb
import training_v3_common as data
import property_text_features_v6 as feature

BASE = data.BASE
PREPARED = BASE / 'processed/training_next_preparation/runs/4fdb8ef79db89b16'
OUT = BASE / 'processed/training_learning_curve'
PROTOCOL_FILE = BASE / 'PROPERTY_EXPANSION_PROTOCOL.md'
PARAMS = dict(objective='reg:squarederror', tree_method='hist', device='cpu', max_depth=3,
    eta=.03, min_child_weight=5, subsample=.8, colsample_bytree=.8, reg_lambda=10,
    seed=42, nthread=4, disable_default_eval_metric=1)
PROTOCOL = dict(folds=3, fractions=[.25, .5, .75, 1.0], rounds=300, params=PARAMS,
    feature_arm='v6/all', train_only=True, early_stopping=False,
    fold_salt='curve-v1/fold/', subset_salt='curve-v1/subset/',
    dev_validation_scored=False, pilot_scored=False, forecast=False)


def hash_number(value):
    return int.from_bytes(hashlib.sha256(value.encode()).digest()[:8], 'big')


def partitions(rows, folds=3):
    if len({r['record_key'] for r in rows}) != len(rows) or len({r['pipeline_group'] for r in rows}) != len(rows):
        raise ValueError('Learning curve requires distinct candidate groups')
    for fold in range(folds):
        outer = [r for r in rows if hash_number(PROTOCOL['fold_salt'] + r['pipeline_group']) % folds == fold]
        train = [r for r in rows if hash_number(PROTOCOL['fold_salt'] + r['pipeline_group']) % folds != fold]
        train.sort(key=lambda r: (hash_number(PROTOCOL['subset_salt'] + r['pipeline_group']), r['record_key']))
        if not outer or len(train) < 10:
            raise ValueError('Too few groups for declared folds')
        for fraction in PROTOCOL['fractions']:
            size = max(1, math.floor(len(train) * fraction))
            yield fold, fraction, train[:size], outer


def context():
    manifest = json.loads((PREPARED / 'manifest.json').read_text(encoding='utf8'))
    data.verify(manifest['output_sha256'], PREPARED)
    root = BASE.parents[2]
    protected = {str(root / name): expected for name, expected in manifest['input_sha256'].items()}
    for path in (BASE / 'processed/evaluation_ledger').glob('*.json'):
        protected[str(path)] = data.sha(path)
    for path, expected in protected.items():
        if data.sha(path) != expected:
            raise ValueError('Protected source differs')
    train = data.read(PREPARED / 'train.csv')
    if len(train) != 2213 or any(r['model_split'] != 'train' or r['reserved_splits'] != 'train' for r in train):
        raise ValueError('Unexpected learning-curve input')
    keys = {r['record_key'] for r in train}
    features = {r['record_key']: r for r in data.read(PREPARED / 'features.csv') if r['record_key'] in keys}
    if features.keys() != keys or any(r['model_split'] != 'train' for r in features.values()):
        raise ValueError('Feature join differs from train')
    paths = [Path(__file__), PROTOCOL_FILE, Path(data.__file__), Path(feature.__file__),
        PREPARED / 'manifest.json', PREPARED / 'train.csv', PREPARED / 'features.csv']
    inputs = {str(p): data.sha(p) for p in paths}
    return train, features, inputs, protected


def predictions(model, rows, values, spec):
    matrix = xgb.DMatrix(feature.encode(rows, values, spec), feature_names=spec['feature_names'])
    return np.exp(np.clip(model.predict(matrix), -20, 30))


def metrics(actual, predicted):
    score = data.scores(actual, predicted)
    return dict(mae=float(score['mae_million']), mape=float(score['mape_pct']))


def render(directory, summaries, fold_scores):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    fig, axes = plt.subplots(1, 3, figsize=(15, 4.8))
    for ax, category in zip(axes, data.CATEGORIES):
        rows = [r for r in summaries if r['category'] == category]
        x = [r['mean_train_n'] for r in rows]
        y = np.array([r['outer_mae_million'] for r in rows])
        spread = np.array([r['fold_mae_sd_million'] for r in rows])
        ax.plot(x, [r['train_mae_million'] for r in rows], 'o-', label='Subset train')
        ax.plot(x, y, 'o-', label='Outer fold')
        ax.fill_between(x, np.maximum(0, y-spread), y+spread, alpha=.15, label='±1 SD giữa 3 fold')
        ax.set_title(category)
        ax.set_xlabel('Số nhóm trong subset train (trung bình)')
        ax.set_ylabel('MAE (triệu VND)')
        ax.grid(alpha=.2)
        ax.legend(fontsize=8)
    fig.suptitle('Learning curve v6/all — chỉ train cũ, cố định 300 rounds\nKhông dùng 299 validation/pilot; không phải benchmark độc lập', fontsize=11)
    fig.tight_layout()
    fig.savefig(directory / 'learning_curve.png', dpi=150)
    fig.savefig(directory / 'learning_curve.svg')
    plt.close(fig)


def verify(directory):
    manifest = json.loads((directory / 'manifest.json').read_text(encoding='utf8'))
    for path, expected in manifest['input_sha256'].items():
        if data.sha(path) != expected:
            raise ValueError('Curve input changed')
    for path, expected in manifest['protected_sha256'].items():
        if data.sha(path) != expected:
            raise ValueError('Protected source changed')
    data.verify(manifest['output_sha256'], directory)
    rows, values, _, _ = context()
    bykey = {r['record_key']: r for r in rows}
    models = json.loads((directory / 'models.json').read_text(encoding='utf8'))
    saved = data.read(directory / 'predictions.csv')
    expected_models = {(category, fold, fraction) for category in data.CATEGORIES for fold in range(3) for fraction in PROTOCOL['fractions']}
    if {(r['category'], r['fold'], r['fraction']) for r in models} != expected_models or len(models) != 36:
        raise ValueError('Curve model keyset differs')
    replay = []
    for item in models:
        subset = [bykey[k] for k in item['train_keys']]
        outer = [bykey[k] for k in item['outer_keys']]
        expected = next((s, o) for f, q, s, o in partitions([r for r in rows if r['category'] == item['category']]) if f == item['fold'] and q == item['fraction'])
        if (subset, outer) != expected:
            raise ValueError('Curve membership differs')
        spec = json.loads((directory / item['schema']).read_text(encoding='utf8'))
        if spec != feature.feature_spec(subset, item['category'], 'all'):
            raise ValueError('Curve vocabulary is not subset-only')
        model = xgb.Booster(); model.load_model(directory / item['model'])
        if model.num_boosted_rounds() != PROTOCOL['rounds']:
            raise ValueError('Unexpected fitted rounds')
        for role, part in [('train', subset), ('outer', outer)]:
            for row, p in zip(part, predictions(model, part, values, spec)):
                replay.append(dict(model_key=item['key'], role=role, record_key=row['record_key'],
                                   actual_million=float(row['price_million']), predicted_million=float(p)))
    if len(saved) != len(replay):
        raise ValueError('Curve prediction count differs')
    for old, new in zip(saved, replay):
        if any(old[k] != str(new[k]) for k in ['model_key', 'role', 'record_key']):
            raise ValueError('Curve prediction identity differs')
        np.testing.assert_allclose([float(old['actual_million']),float(old['predicted_million'])],
                                   [new['actual_million'],new['predicted_million']], rtol=1e-7, atol=1e-6)
    print(json.dumps(dict(verified=True, models=len(models), predictions=len(saved), train_only=True)))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    if args.verify:
        verify(OUT / json.loads((OUT / 'latest.json').read_text(encoding='utf8'))['run']); return
    import matplotlib
    rows, values, inputs, protected = context()
    versions = dict(python=platform.python_version(), numpy=np.__version__, xgboost=xgb.__version__, matplotlib=matplotlib.__version__)
    run_id = hashlib.sha256(json.dumps(dict(inputs=inputs, protocol=PROTOCOL, versions=versions), sort_keys=True).encode()).hexdigest()[:16]
    target = OUT / 'runs' / run_id
    if target.exists():
        verify(target); return
    stage = OUT / 'runs' / ('.building_' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    data.write_json(stage / 'protocol.json', dict(PROTOCOL, versions=versions))
    model_records, scores, all_predictions = [], [], []
    for index, category in enumerate(data.CATEGORIES, 1):
        category_rows = [r for r in rows if r['category'] == category]
        for fold, fraction, subset, outer in partitions(category_rows):
            key = f'cat{index}_fold{fold}_pct{int(100*fraction)}'
            spec = feature.feature_spec(subset, category, 'all')
            dm = xgb.DMatrix(feature.encode(subset, values, spec), label=np.log([float(r['price_million']) for r in subset]), feature_names=spec['feature_names'])
            model = xgb.train(PARAMS, dm, num_boost_round=PROTOCOL['rounds'])
            model.save_model(stage / (key + '.json'))
            data.write_json(stage / (key + '_schema.json'), spec)
            item = dict(key=key, category=category, fold=fold, fraction=fraction, model=key+'.json', schema=key+'_schema.json',
                        train_keys=[r['record_key'] for r in subset], outer_keys=[r['record_key'] for r in outer])
            model_records.append(item)
            train_pred = predictions(model, subset, values, spec)
            outer_pred = predictions(model, outer, values, spec)
            train_score = metrics([float(r['price_million']) for r in subset], train_pred)
            outer_score = metrics([float(r['price_million']) for r in outer], outer_pred)
            scores.append(dict(model_key=key, category=category, fold=fold, fraction=fraction, train_n=len(subset), outer_n=len(outer),
                train_mae_million=train_score['mae'], outer_mae_million=outer_score['mae'], outer_mape_pct=outer_score['mape']))
            for role, part, pred in [('train', subset, train_pred), ('outer', outer, outer_pred)]:
                for row, p in zip(part, pred):
                    all_predictions.append(dict(model_key=key, role=role, record_key=row['record_key'],
                        actual_million=float(row['price_million']), predicted_million=float(p)))
            print(json.dumps(scores[-1], ensure_ascii=False), flush=True)
    summaries = []
    for category in data.CATEGORIES:
        for fraction in PROTOCOL['fractions']:
            subset_scores = [s for s in scores if s['category'] == category and s['fraction'] == fraction]
            keys = {s['model_key'] for s in subset_scores}
            held = [p for p in all_predictions if p['model_key'] in keys and p['role'] == 'outer']
            score = metrics([r['actual_million'] for r in held], [r['predicted_million'] for r in held])
            summaries.append(dict(category=category, fraction=fraction, mean_train_n=float(np.mean([s['train_n'] for s in subset_scores])),
                train_mae_million=float(np.average([s['train_mae_million'] for s in subset_scores], weights=[s['train_n'] for s in subset_scores])),
                outer_mae_million=score['mae'], outer_mape_pct=score['mape'],
                fold_mae_sd_million=float(np.std([s['outer_mae_million'] for s in subset_scores], ddof=1))))
    data.write_json(stage / 'models.json', model_records)
    data.write_csv(stage / 'fold_scores.csv', scores, list(scores[0]))
    data.write_csv(stage / 'summary.csv', summaries, list(summaries[0]))
    data.write_csv(stage / 'predictions.csv', all_predictions, list(all_predictions[0]))
    render(stage, summaries, scores)
    (stage / 'README.md').write_text('# Learning curve chỉ trong train\n\n'
        '36 model v6/all tái huấn luyện, cố định300rounds; không phải model release v6. '
        'Chia3fold theo nhóm ứng viên, train subset lồng nhau25/50/75/100%, schema train-subset-only. '
        'Không chấm299 validation, pilot hoặc dữ liệu mới thu. Không thay API/model/ledger. '
        'Độ lệch giữa fold không phải khoảng tin cậy; chưa xác minh độc lập tài sản.\n', encoding='utf8')
    for path, expected in {**inputs, **protected}.items():
        if data.sha(path) != expected: raise ValueError('Curve source changed')
    data.write_json(stage / 'manifest.json', dict(input_sha256=inputs, protected_sha256=protected, output_sha256=data.outputs(stage)))
    stage.rename(target)
    verify(target)
    data.write_json(OUT / 'latest.json', dict(run='runs/' + run_id))
    print(target)


if __name__ == '__main__':main()
