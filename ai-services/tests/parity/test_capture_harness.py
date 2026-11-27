"""Harness-level tests: every predictor invocation is recorded, including failing ones.

`capture_app` is imported without SMARTPROP_PARITY_CAPTURE, so the production app is untouched
and the wrappers are inert; each test points the module at a tmp file and drives
`_capturing_predict` directly.
"""
import json
from pathlib import Path

import pandas as pd
import pytest

from tests.parity import capture_app

COLUMNS = [f"f{i}" for i in range(22)]


def _target(tmp_path: Path, monkeypatch) -> Path:
    path = tmp_path / "capture.jsonl"
    monkeypatch.setattr(capture_app, "_TARGET", str(path))
    return path


def _records(path: Path):
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _fake_transform(monkeypatch, values=None):
    def transform(df, schema):
        return pd.DataFrame([[0.0] * 22] if values is None else [values], columns=COLUMNS)
    monkeypatch.setattr(capture_app, "_production_transform", transform)


def test_successful_invocation_is_recorded_with_vector(tmp_path, monkeypatch):
    path = _target(tmp_path, monkeypatch)
    _fake_transform(monkeypatch)
    def predict(self, payload):
        capture_app._capturing_transform(pd.DataFrame([{}]), {})
        return {"predicted_asking_price_vnd": 1}

    monkeypatch.setattr(capture_app, "_production_predict", predict)

    capture_app._capturing_predict(object(), {"area_sqm": 100.0})

    [record] = _records(path)
    assert record["outcome"] == "SUCCESS"
    assert record["capture"] == "OK"
    assert len(record["encoded"]) == 22
    assert record["features"] == COLUMNS
    assert record["invocation"] and record["run"]


def test_exception_before_transform_still_records_invocation(tmp_path, monkeypatch):
    path = _target(tmp_path, monkeypatch)
    _fake_transform(monkeypatch)

    def boom(self, payload):
        raise ValueError("before-transform")

    monkeypatch.setattr(capture_app, "_production_predict", boom)

    with pytest.raises(ValueError):
        capture_app._capturing_predict(object(), {})

    [record] = _records(path)
    assert record["outcome"] == "ERROR"
    assert record["error_type"] == "ValueError"
    assert record["encoded"] is None          # no vector was ever produced


def test_exception_after_transform_still_records_invocation_with_vector(tmp_path, monkeypatch):
    path = _target(tmp_path, monkeypatch)
    _fake_transform(monkeypatch)

    def boom(self, payload):
        capture_app._capturing_transform(pd.DataFrame([{}]), {})
        raise RuntimeError("after-transform")

    monkeypatch.setattr(capture_app, "_production_predict", boom)

    with pytest.raises(RuntimeError):
        capture_app._capturing_predict(object(), {})

    [record] = _records(path)
    assert record["outcome"] == "ERROR"
    assert record["error_type"] == "RuntimeError"
    assert len(record["encoded"]) == 22        # the vector that reached the model is kept


def test_two_invocations_produce_two_records(tmp_path, monkeypatch):
    """No deduplication: a second call for the same request is a second record."""
    path = _target(tmp_path, monkeypatch)
    _fake_transform(monkeypatch)
    monkeypatch.setattr(capture_app, "_production_predict",
                        lambda self, payload: {"predicted_asking_price_vnd": 1})

    capture_app._capturing_predict(object(), {})
    capture_app._capturing_predict(object(), {})

    records = _records(path)
    assert len(records) == 2
    assert records[0]["invocation"] != records[1]["invocation"]


def test_write_failure_is_surfaced_through_sidecar(tmp_path, monkeypatch):
    """A capture write failure must be visible to the runner, not silently swallowed."""
    # Capture path is a directory, so appending raises while the sidecar path stays writable -
    # the same shape as a real write failure.
    blocked = tmp_path / "blocked-capture"
    blocked.mkdir()
    monkeypatch.setattr(capture_app, "_TARGET", str(blocked))
    _fake_transform(monkeypatch)

    def predict(self, payload):
        capture_app._capturing_transform(pd.DataFrame([{}]), {})
        return {"predicted_asking_price_vnd": 1}

    monkeypatch.setattr(capture_app, "_production_predict", predict)

    # Must not raise: capture problems never change the response.
    capture_app._capturing_predict(object(), {})

    from tests.parity import run_parity as rp
    with pytest.raises(rp.CaptureError):
        rp.FileCapture(Path(str(blocked)))()
