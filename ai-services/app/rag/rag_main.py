"""Run separately: python -m uvicorn rag_main:app --host 127.0.0.1 --port 8001 --no-proxy-headers."""
from app.rag.api import create_chat_app
from app.imagecheck.api import create_image_router

app = create_chat_app()
app.include_router(create_image_router())
