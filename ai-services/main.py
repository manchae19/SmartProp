"""SmartProp AI service. Start with: python -m uvicorn main:app.

V1.3 is the primary model: the service starts, serves options and predicts with only
the V1.3 artifacts present. V6 is optional and only loads when its own artifacts exist,
so a machine without them still runs every valuation flow.
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.api.valuation import router as v6_router
from app.api.valuation_v1_3 import router as v1_3_router
from app.core.shadow_manager import ShadowTelemetryManager
from app.models.xgboost.predictor_v1_3 import PredictorV1_3, ModelArtifactError

logger = logging.getLogger("smartprop.ai")


def create_app(model_dir=None, v1_3_model_dir=None):
    @asynccontextmanager
    async def lifespan(app):
        # 1. Primary V1.3 model. A missing or broken artifact set is reported through
        #    /health instead of preventing the service from starting.
        app.state.v1_3_error = None
        try:
            app.state.predictor_v1_3 = PredictorV1_3(v1_3_model_dir)
            logger.info("XGBoost V1.3 in-memory predictor initialized and verified.")
        except (ModelArtifactError, Exception) as exc:
            logger.warning(f"XGBoost V1.3 initialization failed: {exc}")
            app.state.predictor_v1_3 = None
            app.state.v1_3_error = str(exc)[:300]

        # 2. V6 is optional. It is only imported and loaded when its artifacts are present,
        #    so a machine that ships V1.3 alone never needs the V6 runtime.
        app.state.predictor = None
        app.state.v6_error = None
        try:
            from app.models.xgboost.predictor_v6 import PredictorV6

            app.state.predictor = PredictorV6(model_dir)
            logger.info("XGBoost V6 predictor initialized (optional fallback).")
        except Exception as exc:
            logger.info(f"XGBoost V6 not available, continuing with V1.3 only: {exc}")
            app.state.v6_error = str(exc)[:300]

        # 3. Shadow Telemetry Manager (only meaningful when both models are loaded).
        app.state.shadow_manager = ShadowTelemetryManager()

        try:
            yield
        finally:
            app.state.predictor = None
            app.state.predictor_v1_3 = None
            app.state.v1_3_error = None
            app.state.v6_error = None
            app.state.shadow_manager = None

    application = FastAPI(
        title="SmartProp AI",
        version="7.0.0",
        description="Ước tính giá rao nhà ở, đất nền và căn hộ từ model V1.3.",
        lifespan=lifespan,
    )

    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo request values: NaN/Infinity cannot be serialized as JSON,
        # and long property descriptions do not belong in an error response.
        details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    # Public valuation routes, now served by V1.3.
    application.include_router(v6_router)

    # Internal V1.3 routes (health, stats, admin).
    application.include_router(v1_3_router)

    return application


app = create_app()
