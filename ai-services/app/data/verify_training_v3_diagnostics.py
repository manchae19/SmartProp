"""Read-only reconciliation of v3 diagnostics; do not rehash unrelated HTML caches."""
import json
from collections import Counter
from datetime import datetime, timezone

import numpy as np
from training_v3_common import BASE, PROCESSED, read, sha, verify, write_json


def latest(name):
    directory = PROCESSED/name
    return directory/json.loads((directory/'latest.json').read_text())['run']


def main():
    root = PROCESSED/'training_v3_diagnostics'
    run = latest('training_v3_diagnostics')
    manifest = json.loads((run/'manifest.json').read_text(encoding='utf-8'))
    summary = json.loads((run/'summary.json').read_text(encoding='utf-8'))
    assert manifest['complete']
    verify(manifest['input_sha256'])
    verify(manifest['output_sha256'], run)
    for relative, expected in manifest['protected_stat'].items():
        stat = (BASE/relative).stat()
        if [stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns] != expected:
            raise ValueError('Previous artifact metadata changed: '+relative)
    data, models = BASE/summary['dataset_run'], BASE/summary['model_run']
    for folder in (data,models):
        frozen = json.loads((folder/'manifest.json').read_text(encoding='utf-8'))
        verify(frozen['output_sha256'], folder)
    train, validation = read(data/'train.csv'), read(data/'validation.csv')
    bykey = {r['record_key']:r for r in train+validation}
    details = read(run/'record_diagnostics.csv')
    assert len(details)==len(bykey)==len(train)+len(validation)
    assert {r['record_key'] for r in details}==set(bykey)
    for row in details:
        original = bykey[row['record_key']]
        assert float(row['actual_million'])==float(original['price_million'])
        assert float(row['area_sqm'])==float(original['area_sqm'])
        assert row['category']==original['category']
        assert row['label_action'].startswith('none;')
    preds = {r['record_key']:r for r in read(models/'validation_predictions.csv') if r['selected']=='True'}
    errors = read(run/'validation_diagnostics.csv')
    assert len(errors)==len(validation)
    assert {r['record_key'] for r in errors}==set(preds)
    for row in errors:
        p = preds[row['record_key']]
        actual, predicted = float(p['actual_million']),float(p['predicted_million'])
        assert float(row['predicted_million'])==predicted
        np.testing.assert_allclose(float(row['absolute_error_million']),abs(actual-predicted))
        np.testing.assert_allclose(float(row['ape_pct']),100*abs(actual-predicted)/actual)
    error_total = sum(float(r['absolute_error_million']) for r in errors)
    assert sum(float(r['ape_pct'])>50 for r in errors)==summary['aggregate']['above_50pct']
    np.testing.assert_allclose(error_total/len(errors),summary['aggregate']['mae_million'])
    segments = read(run/'segment_metrics.csv')
    for dimension in {r['dimension'] for r in segments}:
        rows = [r for r in segments if r['dimension']==dimension]
        assert sum(int(r['n']) for r in rows)==len(validation)
        np.testing.assert_allclose(sum(float(r['mae_million'])*int(r['n']) for r in rows),error_total)
    highest = sorted(errors,key=lambda r:float(r['absolute_error_million']),reverse=True)
    expected_priority = {r['record_key'] for r in highest[:20]}
    expected_priority |= {r['record_key'] for r in errors if float(r['ape_pct'])>50}
    priority = read(run/'validation_priority_review.csv')
    assert len(priority)==len(expected_priority)==summary['validation_priority_n']
    assert {r['record_key'] for r in priority}==expected_priority
    label_candidates = read(run/'label_review_candidates.csv')
    assert {r['record_key'] for r in label_candidates}=={r['record_key'] for r in details if r['diagnostic_flags']}
    assert len(label_candidates)==summary['label_review_candidates_n']
    assert dict(Counter(r['split'] for r in label_candidates))==summary['label_review_candidates_by_split']
    ds = json.loads((data/'summary.json').read_text(encoding='utf-8'))
    pipeline = BASE/ds['pipeline_run']
    old_ids = {r['record_key'] for r in read(pipeline/'all_listings.csv')}
    registry = read(run/'benchmark_exclusion_registry.csv')
    assert len(registry)==len(old_ids)==summary['benchmark']['exclusion_source_ids']
    assert {r['record_key'] for r in registry}==old_ids
    assert not {'price_million','area_sqm','title','predicted_million'} & set(registry[0])
    assert read(run/'benchmark_candidates_template.csv')==[]
    protocol = json.loads((run/'benchmark_protocol.json').read_text(encoding='utf-8'))
    assert protocol['actual_collected']==protocol['actually_scored']==0
    assert protocol['model_manifest_sha256']==sha(models/'manifest.json')
    plans = read(run/'benchmark_collection_plan.csv')
    assert sum(int(r['proposed_target']) for r in plans)==protocol['proposed_total']
    assert all(int(r['collected'])==int(r['verified'])==0 for r in plans)
    # Verify raw snapshots against the original inventory, without opening test rows or HTML.
    inventory = read(pipeline/'source_audit/file_inventory.csv')
    for row in inventory:
        if sha(BASE/row['path']) != row['sha256']:
            raise ValueError('Raw snapshot changed: '+row['path'])
    old_test = [PROCESSED/f'training_v{i}/test.csv' for i in (1,2)]
    assert sha(old_test[0])==sha(old_test[1])
    result = dict(verified=True, checked_at_utc=datetime.now(timezone.utc).isoformat(),
        run=run.relative_to(BASE).as_posix(), train_n=len(train),validation_n=len(validation),
        validation_priority_n=len(priority),label_review_candidates_n=len(label_candidates),
        raw_inventory_files_sha256_verified=len(inventory),
        frozen_data_and_model_output_sha256_verified=True,
        other_previous_artifact_metadata_unchanged=True,
        labels_and_predictions_match_frozen_v3=True, test_evaluated=False,
        benchmark_collected=0, benchmark_scored=0,
        benchmark_exclusion_ids=len(registry))
    write_json(root/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
