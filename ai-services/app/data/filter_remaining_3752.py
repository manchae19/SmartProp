"""Resolve cached-content false positives across all 3752 pending IDs.

No downloads, numeric relabeling, date cutoff, group reassignment or model edits.
"""
import json
import hashlib
import uuid
from collections import Counter, defaultdict
from pathlib import Path

import training_v3_common as c
import remaining_content_rules as rules
import review_remaining_4772 as prior
import filter_all_collected as pipeline

ROOT=c.PROCESSED/'remaining_3752_review'


def regroup(rows,original):
    groups=defaultdict(list)
    for row in rows:
        groups[row['pipeline_group']].append(row)
    for members in groups.values():
        new=[r for r in members if r['pipeline_status']=='eligible' and original[r['record_key']]['pipeline_status']=='needs_review']
        if not new:
            continue
        issues=set()
        values=[r for r in members if prior.number(r['price_million']) and prior.number(r['area_sqm'])]
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            numbers=[float(r[field]) for r in values]
            if numbers and (max(numbers)-min(numbers))/max(numbers)>tolerance:
                issues.add('group_'+field+'_conflict')
        if len({r['category'] for r in members})>1:
            issues.add('group_category_conflict')
        if len({r['district'] for r in members if r['district']})>1:
            issues.add('group_historical_location_conflict')
        if any(r['pipeline_status']=='needs_review' or (r['pipeline_status']=='excluded' and
            prior.codes(r['exclusion_codes'])!={'suspected_duplicate_suppressed'}) for r in members):
            issues.add(prior.LINK)
        if issues:
            for row in new:
                row.update(pipeline_status='needs_review',pipeline_review_codes=';'.join(sorted(prior.codes(row['pipeline_review_codes'])|issues)))
            continue
        contenders=[r for r in members if r['pipeline_status']=='eligible']
        frozen=[r for r in contenders if original[r['record_key']]['pipeline_status']=='eligible']
        rep=frozen[0] if frozen else max(contenders,key=lambda r:(bool(r['review_decision']),bool(r['displayed_date']),r['collected_at'],r['record_key']))
        for row in contenders:
            row['representative_key']=rep['record_key']
            if row is not rep:
                row.update(pipeline_status='excluded',exclusion_codes='suspected_duplicate_suppressed')
    for row in rows:
        row['training_allowed']=str(row['pipeline_status']=='eligible' and row['assigned_split']=='train' and row['protected_holdout']=='False')


def run():
    old=prior.ROOT/json.loads((prior.ROOT/'latest.json').read_text(encoding='utf-8'))['run']
    old_manifest=json.loads((old/'manifest.json').read_text(encoding='utf-8'))
    c.verify(old_manifest['output_sha256'],old)
    originals=c.read(old/'all_listings_after_review.csv')
    original={r['record_key']:r for r in originals}
    pending={r['record_key'] for r in originals if r['pipeline_status']=='needs_review'}
    if len(pending)!=3752 or len(original)!=8509:
        raise ValueError('Expected 3752 pending / 8509 unique IDs')
    source=c.PROCESSED/'collection_source_review'
    evidence=json.loads((source/'parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((source/'fetch_manifest.json').read_text(encoding='utf-8'))
    decisions={r['record_key']:r for r in c.read(source/'review_decisions.csv')}
    paths=[Path(__file__),Path(rules.__file__),Path(prior.__file__),Path(pipeline.__file__),Path(c.__file__),
        old/'manifest.json',old/'all_listings_after_review.csv',source/'parsed_evidence.json',
        source/'fetch_manifest.json',source/'review_decisions.csv',Path(rules.previous.__file__),
        Path(rules.previous.audit.__file__)]
    guarded={}
    for name in ['training_v3','models_v3_validation','models_v4_validation']:
        root=c.PROCESSED/name
        directory=root/json.loads((root/'latest.json').read_text(encoding='utf-8'))['run']
        manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
        c.verify(manifest['output_sha256'],directory)
        paths.append(directory/'manifest.json')
        guarded.update({(directory/p).relative_to(c.BASE).as_posix():v for p,v in manifest['output_sha256'].items()})
    # Reuse the source hashes already verified in this session, checking the
    # actual source snapshots touched by every proposed new content decision.
    for path in paths:
        relative=path.relative_to(c.BASE).as_posix()
        expected=old_manifest['input_sha256'].get(relative)
        if expected and c.sha(path)!=expected:
            raise ValueError('Frozen input changed: '+relative)
    inputs={p.relative_to(c.BASE).as_posix():c.sha(p) for p in paths}
    rows=[dict(r) for r in originals]
    details=[]
    checked_cache={}
    allowed=set(pipeline.DETAIL_RESOLVABLE_CODES)|{'saved_source_review_pending','category_title_inferred'}
    for row in rows:
        key=row['record_key']
        if key not in pending:
            continue
        e=evidence.get(key)
        f=fetch.get(key,{})
        d=decisions.get(key,{})
        before_flags=prior.codes(row['pipeline_review_codes'])
        result=rules.evaluate(row,e) if e else dict(decision='pending',category=row['category'],remaining_codes=['source_evidence_unavailable'],resolutions=[])
        acted=False
        if 'content_location_not_reconciled' in result['remaining_codes']:
            row['pipeline_review_codes']=';'.join(sorted(before_flags|{'content_location_not_reconciled'}))
        if result['decision'] in ['keep','correct','exclude']:
            if not e or not e.get('identity_verified') or f.get('http_status')!=200 or e.get('detail_sha256')!=f.get('sha256'):
                raise ValueError('Proposed decision lacks source identity/hash: '+key)
            path=source/'detail_cache'/f['file']
            if path not in checked_cache:
                if c.sha(path)!=f['sha256']:
                    raise ValueError('HTML evidence changed: '+key)
                checked_cache[path]=f['sha256']
                inputs[path.relative_to(c.BASE).as_posix()]=f['sha256']
            if result['decision']=='exclude' and result['resolutions']:
                row.update(pipeline_status='excluded',exclusion_codes='explicit_existing_rental_building_v2',training_allowed='False')
                acted=True
            elif result['decision'] in ['keep','correct'] and result['category'] in c.CATEGORIES:
                flags=before_flags-allowed-{prior.LINK}
                if any(r['rule']=='complete_billion_plus_three_digit_million' for r in result['resolutions']):
                    flags.discard('title_price_conflict')
                if result['category']!='Căn hộ chung cư':
                    flags.discard('apartment_price_priority')
                row.update(category=result['category'],category_basis='source_detail_content_rules_v2',
                    pipeline_review_codes=';'.join(sorted(flags)),
                    resolved_review_codes=';'.join(sorted(prior.codes(row['resolved_review_codes'])|(before_flags-flags))))
                # Category-dependent numerical quality gates remain mandatory.
                p,a=prior.number(row['price_million']),prior.number(row['area_sqm'])
                if p is None or a is None or p<=0 or a<=0:
                    flags.add('invalid_numeric_target_or_area')
                elif not(100<=p<=200000 and 20<=a<=1000 and 2<=p/a<=300):
                    flags.add('numeric_threshold')
                if row['category']=='Căn hộ chung cư' and p and a and (p<500 or not 15<=p/a<=150):
                    flags.add('apartment_price_priority')
                row['pipeline_review_codes']=';'.join(sorted(flags))
                row['pipeline_status']='needs_review' if flags else 'eligible'
                acted=True
        if acted:
            row.update(review_decision=result['decision'],review_decision_file='remaining_3752_review',
                review_evidence_sha256=e.get('detail_sha256',''),
                review_note='Explicit source-content recheck v2; see latest run reviewed_3752.csv for literal resolutions; not a verified transaction',
                label_quality='source_content_context_review_not_independent_transaction_verification')
        details.append(dict(record_key=key,source=row['source'],previous_category=original[key]['category'],
            reviewed_category=row['category'],source_decision=result['decision'],
            new_context_resolution=bool(result['resolutions']),
            context_resolution_json=json.dumps(result['resolutions'],ensure_ascii=False),
            remaining_source_codes=';'.join(result['remaining_codes']),
            original_source_codes=d.get('review_codes',''),
            source_identity_verified=bool(e and e.get('identity_verified')),
            evidence_sha256=(e or {}).get('detail_sha256',''),cache_file=f.get('file',''),
            cache_state=f.get('state','not_in_batch'),
            source_decision_applied=acted,previous_pipeline_codes=';'.join(sorted(before_flags))))
    regroup(rows,original)
    bykey={r['record_key']:r for r in rows}
    for result in details:
        row=bykey[result['record_key']]
        result.update(final_status=row['pipeline_status'],remaining_pipeline_codes=row['pipeline_review_codes'],
            exclusion_codes=row['exclusion_codes'],pipeline_group=row['pipeline_group'],assigned_split=row['assigned_split'],
            protected_holdout=row['protected_holdout'],training_allowed=row['training_allowed'])
    # Numeric labels, membership and reservations cannot change in this pass.
    for row in rows:
        before=original[row['record_key']]
        for field in ['price_million','area_sqm','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert row[field]==before[field],(row['record_key'],field)
        if before['pipeline_status']=='eligible':
            assert row['pipeline_status']=='eligible' and row['category']==before['category']
        if row['training_allowed']=='True':
            assert row['protected_holdout']=='False' and not (prior.codes(row['reserved_splits']) & {'validation','test'})
    code=hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    target=ROOT/'runs'/code
    if target.exists():
        c.verify(json.loads((target/'manifest.json').read_text(encoding='utf-8'))['output_sha256'],target)
        publish(target);print('Existing review verified: '+str(target));return
    stage=ROOT/'runs'/('.building_'+uuid.uuid4().hex)
    stage.mkdir(parents=True)
    c.write_csv(stage/'reviewed_3752.csv',details,list(details[0]))
    c.write_csv(stage/'all_listings_after_review.csv',rows,list(rows[0]))
    for status in ['eligible','needs_review','excluded']:
        c.write_csv(stage/(status+'.csv'),[r for r in rows if r['pipeline_status']==status],list(rows[0]))
    changed=[r for r in details if r['final_status']!='needs_review']
    c.write_csv(stage/'status_changes.csv',changed,list(details[0]))
    category_changes=[r for r in details if r['previous_category']!=r['reviewed_category']]
    c.write_csv(stage/'category_resolutions.csv',category_changes,list(details[0]))
    unresolved=[r for r in details if r['final_status']=='needs_review']
    for name,subset in [('source_access_missing',[r for r in unresolved if not r['source_identity_verified']]),
                        ('content_or_group_pending',[r for r in unresolved if r['source_identity_verified']])]:
        c.write_csv(stage/(name+'.csv'),subset,list(details[0]))
    training=prior.build_training(rows,stage)
    summary=dict(reviewed_pending=3752,source_content_candidates=dict(Counter(r['source_decision'] for r in details)),
        final_batch_outcomes=dict(Counter(r['final_status'] for r in details)),
        all_collection_statuses=dict(Counter(r['pipeline_status'] for r in rows)),
        contextual_resolutions=sum(r['new_context_resolution'] for r in details),
        category_changes=len(category_changes),numeric_labels_changed=0,
        exact_html_snapshots_sha256_checked=len(checked_cache),
        source_blocked_not_requested=sum(r['cache_state']=='not_requested_source_access_blocked' for r in unresolved),
        remaining_source_identity_verified=sum(r['source_identity_verified'] for r in unresolved),
        remaining_pipeline_codes=dict(Counter(code for r in unresolved for code in prior.codes(r['remaining_pipeline_codes']))),
        training_inputs=training,new_network_requests=0,models_modified=False,manual_property_verification_claimed=False)
    c.write_json(stage/'summary.json',summary)
    lines=['# Lọc tiếp toàn bộ 3.752 tin còn chờ','',
        'Đã kiểm tra mọi ID của nhóm còn chờ, đối chiếu nội dung chi tiết theo đúng ID và kiểm tra SHA-256 HTML cho tất cả '
        'quyết định nguồn được áp dụng. Đây là quy tắc kiểm chứng nội dung, không phải xác minh giao dịch/thực địa.','',
        '| Kết quả trong 3.752 tin | Số ID |','|---|---:|']
    lines += [f'| {k} | {v:,} |' for k,v in summary['final_batch_outcomes'].items()]
    lines += ['',f'Toàn bộ collection: `{summary["all_collection_statuses"]}`. '
        f'Đầu vào mới: **{training["train"]:,} train**, **299 validation cố định**, **{training["reserved_eligible"]:,} eligible giữ riêng**. '
        'Chưa train model mới, không thay v3/v4.','',
        '## Các phân biệt đã kiểm tra','',
        '- “4 tỷ 800” là tổng 4.800 triệu khi thành phần ba chữ số đầy đủ; không nhận số m², số phòng hoặc giá dạng x.',
        '- Nhà có diện tích đất khớp header và diện tích sử dụng/xây dựng khác: không so hai đại lượng đó như cùng một diện tích. '
        'Mâu thuẫn giữa hai diện tích đất, số làm tròn hoặc diện tích căn hộ vẫn giữ chờ.',
        '- Danh mục cụ thể được đối chiếu lời mô tả tài sản hiện hữu; không dùng lời môi giới ở footer, '
        'công trình gần đó hoặc gợi ý xây/cải tạo trong tương lai để chứng minh loại tài sản.',
        '- Cấu hình hiện hữu nguyên tòa cho thuê “công năng: 11 phòng căn hộ khép kín” được giữ ngoài nhà/đất/căn hộ đơn lẻ.',
        '- Các ngưỡng số, phạm vi/giao dịch, giá trả trước, nhiều tài sản và mâu thuẫn nhóm tiếp tục được kiểm tra. '
        'Giữ một đại diện nhóm, bảo toàn reservation validation/test; không phân nhóm lại hoặc gán giá bằng model.','',
        f'{summary["source_blocked_not_requested"]:,} tin Chợ Tốt vẫn chưa có nội dung chi tiết do nguồn bị chặn; '
        'không phải từng URL đều được thử rồi trả 403. Tin còn mơ hồ không bị loại chỉ để tăng số sạch. '
        'Nhóm pending tách thành thiếu nguồn và có nội dung nhưng còn vấn đề. Không áp dụng lại ngưỡng tuổi 183 ngày.','',
        '[Kết quả 3.752 ID](reviewed_3752.csv), [chuyển trạng thái](status_changes.csv), '
        '[quyết định danh mục có bằng chứng](category_resolutions.csv), [còn chờ](needs_review.csv), '
        '[thiếu nguồn/khớp ID](source_access_missing.csv), [còn vấn đề nội dung/nhóm](content_or_group_pending.csv).','',
        '[Train mới](training_inputs/train.csv), [validation cố định](training_inputs/validation.csv), '
        '[registry giữ riêng](training_inputs/reserved_holdout_registry.csv), [số liệu](summary.json). '
        'Các file có tiêu đề/mô tả/quyết định nguồn chỉ phục vụ rà soát, không dùng nguyên file làm feature. '
        'DMatrix dùng đúng feature contract cũ, không chứa giá/đơn giá/ID/mô tả trong X.','']
    (stage/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    c.verify(inputs);c.verify(guarded)
    c.write_json(stage/'manifest.json',dict(complete=True,input_sha256=inputs,protected_sha256=guarded,
        output_sha256=c.outputs(stage),numeric_labels_changed=False,new_network_requests=0))
    stage.rename(target)
    publish(target)
    print(json.dumps(summary,ensure_ascii=False,indent=2),flush=True)
    print(target,flush=True)


def publish(target):
    ROOT.mkdir(parents=True,exist_ok=True)
    c.write_json(ROOT/'latest.json',dict(run=target.relative_to(ROOT).as_posix()))
    (ROOT/'README.md').write_text('# Lọc tiếp 3.752 tin còn lại\n\n'
        f'[Báo cáo và bộ dữ liệu mới]({target.relative_to(ROOT).as_posix()}/README.md).\n',encoding='utf-8')


if __name__=='__main__':
    run()
