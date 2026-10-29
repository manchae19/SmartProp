"""Offline replay, evidence and full-history grouping of the bounded new batch."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path
import re
import uuid

import collect_source_features_75 as collect
import run_source_feature_trial as training
import source_asset_features as feature
import property_snapshot_adjudication as adjudicate
import apartment_followup_rules as apartment
import review_apartment_pilot as pilot
from build_training_v1 import group_records
from source_feature_io import atomic_json, writer_lock

data = training.data
BASE = data.BASE
OUT = BASE/'processed/source_features_75_review'
PREVIOUS = BASE/'processed/property_expansion_review/runs/e58bb9db7377e200'
PRIOR = collect.old.PRIOR


def seller_body(description):
    text = re.sub(r'^Thông tin mô tả\s*', '', description, flags=re.I)
    text = re.sub(r'^Bán (?:căn hộ chung cư|nhà riêng|nhà phố|nhà mặt phố|đất thổ cư|đất nền|đất)\s+.{0,160}?,\s*Đà Nẵng\s*', '', text, count=1, flags=re.I)
    return re.sub(r'(?:Xem thêm\s*)?Giá\s*:\s*[\d., ]+\s*(?:VND|VNĐ|đồng)\s+Diện tích\s*:\s*[\d., ]+\s*m[2²]\s*$', '', text, flags=re.I).strip()


def quality(row, catalog):
    if row['category'] == 'Căn hộ chung cư':
        checked = apartment.quality(row, catalog)
        scanned = adjudicate.scan(dict(row, **checked, exclusion_codes=apartment.scope_exclusions(row)[0]))
        return dict(review_codes=sorted(set(scanned['remaining_codes']) | set(scanned['exclusions_v2'])),
                    location_feature=checked['location_feature'], source_age_days=checked['source_age_days']), scanned['source_proofs']
    flags = set(row['source_evidence_flags'])
    location, _ = pilot.location(row, catalog)
    if not location: flags.add('location_not_in_reviewed_catalog')
    if row['category'] not in ['Nhà ở', 'Đất nền']: flags.add('unsupported_asset_category')
    if row['currency'] != 'VND' or row['transaction_type'] != 'sale': flags.add('sale_currency_unverified')
    p, a = row['price_million'], row['area_sqm']
    if p is None or p <= 0: flags.add('missing_total_price')
    if a is None or not 20 <= a <= 1000: flags.add('area_outside_current_api_scope')
    date = datetime.fromisoformat(row['collected_at']).astimezone(timezone(timedelta(hours=7))).date()
    try:
        age = (date-datetime.strptime(row['source_published_date'], '%Y-%m-%d').date()).days
        if not 0 <= age <= 183: flags.add('source_date_outside_183_days')
    except ValueError:
        age = None
        flags.add('source_date_missing')
    body = seller_body(row['description'])
    text = data.normalized(row['title'] + ' ' + body)
    if len(body.split()) < 15: flags.add('description_insufficient')
    if re.search(r'\b(?:gio hang|nhieu can|cac can|nhieu lo|cac lo|bang gia|quy can|[2-9]\d* lo dat)\b', text):
        flags.add('multiple_assets_or_inventory')
    if re.search(r'\b(?:booking|dat coc|tra truoc|gia tu|chi tu|thanh toan|sau chiet khau)\b', text):
        flags.add('conditional_partial_or_starting_price')
    if re.search(r'\d+[.,]x|\d+\s*(?:ty|ti)\s*\d*x|\d+\s*trieu\s*x', text):
        flags.add('masked_price_requires_review')
    if re.search(r'\b(?:ban toa|toa can ho|khach san|homestay|day tro|can ho dich vu|condotel)\b', text):
        flags.add('nonstandard_asset_requires_review')
    if re.match(r'^(?:cho thue|can thue)\b', data.normalized(row['title'])):
        flags.add('rental_offer')
    subject_pattern = r'\b(?:nha|biet thu)\b' if row['category']=='Nhà ở' else r'\b(?:dat|lo)\b'
    if not re.search(subject_pattern, data.normalized(body)): flags.add('asset_type_not_in_seller_body')
    proofs = adjudicate.full_vnd_proofs(body) + adjudicate.labelled_money_checks(body)
    total = [x for x in proofs if x['status'] == 'total_candidate']
    mentions = apartment.money_mentions(body)
    values = [x['amount_million'] for x in mentions if x['kind']=='total_candidate'] + [x['value'] for x in total]
    if not values or p is None or not any(adjudicate.close(v, p) for v in values):
        flags.add('seller_total_price_not_corroborated')
    if p is not None and any(not adjudicate.close(v, p) for v in values):
        flags.add('seller_total_price_conflict')
    if any(x['status'] in ['conditional_total_price_requires_review', 'ambiguous_total_requires_review'] for x in proofs):
        flags.add('conditional_or_ambiguous_total')
    area_values = []
    for m in adjudicate.AREA.finditer(body):
        value = float(m[1].replace(',', '.'))
        before = data.normalized(body[max(0,m.start()-60):m.start()])
        # Explicit floor/residential subareas are recorded, not relabelled as land area.
        other_basis = bool(re.search(r'\b(?:san|su dung|tho cu|dat o|thong thuy|tim tuong|cong vien|du an)\s*[:=]?\s*$', before))
        proofs.append(adjudicate.evidence('description', body, m, 'literal_area', value=value,
            status='other_explicit_area_basis' if other_basis else 'property_area_candidate'))
        if not other_basis: area_values.append(value)
    if a is None or not any(adjudicate.close(v, a) for v in area_values):
        flags.add('seller_property_area_not_corroborated')
    if a is not None and any(not adjudicate.close(v, a) for v in area_values):
        flags.add('multiple_or_conflicting_area_bases')
    # Only explicit original administrative wording is compared; do not map new wards to old districts.
    for district in collect.cafe_parser.DISTRICTS:
        prefix = 'huyen' if district == 'Hòa Vang' else 'quan'
        if re.search(r'\b'+prefix+' '+data.normalized(district)+r'\b', data.normalized(body)):
            if location in catalog['legacy'] and location != district:
                flags.add('source_seller_district_conflict')
    return dict(review_codes=sorted(flags), location_feature=location, source_age_days=age), proofs


def grouped_decisions(current, history, prior, links, evidence):
    """All old nodes/edges remain present, including excluded bridge nodes."""
    old_rows = {r['record_key']: dict(r) for r in history + prior}
    old_groups = defaultdict(list)
    for row in old_rows.values():
        g = row.get('pipeline_group') or row.get('property_candidate_group')
        if g: old_groups[g].append(row['record_key'])
    frozen_links = list(links)
    for members in old_groups.values():
        frozen_links += [dict(left=members[0], right=k, rule='preserve_original_group', title_similarity=1) for k in members[1:]]
    old_evidence = dict(evidence)
    old_evidence.update({r['record_key']: dict(identity_verified=True, description=r.get('description','')) for r in prior})
    new_links = pilot.extra_pairs(current, list(old_rows.values()), old_evidence)
    membership, _ = group_records([dict(r) for r in [*old_rows.values(), *current]], frozen_links + new_links)
    historical = {membership[k] for k in old_rows}
    groups = defaultdict(list)
    for r in current: groups[membership[r['record_key']]].append(r)
    decisions = []
    for g, members in groups.items():
        codes = []
        if g in historical: codes.append('linked_to_historical_or_reserved_group')
        if any(r['review_codes'] for r in members): codes.append('unresolved_member_in_group')
        if len({r['location_feature'] for r in members}) > 1: codes.append('group_location_conflict')
        for f, tolerance in [('area_sqm', .01), ('price_million', .05)]:
            values = [r[f] for r in members if r[f] is not None]
            if values and not all(adjudicate.close(v, values[0], tolerance) for v in values): codes.append('group_'+f+'_conflict')
        representative = min(r['record_key'] for r in members)
        for r in members:
            role = 'quarantine' if codes else 'fresh_reserved' if r['record_key']==representative else 'suppressed_duplicate'
            decisions.append(dict(r, candidate_group=g, representative_key=representative,
                group_review_codes=codes, dataset_role=role, training_allowed=False))
    return sorted(decisions, key=lambda r:r['record_key']), frozen_links + new_links


def artifacts():
    if (collect.OUT/'collector.lock').exists(): raise ValueError('Collection still running')
    known, plan = collect.plan_context()
    if json.loads((collect.OUT/'plan.json').read_text(encoding='utf8')) != plan: raise ValueError('Collection plan differs')
    records = collect.old.verified_records(collect.OUT)
    catalog = json.loads(collect.old.pilot.CATALOG.read_text(encoding='utf8'))
    rows, failed, proof_rows, feature_rows = [], [], [], []
    inputs = dict(plan['input_sha256'])
    for p in [Path(__file__), Path(feature.__file__), Path(apartment.__file__), Path(adjudicate.__file__),
              Path(pilot.__file__), BASE/'build_training_v1.py', BASE/'review_apartment_labels.py',
              BASE/'remaining_diversity_rules.py', BASE/'run_source_feature_trial.py']:
        inputs[str(p.resolve())] = data.sha(p)
    for p in collect.OUT.rglob('*'):
        if p.is_file(): inputs[str(p.resolve())] = data.sha(p)
    for r in records:
        if r['record_key'] in known: raise ValueError('Historical ID repeated')
        body = collect.OUT/'evidence'/(r['response_sha256']+'.html')
        page = collect.OUT/'list_cache'/(r['listing_response_sha256']+'.html')
        if data.sha(page) != r['listing_response_sha256']: raise ValueError('Listing body changed')
        cards, _ = collect.listing_page(page.read_bytes(), r['listing_page'], r['sampling_category'])
        card = next((x for x in cards if x['record_key']==r['record_key']), None)
        if not card or any(r[k] != v for k,v in card.items() if k!='detail_url'): raise ValueError('Listing replay differs')
        try:
            if r['fetch']['http_status'] != 200: raise ValueError('Source unavailable')
            row = collect.parse_detail(body.read_bytes(), r)
        except (ValueError, KeyError, TypeError) as exc:
            failed.append(dict(record_key=r['record_key'], reason=str(exc)))
            continue
        checked, proofs = quality(row, catalog)
        row.update(checked)
        rows.append(row)
        sources = [dict(kind='current_title', text=row['title'], sha256=r['response_sha256']),
                   dict(kind='current_seller_body', text=seller_body(row['description']), sha256=r['response_sha256'])]
        values, claims = feature.extract_claims(row['category'], sources, row['area_sqm'] or 0)
        feature_rows.append(dict(record_key=r['record_key'], category=row['category'], **values, training_allowed=False))
        proof_rows += [dict(record_key=r['record_key'], **p) for p in proofs + claims]
    history_path = collect.old.audit.HISTORY/'all_listings_after_review.csv'
    history = data.read(history_path)
    prior = data.read(PRIOR/'all_decisions.csv')
    previous = data.read(PREVIOUS/'decisions_private_DO_NOT_TRAIN.csv')
    # Replace the old refresh versions by their latest available snapshots only
    # for grouping text. Their old labels/cohorts remain unchanged on disk.
    prior_bykey = {r['record_key']:r for r in prior}
    prior_bykey.update({r['record_key']:r for r in previous if r['record_key'] not in {x['record_key'] for x in history}})
    evidence_path = collect.old.audit.SOURCE/'parsed_evidence.json'
    evidence = json.loads(evidence_path.read_text(encoding='utf8'))
    links = json.loads((PREVIOUS/'group_links.json').read_text(encoding='utf8'))
    links += json.loads((PRIOR/'duplicate_links.json').read_text(encoding='utf8'))
    adjudicated = training.previous.CURRENT
    links += json.loads((adjudicated/'additional_group_links.json').read_text(encoding='utf8'))
    paths = [history_path, evidence_path, PRIOR/'all_decisions.csv', PRIOR/'duplicate_links.json',
        PREVIOUS/'decisions_private_DO_NOT_TRAIN.csv', PREVIOUS/'group_links.json',
        adjudicated/'manifest.json', adjudicated/'additional_group_links.json',
        adjudicated/'experiment_reservation.json']
    # Validate archive outputs before using any of them as protected group evidence.
    for root in [PRIOR, PREVIOUS, adjudicated]:
        manifest = json.loads((root/'manifest.json').read_text(encoding='utf8'))
        data.verify(manifest.get('output_sha256', manifest), root)
        paths.append(root/'manifest.json')
    inputs.update({str(p.resolve()): data.sha(p) for p in paths})
    _, _, _, protected = training.previous.context()
    decisions, all_links = grouped_decisions(rows, history, list(prior_bykey.values()), links, evidence)
    fresh = [r for r in decisions if r['dataset_role']=='fresh_reserved']
    summary = dict(raw_ids=len(records), parsed=len(rows), parse_failed=len(failed), known_ids=len(known),
        roles=dict(Counter(r['dataset_role'] for r in decisions)),
        raw_categories=dict(Counter(r['sampling_category'] for r in records)),
        fresh_categories=dict(Counter(r['category'] for r in fresh)),
        flag_counts=dict(Counter(c for r in decisions for c in r['review_codes'])),
        model_fit_allowed=False, independent_evaluation_gate=all(sum(r['category']==c for r in fresh)>=20 for c in data.CATEGORIES),
        training_allowed=False, consumed_evaluation_members=0, property_coordinates_verified=0,
        collection_result=json.loads((collect.OUT/'latest_run.json').read_text(encoding='utf8')))
    tables = dict(decisions_private_DO_NOT_TRAIN=decisions, parse_failed=failed, features_DO_NOT_TRAIN=feature_rows,
                  evidence_private=proof_rows, fresh_RESERVED_DO_NOT_TRAIN=fresh)
    return tables, dict(summary=summary, group_links=all_links), inputs, protected


def verify(root):
    tables, objects, inputs, protected = artifacts()
    manifest = json.loads((root/'manifest.json').read_text(encoding='utf8'))
    if manifest['input_sha256'] != inputs or manifest['protected_sha256'] != protected: raise ValueError('Review source differs')
    if manifest['output_sha256'] != data.outputs(root): raise ValueError('Review output inventory/hash differs')
    for name, rows in tables.items():
        if data.read(root/(name+'.csv')) != training.previous.csv_table(rows)[1]: raise ValueError('Review table differs: '+name)
    for name, obj in objects.items():
        if json.loads((root/(name+'.json')).read_text(encoding='utf8')) != obj: raise ValueError('Review decisions/links differ')
    training.previous.check_unchanged(inputs, protected)
    return dict(verified=True, run_id=root.name, **objects['summary'])


def run():
    with writer_lock(OUT):
        tables, objects, inputs, protected = artifacts()
        fingerprint = hashlib.sha256(training.previous.canonical(inputs).encode()).hexdigest()[:16]
        root = OUT/'runs'/fingerprint
        if root.exists(): return verify(root)
        stage = OUT/'runs'/('.building_'+uuid.uuid4().hex)
        stage.mkdir(parents=True)
        training.write_tables(stage, tables)
        for name, obj in objects.items(): atomic_json(stage/(name+'.json'), obj)
        training.previous.check_unchanged(inputs, protected)
        atomic_json(stage/'manifest.json', dict(input_sha256=inputs, protected_sha256=protected, output_sha256=data.outputs(stage)))
        stage.rename(root)
        result = verify(root)
        atomic_json(OUT/'latest.json', dict(run='runs/'+root.name))
        return result


if __name__=='__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--verify', action='store_true')
    args = parser.parse_args()
    root = OUT/json.loads((OUT/'latest.json').read_text(encoding='utf8'))['run'] if args.verify else None
    print(json.dumps(verify(root) if args.verify else run(), ensure_ascii=False, indent=2))
