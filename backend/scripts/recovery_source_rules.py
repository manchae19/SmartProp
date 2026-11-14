"""Narrow, evidence-backed recovery adapters. No source/model/database mutation.

Existing parsers remain the default; only independently testable token/scope
mistakes are resolved. Source conflicts are never settled by majority voting.
"""
import re
from decimal import Decimal
import final_review_recovered as review

norm=review.source_rules.norm
D=review.prior.decimal

def money_mentions(text):
    """Preserve existing context policy, add missing Vietnamese shorthand safely."""
    s=norm(text).replace('t.y','ty')
    pattern=re.compile(r'(?<![\w.,])(\d+(?:[.,]\d+)?)\s*(ty|ti|trieu|tr)(?![a-z])')
    result=[]
    for m in pattern.finditer(s):
        amount=Decimal(m[1].replace(',','.'))*(1000 if m[2] in {'ty','ti'} else 1)
        end=m.end();rules=[]
        if m[2] in {'ty','ti'}:
            tail=s[end:]
            explicit=re.match(r'\s*(\d+(?:[.,]\d+)?)\s*(?:trieu|tr)\b',tail)
            shorthand=re.match(r'\s*(\d{1,3})(?![\d.,])(?=\s|[);,\-–.!]|$)',tail)
            if explicit:
                amount+=Decimal(explicit[1].replace(',','.'));end+=explicit.end()
            elif shorthand and not re.match(r'\s*(?:m[2²]?|tang|pn|phong|met|can|lo)\b',tail[shorthand.end():]):
                digits=shorthand[1]
                # A one-digit suffix is conventional (3 tỷ 5); two digits are
                # ambiguous, so require an explicit million unit for those.
                if len(digits) in {1,3}:
                    amount+=Decimal(digits)*(100 if len(digits)==1 else 1)
                    end+=shorthand.end();rules.append('VN_BILLION_MILLION_SHORTHAND')
        # An explicit remainder was already consumed; do not emit it again.
        if result and m.start()<result[-1]['end']:continue
        before=s[max(0,m.start()-45):m.start()];after=s[end:end+28]
        kind='total_candidate'
        if re.match(r'\s*/?\s*m[2²]\b',after):kind='unit_price'
        elif re.match(r'\s*(?:/\s*(?:1\s*)?|moi\s+)(?:thang|th|nam|dem)\b',after):kind='rental_income'
        elif re.search(r'(gia thue|dong tien|thu nhap|cho thue).{0,18}$',before):kind='rental_income'
        elif re.search(r'(giam|thap hon|re hon|chiet khau|qua tang|tang gia|loi nhuan).{0,18}$',before):kind='discount_or_gift'
        elif re.search(r'(tra truoc|thanh toan|von ban dau|booking|dat coc|chi tu|gia tu|chi can).{0,20}$',before):kind='partial_or_starting'
        elif re.search(r'(nhinh|chua toi|duoi|khoang|hon|tu|tam).{0,10}$',before):kind='approximate_or_bound'
        result.append(dict(amount_million=amount,kind=kind,start=m.start(),end=end,rules=rules))
    return result

def areas(text):
    pattern=r'\b(dien tich(?: su dung| xay dung| thong thuy| tim tuong| cong nhan| tren so| so do| thuc te| khung| toi uu| dat| san)?|dtsd|dt(?: su dung| thong thuy| tim tuong| tren so| so do| thuc te| khung| toi uu| dat| san| xay dung)?)\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]\b'
    found=[]
    for m in re.finditer(pattern,norm(text)):
        label=m[1]
        basis='FLOOR' if any(w in label for w in ['su dung','xay dung','san','dtsd']) else 'LAND' if any(w in label for w in [' dat','cong nhan','tren so']) else 'USABLE' if 'thong thuy' in label else 'GROSS' if 'tim tuong' in label else 'UNSPECIFIED'
        found.append(dict(basis=basis,value=Decimal(m[2].replace(',','.')),label=label))
    return found

def resolve_source(row,evidence):
    """Return a traced prepared copy; never edit row or evidence supplied by caller."""
    original=dict(row);recovered=dict(row);resolved=set();rules=[];changes=[]
    e=dict(evidence)
    description=e.get('asset_description',e.get('description',''))
    title=e.get('title',row['title']);combined=title+' '+description
    base_decision,category,base_flags=review.source_rules.decide(row,evidence)
    flags=set(base_flags)
    if base_decision=='exclude':flags.add('EXPLICIT_NON_MODEL_ASSET')
    # Strengthen, never waive, admission for a hidden down-payment advertisement.
    if re.search(r'\bchi can\s*\d',norm(combined)):flags.add('partial_or_starting_price_context')
    explicit_outside=re.search(r'\b(?:tai|toa lac|dia chi|vi tri)\b[^.!?]{0,150}\b(?:long an|tay ninh|binh dinh|hoai nhon|ha noi|ho chi minh|dong nai|nha trang)\b',norm(description))
    if explicit_outside:flags.add('EXPLICIT_ASSET_OUTSIDE_SUPPORTED_SCOPE')
    mentions=money_mentions(combined)
    totals=[m['amount_million'] for m in mentions if m['kind']=='total_candidate']
    current=D(row['price_million']);area=D(row['area_sqm'])
    if ('description_total_price_needs_review' in flags and totals and current>0
        and all(abs(p-current)/max(p,current)<=Decimal('.02') for p in totals)):
        resolved.add('description_total_price_needs_review');flags.remove('description_total_price_needs_review')
        rules.append('EXACT_VN_SHORTHAND_OR_EXPLICIT_NON_TOTAL_CONTEXT')
    values=areas(description)
    nonfloor=[v for v in values if v['basis']!='FLOOR']
    land={v['value'] for v in nonfloor if v['basis']=='LAND'}
    concrete={v['value'] for v in nonfloor if v['value']!=area}
    multiple='multiple_assets_or_inventory_context' in flags
    chosen=None;basis=None
    if not multiple and row['category'] in {'Nhà ở','Đất nền'}:
        if len(land)==1:chosen=next(iter(land));basis='LAND'
        elif len(concrete)==1 and nonfloor:chosen=next(iter(concrete));basis='SOURCE_AREA_UNSPECIFIED'
        if chosen is not None:
            consistent=all(v['value'] in {area,chosen} for v in nonfloor)
            # Only recover the quoted, more precise value when the integer card
            # is exactly its truncation. Large/semantic disagreements stay open.
            truncation=(area==area.to_integral_value() and chosen.to_integral_value(rounding='ROUND_FLOOR')==area
                and chosen>area and chosen-area<1 and (chosen-area)/area<=Decimal('.01')) if area>0 else False
            if consistent and truncation:
                recovered['area_sqm']=str(chosen);e['area_sqm']=float(chosen)
                changes.append(dict(field='area_sqm',before=str(area),after=str(chosen),basis=basis,evidence_selector='identity-verified seller description: explicit area label'))
                rules.append('EXPLICIT_PRECISE_AREA_VS_TRUNCATED_INTEGER_CARD')
            elif chosen!=area:chosen=None
    new_area=D(recovered['area_sqm'])
    if 'description_area_needs_review' in flags and nonfloor and all(v['value'] in {area,new_area} for v in nonfloor):
        # A different land value must have been explicitly recovered above.
        if all(v['value']==new_area for v in nonfloor) or changes:
            flags.remove('description_area_needs_review');resolved.add('description_area_needs_review')
            rules.append('SEPARATE_EXPLICIT_FLOOR_AREA_FROM_ASSET_AREA')
    # Unit-price arithmetic requires a rate in the BODY, a matching explicit area,
    # and no inventory/partial/project ambiguity; a title alone never suffices.
    body_mentions=money_mentions(description)
    rates={m['amount_million'] for m in body_mentions if m['kind']=='unit_price'}
    area_agrees=bool(nonfloor) and all(v['value'] in {area,new_area} for v in nonfloor)
    blockers={'multiple_assets_or_inventory_context','partial_or_starting_price_context','project_marketing_requires_specific_asset','mixed_land_and_building_context','special_or_whole_building_not_resolved','description_price_or_area_range'}
    if len(rates)==1 and area_agrees and not(flags&blockers):
        rate=next(iter(rates));derived=rate*new_area
        body_totals=[m['amount_million'] for m in body_mentions if m['kind']=='total_candidate']
        # Require a single consistent total if one is explicitly quoted.
        totals_agree=all(abs(p-derived)/max(p,derived)<=Decimal('.02') for p in body_totals) if derived>0 else False
        if current==rate and totals_agree and derived>rate:
            recovered['price_million']=str(derived);recovered['price_vnd']=str(derived*1000000)
            changes.append(dict(field='price_million',before=str(current),after=str(derived),basis='EXPLICIT_BODY_UNIT_PRICE_X_EXPLICIT_SINGLE_AREA',evidence_selector='seller description: money/m² and explicit area labels'))
            rules.append('SOURCE_EXPLICIT_UNIT_PRICE_TO_TOTAL');current=derived
        if 'structured_and_displayed_price_conflict' in flags and D(e.get('structured_price_million'))==rate and D(recovered['price_million'])==derived:
            flags.remove('structured_and_displayed_price_conflict');resolved.add('structured_and_displayed_price_conflict')
            rules.append('STRUCTURED_OFFER_IS_EXPLICIT_UNIT_PRICE_NOT_OPPOSING_TOTAL')
    # Never change a category from a vague title. Only fix a lexical false negative
    # for an explicit, same-type asset claim omitted by the old regular expression.
    claim_title=re.sub(r'^ban [^:]{1,35}:\s*','',norm(title)) if row['source']=='cafeland' else norm(title)
    claim=claim_title+' '+norm(description)
    explicit_type=(row['category']=='Nhà ở' and re.search(r'\b(?:can nha|ngoi nha|so huu nha|nha cap [1234]|nha \d+ me)\b',claim)
        or row['category']=='Căn hộ chung cư' and re.search(r'\b(?:ban lai|ban nhanh|nhuong lai)\s+(?:can ho|chung cu)\b',claim))
    if 'specific_category_not_supported_by_asset_claims' in flags and explicit_type and e.get('category')==row['category']:
        flags.remove('specific_category_not_supported_by_asset_claims');resolved.add('specific_category_not_supported_by_asset_claims')
        rules.append('EXPLICIT_ASSET_TYPE_ALIAS_WITH_SAME_SOURCE_CATEGORY')
    # Pending is only resolved after every substantive source issue is cleared AND
    # the seller body independently quotes the total and area. This is a new
    # technical resolution, not owner verification or a blanket pending waiver.
    remaining=flags-{'prior_pending_requires_explicit_resolution'}
    matching_total=any(m['kind']=='total_candidate' and abs(m['amount_million']-D(recovered['price_million']))/max(m['amount_million'],D(recovered['price_million']))<=Decimal('.02') for m in body_mentions) if D(recovered['price_million'])>0 else False
    location_text=norm(description)
    independent_location=('da nang' in location_text or norm(row['district']) in location_text)
    if not remaining and matching_total and area_agrees and e.get('sale_verified') and resolved and not independent_location:
        flags.add('SOURCE_LOCATION_CORROBORATION_MISSING')
    if not remaining and matching_total and area_agrees and e.get('sale_verified') and resolved and independent_location:
        if 'prior_pending_requires_explicit_resolution' in flags:
            flags.remove('prior_pending_requires_explicit_resolution');resolved.add('prior_pending_requires_explicit_resolution');rules.append('PENDING_TECHNICAL_RESOLUTION_WITH_EXPLICIT_BODY_PRICE_AREA')
    return dict(values=recovered,remaining_flags=sorted(flags),resolved_flags=sorted(resolved),changes=changes,rules=rules,
        area_facts=[dict(v,value=str(v['value'])) for v in values],money_facts=[dict(amount_million=str(m['amount_million']),kind=m['kind'],rules=m['rules']) for m in mentions],
        category=category,original_source_decision=base_decision,source_values=dict(price_raw=evidence.get('price_raw'),area_raw=evidence.get('area_raw'),source_category=evidence.get('source_category')))
