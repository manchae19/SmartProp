"""Notebook cell 6: multilingual-e5-small, normalized query/passage vectors."""
from pathlib import Path
from threading import Lock
from .config import RagUnavailable


class E5Embedding:
    model_id = "intfloat/multilingual-e5-small"

    def __init__(self, local_path="", revision="614241f622f53c4eeff9890bdc4f31cfecc418b3"):
        self.local_path = local_path
        self.revision = revision
        self.model = None
        self.lock = Lock()

    def encode(self, texts, *, query=False):
        if not self.local_path or not Path(self.local_path).is_dir():
            raise RagUnavailable("E5_LOCAL_WEIGHTS_MISSING")
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as e:
            raise RagUnavailable("E5_DEPENDENCIES_MISSING") from e
        try:
            with self.lock:
                if self.model is None:
                    import torch
                    torch.set_num_threads(4)
                    self.model = SentenceTransformer(self.local_path, device="cpu", local_files_only=True, trust_remote_code=False)
                    self.model.max_seq_length = 512
                prefix = "query: " if query else "passage: "
                return self.model.encode([prefix + t for t in texts], normalize_embeddings=True, batch_size=16, show_progress_bar=False).astype("float32")
        except Exception as e:
            raise RagUnavailable("E5_RUNTIME_UNAVAILABLE") from e
