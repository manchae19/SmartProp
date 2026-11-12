"""Internal Valuation API Router for XGBoost V1.3 Multi-Source.

Enforces zero-trust authorization, constant-time token comparison, role-based
endpoint isolation (Read vs Admin), and strict input validation.
"""
import os
import secrets
from typing import Annotated, Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Security, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field

router = APIRouter(prefix="/api/internal/v1_3", tags=["Valuation V1.3 Internal"])

security_bearer = HTTPBearer(auto_error=False)




def _extract_provided_token(
    x_internal_token: Optional[str] = Header(None, alias="X-Internal-Token"),
    bearer_creds: Optional[HTTPAuthorizationCredentials] = Security(security_bearer),
) -> Optional[str]:
    """Extract internal token from either X-Internal-Token or Bearer Authorization."""
    if x_internal_token:
        return x_internal_token.strip()
    if bearer_creds and bearer_creds.credentials:
        return bearer_creds.credentials.strip()
    return None


def verify_internal_read(
    token: Optional[str] = Depends(_extract_provided_token),
) -> bool:
    """Authorize read-only internal access (stats, model info, test predictions)."""
    expected = os.environ.get("SMARTPROP_INTERNAL_KEY")

    if not expected:
        raise HTTPException(status_code=503, detail="Internal access is not configured")

    # Check if credentials provided
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Missing internal credentials (X-Internal-Token or Authorization: Bearer)",
            headers={"WWW-Authenticate": "Bearer"},
        )

    # Constant-time comparison
    if not secrets.compare_digest(token, expected):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Invalid internal token"
        )
    return True


def verify_internal_admin(
    token: Optional[str] = Depends(_extract_provided_token),
) -> bool:
    """Authorize administrative state-changing access (toggle shadow, reset telemetry)."""
    # Requires admin key or falls back to master internal key
    expected_admin = os.environ.get("SMARTPROP_INTERNAL_ADMIN_KEY") or os.environ.get("SMARTPROP_INTERNAL_KEY")

    if not expected_admin:
        raise HTTPException(status_code=503, detail="Internal admin access is not configured")

    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Unauthorized: Admin credentials required for state mutation",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not secrets.compare_digest(token, expected_admin):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Forbidden: Insufficient privileges for admin shadow control"
        )
    return True


def get_v1_3_predictor(request: Request):
    """Retrieve in-memory V1.3 predictor from application state."""
    predictor = getattr(request.app.state, "predictor_v1_3", None)
    if predictor is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Mô hình XGBoost V1.3 chưa sẵn sàng hoặc nạp thất bại."
        )
    return predictor


def get_shadow_manager(request: Request):
    """Retrieve shadow manager instance from application state."""
    manager = getattr(request.app.state, "shadow_manager", None)
    if manager is None:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Shadow Telemetry Manager chưa được khởi tạo."
        )
    return manager


# --- Pydantic Schemas ---

class V1_3DirectRequest(BaseModel):
    """Canonical input schema for direct XGBoost V1.3 inference."""
    model_config = ConfigDict(extra="ignore", str_strip_whitespace=True)

    area: Annotated[float, Field(ge=5.0, le=50_000.0, description="Diện tích (m²)")]
    normalized_type: Literal["HOUSE", "LAND", "APARTMENT", "VILLA"]
    district: Annotated[str, Field(min_length=1, max_length=100, description="Quận/Huyện thuộc Đà Nẵng")]
    ward: Optional[str] = None
    street_name: Optional[str] = None
    project_name: Optional[str] = None
    floor_count: Optional[float] = Field(None, ge=0.0, le=100.0)
    bedroom_count: Optional[float] = Field(None, ge=0.0, le=100.0)
    bathroom_count: Optional[float] = Field(None, ge=0.0, le=100.0)
    road_width: Optional[float] = Field(None, ge=0.0, le=100.0)
    frontage_width: Optional[float] = Field(None, ge=0.0, le=500.0)
    house_direction: Optional[str] = None
    balcony_direction: Optional[str] = None


class ToggleShadowRequest(BaseModel):
    enabled: bool


# --- Endpoints ---

@router.get("/health")
def v1_3_health(request: Request):
    """Liveness check for V1.3 microservice (safe public or internal probe)."""
    predictor = getattr(request.app.state, "predictor_v1_3", None)
    ready = predictor is not None
    return {
        "status": "ok" if ready else "degraded",
        "model_version": "v1.3",
        "model_ready": ready,
    }


@router.get("/model/info")
def v1_3_model_info(
    request: Request,
    _auth: bool = Depends(verify_internal_read)
):
    """Return model hyperparameters and schema metadata (Protected: Read-token)."""
    predictor = get_v1_3_predictor(request)
    return predictor.info()


@router.post("/predict")
def v1_3_predict(
    payload: Dict[str, Any],
    request: Request,
    _auth: bool = Depends(verify_internal_read)
):
    """Execute prediction on V1.3 using either V1.3 canonical or V6 payload (Protected)."""
    predictor = get_v1_3_predictor(request)

    try:
        # Detect payload format
        if "category" in payload or "area_sqm" in payload:
            # V6 Format adapter path
            res = predictor.predict_from_v6_payload(payload)
        else:
            # Direct V1.3 format
            validated = V1_3DirectRequest(**payload)
            res = predictor.predict(validated.model_dump())

        return res
    except ValueError as err:
        raise HTTPException(status_code=422, detail=str(err)) from err
    except Exception as err:
        raise HTTPException(status_code=500, detail=f"Lỗi suy luận V1.3: {str(err)}") from err


@router.get("/shadow/stats")
def v1_3_shadow_stats(
    request: Request,
    _auth: bool = Depends(verify_internal_read)
):
    """Retrieve statistical divergence and latency metrics from shadow buffer (Protected: Read-token)."""
    manager = get_shadow_manager(request)
    return manager.get_summary_statistics()


@router.post("/shadow/toggle")
def v1_3_shadow_toggle(
    payload: ToggleShadowRequest,
    request: Request,
    _auth: bool = Depends(verify_internal_admin)
):
    """Enable or disable async Shadow evaluation at runtime (Protected: Admin-token)."""
    manager = get_shadow_manager(request)
    manager.set_enabled(payload.enabled)
    return {
        "status": "ok",
        "shadow_enabled": manager.is_enabled(),
        "circuit_breaker": manager.circuit_open
    }


@router.post("/shadow/reset")
def v1_3_shadow_reset(
    request: Request,
    _auth: bool = Depends(verify_internal_admin)
):
    """Reset telemetry buffer, counters, and circuit breaker (Protected: Admin-token)."""
    manager = get_shadow_manager(request)
    manager.reset_stats()
    return {"status": "ok", "message": "Telemetry metrics and circuit breaker reset."}
