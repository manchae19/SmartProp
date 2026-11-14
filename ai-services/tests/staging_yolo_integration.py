"""End-to-end staging test for YOLOv8 listing integration.

Runs against an isolated staging stack only:
  * MySQL 3307 (isolated datadir)
  * Backend 18080 (profile hybrid-local-existing-v13-staging)
  * Imagecheck 18001 (duplicate scan)
  * Vision 18002 (YOLOv8)

It never touches MySQL 3306, Cloudinary, or any production service.
"""
from __future__ import annotations

import os

import io
import json
import sys
import time
import urllib.error
import urllib.request
import uuid
from pathlib import Path

from PIL import Image, ImageDraw

BASE = "http://127.0.0.1:18080/api/v1"
EMAIL = "yolo.staging@example.test"
PASSWORD = os.environ.get("SMARTPROP_STAGING_PASSWORD", "")
SAMPLES = Path(r"F:\SmartProp\.scratch\yolov8-samples")

results: list[tuple[str, bool, str]] = []


def check(name: str, ok: bool, detail: str = "") -> None:
    results.append((name, ok, detail))
    print(f"{'PASS' if ok else 'FAIL'}  {name}{' :: ' + detail if detail else ''}")


def call(method: str, path: str, body=None, token=None, raw=None, content_type=None):
    url = BASE + path
    headers = {}
    data = None
    if raw is not None:
        data = raw
        headers["Content-Type"] = content_type or "application/octet-stream"
    elif body is not None:
        data = json.dumps(body).encode("utf-8")
        headers["Content-Type"] = "application/json; charset=utf-8"
    if token:
        headers["Authorization"] = "Bearer " + token
    request = urllib.request.Request(url, data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=90) as response:
            payload = response.read()
            try:
                return response.status, json.loads(payload)
            except json.JSONDecodeError:
                return response.status, payload
    except urllib.error.HTTPError as error:
        text = error.read().decode("utf-8", "replace")
        try:
            return error.code, json.loads(text)
        except json.JSONDecodeError:
            return error.code, text


def multipart(fields: dict, filename: str, content: bytes, mime: str):
    boundary = "----staging" + uuid.uuid4().hex
    parts = []
    for key, value in fields.items():
        parts.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"\r\n\r\n{value}\r\n".encode())
    parts.append(
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"file\"; filename=\"{filename}\"\r\n"
        f"Content-Type: {mime}\r\n\r\n".encode() + content + b"\r\n"
    )
    parts.append(f"--{boundary}--\r\n".encode())
    return b"".join(parts), f"multipart/form-data; boundary={boundary}"


def upload(property_id: str, version: int, token: str, path: Path, mime="image/jpeg"):
    body, ctype = multipart({"expectedVersion": version}, path.name, path.read_bytes(), mime)
    return call("POST", f"/properties/{property_id}/images", raw=body, token=token, content_type=ctype)


def make_room(kind: str) -> bytes:
    """Synthetic room images; used only where a real sample is not needed."""
    image = Image.new("RGB", (640, 480), (150, 140, 128))
    draw = ImageDraw.Draw(image)
    if kind == "living":
        draw.rectangle((0, 0, 640, 240), fill=(205, 198, 186))
        draw.rectangle((40, 250, 300, 430), fill=(60, 70, 92))
        draw.rectangle((380, 120, 600, 260), fill=(20, 20, 24))
    elif kind == "bedroom":
        draw.rectangle((0, 0, 640, 240), fill=(198, 190, 178))
        draw.rectangle((80, 250, 520, 440), fill=(120, 96, 110))
    else:
        draw.rectangle((0, 0, 640, 480), fill=(120, 150, 120))
    buffer = io.BytesIO()
    image.save(buffer, format="JPEG", quality=90)
    return buffer.getvalue()


def main() -> int:
    # -- auth -------------------------------------------------------------
    status, login = call("POST", "/auth/login", {"email": EMAIL, "password": PASSWORD})
    if status != 200 or "accessToken" not in login:
        check("login", False, str(login)[:200])
        return 1
    token = login["accessToken"]
    check("login", True)

    # -- create listing ---------------------------------------------------
    status, created = call("POST", "/properties", {
        "title": "YOLO staging living room",
        "description": "Staging listing for YOLOv8 integration test.",
        "propertyType": "HOUSE",
        "transactionType": "SALE",
        "price": 3000000000,
        "areaSqm": 80,
        "district": "Hải Châu",
        "ward": "Nam Dương",
        "address": "1 Đường Test",
        "city": "Đà Nẵng",
        "bedrooms": 2,
        "bathrooms": 1,
        "floor": 1,
        "direction": "Đông",
        "currency": "VND",
        "priceUnit": "TOTAL",
        "declaredAmenities": [],
        "latitude": 16.0544,
        "longitude": 108.2022,
    }, token=token)
    if status not in (200, 201):
        check("create listing", False, str(created)[:300])
        return 1
    property_id = created["property"]["id"]
    version = created["property"]["contentVersion"]
    check("create listing", True, property_id[:8])

    # -- upload a real living-room photo ----------------------------------
    living = SAMPLES / "b5bec5ac5d83492bae6425af1042f749.jpg"
    status, uploaded = upload(property_id, version, token, living)
    check("upload living room image", status in (200, 201), f"status={status}")
    if status in (200, 201):
        version = uploaded["property"]["contentVersion"]

    # -- wait for both pipelines ------------------------------------------
    scan = analysis = None
    for _ in range(40):
        time.sleep(1.5)
        _, scan = call("GET", f"/properties/{property_id}/image-scan", token=token)
        _, analysis = call("GET", f"/properties/{property_id}/image-analysis", token=token)
        scan_done = scan.get("status") not in ("SCANNING", "PENDING")
        analysis_done = analysis.get("status") not in ("ANALYZING", "PENDING")
        if scan_done and analysis_done:
            break

    check("auto-scan completed", scan.get("status") in ("CLEAN", "MATCHES"), f"status={scan.get('status')}")
    check("yolo analysis completed", analysis.get("status") in ("HAS_OBJECTS", "NO_OBJECTS"),
          f"status={analysis.get('status')}")

    images = analysis.get("images") or []
    detections = sum(item.get("detectionCount", 0) for item in images)
    check("yolo detected objects in living room", detections > 0, f"detections={detections}")

    labels = {}
    for item in images:
        for label, count in (item.get("countsByLabel") or {}).items():
            labels[label] = labels.get(label, 0) + count
    check("labels are Vietnamese", any(any(ord(c) > 127 for c in label) for label in labels),
          f"labels={list(labels)[:4]}")

    # -- document image must be flagged, not silently trusted --------------
    doc = SAMPLES / "c70d11168edd4bf79b5cb177b0eaf069.jpg"
    status, uploaded = upload(property_id, version, token, doc)
    if status in (200, 201):
        version = uploaded["property"]["contentVersion"]
    doc_flagged = False
    for _ in range(30):
        time.sleep(1.5)
        _, analysis = call("GET", f"/properties/{property_id}/image-analysis", token=token)
        if analysis.get("status") not in ("ANALYZING", "PENDING"):
            doc_flagged = any((item.get("documentHint") or {}).get("likelyDocument") for item in analysis.get("images") or [])
            break
    check("document image flagged", doc_flagged)

    # -- persistence after reload -----------------------------------------
    _, again = call("GET", f"/properties/{property_id}/image-analysis", token=token)
    check("analysis persists on re-read", again.get("status") == analysis.get("status"),
          f"{again.get('status')} vs {analysis.get('status')}")

    # -- delete image clears its result ------------------------------------
    image_ids = [item["imageId"] for item in (again.get("images") or [])]
    if image_ids:
        status, deleted = call("DELETE", f"/properties/{property_id}/images/{image_ids[-1]}?expectedVersion={version}", token=token)
        if status in (200, 204):
            version = deleted["property"]["contentVersion"] if isinstance(deleted, dict) and "property" in deleted else version
        time.sleep(2)
        _, after_delete = call("GET", f"/properties/{property_id}/image-analysis", token=token)
        remaining = [item["imageId"] for item in (after_delete.get("images") or [])]
        check("deleted image removed from analysis", image_ids[-1] not in remaining,
              f"remaining={len(remaining)}")

    # -- private listing must not leak -------------------------------------
    status, anon = call("GET", f"/properties/{property_id}/image-analysis")
    check("draft analysis hidden from anonymous", status in (401, 403, 404), f"status={status}")

    # -- admin route requires ADMIN ----------------------------------------
    status, admin = call("GET", "/admin/image-analysis", token=token)
    check("admin route rejects BROKER", status in (401, 403), f"status={status}")

    print(f"\n{sum(1 for _, ok, _ in results if ok)}/{len(results)} checks passed")
    return 0 if all(ok for _, ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
