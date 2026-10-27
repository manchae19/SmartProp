"""Additional literal content resolutions; no numeric relabeling or weaker gates."""
import re
import remaining_content_rules as previous
from smartprop_geography import norm


SPECIAL = re.compile(r'\b(toa (?:nha )?can ho|day (?:nha )?tro|\d+ phong tro|condotel|shophouse|dat nong nghiep|dat vuon|dang kinh doanh (?:khach san|nha nghi)|\d+ phong (?:dang )?cho thue)\b')
FOOTER = re.compile(r'\b(?:lien he|hay goi|tu van bat dong san|quy khach|pkd|san giao dich|nhan ky gui|chuyen nhan ky|hay noi yeu cau)\b')
MASKED = re.compile(r'\d+\s*(?:ty|ti|toi)\s*\d*[.,]?x+|\d+[.,]?x+\s*(?:ty|ti|toi|trieu)|\d+\s*trieu\s*x+', re.I)


def prose(text):
    # Markdown bold/heading markers have no numeric or semantic meaning.
    return norm(text).replace('*', '').replace('#', '')


def subject(evidence):
    return FOOTER.split(prose(evidence.get('asset_description', evidence['description'])))[0]


def shorthand(text, target):
    fixes = []
    text = prose(text)
    pattern = r'(?<![\w.,])(\d+)\s*(?:ty|ti)\s*(\d{1,2})(?![\dx]|[.,]\d)(?=\s|[,;.)]|$)'
    def replace(match):
        suffix = text[match.end():match.end()+25]
        if re.match(r'\s*(?:trieu|m[2²]|met|phong|tang|x)\b', suffix):
            return match[0]
        value = int(match[1])*1000 + int(match[2])*10**(3-len(match[2]))
        # An abbreviated fraction is accepted only when the source header
        # independently supplies exactly this total; original numbers stay.
        if abs(value-float(target)) > .01:
            return match[0]
        fixes.append(dict(rule='fractional_billion_matches_explicit_header',
                          source_quote=match[0],value_million=value))
        return f'{value/1000:g} ty'
    return re.sub(pattern, replace, text), fixes


def asset_proof(evidence):
    body = subject(evidence)
    category = evidence['category']
    if category == 'Nhà ở':
        pattern = r'\b(?:nha kien co|biet thu\s+\d+\s*tang|can nha|nha\s+\d+\s*tang)\b'
    elif category == 'Đất nền':
        pattern = r'\b(?:dat vuong|dat o (?:do thi|nong thon)|\d+%\s*dat o|duong truoc dat)\b'
    else:
        return None
    for m in re.finditer(pattern, body[:650]):
        before = body[max(0,m.start()-70):m.start()]
        if not re.search(r'\b(?:xay|cai tao|gan|canh|doi dien|cach|thich hop|phu hop)\b[^.;:]{0,40}$',before):
            return dict(rule='literal_existing_asset_supported_by_source_category',
                        source_quote=body[max(0,m.start()-20):m.end()+70],category=category)
    return None


def future_only_special(text):
    text=prose(text)
    matches=list(SPECIAL.finditer(text))
    if not matches:
        return []
    proofs=[]
    for m in matches:
        before=text[max(0,m.start()-85):m.start()]
        future=re.search(r'\b(?:thich hop (?:de )?xay|tien nang xay|ly tuong xay|phu hop (?:de )?xay)\b[^.!?;]{0,65}$',before)
        if not future:
            return []
        proofs.append(dict(rule='future_construction_is_not_existing_special_asset',
                           source_quote=text[max(0,m.start()-85):m.end()+20]))
    return proofs


def evaluate(row, evidence):
    baseline=previous.evaluate(row,evidence)
    if (not evidence.get('identity_verified') or not evidence.get('structure_verified') or
        baseline['decision']=='exclude' or 'content_location_not_reconciled' in baseline['remaining_codes']):
        return baseline
    copy=dict(evidence)
    local=dict(row,review_decision='')
    fixes=[]
    local['title'], f = shorthand(row['title'],evidence['price_million']); fixes+=f
    copy['description'], f = shorthand(evidence['description'],evidence['price_million']); fixes+=f
    raw_asset=evidence.get('asset_description',evidence['description'])
    clean_asset=FOOTER.split(prose(raw_asset))[0]
    copy['asset_description']=clean_asset
    if clean_asset!=prose(raw_asset):
        fixes.append(dict(rule='broker_footer_not_asset_category_claim',source_quote=prose(raw_asset)[len(clean_asset):len(clean_asset)+180]))
    if '*' in row['title']+evidence['description'] or '#' in row['title']+evidence['description']:
        fixes.append(dict(rule='markdown_formatting_only',source_quote='Formatting markers removed for text matching; all numbers retained'))
    result=previous.evaluate(local,copy)
    flags=set(result['remaining_codes'])
    fixes+=result['resolutions']
    proof=asset_proof(copy)
    if proof and 'specific_category_not_supported_by_asset_claims' in flags:
        flags.remove('specific_category_not_supported_by_asset_claims'); fixes.append(proof)
    future=future_only_special(local['title']+' '+copy['description'])
    if future and 'special_or_whole_building_not_resolved' in flags:
        flags.remove('special_or_whole_building_not_resolved'); fixes+=future
    # Do not let an unrelated category/footer resolution approve a masked price.
    if MASKED.search(prose(row['title']+' '+evidence['description'])):
        flags.add('masked_price_requires_specific_total_reconciliation')
    if re.search(r'\b(?:[2-9]|\d{2,})\s+(?:can )?phong\s+(?:khep|kep)\s+kin\b',subject(evidence)):
        flags.add('multiple_self_contained_rental_units_not_single_home')
    if re.search(r'\bdien tich da dang\b',subject(evidence)):
        flags.add('variable_area_inventory_requires_single_asset_proof')
    # Additional Vietnamese abbreviations not recognized by the frozen parser.
    for m in re.finditer(r'\b(?:dtd|dtich|dt\s*dat)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]',subject(evidence)):
        value=float(m[1].replace(',','.'))
        if abs(value-float(evidence['area_sqm']))>.01:
            flags.add('explicit_site_area_abbreviation_conflicts_with_header')
    for m in re.finditer(r'\b(?:dien tich|dt|dtd)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]\s*\(\s*(\d+(?:[.,]\d+)?)\s*(?:m\s*)?[x×]\s*(\d+(?:[.,]\d+)?)',subject(evidence)):
        stated=float(m[1].replace(',','.'))
        computed=float(m[2].replace(',','.'))*float(m[3].replace(',','.'))
        if abs(computed-stated)/max(computed,stated)>.01:
            flags.add('explicit_parcel_dimensions_not_reconciled')
    if result['category']=='Đất nền' and re.search(r'\b(?:tren dat co nha|dat[^.!?;]{0,60}co nha|hien co nha|tang (?:san )?nha)\b',subject(evidence)):
        flags.add('land_label_existing_building_requires_category_review')
    # Literal source disagreement found while reading the proposed additions.
    # Keep both statements for adjudication; do not substitute a guessed district.
    if (row.get('record_key')=='cafeland:3163843' and
        'hoa tien' in prose(evidence.get('address_raw','')) and
        re.search(r'truong thcs tran phu\s*[-–—]\s*dai hiep',subject(evidence))):
        flags.add('source_locality_and_seller_location_require_reconciliation')
    if not fixes:
        return baseline
    flags.discard('prior_pending_requires_explicit_resolution')
    decision='pending' if flags else ('correct' if result['category']!=row['category'] else 'keep')
    return dict(decision=decision,category=result['category'],remaining_codes=sorted(flags),resolutions=fixes)


def sale_with_rental_context(row,evidence,result):
    """Rental yield is not the asking price, but whole-unit buildings stay out."""
    if result['decision'] not in ('keep','correct') or not evidence.get('sale_verified'):
        return None
    body=subject(evidence)
    if re.search(r'\b(?:tra truoc|tra gop|dat coc|booking|gia tu|chi tu|thanh toan|phong tro|can ho cho thue|phong (?:khep|kep) kin)\b', body):
        return None
    if re.search(r'\b(?:dang cho thue|o hoac cho thue)\b',prose(row['title'])):
        p=float(evidence['price_million'])
        if abs(p-float(row['price_million']))<=.01 and not re.search(r'/\s*(?:thang|nam|ngay)',prose(evidence.get('price_raw',''))):
            return dict(rule='sale_header_total_separate_from_existing_rental_yield',
                        source_quote=row['title'],header_price=evidence.get('price_raw',''),value_million=p)
    return None


def description_signature(evidence):
    """Long exact seller prose, disregarding a leading ordinal and header echo."""
    if not evidence or not evidence.get('identity_verified'):
        return ''
    text=subject(evidence)
    text=re.sub(r'^\s*\d+[.)]?\s+','',text)
    text=re.split(r'\bgia\s*:\s*\d[\d.,]+\s*vnd\b',text)[0]
    text=' '.join(re.findall(r'\w+',text))
    words=text.split()
    return text if len(words)>=50 and len(set(words))>=30 else ''
