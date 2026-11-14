"""Build a versioned FAISS index from an existing verified corpus and local CPU E5 weights."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.embedding import E5Embedding
from app.rag.index_store import IndexStore
from app.rag.knowledge import KnowledgeStore


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--corpus", type=Path, required=True)
    parser.add_argument("--e5-path", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    corpus = KnowledgeStore(args.corpus).load()
    store = IndexStore(args.output, E5Embedding(args.e5_path))
    manifest = store.build(corpus["documents"])
    store.load(corpus["documents"])
    print(json.dumps({k: manifest[k] for k in ["version", "count", "dimensions", "bytes", "indexSha256", "encoderRevision"]}))


if __name__ == "__main__":
    main()
