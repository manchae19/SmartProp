"""Reconcile current asking-price snapshots with old groups; never train."""
import argparse
from collections import Counter, defaultdict
from datetime import datetime
import hashlib
import json
from pathlib import Path
import re
import uuid

from lxml import html
from lxml.etree import LxmlError
import collect_property_expansion as collect
import property_evidence_claims as claims
import apartment_followup_rules as quality
import review_apartment_extension as grouping
from build_training_v1 import group_records
from market_observations import timestamp

BASE = collect.BASE
OUT = BASE / 'processed/property_expansion_review'


def parse_snapshot(record, body, original=None):
    source = record.get('source', record['record_key'].split(':')[0])
    url, observed = record['fetch']['response_url'], record['observed_at']
    timestamp(observed)
    if record['fetch']['http_status'] != 200:
        raise ValueError('Source not available')
    if source == 'cafeland':
        if original is None:
            card = dict(record, detail_url=url)
        else:
            raw = json.loads(original['raw_json'])
            card = dict(record, source=source, detail_url=url, listing_title=original['title'],
                listing_price_raw=raw.get('price_raw', ''), listing_area_raw=raw.get('area_raw', ''),
                listing_address_raw=original.get('address_raw',''))
        row = collect.cafe.parse_detail(body, card, observed)
        row['source_evidence_flags'] = [x for x in row['source_evidence_flags'] if not x.startswith('listing_detail_')]
    else:
        if original is None:
            raise ValueError('Nhadat refresh requires original identity anchor')
        evidence = collect.audit.parser.parse_detail(original, record['fetch'], body)
        if not evidence['identity_verified'] or not evidence['structure_verified']:
            raise ValueError('Current source identity/structure not verified')
        published, raw_date = '', ''
        try:
            raw_date = collect.nhadat.one(html.fromstring(body), 'txtNgaydang').get('value','')
            match = re.match(r'(\d{1,2}/\d{1,2}/\d{4})', raw_date)
            published = datetime.strptime(match[1], '%d/%m/%Y').date().isoformat() if match else ''
        except (ValueError, TypeError):
            pass
        price = collect.cafe.cafe.price(evidence['price_raw'])
        area = collect.cafe.cafe.area(evidence['area_raw'])
        flags = list(evidence['flags'])
        if price is None: flags.append('missing_or_non_total_price')
        if area is None: flags.append('missing_structured_area')
        if not published: flags.append('missing_or_invalid_source_date')
        if not evidence['sale_verified']: flags.append('not_verified_sale')
        category = evidence['category']
        row = dict(record, source=source, detail_url=url, title=evidence['title'],
            source_category='ban-can-ho-chung-cu' if category == claims.APARTMENT else 'unknown', category=category,
            transaction_type='sale' if evidence['sale_verified'] else 'unknown', target_type='asking_price',
            currency='VND' if price is not None else '', currency_basis='literal_source_ty_trieu_units',
            identity_basis='response_listing_id_and_source_title_match', price_raw=evidence['price_raw'],
            price_million=price, area_raw=evidence['area_raw'], area_sqm=area,
            address_raw=evidence['address_raw'], source_location_parts=[x.strip() for x in evidence['address_raw'].split(',')],
            description=evidence.get('asset_description', evidence['description']), rooms=None,
            source_published_date_raw=raw_date, source_published_date=published,
            source_evidence_flags=flags, collected_at=observed, response_sha256=record['response_sha256'])
    row['observed_at'] = observed
    row['source_date_semantics'] = 'Displayed posting/update metadata, not past observation time'
    row['label_basis'] = 'Current price and property claims from same response'
    row['training_allowed'] = False
    return row


def classify_groups(current, history, prior_rows, evidence, catalog, train_keys, prior_links=()):
    current_keys = {r['record_key'] for r in current}
    history_bykey = {r['record_key']: r for r in history}
    old = [r for r in history if r['record_key'] not in current_keys] + prior_rows
    old_groups = defaultdict(list)
    for row in history:
        if row.get('pipeline_group'):
            old_groups[row['pipeline_group']].append(row['record_key'])
    for row in prior_rows:
        if row.get('property_candidate_group'):
            old_groups[row['property_candidate_group']].append(row['record_key'])
    pairs = list(prior_links)
    for members in old_groups.values():
        pairs.extend(dict(left=members[0], right=k, rule='preserve_frozen_group', title_similarity=1) for k in members[1:])
    prepared = [dict(r, description=grouping.dedup_text(r['description'])) for r in current]
    old_evidence = {k: dict(v, description=grouping.dedup_text(v.get('description','')),
        **({'asset_description':grouping.dedup_text(v['asset_description'])} if 'asset_description' in v else {})) for k,v in evidence.items()}
    old_evidence.update({r['record_key']:dict(identity_verified=True, description=grouping.dedup_text(r['description'])) for r in prior_rows})
    pairs += grouping.previous.old.extra_pairs(prepared, old, old_evidence)
    membership, links = group_records([dict(r) for r in current + old], pairs)
    protected = {r['record_key'] for r in history if r.get('protected_holdout') == 'True' or
                 set(r.get('reserved_splits','').split(';')) & {'validation','test'}}
    protected.update(r['record_key'] for r in prior_rows)
    protected_groups = {membership[k] for k in protected}
    historical_groups = {membership[r['record_key']] for r in history + prior_rows}
    assessed = {r['record_key']: quality.quality(r, catalog) for r in current}
    exclusions = {r['record_key']: quality.scope_exclusions(r)[0] for r in current}
    grouped = defaultdict(list)
    for r in current: grouped[membership[r['record_key']]].append(r)
    decisions = []
    for group, members in grouped.items():
        issues = []
        if group in protected_groups: issues.append('linked_to_protected_or_prior_batch')
        if any(assessed[r['record_key']]['review_codes'] or exclusions[r['record_key']] for r in members):
            issues.append('current_group_contains_unresolved_member')
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            values = [r[field] for r in members if r[field] is not None]
            if values and (max(values) <= 0 or (max(values)-min(values))/max(values) > tolerance): issues.append('current_group_'+field+'_conflict')
        if len({assessed[r['record_key']]['location_feature'] for r in members}) > 1:
            issues.append('current_group_location_conflict')
        representatives = sorted(r['record_key'] for r in members if r['record_key'] in train_keys)
        representative = representatives[0] if representatives else min(r['record_key'] for r in members)
        for row in members:
            key = row['record_key']
            role = 'needs_source_review' if issues else 'suppressed_current_duplicate' if key != representative else (
                'refreshed_train_group_candidate' if key in train_keys else
                'linked_historical_group_candidate' if group in historical_groups else 'fresh_group_candidate')
            decisions.append(dict(row, **assessed[key], exclusion_codes=exclusions[key],
                overlay_group=group, original_pipeline_group=history_bykey.get(key,{}).get('pipeline_group',''),
                group_review_codes=issues, candidate_role=role, spatial_features_ready=False))
    return decisions, links


def artifacts():
    parts, original, parsed, fetched, _, source_paths, protected = collect.audit.read_context()
    history = list(original.values())
    old_pilot, old_nhadat, _, evidence, catalog, _ = grouping.previous.context()
    old_rows = old_pilot + old_nhadat + grouping.extension_rows()
    prior = {r['record_key']:r for r in collect.audit.c.read(collect.PRIOR / 'all_decisions.csv')}
    for row in old_rows:
        row['property_candidate_group'] = prior[row['record_key']]['property_candidate_group']
    source_paths += [collect.PRIOR / 'all_decisions.csv', Path(__file__), Path(claims.__file__),
        Path(quality.__file__), Path(grouping.__file__), BASE/'review_apartment_pilot.py',
        BASE/'build_training_v1.py', BASE/'collect_property_expansion.py', collect.PROTOCOL,
        BASE/'review_apartment_followup.py', BASE/'review_apartment_labels.py', BASE/'remaining_diversity_rules.py',
        BASE/'collect_apartment_followup.py', Path(collect.cafe.__file__), Path(collect.cafe.cafe.__file__),
        collect.pilot.CATALOG, collect.PRIOR/'duplicate_links.json']
    for root in [collect.cafe.OUT, collect.nhadat.OUT, grouping.collector.OUT, BASE/'data_raw/apartment_topup_40']:
        source_paths += list(root.glob('*.json')) + list(root.glob('*.jsonl')) + list(root.glob('*.csv'))
        source_paths += list((root/'detail_cache').glob('*.html'))
    records, failed, current = [], [], []
    roots = [collect.audit.SUPPLEMENT, collect.ROOT/'refresh_cafeland', collect.ROOT/'refresh_nhadat24h', collect.ROOT/'new_cafeland_60']
    for root in roots:
        if (root/'collector.lock').exists(): raise ValueError('Collection still in progress')
        source_paths += [p for p in root.glob('*.json')]
        for metadata in sorted((root/'records').glob('*.json')):
            record = json.loads(metadata.read_text(encoding='utf8'))
            path = root/'evidence'/(record['response_sha256']+'.html')
            if collect.cafe.sha(path) != record['response_sha256']: raise ValueError('Response hash differs')
            source_paths.extend([metadata,path])
            is_new = root.name == 'new_cafeland_60'
            if is_new:
                list_path = root/'list_cache'/(record['listing_response_sha256']+'.html')
                if collect.cafe.sha(list_path) != record['listing_response_sha256']: raise ValueError('Listing hash differs')
                cards,_ = collect.cafe.listing_page(list_path.read_bytes(), record['listing_page'])
                card = next((c for c in cards if c['record_key'] == record['record_key']),None)
                if not card or any(record[k] != card[k] for k in card if k != 'detail_url'):
                    raise ValueError('Listing card replay differs')
                source_paths.append(list_path)
            records.append(record)
            try:
                row = parse_snapshot(record, path.read_bytes(), None if is_new else original[record['record_key']])
                current.append(row)
            except (ValueError,KeyError,TypeError,IndexError,LxmlError) as exc:
                failed.append(dict(record_key=record['record_key'], observed_at=record['observed_at'],
                    source=record['record_key'].split(':')[0], response_sha256=record['response_sha256'],
                    reason=type(exc).__name__+': '+str(exc), training_allowed=False))
    if len(records) != len({r['record_key'] for r in records}): raise ValueError('Snapshot IDs repeated across batches')
    decisions, links = classify_groups(current, history, old_rows, evidence, catalog,
        {r['record_key'] for r in parts['train']},
        json.loads((collect.PRIOR/'duplicate_links.json').read_text(encoding='utf8')))
    feature_rows, proof_rows = [], []
    for row in decisions:
        sources = [dict(kind='current_observed_title', text=row['title'], sha256=row['response_sha256']),
                   dict(kind='current_observed_body', text=row['description'], sha256=row['response_sha256'])]
        values, proofs = claims.extract(row['category'], sources, observed_year=timestamp(row['observed_at']).year)
        feature_rows.append(dict(record_key=row['record_key'], observed_at=row['observed_at'],
            price_million=row['price_million'], area_sqm=row['area_sqm'], category=row['category'],
            location_feature=row['location_feature'], overlay_group=row['overlay_group'], candidate_role=row['candidate_role'],
            **values, training_allowed=False, spatial_features_ready=False))
        proof_rows += [dict(record_key=row['record_key'], observed_at=row['observed_at'], **p) for p in proofs]
    train_keys = {r['record_key'] for r in parts['train']}
    summary = dict(raw_snapshots=len(records), parsed_current_snapshots=len(current), parse_failed=len(failed),
        new_ids=sum(r['record_key'] not in original and r['record_key'] not in prior for r in records),
        refreshed_train_ids=sum(r['record_key'] in train_keys for r in records),
        outcomes=dict(Counter(r['candidate_role'] for r in decisions)),
        new_outcomes=dict(Counter(r['candidate_role'] for r in decisions if r['record_key'] not in original)),
        refresh_outcomes=dict(Counter(r['candidate_role'] for r in decisions if r['record_key'] in train_keys)),
        source_quality_passed=sum(not r['review_codes'] and not r['exclusion_codes'] for r in decisions),
        current_price_changed_vs_old=sum(r['record_key'] in original and r['price_million'] is not None and
            abs(r['price_million']-float(original[r['record_key']]['price_million'])) > .01 for r in decisions),
        geo_features_ready=0, model_trained=False, old_cohorts_changed=False, pilot_scored=False,
        note='Source asking-price candidates; IDs/groups not independently verified properties. All outputs DO_NOT_TRAIN.')
    inputs = {str(p.resolve()):collect.cafe.sha(p) for p in set(source_paths) if p.is_file()}
    return decisions, failed, feature_rows, proof_rows, links, summary, inputs, protected


def main():
    parser = argparse.ArgumentParser(description=__doc__); parser.add_argument('--verify',action='store_true'); args=parser.parse_args()
    decisions, failed, features, proofs, links, summary, inputs, protected = artifacts()
    run_id = hashlib.sha256(json.dumps(inputs,sort_keys=True).encode()).hexdigest()[:16]
    target = OUT/'runs'/run_id
    sets = dict(decisions_private_DO_NOT_TRAIN=decisions, parse_failures=failed,
                current_snapshots_DO_NOT_TRAIN=features, evidence_private_DO_NOT_TRAIN=proofs)
    fields = {name:list(dict.fromkeys(k for r in rows for k in r)) for name,rows in sets.items()}
    fields['parse_failures'] = ['record_key','observed_at','source','response_sha256','reason','training_allowed']
    scalar = grouping.previous.scalar
    if target.exists():
        manifest=json.loads((target/'manifest.json').read_text(encoding='utf8'))
        collect.audit.c.verify(manifest['output_sha256'],target)
        for name,rows in sets.items():
            expected=[{k:scalar(r.get(k)) for k in fields[name]} for r in rows]
            if collect.audit.c.read(target/(name+'.csv')) != expected: raise ValueError('Snapshot/feature replay differs')
        if json.loads((target/'group_links.json').read_text(encoding='utf8')) != links: raise ValueError('Group replay differs')
        print(json.dumps(dict(verified=True,run_id=run_id,snapshots=len(features)),ensure_ascii=False));return
    if args.verify: raise ValueError('Build matching input version first')
    stage=OUT/'runs'/('.building_'+uuid.uuid4().hex);stage.mkdir(parents=True)
    for name,rows in sets.items():
        collect.audit.c.write_csv(stage/(name+'.csv'),[{k:scalar(r.get(k)) for k in fields[name]} for r in rows],fields[name])
    summary['run_id']=run_id
    collect.audit.c.write_json(stage/'summary.json',summary);collect.audit.c.write_json(stage/'group_links.json',links)
    (stage/'README.md').write_text('# Snapshot giá/đặc trưng cùng phản hồi\n\n'
        'Giá hiện tại được parse lại từ HTML cùng thời điểm của đặc trưng. Nhãn/split cũ không ghi đè. '
        'Dùng grouping overlay để giữ liên kết cũ và phát hiện quan hệ mới; không đổi registry hoặc chấm pilot. '
        'Các trạng thái candidate vẫn cần review, chưa phát hành X. Tọa độ/POI giữ missing.\n',encoding='utf8')
    for path,expected in {**inputs,**protected}.items():
        candidate=Path(path) if Path(path).is_absolute() else BASE/path
        if collect.cafe.sha(candidate)!=expected: raise ValueError('Source changed')
    collect.audit.c.write_json(stage/'manifest.json',dict(input_sha256=inputs,protected_sha256=protected,output_sha256=collect.audit.c.outputs(stage)))
    stage.rename(target);collect.audit.c.write_json(OUT/'latest.json',dict(run='runs/'+run_id))
    print(json.dumps(summary,ensure_ascii=False,indent=2));print(target)


if __name__=='__main__':main()
