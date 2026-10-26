"""Load pinned artifacts once; reuse the original frozen extractor and encoder."""
import hashlib
import importlib
import json
import math
import os
import re
import sys
from pathlib import Path

import numpy as np
import xgboost as xgb

from app.core.model_registry import DATA_DIR, V6_MANIFEST_SHA256, V6_MODEL_DIR, V6_RUN
from app.core.location_catalog import CATALOG, LOCATION_LABELS


class ModelArtifactError(RuntimeError):
    """A model/code artifact is missing or differs from the approved release."""


def _sha(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _checked_path(root, relative, expected):
    path = (root / relative).resolve()
    if not path.is_relative_to(root.resolve()) or not path.is_file() or _sha(path) != expected:
        raise ModelArtifactError(f"Artifact thiếu hoặc sai SHA-256: {relative}")
    return path


def _load_frozen_code(manifest):
    for name in ["training_v3_common.py", "property_text_features_v6.py"]:
        _checked_path(DATA_DIR, name, manifest["input_sha256"][name])
    # Archived training scripts use absolute sibling imports. Load them from
    # their trusted directory at startup without editing the frozen sources.
    path = str(DATA_DIR)
    inserted = path not in sys.path
    if inserted:
        sys.path.insert(0, path)
    try:
        common = importlib.import_module("training_v3_common")
        extractor = importlib.import_module("property_text_features_v6")
    finally:
        if inserted:
            sys.path.remove(path)
    for module in [common, extractor]:
        if Path(module.__file__).resolve() != (DATA_DIR / (module.__name__ + ".py")).resolve():
            raise ModelArtifactError("Module đặc trưng được nạp từ đường dẫn không đúng.")
    return common, extractor


class PredictorV6:
    def __init__(self, model_dir=None):
        self.model_dir = Path(model_dir or os.environ.get("SMARTPROP_V6_MODEL_DIR") or V6_MODEL_DIR).resolve()
        manifest_path = _checked_path(self.model_dir, "manifest.json", V6_MANIFEST_SHA256)
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        self.common, self.extractor = _load_frozen_code(manifest)
        selection_path = _checked_path(self.model_dir, "selection.json", manifest["output_sha256"]["selection.json"])
        selection = json.loads(selection_path.read_text(encoding="utf-8"))
        if selection["best_global_arm"] != "all":
            raise ModelArtifactError("API này chỉ dùng bản v6/all đã chốt.")
        self.specs, self.models = {}, {}
        for category, info in selection["category_artifacts"].items():
            spec_path = _checked_path(self.model_dir, info["schema_file"], manifest["output_sha256"][info["schema_file"]])
            model_path = _checked_path(self.model_dir, info["model_file"], manifest["output_sha256"][info["model_file"]])
            spec = json.loads(spec_path.read_text(encoding="utf-8"))
            if spec["category"] != category or spec["arm"] != "all":
                raise ModelArtifactError("Schema không khớp loại/model.")
            booster = xgb.Booster()
            booster.load_model(model_path)
            booster.set_param({"nthread": 4, "device": "cpu"})
            if booster.feature_names != spec["feature_names"]:
                raise ModelArtifactError("Thứ tự cột không khớp model.")
            self.specs[category], self.models[category] = spec, booster

    def options(self):
        categories = [
            {"category": category, "locations": [code for code in spec["base_schema"]["locations"] if code in LOCATION_LABELS]}
            for category, spec in self.specs.items()
        ]
        supported = {code for category in categories for code in category["locations"]}
        return {
            "model_version": "v6", "model_run": V6_RUN,
            "categories": categories,
            "location_labels": {code: label for code, label in LOCATION_LABELS.items() if code in supported},
            "location_catalog_version": CATALOG["version"],
            "access_types": {"alley": "Trong kiệt/hẻm", "frontage": "Mặt tiền"},
            "house_subtypes": {"villa": "Biệt thự", "house_c4": "Nhà cấp 4"},
        }

    def predict(self, values):
        category = values["category"]
        if category not in self.specs:
            raise ValueError("Loại bất động sản không được hỗ trợ.")
        spec = self.specs[category]
        location = values["location_feature"]
        if location not in spec["base_schema"]["locations"] or location not in LOCATION_LABELS:
            raise ValueError("Địa bàn không được hỗ trợ. Vui lòng chọn lại trong danh sách của loại bất động sản này.")
        area = values["area_sqm"]
        if isinstance(area, bool) or not math.isfinite(float(area)) or not 20 <= float(area) <= 1000:
            raise ValueError("Diện tích phải trong phạm vi 20–1.000 m² của API v6.")
        ward = re.sub(r"^(phuong|xa|thi tran)\s+", "", self.common.normalized(values.get("ward")))
        if ward in {"khong xac dinh", "dang cap nhat"}:
            ward = ""
        row = dict(record_key="api:input", source="user_input", category=category,
                   rooms=str(values["rooms"]) if values.get("rooms") is not None else "",
                   area_sqm=str(area), location_feature=location, ward_source=ward)
        origin = dict(title=values.get("title") or "", raw_json='{"source_category":""}')
        feature, _ = self.extractor.extract(row, origin, values.get("description") or "")
        warnings = []
        conflicts = set(filter(None, feature["conflict_fields"].split(";")))
        for field, request_field in [("floors_claim", "floors"), ("access_claim", "access_type"), ("house_subtype_claim", "house_subtype")]:
            declared = values.get(request_field)
            if declared is not None:
                inferred = feature[field]
                if field in conflicts or (inferred != "" and inferred != declared):
                    feature[field] = ""
                    warnings.append(f"{request_field}: thông tin khai báo và nội dung mâu thuẫn; giữ thiếu.")
                else:
                    feature[field] = declared
        if conflicts:
            warnings.append("Có lời mô tả mâu thuẫn. Số phòng có cấu trúc được giữ; các suy luận mâu thuẫn khác để thiếu.")
        if feature["extraction_notes"]:
            warnings.append("Một số câu gần đó, dự kiến xây hoặc nhiều tài sản không được dùng để tự điền đặc trưng.")
        if ward and location + "|" + ward not in spec["base_schema"]["wards"]:
            warnings.append("Phường/xã chưa đủ mẫu hoặc chưa có trong vocabulary; model dùng trạng thái chưa biết/ít mẫu.")
        matrix = self.extractor.encode([row], {row["record_key"]: feature}, spec)
        if np.isinf(matrix).any():
            raise ValueError("Đầu vào chứa giá trị không hợp lệ.")
        predicted_log = self.models[category].predict(xgb.DMatrix(
            matrix, feature_names=spec["feature_names"], nthread=4))
        million = float(np.exp(np.clip(predicted_log, -20, 30))[0])
        if not math.isfinite(million) or million <= 0:
            raise RuntimeError("Model trả kết quả không hợp lệ.")
        used = dict(area_sqm=float(area), location_feature=location, ward_source=ward or None,
                    rooms=int(feature["rooms_completed"]) if str(feature["rooms_completed"]) else None,
                    floors=float(feature["floors_claim"]) if str(feature["floors_claim"]) else None,
                    access_type=feature["access_claim"] or None, house_subtype=feature["house_subtype_claim"] or None)
        applicable = ["ward_source"]
        if category != "Đất nền": applicable.append("rooms")
        if category == "Nhà ở": applicable += ["floors", "access_type", "house_subtype"]
        if category == "Đất nền": applicable.append("access_type")
        return dict(model_version="v6", model_run=V6_RUN, configuration="all", category=category,
                    predicted_asking_price_vnd=round(million * 1_000_000), predicted_asking_price_million=million,
                    currency="VND", price_basis="Giá rao ước tính từ dữ liệu tin đăng.", features_used=used,
                    missing_features=[field for field in applicable if used[field] is None], warnings=warnings)
