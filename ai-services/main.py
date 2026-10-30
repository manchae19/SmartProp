"""SmartProp AI service. Start with: python -m uvicorn main:app."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.valuation import router
from app.models.xgboost.predictor_v6 import PredictorV6


def create_app(model_dir=None):
    @asynccontextmanager
    async def lifespan(app):
        app.state.predictor = PredictorV6(model_dir)
        try:
            yield
        finally:
            app.state.predictor = None

    application = FastAPI(
        title="SmartProp AI",
        version="6.0.0",
        description="Ước tính giá rao nhà ở, đất nền và căn hộ từ model v6.",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    @application.exception_handler(RequestValidationError)
    async def validation_error(request, error):
        # Do not echo request values: NaN/Infinity cannot be serialized as JSON,
        # and long property descriptions do not belong in an error response.
        details = [{key: item[key] for key in ("loc", "msg", "type")} for item in error.errors()]
        return JSONResponse(status_code=422, content={"detail": details})

    application.include_router(router)
    return application


app = create_app()
