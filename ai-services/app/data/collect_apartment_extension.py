"""Safe, bounded CafeLand extension; archived batches are read-only."""
import argparse
import hashlib
import json
import os
from pathlib import Path

import collect_apartment_pilot as source
import collect_apartment_followup as nhadat
import review_apartment_followup as previous

OUT=source.BASE/'data_raw/apartment_extension_80'
TARGET=80
PAGES=8


def load_rows(output):
    path=output/'records.jsonl'
    return [json.loads(x) for x in path.read_text(encoding='utf8').splitlines() if x] if path.exists() else []


def baseline():
    rows=source.HISTORY
    keys=nhadat.history_keys()
    keys.update(r['record_key'] for r in load_rows(nhadat.OUT))
    checkpoint=json.loads((source.OUT/'checkpoint.json').read_text(encoding='utf8'))
    policy=dict(target=TARGET,max_pages_total=PAGES,start_page=checkpoint['next_page'],delay_seconds=3,
        historical_ids=len(keys),historical_keys_sha256=hashlib.sha256('|'.join(sorted(keys)).encode()).hexdigest(),
        historical_snapshot_sha256=source.sha(rows),pilot_log_sha256=source.sha(source.OUT/'records.jsonl'),
        nhadat_log_sha256=source.sha(nhadat.OUT/'records.jsonl'),collector_sha256=source.sha(__file__),
        parser_sha256=source.sha(source.__file__),previous_review_sha256=source.sha(previous.OUT/'runs/1bb003196b4b5b94/manifest.json'))
    return keys,policy


def run(output=OUT):
    output=Path(output).resolve();keys,policy=baseline()
    def snapshot():
        return {name:source.sha(output/name) if (output/name).exists() else None for name in ['policy.json','records.jsonl','checkpoint.json']}
    before=snapshot()
    existing=output/'policy.json'
    # Refusal and completed resume must not change any batch bytes.
    stored=json.loads(existing.read_text(encoding='utf8')) if existing.exists() else None
    if stored and {k:v for k,v in stored.items() if k!='collector_sha256'}!={k:v for k,v in policy.items() if k!='collector_sha256'}:
        raise ValueError('Policy changed; use a separately versioned batch. Existing batch not modified.')
    rows=load_rows(output);seen={r['record_key'] for r in rows}
    if len(rows)!=len(seen) or seen&keys:raise ValueError('Duplicate/historical persisted IDs')
    cp=output/'checkpoint.json'
    state=json.loads(cp.read_text(encoding='utf8')) if cp.exists() else dict(next_page=policy['start_page'],attempted=[],historical_skipped=0)
    last_page=policy['start_page']+PAGES-1
    if len(rows)>=TARGET or state['next_page']>last_page:
        print(json.dumps(dict(status='read_only_completed',total_new=len(rows))));return 0
    if stored and stored!=policy:raise ValueError('Collector version changed on incomplete batch; use a separately versioned batch')
    output.mkdir(parents=True,exist_ok=True);lock=output/'collector.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        if snapshot()!=before:
            raise ValueError('Batch changed while acquiring lock; no export or metadata write performed')
    except BaseException:
        lock.unlink()
        raise
    status='page_limit';error=None;started=source.now()
    try:
        source.atomic(existing,policy)
        for name in ['detail_cache','list_cache']:(output/name).mkdir(exist_ok=True)
        client=source.Client(output,3);attempted=set(state['attempted'])
        for page in range(state['next_page'],last_page+1):
            url=source.START if page==1 else source.START+f'page-{page}/'
            body,http=client.fetch(url)
            if http!=200:status='listing_unavailable';break
            cards,links=source.listing_page(body,url)
            (output/'list_cache'/f'page-{page}.html').write_bytes(body)
            for card in cards:
                key=card['record_key']
                if key in attempted or key in seen:continue
                if key in keys:attempted.add(key);state['historical_skipped']+=1
                else:
                    raw,http=client.fetch(card['detail_url'])
                    path=output/'detail_cache'/(card['source_listing_id']+'.html');path.write_bytes(raw)
                    if http==200:
                        if client.last_url!=card['detail_url']:card=dict(card,requested_detail_url=card['detail_url'],detail_url=client.last_url)
                        record=source.parse_detail(raw,card,source.now());record['detail_file']=path.relative_to(output).as_posix()
                        with (output/'records.jsonl').open('a',encoding='utf8',newline='\n') as stream:
                            stream.write(json.dumps(record,ensure_ascii=False)+'\n');stream.flush();os.fsync(stream.fileno())
                        rows.append(record);seen.add(key)
                        print(json.dumps(dict(new=len(rows),record_key=key,flags=len(record['source_evidence_flags']))),flush=True)
                    attempted.add(key)
                state.update(next_page=page,attempted=sorted(attempted));source.atomic(cp,state)
                if len(rows)>=TARGET:status='target_reached';break
            if status=='target_reached':break
            if source.START+f'page-{page+1}/' not in links:status='end_of_pages';break
            state['next_page']=page+1;source.atomic(cp,state)
        if baseline()[1]!=policy:raise ValueError('Baseline changed during collection')
    except KeyboardInterrupt:status='interrupted';error='KeyboardInterrupt'
    except Exception as failure:status='stopped_error';error=type(failure).__name__+': '+str(failure)
    finally:
        try:
            source.export_csv(output/'apartment_records.csv',rows)
            run=dict(started_at=started,finished_at=source.now(),status=status,error=error,total_new=len(rows),model_changed=False)
            runs=output/'invocations';runs.mkdir(exist_ok=True)
            source.atomic(runs/(started.replace(':','-')+'.json'),run)
            source.atomic(output/'latest_run.json',run)
        finally:lock.unlink()
    print(json.dumps(dict(status=status,total_new=len(rows),error=error)),flush=True)
    return 1 if error else 0


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--status',choices=['pilot','nhadat','extension'])
    args=parser.parse_args()
    if args.status:
        output={'pilot':source.OUT,'nhadat':nhadat.OUT,'extension':OUT}[args.status]
        print((output/'latest_run.json').read_text(encoding='utf8'));return 0
    return run()


if __name__=='__main__':raise SystemExit(main())
