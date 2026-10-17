"""Fixed v5 experiment on reviewed data; preserve v3/v4 and every held-out ID."""
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
import train_smartprop_baseline as baseline
import prepare_smartprop_dataset as preparation
import filter_remaining_diversity as data_job
import verify_remaining_diversity as data_verifier

OUT=c.PROCESSED/'models_v5_validation'
PROTOCOL=dict(experiment.PROTOCOL,
    dataset_policy='Latest verified remaining_diversity_review; date optional, all numeric/content/group gates retained',
    validation='Exact same 299 development validation rows as v3/v4; not an independent test',
    previous_models_unchanged=True,geospatial_features=False,automatic_deployment=False)


def latest(root):
    return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def publish(target):
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# Mô hình v5\n\n'
        f'[Kết quả hiện tại]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


def main():
    data_verifier.main()
    data=latest(data_job.ROOT)
    folder=data/'training_inputs'
    parts={s:c.read(folder/(s+'.csv')) for s in ['train','validation']}
    if len(parts['train'])!=2214 or len(parts['validation'])!=299:
        raise ValueError('This fixed experiment requires verified 2214/299 data')
    references={}
    paths=[Path(__file__),Path(c.__file__),Path(experiment.__file__),Path(baseline.__file__),Path(preparation.__file__),
        Path(data_job.__file__),Path(data_verifier.__file__),data/'manifest.json',data/'summary.json',
        data_job.ROOT/'verification.json']+list(folder.iterdir())
    protected={}
    for version in ['v3','v4']:
        run=latest(c.PROCESSED/f'models_{version}_validation')
        m=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['output_sha256'],run)
        protected.update({(run/p).relative_to(c.BASE).as_posix():sha for p,sha in m['output_sha256'].items()})
        protected[(run/'manifest.json').relative_to(c.BASE).as_posix()]=c.sha(run/'manifest.json')
        metrics=json.loads((run/'metrics.json').read_text(encoding='utf-8'))
        previous_data=c.BASE/metrics['dataset_run']
        val_file=previous_data/('validation.csv' if version=='v3' else 'training_inputs/validation.csv')
        previous_val={r['record_key']:r for r in c.read(val_file)}
        if previous_val!={r['record_key']:r for r in parts['validation']}:
            raise ValueError('Reference validation changed: '+version)
        predictions=c.read(run/'validation_predictions.csv')
        lookup={(r['record_key'],r['model']):r for r in predictions}
        if len(predictions)!=897 or len(lookup)!=897:
            raise ValueError('Reference predictions not unique/complete')
        references[version]=dict(run=run,metrics=metrics,predictions=lookup)
        paths+=[run/'manifest.json',run/'metrics.json',run/'validation_predictions.csv',val_file]
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths if p.is_file()}
    versions=dict(python=platform.python_version(),numpy=np.__version__,xgboost=xgb.__version__)
    digest=hashlib.sha256(json.dumps(dict(inputs=inputs,protocol=PROTOCOL,versions=versions),sort_keys=True).encode()).hexdigest()
    target=OUT/'runs'/digest[:16]
    if target.exists():
        saved=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        c.verify(saved['input_sha256']);c.verify(saved['protected_sha256']);c.verify(saved['output_sha256'],target)
        publish(target);print('Existing v5 run verified: '+str(target));return
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    c.write_json(stage/'protocol.json',PROTOCOL)
    categories,models,predictions,comparison,selected_comparison={},{},[],[],[]
    for index,category in enumerate(c.CATEGORIES,1):
        train=[r for r in parts['train'] if r['category']==category]
        val=[r for r in parts['validation'] if r['category']==category]
        y=np.asarray([float(r['price_million']) for r in val])
        models[category]=baseline.fit(experiment.baseline_rows(train))
        predicted=experiment.get_baseline_predictions(val,models[category])
        spec=json.loads((folder/f'category_{index}_schema.json').read_text(encoding='utf-8'))
        if spec!=dict(c.schema(train),category=category):
            raise ValueError('Feature schema not fitted on current train')
        dt=xgb.DMatrix(folder/f'category_{index}_train.buffer')
        dv=xgb.DMatrix(folder/f'category_{index}_validation.buffer')
        print(f'Training v5 {category}: train={len(train)}, validation={len(val)}, CPU 4 threads',flush=True)
        trained=xgb.train(experiment.PARAMS,dt,num_boost_round=PROTOCOL['max_rounds'],evals=[(dv,'validation')],
            custom_metric=experiment.log_mae,early_stopping_rounds=PROTOCOL['early_stopping_rounds'],verbose_eval=False)
        best=trained[:trained.best_iteration+1]
        predicted[experiment.FAMILIES[2]]=np.exp(np.clip(best.predict(dv),-20,30))
        filename=f'category_{index}_xgboost.json'
        best.save_model(stage/filename)
        c.write_json(stage/f'category_{index}_schema.json',spec)
        restored=xgb.Booster();restored.load_model(stage/filename)
        np.testing.assert_allclose(restored.predict(dv),best.predict(dv),rtol=1e-7,atol=1e-7)
        scores={f:c.scores(y,values) for f,values in predicted.items()}
        selected=min(experiment.FAMILIES,key=lambda f:scores[f]['mae_million'])
        categories[category]=dict(train_n=len(train),validation_n=len(val),validation=scores,
            selected_by_validation_mae=selected,selected_validation=scores[selected],
            xgboost_best_iteration=trained.best_iteration,xgboost_num_trees=best.num_boosted_rounds(),
            model_file=filename,schema_file=f'category_{index}_schema.json')
        for version,ref in references.items():
            for family in experiment.FAMILIES:
                old=[]
                for row in val:
                    p=ref['predictions'][(row['record_key'],family)]
                    if p['category']!=category or float(p['actual_million'])!=float(row['price_million']):
                        raise ValueError('Reference category/label mismatch')
                    old.append(float(p['predicted_million']))
                old_score=c.scores(y,old)
                for key,value in old_score.items():
                    expected=ref['metrics']['categories'][category]['validation'][family][key]
                    if value is not None:
                        np.testing.assert_allclose(value,expected,rtol=1e-10,atol=1e-8)
                comparison.append(dict(reference_version=version,category=category,model=family,validation_n=len(val),
                    reference_mae_million=old_score['mae_million'],v5_mae_million=scores[family]['mae_million'],
                    mae_change_pct=100*(scores[family]['mae_million']/old_score['mae_million']-1)))
            old=ref['metrics']['categories'][category]
            a=old['selected_validation']['mae_million'];b=scores[selected]['mae_million']
            selected_comparison.append(dict(reference_version=version,category=category,
                reference_model=old['selected_by_validation_mae'],v5_model=selected,
                reference_mae_million=a,v5_mae_million=b,mae_change_pct=100*(b/a-1)))
        for i,row in enumerate(val):
            for family,values in predicted.items():
                p=float(values[i]);actual=float(y[i])
                predictions.append(dict(record_key=row['record_key'],category=category,source=row['source'],
                    pipeline_group=row['pipeline_group'],location_feature=row['location_feature'],model=family,
                    actual_million=actual,predicted_million=p,absolute_error_million=abs(p-actual),
                    ape_pct=100*abs(p-actual)/actual,selected=family==selected))
        print(json.dumps(dict(category=category,selected=selected,mae_million=scores[selected]['mae_million']),ensure_ascii=False),flush=True)
    c.write_json(stage/'baseline_models.json',models)
    loaded=json.loads((stage/'baseline_models.json').read_text(encoding='utf-8'))
    for category in c.CATEGORIES:
        val=[r for r in parts['validation'] if r['category']==category]
        for family,values in experiment.get_baseline_predictions(val,loaded[category]).items():
            observed=[p['predicted_million'] for p in predictions if p['category']==category and p['model']==family]
            np.testing.assert_allclose(values,observed,rtol=1e-10,atol=1e-8)
    chosen=[p for p in predictions if p['selected']]
    aggregate=c.scores([p['actual_million'] for p in chosen],[p['predicted_million'] for p in chosen])
    report=dict(created_at_utc=datetime.now(timezone.utc).isoformat(),dataset_run=data.relative_to(c.BASE).as_posix(),
        protocol=PROTOCOL,versions=versions,train_n=len(parts['train']),validation_n=len(parts['validation']),
        reserved_eligible_n=len(c.read(folder/'reserved_holdout_registry.csv')),categories=categories,
        aggregate_selected_validation=aggregate,same_family_comparison=comparison,selected_family_comparison=selected_comparison,
        references={v:dict(run=r['run'].relative_to(c.BASE).as_posix(),train_n=sum(cat['train_n'] for cat in r['metrics']['categories'].values()),
            aggregate_selected_validation=r['metrics']['aggregate_selected_validation']) for v,r in references.items()},
        model_reload_verified=True,test_evaluated=False,independent_benchmark=False,automatic_deployment=False,
        limitations=['Same development validation reused for early stopping and model selection; results are not independent test accuracy.',
            'Targets are source-checked asking prices, not verified transaction prices.',
            'Geospatial/alley/POI features remain absent; added samples change source/time/category mix.'])
    c.write_json(stage/'metrics.json',report)
    c.write_csv(stage/'validation_predictions.csv',predictions,list(predictions[0]))
    c.write_csv(stage/'same_family_comparison.csv',comparison,list(comparison[0]))
    c.write_csv(stage/'selected_family_comparison.csv',selected_comparison,list(selected_comparison[0]))
    errors=sorted(chosen,key=lambda r:r['absolute_error_million'],reverse=True)
    c.write_csv(stage/'validation_errors.csv',errors,list(errors[0]))
    coverage=experiment.feature_coverage(parts)
    c.write_csv(stage/'feature_coverage.csv',coverage,list(coverage[0]))
    names=dict(zip(experiment.FAMILIES,['Trung vị địa bàn','Ridge','XGBoost']))
    lines=['# Mô hình v5 — train 2.214 tin','',
        'Đã huấn luyện trên **2.214 train**, đánh giá đúng **299 validation** v3/v4. '
        '**684 tin dự phòng giữ riêng**, không chấm test. CPU hist 4 luồng, cùng tham số v3/v4, không tìm kiếm siêu tham số.','',
        '| Loại | Train | Val | V5 chọn | V3 MAE | V4 MAE | V5 MAE |','|---|---:|---:|---|---:|---:|---:|']
    for category,info in categories.items():
        a=references['v3']['metrics']['categories'][category]['selected_validation']['mae_million']
        b=references['v4']['metrics']['categories'][category]['selected_validation']['mae_million']
        lines.append(f'| {category} | {info["train_n"]} | {info["validation_n"]} | {names[info["selected_by_validation_mae"]]} | {a:,.1f} | {b:,.1f} | {info["selected_validation"]["mae_million"]:,.1f} |')
    lines+=['','MAE tính bằng **triệu VND**, thấp hơn là tốt hơn. Bảng trên chọn họ mô hình riêng từng phiên bản/loại.','',
        '| Phiên bản | Train | MAE tổng hợp (triệu VND) | MAPE | Trong sai số 20% |',
        '|---|---:|---:|---:|---:|']
    for version,ref in report['references'].items():
        s=ref['aggregate_selected_validation']
        lines.append(f'| {version} | {ref["train_n"]} | {s["mae_million"]:,.1f} | {s["mape_pct"]:.2f}% | {s["within_20pct"]:.2f}% |')
    lines.append(f'| v5 | 2214 | {aggregate["mae_million"]:,.1f} | {aggregate["mape_pct"]:.2f}% | {aggregate["within_20pct"]:.2f}% |')
    lines+=['','## XGBoost riêng','', '| Loại | V3 MAE | V4 MAE | V5 MAE |','|---|---:|---:|---:|']
    for category in c.CATEGORIES:
        f=experiment.FAMILIES[2]
        values=[references[v]['metrics']['categories'][category]['validation'][f]['mae_million'] for v in ['v3','v4']]
        lines.append(f'| {category} | {values[0]:,.1f} | {values[1]:,.1f} | {categories[category]["validation"][f]["mae_million"]:,.1f} |')
    better=aggregate['mae_million']<references['v3']['metrics']['aggregate_selected_validation']['mae_million']
    lines+=['',f'V5 {"giảm" if better else "chưa giảm"} MAE tổng hợp so với v3 trên validation phát triển. '
        'Không tự triển khai hoặc thay model cũ. Chưa có kiểm chứng độc lập: 299 tin này đã dùng nhiều lần để dừng sớm/chọn model.','',
        'Các số liệu là giá rao. Feature vẫn là diện tích, địa bàn, phường và số phòng từ trường có cấu trúc; '
        'vocabulary học trên train. Không đưa giá/đơn giá/ID/tiêu đề/mô tả vào X, chưa có tọa độ căn nhà, hẻm hoặc POI.','',
        '[Chỉ số](metrics.json), [so sánh cùng họ](same_family_comparison.csv), '
        '[so sánh họ được chọn](selected_family_comparison.csv), [dự đoán](validation_predictions.csv), '
        '[sai số theo tin](validation_errors.csv), [độ phủ feature](feature_coverage.csv). '
        'JSON XGBoost xuất log giá: dùng cùng schema và exp để trả về triệu VND. Đã tải lại model và baseline để kiểm tra dự đoán.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target);publish(target)
    print(json.dumps(dict(run=str(target),aggregate_validation=aggregate,selected_comparison=selected_comparison),ensure_ascii=False,indent=2),flush=True)


if __name__=='__main__':
    main()
