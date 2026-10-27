"""Freeze validation-selected models, validate inference, then score the unchanged test."""
import hashlib
import json
import platform
from pathlib import Path
import numpy as np
import xgboost as xgb
from audit_all_collected import BASE,read,save_csv
from prepare_smartprop_dataset import CATEGORIES
from train_smartprop_baseline import metrics
from predict_model_v2 import predict

DATA=BASE/'processed/training_v2'
MODELS=BASE/'processed/xgboost_v2_validation'
OUT=BASE/'processed/model_evaluation_v2'
FAMILIES={'Nhà ở':'log_area_district_ridge_alpha_1','Đất nền':'district_median_unit_price','Căn hộ chung cư':'xgboost'}


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def inference_rows(rows):
    result=[]
    for r in rows:
        raw=json.loads(r['raw_json'])
        result.append(dict(area_sqm=r['area_sqm'],location_feature=r['location_feature'],ward=raw.get('ward',''),rooms=raw.get('rooms','')))
    return result


def main():
    paths=[DATA/(s+'.csv') for s in ['train','validation','test']]+[DATA/'summary.json',MODELS/'metrics.json',
        MODELS/'validation_predictions.csv',MODELS/'baseline_models.json',MODELS/'category_3.json',
        MODELS/'category_3_features.json',BASE/'processed/xgboost_v1/holdout_predictions.csv',
        BASE/'processed/training_v1/baseline_test_predictions.csv',Path(__file__).resolve(),BASE/'predict_model_v2.py']
    hashes={p:sha(p) for p in paths}
    if (OUT/'manifest.json').exists():
        frozen=json.loads((OUT/'manifest.json').read_text(encoding='utf-8'))
        assert frozen['input_sha256']=={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},'Frozen evaluation inputs changed; use a new version'
        for rel,digest in frozen['output_sha256'].items():assert sha(OUT/rel)==digest
        print('Frozen evaluation already exists; hashes verified, no scoring or mutation.');return
    report=json.loads((MODELS/'metrics.json').read_text(encoding='utf-8'))
    for p,h in report['source_sha256'].items():assert sha(BASE/p)==h
    summary=json.loads((DATA/'summary.json').read_text(encoding='utf-8'))
    for p,h in summary['output_sha256'].items():assert sha(BASE/p)==h
    assert (DATA/'test.csv').read_bytes()==(BASE/'processed/training_v1/test.csv').read_bytes()
    bundle=OUT/'model_bundle';bundle.mkdir(parents=True,exist_ok=True)
    params=json.loads((MODELS/'baseline_models.json').read_text(encoding='utf-8'))
    selection=dict(dataset='training_v2',selection_basis='Minimum MAE on validation v2 between the documented baseline family and fixed XGBoost variant; no test-driven selection.',categories={})
    for i,c in enumerate(CATEGORIES,1):
        info=report['categories'][c]
        assert info['preferred_on_validation']==FAMILIES[c]
        if FAMILIES[c]=='xgboost':
            name='category_3.json';schema='category_3_features.json'
            (bundle/name).write_bytes((MODELS/name).read_bytes())
            (bundle/schema).write_bytes((MODELS/schema).read_bytes())
            selection['categories'][c]=dict(family='xgboost',model_file=name,schema_file=schema,
                validation_mae_million=info['v2_xgboost']['mae_million'])
        else:
            name=f'category_{i}_baseline.json'
            (bundle/name).write_text(json.dumps(params[c],ensure_ascii=False,indent=2),encoding='utf-8')
            selection['categories'][c]=dict(family=FAMILIES[c],model_file=name,
                feature_order=['area_sqm','location_feature'],validation_mae_million=info['v2_baseline']['mae_million'])
    # Record model choice and artifacts before opening any test records.
    selection['artifact_sha256']={p.name:sha(p) for p in bundle.glob('*.json')}
    (bundle/'selection.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2),encoding='utf-8')
    (bundle/'predict.py').write_bytes((BASE/'predict_model_v2.py').read_bytes())
    (bundle/'requirements.txt').write_text(f'numpy=={np.__version__}\nxgboost=={xgb.__version__}\n',encoding='utf-8')
    val=read(DATA/'validation.csv')
    expected={r['record_key']:r for r in read(MODELS/'validation_predictions.csv')}
    for c in CATEGORIES:
        rows=[r for r in val if r['category']==c]
        pred=predict(bundle,c,inference_rows(rows))
        column='xgboost_predicted_million' if FAMILIES[c]=='xgboost' else 'baseline_predicted_million'
        assert np.allclose(pred,[float(expected[r['record_key']][column]) for r in rows],rtol=1e-6,atol=1e-4), 'Exported inference differs from validation run'
    test=read(DATA/'test.csv');assert len(test)==137
    train=read(DATA/'train.csv')
    groups=[{r['duplicate_candidate_group'] for r in p} for p in [train,val,test]]
    assert not groups[0]&groups[1] and not groups[0]&groups[2] and not groups[1]&groups[2]
    v1x={r['record_key']:r for r in read(BASE/'processed/xgboost_v1/holdout_predictions.csv') if r['split']=='test'}
    v1b={r['record_key']:r for r in read(BASE/'processed/training_v1/baseline_test_predictions.csv')}
    assert set(v1x)==set(v1b)=={r['record_key'] for r in test}
    results={};predictions=[];table=[]
    for c in CATEGORIES:
        rows=[r for r in test if r['category']==c]
        actual=[float(r['price_million']) for r in rows]
        assert all(float(v1x[r['record_key']]['actual_million'])==float(r['price_million'])==float(v1b[r['record_key']]['actual_million']) for r in rows)
        values={'v1_baseline':[float(v1b[r['record_key']]['predicted_million']) for r in rows],
                'v1_xgboost':[float(v1x[r['record_key']]['predicted_million']) for r in rows],
                'v2_selected':predict(bundle,c,inference_rows(rows))}
        info=dict(selected_family=FAMILIES[c],test_n=len(rows),scores={m:metrics(actual,p) for m,p in values.items()})
        results[c]=info
        for model,s in info['scores'].items():table.append(dict(category=c,version=model,selected_family=FAMILIES[c] if model=='v2_selected' else '',**s))
        for j,r in enumerate(rows):predictions.append(dict(record_key=r['record_key'],category=c,source=r['source'],
            actual_million=r['price_million'],v1_baseline_million=values['v1_baseline'][j],v1_xgboost_million=values['v1_xgboost'][j],
            v2_selected_million=float(values['v2_selected'][j]),selected_family=FAMILIES[c],duplicate_candidate_group=r['duplicate_candidate_group']))
    assert all(sha(p)==h for p,h in hashes.items())
    result=dict(categories=results,total_test_n=len(test),model_choice=selection['selection_basis'],
        data_version='training_v2',test_hash=hashes[DATA/'test.csv'],
        python_version=platform.python_version(),numpy_version=np.__version__,xgboost_version=xgb.__version__,
        limitations=['The same test was previously exposed during v1 reporting; this is exploratory, not a fresh independent final benchmark.',
          'Test labels remain automatically screened, not fully source-reviewed; asking prices are not transaction prices.',
          'Small per-category holdouts and heuristic property grouping limit generalization claims.',
          'v2 selected families differ from v1 XGBoost; changes are not attributable to data cleaning alone.',
          'No retraining on validation/test; no test-driven changes to thresholds, rows or chosen models.'])
    (OUT/'metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(OUT/'test_comparison.csv',table,list(table[0]))
    save_csv(OUT/'test_predictions.csv',predictions,list(predictions[0]))
    lines=['# Đánh giá mô hình đã chốt trên test v2','',
        '**Đánh giá thử nghiệm trên test đã từng được xem ở v1, chưa phải kiểm chứng độc lập cuối cùng.** '
        '137 ID, nhãn và nhóm test giữ nguyên từng byte. Lựa chọn mô hình được ghi trước khi chấm test: Ridge cho nhà, trung vị đơn giá theo địa bàn cho đất, XGBoost bổ sung phường/số phòng và log giá cho căn hộ. '
        'Mô hình đã huấn luyện chỉ trên train v2, chọn/dừng sớm bằng validation v2; không huấn luyện lại khi chấm test.', '',
        '| Loại | Số test | MAE cơ sở v1 | MAE XGBoost v1 | MAE mô hình chốt v2 | MAPE v2 | R² v2 |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for c,z in results.items():
        s=z['scores'];v=s['v2_selected']
        lines.append(f'| {c} | {z["test_n"]} | {s["v1_baseline"]["mae_million"]:.1f} | {s["v1_xgboost"]["mae_million"]:.1f} | {v["mae_million"]:.1f} | {v["mape_pct"]:.1f}% | {v["r2"]:.3f} |')
    lines+=['','MAE tính bằng triệu VND, càng thấp càng tốt. Các cột dùng cùng ID và nhãn test. '
        'MAPE nhạy với tin giá thấp; R² không phải tỷ lệ dự đoán đúng. Không chọn lại mô hình theo bảng test này.', '',
        '## Tệp dùng cho đồ án', '',
        '- `test_comparison.csv`: bảng chỉ số cho v1 cơ sở, v1 XGBoost và v2 đã chọn.',
        '- `test_predictions.csv`: đối chiếu từng ID để tái lập chỉ số, không phải hàng chờ sửa nhãn theo dự đoán.',
        '- `metrics.json`: kết quả, phiên bản môi trường và giới hạn.',
        '- `model_bundle/selection.json`: mô hình được chọn, schema, hash; baseline JSON và XGBoost JSON tương ứng.',
        '- `model_bundle/predict.py`, `requirements.txt`: suy luận độc lập với các script dữ liệu dự án.',
        '- `manifest.json`: hash đầu vào/đầu ra để kiểm tra tái lập. Các CSV dữ liệu ở [training_v2](../training_v2/README.md).', '',
        '## Chạy dự đoán', '', 'Từ `F:\\SmartProp`:', '', '```powershell',
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/predict_model_v2.py --category "Căn hộ chung cư" --area-sqm 65 --location "Sơn Trà" --ward "Phường An Hải Bắc" --rooms 2',
        '```','',
        'Đầu ra là giá rao dự đoán (triệu VND và VND). `location` phải khớp nhãn địa bàn đã lưu; địa bàn chưa thấy dùng mức chung/không có chỉ báo địa bàn. '
        'Phường và số phòng có thể bỏ trống nếu không có dữ liệu. Không nhập giá rao hoặc đơn giá vào đặc trưng.', '',
        'Để dùng bản độc lập trong thư mục model_bundle, chạy `predict.py --bundle .` cùng các tham số trên. '
        'Những mô hình này chưa phù hợp để coi là định giá giao dịch đã xác minh.', '',
        'Chạy lại `python ai-services/app/data/evaluate_selected_v2.py`: kiểm tra hash của kết quả đã chốt, không chấm lại hoặc đổi lựa chọn.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    frozen=dict(input_sha256={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},
        output_sha256={p.relative_to(OUT).as_posix():sha(p) for p in OUT.rglob('*') if p.is_file() and p.name!='manifest.json'},
        selected_before_test=True,inference_matches_validation=True,source_inputs_unchanged=True)
    (OUT/'manifest.json').write_text(json.dumps(frozen,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(results,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
