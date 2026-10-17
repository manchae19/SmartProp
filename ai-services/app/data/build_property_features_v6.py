"""Enrich the fixed 2214/299 cohort with literal text claims and provenance."""
import hashlib
import json
import uuid
from collections import Counter
from pathlib import Path
import training_v3_common as c
import property_text_features_v6 as rules

OUT=c.PROCESSED/'property_features_v6'


def latest(root):
    return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def admit_body(row,e,fetch):
    if not e or not e.get('identity_verified') or not e.get('structure_verified'):
        return '', 'unavailable_or_unverified'
    if (fetch.get('http_status')!=200 or not e.get('detail_sha256') or
        e['detail_sha256']!=fetch.get('sha256')):
        return '', 'detail_provenance_mismatch'
    if any(e.get(f) is None or abs(float(e[f])-float(row[f]))>.01 for f in ['price_million','area_sqm']):
        return '', 'detail_header_differs_from_frozen_snapshot'
    if e.get('category') and e['category']!=row['category']:
        return '', 'detail_category_differs_from_frozen_snapshot'
    return e.get('asset_description',e.get('description','')), 'verified_matching_snapshot'


def coverage(features,parts):
    result=[]
    for split,rows in parts.items():
        for category in c.CATEGORIES:
            subset=[r for r in rows if r['category']==category]
            for field in rules.FEATURES:
                applicable=(field=='rooms_completed' and category!='Đất nền' or
                    field in ['floors_claim','house_subtype_claim'] and category=='Nhà ở' or
                    field=='access_claim' and category in ['Nhà ở','Đất nền'])
                known=sum(str(features[r['record_key']][field])!='' for r in subset) if applicable else 0
                result.append(dict(split=split,category=category,feature=field,applicable=applicable,
                    n=len(subset),available=known,available_pct=100*known/len(subset) if applicable else None,
                    original_structured_rooms_n=sum(bool(r['rooms']) for r in subset) if field=='rooms_completed' else ''))
    return result


def main():
    data=latest(c.PROCESSED/'remaining_diversity_review')
    data_manifest=json.loads((data/'manifest.json').read_text(encoding='utf-8'))
    c.verify(data_manifest['output_sha256'],data)
    parts={s:c.read(data/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    assert len(parts['train'])==2214 and len(parts['validation'])==299
    original={r['record_key']:r for r in c.read(data/'all_listings_after_review.csv')}
    source=c.PROCESSED/'collection_source_review'
    paths=[Path(__file__),Path(rules.__file__),Path(c.__file__),data/'manifest.json',data/'all_listings_after_review.csv',
        data/'training_inputs/train.csv',data/'training_inputs/validation.csv',data/'training_inputs/reserved_holdout_registry.csv',
        source/'review_manifest.json',source/'parsed_evidence.json',source/'fetch_manifest.json']
    source_manifest=json.loads((source/'review_manifest.json').read_text(encoding='utf-8'))
    for name in ['parsed_evidence.json','fetch_manifest.json']:
        relative=(source/name).relative_to(c.BASE).as_posix()
        c.verify({relative:source_manifest['output_sha256'][relative]})
    parsed=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    protected={(data/p).relative_to(c.BASE).as_posix():sha for p,sha in data_manifest['output_sha256'].items()}
    for version in ['v3','v4','v5']:
        model=latest(c.PROCESSED/f'models_{version}_validation')
        m=json.loads((model/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['output_sha256'],model)
        protected.update({(model/p).relative_to(c.BASE).as_posix():sha for p,sha in m['output_sha256'].items()})
        paths.append(model/'manifest.json')
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    records,evidence=[],[]
    checked=set()
    for split,rows in parts.items():
        for row in rows:
            key=row['record_key'];e=parsed.get(key);f=fetch.get(key,{})
            body,state=admit_body(row,e,f)
            if body:
                path=source/'detail_cache'/f['file']
                if path not in checked:
                    if c.sha(path)!=f['sha256']:raise ValueError('Detail changed: '+key)
                    inputs[path.relative_to(c.BASE).as_posix()]=f['sha256'];checked.add(path)
                    if len(checked)%100==0:print(f'Verified {len(checked)} used body snapshots',flush=True)
            values,claims=rules.extract(row,original[key],body,e['detail_sha256'] if body else '')
            records.append(dict(record_key=key,model_split=split,source=row['source'],category=row['category'],
                **values,body_state=state,detail_sha256=e['detail_sha256'] if body else '',
                title_sha256=hashlib.sha256(original[key]['title'].encode()).hexdigest(),
                quality='literal_source_claim_not_verified_property_measurement'))
            for claim in claims:evidence.append(dict(record_key=key,model_split=split,**claim))
    fingerprint=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    target=OUT/'runs'/fingerprint
    if target.exists():
        c.verify(json.loads((target/'manifest.json').read_text(encoding='utf-8'))['output_sha256'],target)
        publish(target);print('Existing feature run verified: '+str(target));return
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    c.write_csv(stage/'features.csv',records,list(records[0]))
    c.write_csv(stage/'feature_evidence_DO_NOT_TRAIN.csv',evidence,list(evidence[0]))
    for split,rows in parts.items():c.write_csv(stage/(split+'.csv'),rows,c.FIELDS)
    reserved=c.read(data/'training_inputs/reserved_holdout_registry.csv')
    c.write_csv(stage/'reserved_holdout_registry.csv',reserved,list(reserved[0]))
    cov=coverage({r['record_key']:r for r in records},parts)
    c.write_csv(stage/'coverage.csv',cov,list(cov[0]))
    summary=dict(dataset_run=data.relative_to(c.BASE).as_posix(),train_n=2214,validation_n=299,reserved_eligible_n=684,
        feature_rows=len(records),evidence_rows=len(evidence),verified_used_html_snapshots=len(checked),
        body_states=dict(Counter(r['body_state'] for r in records)),
        conflict_rows=sum(bool(r['conflict_fields']) for r in records),coverage=cov,
        numeric_labels_changed=False,new_network_requests=0,geospatial_features=False,
        title_body_claims_not_verified_measurements=True,model_trained=False)
    c.write_json(stage/'summary.json',summary)
    (stage/'README.md').write_text('# Đặc trưng nội dung v6\n\n'
        '2.214 train và 299 validation giữ nguyên giá/diện tích/nhóm/reservation. Chỉ bổ sung lời rao có câu bằng chứng: '
        'phòng ngủ, tầng nhà hiện hữu, mặt tiền/kiệt và biệt thự/nhà cấp 4. Unknown giữ thiếu; '
        'số tầng tòa chung cư, phòng trọ, tương lai, gần đó, footer và mâu thuẫn không tự suy đoán. '
        'Phòng có cấu trúc được giữ khi mâu thuẫn với chữ; không ghi đè nhãn/đầu vào cũ.\n\n'
        f'Đã kiểm tra SHA-256 {len(checked)} HTML dùng cho mô tả; các tin khác chỉ có tiêu đề/trường cấu trúc hoặc không đủ bằng chứng. '
        'Không tải nguồn mới, không tọa độ/POI, không đưa nguyên văn/giá/ID vào feature matrix. '
        'Giá trong header chỉ kiểm tra khớp snapshot để dùng đúng mô tả, không là feature.\n\n'
        '[Feature sidecar](features.csv), [bằng chứng/quote](feature_evidence_DO_NOT_TRAIN.csv), '
        '[độ phủ](coverage.csv), [số liệu](summary.json). Feature sidecar phải join đúng record_key; '
        'ID chỉ phục vụ join, không vào X. Chưa train trong bước xuất này.\n',encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,output_sha256=c.outputs(stage)))
    stage.rename(target);publish(target)
    print(json.dumps({k:v for k,v in summary.items() if k!='coverage'},ensure_ascii=False,indent=2),flush=True)
    print(target,flush=True)


def publish(target):
    c.write_json(OUT/'latest.json',dict(run=target.relative_to(OUT).as_posix()))
    (OUT/'README.md').write_text('# Đặc trưng nội dung v6\n\n'
        f'[Bản hiện tại]({target.relative_to(OUT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':main()
