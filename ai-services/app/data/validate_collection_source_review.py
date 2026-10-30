"""Independent final checks for the completed source-evidence collection."""
import hashlib
import json
from collections import Counter, defaultdict
from audit_all_collected import BASE, read, number
from filter_all_collected import frozen_groups

ROOT=BASE/'processed/collection_source_review'
PRIOR=BASE/'processed/collection_pipeline/runs/2026-10-11_3a4f445cb285945b'


def main():
    frozen=json.loads((ROOT/'input_manifest.json').read_text(encoding='utf-8'))
    for rel,sha in frozen['protected_sha256'].items():
        assert hashlib.sha256((BASE/rel).read_bytes()).hexdigest()==sha,rel
    manifest=json.loads((ROOT/'review_manifest.json').read_text(encoding='utf-8'))
    result=json.loads((ROOT/'result_summary.json').read_text(encoding='utf-8'))
    summary=json.loads((ROOT/'review_summary.json').read_text(encoding='utf-8'))
    assert manifest['complete'] and not summary['partial']
    reviews=read(ROOT/'review_decisions.csv')
    queue=read(ROOT/'queue.csv')
    source=json.loads((ROOT/'fetch_manifest.json').read_text(encoding='utf-8'))
    assert len(queue)==len(reviews)==len(source)==4383
    assert {r['record_key'] for r in queue}=={r['record_key'] for r in reviews}==set(source)
    for review in reviews:
        assert review['decision'] in {'keep','correct','pending','exclude'}
        assert not review['price_million'] and not review['area_sqm']
        meta=source[review['record_key']]
        if meta.get('file'):
            cache=(ROOT/'detail_cache'/meta['file']).relative_to(BASE).as_posix()
            assert manifest['output_sha256'][cache]==meta['sha256']==review['detail_sha256']
        if review['record_key'].startswith('chotot:'):
            assert meta['state']=='not_requested_source_access_blocked' and meta['http_status'] is None
    run=BASE/result['pipeline_run']
    rows=read(run/'all_listings.csv')
    old={r['record_key']:r for r in read(PRIOR/'all_listings.csv')}
    assert len(rows)==len({r['record_key'] for r in rows})==len(old)==8509
    assert {r['record_key'] for r in rows}==set(old)
    bykey={r['record_key']:r for r in rows}
    for row in rows:
        for f in ('price_million','area_sqm'):
            assert number(row[f])==number(old[row['record_key']][f]),(row['record_key'],f)
        assert row['raw_json']==old[row['record_key']]['raw_json'],row['record_key']
    reservations,_=frozen_groups()
    group_reservations=defaultdict(set)
    for row in rows:group_reservations[row['pipeline_group']].update(reservations.get(row['record_key'],set()))
    train=read(run/'train_candidates.csv')
    for row in train:
        assert row['training_allowed']=='True' and row['pipeline_status']=='eligible'
        assert row['protected_holdout']=='False' and row['displayed_date']
        assert row['geographic_scope_status'].startswith('accepted_')
        assert not group_reservations[row['pipeline_group']] & {'test','validation'}
    for review in reviews:
        row=bykey[review['record_key']]
        if review['decision']=='pending':assert row['pipeline_status']!='eligible'
        if review['decision']=='exclude':assert row['pipeline_status']=='excluded'
    assert len(read(BASE/'processed/training_v2/test.csv'))==137
    counts=dict(Counter(r['pipeline_status'] for r in rows))
    assert counts==result['collection_statuses']
    assert len(train)==result['collection_train_candidates']
    queue_counts=dict(Counter(bykey[r['record_key']]['pipeline_status'] for r in queue))
    assert queue_counts==result['queue_statuses']
    print(json.dumps(dict(verified=True,unique_ids=len(rows),queue_ids=len(queue),
        queue_statuses=queue_counts,collection_statuses=counts,train_candidates=len(train),
        raw_labels_and_test_unchanged=True,holdout_leakage=False,
        source_review_decisions=summary['decisions'],identity_verified=summary['identity_verified']),
        ensure_ascii=False,indent=2))


if __name__=='__main__':main()
