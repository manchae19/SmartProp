"""Check every reviewed ID, evidence row and aggregate against unchanged source data."""
import json
from collections import Counter

import geospatial_enrichment as geo
import review_geospatial_candidates as review


def main():
    root = review.OUT / json.loads((review.OUT/'latest.json').read_text())['run']
    manifest = json.loads((root/'manifest.json').read_text())
    geo.assert_hashes(manifest['input_sha256'])
    geo.existing_verified(root,manifest['input_sha256'])
    rows = geo.read(root/'reviewed_80.csv')
    evidence = geo.read(root/'evidence.csv')
    audit = geo.OUT / json.loads((geo.OUT/'latest_audit.json').read_text())['run']
    expected = {r['record_key'] for r in geo.read(audit/'coordinate_review_template.csv')}
    assert len(rows)==80 and len({r['record_key'] for r in rows})==80
    assert {r['record_key'] for r in rows}==expected
    pipeline = geo.latest('collection_pipeline')
    source = {r['record_key']:r for r in geo.read(pipeline/'all_listings.csv')}
    clusters = review.coordinate_clusters(list(source.values()))
    for row in rows:
        original = source[row['record_key']]; raw = json.loads(original['raw_json'])
        assert row['title_evidence']==raw['title']
        assert geo.coordinate(row)[0]==geo.coordinate(raw)[0]
        assert row['location_verified']==row['reuse_for_ml_verified']==row['model_feature_approved']=='False'
        assert row['detail_description_available']=='False'
        assert row['claim_verification_status']=='source_title_claim_only'
        assert row['source_coordinates_consistent']=='True'
        assert int(row['source_snapshot_count'])==2
        assert row['pipeline_group']==original['pipeline_group']
        assert original['pipeline_status']=='eligible'
        assert not any(k in row for k in ['price_million','predicted_million','area_sqm'])
        group = clusters[geo.coordinate(raw)[0]]
        assert int(row['shared_pin_ids'])==len(group)
        assert int(row['shared_pin_distinct_streets'])==len({review.street_key(r.get('street','')) for _,r in group} - {''})
    file_cache = {}
    for row in evidence:
        assert row['record_key'] in expected
        assert row['independent_location_confirmation']=='False'
        path = geo.BASE/row['file']
        assert geo.sha(path)==row['file_sha256']
        if row['file'] not in file_cache:
            file_cache[row['file']] = geo.read(path) if path.suffix=='.csv' else [json.loads(line)
                for line in path.read_text(encoding='utf-8-sig').splitlines() if line.strip()]
        index = int(row['input_row'])-(2 if path.suffix=='.csv' else 1)
        raw = file_cache[row['file']][index]
        assert 'chotot:'+str(raw['source_listing_id'])==row['record_key']
        if row['field']=='title':
            assert row['value']==raw['title']
        else:
            assert json.loads(row['value'])=={k:raw.get(k,'') for k in ['street','ward','district','latitude','longitude']}
    # Manually inspected source-title examples; not assertions based only on the parser's output.
    widths = {r['record_key']:float(r['alley_width_claim_m']) for r in rows if r['alley_width_claim_m']}
    assert widths=={'chotot:135149346':3.0,'chotot:135154937':4.0,
                    'chotot:135157819':5.0,'chotot:135170423':3.0}
    bykey = {r['record_key']:r for r in rows}
    assert bykey['chotot:134925160']['alley_width_claim_m']=='' # 266 is alley ID, not width.
    assert bykey['chotot:135092070']['alley_width_claim_m']=='' # 5m is parcel frontage.
    assert bykey['chotot:135168893']['access_type_claim']=='alley_claim' # near frontage.
    assert bykey['chotot:135165146']['access_type_claim']=='unknown' # near frontage alone.
    summary = json.loads((root/'summary.json').read_text())
    assert summary['cohorts']==dict(Counter(r['v3_cohort'] for r in rows))=={'train':67,'validation':6,'reserved':7}
    assert summary['access_type_claims']==dict(Counter(r['access_type_claim'] for r in rows))
    assert summary['car_access_claims']==dict(Counter(r['car_access_claim'] for r in rows))
    assert summary['alley_width_claims']==len(widths)
    assert summary['road_width_claims']==sum(bool(r['road_width_claim_m']) for r in rows)
    assert summary['shared_pin_multiple_streets']==sum(int(r['shared_pin_distinct_streets'])>1 for r in rows)
    assert summary['approved_model_features']==summary['verified_property_locations']==0
    geo.assert_hashes(manifest['input_sha256'])
    result = dict(verified_at=geo.now(),verified=True,reviewed_ids=len(rows),evidence_rows=len(evidence),
        source_evidence_rows_reconciled=True,aggregate_counts_reconciled=True,
        all_input_sha256_unchanged=True,coordinate_working_review_unchanged=True,
        frozen_data_models_unchanged=True,verified_property_locations=0,
        model_training_performed=False)
    geo.write_json(review.OUT/'verification.json',result)
    print(json.dumps(result,ensure_ascii=False,indent=2))


if __name__=='__main__':
    main()
