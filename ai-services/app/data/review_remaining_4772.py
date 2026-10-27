"""Recheck all 4772 pending IDs; dates are metadata, never an XGBoost gate.

Separate immutable run, no edits to raw data, earlier decisions, v3 or holdouts.
Retain every non-date quality gate and all frozen duplicate memberships/splits.
"""
import hashlib
import json
import math
import uuid
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import training_v3_common as common
from training_v3_common import BASE, read, sha, write_csv, write_json, outputs

ROOT = BASE / 'processed/remaining_4772_review'
DATE_CODES = {'older_than_183_days', 'listing_date_unavailable'}
LINK = 'linked_group_member_not_eligible'
DOC = 'https://xgboost.readthedocs.io/en/stable/python/python_intro.html'


def codes(value):
    return set(filter(None, str(value or '').split(';')))


def number(value):
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (TypeError, ValueError):
        return None


def reconsider(originals):
    """Only waive date gates; resolve linked-member blocking within frozen groups."""
    rows = [dict(r) for r in originals]
    groups = defaultdict(list)
    for r in rows:
        r.update(previous_pipeline_status=r['pipeline_status'],
                 previous_pipeline_review_codes=r['pipeline_review_codes'],
                 waived_date_codes=';'.join(sorted(codes(r['pipeline_review_codes']) & DATE_CODES)),
                 date_missing=not bool(r['displayed_date']),
                 older_than_183_days='older_than_183_days' in codes(r['pipeline_review_codes']))
        if r['pipeline_status']=='needs_review':
            flags = codes(r['pipeline_review_codes']) - DATE_CODES - {LINK}
            p, a = number(r['price_million']), number(r['area_sqm'])
            if p is None or a is None or p<=0 or a<=0:
                flags.add('invalid_numeric_target_or_area')
            if r['category'] not in common.CATEGORIES:
                flags.add('outside_model_property_types')
            r['pipeline_review_codes']=';'.join(sorted(flags))
            r['pipeline_status']='needs_review' if flags else 'eligible'
        groups[r['pipeline_group']].append(r)
    for members in groups.values():
        issues=set()
        numeric=[r for r in members if number(r['price_million']) and number(r['area_sqm'])]
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            values=[float(r[field]) for r in numeric]
            if values and (max(values)-min(values))/max(values)>tolerance:
                issues.add('group_'+field+'_conflict')
        if len({r['category'] for r in members})>1:
            issues.add('group_category_conflict')
        if len({r['district'] for r in members if r['district']})>1:
            issues.add('group_historical_location_conflict')
        if issues:
            for r in members:
                if r['pipeline_status']=='eligible' and r['previous_pipeline_status']!='eligible':
                    r.update(pipeline_status='needs_review',pipeline_review_codes=';'.join(sorted(codes(r['pipeline_review_codes'])|issues)))
        # Already suppressed duplicate observations stay excluded, but do not
        # count as unresolved asset evidence. Genuine excluded assets do.
        blocked = any(r['pipeline_status']=='needs_review' or
            (r['pipeline_status']=='excluded' and codes(r['exclusion_codes'])!={'suspected_duplicate_suppressed'})
            for r in members)
        contenders = [r for r in members if r['pipeline_status']=='eligible']
        if blocked and len(members)>1:
            for r in contenders:
                if r['previous_pipeline_status']=='eligible':
                    # Existing eligible memberships/splits are frozen; never
                    # reinterpret their already adjudicated suppression here.
                    continue
                r.update(pipeline_status='needs_review',pipeline_review_codes=';'.join(sorted(codes(r['pipeline_review_codes'])|{LINK})))
            contenders=[r for r in contenders if r['pipeline_status']=='eligible']
        if contenders:
            prior=[r for r in contenders if r['previous_pipeline_status']=='eligible']
            winner = (prior[0] if prior else max(contenders,key=lambda r:(bool(r['review_decision']),
                bool(r['displayed_date']),r['detail_fetched']=='True',r['collected_at'],r['record_key'])))
            for r in contenders:
                r['representative_key']=winner['record_key']
                if r is not winner:
                    r.update(pipeline_status='excluded',exclusion_codes='suspected_duplicate_suppressed')
        for r in members:
            r['training_allowed']=str(r['pipeline_status']=='eligible' and r['assigned_split']=='train'
                                      and str(r['protected_holdout'])=='False')
    return rows


def primary_issue(row, evidence, fetch, decision):
    if row['pipeline_status']=='eligible':
        return 'eligible_after_date_policy_change'
    if row['pipeline_status']=='excluded':
        return 'duplicate_representative_suppressed'
    if fetch.get('state')=='not_requested_source_access_blocked':
        return 'source_blocked_not_individually_requested'
    if fetch and fetch.get('http_status') not in (None,200):
        return 'detail_http_error'
    if evidence and not evidence.get('identity_verified'):
        return 'source_identity_unverified'
    flags=codes(row['pipeline_review_codes'])|codes(decision.get('review_codes',''))
    if any(c.startswith('group_') or c==LINK for c in flags):
        return 'duplicate_group_unresolved'
    if flags & {'partial_starting_or_booking_title','transaction_or_partial_price_title',
        'partial_or_starting_price_context','multiple_assets_or_inventory_context','multiple_properties_in_title',
        'special_or_whole_building','special_or_whole_building_not_resolved','mixed_land_and_building_context',
        'project_marketing_requires_specific_asset','description_price_or_area_range'}:
        return 'financial_multiple_or_special_asset_context'
    if flags & {'invalid_numeric_target_or_area','missing_or_invalid_price','missing_or_invalid_area',
        'numeric_threshold','unit_price_threshold','total_price_threshold','area_threshold',
        'description_area_needs_review','description_total_price_needs_review','description_dimensions_need_review',
        'structured_and_displayed_price_conflict','title_price_conflict','source_structure_incomplete'}:
        return 'price_area_or_structure_unresolved'
    if any('category' in c for c in flags):
        return 'property_category_unresolved'
    if flags & {'geography_not_supported','sale_not_supported','sale_transaction_unverified',
                'outside_or_unverified_expanded_danang','current_province_not_verified'}:
        return 'geography_or_sale_unverified'
    return 'prior_content_review_still_unresolved'


def verify_inputs(hashes):
    total=sum((BASE/p).stat().st_size for p in hashes)
    print(f'Verifying {len(hashes)} frozen inputs ({total/1e9:.2f} GB), one pass...',flush=True)
    checked={}
    for index,(rel,expected) in enumerate(sorted(hashes.items()),1):
        path=BASE/rel
        stat=path.stat()
        actual=sha(path)
        if actual!=expected:
            raise ValueError('Frozen input changed: '+rel)
        checked[rel]=(stat.st_size,stat.st_mtime_ns)
        if index%250==0:
            print(f'Integrity {index}/{len(hashes)}',flush=True)
    ROOT.mkdir(parents=True,exist_ok=True)
    write_json(ROOT/'input_integrity.json',dict(verified_at_utc=datetime.now(timezone.utc).isoformat(),
        input_sha256=hashes,verified_files=len(hashes),verified_bytes=total,
        size_mtime_after_verification=checked))
    return checked


def ensure_stats(stats):
    for rel,expected in stats.items():
        stat=(BASE/rel).stat()
        if (stat.st_size,stat.st_mtime_ns)!=expected:
            raise ValueError('Input changed during review: '+rel)


def validate_optional_dates(parts,reserved_groups):
    ids,groups=set(),set(reserved_groups)
    for split in ['train','validation']:
        records=parts[split]
        keys={r['record_key'] for r in records}
        current={r['pipeline_group'] for r in records}
        if len(keys)!=len(records) or len(current)!=len(records) or keys & ids or current & groups:
            raise ValueError('Repeated ID/property group across cohorts')
        for row in records:
            reservation=codes(row['reserved_splits'])
            if row['model_split']!=split or row['category'] not in common.CATEGORIES:
                raise ValueError('Unexpected split/category')
            if split=='train' and reservation & {'validation','test'}:
                raise ValueError('Holdout in train')
            if split=='validation' and ('validation' not in reservation or 'test' in reservation):
                raise ValueError('Test reservation in validation')
            if not row['geographic_scope_status'].startswith('accepted_') or not row['location_feature']:
                raise ValueError('Missing geography evidence')
            if any(number(row[field]) is None or number(row[field])<=0 for field in ['price_million','area_sqm']):
                raise ValueError('Invalid numeric label/area')
        ids.update(keys);groups.update(current)


def build_training(rows, stage):
    import numpy as np
    import xgboost as xgb
    old=BASE/'processed/training_v3'
    old=old/json.loads((old/'latest.json').read_text())['run']
    validation_ids={r['record_key'] for r in read(old/'validation.csv')}
    parts={'train':[],'validation':[]}
    reserved=[]
    for row in rows:
        if row['pipeline_status']!='eligible':
            continue
        if row['record_key'] in validation_ids:
            parts['validation'].append(common.model_row(row,'validation'))
        elif row['training_allowed']=='True':
            if codes(row['reserved_splits']) & {'validation','test'} or row['protected_holdout']!='False':
                raise ValueError('Reserved group entered train')
            parts['train'].append(common.model_row(row,'train'))
        else:
            reserved.append({k:row[k] for k in ['record_key','source','category','pipeline_group',
                                               'reserved_splits','assigned_split','protected_holdout']})
    if {r['record_key'] for r in parts['validation']}!=validation_ids:
        raise ValueError('Frozen validation membership changed')
    validate_optional_dates(parts,{r['pipeline_group'] for r in reserved})
    folder=stage/'training_inputs'
    folder.mkdir()
    for split,records in parts.items():
        write_csv(folder/(split+'.csv'),records,common.FIELDS)
    write_csv(folder/'reserved_holdout_registry.csv',reserved,list(reserved[0]))
    matrices=[]
    for index,category in enumerate(common.CATEGORIES,1):
        tr=[r for r in parts['train'] if r['category']==category]
        spec=common.schema(tr)
        write_json(folder/f'category_{index}_schema.json',dict(spec,category=category))
        for split,records in parts.items():
            subset=[r for r in records if r['category']==category]
            matrix=common.encode(subset,spec)
            label=np.log(np.asarray([float(r['price_million']) for r in subset],dtype=np.float64))
            # XGBoost accepts NaN feature values (e.g. missing rooms), but not
            # infinite features or missing/infinite regression labels.
            if np.isinf(matrix).any() or not np.isfinite(label).all():
                raise ValueError('Nonfinite matrix/target')
            dm=xgb.DMatrix(matrix,label=label,feature_names=spec['feature_names'])
            dm.save_binary(folder/f'category_{index}_{split}.buffer')
            matrices.append(dict(category=category,split=split,rows=dm.num_row(),columns=dm.num_col(),
                label_transform='natural_log_total_asking_price_million',schema_fit_on='train_only'))
    write_json(folder/'matrix_validation.json',dict(xgboost_version=xgb.__version__,matrices=matrices,
        models_trained=False,test_scored=False,validation_is_fixed_v3_development_set=True))
    return dict(train=len(parts['train']),validation=len(parts['validation']),reserved_eligible=len(reserved),
        by_category={s:dict(Counter(r['category'] for r in records)) for s,records in parts.items()},
        matrix_validation_passed=True,model_trained=False)


def run():
    source_root=BASE/'processed/collection_pipeline'
    source=source_root/json.loads((source_root/'latest.json').read_text())['run']
    pm=json.loads((source/'manifest.json').read_text())
    frozen=dict(pm['input_sha256'])
    frozen.update(pm['output_sha256'])
    # Some old pipeline manifests use BASE-relative outputs; verify exactly that contract.
    if any(not (BASE/p).exists() for p in pm['output_sha256']):
        frozen=dict(pm['input_sha256'])
        frozen.update({(source/p).relative_to(BASE).as_posix():v for p,v in pm['output_sha256'].items()})
    geo_guard=BASE/'processed/geospatial_v1/address_pilot/input_manifest.json'
    frozen.update(json.loads(geo_guard.read_text())['protected_sha256'])
    for path in [Path(__file__),Path(common.__file__),source/'manifest.json',geo_guard]:
        frozen[path.relative_to(BASE).as_posix()]=sha(path)
    checked=verify_inputs(frozen)
    originals=read(source/'all_listings.csv')
    pending={r['record_key'] for r in originals if r['pipeline_status']=='needs_review'}
    if len(pending)!=4772 or len(originals)!=8509 or len({r['record_key'] for r in originals})!=8509:
        raise ValueError('Expected frozen cohort of 4772 pending / 8509 unique IDs')
    rows=reconsider(originals)
    old={r['record_key']:r for r in originals}
    data_root=BASE/'processed/collection_source_review'
    evidence=json.loads((data_root/'parsed_evidence.json').read_text())
    fetch=json.loads((data_root/'fetch_manifest.json').read_text())
    decisions={r['record_key']:r for r in read(data_root/'review_decisions.csv')}
    key=hashlib.sha256(json.dumps(dict(inputs=frozen,policy='dates_optional_v1_fixed_validation'),sort_keys=True).encode()).hexdigest()[:16]
    target=ROOT/'runs'/key
    if target.exists():
        common.verify(json.loads((target/'manifest.json').read_text())['output_sha256'],target)
        write_json(ROOT/'latest.json',dict(run=target.relative_to(ROOT).as_posix()))
        print('Existing review verified: '+str(target));return target
    stage=ROOT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    reviewed=[]
    for r in rows:
        if r['record_key'] not in pending:
            continue
        e=evidence.get(r['record_key'],{})
        f=fetch.get(r['record_key'],{})
        d=decisions.get(r['record_key'],{})
        issue=primary_issue(r,e,f,d)
        record={k:r[k] for k in ['record_key','source','category','price_million','area_sqm','address_raw',
            'detail_url','displayed_date','date_basis','age_days','date_missing','older_than_183_days',
            'waived_date_codes','previous_pipeline_status','previous_pipeline_review_codes','pipeline_status',
            'pipeline_review_codes','exclusion_codes','pipeline_group','reserved_splits','assigned_split',
            'protected_holdout','training_allowed','input_file','input_row']}
        record.update(primary_issue=issue,source_review_codes=d.get('review_codes',''),
            cached_detail_state=f.get('state','not_in_source_batch'),cached_http_status=f.get('http_status',''),
            cached_detail_identity_verified=bool(e.get('identity_verified')),
            description_available=bool(e.get('identity_verified') and e.get('description')),
            cached_detail_sha256=e.get('detail_sha256',''),
            evidence_ref='processed/collection_source_review/parsed_evidence.json#'+r['record_key'] if e else '',
            independent_transaction_verified=False)
        if e.get('identity_verified'):
            if e.get('record_key')!=r['record_key'] or e.get('detail_sha256')!=f.get('sha256'):
                raise ValueError('Source evidence join mismatch: '+r['record_key'])
        reviewed.append(record)
    write_csv(stage/'reviewed_4772.csv',reviewed,list(reviewed[0]))
    write_csv(stage/'all_listings_after_review.csv',rows,list(rows[0]))
    for status in ['eligible','needs_review','excluded']:
        subset=[r for r in rows if r['pipeline_status']==status]
        write_csv(stage/(status+'.csv'),subset,list(rows[0]))
    for issue in sorted({r['primary_issue'] for r in reviewed}):
        folder=stage/'by_issue';folder.mkdir(exist_ok=True)
        write_csv(folder/(issue+'.csv'),[r for r in reviewed if r['primary_issue']==issue],list(reviewed[0]))
    training=build_training(rows,stage)
    changed=[r for r in reviewed if r['pipeline_status']!='needs_review']
    write_csv(stage/'status_changes.csv',changed,list(reviewed[0]))
    summary=dict(reviewed_at_local='2026-10-13',source_rules_as_of='2026-10-11',reviewed_pending=4772,
        total_unique_source_ids=8509,previous_statuses=dict(Counter(r['pipeline_status'] for r in originals)),
        statuses_after_review=dict(Counter(r['pipeline_status'] for r in rows)),
        pending_batch_outcomes=dict(Counter(r['pipeline_status'] for r in reviewed)),
        primary_issues=dict(Counter(r['primary_issue'] for r in reviewed)),
        by_source={s:dict(Counter(r['pipeline_status'] for r in reviewed if r['source']==s)) for s in sorted({r['source'] for r in reviewed})},
        pipeline_issue_counts=dict(Counter(c for r in reviewed for c in codes(r['pipeline_review_codes']))),
        evidence_coverage=dict(identity_verified=sum(r['cached_detail_identity_verified'] for r in reviewed),
            description_available=sum(r['description_available'] for r in reviewed),
            access_states=dict(Counter(r['cached_detail_state'] for r in reviewed))),
        rows_with_waived_date_gates=sum(bool(r['waived_date_codes']) for r in reviewed),
        training_inputs=training,numeric_labels_changed=0,category_labels_changed=0,
        old_v3_modified=False,source_manual_review_claimed=False,new_network_requests=0)
    write_json(stage/'summary.json',summary)
    before_eligible={r['record_key'] for r in originals if r['pipeline_status']=='eligible'}
    assert before_eligible <= {r['record_key'] for r in rows if r['pipeline_status']=='eligible'}
    for r in rows:
        prior=old[r['record_key']]
        for field in ['price_million','area_sqm','category','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert r[field]==prior[field],(r['record_key'],field)
    assert not any(r['training_allowed']=='True' and r['protected_holdout']=='True' for r in rows)
    assert len(reviewed)==len({r['record_key'] for r in reviewed})==4772
    lines=['# Rà soát toàn bộ 4.772 tin — ngày đăng là metadata','',
        'Đối chiếu ngày 13/10/2026 với collection đã chốt ngày 11/10/2026. Đã kiểm tra tất cả 4.772 ID đang chờ, '
        'dữ liệu nguồn và bằng chứng/cache đã lưu. Đây là rà soát bằng quy tắc, không khẳng định đã xác minh thủ công từng tài sản.','',
        '## Chính sách theo yêu cầu mới','',
        'Bỏ hai điều kiện loại tin `older_than_183_days` và `listing_date_unavailable`. XGBoost không yêu cầu ngày đăng '
        'hay tuổi tin tối đa 183 ngày; đây là ngưỡng trước đây của SmartProp. Ngày cũ/thiếu ngày vẫn được giữ trong metadata, '
        'không thay bằng ngày cào và không tự coi giá cũ là giá thị trường hiện tại. '
        f'[Tài liệu đầu vào XGBoost]({DOC}).','',
        'Giữ mọi điều kiện khác về giá/diện tích, danh mục, giao dịch/địa bàn, nội dung nhiều tài sản/giá trả trước, '
        'quyết định nguồn chưa giải quyết và trùng nhóm. Các ngưỡng giá/diện tích là quy tắc chất lượng SmartProp, '
        'không phải giới hạn bắt buộc của thư viện XGBoost. Không sửa nhãn theo mô hình.','',
        '| Kết quả trong 4.772 tin | Số ID |','|---|---:|']
    lines += [f'| {s} | {n:,} |' for s,n in summary['pending_batch_outcomes'].items()]
    lines += ['', '| Lý do/kết quả chính, không chồng lặp | Số ID |','|---|---:|']
    lines += [f'| {s} | {n:,} |' for s,n in summary['primary_issues'].items()]
    lines += ['',f'Toàn bộ collection sau chính sách mới: `{summary["statuses_after_review"]}`. '
        'Nhóm trùng giữ một đại diện; nhóm còn thành viên có vấn đề giữ ngoài train. Không gán lại nhóm hay split lịch sử.','',
        '## Đầu vào XGBoost đã kiểm tra','',
        f'Train **{training["train"]:,}**; validation **{training["validation"]:,}** giữ đúng 299 ID v3; '
        f'eligible giữ riêng **{training["reserved_eligible"]:,}**. Mọi nhóm validation/test cũ tiếp tục được giữ riêng. '
        'Các eligible holdout mới không nhập vào validation phát triển 299 dòng để giữ phép so sánh.','',
        'Đã tạo DMatrix thật bằng XGBoost cài trên máy, kiểm tra ma trận/nhãn hữu hạn và lưu buffer theo từng loại tài sản. '
        'Mã hóa diện tích, khu vực, phường, số phòng và cờ thiếu; vocabulary chỉ fit trên train. '
        'Giá mục tiêu là log của tổng giá rao (triệu VND), không phải giá giao dịch. Không dùng tiêu đề, mô tả, đơn giá hoặc ID làm feature. '
        '**Chưa huấn luyện model mới; model v3 giữ nguyên.**','',
        '## Tệp','',
        '- [Tất cả 4.772 kết quả theo ID](reviewed_4772.csv), [các chuyển trạng thái](status_changes.csv).',
        '- [Collection sau rà soát](all_listings_after_review.csv), [eligible](eligible.csv), [còn chờ](needs_review.csv), [excluded](excluded.csv).',
        '- [Train](training_inputs/train.csv), [validation cố định](training_inputs/validation.csv), '
        '[registry giữ riêng](training_inputs/reserved_holdout_registry.csv), [kiểm tra DMatrix](training_inputs/matrix_validation.json).',
        '- [Số liệu và lý do](summary.json); thư mục `by_issue` chứa từng hàng chờ theo lý do chính.','',
        '1.798 URL Chợ Tốt chưa được yêu cầu từng tin do nguồn bị chặn trước đó; không trình bày thành 1.798 lỗi HTTP riêng. '
        'HTTP 200/khớp ID không tự chứng minh nhãn hoặc vị trí đúng. Chưa có dữ liệu vị trí cấp nhà mới; không thêm tâm đường vào feature.','',
        'Bộ mới thay đổi phân bố thời gian/nguồn so với v3; dùng chung validation để so sánh bước đầu, vẫn cần kiểm chứng theo thời gian '
        'hoặc tập mới độc lập. Validation phát triển đã dùng trước đây, không phải benchmark mới. '
        'Tin không ngày không thể tự gán thứ tự thời gian để đánh giá dự đoán tương lai.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    ensure_stats(checked)
    write_json(stage/'manifest.json',dict(input_sha256=frozen,output_sha256=outputs(stage),complete=True,
        policy='dates_optional_v1_fixed_validation',raw_labels_splits_v3_unchanged=True))
    stage.rename(target)
    ROOT.mkdir(exist_ok=True)
    write_json(ROOT/'latest.json',dict(run=target.relative_to(ROOT).as_posix()))
    (ROOT/'README.md').write_text('# Rà soát 4.772 tin còn lại\n\n'
        f'[Báo cáo và đầu vào XGBoost mới]({target.relative_to(ROOT).as_posix()}/README.md).\n',encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print(target,flush=True)
    return target


if __name__=='__main__':
    run()
