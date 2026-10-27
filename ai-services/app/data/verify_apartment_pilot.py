"""Verify a locked pilot offline; never invokes a prediction or writes data."""
import json
import sys
import review_apartment_pilot as job


def verify():
    latest=json.loads((job.OUT/'latest.json').read_text(encoding='utf8'))['run']
    run=(job.OUT/latest).resolve()
    if not run.is_relative_to((job.OUT/'runs').resolve()):raise ValueError('Invalid run path')
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest.items():
        path=run/name
        if path.parent!=run or job.collector.sha(path)!=digest:raise ValueError('Output changed: '+name)
    summary=json.loads((run/'summary.json').read_text(encoding='utf8'))
    if job.inputs()!=summary['input_sha256']:raise ValueError('Inputs or rules changed; locked run is stale')
    rows=job.replay(job.RAW);history=job.read_csv(job.collector.HISTORY)
    evidence=json.loads(job.EVIDENCE.read_text(encoding='utf8'))
    old_keys={r['record_key'] for r in history};new_keys={r['record_key'] for r in rows}
    if old_keys&new_keys:raise ValueError('Historical ID overlap')
    evidence={k:v for k,v in evidence.items() if k in old_keys}
    catalog=json.loads(job.CATALOG.read_text(encoding='utf8'))
    expected,pairs=job.decide(rows,history,evidence,catalog)
    actual=job.read_csv(run/'all_decisions.csv')
    normalize=lambda value:json.dumps(value,ensure_ascii=False) if isinstance(value,(list,dict)) else '' if value is None else str(value)
    fields=list(actual[0]) if actual else []
    expected_csv=[{k:normalize(row.get(k)) for k in fields} for row in expected]
    if actual!=expected_csv:raise ValueError('Decision replay differs')
    for name,split in [('collection_holdout.csv','collection_holdout'),('needs_review.csv','quarantine'),('suppressed_duplicates.csv','suppressed_duplicate')]:
        if job.read_csv(run/name)!=[r for r in expected_csv if r['cohort_split']==split]:raise ValueError('Subset differs: '+name)
    lock=json.loads((run/'cohort_lock.json').read_text(encoding='utf8'))
    cohort=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in expected if r['cohort_split']=='collection_holdout']
    if lock['members']!=cohort or lock['training_allowed'] or lock['model_predictions_read']:raise ValueError('Invalid holdout lock')
    if any(r['training_allowed'] for r in expected):raise ValueError('Pilot must never enter training')
    if summary['total_raw']!=len(rows) or summary['collection_holdout']!=len(cohort):raise ValueError('Summary count differs')
    if summary['evaluation_gate_passed']!=(len(cohort)>=job.MIN_GROUPS):raise ValueError('Wrong gate')
    print(json.dumps(dict(verified=True,run=latest,raw=len(rows),collection_holdout=len(cohort),
                         all_cache_hashes_verified=True,decisions_replayed=True,historical_id_overlap=0,model_predictions_run=0)))


if __name__=='__main__':
    try:verify()
    except Exception as error:print('FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
