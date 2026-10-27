"""Describe frozen validation errors; never load models, fit, relabel or score holdouts."""
import hashlib
import json
import math
from collections import Counter, defaultdict
from pathlib import Path
from statistics import mean, median
import uuid

import training_v3_common as c

MODEL = c.PROCESSED / 'models_v6_ablation/runs/b4b1339d3f35857e'
FEATURES = c.PROCESSED / 'property_features_v6/runs/6c9b866cdd95c66d'
OUT = c.PROCESSED / 'models_v6_diagnostics'
CATALOG = c.BASE.parent / 'core/location_catalog_v6.json'
REPO = c.BASE.parents[2]
POLICY = dict(small_group_n=10, planning_min_train_per_observed_location=10,
              cohort='299 previously used development validation records',
              planning_order='train support only; not ranked by validation residual',
              label_action='none; high residual is not proof of an incorrect label',
              retrained=False, new_predictions=False, pilot_read=False, new_network_requests=0)


def unique(rows, fields):
    result = {}
    for row in rows:
        key = tuple(row[f] for f in fields)
        if key in result:
            raise ValueError('Duplicate join key: ' + str(key))
        result[key] = row
    return result


def score(rows, column='predicted_million'):
    if not rows:
        raise ValueError('Cannot describe an empty group')
    actual = [float(r['actual_million']) for r in rows]
    predicted = [float(r[column]) for r in rows]
    if any(not math.isfinite(v) or v <= 0 for v in actual + predicted):
        raise ValueError('Prices must be finite and positive')
    signed = [p-y for y,p in zip(actual,predicted)]
    absolute = [abs(v) for v in signed]
    ape = [100*e/y for e,y in zip(absolute,actual)]
    return dict(n=len(rows), mae_million=mean(absolute), mape_pct=mean(ape),
                median_ape_pct=median(ape), within_20pct=100*sum(v <= 20 for v in ape)/len(rows),
                above_50pct=sum(v > 50 for v in ape), signed_mean_error_million=mean(signed),
                total_absolute_error_million=sum(absolute), underpredicted_n=sum(v < 0 for v in signed))


def join_rows(train, validation, features, predictions):
    t, v = unique(train, ['record_key']), unique(validation, ['record_key'])
    f, p = unique(features, ['record_key']), unique(predictions, ['record_key','arm'])
    if set(t) & set(v) or {r['pipeline_group'] for r in train} & {r['pipeline_group'] for r in validation}:
        raise ValueError('Train/validation ID or group leakage')
    if set(f) != set(t) | set(v):
        raise ValueError('Feature cohort does not match train and validation')
    for arm in ['all','control']:
        if {key[0] for key in p if key[1] == arm} != {key[0] for key in v}:
            raise ValueError('Incomplete prediction cohort for ' + arm)
    support = Counter((r['category'],r['location_feature']) for r in train)
    result = []
    for row in validation:
        key = row['record_key']
        feature = f[(key,)]
        chosen, control = p[(key,'all')], p[(key,'control')]
        for prediction in [chosen,control]:
            if any(prediction[name] != row[name] for name in ['category','source','pipeline_group']):
                raise ValueError('Prediction metadata mismatch: ' + key)
            if float(prediction['actual_million']) != float(row['price_million']):
                raise ValueError('Prediction label mismatch: ' + key)
        if feature['category'] != row['category'] or feature['model_split'] != 'validation':
            raise ValueError('Feature metadata mismatch: ' + key)
        actual, predicted = float(row['price_million']), float(chosen['predicted_million'])
        error = abs(predicted-actual)
        if not math.isclose(error,float(chosen['absolute_error_million']),rel_tol=1e-10,abs_tol=1e-8):
            raise ValueError('Stored error does not reconcile')
        item = {k:row[k] for k in ['record_key','category','source','pipeline_group','location_feature','area_sqm']}
        item.update(actual_million=actual,predicted_million=predicted,control_predicted_million=float(control['predicted_million']),
                    signed_error_million=predicted-actual,absolute_error_million=error,ape_pct=100*error/actual,
                    train_location_n=support[(row['category'],row['location_feature'])],
                    price_band='<2 tỷ' if actual<2000 else '2–<5 tỷ' if actual<5000 else '5–<10 tỷ' if actual<10000 else '≥10 tỷ',
                    area_band='<50 m²' if float(row['area_sqm'])<50 else '50–<100 m²' if float(row['area_sqm'])<100 else '≥100 m²',
                    ward_status='available' if row['ward_source'] else 'missing',
                    rooms_status='not_applicable' if row['category']=='Đất nền' else 'available' if feature['rooms_completed'] else 'missing',
                    floors_status='not_applicable' if row['category']!='Nhà ở' else 'available' if feature['floors_claim'] else 'missing',
                    access_status='not_applicable' if row['category']=='Căn hộ chung cư' else feature['access_claim'] or 'missing',
                    label_action='none; DO_NOT_TRAIN')
        result.append(item)
    score(result)
    return sorted(result,key=lambda r:r['record_key'])


def segments(rows):
    output = []
    for category in ['ALL']+c.CATEGORIES:
        subset = rows if category=='ALL' else [r for r in rows if r['category']==category]
        for dimension in ['location_feature','source','price_band','area_band','ward_status','rooms_status','floors_status','access_status']:
            groups = defaultdict(list)
            for row in subset:
                groups[row[dimension]].append(row)
            for value, members in sorted(groups.items()):
                output.append(dict(category=category,dimension=dimension,segment=value,**score(members),
                                   small_group=len(members)<POLICY['small_group_n']))
    return output


def coverage(train, validation, labels):
    counts = {split:Counter((r['category'],r['location_feature']) for r in rows)
              for split,rows in [('train',train),('validation',validation)]}
    output = []
    for category,location in sorted(set(counts['train']) | set(counts['validation'])):
        n = counts['train'][(category,location)]
        output.append(dict(category=category,location_feature=location,location_label=labels.get(location,'[mã chưa được duyệt]'),
                           train_n=n,validation_n=counts['validation'][(category,location)],
                           public_location=location in labels,
                           planning_gap=max(0,POLICY['planning_min_train_per_observed_location']-n) if location in labels else 0,
                           action='source_review_location' if location not in labels else 'collect_for_train_coverage' if n<POLICY['planning_min_train_per_observed_location'] else 'retain_monitor'))
    return output


def close_metrics(actual, reference):
    for key in ['n','mae_million','mape_pct','median_ape_pct','within_20pct','above_50pct']:
        if not math.isclose(actual[key],reference[key],rel_tol=1e-9,abs_tol=1e-8):
            raise ValueError('Frozen metric mismatch: ' + key)


def write_csv(path, rows):
    if not rows:
        raise ValueError('Expected nonempty report table: ' + path.name)
    c.write_csv(path,rows,list(rows[0]))


def main():
    protected = {}
    for directory in [MODEL,FEATURES]:
        manifest = json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        c.verify(manifest['output_sha256'],directory)
        protected.update({(directory/name).relative_to(c.BASE).as_posix():digest for name,digest in manifest['output_sha256'].items()})
        protected[(directory/'manifest.json').relative_to(c.BASE).as_posix()] = c.sha(directory/'manifest.json')
    for name in ['training_v3_common.py','property_text_features_v6.py']:
        protected[name] = c.sha(c.BASE/name)
    paths = [MODEL/'validation_predictions.csv',MODEL/'selected_validation_errors.csv',MODEL/'metrics.json',
             MODEL/'manifest.json',FEATURES/'train.csv',FEATURES/'validation.csv',FEATURES/'features.csv',
             FEATURES/'manifest.json',Path(__file__),CATALOG]
    proof = c.PROCESSED/'models_v6_ablation/verification.json'
    verification = json.loads(proof.read_text(encoding='utf-8'))
    if verification.get('verified') is not True or verification.get('run') != 'runs/'+MODEL.name:
        raise ValueError('Model verification must match the pinned v6 run')
    paths.append(proof)
    inputs = {p.resolve().relative_to(REPO).as_posix():c.sha(p) for p in paths}
    fingerprint = hashlib.sha256(json.dumps(dict(inputs=inputs,policy=POLICY),sort_keys=True).encode()).hexdigest()[:16]
    target = OUT/'runs'/fingerprint
    if target.exists():
        manifest = json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        for path,digest in manifest['input_sha256'].items():
            if c.sha(REPO/path)!=digest:raise ValueError('Diagnostic input changed: '+path)
        c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],target)
    else:
        train,validation,features = [c.read(FEATURES/name) for name in ['train.csv','validation.csv','features.csv']]
        if len(train)!=2214 or len(validation)!=299:
            raise ValueError('Unexpected frozen cohorts')
        rows = join_rows(train,validation,features,c.read(MODEL/'validation_predictions.csv'))
        catalog = json.loads(CATALOG.read_text(encoding='utf-8'))
        labels = catalog['legacy'] | catalog['expanded']
        inventory = coverage(train,validation,labels)
        report = json.loads((MODEL/'metrics.json').read_text(encoding='utf-8'))
        chosen,control = score(rows),score(rows,'control_predicted_million')
        close_metrics(chosen,report['arms']['all']['aggregate_validation'])
        close_metrics(control,report['v5_control'])
        by_category = []
        for category in c.CATEGORIES:
            part = [r for r in rows if r['category']==category]
            metrics = score(part)
            close_metrics(metrics,report['arms']['all']['categories'][category]['validation'])
            by_category.append(dict(category=category,train_n=sum(r['category']==category for r in train),**metrics))
        grouped = segments(rows)
        total = chosen['total_absolute_error_million']
        expensive = [r for r in rows if r['actual_million']>=10000]
        summary = dict(policy=POLICY,model_run=MODEL.name,feature_run=FEATURES.name,train_n=len(train),validation_n=len(rows),
                       selected=chosen,control=control,categories=by_category,
                       improvement_vs_v5_mae_pct=100*(1-chosen['mae_million']/control['mae_million']),
                       top10_error_share_pct=100*sum(r['absolute_error_million'] for r in sorted(rows,key=lambda r:r['absolute_error_million'],reverse=True)[:10])/total,
                       price_ge10b_n=len(expensive),price_ge10b_underpredicted_n=sum(r['signed_error_million']<0 for r in expensive),
                       price_ge10b_error_share_pct=100*sum(r['absolute_error_million'] for r in expensive)/total,
                       blocked_train_n=sum(r['train_n'] for r in inventory if not r['public_location']),
                       small_category_location_groups=sum(r['small_group'] for r in grouped if r['category']!='ALL' and r['dimension']=='location_feature'))
        priorities = sorted([r for r in inventory if r['planning_gap']],key=lambda r:(r['train_n'],r['category'],r['location_feature']))
        summary['coverage_planning_gap'] = sum(r['planning_gap'] for r in priorities)
        summary['collection_priority_cells'] = len(priorities)
        work = OUT/('.building_'+uuid.uuid4().hex)
        work.mkdir(parents=True)
        write_csv(work/'validation_errors_DO_NOT_TRAIN.csv',rows)
        write_csv(work/'category_metrics.csv',by_category)
        write_csv(work/'segment_metrics.csv',grouped)
        write_csv(work/'location_coverage.csv',inventory)
        if priorities:write_csv(work/'collection_priorities.csv',priorities)
        c.write_json(work/'summary.json',summary)
        lines = ['# Phân tích sai số XGBoost v6','',
                 'Phân tích 299 dự đoán validation phát triển đã lưu; không fit model, không chấm pilot/holdout, không đổi nhãn hoặc split. Đây là phân tích mô tả sau khi chọn cấu hình, không phải test độc lập.','',
                 '| Loại | Train | Validation | MAE triệu VND | MAPE | Sai số ≤20% |',
                 '|---|---:|---:|---:|---:|---:|']
        for r in by_category:lines.append(f"| {r['category']} | {r['train_n']} | {r['n']} | {r['mae_million']:,.2f} | {r['mape_pct']:.2f}% | {r['within_20pct']:.2f}% |")
        lines += ['',f"Tổng: MAE {chosen['mae_million']:,.2f} triệu VND, MAPE {chosen['mape_pct']:.2f}%, sai số ≤20% {chosen['within_20pct']:.2f}%. So với control v5 trên cùng 299 ID, MAE giảm {summary['improvement_vs_v5_mae_pct']:.2f}%.",
                  f"Top 10 tin chiếm {summary['top10_error_share_pct']:.2f}% sai số tuyệt đối. {len(expensive)} tin giá rao từ 10 tỷ chiếm {summary['price_ge10b_error_share_pct']:.2f}%; {summary['price_ge10b_underpredicted_n']} tin trong nhóm này bị dự đoán thấp hơn giá rao.",'',
                  '## Địa bàn có đủ ít nhất 10 mẫu validation','',
                  '| Loại | Địa bàn | Train | Validation | MAE triệu VND | MAPE |',
                  '|---|---|---:|---:|---:|---:|']
        eligible = sorted([r for r in grouped if r['category']!='ALL' and r['dimension']=='location_feature' and not r['small_group']],key=lambda r:r['total_absolute_error_million'],reverse=True)
        support = {(r['category'],r['location_feature']):r['train_n'] for r in inventory}
        for r in eligible:lines.append(f"| {r['category']} | {labels.get(r['segment'],'Chưa duyệt')} | {support[(r['category'],r['segment'])]} | {r['n']} | {r['mae_million']:,.2f} | {r['mape_pct']:.2f}% |")
        lines += ['',f"Có {summary['small_category_location_groups']} nhóm loại × địa bàn dưới 10 mẫu validation; không xếp hạng độ chính xác ổn định từ các nhóm đó. Thống kê toàn bộ và thiếu đặc trưng nằm trong segment_metrics.csv. Các liên hệ không chứng minh nguyên nhân sai số.",'',
                  '## Ưu tiên bổ sung dữ liệu','',
                  'Ưu tiên theo số mẫu train trong các địa bàn đã xuất hiện; không xếp thứ tự theo residual. Mốc 10 mẫu/cell chỉ là chỉ tiêu lập kế hoạch, không bảo đảm độ chính xác hoặc cỡ mẫu kiểm định. Tin mới vẫn cần giá rao/diện tích/địa bàn có bằng chứng, chống trùng theo tài sản và tách nhóm/thời gian trước khi đánh giá.','',
                  '| Loại | Địa bàn | Train hiện có | Khoảng thiếu đến mốc 10 |',
                  '|---|---|---:|---:|']
        for r in priorities[:15]:lines.append(f"| {r['category']} | {r['location_label']} | {r['train_n']} | {r['planning_gap']} |")
        lines += ['',f"Có {len(priorities)} cell cần bổ sung theo mốc kế hoạch, tổng khoảng thiếu {summary['coverage_planning_gap']} tin. Căn hộ hiện chỉ có 177 train và 31 validation nên cần bổ sung có mục tiêu và tập kiểm chứng mới; không cân bằng bằng cách nhân bản tin.",
                  f"Có {summary['blocked_train_n']} dòng train cũ có mã địa bàn chưa được duyệt. Giữ nguyên snapshot; bản chuẩn bị 2.213 train đã cách ly tin lỗi, chưa huấn luyện lại.",'',
                  'Giá mục tiêu là giá rao. Tin có sai số cao không tự chứng minh nhãn sai; chỉ đối chiếu nguồn độc lập mới được đề xuất sửa. Không lấy giá do AI lưu trong lịch sử làm nhãn. Không đưa pilot đã chấm vào train hoặc gọi lại là test mới. Chưa có tọa độ tài sản được xác minh để thử khoảng cách tiện ích.','']
        (work/'README.md').write_text('\n'.join(lines),encoding='utf-8')
        c.verify(protected)
        c.write_json(work/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(work)))
        target.parent.mkdir(parents=True,exist_ok=True)
        work.rename(target)
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    print('Verified frozen validation diagnostics: '+str(target))


if __name__=='__main__':
    main()
