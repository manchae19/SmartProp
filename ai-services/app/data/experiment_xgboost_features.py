"""Compare a fixed feature/target ablation on validation only; never evaluate test."""
import hashlib
import json
from collections import Counter
import numpy as np
import xgboost as xgb
from analyze_xgboost_validation import DATA, MODEL, BASE, source_features
from audit_all_collected import read, save_csv
from prepare_smartprop_dataset import CATEGORIES
from train_smartprop_baseline import metrics

OUT=BASE/'processed/xgboost_feature_experiment'


def schema(train):
    locations=sorted({r['location_feature'] for r in train})
    wards=Counter(r['location_feature']+'|'+source_features(r)['ward_source']
                  for r in train if source_features(r)['ward_source'])
    return dict(locations=locations,wards=sorted(w for w,n in wards.items() if n>=3),min_ward_train_count=3,
                numeric=['area_sqm','rooms'],missing=['rooms_missing','ward_missing','ward_unseen_or_rare'],
                feature_names=['area_sqm','rooms','rooms_missing','ward_missing','ward_unseen_or_rare']+
                    ['location:'+v for v in locations]+['ward:'+v for v,n in sorted(wards.items()) if n>=3])


def encode(rows,spec):
    result=[]
    for row in rows:
        f=source_features(row)
        room=f['rooms'] if row['category']!='Đất nền' else None
        ward=row['location_feature']+'|'+f['ward_source'] if f['ward_source'] else ''
        result.append([float(row['area_sqm']),room if room is not None else np.nan,
            float(room is None),float(not ward),float(bool(ward) and ward not in spec['wards'])]+
            [float(row['location_feature']==v) for v in spec['locations']]+
            [float(ward==v) for v in spec['wards']])
    return np.asarray(result,dtype=np.float32)


def raw_mae_log(pred,matrix):
    return 'mae_million',float(np.abs(np.exp(np.clip(pred,-20,30))-np.exp(matrix.get_label())).mean())


def main():
    paths=[DATA/'train.csv',DATA/'validation.csv',DATA/'test.csv',MODEL/'metrics.json']
    frozen={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    old=json.loads((MODEL/'metrics.json').read_text(encoding='utf-8'))
    assert all(frozen[DATA/p]==h for p,h in old['source_sha256'].items())
    # No test rows or predictions are loaded; only the file hash is checked.
    train=read(DATA/'train.csv');val=read(DATA/'validation.csv')
    assert not {r['duplicate_candidate_group'] for r in train}&{r['duplicate_candidate_group'] for r in val}
    OUT.mkdir(parents=True,exist_ok=True)
    results={};predictions=[]
    for i,category in enumerate(CATEGORIES,1):
        tr=[r for r in train if r['category']==category];va=[r for r in val if r['category']==category]
        spec=schema(tr)
        actual=np.array([float(r['price_million']) for r in va])
        info=dict(train_count=len(tr),validation_count=len(va),
                  original_area_location_raw=old['categories'][category]['validation'],experiments={})
        for mode in ['area_location_log','enriched_raw','enriched_log']:
            if mode=='area_location_log':
                def matrix(rows):
                    return np.array([[float(r['area_sqm'])]+[float(r['location_feature']==v) for v in spec['locations']] for r in rows],dtype=np.float32)
                feature_spec=dict(locations=spec['locations'],feature_names=['area_sqm']+['location:'+v for v in spec['locations']])
            else:
                def matrix(rows):return encode(rows,spec)
                feature_spec=spec
            log=mode.endswith('_log')
            yt=np.array([float(r['price_million']) for r in tr])
            dt=xgb.DMatrix(matrix(tr),label=np.log(yt) if log else yt)
            dv=xgb.DMatrix(matrix(va),label=np.log(actual) if log else actual)
            params=dict(old['categories'][category]['params'])
            if log:
                params.pop('eval_metric',None);params['disable_default_eval_metric']=1
            print(category,mode,flush=True)
            kwargs=dict(custom_metric=raw_mae_log) if log else {}
            model=xgb.train(params,dt,num_boost_round=1500,evals=[(dv,'validation')],
                            early_stopping_rounds=50,verbose_eval=False,**kwargs)
            best=model[:model.best_iteration+1]
            pred=best.predict(dv)
            if log:pred=np.exp(np.clip(pred,-20,30))
            name=f'category_{i}_{mode}'
            best.save_model(OUT/(name+'.json'))
            (OUT/(name+'_features.json')).write_text(json.dumps(dict(feature_spec,target_transform='log' if log else 'identity'),ensure_ascii=False,indent=2),encoding='utf-8')
            info['experiments'][mode]=dict(validation=metrics(actual,pred),best_iteration=model.best_iteration,
                                           model_file=name+'.json')
            for r,p in zip(va,pred):predictions.append(dict(record_key=r['record_key'],category=category,mode=mode,
                actual_million=r['price_million'],predicted_million=float(p)))
        scores={'original_area_location_raw':info['original_area_location_raw']['mae_million']}
        scores.update({m:r['validation']['mae_million'] for m,r in info['experiments'].items()})
        selected=min(scores,key=scores.get)
        info.update(selected_by_validation_mae=selected,selected_validation_mae_million=scores[selected],
                    improvement_vs_original_pct=100*(scores['original_area_location_raw']-scores[selected])/scores['original_area_location_raw'])
        results[category]=info
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in frozen.items())
    report=dict(categories=results,input_sha256={p.relative_to(BASE).as_posix():h for p,h in frozen.items()},
        test_evaluated=False,labels_splits_unchanged=True,xgboost_version=xgb.__version__,
        protocol='Three fixed feature/target variants; same tree settings and frozen train/validation. Log variants early-stop on raw-price MAE.',
        limitations=['Validation was used for selection; improvement is not independent test evidence.',
            'Missing and source-specific fields may act as source proxies. Ward aliases are not reconciled.',
            'Legal status, coordinates, direction excluded because of sparse training coverage.',
            'No label corrections, row removal or new source fetches. Previously exposed test held aside.'])
    (OUT/'metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(OUT/'validation_predictions.csv',predictions,['record_key','category','mode','actual_million','predicted_million'])
    lines=['# Thử nghiệm đặc trưng XGBoost trên validation','',
        'Giữ nguyên train/validation/test và mọi nhãn v1. Không đọc bản ghi hoặc dự đoán test trong thử nghiệm này. '
        'Giữ nguyên tham số cây, thử ba biến thể cố định: diện tích/địa bàn + log giá; thêm phường/số phòng + giá gốc; thêm phường/số phòng + log giá. '
        'Log giá dừng sớm theo MAE quy đổi về triệu VND; số phòng đất luôn để thiếu. Không sử dụng giá/m² hay tiêu đề làm đặc trưng.', '',
        '| Loại | MAE validation gốc (triệu) | Biến thể chọn | MAE mới | Giảm |','|---|---:|---|---:|---:|']
    for c,r in results.items():lines.append(f'| {c} | {r["original_area_location_raw"]["mae_million"]:.1f} | {r["selected_by_validation_mae"]} | {r["selected_validation_mae_million"]:.1f} | {r["improvement_vs_original_pct"]:.1f}% |')
    lines+=['', 'Encoder chỉ học danh mục từ train; phường được ghép với địa bàn và cần ít nhất 3 hàng train. '
        'Phường thiếu/chưa thấy/hiếm có cờ riêng. Số phòng chỉ nhận số nguyên 1–30; thiếu giữ NaN, không tự gán 0 phòng. '
        'Đây là thông tin từ nguồn, chưa xác minh thực địa. Pháp lý/tọa độ/hướng chưa dùng do thiếu nhiều.', '',
        'Mức giảm trong bảng so với XGBoost v1, không phải so với mô hình cơ sở Ridge/trung vị. Nhóm nhà vẫn cần đối chiếu Ridge trước khi chọn mô hình cuối. '
        'Xem chỉ số validation của mô hình cơ sở trong `training_v1/baseline_metrics.json`.', '',
        'Cải thiện validation đã được dùng để chọn mô hình nên có thể lạc quan. Cần chốt cấu hình và quy tắc trước khi đánh giá test; '
        'không tiếp tục thử tham số theo điểm test. Không khẳng định mô hình mới tốt hơn trên thị trường.', '',
        'Các model JSON đi kèm `_features.json` xác định thứ tự cột và phép đổi nhãn. `metrics.json` giữ mọi biến thể, '
        '`validation_predictions.csv` giữ từng dự đoán. Model log giá phải lấy exp của đầu ra khi suy luận.', '',
        'Xem [phân tích lỗi và hàng chờ kiểm tra nguồn](../xgboost_validation_review/README.md).', '',
        'Chạy: `python ai-services/app/data/experiment_xgboost_features.py`.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({c:{k:r[k] for k in ['selected_by_validation_mae','selected_validation_mae_million','improvement_vs_original_pct']} for c,r in results.items()},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
