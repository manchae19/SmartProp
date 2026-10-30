"""Public listing-card crawler. Raw data only; no login or block bypass.
Requires lxml. Historical seven-district Da Nang scope; CSV/checkpoint resume.
"""
import argparse
import csv
import json
import re
import time
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen
from urllib.robotparser import RobotFileParser
from lxml import html

BASE = 'https://nhadat24h.net'
LIST = BASE + '/nha-dat-da-nang'
UA = 'SmartPropResearch/0.1'
DISTRICTS = {'quan hai chau', 'quan thanh khe', 'quan son tra', 'quan ngu hanh son',
             'quan lien chieu', 'quan cam le', 'huyen hoa vang'}
FIELDS = ['list_id','source','source_listing_id','detail_url','title','source_category',
          'category','category_needs_review','transaction_type','price_raw','price_million',
          'area_raw','area_sqm','address_raw','district','ward','rooms','toilets',
          'latitude','longitude','image_url','posted_at','posted_at_raw','posted_at_semantics',
          'collected_at','listing_page','detail_fetched','location_status',
          'price_needs_review','area_needs_review']

def clean(s):
    return ' '.join((s or '').split())

def norm(s):
    return ''.join(c for c in unicodedata.normalize('NFD',clean(s).lower())
                   if unicodedata.category(c) != 'Mn').replace('đ','d')

def texts(node, cls):
    return [clean(x.text_content()) for x in node.xpath(
        './/*[contains(concat(" ",normalize-space(@class)," "),$c)]',c=' '+cls+' ')]

def value(node, cls):
    return next(iter(texts(node, cls)), '')

def numeric(raw, unit):
    m = re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*('+unit+r')',norm(raw))
    return (float(m[1].replace(',','.')), m[2]) if m else (None,None)

def parse(body, url):
    doc = html.fromstring(body)
    if not any('da nang' in norm(x.text_content()) for x in doc.xpath('//h1')):
        raise ValueError('Page heading no longer identifies Da Nang')
    boxes = doc.xpath('//*[@id="divlistitemketquatimkiem_2"]')
    if len(boxes) != 1:
        raise ValueError('Listing container missing/changed')
    cards = boxes[0].xpath('./div[starts-with(@id,"descrip_")]')
    if not cards:
        raise ValueError('No expected cards; stop rather than infer end of listings')
    rows = []
    for card in cards:
        anchors = card.xpath('./a[contains(concat(" ",normalize-space(@class)," ")," a-title ")]')
        if len(anchors) != 1:
            raise ValueError('Card title URL changed')
        a = anchors[0]; detail = urljoin(BASE,a.get('href'))
        ident = re.search(r'-ID(\d+)$',urlparse(detail).path)
        if not ident or card.get('id') != 'descrip_'+ident[1] or urlparse(detail).hostname != 'nhadat24h.net':
            raise ValueError('Card identity mismatch')
        r = dict.fromkeys(FIELDS, '')
        address = value(card,'rvVitri'); parts = [clean(p) for p in address.split(',')]
        district = next((p for p in parts if norm(p) in DISTRICTS),'')
        title = clean(a.get('title'))
        src_category = next(iter(texts(card,'ex3')),'')
        s = norm(src_category)
        category = ('Nhà ở' if s in {'nha mat pho','nha trong ngo','biet thu','nha rieng'}
                    else 'Chưa xác định' if s == 'nha dat tho cu'
                    else 'Đất nền' if 'dat' in s
                    else 'Căn hộ chung cư' if 'can ho' in s or 'chung cu' in s
                    else 'Chưa xác định')
        pn, pu = numeric(value(card,'a-txt-cl1'),'ty|trieu')
        price = pn * (1000 if pu == 'ty' else 1) if pn is not None else None
        area, _ = numeric(value(card,'a-txt-cl2'),'m²|m2')
        labels = [clean(x.text_content()) for x in card.xpath('.//div[@class="reviewproperty1"]/label')]
        def count(pattern):
            matches = [re.search(pattern,norm(t)) for t in labels]
            return next((int(m[1]) for m in matches if m),'')
        img = card.xpath('.//img[contains(@class,"imageThumb1")]/@data-src')
        in_scope = bool(district) and card.get('data-tinhthanh') == '28'
        selling = urlparse(detail).path.startswith('/ban-') and card.get('data-loaitin') == '1'
        category_review = category == 'Chưa xác định' or (category == 'Nhà ở' and
            bool(re.search(r'\b(dat|lo dat|toa can ho|khach san|homestay)\b',norm(title))))
        r.update(list_id='nhadat24h:'+ident[1],source='nhadat24h',source_listing_id=ident[1],
                 detail_url=detail,title=title,source_category=src_category,category=category,
                 category_needs_review=category_review,transaction_type='Bán' if selling else 'Chưa xác định/thuê',
                 price_raw=value(card,'a-txt-cl1'),price_million=price,
                 area_raw=value(card,'a-txt-cl2'),area_sqm=area,address_raw=address,
                 district=district,ward=parts[0] if len(parts)>1 else '',
                 rooms=count(r'(\d+)\s*phong ngu'),toilets=count(r'(\d+)\s*wc'),
                 image_url=urljoin(BASE,img[0]) if img else '',
                 posted_at_raw=value(card,'time'),posted_at_semantics='relative display; may reflect update/repost; no exact date inferred',
                 collected_at=datetime.now(timezone.utc).isoformat(),listing_page=url,
                 detail_fetched=False,location_status='in_scope' if in_scope and selling else 'review_or_outside_scope',
                 price_needs_review=price is None or price<100 or
                    (area is not None and area>0 and not 2<=price/area<=300),
                 area_needs_review=area is None or not 20<=area<=1000)
        rows.append(r)
    links = {urljoin(BASE,u).rstrip('/') for u in doc.xpath('//a[@href]/@href')}
    return rows, links

def replace(tmp,path):
    for n in range(10):
        try:
            tmp.replace(path); return
        except PermissionError:
            if n == 9: raise
            print('CSV locked; close Excel. Retrying in 3 seconds.',flush=True); time.sleep(3)

def save(rows,path):
    tmp = path.with_suffix('.csv.tmp')
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS); w.writeheader(); w.writerows(rows)
    replace(tmp,path)

def load(path):
    if not path.exists(): return []
    with path.open(encoding='utf-8-sig',newline='') as f:
        rd=csv.DictReader(f)
        if rd.fieldnames != FIELDS: raise ValueError('Different CSV schema; use another output directory')
        return list(rd)

def main(args):
    args.output_dir.mkdir(parents=True,exist_ok=True)
    out=args.output_dir/'nhadat24h_records.csv'; rejected_path=args.output_dir/'nhadat24h_quarantine.csv'
    cp=args.output_dir/'nhadat24h_checkpoint.json'
    rows=load(out); rejected=load(rejected_path)
    seen={r['list_id'] for r in rows+rejected}
    state=json.loads(cp.read_text()) if cp.exists() else {}
    if state.get('finished'): print('Previous run reached end/scope stop'); return
    page=state.get('next_page',1); last=0
    def get(url):
        nonlocal last
        if urlparse(url).hostname!='nhadat24h.net': raise ValueError('Off-site request refused')
        time.sleep(max(0,args.delay-(time.monotonic()-last))); last=time.monotonic()
        with urlopen(Request(url,headers={'User-Agent':UA,'Accept':'*/*'}),timeout=30) as response:
            if response.url.rstrip('/')!=url.rstrip('/'): raise ValueError('Unexpected redirect')
            body=response.read()
        if any(x in body.lower() for x in [b'cf-chl-',b'verify you are human',b'just a moment']):
            raise ValueError('Challenge page; stop')
        return body
    robot=RobotFileParser(BASE+'/robots.txt')
    robot.parse(get(BASE+'/robots.txt').decode().replace('\\r\\n','\n').splitlines())
    args.delay=max(args.delay,robot.crawl_delay(UA) or 0)
    added=0; signatures=set()
    for _ in range(args.pages):
        url=LIST+(f'/page{page}' if page>1 else '')
        if not robot.can_fetch(UA,url): raise ValueError('robots.txt disallows this page')
        cards,links=parse(get(url),url)
        signature=frozenset(r['list_id'] for r in cards)
        if signature in signatures: raise ValueError('Repeated page; stopped')
        signatures.add(signature)
        kept=0; complete=True
        for r in cards:
            if r['list_id'] in seen: continue
            if added>=args.max_new: complete=False; break
            if r['location_status']=='in_scope': rows.append(r); added+=1; kept+=1
            else: rejected.append(r)
            seen.add(r['list_id'])
        save(rows,out); save(rejected,rejected_path)
        next_url=LIST+f'/page{page+1}'
        finished=complete and (next_url not in links or not any(r['location_status']=='in_scope' for r in cards))
        tmp=cp.with_suffix('.json.tmp'); tmp.write_text(json.dumps({'next_page':page+1 if complete else page,'finished':finished}),encoding='utf-8'); replace(tmp,cp)
        print(f'Page {page}: cards={len(cards)}, new={kept}, run_new={added}, total={len(rows)}, quarantined={len(rejected)}',flush=True)
        if added>=args.max_new or finished: break
        page+=1

if __name__=='__main__':
    p=argparse.ArgumentParser(); p.add_argument('--pages',type=int,default=10)
    p.add_argument('--max-new',type=int,default=200); p.add_argument('--delay',type=float,default=3)
    p.add_argument('--output-dir',type=Path,default=Path(__file__).resolve().parent/'nhadat24h_run')
    args=p.parse_args()
    if args.pages<1 or args.max_new<1 or args.delay<2: p.error('positive limits and delay >= 2 required')
    try: main(args)
    except KeyboardInterrupt: p.exit(130,'Stopped. Saved pages retained; rerun resumes.\n')
    except Exception as e: p.exit(1,f'Stopped: {e}. Saved pages retained; no automatic request retry.\n')
