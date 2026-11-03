"""Separate chat app: valuation/XGBoost lifespan and all Java modules remain unchanged."""
from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
from threading import BoundedSemaphore
from fastapi import FastAPI, Header, HTTPException, Request
from .config import GroundingError, RagUnavailable, Settings
from .embedding import E5Embedding
from .knowledge import KnowledgeStore
from .llm import QwenLLM
from .ollama_llm import OllamaQwen
from .orchestrator import ChatOrchestrator
from .retriever import FaissRetriever
from .schemas import ChatRequest, ChatResponse
from .tools import BackendTools, PublishedPropertyRepository, UpstreamError
from .diagnostics import event, reason, request_trace


def create_chat_app(settings=None, orchestrator=None):
    settings = settings or Settings.from_env()
    backend = None
    if orchestrator is None:
        backend = BackendTools(settings)
        llm = OllamaQwen(settings) if settings.llm_provider == "ollama" else QwenLLM(settings.qwen_path)
        orchestrator = ChatOrchestrator(backend, PublishedPropertyRepository(settings), KnowledgeStore(settings.corpus_path),
                                        FaissRetriever(E5Embedding(settings.e5_path, settings.e5_revision), settings.index_dir), llm)
    slots = BoundedSemaphore(4)

    @asynccontextmanager
    async def lifespan(app):
        yield
        if backend:
            backend.close()

    app = FastAPI(title="SmartProp Grounded Chat", version="19.5.3", lifespan=lifespan)

    @app.middleware("http")
    async def no_store(request, call_next):
        response = await call_next(request)
        response.headers["Cache-Control"] = "no-store"
        return response

    @app.get("/chat/health")
    def health():
        if settings.llm_provider == "ollama":
            deps = {k: importlib.util.find_spec(k) is not None for k in ("torch", "sentence_transformers", "faiss")}
            try:
                status = orchestrator.llm.status()
            except RagUnavailable:
                status = {"available": False}
            configured = all(deps.values()) and bool(settings.e5_path and Path(settings.e5_path).is_dir()) and status["available"]
            return {"status": "ready" if configured and orchestrator.retriever.manifest and orchestrator.retriever.embedding.model is not None else "configured_not_loaded" if configured else "degraded",
                    "dependencies": deps, "backendToolTimeoutSeconds": settings.backend_timeout_seconds, "provider": "OLLAMA", "model": settings.ollama_model,
                    "ollamaAvailable": status["available"], "downloadsAllowed": False,
                    "researchEnabled": settings.research_enabled, "ollamaKeepAliveSeconds": settings.ollama_keep_alive_seconds,
                    "corpusPresent": settings.corpus_path.is_file()}
        deps = {k: importlib.util.find_spec(k) is not None for k in ("torch", "transformers", "bitsandbytes", "sentence_transformers", "faiss")}
        configured = bool(settings.qwen_path and settings.e5_path and Path(settings.qwen_path).is_dir() and Path(settings.e5_path).is_dir())
        return {"status": "configured_not_loaded" if all(deps.values()) and configured else "degraded",
                "dependencies": deps, "localWeightsConfigured": configured, "downloadsAllowed": False,
                "qwenModel": QwenLLM.model_id, "embeddingModel": E5Embedding.model_id,
                "researchEnabled": settings.research_enabled, "corpusPresent": settings.corpus_path.is_file()}

    def run(payload, research=False, token=None):
        with request_trace("/chat/research" if research else "/chat", payload.requireGeneration):
            result = execute(payload, research, token)
            event("response", status=200, generationMode=result.generationMode, retrievalMode=result.retrievalMode)
            return result

    def execute(payload, research, token):
        if not slots.acquire(blocking=False):
            event("response", status=429, reason="CHAT_BUSY")
            raise HTTPException(429, "Chat đang bận; vui lòng thử lại.")
        try:
            return orchestrator.chat(payload, research=research, token=token)
        except UpstreamError as e:
            event("response", status=e.status, reason="BACKEND_UPSTREAM_ERROR")
            raise HTTPException(e.status, "Công cụ Backend chưa sẵn sàng hoặc không đủ quyền truy cập.") from None
        except RagUnavailable as e:
            event("response", status=503, reason=reason(e))
            raise HTTPException(503, "RAG runtime hoặc kho bằng chứng chưa sẵn sàng; không tải model tự động.") from None
        except (GroundingError, KeyError, ValueError, TypeError) as e:
            event("response", status=502, reason=reason(e))
            raise HTTPException(502, "Bằng chứng không khớp hoặc không đúng quyền; đã chặn câu trả lời.") from None
        finally:
            slots.release()

    @app.post("/chat", response_model=ChatResponse)
    def chat(payload: ChatRequest):
        # No caller-controlled mode, SQL, source filter or forwarded credentials on this route.
        return run(payload)

    @app.post("/chat/research", response_model=ChatResponse)
    def research_chat(payload: ChatRequest, request: Request, authorization: str | None = Header(default=None)):
        if not settings.research_enabled or not settings.demo_key:
            raise HTTPException(403, "Research chat chưa được bật nội bộ.")
        if request.client is None or request.client.host not in ("127.0.0.1", "::1"):
            raise HTTPException(403, "Research chat chỉ dành cho loopback.")
        if not authorization:
            raise HTTPException(401, "Cần phiên đăng nhập ADMIN hợp lệ.")
        return run(payload, True, authorization)

    return app
