"""As-of source claims for an offline ablation, with literal audit evidence."""
from collections import Counter
import hashlib
import json
import re
import unicodedata

import property_evidence_claims as claims
import property_text_features_v6 as baseline
import training_v3_common as data

NUMERIC = ['alley_width_m_claim', 'apartment_floor_claim', 'handover_year_claim',
           'residential_area_sqm_claim', 'parcel_width_m_claim']
LEVELS = dict(car_access_claim=['yes', 'no'], interior_claim=['full', 'basic', 'empty'],
              legal_document_claim=['certificate_claimed', 'sale_contract_claimed', 'certificate_not_available_claimed'])
FIELDS = ['street_key', *NUMERIC, *LEVELS]
MIN_STREET_FIT_GROUPS = 3


def street_claim(raw):
    """Normalize a source field, not a map match or accent reconstruction."""
    value = ' '.join(unicodedata.normalize('NFC', str(raw or '')).split())
    name = re.sub(r'^(?:đường|duong)\s+', '', value, flags=re.I).strip()
    normalized = data.normalized(name)
    subject_text = re.sub(r'\b(?:vo van kiet|ly thuong kiet)\b', 'street_name', normalized)
    subject_text = subject_text.replace('cach mang thang tam', 'street_name')
    if not name:
        return '', 'missing'
    if (not 2 <= len(name) <= 65 or not (any(c.isalpha() for c in name) or re.fullmatch(r'\d{1,2}/\d{1,2}', name))
            or re.search(r'[,;|:!?()]', name)
            or re.search(r'\b(?:gan|cach|doi dien|khong ten|chua ro|dang cap nhat|khu do thi|du an|ban nha|ban dat|gia|rong|hem|kiet)\b', subject_text)
            or re.search(r'\d\s*m(?:2|²)?\b', normalized)
            or re.search(r'\s[-–&]\s|\s/\s', name)):
        return '', 'ambiguous_keep_missing'
    # Identical source spellings are merged. This does not disambiguate a
    # homonymous street; locality is also included when fitting the vocabulary.
    return normalized, 'accepted_source_claim_not_geocoded'


def original_features(row, origin):
    raw = json.loads(origin['raw_json'])
    source_hash = hashlib.sha256(origin['raw_json'].encode('utf8')).hexdigest()
    sources = [dict(kind='original_collected_title', text=origin['title'], sha256=source_hash)]
    if raw.get('legal_status'):
        sources.append(dict(kind='structured_legal_status', text=raw['legal_status'], sha256=source_hash))
    values, proofs = extract_claims(row['category'], sources, float(row['area_sqm']))
    street, state = street_claim(raw.get('street', ''))
    values['street_key'] = street
    values['street_raw'] = raw.get('street', '')
    values['street_status'] = state
    if raw.get('street'):
        proofs.append(dict(field='street_key', value=street, source_kind='original_structured_street',
            source_sha256=source_hash, source_quote=raw['street'], rule='literal_street_normalization',
            status=state, reason='no_coordinate_or_property_identity_claim'))
    return values, proofs


def extract_claims(category, sources, area):
    values, proofs = claims.extract(category, sources)
    values = {field: values.get(field, '') for field in FIELDS if field != 'street_key'}
    # The frozen audit matcher can see "Kiệt 6m" within a person's street
    # name. Keep those quotes, explicitly refuse the width interpretation.
    for p in proofs:
        if p['field'] == 'alley_width_m_claim' and re.search(
                r'\b(?:vo van kiet|ly thuong kiet)\s+\d', data.normalized(p['source_quote'])):
            p.update(status='rejected', reason='street_name_not_alley_width')
    accepted_widths = {p['value'] for p in proofs if p['field'] == 'alley_width_m_claim' and p['status'] == 'accepted_literal_claim'}
    values['alley_width_m_claim'] = next(iter(accepted_widths)) if len(accepted_widths) == 1 else ''
    extra = {f: [] for f in ['residential_area_sqm_claim', 'parcel_width_m_claim']}
    if category == 'Đất nền':
        multi = any(claims.MULTIPLE.search(data.normalized(s['text'])) for s in sources)
        for source in sources:
            for quote, text in claims.clauses(source['text']):
                if claims.FOOTER.search(text):
                    break
                patterns = {
                    'residential_area_sqm_claim': r'\b(?:dien tich dat o|dat tho cu|tho cu|dat o)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]\b',
                    'parcel_width_m_claim': r'\b(?:lo dat|dat)\s+(?:co\s+)?(?:chieu ngang|ngang|rong)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m(?![\w²])',
                }
                for field, pattern in patterns.items():
                    for m in re.finditer(pattern, text):
                        number = float(m[1].replace(',', '.'))
                        reason = ''
                        if multi or claims.FUTURE.search(text) or claims.NEAR.search(text) or re.search(r'\b(?:khong|chua)\b', text):
                            reason = 'multiple_future_nearby_or_negated'
                        elif re.match(r'\s*[-–/]\s*\d|\s*(?:den|toi|tro len|tro xuong)\b', text[m.end():]):
                            reason = 'range_or_bound'
                        elif not 0 < number <= (area if field == 'residential_area_sqm_claim' else 100):
                            reason = 'outside_property_area_or_width_bound'
                        p = dict(field=field, value=number, source_kind=source['kind'],
                            source_sha256=source['sha256'], source_quote=quote, rule='explicit_' + field,
                            status='rejected' if reason else 'candidate', reason=reason)
                        proofs.append(p)
                        if not reason:
                            extra[field].append(p)
        for field, items in extra.items():
            distinct = {p['value'] for p in items}
            values[field] = next(iter(distinct)) if len(distinct) == 1 else ''
            for p in items:
                p['status'] = 'accepted_literal_claim' if len(distinct) == 1 else 'conflict_keep_missing'
    return values, proofs


def feature_spec(fit, base_values, extra_values, category, arm):
    spec = baseline.feature_spec(fit, category, 'all')
    if arm == 'v6_all':
        return dict(arm=arm, base=spec, streets=[], feature_names=spec['feature_names'])
    if arm != 'source_enriched':
        raise ValueError('Unknown feature arm')
    counts = Counter(r['location_feature'] + '|' + extra_values[r['record_key']]['street_key']
                     for r in fit if extra_values[r['record_key']]['street_key'])
    streets = sorted(k for k, n in counts.items() if n >= MIN_STREET_FIT_GROUPS)
    names = NUMERIC + [f + ':' + v for f, levels in LEVELS.items() for v in [*levels, 'missing']]
    names += ['street_missing', 'street_unseen_or_rare'] + ['street:' + v for v in streets]
    return dict(arm=arm, base=spec, streets=streets, min_street_fit_groups=MIN_STREET_FIT_GROUPS,
                feature_names=spec['feature_names'] + names)


def encode(rows, base_values, extra_values, spec):
    import numpy as np
    matrix = baseline.encode(rows, base_values, spec['base'])
    if spec['arm'] == 'v6_all':
        return matrix
    extras = []
    for r in rows:
        f = extra_values[r['record_key']]
        street = r['location_feature'] + '|' + f['street_key'] if f['street_key'] else ''
        x = [float(f[k]) if str(f[k]) else np.nan for k in NUMERIC]
        x += [float(f[k] == v) if v != 'missing' else float(not str(f[k]))
              for k, levels in LEVELS.items() for v in [*levels, 'missing']]
        x += [float(not street), float(bool(street) and street not in spec['streets'])]
        x += [float(street == v) for v in spec['streets']]
        extras.append(x)
    return np.column_stack([matrix, np.asarray(extras, dtype=np.float32)])
