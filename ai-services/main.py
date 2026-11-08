"""SmartProp AI service. Start with: python -m uvicorn main:app."""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.valuation import router as v6_router
from app.api.valuation_v1_3 import router as v1_3_router
from app.core.shadow_manager import ShadowTelemetryManager
from app.models.xgboost.predictor_v6 import PredictorV6
from app.models.xgboost.predictor_v1_3 import PredictorV1_3, ModelArtifactError

logger = logging.getLogger("smartprop.ai")


def create_app(model_dir=None, v1_3_model_dir=None):
    @asynccontextmanager
    async def lifespan(app):
        # 1. Primary V6 Production Model
        app.state.predictor = PredictorV6(model_dir)

        # 2. Shadow Telemetry Manager
        app.state.shadow_manager = ShadowTelemetryManager()

        # 3. XGBoost V1.3 Warm In-Memory Predictor
        try:
            app.state.predictor_v1_3 = PredictorV1_3(v1_3_model_dir)
            logger.info("XGBoost V1.3 in-memory predictor initialized and verified.")
        except (ModelArtifactError, Exception) as exc:
            logger.warning(f"XGBoost V1.3 initialization deferred or failed: {exc}")
            app.state.predictor_v1_3 = None

        try:
            yield
        finally:
            app.state.predictor = None
            app.state.predictor_v1_3 = None
            app.state.shadow_manager = None

    application = FastAPI(
        title="SmartProp AI",
        version="6.1.0",
        description="Ước tính giá rao nhà ở, đất nền và căn hộ từ model v6 (kèm Shadow mode V1.3).",
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo request values: NaN/Infinity cannot be serialized as JSON,
        # and long property descriptions do not belong in an error response.
        details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    # Public active V6 router
    application.include_router(v6_router)

    # Internal / Shadow V1.3 router
    application.include_router(v1_3_router)

    return application


app = create_app()
