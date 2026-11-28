"""WP-04 A1 — production matrix parity.

Captures the transformed matrix that `PredictorV1_3.predict()` actually hands to the model and
compares it, feature by feature, with the matrix the benchmark builds for the same input.
No production preprocessing is changed; the capture wraps the module-level `transform` used by
the predictor.
"""
import importlib.util
import os
from pathlib import Path

import pandas as pd
import pytest

import app.models.xgboost.predictor_v1_3 as predictor_module
from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3
from app.models.xgboost.features_v1_3 import transform as real_transform
from app.models.xgboost.predictor_v1_3 import PredictorV1_3


def _artifacts_dir() -> Path:
    env = os.environ.get("SMARTPROP_V1_3_ARTIFACTS")
    return Path(env) if env else Path(__file__).resolve().parents[1] / "artifacts" / "v1_3"


@pytest.fixture(scope="module")
def predictor():
    directory = _artifacts_dir()
    if not (directory / "model.json").exists():
        pytest.skip(f"V1.3 artifacts not available at {directory}")
    return PredictorV1_3(directory)


CASES = {
    "house": {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0,
              "rooms": 3},
    "land": {"category": "Đất nền", "location_feature": "Cẩm Lệ", "area_sqm": 120.0,
             "road_width_m": 5.5, "frontage_width_m": 6.0},
    "apartment": {"category": "Căn hộ chung cư", "location_feature": "Hải Châu",
                  "area_sqm": 75.0, "rooms": 2},
    "villa": {"category": "Nhà ở", "location_feature": "Sơn Trà", "area_sqm": 150.0,
              "house_subtype": "villa", "floors": 3, "rooms": 4},
    "ward-prefixed": {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0,
                      "ward": "Phường 1"},
    "ward-missing": {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0},
    "ward-unknown": {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0,
                     "ward": "phường không tồn tại xyz"},
    "street-unknown": {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0,
                       "street_name": "Đường Không Tồn Tại 123"},
}


BENCH_PATH = Path(__file__).resolve().parents[2] / "docs" / "ai" / "benchmark" / \
    "wp04_explainability_benchmark.py"


def _bench_module():
    """The Phase A benchmark itself, so its preparation code is the single source of truth."""
    if not BENCH_PATH.exists():
        pytest.skip(f"benchmark not found at {BENCH_PATH}")
    spec = importlib.util.spec_from_file_location("wp04_bench", BENCH_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.map_v6_to_v1_3 = map_v6_to_v1_3
    return module


def benchmark_matrix(predictor, payload) -> pd.DataFrame:
    """Build the matrix with the benchmark's own prepare_matrix()."""
    frame, _mapped = _bench_module().prepare_matrix(
        payload, predictor.schema, map_v6_to_v1_3, real_transform, pd)
    return frame


def _legacy_benchmark_matrix(predictor, payload) -> pd.DataFrame:
    mapped = map_v6_to_v1_3(
        payload, district_vocabulary=predictor.schema.get("vocabularies", {}).get("district"))
    input_row = {
        "area": float(mapped["area"]),
        "raw_floor_count": mapped.get("floor_count"),
        "raw_frontage_width": mapped.get("frontage_width"),
        "raw_road_width": mapped.get("road_width"),
        "raw_bedroom_count": mapped.get("bedroom_count"),
        "raw_bathroom_count": mapped.get("bathroom_count"),
        "normalized_type": mapped["normalized_type"],
        "district": mapped["district"],
        "ward": mapped.get("ward"),
        "raw_street_name": mapped.get("street_name"),
        "raw_project_name": mapped.get("project_name"),
        "raw_house_direction": mapped.get("house_direction"),
        "raw_balcony_direction": mapped.get("balcony_direction"),
    }
    return real_transform(pd.DataFrame([input_row]), predictor.schema)


@pytest.fixture()
def capture_production_matrix(monkeypatch):
    captured = {}

    def capturing_transform(frame, schema):
        result = real_transform(frame, schema)
        captured["frame"] = result
        return result

    monkeypatch.setattr(predictor_module, "transform", capturing_transform)
    return captured


@pytest.mark.parametrize("name", list(CASES))
def test_production_matrix_matches_benchmark(predictor, capture_production_matrix, name):
    payload = CASES[name]
    predictor.predict_from_v6_payload(payload)

    production = capture_production_matrix.get("frame")
    assert production is not None, "no matrix captured: the predictor did not use transform"

    expected = benchmark_matrix(predictor, payload)

    assert list(production.columns) == list(expected.columns) == list(predictor.schema["features"])
    assert production.shape == expected.shape == (1, 22)
    pd.testing.assert_frame_equal(production, expected, check_dtype=True,
                                  check_categorical=True, check_exact=True,
                                  check_column_type=True)


def test_encoded_ward_sentinels(predictor, capture_production_matrix):
    predictor.predict_from_v6_payload(CASES["ward-missing"])
    assert capture_production_matrix["frame"].iloc[0]["ward"] == "__MISSING__"

    predictor.predict_from_v6_payload(CASES["ward-unknown"])
    assert capture_production_matrix["frame"].iloc[0]["ward"] == "__UNKNOWN__"

    predictor.predict_from_v6_payload(CASES["ward-prefixed"])
    # "Phường 1" is stripped to "1", which is not in the vocabulary
    assert capture_production_matrix["frame"].iloc[0]["ward"] == "__UNKNOWN__"


@pytest.mark.parametrize("mutation", ["value", "dtype", "order"])
def test_parity_gate_rejects_corrupted_matrix(predictor, capture_production_matrix, mutation):
    payload = CASES["house"]
    predictor.predict_from_v6_payload(payload)
    production = capture_production_matrix["frame"]
    expected = benchmark_matrix(predictor, payload).copy()

    if mutation == "value":
        expected.iloc[0, 0] = expected.iloc[0, 0] + 1.0
    elif mutation == "dtype":
        # object is guaranteed to differ from the numeric dtype transform() produces
        expected["area"] = expected["area"].astype("object")
    else:
        expected = expected[list(expected.columns)[::-1]]

    with pytest.raises(AssertionError):
        pd.testing.assert_frame_equal(production, expected, check_dtype=True,
                                      check_categorical=True, check_exact=True)


def test_invalid_numeric_is_rejected_before_the_matrix(predictor, monkeypatch):
    calls = {"n": 0}

    def counting_transform(frame, schema):
        calls["n"] += 1
        return real_transform(frame, schema)

    monkeypatch.setattr(predictor_module, "transform", counting_transform)
    with pytest.raises(ValueError):
        predictor.predict_from_v6_payload({"category": "Nhà ở",
                                           "location_feature": "Cẩm Lệ",
                                           "area_sqm": -5})
    assert calls["n"] == 0, "invalid numeric must be rejected before the feature transform"


def test_matrix_parity_over_full_synthetic_matrix(predictor):
    """Every one of the 105 synthetic cases, compared feature by feature."""
    bench = _bench_module()
    cases, extras = bench.build_cases(predictor.schema)
    assert len(cases) == 105, f"expected the 105-case matrix, got {len(cases)}"

    captured = []
    original = predictor_module.transform

    def capturing(frame, schema):
        result = original(frame, schema)
        captured.append(result)
        return result

    predictor_module.transform = capturing
    try:
        for case in cases:
            predictor.predict_from_v6_payload(case.payload)
            production = captured[-1]
            expected = bench.prepare_matrix(
                case.payload, predictor.schema, map_v6_to_v1_3, real_transform, pd)[0]
            pd.testing.assert_frame_equal(production, expected, check_dtype=True,
                                          check_categorical=True, check_exact=True)
        assert len(captured) == len(cases)

        for extra in extras:
            if extra.expectation != "SUCCESS":
                continue
            # An extra declared SUCCESS must actually succeed; a failure here is a defect,
            # not something to skip silently.
            predictor.predict_from_v6_payload(extra.payload)
            production = captured[-1]
            expected = bench.prepare_matrix(
                extra.payload, predictor.schema, map_v6_to_v1_3, real_transform, pd)[0]
            pd.testing.assert_frame_equal(production, expected, check_dtype=True,
                                          check_categorical=True, check_exact=True)
    finally:
        predictor_module.transform = original
