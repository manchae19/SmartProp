"""Bounded Nhadat24h follow-up; never writes the earlier CafeLand pilot."""
import argparse
import csv
from datetime import datetime
import hashlib
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.robotparser import RobotFileParser
from urllib.parse import urlparse

from lxml import html
import collect_apartment_pilot as common
import crawl_nhadat24h_danang as source

BASE=common.BASE
ORIGIN='https://nhadat24h.net'
START=ORIGIN+'/ban-can-ho-chung-cu-da-nang'
OUT=BASE/'data_raw/apartment_followup_nhadat24h'
UA='SmartPropResearch/0.3 (+local academic project; public apartment listings)'
MAX_PAGES=12
MAX_TARGET=30


def text(node):return ' '.join(node.text_content().split())


def one(doc,suffix):
    nodes=doc.xpath('//*[substring(@id,string-length(@id)-string-length($s)+1)=$s]',s=suffix)
    if len(nodes)!=1:raise ValueError('Source field changed: '+suffix)
    return nodes[0]


def listing(body,url):
    rows,links=source.parse(body,url)
    doc=html.fromstring(body)
    if not any('can ho chung cu' in source.norm(text(h)) and 'da nang' in source.norm(text(h)) for h in doc.xpath('//h1')):
        raise ValueError('Apartment listing heading changed')
    cards=[]
    for row in rows:
        cards.append(dict(record_key=row['list_id'],source='nhadat24h',source_listing_id=row['source_listing_id'],
            detail_url=row['detail_url'],listing_title=row['title'],listing_price_raw=row['price_raw'],
            listing_area_raw=row['area_raw'],listing_address_raw=row['address_raw'],listing_page=url,
            listing_category_raw=row['source_category'],listing_rooms=row['rooms'],listing_date_raw=row['posted_at_raw']))
    return cards,links


def parse_detail(body,row,collected_at):
    doc=html.fromstring(body)
    title=text(one(doc,'txtcontenttieudetin'))
    products=[json.loads(n.text or '{}',strict=False) for n in doc.xpath('//script[@type="application/ld+json"]')]
    products=[p for p in products if isinstance(p,dict) and p.get('@type')=='Product']
    if (len(products)>1 or (products and (products[0].get('offers',{}).get('url')!=row['detail_url'] or products[0].get('name')!=title)) or
        (not products and title!=row['listing_title'])):
        raise ValueError('JSON-LD detail identity unverified')
    offer=products[0]['offers'] if products else {}
    header=text(one(doc,'lbGiaDienTich'))
    match=re.fullmatch(r'can ban\s*:\s*(.+?)\s*-\s*(\d+(?:[.,]\d+)?\s*m[2²])',source.norm(header))
    if not match:raise ValueError('Sale price/area structure changed')
    pr,ar=match[1],match[2]
    price,area=common.cafe.price(pr),common.cafe.area(ar)
    category=text(one(doc,'lbLoaiBDS'));address=text(one(doc,'lbTinhThanh'))
    sale=one(doc,'txtLoaiTin').get('value')=='1'
    published_raw=one(doc,'txtNgaydang').get('value','')
    date_match=re.fullmatch(r'(\d{1,2}/\d{1,2}/\d{4}),\s*lúc:\s*\d+ giờ \d+ phút',published_raw)
    try:published=datetime.strptime(date_match[1],'%d/%m/%Y').date().isoformat() if date_match else ''
    except ValueError:published=''
    containers=doc.xpath('//*[contains(concat(" ",normalize-space(@class)," ")," sub1detailmaincontent ")]/div[1]')
    if len(containers)!=1:raise ValueError('Description structure changed')
    # Read the seller description container, never author/contact widgets.
    description=re.split(r'\bChat\b|Thông tin người đăng|Xem thêm từ khóa',text(containers[0]))[0]
    flags=[]
    if not products:flags.append('missing_jsonld_product_identity')
    if title!=row['listing_title']:flags.append('listing_detail_title_changed')
    if price!=common.cafe.price(row['listing_price_raw']):flags.append('listing_detail_price_mismatch')
    if area!=common.cafe.area(row['listing_area_raw']):flags.append('listing_detail_area_mismatch')
    if price is None:flags.append('missing_or_non_total_price')
    if area is None:flags.append('missing_structured_area')
    if offer.get('priceCurrency')!='VND':flags.append('currency_unverified')
    try:
        if price is not None and abs(float(offer.get('price',''))/1e6-price)>.01:flags.append('jsonld_price_mismatch')
    except (TypeError,ValueError):flags.append('jsonld_price_unreadable')
    if not sale:flags.append('not_verified_sale')
    if source.norm(category)!='can ho chung cu' or source.norm(row['listing_category_raw'])!='can ho chung cu':flags.append('source_category_not_apartment')
    if not re.search(r'\bda nang\b',source.norm(address)):flags.append('outside_or_unknown_municipality')
    if not published:flags.append('missing_or_invalid_source_date')
    return dict(row,title=title,source_category_original=category,
        source_category='ban-can-ho-chung-cu' if source.norm(category)=='can ho chung cu' else 'unknown',
        source_category_basis='Nhadat24h explicit property category, normalized to shared sale-apartment code',
        category='Căn hộ chung cư' if source.norm(category)=='can ho chung cu' else 'Chưa xác định',
        transaction_type='sale' if sale else 'unknown',target_type='asking_price',currency=offer.get('priceCurrency',''),
        price_raw=pr,price_million=price,area_raw=ar,area_sqm=area,address_raw=address,
        source_location_parts=[x.strip() for x in address.split(',')],rooms=int(row['listing_rooms']) if row['listing_rooms'] else None,
        source_published_date_raw=published_raw,source_published_date=published,
        date_basis='Source calendar display; may reflect update/repost, not independently verified first publication',
        collected_at=collected_at,description=description,source_evidence_flags=flags,detail_fetched=True,
        response_sha256=hashlib.sha256(body).hexdigest())


class Client:
    def __init__(self,output,delay):
        self.output=output;self.delay=max(3,delay);self.last=0;self.robot=None
        body,status=self.fetch(ORIGIN+'/robots.txt',False)
        if status!=200:raise ValueError('robots unavailable')
        (output/'robots.txt').write_bytes(body)
        self.robot=RobotFileParser();self.robot.parse(body.decode('utf8').replace('\\r\\n','\n').splitlines())
        self.delay=max(self.delay,self.robot.crawl_delay(UA) or self.robot.crawl_delay('*') or 0)

    def fetch(self,url,check=True):
        parsed=urlparse(url)
        if parsed.scheme!='https' or parsed.netloc!='nhadat24h.net' or parsed.query:raise ValueError('Unexpected source URL')
        if check and not self.robot.can_fetch(UA,url):raise ValueError('robots disallows URL')
        time.sleep(max(0,self.delay-(time.monotonic()-self.last)));self.last=time.monotonic()
        class NoRedirect(HTTPRedirectHandler):
            def redirect_request(self,*args,**kwargs):raise ValueError('Unexpected redirect; destination not requested')
        try:
            with build_opener(NoRedirect).open(Request(url,headers={'User-Agent':UA,'Accept':'text/html,text/plain'}),timeout=25) as response:
                body=response.read(5*1024*1024+1);status=response.status
                if len(body)>5*1024*1024:raise ValueError('Source body exceeds bound')
        except HTTPError as error:
            if error.code in [404,410]:return error.read(1024*1024),error.code
            raise
        if any(x in body.lower() for x in [b'cf-chl-',b'verify you are human',b'just a moment']):raise ValueError('Challenge detected; stopped')
        return body,status


def history_keys():
    with common.HISTORY.open(encoding='utf-8-sig',newline='') as stream:keys={r['record_key'] for r in csv.DictReader(stream)}
    keys.update(json.loads(x)['record_key'] for x in (common.OUT/'records.jsonl').read_text(encoding='utf8').splitlines() if x)
    return keys


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--target',type=int,default=MAX_TARGET);parser.add_argument('--delay',type=float,default=3)
    parser.add_argument('--output',type=Path,default=OUT);args=parser.parse_args()
    if not 1<=args.target<=MAX_TARGET or args.delay<3:parser.error('target 1..30; delay >=3')
    output=args.output.resolve()
    if not output.is_relative_to((BASE/'data_raw').resolve()) or output==common.OUT.resolve():parser.error('Separate raw batch required')
    output.mkdir(parents=True,exist_ok=True);lock=output/'collector.lock'
    try:fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    except FileExistsError:raise SystemExit('Collector lock exists; inspect before resuming')
    rows=[];status='not_started';error=None;started=common.now()
    try:
        keys=history_keys()
        policy=dict(source='nhadat24h',requested_target=args.target,delay=args.delay,max_page=MAX_PAGES,
            history_sha256=common.sha(common.HISTORY),pilot_sha256=common.sha(common.OUT/'records.jsonl'),
            collector_sha256=common.sha(__file__),card_parser_sha256=common.sha(source.__file__),numeric_parser_sha256=common.sha(common.cafe.__file__))
        path=output/'policy.json'
        if path.exists():
            prior=json.loads(path.read_text(encoding='utf8'))
            if {k:v for k,v in prior.items() if k!='collector_sha256'}!={k:v for k,v in policy.items() if k!='collector_sha256'}:
                raise ValueError('Batch scope/history policy changed; separate batch required')
            if prior.get('collector_sha256')!=policy['collector_sha256']:
                # A parser revision may resume only if every durable record
                # replays identically. Archive the old policy; never edit raw.
                old_log=output/'records.jsonl'
                for line in old_log.read_text(encoding='utf8').splitlines() if old_log.exists() else []:
                    saved=json.loads(line);cache=(output/saved['detail_file']).read_bytes()
                    if hashlib.sha256(cache).hexdigest()!=saved['response_sha256'] or parse_detail(cache,saved,saved['collected_at'])!=saved:
                        raise ValueError('Parser revision changes durable records; separate batch required')
                revisions=output/'policy_history';revisions.mkdir(exist_ok=True)
                common.atomic(revisions/(prior['collector_sha256']+'.json'),prior)
                common.atomic(revisions/(policy['collector_sha256']+'-replay.json'),dict(previous=prior['collector_sha256'],current=policy['collector_sha256'],all_existing_records_replayed=True,changed_at=common.now()))
        common.atomic(path,policy)
        for name in ['list_cache','detail_cache']:(output/name).mkdir(exist_ok=True)
        log=output/'records.jsonl'
        if log.exists():rows=[json.loads(x) for x in log.read_text(encoding='utf8').splitlines() if x]
        seen={r['record_key'] for r in rows}
        if len(seen)!=len(rows) or seen&keys:raise ValueError('Duplicate or historical ID in durable log')
        cp=output/'checkpoint.json'
        state=json.loads(cp.read_text(encoding='utf8')) if cp.exists() else dict(next_page=1,attempted=[],historical_skipped=0,listings_seen=0,page_signatures={})
        attempted=set(state['attempted']);page=state['next_page']
        if len(rows)>=args.target:status='target_already_reached'
        elif page>MAX_PAGES:status='page_limit'
        else:
            client=Client(output,args.delay);status='page_limit'
            while page<=MAX_PAGES:
                url=START+(f'/page{page}' if page>1 else '')
                body,http=client.fetch(url)
                if http!=200:status='listing_unavailable';break
                cards,links=listing(body,url)
                signature=hashlib.sha256('|'.join(sorted(r['record_key'] for r in cards)).encode()).hexdigest()
                if any(v==signature for k,v in state['page_signatures'].items() if k!=str(page)):raise ValueError('Repeated listing page')
                state['page_signatures'][str(page)]=signature
                (output/'list_cache'/f'page-{page}.html').write_bytes(body)
                for card in cards:
                    key=card['record_key']
                    if key in attempted or key in seen:continue
                    state['listings_seen']+=1
                    if key in keys:attempted.add(key);state['historical_skipped']+=1
                    else:
                        raw,http=client.fetch(card['detail_url'])
                        detail=output/'detail_cache'/(card['source_listing_id']+'.html');detail.write_bytes(raw)
                        if http==200:
                            record=parse_detail(raw,card,common.now());record['detail_file']=detail.relative_to(output).as_posix()
                            with log.open('a',encoding='utf8',newline='\n') as stream:
                                stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                            rows.append(record);seen.add(key)
                            print(json.dumps(dict(new=len(rows),record_key=key,flags=len(record['source_evidence_flags']))),flush=True)
                        attempted.add(key)
                    state.update(next_page=page,attempted=sorted(attempted),updated_at=common.now());common.atomic(cp,state)
                    if len(rows)>=args.target:status='target_reached';break
                if status=='target_reached':break
                if START+f'/page{page+1}' not in links:status='end_of_pages';break
                page+=1;state['next_page']=page;common.atomic(cp,state)
        if common.sha(common.HISTORY)!=policy['history_sha256'] or common.sha(common.OUT/'records.jsonl')!=policy['pilot_sha256']:raise ValueError('Historical inputs changed')
    except KeyboardInterrupt:status='interrupted';error='KeyboardInterrupt'
    except Exception as failure:status='stopped_error';error=type(failure).__name__+': '+str(failure)
    finally:
        try:
            common.export_csv(output/'apartment_records.csv',rows)
            common.atomic(output/'latest_run.json',dict(started_at=started,finished_at=common.now(),status=status,error=error,total_new=len(rows),model_changed=False))
        finally:lock.unlink()
    print(json.dumps(dict(status=status,error=error,total_new=len(rows))),flush=True)
    return 1 if status in ['interrupted','stopped_error'] else 0


if __name__=='__main__':raise SystemExit(main())
