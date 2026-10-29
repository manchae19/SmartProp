"""Checkpoint-safe entry point; preserve the collector used for archived data."""
from collections import Counter
from datetime import datetime, timezone
import json
import os
from pathlib import Path

import collect_property_expansion as old


def state_bytes(path):
    return path.read_bytes() if path.exists() else None


def collect_new(output=None, factory=old.SourceClient):
    output = Path(output or old.ROOT/'new_cafeland_60').resolve()
    known, plan = old.new_plan()
    plan_path, checkpoint = output/'plan.json', output/'checkpoint.json'
    before_plan, before_checkpoint = state_bytes(plan_path), state_bytes(checkpoint)
    stored = json.loads(before_plan) if before_plan is not None else None
    if stored is not None and stored != plan:raise ValueError('New batch scope changed; original preserved')
    rows = old.verified_records(output)
    if {r['record_key'] for r in rows} & known:raise ValueError('Historical ID in new batch')
    state = json.loads(before_checkpoint) if before_checkpoint is not None else dict(next_page=plan['start_page'],
        attempted=[],historical_skipped=0,quota_skipped=0,page_signatures={})
    if len(rows)>=plan['target'] or state['next_page']>=plan['start_page']+plan['max_pages'] or state.get('finished'):
        return dict(status='read_only_completed',total=len(rows),error=None)
    output.mkdir(parents=True,exist_ok=True)
    lock=output/'collector.lock'
    fd=os.open(lock,os.O_CREAT|os.O_EXCL|os.O_WRONLY);os.close(fd)
    try:
        if (state_bytes(plan_path)!=before_plan or state_bytes(checkpoint)!=before_checkpoint or
                old.verified_records(output)!=rows):
            raise ValueError('Batch/checkpoint changed while acquiring lock; no request or metadata write')
    except BaseException:
        lock.unlink();raise
    status,error='page_limit',None
    try:
        if not stored:old.cafe.atomic(plan_path,plan)
        (output/'records').mkdir(exist_ok=True);(output/'list_cache').mkdir(exist_ok=True)
        invocation=output/'invocations'/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%f')
        invocation.mkdir(parents=True)
        controller_sha=old.cafe.sha(Path(__file__))
        old.cafe.atomic(invocation/'controller.json',dict(version=2,controller_sha256=controller_sha,
            core_sha256=old.cafe.sha(old.__file__),plan_sha256=old.cafe.sha(plan_path)))
        client=factory(invocation,'cafeland')
        seen={r['record_key'] for r in rows};attempted=set(state['attempted'])
        counts=Counter(r['sampling_locality'] for r in rows)
        catalog=json.loads(old.pilot.CATALOG.read_text(encoding='utf8'))
        for page in range(state['next_page'],plan['start_page']+plan['max_pages']):
            url=old.cafe.START+f'page-{page}/'
            body,http=client.fetch(url)
            if http!=200:status='listing_unavailable';break
            old.persist_evidence(output/'list_cache',body,'.html')
            cards,links=old.cafe.listing_page(body,url)
            signature=old.digest('|'.join(sorted(r['record_key'] for r in cards)).encode())
            if any(v==signature for k,v in state['page_signatures'].items() if k!=str(page)):
                raise ValueError('Repeated listing page; stopped')
            state['page_signatures'][str(page)]=signature
            for card in cards:
                key=card['record_key']
                if key in seen or key in attempted:continue
                if key in known:state['historical_skipped']+=1
                else:
                    address=card['listing_address_raw']
                    locality=old.pilot.location(dict(address_raw=address,source_location_parts=[x.strip() for x in address.split(',')]),catalog)[0] or 'unknown'
                    if counts[locality]>=plan['max_per_locality']:state['quota_skipped']+=1
                    else:
                        detail,code=client.fetch(card['detail_url'])
                        if client.last_url!=card['detail_url']:
                            card=dict(card,requested_detail_url=card['detail_url'],detail_url=client.last_url)
                        record=old.save_response(output,dict(card,sampling_locality=locality,
                            listing_response_sha256=old.digest(body),collection_controller_sha256=controller_sha),client,detail,code)
                        rows.append(record);seen.add(key);counts[locality]+=1
                        print(old.canonical(dict(new=len(rows),record_key=key,http_status=code)),flush=True)
                attempted.add(key)
                state.update(next_page=page,attempted=sorted(attempted));old.cafe.atomic(checkpoint,state)
                if len(rows)>=plan['target']:status='target_reached';break
            if status=='target_reached':break
            if old.cafe.START+f'page-{page+1}/' not in links:
                state['finished']=True;status='end_of_pages';old.cafe.atomic(checkpoint,state);break
            state['next_page']=page+1;old.cafe.atomic(checkpoint,state)
    except KeyboardInterrupt:status,error='interrupted','KeyboardInterrupt'
    except Exception as exc:status,error='stopped_error',type(exc).__name__+': '+str(exc)
    finally:lock.unlink()
    result=dict(status=status,total=len(rows),error=error)
    old.cafe.atomic(output/'latest_run.json',result)
    return result


if __name__=='__main__':
    result=collect_new();print(json.dumps(result,ensure_ascii=False,indent=2));raise SystemExit(1 if result['error'] else 0)
