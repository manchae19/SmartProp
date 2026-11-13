from dataclasses import dataclass, field
from pathlib import Path
import os
from urllib.parse import urlsplit


class RagUnavailable(RuntimeError):
    pass


class GroundingError(RuntimeError):
    pass


@dataclass(frozen=True)
class Settings:
    backend_url: str = "http://127.0.0.1:8080"
    corpus_path: Path = Path("var/rag/public-corpus.json")
    qwen_path: str = ""
    e5_path: str = ""
    e5_revision: str = "614241f622f53c4eeff9890bdc4f31cfecc418b3"
    index_dir: Path | None = None
    llm_provider: str = "transformers"
    ollama_url: str = "http://127.0.0.1:11434"
    ollama_model: str = "qwen3:4b-instruct"
    ollama_digest: str = ""
    ollama_keep_alive_seconds: int = 300
    backend_timeout_seconds: float = 10.0
    research_enabled: bool = False
    demo_key: str = field(default="", repr=False)
    sql_enabled: bool = False
    sql_host: str = "127.0.0.1"
    sql_port: int = 13306
    sql_database: str = ""
    sql_allow_production: bool = False
    sql_use_views: bool = False
    db_user: str = field(default="", repr=False)
    db_password: str = field(default="", repr=False)

    def __post_init__(self):
        u = urlsplit(self.backend_url)
        if u.scheme != "http" or u.hostname != "127.0.0.1" or u.port != 8080 or u.path not in ("", "/") or u.username or u.password or u.query or u.fragment:
            raise ValueError("RAG backend must be http://127.0.0.1:8080")
        o = urlsplit(self.ollama_url)
        if o.scheme != "http" or o.hostname != "127.0.0.1" or o.port != 11434 or o.path not in ("", "/") or o.username or o.password or o.query or o.fragment:
            raise ValueError("Ollama must be http://127.0.0.1:11434")
        if self.llm_provider not in ("transformers", "ollama") or self.ollama_model != "qwen3:4b-instruct":
            raise ValueError("Unsupported local RAG provider/model")
        if not 1 <= self.backend_timeout_seconds <= 60:
            raise ValueError("Backend tool timeout must be bounded")
        if type(self.ollama_keep_alive_seconds) is not int or not 0 <= self.ollama_keep_alive_seconds <= 300:
            raise ValueError("Ollama retention must be bounded between zero and 300 seconds")
        if self.sql_host not in ("127.0.0.1", "localhost"):
            raise ValueError("RAG SQL host must be local")
        if not 1 <= self.sql_port <= 65535:
            raise ValueError("RAG SQL port is invalid")
        if self.sql_port == 3306 and not self.sql_allow_production:
            raise ValueError("RAG SQL port 3306 is disabled; use staging 13306")
        if self.sql_database and not self.sql_database.replace("_", "").isalnum():
            raise ValueError("RAG SQL database name is invalid")
        if self.sql_enabled and (not self.sql_database or not self.db_user or not self.db_password):
            raise ValueError("RAG SQL database and credentials are required when SQL is enabled")

    @classmethod
    def from_env(cls):
        return cls(backend_url=os.getenv("RAG_BACKEND_URL", "http://127.0.0.1:8080"),
                   corpus_path=Path(os.getenv("RAG_CORPUS_PATH", "var/rag/public-corpus.json")),
                   qwen_path=os.getenv("RAG_QWEN_PATH", ""), e5_path=os.getenv("RAG_E5_PATH", ""),
                   e5_revision=os.getenv("RAG_E5_REVISION", "614241f622f53c4eeff9890bdc4f31cfecc418b3"),
                   index_dir=Path(os.environ["RAG_INDEX_DIR"]) if os.getenv("RAG_INDEX_DIR") else None,
                   llm_provider=os.getenv("RAG_LLM_PROVIDER", "transformers"),
                   ollama_url=os.getenv("RAG_OLLAMA_URL", "http://127.0.0.1:11434"),
                   ollama_model=os.getenv("RAG_OLLAMA_MODEL", "qwen3:4b-instruct"),
                   ollama_digest=os.getenv("RAG_OLLAMA_DIGEST", ""),
                   ollama_keep_alive_seconds=int(os.getenv("RAG_OLLAMA_KEEP_ALIVE_SECONDS", "300")),
                   backend_timeout_seconds=float(os.getenv("RAG_BACKEND_TIMEOUT_SECONDS", "10")),
                   research_enabled=os.getenv("RAG_RESEARCH_ENABLED", "false").lower() == "true",
                   demo_key=os.getenv("RAG_DEMO_KEY", ""), sql_enabled=os.getenv("RAG_SQL_ENABLED", "false").lower() == "true",
                   sql_host=os.getenv("RAG_SQL_HOST", "127.0.0.1"),
                   sql_port=int(os.getenv("RAG_SQL_PORT", "13306")),
                   sql_database=os.getenv("RAG_SQL_DATABASE", ""),
                   sql_allow_production=os.getenv("RAG_SQL_ALLOW_PRODUCTION", "false").lower() == "true",
                   sql_use_views=os.getenv("RAG_SQL_USE_VIEWS", "false").lower() == "true",
                   db_user=os.getenv("RAG_DB_USER", ""), db_password=os.getenv("RAG_DB_PASSWORD", ""))
