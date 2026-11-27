"""Test-only harness: capture the ACTUAL inference input, one record per inference.

Production keeps no capture code. This module wraps the real app and spies on
`PredictorV1_3.predict_from_v6_payload` — the actual inference entry point, called once per
request. Inside that call the production `transform` output is recorded, so the record is the
real encoded matrix the model consumes, not a re-implementation.

(Spying on `transform` alone would produce two records per request, because the predictor
transforms once for the prediction and again for the SHAP explanation. One record per
inference is what the parity runner needs.)

Run:
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001

Records are written only for requests that reach inference. A rejected request produces no
record, which is what the negative cases assert.
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

# Correlation tag from X-Parity-Case. Spring does not forward it, so B records carry an
# empty tag and the runner matches them by the capture delta of that same request.
_TAG: ContextVar[str] = ContextVar("parity_tag", default="")
# Per-inference collector: the first transform output of this inference call.
_COLLECTED: ContextVar[object] = ContextVar("parity_collected", default=None)
# One record per HTTP request: /predict re-runs the predictor to build the SHAP explanation,
# so the inference entry point can be hit twice for a single request. Parity is per request.
_REQID: ContextVar[str] = ContextVar("parity_request_id", default="")

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
    """Numeric stays numeric; a categorical label stays a string."""
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None  # NaN -> None
    except (TypeError, ValueError):
        return str(value)


def _capturing_transform(df, schema):
    encoded = _production_transform(df, schema)
    box = _COLLECTED.get()
    if isinstance(box, dict) and "encoded" not in box:
        # First transform of this inference call == the vector that goes to the model.
        try:
            box["encoded"] = [_scalar(v) for v in encoded.iloc[0].tolist()]
            box["features"] = list(encoded.columns)
            box["input"] = {
                k: (None if df.iloc[0][k] is None else str(df.iloc[0][k]))
                for k in RECORD_INPUT_KEYS if k in df.columns
            }
            box["has_bedroom"] = float(encoded.iloc[0].get("has_bedroom", -1))
        except Exception:  # noqa: BLE001 - capture must never change the response
            box["failed"] = True
    return encoded


def _capturing_predict(self, v6_payload):
    box = {"tag": _TAG.get()}
    token = _COLLECTED.set(box)
    try:
        result = _production_predict(self, v6_payload)
    finally:
        _COLLECTED.reset(token)
    # One record per PREDICTOR INVOCATION, never per HTTP request: if the service runs the
    # predictor twice for one request, both must be visible. Deduplication here would hide
    # exactly the defect this harness exists to expose.
    if _TARGET and "encoded" in box:
        try:
            record = {
                "tag": box.get("tag", ""),
                "request": _REQID.get(),
                "thread": threading.current_thread().name,
                "background": _REQID.get() == "",
                "encoded": box["encoded"],
                "features": box["features"],
                "input": box["input"],
                "has_bedroom": box["has_bedroom"],
            }
            with open(_TARGET, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001
            pass
    return result


class _TagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        tag = request.headers.get("x-parity-case", "")
        token = _TAG.set(tag)
        rid = _REQID.set(uuid.uuid4().hex)
        try:
            return await call_next(request)
        finally:
            _REQID.reset(rid)
            _TAG.reset(token)


app = production_app
if _TARGET:
    predictor_module.transform = _capturing_transform
    predictor_module.PredictorV1_3.predict_from_v6_payload = _capturing_predict
    app.add_middleware(_TagMiddleware)
