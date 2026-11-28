from dataclasses import replace
from fractions import Fraction
import math
import unittest

import wp05_prediction_interval_benchmark as wp


class QuantileTests(unittest.TestCase):
    def test_exact_finite_sample_order_statistic(self):
        scores = list(range(1, 21))
        self.assertEqual(wp.cutoff(scores, Fraction(1, 5)), 17)
        self.assertEqual(wp.cutoff(scores, Fraction(1, 10)), 19)
        self.assertEqual(wp.cutoff(scores, Fraction(1, 20)), 20)
        self.assertEqual(wp.cutoff(list(range(9)), 0.1), 8)

    def test_empty_single_and_resolution(self):
        for coverage, minimum in [(80, 4), (90, 9), (95, 19)]:
            alpha = wp.nominal_alpha(coverage)
            for n in (0, 1, minimum - 1):
                with self.subTest(coverage=coverage, n=n):
                    self.assertIsNone(wp.cutoff([1] * n, alpha))
            self.assertEqual(wp.cutoff([0] * minimum, alpha), 0)

    def test_invalid_alpha_and_nominal(self):
        for alpha in (0, -.1, 1, 2, math.nan, math.inf):
            with self.subTest(alpha=alpha), self.assertRaises(ValueError):
                wp.cutoff([], alpha)
        for coverage in (True, 70, 80.0, 100):
            with self.subTest(coverage=coverage), self.assertRaises(ValueError):
                wp.nominal_alpha(coverage)

    def test_corrupt_score_is_rejected(self):
        for score in (-1, math.nan, math.inf, -math.inf):
            with self.subTest(score=score), self.assertRaises(ValueError):
                wp.cutoff([0, score], Fraction(1, 5))


class SplitTests(unittest.TestCase):
    def setUp(self):
        self.cal = wp.synthetic_rows(10, "additive", "calibration", 24)
        self.eval = wp.synthetic_rows(10, "additive", "evaluation", 24)

    def validate(self, rows):
        wp.validate_splits({"calibration": self.cal, "evaluation": rows})

    def test_valid_splits_keep_one_row_per_entity(self):
        self.validate(self.eval)
        distinct = wp.one_per_entity(self.cal)
        self.assertGreater(len(self.cal), len(distinct))
        self.assertEqual(len(distinct), 24)
        self.assertTrue(all(r.observation.endswith("-0") for r in distinct))
        self.assertEqual(wp.fit("log", 80, self.cal).n, 24)

    def test_duplicate_observation_entity_listing_and_repost_leakage(self):
        for key in ("observation", "entity", "listing", "repost"):
            other = replace(self.eval[0], **{key: getattr(self.cal[0], key)})
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, key):
                self.validate([other, *self.eval[1:]])

    def test_same_entity_cannot_span_partitions_when_other_keys_differ(self):
        other = replace(self.eval[0], entity=self.cal[1].entity)
        with self.assertRaisesRegex(ValueError, "entity"):
            self.validate([other])

    def test_residuals_can_only_be_fitted_from_calibration(self):
        for method in wp.METHODS:
            with self.subTest(method=method), self.assertRaisesRegex(ValueError, "calibration"):
                wp.fit(method, 90, [*self.cal, *self.eval])
        self.assertEqual(wp.fit("fixed", 90, self.cal).n, 0)

    def test_future_features_and_overlap_in_outcome_window(self):
        with self.assertRaisesRegex(ValueError, "future feature"):
            self.validate([replace(self.eval[0], feature_day=self.eval[0].snapshot_day + 1)])
        with self.assertRaisesRegex(ValueError, "chronology"):
            self.validate([replace(self.eval[0], snapshot_day=self.cal[0].label_day)])

    def test_source_and_frozen_provenance(self):
        with self.assertRaisesRegex(ValueError, "source population"):
            self.validate([replace(self.eval[0], source="UNAPPROVED")])
        for index in range(len(wp.SIGNATURE)):
            signature = list(wp.SIGNATURE)
            signature[index] = "INCOMPATIBLE"
            with self.subTest(index=index), self.assertRaisesRegex(ValueError, "provenance"):
                wp.fit("log", 80, [replace(self.cal[0], signature=tuple(signature))])

    def test_target_price_cannot_select_group_or_change_width(self):
        row = self.eval[0]
        changed_outcome = replace(row, target=wp.MAX_VND)
        for method in wp.GROUP_METHODS | {"adaptive"}:
            model = wp.fit(method, 90, self.cal)
            self.assertEqual(wp.group_key(method, row.inputs), wp.group_key(method, changed_outcome.inputs))
            self.assertEqual(wp.interval(model, row.inputs), wp.interval(model, changed_outcome.inputs))

    def test_invalid_targets_rejected(self):
        for value in (0, -1, math.nan, math.inf):
            with self.subTest(target=value), self.assertRaisesRegex(ValueError, "price"):
                wp.fit("log", 90, [replace(self.cal[0], target=value)])


class IntervalTests(unittest.TestCase):
    inputs = wp.Inputs(5_000_000_000, "HOUSE", "Hai Chau", 0, False)

    def test_zero_residual_preserves_exact_point(self):
        rows = wp.one_per_entity(wp.synthetic_rows(2, "additive", "calibration", 70))
        perfect = [replace(row, target=row.inputs.point) for row in rows]
        for method in ("absolute", "relative", "log", "asymmetric", "adaptive"):
            value = wp.interval(wp.fit(method, 90, perfect), self.inputs)
            self.assertEqual((value.status, value.point, value.lower, value.upper),
                             ("AVAILABLE", self.inputs.point, self.inputs.point, self.inputs.point))

    def test_ties_cover_calibration_boundary_and_lower_tail_casts_outward(self):
        rows = wp.one_per_entity(wp.synthetic_rows(4, "skewed", "calibration", 200))
        for method in ("absolute", "relative", "log"):
            fitted = wp.fit(method, 90, rows)
            in_score = in_interval = 0
            for row in rows:
                value = wp.interval(fitted, row.inputs)
                if method == "absolute":
                    score = abs(row.target - row.inputs.point)
                elif method == "relative":
                    score = abs(row.target - row.inputs.point) / row.inputs.point
                else:
                    score = abs(wp.log_residual(row))
                in_score += score <= fitted.global_bounds[0]
                in_interval += value.lower <= row.target <= value.upper
            self.assertGreaterEqual(in_interval, in_score)

    def test_monotonic_bounds_and_unchanged_point(self):
        rows = wp.synthetic_rows(7, "heavy_tail", "calibration", 400)
        for method in ("fixed", "absolute", "relative", "log", "asymmetric", "adaptive"):
            values = [wp.interval(wp.fit(method, c, rows), self.inputs) for c in wp.COVERAGES]
            self.assertTrue(all(v.status == "AVAILABLE" and v.point == self.inputs.point for v in values))
            self.assertEqual([v.lower for v in values], sorted((v.lower for v in values), reverse=True))
            self.assertEqual([v.upper for v in values], sorted(v.upper for v in values))

    def test_nonpositive_and_nonfinite_point_rejected(self):
        fitted = wp.Fit("log", 90, (.3, .3), 200, {})
        for point in (0, -1, None, math.nan, math.inf, wp.MAX_VND + 1, 12.5, True):
            with self.subTest(point=point):
                result = wp.interval(fitted, replace(self.inputs, point=point))
                self.assertEqual((result.status, result.lower, result.upper), ("INVALID", None, None))

    def test_exponential_overflow_and_unrepresentable_bounds(self):
        for q in (math.nan, math.inf, 1e3, 10):
            fitted = wp.Fit("log", 90, (q, q), 200, {})
            value = wp.interval(fitted, replace(self.inputs, point=wp.MAX_VND // 2))
            self.assertEqual(value.status, "INVALID")
        tiny = wp.interval(wp.Fit("log", 90, (1e-12, 1e-12), 200, {}),
                           replace(self.inputs, point=10**15))
        self.assertLess(tiny.lower, tiny.point)
        self.assertGreater(tiny.upper, tiny.point)

    def test_nonnegative_support_and_disclosure_scope(self):
        fitted = wp.Fit("absolute", 90, (2e9, 2e9), 200, {})
        outcome = wp.interval(fitted, replace(self.inputs, point=1_000_000))
        self.assertEqual(outcome.lower, 1)
        self.assertEqual(outcome.scope, "GLOBAL")
        self.assertEqual(wp.interval(fitted, self.inputs, ("wrong",)).status, "INVALID")

    def test_support_policy_and_unknown_group_fallback(self):
        self.assertEqual([wp.min_group_support(wp.nominal_alpha(c)) for c in wp.COVERAGES], [50, 100, 200])
        rows = wp.one_per_entity(wp.synthetic_rows(12, "additive", "calibration", 130))
        same_state = [replace(row, inputs=self.inputs) for row in rows]
        fitted = wp.fit("type_and_band", 90, same_state)
        covered_group = wp.interval(fitted, self.inputs)
        self.assertEqual((covered_group.scope, covered_group.n, covered_group.group_n), ("GROUP", 130, 130))
        unsupported = replace(self.inputs, kind="UNKNOWN")
        fallback = wp.interval(fitted, unsupported)
        self.assertEqual((fallback.scope, fallback.n, fallback.group_n), ("GLOBAL_FALLBACK", 130, 0))
        no_fallback = wp.interval(wp.fit("type_and_band_no_fallback", 90, rows), unsupported)
        self.assertEqual(no_fallback.status, "INSUFFICIENT")
        self.assertEqual(wp.interval(wp.fit("type", 90, []), self.inputs).status, "INSUFFICIENT")

    def test_tail_allocation_uses_two_one_sided_cutoffs(self):
        rows = wp.one_per_entity(wp.synthetic_rows(52, "skewed", "calibration", 200))
        alpha = wp.nominal_alpha(90)
        residuals = [wp.log_residual(row) for row in rows]
        lower = wp.cutoff([max(0, -r) for r in residuals], alpha * Fraction(35, 100))
        upper = wp.cutoff([max(0, r) for r in residuals], alpha * Fraction(65, 100))
        self.assertEqual(wp.fit("asymmetric", 90, rows).global_bounds, (lower, upper))

    def test_metrics_account_for_abstentions_and_misses(self):
        rows = wp.one_per_entity(wp.synthetic_rows(10, "additive", "evaluation", 3))
        target = rows[0].target
        outcomes = [wp.Interval("AVAILABLE", target, target, target),
                    wp.Interval("INSUFFICIENT", 1), wp.Interval("INVALID", 1)]
        metrics = wp.metrics(rows, outcomes, 90)
        self.assertEqual(metrics["coverage"], 1)
        self.assertEqual(metrics["covered_fraction_all"], 1 / 3)
        self.assertEqual(metrics["insufficient_rate"], 1 / 3)
        self.assertEqual(metrics["invalid_rate"], 1 / 3)
        self.assertLess(metrics["coverage_wilson_95"][0], 1)


class NegativeControlTests(unittest.TestCase):
    def test_temporal_and_geographic_shifts_degrade_coverage(self):
        scenario = "heteroskedastic"
        seed = 20261128
        parts = {role: wp.synthetic_rows(seed, scenario, role, 1000) for role in wp.ROLES}
        wp.validate_splits(parts)
        fit = wp.fit("log", 90, parts["calibration"])
        coverage = {}
        for role in wp.ROLES[2:]:
            evaluation = wp.one_per_entity(parts[role])
            coverage[role] = wp.evaluate(fit, evaluation)["overall"]["coverage"]
        self.assertGreater(coverage["evaluation"], 0.85)
        for role in ("temporal_shift", "geographic_shift"):
            self.assertLess(coverage[role], coverage["evaluation"] - .12)

    def test_outcomes_with_repeated_feature_states_stay_separate(self):
        rows = wp.one_per_entity(wp.synthetic_rows(3, "heavy_tail", "evaluation", 30))
        repeated = [replace(row, inputs=rows[0].inputs) for row in rows]
        wp.validate_splits({"evaluation": repeated})
        self.assertEqual(len(wp.one_per_entity(repeated)), 30)


if __name__ == "__main__":
    unittest.main()
