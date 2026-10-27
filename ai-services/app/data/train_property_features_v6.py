"""Five preregistered XGBoost feature ablations; fixed cohorts and parameters."""
import hashlib
import json
import platform
import uuid
from datetime import datetime,timezone
from pathlib import Path
import numpy as np
import xgboost as xgb
import training_v3_common as c
import train_training_v3 as experiment
import property_text_features_v6 as features
import build_property_features_v6 as data_job
import verify_property_features_v6 as data_verifier

OUT=c.PROCESSED/'models_v6_ablation'
ARMS=['control','rooms_floors','access','subtype','all']
PROTOCOL=dict(experiment.PROTOCOL,families=['xgboost_enriched_log'],arms=ARMS,
    selection='One global arm with lowest aggregate development validation MAE; all arms reported, no parameter search',
    cohort='Exactly 2214 train, 299 fixed development validation; 684 reserved IDs untouched',
    extraction_rules_frozen_before_fit=True,new_feature_source='Literal source title/body/structured claims with evidence',
    geospatial_features=False,automatic_deployment=False,
    caveat='Exploratory repeated development validation; not independent test or proof of causal feature effects')


def latest(root):return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def publish(target):
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# Thử nghiệm đặc trưng v6\n\n'
        f'[Kết quả hiện tại]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


def main():
    data_verifier.main()
    data=latest(data_job.OUT)
    parts={s:c.read(data/(s+'.csv')) for s in ['train','validation']}
    feature_rows={r['record_key']:r for r in c.read(data/'features.csv')}
    v5=latest(c.PROCESSED/'models_v5_validation')
    v3=latest(c.PROCESSED/'models_v3_validation')
    v5_report=json.loads((v5/'metrics.json').read_text(encoding='utf-8'))
    v3_report=json.loads((v3/'metrics.json').read_text(encoding='utf-8'))
    previous={(r['record_key'],r['model']):r for r in c.read(v5/'validation_predictions.csv')}
    paths=[Path(__file__),Path(features.__file__),Path(c.__file__),Path(experiment.__file__),Path(data_verifier.__file__),
           data/'manifest.json',data/'features.csv',data/'train.csv',data/'validation.csv',data/'reserved_holdout_registry.csv',
           data_job.OUT/'verification.json',v5/'manifest.json',v5/'metrics.json',v5/'validation_predictions.csv',v3/'manifest.json',v3/'metrics.json']
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    protected={}
    for directory in [data,v3,v5,latest(c.PROCESSED/'models_v4_validation')]:
        m=json.loads((directory/'manifest.json').read_text(encoding='utf-8'));c.verify(m['output_sha256'],directory)
        protected.update({(directory/p).relative_to(c.BASE).as_posix():sha for p,sha in m['output_sha256'].items()})
        protected[(directory/'manifest.json').relative_to(c.BASE).as_posix()]=c.sha(directory/'manifest.json')
    versions=dict(python=platform.python_version(),numpy=np.__version__,xgboost=xgb.__version__)
    digest=hashlib.sha256(json.dumps(dict(inputs=inputs,protocol=PROTOCOL,versions=versions),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/digest
    if target.exists():
        m=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['input_sha256']);c.verify(m['protected_sha256']);c.verify(m['output_sha256'],target)
        publish(target);print('Existing ablation verified: '+str(target));return
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    # Persist protocol before the first fit. Extraction rules and cohort already
    # exist as verified immutable input artifacts; do not alter them after scores.
    c.write_json(stage/'protocol.json',PROTOCOL)
    arms,predictions,comparison={},{},[]
    for arm in ARMS:
        categories={};rows=[]
        for index,category in enumerate(c.CATEGORIES,1):
            train=[r for r in parts['train'] if r['category']==category]
            val=[r for r in parts['validation'] if r['category']==category]
            y=np.asarray([float(r['price_million']) for r in val])
            spec=features.feature_spec(train,category,arm)
            X=features.encode(train,feature_rows,spec);V=features.encode(val,feature_rows,spec)
            if np.isinf(X).any() or np.isinf(V).any():raise ValueError('Infinite feature')
            dt=xgb.DMatrix(X,label=np.log([float(r['price_million']) for r in train]),feature_names=spec['feature_names'])
            dv=xgb.DMatrix(V,label=np.log(y),feature_names=spec['feature_names'])
            print(f'v6 {arm}: {category}, train={len(train)}, val={len(val)}, features={len(spec["feature_names"])}',flush=True)
            trained=xgb.train(experiment.PARAMS,dt,num_boost_round=PROTOCOL['max_rounds'],evals=[(dv,'validation')],
                custom_metric=experiment.log_mae,early_stopping_rounds=PROTOCOL['early_stopping_rounds'],verbose_eval=False)
            best=trained[:trained.best_iteration+1]
            prediction=np.exp(np.clip(best.predict(dv),-20,30))
            scores=c.scores(y,prediction)
            if arm=='control':
                old=[float(previous[(r['record_key'],experiment.FAMILIES[2])]['predicted_million']) for r in val]
                np.testing.assert_allclose(prediction,old,rtol=1e-7,atol=1e-5)
            folder=stage/'models'/arm;folder.mkdir(parents=True,exist_ok=True)
            filename=folder/f'category_{index}_xgboost.json'
            schema_file=folder/f'category_{index}_schema.json'
            best.save_model(filename);c.write_json(schema_file,spec)
            restored=xgb.Booster();restored.load_model(filename)
            np.testing.assert_allclose(restored.predict(dv),best.predict(dv),rtol=1e-7,atol=1e-7)
            categories[category]=dict(train_n=len(train),validation_n=len(val),validation=scores,
                best_iteration=trained.best_iteration,num_trees=best.num_boosted_rounds(),feature_n=len(spec['feature_names']),
                model_file=filename.relative_to(stage).as_posix(),schema_file=schema_file.relative_to(stage).as_posix())
            baseline=v5_report['categories'][category]['validation'][experiment.FAMILIES[2]]['mae_million']
            comparison.append(dict(arm=arm,category=category,validation_n=len(val),v5_control_mae_million=baseline,
                arm_mae_million=scores['mae_million'],mae_change_pct=100*(scores['mae_million']/baseline-1)))
            for i,row in enumerate(val):
                p=float(prediction[i]);actual=float(y[i])
                rows.append(dict(record_key=row['record_key'],arm=arm,category=category,source=row['source'],
                    pipeline_group=row['pipeline_group'],actual_million=actual,predicted_million=p,
                    absolute_error_million=abs(actual-p),ape_pct=100*abs(actual-p)/actual))
        aggregate=c.scores([r['actual_million'] for r in rows],[r['predicted_million'] for r in rows])
        arms[arm]=dict(categories=categories,aggregate_validation=aggregate)
        predictions[arm]=rows
    selected=min(ARMS,key=lambda a:arms[a]['aggregate_validation']['mae_million'])
    report=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),feature_run=data.relative_to(c.BASE).as_posix(),
        protocol=PROTOCOL,versions=versions,train_n=2214,validation_n=299,reserved_eligible_n=684,arms=arms,
        best_global_arm=selected,v5_control=arms['control']['aggregate_validation'],
        v3_selected_baseline=v3_report['aggregate_selected_validation'],
        control_predictions_match_v5=True,models_reloaded=True,test_evaluated=False,automatic_deployment=False,
        independent_benchmark=False,numeric_labels_changed=False)
    c.write_json(stage/'metrics.json',report)
    c.write_json(stage/'selection.json',dict(best_global_arm=selected,development_only=True,
        category_artifacts={category:{k:info[k] for k in ['model_file','schema_file']} for category,info in arms[selected]['categories'].items()},
        features_run=data.relative_to(c.BASE).as_posix(),automatic_deployment=False))
    flat=[r for arm in ARMS for r in predictions[arm]]
    c.write_csv(stage/'validation_predictions.csv',flat,list(flat[0]))
    c.write_csv(stage/'category_comparison.csv',comparison,list(comparison[0]))
    scores=[dict(arm=arm,**arms[arm]['aggregate_validation'],mae_change_vs_control_pct=100*(arms[arm]['aggregate_validation']['mae_million']/arms['control']['aggregate_validation']['mae_million']-1)) for arm in ARMS]
    c.write_csv(stage/'arm_comparison.csv',scores,list(scores[0]))
    selected_errors=sorted(predictions[selected],key=lambda r:r['absolute_error_million'],reverse=True)
    c.write_csv(stage/'selected_validation_errors.csv',selected_errors,list(selected_errors[0]))
    lines=['# Thử nghiệm đặc trưng nội dung v6','',
        'Giữ nguyên **2.214 train**, **299 validation** và **684 tin dự phòng**. '
        'Cùng XGBoost/CPU 4 luồng/seed/tham số với v5, thử đúng 5 cấu hình định trước; không đổi luật trích sau khi xem điểm.','',
        '| Cấu hình | MAE (triệu VND) | MAPE | Trong sai số 20% | MAE so v5 |','|---|---:|---:|---:|---:|']
    for row in scores:lines.append(f'| {row["arm"]} | {row["mae_million"]:,.2f} | {row["mape_pct"]:.2f}% | {row["within_20pct"]:.2f}% | {row["mae_change_vs_control_pct"]:+.2f}% |')
    lines+=['',f'Cấu hình có MAE thấp nhất trên validation phát triển: **{selected}**. '
        f'Bộ chọn v3 làm mốc có MAE **{report["v3_selected_baseline"]["mae_million"]:,.2f} triệu VND**. '
        'V3 là bộ Ridge/trung vị/XGBoost theo loại, không phải XGBoost thuần.','',
        '| Loại | V5 control MAE | Cấu hình chọn MAE | Thay đổi |','|---|---:|---:|---:|']
    for row in comparison:
        if row['arm']==selected:lines.append(f'| {row["category"]} | {row["v5_control_mae_million"]:,.2f} | {row["arm_mae_million"]:,.2f} | {row["mae_change_pct"]:+.2f}% |')
    lines+=['','Control được huấn luyện lại và khớp từng dự đoán XGBoost v5; 15 model đã tải lại để kiểm tra. '
        'So sánh các cấu hình là thử nghiệm thêm/bỏ nhóm đặc trưng, không chứng minh quan hệ nhân quả; '
        'dừng sớm và chọn cấu hình vẫn dùng cùng validation đã xem nhiều lần, có thể lạc quan. Không chấm test/triển khai.','',
        '## Feature và bằng chứng','',
        '- rooms_floors: bổ sung phòng ngủ từ câu rõ ràng, giữ phòng có cấu trúc khi xung đột; tầng chỉ áp dụng nhà hiện hữu.',
        '- access: mặt tiền/kiệt của tài sản; không nhận “gần mặt tiền”, tên đường Võ Văn Kiệt hoặc bề ngang thửa đất.',
        '- subtype: lời rao biệt thự/nhà cấp 4, không coi khu biệt thự hoặc dự định xây biệt thự là subtype của căn đang bán.',
        '- all: kết hợp ba nhóm. Nhóm không áp dụng (tầng nhà cho căn hộ/đất, subtype cho đất/căn hộ) không thêm cột.',
        '- Giá/diện tích/nhóm/split giữ nguyên. Không đưa giá/đơn giá/tiêu đề/mô tả/ID/nguồn vào X; chỉ giá trị trích theo whitelist. '
        'Numeric unknown là NaN với missing flag, category unknown có missing flag. Vocabulary địa bàn/phường chỉ fit từ train.',
        '- Chưa có độ rộng hẻm, tọa độ tài sản hay khoảng cách tiện ích; lời rao không phải đo đạc thực địa.',
        '',f'Đầu vào và câu bằng chứng: `{data.relative_to(c.BASE).as_posix()}`. '
        '[Chỉ số](metrics.json), [5 cấu hình](arm_comparison.csv), [theo loại](category_comparison.csv), '
        '[dự đoán](validation_predictions.csv), [model/schema được chọn cho phát triển](selection.json). '
        'Dùng đúng extractor + feature schema khi suy luận; model trả log giá, exp về triệu VND.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target);publish(target)
    print(json.dumps(dict(run=str(target),selected=selected,comparison=scores),ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':main()
