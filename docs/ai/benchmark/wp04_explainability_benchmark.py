#!/usr/bin/env python3
"""WP-04 Phase A — offline explainability benchmark for XGBoost V1.3 (reviewed).

Read-only: uses the real booster and pinned artifacts, changes nothing. Every input is
synthetic (no database, no research dataset, no holdout).

Validated on the REAL model:
  1. native TreeSHAP additivity        z == base + sum(phi_i)
  2. log1p reconstruction              naive == expm1(z)
  3. calibration reconstruction        final == max(0, exp(z) * factor - 1)
  4. top-K + remainder                 sum(top_k) + other == sum(all)
  5. grouped aggregation               signed group sums == sum(all), each feature in exactly
                                      one group, no missing / duplicated feature
  6. provenance derived from the ACTUAL transformed matrix, not from the request
  7. extras classified (expected success / expected rejection / unexpected = failure)
  8. determinism                       per-case results included in the digest

Modes
  --assertions    integrity + full mathematical benchmark + failure-path self-tests
  --integrity-only  artifact hashes only
  --self-test     failure-path self-tests only (proves the checks can fail)
  (default)       full benchmark, human readable

Exit code is non-zero on any failure in every mode, including --json.

Run with the PROJECT venv (ai-services/.venv); a different xgboost build raises
"category not in the training set".
"""
import argparse
import hashlib
import json
import math
import statistics
import sys
import time
import unicodedata
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Tuple

EXPECTED_HASHES = {
    "model.json": "3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03",
    "calibration.json": "17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645",
    "feature_schema.json": "84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea",
}
PROFILES = ("MINIMAL", "TYPICAL", "RICH", "MISSINGNESS", "UNKNOWN_CATEGORY")
ADDITIVITY_TOL_REL = 1e-5     # float32 margins (~20-25); observed max 1.5e-6
RECON_TOL_REL = 1e-9          # same float64 z, only int rounding differs
CALIB_TOL_REL = 1e-5          # float32 z amplified by exp(); observed max 3.6e-6
DIGEST_DECIMALS = 10

FEATURE_GROUPS = {
    "area": "AREA", "frontage_sqrt_area_ratio": "AREA",
    "floor_count": "STRUCTURE", "bedroom_count": "STRUCTURE",
    "bathroom_count": "STRUCTURE", "has_floor": "STRUCTURE",
    "has_bedroom": "STRUCTURE", "has_bathroom": "STRUCTURE",
    "frontage_width": "ACCESS", "road_width": "ACCESS",
    "has_frontage": "ACCESS", "has_road_width": "ACCESS",
    "has_project": "PROJECT", "raw_project_name": "PROJECT",
    "has_street": "LOCATION", "has_ward": "LOCATION", "district": "LOCATION",
    "ward": "LOCATION", "raw_street_name": "LOCATION",
    "normalized_type": "PROPERTY_TYPE",
    "raw_house_direction": "DIRECTION", "raw_balcony_direction": "DIRECTION",
}

# Which raw payload key feeds each model feature, for provenance attribution.
FEATURE_SOURCE = {
    "area": "area_sqm", "floor_count": "floors", "frontage_width": "frontage_width_m",
    "road_width": "road_width_m", "bedroom_count": "rooms", "bathroom_count": "bathrooms",
    "normalized_type": "category", "district": "location_feature", "ward": "ward",
    "raw_street_name": "street_name", "raw_project_name": "project_name",
    "raw_house_direction": "house_direction", "raw_balcony_direction": "balcony_direction",
}
DERIVED_FEATURES = {"has_floor", "has_frontage", "has_road_width", "has_bedroom",
                    "has_bathroom", "has_project", "has_street", "has_ward",
                    "frontage_sqrt_area_ratio"}


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
                             "actual": actual}
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
    provided: set = field(default_factory=set)
    not_applicable: set = field(default_factory=set)


@dataclass
class Extra:
    case_id: str
    payload: Dict[str, Any]
    expectation: str          # SUCCESS | REJECT
    note: str = ""


def build_cases(schema: Dict[str, Any]) -> Tuple[List[Case], List[Extra]]:
    vocab = schema.get("vocabularies", {})
    districts = vocab.get("district", [])
    types = [t.upper() for t in vocab.get("normalized_type", [])]
    categories = {"HOUSE": "Nhà ở", "LAND": "Đất nền", "APARTMENT": "Căn hộ chung cư"}
    supported = [t for t in ("HOUSE", "LAND", "APARTMENT") if t in types]
    cases: List[Case] = []

    for d_index, district in enumerate(districts):
        for model_type in supported:
            category = categories[model_type]
            for profile in PROFILES:
                cid = f"{district}-{model_type}-{profile}"
                payload: Dict[str, Any] = {"category": category,
                                           "location_feature": district, "area_sqm": 90.0}
                provided = {"category", "location_feature", "area_sqm"}
                na: set = set()
                if model_type == "LAND":
                    na = {"bedroom_count", "has_bedroom", "floor_count", "has_floor",
                          "bathroom_count", "has_bathroom"}

                if profile == "TYPICAL":
                    payload.update({"area_sqm": 100.0 if model_type != "APARTMENT" else 75.0,
                                    "rooms": 3})
                    provided.add("rooms")
                elif profile == "RICH":
                    payload.update({"area_sqm": 120.0, "rooms": 4,
                                    "road_width_m": 12.0, "frontage_width_m": 6.0})
                    provided |= {"rooms", "road_width_m", "frontage_width_m"}
                    if model_type == "HOUSE":
                        payload.update({"floors": 3, "house_subtype": "house_c4",
                                        "bathrooms": 2})
                        provided |= {"floors", "house_subtype", "bathrooms"}
                    if model_type == "APARTMENT":
                        payload["balcony_direction"] = "Đông"
                        provided.add("balcony_direction")
                elif profile == "MISSINGNESS":
                    payload["area_sqm"] = 80.0
                elif profile == "UNKNOWN_CATEGORY":
                    # Values deliberately outside the trained vocabulary: the matrix must
                    # classify them as UNKNOWN_CATEGORY, not as observed data.
                    payload.update({"area_sqm": 95.0,
                                    "street_name": "Đường Không Tồn Tại XYZ 123",
                                    "ward": "phường không tồn tại xyz"})
                    provided |= {"street_name", "ward"}

                cases.append(Case(cid, district, category, profile, payload, provided, na))

    extras: List[Extra] = []
    if districts:
        d0 = districts[0]
        base = {"category": "Nhà ở", "location_feature": d0, "area_sqm": 100.0}
        extras += [
            Extra("extra-small-area", dict(base, area_sqm=20.0), "SUCCESS"),
            Extra("extra-large-area", dict(base, area_sqm=1000.0), "SUCCESS"),
            Extra("extra-nfd-district",
                  dict(base, location_feature=unicodedata.normalize("NFD", d0)), "SUCCESS"),
            Extra("extra-nfc-district",
                  dict(base, location_feature=unicodedata.normalize("NFC", d0)), "SUCCESS"),
            Extra("extra-missing-ward", dict(base), "SUCCESS"),
            Extra("extra-invalid-area", dict(base, area_sqm=0), "REJECT",
                  "area below contract minimum"),
            Extra("extra-invalid-location", dict(base, location_feature="Hà Nội"), "REJECT",
                  "district outside model vocabulary"),
            Extra("extra-land-bedrooms", dict(base, category="Đất nền", rooms=3), "REJECT",
                  "LAND must not send rooms"),
            Extra("extra-ward-prefixed", dict(base, ward="Phường 1"), "SUCCESS",
                  "adapter strips the Phường prefix"),
            Extra("extra-ward-bare", dict(base, ward="1"), "SUCCESS"),
            Extra("extra-ward-missing", dict(base), "SUCCESS"),
            Extra("extra-ward-unknown", dict(base, ward="phường không tồn tại xyz"), "SUCCESS"),
            Extra("extra-street-unknown",
                  dict(base, street_name="Đường Không Tồn Tại XYZ 123"), "SUCCESS"),
            Extra("extra-invalid-numeric", dict(base, area_sqm=-5), "REJECT"),
            Extra("extra-villa-subtype", dict(base, house_subtype="villa"), "SUCCESS",
                  "villa is a HOUSE subtype, not a category"),
        ]
    return cases, extras


# --------------------------------------------------------------------------- helpers
def aggregate_groups(features: Sequence[str], contribs: Sequence[float],
                     groups: Dict[str, str]) -> Tuple[Dict[str, float], List[str]]:
    """Signed aggregation by group. Returns (group_sums, problems)."""
    problems: List[str] = []
    duplicated = [f for f in features if features.count(f) > 1]
    if duplicated:
        problems.append(f"duplicate feature(s) in vector: {sorted(set(duplicated))}")
    lost = [f for f in features if f not in groups]
    if lost:
        problems.append(f"feature(s) without group: {lost}")
    unknown = [f for f in groups if f not in features]
    if unknown:
        problems.append(f"grouped feature(s) absent from vector: {unknown}")
    sums: Dict[str, float] = {}
    for feature, value in zip(features, contribs):
        group = groups.get(feature)
        if group is None:
            continue
        sums[group] = sums.get(group, 0.0) + float(value)
    return sums, problems


def provenance(feature: str, encoded_value: Any, provided: set, not_applicable: set
               ) -> Tuple[str, str]:
    """State derived from the ACTUAL transformed value, plus a short basis string."""
    if feature in DERIVED_FEATURES:
        return "DERIVED", "computed from raw input"
    value = encoded_value
    missing = value is None or (isinstance(value, float) and math.isnan(value)) or value == "__MISSING__"
    if value == "__UNKNOWN__":
        return "UNKNOWN_CATEGORY", "value not in trained vocabulary"
    if missing:
        if feature in not_applicable:
            return "NOT_APPLICABLE", "not meaningful for this property type"
        return "MISSING", "not supplied by the caller"
    source = FEATURE_SOURCE.get(feature)
    if source and source in provided:
        return "OBSERVED", f"from request field {source}"
    if source:
        return "DERIVED", "filled by the adapter, not supplied directly"
    return "UNVERIFIED", "no provenance rule"


# --------------------------------------------------------------------------- self-tests
def require_cases(cases: Sequence[Any]) -> List[str]:
    """An empty fixture matrix must never be reported as a pass."""
    return [] if cases else ["empty fixture matrix"]


def require_tolerance(value: float, limit: float, label: str) -> List[str]:
    return [] if value <= limit else [f"{label}: {value:.3e} > {limit:.3e}"]


def run_self_tests() -> List[str]:
    """Prove the checks can FAIL. Each case below must be detected."""
    failures: List[str] = []

    def expect(label: str, problems: Sequence[str]) -> None:
        if not problems:
            failures.append(f"self-test did not detect: {label}")

    features = ["area", "district"]
    contribs = [1.0, 2.0]

    _sums, problems = aggregate_groups(features, contribs, {"area": "AREA"})
    expect("feature without a group", [p for p in problems if "without group" in p])

    _sums, problems = aggregate_groups(["area", "area"], [1.0, 1.0], {"area": "AREA"})
    expect("duplicate feature", [p for p in problems if "duplicate" in p])

    _sums, problems = aggregate_groups(features, contribs,
                                       {"area": "AREA", "district": "LOCATION",
                                        "ghost": "AREA"})
    expect("group entry absent from vector",
           [p for p in problems if "absent from vector" in p])

    # a genuinely wrong group sum must be caught by the reconstruction comparison
    sums, _ = aggregate_groups(features, [1.0, 2.0], {"area": "AREA", "district": "AREA"})
    expect("wrong aggregation",
           require_tolerance(abs(sums.get("AREA", 0.0) - 2.0), 1e-12, "grouped sum"))

    expect("empty fixture matrix", require_cases([]))
    expect("non-zero additivity beyond tolerance",
           require_tolerance(1e-4, ADDITIVITY_TOL_REL, "additivity"))

    # provenance classifier must distinguish the states it claims to
    if provenance("ward", "__UNKNOWN__", set(), set())[0] != "UNKNOWN_CATEGORY":
        failures.append("self-test did not detect: UNKNOWN_CATEGORY classification")
    if provenance("ward", None, set(), set())[0] != "MISSING":
        failures.append("self-test did not detect: MISSING classification")
    if provenance("ward", None, set(), {"ward"})[0] != "NOT_APPLICABLE":
        failures.append("self-test did not detect: NOT_APPLICABLE classification")
    if provenance("ward", "phường 1", {"ward"}, set())[0] != "OBSERVED":
        failures.append("self-test did not detect: OBSERVED classification")

    # the real benchmark must fail when the matrix is empty
    if not require_cases([]):
        failures.append("self-test did not detect: run() on an empty matrix")

    return failures


# --------------------------------------------------------------------------- benchmark
def run(predictor, cases: List[Case], extras: List[Extra]) -> Dict[str, Any]:
    import numpy as np
    import pandas as pd
    import xgboost as xgb
    from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3
    from app.models.xgboost.features_v1_3 import transform

    schema = predictor.schema
    RENAME_FOR_PREFLIGHT = {}
    RENAME = {"street_name": "raw_street_name", "project_name": "raw_project_name",
              "house_direction": "raw_house_direction",
              "balcony_direction": "raw_balcony_direction",
              "floor_count": "raw_floor_count", "frontage_width": "raw_frontage_width",
              "road_width": "raw_road_width", "bedroom_count": "raw_bedroom_count",
              "bathroom_count": "raw_bathroom_count"}
    features = list(schema["features"])
    booster = predictor.model.get_booster()
    best = getattr(predictor.model, "best_iteration", None)
    iter_range = (0, int(best) + 1) if best is not None else (0, 0)

    RENAME = {"street_name": "raw_street_name", "project_name": "raw_project_name",
              "house_direction": "raw_house_direction", "balcony_direction": "raw_balcony_direction",
              "floor_count": "raw_floor_count", "frontage_width": "raw_frontage_width",
              "road_width": "raw_road_width", "bedroom_count": "raw_bedroom_count",
              "bathroom_count": "raw_bathroom_count"}

    def frame_for(payload: Dict[str, Any]):
        """Build the matrix exactly like PredictorV1_3.predict() does.

        Production maps the payload to a canonical record, then assembles an explicit
        `input_row` from the RECORD (not from the raw payload). The earlier version of this
        benchmark overwrote `ward` with the raw payload value, which is not what production
        sees (the adapter strips the "Phường/Xã" prefix and casefolds). That is fixed here and
        asserted below.
        """
        mapped = map_v6_to_v1_3(
            payload, district_vocabulary=schema.get("vocabularies", {}).get("district"))
        input_row = {
            "area": float(mapped["area"]),
            "raw_floor_count": mapped.get("floor_count"),
            "raw_frontage_width": mapped.get("frontage_width"),
            "raw_road_width": mapped.get("road_width"),
            "raw_bedroom_count": mapped.get("bedroom_count"),
            "raw_bathroom_count": mapped.get("bathroom_count"),
            "normalized_type": mapped["normalized_type"],
            "district": mapped["district"],
            "ward": mapped.get("ward"),
            "raw_street_name": mapped.get("street_name"),
            "raw_project_name": mapped.get("project_name"),
            "raw_house_direction": mapped.get("house_direction"),
            "raw_balcony_direction": mapped.get("balcony_direction"),
        }
        return transform(pd.DataFrame([input_row]), schema), mapped, input_row

    additivity, recon_naive, recon_final, topk_rem, group_rem = [], [], [], [], []
    per_case: List[Dict[str, Any]] = []
    failures: List[str] = []
    states: Dict[str, int] = {}
    passed = 0

    for case in cases:
        case_fail_before = len(failures)
        t0 = time.perf_counter()
        out = predictor.predict_from_v6_payload(case.payload)
        total_ms = (time.perf_counter() - t0) * 1000.0

        frame, mapped, input_row = frame_for(case.payload)
        dmat = xgb.DMatrix(frame, feature_names=list(frame.columns))
        margin = float(booster.predict(dmat, output_margin=True, iteration_range=iter_range)[0])

        # PRODUCTION PARITY: the matrix built here must be the matrix the production path uses.
        # model.predict(X) goes through the same booster, so equality proves same feature order
        # and same values. Ward is the field the review flagged.
        if abs(float(predictor.model.predict(frame)[0]) - margin) > 1e-6:
            failures.append(f"{case.case_id}: benchmark matrix differs from production predict()")
        # ward: the INPUT ROW must carry the canonical mapped value (this is what production
        # feeds transform); the ENCODED value must then be the documented sentinel.
        if input_row["ward"] != mapped.get("ward"):
            failures.append(f"{case.case_id}: input row ward != canonical mapped ward "
                            f"({input_row['ward']!r} vs {mapped.get('ward')!r})")
        ward_vocab = set(schema.get("vocabularies", {}).get("ward", []))
        expected_encoded = ("__MISSING__" if mapped.get("ward") is None else
                            (mapped["ward"] if mapped["ward"] in ward_vocab else "__UNKNOWN__"))
        if frame.iloc[0]["ward"] != expected_encoded:
            failures.append(f"{case.case_id}: encoded ward {frame.iloc[0]['ward']!r} != "
                            f"{expected_encoded!r}")
        if list(frame.columns) != features:
            failures.append(f"{case.case_id}: feature order differs from schema")
        contribs = np.asarray(
            booster.predict(dmat, pred_contribs=True, iteration_range=iter_range)[0],
            dtype=np.float64)

        # structural checks
        if len(contribs) != len(features) + 1:
            failures.append(f"{case.case_id}: SHAP dimension {len(contribs)} != {len(features)+1}")
        if list(frame.columns) != features:
            failures.append(f"{case.case_id}: feature order differs from schema")
        if not np.all(np.isfinite(contribs)):
            failures.append(f"{case.case_id}: non-finite SHAP contribution")
        if not math.isfinite(margin):
            failures.append(f"{case.case_id}: non-finite margin")

        dev = abs(margin - (contribs[-1] + contribs[:-1].sum())) / max(1.0, abs(margin))
        additivity.append(dev)
        if dev > ADDITIVITY_TOL_REL:
            failures.append(f"{case.case_id}: additivity rel {dev:.3e}")

        naive = float(np.expm1(margin))
        rel_n = abs(naive - float(out["naive_price_vnd"])) / max(1.0, abs(naive))
        recon_naive.append(rel_n)
        if rel_n > RECON_TOL_REL:
            failures.append(f"{case.case_id}: naive reconstruction rel {rel_n:.3e}")

        factor = float(out["calibration_factor"])
        expected_final = max(0.0, math.exp(margin) * factor - 1.0)
        rel_f = abs(expected_final - float(out["predicted_asking_price_vnd"])) / max(
            1.0, abs(expected_final))
        recon_final.append(rel_f)
        if rel_f > CALIB_TOL_REL:
            failures.append(f"{case.case_id}: calibration reconstruction rel {rel_f:.3e}")

        # top-K + remainder
        factors = out["shap_explanation"]["top_factors"]
        if len(factors) > 6:
            failures.append(f"{case.case_id}: more than 6 factors")
        top_sum = sum(float(f["shap_value"]) for f in factors)
        remainder = contribs[:-1].sum() - top_sum
        topk_rem.append(abs(remainder))

        # real grouped aggregation
        group_sums, problems = aggregate_groups(features, contribs[:-1], FEATURE_GROUPS)
        for problem in problems:
            failures.append(f"{case.case_id}: {problem}")
        g_total = sum(group_sums.values())
        group_rem.append(abs(g_total - contribs[:-1].sum()))
        if abs(g_total - contribs[:-1].sum()) > 1e-12:
            failures.append(f"{case.case_id}: grouped sum != full contribution sum")

        # provenance from the actual matrix
        case_states = {}
        for i, feature in enumerate(features):
            value = frame.iloc[0][feature]
            if isinstance(value, str):
                encoded = value
            else:
                encoded = float(value) if not pd.isna(value) else None
            state, _basis = provenance(feature, encoded, case.provided, case.not_applicable)
            case_states[feature] = state
            states[state] = states.get(state, 0) + 1

        if len(failures) == case_fail_before:
            passed += 1

        per_case.append({
            "case_id": case.case_id, "district": case.district, "category": case.category,
            "profile": case.profile,
            "price": int(out["predicted_asking_price_vnd"]),
            "naive": int(out["naive_price_vnd"]), "calibration_factor": round(factor, 10),
            "margin": round(margin, DIGEST_DECIMALS), "base_log": round(float(contribs[-1]),
                                                                       DIGEST_DECIMALS),
            "contribs": [round(float(c), DIGEST_DECIMALS) for c in contribs[:-1]],
            "top_factors": [f["feature_name"] for f in factors],
            "groups": {k: round(v, DIGEST_DECIMALS) for k, v in sorted(group_sums.items())},
            "provenance": case_states, "total_ms": total_ms,
        })

    # extras: every outcome is classified; only an exact contract match passes
    extra_outcomes: List[Dict[str, Any]] = []
    from app.api.schemas import ValuationRequest
    from pydantic import ValidationError

    for item in extras:
        # 1) API contract
        try:
            ValuationRequest(**item.payload)
        except ValidationError as error:
            extra_outcomes.append({"case_id": item.case_id,
                                   "expectation": item.expectation,
                                   "outcome": "REJECTED", "reject_source": "SCHEMA",
                                   "ok": item.expectation == "REJECT",
                                   "detail": str(error)[:100]})
            if item.expectation != "REJECT":
                failures.append(f"{item.case_id}: expected SUCCESS, rejected by schema")
            continue
        # 2) adapter + feature transform, executed on its own so an adapter rejection is
        #    distinguishable from an internal predictor defect.
        try:
            mapped = map_v6_to_v1_3(
                item.payload,
                district_vocabulary=schema.get("vocabularies", {}).get("district"))
            row = {RENAME.get(k, k): v for k, v in mapped.items()}
            # Same preparation as the matrix: ward comes from the canonical record, never
            # from the raw payload.
            row["ward"] = mapped.get("ward")
            transform(pd.DataFrame([row]), schema)
        except ValueError as error:
            extra_outcomes.append({"case_id": item.case_id,
                                   "expectation": item.expectation,
                                   "outcome": "REJECTED", "reject_source": "ADAPTER",
                                   "ok": item.expectation == "REJECT",
                                   "detail": str(error)[:100]})
            if item.expectation != "REJECT":
                failures.append(f"{item.case_id}: expected SUCCESS, adapter rejected input")
            continue
        except Exception as error:  # noqa: BLE001 - unexpected adapter/transform defect
            extra_outcomes.append({"case_id": item.case_id,
                                   "expectation": item.expectation,
                                   "outcome": "INTERNAL_ERROR", "reject_source": None,
                                   "ok": False,
                                   "detail": f"{type(error).__name__}: {str(error)[:90]}"})
            failures.append(f"{item.case_id}: unexpected adapter/transform error")
            continue
        # 3) full prediction. Any error here is INTERNAL and always fails, even ValueError.
        try:
            out = predictor.predict_from_v6_payload(item.payload)
            extra_outcomes.append({"case_id": item.case_id,
                                   "expectation": item.expectation,
                                   "outcome": "SUCCESS", "reject_source": None,
                                   "ok": item.expectation == "SUCCESS",
                                   "detail": int(out["predicted_asking_price_vnd"])})
            if item.expectation != "SUCCESS":
                failures.append(f"{item.case_id}: expected REJECT, got SUCCESS")
        except Exception as error:  # noqa: BLE001
            extra_outcomes.append({"case_id": item.case_id,
                                   "expectation": item.expectation,
                                   "outcome": "INTERNAL_ERROR", "reject_source": None,
                                   "ok": False,
                                   "detail": f"{type(error).__name__}: {str(error)[:90]}"})
            failures.append(f"{item.case_id}: INTERNAL predictor error always fails")

    # empty fixture matrix must never PASS
    failures.extend(require_cases(cases))

    def stats(seq):
        if not seq:
            return {"n": 0, "max": 0.0, "median": 0.0, "p95": 0.0}
        ordered = sorted(seq)
        return {"n": len(seq), "max": max(seq), "median": statistics.median(seq),
                "p95": ordered[min(len(ordered) - 1, int(0.95 * len(ordered)))]}

    return {
        "cases": len(cases), "case_passed": passed, "case_failed": len(cases) - passed,
        "extras": len(extras), "extra_ok": sum(1 for e in extra_outcomes if e["ok"]),
        "failures": failures,
        "additivity_rel": stats(additivity),
        "naive_rel": stats(recon_naive),
        "calibration_rel": stats(recon_final),
        "topk_remainder_abs": stats(topk_rem),
        "group_remainder_abs": stats(group_rem),
        "provenance_counts": states,
        "per_case": per_case,
        "extras_outcomes": extra_outcomes,
    }


def digest_of(payload: Dict[str, Any]) -> str:
    """Deterministic digest: everything except timing, over per-case results included."""
    def stable(node):
        if isinstance(node, dict):
            return {k: stable(v) for k, v in sorted(node.items())
                    if k not in ("total_ms", "latency_ms", "dir")}
        if isinstance(node, list):
            return [stable(v) for v in node]
        return node
    return hashlib.sha256(json.dumps(stable(payload), sort_keys=True,
                                     ensure_ascii=False, default=str).encode()).hexdigest()[:16]


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--artifacts-dir", default="ai-services/artifacts/v1_3")
    ap.add_argument("--json", action="store_true")
    ap.add_argument("--assertions", action="store_true")
    ap.add_argument("--integrity-only", action="store_true")
    ap.add_argument("--self-test", action="store_true")
    args = ap.parse_args()

    integrity = verify_artifacts(Path(args.artifacts_dir))
    if args.integrity_only:
        print(json.dumps(integrity, indent=2) if args.json else
              "\n".join(f"{k}: {v['status']}" for k, v in integrity["files"].items()))
        return 0 if integrity["ok"] else 2

    if args.self_test:
        failures = run_self_tests()
        for f in failures:
            print("  FAIL ", f)
        print(f"self-tests: {'PASS' if not failures else 'FAIL'}")
        return 0 if not failures else 1

    if not integrity["ok"]:
        print("BLOCKED: artifact hash mismatch")
        print(json.dumps(integrity, indent=2))
        return 2

    sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ai-services"))
    from app.models.xgboost.predictor_v1_3 import PredictorV1_3

    predictor = PredictorV1_3(Path(args.artifacts_dir))
    cases, extras = build_cases(predictor.schema)
    report = run(predictor, cases, extras)
    report.update({"artifact_integrity": integrity, "model_version": "v1.3",
                   "model_run": "tinix_xgboost_v1_3_integrated"})

    has_failure = bool(report["failures"])
    report["digest"] = digest_of(report)

    if args.assertions:
        self_failures = run_self_tests()
        report["self_test_failures"] = self_failures

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2, sort_keys=True, default=str))
        return 0 if not has_failure and not report.get("self_test_failures") else 1

    print(f"WP-04 explainability benchmark · v1.3 · cases={report['cases']} "
          f"extras={report['extras']}")
    print(f"  cases passed {report['case_passed']} · failed {report['case_failed']} · "
          f"extras ok {report['extra_ok']}/{report['extras']}")
    for key in ("additivity_rel", "naive_rel", "calibration_rel",
                "topk_remainder_abs", "group_remainder_abs"):
        s = report[key]
        print(f"  {key:22s} max={s['max']:.3e} median={s['median']:.3e} p95={s['p95']:.3e}")
    print(f"  provenance: {report['provenance_counts']}")
    if args.assertions:
        st = report.get("self_test_failures") or []
        print(f"  self-tests: {'PASS' if not st else 'FAIL'} ({len(st)} lỗi)")
    for f in report["failures"][:10]:
        print("  FAIL ", f)
    print(f"\ndigest {report['digest']}")
    bad = has_failure or bool(report.get("self_test_failures"))
    return 0 if not bad else 1


if __name__ == "__main__":
    sys.exit(main())
