"""Experimental baselines using area and a documented location label only."""
import hashlib
import json
from build_training_v1 import OUT, SEED
from audit_all_collected import read, save_csv
from prepare_smartprop_dataset import CATEGORIES
from train_smartprop_baseline import fit, predict, metrics


def main():
    rows = read(OUT/'main_dataset.csv')
    # Reuse baseline math without altering stored historical districts.
    rows = [dict(r,district=r['location_feature']) for r in rows]
    report = dict(target='total asking price, million VND',features=['area_sqm','location_feature'],
        input_sha256=hashlib.sha256((OUT/'main_dataset.csv').read_bytes()).hexdigest(),
        split_seed=SEED, categories={},limitations=['Automatically screened labels, not verified transactions.',
            'Heuristic property groups can miss or overgroup duplicates.',
            'Grouped random holdouts, not future-time prediction. Small category holdouts.',
            'Source update/display dates are not necessarily first-post dates.'])
    models = {}; predictions = []
    for category in CATEGORIES:
        parts = {s:[r for r in rows if r['category']==category and r['model_split']==s]
                 for s in ['train','validation','test']}
        info = dict(split_counts={s:len(p) for s,p in parts.items()})
        report['categories'][category]=info
        if min(map(len,parts.values()))<5:
            info['status']='insufficient_data';continue
        params = fit(parts['train']);models[category]=params
        estimates = predict(parts['validation'],params)
        info['validation'] = {m:metrics([float(r['price_million']) for r in parts['validation']],v) for m,v in estimates.items()}
        selected = min(info['validation'],key=lambda m:info['validation'][m]['mae_million'])
        info['selected_by_validation_mae']=selected
        # Evaluate the selected model on test after selection.
        testpred = predict(parts['test'],params)[selected]
        info['selected_test_metrics']=metrics([float(r['price_million']) for r in parts['test']],testpred)
        for r,p in zip(parts['test'],testpred):
            predictions.append(dict(record_key=r['record_key'],category=category,location_feature=r['district'],
                actual_million=r['price_million'],predicted_million=float(p),selected_model=selected))
    (OUT/'baseline_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    (OUT/'baseline_models.json').write_text(json.dumps(models,ensure_ascii=False,indent=2),encoding='utf-8')
    save_csv(OUT/'baseline_test_predictions.csv',predictions,
             ['record_key','category','location_feature','actual_million','predicted_million','selected_model'])
    lines=['# Kết quả mô hình cơ sở v1','',
        'Hai ứng viên: trung vị đơn giá theo địa bàn và Ridge log giá theo log diện tích/địa bàn. '
        'Mọi thống kê, danh mục và chuẩn hóa học trên train; chọn mô hình bằng MAE validation. '
        'Không dùng tiêu đề, đơn giá chứa nhãn hay nguồn làm đặc trưng. Địa bàn chưa thấy trong train dùng mức chung.', '',
        '| Loại | Train / Val / Test | MAE test (triệu VND) | MAPE test | R² test |','|---|---|---:|---:|---:|']
    for c,info in report['categories'].items():
        if 'selected_test_metrics' not in info:continue
        m=info['selected_test_metrics'];counts=info['split_counts']
        lines.append(f'| {c} | {counts["train"]} / {counts["validation"]} / {counts["test"]} | {m["mae_million"]:.1f} | {m["mape_pct"]:.1f}% | {m["r2"]:.3f} |')
    lines+=['','Kết quả thử nghiệm trên giá rao và mẫu qua sàng lọc; chưa chứng minh hiệu quả thị trường. '
            'Không so trực tiếp với điểm số trên test cũ. Tập thiếu ngày chưa tham gia huấn luyện. '
            'Chi tiết mô hình đã chọn và chỉ số validation trong `baseline_metrics.json`.', '',
            'Chạy: `python ai-services/app/data/train_training_v1.py`.','']
    (OUT/'BASELINE.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps(report['categories'],ensure_ascii=False,indent=2))


if __name__=='__main__':main()
