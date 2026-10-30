"""Versioned source-content adjudication; frozen earlier parsers stay unchanged."""
import re
import review_source_details as previous
from smartprop_geography import norm


def price_text(text):
    """Only expand a complete 3-digit triệu component; retain original evidence."""
    text=norm(text)
    fixes=[]
    pattern=r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(ty|ti)\s*(\d{3})(?!\d)(?=\s|[,;.)]|$)'
    def replace(match):
        after=text[match.end():match.end()+25]
        if re.match(r'\s*(?:trieu|m[2²]|met|phong|tang|x)\b',after):
            return match[0]
        fixes.append(dict(rule='complete_billion_plus_three_digit_million',source_quote=match[0],
                          value_million=float(match[1].replace(',','.'))*1000+int(match[3])))
        return match[0]+' trieu'
    return re.sub(pattern,replace,text),fixes


def house_area_text(text,area):
    text=norm(text)
    fixes=[]
    amount=r'(\d+(?:[.,]\d+)?)\s*m[2²]'
    targets=[float(m[1].replace(',','.')) for m in re.finditer(
        r'\b(?:dien tich|dt)(?:\s+(?:dat|tren so|cong nhan))?\s*[:=]?\s*(?:dat\s*)?'+amount,text)]
    # Never waive floor differences without a matching site/land area in this ID.
    if not any(abs(value-float(area))<=.01 for value in targets):
        return text,fixes
    pattern=r'\b(?:dtsd|(?:dien tich|dt)\s+(?:su dung|xay dung|san|san xay dung))\s*[:=]?\s*'+amount
    def replace(match):
        value=float(match[1].replace(',','.'))
        if abs(value-float(area))<=.01:
            return match[0]
        fixes.append(dict(rule='house_land_area_matches_distinct_use_or_construction_area',
                          source_quote=match[0],target_area=float(area),other_area=value))
        return ' '
    return re.sub(pattern,replace,text),fixes


def actual_asset_proof(row,evidence):
    source=evidence.get('category')
    body=norm(evidence.get('asset_description',evidence.get('description','')))
    body=re.split(r'\b(?:lien he|tu van bat dong san|quy khach|hay noi nhu cau|pkd)\b',body)[0]
    # A leading source-inserted CafeLand category/address is not seller proof.
    if row['source']=='cafeland' and not evidence.get('asset_description') and body.startswith('ban '):
        body=re.sub(r'^ban [^.]{0,140}?da nang\s*','',body,count=1)
    if source=='Nhà ở':
        pattern=r'\b(?:can nha|nha mat tien|nha mat pho|nha dep|nha rieng|nha moi|nha hien dai|nha pho)\b'
    elif source=='Căn hộ chung cư':
        pattern=r'^\W*can ho (?:cao cap|chung cu|\d+\s*phong|\d+\s*pn)\b'
    else:
        return None
    for match in re.finditer(pattern,body[:600]):
        before=body[max(0,match.start()-60):match.start()]
        if not re.search(r'\b(?:xay|cai tao(?: thanh)?|gan|canh|thich hop(?: de)?|phu hop(?: de)?)\s*(?:mot |can |cac |khu |day |toa )?$',before):
            return dict(rule='specific_source_category_supported_by_actual_asset_phrase',
                        source_quote=body[max(0,match.start()-20):match.end()+60],category=source)
    return None


def evaluate(row,evidence):
    original_decision,original_category,original_flags=previous.decide(row,evidence)
    if not evidence.get('identity_verified') or not evidence.get('structure_verified'):
        return dict(decision=original_decision,category=original_category,remaining_codes=original_flags,resolutions=[])
    locality=re.search(r'\b(?:trung tam|tp\.?|thanh pho|phuong)\s+tam quan\b',norm(row['title']+' '+evidence['description'][:500]))
    if locality and 'tam quan' not in norm(evidence.get('address_raw','')):
        return dict(decision='pending',category=original_category,
            remaining_codes=sorted(set(original_flags)|{'content_location_not_reconciled'}),
            resolutions=[dict(rule='explicit_locality_does_not_reconcile_with_source_address',
                source_quote=locality[0],source_address=evidence.get('address_raw',''),
                reference='https://tamquan.gialai.gov.vn/')])
    # Explicit configuration of an entire rental-unit building, not a nearby
    # apartment or a proposal to build one in the future.
    subject=norm(evidence.get('asset_description',evidence['description']))
    special=re.search(r'\bcong nang\s*:\s*(\d+)\s*phong (?:can ho khep kin|tro)\b',subject)
    existing_structure=bool(re.search(r'\b(?:quy mo|ket cau)\s*:\s*\d+\s*tang\b',subject))
    future_structure=bool(special and re.search(r'\b(?:phuong an|du kien|de xuat|co the xay|xay moi)\b',subject[:special.end()]))
    if special and int(special[1])>=2 and evidence.get('category')=='Nhà ở' and existing_structure and not future_structure:
        return dict(decision='exclude',category='Khác',remaining_codes=['actual_whole_rental_building_outside_model_scope'],
            resolutions=[dict(rule='explicit_existing_rental_unit_configuration',source_quote=special[0])])
    copy=dict(evidence)
    title,fix1=price_text(row['title'])
    description,fix2=price_text(evidence['description'])
    fixes=fix1+fix2
    if evidence.get('category')=='Nhà ở':
        description,fix3=house_area_text(description,evidence['area_sqm'])
        fixes+=fix3
    copy['description']=description
    local=dict(row,title=title,review_decision='')
    decision,category,flags=previous.decide(local,copy)
    flags=set(flags)
    proof=actual_asset_proof(row,evidence)
    if proof and 'specific_category_not_supported_by_asset_claims' in flags:
        flags.remove('specific_category_not_supported_by_asset_claims')
        fixes.append(proof)
    if row.get('review_decision')=='pending' and not fixes:
        flags.add('prior_pending_requires_explicit_resolution')
    if not fixes:
        return dict(decision=original_decision,category=original_category,remaining_codes=original_flags,resolutions=[])
    if flags:
        decision='pending'
    else:
        decision='correct' if category!=row['category'] else 'keep'
    return dict(decision=decision,category=category,remaining_codes=sorted(flags),resolutions=fixes)
