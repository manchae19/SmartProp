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

        try:
            with open(self.target, "a", encoding="utf-8") as handle:
                handle.write(json.dumps(json.loads(body), ensure_ascii=False) + "\n")
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
