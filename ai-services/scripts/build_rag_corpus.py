"""Explicit local corpus snapshot from the real PUBLIC Amenity Evidence API."""
import argparse
import json
from pathlib import Path
import sys
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.rag.config import Settings
from app.rag.knowledge import build_corpus
from app.rag.tools import BackendTools


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    tools = BackendTools(Settings())
    try:
        corpus = build_corpus(tools, args.output)
    finally:
        tools.close()
    print(json.dumps({"documents": len(corpus["documents"]), "summary": corpus["summary"],
                      "contentHash": corpus["contentHash"]}, default=str, ensure_ascii=False))


if __name__ == "__main__":
    main()
