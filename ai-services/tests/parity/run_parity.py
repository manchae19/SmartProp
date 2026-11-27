"""Reproducible three-path parity check for the V1.3 valuation contract.

Paths
  A  POST /predict                            (FastAPI, public)
  B  POST /api/v1/properties/valuation-preview (Spring Boot -> FastAPI)
  C  POST /predict/v1_3_preview                (FastAPI, legacy preview)

Design notes
  * The comparison uses the **actual encoded matrix** captured by the test-only harness at
    the inference boundary (capture_app.py), never a re-implementation.
  * Requests are strictly sequential and every request is bracketed by a capture count
    read, so each positive request must produce **exactly one new record** and every
    negative request must produce **zero**. No record is ever reused, and a missing /
    extra / mis-tagged capture fails the run. A short overlap guard runs between cases so
    concurrent external traffic cannot silently satisfy a delta.
  * The checking logic is a pure function over a transport + capture log, so the runner's
    own correctness can be regression-tested with synthetic captures
    (see test_run_parity.py).

Setup:
    cd ai-services
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001
    APP_VALUATION_ENABLED=true APP_VALUATION_BASE_URL=http://127.0.0.1:8001 ./mvnw spring-boot:run
    SMARTPROP_PARITY_EMAIL=... SMARTPROP_PARITY_PASSWORD=... \\
      python -m tests.parity.run_parity --capture /tmp/parity.jsonl

Exit code is non-zero if any assertion fails.
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
OVERLAP_GUARD_SECONDS = 1.5

PRICE_KEYS = ("predictedAskingPriceVnd", "predicted_asking_price_vnd")
MODEL_KEYS = ("modelVersion", "model_version")


# --------------------------------------------------------------------------- cases
@dataclass(frozen=True)
class Case:
    name: str
    a_body: Dict[str, Any]
    b_body: Dict[str, Any]
    positive: bool
    # Expected Spring contract for a rejected request: "available_false" or "status:<code>"
    b_rejection: str = ""
    # Expected street warning, derived from the request itself (not from the case name).
    expect_street_warning: bool = False
    note: str = ""


def _street_warning(body: Optional[Dict[str, Any]]) -> bool:
    return any(STREET_WARNING_NEEDLE in str(w) for w in ((body or {}).get("warnings") or []))


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
          "locationFeature": "Hà Nội"}, False, b_rejection="available_false"),
    Case("neg-hcm", {"category": "Nhà ở", "area_sqm": 100.0,
                     "location_feature": "TP. Hồ Chí Minh"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "TP. Hồ Chí Minh"}, False, b_rejection="available_false"),
    Case("neg-unknown-district", {"category": "Nhà ở", "area_sqm": 100.0,
                                  "location_feature": "Quận Không Tồn Tại"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Quận Không Tồn Tại"}, False, b_rejection="available_false"),
    Case("neg-land-balcony", {"category": "Đất nền", "area_sqm": 100.0,
                              "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
         {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}, False,
         b_rejection="available_false"),
    Case("neg-house-balcony", {"category": "Nhà ở", "area_sqm": 100.0,
                               "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}, False,
         b_rejection="available_false"),
    Case("neg-bedrooms-31", {"category": "Nhà ở", "area_sqm": 100.0,
                             "location_feature": "Cẩm Lệ", "rooms": 31},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "bedrooms": 31}, False, b_rejection="available_false"),
    Case("neg-subtype", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                         "house_subtype": "penthouse"},
         {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
          "locationFeature": "Cẩm Lệ", "houseSubtype": "penthouse"}, False,
         b_rejection="status:400"),
]


# --------------------------------------------------------------------------- ports
CaptureLog = Callable[[], List[Dict[str, Any]]]
Post = Callable[..., Tuple[int, Dict[str, Any]]]


class FileCapture:
    """Reads the harness output file. Tolerates a partially written last line."""

    def __init__(self, path: Path):
        self.path = path

    def __call__(self) -> List[Dict[str, Any]]:
        if not self.path.exists():
            return []
        records = []
        for line in self.path.read_text(encoding="utf-8").splitlines():
            if not line.strip():
                continue
            try:
                records.append(json.loads(line))
            except ValueError:
                continue
        return records


def http_post(url, body, token=None, tag=None, pause=2.5) -> Tuple[int, Dict[str, Any]]:
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
    except Exception as error:  # noqa: BLE001 - surfaced as a failure, never ignored
        return 0, {"transport_error": str(error)[:200]}


# --------------------------------------------------------------------------- engine
@dataclass
class Report:
    failures: List[str] = field(default_factory=list)
    rows: List[str] = field(default_factory=list)
    positives_ok: int = 0
    negatives_ok: int = 0
    expected_positive_records: int = 0
    actual_positive_records: int = 0
    negative_records: int = 0

    def check(self, ok: bool, label: str) -> None:
        if not ok:
            self.failures.append(label)

    def fail(self, label: str) -> None:
        self.failures.append(label)


def _delta(capture: CaptureLog, before: int) -> List[Dict[str, Any]]:
    return capture()[before:]


def evaluate(cases_positive: List[Case], cases_negative: List[Case],
             post: Post, capture: CaptureLog, paths: Dict[str, Tuple[str, Optional[str]]],
             pause: float = 2.5, overlap_guard: float = OVERLAP_GUARD_SECONDS) -> Report:
    """Pure-ish engine. All I/O arrives through `post` and `capture`."""
    report = Report()
    report.expected_positive_records = len(cases_positive) * 3

    def request(path: str, body: Dict[str, Any], tag: str) -> Tuple[int, Dict[str, Any], List[Dict[str, Any]]]:
        url, token = paths[path]
        before = len(capture())
        status, payload = post(url, body, token=token, tag=tag, pause=pause)
        time.sleep(overlap_guard)  # let the harness finish writing before we count
        return status, payload, _delta(capture, before)

    # ---------------- positive
    for case in cases_positive:
        responses: Dict[str, Tuple[int, Dict[str, Any]]] = {}
        deltas: Dict[str, List[Dict[str, Any]]] = {}
        for path in ("A", "B", "C"):
            tag = f"{case.name}:{path}"
            status, payload, delta = request(path, case.a_body if path != "B" else case.b_body, tag)
            responses[path] = (status, payload)
            deltas[path] = delta

            report.check(status == 200, f"{case.name}/{path}: status {status} != 200")
            requests = {rec.get("request") for rec in delta}
            report.check(len(requests) == 1,
                         f"{case.name}/{path}: expected exactly 1 inference request, got {len(requests)}")
            if len(requests) == 1:
                first = delta[0]
                report.check(all(rec.get("encoded") == first.get("encoded") for rec in delta),
                             f"{case.name}/{path}: repeats of one inference disagree on the vector")
                encoded = first.get("encoded") or []
                report.check(len(encoded) == FEATURE_COUNT,
                             f"{case.name}/{path}: {len(encoded)} encoded features, expected {FEATURE_COUNT}")
                if path in ("A", "C"):
                    report.check(first.get("tag") == tag,
                                 f"{case.name}/{path}: capture tag {first.get('tag')!r} != {tag!r}")
            report.actual_positive_records += len(requests)

            price = _price(payload)
            if path == "B":
                report.check(payload.get("available") is True,
                             f"{case.name}/B: available is not True ({payload.get('available')!r})")
            report.check(price is not None and price > 0,
                         f"{case.name}/{path}: price is not a positive number ({price!r})")
            report.check(_model_version(payload) == "v1.3",
                         f"{case.name}/{path}: model version {_model_version(payload)!r} != 'v1.3'")

            has_warning = _street_warning(payload)
            report.check(has_warning == case.expect_street_warning,
                         f"{case.name}/{path}: street warning {has_warning}, expected {case.expect_street_warning}")

        # A/B/C must come from three records of the SAME case and match exactly
        def _ok(path):
            return len({rec.get("request") for rec in deltas[path]}) == 1
        vectors = {p: deltas[p][0]["encoded"] for p in ("A", "B", "C") if _ok(p)}
        orders = {p: deltas[p][0]["features"] for p in ("A", "B", "C") if _ok(p)}
        if len(vectors) == 3:
            report.check(vectors["A"] == vectors["B"] == vectors["C"],
                         f"{case.name}: encoded vector differs between A/B/C")
            report.check(orders["A"] == orders["B"] == orders["C"],
                         f"{case.name}: feature order differs between A/B/C")
            prices = {p: _price(responses[p][1]) for p in ("A", "B", "C")}
            base = prices["A"]
            report.check(base is not None and all(
                value is not None and abs(value - base) <= TOLERANCE_VND for value in prices.values()),
                f"{case.name}: final price differs between paths ({prices})")
            report.check("/".join(deltas["A"][0].get("input", {}).get(k, "") or ""
                                  for k in ("district",)) != "",
                         f"{case.name}: district was not resolved")
        else:
            report.fail(f"{case.name}: could not compare A/B/C (missing or extra record)")

        ok = not any(label.startswith(case.name) for label in report.failures)
        report.positives_ok += 1 if ok else 0
        report.rows.append(
            f"{case.name:18s} {responses['A'][0]:>4d} {responses['B'][0]:>4d} {responses['C'][0]:>4d}"
            f"  {str(_price(responses['A'][1])):>14s}  "
            f"{len({r.get('request') for r in deltas['A']})}/"
            f"{len({r.get('request') for r in deltas['B']})}/"
            f"{len({r.get('request') for r in deltas['C']})}")

    # ---------------- negative
    for case in cases_negative:
        for path in ("A", "C"):
            status, payload, delta = request(path, case.a_body, f"{case.name}:{path}")
            report.check(status == 422, f"{case.name}/{path}: status {status} != 422")
            report.check(_price(payload) is None,
                         f"{case.name}/{path}: returned a price on rejection ({_price(payload)!r})")
            report.check(len({rec.get("request") for rec in delta}) == 0,
                         f"{case.name}/{path}: produced {len(delta)} inference record(s), expected 0")
            report.negative_records += len({rec.get("request") for rec in delta})

        status, payload, delta = request("B", case.b_body, f"{case.name}:B")
        report.check(status in (200, 400) and status != 0,
                     f"{case.name}/B: unexpected status {status} (500/401/403/429/timeout all fail)")
        if case.b_rejection == "available_false":
            report.check(status == 200 and payload.get("available") is False,
                         f"{case.name}/B: expected 200 + available=false, got {status} + "
                         f"available={payload.get('available')!r}")
        elif case.b_rejection.startswith("status:"):
            expected = int(case.b_rejection.split(":", 1)[1])
            report.check(status == expected,
                         f"{case.name}/B: expected status {expected}, got {status}")
        else:
            report.fail(f"{case.name}/B: no rejection contract declared")
        report.check(_price(payload) is None,
                     f"{case.name}/B: returned a price on rejection ({_price(payload)!r})")
        report.check(len({rec.get("request") for rec in delta}) == 0,
                     f"{case.name}/B: produced {len(delta)} inference record(s), expected 0")
        report.negative_records += len({rec.get("request") for rec in delta})

        ok = not any(label.startswith(f"{case.name}/") for label in report.failures)
        report.negatives_ok += 1 if ok else 0

    report.check(report.actual_positive_records == report.expected_positive_records,
                 f"positive inference records {report.actual_positive_records} != "
                 f"{report.expected_positive_records}")
    report.check(report.negative_records == 0,
                 f"negative cases produced {report.negative_records} inference record(s)")
    return report


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True)
    parser.add_argument("--a", default="http://127.0.0.1:8001")
    parser.add_argument("--b", default="http://127.0.0.1:8080")
    parser.add_argument("--pause", type=float, default=2.5)
    args = parser.parse_args()

    email = os.environ.get("SMARTPROP_PARITY_EMAIL")
    password = os.environ.get("SMARTPROP_PARITY_PASSWORD")
    if not email or not password:
        print("BLOCKED: set SMARTPROP_PARITY_EMAIL and SMARTPROP_PARITY_PASSWORD")
        return 2

    capture_path = Path(args.capture)
    if capture_path.exists():
        capture_path.unlink()

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

    report = evaluate(POSITIVE, NEGATIVE, http_post, FileCapture(capture_path), paths,
                      pause=args.pause)

    print("=== POSITIVE: three-path parity ===")
    print(f"{'case':18s} {'A':>4s} {'B':>4s} {'C':>4s}  {'price A':>14s}  records A/B/C")
    for row in report.rows:
        print(row)
    print(f"\npositive: {report.positives_ok}/{len(POSITIVE)} · "
          f"negative: {report.negatives_ok}/{len(NEGATIVE)} · total: {len(POSITIVE) + len(NEGATIVE)}")
    print(f"inference records: {report.actual_positive_records} positive "
          f"(expected {report.expected_positive_records}) · {report.negative_records} negative (expected 0)")

    if report.failures:
        print("\n--- failures ---")
        for failure in report.failures:
            print("  FAIL ", failure)
    print(f"\n=== THREE-PATH PARITY: {'PASS' if not report.failures else 'FAIL'} "
          f"({len(report.failures)} lỗi) ===")
    return 0 if not report.failures else 1


if __name__ == "__main__":
    sys.exit(main())
