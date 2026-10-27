"""Resume public-detail evidence collection for the frozen 4,383-row review queue."""
import argparse
import hashlib
import json
import threading
import time
from collections import Counter, defaultdict
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from audit_all_collected import BASE, HOSTS, read, save_csv

UA = 'SmartPropResearch/0.1'
ROOT = BASE/'processed/collection_source_review'
QUEUE = BASE/'processed/pending_collection_review/runs/f2c874320c574bb1/source_check_queue.csv'
PRINT_LOCK = threading.Lock()
STOP = threading.Event()


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def now():
    return datetime.now(timezone.utc).isoformat()


def atomic(path, value):
    temp = path.with_suffix('.tmp')
    temp.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')
    for attempt in range(10):
        try:
            temp.replace(path)
            return
        except PermissionError:
            if attempt == 9:
                raise
            time.sleep(.2)


def log(message):
    with PRINT_LOCK:
        print(message, flush=True)


def imported_cache():
    entries = {}
    for relative in ('apartment_review', 'training_source_review', 'pending_collection_review/source_access'):
        directory = BASE/'processed'/relative
        path = directory/'fetch_manifest.json'
        if path.exists():
            for key, meta in json.loads(path.read_text(encoding='utf-8')).items():
                if meta.get('file') and meta.get('http_status') in (200, 404, 410):
                    file = directory/'detail_cache'/meta['file']
                    if file.exists() and sha(file) == meta.get('sha256'):
                        entries[key] = (file, meta)
    return entries


def host_worker(source, rows, output, imported, delay):
    checkpoint = output/(source+'_checkpoint.json')
    state = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.exists() else {}
    cache = output/'detail_cache'
    for row in rows:
        key = row['record_key']
        if key not in state and key in imported:
            file, original = imported[key]
            if original.get('requested_url') != row['detail_url']:
                continue
            name = key.replace(':', '_')+'.html'
            (cache/name).write_bytes(file.read_bytes())
            state[key] = dict(original, file=name, state='cached' if original['http_status']==200 else 'unavailable',
                              reused_from=file.relative_to(BASE).as_posix(), probe_only=False)
    atomic(checkpoint, state)
    pending = [r for r in rows if r['record_key'] not in state or state[r['record_key']].get('state')=='network_error']
    if not pending:
        log(f'{source}: complete, {len(state)}/{len(rows)} checkpoint entries')
        return state
    # Do not repeat the access-block probe for every Chotot ID.
    if source == 'chotot':
        probe = BASE/'processed/pending_collection_review/source_access/fetch_manifest.json'
        known = json.loads(probe.read_text(encoding='utf-8')) if probe.exists() else {}
        blocked = next((m for k,m in known.items() if k.startswith('chotot:') and m.get('state')=='blocked'), None)
        if not blocked:
            raise RuntimeError('Chotot needs a separate source-access assessment')
        for row in pending:
            state[row['record_key']] = dict(state='not_requested_source_access_blocked',
                 requested_url=row['detail_url'], reason='One source-access probe returned HTTP 403; this URL was not requested.',
                 probe_url=blocked['requested_url'], fetched_at_utc='', http_status=None)
        atomic(checkpoint, state)
        log(f'chotot: {len(rows)} rows retained for review; no individual URL verification claimed')
        return state
    session = requests.Session()
    session.headers['User-Agent'] = UA
    host = urlparse(pending[0]['detail_url']).hostname
    try:
        response = session.get('https://'+host+'/robots.txt', timeout=30)
        if response.status_code not in (200, 404):
            raise RuntimeError(f'{source}: robots HTTP {response.status_code}')
        (output/(source+'_robots.txt')).write_bytes(response.content)
        robot = RobotFileParser()
        robot.parse(response.text.replace('\\r\\n', '\n').splitlines() if response.status_code==200 else [])
        wait = max(delay, robot.crawl_delay(UA) or robot.crawl_delay('*') or 0)
    except requests.RequestException as error:
        raise RuntimeError(f'{source}: network error: {error}') from error
    last = 0
    blocked = False
    for row in pending:
        if STOP.is_set():
            break
        key, url = row['record_key'], row['detail_url']
        if urlparse(url).hostname not in HOSTS[source] or urlparse(url).scheme != 'https':
            raise ValueError('Unexpected review URL: '+key)
        if blocked:
            state[key] = dict(state='not_requested_host_blocked', requested_url=url, fetched_at_utc='', http_status=None)
        elif not robot.can_fetch(UA, url):
            state[key] = dict(state='robots_disallowed', requested_url=url, fetched_at_utc='', http_status=None)
        else:
            if STOP.wait(max(0, wait-(time.monotonic()-last))):
                break
            last = time.monotonic()
            meta = dict(requested_url=url, fetched_at_utc=now(), probe_only=False)
            try:
                response = session.get(url, timeout=45)
                meta.update(http_status=response.status_code, response_url=response.url)
                blocked = (response.status_code in (403,429) or any(s in response.content[:50000].lower()
                           for s in (b'cf-chl-', b'captcha', b'access denied')))
                meta['state'] = ('blocked' if blocked else 'downloaded' if response.status_code==200 else
                                 'unavailable' if response.status_code in (404,410) else 'unexpected_http_status')
                name = key.replace(':', '_')+'.html'
                (cache/name).write_bytes(response.content)
                meta.update(file=name, sha256=hashlib.sha256(response.content).hexdigest())
            except requests.RequestException as error:
                meta.update(state='network_error', error=str(error)[:1200])
                blocked = True
            state[key] = meta
        atomic(checkpoint, state)
        if len(state)%10 == 0 or state[key]['state'] not in ('downloaded', 'cached'):
            log(f'{source}: {len(state)}/{len(rows)}; {key}: {state[key]["state"]}')
    session.close()
    return state


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--queue', type=Path, default=QUEUE)
    parser.add_argument('--output-dir', type=Path, default=ROOT)
    parser.add_argument('--delay', type=float, default=3)
    args = parser.parse_args()
    output = args.output_dir
    finalized=output/'review_manifest.json'
    if finalized.exists():
        saved=json.loads(finalized.read_text(encoding='utf-8'))
        prior_input=json.loads((output/'input_manifest.json').read_text(encoding='utf-8'))
        if prior_input['queue_sha256']!=sha(args.queue):
            raise RuntimeError('Queue changed; use a new output directory')
        for relative,expected in saved['output_sha256'].items():
            if sha(BASE/relative)!=expected:
                raise RuntimeError('Frozen review evidence changed: '+relative)
        log('Source review already finalized; evidence hashes verified, no network requests.')
        return
    output.mkdir(parents=True, exist_ok=True)
    (output/'detail_cache').mkdir(exist_ok=True)
    rows = read(args.queue)
    if len(rows) != len({r['record_key'] for r in rows}):
        raise ValueError('Duplicate review IDs')
    input_path = output/'input_manifest.json'
    if input_path.exists():
        frozen = json.loads(input_path.read_text(encoding='utf-8'))
        if frozen['queue_sha256'] != sha(args.queue):
            raise RuntimeError('Queue changed; use a new output directory')
    else:
        from filter_all_collected import raw_paths
        protected = [BASE/'processed'/name for name in (
            'training_v1/test.csv','training_v2/train.csv','training_v2/validation.csv','training_v2/test.csv',
            'apartment_v2/review_decisions.csv','training_source_review/review_decisions.csv')]
        frozen = dict(queue=args.queue.relative_to(BASE).as_posix(), queue_sha256=sha(args.queue),
                      queued_records=len(rows), created_at_utc=now(),
                      protected_sha256={p.relative_to(BASE).as_posix():sha(p) for p in raw_paths()+protected})
        atomic(input_path, frozen)
    if not (output/'queue.csv').exists():
        save_csv(output/'queue.csv', rows, list(rows[0]))
    by_source = defaultdict(list)
    priority = {'category_needs_source':0, 'price_or_area_unresolved':1,
                'financial_or_multiple_asset_context':2, 'duplicate_group_needs_review':3}
    for row in sorted(rows,key=lambda r:(priority.get(r['review_outcome'],4), r['record_key'])):
        by_source[row['source']].append(row)
    imported = imported_cache()
    results, failures = {}, []
    with ThreadPoolExecutor(max_workers=4) as pool:
        futures = {pool.submit(host_worker, source, subset, output, imported, max(2,args.delay)):source
                   for source, subset in by_source.items()}
        try:
            for future in as_completed(futures):
                source = futures[future]
                try:
                    results.update(future.result())
                except Exception as error:
                    failures.append(str(error))
                    log(str(error))
        except KeyboardInterrupt:
            STOP.set()
            raise
    atomic(output/'fetch_manifest.json', results)
    assert all(sha(BASE/path)==h for path,h in frozen['protected_sha256'].items())
    stats = dict(queued=len(rows), checkpoint_entries=len(results),
                 states=dict(Counter(m['state'] for m in results.values())), failures=failures,
                 protected_inputs_unchanged=True, completed_at_utc=now())
    atomic(output/'fetch_summary.json', stats)
    log(json.dumps(stats, ensure_ascii=False))
    if failures:
        raise RuntimeError('Source collection failed: '+'; '.join(failures))


if __name__ == '__main__':
    main()
