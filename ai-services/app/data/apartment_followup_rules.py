"""Versioned source-text fixes; frozen pilot rules and labels stay unchanged."""
import re
import review_apartment_pilot as previous
from review_apartment_labels import MONEY, AREA
from remaining_diversity_rules import shorthand
from smartprop_geography import norm


def subject(text):
    value=re.sub(r'^thong tin mo ta\s*','',norm(text))
    # Only a leading source metadata heading may be removed. A trailing
    # "liên hệ để nhận thông tin chi tiết" must not erase the seller prose.
    value=re.sub(r'^ban can ho chung cu\s+.{0,160}?, da nang\s*(?:thong tin chi tiet\s*)?','',value,count=1)
    value=previous.FOOTER.split(value)[0]
    # CafeLand's repeated header echo is not independent seller evidence.
    value=re.sub(r'(?:xem them\s*)?gia\s*:\s*[\d., ]+\s*(?:vnd|dong)\s+dien tich\s*:\s*[\d., ]+\s*m[2²]\s*$','',value)
    return value.strip()


def money_mentions(value):
    value=norm(value);result=[]
    for match in MONEY.finditer(value):
        before=value[max(0,match.start()-65):match.start()]
        after=value[match.end():match.end()+40]
        amount=float(match[1].replace(',','.'))*(1000 if match[2] in ['ty','ti'] else 1)
        if match[3]:amount+=float(match[3])
        kind='total_candidate'
        explicit=bool(re.search(r'\bgia\s*(?:chao\s+ban|ban|chuyen nhuong|chao)?\s*[:=]?\s*$',before))
        if re.match(r'\s*(?:/\s*m[2²]|mot m[2²])',after):kind='unit_price'
        elif re.match(r'\s*(?:/\s*(?:th|thang|nam)|th\b|thang\b)',after):kind='rental_income'
        elif re.search(r'\b(?:tra truoc|thanh toan|chi tu|gia tu)\b.{0,20}$',before):kind='partial_or_starting'
        elif re.match(r'\s*(?:nhinh(?:\s+nhe)?|tro len|do lai|do xuong)\b',after):kind='bound'
        elif not explicit:
            if re.search(r'\b(?:dong tien|thu nhap|cho thue|tien thue)\b.{0,20}$',before):kind='rental_income'
            elif re.search(r'\b(?:giam|thap hon|re hon|chiet khau|lo|loi|tiet kiem)\b.{0,20}$',before):kind='discount_or_profit'
            elif re.search(r'\b(?:chua toi|duoi|hon|tu)\b.{0,8}$',before):kind='bound'
        result.append(dict(amount_million=amount,kind=kind,normalized_excerpt=value[max(0,match.start()-65):match.end()+40]))
    return result


def quality(row,catalog):
    body=subject(row['description'])
    # Remove only a nonsemantic heading phrase before passing the corrected
    # seller boundary to v1. Do not alter any price, area or claim.
    adapted=dict(row,description=body.replace('thong tin chi tiet',' '))
    result=previous.quality(adapted,catalog)
    flags=set(result['review_codes'])
    flags.difference_update(['title_total_price_conflict','description_total_price_conflict',
                             'single_unit_price_area_not_corroborated_in_seller_description'])
    p,a=row['price_million'],row['area_sqm']
    proof=False;mentions={}
    for label,value in [('title',norm(row['title'])),('description',body)]:
        checked,fix=shorthand(value,p) if p is not None else (value,[])
        result['resolutions']+=fix
        found=money_mentions(checked);mentions[label]=found
        totals=[m['amount_million'] for m in found if m['kind']=='total_candidate']
        if p is not None and any(abs(v-p)/max(v,p)>.01 for v in totals):flags.add(label+'_total_price_conflict')
        if label=='description' and p is not None and a is not None and a>0:
            areas=[float(m[1].replace(',','.')) for m in AREA.finditer(value)]
            proof=any(abs(v-p)/max(v,p)<=.01 for v in totals) and any(abs(v-a)/max(v,a)<=.01 for v in areas)
    if not proof:flags.add('single_unit_price_area_not_corroborated_in_seller_description')
    # Literal funding-only amounts and the misspelling "codotel" remain out.
    if re.search(r'\b(?:von chi|chi can dong truoc|von ban dau|chi can\s*\d+%)\b',body):flags.add('partial_starting_or_booking_price')
    if re.search(r'\b(?:codotel|condotel)\b',norm(row['title'])+' '+body):flags.add('nonstandard_apartment_review')
    original=previous.quality(row,catalog)
    result.update(review_codes=sorted(flags),resolved_previous_codes=sorted(set(original['review_codes'])-flags),
        added_codes=sorted(flags-set(original['review_codes'])),price_mentions=mentions)
    return result


def scope_exclusions(row):
    title=norm(row['title']);body=subject(row['description'])
    codes=[];proof=[]
    def add(code,field,pattern,value):
        match=re.search(pattern,value)
        if match:
            codes.append(code);proof.append(dict(code=code,source_field=field,
                normalized_excerpt=value[max(0,match.start()-30):match.end()+100]))
    add('outside_da_nang_literal_title','title',r'\b(?:tp\.?|thanh pho|tinh)\s+(?:hue|ha noi|ho chi minh|nha trang|quy nhon|quang ngai|binh dinh)\b',title)
    add('whole_building_not_single_apartment','description',r'^(?:\d+\s+)?(?:ban\s+)?toa (?:nha\s+)?can ho\b|\bban toa can ho\b',body)
    if 'dien tich dat' in body:
        add('whole_homestay_not_single_apartment','description',r'^homestay\b',body)
    if re.match(r'^(?:can\s+)?cho thue\b',title) and re.search(r'\bgia thue\b',body):
        add('rental_offer_not_sale_cohort','title',r'^cho thue\b',title)
    return sorted(set(codes)),proof


def evidence(row,review):
    body=subject(row['description'])
    return dict(cache_sha256=row['response_sha256'],detail_file=row['detail_file'],
        structured_price_quote=row['price_raw'],structured_area_quote=row['area_raw'],
        original_title_quote=row['title'],original_description_quote=row['description'],
        normalized_seller_subject=body,price_mentions=review['price_mentions'],
        area_mentions=[m[0] for m in AREA.finditer(body)],
        source_flags=row['source_evidence_flags'],
        note='Original source quotes retained locally; normalized excerpts identify matching rules. No numbers relabelled.')
