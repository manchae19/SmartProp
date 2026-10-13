"""Diagnose frozen v3 validation and preregister a new-data verification pilot."""
import hashlib
import json
import math
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import training_v3_common as common
from training_v3_common import (BASE, PROCESSED, CATEGORIES, read, sha, verify,
    write_csv, write_json, outputs, scores)

OUT = PROCESSED/'training_v3_diagnostics'
POLICY = dict(small_location_train_n=10, small_validation_group_n=10,
    unit_price_tail_quantiles=[.01,.99], high_error_ape_pct=50, largest_errors_n=20,
    benchmark_pilot_per_category=50,
    label_action='Diagnostic flags only; no automatic relabeling, deletion or retraining.',
    benchmark_selection='Consecutive independently reviewed new assets by category, never by model residual.')
BENCHMARK_FIELDS = ['record_key','source','source_listing_id','detail_url','first_observed_at',
    'displayed_date','date_basis','category','area_sqm','price_million','currency',
    'location_feature','ward_source','rooms','transaction_type','geography_evidence',
    'total_asking_price_verified','reviewed_by','reviewed_at','source_evidence_sha256',
    'physical_duplicate_status','dedupe_reviewed_by','dedupe_evidence','review_decision','notes']


def latest(name):
    directory = PROCESSED/name
    return directory/json.loads((directory/'latest.json').read_text())['run']


def previous_artifact_stats():
    result = {}
    for path in sorted(PROCESSED.rglob('*')):
        if path.is_file() and OUT not in path.parents:
            stat = path.stat()
            result[path.relative_to(BASE).as_posix()] = [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns]
    return result


def selected_predictions(validation, predictions):
    chosen = [r for r in predictions if r['selected'] == 'True']
    if len(chosen) != len(validation):
        raise ValueError('Selected prediction count does not match validation')
    bykey = {r['record_key']:r for r in chosen}
    if len(bykey) != len(chosen) or set(bykey) != {r['record_key'] for r in validation}:
        raise ValueError('Repeated or missing selected validation ID')
    for row in validation:
        p = bykey[row['record_key']]
        if float(p['actual_million']) != float(row['price_million']) or p['category'] != row['category']:
            raise ValueError('Prediction labels/category differ from frozen validation')
        if not math.isfinite(float(p['predicted_million'])):
            raise ValueError('Nonfinite prediction')
    return bykey


def bin_for(value, limits, labels):
    for limit, label in zip(limits, labels):
        if value < limit:
            return label
    return labels[-1]


def price_band(value):
    return bin_for(value, [2000,5000,10000,20000], ['<2 tỷ','2–<5 tỷ','5–<10 tỷ','10–<20 tỷ','≥20 tỷ'])


def area_band(value):
    return bin_for(value, [50,100,200], ['<50 m²','50–<100 m²','100–<200 m²','≥200 m²'])


def evidence_state(row, source):
    if not source:
        return 'no_cached_detail_in_this_review_round', []
    if not source.get('identity_verified') or not source.get('structure_verified'):
        return 'cached_identity_or_structure_unverified', []
    flags = []
    for field in ('price_million', 'area_sqm'):
        value = source.get(field)
        if value is not None and abs(float(value)-float(row[field])) > .01:
            flags.append('cached_detail_'+field+'_differs_from_snapshot')
    return ('cached_header_matches_snapshot' if not flags else 'cached_header_differs_from_snapshot'), flags


def train_statistics(train):
    result = {}
    for category in CATEGORIES:
        rows = [r for r in train if r['category'] == category]
        if not rows:
            continue
        units = [float(r['price_million'])/float(r['area_sqm']) for r in rows]
        lo, hi = map(float, np.quantile(units, POLICY['unit_price_tail_quantiles']))
        result[category] = dict(n=len(rows), unit_q01=lo, unit_q99=hi,
            area_min=min(float(r['area_sqm']) for r in rows),
            area_max=max(float(r['area_sqm']) for r in rows),
            locations=dict(Counter(r['location_feature'] for r in rows)))
    return result


def diagnostic_row(row, stat, source):
    area, price = float(row['area_sqm']), float(row['price_million'])
    unit = price/area
    support = stat['locations'].get(row['location_feature'],0)
    state, flags = evidence_state(row, source)
    if unit < stat['unit_q01'] or unit > stat['unit_q99']:
        flags.append('unit_price_outside_train_q01_q99')
    if area < stat['area_min'] or area > stat['area_max']:
        flags.append('area_outside_train_category_range')
    return dict(record_key=row['record_key'], split=row['model_split'], category=row['category'],
        source=row['source'], location_feature=row['location_feature'],
        detail_url=row['detail_url'], displayed_date=row['displayed_date'],
        area_sqm=area, actual_million=price, unit_price_million=unit,
        train_location_n=support, location_support='unseen' if support == 0
            else 'below_10' if support < POLICY['small_location_train_n'] else 'at_least_10',
        ward_status='available' if row['ward_source'] else 'missing',
        rooms_status='not_applicable_land' if row['category'] == 'Đất nền'
            else 'available' if row['rooms'] else 'missing',
        price_band=price_band(price), area_band=area_band(area),
        evidence_state=state, evidence_sha256=source.get('detail_sha256','') if source else '',
        diagnostic_flags=';'.join(sorted(flags)),
        label_action='none; independent source verification required')


def segment_metrics(rows, dimension):
    result = []
    for category in CATEGORIES:
        subset = [r for r in rows if r['category'] == category]
        for value in sorted({r[dimension] for r in subset}):
            members = [r for r in subset if r[dimension] == value]
            info = scores([r['actual_million'] for r in members], [r['predicted_million'] for r in members])
            info.update(category=category, dimension=dimension, segment=value,
                signed_mean_error_million=float(np.mean([r['signed_error_million'] for r in members])),
                n_below_10=len(members)<POLICY['small_validation_group_n'],
                interpretation='Descriptive association, not a causal effect or an independent benchmark.')
            result.append(info)
    return result


def publish(target):
    relative = target.relative_to(OUT).as_posix()
    write_json(OUT/'latest.json', dict(run=relative))
    (OUT/'README.md').write_text('# Chẩn đoán mô hình SmartProp v3\n\n'
        f'[Mở báo cáo và kế hoạch kiểm chứng]({relative}/README.md).\n', encoding='utf-8')


def main():
    data, models = latest('training_v3'), latest('models_v3_validation')
    ds = json.loads((data/'summary.json').read_text(encoding='utf-8'))
    pipeline = BASE/ds['pipeline_run']
    report = json.loads((models/'metrics.json').read_text(encoding='utf-8'))
    if report['dataset_run'] != data.relative_to(BASE).as_posix():
        raise ValueError('Model/dataset mismatch')
    for root in (data, models):
        frozen = json.loads((root/'manifest.json').read_text(encoding='utf-8'))
        verify(frozen['output_sha256'], root)
        verify(frozen['input_sha256'])
    source_review = PROCESSED/'collection_source_review/review_manifest.json'
    source_manifest = json.loads(source_review.read_text(encoding='utf-8'))
    if not source_manifest['complete']:
        raise ValueError('Source review is not finalized')
    evidence_relative = 'processed/collection_source_review/parsed_evidence.json'
    verify({evidence_relative:source_manifest['output_sha256'][evidence_relative]})
    inputs = [data/'manifest.json', data/'train.csv', data/'validation.csv',
        data/'reserved_holdout_registry.csv', models/'manifest.json', models/'metrics.json',
        models/'validation_predictions.csv', pipeline/'all_listings.csv', pipeline/'manifest.json',
        PROCESSED/'collection_source_review/parsed_evidence.json', source_review,
        Path(__file__), Path(common.__file__)]
    inputs += [PROCESSED/f'training_v{i}/test.csv' for i in (1,2)]
    hashes = {p.relative_to(BASE).as_posix():sha(p) for p in inputs}
    fingerprint = hashlib.sha256(json.dumps(dict(inputs=hashes, policy=POLICY),
                                            sort_keys=True).encode()).hexdigest()
    target = OUT/'runs'/fingerprint[:16]
    if (target/'manifest.json').exists():
        old = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        verify(old['input_sha256'])
        verify(old['output_sha256'], target)
        publish(target)
        print('Existing v3 diagnostics verified: '+str(target))
        return
    protected_stats = previous_artifact_stats()
    train, validation = read(data/'train.csv'), read(data/'validation.csv')
    prediction_bykey = selected_predictions(validation, read(models/'validation_predictions.csv'))
    statistics = train_statistics(train)
    evidence = json.loads((PROCESSED/'collection_source_review/parsed_evidence.json').read_text(encoding='utf-8'))
    source_bykey = {r['record_key']:r for r in read(pipeline/'all_listings.csv')}
    details, validation_details = [], []
    for row in train + validation:
        origin = source_bykey[row['record_key']]
        for field in ('price_million','area_sqm','category','pipeline_group'):
            if row[field] != origin[field]:
                raise ValueError('Frozen pipeline label/group mismatch')
        detail = diagnostic_row(row, statistics[row['category']], evidence.get(row['record_key']))
        detail.update(title=origin['title'], address_raw=origin['address_raw'],
            label_quality=row['label_quality'], input_file=origin['input_file'], input_row=origin['input_row'],
            selected_model=report['categories'][row['category']]['selected_by_validation_mae'])
        detail['selected_model_uses_ward_or_rooms'] = detail['selected_model'] == 'xgboost_enriched_log'
        if row['model_split'] == 'validation':
            p = float(prediction_bykey[row['record_key']]['predicted_million'])
            actual = float(row['price_million'])
            detail.update(predicted_million=p, signed_error_million=p-actual,
                absolute_error_million=abs(p-actual), ape_pct=100*abs(p-actual)/actual)
            validation_details.append(detail)
        details.append(detail)
    all_metric = scores([r['actual_million'] for r in validation_details],
                       [r['predicted_million'] for r in validation_details])
    for metric, value in all_metric.items():
        np.testing.assert_allclose(value, report['aggregate_selected_validation'][metric], rtol=1e-9)
    segments = []
    for dimension in ('source','location_feature','price_band','area_band','ward_status',
                      'rooms_status','location_support','evidence_state'):
        segments += segment_metrics(validation_details, dimension)
    largest = sorted(validation_details, key=lambda r:r['absolute_error_million'], reverse=True)
    priority_keys = {r['record_key'] for r in largest[:POLICY['largest_errors_n']]}
    priority_keys |= {r['record_key'] for r in largest if r['ape_pct']>POLICY['high_error_ape_pct']}
    priority = []
    for rank, row in enumerate(largest,1):
        if row['record_key'] not in priority_keys:
            continue
        reasons = []
        if rank <= POLICY['largest_errors_n']:
            reasons.append('top20_absolute_error')
        if row['ape_pct']>POLICY['high_error_ape_pct']:
            reasons.append('ape_above_50pct')
        priority.append(dict(row, absolute_error_rank=rank, priority_reasons=';'.join(reasons)))
    label_candidates = [r for r in details if r['diagnostic_flags']]
    total_error = sum(r['absolute_error_million'] for r in largest)
    categories = {}
    for category in CATEGORIES:
        tr = [r for r in train if r['category']==category]
        va = [r for r in validation_details if r['category']==category]
        categories[category] = dict(train_n=len(tr), validation_n=len(va),
            selected_model=report['categories'][category]['selected_by_validation_mae'],
            metrics=scores([r['actual_million'] for r in va], [r['predicted_million'] for r in va]),
            train_ward_available_pct=100*sum(bool(r['ward_source']) for r in tr)/len(tr),
            train_rooms_available_pct=None if category=='Đất nền' else 100*sum(bool(r['rooms']) for r in tr)/len(tr),
            validation_low_location_support_n=sum(r['train_location_n']<10 for r in va),
            label_review_candidates_n=sum(r['category']==category for r in label_candidates))
    new_registry = [dict(record_key=r['record_key'], source=r['source'],
        source_listing_id=r['source_listing_id'], detail_url=r['detail_url'],
        pipeline_group=r['pipeline_group']) for r in source_bykey.values()]
    assert len(new_registry)==len({r['record_key'] for r in new_registry})
    stage = OUT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    coverage_fields = [k for k in details[0] if k not in ('predicted_million','signed_error_million',
                                                        'absolute_error_million','ape_pct')]
    write_csv(stage/'record_diagnostics.csv', [{k:r[k] for k in coverage_fields} for r in details], coverage_fields)
    write_csv(stage/'validation_diagnostics.csv', largest, list(largest[0]))
    write_csv(stage/'segment_metrics.csv', segments, list(segments[0]))
    write_csv(stage/'validation_priority_review.csv', priority, list(priority[0]))
    write_csv(stage/'label_review_candidates.csv', [{k:r[k] for k in coverage_fields} for r in label_candidates], coverage_fields)
    # Registry deliberately has no price, area, title or model prediction columns.
    write_csv(stage/'benchmark_exclusion_registry.csv', new_registry, list(new_registry[0]))
    write_csv(stage/'benchmark_candidates_template.csv', [], BENCHMARK_FIELDS)
    plans = [dict(category=c, proposed_target=POLICY['benchmark_pilot_per_category'],
                  collected=0, verified=0, status='not_collected') for c in CATEGORIES]
    write_csv(stage/'benchmark_collection_plan.csv', plans, list(plans[0]))
    freeze = datetime.now(timezone.utc).isoformat()
    benchmark = dict(status='prepared_not_collected', freeze_at_utc=freeze,
        model_run=models.relative_to(BASE).as_posix(), model_manifest_sha256=sha(models/'manifest.json'),
        proposed_per_category=POLICY['benchmark_pilot_per_category'],
        proposed_total=POLICY['benchmark_pilot_per_category']*len(CATEGORIES),
        actual_collected=0, actually_scored=0, exclusion_source_ids=len(new_registry),
        dedupe_requirement='Exclude every previously collected ID and any suspected same asset across sources, dates or address aliases; independent evidence review required.',
        timestamp_requirement='First observed after protocol freeze. An update/display date alone does not prove initial publication or a future-time listing.',
        label_requirement='Independently verify source identity, sale, ordinary asset type, total asking price, area, Da Nang geography and evidence hash before revealing predictions.',
        selection=POLICY['benchmark_selection'],
        eligibility=dict(categories=CATEGORIES, geography='Old or expanded Da Nang with explicit address evidence.',
            transaction='Sale of an ordinary single house, land parcel or apartment, not rent or whole commercial buildings.',
            currency='VND; price_million is total asking price in million VND, not per-m2, a deposit, installment or a starting range.',
            numeric='Price and area must be finite and positive, verified independently from the main source listing.',
            date='Record actual first observation with timezone after freeze; preserve displayed date and its semantics separately.',
            uniqueness='No previously collected source ID or suspected physical-asset overlap; documented independent dedupe review.',
            sampling='First 50 qualifying, independently reviewed assets per category in observation order; log all excluded/rejected records and reasons.',
            out_of_train_range='Retain valid ordinary assets outside the observed train range and report them separately; do not suppress extremes to improve scores.'),
        review_columns=BENCHMARK_FIELDS, minimum_statistical_guarantee=False,
        scoring_rule='Keep models, encoders and selection fixed; report all collected/rejected/verified counts and per-category errors; do not use benchmark to tune.')
    write_json(stage/'benchmark_protocol.json', benchmark)
    summary = dict(created_at_utc=freeze, fingerprint=fingerprint,
        dataset_run=data.relative_to(BASE).as_posix(), model_run=models.relative_to(BASE).as_posix(),
        train_n=len(train), validation_n=len(validation), aggregate=all_metric, categories=categories,
        top10_absolute_error_share_pct=100*sum(r['absolute_error_million'] for r in largest[:10])/total_error,
        validation_priority_n=len(priority), label_review_candidates_n=len(label_candidates),
        label_review_candidates_by_split=dict(Counter(r['split'] for r in label_candidates)),
        label_review_flags=dict(Counter(flag for r in label_candidates for flag in r['diagnostic_flags'].split(';'))),
        benchmark=benchmark, new_model_trained=False, test_evaluated=False, labels_changed=False,
        integrity='Frozen dataset/model outputs and analysis inputs verified by SHA256; other prior artifacts compared by size/mtime/ctime before and after this read-only analysis.',
        policy=POLICY,
        limitations=['Diagnostic associations do not prove why a model fails.',
            'Validation was used for selection; no new independent performance result.',
            'Tail prices/large residuals do not prove incorrect source labels.',
            'Cache coverage is only this source-review round, not all historical verifications.',
            'Header agreement is not independent confirmation of total market/transaction value.',
            'The benchmark pilot target is a workload proposal, not an accuracy guarantee.'])
    write_json(stage/'summary.json', summary)
    lines = ['# SmartProp v3: phân tích lỗi và chuẩn bị kiểm chứng', '',
        f'Phân tích **{len(validation)} validation**, đối chiếu độ phủ từ **{len(train):,} train**. '
        'Dùng đúng dự đoán và nhãn v3 đã chốt; không huấn luyện lại hoặc chấm test.', '',
        '| Loại | Train | Val | Mô hình chọn | MAE (triệu VND) | MedAPE | APE >50% |',
        '|---|---:|---:|---|---:|---:|---:|']
    for category, info in categories.items():
        m = info['metrics']
        lines.append(f'| {category} | {info["train_n"]} | {info["validation_n"]} | '
            f'{info["selected_model"]} | {m["mae_million"]:,.1f} | {m["median_ape_pct"]:.1f}% | {m["above_50pct"]} |')
    lines += ['', f'Có **{all_metric["above_50pct"]}** tin APE >50%; '
        f'10 lỗi lớn nhất chiếm **{summary["top10_absolute_error_share_pct"]:.1f}%** tổng sai số tuyệt đối. '
        f'Tỷ lệ dự đoán lệch không quá 20% là **{all_metric["within_20pct"]:.1f}%**.', '',
        '## Những gì có thể kết luận', '',
        'Nhà và đất còn sai số lớn. Hai mô hình được chọn cho các nhóm này chỉ dùng diện tích và địa bàn; '
        'chưa diễn tả số tầng, mặt tiền/hẻm, vị trí đường hoặc chất lượng công trình. '
        'Đây là giới hạn đặc trưng, chưa phải bằng chứng rằng bổ sung từng trường sẽ giảm sai số.', '',
        '| Loại | Train có phường nguồn | Train có số phòng | Val có <10 train cùng địa bàn |',
        '|---|---:|---:|---:|']
    for category, info in categories.items():
        room = 'Không áp dụng' if info['train_rooms_available_pct'] is None else f'{info["train_rooms_available_pct"]:.1f}%'
        lines.append(f'| {category} | {info["train_ward_available_pct"]:.1f}% | {room} | {info["validation_low_location_support_n"]} |')
    lines += ['', 'Thiếu phường/số phòng chỉ là mô tả dữ liệu. Ridge nhà và baseline đất hiện không dùng '
        'hai trường này; không diễn giải tương quan trong từng nhóm thành nguyên nhân hoặc tác động nhân quả.', '',
        '## Địa bàn có MAE cao trong nhóm đủ 10 mẫu validation', '',
        '| Loại | Địa bàn | Val n | MAE (triệu VND) | MedAPE |',
        '|---|---|---:|---:|---:|']
    for category in CATEGORIES:
        locations = sorted((r for r in segments if r['category']==category
            and r['dimension']=='location_feature' and not r['n_below_10']),
            key=lambda r:r['mae_million'], reverse=True)[:3]
        for value in locations:
            lines.append(f'| {category} | {value["segment"]} | {value["n"]} | '
                         f'{value["mae_million"]:,.1f} | {value["median_ape_pct"]:.1f}% |')
    lines += ['', 'Đây là xếp hạng mô tả trên validation hiện tại. MAE giữa các địa bàn còn phụ thuộc '
        'mặt bằng giá; không dùng bảng này làm quy tắc loại tin hoặc cam kết độ chính xác.', '',
        '## Hàng chờ rà soát', '',
        f'- [validation_priority_review.csv](validation_priority_review.csv): **{len(priority)} tin**, '
        'hợp của top 20 sai số tuyệt đối và mọi APE >50%. Có URL, nhãn nguồn, sai số, lý do ưu tiên.',
        f'- [label_review_candidates.csv](label_review_candidates.csv): **{len(label_candidates)} tin train/validation**, '
        'được gắn tín hiệu theo giá/m² nằm ngoài phân vị 1–99% của train cùng loại, diện tích ngoài miền train '
        'hoặc header cache khác snapshot. Quy tắc áp dụng toàn bộ train/validation, không phụ thuộc sai số dự đoán.',
        '- Đây là hai hàng chờ kiểm tra, có thể chồng lặp. Không phải danh sách nhãn sai; không tự sửa giá/diện tích '
        'hoặc xóa tin vì nằm ở đuôi phân bố.', '',
        'Ví dụ `cafeland:3164071`: biệt thự 403 m², snapshot 1.000 triệu; dự đoán Ridge khoảng 24.572 triệu. '
        'Header và giá có cấu trúc trong cache cũng ghi 1.000 triệu; phần mô tả không có giá tổng thay thế. '
        'Cần xác minh độc lập giá rao là giá tổng thực sự. Không dùng dự đoán làm giá thay thế.', '',
        'Các đất giá cao ở Ngũ Hành Sơn/Sơn Trà có sai số tuyệt đối lớn cũng chưa chứng minh nhãn sai. '
        'Tên đường, góc/mặt tiền hoặc vị trí sát biển có thể là hướng khảo sát đặc trưng, cần bằng chứng và '
        'thử nghiệm phát triển riêng; không đưa số tiền trong tiêu đề vào đầu vào.', '',
        '## Chỉ số theo phân nhóm', '',
        '[segment_metrics.csv](segment_metrics.csv) chứa MAE, RMSE, MAPE, MedAPE, tỷ lệ lệch ≤20%, '
        'bias trung bình và số mẫu theo loại × nguồn/địa bàn/khoảng giá/diện tích/độ phủ trường/độ hỗ trợ địa bàn. '
        'Nhóm n<10 được đánh dấu. Phân nhóm theo giá chỉ phục vụ chẩn đoán, không phải đặc trưng đầu vào.', '',
        '## Kiểm chứng trên dữ liệu mới', '',
        '**Mới chuẩn bị quy trình, chưa thu thập hoặc chấm tin mới (0 tin).** '
        'Đề xuất pilot 50 tài sản mới mỗi loại, tổng 150; đây là quy mô công việc đề xuất, không bảo đảm thống kê.', '',
        f'- [benchmark_exclusion_registry.csv](benchmark_exclusion_registry.csv): toàn bộ **{len(new_registry):,} ID nguồn** '
        'đã thấy, kèm URL và nhóm, không chứa giá/diện tích/tiêu đề. Loại khỏi pilot cả ID cũ và tài sản nghi trùng xuyên nguồn.',
        '- [benchmark_candidates_template.csv](benchmark_candidates_template.csv): mẫu trống để nhập dữ liệu mới và '
        'bằng chứng duyệt giá tổng, diện tích, loại tài sản, địa bàn, timestamp và kiểm tra nghi trùng.',
        '- [benchmark_protocol.json](benchmark_protocol.json) chốt model/manifest và thời điểm bắt đầu trước khi '
        'thu thập. Lấy các tin đủ điều kiện liên tiếp theo loại; không chọn theo dự đoán đẹp/xấu.',
        '- Người xác minh chốt nhãn và khả năng trùng trước khi xem dự đoán. Giá mục tiêu vẫn là giá rao, '
        'không gọi là giá giao dịch. Ngày cập nhật không chứng minh ngày đăng đầu tiên hoặc tính độc lập theo thời gian.',
        '- Giữ cố định mô hình/encoder/lựa chọn; báo cáo cả tin thu thập, bị loại và được duyệt. '
        'Không dùng kết quả pilot để tối ưu rồi tiếp tục gọi nó là test độc lập.', '',
        '## Chạy lại', '', '```powershell',
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/analyze_training_v3.py',
        '```', '', 'Cùng đầu vào/mã: xác minh bản đã chốt, không ghi đè. Raw, bộ/model v1/v2/v3, '
        'các quyết định cũ và 137 tin test giữ nguyên.', '']
    (stage/'README.md').write_text('\n'.join(lines), encoding='utf-8')
    verify(hashes)
    if previous_artifact_stats() != protected_stats:
        raise ValueError('A previous processed artifact changed during diagnostics')
    write_json(stage/'manifest.json', dict(fingerprint=fingerprint, complete=True,
        input_sha256=hashes, protected_stat=protected_stats, output_sha256=outputs(stage)))
    stage.rename(target)
    publish(target)
    print(json.dumps(dict(run=str(target), validation_priority_n=len(priority),
        label_review_candidates_n=len(label_candidates), benchmark_collected=0), ensure_ascii=False))


if __name__ == '__main__':
    main()
