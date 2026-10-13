"""Report source evidence separately from final collection/training eligibility."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from audit_all_collected import BASE, read, save_csv

ROOT=BASE/'processed/collection_source_review'
PRIOR=BASE/'processed/collection_pipeline/runs/2026-10-11_3a4f445cb285945b'


def reason(row,review):
    codes=set(row['pipeline_review_codes'].split(';')) | set(review['review_codes'].split(';'))
    if review['fetch_state']=='not_requested_source_access_blocked':return 'source_access_blocked_not_individually_requested'
    if review['fetch_state'] not in ('cached','downloaded'):return 'detail_unavailable_or_not_downloaded'
    if review['source_identity_verified']!='True':return 'detail_identity_not_verified'
    if 'prior_pending_requires_explicit_resolution' in codes:return 'prior_complex_source_review_still_pending'
    if any('differs_from_collected_snapshot' in c for c in codes):return 'current_snapshot_differs_requires_reconciliation'
    if any('group_' in c or c=='linked_group_member_not_eligible' for c in codes):return 'duplicate_group_not_resolved'
    if codes & {'partial_or_starting_price_context','multiple_assets_or_inventory_context',
                'special_or_whole_building_not_resolved','mixed_land_and_building_context',
                'description_price_or_area_range','transaction_or_partial_price_title',
                'multiple_properties_in_title','project_marketing_requires_specific_asset'}:
        return 'financial_multiple_or_special_asset_context'
    if codes & {'description_area_needs_review','description_total_price_needs_review',
                'structured_and_displayed_price_conflict','source_structure_incomplete',
                'numeric_threshold','total_price_threshold','unit_price_threshold'}:return 'price_area_or_structure_unresolved'
    if any('category' in c for c in codes):return 'property_category_unresolved_or_conflicting'
    if codes & {'listing_date_unavailable','older_than_183_days','source_date_needs_review'}:return 'date_missing_old_or_unverified'
    return 'other_remaining_checks'


def main():
    frozen=ROOT/'result_manifest.json'
    if frozen.exists():
        saved=json.loads(frozen.read_text(encoding='utf-8'))
        for rel,sha in saved['output_sha256'].items():
            if hashlib.sha256((BASE/rel).read_bytes()).hexdigest()!=sha:
                raise RuntimeError('Frozen source-review report changed: '+rel)
        print('Frozen source-review report verified; no rewriting.')
        return
    manifest=json.loads((ROOT/'review_manifest.json').read_text(encoding='utf-8'))
    if not manifest['complete']:raise RuntimeError('Review is provisional')
    latest=json.loads((BASE/'processed/collection_pipeline/latest.json').read_text(encoding='utf-8'))
    run=BASE/'processed/collection_pipeline'/latest['run']
    pm=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    relative=(ROOT/'review_decisions.csv').relative_to(BASE).as_posix()
    if pm['input_sha256'].get(relative)!=hashlib.sha256((ROOT/'review_decisions.csv').read_bytes()).hexdigest():
        raise RuntimeError('Latest collection pipeline has not applied this source review')
    allrows={r['record_key']:r for r in read(run/'all_listings.csv')}
    prior={r['record_key']:r for r in read(PRIOR/'all_listings.csv')}
    decisions=read(ROOT/'review_decisions.csv')
    rows=[]
    for review in decisions:
        r=dict(allrows[review['record_key']])
        r.update(source_review_decision=review['decision'],source_review_codes=review['review_codes'],
                 source_fetch_state=review['fetch_state'],source_identity_verified=review['source_identity_verified'],
                 pending_primary_reason=reason(r,review) if r['pipeline_status']=='needs_review' else '')
        rows.append(r)
    assert len(rows)==len({r['record_key'] for r in rows})==4383
    fields=list(rows[0])
    for status in ('eligible','needs_review','excluded'):
        save_csv(ROOT/('queue_'+status+'.csv'),[r for r in rows if r['pipeline_status']==status],fields)
    changes=[]
    for key,r in allrows.items():
        before=prior[key]
        if any(before[f]!=r[f] for f in ('pipeline_status','category','price_million','area_sqm','training_allowed')):
            changes.append(dict(record_key=key,previous_status=before['pipeline_status'],status=r['pipeline_status'],
                previous_category=before['category'],category=r['category'],
                previous_price_million=before['price_million'],price_million=r['price_million'],
                previous_area_sqm=before['area_sqm'],area_sqm=r['area_sqm'],
                previous_training_allowed=before['training_allowed'],training_allowed=r['training_allowed'],
                review_codes=r['pipeline_review_codes'],exclusion_codes=r['exclusion_codes']))
    save_csv(ROOT/'collection_changes.csv',changes,list(changes[0]) if changes else ['record_key'])
    s=json.loads((ROOT/'review_summary.json').read_text(encoding='utf-8'))
    fetch=json.loads((ROOT/'fetch_manifest.json').read_text(encoding='utf-8'))
    pipeline=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    summary=dict(queue_statuses=dict(Counter(r['pipeline_status'] for r in rows)),
        queue_train_candidates=sum(r['training_allowed']=='True' for r in rows),
        pending_primary_reasons=dict(Counter(r['pending_primary_reason'] for r in rows if r['pipeline_status']=='needs_review')),
        collection_changes=len(changes),transition_counts=dict(Counter(r['previous_status']+' -> '+r['status'] for r in changes)),
        pipeline_run=run.relative_to(BASE).as_posix(),collection_statuses=pipeline['statuses'],
        collection_train_candidates=pipeline['train_candidates'],raw_and_old_test_unchanged=True,
        source_manual_review_claimed=False,model_trained=False)
    assert sum(summary['queue_statuses'].values())==4383
    (ROOT/'result_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
    lines=['# Bổ sung bằng chứng cho 4.383 tin đang chờ', '',
        'Đối chiếu trang nguồn theo ID/tiêu đề, vùng nội dung chính, loại tài sản, giá tổng, diện tích và địa bàn. '
        'Đây là kiểm tra tự động theo quy tắc có lưu HTML/hash, không phải xác minh giao dịch hay duyệt tay từng tin.', '',
        '| Nguồn | Số tin | Trang HTTP 200 | Đúng ID/tiêu đề | Giữ | Sửa loại | Loại | Chờ |',
        '|---|---:|---:|---:|---:|---:|---:|---:|']
    for source,counts in sorted(s['by_source'].items()):
        subset=[r for r in decisions if r['record_key'].startswith(source+':')]
        ok=sum(m.get('http_status')==200 for key,m in fetch.items() if key.startswith(source+':'))
        identities=sum(r['source_identity_verified']=='True' for r in subset)
        lines.append(f'| {source} | {len(subset):,} | {ok:,} | {identities:,} | {counts.get("keep",0):,} | '
                     f'{counts.get("correct",0):,} | {counts.get("exclude",0):,} | {counts.get("pending",0):,} |')
    lines += ['', '**Quyết định nguồn chưa đồng nghĩa đủ điều kiện train.** Sau khi áp dụng vào pipeline chung, '
        'tính lại tuổi tin, ngưỡng số, nhóm nghi trùng và bảo vệ holdout:', '',
        '| Kết quả riêng hàng chờ 4.383 tin | Số tin |', '|---|---:|']
    for status in ('eligible','needs_review','excluded'):
        lines.append(f'| [{status}](queue_{status}.csv) | {summary["queue_statuses"].get(status,0):,} |')
    lines += ['',f'Trong nhóm qua lọc, **{summary["queue_train_candidates"]:,}** đại diện được xét cho train; '
              'phần còn lại bảo vệ holdout. Không đưa toàn bộ nhóm giữ/sửa loại vào train.', '',
              '## Lý do chính còn chờ (không chồng lặp)', '', '| Nhóm | Số tin |','|---|---:|']
    labels=dict(source_access_blocked_not_individually_requested='Nguồn chặn truy cập; chưa kiểm tra từng URL',
        detail_unavailable_or_not_downloaded='Trang lỗi hoặc chưa tải được',
        detail_identity_not_verified='Chưa đối chiếu được đúng ID/tiêu đề',
        prior_complex_source_review_still_pending='Trường hợp phức tạp đang chờ từ đợt duyệt trước',
        current_snapshot_differs_requires_reconciliation='Trang hiện tại khác snapshot đã cào',
        duplicate_group_not_resolved='Nhóm nghi trùng còn mâu thuẫn hoặc thành viên chờ',
        financial_multiple_or_special_asset_context='Giá có điều kiện/nhiều tài sản/dự án/tài sản đặc thù',
        price_area_or_structure_unresolved='Giá/diện tích/cấu trúc trường chưa rõ',
        property_category_unresolved_or_conflicting='Loại tài sản thiếu căn cứ hoặc mâu thuẫn',
        date_missing_old_or_unverified='Ngày đăng thiếu, cũ hoặc chưa xác minh',other_remaining_checks='Các chốt khác')
    for code,count in summary['pending_primary_reasons'].items():lines.append(f'| {labels[code]} | {count:,} |')
    lines += ['', '## Bằng chứng và giới hạn', '',
        '- [review_decisions.csv](review_decisions.csv): mỗi ID một quyết định, loại đề xuất, giá/diện tích đề xuất, URL, hash HTML và lý do. Các cột sửa giá/diện tích để trống; không tự coi thay đổi trên trang hiện tại là lỗi của snapshot cũ.',
        '- [parsed_evidence.json](parsed_evidence.json), [fetch_manifest.json](fetch_manifest.json), `detail_cache/`: nội dung chính đã trích và trang tải thực tế. `reviewer=source_detail_rules_not_manual_verification` phân biệt với duyệt tay.',
        '- 1.798 tin Chợ Tốt chưa được yêu cầu từng URL. Nguồn từng trả 403 ở một URL thử; không diễn giải thành 1.798 URL đều trả 403. Không vượt chặn truy cập.',
        '- Trang lỗi/chuyển ID/tiêu đề không khớp, ngày thiếu/cũ, giá/diện tích mâu thuẫn, nhiều tài sản, tài sản đặc thù và quyết định pending cũ không tự được duyệt qua.',
        f'- {s["description_duplicate_candidate_pairs"]:,} liên kết mô tả dài trùng hoàn toàn, giá/diện tích phù hợp được bổ sung như **nghi trùng**, không khẳng định cùng tài sản. Tính lại nhóm trên toàn bộ 8.509 ID và giữ cầu nối holdout cũ.',
        '- Raw, training_v1/v2, review cũ và 137 tin test giữ nguyên; không huấn luyện mô hình. Giá đang xét là giá rao.', '',
        '## Kết quả toàn bộ bộ sưu tập', '',
        f'**{pipeline["statuses"].get("eligible",0):,} qua lọc; {pipeline["statuses"].get("needs_review",0):,} cần kiểm tra; '
        f'{pipeline["statuses"].get("excluded",0):,} loại. {pipeline["train_candidates"]:,} ứng viên train.**', '',
        f'[Mở báo cáo pipeline chung](../collection_pipeline/{latest["run"]}/README.md). '
        '[Xem thay đổi so với đợt trước](collection_changes.csv).', '',
        '## Chạy lại', '', 'Từ `F:\\SmartProp`:', '', '```powershell',
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/fetch_pending_details.py',
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/review_source_details.py',
        '.\\ai-services\\.venv\\Scripts\\python.exe -X utf8 ai-services/app/data/filter_all_collected.py',
        '```', '', 'Checkpoint bỏ qua ID đã xử lý. Khi bản duyệt đã chốt, kiểm tra hash và giữ nguyên kết quả. '
        'Muốn kiểm tra snapshot nguồn mới phải tạo đợt/thư mục mới.', '']
    (ROOT/'README.md').write_text('\n'.join(lines),encoding='utf-8')
    outputs={p.relative_to(BASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in
             [ROOT/'README.md',ROOT/'result_summary.json',ROOT/'collection_changes.csv']+
             [ROOT/('queue_'+s+'.csv') for s in ('eligible','needs_review','excluded')]}
    (ROOT/'result_manifest.json').write_text(json.dumps(dict(output_sha256=outputs,
         review_manifest_sha256=hashlib.sha256((ROOT/'review_manifest.json').read_bytes()).hexdigest(),
         pipeline_manifest_sha256=hashlib.sha256((run/'manifest.json').read_bytes()).hexdigest()),indent=2),encoding='utf-8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
