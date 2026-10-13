"""Inspect validation errors and source feature coverage; keep all v1 labels/splits frozen."""
import hashlib
import json
import re
from collections import Counter
import numpy as np
from audit_all_collected import BASE, read, save_csv, number, price
from smartprop_geography import norm
from prepare_smartprop_dataset import CATEGORIES

DATA = BASE/'processed/training_v1'
MODEL = BASE/'processed/xgboost_v1'
OUT = BASE/'processed/xgboost_validation_review'


def source_features(row):
    raw=json.loads(row['raw_json'])
    ward=norm(raw.get('ward',''))
    ward=re.sub(r'^(phuong|xa|thi tran)\s+','',ward)
    if ward in ['', 'khong xac dinh','dang cap nhat']:ward=''
    value=str(raw.get('rooms') or '').strip()
    match=re.fullmatch(r'(\d+)(?:\.0)?(?:\s*(?:phòng|phong)(?:\s*(?:ngủ|ngu))?)?',value,re.I)
    rooms=float(match[1]) if match and 1<=int(match[1])<=30 else None
    return dict(ward_source=ward,rooms=rooms,legal_status=norm(raw.get('legal_status','')),
                street_source=norm(raw.get('street','')),latitude=number(raw.get('latitude')),
                longitude=number(raw.get('longitude')),direction=norm(raw.get('direction','')))


def content_flags(row):
    """Prioritize source review, never silently change a target because prediction is wrong."""
    raw=json.loads(row['raw_json']);t=norm(row['title']);flags=[]
    if re.search(r'\b(dong|tra|thanh toan|von)\s*\d+\s*%|\b\d+\s*%\s*(von|thanh toan)|\b(booking|dat coc|tra truoc)\b',t):
        flags.append('payment_schedule_total_price_needs_source_check')
    if re.search(r'\b(cap (?:dat|lien ke)|\d+\s*lo|gia.{0,15}/lo|gia.{0,15}/can)\b',t):
        flags.append('per_unit_or_multiple_properties_needs_source_check')
    if re.search(r'\b(dat co nha|tang \d*\s*nha|san nha|quy dat)\b',t):
        flags.append('land_with_building_needs_source_check')
    if re.search(r'\b(so huu|thoi han|\d+ nam|condotel|wyndham|cam ket loi nhuan)\b',t):
        flags.append('tenure_or_special_project_needs_source_check')
    p=float(row['price_million'])
    for k in ['price_raw','detail_price_raw']:
        if raw.get(k):
            v=price(raw[k])
            if v is None or abs(v-p)>.01:flags.append(k+'_conflict')
    return flags


def main():
    paths=[DATA/'train.csv',DATA/'validation.csv',DATA/'test.csv',MODEL/'metrics.json',MODEL/'holdout_predictions.csv']
    hashes={p:hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}
    report=json.loads((MODEL/'metrics.json').read_text(encoding='utf-8'))
    assert all(hashes[DATA/p]==h for p,h in report['source_sha256'].items()),'Stale model inputs'
    # Test CSV is hashed solely for preservation; test predictions/labels are not analyzed.
    train=read(DATA/'train.csv');val=read(DATA/'validation.csv')
    predictions={p['record_key']:p for p in read(MODEL/'holdout_predictions.csv') if p['split']=='validation'}
    assert set(predictions)=={r['record_key'] for r in val}
    OUT.mkdir(parents=True,exist_ok=True)
    coverage=[]
    for split,rows in [('train',train),('validation',val)]:
        features=[source_features(r) for r in rows]
        for field in features[0]:
            for category in ['ALL']+CATEGORIES:
                values=[f[field] for r,f in zip(rows,features) if category=='ALL' or r['category']==category]
                available=sum(v is not None and v!='' for v in values)
                coverage.append(dict(split=split,category=category,feature=field,total=len(values),available=available,
                                     available_pct=100*available/len(values) if values else 0))
    errors=[]
    for row in val:
        p=predictions[row['record_key']];actual=float(row['price_million']);pred=float(p['predicted_million'])
        assert float(p['actual_million'])==actual
        features=source_features(row);flags=content_flags(row)
        errors.append(dict(record_key=row['record_key'],category=row['category'],source=row['source'],
            detail_url=row['detail_url'],title=row['title'],address_raw=row['address_raw'],location_feature=row['location_feature'],
            area_sqm=row['area_sqm'],actual_million=actual,predicted_million=pred,
            signed_error_million=pred-actual,absolute_error_million=abs(pred-actual),ape_pct=100*abs(pred-actual)/actual,
            review_codes=';'.join(flags),review_decision='pending_source_check' if flags else 'no_label_change',
            ward_available=bool(features['ward_source']),rooms_available=features['rooms'] is not None,
            detail_fetched=row['detail_fetched'],input_file=row['input_file'],input_row=row['input_row']))
    errors.sort(key=lambda r:r['ape_pct'],reverse=True)
    save_csv(OUT/'validation_errors.csv',errors,list(errors[0]))
    save_csv(OUT/'validation_source_check_queue.csv',[r for r in errors if r['review_codes']],list(errors[0]))
    save_csv(OUT/'feature_coverage.csv',coverage,list(coverage[0]))
    # Apply the same content rules to train, independent of residuals; no test inspection.
    trainflags=[dict(record_key=r['record_key'],title=r['title'],detail_url=r['detail_url'],
                     review_codes=';'.join(content_flags(r)),decision='pending_source_check') for r in train if content_flags(r)]
    save_csv(OUT/'train_source_check_queue.csv',trainflags,['record_key','title','detail_url','review_codes','decision'])
    summary=dict(validation_rows=len(val),train_rows=len(train),
        validation_content_flagged=sum(bool(r['review_codes']) for r in errors),train_content_flagged=len(trainflags),
        categories={c:dict(n=sum(r['category']==c for r in errors),
            ape_above_50pct=sum(r['category']==c and r['ape_pct']>50 for r in errors),
            ape_above_100pct=sum(r['category']==c and r['ape_pct']>100 for r in errors)) for c in CATEGORIES},
        input_sha256={p.relative_to(BASE).as_posix():h for p,h in hashes.items()},
        test_not_analyzed=True,labels_and_splits_unchanged=True)
    assert all(hashlib.sha256(p.read_bytes()).hexdigest()==h for p,h in hashes.items())
    (OUT/'summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Phân tích lỗi XGBoost trên validation','',
        f'Đã phân tích {len(val)} tin validation, đối chiếu hash đầu vào với mô hình gốc. Không phân tích lại test, không sửa nhãn/split.', '',
        '| Loại | Số tin | Sai số tương đối >50% | >100% |','|---|---:|---:|---:|']
    for c,s in summary['categories'].items():lines.append(f'| {c} | {s["n"]} | {s["ape_above_50pct"]} | {s["ape_above_100pct"]} |')
    lines+=['', '## Các trường hợp cần kiểm tra', '',
        f'Có {summary["validation_content_flagged"]} tin validation và {len(trainflags)} tin train có tín hiệu cần kiểm tra nguồn. '
        'Sai số dự đoán lớn không chứng minh nhãn sai. Không loại tin vì mô hình dự đoán sai hoặc sửa giá theo dự đoán.', '',
        '- CafeLand 3146736: đất 516m² ở Hòa Phú, giá 3,6 tỷ nhưng dự đoán khoảng 28,3 tỷ. Giá trong tiêu đề khớp nhãn; có khả năng địa bàn cấp huyện và diện tích chưa đủ diễn tả khác biệt đất vùng ven. Chưa có bằng chứng để sửa nhãn.',
        '- Nhadat24h 4374835: “cặp liền kề”, “890tr/lô”; cần xác minh diện tích tương ứng một lô hay cả cặp.',
        '- Nhadat24h 4396478: “2 tỷ/căn”, “đóng 50%”; cần phân biệt giá toàn bộ và lịch thanh toán. Không tự coi 2 tỷ là giá trả trước.', '',
        '## Bổ sung đặc trưng', '',
        'Đề xuất thử phường/xã có sẵn trong trường nguồn, số phòng hợp lệ và cờ thiếu dữ liệu. Không trích số tiền từ tiêu đề làm đặc trưng. '
        'Danh mục phường học từ train, giá trị chưa thấy có cờ riêng. Không suy phường CafeLand từ tên quận hoặc đoán từ tiêu đề.', '',
        'Pháp lý, tọa độ và hướng có độ phủ thấp trong train nên chưa đưa vào thử nghiệm đầu. Pháp lý không có dữ liệu được giữ là thiếu, không coi là không có sổ.', '',
        '`feature_coverage.csv` ghi độ phủ thực tế theo loại và split; `validation_errors.csv` có sai số từng tin; '
        '`validation_source_check_queue.csv` và `train_source_check_queue.csv` giữ URL và lý do cần đối chiếu. Chưa tải lại trang chi tiết.', '',
        'Chạy: `python ai-services/app/data/analyze_xgboost_validation.py`.', '']
    (OUT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    print(json.dumps({k:v for k,v in summary.items() if k!='input_sha256'},ensure_ascii=False,indent=2))


if __name__=='__main__':main()
