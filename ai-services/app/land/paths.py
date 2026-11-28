"""Where the Hòa Xuân land demo reads its data.

The engine never writes here. The directory is a versioned, unchanged copy of the source
files (see SMARTPROP_DATA/pipelines/land_demo/README.md). Point SMARTPROP_LAND_DATA_DIR at
another version to swap data without touching the chatbot.
"""
import hashlib
import hmac
import json
import os
from pathlib import Path

DATA_VERSION = os.environ.get("SMARTPROP_LAND_DATA_VERSION", "HX-LAND-DEMO-20261126")
_REPO = Path(__file__).resolve().parents[3]
DATA_ROOT = Path(os.environ.get("SMARTPROP_LAND_DATA_DIR") or _REPO / "SMARTPROP_DATA" / "raw" / "land_demo_hoa_xuan" / DATA_VERSION)
FLOOD_DIR = DATA_ROOT / "flood"
PROCESSED_DIR = Path(os.environ.get("SMARTPROP_LAND_PROCESSED_DIR") or _REPO / "SMARTPROP_DATA" / "processed" / "land_demo_hoa_xuan" / DATA_VERSION)

REQUIRED_RAW_FILES = (
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


def _truthy(name: str) -> bool:
    return os.getenv(name, "false").strip().lower() in ("true", "1", "on")


def _norm_rel(rel: str) -> str:
    return rel.replace("\\", "/").lstrip("/")


def verify_land_dataset(data_root: Path | None = None, processed_dir: Path | None = None, version: str | None = None) -> dict:
    """Fail-closed provenance and governance verification for Hòa Xuân land datasets.

    File presence alone never activates the land routes:
    1. `RAG_LAND_ENABLED` must be explicitly `true` (default `false`).
    2. All required raw files and provenance manifests must exist and parse cleanly.
    3. `processed_dir / manifest.json` must match `version` and SHA-256 hashes of required raw files.
    4. Public activation requires `publicApproved=True`, `containsSyntheticData=False`, and a non-empty
       `rightsApprovalRef`. Synthetic demo datasets fail closed unless `RAG_LAND_DEMO_ENABLED=true`
       and `demoApproved=True` (never fabricating rights approvals).
    """
    if not _truthy("RAG_LAND_ENABLED"):
        return {"ok": False, "mode": "DISABLED", "reasons": ["RAG_LAND_ENABLED_NOT_TRUE"]}

    expected_version = version or os.environ.get("SMARTPROP_LAND_DATA_VERSION", DATA_VERSION)
    raw_dir = Path(data_root) if data_root is not None else (
        Path(os.environ["SMARTPROP_LAND_DATA_DIR"]) if os.environ.get("SMARTPROP_LAND_DATA_DIR") else DATA_ROOT
    )
    proc_dir = Path(processed_dir) if processed_dir is not None else (
        Path(os.environ["SMARTPROP_LAND_PROCESSED_DIR"]) if os.environ.get("SMARTPROP_LAND_PROCESSED_DIR") else PROCESSED_DIR
    )

    missing = [item for item in REQUIRED_RAW_FILES if not (raw_dir / item).is_file()]
    if missing:
        return {"ok": False, "mode": "BLOCKED", "reasons": ["MISSING_RAW_FILES", *missing[:5]]}

    try:
        import_manifest = json.loads((raw_dir / "outputs/afternoon-import-20261125/manifest.json").read_text(encoding="utf-8"))
        flood_catalog = json.loads((raw_dir / "flood/flood-catalog-full.json").read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"ok": False, "mode": "BLOCKED", "reasons": ["INVALID_RAW_PROVENANCE_JSON"]}

    if not isinstance(import_manifest, dict) or not import_manifest:
        return {"ok": False, "mode": "BLOCKED", "reasons": ["EMPTY_IMPORT_PROVENANCE"]}
    if not isinstance(flood_catalog, dict) or not flood_catalog.get("commit") or not isinstance(flood_catalog.get("records"), list):
        return {"ok": False, "mode": "BLOCKED", "reasons": ["INVALID_FLOOD_CATALOG_PROVENANCE"]}

    manifest_file = proc_dir / "manifest.json"
    if not manifest_file.is_file():
        return {"ok": False, "mode": "BLOCKED", "reasons": ["MISSING_DATASET_MANIFEST"]}

    try:
        manifest = json.loads(manifest_file.read_text(encoding="utf-8"))
    except (OSError, ValueError, TypeError):
        return {"ok": False, "mode": "BLOCKED", "reasons": ["INVALID_DATASET_MANIFEST"]}

    if not isinstance(manifest, dict) or manifest.get("version") != expected_version:
        return {"ok": False, "mode": "BLOCKED", "reasons": ["MANIFEST_VERSION_MISMATCH"]}

    sources = manifest.get("sources")
    if not isinstance(sources, list) or not sources:
        return {"ok": False, "mode": "BLOCKED", "reasons": ["MANIFEST_SOURCES_MISSING"]}

    by_path = {
        _norm_rel(str(entry.get("path", ""))): entry.get("sha256")
        for entry in sources
        if isinstance(entry, dict) and entry.get("path") and isinstance(entry.get("sha256"), str)
    }
    for rel in REQUIRED_RAW_FILES:
        expected_sha = by_path.get(_norm_rel(rel))
        if not expected_sha:
            return {"ok": False, "mode": "BLOCKED", "reasons": ["MANIFEST_MISSING_REQUIRED_HASH", rel]}
        actual_sha = hashlib.sha256((raw_dir / rel).read_bytes()).hexdigest()
        if actual_sha != expected_sha:
            return {"ok": False, "mode": "BLOCKED", "reasons": ["RAW_FILE_HASH_MISMATCH", rel]}

    if manifest.get("publicApproved") is True:
        # The current Hòa Xuân engine synthesizes demo unit prices and scenario assumptions.
        # Block PUBLIC_APPROVED activation fail-closed until a zero-synthetic public engine exists.
        return {"ok": False, "mode": "UNSUPPORTED_PUBLIC_APPROVED", "reasons": ["PUBLIC_APPROVED_ENGINE_NOT_IMPLEMENTED"]}

    if _truthy("RAG_LAND_DEMO_ENABLED") and manifest.get("demoApproved") is True and manifest.get("containsSyntheticData") is not False:
        return {"ok": True, "mode": "SYNTHETIC_DEMO", "reasons": []}

    return {"ok": False, "mode": "BLOCKED", "reasons": ["DATASET_USAGE_NOT_APPROVED"]}


def demo_key_configured(demo_key: str | None = None) -> bool:
    key = (demo_key if demo_key is not None else os.getenv("RAG_DEMO_KEY", "")).strip()
    return len(key) >= 16


def land_runtime_mode(data_root: Path | None = None, processed_dir: Path | None = None,
                      version: str | None = None, *, demo_key: str | None = None) -> str:
    """Return active land runtime mode: `'SYNTHETIC_DEMO'` or `'DISABLED'`.

    Never collapses public vs synthetic demo modes into an undifferentiated boolean, and
    requires an explicit server-side demo key (`>= 16` chars) before synthetic demo mode can arm.
    """
    status = verify_land_dataset(data_root=data_root, processed_dir=processed_dir, version=version)
    if status.get("ok") and status.get("mode") == "SYNTHETIC_DEMO" and demo_key_configured(demo_key):
        return "SYNTHETIC_DEMO"
    return "DISABLED"


def authorize_land_demo_request(headers, client_host: str | None, expected_demo_key: str | None = None) -> bool:
    """Enforce internal loopback + constant-time `X-SmartProp-Demo-Key` boundary on every request."""
    if client_host not in ("127.0.0.1", "::1"):
        return False
    expected = (expected_demo_key if expected_demo_key is not None else os.getenv("RAG_DEMO_KEY", "")).strip()
    if len(expected) < 16 or headers is None:
        return False
    # Reject proxied external requests even if the reverse proxy sits on 127.0.0.1.
    if headers.get("forwarded") or headers.get("x-forwarded-host"):
        return False
    xff = (headers.get("x-forwarded-for") or "").strip()
    if xff:
        hops = [h.strip() for h in xff.split(",") if h.strip()]
        if any(h not in ("127.0.0.1", "::1") for h in hops):
            return False
    real_ip = (headers.get("x-real-ip") or "").strip()
    if real_ip and real_ip not in ("127.0.0.1", "::1"):
        return False
    provided = (headers.get("x-smartprop-demo-key") or "").strip()
    if not provided:
        return False
    return hmac.compare_digest(provided.encode("utf-8"), expected.encode("utf-8"))


def land_enabled() -> bool:
    """True only when isolated SYNTHETIC_DEMO mode and server demo key are both configured."""
    return land_runtime_mode() == "SYNTHETIC_DEMO"
