"""Export a fingerprinted v3 development dataset, with no test labels copied."""
import argparse
import hashlib
import json
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import training_v3_common as common
from training_v3_common import (BASE, PROCESSED, CATEGORIES, FIELDS, sha, read,
                                write_csv, write_json, verify, outputs, cohort,
                                model_row, validate_parts)

OUT = PROCESSED / 'training_v3'
REGISTRY_FIELDS = ['record_key', 'source', 'category', 'pipeline_group', 'reserved_splits',
                   'assigned_split', 'protected_holdout', 'training_allowed', 'v3_cohort']
PROTOCOL = dict(target='total asking price, million VND',
    train='All eligible representatives with training_allowed=True and only train reservations.',
    validation='Eligible representatives with a validation reservation and NO test reservation; fixed before fitting.',
    reserved='Every other eligible representative, including any test-linked group, kept aside.',
    test='Old 137-row test files preserved by hash; not copied or scored.',
    independence='Development validation, partly exposed in earlier experiments; not a fresh independent benchmark.',
    features=['area_sqm', 'location_feature', 'ward_source', 'rooms', 'missing/unseen flags'],
    forbidden_features=['price_million', 'unit_price', 'title', 'description', 'raw_json',
                        'record_key', 'source', 'group', 'review_flags', 'URL'],
    numeric_corrections=False, duplicate_groups='Frozen pipeline groups, including all historical bridges.')


def publish(target):
    relative = target.relative_to(OUT).as_posix()
    write_json(OUT / 'latest.json', dict(run=relative))
    (OUT / 'README.md').write_text('# Bộ dữ liệu training_v3\n\n'
        f'[Mở bộ dữ liệu đã chốt]({relative}/README.md).\n', encoding='utf-8')


def distribution(parts):
    result = {}
    for split, rows in parts.items():
        result[split] = dict(n=len(rows),
            by_category=dict(Counter(r['category'] for r in rows)),
            by_source=dict(Counter(r['source'] for r in rows)),
            by_location=dict(Counter(r['location_feature'] for r in rows)),
            date_min=min(r['displayed_date'] for r in rows),
            date_max=max(r['displayed_date'] for r in rows), categories={})
        for category in CATEGORIES:
            subset = [r for r in rows if r['category'] == category]
            def quantiles(field):
                import numpy as np
                return dict(zip(['min', 'p25', 'median', 'p75', 'max'],
                                map(float, np.quantile([float(r[field]) for r in subset], [0,.25,.5,.75,1]))))
            result[split]['categories'][category] = dict(n=len(subset),
                price_million=quantiles('price_million'), area_sqm=quantiles('area_sqm'))
    return result


def main(pipeline):
    saved = json.loads((pipeline / 'manifest.json').read_text(encoding='utf-8'))
    verify(saved['output_sha256'])
    # Verify all frozen pipeline inputs, including raw and prior review dependencies.
    verify(saved['input_sha256'])
    sources = [pipeline / name for name in ('manifest.json', 'all_listings.csv', 'eligible.csv',
                                           'train_candidates.csv', 'summary.json')]
    sources += [Path(__file__), Path(common.__file__)]
    sources += [PROCESSED / f'training_v{i}/test.csv' for i in (1, 2)]
    sources += [PROCESSED / 'training_v2/validation.csv']
    inputs = {p.relative_to(BASE).as_posix(): sha(p) for p in sources}
    fingerprint = hashlib.sha256(json.dumps(dict(inputs=inputs, protocol=PROTOCOL),
                                            sort_keys=True).encode()).hexdigest()
    target = OUT / 'runs' / fingerprint[:16]
    if (target / 'manifest.json').exists():
        frozen = json.loads((target / 'manifest.json').read_text(encoding='utf-8'))
        verify(frozen['output_sha256'], target)
        verify(frozen['input_sha256'])
        publish(target)
        print('Existing training_v3 verified: ' + str(target))
        return
    # Record existing raw/review/model artifacts before any output writes.
    protected = {p.relative_to(BASE).as_posix(): sha(p)
                 for p in sorted(PROCESSED.rglob('*'))
                 if p.is_file() and OUT not in p.parents}
    parts = {'train': [], 'validation': []}
    registry, reserved = [], []
    eligible = read(pipeline / 'eligible.csv')
    allrows = read(pipeline / 'all_listings.csv')
    bykey = {r['record_key']: r for r in allrows}
    for row in eligible:
        if row != bykey[row['record_key']]:
            raise ValueError('Eligible snapshot does not match all-listings')
        split = cohort(row)
        if split is None:
            raise ValueError('Noneligible row in eligible file')
        registry.append(dict({k:row[k] for k in REGISTRY_FIELDS if k != 'v3_cohort'}, v3_cohort=split))
        if split in parts:
            parts[split].append(model_row(row, split))
        else:
            reserved.append(registry[-1])
    for rows in parts.values():
        rows.sort(key=lambda r: (r['category'], r['record_key']))
    validate_parts(parts, {r['pipeline_group'] for r in reserved})
    expected_train = {r['record_key'] for r in read(pipeline / 'train_candidates.csv')}
    assert expected_train == {r['record_key'] for r in parts['train']}
    # Check protection against every source ID in each group, not only representatives.
    forbidden_groups = {r['pipeline_group'] for r in allrows
                        if set(r['reserved_splits'].split(';')) & {'validation', 'test'}}
    assert not forbidden_groups & {r['pipeline_group'] for r in parts['train']}
    test_groups = {r['pipeline_group'] for r in allrows if 'test' in r['reserved_splits'].split(';')}
    assert not test_groups & {r['pipeline_group'] for r in parts['validation']}
    old_val = {r['record_key'] for r in read(PROCESSED/'training_v2/validation.csv')}
    old_comparison = [dict(record_key=key, current_status=bykey[key]['pipeline_status'],
        current_group=bykey[key]['pipeline_group'], v3_cohort=cohort(bykey[key]) or 'not_eligible')
        for key in sorted(old_val)]
    summary = dict(created_at_utc=datetime.now(timezone.utc).isoformat(), fingerprint=fingerprint,
        pipeline_run=pipeline.relative_to(BASE).as_posix(), protocol=PROTOCOL,
        counts={s:len(rows) for s, rows in parts.items()}, eligible_total=len(eligible),
        reserved_eligible=len(reserved), distributions=distribution(parts),
        old_v2_validation_n=len(old_val),
        old_v2_validation_ids_in_v3=sum(r['record_key'] in old_val for r in parts['validation']),
        test_evaluated=False, test_rows_copied=False, model_trained=False,
        raw_labels_unchanged=True, group_overlap=False,
        limitations=['Automatically screened asking prices, not verified transaction values.',
                    'Heuristic duplicate detection may miss or overgroup assets.',
                    'Validation is used for model choice, not independent test evidence.',
                    'Mixed old/new administrative units remain distinct; no guessed ward mapping.',
                    'Few apartment samples and source imbalance limit coverage.'])
    stage = OUT / 'runs' / ('.building_' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    for split, rows in parts.items():
        write_csv(stage / (split+'.csv'), rows, FIELDS)
    write_csv(stage/'split_registry.csv', registry, REGISTRY_FIELDS)
    write_csv(stage/'reserved_holdout_registry.csv', reserved, REGISTRY_FIELDS)
    write_csv(stage/'old_validation_membership.csv', old_comparison, list(old_comparison[0]))
    write_json(stage/'summary.json', summary)
    write_json(stage/'protocol.json', PROTOCOL)
    lines = ['# Training v3: dữ liệu phát triển đã chốt', '',
        'Giá tổng rao bán, đơn vị triệu VND. Giữ nguyên nhãn của pipeline; không sửa giá/diện tích.', '',
        '| Loại | Train | Validation |', '|---|---:|---:|']
    for category in CATEGORIES:
        lines.append(f'| {category} | {summary["distributions"]["train"]["by_category"].get(category,0)} | '
                     f'{summary["distributions"]["validation"]["by_category"].get(category,0)} |')
    lines += ['', f'Tổng: **{len(parts["train"]):,} train, {len(parts["validation"]):,} validation**; '
        f'{len(reserved):,} tin qua lọc khác giữ riêng. Không chép nhãn test sang v3.', '',
        'Validation lấy toàn bộ đại diện qua lọc có reservation validation và không có reservation test. '
        'Nhóm có cả train/validation từ các thí nghiệm cũ chỉ dùng cho validation. '
        'Mọi nhóm validation/test cũ bị cấm vào train. Quy tắc được chốt trước khi chạy mô hình.', '',
        f'Có {summary["old_v2_validation_ids_in_v3"]}/{len(old_val)} ID validation v2 xuất hiện trong validation v3. '
        'Tập mới khác thành phần và có dữ liệu từng liên quan các thí nghiệm cũ; '
        'không so trực tiếp MAE với báo cáo v2, không gọi đây là test độc lập.', '',
        '`train.csv`, `validation.csv`: trường đầu vào có cấu trúc và nhãn; '
        'metadata ID/URL/nhóm/nguồn/chất lượng chỉ phục vụ truy vết, không đưa vào ma trận đặc trưng. '
        'Không chép raw_json/tiêu đề/mô tả/đơn giá vào đầu vào mô hình.', '',
        '`split_registry.csv` và `reserved_holdout_registry.csv` lưu ID/nhóm, không có giá hoặc diện tích. '
        '`summary.json` lưu phân bố nguồn, địa bàn, khoảng giá/diện tích và độ phủ ngày. '
        '`manifest.json` chốt hash đầu vào, đầu ra và các artifact cũ.', '',
        'Phường lấy đúng trường nguồn, số phòng chỉ nhận số nguyên 1–30; đất để thiếu số phòng. '
        'Không trích giá hoặc đặc trưng từ tiêu đề. Encoder/trung vị/chuẩn hóa chỉ học từ train.', '',
        'Đây là dữ liệu thử nghiệm cho đồ án, chưa đại diện đầy đủ thị trường. '
        '137 tin test cũ giữ nguyên và không được chấm trong đợt này.', '']
    (stage/'README.md').write_text('\n'.join(lines), encoding='utf-8')
    verify(inputs)
    verify(protected)
    verify(saved['input_sha256'])
    write_json(stage/'manifest.json', dict(fingerprint=fingerprint, input_sha256=inputs,
        protected_sha256=protected, output_sha256=outputs(stage), complete=True))
    stage.rename(target)
    publish(target)
    print(json.dumps(dict(run=str(target), counts=summary['counts'],
                         reserved_eligible=len(reserved)), ensure_ascii=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--pipeline-dir', type=Path)
    args = parser.parse_args()
    directory = args.pipeline_dir or (PROCESSED/'collection_pipeline' /
        json.loads((PROCESSED/'collection_pipeline/latest.json').read_text())['run'])
    main(directory.resolve())
