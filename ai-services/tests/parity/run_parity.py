"""Reproducible cross-flow / cross-endpoint parity check.

Run it the same way a reviewer would:

    # 1. MySQL fixture (see docs: WP-01 runbook), then:
    cd ai-services
    SMARTPROP_PARITY_CAPTURE=/tmp/parity.jsonl \
      uvicorn tests.parity.capture_app:app --host 127.0.0.1 --port 8001

    # 2. Spring Boot pointed at the capture server
    APP_VALUATION_ENABLED=true APP_VALUATION_BASE_URL=http://127.0.0.1:8001 \
      ./mvnw spring-boot:run

    # 3. Then
    python -m tests.parity.run_parity --capture /tmp/parity.jsonl --a http://127.0.0.1:8001 \
        --b http://127.0.0.1:8080 --email <test> --password <test>

Dependencies: the ai-services virtualenv (pandas, fastapi) plus a running FastAPI and
Spring Boot. The capture file is temporary output and must never be committed.
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import pandas as pd

from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3
from app.models.xgboost.features_v1_3 import ALL_FEATURES, transform

SERVICE_ROOT = Path(__file__).resolve().parents[2]
SCHEMA = json.loads((SERVICE_ROOT / "artifacts/v1_3/feature_schema.json").read_text(encoding="utf-8"))

# Metadata the posting flow carries but the model does not consume.
NON_FEATURES = frozenset({"title", "description"})

RENAME = {
    "street_name": "raw_street_name",
    "project_name": "raw_project_name",
    "house_direction": "raw_house_direction",
    "balcony_direction": "raw_balcony_direction",
    "floor_count": "raw_floor_count",
    "frontage_width": "raw_frontage_width",
    "road_width": "raw_road_width",
    "bedroom_count": "raw_bedroom_count",
    "bathroom_count": "raw_bathroom_count",
}


def frame(payload):
    mapped = map_v6_to_v1_3(payload, district_vocabulary=SCHEMA["vocabularies"]["district"])
    row = {RENAME.get(k, k): v for k, v in mapped.items()}
    row["ward"] = payload.get("ward")
    return pd.DataFrame([row])


CASES = [
    ("HOUSE basic", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                     "ward": "Hòa Thọ Đông", "rooms": 3},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "ward": "Hòa Thọ Đông", "bedrooms": 3}),
    ("HOUSE enriched", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                        "ward": "Hòa Thọ Đông", "rooms": 3, "road_width_m": 12,
                        "frontage_width_m": 6, "street_name": "Nguyễn Phước Lan",
                        "floors": 3, "house_subtype": "house_c4", "bathrooms": 2,
                        "house_direction": "Đông Nam"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "ward": "Hòa Thọ Đông", "bedrooms": 3,
      "roadWidthM": 12, "frontageWidthM": 6, "streetName": "Nguyễn Phước Lan",
      "floors": 3, "houseSubtype": "house_c4", "bathrooms": 2, "houseDirection": "Đông Nam"}),
    ("LAND", {"category": "Đất nền", "area_sqm": 120.0, "location_feature": "Cẩm Lệ",
              "road_width_m": 5.5, "frontage_width_m": 6},
     {"propertyType": "LAND", "transactionType": "SALE", "areaSqm": 120,
      "locationFeature": "Cẩm Lệ", "roadWidthM": 5.5, "frontageWidthM": 6}),
    ("APARTMENT", {"category": "Căn hộ chung cư", "area_sqm": 75.0, "location_feature": "Hải Châu",
                   "rooms": 2, "bathrooms": 2, "balcony_direction": "Đông"},
     {"propertyType": "APARTMENT", "transactionType": "SALE", "areaSqm": 75,
      "locationFeature": "Hải Châu", "bedrooms": 2, "bathrooms": 2, "balconyDirection": "Đông"}),
    ("VILLA", {"category": "Nhà ở", "area_sqm": 200.0, "location_feature": "Ngũ Hành Sơn",
               "floors": 3, "house_subtype": "villa", "road_width_m": 12, "frontage_width_m": 10},
     {"propertyType": "VILLA", "transactionType": "SALE", "areaSqm": 200,
      "locationFeature": "Ngũ Hành Sơn", "floors": 3, "houseSubtype": "villa",
      "roadWidthM": 12, "frontageWidthM": 10}),
    # Adversarial: ward must not steal the district.
    ("conflict ward", {"category": "Nhà ở", "area_sqm": 80.0, "location_feature": "Cẩm Lệ",
                       "ward": "Hải Châu 1"},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 80,
      "locationFeature": "Cẩm Lệ", "ward": "Hải Châu 1"}),
    # 0 bedrooms means "not declared" on both flows.
    ("zero bedrooms", {"category": "Nhà ở", "area_sqm": 100.0, "location_feature": "Cẩm Lệ",
                       "rooms": 0},
     {"propertyType": "HOUSE", "transactionType": "SALE", "areaSqm": 100,
      "locationFeature": "Cẩm Lệ", "bedrooms": 0}),
]


def post(url, body, token=None, pause=3.0):
    time.sleep(pause)
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = "Bearer " + token
    req = urllib.request.Request(url, data=json.dumps(body, ensure_ascii=False).encode(),
                                 headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, {}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--capture", required=True)
    ap.add_argument("--a", default="http://127.0.0.1:8001")
    ap.add_argument("--b", default="http://127.0.0.1:8080")
    ap.add_argument("--email", required=True)
    ap.add_argument("--password", required=True)
    args = ap.parse_args()

    capture = Path(args.capture)
    if capture.exists():
        capture.unlink()

    status, token_body = post(f"{args.b}/api/v1/auth/login",
                              {"email": args.email, "password": args.password})
    token = token_body.get("accessToken")
    print("login:", status)

    for label, a_body, b_body in CASES:
        post(f"{args.a}/predict", a_body)
        post(f"{args.b}/api/v1/properties/valuation-preview", b_body, token)
        print("sent:", label)

    records = [json.loads(line) for line in capture.read_text(encoding="utf-8").splitlines() if line.strip()]
    if len(records) < 2 * len(CASES):
        print(f"BLOCKED: only {len(records)} captures"); return 2

    failures = 0
    print(f"\n{'case':16s} {'payload':>8s} {'encoded':>8s}")
    for index, (label, _, _) in enumerate(CASES):
        left, right = records[2 * index], records[2 * index + 1]
        a_keys = {k: v for k, v in left.items() if k not in NON_FEATURES}
        b_keys = {k: v for k, v in right.items() if k not in NON_FEATURES}
        same_payload = a_keys == b_keys
        same_encoded = transform(frame(left), SCHEMA).equals(transform(frame(right), SCHEMA))
        if not (same_payload and same_encoded):
            failures += 1
            print(f"  diff {label}: {a_keys} vs {b_keys}")
        print(f"{label:16s} {str(same_payload):>8s} {str(same_encoded):>8s}")

    print(f"\nfeatures compared: {len(ALL_FEATURES)}")
    print(f"=== PARITY: {'PASS' if failures == 0 else 'FAIL'} ({failures} lỗi) ===")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
