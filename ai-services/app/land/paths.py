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


def land_enabled():
    """Fail closed when the optional land dataset is disabled or not installed."""
    if os.getenv("RAG_LAND_ENABLED", "auto").lower() in ("false", "0", "off"):
        return False
    required = (
        "outputs/hoa-xuan-map-rebuild-20261122/map-grounded-catalog.json",
        "outputs/plot-display-labels.json",
        "outputs/hoa-xuan-enriched-20261122/runtime-cells.json",
        "outputs/hoa-xuan-projects-20261125/projects.json",
        "outputs/afternoon-import-20261125/manifest.json",
        "outputs/afternoon-import-20261125/parcel-records.json",
        "outputs/afternoon-import-20261125/project-candidates.json",
        "outputs/hoa-xuan-projects-20261125/unified-lots.json",
        "outputs/hoa-xuan-enriched-20261122/cells.json",
        "outputs/hoa-xuan-enriched-20261122/plans.json",
        "outputs/hoa-xuan-map-rebuild-20261122/raw/layer-4-metadata.json",
        "outputs/hoa-xuan-road-prices-20261124/cell-reference-estimates.json",
        "flood/flood-catalog-full.json",
        "flood/flood-admin-mapping.json",
        "flood/flood-map-context.geojson",
    )
    return all((DATA_ROOT / item).is_file() for item in required)
