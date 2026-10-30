"""Compare three fixed regression families on frozen v3 validation; never score test."""
import argparse
import hashlib
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb
import training_v3_common as common
import train_smartprop_baseline as baseline
import prepare_smartprop_dataset as preparation
from training_v3_common import (BASE, PROCESSED, CATEGORIES, read, sha, write_csv,
    write_json, outputs, verify, validate_parts, schema, encode, scores)

OUT = PROCESSED / 'models_v3_validation'
PARAMS = dict(objective='reg:squarederror', tree_method='hist', device='cpu',
              max_depth=3, eta=.03, min_child_weight=5, subsample=.8,
              colsample_bytree=.8, reg_lambda=10, seed=42, nthread=4,
              disable_default_eval_metric=1)
FAMILIES = ['location_median_unit_price', 'ridge_log_area_location_alpha_1',
            'xgboost_enriched_log']
PROTOCOL = dict(families=FAMILIES, xgboost_params=PARAMS, max_rounds=1500,
    early_stopping_rounds=50, early_stopping_metric='MAE in original million VND',
    target_transform='natural log for Ridge and XGBoost',
    selection='Lowest validation MAE separately for each category; no parameter search.',
    baselines='Train-only location median unit price with global fallback; Ridge alpha=1 log-area and location.',
    xgboost_features='Area, structured rooms, source ward and location; train-only vocabularies; explicit missing flags.',
    comparison='All models use identical train/validation IDs and labels within each category.',
    test_evaluated=False, independent_benchmark=False)


def log_mae(prediction, matrix):
    return 'mae_million', float(np.abs(np.exp(np.clip(prediction, -20, 30))
                                      - np.exp(matrix.get_label())).mean())


def baseline_rows(rows):
    return [dict(row, district=row['location_feature']) for row in rows]


def get_baseline_predictions(rows, model):
    pred = baseline.predict(baseline_rows(rows), model)
    return {FAMILIES[0]: pred['district_median_unit_price'],
            FAMILIES[1]: pred['log_area_district_ridge_alpha_1']}


def feature_coverage(parts):
    result = []
    for split, rows in parts.items():
        for category in CATEGORIES:
            subset = [r for r in rows if r['category'] == category]
            for field in ['area_sqm', 'location_feature', 'ward_source', 'rooms']:
                available = sum(bool(r[field]) for r in subset)
                result.append(dict(split=split, category=category, feature=field,
                                   n=len(subset), available=available,
                                   available_pct=100*available/len(subset)))
    return result


def publish(target):
    relative = target.relative_to(OUT).as_posix()
    write_json(OUT/'latest.json', dict(run=relative))
    (OUT/'README.md').write_text('# So sánh mô hình v3 trên validation\n\n'
        f'[Mở kết quả đã chốt]({relative}/README.md).\n', encoding='utf-8')


def main(data):
    frozen = json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    verify(frozen['output_sha256'], data)
    verify(frozen['input_sha256'])
    paths = [data/name for name in ('manifest.json', 'train.csv', 'validation.csv',
                                  'reserved_holdout_registry.csv', 'summary.json')]
    paths += [Path(__file__), Path(common.__file__), Path(baseline.__file__), Path(preparation.__file__)]
    inputs = {p.relative_to(BASE).as_posix(): sha(p) for p in paths}
    versions = dict(python=platform.python_version(), numpy=np.__version__, xgboost=xgb.__version__)
    fingerprint = hashlib.sha256(json.dumps(dict(inputs=inputs, protocol=PROTOCOL,
                                               versions=versions), sort_keys=True).encode()).hexdigest()
    target = OUT/'runs'/fingerprint[:16]
    if (target/'manifest.json').exists():
        previous = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        verify(previous['output_sha256'], target)
        verify(previous['input_sha256'])
        publish(target)
        print('Existing v3 models verified; no retraining: '+str(target))
        return
    parts = {split:read(data/(split+'.csv')) for split in ('train', 'validation')}
    reserved = read(data/'reserved_holdout_registry.csv')
    validate_parts(parts, {r['pipeline_group'] for r in reserved})
    if any(sum(r['category'] == c for r in parts[s]) < 5
           for s in parts for c in CATEGORIES):
        raise ValueError('At least five train and validation records per category required')
    # Existing outputs are never edited; keep an integrity snapshot as additional evidence.
    protected = {p.relative_to(BASE).as_posix():sha(p)
                 for p in sorted(PROCESSED.rglob('*'))
                 if p.is_file() and OUT not in p.parents}
    stage = OUT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    write_json(stage/'protocol.json', PROTOCOL)  # persisted before the first fit
    results, predictions, errors, all_baselines = {}, [], [], {}
    for index, category in enumerate(CATEGORIES, 1):
        tr = [r for r in parts['train'] if r['category'] == category]
        va = [r for r in parts['validation'] if r['category'] == category]
        actual = np.asarray([float(r['price_million']) for r in va])
        basemodel = baseline.fit(baseline_rows(tr))
        all_baselines[category] = basemodel
        pred = get_baseline_predictions(va, basemodel)
        spec = schema(tr)
        feature_names = spec['feature_names']
        dt = xgb.DMatrix(encode(tr, spec), label=np.log([float(r['price_million']) for r in tr]),
                         feature_names=feature_names)
        dv = xgb.DMatrix(encode(va, spec), label=np.log(actual), feature_names=feature_names)
        print(f'Training {category}: train={len(tr)}, validation={len(va)}', flush=True)
        model = xgb.train(PARAMS, dt, num_boost_round=PROTOCOL['max_rounds'],
                          evals=[(dv, 'validation')], custom_metric=log_mae,
                          early_stopping_rounds=PROTOCOL['early_stopping_rounds'], verbose_eval=False)
        best = model[:model.best_iteration+1]
        pred[FAMILIES[2]] = np.exp(np.clip(best.predict(dv), -20, 30))
        model_name = f'category_{index}_xgboost.json'
        best.save_model(stage/model_name)
        write_json(stage/f'category_{index}_schema.json', dict(spec, category=category))
        restored = xgb.Booster()
        restored.load_model(stage/model_name)
        np.testing.assert_allclose(restored.predict(dv), best.predict(dv), rtol=1e-7, atol=1e-7)
        metrics = {family:scores(actual, values) for family, values in pred.items()}
        selected = min(FAMILIES, key=lambda family: metrics[family]['mae_million'])
        unseen = [r for r in va if r['location_feature'] not in spec['locations']]
        results[category] = dict(train_n=len(tr), validation_n=len(va), validation=metrics,
            selected_by_validation_mae=selected, selected_validation=metrics[selected],
            xgboost_best_iteration=model.best_iteration, xgboost_num_trees=best.num_boosted_rounds(),
            xgboost_model_file=model_name, schema_file=f'category_{index}_schema.json',
            validation_unseen_location_n=len(unseen),
            validation_ward_available_n=sum(bool(r['ward_source']) for r in va),
            validation_ward_encoded_n=sum(r['location_feature']+'|'+r['ward_source'] in spec['wards'] for r in va),
            group_metrics={})
        for field in ('source', 'location_feature'):
            results[category]['group_metrics'][field] = {}
            for value in sorted({r[field] for r in va}):
                indices = [i for i,r in enumerate(va) if r[field] == value]
                result = scores(actual[indices], pred[selected][indices])
                result['small_sample_n_below_10'] = len(indices) < 10
                results[category]['group_metrics'][field][value] = result
        for i, row in enumerate(va):
            for family in FAMILIES:
                value = float(pred[family][i])
                predictions.append(dict(record_key=row['record_key'], category=category,
                    source=row['source'], pipeline_group=row['pipeline_group'],
                    location_feature=row['location_feature'], model=family,
                    actual_million=float(actual[i]), predicted_million=value,
                    absolute_error_million=abs(value-actual[i]),
                    ape_pct=100*abs(value-actual[i])/actual[i], selected=family == selected))
            value = float(pred[selected][i])
            errors.append(dict(record_key=row['record_key'], category=category, source=row['source'],
                location_feature=row['location_feature'], detail_url=row['detail_url'],
                area_sqm=row['area_sqm'], actual_million=float(actual[i]),
                predicted_million=value, signed_error_million=value-actual[i],
                absolute_error_million=abs(value-actual[i]), ape_pct=100*abs(value-actual[i])/actual[i],
                selected_model=selected, label_action='none; residual is not evidence of a wrong label'))
        print(json.dumps(dict(category=category, selected=selected,
              mae_million=metrics[selected]['mae_million']), ensure_ascii=False), flush=True)
    write_json(stage/'baseline_models.json', all_baselines)
    # Reconstruct baseline predictions from the actual saved JSON, not the in-memory object.
    restored_baselines = json.loads((stage/'baseline_models.json').read_text(encoding='utf-8'))
    for category in CATEGORIES:
        va = [r for r in parts['validation'] if r['category'] == category]
        roundtrip = get_baseline_predictions(va, restored_baselines[category])
        for family, values in roundtrip.items():
            expected = [r['predicted_million'] for r in predictions
                        if r['category'] == category and r['model'] == family]
            np.testing.assert_allclose(values, expected, rtol=1e-10, atol=1e-8)
    selected_rows = [r for r in predictions if r['selected']]
    aggregate = scores([r['actual_million'] for r in selected_rows],
                       [r['predicted_million'] for r in selected_rows])
    report = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), fingerprint=fingerprint,
        dataset_run=data.relative_to(BASE).as_posix(), versions=versions, protocol=PROTOCOL,
        categories=results, aggregate_selected_validation=aggregate,
        test_evaluated=False, model_reload_verified=True, numeric_labels_unchanged=True,
        limitations=['Validation is used for early stopping and model choice, so scores can be optimistic.',
            'Validation partly overlaps prior development experiments; it is not a new independent test.',
            'Do not compare these scores directly with v2: cohort and current categories differ.',
            'Labels are asking prices, not independently verified transaction values.',
            'Sparse wards, mixed administrative units and few apartments limit coverage.',
            'Missing fields can act as source proxies; no future-time or held-out-source evaluation.',
            'No records removed or prices corrected based on model residuals.'])
    write_json(stage/'metrics.json', report)
    write_csv(stage/'validation_predictions.csv', predictions, list(predictions[0]))
    errors.sort(key=lambda r:r['absolute_error_million'], reverse=True)
    write_csv(stage/'validation_errors.csv', errors, list(errors[0]))
    coverage = feature_coverage(parts)
    write_csv(stage/'feature_coverage.csv', coverage, list(coverage[0]))
    lines = ['# Mô hình v3: so sánh trên validation', '',
        f'Đã huấn luyện từ {len(parts["train"]):,} tin train và so sánh trên '
        f'{len(parts["validation"]):,} tin validation đã chốt. Không đọc/chấm lại test.', '',
        '| Loại | Train | Val | Trung vị MAE | Ridge MAE | XGBoost MAE | Chọn theo MAE |',
        '|---|---:|---:|---:|---:|---:|---|']
    short_names = dict(zip(FAMILIES, ['Trung vị địa bàn', 'Ridge', 'XGBoost']))
    for category, info in results.items():
        vals = [info['validation'][f]['mae_million'] for f in FAMILIES]
        lines.append(f'| {category} | {info["train_n"]} | {info["validation_n"]} | '
                     + ' | '.join(f'{v:,.1f}' for v in vals)
                     + f' | {short_names[info["selected_by_validation_mae"]]} |')
    lines += ['', 'MAE tính bằng **triệu VND**; nhỏ hơn là tốt hơn. Cả ba họ mô hình '
        'dùng cùng ID và nhãn trong từng loại. Không mặc định XGBoost thắng.', '',
        '| Loại | MAE mô hình chọn | RMSE | MAPE | MedAPE | Sai số ≤20% |',
        '|---|---:|---:|---:|---:|---:|']
    for category, info in results.items():
        m = info['selected_validation']
        lines.append(f'| {category} | {m["mae_million"]:,.1f} | {m["rmse_million"]:,.1f} | '
                     f'{m["mape_pct"]:.1f}% | {m["median_ape_pct"]:.1f}% | {m["within_20pct"]:.1f}% |')
    lines += ['', '## Cách hiểu kết quả', '',
        'Đây là kết quả phát triển: validation đồng thời dùng để dừng sớm/chọn mô hình và có '
        'liên quan các thí nghiệm trước. Chưa phải kiểm chứng độc lập trên thị trường. '
        'Không so trực tiếp với MAE v2 vì khác cohort; không tối ưu theo 137 tin test cũ.', '',
        'Dữ liệu là giá rao, chưa xác minh giao dịch. Nhóm căn hộ nhỏ; số liệu từng địa bàn/nguồn '
        'có n<10 được đánh dấu trong metrics.json. Địa bàn chưa thấy trong train dùng fallback '
        'trung vị toàn loại ở baseline và indicator bằng 0 ở mô hình tuyến tính/cây.', '',
        '## Đặc trưng và lưu mô hình', '',
        'XGBoost: log giá, cây hist trên CPU 4 luồng, depth=3, eta=0.03, tối đa 1500 vòng; '
        'dừng sớm sau 50 vòng không cải thiện MAE giá gốc. Chỉ thử một cấu hình cố định. '
        'Đặc trưng: diện tích, địa bàn, phường nguồn xuất hiện ≥3 lần trong train, số phòng và cờ thiếu. '
        'Đất không dùng số phòng. Không dùng ID/URL/nguồn/tiêu đề/raw_json/giá trên m²/cờ lọc làm đầu vào.', '',
        'Ridge alpha=1 dùng log diện tích và địa bàn, dự đoán log giá. Baseline trung vị đơn giá '
        'học từ nhãn train theo địa bàn, fallback toàn loại. Mọi thống kê/encoder chỉ học từ train.', '',
        '`metrics.json`: toàn bộ chỉ số, lựa chọn từng loại, sai số theo nguồn/địa bàn. '
        '`validation_predictions.csv`: cả ba mô hình. `validation_errors.csv`: sai số của mô hình '
        'được chọn, xếp giảm dần; sai số lớn không phải căn cứ tự sửa/loại nhãn. '
        '`feature_coverage.csv`: độ phủ đặc trưng.', '',
        'Model XGBoost JSON phải dùng schema cùng loại và exp đầu ra. '
        '`baseline_models.json` lưu hai baseline. Đã tải lại các file mô hình và xác nhận '
        'dự đoán khớp trước khi chốt manifest.', '',
        'Bước tiếp: rà soát lỗi theo khu vực/nguồn và lập tập kiểm chứng mới được xác minh độc lập '
        'trước khi đưa vào ứng dụng. Giữ nguyên tập chờ, raw, các bộ/model v1/v2 và test cũ.', '']
    (stage/'README.md').write_text('\n'.join(lines), encoding='utf-8')
    verify(inputs)
    verify(protected)
    write_json(stage/'manifest.json', dict(fingerprint=fingerprint, input_sha256=inputs,
        protected_sha256=protected, output_sha256=outputs(stage), complete=True))
    stage.rename(target)
    publish(target)
    print(json.dumps(dict(run=str(target), aggregate_validation=aggregate), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-dir', type=Path)
    args = parser.parse_args()
    directory = args.input_dir or (PROCESSED/'training_v3' /
        json.loads((PROCESSED/'training_v3/latest.json').read_text())['run'])
    main(directory.resolve())
