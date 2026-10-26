"""Reviewed display labels, independent of frozen training vocabularies."""
import json
from pathlib import Path

CATALOG = json.loads(Path(__file__).with_name("location_catalog_v6.json").read_text(encoding="utf-8"))
LOCATION_LABELS = {
    **CATALOG["legacy"],
    **{code: name + " (địa bàn mở rộng)" for code, name in CATALOG["expanded"].items()},
}
if set(LOCATION_LABELS) & set(CATALOG["blocked"]):
    raise ValueError("Địa bàn bị chặn không được nằm trong danh sách công khai.")
