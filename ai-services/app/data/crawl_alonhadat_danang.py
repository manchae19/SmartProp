"""SmartProp: resumable public HTML crawler; requires lxml.
Default research scope: the seven historical Da Nang districts in existing data.
No cookies/login/challenge bypass. No seller contacts or description collection.
"""
from pathlib import Path
from datetime import datetime, timezone, date
from urllib.request import Request, urlopen
from urllib.error import HTTPError
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser
import argparse
import csv
import json
import math
import re
import time
import unicodedata
from lxml import html

BASE = 'https://alonhadat.com.vn'
LISTING = BASE + '/can-ban-nha-dat/da-nang'
UA = 'SmartPropResearch/0.1'
DISTRICTS = {'quan hai chau', 'quan thanh khe', 'quan son tra', 'quan ngu hanh son',
             'quan lien chieu', 'quan cam le', 'huyen hoa vang'}
FIELDS = ['list_id', 'source', 'source_listing_id', 'source_url', 'title', 'category',
          'source_category', 'price_raw', 'price_million', 'area_raw', 'area_sqm',
          'address_raw', 'district', 'ward', 'street', 'latitude', 'longitude',
          'rooms', 'toilets', 'image_url', 'detail_url', 'collected_at', 'listing_page',
          'detail_fetched', 'detail_price_raw', 'legal_status', 'direction',
          'price_needs_review', 'area_needs_review', 'region_needs_review',
          'description_mentions_billion', 'detail_error', 'city', 'address_old',
          'ward_old', 'posted_at', 'posted_at_raw', 'posted_at_semantics',
          'date_needs_review', 'category_needs_review', 'location_status',
          'price_structured_vnd', 'price_unit_review', 'transaction_type']


def clean(value):
    return ' '.join(str(value or '').split())


def norm(value):
    s = unicodedata.normalize('NFD', clean(value).lower())
    return ''.join(c for c in s if unicodedata.category(c) != 'Mn').replace('đ', 'd')


def nodes(root, cls):
    return root.xpath('.//*[contains(concat(" ",normalize-space(@class)," ")," ' + cls + ' ")]')


def text(root, cls):
    found = nodes(root, cls)
    return clean(found[0].text_content()) if found else ''


def prop(root, name):
    found = root.xpath('.//*[@itemprop=$name]', name=name)
    return found[0] if found else None


def ptext(root, name):
    node = prop(root, name)
    return clean(node.text_content()) if node is not None else ''


def number(raw):
    s = clean(raw)
    if not re.fullmatch(r'\d+(?:[.,]\d+)?', s):
        return None
    result = float(s.replace(',', '.'))
    return result if math.isfinite(result) else None


def parse_price(raw):
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*(ty|trieu|nghin|ngan|dong|vnd)', norm(raw))
    return number(m[1]) * {'ty': 1000, 'trieu': 1, 'nghin': .001,
                          'ngan': .001, 'dong': .000001, 'vnd': .000001}[m[2]] if m else None


def parse_area(raw):
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m(?:2|²)', clean(raw), re.I)
    return number(m[1]) if m else None


def read_price_area(root, record):
    pn = prop(root, 'price')
    record['price_raw'] = clean(pn.text_content()) if pn is not None else ''
    raw_vnd = (pn.get('content') or pn.get('value') or '') if pn is not None else ''
    record['price_structured_vnd'] = raw_vnd
    # Always parse the displayed total price; unit prices are never treated as totals.
    record['price_million'] = parse_price(record['price_raw'])
    record['price_unit_review'] = bool(re.search(r'/|m2|m²', norm(record['price_raw'])))
    an = prop(root, 'floorSize')
    if an is not None:
        val = ptext(an, 'value')
        record['area_raw'] = val + ' m²' if val else clean(an.text_content())
        record['area_sqm'] = number(val) if val else parse_area(record['area_raw'])
    else:
        record['area_raw'], record['area_sqm'] = '', None


def read_address(root, record):
    an = prop(root, 'address')
    record['address_raw'] = clean(an.text_content()) if an is not None else ''
    record['city'] = ptext(an, 'addressRegion') if an is not None else ''
    record['ward'] = ptext(an, 'addressLocality') if an is not None else ''
    record['street'] = ptext(an, 'streetAddress') if an is not None else ''
    old = re.sub(r'\s*\((?:cũ|địa chỉ cũ)\)\s*$', '', text(root, 'old-address'), flags=re.I)
    record['address_old'] = old
    record['district'], record['ward_old'] = '', ''
    for part in old.split(','):
        part = clean(part).strip(' -.')
        if re.match(r'^(Quận|Huyện)\s+', part, re.I):
            record['district'] = part
        elif re.match(r'^(Phường|Xã)\s+', part, re.I):
            record['ward_old'] = part


def scope(record):
    if norm(record.get('city')) not in {'da nang', 'tp. da nang', 'tp da nang', 'thanh pho da nang'}:
        return 'outside_city' if record.get('city') else 'unknown_location'
    old = record.get('address_old', '')
    if old and norm(old.split(',')[-1]).strip(' .') != 'da nang':
        return 'conflicting_address'
    district = norm(record.get('district'))
    if not district:
        return 'unknown_location'
    return 'in_scope' if district in DISTRICTS else 'outside_district'


def read_date(root, record):
    times = root.xpath('.//time[@itemprop="datePosted"]')
    raw = times[0].get('datetime', '') if times else ''
    record['posted_at_raw'] = raw
    record['posted_at_semantics'] = 'site_datePosted; may reflect repost/update'
    try:
        record['posted_at'] = date.fromisoformat(raw).isoformat()
    except ValueError:
        record['posted_at'] = ''


def category(raw):
    s = norm(raw)
    if s in {'nha mat tien', 'nha trong hem', 'nha biet thu', 'biet thu', 'nha rieng'}:
        return 'Nhà ở'
    if s in {'can ho chung cu', 'can ho', 'chung cu'}:
        return 'Căn hộ chung cư'
    if s in {'dat tho cu', 'dat nen', 'dat nen du an', 'dat o'}:
        return 'Đất nền'
    if s in {'van phong', 'mat bang', 'mat bang kinh doanh', 'cua hang', 'kho xuong', 'nha xuong'}:
        return 'Mặt bằng / Văn phòng'
    return 'Chưa xác định'


def quality(record):
    price, area = record.get('price_million'), record.get('area_sqm')
    structured = number(record.get('price_structured_vnd'))
    record['price_needs_review'] = (price is None or price < 100 or record['price_unit_review']
        or (structured is not None and price is not None and abs(structured / 1e6 - price) > .01)
        or (price is not None and area is not None and area > 0 and not 2 <= price / area <= 300))
    record['area_needs_review'] = area is None or not 20 <= area <= 1000
    record['location_status'] = scope(record)
    record['region_needs_review'] = record['location_status'] != 'in_scope'
    record['category_needs_review'] = record['category'] == 'Chưa xác định'
    posted = record.get('posted_at', '')
    record['date_needs_review'] = not posted or date.fromisoformat(posted) > datetime.now(timezone.utc).date()


def listings(body, page_url):
    doc = html.fromstring(body)
    headings = doc.xpath('//h1')
    if not headings or 'da nang' not in norm(headings[0].text_content()):
        raise ValueError('Listing h1 missing Da Nang; stop')
    # Restrict to listing box: ignore advertisements/recommendations elsewhere.
    boxes = nodes(doc, 'list-property-box')
    if not boxes:
        raise ValueError('Listing container changed; stop')
    cards = nodes(boxes[0], 'property-item')
    records = []
    for card in cards:
        anchors = card.xpath('./a[@itemprop="url"]')
        if not anchors:
            raise ValueError('Card URL missing; selector changed')
        url = urljoin(BASE, anchors[0].get('href', ''))
        mid = re.search(r'-(\d+)\.html$', urlparse(url).path)
        if urlparse(url).hostname != 'alonhadat.com.vn' or not mid:
            raise ValueError('Unexpected card URL')
        r = dict.fromkeys(FIELDS, '')
        r.update(list_id='alonhadat:' + mid[1], source='alonhadat', source_listing_id=mid[1],
                 source_url=url, detail_url=url, title=text(card, 'property-title'),
                 category='Chưa xác định', transaction_type='Cần bán',
                 collected_at=datetime.now(timezone.utc).isoformat(), listing_page=page_url,
                 detail_fetched=False)
        read_price_area(card, r); read_address(card, r); read_date(card, r)
        bedroom = prop(card, 'numberOfBedrooms')
        r['rooms'] = number(ptext(bedroom, 'value')) if bedroom is not None else None
        r['toilets'] = None
        imgs = card.xpath('.//img[@itemprop="image"]')
        r['image_url'] = urljoin(BASE, imgs[0].get('src', '')) if imgs else ''
        quality(r); records.append(r)
    next_links = doc.xpath('//a[@href]/@href')
    current = re.search(r'/trang-(\d+)$', urlparse(page_url).path)
    page = int(current[1]) if current else 1
    expected = LISTING + f'/trang-{page + 1}'
    next_url = expected if any(urljoin(BASE, u).rstrip('/') == expected for u in next_links) else None
    return records, next_url


def enrich(record, body):
    doc = html.fromstring(body)
    articles = doc.xpath('//*[self::article or self::main][contains(concat(" ",normalize-space(@class)," ")," property ")]')
    if len(articles) != 1:
        raise ValueError('Main detail container missing or ambiguous')
    root = articles[0]
    identity = root.xpath('.//input[@id="hddPropertyId"]/@value')
    if identity != [record['source_listing_id']]:
        raise ValueError('Detail ID does not match request')
    h1 = root.xpath('.//h1')
    if not h1:
        raise ValueError('Detail title missing')
    old_price = record.get('price_million')
    record['title'] = clean(h1[0].text_content())
    info = nodes(root, 'more-info')
    if not info:
        raise ValueError('Detail price/area block missing')
    read_price_area(info[0], record)
    record['detail_price_raw'] = record['price_raw']
    read_address(root, record); read_date(root, record)
    tables = nodes(root, 'moreinfor1')
    attrs = {}
    if tables:
        for row in tables[0].xpath('.//tr'):
            cells = row.xpath('./td')
            for i in range(0, len(cells) - 1, 2):
                attrs[norm(cells[i].text_content())] = clean(cells[i+1].text_content())
    record['source_category'] = attrs.get('loai bds', '')
    record['category'] = category(record['source_category'])
    record['transaction_type'] = attrs.get('loai tin', '')
    record['rooms'] = number(attrs.get('so phong ngu', attrs.get('phong ngu', '')))
    record['toilets'] = number(attrs.get('so toilet', attrs.get('so phong tam', '')))
    record['direction'] = attrs.get('huong', '')
    record['legal_status'] = attrs.get('phap ly', '')
    imgs = root.xpath('.//img[@id="limage"]/@src')
    if not imgs:
        image_sections = nodes(root, 'images')
        imgs = image_sections[0].xpath('.//img/@src') if image_sections else []
    if imgs:
        record['image_url'] = urljoin(BASE, imgs[0])
    record['detail_fetched'] = True
    quality(record)
    if old_price is not None and record['price_million'] is not None and abs(old_price - record['price_million']) > .01:
        record['price_needs_review'] = True
    return record


class Stop(RuntimeError):
    pass


class Client:
    def __init__(self, delay):
        self.delay, self.last, self.robot = delay, 0, None

    def get(self, url, robots=True):
        if urlparse(url).hostname != 'alonhadat.com.vn' or urlparse(url).scheme != 'https':
            raise Stop('Refusing off-site URL')
        if robots and (self.robot is None or not self.robot.can_fetch(UA, url)):
            raise Stop('robots.txt does not allow this URL')
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        # robots.txt is plain text; avoid restricting every request to HTML.
        headers = {'User-Agent': UA, 'Accept': '*/*'}
        print(f'[GET] {url}', flush=True)
        try:
            with urlopen(Request(url, headers=headers), timeout=30) as res:
                if urlparse(res.url).hostname != 'alonhadat.com.vn' or urlparse(res.url).path.rstrip('/') != urlparse(url).path.rstrip('/'):
                    raise Stop('Unexpected redirect; stop')
                body = res.read().decode('utf-8', errors='replace')
        except HTTPError as exc:
            raise Stop(
                f'HTTP {exc.code} at {url}; stop, no automatic retry. '
                f'Retry-After={exc.headers.get("Retry-After")}. '
                '406 may mean unacceptable request headers or server rejection; '
                'it does not establish the cause by itself.'
            ) from exc
        lowered = body.lower()
        if any(s in lowered for s in ('cf-chl-', 'just a moment', 'verify you are human')):
            raise Stop('Challenge page; stop')
        return body

    def load_robots(self):
        body = self.get(BASE + '/robots.txt', robots=False)
        if 'user-agent:' not in body.lower():
            raise Stop('Unrecognized robots.txt; stop')
        self.robot = RobotFileParser(BASE + '/robots.txt')
        self.robot.parse(body.replace('\\r\\n', '\n').splitlines())
        self.delay = max(self.delay, self.robot.crawl_delay(UA) or 0)


def atomic_write(path, content):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(content, encoding='utf-8')
    replace_retry(tmp, path)


def replace_retry(tmp, path):
    for attempt in range(10):
        try:
            tmp.replace(path); return
        except PermissionError:
            if attempt == 9:
                raise PermissionError(f'Close Excel/CSV preview. New data retained at {tmp}')
            print('CSV locked; retry in 3 seconds', flush=True); time.sleep(3)


def save(records, path):
    tmp = path.with_suffix('.tmp')
    with tmp.open('w', encoding='utf-8-sig', newline='') as f:
        w = csv.DictWriter(f, fieldnames=FIELDS); w.writeheader(); w.writerows(records)
    replace_retry(tmp, path)


def load(path):
    if not path.exists():
        return []
    with path.open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        if reader.fieldnames != FIELDS:
            raise ValueError('Existing schema differs; use another output directory')
        rows = list(reader)
    if len({r['list_id'] for r in rows}) != len(rows):
        raise ValueError('Duplicate IDs in existing CSV')
    return rows


def property_filter(record):
    """Use source property type, never infer type from sale-title keywords."""
    raw = norm(record.get('source_category'))
    if record.get('category') == 'Đất nền' or re.match(r'^(?:cac loai )?dat\b', raw):
        return 'land'
    if record.get('category') in {'Nhà ở', 'Căn hộ chung cư', 'Mặt bằng / Văn phòng'}:
        return 'keep'
    if re.match(r'^(nha\b|can ho\b|chung cu\b|biet thu\b|van phong\b|mat bang\b|kho\b|cua hang\b|khach san\b)', raw):
        return 'keep'
    return 'unknown'


def crawl(args, client=None):
    args.output_dir.mkdir(parents=True, exist_ok=True)
    out = args.output_dir / 'alonhadat_records.csv'
    quarantine = args.output_dir / 'alonhadat_rejected.csv'
    land_path = args.output_dir / 'alonhadat_land_excluded.csv'
    type_review_path = args.output_dir / 'alonhadat_type_review.csv'
    cp = args.output_dir / 'alonhadat_checkpoint.json'
    accepted, rejected = load(out), load(quarantine)
    land, type_review = load(land_path), load(type_review_path)
    exclude_land = getattr(args, 'exclude_land', False)
    if exclude_land and not args.details:
        raise ValueError('--exclude-land requires --details to verify source property type')
    if any(scope(r) != 'in_scope' for r in accepted):
        raise ValueError('Existing accepted CSV contains out-of-scope records')
    state = json.loads(cp.read_text(encoding='utf-8')) if cp.exists() else {}
    if state and (state.get('listing') != LISTING or state.get('details') != args.details):
        raise ValueError('Checkpoint settings differ; use another output directory')
    # Enable the new filter on an older checkpoint without recrawling saved IDs.
    # Save excluded records first, then replace the accepted CSV; no rows are lost.
    if exclude_land:
        retained = []
        known_land = {r['list_id'] for r in land}
        known_review = {r['list_id'] for r in type_review}
        for record in accepted:
            status = property_filter(record)
            if status == 'keep':
                retained.append(record)
            elif status == 'land' and record['list_id'] not in known_land:
                land.append(record); known_land.add(record['list_id'])
            elif status == 'unknown' and record['list_id'] not in known_review:
                type_review.append(record); known_review.add(record['list_id'])
        if len(retained) != len(accepted):
            if land:
                save(land, land_path)
            if type_review:
                save(type_review, type_review_path)
            save(retained, out)
            print(f'Existing CSV filtered: retained={len(retained)}, land={len(land)}, type_review={len(type_review)}', flush=True)
        accepted = retained
    seen = {r['list_id'] for r in accepted + rejected + land + type_review}
    if state.get('finished') and args.start_page is None:
        print('Previous run reached end/scope stop. Use --start-page 1 to rescan.'); return
    page = args.start_page or state.get('next_page', 1)
    client = client or Client(args.delay)
    client.load_robots()
    signatures, new_count = set(), 0
    for _ in range(args.pages):
        url = LISTING + (f'/trang-{page}' if page > 1 else '')
        records, next_url = listings(client.get(url), url)
        signature = frozenset(r['list_id'] for r in records)
        if not records or signature in signatures:
            atomic_write(cp, json.dumps({'listing': LISTING, 'details': args.details,
                'next_page': page, 'finished': True, 'reason': 'empty_or_repeated_page'}))
            print('Empty/repeated page; stopped'); break
        signatures.add(signature)
        in_scope_count = sum(scope(r) == 'in_scope' for r in records)
        added, complete = 0, True
        for r in records:
            if r['list_id'] in seen:
                continue
            if new_count >= args.max_new:
                complete = False; break
            if scope(r) == 'in_scope' and args.details:
                # Any detail/network failure stops here; same page is retried on resume.
                # The current record is not marked seen until it has been saved.
                detail_body = client.get(r['detail_url'])
                try:
                    enrich(r, detail_body)
                except ValueError as exc:
                    # Preserve the actual response for selector/block-page diagnosis.
                    # Do not mark this ID as processed or accept partial detail data.
                    debug_dir = args.output_dir / 'debug'
                    debug_dir.mkdir(parents=True, exist_ok=True)
                    debug_path = debug_dir / f'detail_{r["source_listing_id"]}_unexpected.html'
                    debug_path.write_text(detail_body, encoding='utf-8')
                    raise Stop(
                        f'{exc} at {r["detail_url"]}. '
                        f'Actual response saved to {debug_path}. '
                        'This ID is not marked processed. Inspect/upload this HTML '
                        'before changing selectors or retrying.'
                    ) from exc
            if scope(r) != 'in_scope' or norm(r['transaction_type']) != 'can ban':
                if scope(r) == 'in_scope':
                    r['location_status'] = 'wrong_transaction'
                rejected.append(r); save(rejected, quarantine)
            elif exclude_land and property_filter(r) == 'land':
                land.append(r); save(land, land_path)
            elif exclude_land and property_filter(r) == 'unknown':
                type_review.append(r); save(type_review, type_review_path)
            else:
                accepted.append(r); save(accepted, out)
                added += 1; new_count += 1
            seen.add(r['list_id'])
        finished = complete and (not next_url or in_scope_count == 0)
        atomic_write(cp, json.dumps({'listing': LISTING, 'details': args.details,
            'next_page': page + 1 if complete and not finished else page,
            'finished': finished, 'reason': 'end_or_no_in_scope_cards' if finished else ''}))
        print(f'Page {page}: cards={len(records)}, in_scope={in_scope_count}, new={added}, '
              f'run_new={new_count}, total={len(accepted)}, rejected={len(rejected)}, '
              f'land_excluded={len(land)}, type_review={len(type_review)}', flush=True)
        if new_count >= args.max_new or finished:
            break
        page += 1
    print(f'Accepted CSV: {out}; these are raw listings, not final training records', flush=True)


def offline(args):
    rows, _ = listings(args.offline_listing.read_bytes(), LISTING)
    if args.offline_detail:
        doc = html.fromstring(args.offline_detail.read_bytes())
        ids = doc.xpath('//input[@id="hddPropertyId"]/@value')
        matches = [r for r in rows if ids == [r['source_listing_id']]]
        if len(matches) != 1:
            raise ValueError('Offline detail ID must match exactly one listing card')
        enrich(matches[0], args.offline_detail.read_bytes())
    args.output_dir.mkdir(parents=True, exist_ok=True)
    save(rows, args.output_dir / 'alonhadat_offline_sample.csv')
    print(f'Offline cards={len(rows)}, in_scope={sum(scope(r)=="in_scope" for r in rows)}')
    if args.offline_detail:
        r = matches[0]
        print({k:r[k] for k in ['list_id','price_million','area_sqm','rooms','category','district','posted_at','location_status']})
    print('Offline sample only; no crawler checkpoint created')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='SmartProp Alonhadat Da Nang research crawler')
    p.add_argument('--pages', type=int, default=3)
    p.add_argument('--max-new', type=int, default=50, help='New in-scope raw records in this run')
    p.add_argument('--start-page', type=int)
    p.add_argument('--details', action='store_true')
    p.add_argument('--exclude-land', action='store_true', help='Exclude land; requires --details. Unclear property types are kept separately for review.')
    p.add_argument('--delay', type=float, default=3)
    p.add_argument('--output-dir', type=Path, default=Path(__file__).resolve().parent/'data_raw'/'alonhadat')
    p.add_argument('--offline-listing', type=Path)
    p.add_argument('--offline-detail', type=Path)
    a = p.parse_args()
    if a.pages < 1 or a.max_new < 1 or a.delay < 2 or (a.start_page is not None and a.start_page < 1):
        p.error('pages/max-new/start-page must be positive; delay >= 2 seconds')
    if a.offline_detail and not a.offline_listing:
        p.error('--offline-detail requires --offline-listing')
    try:
        offline(a) if a.offline_listing else crawl(a)
    except KeyboardInterrupt:
        p.exit(130, 'Stopped by user; completed records retained. Rerun the same command.\n')
    except Exception as exc:
        p.exit(1, f'Stopped: {exc}\nCompleted CSV records retained; rerun resumes without duplicate IDs.\n')
