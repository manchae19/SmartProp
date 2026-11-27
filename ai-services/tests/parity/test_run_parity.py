"""Regression tests for the parity runner itself.

The runner's checking logic is a pure function over a transport and a capture log, so every
false-positive scenario the reviewers found can be reproduced with a synthetic transport and
synthetic captures. These tests do not touch FastAPI, Spring or MySQL.

Run: python -m pytest tests/parity/test_run_parity.py -q
"""
import json
import uuid
from typing import Any, Dict, List, Optional

import pytest

from tests.parity import run_parity as rp

FEATURES = [f"f{i}" for i in range(rp.FEATURE_COUNT)]


def _key(body: Dict[str, Any]) -> float:
    """Stable per-property identity so a mixed-up capture produces a different vector."""
    def pick(*names):
        for name in names:
            if body.get(name) is not None:
                return body[name]
        return ""

    # A/C carry `category` (Vietnamese), B carries `propertyType` (enum): normalise both
    # to the same model type so the harness double compares like with like.
    TYPE = {"Nhà ở": "HOUSE", "Đất nền": "LAND", "Căn hộ chung cư": "APARTMENT", "Căn hộ": "APARTMENT"}
    model_type = pick("propertyType") or TYPE.get(pick("category"), pick("category"))

    def num(value):
        try:
            return f"{float(value):g}"   # 100.0 and 100 are the same property
        except (TypeError, ValueError):
            return str(value)

    parts = [
        model_type,
        num(pick("area_sqm", "areaSqm")),
        pick("location_feature", "locationFeature"),
        pick("street_name", "streetName"),
    ]
    return float(len("|".join(str(p) for p in parts)))


def _record(tag: str, body: Dict[str, Any], request: Optional[str] = None) -> Dict[str, Any]:
    return {
        "tag": tag,
        "request": request if request is not None else uuid.uuid4().hex,
        "background": request == "",
        "thread": "MainThread",
        "encoded": [_key(body)] + [0.0] * (rp.FEATURE_COUNT - 1),
        "features": list(FEATURES),
        "input": {"district": "cẩm lệ"},
        "has_bedroom": 0.0,
    }


def _has_street(body: Dict[str, Any]) -> bool:
    return bool(body.get("street_name") or body.get("streetName"))


class Sim:
    """Synthetic transport + capture log."""

    def __init__(self, overrides: Optional[Dict[tuple, Dict[str, Any]]] = None,
                 seed: Optional[List[Dict[str, Any]]] = None):
        self.records: List[Dict[str, Any]] = list(seed or [])
        self.overrides = overrides or {}

    # --- capture log port
    def capture(self) -> List[Dict[str, Any]]:
        return list(self.records)

    # --- transport port
    def post(self, url, body, token=None, tag=None, pause=0.0):
        name, _, path = (tag or ":x").partition(":")
        override = self.overrides.get((name, path), {})
        if "raise" in override:
            return 0, {"transport_error": override["raise"]}

        # Default behaviour follows the case contract: negative cases reject, positive
        # ones succeed. Overrides then inject the single defect under test.
        case = next((c for c in rp.POSITIVE + rp.NEGATIVE if c.name == name), None)
        is_negative = case is not None and not case.positive
        if is_negative and path in ("A", "C"):
            default_status, default_price, default_records = 422, None, 0
        elif is_negative:
            default_status = 400 if case.b_rejection.startswith("status:") else 200
            default_price, default_records = None, 0
            available_default = False if case.b_rejection == "available_false" else True
        else:
            default_status, default_price, default_records = 200, 5_000_000_000, 1

        status = override.get("status", default_status)
        available = override.get("available", locals().get("available_default", True))
        price = override.get("price", default_price)
        model = override.get("model", None if is_negative else "v1.3")
        warnings = override.get("warnings")
        if warnings is None:
            warnings = [rp.STREET_WARNING_NEEDLE] if _has_street(body) else []

        payload: Dict[str, Any] = {}
        if model is not None:
            payload["model_version" if path in ("A", "C") else "modelVersion"] = model
        if price is not None:
            payload["predicted_asking_price_vnd" if path in ("A", "C") else "predictedAskingPriceVnd"] = price
        if path == "B":
            payload["available"] = available
        payload["warnings"] = warnings

        count = override.get("records", default_records)
        # Each appended record is a distinct inference request unless the override asks for
        # repeats of the same inference (which must still agree on the vector).
        shared = uuid.uuid4().hex if override.get("same_request") else None
        for index in range(count):
            self.records.append(
                _record(override.get("tag", tag if path in ("A", "C") else ""), body, shared))
        return status, payload


PATHS = {"A": ("http://a/predict", None),
         "B": ("http://b/preview", "token"),
         "C": ("http://a/preview", None)}


def run(sim: Sim, positive=None, negative=None) -> rp.Report:
    return rp.evaluate(positive if positive is not None else rp.POSITIVE,
                       negative if negative is not None else rp.NEGATIVE,
                       sim.post, sim.capture, PATHS, pause=0.0, overlap_guard=0.0)


def _contains(report: rp.Report, needle: str) -> bool:
    return any(needle in failure for failure in report.failures)


# ---------------------------------------------------------------- 1. happy path
def test_valid_three_path_capture_passes():
    sim = Sim()
    report = run(sim)
    assert report.failures == [], report.failures
    assert report.positives_ok == len(rp.POSITIVE)
    assert report.negatives_ok == len(rp.NEGATIVE)
    assert report.actual_positive_records == len(rp.POSITIVE) * 3 == 39
    assert report.negative_records == 0


# ---------------------------------------------------------------- 2. missing B record
def test_missing_b_capture_fails():
    sim = Sim({("house-basic", "B"): {"records": 0}})
    report = run(sim)
    assert _contains(report, "house-basic/B: expected exactly 1 predictor invocation"), report.failures
    assert report.failures


# ---------------------------------------------------------------- 3. one B record reused across cases
def test_single_b_record_for_many_cases_fails():
    # Every B request returns no NEW record; one stale untagged record sits in the file.
    overrides = {(case.name, "B"): {"records": 0} for case in rp.POSITIVE}
    seed = [_record("", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"})]
    report = run(Sim(overrides, seed=seed))
    assert _contains(report, "/B: expected exactly 1 predictor invocation"), report.failures
    assert report.actual_positive_records < report.expected_positive_records


# ---------------------------------------------------------------- 4. stale B record with identical vector
def test_stale_b_record_with_same_vector_fails():
    case = rp.POSITIVE[0]
    stale = _record("", case.a_body)  # identical vector to what B would produce
    sim = Sim({(case.name, "B"): {"records": 0}}, seed=[stale])
    report = run(sim, positive=[case], negative=[])
    assert report.failures, "a reused stale record must not satisfy parity"
    assert _contains(report, f"{case.name}/B"), report.failures


# ---------------------------------------------------------------- 5. extra record
def test_extra_capture_fails():
    sim = Sim({("house-basic", "B"): {"records": 2}})
    report = run(sim)
    assert _contains(report, "house-basic/B: expected exactly 1 predictor invocation"), report.failures


# ---------------------------------------------------------------- 6. wrong case tag
def test_wrong_case_tag_fails():
    sim = Sim({("house-basic", "A"): {"tag": "some-other-case:A"}})
    report = run(sim)
    assert _contains(report, "house-basic/A: capture tag"), report.failures


# ---------------------------------------------------------------- 7/8. 422 with a price
@pytest.mark.parametrize("path", ["A", "C"])
def test_rejection_returning_a_price_fails(path):
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, path): {"status": 422, "price": 8_700_000_000, "records": 0}})
    report = run(sim, positive=[], negative=[case])
    assert _contains(report, f"{case.name}/{path}: returned a price"), report.failures


# ---------------------------------------------------------------- 9/10. bad B statuses
@pytest.mark.parametrize("status", [500, 401, 403, 429, 0])
def test_unexpected_b_status_fails(status):
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "B"): {"status": status, "records": 0}})
    report = run(sim, positive=[], negative=[case])
    assert report.failures, f"B must reject status {status}"
    assert _contains(report, f"{case.name}/B"), report.failures


# ---------------------------------------------------------------- 11. available=false with a price
def test_available_false_with_price_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "B"): {"status": 200, "available": False,
                                  "price": 8_700_000_000, "records": 0}})
    report = run(sim, positive=[], negative=[case])
    assert _contains(report, f"{case.name}/B: returned a price"), report.failures


# ---------------------------------------------------------------- 12. negative produces inference
def test_negative_case_producing_inference_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "A"): {"status": 422, "records": 1}})
    report = run(sim, positive=[], negative=[case])
    assert _contains(report, f"{case.name}/A: produced 1 inference record"), report.failures
    assert report.negative_records == 1


# ---------------------------------------------------------------- 13. missing expected warning
def test_missing_street_warning_fails():
    case = next(c for c in rp.POSITIVE if c.expect_street_warning)
    sim = Sim({(case.name, "A"): {"warnings": []}})
    report = run(sim, positive=[case], negative=[])
    assert _contains(report, f"{case.name}/A: street warning False"), report.failures


# ---------------------------------------------------------------- 14. unexpected warning
def test_unexpected_street_warning_fails():
    case = next(c for c in rp.POSITIVE if not c.expect_street_warning)
    sim = Sim({(case.name, "C"): {"warnings": [rp.STREET_WARNING_NEEDLE]}})
    report = run(sim, positive=[case], negative=[])
    assert _contains(report, f"{case.name}/C: street warning True"), report.failures


# ---------------------------------------------------------------- 15. missing available=true
def test_positive_b_without_available_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "B"): {"available": None}})
    report = run(sim, positive=[case], negative=[])
    assert _contains(report, f"{case.name}/B: available is not True"), report.failures


# ---------------------------------------------------------------- extras
def test_price_mismatch_between_paths_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "B"): {"price": 7_000_000_000}})
    report = run(sim, positive=[case], negative=[])
    assert _contains(report, f"{case.name}: final price differs"), report.failures


def test_feature_order_mismatch_fails():
    case = rp.POSITIVE[0]
    sim = Sim()
    original = sim.post

    def post(url, body, token=None, tag=None, pause=0.0):
        status, payload = original(url, body, token=token, tag=tag, pause=pause)
        if (tag or "").endswith(":C") and sim.records:
            sim.records[-1]["features"] = list(reversed(sim.records[-1]["features"]))
        return status, payload

    report = rp.evaluate([case], [], post, sim.capture, PATHS, pause=0.0, overlap_guard=0.0)
    assert _contains(report, f"{case.name}: feature order differs"), report.failures


def test_transport_error_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "B"): {"raise": "connection refused"}})
    report = run(sim, positive=[], negative=[case])
    assert report.failures
    assert _contains(report, f"{case.name}/B"), report.failures
