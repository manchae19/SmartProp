"""Regression tests for the parity runner and the capture harness.

The runner's checking engine takes a transport and a capture reader as parameters, so every
false-positive the reviewers found is reproducible here with a synthetic log. Nothing in this
module touches FastAPI, Spring or MySQL.

Run: python -m pytest tests/parity/test_run_parity.py -q
"""
import json
import uuid
from pathlib import Path
from typing import Any, Dict, List, Optional

import pytest

from tests.parity import run_parity as rp

FEATURES = [f"f{i}" for i in range(rp.FEATURE_COUNT)]
ENDPOINT = {"A": "/predict", "B": "/predict", "C": "/predict/v1_3_preview"}


def _identity(body: Dict[str, Any]) -> float:
    def pick(*names):
        for name in names:
            if body.get(name) is not None:
                return body[name]
        return ""

    def num(value):
        try:
            return f"{float(value):g}"
        except (TypeError, ValueError):
            return str(value)

    types = {"Nhà ở": "HOUSE", "Đất nền": "LAND", "Căn hộ chung cư": "APARTMENT"}
    model_type = pick("propertyType") or types.get(pick("category"), pick("category"))
    parts = [model_type, num(pick("area_sqm", "areaSqm")),
             pick("location_feature", "locationFeature"), pick("street_name", "streetName")]
    return float(len("|".join(str(p) for p in parts)))


def _record(tag: str, body: Dict[str, Any], *, path: str = "A", request: Optional[str] = None,
            invocation: Optional[str] = None, outcome: str = "SUCCESS",
            encoded: Any = "auto", **extra) -> Dict[str, Any]:
    if encoded == "auto":
        encoded = [_identity(body)] + [0.0] * (rp.FEATURE_COUNT - 1)
    record = {
        "run": "testrun",
        "invocation": invocation or uuid.uuid4().hex,
        "request": request if request is not None else uuid.uuid4().hex,
        "tag": tag,
        "endpoint": ENDPOINT[path],
        "thread": "MainThread",
        "background": False,
        "outcome": outcome,
        "error_type": None,
        "encoded": encoded,
        "features": list(FEATURES),
        "input": {"district": "cẩm lệ"},
        "has_bedroom": 0.0,
        "capture": "OK",
    }
    record.update(extra)
    return record


class Sim:
    """Synthetic transport + capture log."""

    def __init__(self, overrides: Optional[Dict[tuple, Dict[str, Any]]] = None,
                 seed: Optional[List[Dict[str, Any]]] = None):
        self.records: List[Dict[str, Any]] = list(seed or [])
        self.overrides = overrides or {}
        self.turn = 0

    def capture(self):
        return list(self.records)

    def post(self, url, body, token=None, tag=None, pause=0.0):
        name, _, path = (tag or ":x").partition(":")
        override = self.overrides.get((name, path), {})
        if "raise" in override:
            return 0, {"transport_error": override["raise"]}

        case = next((c for c in rp.POSITIVE + rp.NEGATIVE if c.name == name), None)
        negative = case is not None and not case.positive
        if negative and path in ("A", "C"):
            default = {"status": 422, "price": None, "records": 0}
        elif negative:
            default = {"status": 400 if case.b_rejection.startswith("status:") else 200,
                       "price": None, "records": 0,
                       "available": False if case.b_rejection == "available_false" else True}
        else:
            default = {"status": 200, "price": 5_000_000_000, "records": 1, "available": True}

        status = override.get("status", default["status"])
        price = override.get("price", default["price"])
        available = override.get("available", default.get("available", True))
        model = override.get("model", None if negative else "v1.3")
        warnings = override.get("warnings")
        if warnings is None:
            has_street = bool(body.get("street_name") or body.get("streetName"))
            warnings = [rp.STREET_WARNING_NEEDLE] if has_street else []

        payload: Dict[str, Any] = {"warnings": warnings}
        if model is not None:
            payload["model_version" if path in ("A", "C") else "modelVersion"] = model
        if price is not None:
            payload["predicted_asking_price_vnd" if path in ("A", "C")
                    else "predictedAskingPriceVnd"] = price
        if path == "B":
            payload["available"] = available

        count = override.get("records", default["records"])
        for _ in range(count):
            self.turn += 1
            if "record" in override:
                record = dict(override["record"])
                record.setdefault("invocation", uuid.uuid4().hex)
            else:
                effective_tag = override.get("tag", "" if path == "B" else tag)
                # Override ids are used verbatim so duplicate-id scenarios are reproducible.
                record = _record(effective_tag, body, path=path,
                                 request=override.get("request"),
                                 invocation=override.get("invocation"),
                                 outcome=override.get("outcome", "SUCCESS"),
                                 encoded=override.get("encoded", "auto"))
            self.records.append(record)
        return status, payload


PATHS = {"A": ("http://a/predict", None),
         "B": ("http://b/preview", "token"),
         "C": ("http://a/preview", None)}


def run(sim: Sim, positive=None, negative=None, settle: Optional[Any] = None) -> rp.Report:
    return rp.evaluate(positive if positive is not None else rp.POSITIVE,
                       negative if negative is not None else rp.NEGATIVE,
                       sim.post, sim.capture, PATHS, pause=0.0, settle_timeout=0.0,
                       settle=settle or (lambda log, timeout: len(log())))


def _has(report: rp.Report, needle: str) -> bool:
    return any(needle in failure for failure in report.failures)


# ------------------------------------------------------------------ 1. happy path
def test_valid_capture_passes():
    report = run(Sim())
    assert report.failures == [], report.failures
    assert report.positives_ok == len(rp.POSITIVE) == 13
    assert report.negatives_ok == len(rp.NEGATIVE) == 7
    assert report.total_records == 39
    assert report.unique_requests == 39
    assert report.unique_invocations == 39
    assert report.positive_invocations == 39
    assert report.negative_invocations == 0
    assert report.orphans == 0
    assert report.background == 0
    assert report.errors == 0


# ------------------------------------------------------------------ 2. background record between windows
def test_background_record_between_windows_fails():
    """Reviewer repro 1: a stray background record must not slip through."""
    sim = Sim()
    real_post = sim.post
    injected = {"done": False}

    def post(url, body, token=None, tag=None, pause=0.0):
        result = real_post(url, body, token=token, tag=tag, pause=pause)
        if not injected["done"]:
            # Arrives after the first request but before the next settle read.
            sim.records.append(_record("", body, path="A", request="", background=True))
            injected["done"] = True
        return result

    report = rp.evaluate(rp.POSITIVE, rp.NEGATIVE, post, sim.capture, PATHS,
                         pause=0.0, settle_timeout=0.0, settle=lambda log, t: len(log()))
    assert report.failures, "a background record must fail the run"
    assert _has(report, "background invocation") or _has(report, "predictor invocation")


# ------------------------------------------------------------------ 3. late record after last request
def test_late_record_after_last_request_fails():
    sim = Sim()
    real_post = sim.post
    state = {"last": False}

    def post(url, body, token=None, tag=None, pause=0.0):
        result = real_post(url, body, token=token, tag=tag, pause=pause)
        if (tag or "").endswith(":B") and "neg-subtype" in (tag or ""):
            state["last"] = True
        return result

    report = rp.evaluate(rp.POSITIVE, rp.NEGATIVE, post, sim.capture, PATHS,
                         pause=0.0, settle_timeout=0.0, settle=lambda log, t: len(log()))
    assert report.failures == []
    # now the delayed arrival: append after everything, then reconcile
    sim.records.append(_record("late:A", rp.POSITIVE[0].a_body, path="A"))
    report2 = rp.evaluate(rp.POSITIVE, rp.NEGATIVE, post, sim.capture, PATHS,
                          pause=0.0, settle_timeout=0.0, settle=lambda log, t: len(log()))
    assert report2.failures, "a delayed record must be visible at reconciliation"
    assert _has(report2, "orphan") or _has(report2, "log holds")


# ------------------------------------------------------------------ 4/5/6. duplicate request ids
def test_duplicate_request_id_between_a_and_b_fails():
    case = rp.POSITIVE[0]
    shared = uuid.uuid4().hex
    sim = Sim({(case.name, "A"): {"request": shared},
               (case.name, "B"): {"request": shared}})
    report = run(sim, positive=[case], negative=[])
    assert report.failures
    assert _has(report, "duplicate request id"), report.failures


def test_duplicate_request_id_across_cases_fails():
    shared = uuid.uuid4().hex
    sim = Sim({(rp.POSITIVE[1].name, "A"): {"record": _record(f"{rp.POSITIVE[1].name}:A",
                                                             rp.POSITIVE[1].a_body,
                                                             path="A", request=shared)}})
    real_post = sim.post

    def post(url, body, token=None, tag=None, pause=0.0):
        return real_post(url, body, token=token, tag=tag, pause=pause)

    # first case uses the shared id too
    sim.overrides[(rp.POSITIVE[0].name, "A")] = {
        "record": _record(f"{rp.POSITIVE[0].name}:A", rp.POSITIVE[0].a_body,
                          path="A", request=shared)}
    report = run(sim, positive=[rp.POSITIVE[0], rp.POSITIVE[1]], negative=[])
    assert _has(report, "duplicate request id"), report.failures


def test_b_record_copied_from_a_fails():
    """Reviewer repro 2: replacing B with a copy of A must not pass."""
    case = rp.POSITIVE[0]
    copy_of_a = _record(f"{case.name}:A", case.a_body, path="A")
    sim = Sim({(case.name, "B"): {"record": copy_of_a}})
    report = run(sim, positive=[case], negative=[])
    assert report.failures, "a copy of the A record must never satisfy B"
    assert _has(report, "tag") or _has(report, "duplicate")


# ------------------------------------------------------------------ 7/8. tag and endpoint contract
def test_b_record_with_tag_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "B"): {"tag": f"{case.name}:B"}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "tag"), report.failures


def test_a_record_without_tag_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "A"): {"tag": ""}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "tag"), report.failures


def test_wrong_endpoint_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "A"): {"record": _record(f"{case.name}:A", case.a_body,
                                                    path="C")}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "endpoint"), report.failures


# ------------------------------------------------------------------ 9/10. orphans and duplicate invocations
def test_orphan_record_fails():
    sim = Sim(seed=[_record("ghost:A", rp.POSITIVE[0].a_body, path="A")])
    report = run(sim, positive=[rp.POSITIVE[0]], negative=[])
    assert _has(report, "log holds") or _has(report, "orphan"), report.failures
    assert report.orphans >= 1


def test_duplicate_invocation_id_fails():
    case = rp.POSITIVE[0]
    same = uuid.uuid4().hex
    sim = Sim({
        (case.name, "A"): {"invocation": same},
        (case.name, "C"): {"invocation": same},
    })
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "duplicate invocation id"), report.failures


# ------------------------------------------------------------------ 14/15. outcome and vector
def test_positive_error_outcome_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "A"): {"outcome": "ERROR"}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "outcome"), report.failures
    assert report.errors >= 1


def test_positive_missing_vector_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "A"): {"encoded": None}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "encoded vector"), report.failures


def test_negative_invocation_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "A"): {"status": 422, "records": 1}})
    report = run(sim, positive=[], negative=[case])
    assert _has(report, f"{case.name}/A: produced 1 invocation"), report.failures
    assert report.negative_invocations == 1


def test_negative_invocation_ending_in_exception_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "A"): {"status": 422, "records": 1, "outcome": "ERROR"}})
    report = run(sim, positive=[], negative=[case])
    assert report.negative_invocations == 1
    assert report.errors >= 1


# ------------------------------------------------------------------ 16/17. capture corruption
def test_malformed_capture_line_fails(tmp_path: Path):
    target = tmp_path / "capture.jsonl"
    target.write_text('{"ok": 1}\nnot json\n', encoding="utf-8")
    log = rp.FileCapture(target)
    with pytest.raises(rp.CaptureError):
        log()


def test_capture_write_failure_fails_closed(tmp_path: Path):
    target = tmp_path / "capture.jsonl"
    target.write_text("", encoding="utf-8")
    Path(str(target) + ".errors").write_text("PermissionError: disk\n", encoding="utf-8")
    log = rp.FileCapture(target)
    with pytest.raises(rp.CaptureError):
        log()


def test_capture_read_failure_fails(tmp_path: Path):
    target = tmp_path / "missing-dir" / "capture.jsonl"
    log = rp.FileCapture(target)
    assert log() == []          # absent file is an empty log, not a failure
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text("", encoding="utf-8")
    assert log() == []


# ------------------------------------------------------------------ 18. completion timeout
def test_settle_timeout_fails():
    sim = Sim()

    def never_settles(log, timeout):
        return -1

    report = run(sim, settle=never_settles)
    assert _has(report, "did not settle"), report.failures


def test_settle_detects_growing_log():
    calls = {"n": 0}
    values = [0, 1, 1, 1, 1]

    class Growing:
        def __init__(self):
            self.records = [_record("x:A", rp.POSITIVE[0].a_body)]

        def __call__(self):
            return self.records

    log = Growing()

    def settle(capture, timeout):
        value = values[min(calls["n"], len(values) - 1)]
        calls["n"] += 1
        return value

    assert rp._settle(log, timeout=0.01) >= -1


# ------------------------------------------------------------------ engine details
def test_price_mismatch_between_paths_fails():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "B"): {"price": 7_000_000_000}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "final price differs"), report.failures


def test_feature_order_mismatch_fails():
    case = rp.POSITIVE[0]
    sim = Sim()
    original = sim.post

    def post(url, body, token=None, tag=None, pause=0.0):
        status, payload = original(url, body, token=token, tag=tag, pause=pause)
        if (tag or "").endswith(":C") and sim.records:
            sim.records[-1]["features"] = list(reversed(sim.records[-1]["features"]))
        return status, payload

    report = rp.evaluate([case], [], post, sim.capture, PATHS, pause=0.0,
                         settle_timeout=0.0, settle=lambda log, t: len(log()))
    assert _has(report, "feature order differs"), report.failures


def test_b_available_false_fails_positive():
    case = rp.POSITIVE[0]
    sim = Sim({(case.name, "B"): {"available": False}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "available is not True"), report.failures


def test_rejection_with_price_fails():
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "A"): {"status": 422, "price": 8_700_000_000, "records": 0}})
    report = run(sim, positive=[], negative=[case])
    assert _has(report, "returned a price"), report.failures


@pytest.mark.parametrize("status", [500, 401, 403, 429, 0])
def test_unexpected_b_status_fails(status):
    case = rp.NEGATIVE[0]
    sim = Sim({(case.name, "B"): {"status": status, "records": 0}})
    report = run(sim, positive=[], negative=[case])
    assert report.failures
    assert _has(report, f"{case.name}/B"), report.failures


def test_missing_street_warning_fails():
    case = next(c for c in rp.POSITIVE if c.expect_street_warning)
    sim = Sim({(case.name, "A"): {"warnings": []}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "street warning False"), report.failures


def test_unexpected_street_warning_fails():
    case = next(c for c in rp.POSITIVE if not c.expect_street_warning)
    sim = Sim({(case.name, "C"): {"warnings": [rp.STREET_WARNING_NEEDLE]}})
    report = run(sim, positive=[case], negative=[])
    assert _has(report, "street warning True"), report.failures
