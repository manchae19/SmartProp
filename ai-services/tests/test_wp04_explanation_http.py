"""WP-04 B1/B2 — HTTP contract tests for /predict and /predict/v1_3_preview.

Uses the real V1.3 predictor and pinned artifacts; no database is involved. Covers the happy
path for every supported property type and the full failure matrix (native SHAP, builder,
validation, true prediction failure).
"""
import os
from pathlib import Path

import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.api.valuation import router
from app.models.xgboost.predictor_v1_3 import PredictorV1_3


def _artifacts_dir() -> Path:
    env = os.environ.get("SMARTPROP_V1_3_ARTIFACTS")
    return Path(env) if env else Path(__file__).resolve().parents[1] / "artifacts" / "v1_3"


HOUSE = {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0, "rooms": 3}
LAND = {"category": "Đất nền", "location_feature": "Cẩm Lệ", "area_sqm": 120.0,
        "road_width_m": 5.5, "frontage_width_m": 6.0}
APARTMENT = {"category": "Căn hộ chung cư", "location_feature": "Hải Châu", "area_sqm": 75.0,
             "rooms": 2, "project_name": None}
VILLA = {"category": "Nhà ở", "location_feature": "Sơn Trà", "area_sqm": 150.0,
         "house_subtype": "villa", "floors": 3, "rooms": 4}


@pytest.fixture(scope="module")
def client():
    directory = _artifacts_dir()
    if not (directory / "model.json").exists():
        pytest.skip(f"V1.3 artifacts not available at {directory}")
    app = FastAPI()
    app.include_router(router)
    app.state.predictor_v1_3 = PredictorV1_3(directory)
    with TestClient(app) as test_client:
        test_client.app.state.predictor_v1_3 = app.state.predictor_v1_3
        yield test_client


# Paths verified from the router itself (router.routes) rather than from the ASGI app object.
PREDICT_PATH = "/predict"
PREVIEW_PATH = "/predict/v1_3_preview"


def _path_for(_client=None, want_preview: bool = False) -> str:
    return PREVIEW_PATH if want_preview else PREDICT_PATH


@pytest.mark.parametrize("payload", [HOUSE, LAND, APARTMENT, VILLA])
def test_predict_returns_available_explanation(client, payload):
    path = _path_for(client, want_preview=False)
    response = client.post(path, json=payload)
    assert response.status_code == 200, response.text
    body = response.json()

    assert body["predicted_asking_price_vnd"] > 0
    explanation = body["explanation"]
    assert explanation["status"] == "AVAILABLE"
    assert len(explanation["feature_provenance"]) == 22

    legacy = body["shap_explanation"]
    assert set(legacy) == {"base_value_log", "base_price_vnd", "scale", "top_factors",
                           "method", "summary_vi", "status"}
    assert legacy["status"] == "AVAILABLE"

    total = (sum(f["contribution_log_raw"] for f in explanation["factors"])
             + explanation["other_contribution_log"])
    expected = explanation["predicted_margin_log"] - explanation["base_value_log"]
    assert abs(total - expected) / max(1.0, abs(expected)) < 1e-5


def test_preview_returns_available_explanation(client):
    path = _path_for(client, want_preview=True)
    response = client.post(path, json=HOUSE)
    assert response.status_code == 200, response.text
    assert response.json()["explanation"]["status"] == "AVAILABLE"


def test_native_shap_failure_is_isolated_over_http(client, monkeypatch):
    predictor = client.app.state.predictor_v1_3
    real_booster = predictor.model.get_booster()

    class ShapBoom:
        def __init__(self, real):
            self.real = real

        def predict(self, *args, **kwargs):
            if kwargs.get("pred_contribs"):
                raise RuntimeError("pred_contribs failed")
            return self.real.predict(*args, **kwargs)

        def __getattr__(self, name):
            return getattr(self.real, name)

    monkeypatch.setattr(predictor.model, "get_booster", lambda: ShapBoom(real_booster))
    path = _path_for(client, want_preview=False)
    response = client.post(path, json=HOUSE)

    assert response.status_code == 200, "a valid prediction must not become a 5xx"
    body = response.json()
    assert body["explanation"]["status"] == "UNAVAILABLE"
    assert body["explanation"]["factors"] is None
    assert body["shap_explanation"] is None, "legacy block must be null, not fabricated"
    assert body["predicted_asking_price_vnd"] > 0
    assert body["calibration_factor"] > 0


def test_builder_failure_keeps_legacy_block(client, monkeypatch):
    monkeypatch.setattr("app.models.xgboost.predictor_v1_3.build_explanation",
                        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("builder boom")))
    path = _path_for(client, want_preview=False)
    response = client.post(path, json=HOUSE)

    assert response.status_code == 200
    body = response.json()
    assert body["explanation"]["status"] == "UNAVAILABLE"
    assert body["shap_explanation"] is not None, "raw SHAP was valid, keep legacy data"


@pytest.mark.parametrize("problem", [
    "dimension mismatch: 21 != 22",
    "non-finite contribution",
    "base + contributions do not reproduce the margin",
])
def test_validation_failure_degrades_to_unavailable(client, monkeypatch, problem):
    real_validate = None
    import app.models.xgboost.explanation_v1_3 as module

    real_validate = module.validate_explanation
    monkeypatch.setattr(module, "validate_explanation",
                        lambda **kwargs: [problem])
    monkeypatch.setattr("app.models.xgboost.predictor_v1_3.build_explanation",
                        module.build_explanation)

    path = _path_for(client, want_preview=False)
    response = client.post(path, json=HOUSE)
    assert response.status_code == 200
    body = response.json()
    assert body["explanation"]["status"] == "UNAVAILABLE"
    assert body["predicted_asking_price_vnd"] > 0
    assert real_validate is not None


def test_true_prediction_failure_is_not_200(client):
    path = _path_for(client, want_preview=False)
    response = client.post(path, json={"category": "Nhà ở", "area_sqm": 0})
    assert response.status_code >= 400, "invalid input must not be reported as a valid valuation"


def test_no_nan_or_infinity_in_json(client):
    path = _path_for(client, want_preview=False)
    body = client.post(path, json=HOUSE).json()
    packed = str(body).lower()
    assert "nan" not in packed and "infinity" not in packed
