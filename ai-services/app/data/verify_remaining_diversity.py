"""Independent export, membership, provenance and matrix checks for new train data."""
import json
from collections import Counter,defaultdict
import numpy as np
import xgboost as xgb
import training_v3_common as c
import filter_remaining_diversity as job


def main():
    directory=job.latest(job.ROOT)
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],directory)
    old=c.BASE/manifest['previous_run']
    originals={r['record_key']:r for r in c.read(old/'all_listings_after_review.csv')}
    rows=c.read(directory/'all_listings_after_review.csv')
    current={r['record_key']:r for r in rows}
    decisions=c.read(directory/'reviewed_pending.csv')
    ds={r['record_key']:r for r in decisions}
    summary=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    es=json.loads((c.PROCESSED/'collection_source_review/parsed_evidence.json').read_text(encoding='utf-8'))
    fetch=json.loads((c.PROCESSED/'collection_source_review/fetch_manifest.json').read_text(encoding='utf-8'))
    assert len(rows)==len(current)==8509 and current.keys()==originals.keys()
    assert len(decisions)==len(ds)==3605
    assert ds.keys()=={k for k,r in originals.items() if r['pipeline_status']=='needs_review'}
    assert Counter(r['pipeline_status'] for r in rows)==summary['all_collection_statuses']
    assert Counter(d['final_status'] for d in decisions)==summary['final_batch_outcomes']
    groups=defaultdict(list)
    signatures=defaultdict(set)
    for row in rows:
        signature=job.rules.description_signature(es.get(row['record_key']))
        if signature:
            signatures[signature].add(row['pipeline_group'])
    for row in rows:
        key=row['record_key'];before=originals[key]
        for field in ['price_million','area_sqm','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert row[field]==before[field],(key,field)
        if before['pipeline_status']!='needs_review':
            assert row==before,key
        if key in ds:
            assert ds[key]['final_status']==row['pipeline_status']
        if before['pipeline_status']=='needs_review' and row['pipeline_status']=='eligible':
            decision=ds[key];e=es[key];f=fetch[key]
            assert decision['source_decision_applied']=='True'
            assert e['identity_verified'] and e['structure_verified'] and e['sale_verified']
            assert f['http_status']==200 and f['sha256']==e['detail_sha256']==decision['evidence_sha256']
            relative=(c.PROCESSED/'collection_source_review/detail_cache'/f['file']).relative_to(c.BASE).as_posix()
            assert manifest['input_sha256'][relative]==f['sha256']
            assert abs(float(row['price_million'])-e['price_million'])<=.01
            assert abs(float(row['area_sqm'])-e['area_sqm'])<=.01
            assert job.rules.evaluate(before,e)['decision'] in ('keep','correct')
            assert not row['pipeline_review_codes']
            p,a=float(row['price_million']),float(row['area_sqm'])
            assert 100<=p<=200000 and 20<=a<=1000 and 2<=p/a<=300
            if row['category']=='Căn hộ chung cư':
                assert p>=500 and 15<=p/a<=150
            signature=job.rules.description_signature(e)
            assert not signature or len(signatures[signature])==1
        groups[row['pipeline_group']].append(row)
    assert all(sum(r['pipeline_status']=='eligible' for r in members)<=1 for members in groups.values())
    parts={s:c.read(directory/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    reserved=c.read(directory/'training_inputs/reserved_holdout_registry.csv')
    job.prior.validate_optional_dates(parts,{r['pipeline_group'] for r in reserved})
    for split in parts:
        previous={r['record_key']:r for r in c.read(old/'training_inputs'/(split+'.csv'))}
        now={r['record_key']:r for r in parts[split]}
        assert previous.keys()<=now.keys() and all(now[k]==r for k,r in previous.items())
        if split=='validation':
            assert now==previous and len(now)==299
        for row in parts[split]:
            assert row==c.model_row(current[row['record_key']],split)
    added=c.read(directory/'added_train.csv')
    old_ids={r['record_key'] for r in c.read(old/'training_inputs/train.csv')}
    assert added==[r for r in parts['train'] if r['record_key'] not in old_ids]
    assert len(added)==summary['additional_train']
    assert set(reserved[0])=={'record_key','source','category','pipeline_group','reserved_splits','assigned_split','protected_holdout'}
    for index,category in enumerate(c.CATEGORIES,1):
        train=[r for r in parts['train'] if r['category']==category]
        spec=json.loads((directory/f'training_inputs/category_{index}_schema.json').read_text(encoding='utf-8'))
        assert spec==dict(c.schema(train),category=category)
        for split in parts:
            subset=[r for r in parts[split] if r['category']==category]
            expected=c.encode(subset,spec)
            matrix=xgb.DMatrix(directory/f'training_inputs/category_{index}_{split}.buffer')
            assert matrix.num_row()==len(subset) and matrix.num_col()==len(spec['feature_names'])
            assert matrix.feature_names==spec['feature_names']
            assert not np.isinf(expected).any()
            np.testing.assert_allclose(matrix.get_label(),np.log([float(r['price_million']) for r in subset]),rtol=1e-6)
            np.testing.assert_allclose(matrix.get_data().toarray(),np.nan_to_num(expected,nan=0),rtol=1e-6)
    for key in ['cafeland:2485950','homedy:2896718','cafeland:3154274','cafeland:3155058',
                'cafeland:3145041','cafeland:3163843','nhadat24h:4395419']:
        assert current[key]['pipeline_status']=='needs_review',key
    result=dict(verified=True,run=directory.relative_to(job.ROOT).as_posix(),total_unique_ids=8509,
        reviewed_pending=3605,statuses=summary['all_collection_statuses'],train=len(parts['train']),
        validation=len(parts['validation']),reserved_eligible=len(reserved),additional_train=len(added),
        previous_train_validation_unchanged=True,numeric_labels_unchanged=True,
        groups_and_holdout_reservations_unchanged=True,new_eligible_cross_group_content_checked=True,
        acted_source_html_sha256_verified=True,matrices_reloaded=True,protected_models_unchanged=True)
    c.write_json(job.ROOT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
