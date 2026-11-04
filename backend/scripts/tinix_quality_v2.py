"""TINIX_RESEARCH_V2 proposal, pure functions only; no importer integration.

Decimal money grammar + contextual asset counts. Raw values and unrelated V1
issues are immutable. A cleared reason is not automatically a trusted listing.
"""
import re
from decimal import Decimal,InvalidOperation
from tinix_quality import norm,exact_decimal

RULE='TINIX_RESEARCH_V2'
MULTI='MULTIPLE_ASSETS';SHORT='SHORTHAND_TOTAL_PRICE'
V1_MULTI=re.compile(r'\b(\d+|hai|ba|nhieu)\s+(lo dat|can nha|can ho|lo lien ke)\b|\b(cap lo|ro hang|bang hang|nhieu lo|nhieu can|day tro|day phong)\b')
WORDS={'mot':1,'hai':2,'ba':3,'bon':4,'nam':5,'sau':6,'bay':7,'tam':8,'chin':9,'muoi':10}
COUNT=re.compile(r'(?<![\w.,])(?P<n>\d+|mot|hai|ba|bon|nam|sau|bay|tam|chin|muoi)[ \t]*(?P<noun>lo(?:[ \t]+(?:dat|lien ke))?|can(?:[ \t]+(?:nha|ho))?|ngoi nha|nha)(?![\w])')
PHRASE=re.compile(r'\b(cap lo|cap dat|nhieu lo|nhieu can|day tro|day phong|ro hang|gio hang|bang hang)\b')
INVENTORY=re.compile(r'\b(?:ban (?:ca|nguyen|tron) (?:block|du an|khu)|ban si|mo ban (?:du an|toan bo)|phan phoi (?:du an|doc quyen)|bang gia (?:cac|nhieu) (?:lo|can)|gia tu .{0,25}den .{0,25}/(?:lo|can))\b')
H=r'[ \t]*';NUM=r'\d+(?:[.,]\d+)*'
BILLION=re.compile(r'(?<![\d.,])(?P<base>'+NUM+r')'+H+r'(?P<unit>ty|ti)(?![a-z])(?P<tail>[ \t]*\d+(?:[.,]\d+)*[ \t]*(?:trieu|tr\b)?)?',re.I)
MILLION=re.compile(r'(?<![\d.,])(?P<base>'+NUM+r')'+H+r'(?:trieu|tr)(?!\w)')
VND=re.compile(r'(?<![\d.,])(?P<base>'+NUM+r')'+H+r'(?:vnd|dong|d)(?!\w)')
MASK=re.compile(r'\b\d+[.,]?[x?]+\s*(?:ty|ti|trieu|tr)(?!\w)|\b\d+\s*(?:ty|ti)\s*\d*[x?]+(?!\w)|\b[x?]+\s*(?:ty|ti|trieu)\b|\b(?:gia|chi tu)\s*:?\s*\d+[.,]?[x?]+(?!\w)')
PER_ASSET=re.compile(r'(?:/\s*(?:lo|can|nen)\b|\b(?:moi|tung|tren mot|tren)\s+(?:lo|can|nen)\b)')
PER_AREA=re.compile(r'(?:/\s*m[²2]\b|\b(?:moi|mot|tren)\s+m[²2]\b)')
PARTIAL=re.compile(r'\b(tra truoc|thanh toan truoc|von tu co|so huu chi tu)\b|\bcoc truoc\s+\d+(?:[.,]\d+)?\s*(?:ty|ti|trieu|tr\b|%)')
AREA=re.compile(r'(?<![\w.,])(?P<n>\d+(?:[.,]\d+)?)\s*m[²2](?!\w)')
PHYSICAL=re.compile(r'\s*(?:m[²2]?\b|tang\b|lau\b|pn\b|phong\b|wc\b|can\b|lo\b|mat tien\b|duong\b)')

def context(text,start,end):return text[max(0,start-70):min(len(text),end+85)]
def reference(text,start):
    before=text[max(0,start-75):start]
    # Use the closest relation; a fresh sale verb overrides an earlier landmark.
    refs=list(re.finditer(r'\b(gan|cach|doi dien|ke ben|ben canh|xung quanh|di qua|sat)\b',before))
    sales=list(re.finditer(r'\b(ban|gom|so huu|chao|con|mua)\b',before))
    if not refs or sales and refs[-1].start()<sales[-1].start():return False
    between=before[refs[-1].end():]
    # A landmark earlier in a paragraph must not swallow a later stock count.
    return len(between)<=32 and not re.search(r'\d|[.;:!?]',between)
def capacity(text,start):
    before=text[max(0,start-85):start]
    future=bool(re.search(r'(?:xay duoc|co the (?:xay|chia|tach)|duoc phep xay|thich hop xay|phu hop xay|du dien tich (?:xay|chia)|chia duoc|tach duoc)\s*(?:them|thanh|toi da|len den)?\s*$',before))
    return future and not re.search(r'\bda\s+(?:xay|chia|tach)',before[-45:])

def assets(row,had_v1=False):
    flags=set();reasons=set();evidence=[];old_count=0;old_explained=0
    for field in ['name','description']:
        text=norm(row.get(field));counts=[]
        for m in COUNT.finditer(text):
            n=int(m['n']) if m['n'].isdigit() else WORDS[m['n']]
            tail=text[m.end():m.end()+25]
            before=text[max(0,m.start()-35):m.start()]
            if re.search(r'\d+\s*/\s*$',before):code='FRACTION_OR_COMPARISON_NOT_ASSET_COUNT'
            elif m['noun']=='can' and re.match(r'\s*(thi|giang|lo)\b',tail):code='LOCATIONAL_PROVERB_NOT_ASSET_COUNT'
            elif re.search(r'\b(?:ty|ti)\s*$',before):code='PRICE_ASSET_BOUNDARY_UNRESOLVED';flags.add('V2_PRICE_ASSET_BOUNDARY_UNRESOLVED')
            elif m['n']=='nam' and re.search(r'(?:\d+|dau|cuoi|trong|dip|nam|sau|truoc|den)\s*$',before):code='YEAR_NOT_ASSET_QUANTITY'
            elif re.search(r'\b(?:duong|lo so|so nha|so can)\s*$',before):code='ADDRESS_NUMBER_NOT_ASSET_QUANTITY'
            elif m['noun']=='nha' and re.match(r'\s*(ve sinh|tam|hang)\b',tail):code='NON_ASSET_ROOM_OR_BUSINESS_NOUN'
            elif m['noun']=='can' and n>1 and re.match(r'\s*(ban(?! giao)|mua|tim|thue|gap)\b',tail):code='AMBIGUOUS_UNACCENTED_NOUN';flags.add('V2_ASSET_COUNT_UNRESOLVED')
            elif reference(text,m.start()):code='LANDMARK_OR_DISTANCE_REFERENCE'
            elif capacity(text,m.start()):code='FUTURE_BUILDING_CAPACITY'
            elif n==1:code='SINGLE_ASSET_MENTION'
            elif not m['n'].isdigit() and m['noun'] in {'nha','can'} and not re.search(r'\b(?:ban|gom|co|con|so luong|tong|chao ban)\s*$',before):code='WORD_OR_NAME_NOT_PROVEN_ASSET_COUNT'
            elif n>=2:code='EXPLICIT_MULTIPLE_ASSET_COUNT';flags.add(MULTI)
            else:code='INVALID_ASSET_COUNT';flags.add('V2_ASSET_COUNT_UNRESOLVED')
            reasons.add(code);counts.append((m.start(),m.end(),code));evidence.append(dict(field=field,reason=code,span=m.group(),context=context(text,m.start(),m.end())))
        for m in PHRASE.finditer(text):
            if reference(text,m.start()):code='LANDMARK_OR_DISTANCE_REFERENCE'
            elif m.group() in {'gio hang','ro hang','bang hang'} and re.search(r'\bcon\s+(?:duy nhat\s+)?(?:1|mot)\s+can\b',text[m.end():m.end()+65]):
                code='SINGLE_UNIT_WITH_INVENTORY_CONTEXT';flags.add('V2_PROJECT_INVENTORY_CONTEXT')
            elif m.group() in {'cap lo','cap dat'}:code='PAIR_OF_ASSETS';flags.add(MULTI)
            else:code='ASSET_INVENTORY_OR_WHOLE_BUILDING';flags.add(MULTI)
            reasons.add(code);counts.append((m.start(),m.end(),code));evidence.append(dict(field=field,reason=code,span=m.group(),context=context(text,m.start(),m.end())))
        for m in INVENTORY.finditer(text):
            if not reference(text,m.start()):
                flags.add('V2_PROJECT_INVENTORY_CONTEXT');reasons.add('PROJECT_INVENTORY_CONTEXT')
                evidence.append(dict(field=field,reason='PROJECT_INVENTORY_CONTEXT',span=m.group(),context=context(text,m.start(),m.end())))
        for m in V1_MULTI.finditer(text):
            old_count+=1
            if any(a<=m.start()<b or m.start()<=a<m.end() for a,b,c in counts):old_explained+=1
    if had_v1 and not flags and (old_count==0 or old_count!=old_explained):
        flags.add('V2_MULTI_CONTEXT_UNRESOLVED');reasons.add('V1_MULTI_TRIGGER_NOT_FULLY_EXPLAINED')
    if had_v1 and not flags:reasons.add('V1_MULTIPLE_ASSETS_FALSE_POSITIVE')
    return flags,reasons,evidence

def decimal_number(text):
    if text.count(',')+text.count('.')>1:return None
    # Three digits after a dot can mean decimal or thousands; never fit to price.
    if re.fullmatch(r'\d{1,3}\.\d{3}',text):return None
    try:return Decimal(text.replace(',','.'))
    except InvalidOperation:return None
def price_context(text,start,end):
    before=text[max(0,start-55):start];tail=text[end:end+35]
    if re.search(r'(?:thue|thu nhap|doanh thu|dong tien|loi nhuan|giam|chiet khau|thap hon|ho tro|vay|chenh|hoa hong)\D{0,22}$',before) or re.match(r'\s*(?:/\s*(?:thang|thg\b|th\b|nam)|thang\b|nam\b)',tail):return 'REFERENCE_PRICE_NOT_SALE_TOTAL'
    if not re.search(r'\bdau tu\s*$',before) and re.search(r'\b(?:gia\s*(?:ban)?\s*)?(?:chi\s*)?tu\s*:?\s*$',before):return 'STARTING_PRICE_NOT_FIXED_TOTAL'
    if PER_AREA.match(tail.strip()):return 'UNIT_PRICE_PER_SQM'
    if PER_ASSET.match(tail.strip()) or re.search(r'\b(?:moi|tung)\s+(?:lo|can|nen)\s*(?:gia|ban|tu)?\s*:?\s*$',before):return 'UNIT_PRICE_PER_ASSET'
    return 'TOTAL_PRICE_CLAIM'

def prices(row,had_v1=False):
    expected=exact_decimal(row.get('price'),2,24);flags=set();reasons=set();evidence=[];claims=[];ambiguous=[];masked=False;units=[]
    for field in ['name','description']:
        text=norm(row.get(field));covered=[]
        if MASK.search(text):flags.add('V2_AMBIGUOUS_PRICE_TEXT');reasons.add('MASKED_PRICE_NOT_INFERRED');masked=True
        if PARTIAL.search(text):flags.add('V2_PARTIAL_PRICE_CONTEXT');reasons.add('DOWNPAYMENT_NOT_TOTAL')
        for m in BILLION.finditer(text):
            base=decimal_number(m['base']);value=base*10**9 if base is not None else None;code='EXPLICIT_BILLION_TOTAL';tail=m['tail'] or '';end=m.end()
            if tail:
                digit=re.match(r'\s*(\d+(?:[.,]\d+)*)',tail);suffix=digit[1];after=text[m.start('tail')+digit.end():]
                if PHYSICAL.match(after):
                    end=m.start('tail');code='PRICE_FOLLOWED_BY_PHYSICAL_ATTRIBUTE'
                elif re.search(r'(trieu|tr)\s*$',tail):
                    extra=decimal_number(suffix);value=value+extra*10**6 if value is not None and extra is not None and extra<1000 else None;code='EXPLICIT_BILLION_PLUS_MILLION'
                elif suffix.isdigit() and len(suffix)==3:
                    value=value+Decimal(suffix)*10**6 if value is not None else None;code='THREE_DIGIT_MILLION_SHORTHAND'
                elif suffix.isdigit() and len(suffix)==1 and not tail.startswith(' '):
                    value=value+Decimal(suffix)*10**8 if value is not None else None;code='COMPACT_TENTH_BILLION'
                elif suffix.isdigit() and len(suffix) in {1,2} and value is not None:
                    candidates={value+Decimal(suffix)*10**6,value+Decimal(suffix)*Decimal(10)**(9-len(suffix))}
                    ambiguous.append((candidates,field,m.group()));value=None;code='SHORT_SUFFIX_REQUIRES_INDEPENDENT_CORROBORATION'
                else:value=None;code='UNRESOLVED_BILLION_SUFFIX'
            category=price_context(text,m.start(),end)
            evidence.append(dict(field=field,reason=code,span=text[m.start():end],kind=category,parsed_vnd=str(value) if value is not None else None))
            reasons.add(code);covered.append((m.start(),m.end()))
            if category.startswith('UNIT_PRICE'):units.append(category)
            elif category=='STARTING_PRICE_NOT_FIXED_TOTAL':flags.add('V2_STARTING_PRICE_NOT_TOTAL')
            elif category=='TOTAL_PRICE_CLAIM':
                if value is not None:claims.append(value)
                elif code!='SHORT_SUFFIX_REQUIRES_INDEPENDENT_CORROBORATION':flags.add('V2_UNRESOLVED_TOTAL_PRICE')
        for pattern,multiplier in [(MILLION,10**6),(VND,1)]:
            for m in pattern.finditer(text):
                if any(a<=m.start()<b for a,b in covered):continue
                n=m['base'];value=None
                if multiplier==1 and re.fullmatch(r'\d{1,3}(?:[.,]\d{3})+',n):value=Decimal(re.sub('[.,]','',n))
                else:value=decimal_number(n)
                if value is not None:value*=multiplier
                category=price_context(text,m.start(),m.end())
                if pattern is VND and re.match(r'\s*(?:song|kenh|suoi|thac)\b',text[m.end():]):category='NON_MONETARY_DONG_WORD';reasons.add('NON_MONETARY_DONG_WORD')
                evidence.append(dict(field=field,reason='EXPLICIT_MILLION_OR_VND',span=m.group(),kind=category,parsed_vnd=str(value) if value is not None else None))
                if category.startswith('UNIT_PRICE'):units.append(category)
                elif category=='STARTING_PRICE_NOT_FIXED_TOTAL':flags.add('V2_STARTING_PRICE_NOT_TOTAL')
                elif category=='TOTAL_PRICE_CLAIM':
                    if value is None:flags.add('V2_UNRESOLVED_TOTAL_PRICE')
                    else:claims.append(value)
        # Price per asset may omit currency; area-per-lot is not a price claim.
        for unit in PER_ASSET.finditer(text):
            prefix=text[max(0,unit.start()-45):unit.start()]
            if re.search(r'm[²2]\s*$',prefix):continue
            if re.search(r'(?:\bgia\b|ty|ti|trieu|\btr\b|xx)[^.;]{0,22}$',prefix):
                flags.add('V2_PER_ASSET_PRICE_NOT_TOTAL');reasons.add('PER_LOT_OR_UNIT_NOT_TOTAL')
    independent=set(claims)
    for candidates,field,span in ambiguous:
        corroborated=independent & candidates
        if len(independent)==1 and len(corroborated)==1:
            claims.append(next(iter(corroborated)));reasons.add('SHORT_SUFFIX_INDEPENDENTLY_CORROBORATED')
        else:flags.add('V2_UNRESOLVED_TOTAL_PRICE')
    if claims and expected is None:flags.add('V2_RAW_PRICE_NOT_COMPARABLE');reasons.add('RAW_PRICE_NOT_COMPARABLE')
    elif claims and any(v!=expected for v in claims):
        flags.add('V2_EXACT_TOTAL_PRICE_CONFLICT');reasons.add('TOTAL_PRICE_DIFFERS_FROM_RAW_DECIMAL')
    if len(set(claims))>1:flags.add('V2_MULTIPLE_TOTAL_PRICE_VALUES')
    if 'UNIT_PRICE_PER_ASSET' in units:flags.add('V2_PER_ASSET_PRICE_NOT_TOTAL');reasons.add('PER_LOT_OR_UNIT_NOT_TOTAL')
    if units and not claims:flags.add('V2_UNIT_PRICE_WITHOUT_EXPLICIT_TOTAL')
    if had_v1 and not claims:flags.add('V2_UNRESOLVED_TOTAL_PRICE')
    if had_v1 and not flags:reasons.add('V1_SHORTHAND_RESOLVED_EXACTLY')
    return flags,reasons,evidence

def area_contradictions(row):
    area=exact_decimal(row.get('area'),6,18);title=norm(row.get('name'));flags=set()
    if area:
        values=[decimal_number(m['n']) for m in AREA.finditer(title)]
        if any(v is not None and v!=area for v in values):flags.add('V2_TITLE_AREA_CONFLICT')
    return flags

def evaluate(row,v1_issues,v1_status,held=False):
    old=set(v1_issues);af,ar,ae=assets(row,MULTI in old);pf,pr,pe=prices(row,SHORT in old)
    issues=(old-{MULTI,SHORT})|af|pf|area_contradictions(row)
    if held:issues.add('PROTECTED_HOLDOUT_FINGERPRINT_CONFLICT')
    # Never overturn excluded/holdout or clear any unrelated V1 reason.
    status='EXCLUDED' if held or v1_status=='EXCLUDED' else 'NEEDS_REVIEW' if issues else 'HYBRID_ELIGIBLE_RESEARCH'
    return dict(rule=RULE,quality_status=status,quality_issues=sorted(issues),reason_codes=sorted(ar|pr),
        multi_reason_false_positive=MULTI in old and not af,shorthand_reason_resolved=SHORT in old and not pf,
        newly_detected_multi=MULTI not in old and bool(af & {MULTI,'V2_PROJECT_INVENTORY_CONTEXT'}),
        multi_evidence=ae,price_evidence=pe)
