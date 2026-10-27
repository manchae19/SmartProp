"""Review every remaining ID, export a richer train set without touching holdouts."""
import hashlib
import json
import uuid
from collections import Counter,defaultdict
from pathlib import Path

import training_v3_common as c
import filter_all_collected as pipeline
import filter_remaining_3752 as old_filter
import remaining_diversity_rules as rules

prior=old_filter.prior
ROOT=c.PROCESSED/'remaining_diversity_review'


def latest(root):
    return root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']


def coverage(rows):
    return {field:dict(Counter(r[field] or '(missing)' for r in rows))
            for field in ['source','category','location_feature','date_basis']}


def guard_cross_group_content(rows,original,evidence):
    signatures=defaultdict(list)
    for row in rows:
        signature=rules.description_signature(evidence.get(row['record_key']))
        if signature:
            signatures[signature].append(row)
    links=[]
    for members in signatures.values():
        if len({r['pipeline_group'] for r in members})<2:
            continue
        for row in members:
            if row['pipeline_status']!='eligible' or original[row['record_key']]['pipeline_status']!='needs_review':
                continue
            others=[r for r in members if r['pipeline_group']!=row['pipeline_group']]
            # Same long prose is a candidate duplicate even if its numeric or
            # location attributes differ; never reconcile those by guessing.
            if others:
                row.update(pipeline_status='needs_review',pipeline_review_codes=';'.join(sorted(
                    prior.codes(row['pipeline_review_codes'])|{'cross_group_long_description_match'})))
                for other in others:
                    links.append(dict(record_key=row['record_key'],other_record_key=other['record_key'],
                        group=row['pipeline_group'],other_group=other['pipeline_group'],
                        rule='exact_long_seller_prose_without_ordinal_or_header_echo',
                        other_reserved_splits=other['reserved_splits']))
    return links


def main():
    old=latest(old_filter.ROOT)
    manifest=json.loads((old/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['output_sha256'],old)
    proof=json.loads((old_filter.ROOT/'verification.json').read_text(encoding='utf-8'))
    if not proof['verified'] or proof['run']!=old.relative_to(old_filter.ROOT).as_posix():
        raise ValueError('Previous data verification does not match input run')
    originals=c.read(old/'all_listings_after_review.csv')
    original={r['record_key']:r for r in originals}
    pending={k for k,r in original.items() if r['pipeline_status']=='needs_review'}
    if len(original)!=8509 or len(pending)!=3605:
        raise ValueError('Expected verified 8509 IDs with 3605 pending')
    source=c.PROCESSED/'collection_source_review'
    es=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    paths=[Path(__file__),Path(rules.__file__),Path(rules.previous.__file__),Path(rules.previous.previous.__file__),
           Path(rules.previous.previous.audit.__file__),Path(old_filter.__file__),Path(prior.__file__),
           Path(c.__file__),Path(pipeline.__file__),old/'manifest.json',old/'all_listings_after_review.csv',
           old/'training_inputs/train.csv',old/'training_inputs/validation.csv',old_filter.ROOT/'verification.json',
           source/'parsed_evidence.json',source/'fetch_manifest.json']
    protected={}
    for name in ['training_v3','models_v3_validation','models_v4_validation']:
        directory=latest(c.PROCESSED/name)
        m=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        c.verify(m['output_sha256'],directory)
        paths.append(directory/'manifest.json')
        protected.update({(directory/p).relative_to(c.BASE).as_posix():v for p,v in m['output_sha256'].items()})
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    # Validate reused direct evidence against the immutable previous manifest.
    for path,sha in inputs.items():
        if path in manifest['input_sha256'] and sha!=manifest['input_sha256'][path]:
            raise ValueError('Frozen direct input changed: '+path)
    rows=[dict(r) for r in originals]
    decisions=[]
    checked=set()
    allowed=set(pipeline.DETAIL_RESOLVABLE_CODES)|{'saved_source_review_pending','category_title_inferred'}
    for row in rows:
        key=row['record_key']
        if key not in pending:
            continue
        e=es.get(key)
        result=rules.evaluate(row,e) if e else dict(decision='pending',category=row['category'],remaining_codes=['source_evidence_unavailable'],resolutions=[])
        before=prior.codes(row['pipeline_review_codes'])
        applied=False
        sale=rules.sale_with_rental_context(row,e,result) if e else None
        if result['decision'] in ('keep','correct'):
            f=fetch.get(key,{})
            if not e['identity_verified'] or not e['structure_verified'] or f.get('http_status')!=200 or e['detail_sha256']!=f.get('sha256'):
                raise ValueError('Identity/structure/hash mismatch: '+key)
            path=source/'detail_cache'/f['file']
            if path not in checked:
                if c.sha(path)!=f['sha256']:
                    raise ValueError('HTML changed: '+key)
                checked.add(path)
                inputs[path.relative_to(c.BASE).as_posix()]=f['sha256']
            flags=before-allowed-{prior.LINK}
            if any(x['rule'] in ('fractional_billion_matches_explicit_header','complete_billion_plus_three_digit_million') for x in result['resolutions']):
                flags.discard('title_price_conflict')
            if sale:
                flags.discard('transaction_or_partial_price_title')
                result['resolutions'].append(sale)
            if result['category']!='Căn hộ chung cư':
                flags.discard('apartment_price_priority')
            p,a=prior.number(row['price_million']),prior.number(row['area_sqm'])
            if p is None or a is None or p<=0 or a<=0:
                flags.add('invalid_numeric_target_or_area')
            elif not(100<=p<=200000 and 20<=a<=1000 and 2<=p/a<=300):
                flags.add('numeric_threshold')
            if result['category']=='Căn hộ chung cư' and p and a and (p<500 or not 15<=p/a<=150):
                flags.add('apartment_price_priority')
            if result['category'] not in c.CATEGORIES:
                flags.add('outside_model_property_types')
            row.update(category=result['category'],category_basis='source_literal_content_diversity_v3',
                resolved_review_codes=';'.join(sorted(prior.codes(row['resolved_review_codes'])|(before-flags))),
                pipeline_review_codes=';'.join(sorted(flags)),pipeline_status='needs_review' if flags else 'eligible',
                review_decision=result['decision'],review_decision_file='remaining_diversity_review',
                review_evidence_sha256=e['detail_sha256'],review_note='Literal source-content resolutions; see reviewed_pending.csv; not verified transaction',
                label_quality='source_literal_content_review_not_independent_transaction_verification')
            applied=True
        decisions.append(dict(record_key=key,source=row['source'],source_decision=result['decision'],
            source_identity_verified=bool(e and e.get('identity_verified')),source_decision_applied=applied,
            remaining_source_codes=';'.join(result['remaining_codes']),
            resolution_json=json.dumps(result['resolutions'],ensure_ascii=False),
            evidence_sha256=(e or {}).get('detail_sha256',''),cache_file=fetch.get(key,{}).get('file',''),
            previous_category=original[key]['category'],reviewed_category=row['category'],
            previous_pipeline_codes=';'.join(sorted(before))))
    content_links=guard_cross_group_content(rows,original,es)
    old_filter.regroup(rows,original)
    bykey={r['record_key']:r for r in rows}
    for d in decisions:
        row=bykey[d['record_key']]
        d.update(final_status=row['pipeline_status'],remaining_pipeline_codes=row['pipeline_review_codes'],
                 exclusion_codes=row['exclusion_codes'],pipeline_group=row['pipeline_group'],
                 assigned_split=row['assigned_split'],training_allowed=row['training_allowed'])
    for row in rows:
        before=original[row['record_key']]
        for field in ['price_million','area_sqm','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert row[field]==before[field],(row['record_key'],field)
        if before['pipeline_status']!='needs_review':
            assert row==before
    code=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    target=ROOT/'runs'/code
    if target.exists():
        c.verify(json.loads((target/'manifest.json').read_text(encoding='utf-8'))['output_sha256'],target)
        publish(target);print('Existing run verified: '+str(target));return
    stage=ROOT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    c.write_csv(stage/'all_listings_after_review.csv',rows,list(rows[0]))
    c.write_csv(stage/'reviewed_pending.csv',decisions,list(decisions[0]))
    c.write_csv(stage/'cross_group_content_links.csv',content_links,
                ['record_key','other_record_key','group','other_group','rule','other_reserved_splits'])
    for status in ['eligible','needs_review','excluded']:
        c.write_csv(stage/(status+'.csv'),[r for r in rows if r['pipeline_status']==status],list(rows[0]))
    training=prior.build_training(rows,stage)
    old_train=c.read(old/'training_inputs/train.csv')
    train=c.read(stage/'training_inputs/train.csv')
    old_keys={r['record_key'] for r in old_train}
    added=[r for r in train if r['record_key'] not in old_keys]
    c.write_csv(stage/'added_train.csv',added,c.FIELDS)
    summary=dict(reviewed_pending=len(pending),final_batch_outcomes=dict(Counter(d['final_status'] for d in decisions)),
        all_collection_statuses=dict(Counter(r['pipeline_status'] for r in rows)),training_inputs=training,
        additional_train=len(added),additional_train_by_category=dict(Counter(r['category'] for r in added)),
        additional_train_by_source=dict(Counter(r['source'] for r in added)),
        exact_html_snapshots_sha256_checked=len(checked),numeric_labels_changed=0,
        cross_group_candidate_links=len(content_links),
        remaining_source_identity_verified=sum(r['pipeline_status']=='needs_review' and es.get(r['record_key'],{}).get('identity_verified',False) for r in rows),
        remaining_pipeline_codes=dict(Counter(code for r in rows if r['pipeline_status']=='needs_review' for code in prior.codes(r['pipeline_review_codes']))),
        category_changes=sum(r['category']!=original[r['record_key']]['category'] for r in rows),
        new_network_requests=0,models_modified=False,model_trained=False)
    c.write_json(stage/'summary.json',summary)
    c.write_json(stage/'diversity_coverage.json',dict(before=coverage(old_train),after=coverage(train),added=coverage(added)))
    (stage/'README.md').write_text('\n'.join([
        '# Lọc bổ sung dữ liệu cho train','',
        f'Rà soát đủ **{len(pending):,} ID** còn chờ bằng nội dung đã lưu đúng ID. '
        f'Bổ sung **{len(added):,} tin train**; tổng **{training["train"]:,} train**, '
        f'**{training["validation"]:,} validation cố định**, **{training["reserved_eligible"]:,} eligible giữ riêng**.','',
        f'Toàn bộ 8.509 ID: `{summary["all_collection_statuses"]}`. '
        f'Kết quả trong nhóm còn chờ: `{summary["final_batch_outcomes"]}`.','',
        'Giá/diện tích số giữ nguyên. Giá viết tắt chỉ được diễn giải khi khớp chính xác tổng giá trên header nguồn. '
        'Bỏ ảnh hưởng ký hiệu định dạng chữ khi so nội dung; phân biệt mô tả tài sản với footer môi giới; '
        'phân biệt dự định xây dựng với công trình hiện hữu và giá bán với tiền thuê. '
        'Giá dạng x, nhiều tài sản/phòng thuê khép kín, ngưỡng số, giao dịch/địa bàn và nhóm mâu thuẫn tiếp tục giữ chờ.','',
        'Đã kiểm tra mô tả dài trùng nhau qua các nhóm cũ: các tin mới có liên kết nghi trùng giữ chờ, '
        'không tự gộp nhóm hoặc thay reservation. [Các liên kết nội dung](cross_group_content_links.csv).','',
        'Không tải thêm nguồn, không phỏng đoán giá, không nhân bản tin, không chuyển holdout vào train. '
        'Đây là kiểm chứng tin rao theo nguồn, chưa xác minh giao dịch hoặc thực địa. '
        'Chưa huấn luyện hoặc thay model v3/v4; chưa thêm đặc trưng tọa độ/POI.','',
        '[Train](training_inputs/train.csv), [validation](training_inputs/validation.csv), '
        '[registry dự phòng](training_inputs/reserved_holdout_registry.csv), [tin mới vào train](added_train.csv), '
        '[độ phủ trước/sau](diversity_coverage.json), [quyết định từng ID](reviewed_pending.csv), [số liệu](summary.json).','',
        'Chỉ dùng training_inputs cho mô hình: schema fit trên train, giá/đơn giá/tiêu đề/mô tả/ID không làm feature. '
        'Đã xuất và kiểm tra DMatrix cho cả ba loại tài sản.','']),encoding='utf-8')
    c.verify(inputs);c.verify(protected)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=protected,
        output_sha256=c.outputs(stage),previous_run=old.relative_to(c.BASE).as_posix(),new_network_requests=0))
    stage.rename(target)
    publish(target)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print(target,flush=True)


def publish(target):
    c.write_json(ROOT/'latest.json',dict(run=target.relative_to(ROOT).as_posix()))
    (ROOT/'README.md').write_text('# Dữ liệu bổ sung cho train\n\n'
        f'[Báo cáo hiện tại]({target.relative_to(ROOT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':
    main()
