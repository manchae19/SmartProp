"""Valuation endpoints; models live in application state, not request state."""
import time
from datetime import datetime, timezone
from fastapi import APIRouter, BackgroundTasks, HTTPException, Request

from app.api.schemas import PredictionResponse, ValuationRequest, V1_3PreviewResponse
from app.models.xgboost.adapter_v1_3 import real_feature_input_enabled
from app.models.xgboost.features_v1_3 import clean_category

router = APIRouter()


def predictor_for(request):
    """The primary predictor is V1.3; V6 is only an optional fallback."""
    predictor = getattr(request.app.state, "predictor_v1_3", None)
    if predictor is None:
        raise HTTPException(status_code=503, detail="Model chưa sẵn sàng.")
    return predictor


@router.get("/health")
def health(request: Request):
    predictor = getattr(request.app.state, "predictor_v1_3", None)
    if predictor is None:
        # Report the real state instead of failing the probe: the service is up but the
        # artifacts are missing or broken, and the reason is what an operator needs.
        return {
            "status": "degraded",
            "model_version": "v1.3",
            "model_ready": False,
            "reason": getattr(request.app.state, "v1_3_error", None),
        }
    return {"status": "ok", "model_version": "v1.3", "model_ready": True}


def real_features_enabled() -> bool:
    """Single source of truth: the adapter decides, so /model/options cannot drift.

    Keeping a second default here meant the API advertised legacy mode while the
    adapter already served real measurements (or the reverse). Delegate instead.
    """
    return real_feature_input_enabled()


OPTIONAL_INPUTS = [
    "road_width_m", "frontage_width_m", "street_name", "project_name",
    "bathrooms", "house_direction", "balcony_direction",
]
DISTRICT_DISPLAY = {
    "cẩm lệ": "Cẩm Lệ", "hòa vang": "Hòa Vang", "hải châu": "Hải Châu",
    "liên chiểu": "Liên Chiểu", "ngũ hành sơn": "Ngũ Hành Sơn",
    "sơn trà": "Sơn Trà", "thanh khê": "Thanh Khê",
}
TYPE_TO_CATEGORY = {
    "house": "Nhà ở", "villa": "Nhà ở",
    "land": "Đất nền", "apartment": "Căn hộ chung cư",
}


@router.get("/model/options")
def model_options(request: Request):
    """Options come from V1.3 itself: its own supported types and districts.

    When the artifacts are missing the route still answers, reporting the model as
    unavailable, so a client can render the reason instead of failing outright.
    """
    predictor = getattr(request.app.state, "predictor_v1_3", None)
    enabled = real_features_enabled()
    if predictor is None:
        return {
            "model_version": "v1.3",
            "model_run": None,
            "categories": [],
            "v1_3": {
                "available": False,
                "status": "UNAVAILABLE",
                "real_features_enabled": enabled,
                "optional_inputs": [],
                "supported_types": [],
                "supported_categories": [],
                "unavailable_reason": getattr(request.app.state, "v1_3_error", None)
                or "V1.3 artifacts unavailable",
            },
        }
    info = predictor.info()
    supported_types = [str(item).lower() for item in info.get("supported_types", [])]
    supported_categories = sorted({TYPE_TO_CATEGORY[item] for item in supported_types if item in TYPE_TO_CATEGORY})
    # V1.3 stores districts in lower case; the API and the form use the display form.
    districts = [DISTRICT_DISPLAY.get(str(item).lower(), str(item)) for item in info.get("supported_districts", [])]
    return {
        "model_version": "v1.3",
        "model_run": info.get("model_run"),
        "categories": [
            {"category": category, "locations": list(districts)}
            for category in supported_categories
        ],
        "v1_3": {
            "available": True,
            "status": "PRIMARY",
            "real_features_enabled": enabled,
            "optional_inputs": list(OPTIONAL_INPUTS) if enabled else [],
            "supported_types": supported_types,
            "supported_categories": supported_categories,
            "unavailable_reason": None,
        },
    }


def _supported_locations(predictor) -> set:
    """Districts the loaded V1.3 schema actually knows, straight from the artifact.

    The schema vocabulary is already NFC-casefolded, so the request value is normalised
    the same way before comparison. Comparison is exact after normalisation: no fuzzy or
    alias matching, and the caller's own spelling is never rewritten.
    """
    info = predictor.info() if hasattr(predictor, "info") else {}
    return {clean_category(v) for v in (info.get("supported_districts") or [])}


@router.post("/predict", response_model=V1_3PreviewResponse)
def predict(payload: ValuationRequest, request: Request, background_tasks: BackgroundTasks):
    predictor = predictor_for(request)
    # The model has no way to price a district it never trained on, so an unknown
    # district is a client error rather than a silent extrapolation.
    locations = _supported_locations(predictor)
    if locations and clean_category(payload.location_feature) not in locations:
        raise HTTPException(
            status_code=422,
            detail="unsupported_location: địa bàn không được mô hình hỗ trợ: "
                   + payload.location_feature,
        )
    t0 = time.perf_counter()
    try:
        response = predictor.predict_from_v6_payload(payload.model_dump())
    except (ValueError, KeyError) as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
    except Exception as error:
        # A model fault must surface as an error response, never take the service down.
        raise HTTPException(status_code=500, detail=f"Lỗi suy luận mô hình V1.3: {error}") from error
    latency_ms = (time.perf_counter() - t0) * 1000.0

    # Shadow comparison only exists when the optional V6 model is loaded.
    shadow_manager = getattr(request.app.state, "shadow_manager", None)
    predictor_v6 = getattr(request.app.state, "predictor", None)
    if shadow_manager and shadow_manager.is_enabled() and predictor_v6:
        background_tasks.add_task(
            shadow_manager.record_shadow_evaluation,
            predictor_v1_3=predictor,
            v6_payload=payload.model_dump(),
            v6_response=response,
            v6_latency_ms=latency_ms,
        )

    return {
        "is_preview": False,
        "model_version": "v1.3",
        "status": "PRIMARY",
        "predicted_asking_price_vnd": response["predicted_asking_price_vnd"],
        "predicted_asking_price_billion": response["predicted_asking_price_billion"],
        "price_band": response["price_band"],
        "calibration_factor": response["calibration_factor"],
        "calibration_policy": response["calibration_policy"],
        "naive_price_vnd": response["naive_price_vnd"],
        "features_used": response["features_used"],
        "missing_features": response.get("missing_features", []),
        "shap_explanation": response.get("shap_explanation"),
        "valuation_timestamp": datetime.now(timezone.utc).isoformat(),
        "disclaimer": "Giá rao ước tính từ mô hình V1.3 (Multi-Source Zenodo + TiniX).",
    }


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
