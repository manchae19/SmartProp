"""Where the Hòa Xuân land demo reads its data.

The engine never writes here. The directory is a versioned, unchanged copy of the source
files (see SMARTPROP_DATA/pipelines/land_demo/README.md). Point SMARTPROP_LAND_DATA_DIR at
another version to swap data without touching the chatbot.
"""
import os
from pathlib import Path

DATA_VERSION = os.environ.get("SMARTPROP_LAND_DATA_VERSION", "HX-LAND-DEMO-20261126")
_REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.environ.get("SMARTPROP_LAND_DATA_DIR") or _REPO / "SMARTPROP_DATA" / "raw" / "land_demo_hoa_xuan" / DATA_VERSION)
FLOOD_DIR = DATA_ROOT / "flood"
PROCESSED_DIR = Path(os.environ.get("SMARTPROP_LAND_PROCESSED_DIR") or _REPO / "SMARTPROP_DATA" / "processed" / "land_demo_hoa_xuan" / DATA_VERSION)
