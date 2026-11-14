"""Valuation endpoints; models live in application state, not request state."""
import os
import time
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.schemas import PredictionResponse, ValuationRequest, V1_3PreviewResponse

router = APIRouter()


def predictor_for(request):
    predictor = getattr(request.app.state, "predictor", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model chưa sẵn sàng.")
    return predictor


@router.get("/health")
def health(request: Request):
    predictor_for(request)
    return {"status": "ok", "model_version": "v6", "model_ready": True}


def real_features_enabled() -> bool:
    return os.environ.get("SMARTPROP_V1_3_REAL_FEATURES", "false").strip().lower() in {"1", "true", "yes", "on"}


OPTIONAL_INPUTS = [
    "road_width_m", "frontage_width_m", "street_name", "project_name",
    "bathrooms", "house_direction", "balcony_direction",
]
TYPE_TO_CATEGORY = {
    "house": "Nhà ở", "villa": "Nhà ở",
    "land": "Đất nền", "apartment": "Căn hộ chung cư",
}


@router.get("/model/options")
def model_options(request: Request):
    data = predictor_for(request).options()
    predictor_v1_3 = getattr(request.app.state, "predictor_v1_3", None)
    supported_types = []
    if predictor_v1_3 is not None:
        supported_types = [str(item).lower() for item in predictor_v1_3.info().get("supported_types", [])]
    supported_categories = sorted({TYPE_TO_CATEGORY[item] for item in supported_types if item in TYPE_TO_CATEGORY})
    enabled = real_features_enabled()
    data["v1_3"] = {
        "available": predictor_v1_3 is not None,
        "status": "PREVIEW_EXPERIMENTAL" if predictor_v1_3 is not None else "UNAVAILABLE",
        "real_features_enabled": enabled,
        "optional_inputs": list(OPTIONAL_INPUTS) if enabled and predictor_v1_3 is not None else [],
        "supported_types": supported_types,
        "supported_categories": supported_categories,
        "unavailable_reason": None if predictor_v1_3 is not None else "V1.3 artifacts unavailable",
    }
    return data


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: ValuationRequest, request: Request, background_tasks: BackgroundTasks):
    predictor = predictor_for(request)
    t0 = time.perf_counter()
    try:
        response = predictor.predict(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    v6_latency_ms = (time.perf_counter() - t0) * 1000.0

    # Non-blocking async shadow hook for V1.3 comparison
    shadow_manager = getattr(request.app.state, "shadow_manager", None)
    predictor_v1_3 = getattr(request.app.state, "predictor_v1_3", None)
    if shadow_manager and shadow_manager.is_enabled() and predictor_v1_3:
        background_tasks.add_task(
            shadow_manager.record_shadow_evaluation,
            predictor_v1_3=predictor_v1_3,
            v6_payload=payload.model_dump(),
            v6_response=response,
            v6_latency_ms=v6_latency_ms,
        )

    return response


@router.post("/predict/v1_3_preview", response_model=V1_3PreviewResponse)
def predict_v1_3_preview(payload: ValuationRequest, request: Request):
    """Safe authenticated developer preview endpoint for V1.3 Multi-Source XGBoost.

    Does NOT replace public V6. Exposes V1.3 prediction and TreeSHAP explainability
    for research, staging preview, and side-by-side model auditing without requiring
    administrative master credentials in client code.
    """
    predictor_v1_3 = getattr(request.app.state, "predictor_v1_3", None)
    if predictor_v1_3 is None:
        raise HTTPException(
            status_code=503,
            detail="Mô hình thử nghiệm V1.3 chưa sẵn sàng hoặc chưa được khởi tạo."
        )

    try:
        raw_res = predictor_v1_3.predict_from_v6_payload(payload.model_dump())
    except (ValueError, KeyError) as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Lỗi suy luận mô hình V1.3: {exc}") from exc

    return {
        "is_preview": True,
        "model_version": "v1.3",
        "status": "PREVIEW_EXPERIMENTAL",
        "predicted_asking_price_vnd": raw_res["predicted_asking_price_vnd"],
        "predicted_asking_price_billion": raw_res["predicted_asking_price_billion"],
        "price_band": raw_res["price_band"],
        "calibration_factor": raw_res["calibration_factor"],
        "calibration_policy": raw_res["calibration_policy"],
        "naive_price_vnd": raw_res["naive_price_vnd"],
        "features_used": raw_res["features_used"],
        "missing_features": raw_res.get("missing_features", []),
        "shap_explanation": raw_res.get("shap_explanation"),
        "valuation_timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Mô hình thử nghiệm nghiên cứu V1.3 (Multi-Source Zenodo + TiniX). Không sử dụng làm định giá giao dịch chính thức."
    }
