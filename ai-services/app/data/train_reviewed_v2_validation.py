"""Refit the previously chosen feature variants on reviewed v2; validation only."""
import hashlib
import json
import numpy as np
import xgboost as xgb
from audit_all_collected import BASE,read,save_csv
from prepare_smartprop_dataset import CATEGORIES
from experiment_xgboost_features import schema,encode,raw_mae_log
from train_smartprop_baseline import fit,predict,metrics

DATA=BASE/'processed/training_v2'
OUT=BASE/'processed/xgboost_v2_validation'


def main():
    old=BASE/'processed/xgboost_v1'
    previous=BASE/'processed/xgboost_feature_experiment'
    baseline=BASE/'processed/training_v1/baseline_metrics.json'
    inputs=[DATA/'train.csv',DATA/'validation.csv',DATA/'test.csv',old/'metrics.json',
            old/'holdout_predictions.csv',previous/'metrics.json',previous/'validation_predictions.csv',baseline]
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in inputs}
    frozen=json.loads((DATA/'summary.json').read_text(encoding='utf-8'))
    for p,h in frozen['output_sha256'].items():assert hashlib.sha256((BASE/p).read_bytes()).hexdigest()==h
    train=read(DATA/'train.csv');val=read(DATA/'validation.csv')
    assert not {r['duplicate_candidate_group'] for r in train}&{r['duplicate_candidate_group'] for r in val}
    assert (DATA/'test.csv').read_bytes()==(BASE/'processed/training_v1/test.csv').read_bytes()
    previous_report=json.loads((previous/'metrics.json').read_text(encoding='utf-8'))
    old_report=json.loads((old/'metrics.json').read_text(encoding='utf-8'))
    baseline_report=json.loads(baseline.read_text(encoding='utf-8'))
    old_predictions={r['record_key']:r for r in read(old/'holdout_predictions.csv') if r['split']=='validation'}
    previous_predictions={(r['record_key'],r['mode']):r for r in read(previous/'validation_predictions.csv')}
    OUT.mkdir(parents=True,exist_ok=True)
    results={};predictions=[];basemodels={}
    for i,c in enumerate(CATEGORIES,1):
        tr=[r for r in train if r['category']==c];va=[r for r in val if r['category']==c]
        actual=np.array([float(r['price_million']) for r in va])
        mode=previous_report['categories'][c]['selected_by_validation_mae']
        assert mode in ['enriched_raw','enriched_log','area_location_log']
        spec=schema(tr)
        def matrix(rows):
            if mode=='area_location_log':
                return np.array([[float(r['area_sqm'])]+[float(r['location_feature']==v) for v in spec['locations']] for r in rows],dtype=np.float32)
            return encode(rows,spec)
        log=mode.endswith('_log')
        ytrain=np.array([float(r['price_million']) for r in tr])
        dt=xgb.DMatrix(matrix(tr),label=np.log(ytrain) if log else ytrain)
        dv=xgb.DMatrix(matrix(va),label=np.log(actual) if log else actual)
        params=dict(old_report['categories'][c]['params'])
        if log:params.pop('eval_metric',None);params['disable_default_eval_metric']=1
        model=xgb.train(params,dt,num_boost_round=1500,evals=[(dv,'validation')],
            early_stopping_rounds=50,verbose_eval=False,**(dict(custom_metric=raw_mae_log) if log else {}))
        best=model[:model.best_iteration+1];pred=best.predict(dv)
        if log:pred=np.exp(np.clip(pred,-20,30))
        best.save_model(OUT/f'category_{i}.json')
        spec=dict(spec)
        if mode=='area_location_log':
            spec=dict(locations=spec['locations'],feature_names=['area_sqm']+['location:'+v for v in spec['locations']])
        (OUT/f'category_{i}_features.json').write_text(json.dumps(dict(spec,target_transform='log' if log else 'identity'),ensure_ascii=False,indent=2),encoding='utf-8')
        # Fit the original baseline family on v2 train; encoders/statistics stay train-only.
        btrain=[dict(r,district=r['location_feature']) for r in tr]
        bval=[dict(r,district=r['location_feature']) for r in va]
        bp=fit(btrain);basemodels[c]=bp
        bname=baseline_report['categories'][c]['selected_by_validation_mae']
        bpred=predict(bval,bp)[bname]
        oldpred=[float(old_predictions[r['record_key']]['predicted_million']) for r in va]
        prevpred=[float(previous_predictions[(r['record_key'],mode)]['predicted_million']) for r in va]
        info=dict(train_n=len(tr),validation_n=len(va),fixed_feature_variant=mode,best_iteration=model.best_iteration,
            v1_xgboost_on_common_v2_labels=metrics(actual,oldpred),
            v1_selected_variant_on_common_v2_labels=metrics(actual,prevpred),
            v2_xgboost=metrics(actual,pred),v2_baseline=metrics(actual,bpred),baseline_family=bname)
        info['preferred_on_validation']='xgboost' if info['v2_xgboost']['mae_million']<info['v2_baseline']['mae_million'] else bname
        results[c]=info
        for r,a,b in zip(va,pred,bpred):
            predictions.append(dict(record_key=r['record_key'],category=c,actual_million=r['price_million'],
                                    xgboost_predicted_million=float(a),baseline_predicted_million=float(b)))
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    report=dict(categories=results,source_sha256={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},
        test_evaluated=False,previous_test_unchanged=True,
        protocol='Fixed v1-selected feature/target settings; refit on v2 train, early stopping on v2 validation. Compare previous predictions only on the same remaining IDs and v2 labels.',
        limitations=['Validation is used for early stopping and model choice, not independent accuracy evidence.',
            'Validation is a smaller reviewed subset; no direct comparison with old full-set metrics.',
            'Old predictions vs refit measure both data review and training changes; no causal attribution.',
            'Test labels remain automatically screened and may retain analogous issues; no new test inspection or scoring.'])
    (OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'baseline_models.json').write_text(json.dumps(basemodels,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(OUT/'validation_predictions.csv',predictions,list(predictions[0]))
    lines=['# Huấn luyện lại sau đối chiếu nguồn v2','',
        'Dùng biến thể XGBoost đã chọn trên validation v1; giữ nguyên tham số cây. Huấn luyện trên train v2 và dừng sớm bằng validation v2. '
        'Huấn luyện lại cùng họ mô hình cơ sở đã chọn ở v1. Không đọc bản ghi test hay chấm lại test.', '',
        '| Loại | Val n | XGBoost v1 trên nhãn v2 | XGBoost v2 | Cơ sở v2 | Đơn vị |','|---|---:|---:|---:|---:|---|']
    for c,z in results.items():lines.append(f'| {c} | {z["validation_n"]} | {z["v1_xgboost_on_common_v2_labels"]["mae_million"]:.1f} | {z["v2_xgboost"]["mae_million"]:.1f} | {z["v2_baseline"]["mae_million"]:.1f} | triệu VND |')
    lines+=['', 'Các cột đều dùng cùng ID validation còn lại và cùng nhãn v2. Cột v1 là dự đoán đã lưu, không huấn luyện lại. '
        'So sánh này không phải kết quả test, không chứng minh tổng quát hóa. Không so trực tiếp với MAE trên toàn bộ 126 tin validation cũ.', '',
        '`metrics.json` có MAE, MAPE, R², cả biến thể được chọn trước đó, mô hình cơ sở và hash đầu vào. '
        'Các model JSON có schema đi kèm; dùng exp cho model log giá. Nhóm nhà vẫn cần xem mô hình cơ sở trước khi chọn XGBoost.', '',
        'Test v1 giữ nguyên 137 tin và vẫn có chất lượng sàng lọc tự động, có thể còn lỗi tương tự. Chưa gọi đây là benchmark sạch cuối cùng.', '',
        'Xem [quyết định nguồn và bộ v2](../training_v2/README.md).', '',
        'Chạy: `python ai-services/app/data/train_reviewed_v2_validation.py`.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({c:dict(validation_n=z['validation_n'],old_mae=z['v1_xgboost_on_common_v2_labels']['mae_million'],
        new_mae=z['v2_xgboost']['mae_million'],baseline_mae=z['v2_baseline']['mae_million']) for c,z in results.items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
