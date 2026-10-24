"""Explicit release pin; future training runs do not change the API model."""
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[1] / "data"
SERVICE_DIR = Path(__file__).resolve().parents[2]
V6_RUN = "b4b1339d3f35857e"
V6_MANIFEST_SHA256 = "6e8c8cb6351b19245bf7e9c70698f786f19c8f8b6deff0d8f161f670569ccba1"
V6_MODEL_DIR = SERVICE_DIR / "artifacts" / "v6"
