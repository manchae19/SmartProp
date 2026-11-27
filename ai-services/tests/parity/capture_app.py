"""Test-only harness: capture the ACTUAL inference input, not the raw request.

Production keeps no capture code. This module wraps the real app and spies on
`predictor_v1_3.transform`, i.e. the exact call that produces the encoded matrix the model
consumes. So the record is the production vector, not a re-implementation.

Run:
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001

Records are written only for requests that reach inference. A rejected request produces no
record, which is what the negative cases assert.
"""
import json
import os
from contextvars import ContextVar

from starlette.middleware.base import BaseHTTPMiddleware

from app.models.xgboost import predictor_v1_3 as predictor_module
from main import app as production_app

_TARGET = os.environ.get("SMARTPROP_PARITY_CAPTURE")

# Correlation tag: the runner sends X-Parity-Case. Spring does not forward it, so those
# records simply carry an empty tag and are matched by strict sequence within their path.
_TAG: ContextVar[str] = ContextVar("parity_tag", default="")

# Only model-relevant fields; free text, credentials and headers are never recorded.
RECORD_INPUT_KEYS = (
    "normalized_type", "district", "ward",
    "area", "floor_count", "frontage_width", "road_width",
    "bedroom_count", "bathroom_count",
    "street_name", "project_name",
    "house_direction", "balcony_direction",
)

def _scalar(value):
    try:
        if value is None:
            return None
        number = float(value)
        return number if number == number else None  # NaN -> None
    except (TypeError, ValueError):
        return str(value)


_production_transform = predictor_module.transform


def _capturing_transform(df, schema):
    encoded = _production_transform(df, schema)
    if _TARGET:
        try:
            row = {k: df.iloc[0][k] for k in RECORD_INPUT_KEYS if k in df.columns}
            record = {
                "tag": _TAG.get(),
                # Categorical columns stay as their label; numeric columns stay numeric.
                # Coercing everything to float would either lose the category or raise.
                "encoded": [_scalar(v) for v in encoded.iloc[0].tolist()],
                "features": list(encoded.columns),
                "input": {k: (None if v is None else str(v)) for k, v in row.items()},
                "has_bedroom": float(encoded.iloc[0].get("has_bedroom", -1)),
            }
            with open(_TARGET, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")
        except Exception:  # noqa: BLE001 - capture must never change the response
            pass
    return encoded


class _TagMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        token = _TAG.set(request.headers.get("x-parity-case", ""))
        try:
            return await call_next(request)
        finally:
            _TAG.reset(token)


app = production_app
if _TARGET:
    predictor_module.transform = _capturing_transform
    app.add_middleware(_TagMiddleware)
