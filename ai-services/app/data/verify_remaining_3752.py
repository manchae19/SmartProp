"""Reconcile every pending decision, immutable label and frozen holdout group."""
import json
from collections import Counter,defaultdict
import numpy as np
import xgboost as xgb
import training_v3_common as c
import filter_remaining_3752 as review


def main():
    directory=review.ROOT/json.loads((review.ROOT/'latest.json').read_text(encoding='utf-8'))['run']
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['input_sha256']);c.verify(manifest['protected_sha256']);c.verify(manifest['output_sha256'],directory)
    old=review.prior.ROOT/json.loads((review.prior.ROOT/'latest.json').read_text(encoding='utf-8'))['run']
    original={r['record_key']:r for r in c.read(old/'all_listings_after_review.csv')}
    rows=c.read(directory/'all_listings_after_review.csv')
    bykey={r['record_key']:r for r in rows}
    decisions=c.read(directory/'reviewed_3752.csv')
    stats=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    assert len(rows)==len(bykey)==8509
    assert len(decisions)==len({r['record_key'] for r in decisions})==3752
    assert {r['record_key'] for r in decisions}=={k for k,r in original.items() if r['pipeline_status']=='needs_review'}
    assert Counter(r['final_status'] for r in decisions)==stats['final_batch_outcomes']
    assert Counter(r['pipeline_status'] for r in rows)==stats['all_collection_statuses']
    changes={r['record_key']:r for r in decisions}
    groups=defaultdict(list)
    for row in rows:
        before=original[row['record_key']]
        for field in ['price_million','area_sqm','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert row[field]==before[field],(row['record_key'],field)
        if before['pipeline_status']=='eligible':
            assert row['pipeline_status']=='eligible' and row['category']==before['category']
        if before['pipeline_status']=='excluded':
            assert row['pipeline_status']=='excluded'
        if row['pipeline_status']=='eligible':
            assert not row['pipeline_review_codes']
            assert row['category'] in c.CATEGORIES
            assert float(row['price_million'])>0 and float(row['area_sqm'])>0
        if row['training_allowed']=='True':
            assert row['protected_holdout']=='False'
            assert not (review.prior.codes(row['reserved_splits']) & {'validation','test'})
        if row['category']!=before['category']:
            assert changes[row['record_key']]['source_decision_applied']=='True'
            assert changes[row['record_key']]['source_identity_verified']=='True'
        groups[row['pipeline_group']].append(row)
    assert all(sum(r['pipeline_status']=='eligible' for r in group)<=1 for group in groups.values())
    parts={s:c.read(directory/'training_inputs'/(s+'.csv')) for s in ['train','validation']}
    reserved=c.read(directory/'training_inputs/reserved_holdout_registry.csv')
    review.prior.validate_optional_dates(parts,{r['pipeline_group'] for r in reserved})
    for split in ['train','validation']:
        previous={r['record_key']:r for r in c.read(old/'training_inputs'/(split+'.csv'))}
        current={r['record_key']:r for r in parts[split]}
        assert previous.keys()<=current.keys()
        assert all(current[key]==row for key,row in previous.items())
        if split=='validation':
            assert previous.keys()==current.keys()
    for index,category in enumerate(c.CATEGORIES,1):
        spec=json.loads((directory/f'training_inputs/category_{index}_schema.json').read_text(encoding='utf-8'))
        assert spec==dict(c.schema([r for r in parts['train'] if r['category']==category]),category=category)
        for split in ['train','validation']:
            subset=[r for r in parts[split] if r['category']==category]
            matrix=xgb.DMatrix(directory/f'training_inputs/category_{index}_{split}.buffer')
            assert matrix.num_row()==len(subset) and matrix.num_col()==len(spec['feature_names'])
            np.testing.assert_allclose(matrix.get_label(),np.log([float(r['price_million']) for r in subset]),rtol=1e-6)
            np.testing.assert_allclose(matrix.get_data().toarray(),np.nan_to_num(c.encode(subset,spec),nan=0),rtol=1e-6)
    assert bykey['cafeland:2485950']['pipeline_status']=='needs_review'  # locality/metadata discrepancy
    assert bykey['cafeland:3140653']['pipeline_status']=='excluded'      # whole rental-unit building
    assert changes['cafeland:3145191']['source_decision']=='keep'
    assert bykey['cafeland:3145191']['pipeline_status']=='needs_review'
    assert 'linked_group_member_not_eligible' in bykey['cafeland:3145191']['pipeline_review_codes']
    for key in ['cafeland:3145216','cafeland:3146698']:
        assert bykey[key]['pipeline_status']=='eligible'
    result=dict(verified=True,run=directory.relative_to(review.ROOT).as_posix(),reviewed_ids=3752,
        outcomes=stats['final_batch_outcomes'],train=len(parts['train']),validation=len(parts['validation']),
        reserved_eligible=len(reserved),numeric_labels_unchanged=True,category_changes_traced=True,
        old_train_validation_rows_unchanged=True,all_frozen_models_sha256_unchanged=True,
        source_and_output_sha256_verified=True,matrices_reloaded=True)
    c.write_json(review.ROOT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
