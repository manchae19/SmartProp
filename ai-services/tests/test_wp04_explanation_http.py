"""WP-04 B1/B2 — HTTP contract tests for both valuation endpoints.

Real V1.3 predictor, pinned artifacts, no database. Covers happy path for every supported
property type, and the failure matrix injected at the NATIVE SHAP OUTPUT (not into the
validator): exception, NaN, Infinity, dimension mismatch, additivity mismatch, margin
mismatch, and builder-only failure.
"""
import json
import math
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.valuation import router
from app.models.xgboost.predictor_v1_3 import PredictorV1_3

PREDICT_PATH = "/predict"
PREVIEW_PATH = "/predict/v1_3_preview"
ENDPOINTS = [PREDICT_PATH, PREVIEW_PATH]
LEGACY_KEYS = {"base_value_log", "base_price_vnd", "scale", "top_factors", "method",
               "summary_vi"}

HOUSE = {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0, "rooms": 3}
LAND = {"category": "Đất nền", "location_feature": "Cẩm Lệ", "area_sqm": 120.0,
        "road_width_m": 5.5, "frontage_width_m": 6.0}
APARTMENT = {"category": "Căn hộ chung cư", "location_feature": "Hải Châu", "area_sqm": 75.0,
             "rooms": 2}
VILLA = {"category": "Nhà ở", "location_feature": "Sơn Trà", "area_sqm": 150.0,
         "house_subtype": "villa", "floors": 3, "rooms": 4}
PAYLOADS = {"HOUSE": HOUSE, "LAND": LAND, "APARTMENT": APARTMENT, "VILLA": VILLA}


def _artifacts_dir() -> Path:
    env = os.environ.get("SMARTPROP_V1_3_ARTIFACTS")
    return Path(env) if env else Path(__file__).resolve().parents[1] / "artifacts" / "v1_3"


@pytest.fixture(scope="module")
def client():
    directory = _artifacts_dir()
    if not (directory / "model.json").exists():
        pytest.skip(f"V1.3 artifacts not available at {directory}")
    app = FastAPI()
    app.include_router(router)
    app.state.predictor_v1_3 = PredictorV1_3(directory)
    with TestClient(app) as test_client:
        yield test_client


def assert_all_finite(node, path="root"):
    """Recursive numeric finiteness check (no substring heuristics)."""
    if isinstance(node, dict):
        for key, value in node.items():
            assert_all_finite(value, f"{path}.{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            assert_all_finite(value, f"{path}[{index}]")
    elif isinstance(node, (int, float)) and not isinstance(node, bool):
        assert math.isfinite(float(node)), f"non-finite number at {path}: {node}"


def additivity(body):
    explanation = body["explanation"]
    total = (sum(f["contribution_log_raw"] for f in explanation["factors"])
             + explanation["other_contribution_log"])
    margin = explanation["predicted_margin_log"]
    base = explanation["base_value_log"]
    # Reviewed Phase A normalisation: residual against |margin|.
    return abs(margin - (base + total)) / max(1.0, abs(margin))


class ShapProxy:
    """Wraps the real booster and corrupts only the SHAP output."""

    def __init__(self, real, mode):
        self._real = real
        self._mode = mode

    def predict(self, *args, **kwargs):
        result = self._real.predict(*args, **kwargs)
        if not kwargs.get("pred_contribs"):
            if self._mode == "margin_mismatch":
                return result + 1.0
            return result
        array = result[0]
        if self._mode == "exception":
            raise RuntimeError("native pred_contribs failed")
        if self._mode == "nan":
            array = array.copy()
            array[0] = float("nan")
        elif self._mode == "inf":
            array = array.copy()
            array[0] = float("inf")
        elif self._mode == "dimension":
            array = array[:-1]
        elif self._mode == "additivity":
            array = array.copy()
            array[0] = array[0] + 1.0
        return [array]

    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.fixture()
def proxy_factory(client, monkeypatch):
    predictor = client.app.state.predictor_v1_3
    real_booster = predictor.model.get_booster()

    def install(mode):
        monkeypatch.setattr(predictor.model, "get_booster",
                            lambda: ShapProxy(real_booster, mode))
        return predictor

    return install


# ---------------------------------------------------------------- happy path
@pytest.mark.parametrize("path", ENDPOINTS)
@pytest.mark.parametrize("name", list(PAYLOADS))
def test_available_explanation_on_both_endpoints(client, path, name):
    response = client.post(path, json=PAYLOADS[name])
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["predicted_asking_price_vnd"] > 0
    explanation = body["explanation"]
    assert explanation["status"] == "AVAILABLE"
    assert len(explanation["feature_provenance"]) == 22
    assert additivity(body) <= 1e-5

    legacy = body["shap_explanation"]
    assert set(legacy) == LEGACY_KEYS, "legacy block keeps exactly the 6 legacy keys"
    assert legacy["base_value_log"] is not None

    assert_all_finite(body)
    json.dumps(body, allow_nan=False)          # strict JSON: raises on NaN/Infinity


# ---------------------------------------------------------------- SHAP failures
@pytest.mark.parametrize("mode", ["exception", "nan", "inf", "dimension",
                                  "additivity", "margin_mismatch"])
@pytest.mark.parametrize("path", ENDPOINTS)
def test_invalid_native_shap_degrades_but_keeps_price(client, proxy_factory, path, mode):
    baseline = client.post(path, json=HOUSE).json()["predicted_asking_price_vnd"]
    proxy_factory(mode)

    response = client.post(path, json=HOUSE)
    assert response.status_code == 200, "a valid prediction must stay a 200"
    body = response.json()

    assert body["explanation"]["status"] == "UNAVAILABLE"
    assert body["explanation"]["factors"] is None
    assert body["shap_explanation"] is None, "no fabricated legacy contribution"
    assert body["predicted_asking_price_vnd"] == baseline
    assert body["calibration_factor"] > 0

    assert_all_finite(body)
    json.dumps(body, allow_nan=False)


def test_builder_failure_keeps_valid_legacy_block(client, monkeypatch):
    monkeypatch.setattr(
        "app.models.xgboost.predictor_v1_3.build_explanation",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("builder boom")))
    response = client.post(PREDICT_PATH, json=HOUSE)

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"]["status"] == "UNAVAILABLE"
    assert set(body["shap_explanation"]) == LEGACY_KEYS
    assert body["shap_explanation"]["top_factors"], "native SHAP was valid, legacy kept"


# ---------------------------------------------------------------- input failures
def test_invalid_input_is_not_200(client):
    response = client.post(PREDICT_PATH, json={"category": "Nhà ở", "area_sqm": 0})
    assert response.status_code >= 400


def test_unknown_location_is_not_silently_served(client):
    response = client.post(PREDICT_PATH,
                           json={"category": "Nhà ở", "location_feature": "Hà Nội",
                                 "area_sqm": 100.0})
    assert response.status_code >= 400
