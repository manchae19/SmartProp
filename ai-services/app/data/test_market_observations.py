"""Behavioral tests with synthetic responses; no crawl archive or network."""
import json
from pathlib import Path
import sqlite3
import tempfile
import unittest
from unittest.mock import patch

import market_observations as core
import market_price_pipeline as pipeline


BODY = b'<html>synthetic evidence</html>'
PROOF = b'{"mode":"synthetic"}'


def event(identifier='1', when='2026-01-20T00:00:00+00:00', price=3000, group=None, **changes):
    row = dict(schema_version=1, source='cafeland', source_listing_id=identifier,
        record_key='cafeland:' + identifier, detail_url=f'https://nhadat.cafeland.vn/can-ho-{identifier}.html',
        observed_at=when, source_published_date='2025-10-01', target_type='asking_price', training_allowed=False,
        property_candidate_group=group or 'group:' + identifier, quality_flags=[], quality_eligible=True,
        http_status=200, availability='available', currency='VND', category=core.APARTMENT,
        transaction_type='sale', price_million=price, area_sqm=60, location_feature='Sơn Trà',
        response_sha256=core.digest(BODY), provenance_sha256=core.digest(PROOF))
    row.update(changes)
    return core.normalize(row)


class ObservationTests(unittest.TestCase):
    def test_retry_is_idempotent_but_same_listing_new_time_keeps_changed_price(self):
        with tempfile.TemporaryDirectory() as temp:
            store = core.ObservationStore(temp, create=True)
            try:
                self.assertTrue(store.append(event(), BODY, PROOF))
                self.assertFalse(store.append(event(), BODY, PROOF))
                self.assertTrue(store.append(event(when='2026-02-20T00:00:00+00:00', price=3200), BODY, PROOF))
                rows = store.read_verified()
                self.assertEqual([r['price_million'] for r in rows], [3000, 3200])
                self.assertEqual(store.db.execute('SELECT COUNT(*) FROM listings').fetchone()[0], 1)
                with self.assertRaisesRegex(ValueError, 'Conflicting observation'):
                    store.append(event(price=3100), BODY, PROOF)
                self.assertEqual(len(store.read_verified()), 2)
            finally:
                store.close()

    def test_source_date_does_not_create_old_observations_and_vn_month_boundary(self):
        series, summary = core.monthly_series([event(when='2026-01-31T18:00:00+00:00')])
        self.assertEqual(series[0]['month'], '2026-02')
        self.assertEqual(summary['observations_by_month'], {'2026-02': 1})
        self.assertFalse(summary['backtest_history_gate_passed'])

    def test_reject_naive_future_and_invalid_prices_or_prediction_labels(self):
        cases = [dict(observed_at='2026-01-20'), dict(observed_at='2099-01-01T00:00:00Z'),
                 dict(price_million=0), dict(price_million=float('nan')), dict(area_sqm=-1),
                 dict(target_type='model_prediction'), dict(training_allowed=True),
                 dict(detail_url='https://example.com/1.html')]
        for change in cases:
            with self.subTest(change=change), self.assertRaises(ValueError):
                event(**change)

    def test_append_only_and_evidence_tampering_detected(self):
        with tempfile.TemporaryDirectory() as temp:
            store = core.ObservationStore(temp, create=True)
            try:
                store.append(event(), BODY, PROOF)
                for table in ['observations', 'listings']:
                    with self.assertRaisesRegex(sqlite3.IntegrityError, 'append only'):
                        store.db.execute('DELETE FROM ' + table)
                    store.db.rollback()
                path = Path(temp) / 'evidence' / (core.digest(BODY) + '.html')
                path.write_bytes(b'changed')
                with self.assertRaisesRegex(ValueError, 'evidence changed'):
                    store.read_verified()
            finally:
                store.close()

    def test_missing_database_read_does_not_create_one(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaises(FileNotFoundError):
                core.ObservationStore(Path(temp) / 'missing')
            self.assertFalse((Path(temp) / 'missing').exists())

    def test_latest_failed_snapshot_suppresses_stale_price_without_sold_inference(self):
        good = event()
        missing = event(when='2026-01-21T00:00:00Z', availability='not_found', http_status=404,
            price_million=None, area_sqm=None, quality_eligible=False)
        series, summary = core.monthly_series([good, missing])
        self.assertEqual(series, [])
        self.assertEqual(missing['availability'], 'not_found')
        self.assertEqual(summary['observations_by_availability']['not_found'], 1)
        with self.assertRaises(ValueError):
            event(availability='not_found', http_status=404, quality_eligible=False)

    def test_duplicate_ads_count_once_and_conflicting_group_is_suppressed(self):
        rows = [event('1', group='same'), event('2', group='same')]
        series, _ = core.monthly_series(rows)
        self.assertEqual(series[0]['groups'], 1)
        series, summary = core.monthly_series([rows[0], event('2', group='same', price=4000)])
        self.assertEqual(series, [])
        self.assertEqual(summary['suppressed_group_months']['group_values_conflict'], 1)

    def test_one_bad_duplicate_cannot_hide_behind_good_listing(self):
        series, _ = core.monthly_series([event('1', group='same'), event('2', group='same',
            quality_eligible=False, quality_flags=['uncertain'])])
        self.assertEqual(series, [])

    def test_no_forward_fill_and_no_change_for_nonadjacent_months(self):
        series, _ = core.monthly_series([event(), event(when='2026-03-20T00:00:00Z')])
        self.assertEqual([r['month'] for r in series], ['2026-01', '2026-03'])
        self.assertIsNone(series[1]['paired_median_change_pct'])
        self.assertEqual(series[1]['paired_groups'], 0)

    def test_paired_change_controls_for_new_luxury_listings_and_has_minimum_support(self):
        old = [event(str(i)) for i in range(1, 11)]
        now = [event(str(i), when='2026-02-20T00:00:00Z', price=3300) for i in range(1, 11)]
        luxury = [event(str(i), when='2026-02-20T00:00:00Z', price=9000) for i in range(11, 31)]
        series, _ = core.monthly_series(old + now + luxury)
        self.assertEqual(series[-1]['median_total_price_million'], 9000)
        self.assertEqual(series[-1]['paired_groups'], 10)
        self.assertAlmostEqual(series[-1]['paired_median_change_pct'], 10)
        few, _ = core.monthly_series(old[:9] + now[:9])
        self.assertIsNone(few[-1]['paired_median_change_pct'])

    def test_area_changes_are_not_comparable_pairs(self):
        series, _ = core.monthly_series([event(), event(when='2026-02-20T00:00:00Z', area_sqm=65)])
        self.assertEqual(series[-1]['paired_groups'], 0)

    def test_missing_or_sparse_month_breaks_backtest_streak(self):
        rows = [event(str(i), when=f'2026-{month:02d}-20T00:00:00Z')
                for month in [1, 2, 4, 5, 6] for i in range(1, 11)]
        _, summary = core.monthly_series(rows)
        self.assertEqual(summary['longest_adequate_month_streak'], 3)
        self.assertFalse(summary['forecast_model_trained'])


def fake_context():
    row = dict(record_key='cafeland:1', source='cafeland', source_listing_id='1',
        detail_url='https://nhadat.cafeland.vn/can-ho-1.html', collected_at='2026-01-20T00:00:00Z',
        category=core.APARTMENT, transaction_type='sale', currency='VND', price_million=3000, area_sqm=60,
        source_evidence_flags=[], source_published_date='2026-01-01', title='Căn hộ', description='synthetic')
    decision = dict(record_key=row['record_key'], review_codes='[]', group_review_codes='[]', exclusion_codes='[]',
        cohort_split='collection_holdout', location_feature='Sơn Trà', property_candidate_group='group:1')
    return [(row, decision, BODY)], 'a' * 64


class PipelineTests(unittest.TestCase):
    def test_real_parser_changed_price_and_evidence_replay(self):
        from test_collect_apartment_pilot import fixture
        original_body, card = fixture()
        description = ('Căn hộ đơn lẻ diện tích 55m2 giá bán 2 tỷ 500 triệu, hai phòng ngủ thoáng mát, '
                       'phù hợp cho gia đình ở lâu dài tại khu dân cư yên tĩnh.')
        original_body = original_body.replace('Căn hộ đơn lẻ có thông tin giá và diện tích.'.encode(), description.encode())
        original = pipeline.cafe.parse_detail(original_body, card, '2026-10-27T00:00:00Z')
        decision = dict(fake_context()[0][0][1], record_key=original['record_key'])
        current_body = original_body.replace('2 tỷ 500 triệu'.encode(), '3 tỷ'.encode()).replace(b'2500000000', b'3000000000')
        class Client:
            def __init__(self, output, delay):
                self.last_url = original['detail_url']
            def fetch(self, url):
                return current_body, 200
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context',
                return_value=([(original, decision, original_body)], 'a' * 64)):
            result = pipeline.observe('real-parser', 1, temp, Client)
            self.assertIsNone(result['error'])
            rows = pipeline.verify(temp)
            self.assertEqual(rows[0]['price_million'], 3000)
            self.assertTrue(rows[0]['quality_eligible'], rows[0]['quality_flags'])

    def test_revisit_allows_price_change_but_checks_new_source_and_identity(self):
        rows, _ = fake_context()
        seed, decision, _ = rows[0]
        parsed = dict(seed, price_million=3200, source_evidence_flags=['listing_detail_price_mismatch'])
        check = dict(review_codes=[], location_feature='Sơn Trà')
        with patch.object(pipeline.cafe, 'parse_detail', return_value=parsed), \
             patch.object(pipeline.rules, 'quality', return_value=check), \
             patch.object(pipeline.rules, 'scope_exclusions', return_value=([], [])):
            row, accepted = pipeline.parse_revisit(BODY, seed, decision, seed['collected_at'], seed['detail_url'], {})
            self.assertEqual(row['source_evidence_flags'], [])
            self.assertEqual(row['price_million'], 3200)
            self.assertEqual(accepted['review_codes'], [])
            parsed['area_sqm'] = 100
            _, rejected = pipeline.parse_revisit(BODY, seed, decision, seed['collected_at'], seed['detail_url'], {})
            self.assertIn('possible_listing_reuse_or_property_identity_drift', rejected['review_codes'])

    def test_failed_revisit_keeps_no_old_price(self):
        rows, _ = fake_context()
        original, decision, _ = rows[0]
        missing = pipeline.event_for(original, decision, BODY, PROOF, status=410)
        broken = pipeline.event_for(original, decision, BODY, PROOF, error='parse_error:ValueError')
        self.assertEqual(missing['availability'], 'not_found')
        self.assertEqual(broken['availability'], 'parse_error')
        self.assertIsNone(missing['price_million'])
        self.assertIsNone(broken['price_million'])

    def test_completed_run_has_no_new_requests_and_retry_does_not_duplicate(self):
        class MissingClient:
            calls = 0
            def __init__(self, output, delay):
                self.last_url = fake_context()[0][0][0]['detail_url']
            def fetch(self, url):
                MissingClient.calls += 1
                return BODY, 404
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context', side_effect=fake_context):
            first = pipeline.observe('synthetic', 1, temp, MissingClient)
            second = pipeline.observe('synthetic', 1, temp, MissingClient)
            self.assertEqual(first['inserted'], 1)
            self.assertEqual(second['status'], 'read_only_completed')
            self.assertEqual(MissingClient.calls, 1)
            self.assertFalse((Path(temp) / 'batches/synthetic/collector.lock').exists())
            self.assertEqual(len(pipeline.verify(temp)), 1)

    def test_network_error_stops_and_cleans_lock_then_same_run_can_resume(self):
        class FailingClient:
            def __init__(self, output, delay):
                raise OSError('synthetic network failure')
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context', side_effect=fake_context):
            result = pipeline.observe('synthetic', 1, temp, FailingClient)
            self.assertEqual(result['status'], 'stopped_error')
            self.assertEqual(result['observed'], 0)
            self.assertFalse((Path(temp) / 'batches/synthetic/collector.lock').exists())
            self.assertEqual(pipeline.verify(temp), [])

    def test_interrupted_partial_run_resumes_only_missing_ids(self):
        rows, sha = fake_context()
        first, decision, body = rows[0]
        second = dict(first, record_key='cafeland:2', source_listing_id='2',
                      detail_url='https://nhadat.cafeland.vn/can-ho-2.html')
        rows.append((second, dict(decision, record_key='cafeland:2', property_candidate_group='group:2'), body))
        calls = []
        class InterruptedClient:
            def __init__(self, output, delay):
                pass
            def fetch(self, url):
                calls.append(url)
                if len(calls) == 2:
                    raise KeyboardInterrupt()
                self.last_url = url
                return BODY, 404
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context', return_value=(rows, sha)):
            interrupted = pipeline.observe('partial', 2, temp, InterruptedClient)
            self.assertEqual(interrupted['status'], 'interrupted')
            self.assertEqual(interrupted['observed'], 1)
            resumed = pipeline.observe('partial', 2, temp, InterruptedClient)
            self.assertEqual(resumed['observed'], 2)
            self.assertEqual(calls, [first['detail_url'], second['detail_url'], second['detail_url']])
            self.assertEqual(len(pipeline.verify(temp)), 2)

    def test_completed_run_stays_read_only_after_code_change(self):
        class Client:
            def __init__(self, output, delay):
                pass
            def fetch(self, url):
                self.last_url = url
                return BODY, 404
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context', side_effect=fake_context):
            pipeline.observe('done', 1, temp, Client)
            root = Path(temp)
            before = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            with patch.object(pipeline, 'code_hashes', return_value={'version': 'changed'}):
                result = pipeline.observe('done', 1, temp, lambda *_: self.fail('Network called'))
            after = {p.relative_to(root): p.read_bytes() for p in root.rglob('*') if p.is_file()}
            self.assertEqual(result['status'], 'read_only_completed')
            self.assertEqual(before, after)

    def test_policy_change_refused_before_network(self):
        with tempfile.TemporaryDirectory() as temp, patch.object(pipeline, 'review_context', side_effect=fake_context):
            path = Path(temp) / 'batches/synthetic'
            path.mkdir(parents=True)
            (path / 'plan.json').write_text('{}', encoding='utf8')
            with self.assertRaisesRegex(ValueError, 'policy changed'):
                pipeline.observe('synthetic', 1, temp, lambda *_: self.fail('network reached'))
            self.assertEqual((path / 'plan.json').read_text(encoding='utf8'), '{}')


if __name__ == '__main__':
    unittest.main()
