"""Reproducible three-path parity check for the V1.3 valuation contract.

Paths
  A  POST /predict                            (FastAPI, public)
  B  POST /api/v1/properties/valuation-preview (Spring Boot -> FastAPI)
  C  POST /predict/v1_3_preview                (FastAPI, legacy preview)

Why this runner looks the way it does
  * The comparison uses the **actual encoded matrix** captured at the inference boundary by
    the test-only harness (capture_app.py), never a re-implementation.
  * Per-request counts alone are not enough: a record smuggled between two request windows, or
    a B record replaced by a copy of A, would keep the totals plausible. So every request
    claims a contiguous slice of the log, every record carries a unique `request` and
    `invocation` id, and at the end the **whole log** is reconciled: every record must belong
    to exactly one claimed window, ids must be globally unique, nothing background, nothing in
    ERROR, nothing orphaned, nothing unparsed.
  * Completion is not a fixed sleep: the log must stop growing (A requests are followed by a
    settle poll with a bounded timeout) or the run fails.
  * The checking engine takes a transport and a capture reader as parameters so it can be
    regression-tested with synthetic logs (test_run_parity.py).

Setup:
    cd ai-services
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001
    APP_VALUATION_ENABLED=true APP_VALUATION_BASE_URL=http://127.0.0.1:8001 ./mvnw spring-boot:run
    SMARTPROP_PARITY_EMAIL=... SMARTPROP_PARITY_PASSWORD=... \\
      python -m tests.parity.run_parity --capture /tmp/parity.jsonl
"""
import argparse
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

FEATURE_COUNT = 22
TOLERANCE_VND = 1
STREET_WARNING_NEEDLE = "chưa được đối chiếu với khu vực"
DEFAULT_PAUSE = 2.5
DEFAULT_SETTLE_TIMEOUT = 12.0
STABLE_READS = 3
POLL_INTERVAL = 0.25

PRICE_KEYS = ("predictedAskingPriceVnd", "predicted_asking_price_vnd")
MODEL_KEYS = ("modelVersion", "model_version")

EXPECTED_ENDPOINT = {"A": "/predict", "B": "/predict", "C": "/predict/v1_3_preview"}


# --------------------------------------------------------------------------- cases
@dataclass(frozen=True)
class Case:
    name: str
    a_body: Dict[str, Any]
    b_body: Dict[str, Any]
    positive: bool
    b_rejection: str = ""
    expect_street_warning: bool = False


def _price(body: Dict[str, Any]) -> Optional[int]:
    for key in PRICE_KEYS:
        value = body.get(key)
        if value is not None:
            try:
                return int(value)
            except (TypeError, ValueError):
                return None
    return None


def _model_version(body: Dict[str, Any]) -> Optional[str]:
    for key in MODEL_KEYS:
        value = body.get(key)
        if value:
            return str(value)
    return None


def _street_warning(body: Optional[Dict[str, Any]]) -> bool:
    return any(STREET_WARNING_NEEDLE in str(w) for w in ((body or {}).get("warnings") or []))


NFD_CAM_LE = unicodedata.normalize("NFD", "Cẩm Lệ")

POSITIVE: List[Case] = [
    Case("house-basic",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ"}, True),
    Case("house-enriched",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
          "ward": "Hòa Thọ Đông", "rooms": 3, "road_width_m": 12, "frontage_width_m": 6,
          "street_name": "Nguyễn Phước Lan", "floors": 3, "house_subtype": "house_c4",
          "bathrooms": 2, "house_direction": "Đông Nam"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "ward": "Hòa Thọ Đông", "bedrooms": 3,
          "roadWidthM": 12, "frontageWidthM": 6, "streetName": "Nguyễn Phước Lan",
          "floors": 3, "houseSubtype": "house_c4", "bathrooms": 2,
          "houseDirection": "Đông Nam"}, True, expect_street_warning=True),
    Case("land",
         {"category": "Đất nền", "area_sqm": 120.0, "location_feature": "Cẩm Lệ",
          "road_width_m": 5.5, "frontage_width_m": 6},
         {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 120,
          "locationFeature": "Cẩm Lệ", "roadWidthM": 5.5, "frontageWidthM": 6}, True),
    Case("apartment-balcony",
         {"category": "Căn hộ chung cư", "area_sqm": 75.0, "location_feature": "Hải Châu",
          "rooms": 2, "bathrooms": 2, "balcony_direction": "Đông"},
         {"propertyType": "APARTMENT", "transactionType": "SALE", "areaSqm": 75,
          "locationFeature": "Hải Châu", "bedrooms": 2, "bathrooms": 2,
          "balconyDirection": "Đông"}, True),
    Case("villa",
         {"category": "Nhà ở", "area_sqm": 200.0, "location_feature": "Ngũ Hành Sơn",
          "floors": 3, "house_subtype": "villa", "road_width_m": 12,
          "frontage_width_m": 10},
         {"propertyType": "VILLA", "transactionType": "SALE", "areaSqm": 200,
          "locationFeature": "Ngũ Hành Sơn", "floors": 3, "houseSubtype": "villa",
          "roadWidthM": 12, "frontageWidthM": 10}, True),
    Case("ward-conflict",
         {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Cẩm Lệ",
          "ward": "Hải Châu 1"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 80,
          "locationFeature": "Cẩm Lệ", "ward": "Hải Châu 1"}, True),
    Case("bedrooms-zero",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ", "rooms": 0},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "bedrooms": 0}, True),
    Case("bedrooms-omitted",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ"}, True),
    Case("district-nfc",
         {"category": "Nhà ở", "area_sqm": 90.0, "location_feature": "Cẩm Lệ"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 90,
          "locationFeature": "Cẩm Lệ"}, True),
    Case("district-nfd",
         {"category": "Nhà ở", "area_sqm": 90.0, "location_feature": NFD_CAM_LE},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 90,
          "locationFeature": NFD_CAM_LE}, True),
    Case("street-known",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
          "street_name": "Nguyễn Phước Lan"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "streetName": "Nguyễn Phước Lan"}, True,
         expect_street_warning=True),
    Case("street-prefix",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
          "street_name": "Đường Nguyễn Phước Lan"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "streetName": "Đường Nguyễn Phước Lan"}, True,
         expect_street_warning=True),
    Case("street-oov",
         {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
          "street_name": "Đường Không Tồn Tại XYZ 123"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "streetName": "Đường Không Tồn Tại XYZ 123"}, True,
         expect_street_warning=True),
]

NEGATIVE: List[Case] = [
    Case("neg-hanoi", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Hà Nội"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Hà Nội"}, False, "available_false"),
    Case("neg-hcm", {"category": "Nhà ở", "area_sqm": 100.0,
                     "location_feature": "TP. Hồ Chí Minh"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "TP. Hồ Chí Minh"}, False, "available_false"),
    Case("neg-unknown-district", {"category": "Nhà ở", "area_sqm": 100.0,
                                  "location_feature": "Quận Không Tồn Tại"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Quận Không Tồn Tại"}, False, "available_false"),
    Case("neg-land-balcony", {"category": "Đất nền", "area_sqm": 100.0,
                              "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
         {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}, False, "available_false"),
    Case("neg-house-balcony", {"category": "Nhà ở", "area_sqm": 100.0,
                               "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}, False, "available_false"),
    Case("neg-bedrooms-31", {"category": "Nhà ở", "area_sqm": 100.0,
                             "location_feature": "Cẩm Lệ", "rooms": 31},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "bedrooms": 31}, False, "available_false"),
    Case("neg-subtype", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                         "house_subtype": "penthouse"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "houseSubtype": "penthouse"}, False, "status:400"),
]


# --------------------------------------------------------------------------- ports
class CaptureError(RuntimeError):
    pass


CaptureLog = Callable[[], List[Dict[str, Any]]]
Post = Callable[..., Tuple[int, Dict[str, Any]]]


class FileCapture:
    """Strict reader: a malformed line or a write-error sidecar is a capture failure."""

    def __init__(self, path: Path):
        self.path = path
        self.errors = Path(str(path) + ".errors")

    def __call__(self) -> List[Dict[str, Any]]:
        if self.errors.exists() and self.errors.read_text(encoding="utf-8").strip():
            raise CaptureError(f"capture write failed: {self.errors.read_text(encoding='utf-8')[:200]}")
        if not self.path.exists():
            return []
        try:
            raw = self.path.read_text(encoding="utf-8")
        except OSError as error:
            raise CaptureError(f"capture read failed: {error}") from error
        records = []
        for number, line in enumerate(raw.splitlines(), start=1):
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError as error:
                raise CaptureError(f"malformed capture line {number}: {error}") from error
        return records


def http_post(url, body, token=None, tag=None, pause=DEFAULT_PAUSE) -> Tuple[int, Dict[str, Any]]:
    time.sleep(pause)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if tag:
        headers["X-Parity-Case"] = tag
    request = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(),
                                     headers=headers, method="POST")
    try:
        with urllib.request.urlopen(request, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode(errors="replace")
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw[:200]}
    except Exception as error:  # noqa: BLE001
        return 0, {"transport_error": str(error)[:200]}


# --------------------------------------------------------------------------- engine
@dataclass
class Report:
    failures: List[str] = field(default_factory=list)
    rows: List[str] = field(default_factory=list)
    positives_ok: int = 0
    negatives_ok: int = 0
    positive_invocations: int = 0
    negative_invocations: int = 0
    total_records: int = 0
    unique_requests: int = 0
    unique_invocations: int = 0
    background: int = 0
    errors: int = 0
    orphans: int = 0

    def fail(self, label: str) -> None:
        self.failures.append(label)

    def check(self, ok: bool, label: str) -> bool:
        if not ok:
            self.failures.append(label)
        return ok


def _settle(capture: CaptureLog, timeout: float, poll: float = POLL_INTERVAL) -> int:
    """Wait until the log stops growing. Returns the stable count; raises no exception."""
    deadline = time.monotonic() + timeout
    last = len(capture())
    stable = 0
    while time.monotonic() < deadline:
        time.sleep(poll)
        current = len(capture())
        if current == last:
            stable += 1
            if stable >= STABLE_READS:
                return current
        else:
            stable = 0
            last = current
    return -1


def evaluate(cases_positive: List[Case], cases_negative: List[Case],
             post: Post, capture: CaptureLog, paths: Dict[str, Tuple[str, Optional[str]]],
             pause: float = 0.0, settle_timeout: float = 1.0,
             settle: Optional[Callable[[CaptureLog, float], int]] = None) -> Report:
    report = Report()
    settle_fn = settle or (lambda log, timeout: _settle(log, timeout))
    used_requests: set = set()
    used_invocations: set = set()
    claimed: List[Tuple[int, int]] = []          # index ranges covered by requests
    claimed_labels: List[str] = []

    def window(path: str, body: Dict[str, Any], tag: str, label: str):
        """Do one request and return its claimed slice, or None when the log never settled."""
        start = settle_fn(capture, settle_timeout)
        if start < 0:
            report.fail(f"{label}: capture did not settle before the request (delayed inference)")
            start = len(capture())
        status, payload = post(paths[path][0], body, token=paths[path][1], tag=tag, pause=pause)
        end = settle_fn(capture, settle_timeout)
        if end < 0:
            report.fail(f"{label}: capture did not settle after the request (delayed inference)")
            end = len(capture())
        records = capture()
        claimed.append((start, min(end, len(records))))
        claimed_labels.append(label)
        return status, payload, records[start:min(end, len(records))]

    # ---------------- positive
    for case in cases_positive:
        responses: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        records_by_path: Dict[str, List[Dict[str, Any]]] = {}
        for path in ("A", "B", "C"):
            tag = f"{case.name}:{path}"
            label = f"{case.name}/{path}"
            body = case.a_body if path != "B" else case.b_body
            status, payload, records = window(path, body, tag, label)
            responses[path] = (status, payload)
            records_by_path[path] = records

            report.check(status == 200, f"{label}: status {status} != 200")
            report.check(len(records) == 1,
                         f"{label}: expected exactly 1 predictor invocation, got {len(records)}")
            if len(records) == 1:
                record = records[0]
                report.check(record.get("run"), f"{label}: record has no capture run id")
                invocation = record.get("invocation")
                request_id = record.get("request")
                report.check(bool(request_id), f"{label}: request id is empty (background work)")
                report.check(record.get("background") is not True, f"{label}: marked background")
                report.check(record.get("outcome") == "SUCCESS",
                             f"{label}: invocation outcome {record.get('outcome')!r}")
                report.check(record.get("capture") == "OK",
                             f"{label}: capture status {record.get('capture')!r}")
                report.check(record.get("endpoint") == EXPECTED_ENDPOINT[path],
                             f"{label}: endpoint {record.get('endpoint')!r} != "
                             f"{EXPECTED_ENDPOINT[path]!r}")
                # A/C carry the explicit tag; Spring does not forward it, so B must be untagged.
                expected_tag = "" if path == "B" else tag
                report.check(record.get("tag") == expected_tag,
                             f"{label}: tag {record.get('tag')!r} != {expected_tag!r}")
                if path == "B":
                    report.check(record.get("tag") == "",
                                 f"{label}: B record carries a tag, so it was not produced by Spring")
                if request_id:
                    report.check(request_id not in used_requests,
                                 f"{label}: duplicate request id {request_id} (record reused)")
                    used_requests.add(request_id)
                if invocation:
                    report.check(invocation not in used_invocations,
                                 f"{label}: duplicate invocation id {invocation}")
                    used_invocations.add(invocation)
                encoded = record.get("encoded")
                report.check(isinstance(encoded, list) and len(encoded) == FEATURE_COUNT,
                             f"{label}: encoded vector missing or not {FEATURE_COUNT} features")
            report.positive_invocations += len(records)

            price = _price(payload)
            if path == "B":
                report.check(payload.get("available") is True,
                             f"{case.name}/B: available is not True ({payload.get('available')!r})")
            report.check(price is not None and price > 0,
                         f"{label}: price is not a positive number ({price!r})")
            report.check(_model_version(payload) == "v1.3",
                         f"{label}: model version {_model_version(payload)!r} != 'v1.3'")
            has_warning = _street_warning(payload)
            report.check(has_warning == case.expect_street_warning,
                         f"{label}: street warning {has_warning}, expected {case.expect_street_warning}")

        usable = {p: records_by_path[p] for p in ("A", "B", "C") if len(records_by_path[p]) == 1}
        if len(usable) == 3:
            vectors = {p: usable[p][0].get("encoded") for p in usable}
            orders = {p: usable[p][0].get("features") for p in usable}
            report.check(vectors["A"] == vectors["B"] == vectors["C"],
                         f"{case.name}: encoded vector differs between A/B/C")
            report.check(orders["A"] == orders["B"] == orders["C"],
                         f"{case.name}: feature order differs between A/B/C")
            prices = {p: _price(responses[p][1]) for p in usable}
            base = prices["A"]
            report.check(base is not None and all(
                value is not None and abs(value - base) <= TOLERANCE_VND for value in prices.values()),
                f"{case.name}: final price differs between paths ({prices})")
        else:
            report.fail(f"{case.name}: could not compare A/B/C (missing or extra record)")

        ok = not any(label.startswith(case.name) for label in report.failures)
        report.positives_ok += 1 if ok else 0
        report.rows.append(
            f"{case.name:18s} {responses['A'][0]:>4d} {responses['B'][0]:>4d} {responses['C'][0]:>4d}"
            f"  {str(_price(responses['A'][1])):>14s}  "
            f"{len(records_by_path['A'])}/{len(records_by_path['B'])}/{len(records_by_path['C'])}")

    # ---------------- negative
    for case in cases_negative:
        for path in ("A", "C"):
            label = f"{case.name}/{path}"
            status, payload, records = window(path, case.a_body, f"{case.name}:{path}", label)
            report.check(status == 422, f"{label}: status {status} != 422")
            report.check(_price(payload) is None,
                         f"{label}: returned a price on rejection ({_price(payload)!r})")
            report.check(len(records) == 0,
                         f"{label}: produced {len(records)} invocation(s), expected 0")
            report.negative_invocations += len(records)

        label = f"{case.name}/B"
        status, payload, records = window("B", case.b_body, f"{case.name}:B", label)
        report.check(status in (200, 400) and status != 0,
                     f"{label}: unexpected status {status} (500/401/403/429/timeout all fail)")
        if case.b_rejection == "available_false":
            report.check(status == 200 and payload.get("available") is False,
                         f"{label}: expected 200 + available=false, got {status} + "
                         f"available={payload.get('available')!r}")
        elif case.b_rejection.startswith("status:"):
            report.check(status == int(case.b_rejection.split(":", 1)[1]),
                         f"{label}: expected status {case.b_rejection.split(':', 1)[1]}, got {status}")
        else:
            report.fail(f"{label}: no rejection contract declared")
        report.check(_price(payload) is None,
                     f"{label}: returned a price on rejection ({_price(payload)!r})")
        report.check(len(records) == 0, f"{label}: produced {len(records)} invocation(s), expected 0")
        report.negative_invocations += len(records)
        ok = not any(entry.startswith(f"{case.name}/") for entry in report.failures)
        report.negatives_ok += 1 if ok else 0

    # ---------------- full-log reconciliation
    try:
        final_records = capture()
    except CaptureError as error:
        report.fail(f"capture unreadable at reconciliation: {error}")
        final_records = []

    report.total_records = len(final_records)
    covered = [index for start, end in claimed for index in range(start, end)]
    report.check(len(covered) == len(set(covered)),
                 "a capture record was claimed by more than one request window")
    expected_total = report.positive_invocations + report.negative_invocations
    report.orphans = len(final_records) - len(set(covered))
    report.check(report.orphans == 0,
                 f"{report.orphans} record(s) outside every request window (orphan or delayed)")
    report.check(len(final_records) == expected_total,
                 f"log holds {len(final_records)} records but {expected_total} were claimed")

    for index, record in enumerate(final_records):
        if not isinstance(record, dict):
            report.fail(f"record {index} is not an object")
            continue
        for required in ("run", "invocation", "request", "endpoint", "outcome", "capture"):
            if required not in record:
                report.fail(f"record {index} missing field {required!r}")
        if record.get("outcome") != "SUCCESS":
            report.errors += 1
        if record.get("background") is True:
            report.background += 1

    report.check(report.errors == 0, f"{report.errors} invocation(s) ended in ERROR")
    report.check(report.background == 0, f"{report.background} background invocation(s)")
    report.unique_requests = len({r.get("request") for r in final_records if isinstance(r, dict)})
    report.unique_invocations = len({r.get("invocation") for r in final_records if isinstance(r, dict)})
    report.check(report.unique_requests == expected_total,
                 f"{report.unique_requests} unique request ids for {expected_total} invocations")
    report.check(report.unique_invocations == expected_total,
                 f"{report.unique_invocations} unique invocation ids for {expected_total} invocations")
    report.check(report.positive_invocations == len(cases_positive) * 3,
                 f"positive invocations {report.positive_invocations} != {len(cases_positive) * 3}")
    report.check(report.negative_invocations == 0,
                 f"negative cases produced {report.negative_invocations} invocation(s)")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True)
    parser.add_argument("--a", default="http://127.0.0.1:8001")
    parser.add_argument("--b", default="http://127.0.0.1:8080")
    parser.add_argument("--pause", type=float, default=DEFAULT_PAUSE)
    parser.add_argument("--settle-timeout", type=float, default=DEFAULT_SETTLE_TIMEOUT)
    args = parser.parse_args()

    email = os.environ.get("SMARTPROP_PARITY_EMAIL")
    password = os.environ.get("SMARTPROP_PARITY_PASSWORD")
    if not email or not password:
        print("BLOCKED: set SMARTPROP_PARITY_EMAIL and SMARTPROP_PARITY_PASSWORD")
        return 2

    path = Path(args.capture)
    for suffix in ("", ".errors"):
        candidate = Path(str(path) + suffix)
        if candidate.exists():
            candidate.unlink()

    status, body = http_post(f"{args.b}/api/v1/auth/login",
                             {"email": email, "password": password}, pause=0)
    token = body.get("accessToken")
    if status != 200 or not token:
        print(f"BLOCKED: login failed (status {status})")
        return 2
    print(f"login: {status}\n")

    paths = {"A": (f"{args.a}/predict", None),
             "B": (f"{args.b}/api/v1/properties/valuation-preview", token),
             "C": (f"{args.a}/predict/v1_3_preview", None)}

    try:
        report = evaluate(POSITIVE, NEGATIVE, http_post, FileCapture(path), paths,
                          pause=args.pause, settle_timeout=args.settle_timeout)
    except CaptureError as error:
        print(f"FAIL capture: {error}")
        return 1

    print("=== POSITIVE: three-path parity ===")
    print(f"{'case':18s} {'A':>4s} {'B':>4s} {'C':>4s}  {'price A':>14s}  invocations A/B/C")
    for row in report.rows:
        print(row)
    print(f"\npositive: {report.positives_ok}/{len(POSITIVE)} · "
          f"negative: {report.negatives_ok}/{len(NEGATIVE)} · total: {len(POSITIVE) + len(NEGATIVE)}")
    print(f"records: {report.total_records} · unique requests: {report.unique_requests} · "
          f"unique invocations: {report.unique_invocations} · orphans: {report.orphans} · "
          f"background: {report.background} · errors: {report.errors} · "
          f"positive invocations: {report.positive_invocations} · negative: {report.negative_invocations}")

    if report.failures:
        print("\n--- failures ---")
        for failure in report.failures:
            print("  FAIL ", failure)
    print(f"\n=== THREE-PATH PARITY: {'PASS' if not report.failures else 'FAIL'} "
          f"({len(report.failures)} lỗi) ===")
    return 0 if not report.failures else 1


if __name__ == "__main__":
    sys.exit(main())
