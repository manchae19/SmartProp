"""Reproducible conservative screening, duplicate candidates, and baseline inputs."""
import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import date, datetime
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

from review_nhadat24h import classify as classify_nhadat, displayed_date
from smartprop_geography import DISTRICTS, REFERENCE, norm, resolve

CATEGORIES = ['Nhà ở', 'Đất nền', 'Căn hộ chung cư']
BASE = Path(__file__).resolve().parent
INPUTS = [
    ('cafeland', 'data_raw/cafeland_batch/cafeland_listings.csv'),
    ('cafeland', 'data_raw/cafeland_batch/cafeland_scope_recovered.csv'),
    ('homedy', 'data_raw/homedy_batch_3000/homedy_records.csv'),
    ('nhadat24h', 'data_raw/nhadat24h_batch/nhadat24h_records.csv'),
]
FIELDS = ['record_key', 'source', 'source_listing_id', 'detail_url', 'title',
          'category', 'category_basis', 'district', 'district_candidates',
          'location_basis', 'ward', 'address_raw', 'price_million', 'area_sqm',
          'price_per_sqm_million', 'displayed_date', 'date_basis', 'age_days',
          'detail_fetched', 'collected_at', 'status', 'review_reasons',
          'duplicate_candidate_group', 'model_split', 'input_file', 'input_row', 'raw_json']


def number(value):
    try:
        result = float(value)
        return result if math.isfinite(result) else None
    except (TypeError, ValueError):
        return None


def price(raw):
    s = norm(raw)
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*ty(?:\s*(\d+(?:[.,]\d+)?)\s*trieu)?', s)
    if m:
        return float(m[1].replace(',', '.')) * 1000 + (float(m[2].replace(',', '.')) if m[2] else 0)
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*trieu', s)
    return float(m[1].replace(',', '.')) if m else None


def classify(row, source):
    title = norm(row['title'])
    if source == 'nhadat24h':
        cat, basis, review = classify_nhadat(row)
    else:
        src = norm(row.get('source_category'))
        mapping = {'ban-nha-rieng': 'Nhà ở', 'ban-biet-thu': 'Nhà ở',
                   'ban-nha-pho': 'Nhà ở', 'ban-nha-pho-du-an': 'Nhà ở',
                   'ban-can-ho-chung-cu': 'Căn hộ chung cư',
                   'ban-dat-tho-cu': 'Đất nền', 'ban-dat-nen-du-an': 'Đất nền',
                   'ban-dat-nen': 'Đất nền', 'nha rieng': 'Nhà ở',
                   'ban-nha-hang-khach-san': 'Khác', 'ban-can-ho-mini-dich-vu': 'Khác'}
        cat = mapping.get(src, 'Chưa xác định')
        basis, review = 'source_category', cat == 'Chưa xác định'
    if re.search(r'\b(condotel|shophouse|khach san|toa can ho|toa chdv|toa nha|nha tro|homestay)\b', title):
        return 'Khác', 'special_property_title', False
    land = bool(re.search(r'\b(ban dat|lo dat|dat nen|dat tho cu)\b', title))
    house = bool(re.search(r'\b(ban nha|nha \d+ tang|ban biet thu)\b', title))
    if (cat == 'Nhà ở' and land) or (cat == 'Đất nền' and house):
        review = True
        basis += ';source_title_conflict'
    return cat, basis, review


def screen(raw, source, path, rownum, asof):
    reasons = []
    district, loc, district_candidates = resolve(raw['address_raw'], raw.get('district', ''), source)
    if (source == 'nhadat24h' and raw.get('location_status') == 'in_scope'
            and urlparse(raw.get('listing_page', '')).hostname == 'nhadat24h.net'
            and urlparse(raw.get('listing_page', '')).path.startswith('/nha-dat-da-nang')):
        # Nhadat24h cards omit the province in their address. The source crawler
        # also checked the Da Nang province code; retain that distinct evidence.
        district, loc, district_candidates = resolve(raw['address_raw'] + ', Đà Nẵng',
                                                     raw.get('district', ''), source)
        if district:
            loc = 'source_province_flag_and_historical_district'
    cat, cat_basis, cat_review = classify(raw, source)
    pr = price(raw.get('price_raw', ''))
    ar = number(raw.get('area_sqm'))
    source_price = number(raw.get('price_million'))
    if pr is None:
        reasons.append('price_unavailable_or_non_total')
    elif source_price is None or abs(pr - source_price) > .01:
        reasons.append('source_price_parse_mismatch')
    if source == 'homedy':
        detail_price = price(raw.get('detail_price_raw', ''))
        if raw.get('detail_fetched') != 'True' or raw.get('detail_error'):
            reasons.append('detail_not_verified')
        if detail_price is None:
            reasons.append('detail_price_unavailable')
        elif pr is not None and abs(detail_price - pr) > .01:
            reasons.append('listing_detail_price_mismatch')
        if '/ban-' not in raw.get('detail_url', ''):
            reasons.append('transaction_unverified')
    elif raw.get('transaction_type') != 'Bán':
        reasons.append('transaction_unverified')
    area_match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m[2²]', norm(raw.get('area_raw')))
    if not area_match or ar is None or abs(float(area_match[1].replace(',', '.')) - ar) > .01:
        reasons.append('source_area_parse_mismatch')
    if ar is None or not 20 <= ar <= 1000:
        reasons.append('area_threshold_review')
    unit = pr / ar if pr is not None and ar and ar > 0 else None
    if pr is not None and (pr < 100 or unit is not None and not 2 <= unit <= 300):
        reasons.append('price_threshold_review')
    if cat_review:
        reasons.append('category_ambiguous')
    if re.search(r'\b(tra truoc|thanh toan \d+\s*%|chi tu)\b', norm(raw['title'])):
        reasons.append('possible_partial_or_starting_price_title')
    for key in ['price_needs_review', 'area_needs_review']:
        if raw.get(key) == 'True':
            reasons.append('source_' + key)
    reasons.extend(filter(None, raw.get('review_reason', '').split(';')))
    d, date_basis = '', 'unavailable'
    if source == 'cafeland':
        try:
            d = datetime.strptime(raw['updated_attribute_raw'], '%d-%m-%Y %H:%M:%S').date().isoformat()
            date_basis = 'source_update_attribute_not_first_post'
        except (ValueError, KeyError):
            pass
    elif source == 'nhadat24h':
        d, date_basis, _, _ = displayed_date(raw)
    age = (asof - date.fromisoformat(d)).days if d else None
    if age is not None and age < 0:
        reasons.append('future_display_date')
    if not raw.get('source_listing_id', '').isdigit():
        reasons.append('invalid_source_id')
    if loc == 'outside_or_unknown':
        status = 'outside_or_unknown'
    elif not district:
        status = 'district_needs_review'
    elif cat == 'Khác':
        status = 'other_property'
    elif reasons:
        status = 'needs_review'
    elif age is not None and age > 183:
        status = 'older_than_183_days'
    else:
        status = 'candidate'
    return dict(record_key=source + ':' + raw['source_listing_id'], source=source,
        source_listing_id=raw['source_listing_id'], detail_url=raw['detail_url'], title=raw['title'],
        category=cat, category_basis=cat_basis, district=district, district_candidates=district_candidates,
        location_basis=loc, ward=raw.get('ward', ''), address_raw=raw['address_raw'],
        price_million=pr, area_sqm=ar, price_per_sqm_million=unit, displayed_date=d,
        date_basis=date_basis, age_days=age, detail_fetched=raw['detail_fetched'],
        collected_at=raw['collected_at'], status=status, review_reasons=';'.join(sorted(set(reasons))),
        duplicate_candidate_group='', model_split='', input_file=path, input_row=rownum,
        raw_json=json.dumps(raw, ensure_ascii=False, sort_keys=True))


def duplicates(rows):
    """Heuristic groups, not proof of identity. Do not delete original records."""
    parent = list(range(len(rows)))
    def find(i):
        while parent[i] != i:
            parent[i] = parent[parent[i]]
            i = parent[i]
        return i
    blocks = defaultdict(list)
    pairs = []
    for i, row in enumerate(rows):
        if row['district'] and row['category'] in CATEGORIES:
            blocks[row['district'], row['category']].append(i)
    for members in blocks.values():
        for pos, i in enumerate(members):
            a = rows[i]
            ta = re.sub(r'\W+', ' ', norm(a['title'])).strip()
            sa = set(ta.split())
            if len(sa) < 6:
                continue
            for j in members[pos+1:]:
                b = rows[j]
                tb = re.sub(r'\W+', ' ', norm(b['title'])).strip()
                rule = ''
                similarity = 1.0
                if ta == tb:
                    rule = 'exact_normalized_title_and_district_category'
                elif a['area_sqm'] and b['area_sqm'] and a['price_million'] and b['price_million']:
                    if abs(a['area_sqm'] - b['area_sqm']) / max(a['area_sqm'], b['area_sqm']) > .01:
                        continue
                    if abs(a['price_million'] - b['price_million']) / max(a['price_million'], b['price_million']) > .05:
                        continue
                    sb = set(tb.split())
                    if len(sa & sb) < 8 or len(sa & sb) / len(sa | sb) < .65:
                        continue
                    similarity = SequenceMatcher(None, ta, tb, autojunk=False).ratio()
                    if similarity >= .88:
                        rule = 'similar_title_area_1pct_price_5pct'
                if rule:
                    parent[find(j)] = find(i)
                    pairs.append(dict(left=a['record_key'], right=b['record_key'], rule=rule,
                        title_similarity=round(similarity, 4), cross_source=a['source'] != b['source'],
                        left_url=a['detail_url'], right_url=b['detail_url']))
    groups = defaultdict(list)
    for i, row in enumerate(rows):
        groups[find(i)].append(row)
    for members in groups.values():
        keys = sorted(r['record_key'] for r in members)
        gid = 'possible:' + hashlib.sha256('|'.join(keys).encode()).hexdigest()[:16] if len(keys) > 1 else keys[0]
        bucket = int(hashlib.sha256(('smartprop-v1:' + gid).encode()).hexdigest()[:8], 16) % 100
        split = 'train' if bucket < 80 else 'validation' if bucket < 90 else 'test'
        for row in members:
            row['duplicate_candidate_group'] = gid
            row['model_split'] = split
    return pairs


def save_csv(path, rows, fields):
    with path.open('w', encoding='utf-8-sig', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def main(output, asof):
    output.mkdir(parents=True, exist_ok=True)
    rows, manifest, repeated = [], {}, []
    seen = set()
    for source, relative in INPUTS:
        path = BASE / relative
        if not path.exists():
            if 'recovered' in relative:
                continue
            raise FileNotFoundError(path)
        manifest[relative] = hashlib.sha256(path.read_bytes()).hexdigest()
        with path.open(encoding='utf-8-sig', newline='') as f:
            for rownum, raw in enumerate(csv.DictReader(f), 2):
                if None in raw or any(v is None for v in raw.values()):
                    raise ValueError(f'Malformed CSV {relative}:{rownum}')
                r = screen(raw, source, relative, rownum, asof)
                if r['record_key'] in seen:
                    repeated.append(r)
                    continue
                seen.add(r['record_key'])
                rows.append(r)
    pairs = duplicates(rows)
    candidates = [r for r in rows if r['status'] == 'candidate']
    groups = defaultdict(list)
    for r in candidates:
        groups[r['duplicate_candidate_group']].append(r)
    representatives = [sorted(members, key=lambda r: (r['detail_fetched'] == 'True',
        bool(r['displayed_date']), r['collected_at'], r['record_key']), reverse=True)[0]
        for members in groups.values()]
    scope_path = BASE / 'data_raw/cafeland_batch/cafeland_scope_review.csv'
    manifest[str(scope_path.relative_to(BASE)).replace('\\', '/')] = hashlib.sha256(scope_path.read_bytes()).hexdigest()
    scope = []
    for raw in csv.DictReader(scope_path.open(encoding='utf-8-sig', newline='')):
        district, basis, choices = resolve(raw['address_raw'], source='cafeland')
        scope.append(dict(source_listing_id=raw['source_listing_id'], detail_url=raw['detail_url'],
            address_raw=raw['address_raw'], district_suggested=district,
            district_candidates=choices, location_basis=basis,
            recovered_detail=('cafeland:' + raw['source_listing_id']) in seen,
            reference=REFERENCE if basis != 'outside_or_unknown' else ''))
    save_csv(output / 'all_records_audit.csv', rows, FIELDS)
    save_csv(output / 'candidates.csv', candidates, FIELDS)
    save_csv(output / 'needs_review.csv', [r for r in rows if r['status'] in {'needs_review', 'district_needs_review'}], FIELDS)
    save_csv(output / 'baseline_inputs.csv', representatives, FIELDS)
    save_csv(output / 'duplicate_source_rows.csv', repeated, FIELDS)
    save_csv(output / 'possible_duplicate_pairs.csv', pairs,
             ['left', 'right', 'rule', 'title_similarity', 'cross_source', 'left_url', 'right_url'])
    save_csv(output / 'cafeland_scope_audit.csv', scope,
             ['source_listing_id', 'detail_url', 'address_raw', 'district_suggested',
              'district_candidates', 'location_basis', 'recovered_detail', 'reference'])
    coverage = []
    for d in DISTRICTS:
        for cat in CATEGORIES:
            subset = [r for r in representatives if r['district'] == d and r['category'] == cat]
            coverage.append(dict(district=d, category=cat, count=len(subset),
                suggested_additional_to_50=max(0, 50-len(subset)),
                collection_action=('check_market_supply_before_collecting' if not subset
                    else 'target_missing_category_and_location_features' if len(subset)<50
                    else 'prioritize_quality_and_location_features_over_volume'),
                **{s: sum(r['source'] == s for r in subset) for s in ['cafeland', 'homedy', 'nhadat24h']}))
    save_csv(output / 'coverage_and_collection_plan.csv', coverage,
             ['district', 'category', 'count', 'suggested_additional_to_50', 'collection_action', 'cafeland', 'homedy', 'nhadat24h'])
    summary = dict(as_of=asof.isoformat(), source_sha256=manifest, unique_records=len(rows),
        duplicate_source_rows=len(repeated), by_source=dict(Counter(r['source'] for r in rows)),
        statuses=dict(Counter(r['status'] for r in rows)),
        statuses_by_source={s: dict(Counter(r['status'] for r in rows if r['source'] == s)) for s in ['cafeland','homedy','nhadat24h']},
        review_reasons=dict(Counter(reason for r in rows for reason in r['review_reasons'].split(';') if reason)),
        candidates=len(candidates), baseline_representatives=len(representatives),
        possible_duplicate_pairs=len(pairs), cross_source_pairs=sum(p['cross_source'] for p in pairs),
        candidate_rows_with_unknown_date=sum(not r['displayed_date'] for r in candidates),
        scope_review=dict(Counter(r['location_basis'] for r in scope)),
        recovered_detail_count=sum(r['recovered_detail'] for r in scope),
        split_counts=dict(Counter(r['model_split'] for r in representatives)),
        assumptions={'age_limit_days':183,'area_range_sqm':[20,1000],
            'unit_price_range_million_per_sqm':[2,300], 'coverage_target_per_cell':50,
            'unknown_dates':'retained and identified; never inferred from collection date',
            'duplicate_groups':'heuristic candidates, one representative for baseline only',
            'price_target':'asking price in million VND, not transaction price'})
    for relative, digest in manifest.items():
        assert hashlib.sha256((BASE / relative).read_bytes()).hexdigest() == digest, 'Input changed during processing; rerun after crawler stops'
    assert len(set(r['record_key'] for r in rows)) == len(rows)
    assert all(r['district'] in DISTRICTS and r['category'] in CATEGORIES for r in candidates)
    assert len(representatives) == len(set(r['duplicate_candidate_group'] for r in representatives))
    (output / 'summary.json').write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding='utf-8')
    print(json.dumps(summary, ensure_ascii=True, indent=2))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, default=BASE / 'processed/smartprop_review')
    parser.add_argument('--as-of', type=date.fromisoformat, default=date(2026,10,11))
    args = parser.parse_args()
    main(args.output_dir, args.as_of)
