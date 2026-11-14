"""Separate bounded top-up after the 80-record batch; all old batches read-only."""
import json
import collect_apartment_extension as runner

OUT=runner.source.BASE/'data_raw/apartment_topup_40'
BASELINE=runner.baseline


def baseline():
    keys,previous=BASELINE()
    keys.update(r['record_key'] for r in runner.load_rows(runner.OUT))
    checkpoint=json.loads((runner.OUT/'checkpoint.json').read_text(encoding='utf8'))
    policy=dict(previous,target=40,max_pages_total=4,start_page=checkpoint['next_page'],historical_ids=len(keys),
        historical_keys_sha256=runner.hashlib.sha256('|'.join(sorted(keys)).encode()).hexdigest(),
        extension_log_sha256=runner.source.sha(runner.OUT/'records.jsonl'),
        collector_sha256=runner.source.sha(__file__),runner_sha256=runner.source.sha(runner.__file__))
    return keys,policy


def main():
    # Process-local configuration of the reviewed lifecycle; no frozen file edits.
    runner.TARGET=40;runner.PAGES=4;runner.baseline=baseline
    return runner.run(OUT)


if __name__=='__main__':raise SystemExit(main())
