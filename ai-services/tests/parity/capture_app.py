"""Test-only capture server cho parity test.

Production app không còn bất kỳ đường ghi request ra file. Module này bọc app thật bằng
một ASGI middleware CHỈ tồn tại trong test, chỉ ghi khi biến môi trường test được đặt,
và chỉ ghi body của POST /predict (payload đặc trưng định giá, không có PII/token).

Chạy:
    SMARTPROP_PARITY_CAPTURE=<file> uvicorn tests.parity.capture_app:app --port 8001
"""
import json
import os

from main import app as production_app

_TARGET = os.environ.get("SMARTPROP_PARITY_CAPTURE")

# Model-relevant fields only. Anything not listed here is never written to disk.
CAPTURE_FIELDS = frozenset({
    "category", "area_sqm", "location_feature", "ward",
    "rooms", "bathrooms", "floors", "house_subtype",
    "road_width_m", "frontage_width_m", "street_name", "project_name",
    "house_direction", "balcony_direction", "access_type",
})


class _CaptureMiddleware:
    """Pure ASGI so the request body can be buffered and replayed without loss."""

    def __init__(self, app, target):
        self.app = app
        self.target = target

    async def __call__(self, scope, receive, send):
        if (scope.get("type") != "http" or scope.get("path") != "/predict"
                or scope.get("method") != "POST"):
            return await self.app(scope, receive, send)

        chunks = []
        while True:
            message = await receive()
            chunks.append(message.get("body", b""))
            if not message.get("more_body"):
                break
        body = b"".join(chunks)

        # Minimised capture: only the fields that feed the V1.3 feature pipeline.
        # Free text (title/description/address) and any header, token or cookie are
        # deliberately not written - parity is a feature question, not a data dump.
        try:
            payload = json.loads(body)
            kept = {k: v for k, v in payload.items() if k in CAPTURE_FIELDS}
            with open(self.target, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(kept, ensure_ascii=False, sort_keys=True) + "\n")
        except (OSError, ValueError):
            pass  # capture is best-effort; it must never affect the response

        replayed = False

        async def replay():
            nonlocal replayed
            if not replayed:
                replayed = True
                return {"type": "http.request", "body": body, "more_body": False}
            return await receive()

        return await self.app(scope, replay, send)


app = production_app
if _TARGET:
    app.add_middleware(_CaptureMiddleware, target=_TARGET)
