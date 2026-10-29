"""Offline per-ID adjudication and an untrained, group-separated data version."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import uuid

import property_snapshot_adjudication as rules
import property_evidence_claims as claims
import training_v3_common as data
from market_observations import canonical, timestamp
from verify_property_expansion import verify as verify_source

BASE=data.BASE
SOURCE=BASE/'processed/property_expansion_review/runs/e58bb9db7377e200'
PREPARED=BASE/'processed/training_next_preparation/runs/4fdb8ef79db89b16'
HISTORY=BASE/'processed/remaining_diversity_review/runs/1d45c8941172a52d/all_listings_after_review.csv'
PRIOR=BASE/'processed/apartment_extension_review/runs/c458ee98726ea981/all_decisions.csv'
OUT=BASE/'processed/property_source_adjudication'
PROTOCOL=BASE/'PROPERTY_ADJUDICATION_PROTOCOL.md'
MIN_FRESH_GROUPS=20

ACTIONS={
    'single_unit_price_area_not_corroborated_in_seller_description':'Cần giá tổng và diện tích của cùng một căn trong lời người bán; metadata lặp không đủ.',
    'description_area_conflict':'Làm rõ diện tích thông thủy/tim tường/ban công/dự án; không tự chọn số.',
    'title_area_conflict':'Đối chiếu diện tích trong tiêu đề, mô tả và trường cấu trúc.',
    'description_total_price_conflict':'Làm rõ giá tổng, giá chiết khấu, giá vay/trả trước và thuế phí.',
    'title_total_price_conflict':'Đối chiếu giá trong tiêu đề với giá tổng của cùng căn.',
    'bedroom_claims_conflict':'Làm rõ số phòng ngủ hiện tại, phòng phụ và phương án cải tạo.',
    'bedroom_pn_br_header_conflict':'PN/BR trong lời rao khác header; giữ số phòng thiếu, không tự đổi.',
    'multiple_units_or_inventory':'Cần tách rõ một căn với giá/diện tích tương ứng; không tách giỏ hàng tự động.',
    'partial_starting_or_booking_price':'Cần giá tổng và điều kiện thanh toán; không dùng số tiền đặt cọc/trả trước.',
    'source_date_outside_pilot_window':'Ngày nguồn ngoài 183 ngày của cổng pilot; đọc lại không làm mới ngày đăng.',
    'handover_or_construction_status_needs_review':'Cần phân biệt đang xây/chưa nhận nhà với đã bàn giao.',
    'title_unit_price_disagrees_with_total_area':'Làm rõ định nghĩa diện tích hoặc đơn giá, không dùng đơn giá làm X.',
    'nonstandard_apartment_review':'Cần xác định căn hộ ở hay condotel/dịch vụ và thời hạn sở hữu.',
    'apartment_not_supported_by_seller_description':'Cần lời rao xác định đúng một căn hộ, không suy từ sidebar.',
    'whole_building_scope_not_resolved':'Heading “tòa căn hộ” chưa chứng minh bán nguyên tòa; cần xác định một căn và điều kiện giá.',
}


def decoded_rows(path):
    rows=data.read(path)
    lists=['review_codes','exclusion_codes','group_review_codes']
    for row in rows:
        for field in lists:row[field]=json.loads(row[field])
        for field in ['price_million','area_sqm']:row[field]=float(row[field]) if row[field] else None
        row['rooms']=int(row['rooms']) if row['rooms'] else None
    return rows


def validate_inputs(source, prepared, history, prior, protocol):
    manifest=json.loads((source/'manifest.json').read_text(encoding='utf8'))
    data.verify(manifest['output_sha256'],source)
    for path,digest in {**manifest['input_sha256'],**manifest['protected_sha256']}.items():
        if data.sha(BASE/path)!=digest:raise ValueError('Archived input changed: '+path)
    paths=[source/'manifest.json',*[source/name for name in manifest['output_sha256']],
           prepared/'manifest.json',prepared/'train.csv',prepared/'reserved_holdout_registry.csv',
           history,prior,protocol,Path(__file__),Path(rules.__file__),Path(claims.__file__),BASE/'verify_property_expansion.py']
    ledger_paths=sorted((BASE/'processed/evaluation_ledger').glob('*.json'))
    # The evidence source includes its consumed-cohort ledger in the manifest.
    # Reject changed/additional ledgers until they are reviewed explicitly.
    recorded={str(Path(p).resolve()) for p in manifest['input_sha256'] if 'evaluation_ledger' in p}
    if {str(p.resolve()) for p in ledger_paths}!=recorded:raise ValueError('Evaluation ledger inventory differs')
    hashes={str(p.resolve()):data.sha(p) for p in paths+ledger_paths}
    return manifest,hashes


def assemble(rows, old_links, train, history, prior):
    keys={r['record_key'] for r in history+prior+rows}
    archived=rules.component_members(keys,old_links)
    for row in rows:
        if row['record_key'] not in archived.get(row['overlay_group'],set()):
            raise ValueError('Archived full group membership differs')
    historical_keys={r['record_key'] for r in history+prior}
    historical_groups={gid for gid,values in archived.items() if values&historical_keys}
    scanned=[rules.scan(row) for row in rows]
    extra=rules.explicit_unit_links(scanned)
    decisions=rules.adjudicate_groups(scanned,extra,{r['record_key'] for r in train},historical_keys,historical_groups)
    for row in decisions:
        row['next_action']=' '.join(dict.fromkeys(ACTIONS.get(c,'Đối chiếu nguồn cho cờ: '+c+'.') for c in row['remaining_codes']))
        if row['exclusions_v2']:row['next_action']='Tách khỏi tập một căn hộ; giữ snapshot để truy vết.'
        elif row['dataset_role']=='quarantine' and not row['next_action']:
            row['next_action']='Còn quan hệ nhóm/bảo vệ cần giải quyết: '+'; '.join(row['group_codes_v2'])
        elif not row['next_action']:row['next_action']='Giữ vai trò nhóm đã khóa, chưa phát hành X hoặc fit model.'
    return decisions,extra


def prepared_tables(decisions):
    observations=[];proofs=[];features=[]
    for row in decisions:
        key=row['record_key'];observed=row['observed_at'];sha=row['response_sha256']
        observations.append(dict(record_key=key,source=row['source'],observed_at=observed,response_sha256=sha,
            original_pipeline_group=row['original_pipeline_group'],adjudicated_group=row['adjudicated_group'],
            representative_key=row['representative_key'],dataset_role=row['dataset_role'],
            category=row['category'],price_million=row['price_million'],area_sqm=row['area_sqm'],
            location_feature=row['location_feature'],source_published_date=row['source_published_date'],
            source_age_days=row['source_age_days'],label_basis=row['label_basis'],training_allowed=False))
        for item in row['source_proofs']:
            proofs.append(dict(record_key=key,observed_at=observed,response_sha256=sha,**item))
        sources=[dict(kind='current_title',text=row['title'],sha256=sha),
                 dict(kind='current_seller_body',text=row['seller_text'],sha256=sha)]
        values,evidence=claims.extract(row['category'],sources,observed_year=timestamp(observed).year)
        for item in evidence:
            proofs.append(dict(record_key=key,observed_at=observed,response_sha256=sha,**item))
        bedrooms={p['value'] for p in row['source_proofs'] if p['rule']=='bedroom_literal' and p['status']=='current_claim'}
        if row['rooms'] is not None:bedrooms.add(row['rooms'])
        features.append(dict(record_key=key,observed_at=observed,response_sha256=sha,
            adjudicated_group=row['adjudicated_group'],dataset_role=row['dataset_role'],
            category=row['category'],area_sqm=row['area_sqm'],location_feature=row['location_feature'],
            rooms_claim=next(iter(bedrooms)) if len(bedrooms)==1 else '',
            **values,coordinates_verified=False,training_allowed=False))
    candidates=[r for r in observations if r['dataset_role'] in ['train_refresh_candidate','fresh_evaluation_reserved']]
    if len({r['adjudicated_group'] for r in candidates})!=len(candidates):raise ValueError('Repeated representative group')
    refresh={r['adjudicated_group'] for r in candidates if r['dataset_role']=='train_refresh_candidate'}
    fresh={r['adjudicated_group'] for r in candidates if r['dataset_role']=='fresh_evaluation_reserved'}
    if refresh&fresh:raise ValueError('Dataset role leakage')
    return observations,features,proofs,candidates


def artifacts():
    manifest,inputs=validate_inputs(SOURCE,PREPARED,HISTORY,PRIOR,PROTOCOL)
    rows=decoded_rows(SOURCE/'decisions_private_DO_NOT_TRAIN.csv')
    if len(rows)!=234 or sum(r['candidate_role']=='needs_source_review' for r in rows)!=222:
        raise ValueError('Unexpected source review cohort')
    train=data.read(PREPARED/'train.csv');history=data.read(HISTORY);prior=data.read(PRIOR)
    old_links=json.loads((SOURCE/'group_links.json').read_text(encoding='utf8'))
    decisions,extra=assemble(rows,old_links,train,history,prior)
    observations,features,proofs,candidates=prepared_tables(decisions)
    pending=[r for r in decisions if r['candidate_role']=='needs_source_review']
    fresh=[r for r in candidates if r['dataset_role']=='fresh_evaluation_reserved']
    refresh=[r for r in candidates if r['dataset_role']=='train_refresh_candidate']
    plan=dict(status='prepared_not_released',training_allowed=False,model_fit_allowed=False,
        reservation_scope='this_candidate_version_only; future experiments must consult this plan and the existing global ledger',
        reason='A separate experiment protocol and feature matrix must be frozen before any fit or scoring.',
        prospective_evaluation_minimum=MIN_FRESH_GROUPS,fresh_group_count=len(fresh),
        collection_size_gate=len(fresh)>=MIN_FRESH_GROUPS,
        minimum_is_not_statistical_guarantee=True,
        train_refresh_members=[dict(record_key=r['record_key'],group=r['adjudicated_group'],response_sha256=r['response_sha256']) for r in refresh],
        fresh_reserved_members=[dict(record_key=r['record_key'],group=r['adjudicated_group'],response_sha256=r['response_sha256']) for r in fresh],
        forbid_old_label_new_description_join=True,never_use_price_or_unit_price_as_feature=True,
        consumed_cohorts_not_scored=True,automatic_model_promotion=False)
    summary=dict(total_snapshots=len(decisions),previous_pending=len(pending),reviewed_pending=len(pending),
        all_outcomes=dict(Counter(r['dataset_role'] for r in decisions)),
        pending_outcomes=dict(Counter(r['dataset_role'] for r in pending)),
        source_decisions=dict(Counter(r['source_decision'] for r in decisions)),
        old_candidates_requarantined=sum(r['candidate_role']!='needs_source_review' and r['dataset_role'] not in ['train_refresh_candidate','fresh_evaluation_reserved'] for r in decisions),
        resolved_flag_counts=dict(Counter(p['code'] for r in decisions for p in r['resolved_codes_v2'])),
        remaining_flag_counts=dict(Counter(c for r in decisions for c in r['remaining_codes'])),
        new_explicit_unit_links=len(extra),train_refresh_groups=len(refresh),fresh_reserved_groups=len(fresh),
        minimum_fresh_groups=MIN_FRESH_GROUPS,collection_size_gate=plan['collection_size_gate'],
        clean_existing_train=len(train),model_fits=0,model_predictions=0,production_model_changed=False,
        old_cohorts_changed=False,network_requests=0,geo_features_ready=0,
        limitation='Offline rule-assisted source review; unresolved claims stay missing/quarantined. Candidate groups are not physically verified assets.')
    sets=dict(all_decisions=decisions,pending_222_decisions=pending,
        current_observations_DO_NOT_TRAIN=observations,features_DO_NOT_TRAIN=features,
        evidence_private=proofs,candidate_groups_DO_NOT_TRAIN=candidates,
        train_refresh_DO_NOT_TRAIN=refresh,fresh_evaluation_RESERVED_DO_NOT_TRAIN=fresh,
        excluded=[r for r in decisions if r['dataset_role']=='excluded'],
        needs_evidence=[r for r in decisions if r['dataset_role']=='quarantine'],
        suppressed_duplicates=[r for r in decisions if r['dataset_role']=='suppressed_duplicate'])
    return sets,extra,summary,plan,inputs,manifest['protected_sha256']


def scalar(value):
    return json.dumps(value,ensure_ascii=False,sort_keys=True) if isinstance(value,(list,dict)) else '' if value is None else str(value)


def csv_table(rows):
    fields=list(dict.fromkeys(k for row in rows for k in row)) or ['record_key','dataset_role']
    return fields,[{k:scalar(row.get(k)) for k in fields} for row in rows]


def schema():
    return dict(version='property_current_snapshot_candidates_v1',status='DO_NOT_TRAIN',
        allowed_predictor_candidates=['area_sqm','location_feature','rooms_claim',*claims.FIELDS],
        metadata_only=['record_key','observed_at','response_sha256','adjudicated_group','dataset_role','category','conflict_fields'],
        target='price_million from same current response; asking price, not transaction price',
        forbidden_predictors=['price_million','unit_price','description','title','detail_url','source_listing_id'],
        vocab_fit='training partition only after independent experiment protocol',
        feature_missingness='empty means unknown or conflicting, never synthetic zero',
        geospatial='No verified coordinates or distances are released')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    verify_source(SOURCE)
    sets,links,summary,plan,inputs,protected=artifacts()
    run_id=hashlib.sha256(canonical(inputs).encode()).hexdigest()[:16]
    target=OUT/'runs'/run_id
    summary['run_id']=run_id
    if target.exists():
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf8'))
        if manifest['input_sha256']!=inputs or manifest['protected_sha256']!=protected:raise ValueError('Manifest identity changed')
        data.verify(manifest['output_sha256'],target)
        if data.outputs(target)!=manifest['output_sha256']:raise ValueError('Output inventory differs')
        for name,rows in sets.items():
            _,expected=csv_table(rows)
            if data.read(target/(name+'.csv'))!=expected:raise ValueError('Decision/quote replay differs: '+name)
        for name,value in [('summary',summary),('experiment_reservation',plan),('additional_group_links',links),('schema',schema())]:
            if json.loads((target/(name+'.json')).read_text(encoding='utf8'))!=value:raise ValueError('JSON replay differs: '+name)
        print(json.dumps(dict(verified=True,**summary),ensure_ascii=False,indent=2));return
    if args.verify:raise ValueError('Build matching version before verify')
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    for name,rows in sets.items():
        fields,table=csv_table(rows);data.write_csv(stage/(name+'.csv'),table,fields)
    for name,value in [('summary',summary),('experiment_reservation',plan),('additional_group_links',links)]:
        data.write_json(stage/(name+'.json'),value)
    data.write_json(stage/'schema.json',schema())
    (stage/'README.md').write_text('# Rà soát nguồn và dữ liệu thử nghiệm chưa huấn luyện\n\n'
        f"Đã xử lý {summary['reviewed_pending']}/222 tin chờ và kiểm tra lại toàn bộ 234 snapshot.\n\n"
        f"Kết quả: {summary['all_outcomes']}. Nhóm train đọc lại: {len(sets['train_refresh_DO_NOT_TRAIN'])}; "
        f"nhóm mới giữ ngoài train: {len(sets['fresh_evaluation_RESERVED_DO_NOT_TRAIN'])}.\n\n"
        'Mỗi kết luận giữ bằng chứng/giá/diện tích/đặc trưng cùng phản hồi. Các cờ không giải quyết vẫn được giữ. '
        'Đây là rà soát hỗ trợ bằng quy tắc trên dữ liệu nguồn, chưa xác minh thực địa hoặc giao dịch. '
        'Không nối mô tả hiện tại vào nhãn cũ, không tăng 2.213 train, không dùng cohort đã chấm. '
        'Mọi CSV ứng viên vẫn DO_NOT_TRAIN. Xem experiment_reservation.json và schema.json.\n',encoding='utf8')
    for path,digest in {**inputs,**protected}.items():
        if data.sha(BASE/path)!=digest:raise ValueError('Input/protected file changed while building')
    data.write_json(stage/'manifest.json',dict(input_sha256=inputs,protected_sha256=protected,output_sha256=data.outputs(stage)))
    stage.rename(target);data.write_json(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps(summary,ensure_ascii=False,indent=2));print(target)


if __name__=='__main__':main()
