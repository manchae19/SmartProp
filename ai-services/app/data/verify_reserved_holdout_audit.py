"""Independently reconstruct historical connectivity and reconcile all 684 IDs."""
import json
from collections import Counter,defaultdict
from pathlib import Path
import training_v3_common as c
import audit_reserved_holdout as a


def main():
    run=a.latest(a.OUT)
    manifest=json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],run)
    summary=json.loads((run/'summary.json').read_text(encoding='utf-8'))
    inventory=c.read(run/'history_inventory.csv')
    snapshot={r['path'] for r in inventory}
    current={p.relative_to(c.BASE).as_posix() for p in c.PROCESSED.rglob('*.csv') if a.OUT not in p.parents}
    assert snapshot==current
    parent={}
    def find(key):
        parent.setdefault(key,key)
        while parent[key]!=key:parent[key]=parent[parent[key]];key=parent[key]
        return key
    def union(left,right):
        if left and right:
            l,r=find(left),find(right)
            if l!=r:parent[max(l,r)]=min(l,r)
    events=set();file_rows={}
    for index,item in enumerate(inventory,1):
        path=c.BASE/item['path']
        assert item['sha256']==manifest['input_sha256'][item['path']]
        fields,rows=a.projected(path)
        assert ';'.join(fields)==item['projected_columns'] and len(rows)==int(item['metadata_rows'])
        allowed_categories=None
        if path.name=='baseline_inputs.csv' and (path.parent/'baseline_metrics.json').exists():
            status=json.loads((path.parent/'baseline_metrics.json').read_text(encoding='utf-8'))
            allowed_categories={category for category,info in status['categories'].items() if info.get('status')!='insufficient_data'}
        grouped={}
        for row in rows:
            key=row.get('record_key','')
            if key:
                find(key)
                for field in a.GROUP_FIELDS:
                    if row.get(field):
                        group=(field,row[field]);union(key,grouped.setdefault(group,key))
                role=a.activity(row,path.name,allowed_categories)
                if role:events.add((key,role,item['path']))
                union(key,row.get('other_record_key',''))
                for other in a.VN_KEY.findall(row.get('group_blocking_ids','')):union(key,other)
            union(row.get('left',''),row.get('right',''))
        if index%100==0:print(f'Replayed history metadata: {index}/{len(inventory)}',flush=True)
    data=c.BASE/summary['features_run']
    reserved=c.read(data/'reserved_holdout_registry.csv')
    original={r['record_key']:r for r in reserved}
    audit=c.read(run/'reserved_id_audit.csv')
    assert len(audit)==len({r['record_key'] for r in audit})==684
    assert {r['record_key'] for r in audit}==original.keys()
    active={key for key,_,_ in events};used_components={find(key) for key in active}
    candidates=[]
    for row in audit:
        key=row['record_key']
        for field,value in original[key].items():assert row[field]==value
        expected='direct_used_or_prepared' if key in active else 'historical_group_related' if find(key) in used_components else 'no_usage_evidence'
        assert row['audit_status']==expected
        assert row['independent_test_certified']=='False' and row['price_or_error_used_for_selection']=='False'
        if expected=='no_usage_evidence':candidates.append(row)
        else:
            witness=row['exposed_witness_key']
            assert witness in active and find(key)==find(witness)
            assert any(k==witness and path==row['witness_history_file'] for k,_,path in events)
    assert c.read(run/'candidate_registry.csv')==candidates
    assert len(candidates)==summary['candidate_ids'] and len({find(r['record_key']) for r in candidates})==summary['candidate_components']
    assert Counter(r['audit_status'] for r in audit)==summary['classification']
    assert Counter(r['category'] for r in candidates)==summary['candidate_by_category']
    assert Counter(r['source'] for r in candidates)==summary['candidate_by_source']
    reserved_components={find(k) for k in original}
    relevant={(k,role,path) for k,role,path in events if find(k) in reserved_components}
    observed={(r['record_key'],r['role'],r['history_file']) for r in c.read(run/'usage_evidence.csv')}
    assert observed==relevant and len(observed)==summary['relevant_usage_events']
    links=c.read(run/'group_exposure_paths.csv')
    for row in links:
        assert find(row['left'])==find(row['right'])==find(row['reserved_record_key'])==find(row['exposed_witness_key'])
        assert row['history_file'] in snapshot
    protocol=json.loads((run/'locked_candidate_protocol.json').read_text(encoding='utf-8'))
    model=c.BASE/protocol['model_run']
    assert protocol['candidate_registry_sha256']==c.sha(run/'candidate_registry.csv')
    assert protocol['model_manifest_sha256']==c.sha(model/'manifest.json')
    assert protocol['model_selection_sha256']==c.sha(model/'selection.json')
    assert protocol['feature_extractor_sha256']==c.sha(c.BASE/'property_text_features_v6.py')
    assert not protocol['labels_inspected_in_audit'] and protocol['actually_scored']==0
    assert not summary['test_evaluated'] and not summary['models_modified'] and summary['new_network_requests']==0
    prohibited={'price_million','area_sqm','actual_million','predicted_million','title','raw_json'}
    for path in run.glob('*.csv'):
        with path.open(encoding='utf-8-sig') as s:assert not prohibited&set(s.readline().strip().split(','))
    result=dict(verified=True,run=run.relative_to(a.OUT).as_posix(),reserved_ids=684,
        classification=summary['classification'],candidate_ids=len(candidates),candidate_by_category=summary['candidate_by_category'],
        full_historical_metadata_connectivity_replayed=True,input_inventory_complete=True,
        frozen_models_data_and_candidate_protocol_sha256_verified=True,target_columns_not_projected=True,
        test_evaluated=False,independent_test_certified=False,verifier_sha256=c.sha(Path(__file__)))
    c.write_json(a.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':main()
