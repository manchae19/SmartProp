"""Standalone imagecheck FastAPI entrypoint for isolated staging tests."""
from fastapi import FastAPI

from app.imagecheck.api import create_image_router
from app.rag.config import Settings

app = FastAPI(title="SmartProp imagecheck")
app.include_router(create_image_router(Settings.from_env()))
