"""Offline verifier for the corrected dedup cohort; no prediction calls."""
import json
import sys
import review_apartment_extension as job


def verify():
    latest=json.loads((job.OUT/'latest.json').read_text(encoding='utf8'))['run']
    run=(job.OUT/latest).resolve()
    if not run.is_relative_to((job.OUT/'runs').resolve()):raise ValueError('Invalid run path')
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest.items():
        path=run/name
        if path.parent!=run or job.collector.source.sha(path)!=digest:raise ValueError('Output changed: '+name)
    summary=json.loads((run/'summary.json').read_text(encoding='utf8'))
    if job.inputs()!=summary['input_sha256']:raise ValueError('Inputs changed')
    decisions,cohort,links,expected=job.artifacts()
    for key,value in expected.items():
        if summary[key]!=value:raise ValueError('Summary differs: '+key)
    fields=list(job.previous.old.read_csv(run/'all_decisions.csv')[0])
    for name,rows in [('all_decisions.csv',decisions),('collection_holdout.csv',cohort),
                      ('needs_evidence.csv',[r for r in decisions if r['cohort_split']=='needs_evidence']),
                      ('excluded_scope.csv',[r for r in decisions if r['cohort_split']=='excluded_scope'])]:
        if job.previous.old.read_csv(run/name)!=[{k:job.previous.scalar(r.get(k)) for k in fields} for r in rows]:raise ValueError('CSV differs: '+name)
    lock=json.loads((run/'cohort_lock.json').read_text(encoding='utf8'))
    members=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in cohort]
    if lock['members']!=members or lock['training_allowed'] or lock['model_predictions_read']:raise ValueError('Invalid lock')
    print(json.dumps(dict(verified=True,run=latest,cache_replays=len(decisions),collection_holdout=len(cohort),predictions_run=0,protected_v6_verified=True)))


if __name__=='__main__':
    try:verify()
    except Exception as error:print('FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
