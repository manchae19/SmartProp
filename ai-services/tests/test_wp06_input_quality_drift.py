"""Synthetic classified features and fixed-reference aggregate comparisons."""

from dataclasses import replace
from unittest import TestCase

import pandas as pd

from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3
from app.models.xgboost.features_v1_3 import transform
from app.monitoring.accumulator import Availability
from app.monitoring.batches import SERVING, SYNTHETIC
from app.monitoring.drift import DUAN_V13, Counts, DriftWindow, Reference, ReferenceKey, compare
from app.monitoring.fastapi_adapter import FastAPIWorker, Flags, Route
from app.monitoring.input_quality import DERIVED, FeatureFact, InputMode, MatrixState, PropertyKind, Provenance
from app.monitoring.reducer import Coverage
from app.monitoring.schema import FEATURES, MAX_SERIES, MAX_VALUE, REGISTRY, RELEASE, VERSION, InvalidTelemetry


def feature_fixture(**overrides):
    return tuple(overrides.get(feature, FeatureFact(False, MatrixState.PRESENT if feature.startswith("has_")
                                                    else MatrixState.MISSING)) for feature in FEATURES)


def as_raw_row(mapped):
    row = {name: mapped.get(name) for name in ("area", "normalized_type", "district", "ward")}
    for key in ("floor_count", "bedroom_count", "bathroom_count", "frontage_width", "road_width",
                "street_name", "project_name", "house_direction", "balcony_direction"):
        row["raw_" + key] = mapped.get(key)
    return row


class FeatureTests(TestCase):
    def test_four_property_types_and_unknown_applicability_preserve_matrix_axis(self):
        worker = FastAPIWorker(Flags(input_quality=True))
        facts = feature_fixture(bedroom_count=FeatureFact(True, MatrixState.PRESENT, Provenance.USER_ASSERTED),
                                area=FeatureFact(True, MatrixState.PRESENT, Provenance.VERIFIED_SOURCE))
        for kind in PropertyKind:
            self.assertTrue(worker.input_quality(Route.PRIMARY, kind, InputMode.CANONICAL, "hai_chau", facts))
        s = worker.recorder.snapshot()
        self.assertIsNone(worker.begin_point(Route.PRIMARY))
        for kind in ("house", "villa", "apartment"):
            self.assertEqual(s.value("feature_effective", ("bedroom_count", "present", f"type:{kind}")), 1)
        self.assertEqual(s.value("feature_effective", ("bedroom_count", "not_applicable", "type:land")), 1)
        self.assertEqual(s.value("feature_effective", ("bedroom_count", "missing", "type:land")), 0)
        self.assertEqual(s.value("feature_effective", ("bedroom_count", "applicability_unknown", "type:other")), 1)
        self.assertEqual(s.value("feature_effective", ("frontage_width", "applicability_unknown", "type:apartment")), 1)
        self.assertEqual(s.value("feature_matrix", ("bedroom_count", "present")), 5)
        self.assertEqual(s.value("feature_raw", ("bedroom_count", "present")), 5)
        self.assertEqual(s.value("feature_provenance", ("bedroom_count", "unverified", "yes")), 5)
        self.assertEqual(s.value("feature_provenance", ("area", "unverified", "yes")), 0)
        self.assertEqual(s.value("feature_provenance", ("has_bedroom", "derived", "yes")), 5)
        self.assertEqual(s.value("feature_effective", ("area", "present", "surface:standalone")), 0)
        self.assertEqual(REGISTRY.size, 3986)
        self.assertLessEqual(REGISTRY.size, MAX_SERIES)

    def test_real_transform_and_compat_adapter_fixture_supplies_all_22_facts_without_model(self):
        schema = {"vocabularies": {
            "normalized_type": ["house", "land", "apartment", "villa"], "district": ["hải châu"],
            "ward": ["fixture-ward"], "raw_street_name": ["fixture-known"],
            "raw_project_name": ["fixture-project"], "raw_house_direction": ["fixture-east"],
            "raw_balcony_direction": ["fixture-west"],
        }}
        payload = {"area_sqm": 100, "category": "Nhà ở", "location_feature": "Hải Châu",
                   "ward": "fixture-ward", "street_name": "fixture-unknown-street",
                   "access_type": "alley", "road_width_m": "invalid-fixture", "rooms": 2}
        real = map_v6_to_v1_3(payload, use_real_features=True, district_vocabulary=("hải châu",))
        legacy = map_v6_to_v1_3(payload, use_real_features=False, district_vocabulary=("hải châu",))
        canonical = {"area": 125, "normalized_type": "VILLA", "district": "hải châu",
                     "frontage_width": 7, "street_name": "Đường fixture-known"}
        inputs = ((real, payload, InputMode.COMPAT_REAL, PropertyKind.HOUSE),
                  (legacy, payload, InputMode.COMPAT_LEGACY, PropertyKind.HOUSE),
                  (canonical, canonical, InputMode.CANONICAL, PropertyKind.VILLA))
        legacy_names = {"area": "area_sqm", "normalized_type": "category", "district": "location_feature",
                        "floor_count": "floors", "bedroom_count": "rooms", "bathroom_count": "bathrooms",
                        "frontage_width": "frontage_width_m", "road_width": "road_width_m"}
        worker = FastAPIWorker(Flags(input_quality=True))
        for mapped, submitted, mode, kind in inputs:
            transformed = transform(pd.DataFrame([as_raw_row(mapped)]), schema)
            self.assertEqual(tuple(transformed.columns), FEATURES)
            row = transformed.iloc[0]
            facts = []
            for feature in FEATURES:
                derived = feature in DERIVED
                name = feature.removeprefix("raw_")
                field = name if mode is InputMode.CANONICAL else legacy_names.get(name, name)
                raw = not derived and submitted.get(field) is not None
                if row[feature] == "__UNKNOWN__":
                    state = MatrixState.UNKNOWN
                elif pd.isna(row[feature]) or row[feature] == "__MISSING__":
                    state = MatrixState.INVALID if feature == "road_width" and mode is InputMode.COMPAT_REAL else MatrixState.MISSING
                else:
                    state = MatrixState.PRESENT
                assumed_width = mode is InputMode.COMPAT_LEGACY and feature in ("frontage_width", "road_width")
                source = Provenance.DEFAULTED if assumed_width else Provenance.UNSPECIFIED
                facts.append(FeatureFact(raw, state, source))
            if mode is InputMode.COMPAT_REAL:
                self.assertEqual(row["has_street"], 1)
                self.assertEqual(row["raw_street_name"], "__UNKNOWN__")
            if mode is InputMode.COMPAT_LEGACY:
                self.assertEqual(row["road_width"], 3)
                self.assertEqual(row["raw_street_name"], "__MISSING__")
            if mode is InputMode.CANONICAL:
                self.assertEqual(row["raw_street_name"], "fixture-known")
            self.assertTrue(worker.input_quality(Route.PRIMARY, kind, mode, "hai_chau", tuple(facts)))
        s = worker.recorder.snapshot()
        self.assertEqual(s.value("feature_effective", ("road_width", "invalid", "input:compat_real")), 1)
        self.assertEqual(s.value("feature_effective", ("road_width", "present", "input:compat_legacy")), 1)
        self.assertEqual(s.value("feature_provenance", ("road_width", "defaulted", "yes")), 1)
        self.assertEqual(s.value("feature_raw", ("frontage_width", "absent")), 2)
        self.assertEqual(s.value("feature_provenance", ("frontage_width", "defaulted", "yes")), 1)
        self.assertEqual(s.value("feature_effective", ("raw_street_name", "unknown", "input:compat_real")), 1)
        self.assertEqual(s.value("feature_effective", ("raw_street_name", "missing", "input:compat_legacy")), 1)
        for feature in FEATURES:
            self.assertEqual(sum(s.value("feature_matrix", (feature, state.value)) for state in MatrixState), 3)

    def test_invalid_frame_is_atomic_and_unknown_district_never_becomes_a_label(self):
        worker = FastAPIWorker(Flags(input_quality=True))
        bad = feature_fixture(has_floor=FeatureFact(True, MatrixState.PRESENT))
        self.assertFalse(worker.input_quality(Route.PRIMARY, PropertyKind.HOUSE, InputMode.CANONICAL, "other", bad))
        self.assertEqual(worker.recorder.snapshot().value("feature_raw", ("area", "absent")), 0)
        for i in range(150):
            self.assertTrue(worker.input_quality(Route.PRIMARY, PropertyKind.OTHER, InputMode.CANONICAL,
                                                 f"fixture-unknown-{i}", feature_fixture()))
        s = worker.recorder.snapshot()
        self.assertEqual(s.value("feature_effective", ("area", "missing", "district:other")), 150)
        self.assertEqual(s.value("telemetry_drop", ("invalid",)), 1)
        numeric_unknown = feature_fixture(area=FeatureFact(True, MatrixState.UNKNOWN))
        self.assertFalse(worker.input_quality(Route.PRIMARY, PropertyKind.VILLA, InputMode.COMPAT_REAL,
                                              "other", numeric_unknown))
        invalid_default = feature_fixture(road_width=FeatureFact(False, MatrixState.PRESENT, Provenance.DEFAULTED))
        self.assertFalse(worker.input_quality(Route.PRIMARY, PropertyKind.VILLA, InputMode.COMPAT_REAL,
                                              "other", invalid_default))
        with self.assertRaises(InvalidTelemetry):
            FeatureFact("raw text", MatrixState.PRESENT)


def key():
    return ReferenceKey(RELEASE, VERSION, DUAN_V13, InputMode.COMPAT_REAL, SYNTHETIC, 1)


def counts(offset=0, n=100, *, missing=2, unknown=3):
    return Counts(tuple(n if i == offset else 0 for i in range(10)),
                  tuple(n if i == offset else 0 for i in range(5)), n, missing, unknown)


class DriftTests(TestCase):
    def setUp(self):
        self.key = key()
        self.coverage = Coverage(1, 1, 1, 1, 0, 0, 0, 60)
        self.batch = DriftWindow(self.key, 0, counts(offset=1, missing=12, unknown=6), self.coverage)
        self.reference = Reference(self.key, counts(), approved=True)

    def test_synthetic_histogram_metrics_have_known_units_bounds_and_empty_bins(self):
        result = compare(self.batch, self.reference, now=60, max_age=0, enabled=True)
        self.assertIs(result.status, Availability.AVAILABLE)
        self.assertAlmostEqual(result.missing_delta, .10)
        self.assertAlmostEqual(result.unknown_rate, .06)
        self.assertAlmostEqual(result.unknown_delta, .03)
        self.assertEqual(result.categorical_js, 1)
        self.assertGreater(result.histogram_psi, 0)
        self.assertEqual(result.histogram_js, 1)
        self.assertEqual(result.w1_vnd, 1_000_000_000)
        self.assertEqual(result.w1_error_bound_vnd, 1_000_000_000)
        self.assertEqual(result.ks_bin_edges, 1)
        same = replace(self.batch, counts=self.reference.counts)
        baseline = compare(same, self.reference, now=60, max_age=0, enabled=True)
        self.assertEqual((baseline.histogram_psi, baseline.histogram_js, baseline.w1_vnd, baseline.ks_bin_edges), (0, 0, 0, 0))

    def test_fixed_reference_compatibility_and_real_data_gate(self):
        for changes in (dict(release=2), dict(schema=VERSION + 1), dict(calibration=2),
                        dict(mode=InputMode.CANONICAL), dict(population=SERVING), dict(version=2)):
            incompatible = replace(self.key, **changes)
            self.assertIs(compare(replace(self.batch, key=incompatible), self.reference, now=60, max_age=0, enabled=True).status,
                          Availability.NOT_AVAILABLE)
        for changes in (dict(release=2), dict(schema=VERSION + 1), dict(calibration=2), dict(population=SERVING)):
            same_incompatible = replace(self.key, **changes)
            self.assertIs(compare(replace(self.batch, key=same_incompatible), replace(self.reference, key=same_incompatible),
                                  now=60, max_age=0, enabled=True).status, Availability.NOT_AVAILABLE)
        self.assertIs(compare(self.batch, replace(self.reference, approved=False), now=60, max_age=0, enabled=True).status,
                      Availability.NOT_AVAILABLE)
        self.assertIs(FastAPIWorker().compare_drift(None, None, now=None, max_age=None).status,
                      Availability.NOT_ENABLED)
        drift_only = FastAPIWorker(Flags(drift=True))
        self.assertIsNone(drift_only.recorder.snapshot())
        self.assertIs(drift_only.compare_drift(None, None, now=60, max_age=0).status, Availability.NOT_AVAILABLE)
        self.assertIs(drift_only.compare_drift(self.batch, self.reference, now=60, max_age=0).status,
                      Availability.AVAILABLE)

    def test_high_sample_selection_bias_stale_sparse_and_empty_are_never_declared_healthy(self):
        for coverage in (replace(self.coverage, expected_sources=2, expected_batches=2),
                         replace(self.coverage, dropped_observations=1),
                         replace(self.coverage, continuity_mismatches=1),
                         replace(self.coverage, lost_terminals=1),
                         replace(self.coverage, expected_batches=None, expected_sources=None)):
            current = replace(self.batch, coverage=coverage)
            result = compare(current, self.reference, now=60, max_age=0, enabled=True)
            self.assertIs(result.status, Availability.INSUFFICIENT_EVIDENCE)
            self.assertIsNone(result.w1_vnd)
        for n in (0, 2, 99):
            inadequate = counts(n=n, missing=0, unknown=0)
            self.assertIs(compare(replace(self.batch, counts=inadequate), self.reference,
                                  now=60, max_age=0, enabled=True).status, Availability.INSUFFICIENT_EVIDENCE)
            self.assertIs(compare(self.batch, replace(self.reference, counts=inadequate),
                                  now=60, max_age=0, enabled=True).status, Availability.INSUFFICIENT_EVIDENCE)
        self.assertIs(compare(self.batch, self.reference, now=61, max_age=0, enabled=True).status, Availability.STALE)

    def test_counts_are_bounded_and_cannot_encode_arbitrary_category_names(self):
        bad = ((MAX_VALUE,) * 10, ("raw-address",) * 10, (-1,) * 10, (True,) * 10, (1,) * 11)
        for prices in bad:
            with self.assertRaises(InvalidTelemetry):
                replace(self.batch.counts, prices=prices)
        with self.assertRaises(InvalidTelemetry):
            replace(self.batch.counts, unknown=100)
        with self.assertRaises(InvalidTelemetry):
            replace(self.batch, start=61)
