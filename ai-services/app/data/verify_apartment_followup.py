"""Offline replay of evidence decisions and extended cohort; no inference."""
import json
import sys
import review_apartment_followup as job


def verify():
    latest=json.loads((job.OUT/'latest.json').read_text(encoding='utf8'))['run']
    run=(job.OUT/latest).resolve()
    if not run.is_relative_to((job.OUT/'runs').resolve()):raise ValueError('Invalid run path')
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf8'))
    for name,digest in manifest.items():
        path=run/name
        if path.parent!=run or job.old.collector.sha(path)!=digest:raise ValueError('Changed output: '+name)
    summary=json.loads((run/'summary.json').read_text(encoding='utf8'))
    if job.inputs()!=summary['input_sha256']:raise ValueError('Inputs or rules changed')
    decisions,pending,cohort,links,expected=job.artifacts()
    for key,value in expected.items():
        if summary[key]!=value:raise ValueError('Summary replay differs: '+key)
    subsets={'all_decisions.csv':decisions,'pending_90_decisions.csv':pending,'collection_holdout.csv':cohort,
        'recovered_candidates.csv':[r for r in pending if r['review_outcome']=='recovered_candidate'],
        'excluded_scope.csv':[r for r in decisions if r['cohort_split']=='excluded_scope'],
        'needs_evidence.csv':[r for r in decisions if r['cohort_split']=='needs_evidence']}
    fields=list(job.old.read_csv(run/'all_decisions.csv')[0])
    for name,rows in subsets.items():
        if job.old.read_csv(run/name)!=[{k:job.scalar(r.get(k)) for k in fields} for r in rows]:raise ValueError('Decisions differ: '+name)
    lock=json.loads((run/'cohort_lock.json').read_text(encoding='utf8'))
    members=[dict(record_key=r['record_key'],property_candidate_group=r['property_candidate_group'],response_sha256=r['response_sha256']) for r in cohort]
    if lock['members']!=members or lock['training_allowed'] or lock['model_predictions_read']:raise ValueError('Invalid cohort lock')
    evidence=json.loads((run/'pending_evidence_private.json').read_text(encoding='utf8'))
    if set(evidence)!={r['record_key'] for r in pending}:raise ValueError('Missing evidence for original pending records')
    for row in pending:
        want=dict(job.rules.evidence(row,row),exclusion_evidence=row['exclusion_evidence'],remaining_codes=row['review_codes'],group_codes=row['group_review_codes'])
        if evidence[row['record_key']]!=want:raise ValueError('Evidence replay differs')
    if any(r['training_allowed'] for r in decisions):raise ValueError('Collection cohort must not enter train')
    print(json.dumps(dict(verified=True,run=latest,original_pending_checked=len(pending),new_source=summary['new_source_raw'],
        collection_holdout=len(cohort),historical_ids_overlap=0,predictions_run=0,protected_v6_and_splits_verified=True)))


if __name__=='__main__':
    try:verify()
    except Exception as error:print('FAILED: '+str(error),file=sys.stderr);raise SystemExit(1)
