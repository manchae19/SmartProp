"""Prepare a new reviewed-location cohort; preserve frozen v6 and all holdouts."""
import csv
import hashlib
import json
import shutil
from collections import Counter
from pathlib import Path

BASE = Path(__file__).resolve().parent
SOURCE = BASE / "processed/property_features_v6/runs/6c9b866cdd95c66d"
GEO = BASE / "processed/geospatial_v1/audit_runs/0f2be923900adb3e"
CATALOG = BASE.parent / "core/location_catalog_v6.json"
ROOT = BASE / "processed/training_next_preparation"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write(path, rows, fields):
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def partition(train, validation, allowed):
    for rows in (train, validation):
        if len({row["record_key"] for row in rows}) != len(rows):
            raise ValueError("Duplicate record_key within a split")
    if {row["record_key"] for row in train} & {row["record_key"] for row in validation}:
        raise ValueError("ID leakage between train and validation")
    if {row["pipeline_group"] for row in train} & {row["pipeline_group"] for row in validation}:
        raise ValueError("Group leakage between train and validation")
    # Keep the development validation cohort fixed, rather than silently improve
    # an apparent score by dropping validation cases.
    if any(row["location_feature"] not in allowed for row in validation):
        raise ValueError("Validation has an unreviewed location; a new evaluation protocol is required")
    kept, quarantined = [], []
    for row in train:
        if row["location_feature"] in allowed:
            kept.append(row.copy())
        else:
            quarantined.append(dict(row, quarantine_reason="unreviewed_or_invalid_location_code"))
    return kept, quarantined


def verify_outputs(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    for name, expected in manifest["output_sha256"].items():
        if sha(directory / name) != expected:
            raise ValueError("Prepared output changed: " + name)


def main():
    catalog = json.loads(CATALOG.read_text(encoding="utf-8"))
    allowed = set(catalog["legacy"]) | set(catalog["expanded"])
    if allowed & set(catalog["blocked"]):
        raise ValueError("Blocked location in reviewed catalog")
    for directory in (SOURCE, GEO):
        manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
        for name, expected in manifest["output_sha256"].items():
            if sha(directory / name) != expected:
                raise ValueError("Frozen source changed: " + str(directory / name))
    review = BASE / "processed/geospatial_v1/coordinate_review.csv"
    model = BASE.parents[1] / "artifacts/v6"
    protected = [SOURCE / name for name in ("manifest.json", "train.csv", "validation.csv", "features.csv", "reserved_holdout_registry.csv")]
    protected += [GEO / "manifest.json", GEO / "location_audit.csv", review, CATALOG, Path(__file__),
                  BASE / "training_v3_common.py", BASE / "property_text_features_v6.py"]
    protected += sorted(model.rglob("*.json"))
    inputs = {str(path.relative_to(BASE.parents[2])): sha(path) for path in protected}
    run_id = hashlib.sha256(json.dumps(inputs, sort_keys=True).encode()).hexdigest()[:16]
    output = ROOT / "runs" / run_id
    if output.exists():
        verify_outputs(output)
        print(output)
        return
    train, validation = read(SOURCE / "train.csv"), read(SOURCE / "validation.csv")
    kept, quarantined = partition(train, validation, allowed)
    audits = {row["record_key"]: row for row in read(GEO / "location_audit.csv")}
    approvals = {row["record_key"]: row for row in read(review)}
    readiness = []
    for row in kept + validation:
        audit, approval = audits.get(row["record_key"], {}), approvals.get(row["record_key"], {})
        readiness.append(dict(record_key=row["record_key"], model_split=row["model_split"],
            has_street_hint=bool(audit.get("street_raw", "").strip()),
            has_source_coordinates=bool(audit.get("latitude") and audit.get("longitude")),
            review_claimed_approved=approval.get("location_verified") == "True" and approval.get("reuse_for_ml_verified") == "True",
            spatial_features_ready=False, reason="requires_verified_property_evidence_and_verified_poi_feature_run"))
    summary = dict(source_train=len(train), prepared_train=len(kept), validation=len(validation),
        quarantined=len(quarantined), quarantine_by_reason=dict(Counter(row["quarantine_reason"] for row in quarantined)),
        by_category=dict(Counter(row["category"] for row in kept)),
        readiness={split: {field: sum(row[field] for row in readiness if row["model_split"] == split)
            for field in ("has_street_hint", "has_source_coordinates", "review_claimed_approved", "spatial_features_ready")}
            for split in sorted({row["model_split"] for row in readiness})},
        model_trained=False, deployed_model_changed=False,
        note="Metadata readiness only. No geocoding, coordinate approval, POI download, distance feature or evaluation performed.")
    output.mkdir(parents=True)
    write(output / "train.csv", kept, list(train[0]))
    write(output / "quarantined_DO_NOT_TRAIN.csv", quarantined, list(train[0]) + ["quarantine_reason"])
    shutil.copyfile(SOURCE / "validation.csv", output / "validation.csv")
    shutil.copyfile(SOURCE / "reserved_holdout_registry.csv", output / "reserved_holdout_registry.csv")
    keys = {row["record_key"] for row in kept + validation}
    features = [row for row in read(SOURCE / "features.csv") if row["record_key"] in keys]
    if len(features) != len(keys) or {row["record_key"] for row in features} != keys:
        raise ValueError("Feature rows do not match prepared cohort")
    write(output / "features.csv", features, list(features[0]))
    write(output / "spatial_readiness_DO_NOT_TRAIN.csv", readiness, list(readiness[0]))
    (output / "summary.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    (output / "README.md").write_text(
        f"# Bản chuẩn bị huấn luyện tiếp theo\n\nTrain: {len(kept)}; validation phát triển giữ nguyên: {len(validation)}; cách ly: {len(quarantined)}.\n\n"
        "Chỉ kiểm tra địa bàn theo catalog đã duyệt. Giá, diện tích, nhóm và split của tin được giữ nguyên; validation và registry dự phòng sao chép nguyên byte. "
        "features.csv là đặc trưng lời rao v6 của đúng cohort mới. Chưa train model mới, chưa fit encoder hay chấm lại pilot. "
        "Các file DO_NOT_TRAIN không được nối vào X. Chưa có vị trí tài sản được xác minh và snapshot POI đã kiểm chứng để tạo khoảng cách.\n",
        encoding="utf-8")
    for path in protected:
        if sha(path) != inputs[str(path.relative_to(BASE.parents[2]))]:
            raise ValueError("Source changed during preparation")
    outputs = {path.name: sha(path) for path in output.iterdir()}
    (output / "manifest.json").write_text(json.dumps(dict(input_sha256=inputs, output_sha256=outputs), indent=2) + "\n", encoding="utf-8")
    verify_outputs(output)
    (ROOT / "latest.json").write_text(json.dumps(dict(run=f"runs/{run_id}")) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(output)


if __name__ == "__main__":
    main()
