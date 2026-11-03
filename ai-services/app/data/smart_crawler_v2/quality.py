"""Quality-first admission of new observations, not legacy-label recovery."""
from datetime import date,datetime,timezone,timedelta
from decimal import Decimal,InvalidOperation
import json,re
from lxml import html
from .sources import detail_parser
from .index import norm
from .evidence import excerpt
import smartprop_geography as geography

def amount(raw):
    text=norm(raw)
    if re.search(r'/\s*m[2²]|tren\s*m[2²]',text):return None,'UNIT_PRICE_NOT_TOTAL'
    if re.search(r'/\s*(thang|nam)|moi\s+(thang|nam)',text):return None,'RENTAL_PRICE_NOT_SALE_TOTAL'
    match=re.fullmatch(r'(-?\d+(?:[.,]\d+)?)\s*ty(?:\s*(\d+(?:[.,]\d+)?)\s*trieu)?',text)
    if match:return Decimal(match[1].replace(',','.'))*1000000000+(Decimal(match[2].replace(',','.'))*1000000 if match[2] else 0),None
    match=re.fullmatch(r'(-?\d+(?:[.,]\d+)?)\s*trieu',text)
    if match:return Decimal(match[1].replace(',','.'))*1000000,None
    match=re.fullmatch(r'(\d+|\d{1,3}(?:\.\d{3})+)\s*(?:vnd|dong|đ)',text)
    if match:return Decimal(match[1].replace('.','')),None
    return None,'MISSING_OR_AMBIGUOUS_TOTAL_PRICE'

def area(raw):
    match=re.fullmatch(r'(-?\d+(?:[.,]\d+)?)\s*m[2²]',norm(raw))
    return Decimal(match[1].replace(',','.')) if match else None

def labelled_areas(text):
    found=[]
    for m in re.finditer(r'\b(dien tich(?: su dung| xay dung| thong thuy| tim tuong| tren so| so do| thuc te| khung| toi uu| dat| san)?|dtsd|dt(?: su dung| xay dung| dat| san| khung| toi uu)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]\b',norm(text)):
        basis='FLOOR' if any(t in m[1] for t in ['su dung','xay dung','san','dtsd']) else 'LAND' if ' dat' in m[1] else 'UNSPECIFIED'
        found.append((basis,Decimal(m[2].replace(',','.'))))
    return found

def source_dates(card,body):
    values={'published_at':None,'updated_at':None,'date_basis':None};doc=html.fromstring(body)
    for key,prop in [('published_at','article:published_time'),('updated_at','article:modified_time')]:
        raw=doc.xpath('//meta[@property=$p]/@content',p=prop)
        if len(raw)==1:
            try:values[key]=datetime.fromisoformat(raw[0].replace('Z','+00:00')).isoformat();values['date_basis']='SOURCE_META_'+prop
            except ValueError:pass
    raw=card.get('updated_attribute_raw') or card.get('posted_at_raw') or ''
    for fmt in ['%d-%m-%Y %H:%M:%S','%d/%m/%Y %H:%M:%S','%d-%m-%Y','%d/%m/%Y']:
        if not raw:break
        try:
            parsed=datetime.strptime(raw,fmt)
            # Preserve a date where the publisher does not specify a timezone.
            key='updated_at' if card.get('updated_attribute_raw') else 'published_at'
            if not values[key]:values[key]=parsed.date().isoformat();values['date_basis']='SOURCE_CARD_DATE_TIMEZONE_UNSPECIFIED'
            break
        except ValueError:pass
    return values

def evaluate(source,card,e,body,crawled_at,max_age_days=30):
    flags=[];reject=[];price,price_issue=amount(e.get('price_raw'));sqm=area(e.get('area_raw'))
    if price_issue:flags.append(price_issue)
    if sqm is None:flags.append('MISSING_OR_AMBIGUOUS_AREA')
    if not e.get('identity_verified'):flags.append('DETAIL_IDENTITY_NOT_VERIFIED')
    if not e.get('structure_verified'):flags.append('DETAIL_STRUCTURE_INCOMPLETE')
    if not e.get('sale_verified'):flags.append('SALE_TRANSACTION_UNCONFIRMED')
    if price is not None and (price<=0 or price>Decimal('999999999999999')):reject.append('INVALID_TOTAL_PRICE_RANGE')
    if sqm is not None and (sqm<=0 or sqm>1000000):reject.append('INVALID_AREA_RANGE')
    if price is not None and price!=price.quantize(Decimal('.01')):flags.append('PRICE_DECIMAL_PRECISION')
    if sqm is not None and sqm!=sqm.quantize(Decimal('.01')):flags.append('AREA_DECIMAL_PRECISION')
    category=e.get('category','')
    if category=='Khác':reject.append('UNSUPPORTED_PROPERTY_TYPE')
    elif category not in {'Nhà ở','Đất nền','Căn hộ chung cư'}:flags.append('UNRESOLVED_PROPERTY_TYPE')
    district,basis,candidates=geography.resolve(e.get('address_raw',''),source=source)
    if not district:flags.append('LOCATION_REQUIRES_EVIDENCED_MAPPING')
    # Use both list/detail values when supplied; conflicting labels never vote.
    card_price,_=amount(card.get('price_raw'));card_area=area(card.get('area_raw'))
    if card_price is not None and price is not None and card_price!=price:flags.append('LIST_DETAIL_PRICE_CONFLICT')
    if card_area is not None and sqm is not None and card_area!=sqm:flags.append('LIST_DETAIL_AREA_CONFLICT')
    if price and sqm and price>0 and sqm>0:
        unit=price/sqm
        if unit<1000000 or unit>500000000:flags.append('UNIT_PRICE_REQUIRES_REVIEW')
    row=dict(source=source,title=card.get('title',''),category=category,district=district,
        price_million=str(price/1000000) if price is not None else '',area_sqm=str(sqm) if sqm is not None else '',review_decision='',pipeline_review_codes='')
    if all(e.get(f) for f in ['identity_verified','structure_verified']) and e.get('price_million') and e.get('area_sqm'):
        decision,_,source_flags=detail_parser.decide(row,e)
        typed=labelled_areas(e.get('description',''));nonfloor=[n for kind,n in typed if kind!='FLOOR']
        # Comparison scope is typed: a clearly labelled floor area is stored
        # separately, never compared as if it were the land/asset area.
        if 'description_area_needs_review' in source_flags and typed and nonfloor and sqm and all(n==sqm for n in nonfloor) and any(kind=='FLOOR' for kind,n in typed):
            source_flags=[f for f in source_flags if f!='description_area_needs_review']
        flags.extend(c.upper() for c in source_flags)
        if decision=='exclude':reject.append('EXPLICIT_NON_MODEL_PROPERTY')
    # Boundaries already proven troublesome in old audit reports: fail early.
    text=norm(e.get('description','')+' '+e.get('title',''))
    if re.search(r'\bchi can\s*\d',text):flags.append('PARTIAL_OR_DOWNPAYMENT_PRICE')
    if re.search(r'\b(?:tai|toa lac|dia chi|vi tri)\b[^.!?]{0,150}\b(?:long an|tay ninh|binh dinh|ha noi|ho chi minh|dong nai)\b',text):reject.append('EXPLICIT_ASSET_OUTSIDE_SCOPE')
    if not e.get('description') or len(e.get('description',''))<30:flags.append('MISSING_ASSET_DESCRIPTION')
    dates=source_dates(card,body)
    current=datetime.fromisoformat(crawled_at).date();dated=dates['updated_at'] or dates['published_at']
    if not dated:flags.append('SOURCE_DATE_UNAVAILABLE')
    else:
        observed=date.fromisoformat(dated[:10]);age=(current-observed).days
        if age>max_age_days:flags.append('SOURCE_DATE_TOO_OLD')
        if age< -1:flags.append('SOURCE_DATE_IN_FUTURE')
    flags=sorted(set(flags+reject));status='REJECTED' if reject else 'NEEDS_REVIEW' if flags else 'READY_FOR_INTERNAL_REVIEW'
    ward=next((p.strip() for p in e.get('address_raw','').split(',') if re.match(r'^(phường|xã)\s+',p.strip(),re.I)),None)
    typed=labelled_areas(e.get('description',''));land={n for kind,n in typed if kind=='LAND'};floors={n for kind,n in typed if kind=='FLOOR'}
    if len(land)>1:flags.append('MULTIPLE_LAND_AREA_VALUES')
    if len(floors)>1:flags.append('MULTIPLE_FLOOR_AREA_VALUES')
    if category=='Nhà ở' and len(land)==1 and sqm and sqm!=next(iter(land)):flags.append('SOURCE_CARD_LAND_AREA_CONFLICT')
    flags=sorted(set(flags));status='REJECTED' if reject else 'NEEDS_REVIEW' if flags else 'READY_FOR_INTERNAL_REVIEW'
    record=dict(source=source,source_listing_id=str(card['source_listing_id']),record_key=source+':'+str(card['source_listing_id']),
        source_url=card['detail_url'],crawled_at=crawled_at,**dates,title=excerpt(e.get('title',card.get('title',''))),description=excerpt(e.get('description','')),
        transaction_type='SALE' if e.get('sale_verified') else None,property_type=category,category=category,
        price_vnd=str(price) if price is not None else None,price_million=str(price/1000000) if price is not None else None,area_sqm=str(sqm) if sqm is not None else None,
        land_area_sqm=str(next(iter(land))) if len(land)==1 else None,floor_area_sqm=str(next(iter(floors))) if len(floors)==1 else None,
        city='Đà Nẵng' if 'da nang' in norm(e.get('address_raw')) else None,district=district or None,ward=ward,address=excerpt(e.get('address_raw','')),
        latitude=None,longitude=None,images=[],quality_status=status,quality_score=max(0,100-len(flags)*10),quality_flags=flags,
        verification_status='UNVERIFIED',duplicate_status='NOT_CHECKED',holdout_status='NOT_CHECKED',evidence_status='NOT_STORED',
        source_fields={'price_raw':e.get('price_raw'),'area_raw':e.get('area_raw'),'category_raw':e.get('source_category'),'address_raw':excerpt(e.get('address_raw',''))},
        normalization_basis={'price':'EXPLICIT_SOURCE_TOTAL_VND_ONLY','area':'EXPLICIT_SOURCE_LABEL_UNSPECIFIED_BASIS','district':basis,'mapping_reference':geography.REFERENCE},
        training_allowed=False,public_display_allowed=False)
    return record
