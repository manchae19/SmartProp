"""CafeLand public pages, seven historical Da Nang districts, resumable CSV.
Requires: pip install lxml. No contacts, login, challenge or rate-limit bypass.
"""
import argparse, csv, json, re, time, unicodedata
from pathlib import Path
from datetime import datetime, timezone
from urllib.request import Request, urlopen
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from lxml import html
BASE = 'https://nhadat.cafeland.vn'
LIST = BASE + '/nha-dat-ban-tai-da-nang/'
UA = 'SmartPropResearch/0.1'
DISTRICTS = ['Hải Châu','Thanh Khê','Sơn Trà','Ngũ Hành Sơn','Liên Chiểu','Cẩm Lệ','Hòa Vang']
FIELDS = ['list_id','source','source_listing_id','detail_url','title','source_category','category','category_needs_review','transaction_type','price_raw','price_million','area_raw','area_sqm','address_raw','district','ward','rooms','toilets','image_url','posted_at','updated_display_raw','updated_attribute_raw','updated_timestamp_raw','date_needs_review','price_valid_until_raw','collected_at','listing_page','detail_fetched','location_status','price_needs_review','area_needs_review','review_reason']
def clean(s): return ' '.join((s or '').split())
def norm(s): return ''.join(c for c in unicodedata.normalize('NFD',clean(s).lower()) if unicodedata.category(c)!='Mn').replace('đ','d')
def nodes(x,c): return x.xpath('.//*[contains(concat(" ",normalize-space(@class)," "),$c)]',c=' '+c+' ')
def value(x,c): return clean(nodes(x,c)[0].text_content()) if nodes(x,c) else ''
def price(s):
    s=norm(s)
    m=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*ty(?:\s*(\d+(?:[.,]\d+)?)\s*trieu)?',s)
    if m: return float(m[1].replace(',','.'))*1000+(float(m[2].replace(',','.')) if m[2] else 0)
    m=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*trieu',s)
    return float(m[1].replace(',','.')) if m else None

def area(s):
    m=re.fullmatch(r'(\d+(?:[.,]\d+)?)\s*m[2²]',norm(s))
    return float(m[1].replace(',','.')) if m else None

def location(parts):
    district=next((d for d in DISTRICTS if any(norm(p) in {norm(d),'quan '+norm(d),'huyen '+norm(d)} for p in parts)),'')
    return district, 'in_scope' if district and any(norm(p)=='da nang' for p in parts) else 'review_or_outside_scope'

def parse_list(body,url):
    doc=html.fromstring(body)
    if not any('da nang' in norm(h.text_content()) for h in doc.xpath('//h1')): raise ValueError('Unexpected listing heading')
    result=[]; seen=set()
    for card in nodes(doc,'row-item'):
        aa=nodes(card,'realTitle')
        if not aa: continue
        a=aa[0]; link=a.get('href',''); m=re.fullmatch(r'https://nhadat\.cafeland\.vn/[^/?]+-(\d+)\.html',link)
        if not m: raise ValueError('Unexpected detail URL')
        if m[1] in seen: continue
        seen.add(m[1]); r=dict.fromkeys(FIELDS,'')
        address=value(card,'info-location'); district,status=location([clean(p) for p in address.split(',')])
        dt=nodes(card,'reals-update-time'); imgs=card.xpath('.//img/@data-src')
        r.update(list_id='cafeland:'+m[1],source='cafeland',source_listing_id=m[1],detail_url=link,title=clean(a.text_content()),transaction_type='Bán',price_raw=value(card,'reales-price'),area_raw=value(card,'reales-area'),address_raw=address,district=district,image_url=imgs[0] if imgs else '',updated_display_raw=clean(dt[0].text_content()) if dt else '',updated_attribute_raw=dt[0].get('data-time','') if dt else '',updated_timestamp_raw=dt[0].get('data-timestp','') if dt else '',date_needs_review=True,collected_at=datetime.now(timezone.utc).isoformat(),listing_page=url,detail_fetched=False,location_status=status)
        result.append(r)
    if not result: raise ValueError('No expected listing cards; inspect page')
    next_url=LIST+'page-'+str(2 if url==LIST else int(re.search(r'page-(\d+)',url)[1])+1)+'/'
    return result, bool(doc.xpath('//a[@href=$u]',u=next_url))

def parse_detail(body,r,location_resolver=None):
    doc=html.fromstring(body); roots=nodes(doc,'detail-property')
    if len(roots)!=1: raise ValueError('Property container changed')
    root=roots[0]; titles=root.xpath('.//h1')
    if len(titles)!=1 or clean(titles[0].text_content())!=r['title']: raise ValueError('Detail title mismatch')
    products=[]; jsonld_control_characters=False
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        try:
            obj=json.loads(script.text or '{}')
        except json.JSONDecodeError:
            # Some public pages embed literal newlines in JSON string values.
            # Other syntax errors still fail, and identity checks remain below.
            obj=json.loads(script.text or '{}',strict=False)
            jsonld_control_characters=True
        if isinstance(obj,dict) and obj.get('@type')=='Product': products.append(obj)
    if len(products)!=1 or products[0].get('offers',{}).get('url')!=r['detail_url']: raise ValueError('Detail identity mismatch')
    offer=products[0]['offers']; loc=next((x for x in nodes(root,'infor') if norm(x.text_content()).startswith('vi tri:')),None)
    if loc is None: raise ValueError('Property location missing')
    links=loc.xpath('./a'); parts=[clean(a.text_content()) for a in links]
    district,status=(location_resolver or location)(parts)
    if status!='in_scope' or district!=r['district']: raise ValueError('Listing/detail location mismatch')
    data={}
    for box in nodes(root,'col-item'):
        labels=nodes(box,'infor-note'); vals=nodes(box,'infor-data')
        if labels and vals: data[norm(labels[0].text_content())]=clean(vals[0].text_content())
    pr=data.get('gia ban',''); ar=data.get('dien tich','')
    if 'gia ban' not in data or 'dien tich' not in data:
        raise ValueError('Property price/area labels missing; inspect structure')
    reasons=[]
    if jsonld_control_characters: reasons.append('jsonld_control_characters')
    if not pr: reasons.append('missing_detail_price')
    if not ar: reasons.append('missing_detail_area')
    if price(pr)!=price(r['price_raw']) or area(ar)!=area(r['area_raw']): reasons.append('listing_detail_value_mismatch')
    src=next((re.search(r'/nha-dat-ban/(ban-[^/]+)-tai-',a.get('href',''))[1] for a in links if re.search(r'/nha-dat-ban/(ban-[^/]+)-tai-',a.get('href',''))),'')
    category={'ban-nha-rieng':'Nhà ở','ban-nha-pho':'Nhà ở','ban-biet-thu':'Nhà ở','ban-can-ho-chung-cu':'Căn hộ chung cư','ban-dat':'Đất nền','ban-dat-tho-cu':'Đất nền','ban-dat-nen':'Đất nền','ban-dat-nen-du-an':'Đất nền'}.get(src,'Chưa xác định')
    pn=price(pr); an=area(ar)
    pcheck=pn is None or pn<100 or pn>1000000
    if pn is not None and offer.get('priceCurrency')=='VND':
        try:
            if abs(float(offer.get('price',''))/1000000-pn)>0.01: reasons.append('jsonld_price_mismatch'); pcheck=True
        except (TypeError,ValueError): reasons.append('jsonld_price_unreadable'); pcheck=True
    catcheck=category=='Chưa xác định' or (category=='Nhà ở' and bool(re.search(r'\b(dat|khach san|homestay|toa can ho)\b',norm(r['title']))))
    r.update(source_category=src,category=category,category_needs_review=catcheck,price_raw=pr,price_million=pn,area_raw=ar,area_sqm=an,address_raw=', '.join(parts),district=district,rooms=data.get('phong ngu',''),toilets=data.get('phong tam',''),price_valid_until_raw=offer.get('priceValidUntil',''),detail_fetched=True,price_needs_review=pcheck or bool(reasons),area_needs_review=an is None or an<=0 or an>100000 or bool(reasons),review_reason=';'.join(reasons))
    return r

class Client:
    def __init__(self,delay):
        self.delay=max(2,delay); self.last=0
        self.robot=RobotFileParser(); self.robot.parse(self.fetch(BASE+'/robots.txt',False).decode('utf-8').splitlines())
        self.delay=max(self.delay,self.robot.crawl_delay(UA) or self.robot.crawl_delay('*') or 0)
    def fetch(self,url,check=True):
        if urlparse(url).hostname!='nhadat.cafeland.vn': raise ValueError('Unexpected host')
        if check and not self.robot.can_fetch(UA,url): raise ValueError('robots.txt disallows URL')
        if check: time.sleep(max(0,self.delay-(time.monotonic()-self.last)))
        self.last=time.monotonic()
        with urlopen(Request(url,headers={'User-Agent':UA}),timeout=30) as f:
            if f.status!=200 or 'html' not in f.headers.get('Content-Type','') and check: raise ValueError('Unexpected response')
            body=f.read()
        if check and any(w in body[:50000].lower() for w in [b'cf-chl-',b'captcha',b'access denied']): raise ValueError('Challenge/block detected; stopped')
        return body

def append(path,row):
    new=not path.exists()
    with path.open('a',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS)
        if new:w.writeheader()
        w.writerow(row)

def save_checkpoint(path,state):
    temporary=path.with_suffix('.tmp')
    temporary.write_text(json.dumps(state,indent=2),encoding='utf-8')
    # Windows readers/indexers may briefly deny replacement of an open file.
    # Keep the previous valid checkpoint until replacement succeeds.
    for attempt in range(10):
        try:
            temporary.replace(path)
            return
        except PermissionError:
            if attempt==9:
                raise
            time.sleep(min(0.2*(attempt+1),1))

def main():
    p=argparse.ArgumentParser(); p.add_argument('--pages',type=int,default=50); p.add_argument('--max-new',type=int,default=1000); p.add_argument('--delay',type=float,default=3); p.add_argument('--output-dir',default='cafeland_batch'); args=p.parse_args()
    if args.pages<1 or args.max_new<1:p.error('pages/max-new must be positive')
    out=Path(args.output_dir); out.mkdir(parents=True,exist_ok=True); checkpoint=out/'checkpoint.json'
    state=json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {'version':1,'next_page':1,'finished':False}
    if state.get('version')!=1:raise ValueError('Checkpoint version mismatch')
    if state.get('finished'):print('Reached pagination end; use a new output directory for a fresh crawl.'); return
    seen=set()
    for filename in ['cafeland_listings.csv','cafeland_scope_review.csv']:
        path=out/filename
        if path.exists():
            with path.open(encoding='utf-8-sig',newline='') as f:seen.update(r['source_listing_id'] for r in csv.DictReader(f))
    client=Client(args.delay); added=0; last_signature=None
    for page in range(state['next_page'],state['next_page']+args.pages):
        url=LIST if page==1 else LIST+f'page-{page}/'; body=client.fetch(url)
        try: rows,has_next=parse_list(body,url)
        except Exception:
            (out/'debug_listing.html').write_bytes(body); raise
        signature=tuple(r['source_listing_id'] for r in rows)
        if signature==last_signature:raise ValueError('Repeated page; stopped')
        last_signature=signature
        for r in rows:
            if r['source_listing_id'] in seen:continue
            if r['location_status']=='in_scope':
                detail=client.fetch(r['detail_url'])
                try:r=parse_detail(detail,r)
                except Exception:
                    (out/'debug_detail.html').write_bytes(detail); raise
                append(out/'cafeland_listings.csv',r); added+=1
                print(f"Saved {r['list_id']} ({added} new)",flush=True)
            else:append(out/'cafeland_scope_review.csv',r)
            seen.add(r['source_listing_id'])
            # Current page remains resumable if interrupted or max-new reached.
            state['next_page']=page; save_checkpoint(checkpoint,state)
            if added>=args.max_new: print(f'Added {added} detail listings; resume with same output directory.');return
        state.update(next_page=page+1,finished=not has_next); save_checkpoint(checkpoint,state)
        print(f'Page {page}: {len(rows)} unique cards, added {added} details',flush=True)
        if not has_next:break
    print(f'Completed: {added} new detail listings. Output: {out.resolve()}')
if __name__=='__main__':
    try:
        main()
    except KeyboardInterrupt:
        print('\nStopped by user. Saved CSV rows are retained. Run again with the same --output-dir to resume; saved IDs will be skipped.',flush=True)
        raise SystemExit(130)
