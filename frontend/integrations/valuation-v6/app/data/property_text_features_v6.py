"""Literal listing claims with evidence; no price, coordinates, or guessed values."""
import json
import re
import training_v3_common as c

FEATURES=['rooms_completed','floors_claim','access_claim','house_subtype_claim']
FUTURE=re.compile(r'\b(?:co the xay|du kien|phuong an|xay moi|xay dung moi|xay duoc|duoc phep xay|quy hoach|toi da|thich hop (?:de )?xay|phu hop (?:de )?xay|tiem nang xay|ly tuong xay|thiet ke du kien)\b')
NEAR=re.compile(r'\b(?:gan|cach|canh|ke ben|doi dien|phia sau|sau lung)\b[^,;.!?]{0,35}$')
FOOTER=re.compile(r'\b(?:quy khach|lien he|tu van bat dong san|chuyen nhan ky|nhan ky gui|san giao dich|hay goi|pkd)\b')
MULTI=re.compile(r'\b(?:day tro|\d+\s*phong tro|\d+\s*(?:can )?phong (?:khep|kep) kin|gio hang|nhieu can|cac can|nhieu lo|cac lo)\b')


def units(text):
    # Work on literal sentences, not a bag of words. Keep original quotes.
    text=text.replace('/n','\n').replace('\\n','\n')
    result=[]
    for raw in re.split(r'\n|(?<!\d)[.!?;]',text):
        normalized=c.normalized(raw).replace('*','').replace('#','')
        if normalized.strip():result.append((raw.strip(),normalized))
    return result


def before_is_other_subject(text,start):
    before=text[max(0,start-85):start]
    return bool(NEAR.search(before) or FUTURE.search(before) or re.search(r'\b(?:khong|chua)(?:\s+(?:phai|co))?\s*$',before))


def extract(row,origin,body='',body_sha256=''):
    candidates={field:[] for field in FEATURES}
    excluded=[]
    def claim(field,value,kind,quote,rule):
        candidates[field].append(dict(field=field,value=value,source_kind=kind,source_quote=quote,
            rule=rule,source_sha256=body_sha256 if kind=='verified_detail_body' else ''))
    if row['rooms']:
        claim('rooms_completed',int(row['rooms']),'structured_rooms',str(row['rooms']),'existing_structured_rooms')
    raw_title=origin['title']
    # A CafeLand source-inserted category is metadata rather than an access claim.
    if row['source']=='cafeland':
        raw_title=re.sub(r'^(?:Bán nhà riêng|Bán nhà mặt phố|Bán biệt thự|Biệt thự|Bán đất thổ cư|Bán căn hộ chung cư)\s*:\s*','',raw_title,flags=re.I)
    sources=[('collected_title',raw_title)]
    if body:sources.append(('verified_detail_body',body))
    multi=any(MULTI.search(c.normalized(text)) for _,text in sources)
    for kind,text in sources:
        # Retain source wording in quotes, but do not classify the broker footer.
        cut=FOOTER.search(c.normalized(text))
        if cut:
            # Locate the footer through original clauses, avoiding normalized offsets.
            selected=[]
            for raw,normalized in units(text):
                m=FOOTER.search(normalized)
                if m:
                    # Unicode accent stripping preserves character lengths except
                    # whitespace; taking the prefix of the normalized clause is
                    # safe for matching. Quote stays the original whole clause.
                    selected.append((raw,normalized[:m.start()]))
                    break
                selected.append((raw,normalized))
        else:selected=units(text)
        for quote,t in selected:
            # "Võ Văn Kiệt" is a street name. MT width alone is parcel frontage.
            t=re.sub(r'\b(?:vo van kiet|ly thuong kiet)\b',' street_name ',t)
            if row['category']!='Đất nền' and not multi:
                for m in re.finditer(r'(?<![\w.,])(\d{1,2})\s*(?:pn\b|phong ngu\b|p\s*ngu\b)',t):
                    before=t[max(0,m.start()-100):m.start()]
                    if (before_is_other_subject(t,m.start()) or re.search(r'\btang\s*\d+\s*[:=-]',before)
                        or re.search(r'\d+\s*(?:[-–]|den|toi)\s*$',before)):
                        excluded.append('bedrooms_other_or_floor_specific');continue
                    value=int(m[1])
                    if 1<=value<=30:claim('rooms_completed',value,kind,quote,'explicit_bedrooms_not_rental_units')
            if row['category']=='Nhà ở' and not multi:
                pattern=r'\b(?:nha|biet thu|ket cau|quy mo|hien trang)(?:\s*[:=-]\s*|\s+)(\d+(?:[.,]\d+)?)\s*tang\b'
                for m in re.finditer(pattern,t):
                    if before_is_other_subject(t,m.start()):
                        excluded.append('floors_future_or_nearby');continue
                    value=float(m[1].replace(',','.'))
                    if 1<=value<=20:claim('floors_claim',value,kind,quote,'explicit_existing_house_floor_count')
                for m in re.finditer(r'\b(?:can )?biet thu\b|\bnha\s*(?:cap\s*4|c4)\b',t):
                    before=t[max(0,m.start()-85):m.start()]
                    if before_is_other_subject(t,m.start()) or re.search(r'\b(?:dat|lo|xay|khu|loi|day|cum|cac)\s*$',before):continue
                    claim('house_subtype_claim','villa' if 'biet thu' in m[0] else 'house_c4',kind,quote,'literal_existing_house_subtype')
            if row['category'] in ['Nhà ở','Đất nền']:
                # Negative/nearby claims are explicitly unknown, not inferred opposites.
                for m in re.finditer(r'\b(?:kiet|hem)\b|\bmat (?:tien|pho)\b|\bmt\s+duong\b',t):
                    before=t[max(0,m.start()-85):m.start()]
                    after=t[m.end():m.end()+30]
                    if before_is_other_subject(t,m.start()) or re.search(r'\b(?:khong|chua)(?:\s+phai)?\s*(?:nha\s+)?(?:trong\s+)?$',before):
                        excluded.append('access_negated_nearby_or_future');continue
                    access='alley' if m[0] in ['kiet','hem'] else 'frontage'
                    if access=='frontage' and re.match(r'\s*[:=]?\s*\d+(?:[.,]\d+)?\s*m',after):
                        excluded.append('parcel_frontage_width_not_street_access');continue
                    claim('access_claim',access,kind,quote,'explicit_property_access_claim')
    # Source-specific villa category supports subtype, but broad "nhà riêng"
    # does not prove it is an ordinary house rather than a villa.
    raw=json.loads(origin['raw_json'])
    source_category=c.normalized(raw.get('source_category',''))
    if row['category']=='Nhà ở' and source_category in ['ban-biet-thu','biet thu','biet thu, nha lien ke']:
        if source_category!='biet thu, nha lien ke':
            claim('house_subtype_claim','villa','structured_source_category',str(raw['source_category']),'explicit_villa_source_category')
    values={};evidence=[];conflicts=[]
    for field,claims in candidates.items():
        distinct={r['value'] for r in claims}
        if len(distinct)==1:
            values[field]=next(iter(distinct))
            for r in claims:evidence.append(dict(r,status='accepted'))
        elif len(distinct)>1:
            # Keep the original structured room value, but add no text inference.
            structured=[r for r in claims if r['source_kind']=='structured_rooms']
            values[field]=structured[0]['value'] if field=='rooms_completed' and structured else ''
            conflicts.append(field)
            for r in claims:evidence.append(dict(r,status='conflict_structured_retained' if r in structured else 'conflict_not_used'))
        else:values[field]=''
    if multi:excluded.append('multi_asset_or_rental_unit_context_no_room_floor_subtype_inference')
    return dict(values,conflict_fields=';'.join(conflicts),extraction_notes=';'.join(sorted(set(excluded)))),evidence


def feature_spec(train,category,arm):
    groups={'control':[], 'rooms_floors':['rooms_floors'], 'access':['access'],
            'subtype':['subtype'], 'all':['rooms_floors','access','subtype']}[arm]
    extra=[]
    if 'rooms_floors' in groups and category=='Nhà ở':extra+=['floors_claim','floors_missing']
    if 'access' in groups and category in ['Nhà ở','Đất nền']:
        extra+=['access_alley','access_frontage','access_missing']
    if 'subtype' in groups and category=='Nhà ở':extra+=['subtype_villa','subtype_house_c4','subtype_missing']
    base=c.schema(train)
    return dict(category=category,arm=arm,groups=groups,base_schema=base,
        feature_names=base['feature_names']+extra,extra_features=extra,
        text_values='literal source claims, missing if ambiguous; not verified measurements')


def encode(rows,features,spec):
    import numpy as np
    enriched=[dict(r,rooms=str(features[r['record_key']]['rooms_completed'])) if 'rooms_floors' in spec['groups'] else dict(r) for r in rows]
    base=c.encode(enriched,spec['base_schema'])
    extra=[]
    for row in rows:
        f=features[row['record_key']]
        access=f['access_claim'];subtype=f['house_subtype_claim'];floors=f['floors_claim']
        values=dict(floors_claim=float(floors) if str(floors) else np.nan,floors_missing=float(not str(floors)),
            access_alley=float(access=='alley'),access_frontage=float(access=='frontage'),access_missing=float(not access),
            subtype_villa=float(subtype=='villa'),subtype_house_c4=float(subtype=='house_c4'),subtype_missing=float(not subtype))
        extra.append([values[k] for k in spec['extra_features']])
    return np.concatenate([base,np.asarray(extra,dtype=np.float32)],axis=1) if spec['extra_features'] else base
