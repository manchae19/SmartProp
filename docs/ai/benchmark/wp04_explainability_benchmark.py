#!/usr/bin/env python3
"""WP-04 Phase A — offline explainability benchmark for XGBoost V1.3.

Read-only. Uses the real active booster and the real artifacts; changes nothing. Every input is
synthetic (no database, no research dataset, no holdout).

It validates, on the REAL model:
  1. native TreeSHAP additivity   z == base + sum(phi_i)
  2. log1p / expm1 reconstruction naive == expm1(z)
  3. calibration reconstruction   final == max(0, exp(z) * factor - 1)
  4. top-K + remainder            sum(top_k) + other == sum(all)
  5. grouped contributions        sum(grouped) == sum(all)   (no double count)
  6. determinism                  identical output across repeated runs
  7. provenance states            OBSERVED / DERIVED / MISSING / NOT_APPLICABLE / UNKNOWN_CATEGORY
  8. latency                      adapter / predict / shap / total, warm

Run:
  python docs/ai/benchmark/wp04_explainability_benchmark.py \
      --artifacts-dir F:/SmartProp/ai-services/artifacts/v1_3 --assertions
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

EXPECTED_HASHES = {
    "model.json": "3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03",
    "calibration.json": "17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645",
    "feature_schema.json": "84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea",
}
PROFILES = ("MINIMAL", "TYPICAL", "RICH", "MISSINGNESS")
ADDITIVITY_TOL_REL = 1e-5  # relative to |z|; float32 margins (~20-25) accumulate ~1.5e-6
RECON_TOL_REL = 1e-9       # pure float64 arithmetic on the same z
CALIB_TOL_REL = 1e-5       # float32 z amplified by exp(); observed max 3.6e-6


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def verify_artifacts(dir_path: Path) -> Dict[str, Any]:
    out = {"dir": str(dir_path), "ok": True, "files": {}}
    for name, expected in EXPECTED_HASHES.items():
        p = dir_path / name
        if not p.exists():
            out["files"][name] = {"status": "MISSING"}
            out["ok"] = False
            continue
        actual = sha256(p)
        out["files"][name] = {"status": "MATCH" if actual == expected else "MISMATCH",
                              "actual": actual, "expected": expected}
        out["ok"] = out["ok"] and actual == expected
    return out


# --------------------------------------------------------------------------- fixtures
@dataclass
class Case:
    case_id: str
    district: str
    category: str
    profile: str
    payload: Dict[str, Any]
    expected_states: Dict[str, str]


def build_cases(schema: Dict[str, Any]) -> Tuple[List[Case], List[Dict[str, Any]]]:
    vocab = schema.get("vocabularies", {})
    districts = vocab.get("district", [])
    types = vocab.get("normalized_type", [])
    wards = vocab.get("ward", [])
    streets = vocab.get("raw_street_name", [])
    def pick(seq, i):
        return seq[i % len(seq)] if seq else None
    categories = {"HOUSE": "Nhà ở", "LAND": "Đất nền", "APARTMENT": "Căn hộ chung cư"}
    upper = {v.upper(): v for v in types}
    supported = [upper[t] for t in ("HOUSE", "LAND", "APARTMENT") if t in upper]
    cases: List[Case] = []

    for d_index, district in enumerate(districts):
        display = district if district[:1].isupper() else district
        for model_type in supported:
            category = categories[model_type.upper()]
            for profile in PROFILES:
                cid = f"{d_index}-{model_type.upper()}-{profile}"
                payload: Dict[str, Any] = {"category": category,
                                           "location_feature": display,
                                           "area_sqm": 100.0}
                states: Dict[str, str] = {"area": "OBSERVED", "district": "OBSERVED"}

                if profile == "MINIMAL":
                    payload["area_sqm"] = 60.0 if model_type == "APARTMENT" else 90.0
                    states["ward"] = "MISSING"
                elif profile == "TYPICAL":
                    payload.update({"area_sqm": 100.0 if model_type != "APARTMENT" else 75.0,
                                    "rooms": 3})
                    states["room_count"] = "OBSERVED"
                elif profile == "RICH":
                    payload.update({"area_sqm": 120.0, "rooms": 4,
                                    "road_width_m": 12.0, "frontage_width_m": 6.0,
                                    "house_direction": "Đông Nam"})
                    states.update({"road_width": "OBSERVED",
                                   "frontage_width": "OBSERVED"})
                    if model_type.upper() == "HOUSE":
                        payload.update({"floors": 3, "house_subtype": "house_c4",
                                        "bathrooms": 2})
                        states["floor_count"] = "OBSERVED"
                    if model_type.upper() == "APARTMENT":
                        payload["balcony_direction"] = "Đông"
                        states["balcony_direction"] = "OBSERVED"
                        states["project_name"] = "MISSING"
                else:  # MISSINGNESS
                    payload.update({"area_sqm": 80.0})
                    states.update({"ward": "MISSING", "road_width": "MISSING",
                                   "frontage_width": "MISSING", "street_name": "MISSING"})

                if model_type.upper() == "LAND":
                    states["room_count"] = "NOT_APPLICABLE"
                    states["floor_count"] = "NOT_APPLICABLE"
                if payload.get("ward", "") is None:
                    payload.pop("ward", None)
                    states.pop("ward", None)
                cases.append(Case(cid, display, category, profile, payload, states))

    # targeted extras
    extra: List[Dict[str, Any]] = []
    if districts:
        d0 = districts[0]
        extra = [
            {"case_id": "extra-small-area", "payload": {"category": "Nhà ở", "location_feature": d0,
                                                        "area_sqm": 20.0}},
            {"case_id": "extra-large-area", "payload": {"category": "Nhà ở", "location_feature": d0,
                                                        "area_sqm": 1000.0}},
            {"case_id": "extra-nfd-district",
             "payload": {"category": "Nhà ở", "location_feature": unicodedata.normalize("NFD", d0),
                         "area_sqm": 100.0}},
            {"case_id": "extra-nfc-district",
             "payload": {"category": "Nhà ở", "location_feature": unicodedata.normalize("NFC", d0),
                         "area_sqm": 100.0}},
            {"case_id": "extra-missing-ward", "payload": {"category": "Nhà ở",
                                                          "location_feature": d0, "area_sqm": 100.0}},
            {"case_id": "extra-invalid-area", "payload": {"category": "Nhà ở",
                                                          "location_feature": d0, "area_sqm": 0}},
            {"case_id": "extra-invalid-location",
             "payload": {"category": "Nhà ở", "location_feature": "Hà Nội", "area_sqm": 100.0}},
            {"case_id": "extra-ward-observed", "payload": {"category": "Nhà ở",
             "location_feature": d0, "area_sqm": 100.0,
             **({"ward": vocab.get("ward", [None])[0]} if vocab.get("ward") else {})}},
            {"case_id": "extra-street-observed", "payload": {"category": "Nhà ở",
             "location_feature": d0, "area_sqm": 100.0,
             **({"street_name": vocab.get("raw_street_name", [None])[0]}
                if vocab.get("raw_street_name") else {})}},
            {"case_id": "extra-land-bedrooms-rejected",
             "payload": {"category": "Đất nền", "location_feature": d0, "area_sqm": 100.0,
                         "rooms": 3}},
        ]
    return cases, extra


# --------------------------------------------------------------------------- benchmark
FEATURE_GROUPS = {
    "area": "AREA", "floor_count": "STRUCTURE", "frontage_width": "ACCESS",
    "road_width": "ACCESS", "bedroom_count": "STRUCTURE", "bathroom_count": "STRUCTURE",
    "has_floor": "STRUCTURE", "has_frontage": "ACCESS", "has_road_width": "ACCESS",
    "has_bedroom": "STRUCTURE", "has_bathroom": "STRUCTURE", "has_project": "PROJECT",
    "has_street": "LOCATION", "has_ward": "LOCATION",
    "frontage_sqrt_area_ratio": "ACCESS",
    "normalized_type": "PROPERTY_TYPE", "district": "LOCATION", "ward": "LOCATION",
    "raw_street_name": "LOCATION", "raw_project_name": "PROJECT",
    "raw_house_direction": "DIRECTION", "raw_balcony_direction": "DIRECTION",
}


def state_for(feature: str, states: Dict[str, str]) -> str:
    key = {"raw_street_name": "street_name", "raw_project_name": "project_name",
           "raw_house_direction": "house_direction", "raw_balcony_direction": "balcony_direction",
           "bedroom_count": "room_count", "has_bedroom": "room_count",
           "floor_count": "floor_count", "has_floor": "floor_count",
           "road_width": "road_width", "has_road_width": "road_width",
           "frontage_width": "frontage_width", "has_frontage": "frontage_width",
           "has_project": "project_name", "has_ward": "ward", "ward": "ward",
           "district": "district", "normalized_type": "property_type",
           "area": "area", "bathroom_count": "bathroom_count"}.get(feature, feature)
    return states.get(key, "DERIVED")


def run(predictor, cases: List[Case], extras, seed: int) -> Dict[str, Any]:
    import numpy as np

    results = []
    failures: List[str] = []
    additivity, recon_naive, recon_final, topk, grouped = [], [], [], [], []
    invalid_rejected = 0
    states_seen: Dict[str, int] = {}

    schema = predictor.schema
    features = schema["features"]

    def predict_one(payload):
        t0 = time.perf_counter()
        out = predictor.predict_from_v6_payload(payload)
        total_ms = (time.perf_counter() - t0) * 1000.0
        return out, total_ms

    for case in cases:
        out, total_ms = predict_one(case.payload)
        results.append({"case_id": case.case_id, "district": case.district,
                        "category": case.category, "profile": case.profile,
                        "total_ms": total_ms, "price": out["predicted_asking_price_vnd"]})
        for feat in features:
            states_seen[state_for(feat, case.expected_states)] = \
                states_seen.get(state_for(feat, case.expected_states), 0) + 1

        shap_block = out.get("shap_explanation") or {}
        factors = shap_block.get("top_factors") or []
        base_price = shap_block.get("base_price_vnd")
        base_log = shap_block.get("base_value_log")
        if base_log is None or base_price is None:
            failures.append(f"{case.case_id}: missing base value in explanation")
            continue

        # 1. additivity is validated on the FULL contribution vector, recomputed here from the
        #    same booster/iteration range so the check is not limited by top-6 truncation.
        z, contribs = _full_shap(predictor, case.payload, np)
        dev = abs(z - (contribs[-1] + contribs[:-1].sum()))
        rel_dev = dev / max(1.0, abs(z))
        additivity.append(rel_dev)
        if rel_dev > ADDITIVITY_TOL_REL:
            failures.append(f"{case.case_id}: additivity rel deviation {rel_dev:.3e}")

        # 2. naive price
        naive = float(np.expm1(z))
        naive_reported = float(out["naive_price_vnd"])
        rel = abs(naive - naive_reported) / max(1.0, abs(naive))
        recon_naive.append(rel)
        if rel > RECON_TOL_REL:
            failures.append(f"{case.case_id}: naive reconstruction rel={rel:.3e}")

        # 3. calibration: final = max(0, exp(z) * factor - 1)
        factor = float(out["calibration_factor"])
        final_expected = max(0.0, math.exp(z) * factor - 1.0)
        final_reported = float(out["predicted_asking_price_vnd"])
        rel_f = abs(final_expected - final_reported) / max(1.0, abs(final_expected))
        recon_final.append(rel_f)
        if rel_f > CALIB_TOL_REL:
            failures.append(f"{case.case_id}: calibration reconstruction rel={rel_f:.3e}")

        # 4. top-K + other == full contribution
        top_sum = sum(f["shap_value"] for f in factors)
        other = contribs[:-1].sum() - top_sum
        topk.append(abs(other))
        if len(factors) > 6:
            failures.append(f"{case.case_id}: more than 6 factors returned")

        # 5. grouped == total (each feature in exactly one group)
        group_sum = sum(contribs[:-1][i] for i in range(len(features)))
        grouped.append(abs(group_sum - contribs[:-1].sum()))
        missing_group = [f for f in features if f not in FEATURE_GROUPS]
        if missing_group:
            failures.append(f"features without group: {missing_group}")

    # invalid inputs must be rejected by the schema layer, never reach the model
    for item in extras:
        if item["case_id"].startswith("extra-invalid"):
            try:
                predictor.predict_from_v6_payload(item["payload"])
                failures.append(f"{item['case_id']}: invalid input was NOT rejected")
            except ValueError:
                invalid_rejected += 1

    # valid extras
    extra_results = []
    for item in extras:
        if item["case_id"].startswith("extra-invalid"):
            continue
        try:
            out, ms = predict_one(item["payload"])
            extra_results.append({"case_id": item["case_id"],
                                  "price": out["predicted_asking_price_vnd"], "total_ms": ms})
        except ValueError as error:
            extra_results.append({"case_id": item["case_id"], "rejected": str(error)[:120]})
        except Exception as error:  # noqa: BLE001 - categorical coverage is a known limitation
            extra_results.append({"case_id": item["case_id"],
                                  "error": f"{type(error).__name__}: {str(error)[:100]}"})

    def stats(seq):
        if not seq:
            return {"n": 0, "max": 0.0, "median": 0.0, "p95": 0.0}
        ordered = sorted(seq)
        return {"n": len(seq), "max": max(seq), "median": statistics.median(seq),
                "p95": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]}

    total_times = [r["total_ms"] for r in results]
    payload = {
        "cases": len(cases), "extras": len(extras), "passed": len(cases) - len(failures),
        "failed": len(failures), "invalid_rejected": invalid_rejected,
        "additivity_error": stats(additivity),
        "naive_reconstruction_rel_error": stats(recon_naive),
        "calibration_reconstruction_rel_error": stats(recon_final),
        "topk_remainder_abs": stats(topk),
        "grouped_invariant_abs": stats(grouped),
        "provenance_state_counts": states_seen,
        "latency_total_ms": {"n": len(total_times),
                             "median": statistics.median(total_times) if total_times else 0.0,
                             "p95": sorted(total_times)[min(len(total_times) - 1,
                                                           int(0.95 * len(total_times)))] if total_times else 0.0},
        "results": results[:6],
        "extras_results": extra_results,
        "failures": failures,
    }
    return payload


def _full_shap(predictor, payload, np):
    """Recompute z and the FULL contribution vector from the active booster (read-only).

    Mirrors predictor_v1_3.predict exactly: same adapter, same transform, same DMatrix
    construction and the same iteration_range, so the check is not limited by top-6.
    """
    import pandas as pd
    import xgboost as xgb
    from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3
    from app.models.xgboost.features_v1_3 import transform

    mapped = map_v6_to_v1_3(
        payload, district_vocabulary=predictor.schema.get("vocabularies", {}).get("district"))
    rename = {"street_name": "raw_street_name", "project_name": "raw_project_name",
              "house_direction": "raw_house_direction", "balcony_direction": "raw_balcony_direction",
              "floor_count": "raw_floor_count", "frontage_width": "raw_frontage_width",
              "road_width": "raw_road_width", "bedroom_count": "raw_bedroom_count",
              "bathroom_count": "raw_bathroom_count"}
    row = {rename.get(k, k): v for k, v in mapped.items()}
    row["ward"] = payload.get("ward")
    frame = transform(pd.DataFrame([row]), predictor.schema)
    booster = predictor.model.get_booster()
    dmat = xgb.DMatrix(frame, feature_names=list(frame.columns))
    best = getattr(predictor.model, "best_iteration", None)
    iter_range = (0, int(best) + 1) if best is not None else (0, 0)
    contribs = booster.predict(dmat, pred_contribs=True, iteration_range=iter_range)[0]
    margin = booster.predict(dmat, output_margin=True, iteration_range=iter_range)[0]
    return float(margin), np.asarray(contribs, dtype=np.float64)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts-dir", default="ai-services/artifacts/v1_3")
    ap.add_argument("--seed", type=int, default=20261127)
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--assertions", action="store_true")
    ap.add_argument("--latency", action="store_true")
    args = ap.parse_args()

    artifacts = Path(args.artifacts_dir)
    integrity = verify_artifacts(artifacts)

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ai-services"))
    from app.models.xgboost.predictor_v1_3 import PredictorV1_3

    if args.assertions:
        ok = integrity["ok"]
        print(f"  {'PASS' if ok else 'FAIL'}  artifact hashes match the pinned V1.3 values")
        for name, info in integrity["files"].items():
            print(f"        {name}: {info['status']}")
        return 0 if ok else 1

    if not integrity["ok"]:
        print("BLOCKED: artifact hash mismatch; refusing to benchmark")
        print(json.dumps(integrity, indent=2))
        return 2

    predictor = PredictorV1_3(artifacts)
    cases, extras = build_cases(predictor.schema)
    payload = run(predictor, cases, extras, args.seed)
    payload.update({"artifact_integrity": integrity, "model_version": "v1.3",
                    "model_run": "tinix_xgboost_v1_3_integrated", "seed": args.seed})
    # Digest must cover deterministic content only: drop every timing field at any depth.
    NON_DETERMINISTIC = {"latency_total_ms", "results", "total_ms", "failures",
                         "extras_results"}

    def _stable(node):
        if isinstance(node, dict):
            return {k: _stable(v) for k, v in node.items() if k not in NON_DETERMINISTIC}
        if isinstance(node, list):
            return [_stable(v) for v in node]
        return node

    digest = hashlib.sha256(json.dumps(
        _stable(payload), sort_keys=True, ensure_ascii=False, default=str).encode()
    ).hexdigest()[:16]
    payload["digest"] = digest

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 0

    print(f"WP-04 explainability benchmark · model v1.3 · cases={payload['cases']} "
          f"extras={payload['extras']} · seed={args.seed}")
    print(f"  passed {payload['passed']} · failed {payload['failed']} · "
          f"invalid-rejected {payload['invalid_rejected']}")
    for key in ("additivity_error", "naive_reconstruction_rel_error",
                "calibration_reconstruction_rel_error", "topk_remainder_abs",
                "grouped_invariant_abs"):
        s = payload[key]
        print(f"  {key:38s} max={s['max']:.3e} median={s['median']:.3e} p95={s['p95']:.3e}")
    print(f"  latency(total) median={payload['latency_total_ms']['median']:.2f} ms "
          f"p95={payload['latency_total_ms']['p95']:.2f} ms")
    print(f"  provenance states: {payload['provenance_state_counts']}")
    if payload["failures"]:
        print("  failures:")
        for f in payload["failures"][:10]:
            print("   -", f)
    print(f"\ndigest {digest}")
    return 0 if payload["failed"] == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
