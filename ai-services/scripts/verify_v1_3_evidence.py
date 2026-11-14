#!/usr/bin/env python3
"""Verify the local V1.3 dev-test evidence without embedding row data or creating metrics.

Expected evidence directory (local/ignored):
  ai-services/artifacts/v1_3/evidence/
    evaluation.json
    test_predictions_dev.csv
    train_v1_3_integrated.csv   (optional for this check; hash still verified if present)

The script verifies SHA-256, recomputes MAE/RMSE/MAPE/median/P90/within-20/R²/bias
from actual_vnd and pred_v1_3_vnd, and checks train/test entity overlap. It never
modifies files and never reads a blind-test set.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path

EXPECTED = {
    "evaluation.json": (27128, "0c4bc5bf15732e4479508bfc7ae9179cd5489120a768806b29876ac3507bf303"),
    "test_predictions_dev.csv": (1127094, "8e29fc0471635ff9e6326f23f68059790ccc965b8886f3e9fd3ab9fa21fb9c43"),
    "train_v1_3_integrated.csv": (7423218, "56e68164a1753816fa4a3834aa87229088b2c814ef4aaa625c9de3590601091d"),
}
REQUIRED = ("evaluation.json", "test_predictions_dev.csv")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(65536), b""):
            digest.update(chunk)
    return digest.hexdigest()


def compute(rows: list[dict[str, str]]) -> dict[str, float | int]:
    actual = [float(row["actual_vnd"]) for row in rows]
    predicted = [float(row["pred_v1_3_vnd"]) for row in rows]
    errors = [p - a for p, a in zip(predicted, actual)]
    absolute = [abs(error) for error in errors]
    ape = [abs(error) / max(1.0, a) * 100.0 for error, a in zip(errors, actual)]
    mean_actual = sum(actual) / len(actual)
    sse = sum(error * error for error in errors)
    sst = sum((value - mean_actual) ** 2 for value in actual)
    ordered = sorted(ape)

    def percentile(p: float) -> float:
        # Same linear interpolation as numpy.percentile (used by the evaluation artifact).
        position = (len(ordered) - 1) * p / 100.0
        lower = math.floor(position)
        upper = math.ceil(position)
        if lower == upper:
            return ordered[lower]
        weight = position - lower
        return ordered[lower] * (1.0 - weight) + ordered[upper] * weight

    return {
        "rows": len(rows),
        "mae_vnd": sum(absolute) / len(actual),
        "rmse_vnd": math.sqrt(sse / len(actual)),
        "mape_percent": sum(ape) / len(ape),
        "median_ape_percent": percentile(50),
        "p90_ape_percent": percentile(90),
        "within_20_percent": sum(value <= 20.0 for value in ape) / len(ape) * 100.0,
        "r2": 1.0 - sse / sst if sst else None,
        "mean_signed_bias_vnd": sum(errors) / len(errors),
        "under_predicted_percent": sum(p < a for p, a in zip(predicted, actual)) / len(actual) * 100.0,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--evidence-dir", type=Path, default=Path(__file__).resolve().parents[1] / "artifacts" / "v1_3" / "evidence")
    args = parser.parse_args()
    directory = args.evidence_dir.resolve()

    errors: list[str] = []
    print(f"evidence={directory}")
    for name in REQUIRED:
        path = directory / name
        if not path.is_file():
            errors.append(f"missing {name}")
            continue
        expected_size, expected_hash = EXPECTED[name]
        actual_hash = sha256(path)
        print(f"{name}: bytes={path.stat().st_size} sha256={actual_hash}")
        if path.stat().st_size != expected_size:
            errors.append(f"{name}: size mismatch")
        if actual_hash != expected_hash:
            errors.append(f"{name}: SHA-256 mismatch")
    train = directory / "train_v1_3_integrated.csv"
    if train.is_file():
        print(f"train_v1_3_integrated.csv: bytes={train.stat().st_size} sha256={sha256(train)}")
        if train.stat().st_size != EXPECTED["train_v1_3_integrated.csv"][0] or sha256(train) != EXPECTED["train_v1_3_integrated.csv"][1]:
            errors.append("train_v1_3_integrated.csv: size/SHA-256 mismatch")
    else:
        print("train_v1_3_integrated.csv: not present (optional; entity overlap skipped)")

    if (directory / "test_predictions_dev.csv").is_file():
        with (directory / "test_predictions_dev.csv").open(newline="", encoding="utf-8-sig") as handle:
            test_rows = list(csv.DictReader(handle))
        metrics = compute(test_rows)
        print(json.dumps(metrics, ensure_ascii=False, indent=2))
        if metrics["rows"] != 4403:
            errors.append("test rows != 4403")
        expected_metrics = {"mae_vnd": 3765301650.6103134, "mape_percent": 19.81549025877262,
                            "median_ape_percent": 15.023037099207773, "within_20_percent": 62.3665682489212,
                            "r2": 0.7326720223520334}
        for key, expected in expected_metrics.items():
            if abs(float(metrics[key]) - expected) > 1e-6:
                errors.append(f"metric {key} mismatch")
        if train.is_file():
            with train.open(newline="", encoding="utf-8-sig") as handle:
                train_rows = list(csv.DictReader(handle))
            train_entities = {row["entity"] for row in train_rows}
            test_entities = {row["entity"] for row in test_rows}
            overlap = train_entities & test_entities
            print(f"entities: train={len(train_entities)} test={len(test_entities)} overlap={len(overlap)}")
            if overlap:
                errors.append("train/test entity overlap is not zero")
    if errors:
        print("VERIFY_RESULT=FAIL")
        for error in errors:
            print(" -", error)
        return 1
    print("VERIFY_RESULT=PASS")
    print("blind_test=NOT_READ (sealed; not part of this evidence)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
