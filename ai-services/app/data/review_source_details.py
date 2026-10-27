"""Source-container evidence and conservative decisions for the pending collection."""
import argparse
import hashlib
import json
import re
from collections import Counter, defaultdict
from difflib import SequenceMatcher
from pathlib import Path
from urllib.parse import urlparse

from lxml import html, etree
import audit_all_collected as audit
from collection_review_rules import SPECIFIC, SPECIAL, area
from smartprop_geography import norm, resolve

ROOT = audit.BASE/'processed/collection_source_review'
SOURCE = audit.BASE/'processed/collection_pipeline/runs/2026-10-11_3a4f445cb285945b'
CATEGORY_MAP = dict(SPECIFIC, **{'ban-dat':'Đất nền', 'ban-dat-nen':'Đất nền',
                               'biet thu, nha lien ke':'Nhà ở'})
SPECIAL_CODES = SPECIAL | {'ban-can-ho-mini-dich-vu', 'ban-dat-nong-lam-nghiep',
                          'ban-kho-nha-xuong', 'ban-mat-bang', 'ban-shophouse'}


def text(node):
    return ' '.join(' '.join(node.itertext()).split())


def nodes(root, name):
    return root.xpath('.//*[contains(concat(" ",normalize-space(@class)," "),$name)]', name=' '+name+' ')


def label_value(root, label):
    for li in root.iter('li'):
        labels = li.xpath('./label')
        if labels and norm(text(labels[0])) == norm(label):
            values = li.xpath('./strong')
            return text(values[0]) if values else ''
    return ''


def parse_detail(row, meta, body):
    result = dict(identity_verified=False, structure_verified=False, source_category='',
                  category='', price_raw='', area_raw='', price_million=None, area_sqm=None,
                  address_raw='', description='', sale_verified=False, flags=[])
    if meta.get('http_status') != 200 or meta.get('state') in ('blocked', 'network_error'):
        result['flags'] = [meta.get('state', 'detail_unavailable')]
        return result
    source = row['source']
    url = meta.get('response_url', '')
    if (urlparse(url).hostname != urlparse(row['detail_url']).hostname or
            audit.sid_url(source, url) != row['source_listing_id']):
        result['flags'] = ['response_identity_mismatch']
        return result
    try:
        root = html.fromstring(body.decode('utf-8', errors='replace'))
    except (etree.ParserError, ValueError):
        result['flags'] = ['invalid_source_html']
        return result
    container = root
    if source == 'cafeland':
        found = nodes(root, 'detail-property')
        if len(found) != 1:
            result['flags'] = ['detail_container_ambiguous']
            return result
        container = found[0]
        headings = container.xpath('.//h1')
    elif source == 'nhadat24h':
        headings = root.xpath('//*[@id="txtcontenttieudetin"]')
    elif source == 'alonhadat':
        articles = root.xpath('//*[self::article or self::main][contains(concat(" ",normalize-space(@class)," ")," property ")]')
        found = [a for a in articles if a.xpath('.//input[@id="hddPropertyId"]/@value') == [row['source_listing_id']]]
        if len(found) != 1:
            result['flags'] = ['detail_container_ambiguous']
            return result
        container = found[0]
        headings = container.xpath('.//h1')
    elif source == 'homedy':
        headings = root.xpath('//h1')
        if len(headings)==1:
            parents=headings[0].xpath('ancestor::*[contains(concat(" ",normalize-space(@class)," ")," product-item ")]')
            if len(parents)!=1:
                result['flags']=['detail_container_ambiguous']
                return result
            container=parents[0]
    else:
        result['flags']=['unsupported_source_parser']
        return result
    if len(headings) != 1 or SequenceMatcher(None, norm(text(headings[0])), norm(row['title'])).ratio() < .8:
        result['flags'] = ['title_identity_mismatch']
        return result
    result['identity_verified'] = True
    result['title'] = text(headings[0])
    if source == 'cafeland':
        data = {}
        for box in nodes(container, 'col-item'):
            labels, values = nodes(box, 'infor-note'), nodes(box, 'infor-data')
            if labels and values:
                data[norm(text(labels[0]))] = text(values[0])
        result.update(price_raw=data.get('gia ban',''), area_raw=data.get('dien tich',''),
                      sale_verified='gia ban' in data)
        locations = [x for x in nodes(container,'infor') if norm(text(x)).startswith('vi tri:')]
        if len(locations) == 1:
            anchors = locations[0].xpath('./a')
            result['address_raw'] = ', '.join(text(a) for a in anchors)
            categories = set()
            for a in anchors:
                match = re.search(r'/nha-dat-ban/(ban-[^/]+)-tai-', a.get('href',''))
                if match:
                    categories.add(match[1])
            if len(categories) == 1:
                result['source_category'] = categories.pop()
        description = nodes(container,'reals-description')
        result['description'] = text(description[0]) if len(description)==1 else ''
        if len(description)==1:
            blocks=nodes(description[0],'blk-content')
            if len(blocks)==1:
                result['description']=text(blocks[0])
                parts=list(blocks[0].itertext())
                first=norm(parts[0]) if parts else ''
                if (result['source_category'] and first.startswith(result['source_category'].replace('-',' ')) and
                        any(p in first for p in ('da nang','quang nam')) and len(parts)>1):
                    result['asset_description']=' '.join(' '.join(parts[1:]).split())
        products = []
        for node in root.xpath('//script[@type="application/ld+json"]'):
            try:
                value = json.loads(node.text or '{}', strict=False)
            except (ValueError, TypeError):
                continue
            if isinstance(value,dict) and value.get('@type')=='Product':
                products.append(value)
        if len(products)==1:
            offer = products[0].get('offers',{})
            if audit.sid_url(source,offer.get('url','')) != row['source_listing_id']:
                result['flags'].append('structured_identity_mismatch')
            structured = audit.number(offer.get('price'))
            if offer.get('priceCurrency')=='VND' and structured is not None:
                result['structured_price_million'] = structured/1e6
    elif source == 'nhadat24h':
        labels = root.xpath('//*[contains(@id,"lbGiaDienTich")]')
        label = norm(text(labels[0])) if len(labels)==1 else ''
        match = re.fullmatch(r'can (ban|thue)\s*:\s*(.+?)\s*-\s*(\d+(?:[.,]\d+)?\s*m[2²])', label)
        if match:
            result.update(price_raw=match[2], area_raw=match[3], sale_verified=match[1]=='ban')
        categories = root.xpath('//*[contains(@id,"lbLoaiBDS")]')
        result['source_category'] = text(categories[0]) if len(categories)==1 else ''
        descriptions = nodes(root,'sub1detailmaincontent')
        if len(descriptions)==1:
            desc = descriptions[0].xpath('./div')
            result['description'] = text(desc[0]) if desc else text(descriptions[0])
        breadcrumbs = nodes(root,'dv-breadcrumb')
        if breadcrumbs:
            result['address_raw'] = ', '.join(text(a) for a in breadcrumbs[0].iter('a') if
                                              any(k in norm(text(a)) for k in ('da nang','quang nam','quan ','huyen ')))
    elif source == 'homedy':
        result.update(price_raw=label_value(container,'Giá'), area_raw=label_value(container,'Diện tích'),
                      sale_verified=urlparse(url).path.startswith('/ban-'))
        for attribute in nodes(container,'product-attributes--item'):
            spans=attribute.xpath('./span')
            if len(spans)>=2 and norm(text(spans[0]))=='loai hinh':
                result['source_category']=text(spans[1])
        descriptions=nodes(container,'description')
        result['description']=text(descriptions[0]) if len(descriptions)==1 else ''
        parent=headings[0].getparent()
        addresses=[x for x in parent.xpath('./div') if 'address' in (x.get('class') or '').split()]
        result['address_raw']=text(addresses[0]) if len(addresses)==1 else ''
    elif source == 'alonhadat':
        boxes=nodes(container,'more-info')
        if boxes:
            prices=boxes[0].xpath('.//*[@itemprop="price"]')
            areas=boxes[0].xpath('.//*[@itemprop="floorSize"]')
            result['price_raw']=text(prices[0]) if len(prices)==1 else ''
            result['area_raw']=text(areas[0]) if len(areas)==1 else ''
        attrs={}
        tables=nodes(container,'moreinfor1')
        if tables:
            for tr in tables[0].xpath('.//tr'):
                cells=tr.xpath('./td')
                for i in range(0,len(cells)-1,2):
                    attrs[norm(text(cells[i]))]=text(cells[i+1])
        result.update(source_category=attrs.get('loai bds',''), sale_verified=norm(attrs.get('loai tin',''))=='can ban')
        descriptions=container.xpath('.//section[contains(@class,"text-content")]//*[@itemprop="description"]')
        result['description']=text(descriptions[0]) if len(descriptions)==1 else ''
        addresses=container.xpath('.//address[@itemprop="address"]')
        result['address_raw']=text(addresses[0]) if len(addresses)==1 else ''
    result['description']=re.split(r'\bChat\b|Thông tin người đăng|Xem thêm từ khóa',result['description'])[0]
    result['price_million']=audit.price(result['price_raw'])
    result['area_sqm']=area(result['area_raw'])
    src=norm(result['source_category'])
    result['category']='Khác' if src in SPECIAL_CODES else CATEGORY_MAP.get(src,'')
    result['structure_verified']=bool(result['description'] and result['source_category'] and
                                      result['price_million'] and result['area_sqm'])
    return result


def decide(row, evidence):
    flags = set(evidence['flags'])
    if not evidence['identity_verified']:
        return 'pending', '', sorted(flags | {'source_identity_not_verified'})
    src = norm(evidence['source_category'])
    title, desc = norm(row['title']), norm(evidence['description']).replace('t.y','ty')
    combined = title+' '+desc
    if evidence['category']=='Khác':
        return 'exclude', 'Khác', ['explicit_non_model_source_category']
    if (re.search(r'\b(?:ban (?:nguyen )?(?:toa (?:nha )?(?:can ho|chdv|ch)|(?:nha )?shophouse|khach san|nha nghi|nha tro|day tro)|'
                  r'toa nha \d+ tang.{0,35}\d+ phong tro)\b', title) or
            re.match(r'^\W*(?:(?:can )?ban )?(?:can ho luu tru|condotel|shophouse|nha tro|day tro|khach san|nha nghi)\b', title)):
        return 'exclude', 'Khác', ['explicit_commercial_or_whole_building_asset']
    if not evidence['structure_verified']:
        return 'pending', evidence['category'], sorted(flags | {'source_structure_incomplete'})
    if not evidence['sale_verified']:
        flags.add('current_sale_not_verified')
    if re.search(r'\b(tra truoc|tra gop|von ban dau|von tu co|dat coc|booking|gia tu|chi tu|thanh toan)\b', combined):
        flags.add('partial_or_starting_price_context')
    if re.search(r'\b(tong quan du an|dang ky thong tin|bang gia moi nhat|chinh sach ban hang|'
                 r'dat mua san pham|check can|nhan bang gia|gia tung can|tung can cu the)\b',desc):
        flags.add('project_marketing_requires_specific_asset')
    if re.search(r'\b(gio hang|quy can|bang hang|nhieu can|nhieu lo|mot so can|cac can|cac lo|'
                 r'cap dat|cap lo|hai lo|ba lo|ban (?:[2-9]|\d{2,})\s+lo|'
                 r'(?:[2-9]|\d{2,})\s+lo|(?:[2-9]|\d{2,})\s+can (?:ho|nha|cho thue))\b', combined):
        flags.add('multiple_assets_or_inventory_context')
    if ('special_or_whole_building' in row.get('pipeline_review_codes','').split(';') or
            re.search(r'\b(toa (?:nha )?can ho|day (?:nha )?tro|\d+ phong tro|condotel|shophouse|dat nong nghiep|dat vuon|'
                      r'dang kinh doanh (?:khach san|nha nghi)|'
                      r'\d+ phong (?:dang )?cho thue)\b',combined)):
        flags.add('special_or_whole_building_not_resolved')
    if re.search(r'\d+[.,]?x+\s*(?:ty|trieu)|\d+\s*(?:ty|trieu)\s*x+\b|'
                 r'\b(?:gia|chi|tam|khoang|hon)\s*\d+[.,]x+\b|'
                 r'\b(?:dien tich|dt)\s*:?\s*\d+(?:[.,]\d+)?\s*[-–]\s*\d+(?:[.,]\d+)?\s*m[2²]',combined):
        flags.add('description_price_or_area_range')
    if re.search(r'\b(dat tang nha|dat co nha|dat kem nha|tang (?:\d+ )?nha|dat va nha|nha va dat)\b', combined):
        flags.add('mixed_land_and_building_context')
    category = evidence['category']
    # Source-inserted CafeLand prefixes are metadata, not seller asset claims.
    asset_title=re.sub(r'^ban [^:]{1,35}:\s*','',title) if row['source']=='cafeland' else title
    claims=asset_title+' '+norm(evidence.get('asset_description',evidence['description']))
    land = bool(re.search(r'\b(ban dat|lo dat|dat nen|dat tho cu|dat biet thu)\b', claims)
                or re.match(r'^\W*dat\b',asset_title)
                or re.match(r'^\W*(?:ban )?lo (?:goc|dat|\d)',asset_title))
    house = bool(re.search(r'\b(ban nha|nha (?:\d+(?:[.,]\d+)?\s*tang|cap 4|c4|gac lung|me lung)|ban biet thu)\b', claims)
                 or re.match(r'^\W*(?:nha|biet thu)\b',asset_title))
    # Nearby projects or a suggestion to build apartments do not identify a unit for sale.
    apartment = bool(re.search(r'\bban (?:can ho|chung cu|studio)\b',claims) or
                     re.match(r'^\W*(?:(?:can )?ban )?(?:can ho|chung cu|studio)\b',asset_title))
    if not category and src=='nha dat tho cu':
        if land and not house and not apartment:
            category='Đất nền'
        elif house and not land and not apartment:
            category='Nhà ở'
        elif apartment and not house and not land:
            category='Căn hộ chung cư'
        else:
            flags.add('broad_source_category_unresolved')
    if not category:
        flags.add('current_category_unresolved')
    if ((category=='Nhà ở' and not house) or (category=='Đất nền' and not land) or
            (category=='Căn hộ chung cư' and not apartment)):
        flags.add('specific_category_not_supported_by_asset_claims')
    if ((category=='Nhà ở' and land) or (category=='Đất nền' and house) or
            (category=='Căn hộ chung cư' and (land or house))):
        flags.add('source_category_content_conflict')
    oldp, olda = audit.number(row['price_million']), audit.number(row['area_sqm'])
    p, a = evidence['price_million'], evidence['area_sqm']
    if oldp is None or abs(oldp-p)>.01:
        flags.add('current_price_differs_from_collected_snapshot')
    if olda is None or abs(olda-a)>.01:
        flags.add('current_area_differs_from_collected_snapshot')
    structured=evidence.get('structured_price_million')
    if structured is not None and abs(structured-p)>.01:
        flags.add('structured_and_displayed_price_conflict')
    money=audit.mentions(row['title']+' '+evidence['description'])
    totals=[m['amount_million'] for m in money if m['kind']=='total_candidate']
    if totals and any(abs(v-p)/max(v,p)>.02 for v in totals if v>0):
        flags.add('description_total_price_needs_review')
    for match in re.finditer(r'\b(?:dien tich|dt|dtsd)(?: dat| su dung| thong thuy| tim tuong| tren so| so do| thuc te| khung| toi uu| xay dung| san)?'
                             r'\s*[:=]?\s*(\d+(?:[.,]\d+)?)\s*m[2²]', desc):
        number=float(match[1].replace(',','.'))
        if abs(number-a)>.01:
            flags.add('description_area_needs_review')
    for match in re.finditer(r'\b(?:dien tich|dt)\s*[:=]?\s*\(?\s*(\d+(?:[.,]\d+)?)\s*(?:m\s*)?[x×]\s*(\d+(?:[.,]\d+)?)\s*m',desc):
        computed=float(match[1].replace(',','.'))*float(match[2].replace(',','.'))
        if abs(computed-a)/max(computed,a)>.01:
            flags.add('description_dimensions_need_review')
    olddistrict=row['district']
    district, _, _=resolve(evidence['address_raw'], source=row['source'])
    if district and olddistrict and district!=olddistrict:
        flags.add('current_location_differs_from_collected_snapshot')
    if not any(x in norm(evidence['address_raw']) for x in ('da nang', 'quang nam')):
        flags.add('current_province_not_verified')
    if row.get('review_decision')=='pending':
        flags.add('prior_pending_requires_explicit_resolution')
    if flags:
        return 'pending', category, sorted(flags)
    return ('correct' if category!=row['category'] else 'keep'), category, []


def current_manifest():
    manifest={}
    for source in audit.HOSTS:
        path=ROOT/(source+'_checkpoint.json')
        if path.exists():
            manifest.update(json.loads(path.read_text(encoding='utf-8')))
    return manifest


def description_pairs(queue, parsed):
    """Conservative candidate links, never a claim of verified physical identity."""
    groups=defaultdict(list)
    for row in queue:
        e=parsed[row['record_key']]
        description=norm(e.get('description',''))
        words=description.split()
        if (e['identity_verified'] and e['structure_verified'] and len(words)>=80 and len(set(words))>=35):
            groups[description].append(row)
    pairs=[]
    for members in groups.values():
        for i,left in enumerate(members):
            for right in members[i+1:]:
                p,pp=audit.number(left['price_million']),audit.number(right['price_million'])
                a,aa=audit.number(left['area_sqm']),audit.number(right['area_sqm'])
                if (not all((p,pp,a,aa)) or abs(p-pp)/max(p,pp)>.05 or abs(a-aa)/max(a,aa)>.01 or
                        parsed[left['record_key']]['category']!=parsed[right['record_key']]['category']):
                    continue
                pairs.append(dict(left=left['record_key'],right=right['record_key'],
                    rule='exact_long_source_description_price5pct_area1pct_candidate',
                    title_similarity=round(SequenceMatcher(None,norm(left['title']),norm(right['title']),autojunk=False).ratio(),4)))
    return pairs


def analyze(partial=False):
    frozen=ROOT/'review_manifest.json'
    if frozen.exists():
        saved=json.loads(frozen.read_text(encoding='utf-8'))
        for rel,sha in saved['output_sha256'].items():
            if hashlib.sha256((audit.BASE/rel).read_bytes()).hexdigest()!=sha:
                raise RuntimeError('Frozen source-review output changed: '+rel)
        print('Frozen source review verified; no rewriting.')
        return audit.read(ROOT/'review_decisions.csv'), json.loads((ROOT/'review_summary.json').read_text(encoding='utf-8'))
    queue=audit.read(ROOT/'queue.csv')
    meta=current_manifest()
    if not partial:
        fetch_summary=json.loads((ROOT/'fetch_summary.json').read_text(encoding='utf-8'))
        if fetch_summary.get('failures') or set(meta)!=set(r['record_key'] for r in queue):
            raise RuntimeError('Fetch run is incomplete; use --partial for provisional analysis')
        inputs=json.loads((ROOT/'input_manifest.json').read_text(encoding='utf-8'))
        source_queue=audit.BASE/inputs['queue']
        if (hashlib.sha256(source_queue.read_bytes()).hexdigest()!=inputs['queue_sha256'] or
                queue!=audit.read(source_queue)):
            raise RuntimeError('Frozen queue changed or copied rows do not match')
    evidence_path=ROOT/'parsed_evidence.json'
    parsed=json.loads(evidence_path.read_text(encoding='utf-8')) if evidence_path.exists() else {}
    decisions=[]
    parser_text=Path(__file__).read_text(encoding='utf-8')
    for row in queue:
        key=row['record_key']
        m=meta.get(key,dict(state='not_fetched',http_status=None))
        sha=m.get('sha256','')
        stamp=hashlib.sha256((parser_text+sha+
                              json.dumps(m,sort_keys=True)).encode()).hexdigest()
        if key not in parsed or parsed[key].get('parse_stamp')!=stamp:
            body=(ROOT/'detail_cache'/m['file']).read_bytes() if m.get('file') else b''
            if body and hashlib.sha256(body).hexdigest()!=sha:
                raise RuntimeError('Cache SHA mismatch: '+key)
            e=parse_detail(row,m,body)
            e.update(parse_stamp=stamp,record_key=key,detail_sha256=sha,
                     http_status=m.get('http_status'),fetch_state=m.get('state'))
            parsed[key]=e
        e=parsed[key]
        decision,category,flags=decide(row,e)
        # Keep source descriptions in the evidence cache; CSV notes contain only reasons.
        note=('Loại nguồn rõ ngoài mục tiêu nhà/đất/căn hộ thông thường.' if decision=='exclude' else
              'Đúng ID/tiêu đề, loại nguồn và giá/diện tích hiện tại phù hợp snapshot; chưa xác minh giao dịch.' if not flags else
              'Cần đối chiếu thêm: '+'; '.join(flags))
        decisions.append(dict(record_key=key,decision=decision,reviewed_category=category,
             category_evidence_validated=e['identity_verified'] and e['structure_verified'] and bool(category),
             price_million='',area_sqm='',original_price_million=row['price_million'],original_area_sqm=row['area_sqm'],
             proposed_price_million=e['price_million'],proposed_area_sqm=e['area_sqm'],
             note=note,source_url=row['detail_url'],detail_sha256=sha,
             detail_fetched_at=m.get('fetched_at_utc',''),reviewer='source_detail_rules_not_manual_verification',
             reviewed_on='2026-10-11',evidence_scope='public advertised page; not a verified transaction',
             source_category=e['source_category'],review_codes=';'.join(flags),
             source_identity_verified=e['identity_verified'],fetch_state=m.get('state','not_fetched')))
    evidence_path.write_text(json.dumps(parsed,ensure_ascii=False,indent=2),encoding='utf-8')
    audit.save_csv(ROOT/'review_decisions.csv',decisions,list(decisions[0]))
    pairs=description_pairs(queue,parsed)
    audit.save_csv(ROOT/'description_duplicate_pairs.csv',pairs,['left','right','rule','title_similarity'])
    stats=dict(queue=len(queue),download_checkpoints=len(meta),
               fetch_states=dict(Counter(m.get('state','not_fetched') for m in meta.values())),
               decisions=dict(Counter(r['decision'] for r in decisions)),
               by_source={s:dict(Counter(r['decision'] for r in decisions if r['record_key'].startswith(s+':')))
                          for s in sorted(audit.HOSTS)},
               identity_verified=sum(r['source_identity_verified'] for r in decisions),
               description_duplicate_candidate_pairs=len(pairs),
               pending_codes=dict(Counter(c for r in decisions for c in r['review_codes'].split(';') if c)),
               partial=partial,all_individual_urls_verified=False)
    (ROOT/'review_summary.json').write_text(json.dumps(stats,ensure_ascii=False,indent=2),encoding='utf-8')
    if not partial:
        protected=json.loads((ROOT/'input_manifest.json').read_text(encoding='utf-8'))['protected_sha256']
        if not all(hashlib.sha256((audit.BASE/p).read_bytes()).hexdigest()==sha for p,sha in protected.items()):
            raise RuntimeError('Protected raw/training/review input changed')
        paths=[ROOT/name for name in ('queue.csv','review_decisions.csv','review_summary.json',
               'description_duplicate_pairs.csv','parsed_evidence.json','fetch_manifest.json','input_manifest.json')]
        paths += list((ROOT/'detail_cache').glob('*.html'))
        payload=dict(complete=True,queue_records=len(queue),protected_inputs_unchanged=True,
            output_sha256={p.relative_to(audit.BASE).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
            input_sha256={Path(__file__).relative_to(audit.BASE).as_posix():hashlib.sha256(Path(__file__).read_bytes()).hexdigest()},
            protected_sha256=protected)
        frozen.write_text(json.dumps(payload,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(stats,ensure_ascii=False,indent=2))
    return decisions,stats


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--partial',action='store_true')
    analyze(parser.parse_args().partial)
