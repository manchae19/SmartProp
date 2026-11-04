"""Notebook cell 6: filter permission first, IndexFlatIP over normalized E5 vectors."""
from threading import Lock
from .config import RagUnavailable
from .index_store import IndexStore


class FaissRetriever:
    def __init__(self, embedding, index_dir=None):
        self.embedding = embedding
        self._vectors = {}
        self._lock = Lock()
        self.store = IndexStore(index_dir, embedding) if index_dir else None
        self.manifest = None

    def search(self, question, documents, *, internal=False, district=None, categories=None, k=4):
        # No global mixed-access index. Research documents never enter the public corpus.
        valid = [d for d in documents if d["scope"] == "PUBLIC" or internal]
        if district:
            valid = [d for d in valid if d["metadata"].get("district") == district]
        if categories:
            # Explicit POI category is a HARD filter applied BEFORE any vector search.
            # Similarity may only rank inside this eligible set; it never widens category.
            valid = [d for d in valid if d["kind"] == "POI_EVIDENCE"
                     and d["metadata"].get("category") in categories]
        if not valid:
            return []
        try:
            import faiss
            import numpy as np
        except ImportError as e:
            raise RagUnavailable("FAISS_DEPENDENCIES_MISSING") from e
        key = tuple((d["sourceId"], d["version"]) for d in valid)
        with self._lock:
            if self.store:
                # Persistent index is PUBLIC only. Filter BEFORE constructing/searching the request index.
                public = [d for d in documents if d["scope"] == "PUBLIC"]
                all_key = tuple((d["sourceId"], d["version"]) for d in public)
                if all_key not in self._vectors:
                    values, self.manifest = self.store.load(public)
                    self._vectors = {all_key: values}
                lookup = {d["sourceId"]: i for i, d in enumerate(public)}
                if any(d["sourceId"] not in lookup for d in valid):
                    raise RagUnavailable("RESEARCH_DOCUMENTS_NOT_IN_PUBLIC_INDEX")
                vectors = self._vectors[all_key][[lookup[d["sourceId"]] for d in valid]]
            else:
                if key not in self._vectors:
                    self._vectors = {key: self.embedding.encode([d["text"] for d in valid])}
                vectors = self._vectors[key]
        index = faiss.IndexFlatIP(vectors.shape[1])
        index.add(np.ascontiguousarray(vectors))
        query = self.embedding.encode([question], query=True)
        scores, indices = index.search(query, min(k, len(valid)))
        return [{**valid[int(i)], "similarity": float(s)} for s, i in zip(scores[0], indices[0]) if i >= 0]
