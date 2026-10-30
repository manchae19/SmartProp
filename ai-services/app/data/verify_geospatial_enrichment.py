"""Reconcile the location audit with frozen collection/v3 and untouched raw snapshots."""
import json
from collections import Counter

import geospatial_enrichment as geo


def verify():
    root = geo.OUT / json.loads((geo.OUT/'latest_audit.json').read_text())['run']
    manifest = json.loads((root/'manifest.json').read_text())
    geo.assert_hashes(manifest['input_sha256'])
    geo.existing_verified(root,manifest['input_sha256'])
    before = geo.artifact_stats()
    pipeline, training = geo.latest('collection_pipeline'), geo.latest('training_v3')
    source = geo.read(pipeline/'all_listings.csv')
    audit = geo.read(root/'location_audit.csv')
    assert len(source) == len(audit)
    original = {r['record_key']:r for r in source}
    assert len(original) == len(source)
    assert len({r['record_key'] for r in audit}) == len(audit)
    assert {r['record_key'] for r in audit} == set(original)
    decoded = {k:json.loads(r['raw_json']) for k,r in original.items()}
    pair_counts = Counter(geo.coordinate(r)[0] for r in decoded.values() if geo.coordinate(r)[0])
    cohorts = {r['record_key']:split for split in ('train','validation')
               for r in geo.read(training/(split+'.csv'))}
    cohorts.update({r['record_key']:'reserved'
                    for r in geo.read(training/'reserved_holdout_registry.csv')})
    for row in audit:
        key = row['record_key']; pair,state = geo.coordinate(decoded[key])
        assert geo.coordinate(row)[0] == pair
        assert row['coordinate_state'] == state
        assert row['v3_cohort'] == cohorts.get(key,'outside_v3')
        assert row['pipeline_status'] == original[key]['pipeline_status']
        assert row['pipeline_group'] == original[key]['pipeline_group']
        assert int(row['coordinate_repeated_ids']) == (pair_counts[pair] if pair else 0)
        assert row['location_verified'] == row['reuse_for_ml_verified'] == 'False'
        assert not any(k in row for k in ('price_million','area_sqm','predicted_million'))
    reviews = geo.read(root/'coordinate_review_template.csv')
    queue = geo.read(root/'geocoding_queue.csv')
    eligible = {r['record_key'] for r in source if r['pipeline_status']=='eligible'}
    assert {r['record_key'] for r in reviews} | {r['record_key'] for r in queue} == eligible
    assert len(reviews) + len(queue) == len(eligible)
    assert not ({r['record_key'] for r in reviews} & {r['record_key'] for r in queue})
    assert not any(geo.approved_review(r) for r in reviews)
    summary = json.loads((root/'summary.json').read_text())
    assert summary['rows'] == len(audit)
    assert summary['numeric_coordinates'] == sum(pair_counts.values())
    assert summary['distinct_coordinate_pairs'] == len(pair_counts)
    assert summary['eligible_coordinate_candidates'] == len(reviews)
    assert summary['eligible_needing_location'] == len(queue)
    for split in ('train','validation'):
        assert summary[split+'_coordinates'] == sum(r['v3_cohort']==split and bool(r['latitude']) for r in audit)
    coverage = geo.read(root/'coverage.csv')
    for row in coverage:
        selected = [r for r in audit if row['dimension']=='all' or
                    r[row['dimension']] == row['value']]
        metric = row['metric']
        expected = (len(selected) if metric=='rows' else
            sum(bool(r['latitude']) for r in selected) if metric=='numeric_coordinates' else
            sum(int(r['coordinate_repeated_ids'])>1 for r in selected) if metric=='repeated_coordinate' else
            sum(r[metric]=='True' for r in selected))
        assert expected == int(row['count'])
    pipeline_manifest = json.loads((pipeline/'manifest.json').read_text())
    # All pipeline data outputs and all 20 original raw snapshot inputs, not just a sample.
    geo.assert_hashes(pipeline_manifest['output_sha256'])
    raw = {k:v for k,v in pipeline_manifest['input_sha256'].items()
           if k.endswith(('.csv','.jsonl')) and not k.startswith('processed/')}
    geo.assert_hashes(raw)
    geo.frozen_paths()
    assert geo.artifact_stats() == before
    result = dict(verified_at=geo.now(),verified=True,rows=len(audit),
        raw_snapshots_sha256_verified=len(raw),frozen_collection_outputs_sha256_verified=True,
        frozen_v3_data_and_model_outputs_sha256_verified=True,
        other_processed_artifacts_stat_unchanged=True,
        numeric_coordinate_candidates=sum(pair_counts.values()),
        eligible_coordinate_review_rows=len(reviews),eligible_geocoding_queue_rows=len(queue),
        verified_locations=0,model_training_performed=False,
        osm_snapshots_available=len(list((geo.OUT/'osm_snapshots').glob('*/metadata.json'))),
        feature_runs_available=len(list((geo.OUT/'feature_runs').glob('*/manifest.json'))))
    geo.write_json(geo.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__ == '__main__':
    verify()
