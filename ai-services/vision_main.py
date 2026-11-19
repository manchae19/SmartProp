"""Standalone YOLOv8 property-image analysis service.

Run from ``ai-services/`` with the vision virtualenv:

    ..\\.scratch\\yolov8-venv\\Scripts\\python.exe -m uvicorn vision_main:app --host 127.0.0.1 --port 18002

This process is intentionally separate from:
  * ``rag_main``      (port 8001) — RAG chat, E5 + FAISS + Qwen
  * ``imagecheck_main`` (port 18001) — duplicate-image detection

Keeping them apart means a torch/ultralytics import failure here cannot take
down chat or duplicate scanning, and each can be restarted on its own.

Model: Ultralytics YOLOv8n, COCO pretrained, used as published (no retraining).
License **AGPL-3.0** — https://github.com/ultralytics/ultralytics
See ``ai-services/docs/YOLOV8_LICENSE_NOTICE.md`` for the academic-use record and
the obligations that apply if this service is ever exposed beyond the project.
"""
from fastapi import FastAPI

from app.vision.api import create_vision_router
from app.vision.config import VisionSettings

settings = VisionSettings.from_env()

app = FastAPI(
    title="SmartProp image analysis",
    version="1.0.0",
    description=(
        "YOLOv8n object detection for property photos (MVP). "
        "Model: Ultralytics YOLOv8n (AGPL-3.0), COCO pretrained, not retrained."
    ),
)
app.include_router(create_vision_router(settings))
