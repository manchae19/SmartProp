"""Bounded, resumable public-listing collection. Standard library only."""
import argparse
import csv
import hashlib
import json
import math
import os
import re
import time
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parent
API = 'https://gateway.chotot.com/v1/public/ad-listing'
FIELDS = ['source','source_listing_id','source_url','collected_at','source_list_time','source_date_raw',
          'source_category_id','source_type','source_region_v2','region_name','title','property_type',
          'transaction_type','target_type','currency','price_unit','price_vnd','price_million','area_sqm',
          'district','ward','street','latitude','longitude','rooms','toilets','image_url',
          'quality_status','review_flags']

def now():
    return datetime.now(timezone.utc).isoformat()

def number(value):
    if value is None or isinstance(value, bool):
        return None
    try:
        value = float(value)
        return value if math.isfinite(value) else None
    except (ValueError, TypeError):
        return None

def normalize(item, collected):
    if str(item.get('category')) != '1020':
        return None, 'wrong_category'
    if str(item.get('region_v2')) != '3017' or item.get('region_name') != 'Đà Nẵng':
        return None, 'wrong_or_unverified_region'
    if item.get('type') != 's':
        return None, 'not_sale'
    sid = str(item.get('list_id', ''))
    if not sid.isdigit():
        return None, 'missing_id'
    price, area = number(item.get('price')), number(item.get('size'))
    lat, lon = number(item.get('latitude')), number(item.get('longitude'))
    flags = []
    if price is None or price <= 0:
        flags.append('missing_or_invalid_price')
    elif not 100_000_000 <= price <= 200_000_000_000:
        flags.append('price_outside_review_range')
    if area is None or area <= 0:
        flags.append('missing_or_invalid_area')
    elif not 10 <= area <= 5000:
        flags.append('area_outside_review_range')
    if (lat is not None and not -90 <= lat <= 90) or (lon is not None and not -180 <= lon <= 180):
        flags.append('invalid_coordinates')
        lat, lon = None, None
    if lat is None or lon is None or (lat == 0 and lon == 0):
        flags.append('missing_coordinates')
        lat, lon = None, None
    # Timestamp is listing/update time supplied by source, not a transaction date.
    stamp = number(item.get('list_time'))
    try:
        stamp = datetime.fromtimestamp(stamp / 1000, timezone.utc).isoformat() if stamp else None
    except (ValueError, OverflowError, OSError):
        stamp = None
    record = dict(zip(FIELDS, [None] * len(FIELDS)))
    record.update(source='chotot', source_listing_id=sid, source_url=f'https://nha.chotot.com/{sid}.htm',
        collected_at=collected, source_list_time=stamp, source_date_raw=item.get('date'),
        source_category_id=item.get('category'), source_type=item.get('type'), source_region_v2=item.get('region_v2'),
        region_name=item.get('region_name'), title=item.get('subject'), property_type='house',
        transaction_type='sale', target_type='asking_price', currency='VND', price_unit='total',
        price_vnd=price, price_million=price / 1_000_000 if price is not None else None,
        area_sqm=area, district=item.get('area_name'), ward=item.get('ward_name'), street=item.get('street_name'),
        latitude=lat, longitude=lon, rooms=number(item.get('rooms')), toilets=number(item.get('toilets')),
        image_url=item.get('image'), quality_status='review' if flags else 'candidate', review_flags=flags)
    return record, None

def atomic_json(path, data):
    tmp = path.with_suffix(path.suffix + '.tmp')
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')
    os.replace(tmp, path)

def read_existing(paths):
    seen, inventory = set(), []
    for path in paths:
        count = 0
        with path.open(encoding='utf-8-sig', newline='') as f:
            for row in csv.DictReader(f):
                count += 1
                sid = row.get('list_id') or row.get('source_listing_id')
                if not sid:
                    match = re.search(r'/([0-9]+)\.htm(?:\?.*)?$', row.get('detail_url') or row.get('source_url') or '')
                    sid = match.group(1) if match else None
                if sid:
                    seen.add(str(sid))
        inventory.append({'path':str(path), 'rows':count,'sha256':hashlib.sha256(path.read_bytes()).hexdigest()})
    return seen, inventory

def fetch(params):
    url = API + '?' + urlencode(params)
    for attempt in range(3):
        try:
            with urlopen(Request(url, headers={'User-Agent':'SmartProp-Research/1.0', 'Accept':'application/json'}), timeout=25) as r:
                data = json.load(r)
            if not isinstance(data, dict) or not isinstance(data.get('ads'), list):
                raise ValueError('Unexpected response schema; stopped')
            return data
        except HTTPError as e:
            if e.code in (401,403,429) or attempt == 2:
                raise
            if e.code < 500:
                raise
        except (URLError, TimeoutError):
            if attempt == 2:
                raise
        time.sleep(2 ** (attempt + 1))

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--max-new', type=int, default=100)
    parser.add_argument('--max-pages', type=int, default=10)
    parser.add_argument('--delay', type=float, default=2)
    parser.add_argument('--restart', action='store_true', help='Scan newest listings; keep dedup history')
    parser.add_argument('--output', type=Path, default=ROOT/'data_raw'/'chotot_incremental')
    args = parser.parse_args()
    if not (1 <= args.max_new <= 1000 and 1 <= args.max_pages <= 100 and args.delay >= 2):
        parser.error('max-new 1..1000, max-pages 1..100, delay >= 2 seconds')
    out = args.output.resolve(); out.mkdir(parents=True, exist_ok=True)
    lock = out/'collector.lock'
    try:
        fd = os.open(lock, os.O_CREAT|os.O_EXCL|os.O_WRONLY)
    except FileExistsError:
        raise SystemExit('Collector lock exists. Verify no active process before removing stale lock.')
    os.close(fd)
    try:
        run(args, out)
    finally:
        lock.unlink()

def run(args, out):
    started = now()
    seen, inventory = read_existing(sorted(ROOT.glob('danang_chotot*.csv')))
    old_count = len(seen)
    log = out/'records.jsonl'; checkpoint = out/'checkpoint.json'
    records = []
    if log.exists():
        with log.open(encoding='utf-8') as f:
            for line in f:
                # Fail closed on a truncated log, rather than silently losing records.
                record = json.loads(line); records.append(record); seen.add(record['source_listing_id'])
    offset = 0
    if checkpoint.exists() and not args.restart:
        state = json.loads(checkpoint.read_text(encoding='utf-8'))
        if state.get('query') != {'region_v2':3017,'cg':1020,'st':'s'}:
            raise ValueError('Checkpoint query mismatch')
        offset = state['next_offset']
    count = 0; pages = 0; duplicates = 0; rejected = Counter(); fingerprints = set(); status = 'page_limit'; error = None
    try:
        for page in range(args.max_pages):
            data = fetch({'region_v2':3017,'cg':1020,'st':'s','limit':50,'o':offset,'w':1})
            ads = data['ads']; pages += 1
            if not ads:
                status = 'source_exhausted'; break
            fingerprint = tuple(str(a.get('list_id')) for a in ads)
            if fingerprint in fingerprints:
                status = 'repeated_page'; break
            fingerprints.add(fingerprint)
            partial = False
            with log.open('a', encoding='utf-8', newline='\n') as f:
                for item in ads:
                    if str(item.get('list_id')) in seen:
                        duplicates += 1; continue
                    record, reason = normalize(item, now())
                    if reason:
                        rejected[reason] += 1; continue
                    # Keep original selected fields for unit/normalization review; no seller phone/account data.
                    record['source_values'] = {k:item.get(k) for k in ['price','size','latitude','longitude','rooms','toilets','list_time']}
                    f.write(json.dumps(record, ensure_ascii=False)+'\n'); f.flush(); os.fsync(f.fileno())
                    records.append(record); seen.add(record['source_listing_id']); count += 1
                    if count >= args.max_new:
                        partial = True; status = 'new_limit'; break
            if not partial:
                offset += 50
            atomic_json(checkpoint, {'query':{'region_v2':3017,'cg':1020,'st':'s'},'next_offset':offset,'updated_at':now()})
            print(json.dumps({'pages':pages,'new':count,'duplicate_skips':duplicates,'next_offset':offset}), flush=True)
            if partial:
                break
            time.sleep(args.delay)
    except (HTTPError, URLError, TimeoutError, ValueError, OSError) as e:
        status = 'stopped_error'; error = str(e)
    tmp = out/'records.csv.tmp'
    with tmp.open('w',encoding='utf-8-sig',newline='') as f:
        writer = csv.DictWriter(f, fieldnames=FIELDS, extrasaction='ignore'); writer.writeheader()
        for record in records:
            writer.writerow({**record, 'review_flags':';'.join(record['review_flags'])})
    os.replace(tmp,out/'records.csv')
    summary = {'started_at':started,'finished_at':now(),'status':status,'error':error,'new_records':count,
        'incremental_total':len(records),'existing_unique_ids':old_count,'duplicate_skips':duplicates,
        'pages_requested_successfully':pages,'scope_rejections':dict(rejected),'next_offset':offset,
        'quality_counts':dict(Counter(r['quality_status'] for r in records)),
        'district_counts':dict(Counter(r['district'] for r in records)),
        'missing_fields':{k:sum(r.get(k) is None or r.get(k)=='' for r in records) for k in ['price_vnd','area_sqm','rooms','toilets','latitude','ward']},
        'prior_files':inventory,'query':{'region_v2':3017,'cg':1020,'st':'s'},
        'limitations':['Unique source listing IDs are not unique properties.',
            'Candidate does not mean manually verified or training-ready.',
            'Current listing timestamps are not historical transaction dates.',
            'Pagination may shift while collecting; restart periodically with ID dedup.',
            'Source data use/redistribution terms must be assessed before dataset release.']}
    atomic_json(out/'latest_run.json',summary)
    atomic_json(out/('run_'+started.replace(':','-')+'.json'),summary)
    print(json.dumps(summary,ensure_ascii=True,indent=2),flush=True)
    if error:
        raise SystemExit(1)

if __name__ == '__main__':
    main()

