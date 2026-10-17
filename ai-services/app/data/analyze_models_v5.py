"""Paired residual analysis of frozen v3/v4/v5 validation; never fit or relabel."""
import hashlib
import json
import re
import uuid
from collections import Counter,defaultdict
from pathlib import Path

import numpy as np
import training_v3_common as c
import train_training_v3 as experiment
import review_geospatial_candidates as title_review
import geospatial_enrichment as geo
from smartprop_geography import norm

OUT=c.PROCESSED/'models_v5_diagnostics'
POLICY=dict(priority_per_ranking=10,small_group_n=10,sparse_location_train_n=10,
    price_band_limits_million=[2000,5000,10000,20000],
    label_action='none; residuals do not prove bad labels',
    claim_scope='Source title claims for planning only; not verified geometry or model features',
    test_evaluated=False,retrained=False,new_network_requests=0)


def latest(root):
    return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def band(value):
    for limit,label in zip(POLICY['price_band_limits_million'],['<2 tỷ','2–<5 tỷ','5–<10 tỷ','10–<20 tỷ']):
        if value<limit:
            return label
    return '≥20 tỷ'


def area_band(value):
    return '<50 m²' if value<50 else '50–<100 m²' if value<100 else '100–<200 m²' if value<200 else '≥200 m²'


def support_band(n):
    return 'unseen' if n==0 else 'below_10' if n<10 else 'at_least_10'


def metrics(rows,version):
    actual=[float(r['actual_million']) for r in rows]
    predicted=[float(r[version+'_predicted_million']) for r in rows]
    return c.scores(actual,predicted)


def feature_inventory(parts,origin):
    result=[]
    for split,rows in parts.items():
        for row in rows:
            original=origin[row['record_key']]
            title=original['title']
            claims=title_review.access_claims(title)
            text=norm(title)
            scope=[]
            if re.search(r'\bdat (?:vuon|nong nghiep)\b',text):scope.append('garden_or_agricultural_title_requires_source_context')
            if re.search(r'\b(?:[2-9]|\d{2,})\s*phong tro\b|\bday tro\b',text):scope.append('rental_unit_building_title_requires_source_context')
            result.append(dict(record_key=row['record_key'],split=split,category=row['category'],source=row['source'],
                title=title,access_type_claim=claims['access_type_claim'],
                alley_width_claim_m=';'.join(map(str,claims['alley_width_claim_m'])),
                road_width_claim_m=';'.join(map(str,claims['road_width_claim_m'])),
                car_access_claim=claims['car_access_claim'],
                floor_number_title_mention=bool(re.search(r'\d+(?:[.,]\d+)?\s*tang\b',text)),
                villa_title_mention=bool(re.search(r'\bbiet thu\b',text)),
                claim_flags=';'.join(claims['flags']),scope_review_flags=';'.join(scope),
                provenance='frozen_collected_title; unverified_source_claim; DO_NOT_TRAIN',label_action='none'))
    return result


def segment_metrics(rows):
    result=[]
    for category in ['ALL']+c.CATEGORIES:
        subset=rows if category=='ALL' else [r for r in rows if r['category']==category]
        for dimension in ['source','location_feature','price_band','area_band','ward_status','rooms_status',
                          'location_support_v5','ward_encoded_status_v5','unit_price_tail_v5','access_title_claim','villa_title_mention']:
            groups=defaultdict(list)
            for row in subset:groups[str(row[dimension])].append(row)
            for value,members in sorted(groups.items()):
                for version in ['v3','v4','v5']:
                    scores=metrics(members,version)
                    result.append(dict(category=category,dimension=dimension,segment=value,version=version,
                        **scores,signed_mean_error_million=float(np.mean([r[version+'_signed_error_million'] for r in members])),
                        total_absolute_error_million=sum(r[version+'_absolute_error_million'] for r in members),
                        n_below_10=len(members)<10,interpretation='Descriptive association only; not causal or independent test'))
    return result


def main():
    runs={v:latest(c.PROCESSED/f'models_{v}_validation') for v in ['v3','v4','v5']}
    reports={v:json.loads((r/'metrics.json').read_text(encoding='utf-8')) for v,r in runs.items()}
    data=c.BASE/reports['v5']['dataset_run']
    proof_path=c.PROCESSED/'models_v5_validation/verification.json'
    proof=json.loads(proof_path.read_text(encoding='utf-8'))
    if not proof['verified'] or proof['run']!=runs['v5'].relative_to(c.PROCESSED/'models_v5_validation').as_posix():
        raise ValueError('V5 verification must match the analyzed model run')
    protected={}
    paths=[Path(__file__),Path(c.__file__),Path(experiment.__file__),Path(title_review.__file__),Path(geo.__file__),
           proof_path,data/'manifest.json',data/'all_listings_after_review.csv']
    for directory in list(runs.values())+[data]:
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        c.verify(manifest['output_sha256'],directory)
        protected.update({(directory/p).relative_to(c.BASE).as_posix():sha for p,sha in manifest['output_sha256'].items()})
        protected[(directory/'manifest.json').relative_to(c.BASE).as_posix()]=c.sha(directory/'manifest.json')
        paths.append(directory/'manifest.json')
    parts={s:c.read(data/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    if len(parts['train'])!=2214 or len(parts['validation'])!=299:
        raise ValueError('Unexpected current cohorts')
    origin={r['record_key']:r for r in c.read(data/'all_listings_after_review.csv')}
    predictions={v:{(r['record_key'],r['model']):r for r in c.read(directory/'validation_predictions.csv')}
                 for v,directory in runs.items()}
    for version,directory in runs.items():
        paths += [directory/'metrics.json',directory/'validation_predictions.csv']
        previous_data=c.BASE/reports[version]['dataset_run']
        val=previous_data/('validation.csv' if version=='v3' else 'training_inputs/validation.csv')
        assert {r['record_key']:r for r in c.read(val)}=={r['record_key']:r for r in parts['validation']}
        paths.append(val)
    paths+=[data/'training_inputs/train.csv',data/'training_inputs/validation.csv']
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    fingerprint=hashlib.sha256(json.dumps(dict(inputs=inputs,policy=POLICY),sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/fingerprint
    if target.exists():
        m=json.loads((target/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['input_sha256']);c.verify(m['protected_sha256']);c.verify(m['output_sha256'],target)
        publish(target);print('Existing diagnostics verified: '+str(target));return
    inventory=feature_inventory(parts,origin)
    inventory_bykey={r['record_key']:r for r in inventory}
    train_locations=Counter((r['category'],r['location_feature']) for r in parts['train'])
    specs={category:c.schema([r for r in parts['train'] if r['category']==category]) for category in c.CATEGORIES}
    tails={category:np.quantile([float(r['price_million'])/float(r['area_sqm']) for r in parts['train'] if r['category']==category],[.01,.99]) for category in c.CATEGORIES}
    paired,family_rows=[],[]
    for row in parts['validation']:
        key=row['record_key'];actual=float(row['price_million']);area=float(row['area_sqm'])
        original=origin[key];feature=inventory_bykey[key];category=row['category']
        ward=row['location_feature']+'|'+row['ward_source'] if row['ward_source'] else ''
        unit=actual/area;lo,hi=tails[category]
        r=dict(record_key=key,category=category,source=row['source'],pipeline_group=row['pipeline_group'],
            location_feature=row['location_feature'],actual_million=actual,area_sqm=area,price_band=band(actual),area_band=area_band(area),
            ward_status='available' if row['ward_source'] else 'missing',
            rooms_status='not_applicable_land' if category=='Đất nền' else 'available' if row['rooms'] else 'missing',
            train_location_n_v5=train_locations[(category,row['location_feature'])],
            location_support_v5=support_band(train_locations[(category,row['location_feature'])]),
            ward_encoded_status_v5='missing' if not ward else 'encoded' if ward in specs[category]['wards'] else 'unseen_or_rare',
            unit_price_tail_v5='below_train_q01' if unit<lo else 'above_train_q99' if unit>hi else 'within_train_q01_q99',
            access_title_claim=feature['access_type_claim'],villa_title_mention=feature['villa_title_mention'],
            title=original['title'],detail_url=row['detail_url'],source_price_raw=json.loads(original['raw_json']).get('price_raw',''),
            label_quality=row['label_quality'],scope_review_flags=feature['scope_review_flags'],label_action='none; independent source review required')
        for version in ['v3','v4','v5']:
            chosen=reports[version]['categories'][category]['selected_by_validation_mae']
            p=predictions[version][(key,chosen)]
            assert p['category']==category and float(p['actual_million'])==actual
            value=float(p['predicted_million']);error=value-actual
            r.update({version+'_model':chosen,version+'_predicted_million':value,version+'_signed_error_million':error,
                      version+'_absolute_error_million':abs(error),version+'_ape_pct':100*abs(error)/actual})
        r.update(v5_error_change_vs_v3_million=r['v5_absolute_error_million']-r['v3_absolute_error_million'],
                 v5_error_change_vs_v4_million=r['v5_absolute_error_million']-r['v4_absolute_error_million'])
        paired.append(r)
        for family in experiment.FAMILIES:
            f=dict(record_key=key,category=category,source=row['source'],model=family,actual_million=actual)
            for version in ['v3','v4','v5']:
                p=predictions[version][(key,family)]
                assert p['category']==category and float(p['actual_million'])==actual
                value=float(p['predicted_million'])
                f.update({version+'_predicted_million':value,version+'_absolute_error_million':abs(value-actual)})
            family_rows.append(f)
    aggregate={v:metrics(paired,v) for v in ['v3','v4','v5']}
    for version in aggregate:
        for field,value in aggregate[version].items():
            if value is not None:np.testing.assert_allclose(value,reports[version]['aggregate_selected_validation'][field],rtol=1e-9)
    total=sum(r['v5_absolute_error_million'] for r in paired)
    for row in paired:row['v5_error_share_pct']=100*row['v5_absolute_error_million']/total
    rankings={'largest_absolute_error':sorted(paired,key=lambda r:r['v5_absolute_error_million'],reverse=True)[:10],
              'largest_percentage_error':sorted(paired,key=lambda r:r['v5_ape_pct'],reverse=True)[:10],
              'largest_regression_vs_v3':sorted([r for r in paired if r['v5_error_change_vs_v3_million']>0],key=lambda r:r['v5_error_change_vs_v3_million'],reverse=True)[:10]}
    reasons=defaultdict(list)
    for name,rows in rankings.items():
        for row in rows:reasons[row['record_key']].append(name)
    priority=[dict(r,priority_reasons=';'.join(reasons[r['record_key']]),review_decision='not_reviewed',
                   review_scope='Source QA/feature investigation only; DO_NOT_TRAIN',proposed_price_million='',proposed_area_sqm='')
              for r in sorted(paired,key=lambda r:r['v5_absolute_error_million'],reverse=True) if r['record_key'] in reasons]
    contributions=[]
    for reference in ['v3','v4']:
        for category in c.CATEGORIES:
            subset=[r for r in paired if r['category']==category]
            old=sum(r[reference+'_absolute_error_million'] for r in subset);new=sum(r['v5_absolute_error_million'] for r in subset)
            contributions.append(dict(reference_version=reference,category=category,n=len(subset),
                reference_mae_million=old/len(subset),v5_mae_million=new/len(subset),
                contribution_to_overall_mae_change_million=(new-old)/len(paired)))
    feature_gaps=experiment.feature_coverage(parts)
    claim_counts=[]
    for split in parts:
        for category in c.CATEGORIES:
            subset=[r for r in inventory if r['split']==split and r['category']==category]
            for field in ['access_type_claim','alley_width_claim_m','road_width_claim_m','floor_number_title_mention','villa_title_mention']:
                n=sum(r[field] in ['alley_claim','frontage_claim'] if field=='access_type_claim' else bool(r[field]) for r in subset)
                claim_counts.append(dict(split=split,category=category,claim=field,n=len(subset),available=n,available_pct=100*n/len(subset),
                    status='title_claim_only_not_model_feature'))
    high_price=[r for r in paired if r['actual_million']>=10000]
    highest=sorted(paired,key=lambda r:r['v5_absolute_error_million'],reverse=True)
    transitions={reference:dict(improved=sum(r['v5_absolute_error_million']<r[reference+'_absolute_error_million']-1e-8 for r in paired),
        worsened=sum(r['v5_absolute_error_million']>r[reference+'_absolute_error_million']+1e-8 for r in paired),
        unchanged=sum(abs(r['v5_absolute_error_million']-r[reference+'_absolute_error_million'])<=1e-8 for r in paired),
        newly_within_20pct=sum(r['v5_ape_pct']<=20<r[reference+'_ape_pct'] for r in paired),
        lost_within_20pct=sum(r[reference+'_ape_pct']<=20<r['v5_ape_pct'] for r in paired)) for reference in ['v3','v4']}
    summary=dict(model_runs={v:r.relative_to(c.BASE).as_posix() for v,r in runs.items()},dataset_run=data.relative_to(c.BASE).as_posix(),
        train_n=2214,validation_n=299,reserved_eligible_n=684,aggregate_selected=aggregate,
        aggregate_xgboost={v:c.scores([r['actual_million'] for r in family_rows if r['model']==experiment.FAMILIES[2]],
            [r[v+'_predicted_million'] for r in family_rows if r['model']==experiment.FAMILIES[2]]) for v in ['v3','v4','v5']},
        top10_absolute_error_share_pct=100*sum(r['v5_absolute_error_million'] for r in highest[:10])/total,
        top20_absolute_error_share_pct=100*sum(r['v5_absolute_error_million'] for r in highest[:20])/total,
        price_ge10b_n=len(high_price),price_ge10b_absolute_error_share_pct=100*sum(r['v5_absolute_error_million'] for r in high_price)/total,
        price_ge10b_underpredicted_n=sum(r['v5_signed_error_million']<0 for r in high_price),
        priority_review_n=len(priority),scope_title_watchlist_n=sum(bool(r['scope_review_flags']) for r in inventory),
        paired_transitions=transitions,policy=POLICY)
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    exports={'paired_validation.csv':paired,'same_family_validation.csv':family_rows,'segment_metrics.csv':segment_metrics(paired),
        'category_contributions.csv':contributions,'priority_review.csv':priority,'feature_claim_inventory_DO_NOT_TRAIN.csv':inventory,
        'feature_coverage.csv':feature_gaps,'title_claim_coverage.csv':claim_counts}
    for name,rows in exports.items():c.write_csv(stage/name,rows,list(rows[0]))
    watchlist=[r for r in inventory if r['scope_review_flags']]
    c.write_csv(stage/'source_scope_watchlist.csv',watchlist,list(inventory[0]))
    c.write_json(stage/'summary.json',summary)
    write_report(stage,summary,paired,contributions,feature_gaps,claim_counts)
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target);publish(target)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True);print(target,flush=True)


def write_report(stage,s,paired,contributions,gaps,claims):
    lines=['# Phân tích sai số v5 so với v3/v4','',
        'Đối chiếu đúng **299 ID validation**, cùng giá/diện tích/nhãn và giá trị trường đầu vào giữa ba phiên bản. '
        'Vocabulary/encoder được học riêng từ train của từng phiên bản. '
        'V5 dùng 2.214 train; không fit model, không sửa nhãn, không chấm 684 tin dự phòng.','',
        '| Phiên bản | MAE (triệu VND) | MAPE | Trong sai số 20% | Tin sai >50% |','|---|---:|---:|---:|---:|']
    for v,a in s['aggregate_selected'].items():lines.append(f'| {v} | {a["mae_million"]:,.2f} | {a["mape_pct"]:.2f}% | {a["within_20pct"]:.2f}% | {a["above_50pct"]} |')
    a=s['aggregate_xgboost']['v3']['mae_million'];b=s['aggregate_xgboost']['v5']['mae_million']
    lines+=['',f'**So riêng XGBoost:** MAE tổng hợp v3 **{a:,.2f}** → v5 **{b:,.2f}** triệu VND '
        f'({100*(b/a-1):+.2f}%). XGBoost v5 tiến bộ theo MAE, nhưng vẫn chưa vượt bộ model được chọn của v3 '
        '(Ridge cho nhà, trung vị cho đất, XGBoost cho căn hộ). Không gọi bộ v3 đó là XGBoost thuần.']
    lines+=['','## Sai số tập trung ở đâu','',
        f'- **{s["price_ge10b_n"]} tin ≥10 tỷ** chiếm **{s["price_ge10b_absolute_error_share_pct"]:.2f}%** tổng sai số tuyệt đối; '
        f'**{s["price_ge10b_underpredicted_n"]}** tin trong nhóm này được dự đoán thấp hơn giá rao.',
        f'- **10 tin sai nhiều nhất** chiếm **{s["top10_absolute_error_share_pct"]:.2f}%**; 20 tin chiếm **{s["top20_absolute_error_share_pct"]:.2f}%** tổng sai số tuyệt đối.',
        '- MAE tính theo số tiền nên chịu ảnh hưởng lớn từ tin giá cao; MAPE chia sai số cho giá từng tin, có thể rất lớn ở tin giá thấp. '
        'Hai chỉ số cùng được báo cáo, không đổi thước đo chọn model sau khi nhìn kết quả.','',
        '| Loại | V3 MAE | V5 MAE | Đóng góp vào thay đổi MAE tổng |','|---|---:|---:|---:|']
    for r in contributions:
        if r['reference_version']=='v3':lines.append(f'| {r["category"]} | {r["reference_mae_million"]:,.2f} | {r["v5_mae_million"]:,.2f} | {r["contribution_to_overall_mae_change_million"]:+.2f} |')
    lines+=['','Đơn vị triệu VND. Đây là so sánh **họ được chọn riêng từng phiên bản**, v3 chọn Ridge cho nhà và trung vị cho đất; '
        'v5 chọn XGBoost cả ba loại. [So sánh cùng họ từng ID](same_family_validation.csv) tránh lẫn hai phép so sánh.','',
        '## Các nhóm cần chú ý','', '| Nhóm | Số tin | V3 MAE | V5 MAE | V5 MAPE |','|---|---:|---:|---:|---:|']
    for dimension in ['price_band','source','rooms_status','ward_encoded_status_v5']:
        values=['<2 tỷ','2–<5 tỷ','5–<10 tỷ','10–<20 tỷ','≥20 tỷ'] if dimension=='price_band' else sorted({str(r[dimension]) for r in paired})
        for value in values:
            rows=[r for r in paired if str(r[dimension])==value];a=metrics(rows,'v3');b=metrics(rows,'v5')
            warning=' (nhóm nhỏ)' if len(rows)<10 else ''
            lines.append(f'| {dimension}: {value}{warning} | {len(rows)} | {a["mae_million"]:,.1f} | {b["mae_million"]:,.1f} | {b["mape_pct"]:.1f}% |')
    lines+=['','[Toàn bộ phân nhóm](segment_metrics.csv) gồm địa bàn, nguồn, mức giá, diện tích, độ phủ phường/số phòng, '
        'mức hỗ trợ địa bàn trong train, đuôi đơn giá và dấu hiệu mặt tiền/kiệt. Nhóm dưới 10 tin được gắn cờ; '
        'không suy ra nguyên nhân từ các tương quan này vì nguồn, địa bàn, loại và mức giá có thể cùng thay đổi.','',
        '## Đặc trưng nên bổ sung','',
        '1. **Số phòng và số tầng:** ưu tiên trường có cấu trúc, sau đó trích câu mô tả tài sản hiện hữu có bằng chứng. '
        'Không lấy số tầng của tòa chung cư làm tầng căn hộ, số phòng kinh doanh làm phòng ngủ, hoặc kế hoạch xây dựng làm hiện trạng.',
        '2. **Mặt tiền/kiệt và độ rộng đường/hẻm:** chỉ chấp nhận câu xác định tài sản, phân biệt “gần mặt tiền”, '
        'số kiệt, đường Võ Văn Kiệt và bề ngang thửa đất. Không điền unknown thành 0 hoặc coi lời rao là đo đạc đã xác minh.',
        '3. **Nhà thông thường/biệt thự và địa bàn:** nhà đang gộp nhiều phân khúc; kiểm chứng subtype theo nguồn và '
        'đồng nhất địa bàn cũ/mới trước thử nghiệm. Không tự quy đổi phường từ tên đường.',
        '4. **Khoảng cách tiện ích:** để sau khi có tọa độ tài sản đủ tin cậy; tên đường hoặc pin khu vực chưa xác minh không đủ.','',
        '| Loại train | Feature đang dùng | Có dữ liệu | Tổng |','|---|---|---:|---:|']
    for r in gaps:
        if r['split']=='train' and r['feature'] in ['ward_source','rooms'] and not(r['category']=='Đất nền' and r['feature']=='rooms'):
            lines.append(f'| {r["category"]} | {r["feature"]} | {r["available"]} ({r["available_pct"]:.1f}%) | {r["n"]} |')
    lines+=['','[Độ phủ dấu hiệu trong tiêu đề](title_claim_coverage.csv) chỉ cho biết khả năng khảo sát dữ liệu đã lưu; '
        'chưa phải bộ feature mới, chưa trích toàn bộ mô tả/HTML và không chứng minh dấu hiệu làm model tốt hơn. '
        'Mỗi feature mới cần kiểm thử các câu phủ định/địa điểm gần đó/giá và thử nghiệm bỏ/thêm feature với giao thức cố định.','',
        '## Rà soát nguồn có mục tiêu','',
        f'[Danh sách ưu tiên](priority_review.csv) có **{s["priority_review_n"]} ID**, là hợp của top 10 sai số tiền, top 10 sai số phần trăm '
        'và top 10 tăng sai số so với v3. Các cột quyết định giữ `not_reviewed`, giá/diện tích đề xuất để trống. '
        'Sai số cao không chứng minh nhãn sai; không xóa hoặc sửa giá chỉ để cải thiện metric.',
        f'[Danh sách cần kiểm tra phạm vi loại tài sản](source_scope_watchlist.csv) có **{s["scope_title_watchlist_n"]} ID train/validation** '
        'mang dấu hiệu đất vườn/nông nghiệp hoặc phòng trọ trên tiêu đề. Cần đọc nguồn đúng ID trước quyết định; '
        'đây không phải kết luận các tin đã sai hoặc tự bị loại.','',
        'Ví dụ `cafeland:3164071`: nguồn lưu giá rao 1.000 triệu, diện tích 403 m²; v5 dự đoán khoảng 16.354 triệu. '
        'Sự chênh lệch cần đối chiếu nguồn, phân khúc và đặc trưng; không có căn cứ từ dự đoán để đổi giá thành 16 tỷ.','',
        '## Giới hạn và bước kế tiếp','',
        'Đây là phân tích hậu nghiệm trên validation phát triển đã dùng cho dừng sớm/chọn model, không phải test độc lập. '
        'Các mức giá chỉ là phân nhóm sai số, không được đưa giá thật/đơn giá vào X. '
        'Giữ nguyên model và các cohort; không đổi nhãn validation rồi so metric như cùng một tập.',
        'Bước tiếp theo: xây bộ trích đặc trưng có bằng chứng cho số tầng/phòng, mặt tiền/kiệt và subtype nhà; '
        'đóng băng giao thức trước thử nghiệm. Tập kiểm chứng mới cần tài sản mới, tránh trùng train/validation và '
        'không chọn theo residual; kế hoạch pilot của v3 trước đây chưa phải dữ liệu test đã thu thập.','',
        '[299 cặp dự đoán](paired_validation.csv), [đóng góp theo loại](category_contributions.csv), [số liệu](summary.json). '
        'Các file rà soát có tiêu đề/giá thật/dự đoán không dùng làm đầu vào huấn luyện.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')


def publish(target):
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# Phân tích sai số v5\n\n'
        f'[Báo cáo hiện tại]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':
    main()
