"""Seed verified CafeLand caches, revisit old IDs, and report observed prices."""
import argparse
from collections import Counter
import csv
from datetime import datetime, timezone
import html
import json
import os
from pathlib import Path
import re

import apartment_followup_rules as rules
import collect_apartment_pilot as cafe
from market_observations import ObservationStore, canonical, digest, monthly_series, normalize, timestamp

BASE = Path(__file__).resolve().parent
STORE = BASE / 'data_raw/market_price_observations'
REVIEW = BASE / 'processed/apartment_extension_review/runs/c458ee98726ea981'
PREPARED = BASE / 'processed/training_next_preparation/runs/4fdb8ef79db89b16'
CATALOG = BASE.parent / 'core/location_catalog_v6.json'
BATCHES = ['apartment_pilot_100', 'apartment_extension_80', 'apartment_topup_40']
REPORTS = BASE / 'processed/market_price_observations'


def read_csv(path):
    with Path(path).open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))


def location_labels(catalog):
    return dict(catalog['legacy'], **{code: name + ' (địa bàn mở rộng)' for code, name in catalog['expanded'].items()})


def write_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows({k: r.get(k) for k in fields} for r in rows)


def code_hashes():
    return {p.name: cafe.sha(p) for p in [Path(__file__), BASE / 'market_observations.py',
        Path(cafe.__file__), Path(rules.__file__), Path(rules.previous.__file__), CATALOG,
        Path(cafe.cafe.__file__)]}


def review_context(review=REVIEW, batches=None):
    """Read frozen decisions; every row must still match its source response."""
    manifest = json.loads((review / 'manifest.json').read_text(encoding='utf8'))
    for name, expected in manifest.items():
        if Path(name).name != name or cafe.sha(review / name) != expected:
            raise ValueError('Review artifact differs: ' + name)
    reviewed = {r['record_key']: r for r in read_csv(review / 'all_decisions.csv')}
    rows = []
    for batch in batches or [BASE / 'data_raw' / name for name in BATCHES]:
        for line in (batch / 'records.jsonl').read_text(encoding='utf8').splitlines():
            if not line:
                continue
            row = json.loads(line)
            expected = batch.resolve() / 'detail_cache' / (row['source_listing_id'] + '.html')
            if (batch / row['detail_file']).resolve() != expected:
                raise ValueError('Unexpected cache path')
            body = expected.read_bytes()
            if digest(body) != row['response_sha256'] or cafe.parse_detail(body, row, row['collected_at']) != row:
                raise ValueError('Source cache replay differs: ' + row['record_key'])
            decision = reviewed[row['record_key']]
            if decision['response_sha256'] != row['response_sha256']:
                raise ValueError('Review is for a different response')
            rows.append((row, decision, body))
    if len({r['record_key'] for r, _, _ in rows}) != len(rows):
        raise ValueError('Duplicate cache IDs')
    return rows, cafe.sha(review / 'manifest.json')


def event_for(row, review, body, provenance, *, status=200, error=None, current=False):
    flags = list(row.get('source_evidence_flags', []))
    for field in ['review_codes', 'group_review_codes', 'exclusion_codes']:
        flags.extend(json.loads(review[field]) if isinstance(review[field], str) else review[field])
    if review['cohort_split'] not in ['collection_holdout', 'suppressed_duplicate']:
        flags.append('baseline_review_not_eligible')
    if current:
        flags = [x for x in flags if not x.startswith('listing_detail_')]
    if error:
        flags.append(error)
    available = status == 200 and error is None
    event = dict(schema_version=1, source='cafeland', record_key=row['record_key'],
        source_listing_id=row['source_listing_id'], detail_url=row['detail_url'],
        observed_at=row['collected_at'], source_published_date=row.get('source_published_date', '') if available else '',
        source_published_date_raw=row.get('source_published_date_raw', '') if available else '',
        source_date_semantics='Source publication/update/repost display; not a historical observation time',
        price_million=row.get('price_million') if available else None,
        area_sqm=row.get('area_sqm') if available else None,
        price_raw=row.get('price_raw', '') if available else '', area_raw=row.get('area_raw', '') if available else '',
        currency=row.get('currency', '') if available else '', category=row.get('category', ''),
        transaction_type=row.get('transaction_type', ''), target_type='asking_price',
        location_feature=review['location_feature'], property_candidate_group=review['property_candidate_group'],
        group_basis='Frozen candidate linkage; not physically verified',
        availability='available' if available else 'not_found' if status in [404, 410] else 'parse_error',
        http_status=status, quality_flags=sorted(set(flags)),
        quality_eligible=available and not flags, response_sha256=digest(body),
        provenance_sha256=digest(provenance), training_allowed=False)
    return normalize(event)


def seed(root=STORE):
    rows, review_sha = review_context()
    store = ObservationStore(root, create=True)
    added = 0
    try:
        existing = {(r['record_key'], r['observed_at']): r for r in store.read_verified()}
        hashes = code_hashes()
        for row, decision, body in rows:
            identity = (row['record_key'], timestamp(row['collected_at']).isoformat(timespec='microseconds'))
            if identity in existing:
                saved = existing[identity]
                proof = (Path(root) / 'evidence' / (saved['provenance_sha256'] + '.json')).read_bytes()
                prior = json.loads(proof)
                if (prior.get('mode') != 'archive_cache' or prior['raw_record'] != row or prior['review'] != decision or
                        prior['review_manifest_sha256'] != review_sha or
                        event_for(row, decision, body, proof) != {k: v for k, v in saved.items() if k != 'observation_id'}):
                    raise ValueError('Archived observation differs; original preserved')
                continue
            provenance = canonical(dict(mode='archive_cache', raw_record=row, review=decision,
                review_manifest_sha256=review_sha, code_sha256=hashes)).encode('utf8')
            added += store.append(event_for(row, decision, body, provenance), body, provenance)
        count = len(store.read_verified())
    finally:
        store.close()
    return dict(cache_replayed=len(rows), inserted=added, total_observations=count,
                source_date_backfilled=False, training_started=False)


def parse_revisit(body, seed, decision, observed_at, resolved_url, catalog):
    # Listing-card fields are yesterday's evidence. Price/title changes between
    # observations are expected; current structured fields must still agree
    # with today's JSON-LD and seller description.
    row = cafe.parse_detail(body, dict(seed, detail_url=resolved_url), observed_at)
    row['source_evidence_flags'] = [x for x in row['source_evidence_flags'] if not x.startswith('listing_detail_')]
    checked = rules.quality(row, catalog)
    excluded, _ = rules.scope_exclusions(row)
    if (checked['location_feature'] != decision['location_feature'] or row['category'] != seed['category'] or
            row['area_sqm'] is None or seed['area_sqm'] is None or
            abs(row['area_sqm'] - seed['area_sqm']) / max(row['area_sqm'], seed['area_sqm'], 1) > .01):
        checked['review_codes'].append('possible_listing_reuse_or_property_identity_drift')
    decision = dict(decision, review_codes=sorted(set(checked['review_codes'])), exclusion_codes=excluded)
    return row, decision


def run_progress(events, root, run_id, plan):
    done = set()
    for event in events:
        provenance = json.loads((root / 'evidence' / (event['provenance_sha256'] + '.json')).read_text(encoding='utf8'))
        if provenance.get('collection_run') == run_id:
            if provenance['plan'] != plan or event['record_key'] not in plan['watchlist']:
                raise ValueError('Persisted run differs from plan')
            if event['record_key'] in done:
                raise ValueError('Duplicate observation within run')
            done.add(event['record_key'])
    return done


def observe(run_id, count=20, root=STORE, client_factory=cafe.Client):
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,64}', run_id) or not 1 <= count <= 20:
        raise ValueError('run-id: letters/digits/_/-, count: 1..20')
    rows, review_sha = review_context()
    selected = sorted([(r, d) for r, d, _ in rows if d['cohort_split'] == 'collection_holdout'],
                      key=lambda pair: pair[0]['record_key'])[:count]
    if not selected:
        raise ValueError('No reviewed watchlist')
    root = Path(root).resolve()
    batch = root / 'batches' / run_id
    plan = dict(schema_version=1, run_id=run_id, max_listings=count, delay_seconds=3,
        review_manifest_sha256=review_sha, code_sha256=code_hashes(),
        watchlist=[r['record_key'] for r, _ in selected])
    plan_path = batch / 'plan.json'
    stored_plan = json.loads(plan_path.read_text(encoding='utf8')) if plan_path.exists() else None
    if stored_plan:
        if {k: v for k, v in stored_plan.items() if k != 'code_sha256'} != {k: v for k, v in plan.items() if k != 'code_sha256'}:
            raise ValueError('Watchlist/policy changed; use a new run-id')
        if (root / 'observations.sqlite3').exists():
            reader = ObservationStore(root)
            try:
                done = run_progress(reader.read_verified(), root, run_id, stored_plan)
            finally:
                reader.close()
            if done == set(stored_plan['watchlist']):
                return dict(status='read_only_completed', observed=len(done), inserted=0, error=None)
        if stored_plan != plan:
            raise ValueError('Code changed on incomplete run; use a new run-id')
    elif stored_plan is not None:
        raise ValueError('Watchlist/policy changed; use a new run-id')
    batch.mkdir(parents=True, exist_ok=True)
    lock = batch / 'collector.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    store = None
    status, failure = 'completed', None
    inserted = 0
    try:
        if plan_path.exists() and json.loads(plan_path.read_text(encoding='utf8')) != plan:
            raise ValueError('Plan changed while acquiring lock')
        if not plan_path.exists():
            cafe.atomic(plan_path, plan)
        store = ObservationStore(root, create=True)
        done = run_progress(store.read_verified(), root, run_id, plan)
        if done == set(plan['watchlist']):
            return dict(status='read_only_completed', observed=len(done), inserted=0, error=None)
        catalog = json.loads(CATALOG.read_text(encoding='utf8'))
        client = client_factory(batch, 3)
        for original, decision in selected:
            if original['record_key'] in done:
                continue
            body, http = client.fetch(original['detail_url'])
            observed_at = datetime.now(timezone.utc).isoformat()
            error = None
            row = dict(original, collected_at=observed_at, detail_url=client.last_url)
            checked = decision
            if http == 200:
                try:
                    row, checked = parse_revisit(body, original, decision, observed_at, client.last_url, catalog)
                except (ValueError, KeyError, TypeError, IndexError) as exc:
                    error = 'parse_error:' + type(exc).__name__
            provenance = canonical(dict(mode='detail_revisit', collection_run=run_id, plan=plan,
                seed_record=original, baseline_review=decision, current_review=checked,
                observed_at=observed_at, resolved_url=client.last_url, http_status=http, error=error)).encode('utf8')
            inserted += store.append(event_for(row, checked, body, provenance, status=http, error=error, current=True), body, provenance)
            done.add(original['record_key'])
            print(canonical(dict(observed=len(done), record_key=original['record_key'], http_status=http)), flush=True)
    except KeyboardInterrupt:
        status, failure = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        status, failure = 'stopped_error', type(exc).__name__ + ': ' + str(exc)
    finally:
        if store:
            store.close()
        lock.unlink()
    result = dict(status=status, observed=len(done) if 'done' in locals() else 0, inserted=inserted, error=failure)
    cafe.atomic(batch / 'latest_run.json', result)
    return result


def verify(root=STORE):
    store = ObservationStore(root)
    try:
        events = store.read_verified()
    finally:
        store.close()
    catalog = json.loads(CATALOG.read_text(encoding='utf8'))
    for saved in events:
        evidence = Path(root) / 'evidence'
        body = (evidence / (saved['response_sha256'] + '.html')).read_bytes()
        provenance = (evidence / (saved['provenance_sha256'] + '.json')).read_bytes()
        proof = json.loads(provenance)
        if proof['mode'] == 'archive_cache':
            row, decision = proof['raw_record'], proof['review']
            if cafe.parse_detail(body, row, row['collected_at']) != row:
                raise ValueError('Archive replay changed')
            replay = event_for(row, decision, body, provenance)
        elif proof['mode'] == 'detail_revisit':
            original, decision = proof['seed_record'], proof['baseline_review']
            row = dict(original, collected_at=proof['observed_at'], detail_url=proof['resolved_url'])
            error = None
            if proof['http_status'] == 200:
                try:
                    row, decision = parse_revisit(body, original, decision, proof['observed_at'], proof['resolved_url'], catalog)
                except (ValueError, KeyError, TypeError, IndexError) as exc:
                    error = 'parse_error:' + type(exc).__name__
            if error != proof['error'] or decision != proof['current_review']:
                raise ValueError('Revisit interpretation changed')
            replay = event_for(row, decision, body, provenance, status=proof['http_status'], error=error, current=True)
        else:
            raise ValueError('Unsupported evidence mode')
        if replay != {k: v for k, v in saved.items() if k != 'observation_id'}:
            raise ValueError('Observation replay differs: ' + saved['record_key'])
    return events


def valuation_readiness(prepared=PREPARED, catalog_path=CATALOG):
    manifest = json.loads((prepared / 'manifest.json').read_text(encoding='utf8'))
    for name, expected in manifest['output_sha256'].items():
        if cafe.sha(prepared / name) != expected:
            raise ValueError('Prepared cohort changed: ' + name)
    train, validation = read_csv(prepared / 'train.csv'), read_csv(prepared / 'validation.csv')
    features = {r['record_key']: r for r in read_csv(prepared / 'features.csv')}
    spatial = {r['record_key']: r for r in read_csv(prepared / 'spatial_readiness_DO_NOT_TRAIN.csv')}
    readiness = []
    for split, rows in [('train', train), ('validation', validation)]:
        for category in sorted({r['category'] for r in rows}):
            members = [r for r in rows if r['category'] == category]
            readiness.append(dict(split=split, category=category, rows=len(members),
                source_date_present=sum(bool(r['displayed_date']) for r in members),
                source_date_missing=sum(not r['displayed_date'] for r in members),
                source_coordinates=sum(spatial[r['record_key']]['has_source_coordinates'] == 'True' for r in members),
                street_hint=sum(spatial[r['record_key']]['has_street_hint'] == 'True' for r in members),
                spatial_features_ready=sum(spatial[r['record_key']]['spatial_features_ready'] == 'True' for r in members),
                **{f: sum(bool(features[r['record_key']][f]) for r in members)
                   for f in ['rooms_completed', 'floors_claim', 'access_claim', 'house_subtype_claim']},
                conflict_rows=sum(bool(features[r['record_key']]['conflict_fields']) for r in members)))
    # Only train counts guide collection. No pilot score, validation error or
    # reserved-group labels enter priorities.
    catalog = json.loads(catalog_path.read_text(encoding='utf8'))
    locations = location_labels(catalog)
    counts = Counter((category, location) for category, location, group in
                     {(r['category'], r['location_feature'], r['pipeline_group']) for r in train})
    priorities = [dict(category=category, location_feature=key, location_label=label,
        train_groups=counts[(category, key)], planning_gap_to_10=max(0, 10 - counts[(category, key)]))
        for category in sorted({r['category'] for r in train}) for key, label in locations.items()
        if counts[(category, key)] < 10]
    return readiness, sorted(priorities, key=lambda r: (r['category'], r['train_groups'], r['location_feature']))


def report(root=STORE, reports=REPORTS):
    events = verify(root)
    series, summary = monthly_series(events)
    readiness, priorities = valuation_readiness()
    inputs = dict(event_ids=[r['observation_id'] for r in events],
        prepared_manifest_sha256=cafe.sha(PREPARED / 'manifest.json'), code_sha256=code_hashes())
    run_id = digest(canonical(inputs).encode('utf8'))[:16]
    output = Path(reports) / 'runs' / run_id
    if output.exists():
        manifest = json.loads((output / 'manifest.json').read_text(encoding='utf8'))
        if manifest['inputs'] != inputs:
            raise ValueError('Existing report input identity differs')
        for name, expected in manifest['outputs'].items():
            if cafe.sha(output / name) != expected:
                raise ValueError('Existing report changed')
        cafe.atomic(Path(reports) / 'latest.json', dict(run='runs/' + run_id))
        return output
    output.mkdir(parents=True)
    fields = ['observation_id', 'record_key', 'observed_at', 'source_published_date', 'availability',
        'price_million', 'area_sqm', 'location_feature', 'property_candidate_group', 'quality_eligible',
        'quality_flags', 'response_sha256', 'provenance_sha256', 'training_allowed']
    write_csv(output / 'observations_DO_NOT_TRAIN.csv', [dict(r, quality_flags=canonical(r['quality_flags'])) for r in events], fields)
    write_csv(output / 'monthly_asking_prices.csv', series, ['month', 'location_feature', 'area_band', 'groups', 'sources',
        'median_unit_price_million', 'median_total_price_million', 'sample_gate_passed', 'paired_groups', 'paired_median_change_pct'])
    write_csv(output / 'valuation_readiness.csv', readiness, list(readiness[0]))
    write_csv(output / 'collection_priorities.csv', priorities, ['category', 'location_feature', 'location_label', 'train_groups', 'planning_gap_to_10'])
    summary.update(run_id=run_id, observation_dates=sorted({r['observed_at'][:10] for r in events}),
        note='Source dates do not create past prices. 10 groups/18 months are conservative planning gates, not accuracy guarantees.')
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf8')
    text = f'''# Quan sát giá rao — {run_id}

Đã kiểm chứng lại bằng chứng cho **{len(events)} quan sát**, **{summary['listings']} ID**.
Tháng quan sát (giờ Việt Nam): `{summary['observations_by_month']}`.
Không dùng ngày đăng/cập nhật của nguồn để tạo giá quá khứ.

Độ dài liên tiếp lớn nhất của ô địa bàn × diện tích có ít nhất 10 nhóm:
**{summary['longest_adequate_month_streak']} tháng**. Cổng chuẩn bị backtest
(18 tháng, quy ước kế hoạch): **{summary['backtest_history_gate_passed']}**.
**Chưa train hoặc công bố mô hình dự báo xu hướng.**

`monthly_asking_prices.csv` là thống kê mẫu giá rao, không phải giá giao dịch
hoặc chỉ số thị trường đã điều chỉnh cơ cấu. Mỗi tháng lấy quan sát mới nhất
của mỗi ID rồi gom nhóm ứng viên; không điền giá vào tháng thiếu. Nhóm có thành
viên lỗi/404/410 hoặc mâu thuẫn bị cách ly. Chỉ tính thay đổi trên cùng nhóm
của hai tháng kề nhau nếu có ít nhất 10 cặp với diện tích ổn định.

`valuation_readiness.csv` rà đúng cohort 2.213 train/299 validation đã chuẩn bị.
`collection_priorities.csv` dùng số nhóm train theo địa bàn; mốc 10 chỉ gợi ý
lấy mẫu. Số phòng/tầng/lối vào là lời rao; không xác nhận thực địa.
Các trường dự án, pháp lý, năm bàn giao, độ rộng hẻm và vị trí chính xác cần
nguồn riêng; không tự suy ra hoặc điền 0.

`observations_DO_NOT_TRAIN.csv` giữ bằng chứng quan sát. Mọi tin của pilot đã
chấm vẫn thuộc registry bảo vệ, không tự ghép vào train/encoder/early stopping.
404/410 chỉ là trang không còn truy cập, không xác nhận đã bán.

HTML bên cạnh chỉ là bảng mô tả cục bộ; API và lịch sử người dùng vẫn dùng v6.
'''
    (output / 'README.md').write_text(text, encoding='utf8')
    catalog = json.loads(CATALOG.read_text(encoding='utf8'))
    labels = location_labels(catalog)
    bands = {'under20': '<20 m²', '20-49': '20–<50 m²', '50-79': '50–<80 m²', '80-119': '80–<120 m²', '120plus': '≥120 m²'}
    table_rows = []
    for row in series:
        values = [row['month'], labels[row['location_feature']], bands[row['area_band']], row['groups'],
            f"{row['median_unit_price_million']:.2f}".replace('.', ','),
            'Đủ mốc kế hoạch' if row['sample_gate_passed'] else 'Dưới 10 nhóm', row['paired_groups'],
            f"{row['paired_median_change_pct']:.2f}%".replace('.', ',') if row['paired_median_change_pct'] is not None else 'Chưa đủ dữ liệu']
        table_rows.append('<tr>' + ''.join(f'<td>{html.escape(str(value))}</td>' for value in values) + '</tr>')
    table = ''.join(table_rows)
    (output / 'dashboard.html').write_text('''<!doctype html><html lang="vi"><meta charset="utf-8"><title>SmartProp — Quan sát giá rao</title>
<style>body{font:16px system-ui;max-width:1100px;margin:40px auto;padding:0 20px;color:#203252}table{border-collapse:collapse;width:100%}th,td{padding:10px;border:1px solid #ccd;text-align:left}th{background:#edf1f8}</style>
<h1>SmartProp — Quan sát giá rao căn hộ</h1><p><strong>Chưa có dự báo xu hướng.</strong> Bảng phản ánh mẫu tin thu được, không phải giá giao dịch.</p>
<p>Tháng theo giờ Việt Nam. Giá: triệu đồng/m². Không có quan sát thì để thiếu; ngày đăng không tạo giá quá khứ. Nhóm ứng viên chưa được xác minh là tài sản riêng biệt.</p>
<p>Mốc xem xét backtest: 18 tháng liên tiếp có ít nhất 10 nhóm/ô; đây là quy ước kế hoạch, không bảo đảm chất lượng dự báo. Thay đổi % chỉ hiện khi có ít nhất 10 cặp nhóm cùng diện tích qua hai tháng kề nhau.</p>
<table><tr><th>Tháng</th><th>Địa bàn</th><th>Diện tích</th><th>Nhóm</th><th>Trung vị giá/m²</th><th>Độ phủ mẫu</th><th>Số cặp</th><th>Trung vị thay đổi %</th></tr>''' + table + '</table></html>', encoding='utf8')
    hashes = {p.name: cafe.sha(p) for p in output.iterdir() if p.is_file()}
    (output / 'manifest.json').write_text(json.dumps(dict(inputs=inputs, outputs=hashes), ensure_ascii=False, indent=2), encoding='utf8')
    Path(reports).mkdir(exist_ok=True)
    cafe.atomic(Path(reports) / 'latest.json', dict(run='runs/' + run_id))
    return output


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('seed', help='Replay 220 cached CafeLand pages; no network')
    live = sub.add_parser('observe', help='Revisit at most 20 reviewed IDs; resume by run-id')
    live.add_argument('--run-id', required=True)
    live.add_argument('--count', type=int, default=20)
    sub.add_parser('verify', help='Replay every stored response and decision; no network')
    sub.add_parser('report', help='Descriptive monthly sample and valuation readiness')
    args = parser.parse_args()
    if args.command == 'seed':
        result = seed()
    elif args.command == 'observe':
        result = observe(args.run_id, args.count)
    elif args.command == 'verify':
        result = dict(verified_observations=len(verify()))
    else:
        result = dict(report=str(report()))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result.get('error') else 0


if __name__ == '__main__':
    raise SystemExit(main())
