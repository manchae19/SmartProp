"""Bounded CafeLand apartment pilot; separate checkpoint, no model or old-data writes."""
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.robotparser import RobotFileParser

from lxml import html
from crawler_cafeland import crawl_cafeland_danang as cafe

BASE=Path(__file__).resolve().parent
ORIGIN='https://nhadat.cafeland.vn'
START=ORIGIN+'/nha-dat-ban/ban-can-ho-chung-cu-tai-da-nang/'
UA='SmartPropResearch/0.2 (+local academic project; public apartment listings)'
HISTORY=BASE/'processed/remaining_diversity_review/runs/1d45c8941172a52d/all_listings_after_review.csv'
OUT=BASE/'data_raw/apartment_pilot_100'
POLICY=dict(target=100,request_delay_seconds=3,max_pages=12,source='cafeland',
            date_semantics='Source declared publication display; may be update/repost, not independently verified',
            old_history_read_only=True,no_model_training=True)


def now():return datetime.now(timezone.utc).isoformat()
def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def atomic(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    temporary.write_text(json.dumps(value,ensure_ascii=False,indent=2),encoding='utf-8')
    temporary.replace(path)


def listing_page(body,url):
    doc=html.fromstring(body.decode('utf-8'))
    if not any('can ho' in cafe.norm(h.text_content()) and 'da nang' in cafe.norm(h.text_content()) for h in doc.xpath('//h1')):
        raise ValueError('Apartment listing scope or HTML changed')
    rows=[];seen=set()
    for card in cafe.nodes(doc,'row-item'):
        anchors=cafe.nodes(card,'realTitle')
        if not anchors:continue
        link=anchors[0].get('href','')
        match=re.fullmatch(r'https://nhadat\.cafeland\.vn/[^/?]+-(\d+)\.html',link)
        if not match:raise ValueError('Unexpected detail URL')
        if match[1] in seen:continue
        seen.add(match[1])
        rows.append(dict(record_key='cafeland:'+match[1],source='cafeland',source_listing_id=match[1],detail_url=link,
                         listing_title=cafe.clean(anchors[0].text_content()),listing_price_raw=cafe.value(card,'reales-price'),
                         listing_area_raw=cafe.value(card,'reales-area'),listing_address_raw=cafe.value(card,'info-location'),listing_page=url))
    if not rows:raise ValueError('No expected apartment listing cards')
    links={a for a in doc.xpath('//a/@href') if re.fullmatch(re.escape(START)+r'page-\d+/',a)}
    return rows,links


def parse_detail(body,row,collected_at):
    doc=html.fromstring(body.decode('utf-8'))
    roots=cafe.nodes(doc,'detail-property')
    if len(roots)!=1:raise ValueError('Property container changed')
    root=roots[0];heads=root.xpath('.//h1')
    if len(heads)!=1:raise ValueError('Property heading missing or ambiguous')
    products=[]
    for script in doc.xpath('//script[@type="application/ld+json"]'):
        obj=json.loads(script.text or '{}',strict=False)
        if isinstance(obj,dict) and obj.get('@type')=='Product':products.append(obj)
    if len(products)!=1 or products[0].get('offers',{}).get('url')!=row['detail_url']:
        raise ValueError('Detail identity could not be verified')
    offer=products[0]['offers']
    locations=[n for n in cafe.nodes(root,'infor') if cafe.norm(n.text_content()).startswith('vi tri:')]
    if len(locations)!=1:raise ValueError('Property location missing')
    anchors=locations[0].xpath('./a')
    parts=[cafe.clean(a.text_content()) for a in anchors]
    source_category=next((re.search(r'/nha-dat-ban/(ban-[^/]+)-tai-',a.get('href',''))[1]
                          for a in anchors if re.search(r'/nha-dat-ban/(ban-[^/]+)-tai-',a.get('href',''))),'')
    attributes={}
    for block in cafe.nodes(root,'col-item'):
        labels,values=cafe.nodes(block,'infor-note'),cafe.nodes(block,'infor-data')
        if labels:
            attributes[cafe.norm(labels[0].text_content())]=cafe.clean(values[0].text_content()) if values else ''
    if 'gia ban' not in attributes or 'dien tich' not in attributes:
        raise ValueError('Structured price/area labels changed')
    price_raw,area_raw=attributes['gia ban'],attributes['dien tich']
    title=cafe.clean(heads[0].text_content())
    descriptions=cafe.nodes(root,'reals-description')
    description=cafe.clean(descriptions[0].text_content()) if descriptions else ''
    metadata=' '.join(cafe.clean(n.text_content()) for n in cafe.nodes(root,'infor'))
    date_match=re.search(r'Ngày đăng:\s*(\d{2}-\d{2}-\d{4})',metadata,re.I)
    source_date=date_match[1] if date_match else ''
    try:published=datetime.strptime(source_date,'%d-%m-%Y').date().isoformat() if source_date else ''
    except ValueError:published=''
    price,area=cafe.price(price_raw),cafe.area(area_raw)
    flags=[]
    if title!=row['listing_title']:flags.append('listing_detail_title_changed')
    if price!=cafe.price(row['listing_price_raw']):flags.append('listing_detail_price_mismatch')
    if area!=cafe.area(row['listing_area_raw']):flags.append('listing_detail_area_mismatch')
    if price is None:flags.append('missing_or_non_total_price')
    if area is None:flags.append('missing_structured_area')
    if offer.get('priceCurrency')!='VND':flags.append('currency_unverified')
    if price is not None:
        try:
            if abs(float(offer.get('price',''))/1e6-price)>.01:flags.append('jsonld_price_mismatch')
        except (TypeError,ValueError):flags.append('jsonld_price_unreadable')
    if not published:flags.append('missing_or_invalid_source_date')
    if not any(cafe.norm(part)=='da nang' for part in parts):flags.append('outside_or_unknown_municipality')
    if source_category!='ban-can-ho-chung-cu':flags.append('source_category_not_apartment')
    room_match=re.fullmatch(r'(\d+)\s*(?:PN|phòng)?',attributes.get('phong ngu',''),re.I)
    return dict(row,title=title,source_category=source_category,category='Căn hộ chung cư' if source_category=='ban-can-ho-chung-cu' else 'Chưa xác định',
                transaction_type='sale',target_type='asking_price',currency=offer.get('priceCurrency',''),
                price_raw=price_raw,price_million=price,area_raw=area_raw,area_sqm=area,
                address_raw=', '.join(parts),source_location_parts=parts,rooms=int(room_match[1]) if room_match else None,
                source_published_date_raw=source_date,source_published_date=published,date_basis=POLICY['date_semantics'],
                price_valid_until_raw=offer.get('priceValidUntil',''),collected_at=collected_at,
                description=description,source_evidence_flags=flags,detail_fetched=True,
                response_sha256=hashlib.sha256(body).hexdigest())


class Client:
    def __init__(self,output,delay):
        self.output=output;self.delay=max(3,delay);self.last=0;self.robot=None
        raw,_=self.fetch(ORIGIN+'/robots.txt',False)
        (output/'robots.txt').write_bytes(raw)
        self.robot=RobotFileParser();self.robot.parse(raw.decode('utf-8').replace('\\r\\n','\n').splitlines())
        self.delay=max(self.delay,self.robot.crawl_delay(UA) or self.robot.crawl_delay('*') or 0)

    def validate_redirect(self,old,new):
        parsed=urlparse(new)
        old_id=re.fullmatch(r'/[^/?]+-(\d+)\.html',urlparse(old).path)
        new_id=re.fullmatch(r'/[^/?]+-(\d+)\.html',parsed.path)
        if (parsed.scheme!='https' or parsed.netloc!='nhadat.cafeland.vn' or parsed.query or
            not old_id or not new_id or old_id[1]!=new_id[1] or
            not self.robot or not self.robot.can_fetch(UA,new)):
            raise ValueError('Unexpected redirect; destination not requested')

    def fetch(self,url,check=True):
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.hostname!='nhadat.cafeland.vn':raise ValueError('Off-site request refused')
        if check and not self.robot.can_fetch(UA,url):raise ValueError('robots.txt disallows URL')
        time.sleep(max(0,self.delay-(time.monotonic()-self.last)));self.last=time.monotonic()
        client=self
        class SameListingRedirect(HTTPRedirectHandler):
            max_redirections=3
            def redirect_request(self,req,fp,code,msg,headers,newurl):
                client.validate_redirect(req.full_url,newurl)
                time.sleep(max(0,client.delay-(time.monotonic()-client.last)));client.last=time.monotonic()
                return super().redirect_request(req,fp,code,msg,headers,newurl)
        try:
            with build_opener(SameListingRedirect).open(Request(url,headers={'User-Agent':UA,'Accept':'text/html,text/plain'}),timeout=25) as response:
                self.last_url=response.url
                body=response.read(10*1024*1024+1)
                if len(body)>10*1024*1024:raise ValueError('Source response exceeds bound')
                status=response.status
        except HTTPError as error:
            if error.code in [404,410]:
                self.last_url=url
                return error.read(1024*1024),error.code
            raise
        if any(marker in body.lower() for marker in [b'cf-chl-',b'verify you are human',b'just a moment']):
            raise ValueError('Challenge detected; stopped without bypass')
        return body,status


def export_csv(path,rows):
    if not rows:return
    fields=list(dict.fromkeys(key for row in rows for key in row))
    with path.with_suffix('.csv.tmp').open('w',encoding='utf-8-sig',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for row in rows:writer.writerow({k:json.dumps(v,ensure_ascii=False) if isinstance(v,(list,dict)) else v for k,v in row.items()})
    path.with_suffix('.csv.tmp').replace(path)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=int,default=100)
    parser.add_argument('--pages',type=int,default=12,help='Maximum listing pages per invocation, starting at checkpoint')
    parser.add_argument('--delay',type=float,default=3);parser.add_argument('--output',type=Path,default=OUT)
    args=parser.parse_args()
    if not 1<=args.target<=100 or not 1<=args.pages<=12 or args.delay<3:parser.error('target 1..100, pages 1..12, delay>=3')
    output=args.output.resolve()
    if not output.is_relative_to((BASE/'data_raw').resolve()):parser.error('Output must be a separate data_raw batch')
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'collector.lock'
    try:descriptor=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(descriptor)
    except FileExistsError:raise SystemExit('Collector lock exists; inspect before resuming')
    status='not_started';error=None;started=now();rows=[]
    try:
        previous=output/'latest_run.json'
        if previous.exists():
            runs=output/'run_history';runs.mkdir(exist_ok=True)
            prior=json.loads(previous.read_text(encoding='utf8'))
            atomic(runs/(prior['started_at'].replace(':','-')+'.json'),prior)
        (output/'detail_cache').mkdir(exist_ok=True);(output/'list_cache').mkdir(exist_ok=True)
        history_sha=sha(HISTORY)
        with HISTORY.open(encoding='utf-8-sig',newline='') as stream:history={r['record_key'] for r in csv.DictReader(stream)}
        policy_path=output/'policy.json'
        policy=dict(POLICY,history_sha256=history_sha,history_n=len(history),requested_target=args.target,max_pages=args.pages)
        if policy_path.exists() and json.loads(policy_path.read_text(encoding='utf8'))!=policy:raise ValueError('Batch policy changed; use a new output batch')
        atomic(policy_path,policy)
        log=output/'records.jsonl'
        if log.exists():rows=[json.loads(line) for line in log.read_text(encoding='utf8').splitlines() if line]
        seen={r['record_key'] for r in rows}
        if len(seen)!=len(rows) or seen&history:raise ValueError('Persisted duplicate/historical IDs')
        checkpoint=output/'checkpoint.json'
        state=json.loads(checkpoint.read_text(encoding='utf8')) if checkpoint.exists() else dict(next_page=1,attempted=[],listings_seen=0,historical_skipped=0)
        attempted=set(state['attempted']);page=int(state['next_page']);status='page_limit'
        if len(rows)<args.target:
            client=Client(output,args.delay)
            for _ in range(args.pages):
                url=START if page==1 else START+f'page-{page}/'
                body,http=client.fetch(url)
                if http!=200:status='listing_unavailable';break
                (output/'list_cache'/f'page-{page}.html').write_bytes(body)
                cards,links=listing_page(body,url)
                for card in cards:
                    key=card['record_key']
                    if key in attempted or key in seen:continue
                    state['listings_seen']+=1
                    if key in history:
                        state['historical_skipped']+=1;attempted.add(key)
                    else:
                        raw,http=client.fetch(card['detail_url'])
                        path=output/'detail_cache'/(card['source_listing_id']+'.html')
                        path.write_bytes(raw)
                        attempted.add(key)
                        if http==200:
                            if client.last_url!=card['detail_url']:
                                card=dict(card,requested_detail_url=card['detail_url'],detail_url=client.last_url)
                            record=parse_detail(raw,card,now());record['detail_file']=path.relative_to(output).as_posix()
                            with log.open('a',encoding='utf8',newline='\n') as stream:
                                stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                            rows.append(record);seen.add(key)
                            print(json.dumps(dict(total_new=len(rows),record_key=key,evidence_flags=len(record['source_evidence_flags'])),ensure_ascii=True),flush=True)
                    state.update(next_page=page,attempted=sorted(attempted),updated_at=now())
                    atomic(checkpoint,state)
                    if len(rows)>=args.target:status='target_reached';break
                if status=='target_reached':break
                next_url=START+f'page-{page+1}/'
                if next_url not in links:status='end_of_pages';break
                page+=1;state['next_page']=page;atomic(checkpoint,state)
        else:status='target_already_reached'
        if sha(HISTORY)!=history_sha:raise ValueError('Historical snapshot changed during collection')
    except KeyboardInterrupt:
        status='interrupted';error='KeyboardInterrupt'
    except Exception as failure:
        status='stopped_error';error=type(failure).__name__+': '+str(failure)
    finally:
        export_csv(output/'apartment_records.csv',rows)
        atomic(output/'latest_run.json',dict(started_at=started,finished_at=now(),status=status,error=error,total_new=len(rows),
               source='cafeland',model_changed=False,detail_cache_private=True,
               collector_sha256=sha(__file__),numeric_parser_sha256=sha(cafe.__file__)))
        lock.unlink()
    print(json.dumps(dict(status=status,total_new=len(rows),error=error),ensure_ascii=True),flush=True)
    return 0 if status in ['target_reached','target_already_reached','end_of_pages','page_limit'] else 1


if __name__=='__main__':raise SystemExit(main())
