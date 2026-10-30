"""Fixed v4 experiment: expanded train, identical 299-row v3 development validation."""
import hashlib
import json
import platform
import uuid
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
import xgboost as xgb
import training_v3_common as c
import train_training_v3 as v3
import train_smartprop_baseline as baseline
import prepare_smartprop_dataset as preparation
import review_remaining_4772 as review
from verify_remaining_4772 import verify_dataset

OUT=c.PROCESSED/'models_v4_validation'
PROTOCOL=dict(v3.PROTOCOL,dataset_policy='Date and age are optional metadata; all other quality gates retained',
    validation='Exact same 299 IDs, labels and feature values as v3; development validation, not a new test',
    previous_model_unchanged=True,geospatial_features=False,automatic_deployment=False)


def last(root):
    return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def main():
    data=last(review.ROOT)
    proof=json.loads((review.ROOT/'independent_verification.json').read_text(encoding='utf-8'))
    if not proof.get('source_inputs_sha256_verified') or proof['run']!=data.relative_to(review.ROOT).as_posix():
        raise ValueError('Run verify_remaining_4772.py first')
    verify_dataset(data,full_inputs=False)
    folder=data/'training_inputs'
    previous=last(c.PROCESSED/'models_v3_validation')
    prior_manifest=json.loads((previous/'manifest.json').read_text(encoding='utf-8'))
    c.verify(prior_manifest['output_sha256'],previous)
    protected={p.relative_to(c.BASE).as_posix():c.sha(p) for p in [previous/'manifest.json']+
        [previous/name for name in prior_manifest['output_sha256']]}
    paths=[data/'manifest.json',data/'summary.json',previous/'metrics.json',previous/'validation_predictions.csv',
        Path(__file__),Path(c.__file__),Path(v3.__file__),Path(baseline.__file__),Path(preparation.__file__),
        c.BASE/'verify_remaining_4772.py',Path(review.__file__)]
    paths+=list(folder.iterdir())
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths if p.is_file()}
    versions=dict(python=platform.python_version(),numpy=np.__version__,xgboost=xgb.__version__)
    fingerprint=hashlib.sha256(json.dumps(dict(inputs=inputs,protocol=PROTOCOL,versions=versions),sort_keys=True).encode()).hexdigest()
    target=OUT/'runs'/fingerprint[:16]
    if target.exists():
        c.verify(json.loads((target/'manifest.json').read_text(encoding='utf-8'))['output_sha256'],target)
        publish(target)
        print('Existing model run verified: '+str(target));return
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    c.write_json(stage/'protocol.json',PROTOCOL)
    parts={s:c.read(folder/(s+'.csv')) for s in ['train','validation']}
    prior_predictions=c.read(previous/'validation_predictions.csv')
    prior_metrics=json.loads((previous/'metrics.json').read_text(encoding='utf-8'))
    oldmap={(r['record_key'],r['model']):r for r in prior_predictions}
    if len(oldmap)!=len(prior_predictions):
        raise ValueError('Duplicate prior prediction ID/model')
    categories,predictions,models,comparison,errors={},{},{},[],[]
    for index,category in enumerate(c.CATEGORIES,1):
        train=[r for r in parts['train'] if r['category']==category]
        val=[r for r in parts['validation'] if r['category']==category]
        y=np.asarray([float(r['price_million']) for r in val])
        model=baseline.fit(v3.baseline_rows(train))
        models[category]=model
        predicted=v3.get_baseline_predictions(val,model)
        spec=json.loads((folder/f'category_{index}_schema.json').read_text(encoding='utf-8'))
        dt=xgb.DMatrix(folder/f'category_{index}_train.buffer')
        dv=xgb.DMatrix(folder/f'category_{index}_validation.buffer')
        print(f'Training {category}: train={len(train)}, validation={len(val)}, CPU 4 threads',flush=True)
        trained=xgb.train(v3.PARAMS,dt,num_boost_round=PROTOCOL['max_rounds'],evals=[(dv,'validation')],
            custom_metric=v3.log_mae,early_stopping_rounds=PROTOCOL['early_stopping_rounds'],verbose_eval=False)
        best=trained[:trained.best_iteration+1]
        predicted[v3.FAMILIES[2]]=np.exp(np.clip(best.predict(dv),-20,30))
        model_name=f'category_{index}_xgboost.json'
        best.save_model(stage/model_name)
        c.write_json(stage/f'category_{index}_schema.json',spec)
        restored=xgb.Booster();restored.load_model(stage/model_name)
        np.testing.assert_allclose(restored.predict(dv),best.predict(dv),rtol=1e-7,atol=1e-7)
        scores={family:c.scores(y,values) for family,values in predicted.items()}
        selected=min(v3.FAMILIES,key=lambda f:scores[f]['mae_million'])
        categories[category]=dict(train_n=len(train),validation_n=len(val),validation=scores,
            selected_by_validation_mae=selected,selected_validation=scores[selected],
            xgboost_best_iteration=trained.best_iteration,model_file=model_name,schema_file=f'category_{index}_schema.json')
        for family in v3.FAMILIES:
            old=[]
            for row in val:
                prior=oldmap[(row['record_key'],family)]
                if prior['category']!=category or float(prior['actual_million'])!=float(row['price_million']):
                    raise ValueError('Prior validation labels/category changed')
                old.append(float(prior['predicted_million']))
            old_score=c.scores(y,old)
            np.testing.assert_allclose(old_score['mae_million'],prior_metrics['categories'][category]['validation'][family]['mae_million'],rtol=1e-10)
            new_score=scores[family]
            comparison.append(dict(category=category,model=family,validation_n=len(val),
                v3_mae_million=old_score['mae_million'],v4_mae_million=new_score['mae_million'],
                mae_change_pct=100*(new_score['mae_million']/old_score['mae_million']-1),
                v3_mape_pct=old_score['mape_pct'],v4_mape_pct=new_score['mape_pct']))
        for i,row in enumerate(val):
            for family,values in predicted.items():
                value=float(values[i])
                predictions.setdefault('rows',[]).append(dict(record_key=row['record_key'],category=category,
                    source=row['source'],pipeline_group=row['pipeline_group'],location_feature=row['location_feature'],
                    model=family,actual_million=float(y[i]),predicted_million=value,
                    absolute_error_million=abs(value-y[i]),ape_pct=100*abs(value-y[i])/y[i],selected=family==selected))
            errors.append(dict(record_key=row['record_key'],category=category,source=row['source'],detail_url=row['detail_url'],
                actual_million=float(y[i]),predicted_million=float(predicted[selected][i]),
                absolute_error_million=abs(float(predicted[selected][i])-y[i]),selected_model=selected))
        print(json.dumps(dict(category=category,selected=selected,mae_million=scores[selected]['mae_million']),ensure_ascii=False),flush=True)
    c.write_json(stage/'baseline_models.json',models)
    # Baselines also round-trip from the saved artifact.
    loaded=json.loads((stage/'baseline_models.json').read_text(encoding='utf-8'))
    for category in c.CATEGORIES:
        val=[r for r in parts['validation'] if r['category']==category]
        expected=v3.get_baseline_predictions(val,loaded[category])
        for family,values in expected.items():
            observed=[r['predicted_million'] for r in predictions['rows'] if r['category']==category and r['model']==family]
            np.testing.assert_allclose(values,observed,rtol=1e-10,atol=1e-8)
    chosen=[r for r in predictions['rows'] if r['selected']]
    aggregate=c.scores([r['actual_million'] for r in chosen],[r['predicted_million'] for r in chosen])
    paired_selected=[]
    for category in c.CATEGORIES:
        old=prior_metrics['categories'][category]['selected_validation']['mae_million']
        new=categories[category]['selected_validation']['mae_million']
        paired_selected.append(dict(category=category,v3_model=prior_metrics['categories'][category]['selected_by_validation_mae'],
            v4_model=categories[category]['selected_by_validation_mae'],v3_mae_million=old,v4_mae_million=new,
            mae_change_pct=100*(new/old-1),v4_improves_development_mae=new<old))
    report=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),dataset_run=data.relative_to(c.BASE).as_posix(),
        protocol=PROTOCOL,versions=versions,train_n=len(parts['train']),validation_n=len(parts['validation']),
        categories=categories,aggregate_selected_validation=aggregate,
        v3_aggregate_selected_validation=prior_metrics['aggregate_selected_validation'],
        same_family_comparison=comparison,selected_family_comparison=paired_selected,
        model_reload_verified=True,test_evaluated=False,independent_benchmark=False,automatic_deployment=False,
        limitations=['Development validation reused for early stopping, model choice and v3/v4 comparison; optimistic selection is possible.',
            'Added older/undated listings change both source and time distributions; improvement cannot be attributed to age alone.',
            'Labels are asking prices, not independently verified transactions.',
            'No property-level coordinates, alley measurements or POI distances have been added.'])
    c.write_json(stage/'metrics.json',report)
    c.write_csv(stage/'validation_predictions.csv',predictions['rows'],list(predictions['rows'][0]))
    c.write_csv(stage/'v3_v4_same_family_comparison.csv',comparison,list(comparison[0]))
    c.write_csv(stage/'v3_v4_selected_comparison.csv',paired_selected,list(paired_selected[0]))
    errors.sort(key=lambda r:r['absolute_error_million'],reverse=True)
    c.write_csv(stage/'validation_errors.csv',errors,list(errors[0]))
    coverage=v3.feature_coverage(parts)
    c.write_csv(stage/'feature_coverage.csv',coverage,list(coverage[0]))
    short=dict(zip(v3.FAMILIES,['Trung vị địa bàn','Ridge','XGBoost']))
    lines=['# Mô hình v4 — mở rộng train, giữ nguyên validation','',
        f'Đã huấn luyện từ **{len(parts["train"]):,}** tin train và đánh giá trên đúng **299** tin validation v3. '
        'Train tăng 675 tin; không áp dụng ngưỡng tuổi 183 ngày hoặc bắt buộc ngày đăng. Giữ mọi điều kiện chất lượng khác, '
        'phân nhóm và các tập dành riêng. Không chấm test, không tự triển khai/thay model v3.','',
        '| Loại | Train | Val | V3 chọn | V4 chọn | V3 MAE | V4 MAE | Thay đổi MAE |',
        '|---|---:|---:|---|---|---:|---:|---:|']
    for row in paired_selected:
        info=categories[row['category']]
        lines.append(f'| {row["category"]} | {info["train_n"]} | {info["validation_n"]} | {short[row["v3_model"]]} | '
            f'{short[row["v4_model"]]} | {row["v3_mae_million"]:,.1f} | {row["v4_mae_million"]:,.1f} | {row["mae_change_pct"]:+.1f}% |')
    lines+=['','MAE tính bằng **triệu VND**; âm ở cột thay đổi là cải thiện. So sánh ở trên cho phép chọn họ mô hình '
        'riêng từng phiên bản/loại; xem bảng cùng họ để đánh giá riêng tác động của mở rộng train.','',
        '| Loại | XGBoost v3 MAE | XGBoost v4 MAE | Thay đổi |','|---|---:|---:|---:|']
    for row in comparison:
        if row['model']==v3.FAMILIES[2]:
            lines.append(f'| {row["category"]} | {row["v3_mae_million"]:,.1f} | {row["v4_mae_million"]:,.1f} | {row["mae_change_pct"]:+.1f}% |')
    lines+=['',f'MAE tổng hợp các mô hình được chọn: v3 **{report["v3_aggregate_selected_validation"]["mae_million"]:,.1f}**, '
        f'v4 **{aggregate["mae_million"]:,.1f}** triệu VND; MAPE v4 **{aggregate["mape_pct"]:.1f}%**.','',
        'Validation là tập phát triển đã dùng trước đây và đồng thời dùng để dừng sớm/chọn mô hình; '
        'đây chưa phải kiểm chứng độc lập. Không suy ra rằng dữ liệu cũ tự làm mô hình tốt/xấu: đợt bổ sung còn thay đổi nguồn dữ liệu. '
        'Cần tập kiểm chứng mới hoặc phép đánh giá theo thời gian trước khi kết luận khả năng dự đoán giá hiện tại.','',
        'CPU hist 4 luồng; cùng tham số cố định với v3, không tìm kiếm siêu tham số. Mỗi loại thử trung vị địa bàn, Ridge và XGBoost. '
        'Encoder/thống kê chỉ học từ train; không đưa giá/mô tả/tiêu đề/ID/đơn giá vào feature. '
        'Chưa bổ sung tọa độ căn nhà, độ rộng hẻm hoặc khoảng cách tiện ích. Giá mục tiêu vẫn là giá rao.','',
        '[Chỉ số đầy đủ](metrics.json), [so sánh cùng họ](v3_v4_same_family_comparison.csv), '
        '[dự đoán validation](validation_predictions.csv), [sai số theo tin](validation_errors.csv). '
        'Các model JSON và schema cùng loại phải dùng chung; đầu ra XGBoost là log giá, cần exp để về triệu VND. '
        'Đã tải lại model và so sánh dự đoán trước khi chốt.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target)
    publish(target)
    print(json.dumps(dict(run=str(target),aggregate_validation=aggregate,comparison=paired_selected),ensure_ascii=False,indent=2))


def publish(target):
    OUT.mkdir(parents=True,exist_ok=True)
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# So sánh mô hình v4 với v3\n\n'
        f'[Kết quả đã chốt]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':
    main()
