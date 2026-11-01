"""Valuation endpoints; models live in application state, not request state."""
from fastapi import APIRouter, HTTPException, Request

from app.api.schemas import PredictionResponse, ValuationRequest

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


@router.get("/model/options")
def model_options(request: Request):
    return predictor_for(request).options()


@router.post("/predict", response_model=PredictionResponse)
def predict(payload: ValuationRequest, request: Request):
    predictor = predictor_for(request)
    try:
        return predictor.predict(payload.model_dump())
    except ValueError as error:
        raise HTTPException(status_code=422, detail=str(error)) from error
