"""Versioned FAISS artifact; corpus identity/permissions are verified before deserializing."""
import json
import hashlib
from pathlib import Path
from .config import GroundingError, RagUnavailable
from .knowledge import digest


class IndexStore:
    def __init__(self, directory, embedding):
        self.directory, self.embedding = Path(directory), embedding

    def identity(self, documents):
        if not documents or any(d["scope"] != "PUBLIC" for d in documents):
            raise GroundingError("PERSISTENT_INDEX_MUST_BE_PUBLIC")
        return {"format": "SMARTPROP_E5_FAISS_V1", "encoder": self.embedding.model_id,
                "encoderRevision": self.embedding.revision, "dimensions": 384,
                "normalization": "L2", "indexType": "IndexFlatIP", "prefixes": ["passage: ", "query: "],
                "documents": [{k: d[k] for k in ["sourceId", "version", "contentHash", "scope"]} for d in documents]}

    def build(self, documents):
        import faiss
        import numpy as np
        identity = self.identity(documents)
        version = digest(identity)
        vectors = self.embedding.encode([d["text"] for d in documents])
        if vectors.shape != (len(documents), 384) or not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
            raise GroundingError("INVALID_E5_VECTORS")
        index = faiss.IndexFlatIP(384)
        index.add(np.ascontiguousarray(vectors))
        self.directory.mkdir(parents=True, exist_ok=True)
        file = self.directory / (version + ".faiss")
        temporary = file.with_suffix(".tmp")
        faiss.write_index(index, str(temporary))
        sha = hashlib.sha256(temporary.read_bytes()).hexdigest()
        temporary.replace(file)
        manifest = {**identity, "version": version, "indexSha256": sha, "count": len(documents), "bytes": file.stat().st_size}
        target = self.directory / (version + ".json")
        temp_manifest = target.with_suffix(".tmp")
        temp_manifest.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")
        temp_manifest.replace(target)
        return manifest

    def load(self, documents):
        import faiss
        import numpy as np
        identity = self.identity(documents)
        version = digest(identity)
        file, meta = self.directory / (version + ".faiss"), self.directory / (version + ".json")
        try:
            if meta.stat().st_size > 2 * 1024 * 1024 or file.stat().st_size > 8 * 1024 * 1024:
                raise GroundingError("INVALID_INDEX_SIZE")
            manifest = json.loads(meta.read_text(encoding="utf-8"))
            if any(manifest.get(k) != v for k, v in identity.items()) or manifest.get("version") != version:
                raise GroundingError("INDEX_VERSION_DRIFT")
            if hashlib.sha256(file.read_bytes()).hexdigest() != manifest["indexSha256"]:
                raise GroundingError("INDEX_CHECKSUM_MISMATCH")
            index = faiss.read_index(str(file))
            if type(index).__name__ != "IndexFlatIP" or index.d != 384 or index.ntotal != len(documents):
                raise GroundingError("INDEX_MAPPING_MISMATCH")
            vectors = index.reconstruct_n(0, index.ntotal)
            if not np.isfinite(vectors).all() or not np.allclose(np.linalg.norm(vectors, axis=1), 1, atol=1e-4):
                raise GroundingError("INVALID_INDEX_VECTORS")
            return vectors, manifest
        except GroundingError as e:
            raise RagUnavailable("PERSISTENT_INDEX_INVALID") from e
        except (OSError, ValueError, KeyError, RuntimeError) as e:
            raise RagUnavailable("PERSISTENT_INDEX_UNAVAILABLE") from e
