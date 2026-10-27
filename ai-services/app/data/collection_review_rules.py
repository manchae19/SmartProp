import json
import re
import audit_all_collected as audit
import expand_collection_audit_scope as scope
from smartprop_geography import norm

SPECIAL = {'condotel', 'nha tro, phong tro', 'dat nong nghiep, dat vuon',
           'dat dich vu, den bu', 'nha hang, khach san, resort', 'shophouse',
           'nha xuong, mat bang, kho bai', 'ban-nha-hang-khach-san'}
SPECIFIC = {
    'nha mat pho': 'Nhà ở', 'nha trong ngo': 'Nhà ở', 'nha biet thu, lien ke': 'Nhà ở',
    'nha mat tien': 'Nhà ở', 'nha rieng': 'Nhà ở', 'ban-nha-rieng': 'Nhà ở',
    'ban-nha-pho-du-an': 'Nhà ở', 'ban-nha-pho': 'Nhà ở', 'ban-biet-thu': 'Nhà ở',
    'dat tho cu, dat o': 'Đất nền', 'dat nen du an': 'Đất nền',
    'ban-dat-tho-cu': 'Đất nền', 'ban-dat-nen-du-an': 'Đất nền',
    'can ho chung cu': 'Căn hộ chung cư', 'ban-can-ho-chung-cu': 'Căn hộ chung cư',
}


def area(value):
    match = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m[2²]', norm(value))
    return float(match[1].replace(',', '.')) if match else None


def compatible_category(row, raw):
    category = SPECIFIC.get(norm(raw.get('source_category', '')))
    title = norm(row['title'])
    # Category prefixes inserted by CafeLand are metadata, not asset descriptions.
    title = re.sub(r'^ban nha rieng\s*:\s*', '', title)
    mixed = re.search(r'\b(dat co nha|dat tang|tang (?:\d+ )?nha|san nha|quy dat|dat vang|'
                      r'dat va nha|nha va dat|dat kem nha|khach san|condotel|toa can ho|day tro)\b', title)
    land = re.search(r'\b(ban dat|lo dat|cap dat|dat nen|dat tho cu)\b', title) or re.match(r'^dat\b', title)
    house = re.search(r'\b(ban nha|nha (?:\d+(?:[.,]\d+)? tang|cap 4|gac lung|c4)|ban biet thu)\b', title)
    if mixed or (land and house):
        return None
    if category == 'Nhà ở' and (land or re.search(r'\bdat\b', title)):
        return None
    if category == 'Đất nền' and (house or re.search(r'\bnha\b', title)):
        return None
    if category == 'Căn hộ chung cư' and (land or house):
        return None
    return category if category == row['category'] else None


def repair(row):
    """Fill only missing normalized values from unambiguous source strings."""
    row = dict(row)
    raw = json.loads(row['raw_json'])
    changes = []
    for field, rawfield, parser in (('price_million', 'price_raw', audit.price),
                                    ('area_sqm', 'area_raw', area)):
        value = parser(raw.get(rawfield, ''))
        if audit.number(row[field]) is None and value is not None and value > 0:
            changes.append(dict(record_key=row['record_key'], field=field, previous=row[field],
                                value=value, source_field=rawfield, source_text=raw.get(rawfield, ''),
                                rule='full_string_source_parse_no_estimation'))
            row[field] = value
            raw[field] = value
    row['raw_json'] = json.dumps(raw, ensure_ascii=False)
    typed = dict(row)
    typed['price_million'], typed['area_sqm'] = audit.number(row['price_million']), audit.number(row['area_sqm'])
    p, a = typed['price_million'], typed['area_sqm']
    typed['price_per_sqm_million'] = p/a if p is not None and a and a > 0 else None
    typed['age_days'] = int(row['age_days']) if str(row.get('age_days', '')) not in ('', 'None') else None
    typed['transaction_verified'] = str(row['transaction_verified']) == 'True'
    flags, money = audit.checks(typed)
    # These flags compare multiple observations and cannot be recomputed from one row.
    flags = sorted(set(flags) | {c for c in row['review_codes'].split(';') if c.startswith('snapshot_')})
    row.update(review_codes=';'.join(flags), title_money_evidence=json.dumps(money, ensure_ascii=False))
    return scope.rescreen(row), changes


def apply_review_rules(row, normalized_raw):
    row = dict(row)
    flags = set(filter(None, row['pipeline_review_codes'].split(';')))
    resolved = set(filter(None, row['resolved_review_codes'].split(';')))
    excluded = set(filter(None, row['exclusion_codes'].split(';')))
    raw = json.loads(normalized_raw['raw_json'])
    category_rule = ''
    # A previous pending source decision is never overridden by a title/category rule.
    if not row['review_decision'] and compatible_category(row, raw):
        removable = flags & {'source_category_needs_review', 'category_review_pending'}
        if removable:
            flags -= removable
            resolved |= removable
            category_rule = 'specific_source_category_no_opposing_asset_cues'
    if not row['review_decision'] and norm(raw.get('source_category', '')) in SPECIAL:
        excluded.add('explicit_special_source_category')
    title = re.sub(r'^\W+', '', norm(row['title']))
    if not row['review_decision'] and re.match(
            r'^(?:(?:can )?ban (?:nguyen )?)?(?:shophouse|condotel)\b', title):
        excluded.add('explicit_commercial_asset_title')
    row.update(pipeline_status='excluded' if excluded else 'needs_review' if flags else 'eligible',
               exclusion_codes=';'.join(sorted(excluded)), pipeline_review_codes=';'.join(sorted(flags)),
               resolved_review_codes=';'.join(sorted(resolved)))
    return row, category_rule

