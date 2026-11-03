"""Request-local, content-free diagnostics. Never logs questions, facts or credentials."""
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime, timezone
import json
import logging
import time
import uuid

_trace = ContextVar("rag_trace", default=None)
logger = logging.getLogger("uvicorn.error")
KNOWN_CODES = frozenset(['CONTROLLED_INDEX_UNAVAILABLE', 'CONTROLLED_OLLAMA_UNAVAILABLE', 'CORPUS_DOCUMENT_HASH_MISMATCH', 'CORPUS_HASH_MISMATCH', 'CORPUS_SOURCE_ID_COLLISION', 'CORPUS_TOO_LARGE', 'DUPLICATE_RECOMMENDATION_GROUP', 'E5_DEPENDENCIES_MISSING', 'E5_LOCAL_WEIGHTS_MISSING', 'E5_RUNTIME_UNAVAILABLE', 'FAISS_DEPENDENCIES_MISSING', 'FULL_RAG_RUNTIME_UNAVAILABLE', 'GENERATED_RANKING_DRIFT', 'INDEX_CHECKSUM_MISMATCH', 'INDEX_MAPPING_MISMATCH', 'INDEX_VERSION_DRIFT', 'INELIGIBLE_RECOMMENDATION', 'INVALID_AREA_ID', 'INVALID_CATALOG_COVERAGE', 'INVALID_CORPUS_PERMISSIONS', 'INVALID_E5_VECTORS', 'INVALID_GENERATED_ANSWER', 'INVALID_GENERATED_SENTENCE', 'INVALID_INDEX_SIZE', 'INVALID_INDEX_VECTORS', 'INVALID_MODEL_PLAN', 'INVALID_PROPERTY_IDS', 'INVALID_RECOMMENDATION_NUMBER', 'INVALID_RECOMMENDATION_RESULT', 'NO_GROUNDED_FACTS', 'OLLAMA_BUSY', 'OLLAMA_GENERATION_INCOMPLETE', 'OLLAMA_GENERATION_UNAVAILABLE', 'OLLAMA_INVALID_RANKED_OUTPUT', 'OLLAMA_MODEL_IDENTITY_MISMATCH', 'OLLAMA_UNAVAILABLE_OR_MODEL_MISMATCH', 'PERSISTENT_INDEX_INVALID', 'PERSISTENT_INDEX_MUST_BE_PUBLIC', 'PERSISTENT_INDEX_UNAVAILABLE', 'PUBLIC_CORPUS_PERMISSION_VIOLATION', 'PUBLIC_CORPUS_SNAPSHOT_EXPIRED', 'PUBLIC_CORPUS_UNAVAILABLE', 'PUBLIC_CORPUS_VERSION_DRIFT', 'PUBLIC_RESEARCH_LEAK', 'QWEN_BUSY', 'QWEN_CONTEXT_LIMIT', 'QWEN_CUDA_UNAVAILABLE', 'QWEN_DEPENDENCIES_MISSING', 'QWEN_INSUFFICIENT_FREE_VRAM', 'QWEN_LOCAL_WEIGHTS_MISSING', 'QWEN_RUNTIME_UNAVAILABLE', 'READ_ONLY_SQL_NOT_CONFIGURED', 'READ_ONLY_SQL_UNAVAILABLE', 'RESEARCH_DOCUMENTS_NOT_IN_PUBLIC_INDEX', 'RESTRICTED_AMENITY_METADATA', 'SEMANTIC_RETRIEVAL_UNAVAILABLE', 'SQL_API_FACT_MISMATCH', 'UNEXPECTED_RECOMMENDATION_MODE', 'UNSUPPORTED_GENERATED_CLAIM', 'UNSUPPORTED_MODEL_FACT', 'WRONG_SQL_TARGET', 'INVALID_AMENITY_CATEGORY', 'INVALID_AMENITY_MAP_EVIDENCE', 'AMENITY_SCOPE_MISMATCH', 'NO_MATCHING_AMENITY_EVIDENCE'])


def reason(error):
    # Only internal constant codes may reach the log, never arbitrary exception text.
    value = str(error)
    if value in KNOWN_CODES:
        return value
    return type(error).__name__


def event(name, **fields):
    trace = _trace.get()
    if trace is not None:
        logger.info("RAG_DIAGNOSTIC %s", json.dumps({"timestampUtc": datetime.now(timezone.utc).isoformat(),
            "requestId": trace["id"], "event": name, **fields}, separators=(",", ":")))


@contextmanager
def request_trace(endpoint, strict):
    token = _trace.set({"id": uuid.uuid4().hex})
    start = time.perf_counter()
    event("request_start", endpoint=endpoint, strict=strict)
    try:
        yield _trace.get()["id"]
    finally:
        event("request_end", elapsedMs=round((time.perf_counter()-start)*1000, 1))
        _trace.reset(token)


def traced(stage, operation):
    start = time.perf_counter()
    event("stage_start", stage=stage)
    try:
        result = operation()
    except Exception as error:
        fields = {"stage": stage, "outcome": "error", "reason": reason(error), "errorType": type(error).__name__}
        cause = error.__cause__
        if cause is not None:
            fields["causeType"] = type(cause).__name__
        event("stage_end", elapsedMs=round((time.perf_counter()-start)*1000, 1), **fields)
        raise
    event("stage_end", stage=stage, outcome="ok", elapsedMs=round((time.perf_counter()-start)*1000, 1))
    return result
