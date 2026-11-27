"""Test-only harness: record EVERY predictor invocation, success or failure.

Production keeps no capture code. This module wraps the real app and spies on
`PredictorV1_3.predict_from_v6_payload` — the actual inference entry point.

Each invocation produces exactly one record, written in a `finally` block so an invocation that
raises is still counted (a positive case with an ERROR outcome must fail the parity run, and a
negative case must produce no invocation at all). Records carry their own identity so the
runner can reconcile the whole log instead of trusting per-request counts:

    run      unique id of this capture session
    invocation  unique id of this predictor call
    request  HTTP request id (empty means background / outside a request)
    tag      X-Parity-Case header (Spring does not forward it -> empty for path B)
    endpoint request path
    background, outcome (SUCCESS|ERROR), encoded, features

Write failures are surfaced through a `<capture>.errors` sidecar so the runner can fail closed
instead of silently losing records.

Run:
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001
"""
import json
import os
import threading
import uuid
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware

from app.models.xgboost import predictor_v1_3 as predictor_module
from main import app as production_app

_TARGET = os.environ.get("SMARTPROP_PARITY_CAPTURE")

_TAG: ContextVar[str] = ContextVar("parity_tag", default="")
_REQID: ContextVar[str] = ContextVar("parity_request_id", default="")
_PATH: ContextVar[str] = ContextVar("parity_path", default="")
_COLLECTED: ContextVar[object] = ContextVar("parity_collected", default=None)

_RUN = uuid.uuid4().hex[:12]
_WRITE_LOCK = threading.Lock()

RECORD_INPUT_KEYS = (
    "normalized_type", "district", "ward",
    "area", "floor_count", "frontage_width", "road_width",
    "bedroom_count", "bathroom_count",
    "street_name", "project_name",
    "house_direction", "balcony_direction",
)

_production_transform = predictor_module.transform
_production_predict = predictor_module.PredictorV1_3.predict_from_v6_payload


def _scalar(value):
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None
    except (TypeError, ValueError):
        return str(value)


def _capturing_transform(df, schema):
    encoded = _production_transform(df, schema)
    box = _COLLECTED.get()
    if isinstance(box, dict) and "encoded" not in box:
        try:
            box["encoded"] = [_scalar(v) for v in encoded.iloc[0].tolist()]
            box["features"] = list(encoded.columns)
            box["input"] = {k: (None if df.iloc[0][k] is None else str(df.iloc[0][k]))
                            for k in RECORD_INPUT_KEYS if k in df.columns}
            box["has_bedroom"] = float(encoded.iloc[0].get("has_bedroom", -1))
        except Exception:  # noqa: BLE001 - capture must never change the response
            box["capture_error"] = True
    return encoded


def _write(payload):
    """Append one record. Failures go to a sidecar the runner treats as fatal."""
    if not _TARGET:
        return
    line = json.dumps(payload, ensure_ascii=False, sort_keys=True)
    with _WRITE_LOCK:
        try:
            with open(_TARGET, "a", encoding="utf-8") as handle:
                handle.write(line + "\n")
        except OSError as error:
            try:
                with open(_TARGET + ".errors", "a", encoding="utf-8") as handle:
                    handle.write(f"{type(error).__name__}: {error}\n")
            except OSError:
                pass


def _capturing_predict(self, v6_payload):
    box = {"tag": _TAG.get()}
    token = _COLLECTED.set(box)
    outcome, error_type = "ERROR", None
    try:
        result = _production_predict(self, v6_payload)
        outcome = "SUCCESS"
        return result
    except BaseException as error:  # noqa: BLE001 - re-raised unchanged
        error_type = type(error).__name__
        raise
    finally:
        _COLLECTED.reset(token)
        try:
            record = {
                "run": _RUN,
                "invocation": uuid.uuid4().hex,
                "request": _REQID.get(),
                "tag": box.get("tag", ""),
                "endpoint": _PATH.get(),
                "thread": threading.current_thread().name,
                "background": _REQID.get() == "",
                "outcome": outcome,
                "error_type": error_type,          # exception class only, never the message
                "encoded": box.get("encoded"),
                "features": box.get("features"),
                "input": box.get("input"),
                "has_bedroom": box.get("has_bedroom"),
                "capture": "ERROR" if box.get("capture_error") else "OK",
            }
            _write(record)
        except Exception:  # noqa: BLE001 - never disturb the response
            try:
                _write({"run": _RUN, "capture": "ERROR", "outcome": outcome})
            except Exception:
                pass


class _ContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tag = request.headers.get("x-parity-case", "")
        tag_token = _TAG.set(tag)
        id_token = _REQID.set(uuid.uuid4().hex)
        path_token = _PATH.set(request.url.path)
        try:
            return await call_next(request)
        finally:
            _PATH.reset(path_token)
            _REQID.reset(id_token)
            _TAG.reset(tag_token)


app = production_app
if _TARGET:
    predictor_module.transform = _capturing_transform
    predictor_module.PredictorV1_3.predict_from_v6_payload = _capturing_predict
    app.add_middleware(_ContextMiddleware)
