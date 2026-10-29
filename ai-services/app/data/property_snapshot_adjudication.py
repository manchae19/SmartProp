"""Second-pass source checks, retaining unresolved frozen review flags."""
from collections import defaultdict
import hashlib
import re

from smartprop_geography import norm

CORROBORATION = 'single_unit_price_area_not_corroborated_in_seller_description'
NUMBER = r'(?<![\w.,])(\d+(?:[.,]\d+)?)'
AREA = re.compile(NUMBER + r'\s*m[2²](?!\d)', re.I)
ROOM = re.compile(r'(?<![\w.,])(\d{1,2})\s*(?:PN\b|BR\b|phòng\s+ngủ\b)', re.I)
VND = re.compile(r'(?<![\w.,])(\d{1,3}(?:[.,]\d{3}){2,}|\d{9,12})\s*(?:VNĐ|VND|đồng)\b', re.I)


def close(a, b, tolerance=.01):
    return a is not None and b is not None and min(a, b) > 0 and abs(a-b)/max(a,b) <= tolerance


def seller_text(description):
    """Strip source echoes, retaining exact seller text and post-contact prose."""
    text = re.sub(r'^Thông tin mô tả\s*', '', description, flags=re.I)
    text = re.sub(r'^Bán căn hộ chung cư\s+.{0,160}?,\s*Đà Nẵng\s*', '', text, count=1, flags=re.I)
    return re.sub(r'(?:Xem thêm\s*)?Giá\s*:\s*[\d., ]+\s*(?:VND|VNĐ|đồng)\s+Diện tích\s*:\s*[\d., ]+\s*m[2²]\s*$', '', text, flags=re.I).strip()


def evidence(field, text, match, rule, *, value=None, status='literal'):
    return dict(source_field=field, source_quote=match[0],
                context=text[max(0,match.start()-110):match.end()+100],
                rule=rule, value=value, status=status)


def full_vnd_proofs(body):
    proofs = []
    for match in VND.finditer(body):
        before = norm(body[max(0,match.start()-95):match.start()])
        after = norm(body[match.end():match.end()+45])
        total_label = re.search(r'\bgia\s*(?:ban(?:\s+sau\s+chiet\s+khau)?|chuyen\s+nhuong|goc\s+chu\s+dau\s+tu|niem\s+yet)?\s*[:=]?\s*$', before)
        blocked = re.search(r'\b(?:thue|tra truoc|thanh toan|booking|dat coc|vay|qua tang|tu|hon|duoi|khoang)\b[^.;:]{0,45}$', before)
        blocked = blocked or re.match(r'\s*(?:/|moi\s+|mot\s+)(?:m[2²]|thang|nam|dem|ngay)', after)
        amount = int(re.sub(r'[.,]', '', match[1]))/1e6
        proofs.append(evidence('description', body, match, 'explicit_full_vnd_total', value=amount,
                               status='total_candidate' if total_label and not blocked else 'not_unconditional_total'))
    return proofs


def scan(row):
    """Return per-ID evidence and retain all flags without a proven resolution."""
    body = seller_text(row['description'])
    flags = set(row['review_codes'])
    proofs = full_vnd_proofs(body)
    area_proofs = []
    for match in AREA.finditer(body):
        before=norm(body[max(0,match.start()-90):match.start()])
        labelled=re.search(r'\b(?:dien tich(?:\s+(?:can ho|su dung|thong thuy|tim tuong|san))?|dt)\s*[:=]?\s*$',before)
        other=re.search(r'\b(?:cong vien|tang ham|khu dat|trung tam thuong mai|dien tich du an)\b[^.;]{0,60}$',before)
        area_proofs.append(evidence('description',body,match,'literal_area',value=float(match[1].replace(',','.')),
                                   status='property_area_candidate' if labelled and not other else 'unscoped_area'))
    proofs += area_proofs
    resolved = []
    totals = [p['value'] for p in proofs if p['status']=='total_candidate']
    # Only add evidence for a format the frozen money matcher misses. Any
    # other flags, including numeric conflicts and source age, remain intact.
    if (CORROBORATION in flags and totals and all(close(p,row['price_million']) for p in totals)
            and any(p['status']=='property_area_candidate' and close(p['value'],row['area_sqm']) for p in area_proofs)):
        flags.remove(CORROBORATION)
        resolved.append(dict(code=CORROBORATION, rule='full_vnd_total_and_literal_area_match_same_response'))
    normalized = norm(body)
    new_flags = set()
    exclusions = list(row['exclusion_codes'])
    if 'whole_building_not_single_apartment' in exclusions:
        # An opening "Tòa căn hộ ..." can introduce a project followed by a
        # specific unit. It does not, by itself, say the whole building is sold.
        whole_sale=re.search(r'\b(?:ban|chuyen nhuong)\s+(?:(?:nguyen|ca)\s+)?toa\s+(?:nha|can ho)\b',norm(row['title'])+' '+normalized)
        if not whole_sale:
            exclusions.remove('whole_building_not_single_apartment')
            new_flags.add('whole_building_scope_not_resolved')
            resolved.append(dict(code='whole_building_not_single_apartment',
                rule='heading_only_is_not_whole_building_sale_proof; demoted_to_review_not_accepted'))
    inventory = re.compile(r'\b(?:(?:mo ban|ban|tong hop|chuyen nhuong)\s+(?:gio hang|quy can|[2-9]\d*\s+can\b)|(?:ngoai ra toi con|toi con|hien co)\s+gio hang)\b')
    for match in inventory.finditer(normalized):
        before=normalized[max(0,match.start()-30):match.start()]
        if re.search(r'\b(?:khong|chua)\b[^.;]{0,20}$',before):continue
        exclusions.append('explicit_multi_asset_offer')
        new_flags.add('multiple_units_in_full_seller_text')
        # Normalized excerpts are separately labelled; the full exact prose
        # remains in all_decisions and has the original response SHA.
        proofs.append(evidence('normalized_seller_text',normalized,match,'explicit_multi_asset_offer'))
    future = re.search(r'\b(?:chua nhan nha|sap ban giao|du kien\s+(?:quy|thang)|dang thi cong|dang xay)\b',normalized)
    if future:
        new_flags.add('handover_or_construction_status_needs_review')
        proofs.append(evidence('normalized_seller_text',normalized,future,'handover_or_construction_not_confirmed'))
    room_values = set()
    for field,text in [('title',row['title']),('description',body)]:
        for match in ROOM.finditer(text):
            before = norm(text[max(0,match.start()-60):match.start()])
            hypothetical = bool(re.search(r'\b(?:co the|cai tao|chuyen thanh|du kien)\b[^.;]{0,45}$',before))
            proofs.append(evidence(field,text,match,'bedroom_literal',value=int(match[1]),
                                   status='hypothetical' if hypothetical else 'current_claim'))
            if not hypothetical:room_values.add(int(match[1]))
    if row.get('rooms') is not None:room_values.add(row['rooms'])
    if len(room_values)>1:new_flags.add('bedroom_pn_br_header_conflict')
    # A unit price in the title is not the total-price target; disagreement
    # remains a review reason (possibly different area definitions).
    title = norm(row['title'])
    for match in re.finditer(NUMBER+r'\s*(?:trieu|tr)\s*/\s*m[2²]',title):
        unit = float(match[1].replace(',','.'))
        if row['price_million'] and row['area_sqm'] and not close(unit,row['price_million']/row['area_sqm']):
            new_flags.add('title_unit_price_disagrees_with_total_area')
            proofs.append(evidence('normalized_title',title,match,'unit_price_requires_area_basis',value=unit))
    return dict(row, seller_text=body, remaining_codes=sorted(flags|new_flags),
                added_codes_v2=sorted(new_flags), resolved_codes_v2=resolved,
                exclusions_v2=sorted(set(exclusions)), source_proofs=proofs,
                source_decision='exclude_single_apartment_dataset' if exclusions else
                    'needs_evidence' if flags|new_flags else 'source_candidate')


def explicit_unit_links(rows):
    """Add only literal complete project+unit-code matches; never unlink."""
    buckets=defaultdict(list)
    for row in rows:
        text=norm(seller_text(row['description']))
        # Versioned, explicit project pattern for this source review. Names
        # elsewhere (sidebar/title) never establish unit identity.
        project=re.search(r'\bthe meridian\b',text)
        if not project:continue
        for match in re.finditer(r'\b(?:ma can\s*:\s*|can\s+)([a-z]\d+-\d{2}-\d{2})\b',text):
            buckets[('the meridian',match[1])].append((row,match[0]))
    links=[]
    for (project,unit),members in sorted(buckets.items()):
        unique={r['record_key']:(r,quote) for r,quote in members}
        values=[unique[k] for k in sorted(unique)]
        for i,(left,lquote) in enumerate(values):
            for right,rquote in values[i+1:]:
                if close(left['area_sqm'],right['area_sqm']):
                    links.append(dict(left=left['record_key'],right=right['record_key'],
                        rule='same_explicit_project_complete_unit_code_area',project=project,unit_code=unit,
                        left_quote=lquote,right_quote=rquote,title_similarity=1))
    return links


def component_members(keys, links):
    """Recover complete archived components, including non-current bridges."""
    parent={key:key for key in keys}
    def find(key):
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    for link in links:
        left,right=link['left'],link['right']
        if left not in parent or right not in parent:raise ValueError('Unknown graph endpoint')
        parent[find(right)]=find(left)
    groups=defaultdict(set)
    for key in parent:groups[find(key)].add(key)
    return {'property_candidate:'+hashlib.sha256('|'.join(sorted(values)).encode()).hexdigest()[:20]:values
            for values in groups.values()}


def adjudicate_groups(rows, extra_links, train_keys, historical_keys, historical_groups=()):
    """Preserve complete existing components, union additions, quarantine bridges."""
    parent={r['overlay_group']:r['overlay_group'] for r in rows}
    bykey={r['record_key']:r for r in rows}
    if len(bykey)!=len(rows):raise ValueError('Repeated snapshot ID')
    def find(key):
        while parent[key]!=key:
            parent[key]=parent[parent[key]];key=parent[key]
        return key
    for link in extra_links:
        a,b=(bykey[link[k]]['overlay_group'] for k in ['left','right'])
        parent[find(b)]=find(a)
    components=defaultdict(list)
    for row in rows:components[find(row['overlay_group'])].append(row)
    result=[]
    for members in components.values():
        originals=sorted({r['overlay_group'] for r in members})
        gid=originals[0] if len(originals)==1 else 'adjudicated:'+hashlib.sha256('|'.join(originals).encode()).hexdigest()[:20]
        issues=set()
        # All non-source baseline group reasons remain effective, even if a
        # protected/historical bridge is outside the current 234 snapshots.
        for r in members:
            issues.update(c for c in r['group_review_codes'] if c!='current_group_contains_unresolved_member')
        if any(r['source_decision']!='source_candidate' for r in members):issues.add('group_has_unresolved_or_excluded_member')
        for field,tolerance in [('price_million',.05),('area_sqm',.01)]:
            v=[r[field] for r in members if r[field] is not None]
            if v and not close(min(v),max(v),tolerance):issues.add('current_group_'+field+'_conflict')
        if len({r['location_feature'] for r in members})>1:issues.add('current_group_location_conflict')
        representative=min((r['record_key'] for r in members if r['record_key'] in train_keys),
                           default=min(r['record_key'] for r in members))
        has_history=any(r['record_key'] in historical_keys or r['overlay_group'] in historical_groups for r in members)
        # An apparently fresh row previously classified as linked historical
        # cannot become a fresh evaluation group through this second pass.
        if any(r['candidate_role']=='linked_historical_group_candidate' for r in members):has_history=True
        for row in members:
            role='excluded' if row['exclusions_v2'] else 'quarantine' if issues else (
                'suppressed_duplicate' if row['record_key']!=representative else
                'train_refresh_candidate' if row['record_key'] in train_keys else
                'historical_linked_candidate' if has_history else 'fresh_evaluation_reserved')
            result.append(dict(row, adjudicated_group=gid, representative_key=representative,
                group_codes_v2=sorted(issues), dataset_role=role, training_allowed=False))
    return sorted(result,key=lambda r:r['record_key'])
