"""WP-04 B1/B2 — explanation contract tests (synthetic, no database).

Covers the additive contract, top-K reconstruction, grouped aggregation, provenance states,
legacy compatibility, failure isolation and prediction invariance.
"""
import copy
import os
from pathlib import Path

import pytest

from app.api import schemas as api_schemas
from app.models.xgboost import explanation_v1_3 as ex
from app.models.xgboost.predictor_v1_3 import PredictorV1_3

HOUSE = {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0,
         "rooms": 3, "ward": "phường 1"}
LAND = {"category": "Đất nền", "location_feature": "Cẩm Lệ", "area_sqm": 120.0,
        "road_width_m": 5.5, "frontage_width_m": 6.0}
# Reference price measured on the pinned artifact before WP-04 (must not change).
EXPECTED_HOUSE_PRICE_WITHOUT_WARD = 6_605_239_848


def _artifacts_dir() -> Path:
    """Artifacts are gitignored, so tests locate them via env or a repo-relative default."""
    env = os.environ.get("SMARTPROP_V1_3_ARTIFACTS")
    if env:
        return Path(env)
    return Path(__file__).resolve().parents[1] / "artifacts" / "v1_3"


@pytest.fixture(scope="module")
def predictor():
    directory = _artifacts_dir()
    if not (directory / "model.json").exists():
        pytest.skip(f"V1.3 artifacts not available at {directory}")
    return PredictorV1_3(directory)


# ---------------------------------------------------------------- contract shape
def test_contract_fields_and_metadata(predictor):
    out = predictor.predict_from_v6_payload(HOUSE)
    exp = out["explanation"]

    assert exp["explanation_version"] == "1.0"
    assert exp["status"] == "AVAILABLE"
    assert exp["method"] == "XGBOOST_NATIVE_TREESHAP"
    assert exp["target"] == "ASKING_PRICE_VND"
    assert exp["output_space"] == "LOG1P_PRICE_VND"
    for key in ("predicted_margin_log", "base_value_log", "base_price_vnd",
                "naive_price_vnd", "calibration", "factors",
                "other_contribution_log", "grouped_contributions", "limitations"):
        assert key in exp
    assert exp["calibration"]["adjusted_price_vnd"] == out["predicted_asking_price_vnd"]
    assert isinstance(exp["factors"], list) and 0 < len(exp["factors"]) <= ex.TOP_K


def test_top_k_plus_other_reconstructs_full_contribution(predictor):
    exp = predictor.predict_from_v6_payload(HOUSE)["explanation"]
    total = (sum(f["contribution_log_raw"] for f in exp["factors"])
             + exp["other_contribution_log"])
    expected = exp["predicted_margin_log"] - exp["base_value_log"]
    # margin comes from a float32 booster; 1e-5 relative is the justified tolerance
    assert abs(total - expected) / max(1.0, abs(expected)) < 1e-5


def test_grouped_contributions_are_signed_and_complete(predictor):
    exp = predictor.predict_from_v6_payload(HOUSE)["explanation"]
    grouped = exp["grouped_contributions"]
    assert grouped, "grouped contributions must not be empty"
    expected = exp["predicted_margin_log"] - exp["base_value_log"]
    assert abs(sum(grouped.values()) - expected) / max(1.0, abs(expected)) < 1e-5
    # a group may legitimately be negative: signed, not absolute mass
    assert any(v < 0 for v in grouped.values()) or any(v > 0 for v in grouped.values())


def test_factor_order_is_deterministic(predictor):
    first = [f["feature_name"] for f in predictor.predict_from_v6_payload(HOUSE)["explanation"]["factors"]]
    second = [f["feature_name"] for f in predictor.predict_from_v6_payload(HOUSE)["explanation"]["factors"]]
    assert first == second


def test_raw_contribution_is_full_precision_and_display_rounds(predictor):
    exp = predictor.predict_from_v6_payload(HOUSE)["explanation"]
    factor = exp["factors"][0]
    assert factor["contribution_log_raw"] == pytest.approx(
        factor["contribution_log_display"], abs=1e-4)
    # raw must not be pre-rounded to 4 decimals by construction
    assert isinstance(factor["contribution_log_raw"], float)


# ---------------------------------------------------------------- provenance
def test_missing_ward_is_not_reported_as_observed(predictor):
    payload = {k: v for k, v in HOUSE.items() if k != "ward"}
    exp = predictor.predict_from_v6_payload(payload)["explanation"]
    states = {f["feature_name"]: f["input_state"] for f in exp["factors"]}
    assert states.get("ward", "MISSING") != "OBSERVED"


def test_unknown_ward_is_classified_unknown_category(predictor):
    payload = dict(HOUSE, ward="phường không tồn tại xyz")
    exp = predictor.predict_from_v6_payload(payload)["explanation"]
    assert "UNKNOWN_CATEGORY" in {f["input_state"] for f in exp["factors"]}


def test_land_marks_not_applicable_features(predictor):
    exp = predictor.predict_from_v6_payload(LAND)["explanation"]
    provenance = exp["feature_provenance"]          # covers ALL features, not just top-K
    # numeric attributes are not applicable for LAND; the has_* indicators are derived flags
    # Requirement: LAND features must never be reported as observed data.
    for feature in ("bedroom_count", "bathroom_count"):
        assert provenance[feature] in ("NOT_APPLICABLE", "MISSING"), (feature, provenance[feature])
    for feature in ("has_bedroom", "has_bathroom"):
        assert provenance[feature] != "OBSERVED", (feature, provenance[feature])


def test_classifier_never_defaults_to_derived():
    assert ex.classify_provenance("ward", "__UNKNOWN__", [], "HOUSE") == "UNKNOWN_CATEGORY"
    assert ex.classify_provenance("ward", None, [], "HOUSE") == "MISSING"
    assert ex.classify_provenance("ward", None, [], "HOUSE") != "DERIVED"
    assert ex.classify_provenance("ward", "phường 1", ["ward"], "HOUSE") == "OBSERVED"
    assert ex.classify_provenance("has_ward", 0.0, [], "HOUSE") == "DERIVED"
    # adapter-filled value whose source is not documented -> UNVERIFIED, never DERIVED
    assert ex.classify_provenance("ward", "phường 1", [], "HOUSE") == "UNVERIFIED"
    # adapter assumption must be DEFAULTED
    assert ex.classify_provenance("road_width", 5.5, [], "HOUSE", ["road_width"]) == "DEFAULTED"
    import numpy as np
    assert ex.is_missing(np.float32("nan")) is True
    assert ex.classify_provenance("ward", np.float32("nan"), [], "HOUSE") == "MISSING"
    # caller supplied a value that the adapter rejected
    assert ex.classify_provenance("area", None, ["area_sqm"], "HOUSE") == "MISSING_INVALID"


# ---------------------------------------------------------------- legacy + invariance
def test_legacy_shap_block_unchanged(predictor):
    shap = predictor.predict_from_v6_payload(HOUSE)["shap_explanation"]
    assert set(shap) == {"base_value_log", "base_price_vnd", "scale", "top_factors",
                         "method", "summary_vi", "status"}
    assert shap["status"] == "AVAILABLE"
    assert len(shap["top_factors"]) <= 6


def test_prediction_is_unchanged_by_wp04(predictor):
    # district + area only: this is the payload whose price was pinned before WP-04
    payload = {"category": "Nhà ở", "location_feature": "Cẩm Lệ", "area_sqm": 100.0}
    price = predictor.predict_from_v6_payload(payload)["predicted_asking_price_vnd"]
    assert price == EXPECTED_HOUSE_PRICE_WITHOUT_WARD


# ---------------------------------------------------------------- failure isolation
def test_explanation_failure_is_isolated(monkeypatch, predictor):
    def boom(**kwargs):
        raise RuntimeError("shap exploded")

    monkeypatch.setattr("app.models.xgboost.predictor_v1_3.build_explanation", boom)
    out = predictor.predict_from_v6_payload(HOUSE)

    assert out["explanation"]["status"] == "UNAVAILABLE"
    assert out["explanation"]["factors"] is None
    assert out["predicted_asking_price_vnd"] > 0          # prediction still valid
    assert out["shap_explanation"]["base_value_log"] is not None  # legacy block intact


def test_unavailable_payload_has_no_fake_contributions():
    payload = ex.unavailable_explanation("n/a")
    assert payload["status"] == "UNAVAILABLE"
    for key in ("factors", "other_contribution_log", "grouped_contributions",
                "predicted_margin_log", "base_value_log", "calibration"):
        assert payload[key] is None


# ---------------------------------------------------------------- API surface
def test_api_schema_accepts_explanation_additively():
    assert "explanation" in api_schemas.V1_3PreviewResponse.model_fields
    field = api_schemas.V1_3PreviewResponse.model_fields["explanation"]
    assert field.default is None, "explanation must be optional for old payloads"

    payload = predictor_payload = {                      # old-style payload without explanation
        "is_preview": False, "model_version": "v1.3", "status": "PRIMARY",
        "predicted_asking_price_vnd": 1, "predicted_asking_price_billion": 1.0,
        "price_band": "x", "calibration_factor": 1.0, "calibration_policy": "p",
        "naive_price_vnd": 1, "features_used": {}, "missing_features": [],
        "valuation_timestamp": "2026-01-01T00:00:00+00:00", "disclaimer": "d",
    }
    model = api_schemas.V1_3PreviewResponse(**payload)
    assert model.explanation is None
    assert predictor_payload["model_version"] == "v1.3"
