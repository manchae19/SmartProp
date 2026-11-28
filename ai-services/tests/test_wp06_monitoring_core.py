"""Tests for the dark-off core. No model, server, credentials or datasets."""

import ast
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace
from hashlib import sha256
from pathlib import Path
from struct import pack_into
from sys import getsizeof
from threading import Barrier, Event, Lock
from unittest import TestCase

from app.monitoring.accumulator import Availability, BucketEstimate, Histogram, WINDOW_SECONDS, ratio
from app.monitoring.alerts import Policy, WindowAlerts
from app.monitoring.batches import (
    ENTRY, HEADER, MAX_PENDING, BatchIdentity, BatchQueue, SERVING, SYNTHETIC, decode, encode,
    publish_window,
)
from app.monitoring.core import Telemetry, TelemetryConfig
from app.monitoring.reducer import MAX_DEDUPE, OPEN_WINDOWS, Reducer
from app.monitoring.schema import (
    FEATURES, LATENCY_EDGES, MAX_DURATION_US, MAX_SERIES, MAX_VALUE, REGISTRY, VERSION,
    InvalidTelemetry, Metric, Registry,
)


class Clock:
    ns = 0

    def __call__(self):
        return self.ns


def core(start=0, clock_ns=None, max_active=1024):
    return Telemetry(TelemetryConfig(True, max_active), start=start, clock_ns=clock_ns or Clock())


def wire(producer=1, generation=1, sequence=1, start=0, value=1, drop=False, population=SYNTHETIC):
    telemetry = core(start)
    telemetry.record("retry", ("advisor", "transport"), value)
    if drop:
        telemetry.drop("lock_busy")
    return encode(BatchIdentity(producer, generation, population, sequence), telemetry.snapshot())


def reducer(producers=(1,), **options):
    result = Reducer(producers, population=SYNTHETIC, watermark=options.pop("watermark", 0), **options)
    for p in producers:
        result.register_generation(p, 1, 0)
    return result


def evidence(window, **options):
    return window.coverage.status(**{"now": window.snapshot.end, "max_age": 60,
                                     "samples": 2000, "min_samples": 100, **options})


class SchemaTests(TestCase):
    def test_closed_registry_and_cardinality(self):
        self.assertEqual(REGISTRY.size, 3986)
        self.assertLessEqual(REGISTRY.size, MAX_SERIES)
        self.assertEqual(len(FEATURES), 22)
        with self.assertRaisesRegex(InvalidTelemetry, "registry_capacity"):
            Registry((Metric("x", "counter", "count", (("dim", ("a", "b")),)),), capacity=1)
        with self.assertRaisesRegex(InvalidTelemetry, "duplicate_metric"):
            Registry((Metric("x", "counter", "count", ()),) * 2)

    def test_feature_vocabulary_matches_transform_source_without_importing_model(self):
        file = Path(__file__).resolve().parents[1] / "app/models/xgboost/features_v1_3.py"
        groups = ("BASE_NUMERIC", "INDICATORS", "RATIO_FEATURES", "CATEGORICAL_FEATURES")
        expected = {}
        for statement in ast.parse(file.read_text(encoding="utf-8")).body:
            if isinstance(statement, ast.Assign) and len(statement.targets) == 1:
                target = statement.targets[0]
                if isinstance(target, ast.Name) and target.id in groups:
                    expected[target.id] = ast.literal_eval(statement.value)
        self.assertEqual(FEATURES, tuple(feature for group in groups for feature in expected[group]))

    def test_reject_schema_definitions(self):
        for edges in ((0, 0), (2, 1), (float("nan"),), (True,), (-1,), (MAX_VALUE + 1,)):
            with self.subTest(edges=edges):
                with self.assertRaisesRegex(InvalidTelemetry, "histogram_edges"):
                    Registry((Metric("x", "histogram", "us", (), edges),))
        with self.assertRaisesRegex(InvalidTelemetry, "label_definition"):
            Registry((Metric("x", "counter", "count", (("x", ("a", "a")),)),))
        with self.assertRaisesRegex(InvalidTelemetry, "metric_definition"):
            Registry((Metric("x", "meter", "unknown", ()),))

    def test_privacy_accepts_only_exact_names_and_bounded_labels(self):
        telemetry = core()
        sentinel = "private@example.invalid"
        for number in range(50):
            self.assertFalse(telemetry.record(f"custom{number}", (sentinel,)))
        self.assertFalse(telemetry.record("retry", ("advisor", sentinel)))
        self.assertFalse(telemetry.record("retry", {"surface": sentinel}))
        self.assertFalse(telemetry.record("retry", ("advisor", "transport", sentinel)))
        self.assertFalse(telemetry.record("retry", ("advisor", "transport"), sentinel))
        self.assertFalse(telemetry.record("invocation_started", ("advisor",), 10))
        snap = telemetry.snapshot()
        self.assertEqual(snap.value("telemetry_drop", ("invalid",)), 55)
        self.assertNotIn(sentinel.encode(), encode(BatchIdentity(1, 1, SYNTHETIC, 1), snap))
        self.assertEqual(snap.value("retry", ("advisor", "transport")), 0)

    def test_feature_dimensions_are_separate_and_applicability_is_explicit(self):
        telemetry = core()
        self.assertTrue(telemetry.feature("bedroom_count", "not_applicable", True,
                         segments=("surface:advisor", "type:land", "district:hai_chau", "input:compat_real"),
                         derived=True, unverified=True))
        self.assertTrue(telemetry.feature("bedroom_count", "applicability_unknown", False))
        self.assertFalse(telemetry.feature("bedroom_count", "present", True, segments=("type:land", "type:house")))
        self.assertFalse(telemetry.feature("bedroom_count", "present", True, segments=("district:unbounded",)))
        self.assertFalse(telemetry.feature("bedroom_count", "present", 1))
        snap = telemetry.snapshot()
        self.assertEqual(snap.value("feature_effective", ("bedroom_count", "not_applicable", "type:land")), 1)
        self.assertEqual(snap.value("feature_effective", ("bedroom_count", "missing", "global")), 0)
        self.assertEqual(snap.value("feature_raw", ("bedroom_count", "absent")), 1)
        self.assertEqual(snap.value("feature_provenance", ("bedroom_count", "derived", "yes")), 1)
        self.assertEqual(snap.value("feature_provenance", ("bedroom_count", "defaulted", "yes")), 0)

    def test_numeric_rejection_and_atomic_intermediate_overflow(self):
        telemetry = core()
        for value in (float("nan"), float("inf"), -float("inf"), -1, True, "1", 1.0, 2**80, MAX_DURATION_US + 1):
            with self.subTest(value=value):
                self.assertFalse(telemetry.record("stage_latency", ("advisor", "point"), value))
        self.assertTrue(telemetry.record("retry", ("advisor", "auth"), MAX_VALUE))
        self.assertFalse(telemetry.record("retry", ("advisor", "auth")))
        self.assertTrue(telemetry.interval("advisor", "available", scope="global", width_vnd=MAX_VALUE))
        self.assertFalse(telemetry.interval("advisor", "available", scope="global", width_vnd=1))
        snap = telemetry.snapshot()
        snap.validate()
        self.assertEqual(snap.value("retry", ("advisor", "auth")), MAX_VALUE)
        self.assertEqual(snap.value("telemetry_drop", ("numeric_overflow",)), 2)
        self.assertEqual(snap.value("interval_status", ("advisor", "available")), 1)
        self.assertEqual(snap.histogram("interval_width", ("advisor",)).count, 1)
        self.assertEqual(snap.histogram("interval_width", ("advisor",)).total, MAX_VALUE)

    def test_optional_contracts_do_not_count_as_model_failures(self):
        telemetry = core()
        for state in ("not_available", "not_enabled", "invalid_bounds"):
            self.assertTrue(telemetry.interval("advisor", state))
        self.assertFalse(telemetry.interval("advisor", "not_enabled", scope="global", width_vnd=0))
        self.assertFalse(telemetry.interval("advisor", "not_enabled", duration_us=0))
        self.assertFalse(telemetry.record("stage_latency", ("advisor", "interval"), 15))
        self.assertTrue(telemetry.interval("advisor", "available", scope="global_fallback", width_vnd=42,
                                           width_ppm=100, duration_us=10))
        self.assertTrue(telemetry.explanation("advisor", "not_available", "wp04_v1", "failed"))
        self.assertTrue(telemetry.explanation("advisor", "not_enabled", "absent", "not_checked"))
        self.assertFalse(telemetry.explanation("advisor", "available", "absent", "passed"))
        self.assertFalse(telemetry.explanation("advisor", "partial", "wp04_v1", "passed", provenance=(22,) * 6))
        self.assertTrue(telemetry.explanation("advisor", "partial", "wp04_v1", "passed",
                                              provenance=(3, 1, 0, 2, 0, 0), duration_us=100))
        snap = telemetry.snapshot()
        self.assertEqual(snap.value("invocation_started", ("advisor",)), 0)
        self.assertEqual(snap.value("interval_status", ("advisor", "not_enabled")), 1)
        self.assertEqual(snap.value("interval_scope", ("advisor", "global_fallback")), 1)
        self.assertEqual(snap.value("explanation_provenance", ("advisor", "provided")), 3)


class AccumulatorTests(TestCase):
    def test_histogram_bounds_merge_units_and_empty(self):
        telemetry = core()
        for n in (0, 1000, LATENCY_EDGES[-1], LATENCY_EDGES[-1] + 1):
            self.assertTrue(telemetry.record("stage_latency", ("advisor", "point"), n))
        hist = telemetry.rotate().histogram("stage_latency", ("advisor", "point"))
        empty = telemetry.snapshot().histogram("stage_latency", ("advisor", "point"))
        self.assertIsNone(empty.quantile(50))
        self.assertEqual(hist.counts[0], 2)
        self.assertEqual(hist.counts[-2:], (1, 1))
        self.assertEqual(hist.quantile(50), BucketEstimate(0, LATENCY_EDGES[0]))
        self.assertEqual(hist.quantile(75).upper, LATENCY_EDGES[-1])
        for percentile in (90, 95, 99):
            self.assertEqual(hist.quantile(percentile), BucketEstimate(LATENCY_EDGES[-1] + 1, None))
        self.assertEqual(hist.merge(empty), hist)
        self.assertEqual(hist.merge(hist).total, 2 * hist.total)
        self.assertEqual(hist.merge(hist).count, 8)
        for incompatible in (replace(hist, unit="vnd"), replace(hist, edges=(1, 2)), replace(hist, version=VERSION + 1)):
            with self.assertRaisesRegex(InvalidTelemetry, "incompatible_histogram"):
                hist.merge(incompatible)
        with self.assertRaisesRegex(InvalidTelemetry, "invalid_histogram_sum"):
            replace(hist, total=0).validate()
        with self.assertRaisesRegex(InvalidTelemetry, "invalid_histogram"):
            replace(hist, counts=hist.counts[:-1] + (2,)).validate()

    def test_quantile_combined_counts_and_zero_denominator(self):
        small = Histogram(VERSION, "us", (10, 20), (1, 0, 0), 10, 1, 100)
        large = Histogram(VERSION, "us", (10, 20), (0, 99, 0), 1980, 99, 100)
        self.assertEqual(small.merge(large).quantile(95).upper, 20)
        self.assertIsNone(ratio(0, 0))
        self.assertEqual(ratio(2, 4), .5)
        with self.assertRaises(InvalidTelemetry):
            ratio(1, 0)

    def test_lifecycle_surface_skip_options_dispatch_and_prediction_are_distinct(self):
        telemetry = core()
        for kind, outcome in (("surface", "served"), ("candidate", "eligible"), ("candidate", "skip"),
                              ("opportunity", "skip"), ("opportunity", "cache_hit"),
                              ("dispatch", "timeout"), ("dispatch", "ai_response"),
                              ("invocation", "valid_point"), ("invocation", "valid_point")):
            self.assertTrue(telemetry.finish(telemetry.begin(kind, "advisor"), outcome))
        telemetry.record("probe", ("advisor", "options", "ready"))
        snap = telemetry.snapshot()
        snap.validate()
        self.assertEqual(snap.value("surface_completed", ("advisor",)), 1)
        self.assertEqual(snap.value("opportunity_outcome", ("advisor", "skip")), 1)
        self.assertEqual(snap.value("invocation_outcome", ("advisor", "valid_point")), 2)
        self.assertEqual(snap.value("invocation_in_flight", ("advisor",)), 0)
        self.assertEqual(snap.histogram("invocation_latency", ("advisor",)).count, 2)

    def test_atomic_terminal_dedupe_across_rotation_and_orderly_stop(self):
        telemetry = core(max_active=2)
        first = telemetry.begin("invocation", "posting")
        second = telemetry.begin("invocation", "posting")
        self.assertIsNone(telemetry.begin("invocation", "posting"))
        opened = telemetry.rotate()
        opened.validate()
        self.assertEqual(opened.value("invocation_in_flight", ("posting",)), 2)
        self.assertFalse(telemetry.finish(first, "skip"))
        self.assertTrue(telemetry.finish(first, "valid_point"))
        self.assertFalse(telemetry.finish(first, "valid_point"))
        self.assertTrue(telemetry.stop())
        self.assertFalse(telemetry.finish(second, "valid_point"))
        closed = telemetry.snapshot()
        closed.validate()
        self.assertEqual(closed.value("invocation_opening_in_flight", ("posting",)), 2)
        self.assertEqual(closed.value("invocation_outcome", ("posting", "interrupted")), 1)
        self.assertEqual(closed.value("invocation_completed", ("posting",)), 2)
        self.assertEqual(closed.value("duplicate_completion"), 2)
        self.assertEqual(closed.value("invocation_in_flight", ("posting",)), 0)
        self.assertEqual(opened.value("invocation_completed", ("posting",)), 0)

    def test_barriers_hold_active_writers_while_consistent_snapshots_are_taken(self):
        telemetry = core()
        workers = 4
        active = Barrier(workers + 1, timeout=8)
        release = Barrier(workers + 1, timeout=8)
        completed = Barrier(workers + 1, timeout=8)

        def write():
            for _ in range(12):
                ticket = telemetry.begin("invocation", "standalone")
                active.wait()
                release.wait()
                self.assertTrue(telemetry.finish(ticket, "valid_point"))
                completed.wait()

        with ThreadPoolExecutor(workers) as pool:
            futures = [pool.submit(write) for _ in range(workers)]
            for i in range(12):
                active.wait()
                open_snapshot = telemetry.snapshot()
                open_snapshot.validate()
                self.assertEqual(open_snapshot.value("invocation_in_flight", ("standalone",)), workers)
                self.assertEqual(open_snapshot.value("invocation_completed", ("standalone",)), i * workers)
                release.wait()
                completed.wait()
            for f in futures:
                f.result()
        last = telemetry.snapshot()
        self.assertEqual(last.value("invocation_completed", ("standalone",)), 48)
        self.assertEqual(last.histogram("invocation_latency", ("standalone",)).count, 48)

    def test_many_concurrent_unit_writes_have_no_lost_counts(self):
        telemetry = core()
        gate = Barrier(16, timeout=8)

        def write():
            gate.wait()
            return sum(telemetry.record("retry", ("advisor", "transport")) for _ in range(200))

        with ThreadPoolExecutor(16) as pool:
            jobs = [pool.submit(write) for _ in range(16)]
            success = sum(f.result() for f in jobs)
        snapshot = telemetry.snapshot()
        self.assertEqual(snapshot.value("retry", ("advisor", "transport")), success)
        self.assertEqual(success + snapshot.value("telemetry_drop", ("lock_busy",)), 3200)

    def test_reader_races_with_terminal_update_at_the_same_lock(self):
        inside_finish, snapshot_attempted = Event(), Event()
        timestamps = iter((0, 1000))

        def clock():
            now = next(timestamps)
            if now:
                inside_finish.set()
                self.assertTrue(snapshot_attempted.wait(2))
            return now

        class InterleavedLock:
            def __init__(self):
                self.lock = Lock()

            def acquire(self, **options):
                if inside_finish.is_set() and self.lock.locked():
                    snapshot_attempted.set()
                return self.lock.acquire(**options)

            def release(self):
                self.lock.release()

        telemetry = core(clock_ns=clock)
        telemetry._lock = InterleavedLock()
        ticket = telemetry.begin("invocation", "advisor")

        with ThreadPoolExecutor(2) as pool:
            writer = pool.submit(telemetry.finish, ticket, "valid_point")
            self.assertTrue(inside_finish.wait(2))
            snapshot = pool.submit(telemetry.snapshot).result()
            self.assertTrue(writer.result())
        snapshot.validate()
        self.assertEqual(snapshot.value("invocation_in_flight", ("advisor",)), 0)
        self.assertEqual(snapshot.histogram("invocation_latency", ("advisor",)).count, 1)

    def test_disabled_is_noop_and_faulty_clock_does_not_leak_or_leave_a_partial_start(self):
        def bad_clock():
            raise RuntimeError("fixture-only-secret")

        disabled = Telemetry(clock_ns=bad_clock, start="not inspected")
        self.assertFalse(disabled.record("retry", ("advisor", "transport")))
        self.assertIsNone(disabled.begin("invocation", "advisor"))
        self.assertIsNone(disabled.snapshot())
        self.assertFalse(publish_window(disabled, None, None))
        telemetry = core(clock_ns=bad_clock)
        self.assertIsNone(telemetry.begin("invocation", "advisor"))
        self.assertFalse(telemetry.stop())
        snap = telemetry.snapshot()
        snap.validate()
        self.assertEqual(snap.value("telemetry_drop", ("invalid",)), 2)
        self.assertEqual(snap.value("invocation_in_flight", ("advisor",)), 0)
        self.assertNotIn(b"fixture-only-secret", encode(BatchIdentity(1, 1, SYNTHETIC, 1), snap))

    def test_lock_contention_returns_and_preserves_health_counter(self):
        telemetry = core()
        locked = Event()
        release = Event()

        def block():
            with telemetry._lock:
                locked.set()
                release.wait(3)

        with ThreadPoolExecutor(1) as pool:
            job = pool.submit(block)
            self.assertTrue(locked.wait(1))
            self.assertFalse(telemetry.record("retry", ("advisor", "transport")))
            release.set()
            job.result()
        self.assertEqual(telemetry.snapshot().value("telemetry_drop", ("lock_busy",)), 1)


class ProtocolTests(TestCase):
    def test_batch_roundtrip_determinism_and_invalid_wire(self):
        sample = wire()
        self.assertEqual(sample, wire())
        self.assertEqual(sha256(sample).hexdigest(), sha256(wire()).hexdigest())
        parsed = decode(sample)
        self.assertEqual(encode(parsed.identity, parsed.snapshot), sample)
        self.assertEqual(parsed.snapshot.value("retry", ("advisor", "transport")), 1)
        invalid_version = sample[:4] + b"\xff" + sample[5:]
        invalid_index = bytearray(sample)
        pack_into("<H", invalid_index, HEADER.size, REGISTRY.size)
        invalid_amount = bytearray(sample)
        pack_into("<Q", invalid_amount, HEADER.size + ENTRY.size - 8, MAX_VALUE + 1)
        for malformed in (b"token", sample + b"extra", sample[:-1], invalid_version, bytes(invalid_index),
                          bytes(invalid_amount), bytearray(sample)):
            with self.subTest(malformed_type=type(malformed)):
                with self.assertRaises(InvalidTelemetry):
                    decode(malformed)
        with self.assertRaises(InvalidTelemetry):
            encode(BatchIdentity(1, 1, SYNTHETIC, 1, release=False), parsed.snapshot)

    def test_queue_pending_count_memory_and_privacy_limits(self):
        sample = wire()
        q = BatchQueue()
        for _ in range(MAX_PENDING):
            self.assertEqual(q.offer(sample), "accepted")
        self.assertEqual(q.offer(sample), "full")
        self.assertEqual(q.usage[0], MAX_PENDING)
        bytes_reserved = BatchQueue(capacity=3).usage[1]
        small = BatchQueue(capacity=3, max_bytes=bytes_reserved + 2 * getsizeof(sample))
        self.assertEqual(small.offer(sample), "accepted")
        self.assertEqual(small.offer(sample), "accepted")
        self.assertEqual(small.offer(sample), "full")
        self.assertEqual(small.offer(sample + b"payload"), "invalid")
        self.assertEqual(small.pop(), sample)
        self.assertEqual(small.pop(), sample)
        self.assertIsNone(small.pop())
        self.assertEqual(small.usage, (0, bytes_reserved))

    def test_failed_enqueue_returns_and_marks_the_next_window(self):
        q = BatchQueue(capacity=1)
        telemetry = core()
        self.assertTrue(publish_window(telemetry, q, BatchIdentity(1, 1, SYNTHETIC, 1)))
        self.assertFalse(publish_window(telemetry, q, BatchIdentity(1, 1, SYNTHETIC, 2)))
        self.assertEqual(telemetry.snapshot().value("telemetry_drop", ("queue_full",)), 1)
        self.assertEqual(q.usage[0], 1)
        collector = reducer()
        self.assertEqual(collector.accept(q.pop(), source=1), "accepted")
        first, missing = collector.seal(120)
        self.assertEqual(evidence(first), Availability.AVAILABLE)
        self.assertEqual(evidence(missing), Availability.INSUFFICIENT_EVIDENCE)

    def test_reducer_out_of_order_duplicate_sequence_overlap_and_trusted_source(self):
        r = reducer((1, 2))
        later = wire(start=60, sequence=2)
        self.assertEqual(r.accept(later, source=1), "accepted")
        self.assertEqual(r.accept(wire(sequence=2), source=1), "sequence")
        self.assertEqual(r.accept(wire(), source=2), "untrusted")
        self.assertEqual(r.accept(wire(population=SERVING), source=1), "untrusted")
        self.assertEqual(r.accept(wire(), source=1), "accepted")
        self.assertEqual(r.accept(wire(), source=1), "duplicate")
        self.assertEqual(r.accept(wire(value=2), source=1), "overlap")
        self.assertEqual(r.accept(wire(producer=2, value=3), source=2), "accepted")
        first, later_result = r.seal(120)
        self.assertEqual(first.snapshot.value("retry", ("advisor", "transport")), 4)
        self.assertEqual(first.coverage.conflicting_batches, 1)
        self.assertEqual(evidence(first), Availability.INSUFFICIENT_EVIDENCE)
        self.assertEqual(later_result.coverage.missing_batches, 1)

    def test_late_replay_after_bounded_retention_and_reducer_reconstruction(self):
        r = reducer()
        self.assertEqual(r.accept(wire(), source=1), "accepted")
        self.assertEqual(r.seal(WINDOW_SECONDS)[0].coverage.received_batches, 1)
        for _ in range(2):
            r.seal(r.watermark + OPEN_WINDOWS * WINDOW_SECONDS)
        self.assertEqual(r.accept(wire(), source=1), "late")
        restored = reducer(watermark=r.watermark)
        self.assertEqual(restored.accept(wire(), source=1), "late")
        self.assertEqual(r.health()["late"], 1)
        self.assertEqual(r.seal(r.watermark + WINDOW_SECONDS)[0].coverage.late_arrivals_total, 1)

    def test_restart_uses_new_generation_without_reusing_old_window_or_faking_terminal_counts(self):
        r = reducer()
        old = core()
        old.begin("invocation", "advisor")
        self.assertEqual(r.accept(encode(BatchIdentity(1, 1, SYNTHETIC, 1), old.snapshot()), source=1), "accepted")
        r.register_generation(1, 2, 60)
        self.assertFalse(r.register_generation(1, 2, 60))
        with self.assertRaises(InvalidTelemetry):
            r.register_generation(1, 3, 60)
        self.assertEqual(r.accept(wire(generation=1, start=60, sequence=2), source=1), "old_generation")
        self.assertEqual(r.accept(wire(generation=2, start=60), source=1), "accepted")
        first, next_window = r.seal(120)
        self.assertEqual(first.snapshot.value("invocation_in_flight", ("advisor",)), 1)
        self.assertEqual(first.snapshot.value("invocation_completed", ("advisor",)), 0)
        self.assertEqual(next_window.snapshot.value("invocation_opening_in_flight", ("advisor",)), 0)

    def test_dedupe_capacity_rejects_new_keys_without_evicting_old_keys(self):
        r = reducer(max_dedupe=1)
        self.assertEqual(MAX_DEDUPE, 4096)
        self.assertEqual(r.accept(wire(), source=1), "accepted")
        future = wire(start=60, sequence=2)
        self.assertEqual(r.accept(future, source=1), "capacity")
        self.assertEqual(r.accept(wire(), source=1), "duplicate")
        r.seal(60)
        self.assertEqual(r.accept(future, source=1), "accepted")
        self.assertEqual(r.accept(wire(), source=1), "late")

    def test_reducer_merge_overflow_is_transactional(self):
        r = reducer((1, 2))
        self.assertEqual(r.accept(wire(value=MAX_VALUE), source=1), "accepted")
        self.assertEqual(r.accept(wire(producer=2), source=2), "numeric_overflow")
        first = r.seal(60)[0]
        self.assertEqual(first.snapshot.value("retry", ("advisor", "transport")), MAX_VALUE)
        self.assertEqual(first.coverage.received_batches, 1)

    def test_high_sample_bias_missing_batches_and_unknown_inventory_suppress_quality(self):
        r = reducer((1, 2))
        healthy = core()
        for _ in range(130):
            self.assertTrue(healthy.finish(healthy.begin("invocation", "advisor"), "valid_point"))
        rejected = core()
        for _ in range(130):
            self.assertTrue(rejected.finish(rejected.begin("invocation", "advisor"), "inference_exception"))
        self.assertEqual(r.accept(encode(BatchIdentity(1, 1, SYNTHETIC, 1), healthy.snapshot()), source=1), "accepted")
        # The failed source in this selection-bias case never reaches the reducer.
        self.assertEqual(rejected.snapshot().value("invocation_outcome", ("advisor", "inference_exception")), 130)
        closed = r.seal(60)[0]
        self.assertEqual(closed.snapshot.value("invocation_outcome", ("advisor", "valid_point")), 130)
        self.assertEqual(closed.coverage.batch_coverage, .5)
        self.assertEqual(evidence(closed, samples=130), Availability.INSUFFICIENT_EVIDENCE)
        self.assertEqual(evidence(closed, now=500), Availability.STALE)
        unknown = reducer(inventory_known=False)
        unknown.accept(wire(), source=1)
        coverage = unknown.seal(60)[0]
        self.assertIsNone(coverage.coverage.expected_batches)
        self.assertIsNone(coverage.coverage.missing_batches)
        self.assertEqual(evidence(coverage), Availability.INSUFFICIENT_EVIDENCE)
        dropped = reducer()
        dropped.accept(wire(drop=True), source=1)
        self.assertEqual(evidence(dropped.seal(60)[0]), Availability.INSUFFICIENT_EVIDENCE)

    def test_cross_source_merge_matches_sequential_histograms(self):
        r = reducer((1, 2))
        expected = core()
        for p, values in ((2, (20, 30_000)), (1, (15_000, 1000))):
            producer = core()
            for value in values:
                producer.record("stage_latency", ("advisor", "point"), value)
                expected.record("stage_latency", ("advisor", "point"), value)
            self.assertEqual(r.accept(encode(BatchIdentity(p, 1, SYNTHETIC, 1), producer.snapshot()), source=p), "accepted")
        actual = r.seal(60)[0]
        self.assertEqual(actual.snapshot.histogram("stage_latency", ("advisor", "point")),
                         expected.snapshot().histogram("stage_latency", ("advisor", "point")))


class AlertTests(TestCase):
    def test_one_window_policy_requires_one_new_consecutive_window_after_gap(self):
        a = WindowAlerts(Policy(1, 10, 20, 5, confirm=1), enabled=True)
        self.assertEqual(a.observe(60, 1, Availability.AVAILABLE, 11), "warning")
        self.assertIsNone(a.observe(180, 1, Availability.AVAILABLE, 1))
        self.assertEqual(a.incident.state, Availability.STALE)
        self.assertEqual(a.observe(240, 1, Availability.AVAILABLE, 1), "recovered")

    def test_order_duplicate_and_late_gap_clear_confirmation_and_preserve_active_stale(self):
        a = WindowAlerts(Policy(1, 10, 20, 5), enabled=True)
        self.assertIsNone(a.observe(60, 1, Availability.AVAILABLE, 11))
        self.assertEqual(a.observe(60, 1, Availability.AVAILABLE, 21), "duplicate")
        self.assertIsNone(a.observe(180, 1, Availability.AVAILABLE, 11))
        self.assertEqual(a.observe(120, 1, Availability.AVAILABLE, 11), "late")
        self.assertEqual(a.observe(240, 1, Availability.AVAILABLE, 11), "warning")
        self.assertIsNone(a.observe(360, 1, Availability.AVAILABLE, 1))
        self.assertEqual(a.incident.state, Availability.STALE)
        self.assertEqual(a.observe(420, 7, Availability.AVAILABLE, 1), "insufficient")
        self.assertEqual(a.observe(480, 1, Availability.INSUFFICIENT_EVIDENCE), "insufficient")
        self.assertEqual(a.incident.level, 1)
        self.assertIsNone(a.observe(540, 1, Availability.AVAILABLE, 1))
        self.assertEqual(a.observe(600, 1, Availability.AVAILABLE, 1), "recovered")

    def test_cooldown_only_integrity_can_bypass_and_restart_restores_policy_state(self):
        for integrity in (False, True):
            p = Policy(1, 10, 20, 5, confirm=1, cooldown=2, integrity=integrity)
            a = WindowAlerts(p, enabled=True)
            self.assertEqual(a.observe(60, 1, Availability.AVAILABLE, 11), "warning")
            self.assertIsNone(a.observe(120, 1, Availability.AVAILABLE, 7))
            restored = WindowAlerts(p, enabled=True)
            restored.restore(a.checkpoint())
            self.assertEqual(restored.observe(180, 1, Availability.AVAILABLE, 2), "recovered")
            self.assertEqual(restored.observe(240, 1, Availability.AVAILABLE, 23), "critical" if integrity else None)
            with self.assertRaises(InvalidTelemetry):
                WindowAlerts(replace(p, reference=2), enabled=True).restore(a.checkpoint())
        cold = WindowAlerts(Policy(1, 10, 20, 5), enabled=True)
        self.assertEqual(cold.incident.state, Availability.NOT_AVAILABLE)
        self.assertEqual(WindowAlerts(Policy(1, 10, 20, 5)).observe(None, None, None), "disabled")
