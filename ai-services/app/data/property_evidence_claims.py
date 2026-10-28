"""Conservative research claims; unknown/conflicting values remain missing."""
import re
from collections import defaultdict
from training_v3_common import normalized

FIELDS = ['alley_width_m_claim', 'car_access_claim', 'apartment_floor_claim',
          'handover_year_claim', 'interior_claim', 'legal_document_claim']
NAME_FIELDS = ['project_name', 'building_name']
APARTMENT = 'Căn hộ chung cư'
MULTIPLE = re.compile(r'\b(?:gio hang|nhieu can|cac can|nhieu lo|cac lo|bang gia|quy can)\b')
FUTURE = re.compile(r'\b(?:du kien|sap|se|co the|quy hoach|cho phep xay|xay duoc|toi da|thiet ke du kien)\b')
NEAR = re.compile(r'\b(?:gan|cach|canh|doi dien|ke ben|xung quanh)\b')
FOOTER = re.compile(r'^(?:lien he|hotline|zalo|nhan ky gui|tu van|quy khach)\b')


def clauses(text):
    # Keep the exact source quote; punctuation splits must preserve 3.5m.
    for value in re.split(r'\n|[;!?•●]|(?<!\d)\.(?!\d)|\s[-–—]\s|,\s+(?!\d)', text):
        value = value.strip()
        if value:
            yield value, normalized(value).replace('*', '')


def extract(category, sources, *, observed_year=2026):
    """sources: [{kind,text,sha256}]; name candidates always require review."""
    proof = []
    multi = any(MULTIPLE.search(normalized(s['text'])) for s in sources if s['kind'] != 'structured_legal_status')

    def claim(field, value, source, quote, text, start, rule, reason=None):
        prefix = text[:start]
        why = reason
        if multi:
            why = 'multiple_assets_or_inventory'
        elif FUTURE.search(text):
            why = 'future_or_hypothetical'
        elif NEAR.search(prefix[-65:]):
            why = 'nearby_or_other_subject'
        elif re.search(r'\b(?:khong|chua)(?:\s+(?:phai|co|o))?\s*$', prefix[-25:]) and rule not in ['explicit_car_no', 'certificate_pending', 'unfurnished']:
            why = 'negated_or_uncertain'
        proof.append(dict(field=field, value=value, source_kind=source['kind'], source_sha256=source['sha256'],
                          source_quote=quote, rule=rule, status='rejected' if why else 'candidate', reason=why or ''))

    for source in sources:
        if source['kind'] == 'structured_legal_status':
            value = normalized(source['text'])
            if value in ['so hong rieng', 'so hong/ so do', 'so hong/so do', 'so do', 'so hong']:
                claim('legal_document_claim', 'certificate_claimed', source, source['text'], value, 0, 'structured_certificate_claim')
            continue
        for quote, text in clauses(source['text']):
            if FOOTER.search(text):
                break
            if category != APARTMENT:
                width = r'\b(?:kiet|hem)\s+(?:(?:o\s*to|oto)\s+)?(?:rong\s+)?(\d+(?:[.,]\d+)?)\s*m(?![\w²])'
                for match in re.finditer(width, text):
                    number = float(match[1].replace(',', '.'))
                    reason = 'width_range_or_bound' if re.match(r'\s*[-–/]\s*\d|\s*(?:tro len|tro xuong|do lai)\b', text[match.end():]) else None
                    if not 1 <= number <= 20:
                        reason = 'width_outside_review_range'
                    claim('alley_width_m_claim', number, source, quote, text, match.start(), 'explicit_alley_width',
                          reason)
                car_no = r'\b(?:o\s*to|oto)\s+(?:khong|chua)\s+vao(?:\s+duoc)?|\b(?:kiet|hem)\s+khong\s+(?:co\s+)?(?:o\s*to|oto)\b'
                no_matches = list(re.finditer(car_no, text))
                for match in no_matches:
                    claim('car_access_claim', 'no', source, quote, text, match.start(), 'explicit_car_no')
                for match in re.finditer(r'\b(?:kiet|hem)\s+(?:o\s*to|oto)\b|\b(?:o\s*to|oto)\s+(?:vao|den)\s+tan\s+(?:nha|dat|noi|cua)\b', text):
                    claim('car_access_claim', 'yes', source, quote, text, match.start(), 'explicit_car_access',
                          'car_access_negated_in_clause' if no_matches else None)
            if category == APARTMENT:
                for match in re.finditer(r'\btang\s+(?:thu\s+)?(\d{1,2})(?!\d)', text):
                    number = int(match[1])
                    before, after = text[max(0, match.start()-40):match.start()], text[match.end():]
                    reason = None
                    if re.search(r'\b(?:toa nha|quy mo|tong so|cao|duoc xay)\b', before):
                        reason = 'building_height_not_unit_floor'
                    elif re.match(r'\s*[-–/]|\s*(?:den|va|hoac)\s+\d', after):
                        reason = 'floor_range_or_multiple_units'
                    elif not 1 <= number <= 80:
                        reason = 'floor_outside_review_range'
                    claim('apartment_floor_claim', number, source, quote, text, match.start(), 'explicit_unit_floor', reason)
                for match in re.finditer(r'\bban giao\s+(?:(?:tu|vao)\s+)?(?:nam\s+)?(20\d{2})\b', text):
                    year = int(match[1])
                    reason = 'unknown_observation_year' if observed_year is None else 'year_after_observation' if year > observed_year else None
                    claim('handover_year_claim', year, source, quote, text, match.start(), 'literal_handover_year', reason)
                for field, pattern in [('project_name', r'(?:dự án|du an)\s*:\s*([^,:;|]{2,80})'),
                                       ('building_name', r'(?:Tòa|Toà|Block|block)\s+([A-Z][A-Z0-9-]{0,9})\b')]:
                    for match in re.finditer(pattern, quote, flags=re.I if field == 'project_name' else 0):
                        # Candidate names are source strings, not a canonical
                        # project registry or model categories.
                        proof.append(dict(field=field, value=match[1].strip(), source_kind=source['kind'],
                            source_sha256=source['sha256'], source_quote=quote, rule='literal_name_candidate',
                            status='needs_name_review', reason='requires_project_or_building_identity_review'))
            if category in [APARTMENT, 'Nhà ở']:
                patterns = [('full', r'\b(?:full noi that|day du noi that|noi that day du)\b', 'explicit_full_interior'),
                            ('basic', r'\bnoi that\s*:?\s*co ban\b', 'explicit_basic_interior'),
                            ('empty', r'\b(?:khong|chua)\s+(?:co\s+)?noi that\b', 'unfurnished')]
                for value, pattern, rule in patterns:
                    for match in re.finditer(pattern, text):
                        claim('interior_claim', value, source, quote, text, match.start(), rule)
            pending = list(re.finditer(r'\b(?:chua co|cho cap|dang cho cap|chua cap)\s+so(?:\s+(?:hong|do))?\b', text))
            for match in pending:
                claim('legal_document_claim', 'certificate_pending_claimed', source, quote, text, match.start(), 'certificate_pending')
            for match in re.finditer(r'\bso\s+(?:hong|do)\b', text):
                if any(m.start() <= match.start() < m.end() for m in pending):
                    continue
                claim('legal_document_claim', 'certificate_claimed', source, quote, text, match.start(), 'literal_certificate_claim')
            for match in re.finditer(r'\bphap ly\s*:\s*hop dong mua ban\b', text):
                claim('legal_document_claim', 'sale_contract_claimed', source, quote, text, match.start(), 'literal_legal_contract')
    candidates = defaultdict(list)
    for item in proof:
        if item['status'] == 'candidate':
            candidates[item['field']].append(item)
    values, conflicts = {field: '' for field in FIELDS}, []
    for field, items in candidates.items():
        distinct = {p['value'] for p in items}
        if len(distinct) == 1:
            values[field] = next(iter(distinct))
            for item in items:
                item['status'] = 'accepted_literal_claim'
        else:
            conflicts.append(field)
            for item in items:
                item['status'] = 'conflict_keep_missing'
    return dict(values, conflict_fields=';'.join(sorted(conflicts))), proof
