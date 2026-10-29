"""Bounded multi-category snapshots; historical collectors stay byte-for-byte."""
import argparse
from collections import Counter
from datetime import datetime, timezone
import json
from pathlib import Path
import re

from lxml import html
import collect_property_expansion as old
from crawler_cafeland import crawl_cafeland_danang as cafe_parser
from source_feature_io import atomic_json, writer_lock

BASE = old.BASE
OUT = BASE / 'data_raw/source_features_75_20261029'
PROTOCOL = BASE / 'SOURCE_FEATURE_TRIAL_PROTOCOL.md'
STARTS = {
    'Nhà ở': old.cafe.ORIGIN + '/nha-dat-ban/ban-nha-rieng-tai-da-nang/',
    'Đất nền': old.cafe.ORIGIN + '/nha-dat-ban/dat-nen-dat-o-dat-tho-cu-tai-da-nang/',
    'Căn hộ chung cư': old.cafe.START,
}
CATEGORIES = {'ban-nha-rieng': 'Nhà ở', 'ban-nha-pho': 'Nhà ở', 'ban-biet-thu': 'Nhà ở',
    'ban-dat': 'Đất nền', 'ban-dat-tho-cu': 'Đất nền', 'ban-dat-nen': 'Đất nền',
    'ban-dat-nen-du-an': 'Đất nền', 'ban-can-ho-chung-cu': 'Căn hộ chung cư'}


def listing_page(body, url, category):
    doc = html.fromstring(body.decode('utf8'))
    headings = ' '.join(cafe_parser.norm(x.text_content()) for x in doc.xpath('//h1'))
    token = {'Nhà ở': 'nha', 'Đất nền': 'dat', 'Căn hộ chung cư': 'can ho'}[category]
    if 'da nang' not in headings or token not in headings:
        raise ValueError('Listing scope/structure differs')
    rows = []
    seen = set()
    for card in cafe_parser.nodes(doc, 'row-item'):
        anchors = cafe_parser.nodes(card, 'realTitle')
        if not anchors:
            continue
        link = anchors[0].get('href', '')
        match = re.fullmatch(r'https://nhadat\.cafeland\.vn/[^/?]+-(\d+)\.html', link)
        if not match:
            raise ValueError('Unexpected detail URL')
        if match[1] in seen:
            continue
        seen.add(match[1])
        rows.append(dict(record_key='cafeland:' + match[1], source='cafeland', source_listing_id=match[1],
            detail_url=link, listing_title=cafe_parser.clean(anchors[0].text_content()),
            listing_price_raw=cafe_parser.value(card, 'reales-price'),
            listing_area_raw=cafe_parser.value(card, 'reales-area'),
            listing_address_raw=cafe_parser.value(card, 'info-location'), listing_page=url,
            sampling_category=category))
    if not rows:
        raise ValueError('No expected listing cards')
    return rows, set(doc.xpath('//a/@href'))


def parse_detail(body, record):
    row = old.cafe.parse_detail(body, dict(record, detail_url=record['fetch']['response_url']), record['observed_at'])
    category = CATEGORIES.get(row['source_category'], 'Chưa xác định')
    flags = [x for x in row['source_evidence_flags'] if x != 'source_category_not_apartment']
    if category != record['sampling_category']:
        flags.append('source_category_differs_from_sampling_category')
    return dict(row, category=category, source_evidence_flags=flags,
                label_basis='price_and_claims_from_same_response', training_allowed=False)


def plan_context():
    history = old.audit.HISTORY / 'all_listings_after_review.csv'
    prior = old.PRIOR / 'all_decisions.csv'
    previous = old.ROOT / 'new_cafeland_60'
    paths = [history, prior, previous / 'checkpoint.json', previous / 'plan.json', PROTOCOL,
             Path(__file__), BASE / 'source_feature_io.py', Path(old.__file__), Path(old.cafe.__file__),
             Path(old.cafe.cafe.__file__), old.pilot.CATALOG]
    known = {r['record_key'] for r in old.audit.c.read(history)}
    known.update(r['record_key'] for r in old.audit.c.read(prior))
    for p in sorted((previous / 'records').glob('*.json')):
        record = json.loads(p.read_text(encoding='utf8'))
        body = previous / 'evidence' / (record['response_sha256'] + '.html')
        if old.cafe.sha(body) != record['response_sha256']:
            raise ValueError('Previous source snapshot changed')
        known.add(record['record_key'])
        paths.extend([p, body])
    if len(known) != 8791:
        raise ValueError('Known-ID inventory differs from declared 8791')
    cp = json.loads((previous / 'checkpoint.json').read_text(encoding='utf8'))
    # The previous target may stop midway through a page; revisit that page and skip known IDs.
    starts = {'Nhà ở': 1, 'Đất nền': 1, 'Căn hộ chung cư': cp['next_page']}
    return known, dict(target_each=25, max_pages_each=12, max_per_category_locality=10,
        starts=STARTS, start_pages=starts, source='cafeland', request_delay_seconds=3,
        known_count=len(known), known_sha256=old.digest('|'.join(sorted(known)).encode()),
        input_sha256={str(p.resolve()): old.cafe.sha(p) for p in paths})


def bytes_or_none(path):
    return path.read_bytes() if path.exists() else None


def collect(output=OUT, factory=old.SourceClient, context_factory=plan_context):
    output = Path(output).resolve()
    known, plan = context_factory()
    plan_path, cp = output / 'plan.json', output / 'checkpoint.json'
    before = [bytes_or_none(p) for p in [plan_path, cp]]
    if before[0] is not None and json.loads(before[0]) != plan:
        raise ValueError('Plan changed; preserve original batch')
    rows = old.verified_records(output)
    if {r['record_key'] for r in rows} & known:
        raise ValueError('Historical ID in new batch')
    state = json.loads(before[1]) if before[1] else dict(
        next_pages=dict(plan['start_pages']), attempted=[], page_signatures={}, completed=[],
        historical_skipped=0, quota_skipped=0, unknown_locality_skipped=0)
    if set(state['completed']) == set(plan['starts']):
        return dict(status='read_only_completed', total=len(rows), error=None)
    counts = Counter(r['sampling_category'] for r in rows)
    if all(counts[c] >= plan['target_each'] for c in plan['starts']):
        return dict(status='read_only_completed', total=len(rows), error=None)
    localities = Counter((r['sampling_category'], r['sampling_locality']) for r in rows)
    seen = {r['record_key'] for r in rows}
    attempted = set(state['attempted'])
    status, error = 'completed', None
    with writer_lock(output, 'collector.lock'):
        if [bytes_or_none(p) for p in [plan_path, cp]] != before or old.verified_records(output) != rows:
            raise ValueError('Batch changed while acquiring lock; no request or write')
        if before[0] is None:
            atomic_json(plan_path, plan)
        (output / 'records').mkdir(exist_ok=True)
        (output / 'list_cache').mkdir(exist_ok=True)
        invocation = output / 'invocations' / datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        invocation.mkdir(parents=True)
        try:
            client = factory(invocation, 'cafeland')
            catalog = json.loads(old.pilot.CATALOG.read_text(encoding='utf8'))
            for category, start in plan['starts'].items():
                if category in state['completed']:
                    continue
                for page in range(state['next_pages'][category], plan['start_pages'][category] + plan['max_pages_each']):
                    if counts[category] >= plan['target_each']:
                        break
                    url = start if page == 1 else start + f'page-{page}/'
                    body, http = client.fetch(url)
                    if http != 200:
                        raise ValueError('Listing unavailable: ' + str(http))
                    old.persist_evidence(output / 'list_cache', body, '.html')
                    cards, links = listing_page(body, url, category)
                    signature = old.digest('|'.join(sorted(r['record_key'] for r in cards)).encode())
                    page_key = category + ':' + str(page)
                    if any(v == signature for k, v in state['page_signatures'].items() if k != page_key):
                        raise ValueError('Repeated listing page')
                    state['page_signatures'][page_key] = signature
                    for card in cards:
                        key = card['record_key']
                        if key in seen or key in attempted:
                            continue
                        if key in known:
                            state['historical_skipped'] += 1
                        else:
                            address = card['listing_address_raw']
                            locality = old.pilot.location(dict(address_raw=address,
                                source_location_parts=[x.strip() for x in address.split(',')]), catalog)[0]
                            if not locality:
                                state['unknown_locality_skipped'] += 1
                            elif localities[(category, locality)] >= plan['max_per_category_locality']:
                                state['quota_skipped'] += 1
                            else:
                                detail, code = client.fetch(card['detail_url'])
                                if client.last_url != card['detail_url']:
                                    card = dict(card, requested_detail_url=card['detail_url'], detail_url=client.last_url)
                                record = old.save_response(output, dict(card, sampling_locality=locality,
                                    listing_response_sha256=old.digest(body)), client, detail, code)
                                rows.append(record)
                                seen.add(key)
                                counts[category] += 1
                                localities[(category, locality)] += 1
                                if code == 200:
                                    # Preserve the raw response even if parsing fails, then stop
                                    # this invocation before fetching another card/category.
                                    parse_detail(detail, record)
                                print(old.canonical(dict(total=len(rows), category=category,
                                    count=counts[category], record_key=key, http_status=code)), flush=True)
                        attempted.add(key)
                        state['attempted'] = sorted(attempted)
                        atomic_json(cp, state)
                        if counts[category] >= plan['target_each']:
                            break
                    if counts[category] >= plan['target_each'] or start + f'page-{page+1}/' not in links:
                        break
                    state['next_pages'][category] = page + 1
                    atomic_json(cp, state)
                state['completed'].append(category)
                atomic_json(cp, state)
        except KeyboardInterrupt:
            status, error = 'interrupted', 'KeyboardInterrupt'
        except Exception as exc:
            status, error = 'stopped_error', type(exc).__name__ + ': ' + str(exc)
        result = dict(status=status, total=len(rows), category_counts=dict(counts), error=error)
        atomic_json(output / 'latest_run.json', result)
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--run', action='store_true', help='Execute the frozen bounded collection')
    args = parser.parse_args()
    result = collect() if args.run else plan_context()[1]
    print(json.dumps(result, ensure_ascii=False, indent=2))
    raise SystemExit(1 if result.get('error') else 0)
