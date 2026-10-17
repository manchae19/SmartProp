"""Copy the pinned release and create a label-free API parity fixture."""
import csv
import hashlib
import json
import sys
from pathlib import Path

SERVICE_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(SERVICE_DIR))
from app.core.model_registry import DATA_DIR, V6_MANIFEST_SHA256, V6_MODEL_DIR, V6_RUN

MODEL_SOURCE = DATA_DIR / "processed" / "models_v6_ablation" / "runs" / V6_RUN
FEATURE_SOURCE = DATA_DIR / "processed/property_features_v6/runs/6c9b866cdd95c66d"
FIXTURE_PATH = SERVICE_DIR / "tests/fixtures/v6_validation_parity.json"


def sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def read_csv(path):
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream))


def write_once(path, payload):
    if path.exists():
        if path.read_bytes() != payload:
            raise ValueError(f"Từ chối ghi đè file khác nội dung: {path}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(payload)


def main():
    manifest_path = MODEL_SOURCE / "manifest.json"
    if sha(manifest_path) != V6_MANIFEST_SHA256:
        raise ValueError("Manifest nguồn không phải bản v6 đã chốt.")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    for name in ("training_v3_common.py", "property_text_features_v6.py"):
        if sha(DATA_DIR / name) != manifest["input_sha256"][name]:
            raise ValueError(f"Mã đặc trưng khác bản đã chốt: {name}")
    selection_path = MODEL_SOURCE / "selection.json"
    if sha(selection_path) != manifest["output_sha256"]["selection.json"]:
        raise ValueError("Selection nguồn không đúng hash.")
    selection = json.loads(selection_path.read_text(encoding="utf-8"))
    names = ["manifest.json", "selection.json", "metrics.json"]
    for info in selection["category_artifacts"].values():
        names.extend([info["model_file"], info["schema_file"]])
    payloads = {}
    for name in names:
        source = (MODEL_SOURCE / name).resolve()
        if not source.is_relative_to(MODEL_SOURCE.resolve()):
            raise ValueError("Đường dẫn artifact không nằm trong run nguồn.")
        expected = V6_MANIFEST_SHA256 if name == "manifest.json" else manifest["output_sha256"][name]
        if sha(source) != expected:
            raise ValueError(f"Artifact nguồn sai hash: {name}")
        payloads[name] = source.read_bytes()

    source_paths = {
        "validation": FEATURE_SOURCE / "validation.csv",
        "features": FEATURE_SOURCE / "features.csv",
        "predictions": MODEL_SOURCE / "validation_predictions.csv",
    }
    features = {row["record_key"]: row for row in read_csv(source_paths["features"])}
    predictions = {row["record_key"]: float(row["predicted_million"])
                   for row in read_csv(source_paths["predictions"]) if row["arm"] == "all"}
    validation = read_csv(source_paths["validation"])
    if len(validation) != 299 or {row["record_key"] for row in validation} != set(predictions):
        raise ValueError("Không đúng cohort 299 validation đã đánh giá.")
    if sha(source_paths["predictions"]) != manifest["output_sha256"]["validation_predictions.csv"]:
        raise ValueError("Dự đoán nguồn sai hash.")
    # The model manifest anchors the complete feature run's input hashes.
    for name in ("validation", "features"):
        relative = source_paths[name].relative_to(DATA_DIR).as_posix()
        if sha(source_paths[name]) != manifest["input_sha256"][relative]:
            raise ValueError(f"Đầu vào fixture khác bản model: {name}")
    cases = []
    for index, row in enumerate(validation, 1):
        feature = features[row["record_key"]]
        request = dict(category=row["category"], area_sqm=float(row["area_sqm"]),
                       location_feature=row["location_feature"], ward=row["ward_source"] or None)
        if row["category"] != "Đất nền":
            request["rooms"] = int(feature["rooms_completed"]) if feature["rooms_completed"] else None
        if row["category"] == "Nhà ở":
            request["floors"] = float(feature["floors_claim"]) if feature["floors_claim"] else None
            request["house_subtype"] = feature["house_subtype_claim"] or None
        if row["category"] != "Căn hộ chung cư":
            request["access_type"] = feature["access_claim"] or None
        cases.append(dict(case=index, request=request,
                          expected_asking_price_million=predictions[row["record_key"]]))
    fixture = dict(model_run=V6_RUN, model_manifest_sha256=V6_MANIFEST_SHA256,
                   purpose="Replay already exposed validation; no new model evaluation.",
                   source_sha256={key: sha(path) for key, path in source_paths.items()}, cases=cases)
    fixture_bytes = (json.dumps(fixture, ensure_ascii=False, indent=2, allow_nan=False) + "\n").encode("utf-8")
    # Validate every source before writing anything. Preserve all archive files.
    for name, payload in payloads.items():
        write_once(V6_MODEL_DIR / name, payload)
    write_once(FIXTURE_PATH, fixture_bytes)
    print(json.dumps(dict(model_run=V6_RUN, artifacts=len(payloads),
                          artifact_bytes=sum(map(len, payloads.values())), parity_cases=len(cases),
                          fixture_bytes=len(fixture_bytes), archive_unchanged=True), ensure_ascii=False))


if __name__ == "__main__":
    main()
