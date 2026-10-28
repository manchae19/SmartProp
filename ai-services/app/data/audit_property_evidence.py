"""Audit literal property claims on the clean fixed cohort; never fit a model."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import uuid
from market_observations import timestamp

import training_v3_common as c
from build_property_features_v6 import admit_body
import property_evidence_claims as rules
import review_source_details as parser

BASE = c.BASE
PREPARED = BASE / 'processed/training_next_preparation/runs/4fdb8ef79db89b16'
HISTORY = BASE / 'processed/remaining_diversity_review/runs/1d45c8941172a52d'
SOURCE = BASE / 'processed/collection_source_review'
OUT = BASE / 'processed/property_evidence_audit'
SUPPLEMENT = BASE / 'data_raw/training_property_evidence_20'
PROTOCOL = BASE / 'PROPERTY_EVIDENCE_PROTOCOL.md'


def validate_cohort(parts, reserved):
    seen_keys, seen_groups = set(), set()
    blocked = {r['pipeline_group'] for r in reserved}
    for split, rows in parts.items():
        keys, groups = {r['record_key'] for r in rows}, {r['pipeline_group'] for r in rows}
        if len(keys) != len(rows) or len(groups) != len(rows) or keys & seen_keys or groups & seen_groups or groups & blocked:
            raise ValueError('Repeated/protected property group in audit cohort')
        if any(r['model_split'] != split for r in rows):
            raise ValueError('Split differs')
        if any(r['reserved_splits'] != 'train' for r in rows if split == 'train'):
            raise ValueError('Reserved row admitted to train audit')
        seen_keys.update(keys)
        seen_groups.update(groups)


def read_context():
    manifest = json.loads((PREPARED / 'manifest.json').read_text(encoding='utf8'))
    c.verify(manifest['output_sha256'], PREPARED)
    parts = {s: c.read(PREPARED / (s + '.csv')) for s in ['train', 'validation']}
    validate_cohort(parts, c.read(PREPARED / 'reserved_holdout_registry.csv'))
    source_manifest = json.loads((SOURCE / 'review_manifest.json').read_text(encoding='utf8'))
    history_manifest = json.loads((HISTORY / 'manifest.json').read_text(encoding='utf8'))
    paths = [PREPARED / 'manifest.json', *[PREPARED / p for p in manifest['output_sha256']],
        HISTORY / 'manifest.json', HISTORY / 'all_listings_after_review.csv', SOURCE / 'review_manifest.json',
        SOURCE / 'parsed_evidence.json', SOURCE / 'fetch_manifest.json', Path(__file__), Path(rules.__file__),
        Path(parser.__file__), BASE / 'build_property_features_v6.py', BASE / 'training_v3_common.py', PROTOCOL]
    paths += [BASE / name for name in ['audit_all_collected.py', 'collection_review_rules.py', 'smartprop_geography.py']]
    c.verify({'all_listings_after_review.csv': history_manifest['output_sha256']['all_listings_after_review.csv']}, HISTORY)
    for name in ['parsed_evidence.json', 'fetch_manifest.json']:
        relative = (SOURCE / name).relative_to(BASE).as_posix()
        c.verify({relative: source_manifest['output_sha256'][relative]})
    original = {r['record_key']: r for r in c.read(HISTORY / 'all_listings_after_review.csv')}
    parsed = json.loads((SOURCE / 'parsed_evidence.json').read_text(encoding='utf8'))
    fetched = json.loads((SOURCE / 'fetch_manifest.json').read_text(encoding='utf8'))
    # Preserve exact inputs protected by the clean preparation (including v6).
    protected = {}
    root = BASE.parents[2]
    for relative, expected in manifest['input_sha256'].items():
        path = root / relative
        if c.sha(path) != expected:
            raise ValueError('Protected source changed: ' + relative)
        protected[path.relative_to(BASE).as_posix() if path.is_relative_to(BASE) else str(path)] = expected
    for path in sorted((BASE / 'processed/evaluation_ledger').glob('*.json')):
        paths.append(path)
    supplements = {}
    if SUPPLEMENT.exists():
        if (SUPPLEMENT / 'collector.lock').exists():
            raise ValueError('Supplement collection in progress')
        for path in sorted((SUPPLEMENT / 'records').glob('*.json')):
            record = json.loads(path.read_text(encoding='utf8'))
            train_by_key = {r['record_key']: r for r in parts['train']}
            row = train_by_key.get(record['record_key'])
            if not row or row['category'] != rules.APARTMENT or row['source'] != 'cafeland' or record['pipeline_group'] != row['pipeline_group']:
                raise ValueError('Supplement outside training-apartment scope')
            timestamp(record['observed_at'])
            if record['record_key'] in supplements:
                raise ValueError('Duplicate supplement ID')
            supplements[record['record_key']] = record
            paths.append(path)
            body_path = SUPPLEMENT / 'evidence' / (record['response_sha256'] + '.html')
            if c.sha(body_path) != record['response_sha256']:
                raise ValueError('Supplement body differs')
            paths.append(body_path)
        if (SUPPLEMENT / 'plan.json').exists():
            paths.append(SUPPLEMENT / 'plan.json')
    return parts, original, parsed, fetched, supplements, paths, protected


def sources_for(row, origin, parsed, fetched, paths, supplement=None):
    raw = json.loads(origin['raw_json'])
    sources = [dict(kind='collected_title', text=origin['title'],
                    sha256=hashlib.sha256(origin['title'].encode()).hexdigest())]
    if raw.get('legal_status'):
        sources.append(dict(kind='structured_legal_status', text=str(raw['legal_status']),
                            sha256=hashlib.sha256(origin['raw_json'].encode()).hexdigest()))
    body, state = admit_body(row, parsed, fetched)
    body_sha = ''
    if body:
        file = fetched['file']
        if Path(file).name != file:
            raise ValueError('Unexpected source cache path')
        path = SOURCE / 'detail_cache' / file
        if c.sha(path) != fetched['sha256']:
            raise ValueError('Source HTML differs')
        paths.append(path)
        replay = parser.parse_detail(origin, fetched, path.read_bytes())
        fields = ['identity_verified', 'structure_verified', 'category', 'price_million', 'area_sqm',
                  'description', 'asset_description', 'source_category', 'sale_verified', 'flags']
        if any(replay.get(k) != parsed.get(k) for k in fields):
            body, state = '', 'cached_parser_replay_differs'
        else:
            body_sha = fetched['sha256']
    if supplement:
        # The refresh is a new observation, not proof these attributes existed
        # at the old label time. This audit never releases it into model X.
        if supplement['record_key'] != row['record_key'] or supplement['pipeline_group'] != row['pipeline_group']:
            raise ValueError('Supplement identity/group differs')
        path = SUPPLEMENT / 'evidence' / (supplement['response_sha256'] + '.html')
        refreshed = parser.parse_detail(origin, supplement['fetch'], path.read_bytes())
        refreshed['detail_sha256'] = supplement['response_sha256']
        fresh_body, _ = admit_body(row, refreshed, dict(supplement['fetch'], sha256=supplement['response_sha256']))
        if not body and fresh_body and not refreshed['flags'] and refreshed['sale_verified']:
            body, body_sha = fresh_body, supplement['response_sha256']
            state = 'refreshed_matching_labels_NOT_ASOF_VERIFIED'
    if body:
        sources.append(dict(kind='verified_detail_body' if not state.startswith('refreshed') else 'refreshed_detail_NOT_ASOF_VERIFIED',
                            text=body, sha256=body_sha))
    return sources, state, body_sha


def artifacts():
    parts, original, parsed, fetched, supplements, paths, protected = read_context()
    features, evidence, requests = [], [], []
    for split, rows in parts.items():
        for row in rows:
            key = row['record_key']
            sources, state, body_sha = sources_for(row, original[key], parsed.get(key), fetched.get(key, {}), paths, supplements.get(key))
            collected = original[key].get('collected_at', '')
            try:
                observed_year = datetime.fromisoformat(collected.replace('Z', '+00:00')).year
            except ValueError:
                observed_year = None
            values, proofs = rules.extract(row['category'], sources, observed_year=observed_year)
            features.append(dict(record_key=key, model_split=split, category=row['category'],
                body_state=state, detail_sha256=body_sha, **values, training_allowed=False))
            evidence.extend(dict(record_key=key, model_split=split, **p) for p in proofs)
            if split == 'train' and row['category'] == rules.APARTMENT and not body_sha and row['source'] == 'cafeland':
                requests.append(dict(record_key=key, source=row['source'], source_listing_id=original[key]['source_listing_id'],
                    pipeline_group=row['pipeline_group'], detail_url=row['detail_url'], title=original[key]['title'],
                    expected_category=row['category'], expected_price_million=row['price_million'], expected_area_sqm=row['area_sqm'],
                    reason='missing_verified_matching_apartment_description', fields_needed='project;building;unit_floor;handover;interior;legal'))
    bykey = {r['record_key']: r for r in features}
    coverage = []
    for split, rows in parts.items():
        for category in c.CATEGORIES:
            members = [r for r in rows if r['category'] == category]
            for field in rules.FIELDS:
                applicable = (category == rules.APARTMENT if field in ['apartment_floor_claim', 'handover_year_claim'] else
                              category != rules.APARTMENT if field in ['alley_width_m_claim', 'car_access_claim'] else
                              category != 'Đất nền' if field == 'interior_claim' else True)
                coverage.append(dict(split=split, category=category, field=field, applicable=applicable,
                    rows=len(members), literal_claims=sum(bykey[r['record_key']][field] != '' for r in members) if applicable else 0,
                    conflict_rows=sum(field in bykey[r['record_key']]['conflict_fields'].split(';') for r in members),
                    note='Literal source claim; not verified measurement/legal status; audit only'))
    summary = dict(train=len(parts['train']), validation=len(parts['validation']), feature_rows=len(features),
        body_states_by_split={s: dict(Counter(r['body_state'] for r in features if r['model_split'] == s)) for s in parts},
        apartment_body_states={s: dict(Counter(r['body_state'] for r in features if r['model_split'] == s and r['category'] == rules.APARTMENT)) for s in parts},
        evidence_rows=len(evidence), evidence_statuses=dict(Counter(p['status'] for p in evidence)),
        name_candidates_need_review=sum(p['status'] == 'needs_name_review' for p in evidence),
        requested_apartment_details=len(requests), supplemented=len(supplements), model_trained=False,
        training_matrix_released=False, evaluation_members_used=0, labels_splits_changed=False,
        note='Coverage audit only; post-snapshot refreshes do not prove old-time attributes. No model or future-price claims.')
    inputs = {str(p.resolve()): c.sha(p) for p in set(paths)}
    return features, evidence, coverage, sorted(requests, key=lambda r: r['record_key']), summary, inputs, protected


def main():
    parser_cli = argparse.ArgumentParser(description=__doc__)
    parser_cli.add_argument('--verify', action='store_true')
    args = parser_cli.parse_args()
    features, evidence, coverage, requests, summary, inputs, protected = artifacts()
    run_id = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    target = OUT / 'runs' / run_id
    fields = dict(features_DO_NOT_TRAIN=list(features[0]), evidence_private_DO_NOT_TRAIN=
        ['record_key', 'model_split', 'field', 'value', 'source_kind', 'source_sha256', 'source_quote', 'rule', 'status', 'reason'],
        coverage=list(coverage[0]), collection_requests=['record_key', 'source', 'source_listing_id', 'pipeline_group',
        'detail_url', 'title', 'expected_category', 'expected_price_million', 'expected_area_sqm', 'reason', 'fields_needed'])
    values = dict(features_DO_NOT_TRAIN=features, evidence_private_DO_NOT_TRAIN=evidence, coverage=coverage, collection_requests=requests)
    if target.exists():
        manifest = json.loads((target / 'manifest.json').read_text(encoding='utf8'))
        c.verify(manifest['output_sha256'], target)
        if manifest['input_sha256'] != inputs:
            raise ValueError('Input identity differs')
        for name, rows in values.items():
            expected = [{k: str(r.get(k, '')) for k in fields[name]} for r in rows]
            if c.read(target / (name + '.csv')) != expected:
                raise ValueError('Feature/quote replay differs: ' + name)
        print(json.dumps(dict(verified=True, run_id=run_id, feature_rows=len(features), evidence_rows=len(evidence)), ensure_ascii=False))
        return
    if args.verify:
        raise ValueError('No matching complete audit; build first')
    stage = OUT / 'runs' / ('.building_' + uuid.uuid4().hex)
    stage.mkdir(parents=True)
    for name, rows in values.items():
        c.write_csv(stage / (name + '.csv'), rows, fields[name])
    summary['run_id'] = run_id
    c.write_json(stage / 'summary.json', summary)
    (stage / 'README.md').write_text(f'''# Rà đặc trưng tài sản — {run_id}

{summary['train']} train / {summary['validation']} validation, đúng cohort đã chuẩn bị.
Xuất sidecar DO_NOT_TRAIN và quote/hash từng lời rao; không fit/train/chấm model.
Không sửa raw/giá/diện tích/split/ledger hoặc v6. Chỉ quan sát độ phủ validation,
không dùng ví dụ/điểm validation để sửa quy tắc.

`coverage.csv`: độ phủ sáu trường lời rao. Dự án/tòa là ứng viên cần kiểm tra,
không tự tạo registry hoặc gán nhãn dự án. Pháp lý là lời khai, không xác minh.
Mâu thuẫn, tương lai, gần đó, giỏ hàng và thuộc tính tài sản khác giữ missing.
`collection_requests.csv`: chỉ hàng đợi train căn hộ CafeLand thiếu mô tả khớp
snapshot, không lấy các nhóm kiểm chứng đã chấm. Có {len(requests)} ID còn cần.

Mô tả refresh có cùng nhãn giá/diện tích chỉ hỗ trợ nghiên cứu nguồn hiện tại,
không chứng minh đặc trưng đã tồn tại tại thời điểm nhãn cũ. Không tự nối sidecar
vào X. Cần review nguồn/thời gian và thiết kế thử nghiệm trước model tiếp theo.
''', encoding='utf8')
    for path, expected in inputs.items():
        if c.sha(path) != expected:
            raise ValueError('Input changed during audit')
    for path, expected in protected.items():
        actual = Path(path) if Path(path).is_absolute() else BASE / path
        if c.sha(actual) != expected:
            raise ValueError('Protected input changed')
    c.write_json(stage / 'manifest.json', dict(input_sha256=inputs, protected_sha256=protected, output_sha256=c.outputs(stage)))
    stage.rename(target)
    c.write_json(OUT / 'latest.json', dict(run='runs/' + run_id))
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(target)


if __name__ == '__main__':
    main()
