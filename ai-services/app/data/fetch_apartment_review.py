"""Cache public detail pages for apartment audit; resume by record key."""
import argparse
import csv
import hashlib
import json
import time
from datetime import datetime, timezone
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from pathlib import Path
import requests
from prepare_smartprop_dataset import BASE, CATEGORIES

OUT = BASE / 'processed/apartment_review'
CACHE = OUT / 'detail_cache'
UA = 'SmartPropResearch/0.1'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--ids', nargs='*')
    parser.add_argument('--max-new', type=int, default=1000)
    parser.add_argument('--queue-files', nargs='+', type=Path,
                        help='Explicit review CSVs for the frozen training-v1 dataset')
    parser.add_argument('--output-dir', type=Path, default=OUT)
    args = parser.parse_args()
    output=args.output_dir
    cache=output/'detail_cache'
    source=BASE/('processed/training_v1/main_dataset.csv' if args.queue_files else 'processed/smartprop_review/baseline_inputs.csv')
    with source.open(encoding='utf-8-sig', newline='') as stream:
        rows = list(csv.DictReader(stream))
    if args.queue_files:
        keys=set()
        for path in args.queue_files:
            with path.open(encoding='utf-8-sig',newline='') as stream:
                keys.update(r['record_key'] for r in csv.DictReader(stream))
        rows=[r for r in rows if r['record_key'] in keys]
        if {r['record_key'] for r in rows}!=keys:
            raise ValueError('Review queue contains IDs outside frozen training-v1 dataset')
    else:
        rows = [r for r in rows if r['category'] == CATEGORIES[2]]
    if args.ids:
        rows = [r for r in rows if r['record_key'] in args.ids]
    elif not args.queue_files:
        with (OUT/'needs_review.csv').open(encoding='utf-8-sig', newline='') as stream:
            queue = list(csv.DictReader(stream))
        keys = {r['record_key'] for r in queue}
        rows = [r for r in rows if r['record_key'] in keys]
    cache.mkdir(parents=True, exist_ok=True)
    manifest = output/'fetch_manifest.json'
    state = json.loads(manifest.read_text(encoding='utf-8')) if manifest.exists() else {}
    session = requests.Session()
    session.headers['User-Agent'] = UA
    robots, last = {}, 0
    added = 0
    for row in rows:
        key, url = row['record_key'], row['detail_url']
        if key in state:
            continue
        host = urlparse(url).hostname
        if host not in ['nhadat24h.net', 'nhadat.cafeland.vn'] or urlparse(url).scheme != 'https':
            raise ValueError('Unexpected detail host')
        if host not in robots:
            response = session.get(f'https://{host}/robots.txt', timeout=30)
            response.raise_for_status()
            robot = RobotFileParser()
            robot.parse(response.text.replace('\\r\\n', '\n').splitlines())
            robots[host] = robot
            (cache/f'{host}_robots.txt').write_bytes(response.content)
        robot = robots[host]
        if not robot.can_fetch(UA, url):
            raise ValueError(f'robots.txt disallows {key}')
        time.sleep(max(0, max(3, robot.crawl_delay(UA) or robot.crawl_delay('*') or 0)-(time.monotonic()-last)))
        last = time.monotonic()
        response = session.get(url, timeout=45)
        if response.status_code in [403, 429] or any(x in response.content[:50000].lower() for x in [b'cf-chl-', b'captcha', b'access denied']):
            raise RuntimeError(f'Challenge or block for {key}; stopped without bypass.')
        if response.status_code not in [200,404,410]:
            response.raise_for_status()
        path = cache/(key.replace(':','_')+'.html')
        path.write_bytes(response.content)
        state[key] = dict(requested_url=url, response_url=response.url, http_status=response.status_code,
            fetched_at_utc=datetime.now(timezone.utc).isoformat(), file=path.name,
            sha256=hashlib.sha256(response.content).hexdigest())
        temporary = manifest.with_suffix('.tmp')
        temporary.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        for attempt in range(10):
            try:
                temporary.replace(manifest)
                break
            except PermissionError:
                if attempt == 9:
                    raise
                time.sleep(min(.2*(attempt+1), 1))
        added += 1
        print(f'{key}: HTTP {response.status_code} ({added} new)', flush=True)
        if added >= args.max_new:
            break
    print(f'Cached {added} new detail pages; raw listings unchanged.', flush=True)

if __name__ == '__main__':
    main()
