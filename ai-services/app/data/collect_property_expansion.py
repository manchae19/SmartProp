"""Bounded current snapshots: missing training descriptions and 60 new IDs."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import time
from urllib.error import HTTPError
from urllib.parse import urlparse
from urllib.request import Request, HTTPRedirectHandler, build_opener
from urllib.robotparser import RobotFileParser

import audit_property_evidence as audit
import collect_apartment_pilot as cafe
import collect_apartment_followup as nhadat
from collect_training_property_evidence import publish_record
from market_observations import canonical, digest, persist_evidence
import review_apartment_pilot as pilot

BASE = cafe.BASE
ROOT = BASE / 'data_raw/property_expansion_20261029'
PROTOCOL = BASE / 'PROPERTY_EXPANSION_PROTOCOL.md'
PRIOR = BASE / 'processed/apartment_extension_review/runs/c458ee98726ea981'
HOSTS = dict(cafeland='nhadat.cafeland.vn', nhadat24h='nhadat24h.net')
UA = 'SmartPropResearch/0.4 (+academic property data project; bounded source review)'


class SourceClient:
    def __init__(self, output, source):
        self.host = HOSTS[source]
        self.source = source
        self.last = 0
        self.delay = 3
        self.robot = None
        raw, status = self.fetch('https://' + self.host + '/robots.txt', False)
        if status != 200:
            raise ValueError('robots unavailable')
        (output / 'robots.txt').write_bytes(raw)
        self.robot = RobotFileParser()
        self.robot.parse(raw.decode('utf8').replace('\\r\\n', '\n').splitlines())
        self.delay = max(3, self.robot.crawl_delay(UA) or self.robot.crawl_delay('*') or 0)

    def validate_url(self, url):
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc != self.host or parsed.query or parsed.fragment:
            raise ValueError('Unexpected source URL')

    def fetch(self, url, check=True):
        self.validate_url(url)
        if check and not self.robot.can_fetch(UA, url):
            raise ValueError('robots disallows URL')
        owner = self
        class SameID(HTTPRedirectHandler):
            max_redirections = 3
            def redirect_request(self, request, fp, code, msg, headers, newurl):
                owner.validate_url(newurl)
                before = audit.parser.audit.sid_url(owner.source, request.full_url)
                after = audit.parser.audit.sid_url(owner.source, newurl)
                if not check or not before or before != after or not owner.robot.can_fetch(UA, newurl):
                    raise ValueError('Unexpected redirect; not requested')
                time.sleep(max(0, owner.delay - (time.monotonic() - owner.last)))
                owner.last = time.monotonic()
                return super().redirect_request(request, fp, code, msg, headers, newurl)
        time.sleep(max(0, self.delay - (time.monotonic() - self.last)))
        self.last = time.monotonic()
        try:
            with build_opener(SameID).open(Request(url, headers={'User-Agent': UA, 'Accept': 'text/html,text/plain'}), timeout=25) as response:
                raw = response.read(10 * 1024 * 1024 + 1)
                status = response.status
                self.last_url = response.url
                if len(raw) > 10 * 1024 * 1024:
                    raise ValueError('Source response too large')
        except HTTPError as exc:
            if exc.code not in [404, 410]:
                raise
            raw, status, self.last_url = exc.read(1024 * 1024), exc.code, exc.geturl()
        if any(x in raw.lower() for x in [b'cf-chl-', b'verify you are human', b'just a moment', b'<title>captcha', b'captcha verification required']):
            raise ValueError('Challenge detected; stopped')
        return raw, status


def context():
    parts, original, parsed, fetched, supplements, _, _ = audit.read_context()
    known = set(original)
    known.update(r['record_key'] for r in audit.c.read(PRIOR / 'all_decisions.csv'))
    hashes = {str(p): cafe.sha(p) for p in [Path(__file__), PROTOCOL, audit.PREPARED / 'manifest.json',
        audit.HISTORY / 'all_listings_after_review.csv', PRIOR / 'all_decisions.csv',
        audit.SOURCE / 'parsed_evidence.json', audit.SOURCE / 'fetch_manifest.json',
        Path(cafe.__file__), Path(cafe.cafe.__file__), Path(pilot.__file__), pilot.CATALOG,
        BASE / 'smartprop_geography.py', Path(publish_record.__code__.co_filename), BASE / 'market_observations.py']}
    return parts, original, parsed, fetched, supplements, known, hashes


def refresh_plan(source):
    parts, original, parsed, fetched, supplements, _, hashes = context()
    rows = []
    for row in parts['train']:
        key = row['record_key']
        if row['category'] != 'Căn hộ chung cư' or row['source'] != source or key in supplements:
            continue
        if audit.admit_body(row, parsed.get(key), fetched.get(key, {}))[0]:
            continue
        rows.append(dict(record_key=key, source=source, source_listing_id=original[key]['source_listing_id'],
            detail_url=row['detail_url'], pipeline_group=row['pipeline_group'], title=original[key]['title'],
            expected_price_million=row['price_million'], expected_area_sqm=row['area_sqm']))
    limit = dict(cafeland=11, nhadat24h=143)[source]
    if len(rows) > limit:
        raise ValueError('Missing-description queue changed')
    return dict(mode='refresh', source=source, rows=sorted(rows, key=lambda r: r['record_key']), max_records=limit,
                input_sha256=hashes, delay_seconds=3)


def verified_records(output):
    records = []
    for path in sorted((output / 'records').glob('*.json')):
        row = json.loads(path.read_text(encoding='utf8'))
        if cafe.sha(output / 'evidence' / (row['response_sha256'] + '.html')) != row['response_sha256']:
            raise ValueError('Source evidence differs')
        records.append(row)
    if len(records) != len({r['record_key'] for r in records}):
        raise ValueError('Duplicate snapshot IDs in batch')
    return records


def save_response(output, row, client, body, status):
    stamp = datetime.now(timezone.utc).isoformat()
    persist_evidence(output / 'evidence', body, '.html')
    record = dict(row, observed_at=stamp,
        response_sha256=digest(body), training_allowed=False,
        fetch=dict(requested_url=row.get('requested_detail_url', row['detail_url']), response_url=client.last_url, http_status=status,
                   state='downloaded' if status == 200 else 'not_found'))
    publish_record(output / 'records' / (row['record_key'].replace(':', '_') + '.json'), record)
    return record


def refresh(source, output=None, factory=SourceClient):
    output = Path(output or ROOT / ('refresh_' + source)).resolve()
    plan = refresh_plan(source)
    stored = json.loads((output / 'plan.json').read_text(encoding='utf8')) if (output / 'plan.json').exists() else None
    if stored is not None and stored != plan:
        raise ValueError('Refresh plan changed; preserve existing batch')
    rows = verified_records(output)
    allowed = {r['record_key'] for r in plan['rows']}
    done = {r['record_key'] for r in rows}
    if not done <= allowed:
        raise ValueError('Unexpected persisted ID')
    if done == allowed:
        return dict(status='read_only_completed', total=len(rows), error=None)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'collector.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    status, error = 'completed', None
    try:
        current_plan = json.loads((output / 'plan.json').read_text(encoding='utf8')) if (output / 'plan.json').exists() else None
        if current_plan != stored or verified_records(output) != rows:
            raise ValueError('Batch changed while acquiring lock')
        if not stored:
            cafe.atomic(output / 'plan.json', plan)
        (output / 'records').mkdir(exist_ok=True)
        invocation = output / 'invocations' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        invocation.mkdir(parents=True)
        client = factory(invocation, source)
        for row in plan['rows']:
            if row['record_key'] in done:
                continue
            body, http = client.fetch(row['detail_url'])
            record = save_response(output, row, client, body, http)
            rows.append(record); done.add(row['record_key'])
            print(canonical(dict(source=source, total=len(rows), record_key=row['record_key'], http_status=http)), flush=True)
    except KeyboardInterrupt:
        status, error = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        status, error = 'stopped_error', type(exc).__name__ + ': ' + str(exc)
    finally:
        lock.unlink()
    result = dict(status=status, total=len(rows), error=error)
    cafe.atomic(output / 'latest_run.json', result)
    return result


def new_plan():
    _, _, _, _, _, known, hashes = context()
    cp = BASE / 'data_raw/apartment_topup_40/checkpoint.json'
    start = json.loads(cp.read_text(encoding='utf8'))['next_page']
    hashes[str(cp)] = cafe.sha(cp)
    return known, dict(mode='new', source='cafeland', target=60, max_pages=16, start_page=start,
        max_per_locality=20, delay_seconds=3, known_keys_sha256=digest('|'.join(sorted(known)).encode()), input_sha256=hashes)


def collect_new(output=None, factory=SourceClient):
    output = Path(output or ROOT / 'new_cafeland_60').resolve()
    known, plan = new_plan()
    stored = json.loads((output / 'plan.json').read_text(encoding='utf8')) if (output / 'plan.json').exists() else None
    if stored is not None and stored != plan:
        raise ValueError('New batch scope changed; preserve original')
    rows = verified_records(output)
    if {r['record_key'] for r in rows} & known:
        raise ValueError('Historical ID in new batch')
    checkpoint = output / 'checkpoint.json'
    state = json.loads(checkpoint.read_text(encoding='utf8')) if checkpoint.exists() else dict(next_page=plan['start_page'], attempted=[], historical_skipped=0, quota_skipped=0, page_signatures={})
    if len(rows) >= plan['target'] or state['next_page'] >= plan['start_page'] + plan['max_pages'] or state.get('finished'):
        return dict(status='read_only_completed', total=len(rows), error=None)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'collector.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY); os.close(fd)
    status, error = 'page_limit', None
    try:
        current_plan = json.loads((output / 'plan.json').read_text(encoding='utf8')) if (output / 'plan.json').exists() else None
        if current_plan != stored or verified_records(output) != rows:
            raise ValueError('Batch changed while acquiring lock')
        if not stored:
            cafe.atomic(output / 'plan.json', plan)
        (output / 'records').mkdir(exist_ok=True)
        (output / 'list_cache').mkdir(exist_ok=True)
        invocation = output / 'invocations' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        invocation.mkdir(parents=True)
        client = factory(invocation, 'cafeland')
        seen = {r['record_key'] for r in rows}; attempted = set(state['attempted'])
        counts = Counter(r['sampling_locality'] for r in rows)
        catalog = json.loads(pilot.CATALOG.read_text(encoding='utf8'))
        for page in range(state['next_page'], plan['start_page'] + plan['max_pages']):
            url = cafe.START + f'page-{page}/'
            body, http = client.fetch(url)
            if http != 200:
                status = 'listing_unavailable'; break
            persist_evidence(output / 'list_cache', body, '.html')
            cards, links = cafe.listing_page(body, url)
            signature = digest('|'.join(sorted(r['record_key'] for r in cards)).encode())
            if any(value == signature for key, value in state['page_signatures'].items() if key != str(page)):
                raise ValueError('Repeated listing page; stopped')
            state['page_signatures'][str(page)] = signature
            for card in cards:
                key = card['record_key']
                if key in seen or key in attempted:
                    continue
                if key in known:
                    state['historical_skipped'] += 1
                else:
                    address = card['listing_address_raw']
                    locality = pilot.location(dict(address_raw=address, source_location_parts=[x.strip() for x in address.split(',')]), catalog)[0] or 'unknown'
                    if counts[locality] >= plan['max_per_locality']:
                        state['quota_skipped'] += 1
                    else:
                        detail, code = client.fetch(card['detail_url'])
                        if client.last_url != card['detail_url']:
                            card = dict(card, requested_detail_url=card['detail_url'], detail_url=client.last_url)
                        record = save_response(output, dict(card, sampling_locality=locality, listing_response_sha256=digest(body)), client, detail, code)
                        rows.append(record); seen.add(key); counts[locality] += 1
                        print(canonical(dict(new=len(rows), record_key=key, http_status=code, locality=locality)), flush=True)
                attempted.add(key)
                state.update(next_page=page, attempted=sorted(attempted))
                cafe.atomic(checkpoint, state)
                if len(rows) >= plan['target']:
                    status = 'target_reached'; break
            if status == 'target_reached':
                break
            if cafe.START + f'page-{page+1}/' not in links:
                state['finished'] = True
                status = 'end_of_pages'
                cafe.atomic(checkpoint, state); break
            state['next_page'] = page + 1
            cafe.atomic(checkpoint, state)
    except KeyboardInterrupt:
        status, error = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        status, error = 'stopped_error', type(exc).__name__ + ': ' + str(exc)
    finally:
        lock.unlink()
    result = dict(status=status, total=len(rows), error=error)
    cafe.atomic(output / 'latest_run.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['refresh', 'new'])
    parser.add_argument('--source', choices=list(HOSTS), default='cafeland')
    args = parser.parse_args()
    result = refresh(args.source) if args.mode == 'refresh' else collect_new()
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
