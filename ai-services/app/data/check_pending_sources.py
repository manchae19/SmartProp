"""Probe public source availability for the pending review; checkpoint every request."""
import argparse
import hashlib
import json
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import requests
from audit_all_collected import read, HOSTS

UA = 'SmartPropResearch/0.1'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True)
    parser.add_argument('--output-dir', type=Path, required=True)
    args = parser.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    cache = args.output_dir/'detail_cache'
    cache.mkdir(exist_ok=True)
    path = args.output_dir/'fetch_manifest.json'
    state = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {}
    session = requests.Session()
    session.headers['User-Agent'] = UA
    selected = {}
    for row in read(args.input):
        if row['source'] not in selected:
            selected[row['source']] = row
    errors = []
    for source, row in sorted(selected.items()):
        key, url = row['record_key'], row['detail_url']
        if key in state:
            print(key+': existing probe', flush=True)
            continue
        host = urlparse(url).hostname
        if host not in HOSTS[source] or urlparse(url).scheme != 'https':
            raise ValueError('Unexpected source URL')
        entry = dict(requested_url=url, fetched_at_utc=datetime.now(timezone.utc).isoformat(),
                     probe_only=True)
        try:
            robot_response = session.get('https://'+host+'/robots.txt', timeout=30)
            entry['robots_http_status'] = robot_response.status_code
            (args.output_dir/(host+'_robots.txt')).write_bytes(robot_response.content)
            if robot_response.status_code not in (200, 404):
                entry['state'] = 'robots_unavailable'
            else:
                robot = RobotFileParser()
                robot.parse(robot_response.text.replace('\\r\\n', '\n').splitlines()
                            if robot_response.status_code == 200 else [])
                if not robot.can_fetch(UA, url):
                    entry['state'] = 'robots_disallowed'
                else:
                    time.sleep(max(3, robot.crawl_delay(UA) or robot.crawl_delay('*') or 0))
                    response = session.get(url, timeout=45)
                    entry.update(http_status=response.status_code, response_url=response.url)
                    challenge = any(s in response.content[:50000].lower()
                                    for s in (b'cf-chl-', b'captcha', b'access denied'))
                    entry['state'] = ('blocked' if response.status_code in (403, 429) or challenge else
                                      'unavailable' if response.status_code in (404, 410) else
                                      'downloaded_not_identity_verified' if response.status_code == 200 else
                                      'unexpected_http_status')
                    file = key.replace(':', '_')+'.html'
                    (cache/file).write_bytes(response.content)
                    entry.update(file=file, sha256=hashlib.sha256(response.content).hexdigest())
        except requests.RequestException as error:
            entry.update(state='network_error', error=str(error)[:1000])
            errors.append(str(error))
        state[key] = entry
        tmp = path.with_suffix('.tmp')
        tmp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        tmp.replace(path)
        print(key+': '+entry['state'], flush=True)
    # Permit a rerun after a restricted-network failure without treating failures as successes.
    if errors:
        for key in list(state):
            if state[key]['state'] == 'network_error':
                del state[key]
        path.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding='utf-8')
        raise RuntimeError('Source probe network failed: '+errors[0])


if __name__ == '__main__':
    main()
