"""Reproducible three-path parity check for the V1.3 valuation contract.

Paths
  A  POST /predict                          (FastAPI, public)
  B  POST /api/v1/properties/valuation-preview (Spring Boot -> FastAPI)
  C  POST /predict/v1_3_preview              (FastAPI, legacy preview)

The comparison uses the **actual encoded matrix** captured by the test-only harness at the
inference boundary (see capture_app.py), so it never rebuilds features with a second
implementation. A rejected request must produce no capture record at all.

Setup (see also README.md):
    cd ai-services
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \\
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001
    # Spring Boot must point at the harness:
    APP_VALUATION_ENABLED=true APP_VALUATION_BASE_URL=http://127.0.0.1:8001 ./mvnw spring-boot:run
    # then
    SMARTPROP_PARITY_EMAIL=... SMARTPROP_PARITY_PASSWORD=... \\
      python -m tests.parity.run_parity --capture /tmp/parity.jsonl

Exit code is non-zero if any assertion fails. The capture file is temporary output and must
never be committed.
"""
import argparse
import json
import os
import sys
import time
import unicodedata
import urllib.error
import urllib.request
from pathlib import Path

STREET_WARNING_NEEDLE = "chưa được đối chiếu với khu vực"
TOLERANCE_VND = 1  # identical model, identical vector: only rounding may differ


def post(url, body, token=None, tag=None, pause=2.5):
    """One request. Returns (status, body). HTTP errors are data, not failures to hide."""
    time.sleep(pause)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    if tag:
        headers["X-Parity-Case"] = tag
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            return response.status, json.loads(response.read() or b"{}")
    except urllib.error.HTTPError as error:
        raw = error.read().decode(errors="replace")
        try:
            return error.code, json.loads(raw)
        except ValueError:
            return error.code, {"raw": raw[:200]}
    except Exception as error:  # noqa: BLE001 - connection problems are reported, not ignored
        return 0, {"error": str(error)[:200]}


# ---------------------------------------------------------------- cases
# Each positive case: same property, expressed for each path.
POSITIVE = [
    ("house-basic", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ"}),
    ("house-enriched", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                        "ward": "Hòa Thọ Đông", "rooms": 3, "road_width_m": 12,
                        "frontage_width_m": 6, "street_name": "Nguyễn Phước Lan",
                        "floors": 3, "house_subtype": "house_c4", "bathrooms": 2,
                        "house_direction": "Đông Nam"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "ward": "Hòa Thọ Đông", "bedrooms": 3,
      "roadWidthM": 12, "frontageWidthM": 6, "streetName": "Nguyễn Phước Lan",
      "floors": 3, "houseSubtype": "house_c4", "bathrooms": 2, "houseDirection": "Đông Nam"}),
    ("land", {"category": "Đất nền", "area_sqm": 120.0, "location_feature": "Cẩm Lệ",
              "road_width_m": 5.5, "frontage_width_m": 6},
     {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 120,
      "locationFeature": "Cẩm Lệ", "roadWidthM": 5.5, "frontageWidthM": 6}),
    ("apartment-balcony", {"category": "Căn hộ chung cư", "area_sqm": 75.0,
                           "location_feature": "Hải Châu", "rooms": 2, "bathrooms": 2,
                           "balcony_direction": "Đông"},
     {"propertyType": "APARTMENT", "transactionType": "SALE", "areaSqm": 75,
      "locationFeature": "Hải Châu", "bedrooms": 2, "bathrooms": 2,
      "balconyDirection": "Đông"}),
    ("villa", {"category": "Nhà ở", "area_sqm": 200.0, "location_feature": "Ngũ Hành Sơn",
               "floors": 3, "house_subtype": "villa", "road_width_m": 12,
               "frontage_width_m": 10},
     {"propertyType": "VILLA", "transactionType": "SALE", "areaSqm": 200,
      "locationFeature": "Ngũ Hành Sơn", "floors": 3, "houseSubtype": "villa",
      "roadWidthM": 12, "frontageWidthM": 10}),
    # Ward must never move the property to another district.
    ("ward-conflict", {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Cẩm Lệ",
                       "ward": "Hải Châu 1"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 80,
      "locationFeature": "Cẩm Lệ", "ward": "Hải Châu 1"}),
    # 0 bedrooms and omitted bedrooms must be the same effective input.
    ("bedrooms-zero", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                       "rooms": 0},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "bedrooms": 0}),
    ("bedrooms-omitted", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ"}),
    # NFC vs NFD must normalise to the same district.
    ("district-nfc", {"category": "Nhà ở", "area_sqm": 90.0, "location_feature": "Cẩm Lệ"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 90,
      "locationFeature": "Cẩm Lệ"}),
    # NFD thật: phân rã bằng unicodedata để không tự viết sai dấu.
    ("district-nfd", {"category": "Nhà ở", "area_sqm": 90.0,
                      "location_feature": unicodedata.normalize("NFD", "Cẩm Lệ")},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 90,
      "locationFeature": unicodedata.normalize("NFD", "Cẩm Lệ")}),
    # Street spelling variants.
    ("street-known", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                      "street_name": "Nguyễn Phước Lan"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "streetName": "Nguyễn Phước Lan"}),
    ("street-prefix", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                       "street_name": "Đường Nguyễn Phước Lan"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "streetName": "Đường Nguyễn Phước Lan"}),
    ("street-oov", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                    "street_name": "Đường Không Tồn Tại XYZ 123"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "streetName": "Đường Không Tồn Tại XYZ 123"}),
]

# Each negative case must be rejected and must produce NO inference record.
NEGATIVE = [
    ("neg-hanoi", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Hà Nội"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Hà Nội"}),
    ("neg-hcm", {"category": "Nhà ở", "area_sqm": 100.0,
                 "location_feature": "TP. Hồ Chí Minh"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "TP. Hồ Chí Minh"}),
    ("neg-unknown-district", {"category": "Nhà ở", "area_sqm": 100.0,
                              "location_feature": "Quận Không Tồn Tại"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Quận Không Tồn Tại"}),
    ("neg-land-balcony", {"category": "Đất nền", "area_sqm": 100.0,
                          "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
     {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}),
    ("neg-house-balcony", {"category": "Nhà ở", "area_sqm": 100.0,
                           "location_feature": "Cẩm Lệ", "balcony_direction": "Đông"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "balconyDirection": "Đông"}),
    ("neg-bedrooms-31", {"category": "Nhà ở", "area_sqm": 100.0,
                         "location_feature": "Cẩm Lệ", "rooms": 31},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "bedrooms": 31}),
    ("neg-subtype", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                     "house_subtype": "penthouse"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "houseSubtype": "penthouse"}),
]


def read_records(path):
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--capture", required=True)
    parser.add_argument("--a", default="http://127.0.0.1:8001")
    parser.add_argument("--b", default="http://127.0.0.1:8080")
    parser.add_argument("--pause", type=float, default=2.5)
    args = parser.parse_args()

    email = os.environ.get("SMARTPROP_PARITY_EMAIL")
    password = os.environ.get("SMARTPROP_PARITY_PASSWORD")
    if not email or not password:
        print("BLOCKED: set SMARTPROP_PARITY_EMAIL and SMARTPROP_PARITY_PASSWORD "
              "(credentials are never passed on the command line)")
        return 2

    capture = Path(args.capture)
    if capture.exists():
        capture.unlink()

    failures = []
    def check(ok, label, detail=""):
        print(f"  {'PASS' if ok else 'FAIL'}  {label}{'  -> ' + str(detail)[:110] if detail else ''}")
        if not ok:
            failures.append(label)

    # ---- prerequisite: login ----
    status, body = post(f"{args.b}/api/v1/auth/login", {"email": email, "password": password},
                        pause=0)
    token = body.get("accessToken")
    if status != 200 or not token:
        print(f"BLOCKED: login failed (status {status})")
        return 2
    print(f"login: {status}\n")

    paths = {"A": (f"{args.a}/predict", None), "B": (f"{args.b}/api/v1/properties/valuation-preview", token),
             "C": (f"{args.a}/predict/v1_3_preview", None)}

    print("=== POSITIVE: three-path parity ===")
    print(f"{'case':18s} {'A':>4s} {'B':>4s} {'C':>4s}  {'price A':>14s} {'encoded A/B/C':>14s}")
    positive_ok = 0
    for name, a_body, b_body in POSITIVE:
        responses = {}
        for path, (url, tkn) in paths.items():
            responses[path] = post(url, a_body if path != "B" else b_body, token=tkn, tag=name,
                                   pause=args.pause)
        records = [r for r in read_records(capture) if r.get("tag") == name]
        # B is routed through Spring, which does not forward the tag: match by growth instead.
        untagged = [r for r in read_records(capture) if not r.get("tag")]

        ok_status = all(responses[p][0] == 200 for p in paths)
        prices = {}
        for path in paths:
            body = responses[path][1]
            prices[path] = body.get("predictedAskingPriceVnd") or body.get("predicted_asking_price_vnd")
            if path == "B":
                ok_status = ok_status and body.get("available") is not False
        model_ok = all((responses[p][1].get("modelVersion") or responses[p][1].get("model_version")) == "v1.3"
                       for p in paths)
        encoded_a = records[0]["encoded"] if records else None
        encoded_c = records[1]["encoded"] if len(records) > 1 else None
        # exactly two tagged records expected (A and C); B arrives untagged
        ok_count = len(records) == 2 and len(untagged) >= 1
        if records and len(untagged) >= 1:
            b_rec = untagged[-1]["encoded"]
            same_ab = encoded_a == b_rec
            same_ac = encoded_a == encoded_c
        else:
            same_ab = same_ac = False
        price_ok = all(p and abs(int(p) - int(prices["A"] or 0)) <= TOLERANCE_VND for p in prices.values())

        # Warnings phải nhất quán theo semantics: nếu A cảnh báo street thì C cũng phải
        # cảnh báo, và B (Spring forward) cũng phải mang cùng cảnh báo đó.
        warnings_ok = True
        if "street" in name:
            def has_warning(path):
                body = responses[path][1]
                return any(STREET_WARNING_NEEDLE in str(w) for w in (body.get("warnings") or []))
            warnings_ok = has_warning("A") and has_warning("C") and has_warning("B")

        ok = (ok_status and model_ok and ok_count and same_ab and same_ac and price_ok
              and warnings_ok)
        positive_ok += 1 if ok else 0
        print(f"{name:18s} {responses['A'][0]:>4d} {responses['B'][0]:>4d} {responses['C'][0]:>4d}"
              f"  {str(prices['A']):>14s}  {str(same_ab and same_ac):>14s}")
        check(ok, f"positive {name}",
              f"status={ok_status} model={model_ok} records={len(records)}/{len(untagged)} "
              f"A=B:{same_ab} A=C:{same_ac} price={price_ok} warnings={warnings_ok}")
        if records:
            check(records[0]["input"].get("district") is not None, f"{name} district resolved",
                  records[0]["input"].get("district"))

    # bedrooms 0 and omitted must have the same encoded vector and has_bedroom=0
    zero = next((r for r in read_records(capture) if r.get("tag") == "bedrooms-zero"), None)
    omitted = next((r for r in read_records(capture) if r.get("tag") == "bedrooms-omitted"), None)
    if zero and omitted:
        check(zero["has_bedroom"] == 0, "bedrooms=0 -> has_bedroom=0", zero["has_bedroom"])
        check(omitted["has_bedroom"] == 0, "bedrooms omitted -> has_bedroom=0", omitted["has_bedroom"])
        check(zero["encoded"] == omitted["encoded"], "bedrooms 0 == omitted (encoded)")
    else:
        check(False, "bedrooms zero/omitted capture", "missing")

    # NFC and NFD must resolve to the same district
    nfc = next((r for r in read_records(capture) if r.get("tag") == "district-nfc"), None)
    nfd = next((r for r in read_records(capture) if r.get("tag") == "district-nfd"), None)
    if nfc and nfd:
        check(nfc["input"]["district"] == nfd["input"]["district"], "NFC == NFD district",
              f"{nfc['input']['district']} vs {nfd['input']['district']}")
    else:
        check(False, "NFC/NFD capture", "missing")

    # ward must not override the district
    conflict = next((r for r in read_records(capture) if r.get("tag") == "ward-conflict"), None)
    if conflict:
        check("cẩm lệ" == (conflict["input"]["district"] or "").casefold(),
              "ward cannot override district", conflict["input"].get("district"))

    print("\n=== NEGATIVE: rejection and no inference ===")
    negative_ok = 0
    for name, a_body, b_body in NEGATIVE:
        before = len(read_records(capture))
        a_status, _ = post(f"{paths['A'][0]}", a_body, tag=name, pause=args.pause)
        c_status, _ = post(f"{paths['C'][0]}", a_body, tag=name, pause=args.pause)
        b_status, b_body_resp = post(paths["B"][0], b_body, token=token, tag=name, pause=args.pause)
        after = read_records(capture)
        b_price = b_body_resp.get("predictedAskingPriceVnd")
        b_rejected = b_status >= 400 or b_body_resp.get("available") is False
        ok = (a_status == 422 and c_status == 422 and b_rejected and not b_price
              and len(after) == before)
        negative_ok += 1 if ok else 0
        print(f"{name:20s} A={a_status} C={c_status} B={b_status} "
              f"px={bool(b_price)} new_records={len(after) - before}")
        check(ok, f"negative {name}",
              f"A={a_status} C={c_status} B={b_status} price={b_price} records+={len(after)-before}")

    total_positive, total_negative = len(POSITIVE), len(NEGATIVE)
    print(f"\npositive: {positive_ok}/{total_positive} · negative: {negative_ok}/{total_negative}"
          f" · total cases: {total_positive + total_negative}")
    print(f"=== THREE-PATH PARITY: {'PASS' if not failures else 'FAIL'} ({len(failures)} lỗi) ===")
    return 0 if not failures else 1


if __name__ == "__main__":
    sys.exit(main())
