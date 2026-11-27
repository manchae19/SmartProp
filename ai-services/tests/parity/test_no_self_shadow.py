"""The V1.3 endpoints must perform exactly one primary inference and never self-shadow.

Background: `/predict` used to register a shadow task that re-ran *the same* V1.3 predictor
(`shadow_manager._execute_shadow_worker` calls `predictor_v1_3.predict_from_v6_payload`) and
compared it with the V1.3 response it was just handed. With a stale persisted
`shadow_state.json` containing `enabled: true`, that fired on every request and produced a
second inference after the response.

These tests build a minimal app around the real router and prove the dispatch is gone, using a
counting predictor and a shadow manager that would happily run.
"""
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from pydantic import BaseModel

from app.api import valuation as valuation_api


class _FakePredictor:
    def __init__(self, available=True):
        self.calls = []
        self.available = available

    def info(self):
        return {"supported_districts": ["Cẩm Lệ", "Hải Châu"], "model_version": "v1.3"}

    def predict_from_v6_payload(self, payload):
        self.calls.append(payload)
        return {
            "predicted_asking_price_vnd": 6_600_000_000,
            "predicted_asking_price_billion": 6.6,
            "price_band": "band",
            "calibration_factor": 1.0,
            "calibration_policy": "duan",
            "naive_price_vnd": 6_500_000_000,
            "features_used": {"area": payload.get("area_sqm"), "district": payload.get("location_feature")},
            "missing_features": [],
            "warnings": [],
            "shap_explanation": {
                "base_value_log": 20.0,
                "base_price_vnd": 5_000_000_000,
                "top_factors": [],
                "summary_vi": "Tổng hợp yếu tố chính.",
            },
        }


class _FakeShadowManager:
    """Enabled and ready to record - the endpoint must not call it."""

    def __init__(self):
        self.recorded = 0

    def is_enabled(self):
        return True

    def record_shadow_evaluation(self, **kwargs):
        self.recorded += 1


def _client(predictor=None, shadow=None, v6=None):
    app = FastAPI()
    app.include_router(valuation_api.router)
    app.state.predictor_v1_3 = predictor or _FakePredictor()
    app.state.shadow_manager = shadow
    app.state.predictor = v6
    return TestClient(app), app


BODY = {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"}


def test_primary_endpoint_infers_once_without_shadow():
    predictor = _FakePredictor()
    shadow = _FakeShadowManager()
    client, _ = _client(predictor, shadow, v6=object())

    response = client.post("/predict", json=BODY)

    assert response.status_code == 200
    assert len(predictor.calls) == 1, "primary endpoint must infer exactly once"
    assert shadow.recorded == 0, "a stale enabled shadow must not trigger a background inference"


def test_preview_endpoint_infers_once():
    predictor = _FakePredictor()
    client, _ = _client(predictor, _FakeShadowManager(), v6=object())

    response = client.post("/predict/v1_3_preview", json=BODY)

    assert response.status_code == 200
    assert len(predictor.calls) == 1


@pytest.mark.parametrize("body", [
    {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Hà Nội"},
    {"category": "Nhà ở", "area_sqm": 0, "location_feature": "Cẩm Lệ"},
    {"category": "Đất nền", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
     "balcony_direction": "Đông"},
])
def test_invalid_requests_never_infer(body):
    predictor = _FakePredictor()
    client, _ = _client(predictor, _FakeShadowManager(), v6=object())

    assert client.post("/predict", json=body).status_code == 422
    assert client.post("/predict/v1_3_preview", json=body).status_code == 422
    assert predictor.calls == []


def test_unavailable_model_is_503_and_does_not_infer():
    shadow = _FakeShadowManager()
    client, _ = _client(None, shadow, v6=object())
    client.app.state.predictor_v1_3 = None

    response = client.post("/predict", json=BODY)

    assert response.status_code == 503
    assert shadow.recorded == 0


def test_price_and_shap_are_preserved():
    predictor = _FakePredictor()
    client, _ = _client(predictor, _FakeShadowManager())

    payload = client.post("/predict", json=BODY).json()

    assert payload["predicted_asking_price_vnd"] == 6_600_000_000
    assert payload["model_version"] == "v1.3"
    assert payload["warnings"] == []
    assert payload["shap_explanation"]["base_price_vnd"] == 5_000_000_000
    assert payload["shap_explanation"]["top_factors"] == []
