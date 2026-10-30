"""Small Homedy trial: public house-sale listings, provenance, checkpoints and review flags."""
import argparse,csv,hashlib,json,os,re,time
from collections import Counter
from datetime import datetime,timezone
from pathlib import Path
from urllib.error import HTTPError,URLError
from urllib.parse import urljoin,urlparse
from urllib.request import Request,urlopen
from urllib.robotparser import RobotFileParser
from lxml import html

ROOT=Path(__file__).resolve().parent
BASE='https://homedy.com'
START=BASE+'/ban-nha-rieng-da-nang'
AGENT='SmartProp-Research/1.0'
FIELDS=['source','source_listing_id','source_url','collected_at','source_published_date_raw','source_expiry_date_raw','title','property_type','transaction_type','target_type','currency','price_unit','price_raw','price_vnd','price_million','area_raw','area_sqm','address_raw','district','ward','rooms','toilets','latitude','longitude','image_url','quality_status','review_flags','detail_sha256']
def now():return datetime.now(timezone.utc).isoformat()
def clean(s):return ' '.join((s or '').split())
def cls(name):return 'contains(concat(" ",normalize-space(@class)," ")," '+name+' ")'
def text(node,xpath):
    values=node.xpath(xpath)
    return clean(values[0].text_content() if hasattr(values[0],'text_content') else str(values[0])) if values else ''
def numeric(s):
    s=clean(s).replace(' ','')
    if not re.fullmatch(r'\d+(?:[.,]\d+)*',s):return None
    if ',' in s:s=s.replace('.','').replace(',','.')
    elif s.count('.')>1 or re.fullmatch(r'\d{1,3}(?:\.\d{3})+',s):s=s.replace('.','')
    try:return float(s)
    except ValueError:return None

def parse_price(raw):
    low=clean(raw).lower()
    if '/' in low or 'thỏa thuận' in low or 'thoả thuận' in low:return None
    match=re.fullmatch(r'([\d., ]+)\s*(tỷ|tỉ|triệu|tr|đ|đồng|vnd)',low)
    if not match:return None
    value=numeric(match[1]);unit=match[2]
    return value*({'tỷ':1e9,'tỉ':1e9,'triệu':1e6,'tr':1e6}.get(unit,1)) if value is not None else None

def get(url):
    parsed=urlparse(url)
    if parsed.scheme!='https' or parsed.hostname!='homedy.com':raise ValueError('Unexpected source URL')
    with urlopen(Request(url,headers={'User-Agent':AGENT,'Accept':'text/html,text/plain'}),timeout=30) as r:
        if urlparse(r.url).hostname!='homedy.com':raise ValueError('Unexpected redirect')
        data=r.read()
    return data

def listing_links(data):
    doc=html.fromstring(data.decode('utf-8'))
    heading=text(doc,'//h1')
    if 'Nhà Riêng' not in heading or 'Đà Nẵng' not in heading:raise ValueError('Listing scope changed')
    links=[]
    for card in doc.xpath('//div['+cls('product-item')+']'):
        href=text(card,'.//a[contains(@href,"-es")]/@href')
        if href:
            url=urljoin(BASE+'/',href)
            if re.search(r'-es\d+$',url) and url not in links:links.append(url)
    if not links:raise ValueError('No listing links; possible changed HTML or challenge')
    return links

def parse_detail(data,url,collected):
    doc=html.fromstring(data.decode('utf-8'));heads=doc.xpath('//h1')
    if not heads:raise ValueError('Missing listing heading')
    head=heads[0]
    scope=next((a for a in head.iterancestors() if 'product-item' in (a.get('class') or '').split()),None)
    if scope is None:raise ValueError('Missing main detail scope')
    breadcrumbs=scope.xpath('.//div['+cls('breadcrumb')+']//a/@href')
    if START not in breadcrumbs:raise ValueError('Detail is outside house-sale Da Nang scope')
    title=clean(head.text_content());attrs={};info={};primary={}
    for item in scope.xpath('.//div['+cls('product-attributes--item')+']'):
        vals=[clean(s.text_content()) for s in item.xpath('./span')]
        if len(vals)>=2:attrs[vals[0]]=vals[1]
    sid=re.search(r'-es(\d+)$',url)[1]
    for block in doc.xpath('//div['+cls('product-info')+']'):
        candidate={}
        for item in block.xpath('./div'):
            label=text(item,'./p['+cls('lb-code')+']');value=text(item,'./p['+cls('code')+']')
            if label:candidate[label]=value
        if candidate.get('ID tin')==sid:
            info=candidate;break
    for item in scope.xpath('.//div['+cls('product-detail')+']//li'):
        label=text(item,'./label');value=text(item,'./strong')
        if label:primary[label]=value
    price_raw=primary.get('Giá','');area_raw=primary.get('Diện tích','')
    if not price_raw or not area_raw:raise ValueError('Missing structured price/area; stopped for parser review')
    sid=re.search(r'-es(\d+)$',url)[1]
    if info.get('ID tin')!=sid or info.get('Loại tin')!='Bán' or attrs.get('Loại hình')!='Nhà riêng':raise ValueError('Detail ID/type mismatch')
    price=parse_price(price_raw)
    match=re.fullmatch(r'([\d., ]+)\s*m[²2]',area_raw)
    area=numeric(match[1]) if match else None
    flags=[]
    if price is None or price<=0:flags.append('missing_or_negotiated_price')
    elif not 1e8<=price<=2e11:flags.append('price_outside_review_range')
    if area is None or not 10<=area<=5000:flags.append('area_missing_or_outside_review_range')
    description=text(scope,'.//div['+cls('description')+']')
    if price is not None and price<1e8 and re.search(r'\d[\d.,]*\s*(?:tỷ|tỉ)\b',description,re.I):flags.append('possible_price_unit_conflict')
    if re.search(r'\bbán\s+đất\b',title,re.I):flags.append('title_may_describe_land')
    address=text(scope,'.//div['+cls('product-top')+']//div['+cls('address')+']')
    district_match=re.search(r'(Quận\s+[^,\-]+|Huyện\s+[^,\-]+)',address)
    ward_match=re.search(r'((?:Phường|Xã)\s+[^,\-]+)',address)
    def count_feature(keys):
        for key in keys:
            raw=attrs.get(key,'')
            m=re.fullmatch(r'\s*(\d+)\s*(?:phòng)?\s*',raw)
            if m:return int(m[1])
        return None
    record=dict.fromkeys(FIELDS)
    record.update(source='homedy',source_listing_id=sid,source_url=url,collected_at=collected,
        source_published_date_raw=info.get('Ngày đăng'),source_expiry_date_raw=info.get('Ngày hết hạn'),
        title=title,property_type='house',transaction_type='sale',target_type='asking_price',currency='VND',price_unit='total',
        price_raw=price_raw,price_vnd=price,price_million=price/1e6 if price is not None else None,area_raw=area_raw,area_sqm=area,
        address_raw=address,district=clean(district_match[1]) if district_match else None,ward=clean(ward_match[1]) if ward_match else None,
        rooms=count_feature(['Số phòng ngủ','Phòng ngủ']),toilets=count_feature(['Số phòng tắm','Số toilet','Phòng tắm','Số phòng vệ sinh']),
        image_url=text(scope,'.//div['+cls('button-report')+']//button/@data-media'),
        quality_status='review' if flags else 'candidate',review_flags=flags,detail_sha256=hashlib.sha256(data).hexdigest())
    # Deliberately do not read global JSON-LD LocalBusiness.geo: it belongs to Homedy's office.
    return record

def atomic(path,data):
    tmp=path.with_suffix(path.suffix+'.tmp');tmp.write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding='utf-8');os.replace(tmp,path)

def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--max-new',type=int,default=20);p.add_argument('--pages',type=int,default=2);p.add_argument('--delay',type=float,default=2);p.add_argument('--output',type=Path,default=ROOT/'data_raw'/'homedy');args=p.parse_args()
    if not 1<=args.max_new<=100 or not 1<=args.pages<=5 or args.delay<2:p.error('max-new 1..100, pages 1..5, delay >=2')
    out=args.output.resolve();out.mkdir(parents=True,exist_ok=True)
    lock=out/'collector.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    except FileExistsError:raise SystemExit('Collector already running or stale lock; inspect before removing')
    try:run(args,out)
    finally:lock.unlink()

def run(args,out):
    started=now();log=out/'records.jsonl';records=[]
    if log.exists():records=[json.loads(x) for x in log.read_text(encoding='utf-8').splitlines()]
    seen={r['source_listing_id'] for r in records};initial=len(records);visited=[];page_hashes=set();status='page_limit';error=None
    try:
        raw=get(BASE+'/robots.txt');(out/'robots.txt').write_bytes(raw)
        robot=RobotFileParser();robot.parse(raw.decode('utf-8').splitlines())
        delay=max(args.delay,robot.crawl_delay(AGENT) or 0)
        if not robot.can_fetch(AGENT,START):raise ValueError('robots.txt disallows this collector')
        time.sleep(delay)
        for page in range(1,args.pages+1):
            url=START if page==1 else START+'/p'+str(page)
            if not robot.can_fetch(AGENT,url):raise ValueError('robots.txt disallows listing page')
            data=get(url);links=listing_links(data);signature=tuple(links)
            if signature in page_hashes:status='repeated_page';break
            page_hashes.add(signature);visited.append({'url':url,'unique_links':len(links),'sha256':hashlib.sha256(data).hexdigest()})
            for detail_url in links:
                sid=re.search(r'-es(\d+)$',detail_url)[1]
                if sid in seen:continue
                if not robot.can_fetch(AGENT,detail_url):raise ValueError('robots.txt disallows detail')
                time.sleep(delay);raw=get(detail_url);record=parse_detail(raw,detail_url,now())
                with log.open('a',encoding='utf-8',newline='\n') as f:f.write(json.dumps(record,ensure_ascii=False)+'\n');f.flush();os.fsync(f.fileno())
                records.append(record);seen.add(sid)
                atomic(out/'checkpoint.json',{'last_page':page,'last_source_id':sid,'updated_at':now(),'resume_policy':'Rescan from page 1, skip persisted source IDs'})
                print(json.dumps({'new':len(records)-initial,'id':sid,'quality':record['quality_status']}),flush=True)
                if len(records)-initial>=args.max_new:status='new_limit';break
            if status=='new_limit':break
            time.sleep(delay)
    except (HTTPError,URLError,TimeoutError,ValueError,OSError) as e:status='stopped_error';error=str(e)
    tmp=out/'homedy_records.csv.tmp'
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for r in records:w.writerow({**r,'review_flags':';'.join(r['review_flags'])})
    os.replace(tmp,out/'homedy_records.csv')
    review=[r for r in records if r['quality_status']=='review']
    with (out/'review_required.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=FIELDS);w.writeheader()
        for r in review:w.writerow({**r,'review_flags':';'.join(r['review_flags'])})
    report={'started_at':started,'finished_at':now(),'status':status,'error':error,'new_records':len(records)-initial,'total_records':len(records),
        'quality_counts':dict(Counter(r['quality_status'] for r in records)),'district_counts':dict(Counter(r['district'] for r in records)),
        'missing_fields':{k:sum(r[k] is None or r[k]=='' for r in records) for k in ['price_vnd','area_sqm','rooms','toilets','ward','latitude','longitude']},
        'listing_pages':visited,'robots_user_agent':AGENT,
        'limitations':['Candidates need manual review and cross-source property deduplication before training.','No property coordinates verified; site-wide company coordinates are excluded.','Source listing dates are not historical transaction dates.','Source use/redistribution terms are not established by robots.txt.','Missing rooms/toilets are not filled with zeros.']}
    atomic(out/'latest_run.json',report);atomic(out/('run_'+started.replace(':','-')+'.json'),report);print(json.dumps(report,ensure_ascii=True,indent=2),flush=True)
    if error:raise SystemExit(1)
if __name__=='__main__':main()
