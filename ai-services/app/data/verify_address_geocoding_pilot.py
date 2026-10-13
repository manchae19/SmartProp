"""Independently reconcile pilot IDs, URLs, cache evidence and frozen model inputs."""
import json
from collections import Counter
from urllib.parse import parse_qs, urlsplit

import geocode_address_pilot as pilot
from training_v3_common import read, sha, verify


def main():
    root = pilot.ROOT
    inputs = pilot.load(root / 'input_manifest.json')
    verify(inputs['protected_sha256'])
    assert sha(root / 'queue.csv') == inputs['queue_sha256']
    queue = read(root / 'queue.csv')
    run = root / pilot.load(root / 'latest.json')['run']
    manifest = pilot.load(run / 'manifest.json')
    summary = pilot.load(run / 'summary.json')
    verify(manifest['output_sha256'], base=run)
    verify(manifest['cache_sha256'], base=root)
    assert manifest['code_sha256'] == sha(pilot.Path(pilot.__file__))
    assert manifest['queue_sha256'] == inputs['queue_sha256']
    checkpoint = read(run / 'checkpoint.csv')
    candidates = read(run / 'candidates_DO_NOT_TRAIN.csv')
    expected = {r['record_key']:r for r in queue}
    assert len(queue) == len(checkpoint) == len(expected) == 80
    assert {r['record_key'] for r in checkpoint} == set(expected)
    assert len({r['query_id'] for r in queue}) == summary['unique_queries'] == inputs['unique_queries']
    assert Counter(r['state'] for r in checkpoint) == summary['states']
    assert len(candidates) == summary['candidate_rows']
    assert summary['property_locations_verified'] == summary['approved_model_features'] == 0
    assert summary['google_content_downloaded'] is False
    seen_queries = set()
    expected_candidates = Counter()
    for row in queue:
        url = urlsplit(row['google_maps_url'])
        assert url.netloc == 'www.google.com' and url.path == '/maps/search/'
        assert parse_qs(url.query) == {'api':['1'], 'query':[row['address_query']]}
        assert row['exact_house_number_verified'] == 'False'
        value = pilot.cached(root, summary['endpoint'], row)
        if value:
            seen_queries.add(row['query_id'])
            assert value['request_url'].startswith(summary['endpoint'] + '?')
            expected_candidates[row['record_key']] = len(value.get('results', []))
    assert len(seen_queries) == summary['unique_queries_attempted']
    assert Counter(r['record_key'] for r in candidates) == +expected_candidates
    for row in candidates:
        assert row['location_verified'] == row['model_feature_approved'] == 'False'
        assert row['precision'] in {'street_reference', 'unresolved_candidate'}
        assert row['query_id'] == expected[row['record_key']]['query_id']
        cached = pilot.cached(root, summary['endpoint'], expected[row['record_key']])
        actual = cached['results'][int(row['rank']) - 1]
        assert row['candidate_latitude'] == str(actual['lat'])
        assert row['candidate_longitude'] == str(actual['lon'])
        assessment = pilot.assess(expected[row['record_key']], actual)
        assert row['precision'] == assessment['precision']
    matched_ids = {r['record_key'] for r in candidates if r['precision'] == 'street_reference'}
    assert len(matched_ids) == summary['records_with_street_reference']
    assert (run / 'review.html').read_text(encoding='utf-8').count('href="https://www.google.com/maps/search/?') == 80
    verification = dict(verified=True, verified_at_utc=pilot.now(), run=run.relative_to(root).as_posix(),
        records=80, unique_queries=summary['unique_queries'], queries_attempted=len(seen_queries),
        property_locations_verified=0, approved_model_features=0, raw_labels_splits_models_sha256_unchanged=True,
        queue_cache_output_sha256_verified=True)
    pilot.save(root / 'independent_verification.json', verification)
    print(json.dumps(verification, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
