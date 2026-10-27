"""Verify the date-optional dataset against original IDs, labels and reservations."""
import json
from collections import Counter, defaultdict

import training_v3_common as c
import review_remaining_4772 as review


def verify_dataset(directory, full_inputs=True):
    manifest=json.loads((directory/'manifest.json').read_text(encoding='utf-8'))
    c.verify(manifest['output_sha256'],directory)
    if full_inputs:
        for index,(relative,expected) in enumerate(manifest['input_sha256'].items(),1):
            if c.sha(c.BASE/relative)!=expected:
                raise ValueError('Input changed: '+relative)
            if index%500==0:
                print(f'Verified source files {index}/{len(manifest["input_sha256"])}',flush=True)
    source_root=c.PROCESSED/'collection_pipeline'
    source=source_root/json.loads((source_root/'latest.json').read_text(encoding='utf-8'))['run']
    original={r['record_key']:r for r in c.read(source/'all_listings.csv')}
    rows=c.read(directory/'all_listings_after_review.csv')
    checked=c.read(directory/'reviewed_4772.csv')
    summary=json.loads((directory/'summary.json').read_text(encoding='utf-8'))
    assert len(rows)==len({r['record_key'] for r in rows})==len(original)==8509
    assert len(checked)==len({r['record_key'] for r in checked})==4772
    assert {r['record_key'] for r in checked}=={k for k,r in original.items() if r['pipeline_status']=='needs_review'}
    assert Counter(r['pipeline_status'] for r in rows)==summary['statuses_after_review']
    assert Counter(r['pipeline_status'] for r in checked)==summary['pending_batch_outcomes']
    assert Counter(r['primary_issue'] for r in checked)==summary['primary_issues']
    groups=defaultdict(list)
    for row in rows:
        old=original[row['record_key']]
        for field in ['price_million','area_sqm','category','raw_json','pipeline_group','reserved_splits','assigned_split','protected_holdout']:
            assert row[field]==old[field],(row['record_key'],field)
        if old['pipeline_status']=='eligible':
            assert row['pipeline_status']=='eligible'
        if old['pipeline_status']=='excluded':
            assert row['pipeline_status']=='excluded'
        if row['pipeline_status']=='eligible':
            assert not review.codes(row['pipeline_review_codes'])
            assert review.number(row['price_million'])>0 and review.number(row['area_sqm'])>0
            assert row['category'] in c.CATEGORIES
        if row['training_allowed']=='True':
            assert row['protected_holdout']=='False' and row['assigned_split']=='train'
            assert not (review.codes(row['reserved_splits']) & {'validation','test'})
        groups[row['pipeline_group']].append(row)
    assert all(sum(r['pipeline_status']=='eligible' for r in members)<=1 for members in groups.values())
    data=directory/'training_inputs'
    parts={split:c.read(data/(split+'.csv')) for split in ['train','validation']}
    reserved=c.read(data/'reserved_holdout_registry.csv')
    review.validate_optional_dates(parts,{r['pipeline_group'] for r in reserved})
    old_root=c.PROCESSED/'training_v3'
    old_root=old_root/json.loads((old_root/'latest.json').read_text(encoding='utf-8'))['run']
    for split in ['train','validation']:
        old={r['record_key']:r for r in c.read(old_root/(split+'.csv'))}
        new={r['record_key']:r for r in parts[split]}
        assert set(old)<=set(new)
        if split=='validation':
            assert set(old)==set(new)
        assert all(new[key]==row for key,row in old.items())
    assert len(parts['train'])==summary['training_inputs']['train']==2110
    assert len(parts['validation'])==299 and len(reserved)==653
    # Reload the actual serialized matrices; do not infer validity from CSV counts.
    import numpy as np
    import xgboost as xgb
    for index,category in enumerate(c.CATEGORIES,1):
        spec=json.loads((data/f'category_{index}_schema.json').read_text(encoding='utf-8'))
        assert spec==dict(c.schema([r for r in parts['train'] if r['category']==category]),category=category)
        for split in ['train','validation']:
            subset=[r for r in parts[split] if r['category']==category]
            dm=xgb.DMatrix(data/f'category_{index}_{split}.buffer')
            assert dm.num_row()==len(subset) and dm.num_col()==len(spec['feature_names'])
            assert dm.feature_names==spec['feature_names']
            np.testing.assert_allclose(dm.get_label(),np.log([float(r['price_million']) for r in subset]),rtol=1e-6)
            np.testing.assert_allclose(dm.get_data().toarray(),np.nan_to_num(c.encode(subset,spec),nan=0),rtol=1e-6)
    return dict(verified=True,reviewed_ids=4772,train=2110,validation=299,reserved_eligible=653,
        source_inputs_sha256_verified=full_inputs,old_v3_train_and_validation_rows_unchanged=True,
        duplicate_groups_and_holdout_reservations_verified=True,matrices_reloaded_and_verified=True)


if __name__=='__main__':
    directory=review.ROOT/json.loads((review.ROOT/'latest.json').read_text(encoding='utf-8'))['run']
    result=verify_dataset(directory)
    c.write_json(review.ROOT/'independent_verification.json',dict(result,run=directory.relative_to(review.ROOT).as_posix()))
    print(json.dumps(result,ensure_ascii=False,indent=2))
