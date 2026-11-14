"""Prepare fixed missing-bedroom ablation without fitting or scoring a model."""
from collections import Counter
import hashlib
import json
import uuid
import csv
from pathlib import Path

import review_apartment_extension as cohort

BASE=cohort.BASE
SOURCE=cohort.previous.old.PREPARED
OUT=BASE/'processed/v7_trial_preparation'
PROTOCOL=dict(hypothesis='Ambiguous bedroom claims should be missing rather than retain a conflicting structured value',
    configurations=['control_clean_v6_all','mask_conflicting_bedrooms'],
    dataset='2213 prepared train and 299 unchanged development validation; new collection groups held out',
    changed_field='rooms_completed only when conflict_fields contains rooms_completed',
    labels_changed=False,old_splits_changed=False,price_or_text_in_X=False,
    xgboost=dict(objective='reg:squarederror',tree_method='hist',device='cpu',max_depth=3,eta=.03,
        min_child_weight=5,subsample=.8,colsample_bytree=.8,reg_lambda=10,seed=42,nthread=4),
    max_rounds=1500,early_stopping_rounds=50,early_stopping_metric='MAE in original million VND on development validation',
    fit_vocabulary_on_train_only=True,target_transform='natural_log',feature_groups='v6/all',
    collection_evaluation='Only after corrected cohort reaches minimum; freeze both configurations before one-time comparison',
    automatic_deployment=False,geospatial_features=False)


def mask(features):
    result=[];changed=[]
    for row in features:
        copy=dict(row)
        if 'rooms_completed' in row['conflict_fields'].split(';') and row['rooms_completed']!='':
            copy['rooms_completed']='';changed.append(dict(record_key=row['record_key'],model_split=row['model_split'],
                category=row['category'],old_rooms=row['rooms_completed'],new_rooms='',reason='conflicting_bedroom_claims_are_missing'))
        result.append(copy)
    return result,changed


def read_collection(path):
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        return reader.fieldnames,list(reader)


def main():
    import verify_apartment_extension
    verify_apartment_extension.verify()
    review=cohort.OUT/json.loads((cohort.OUT/'latest.json').read_text(encoding='utf8'))['run']
    report=json.loads((review/'summary.json').read_text(encoding='utf8'))
    paths=[Path(__file__),SOURCE/'manifest.json',SOURCE/'train.csv',SOURCE/'validation.csv',SOURCE/'features.csv',
           SOURCE/'reserved_holdout_registry.csv',review/'manifest.json',review/'cohort_lock.json',review/'collection_holdout.csv']
    hashes={p.relative_to(BASE.parents[2]).as_posix():cohort.collector.source.sha(p) for p in paths}
    digest=hashlib.sha256(json.dumps(dict(inputs=hashes,protocol=PROTOCOL),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/digest
    if target.exists():
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf8'))
        if manifest['input_sha256']!=hashes:raise ValueError('Preparation stale')
        for name,value in manifest['output_sha256'].items():
            if cohort.collector.source.sha(target/name)!=value:raise ValueError('Prepared output changed')
        print('Existing untrained preparation verified: '+str(target));return
    train=cohort.previous.old.read_csv(SOURCE/'train.csv');validation=cohort.previous.old.read_csv(SOURCE/'validation.csv')
    features=cohort.previous.old.read_csv(SOURCE/'features.csv');masked,changed=mask(features)
    if len(train)!=2213 or len(validation)!=299:raise ValueError('Unexpected prepared cohort')
    output=OUT/'runs'/('.building_'+uuid.uuid4().hex);output.mkdir(parents=True)
    for name,rows in [('train.csv',train),('validation.csv',validation),('features_control.csv',features),('features_masked.csv',masked)]:
        cohort.previous.old.write_csv(output/name,rows,list(rows[0]))
    cohort.previous.old.write_csv(output/'feature_changes.csv',changed,['record_key','model_split','category','old_rooms','new_rooms','reason'])
    collection_fields,collection_rows=read_collection(review/'collection_holdout.csv')
    cohort.previous.old.write_csv(output/'collection_DO_NOT_TRAIN.csv',collection_rows,collection_fields)
    (output/'protocol.json').write_text(json.dumps(PROTOCOL,ensure_ascii=False,indent=2),encoding='utf8')
    summary=dict(train=2213,validation=299,holdout_groups=report['collection_holdout'],minimum_groups=report['minimum_groups'],
        evaluation_gate_passed=report['evaluation_gate_passed'],missing_groups=report['missing_groups'],
        feature_changes=dict(Counter(r['model_split']+'|'+r['category'] for r in changed)),
        labels_changed=0,model_fits=0,model_predictions=0,production_model_changed=False,
        status='prepared_untrained' if report['evaluation_gate_passed'] else 'prepared_waiting_for_more_verified_groups')
    (output/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    (output/'README.md').write_text(f'''# Chuẩn bị thử nghiệm v7, chưa huấn luyện

Train 2.213, validation phát triển 299; giữ nguyên nhãn/ID/split.
Thử đúng hai cấu hình đã chốt: control v6/all trên bộ sạch và để missing
số phòng khi bằng chứng mâu thuẫn. Thay đổi feature: {summary['feature_changes']}.
Không thêm giá/đơn giá/tiêu đề/mô tả vào X, không có tọa độ/khoảng cách giả.

Tập kiểm chứng: {summary['holdout_groups']} nhóm, thiếu {summary['missing_groups']} so với mốc {summary['minimum_groups']}.
Trạng thái: {summary['status']}. **Chưa fit model hoặc chạy dự đoán.**
`collection_DO_NOT_TRAIN.csv` cấm ghép vào train. Mốc số nhóm không bảo đảm
thống kê; cohort căn hộ chỉ hỗ trợ kết luận thăm dò cho căn hộ.
Model v6 và database đang chạy giữ nguyên.
''',encoding='utf8')
    outputs={p.name:cohort.collector.source.sha(p) for p in output.iterdir() if p.is_file()}
    for path,digest_before in hashes.items():
        if cohort.collector.source.sha(BASE.parents[2]/path)!=digest_before:raise ValueError('Inputs changed during preparation')
    (output/'manifest.json').write_text(json.dumps(dict(input_sha256=hashes,output_sha256=outputs),indent=2),encoding='utf8')
    output.rename(target)
    cohort.collector.source.atomic(OUT/'latest.json',dict(run='runs/'+digest))
    print(json.dumps(summary,ensure_ascii=False))


if __name__=='__main__':main()
