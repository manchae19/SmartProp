"""Pre-score source scope and duplicate candidates; never use target/residual."""
import re
import training_v3_common as c

POLICY=dict(scope='ordinary house/residential land/single apartment; ambiguous cases held for review',
    duplicate='Cross-current-group exact long seller prose OR long exact masked title plus category/location/area',
    min_body_words=50,min_body_unique_words=30,min_title_words=12,min_title_chars=90,
    targets_used=False,residuals_used=False,duplicates_are_candidates_not_verified_physical_identity=True)
FOOTER=re.compile(r'\b(?:quy khach|lien he|tu van bat dong san|chuyen nhan ky|nhan ky gui|san giao dich|hay goi|pkd)\b')
FUTURE=re.compile(r'\b(?:thich hop (?:de )?xay|phu hop (?:de )?xay|co the xay|phuong an|du kien|tiem nang xay|ly tuong xay|xay moi|quy hoach)\b')


def title_text(row):
    text=c.normalized(row['title'])
    if row['source']=='cafeland':text=re.sub(r'^(?:ban nha rieng|ban nha mat pho|ban biet thu|biet thu|ban dat tho cu|ban can ho chung cu)\s*:\s*','',text)
    return text


def mask_money(text):
    text=c.normalized(text)
    text=re.sub(r'(?<!\w)\d[\d.,]*\s*vnd\b',' money ',text)
    return re.sub(r'(?<![\w.,])\d+(?:[.,]\d+)?\s*(?:ty|ti|toi|trieu|tr)\b(?:\s*\d{1,3}(?:\s*trieu)?)?',' money ',text)


def title_signature(row):
    text=title_text(row)
    text=re.sub(r'\blam viec truc tiep gia tot.*$','',text)
    text=' '.join(re.findall(r'\w+',mask_money(text)))
    return text if len(text.split())>=12 and len(text)>=90 else ''


def body_signature(evidence):
    if not evidence or not evidence.get('identity_verified'):return ''
    text=c.normalized(evidence.get('asset_description',evidence.get('description','')))
    text=FOOTER.split(text)[0]
    text=re.sub(r'^\s*\d+[.)]?\s+','',text)
    text=' '.join(re.findall(r'\w+',mask_money(text)))
    words=text.split()
    return text if len(words)>=50 and len(set(words))>=30 else ''


def scope_flags(row,evidence=None):
    sources=[('collected_title',title_text(row))]
    if evidence and evidence.get('identity_verified'):
        sources.append(('identity_verified_saved_body',FOOTER.split(c.normalized(evidence.get('asset_description',evidence.get('description',''))))[0]))
    flags=[]
    for source,text in sources:
        clauses=re.split(r'\n|(?<!\d)[.!?;]',text)
        for clause in clauses:
            patterns=[('explicit_special_asset_subject',r'\b(?:ban|chuyen nhuong)\s+(?:nguyen\s+)?(?:day tro|nha tro|khach san|nha nghi|shophouse|condotel|toa (?:nha )?(?:can ho|chdv))\b'),
                ('multiple_assets_or_inventory',r'\b(?:ban\s+)?(?:[2-9]|\d{2,})\s*(?:lo dat|lo lien ke|can nha|can ho)\b|\bgio hang\b'),
                ('partial_starting_or_booking',r'\b(?:tra truoc|von ban dau|von tu co|booking|gia tu|chi tu)\b')]
            if row['category']=='Đất nền':patterns.append(('garden_or_agricultural_land_scope',r'\b(?:ban\s+)?dat\s+(?:vuon|nong nghiep|nong lam nghiep)\b'))
            if row['category']=='Nhà ở':patterns.append(('existing_multiple_rental_units',r'\b(?:[2-9]|\d{2,})\s*(?:phong tro|(?:can )?phong (?:khep|kep) kin)\b|\bday tro\b'))
            for rule,pattern in patterns:
                for m in re.finditer(pattern,clause):
                    before=clause[max(0,m.start()-100):m.start()]
                    if FUTURE.search(before) or re.search(r'\b(?:gan|cach|canh|doi dien)\b[^,;]{0,45}$',before):continue
                    flags.append(dict(rule=rule,source=source,quote=clause[max(0,m.start()-60):m.end()+80]))
    if evidence and evidence.get('identity_verified') and evidence.get('category') and evidence['category']!=row['category']:
        flags.append(dict(rule='specific_source_category_disagrees_with_frozen_category',source='saved_category',quote=evidence['category']))
    return flags
