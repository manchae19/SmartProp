"""Step18.3: read-only recovery import planner. There is deliberately no apply mode.

Reuses the existing quality gate on isolated copies. Never invokes its SQL builder
or importer. Evidence is a historical snapshot, not owner/legal verification.
"""
import argparse
import contextlib
import copy
import csv
import hashlib
import importlib.util
import io
import json
import re
import unicodedata
from collections import Counter, defaultdict
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import urlsplit

import import_external_listings as legacy

ROOT = Path(__file__).resolve().parents[2]
AUDIT = ROOT / '.scratch/hybrid-full-audit'
DEFAULT_OUTPUT = AUDIT / 'step18-3'

def rows(path):
    with path.open(encoding='utf-8-sig', newline='') as stream:
        return list(csv.DictReader(stream))

def norm(value):
    value = unicodedata.normalize('NFD', str(value or '').lower()).replace('đ', 'd')
    return ' '.join(re.sub(r'[^a-z0-9 ]', ' ', ''.join(c for c in value if not unicodedata.combining(c))).split())

def truth(value):
    return str(value).lower() in {'true', '1'}

def decimal(value):
    try:
        result = Decimal(str(value))
        return result if result.is_finite() else Decimal(0)
    except (InvalidOperation, ValueError):
        return Decimal(0)

def write_csv(path, items):
    if not items:
        path.write_text('record_key\n', encoding='utf-8-sig')
        return
    with path.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(items[0]))
        writer.writeheader()
        writer.writerows(items)

def read_local():
    spec = importlib.util.spec_from_file_location('read_local', ROOT / 'backend/scripts/flyway-local-forward.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    client = module.Local()
    identity = client.objects("SELECT JSON_OBJECT('database',DATABASE(),'port',@@port,'server_uuid',@@server_uuid,'version',VERSION())")[0]
    if identity['database'] != 'smartprop' or identity['port'] != 3306 or identity['server_uuid'] != module.SERVER_UUID:
        raise RuntimeError('Wrong MySQL Local target')
    return client, identity

def evidence_reasons(row, parsed, manifest):
    key = row['record_key']; p = parsed.get(key, {}); m = manifest.get(key, {})
    reasons = []
    path = (ROOT / row['evidence_path']).resolve()
    cache = (ROOT / 'ai-services/app/data/processed/collection_source_review/detail_cache').resolve()
    if not path.is_relative_to(cache) or not path.is_file():
        reasons.append('MISSING_OR_UNSAFE_EVIDENCE_PATH')
    elif hashlib.sha256(path.read_bytes()).hexdigest() != p.get('detail_sha256') or p.get('detail_sha256') != m.get('sha256'):
        reasons.append('EVIDENCE_HASH_MISMATCH')
    if p.get('record_key') != key or p.get('http_status') != 200 or m.get('http_status') != 200 or not p.get('identity_verified') or not p.get('structure_verified'):
        reasons.append('EVIDENCE_IDENTITY_OR_STRUCTURE')
    url = urlsplit(row.get('detail_url', ''))
    if url.scheme not in {'http', 'https'} or not url.hostname or url.username or url.password or m.get('requested_url') != row['detail_url'] or m.get('response_url') != row['detail_url']:
        reasons.append('SOURCE_URL_OR_REDIRECT_MISMATCH')
    if not p.get('sale_verified') or row.get('normalized_transaction_type') != 'SALE':
        reasons.append('SALE_NOT_EVIDENCED')
    if p.get('flags'):
        reasons.append('SOURCE_PARSER_FLAGS')
    if p.get('category') != row.get('normalized_category'):
        reasons.append('CATEGORY_REQUIRES_SOURCE_REVIEW')
    if norm(row.get('normalized_district')) not in norm(p.get('address_raw')):
        reasons.append('DISTRICT_INFERENCE_REQUIRES_REVIEW')
    for field, source_field in [('normalized_price_million','price_million'), ('normalized_area_sqm','area_sqm')]:
        if decimal(row.get(field)) <= 0 or decimal(row.get(field)) != decimal(p.get(source_field)):
            reasons.append('SOURCE_' + source_field.upper() + '_MISMATCH')
    price = decimal(row.get('normalized_price_million')) * 1000000
    if price != decimal(row.get('normalized_price_vnd')) or price > Decimal('999999999999999'):
        reasons.append('PRICE_UNIT_OR_RANGE')
    if decimal(row.get('normalized_area_sqm')) > Decimal('1000000'):
        reasons.append('AREA_RANGE')
    if row.get('normalized_category') not in {'Nhà ở','Đất nền','Căn hộ chung cư'}:
        reasons.append('UNSUPPORTED_CATEGORY')
    if truth(row.get('is_protected_holdout')) or truth(row.get('group_has_holdout')):
        reasons.append('PROTECTED_HOLDOUT')
    return reasons

def new_records_only(records, existing_keys):
    """Insert-only planning: a repeated key is a no-op, never an UPDATE."""
    seen = set(existing_keys); new = []
    for row in sorted(records, key=lambda r:r['record_key']):
        if row['record_key'] not in seen:
            seen.add(row['record_key']); new.append(row)
    return new

def merged_groups(keys, groups):
    """Conservative union of prior and gate clusters; never split a known group."""
    parent = {k:k for k in keys}
    def find(k):
        while parent[k] != k:
            parent[k] = parent[parent[k]];k = parent[k]
        return k
    for members in groups:
        members = sorted(set(members) & parent.keys())
        for k in members[1:]:parent[find(k)] = find(members[0])
    components = defaultdict(set)
    for k in parent:components[find(k)].add(k)
    return {k:components[find(k)] for k in parent}

def build_insert_only_preview(prepared, groups):
    """Offline SQL artifact for review, never executed by this program.

    Reuse legacy literal escaping and field conventions, replacing its UPDATE
    behavior with insert-only anti-joins. Existing keys are untouched on repeats.
    A future execution adapter must recheck the manifest/target and holdout links.
    """
    quote = legacy.escape_sql
    sql = ['-- REVIEW ONLY: requires a new explicit write approval and fresh preflight.',
           '-- No execution path in prepare_recovered_external.py.',
           'SET NAMES utf8mb4;', 'START TRANSACTION;']
    def insert(table, key, columns, values):
        sql.append('INSERT INTO '+table+' ('+', '.join(columns)+')\nSELECT '+', '.join(quote(v) for v in values)+
            '\nFROM (SELECT 1 AS n) AS input_row LEFT JOIN '+table+' AS existing_row ON existing_row.'+key+'='+quote(values[0])+
            '\nWHERE existing_row.'+key+' IS NULL;')
    for g in groups:
        member = next(p for p in prepared if p['duplicate_group']==g['group_id'])
        columns=['group_id','name','category','district','listing_count','min_price','max_price','min_area','max_area']
        values=[g['group_id'],'Nhóm nghi trùng phục hồi; chưa xác minh',member['category'],member['district'],g['listing_count']]+[Decimal(g[f]) for f in ['min_price','max_price','min_area','max_area']]
        insert('external_duplicate_groups','group_id',columns,values)
    for p in sorted(prepared,key=lambda p:p['record_key']):
        from datetime import datetime,timezone
        collected = None
        if p['collected_at']:
            observed=datetime.fromisoformat(p['collected_at'].replace('Z','+00:00'))
            if observed.tzinfo is None:raise ValueError('collected_at needs timezone')
            collected=observed.astimezone(timezone.utc).strftime('%Y-%m-%d %H:%M:%S.%f')
        columns=['record_key','source','source_listing_id','title','detail_url','category','transaction_type','transaction_basis',
                 'price','price_million','area_sqm','price_per_sqm_million','district','address_raw','quality_status','quality_issues',
                 'verification_status','duplicate_group','is_duplicate','is_protected_holdout','collected_at','raw_metadata']
        values=[p['record_key'],p['source'],p['source_listing_id'],p['title'],p['detail_url'],p['category'],'SALE',p['transaction_basis'],
                Decimal(p['price_vnd']),Decimal(p['price_million']),Decimal(p['area_sqm']),None,p['district'],p['address_raw'],
                p['quality_status'],p['quality_issues'],'UNVERIFIED',p['duplicate_group'] or None,bool(p['duplicate_group']),
                p['protected_holdout'],collected,json.dumps(dict(p,recovery_stage='STEP18_3_DRY_RUN'),ensure_ascii=False)]
        insert('external_listings','record_key',columns,values)
    sql.append('COMMIT;')
    return '\n\n'.join(sql)+'\n'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--dry-run', action='store_true', help='Read-only; also the only supported/default mode')
    parser.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    args = parser.parse_args(); out = args.output.resolve()
    if not out.is_relative_to(DEFAULT_OUTPUT.resolve()):
        raise ValueError('Output must stay inside step18-3; recovery inputs are immutable')
    out.mkdir(parents=True, exist_ok=True)
    recovered = rows(AUDIT / 'step18-2/recovered_hybrid_candidates.csv')
    auto = rows(AUDIT / 'step18-2/auto_recoverable.csv')
    decisions = rows(AUDIT / 'step18-2/recovery_decision_audit.csv')
    previous = rows(AUDIT / 'hybrid_candidates.csv')
    all_pipeline = rows(ROOT / 'ai-services/app/data/processed/remaining_diversity_review/runs/518bbc989587326c/all_listings_after_review.csv')
    parsed = json.loads((ROOT/'ai-services/app/data/processed/collection_source_review/parsed_evidence.json').read_text(encoding='utf8'))
    manifest = json.loads((ROOT/'ai-services/app/data/processed/collection_source_review/fetch_manifest.json').read_text(encoding='utf8'))
    # Reparse every archived HTML with the existing identity/container parser.
    # This imports its functions only; no crawl, review persistence or training runs.
    import sys
    sys.path.insert(0,str(ROOT/'ai-services/app/data'))
    from review_source_details import parse_detail
    reparsed = {}
    for r in recovered:
        path = (ROOT/r['evidence_path']).resolve()
        if not path.is_relative_to((ROOT/'ai-services/app/data/processed/collection_source_review/detail_cache').resolve()) or not path.is_file():
            continue
        value = parse_detail(r,manifest.get(r['record_key'],{}),path.read_bytes())
        value.update(record_key=r['record_key'],detail_sha256=hashlib.sha256(path.read_bytes()).hexdigest(),http_status=manifest.get(r['record_key'],{}).get('http_status'))
        reparsed[r['record_key']] = value
    assert len(recovered) == len({r['record_key'] for r in recovered}) == 799 and recovered == auto
    assert len(previous) == len({r['record_key'] for r in previous}) == 1792
    assert len(decisions) == len({r['record_key'] for r in decisions}) == 3338
    client, identity = read_local()
    checksum_sql = 'CHECKSUM TABLE properties,property_images,external_listings,external_duplicate_groups,flyway_schema_history EXTENDED'
    before = client.query(checksum_sql)
    for table in ['external_listings','external_duplicate_groups']:
        (out/(table+'-schema.txt')).write_text(client.query('SHOW CREATE TABLE '+table),encoding='utf8')
    history = client.objects("SELECT JSON_OBJECT('version',version,'type',type,'checksum',checksum,'success',success) FROM flyway_schema_history ORDER BY installed_rank")
    tables = int(client.query("SELECT COUNT(*) FROM information_schema.tables WHERE table_schema='smartprop' AND table_type='BASE TABLE'"))
    existing = client.objects("""SELECT JSON_OBJECT('record_key',record_key,'source',source,'source_listing_id',source_listing_id,
      'title',title,'detail_url',detail_url,'category',category,'district',district,'address_raw',address_raw,
      'price_million',CAST(price_million AS CHAR),'area_sqm',CAST(area_sqm AS CHAR),'duplicate_group',duplicate_group,
      'quality_status',quality_status,'verification_status',verification_status,'quality_issues',quality_issues,
      'is_protected_holdout',is_protected_holdout,'is_duplicate',is_duplicate,'transaction_type',transaction_type)
      FROM external_listings ORDER BY record_key""")
    properties = client.objects("""SELECT JSON_OBJECT('record_key',id,'title',title,'category',property_type,'district',district,
      'address_raw',address,'price',CAST(price AS CHAR),'area_sqm',CAST(area_sqm AS CHAR),'status',status,
      'transaction_type',transaction_type,'currency',currency,'price_unit',price_unit,
      'latitude',ST_Latitude(location),'longitude',ST_Longitude(location)) FROM properties ORDER BY id""")
    groups = int(client.query('SELECT COUNT(*) FROM external_duplicate_groups'))
    if tables != 48 or len(existing) != 3204 or len(properties) != 16 or groups != 332:
        raise RuntimeError('Unexpected Local inventory; stop without writes')
    # The quality gate mutates transaction_type: use copies only after independent SALE checks.
    normalized = []
    for r in recovered:
        d = dict(r, category=r['normalized_category'],district=r['normalized_district'],
                 price_million=r['normalized_price_million'],area_sqm=r['normalized_area_sqm'])
        normalized.append(d)
    combined = copy.deepcopy(existing + normalized)
    with contextlib.redirect_stdout(io.StringIO()):
        gate_groups = legacy.run_quality_gate(combined)
    by_key = {r['record_key']:r for r in combined}
    related = defaultdict(set)
    for g in gate_groups:
        for k in g['members']:related[k].update(g['members'])
    existing_keys = {r['record_key'] for r in existing}
    existing_source_ids = {(r['source'],str(r['source_listing_id'])) for r in existing}
    previous_keys = {r['record_key'] for r in previous}
    previous_groups = {r['pipeline_group'] for r in previous if r.get('pipeline_group')}
    pipeline_by_key = {r['record_key']:r for r in all_pipeline}
    def pipeline_group(r):
        p = pipeline_by_key.get(r['record_key'], {})
        return r.get('pipeline_group') or p.get('pipeline_group')
    pipeline_members = defaultdict(set)
    for r in combined:
        if pipeline_group(r):pipeline_members[pipeline_group(r)].add(r['record_key'])
    related = merged_groups([r['record_key'] for r in combined], [g['members'] for g in gate_groups] + list(pipeline_members.values()))
    holdout_keys = {r['record_key'] for r in existing if truth(r['is_protected_holdout'])}
    holdout_keys.update(r['record_key'] for r in all_pipeline if truth(r.get('protected_holdout')))
    held_pipeline_groups = {pipeline_group(r) for r in all_pipeline if r['record_key'] in holdout_keys} - {None,''}
    old_pipeline_groups = {pipeline_group(r) for r in existing} - {None,''}
    held_db_groups = {r['duplicate_group'] for r in existing if r['record_key'] in holdout_keys} - {None,''}
    held_members = {r['record_key'] for r in existing if r['duplicate_group'] in held_db_groups} | holdout_keys
    plan = []; evidence_counts = Counter(); blocked_counts = Counter()
    for r in recovered:
        k = r['record_key']; reasons = evidence_reasons(r, parsed, manifest)
        original_pipeline = pipeline_by_key.get(k,{})
        latest = reparsed.get(k,{})
        if any(latest.get(f) != parsed.get(k,{}).get(f) for f in ['identity_verified','structure_verified','sale_verified','category','price_million','area_sqm','address_raw','flags']):
            reasons.append('ARCHIVED_REPARSE_DIFFERS')
        evidence_counts.update(reasons)
        gate = by_key[k]; pg = pipeline_group(r)
        same_group = related[k]
        if k in existing_keys or (r['source'],str(r['source_listing_id'])) in existing_source_ids:
            reasons.append('ALREADY_EXISTS')
        if pg in held_pipeline_groups or same_group & held_members or any(pipeline_group(by_key[s]) in held_pipeline_groups for s in same_group):
            reasons.append('POSSIBLE_PROTECTED_GROUP_OVERLAP')
        if pg in old_pipeline_groups or same_group & existing_keys:
            reasons.append('POSSIBLE_EXISTING_DUPLICATE_REQUIRES_RECONCILIATION')
        if pg in previous_groups:
            reasons.append('PIPELINE_GROUP_OVERLAP_1792')
        # Cross-platform matching is a review signal, never proof of one asset.
        platform_matches = []
        for p in properties:
            title_match = legacy.jaccard(legacy.tokenize(r['title']),legacy.tokenize(p['title'])) >= .65
            address_match = bool(legacy.clean_address(r['address_raw'])) and legacy.clean_address(r['address_raw']) == legacy.clean_address(p['address_raw'])
            if decimal(p['price']) > 0 and decimal(p['area_sqm']) > 0 and (title_match or address_match) and abs(decimal(r['normalized_area_sqm'])-decimal(p['area_sqm']))/max(decimal(r['normalized_area_sqm']),decimal(p['area_sqm'])) <= Decimal('.03'):
                platform_matches.append(p['record_key'])
        if platform_matches:reasons.append('POSSIBLE_PLATFORM_DUPLICATE')
        if gate['quality_status'] == 'REJECTED' or set(gate['quality_issues']) - {'NEAR_DUPLICATE','MISSING_DISTRICT'}:
            reasons.append('QUALITY_GATE_BLOCKED')
        siblings = sorted(same_group - existing_keys) or [k]
        stable_group = 'recovered18_' + hashlib.sha256('|'.join(siblings).encode()).hexdigest()[:24] if len(siblings)>1 else ''
        quality_issues = list(gate['quality_issues'])
        if len(same_group)>1 and 'NEAR_DUPLICATE' not in quality_issues:quality_issues.append('NEAR_DUPLICATE')
        quality_status = 'NEEDS_REVIEW' if quality_issues and gate['quality_status']=='VALID' else gate['quality_status']
        # Match actual DECIMAL precision/scale; never silently round imported labels.
        for field,scale,maximum in [('normalized_price_million',2,Decimal('999999999999.99')),('normalized_area_sqm',2,Decimal('99999999.99'))]:
            value = decimal(r.get(field))
            if value > maximum or value != value.quantize(Decimal(1).scaleb(-scale)):
                reasons.append('MYSQL_DECIMAL_PRECISION_REQUIRES_REVIEW')
        if len(r['title'])>500 or len(r['source_listing_id'])>100 or len(r['record_key'])>100 or not r['record_key'].isascii():
            reasons.append('MYSQL_TEXT_CONSTRAINT_REQUIRES_REVIEW')
        blocked_counts.update(set(reasons))
        plan.append(dict(record_key=k,source=r['source'],source_listing_id=r['source_listing_id'],title=r['title'],detail_url=r['detail_url'],
            category=r['normalized_category'],district=r['normalized_district'],address_raw=r['address_raw'],
            price_million=str(decimal(r['normalized_price_million'])),price_vnd=str(decimal(r['normalized_price_million'])*1000000),
            area_sqm=str(decimal(r['normalized_area_sqm'])),transaction_type=r['normalized_transaction_type'],
            transaction_basis='ARCHIVED_SOURCE_SALE_EVIDENCE',verification_status='UNVERIFIED',protected_holdout=truth(r.get('is_protected_holdout')),
            quality_status=quality_status,quality_issues=json.dumps(quality_issues,ensure_ascii=False),
            duplicate_group=stable_group,pipeline_group=pg or '',possible_existing_matches='|'.join(sorted(same_group & existing_keys)),
            possible_platform_matches='|'.join(platform_matches),evidence_path=r['evidence_path'],evidence_sha256=parsed.get(k,{}).get('detail_sha256',''),
            assigned_split=original_pipeline.get('assigned_split',''),reserved_splits=original_pipeline.get('reserved_splits',''),
            training_allowed=original_pipeline.get('training_allowed',''),original_pipeline_protected_holdout=original_pipeline.get('protected_holdout',''),
            original_price_million=original_pipeline.get('original_price_million',''),original_area_sqm=original_pipeline.get('original_area_sqm',''),
            original_category=original_pipeline.get('original_category',''),original_review_codes=original_pipeline.get('review_codes',''),
            original_pipeline_status=original_pipeline.get('status',''),
            evidence_fetched_at_utc=manifest.get(k,{}).get('fetched_at_utc',''),
            latitude=r.get('latitude',''),longitude=r.get('longitude',''),
            collected_at=r['collected_at'],decision='BLOCKED_PENDING_REVIEW' if reasons else 'PREPARED_UNVERIFIED_ONLY',reasons='|'.join(sorted(set(reasons)))))
    prepared = [p for p in plan if p['decision']=='PREPARED_UNVERIFIED_ONLY']
    group_plan = []
    for gid in sorted({p['duplicate_group'] for p in prepared if p['duplicate_group']}):
        members = [p for p in prepared if p['duplicate_group']==gid]
        group_plan.append(dict(group_id=gid,listing_count=len(members),members='|'.join(sorted(p['record_key'] for p in members)),
            min_price=str(min(decimal(p['price_vnd']) for p in members)),max_price=str(max(decimal(p['price_vnd']) for p in members)),
            min_area=str(min(decimal(p['area_sqm']) for p in members)),max_area=str(max(decimal(p['area_sqm']) for p in members)),
            matching_basis='SUSPECTED_ADDRESS_PRICE_AREA_TITLE_HEURISTIC_NOT_PHYSICAL_PROOF'))
    first = new_records_only(prepared,existing_keys)
    second = new_records_only(prepared,existing_keys | {r['record_key'] for r in first})
    assert not second and first == new_records_only(list(reversed(prepared)),existing_keys)
    preview = build_insert_only_preview(prepared,group_plan)
    # Source-to-source title/address heuristic adds review candidates, not location/ownership proof.
    after = client.query(checksum_sql)
    if before != after:raise RuntimeError('Source database changed during audit; review before proceeding')
    write_csv(out/'recovered_import_plan.csv',plan);write_csv(out/'prepared_unverified.csv',prepared)
    write_csv(out/'prepared_duplicate_groups.csv',group_plan)
    (out/'IMPORT_PREVIEW_DO_NOT_EXECUTE.sql').write_text(preview,encoding='utf8')
    (out/'mysql-external-snapshot.json').write_text(json.dumps(existing,ensure_ascii=False,indent=2),encoding='utf8')
    (out/'mysql-properties-snapshot.json').write_text(json.dumps(properties,ensure_ascii=False,indent=2),encoding='utf8')
    summary = dict(mode='DRY_RUN_ONLY',database_writes=0,identity=identity,tables=tables,flyway_history=history,
        recovery_input=len(decisions),recovery_decisions=dict(Counter(r['decision_code'] for r in decisions)),
        recovered=len(recovered),existing_external=len(existing),existing_properties=len(properties),existing_groups=groups,
        existing_quality=dict(Counter(r['quality_status'] for r in existing)),existing_verification=dict(Counter(r['verification_status'] for r in existing)),
        existing_protected=sum(truth(r['is_protected_holdout']) for r in existing),existing_suspected=sum(truth(r['is_duplicate']) for r in existing),
        new_source_keys=sum(r['record_key'] not in existing_keys for r in recovered),
        new_source_identities=sum((r['source'],r['source_listing_id']) not in existing_source_ids for r in recovered),
        previous_candidates=len(previous),previous_candidates_in_mysql=len(previous_keys & existing_keys),
        previous_candidate_keys_missing_mysql=sorted(previous_keys-existing_keys),
        recovered_key_overlap_previous=len({r['record_key'] for r in recovered}&previous_keys),
        recovered_pipeline_groups=len({pipeline_group(r) or r['record_key'] for r in recovered}),
        recovered_conservative_components=len({tuple(sorted(related[r['record_key']])) for r in recovered}),
        recovered_direct_holdout=sum(truth(r.get('is_protected_holdout')) or truth(r.get('group_has_holdout')) for r in recovered),
        cross_source_heuristic_components=len({tuple(sorted(related[r['record_key']])) for r in recovered if len({by_key[k]['source'] for k in related[r['record_key']]})>1}),
        pipeline_group_overlap_previous=len({pipeline_group(r) for r in recovered}&previous_groups),
        evidence_failures=dict(evidence_counts),blocked_reason_counts=dict(blocked_counts),
        archived_html_reparsed=len(reparsed),archived_reparse_mismatches=sum('ARCHIVED_REPARSE_DIFFERS' in p['reasons'] for p in plan),
        prepared_quality=dict(Counter(r['quality_status'] for r in prepared)),
        prepared_sources=dict(Counter(r['source'] for r in prepared)),
        prepared_real_coordinate_fields=sum(bool(r['latitude'] or r['longitude']) for r in prepared),
        source_category=dict(Counter(r['normalized_category'] for r in recovered)),
        source_district=dict(Counter(r['normalized_district'] for r in recovered)),
        quality_gate_recovered=dict(Counter(by_key[r['record_key']]['quality_status'] for r in recovered)),
        prepared_insert_only=len(prepared),prepared_suspected_groups=len({r['duplicate_group'] for r in prepared if r['duplicate_group']}),
        prepared_demo_representatives=len({r['duplicate_group'] or r['record_key'] for r in prepared}),
        prepared_public_eligible=0,idempotence_offline_first=len(first),idempotence_offline_repeat=len(second),
        actual_mysql_idempotence='NOT_EXECUTED_NO_WRITE_AUTHORIZATION',source_checksums_unchanged=before==after,
        checksums=before,physical_unique_assets='UNKNOWN;708 are pipeline clusters, not verified physical assets')
    (out/'dry-run-summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf8')
    print(json.dumps(summary,ensure_ascii=False,indent=2))

if __name__ == '__main__':
    main()
