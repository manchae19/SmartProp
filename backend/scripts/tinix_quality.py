"""Dataset-specific, conservative research gate. Never opens old crawler HTML.

Original values are never corrected. SALE requires textual evidence; price is
parsed from the original Parquet string using Decimal, not binary floating point.
"""
import hashlib,json,math,re,unicodedata
from decimal import Decimal,InvalidOperation

RULE='TINIX_RESEARCH_V1'
def norm(s):
    return ' '.join(''.join(c for c in unicodedata.normalize('NFD',str(s or '').lower()) if not unicodedata.combining(c)).replace('đ','d').split())
def sha(s):return hashlib.sha256(s.encode('utf8')).hexdigest()
TYPES={'nha':'HOUSE','can ho chung cu':'APARTMENT','dat':'LAND','biet thu/nha lien ke':'VILLA','biet thu / nha lien ke':'VILLA'}
DISTRICTS={norm(v):v for v in ['Hải Châu','Thanh Khê','Sơn Trà','Ngũ Hành Sơn','Liên Chiểu','Cẩm Lệ','Hòa Vang','Hoàng Sa']}
def exact_decimal(value,scale,max_digits):
    if value is None:return None
    try:
        d=Decimal(str(value))
        if not d.is_finite() or d<=0 or d>=Decimal(10)**(max_digits-scale) or d!=d.quantize(Decimal(10)**-scale):return None
        return d
    except (InvalidOperation,ValueError):return None
def canonical(row):return json.dumps(row,ensure_ascii=False,sort_keys=True,separators=(',',':'),allow_nan=False)
def restore_original(payload,bits):
    """Recover original float64 values after MySQL binary JSON normalization.

    Binary JSON may normalize a numeric literal by one ULP. The separately
    stored IEEE-754 hexadecimal strings are authoritative source provenance.
    Larger differences or a missing/changed numeric field are errors.
    """
    restored=dict(payload)
    for field,representation in bits.items():
        original=float.fromhex(representation);actual=payload.get(field)
        if math.isfinite(original):
            if not isinstance(actual,(float,int)) or isinstance(actual,bool) or not math.isfinite(actual) or abs(actual-original)>math.ulp(original):
                raise ValueError('JSON numeric payload corruption:'+field)
            restored[field]=original
        elif actual!={'$nonfinite_float64':representation}:raise ValueError('Nonfinite source provenance mismatch:'+field)
    return restored
def quality(row):
    flags=[];title=norm(row.get('name'));body=norm(row.get('description'));text=title+' '+body
    price=exact_decimal(row.get('price'),2,24);area=exact_decimal(row.get('area'),6,18)
    if price is None:flags.append('MISSING_OR_NONEXACT_TOTAL_PRICE')
    if area is None:flags.append('MISSING_OR_NONEXACT_AREA')
    if not title or not body:flags.append('MISSING_ASSET_TEXT')
    if norm(row.get('province_name'))!='da nang':flags.append('NOT_DA_NANG')
    district=DISTRICTS.get(re.sub(r'^(quan|huyen)\s+','',norm(row.get('district_name'))))
    if not district:flags.append('DISTRICT_NOT_EVIDENCED')
    kind=TYPES.get(norm(row.get('property_type_name')))
    if not kind:flags.append('UNSUPPORTED_PROPERTY_TYPE')
    sale=bool(re.search(r'\b(ban|chuyen nhuong|sang nhuong)\b',title))
    rent=bool(re.search(r'\b(cho thue|can thue|thue nha|thue can ho)\b',title))
    if not sale and not rent:
        sale=bool(re.search(r'\b(can ban|gia ban|gui ban|chinh chu ban|chuyen nhuong)\b',body))
        rent=bool(re.search(r'\b(cho thue|gia thue|/thang|/nam)\b',body))
    transaction='SALE' if sale and not rent else 'RENT' if rent and not sale else 'UNKNOWN'
    if transaction!='SALE':flags.append('TRANSACTION_NOT_UNAMBIGUOUS_SALE')
    if re.search(r'\b(tra truoc|thanh toan truoc|chi can|von tu co|so huu chi tu)\b',text):flags.append('PARTIAL_PRICE_CONTEXT')
    if re.search(r'\b(\d+|hai|ba|nhieu)\s+(lo dat|can nha|can ho|lo lien ke)\b|\b(cap lo|ro hang|bang hang|nhieu lo|nhieu can|day tro|day phong)\b',text):flags.append('MULTIPLE_ASSETS')
    if re.search(r'\b(khach san|toa nha|can ho dich vu|shophouse|kho xuong|nha xuong|condotel)\b',title):flags.append('SPECIAL_ASSET')
    category_claim='LAND' if re.search(r'\bban (lo )?dat\b',title) else 'APARTMENT' if re.search(r'\bban (can ho|chung cu)\b',title) else 'HOUSE' if re.search(r'\bban nha\b',title) else None
    if category_claim and kind and category_claim!=kind:flags.append('CATEGORY_CONTRADICTION')
    # Explicit totals in title/body must agree exactly. Never repair a rounded
    # source value or treat unit/monthly amounts as a complete sale price.
    if price:
        for m in re.finditer(r'(?<![\d.,])([0-9]+(?:[.,][0-9]+)?)\s*(ty|ti|trieu)\b',text):
            tail=text[m.end():m.end()+22];before=text[max(0,m.start()-35):m.start()]
            if re.match(r'\s*(/|m2|m²|mot met|moi met|dong/m)',tail):continue
            if re.search(r'(thue|thu nhap|dong tien|loi nhuan|giam|chiet khau|thap hon|ho tro|vay|chenh|von)\D{0,20}$',before) or re.search(r'^\s*(/thang|/nam|thang|nam)',tail):continue
            # Billion followed by extra million digits has ambiguous shorthand.
            if m.group(2) in {'ty','ti'} and re.match(r'\s*\d',tail):flags.append('SHORTHAND_TOTAL_PRICE');continue
            amount=Decimal(m.group(1).replace(',','.'))*(10**9 if m.group(2) in {'ty','ti'} else 10**6)
            if amount!=price:flags.append('EXPLICIT_PRICE_CONFLICT')
        if area:
            for m in re.finditer(r'([0-9]+(?:[.,][0-9]+)?)\s*trieu\s*/\s*m[²2]',text):
                if Decimal(m.group(1).replace(',','.'))*10**6*area!=price:flags.append('UNIT_PRICE_CONFLICT')
    if area:
        for m in re.finditer(r'(?:dien tich|dt|dtcn)\s*[:=]?\s*([0-9]+(?:[.,][0-9]+)?)\s*m[²2]',text):
            if Decimal(m.group(1).replace(',','.'))!=area:flags.append('EXPLICIT_AREA_CONFLICT')
    if price and area and not Decimal('1000000')<=price/area<=Decimal('500000000'):flags.append('UNIT_PRICE_REQUIRES_REVIEW')
    flags=sorted(set(flags))
    excluded='NOT_DA_NANG' in flags or transaction=='RENT' or 'UNSUPPORTED_PROPERTY_TYPE' in flags
    return dict(price_vnd=str(price) if price else None,area_sqm=str(area) if area else None,normalized_type=kind,district=district,
        ward=row.get('ward_name') if row.get('ward_name') and len(row['ward_name'])<=100 else None,
        transaction_type=transaction,transaction_basis='EXPLICIT_SALE_TEXT' if transaction=='SALE' else 'TEXT_RENT' if transaction=='RENT' else 'NOT_ESTABLISHED',
        quality_status='EXCLUDED' if excluded else 'NEEDS_REVIEW' if flags else 'HYBRID_ELIGIBLE_RESEARCH',quality_issues=flags)
