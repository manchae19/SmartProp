"""Predictor implementation for XGBoost V1.3 Multi-Source Standalone.

Loads pinned artifacts into memory once at service startup. Executes warm in-memory
inference in < 3 ms on CPU (n_jobs <= 4) with price-band Duan Smearing calibration.
"""
import hashlib
import json
import math
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import xgboost as xgb

from app.models.xgboost.adapter_v1_3 import map_v6_to_v1_3, real_feature_input_enabled
from app.models.xgboost.features_v1_3 import (
    ALL_FEATURES,
    LIMITS,
    clean_category,
    transform,
)

V1_3_MODEL_HASH = "3c56b6937902d9f736f9eb0278683f0c5ab8af027f5ea12b1a4072abff840a03"
V1_3_SCHEMA_HASH = "84be275b12b3c426497c00be80eed621d7323ac2a2abcb282752c7a89361e7ea"
V1_3_CALIBRATION_HASH = "17632bdf4d578723a5c336b7c7e3aed6021dbb68f38985b763839a763fbfe645"

DEFAULT_V1_3_DIR = Path(__file__).resolve().parents[3] / "artifacts" / "v1_3"

PRICE_BANDS_6: List[Tuple[float, float, str]] = [
    (0, 2e9, "<2B"),
    (2e9, 3e9, "2-3B"),
    (3e9, 5e9, "3-5B"),
    (5e9, 1e10, "5-10B"),
    (1e10, 2e10, "10-20B"),
    (2e10, float("inf"), ">20B"),
]


class ModelArtifactError(RuntimeError):
    """Raised when an artifact file is missing or fails cryptographic checksum validation."""


def _file_sha256(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as f:
        while chunk := f.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest().lower()


def band_of(v: float) -> str:
    """Classify numerical price into canonical 6-band scale."""
    val = float(v)
    for low, high, name in PRICE_BANDS_6:
        if low <= val < high:
            return name
    return ">20B"


class PredictorV1_3:
    """Production-ready warm in-memory predictor for XGBoost V1.3 Multi-Source."""

    def __init__(self, artifacts_dir: Optional[str | Path] = None):
        self.artifacts_dir = Path(
            artifacts_dir
            or os.environ.get("SMARTPROP_V1_3_MODEL_DIR")
            or DEFAULT_V1_3_DIR
        ).resolve()

        self._validate_and_load_artifacts()

    def _validate_and_load_artifacts(self) -> None:
        """Verify checksums and load weights + schemas into memory."""
        required = [
            ("model.json", V1_3_MODEL_HASH),
            ("feature_schema.json", V1_3_SCHEMA_HASH),
            ("calibration.json", V1_3_CALIBRATION_HASH),
        ]

        for fname, expected_hash in required:
            fpath = self.artifacts_dir / fname
            if not fpath.exists():
                raise ModelArtifactError(f"Missing required V1.3 artifact: {fpath}")
            actual_hash = _file_sha256(fpath)
            if actual_hash != expected_hash:
                raise ModelArtifactError(
                    f"Checksum mismatch for {fname}: got {actual_hash}, expected {expected_hash}"
                )

        # Load feature schema and calibration
        schema_path = self.artifacts_dir / "feature_schema.json"
        calib_path = self.artifacts_dir / "calibration.json"
        self.schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.calibration = json.loads(calib_path.read_text(encoding="utf-8"))

        # Load XGBoost booster in memory
        model_path = self.artifacts_dir / "model.json"
        self.model = xgb.XGBRegressor()
        self.model.load_model(model_path)
        self.model.set_params(n_jobs=4, device="cpu")

    def info(self) -> Dict[str, Any]:
        """Return operational metadata and configuration of V1.3."""
        return {
            "model_version": "v1.3",
            "model_run": "tinix_xgboost_v1_3_integrated",
            "algorithm": "XGBoost Regressor (hist)",
            "status": "READY",
            "calibration_policy": self.calibration.get("method", "duan_by_band"),
            "band_smearing_factors": self.calibration.get("band_smearing_factors", {}),
            "supported_districts": self.schema.get("vocabularies", {}).get("district", []),
            "supported_types": self.schema.get("vocabularies", {}).get("normalized_type", []),
            "target_bounds": LIMITS["area"],
            "real_feature_input_enabled": real_feature_input_enabled(),
        }

    def predict(self, record: Dict[str, Any]) -> Dict[str, Any]:
        """Execute in-memory prediction from canonical V1.3 record."""
        # 1. Mandatory fields
        for field in ["area", "normalized_type", "district"]:
            val = record.get(field)
            if val is None or str(val).strip() in ("", "None", "nan"):
                raise ValueError(f"Thiếu trường bắt buộc: {field}")

        # 2. Area validation
        try:
            area_val = float(record["area"])
        except (ValueError, TypeError):
            raise ValueError(f"Diện tích không hợp lệ: {record.get('area')}")

        if not (LIMITS["area"][0] <= area_val <= LIMITS["area"][1]):
            raise ValueError(
                f"Diện tích {area_val} m² nằm ngoài phạm vi cho phép ({LIMITS['area'][0]} - {LIMITS['area'][1]} m²)"
            )

        # 3. Assemble raw input frame
        input_row = {
            "area": area_val,
            "raw_floor_count": record.get("floor_count"),
            "raw_frontage_width": record.get("frontage_width"),
            "raw_road_width": record.get("road_width"),
            "raw_bedroom_count": record.get("bedroom_count"),
            "raw_bathroom_count": record.get("bathroom_count"),
            "normalized_type": record["normalized_type"],
            "district": record["district"],
            "ward": record.get("ward"),
            "raw_street_name": record.get("street_name"),
            "raw_project_name": record.get("project_name"),
            "raw_house_direction": record.get("house_direction"),
            "raw_balcony_direction": record.get("balcony_direction"),
        }

        df_in = pd.DataFrame([input_row])
        X = transform(df_in, self.schema)

        # 4. In-memory tree inference
        log_pred = float(self.model.predict(X)[0])
        naive_vnd = float(np.expm1(log_pred))

        # Compute native TreeSHAP on active booster
        booster = self.model.get_booster()
        dmat = xgb.DMatrix(X, feature_names=list(X.columns))
        best_iter = getattr(self.model, "best_iteration", None)
        iter_range = (0, int(best_iter) + 1) if best_iter is not None else (0, 0)
        contribs = booster.predict(dmat, pred_contribs=True, iteration_range=iter_range)[0]
        base_log = float(contribs[-1])
        base_price_vnd = int(np.expm1(base_log))

        v1_3_factors = []
        name_map = {
            "area": "Diện tích đất/sàn (m²)",
            "normalized_type": "Loại tài sản",
            "district": "Quận/Huyện",
            "ward": "Phường/Xã",
            "raw_street_name": "Tên tuyến đường",
            "raw_bedroom_count": "Số phòng ngủ",
            "bedroom_count": "Số phòng ngủ",
            "raw_road_width": "Độ rộng đường vào (m)",
            "road_width": "Độ rộng đường vào (m)",
            "raw_project_name": "Dự án BĐS",
            "raw_frontage_width": "Bề ngang mặt tiền (m)",
            "frontage_width": "Bề ngang mặt tiền (m)",
            "raw_floor_count": "Số tầng",
            "floor_count": "Số tầng",
            "raw_bathroom_count": "Số phòng tắm",
            "bathroom_count": "Số phòng tắm",
            "frontage_sqrt_area_ratio": "Tỷ lệ mặt tiền / diện tích",
        }
        for name, val in zip(list(X.columns), contribs[:-1]):
            val_float = float(val)
            if abs(val_float) < 1e-4:
                continue
            impact_pct = round((math.exp(val_float) - 1.0) * 100, 2)
            direction = "increase" if val_float > 0 else "decrease"
            label = name_map.get(name, name)
            note = f"Đóng góp {impact_pct:+.1f}% vào log-price"
            if name == "ward" and not record.get("ward"):
                label = "Phường/Xã (đang thiếu)"
                note = "Giá trị phường/xã không có trong input; đây là trạng thái thiếu của model, không phải địa chỉ thực."
            elif name == "raw_street_name" and not record.get("street_name"):
                label = "Tên tuyến đường (không có trong input)"
                note = "Tên đường không có trong input; đây là trạng thái thiếu của model, không phải địa chỉ thực."
            v1_3_factors.append({
                "feature_name": name,
                "label": label,
                "shap_value": round(val_float, 4),
                "impact_pct": impact_pct,
                "direction": direction,
                "context_note": note,
            })
        v1_3_factors.sort(key=lambda x: abs(x["shap_value"]), reverse=True)
        top_factors = v1_3_factors[:6]

        # 5. Price-band Duan Smearing Calibration
        method = self.calibration.get("method", "duan_by_band")
        if method == "duan_by_band":
            naive_band = band_of(naive_vnd)
            factors = self.calibration.get("band_smearing_factors", {})
            factor = float(factors.get(naive_band, self.calibration.get("duan_global_factor", 1.06613)))
            calibrated_vnd = float(np.maximum(0, np.exp(log_pred) * factor - 1.0))
        elif method == "duan_global":
            factor = float(self.calibration.get("duan_global_factor", 1.06613))
            calibrated_vnd = float(np.maximum(0, np.exp(log_pred) * factor - 1.0))
        else:
            factor = 1.0
            calibrated_vnd = naive_vnd

        if not math.isfinite(calibrated_vnd) or calibrated_vnd <= 0:
            raise RuntimeError(f"Kết quả dự đoán không hợp lệ: {calibrated_vnd}")

        # 6. Audit missing optional features and unknown categories
        optional_fields = [
            "floor_count", "frontage_width", "road_width",
            "bedroom_count", "bathroom_count", "street_name", "project_name",
            "house_direction", "balcony_direction",
        ]
        missing = [f for f in optional_fields if record.get(f) in (None, "")]

        warnings = [
            "Giá dự đoán là giá rao bán ước tính trên thị trường, không phải giá giao dịch công chứng.",
            "Giá giao dịch thực tế trên thị trường thường có biên độ thương lượng tùy theo vị trí, pháp lý và thỏa thuận giữa các bên."
        ]

        # Check for unknown vocabulary items
        vocabs = self.schema.get("vocabularies", {})
        if clean_category(record["district"]) not in vocabs.get("district", []):
            warnings.append(f"Quận '{record['district']}' chưa có trong danh mục chính thức Đà Nẵng; sử dụng ước tính tổng quát.")
        if record.get("ward") and clean_category(record["ward"]) not in vocabs.get("ward", []):
            warnings.append(f"Phường/xã '{record.get('ward')}' ít dữ liệu hoặc mới; mô hình áp dụng trọng số trung bình.")

        return {
            "model_version": "v1.3",
            "model_run": "tinix_xgboost_v1_3_integrated",
            "configuration": "standalone_duan_calibrated",
            "predicted_asking_price_vnd": int(round(calibrated_vnd)),
            "predicted_asking_price_million": round(calibrated_vnd / 1e6, 2),
            "predicted_asking_price_billion": round(calibrated_vnd / 1e9, 3),
            "price_band": band_of(calibrated_vnd),
            "currency": "VND",
            "price_basis": "Giá rao bán ước tính (Đà Nẵng TiniX + Zenodo multi-source).",
            "calibration_policy": method,
            "calibration_factor": round(factor, 5),
            "naive_price_vnd": int(round(naive_vnd)),
            "features_used": {
                "area": area_val,
                "normalized_type": record["normalized_type"],
                "district": record["district"],
                "ward": record.get("ward"),
                "bedroom_count": record.get("bedroom_count"),
                "floor_count": record.get("floor_count"),
                "road_width": record.get("road_width"),
                "frontage_width": record.get("frontage_width"),
                "street_name": record.get("street_name"),
                "project_name": record.get("project_name"),
                "bathroom_count": record.get("bathroom_count"),
                "house_direction": record.get("house_direction"),
                "balcony_direction": record.get("balcony_direction"),
                "road_width_source": record.get("road_width_source"),
                "frontage_width_source": record.get("frontage_width_source"),
            },
            "missing_features": missing,
            "warnings": warnings,
            "shap_explanation": {
                "base_value_log": round(base_log, 4),
                "base_price_vnd": base_price_vnd,
                "scale": "log(1 + price_vnd)",
                "top_factors": top_factors,
                "method": "TreeSHAP (Native Additive Contribution)",
                "summary_vi": f"Giá cơ sở phân khúc của V1.3 là {round(base_price_vnd / 1e9, 2)} tỷ đồng. Hiệu chỉnh Duan Smearing phân khúc {band_of(calibrated_vnd)} là {round(factor, 4)}x.",
            },
        }

    def predict_from_v6_payload(self, v6_payload: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a V6 ValuationRequest payload and execute V1.3 prediction."""
        v1_3_record = map_v6_to_v1_3(
            v6_payload,
            district_vocabulary=self.schema.get("vocabularies", {}).get("district"),
        )
        return self.predict(v1_3_record)
