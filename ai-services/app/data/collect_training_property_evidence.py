"""Bounded training-apartment source probe; new cache, no label/model changes."""
import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import uuid

import audit_property_evidence as audit
import collect_apartment_pilot as client_source
from market_observations import canonical, digest, persist_evidence

OUT = audit.SUPPLEMENT


def selection(count):
    parts, original, parsed, fetched, _, _, _ = audit.read_context()
    rows = []
    for row in parts['train']:
        if row['category'] != 'Căn hộ chung cư' or row['source'] != 'cafeland':
            continue
        key = row['record_key']
        body, _ = audit.admit_body(row, parsed.get(key), fetched.get(key, {}))
        if not body:
            rows.append(dict(record_key=key, source_listing_id=original[key]['source_listing_id'],
                detail_url=row['detail_url'], pipeline_group=row['pipeline_group']))
    rows.sort(key=lambda r: r['record_key'])
    hashes = {str(path): client_source.sha(path) for path in [Path(__file__), audit.PREPARED / 'manifest.json',
        audit.HISTORY / 'all_listings_after_review.csv', audit.SOURCE / 'parsed_evidence.json',
        audit.SOURCE / 'fetch_manifest.json', Path(client_source.__file__), audit.PROTOCOL]}
    return rows[:count], dict(max_records=count, delay_seconds=3, source='cafeland',
                             selection='train_apartment_missing_matching_body_sorted_by_id', input_sha256=hashes)


def publish_record(path, record):
    content = canonical(record).encode('utf8')
    temporary = path.parent / ('.pending_' + uuid.uuid4().hex)
    try:
        with temporary.open('xb') as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            if path.read_bytes() != content:
                raise ValueError('Existing observation differs; original preserved')
    finally:
        temporary.unlink(missing_ok=True)


def run(count=20, output=OUT, factory=client_source.Client):
    if not 1 <= count <= 20:
        raise ValueError('count must be 1..20')
    rows, policy = selection(count)
    if not rows:
        raise ValueError('No training-apartment source probe candidates')
    plan = dict(policy, watchlist=rows)
    output = Path(output).resolve()
    plan_path = output / 'plan.json'
    stored = json.loads(plan_path.read_text(encoding='utf8')) if plan_path.exists() else None
    if stored is not None and stored != plan:
        raise ValueError('Probe policy/selection changed; original batch preserved')
    def completed():
        result = set()
        for path in sorted((output / 'records').glob('*.json')):
            record = json.loads(path.read_text(encoding='utf8'))
            members = {r['record_key']: r for r in rows}
            key = record['record_key']
            if key not in members or record['pipeline_group'] != members[key]['pipeline_group'] or key in result:
                raise ValueError('Probe checkpoint identity/group differs')
            if client_source.sha(output / 'evidence' / (record['response_sha256'] + '.html')) != record['response_sha256']:
                raise ValueError('Probe checkpoint evidence differs')
            result.add(key)
        return result
    before = completed()
    if len(before) == len(rows):
        return dict(status='read_only_completed', records=len(before), inserted=0, error=None)
    output.mkdir(parents=True, exist_ok=True)
    lock = output / 'collector.lock'
    fd = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    os.close(fd)
    done, added, status, error = set(), 0, 'completed', None
    try:
        current_plan = json.loads(plan_path.read_text(encoding='utf8')) if plan_path.exists() else None
        if current_plan != stored or completed() != before:
            raise ValueError('Probe changed while acquiring lock')
        if not stored:
            client_source.atomic(plan_path, plan)
        done = completed()
        (output / 'records').mkdir(exist_ok=True)
        probe = output / 'invocations' / uuid.uuid4().hex
        probe.mkdir(parents=True)
        client = factory(probe, 3)
        for row in rows:
            if row['record_key'] in done:
                continue
            body, status_code = client.fetch(row['detail_url'])
            stamp = datetime.now(timezone.utc).isoformat()
            persist_evidence(output / 'evidence', body, '.html')
            record = dict(row, observed_at=stamp, response_sha256=digest(body),
                fetch=dict(requested_url=row['detail_url'], response_url=client.last_url,
                    http_status=status_code, state='downloaded' if status_code == 200 else 'not_found'),
                training_allowed=False, temporal_status='new_observation_NOT_ASOF_VERIFIED')
            publish_record(output / 'records' / ('cafeland_' + row['source_listing_id'] + '.json'), record)
            done.add(row['record_key'])
            added += 1
            print(canonical(dict(record_key=row['record_key'], records=len(done), http_status=status_code)), flush=True)
    except KeyboardInterrupt:
        status, error = 'interrupted', 'KeyboardInterrupt'
    except Exception as exc:
        status, error = 'stopped_error', type(exc).__name__ + ': ' + str(exc)
    finally:
        lock.unlink()
    result = dict(status=status, records=len(done), inserted=added, error=error)
    client_source.atomic(output / 'latest_run.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--count', type=int, default=20)
    args = parser.parse_args()
    result = run(args.count)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 1 if result['error'] else 0


if __name__ == '__main__':
    raise SystemExit(main())
