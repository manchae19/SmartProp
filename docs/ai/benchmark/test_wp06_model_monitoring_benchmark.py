"""Phase A checks for the offline prototype. No services or artifacts are loaded."""

from concurrent.futures import ThreadPoolExecutor
import json
import math
import unittest

import wp06_model_monitoring_benchmark as bench


def event(key, outcome="valid", surface="standalone", latency=50, feature="known",
          explanation="available", interval="not_enabled"):
    return key, surface, outcome, latency, feature, explanation, interval


class MetricTests(unittest.TestCase):
    def test_disjoint_boundaries_and_overflow(self):
        self.assertEqual(bench.bins([0, 5, 10, 11], (5, 10)), (2, 1, 1))
        with self.assertRaises(ValueError):
            bench.bins([1], (5, 5))

    def test_quantile_is_bucket_bound_not_an_average(self):
        self.assertEqual(bench.quantile_bucket((50, 40, 9, 1), (10, 30, 100), .50), 10)
        self.assertEqual(bench.quantile_bucket((50, 40, 9, 1), (10, 30, 100), .90), 30)
        self.assertEqual(bench.quantile_bucket((50, 40, 9, 1), (10, 30, 100), .95), 100)
        self.assertEqual(bench.quantile_bucket((50, 40, 9, 1), (10, 30, 100), .99), 100)
        self.assertEqual(bench.quantile_bucket((50, 40, 9, 1), (10, 30, 100), 1), math.inf)
        bounds = (10, 20)
        small_node, big_node = (1, 0, 0), (0, 99, 0)
        pooled = tuple(a + b for a, b in zip(small_node, big_node))
        self.assertEqual(bench.quantile_bucket(pooled, bounds, .95), 20)

    def test_latency_overflow_still_crosses_alert_threshold(self):
        w = bench.Window()
        w.record(*event(1, latency=3000))
        self.assertTrue(w.snapshot(1)["latency_p95_overflow"])
        self.assertGreater(w.snapshot(1)["latency"], bench.RULES["latency"].critical)

    def test_empty_window_has_no_estimate(self):
        snap = bench.Window().snapshot(0)
        for key in ("failure", "latency", "missing", "gap", "timeout"):
            self.assertIsNone(snap[key])
        self.assertIsNone(bench.distribution_metrics((0, 0), (3, 1)))
        self.assertIsNone(bench.ecdf_metrics([], [1]))
        self.assertIsNone(bench.point_quality([]))
        self.assertIsNone(bench.interval_quality([]))

    def test_psi_smoothing_and_js_symmetry_at_zero_bins(self):
        a, b = (12, 0, 0), (0, 12, 0)
        metrics = bench.distribution_metrics(a, b)
        self.assertTrue(math.isfinite(metrics["psi"]))
        self.assertAlmostEqual(metrics["js"], 1)
        self.assertEqual(metrics, bench.distribution_metrics(b, a))
        self.assertEqual(bench.distribution_metrics(a, a), {"psi": 0.0, "js": 0.0})

    def test_ecdf_distance_uses_ties_and_original_units(self):
        metrics = bench.ecdf_metrics([0, 0, 2, 2], [0, 0, 4, 4])
        self.assertEqual(metrics, {"ks": .5, "w1": 1.0})
        self.assertEqual(metrics, bench.ecdf_metrics([0, 0, 4, 4], [0, 0, 1, 3]))
        self.assertEqual(bench.ecdf_metrics([1, 1], [1]), {"ks": 0.0, "w1": 0.0})

    def test_unknown_categories_cannot_create_series(self):
        counts = bench.category_counts(["house", "arbitrary", "another", None], bench.TYPES)
        self.assertEqual(counts, (1, 0, 0, 3))

    def test_reference_partition_and_sparse_current_or_reference(self):
        r = bench.Reference(("v1", "schema", "native"), (2,) * 100, (100, 0, 0, 0), (100, 0, 0, 0))
        rows = [(2, "house", "d1")] * 100
        self.assertIsNone(r.compare(("v1", "changed", "native"), rows))
        self.assertIsNone(r.compare(r.key, rows[:99]))
        self.assertIsNone(bench.Reference(r.key, (2,), r.property_types, r.districts).compare(r.key, rows))
        self.assertEqual(r.compare(r.key, rows)["w1"], 0)

    def test_invalid_numeric(self):
        for value in (float("nan"), float("inf"), -float("inf"), "2", True, 10**1000):
            with self.subTest(value_type=type(value)):
                with self.assertRaises(ValueError):
                    bench.bins([value], (1, 2))
                self.assertFalse(bench.Window().record(*event(0, latency=value)))
        for counts in ((-1,), (1.1,), (True,)):
            with self.assertRaises(ValueError):
                bench.distribution_metrics(counts, (1,))
        with self.assertRaises(ValueError):
            bench.ecdf_metrics([-1e308], [1e308])
        with self.assertRaises(ValueError):
            bench.distribution_metrics((1, 0), (0, 1), smoothing=1e308)
        with self.assertRaises(ValueError):
            bench.quantile_bucket((1, 2), (), .95)
        with self.assertRaises(ValueError):
            bench.interval_quality([(3, 2, 4)])

    def test_point_and_interval_quality_require_matching_observed_target(self):
        quality = bench.point_quality([(8, 10), (12, 10), (10, 10), (15, 12)])
        self.assertAlmostEqual(quality["w20"], .75)
        self.assertAlmostEqual(quality["bias"], .75)
        self.assertAlmostEqual(quality["under"], .25)
        self.assertAlmostEqual(quality["over"], .5)
        self.assertAlmostEqual(quality["mae"], 1.75)
        self.assertIsNone(bench.point_quality([(8, 10), (10, 10)])["r2"])
        with self.assertRaises(ValueError):
            bench.point_quality([(5, 0)])
        score = bench.interval_quality([(1, 2, 1), (1, 2, 2), (1, 2, .9), (1, 2, 2.1)])
        self.assertEqual(score, {"coverage": .5, "lower_miss": .25, "upper_miss": .25})


class WindowTests(unittest.TestCase):
    def test_denominators_keep_skip_cache_and_telemetry_loss_separate(self):
        w = bench.Window()
        for i, outcome in enumerate(("valid", "valid", "validation", "skipped", "timeout", "cache", "unavailable")):
            w.record(*event(i, outcome, feature="missing" if i == 0 else "known"))
        snapshot = w.snapshot(8)
        self.assertEqual((snapshot["seen"], snapshot["attempts"], snapshot["valid"]), (7, 4, 2))
        self.assertEqual(snapshot["gap"], 1 / 8)
        self.assertEqual(snapshot["failure"], .5)
        self.assertEqual(snapshot["missing"], .5)
        self.assertEqual(snapshot["timeout"], .25)
        self.assertEqual(snapshot["unavailable"], .25)
        self.assertEqual(snapshot["unavailable_explanation"], 0)
        with self.assertRaises(ValueError):
            w.snapshot(6)

    def test_duplicate_events_do_not_duplicate_terminal_or_histogram_counts(self):
        w = bench.Window()
        for _ in range(10):
            w.record(*event(1))
        self.assertEqual(w.total("terminal"), 1)
        self.assertEqual(w.total("histogram"), 1)
        self.assertEqual(w.rejected["duplicate"], 9)

    def test_concurrent_local_ingest_counts_each_event_once(self):
        w = bench.Window()
        with ThreadPoolExecutor(max_workers=8) as pool:
            outcomes = list(pool.map(lambda i: w.record(*event(i % 128)), range(2048)))
        self.assertEqual(sum(outcomes), 128)
        self.assertEqual(w.total("terminal"), 128)
        self.assertEqual(w.rejected["duplicate"], 2048 - 128)

    def test_cardinality_and_capacity_cannot_grow_with_unapproved_values(self):
        w = bench.Window(2)
        for key in range(1000):
            self.assertFalse(w.record(*event(key, surface=str(key))))
        self.assertEqual(len(w.series), 0)
        self.assertTrue(w.record(*event(1)))
        self.assertTrue(w.record(*event(2)))
        self.assertFalse(w.record(*event(3)))
        self.assertEqual(len(w.ids), 2)
        self.assertEqual(w.rejected["overflow"], 1)

    def test_optional_failures_do_not_reduce_point_availability(self):
        w = bench.Window()
        w.record(*event(1, explanation="reconstruction_failure", interval="invalid"))
        w.record(*event(2, explanation="not_supported"))
        s = w.snapshot(2)
        self.assertEqual((s["valid"], s["failure"], s["invalid"], s["not_enabled"]), (2, 0, .5, .5))


class AlertTests(unittest.TestCase):
    def test_confirmation_hysteresis_recovery_and_cooldown(self):
        alert = bench.Alert(bench.Rule(10, 20, 4))
        data = [11, 13, 7, 3, 3, 11, 12, 13, 24, 25]
        self.assertEqual([alert.update(i, x) for i, x in enumerate(data)],
                         [None, "warning", None, None, "recovered", None, None, "warning", None, "critical"])

    def test_insufficient_does_not_recover_or_confirm_active_unknown_state(self):
        alert = bench.Alert(bench.Rule(10, 20, 4))
        data = [12, None, 13, 12, 3, None, 3, 3]
        self.assertEqual([alert.update(i, x) for i, x in enumerate(data)],
                         [None, "insufficient", None, "warning", None, "insufficient", None, "recovered"])

    def test_critical_bypasses_warning_cooldown(self):
        alert = bench.Alert(bench.Rule(10, 20, 4, confirm=1, cooldown=2))
        self.assertEqual([alert.update(i, x) for i, x in enumerate([11, 3, 21])],
                         ["warning", "recovered", "critical"])


class ExperimentTests(unittest.TestCase):
    def test_negative_controls_separate_drift_and_ground_truth(self):
        healthy, _, _ = bench.experiment(6, "healthy")
        shifted, _, _ = bench.experiment(6, "drift_no_quality_loss")
        degraded, _, _ = bench.experiment(6, "quality_loss_no_drift")
        self.assertGreater(shifted[bench.START]["drift"]["js"], healthy[bench.START]["drift"]["js"])
        self.assertAlmostEqual(shifted[bench.START + 2]["mape"], healthy[bench.START + 2]["mape"])
        self.assertEqual(degraded[bench.START]["drift"], healthy[bench.START]["drift"])
        self.assertGreater(degraded[bench.START + 2]["mape"], healthy[bench.START + 2]["mape"])

    def test_sparse_and_empty_windows_are_suppressed(self):
        for name in ("sparse", "empty"):
            rows, _, _ = bench.experiment(17, name)
            self.assertIsNone(rows[bench.START]["drift"])
        control = bench.small_sample_control()
        self.assertEqual(control["insufficient_with_gate"][12], control["trials_per_size"])
        self.assertGreater(control["raw_cutoff_exceedances"][12]["ks"],
                           control["raw_cutoff_exceedances"][bench.N]["ks"])

    def test_mature_labeled_denominator_and_unsupported_intervals(self):
        delayed, _, _ = bench.experiment(6, "delayed_labels")
        self.assertTrue(all(data["mape"] is None for data in delayed[:4]))
        mature = delayed[bench.START + 4]
        self.assertLess(mature["matched"], mature["mature_eligible"])
        unsupported, _, _ = bench.experiment(6, "unsupported_interval")
        self.assertEqual(unsupported[bench.START]["not_enabled"], 1.0)
        self.assertEqual(unsupported[bench.START]["invalid"], 0)

    def test_deterministic_seed_output(self):
        args = (61, "price_variance_shift")
        self.assertEqual(json.dumps(bench.experiment(*args), sort_keys=True, allow_nan=False),
                         json.dumps(bench.experiment(*args), sort_keys=True, allow_nan=False))


if __name__ == "__main__":
    unittest.main()
