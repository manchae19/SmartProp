"""Descriptive reference coverage, separate from model predictions/confidence."""
import hashlib
import json
import math
from pathlib import Path

from app.core.model_registry import V6_RUN, V6_MANIFEST_SHA256

PROFILE_PATH = Path(__file__).with_name("reference_support_v6.json")
PROFILE_SHA256 = "497765c4226df7b52fcd71d24d37b2e3af2082b71d7c092cd87110d7dd9a0217"
PROFILE_VERSION = "v6_clean_reference_support_1"
UNAVAILABLE = "Chưa có thống kê độ phủ dữ liệu tham chiếu phù hợp để đánh giá đầu vào này."


def _integer(value):
    return isinstance(value, int) and not isinstance(value, bool) and value > 0


def load_profile(path, expected_sha, model_run, model_manifest_sha):
    try:
        raw = Path(path).read_bytes()
        if hashlib.sha256(raw).hexdigest() != expected_sha:
            return None
        value = json.loads(raw)
        if (value["version"] != PROFILE_VERSION or value["model_run"] != model_run
                or value["model_manifest_sha256"] != model_manifest_sha):
            return None
        if value["policy"] != dict(low_reference_groups_below=10, area_percentiles=[.05, .95], minimum_groups_for_area_range=10):
            return None
        if not _integer(value["reference_groups"]):
            return None
        categories = value["categories"]
        if set(categories) != {"Nhà ở", "Đất nền", "Căn hộ chung cư"}:
            return None
        total = 0
        for locations in categories.values():
            if not isinstance(locations, dict):
                return None
            for location, cell in locations.items():
                count = cell["reference_groups"]
                if not isinstance(location, str) or not location or not _integer(count):
                    return None
                total += count
                area = cell["area_percentiles_sqm"]
                if count < 10:
                    if area is not None:
                        return None
                elif (not isinstance(area, dict) or set(area) != {"p05", "p95"}
                      or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or v <= 0 for v in area.values())
                      or area["p05"] > area["p95"]):
                    return None
        return value if total == value["reference_groups"] else None
    except (OSError, ValueError, TypeError, KeyError, AttributeError):
        return None


class ReferenceSupport:
    def __init__(self, *, path=None, expected_sha=None, model_run=V6_RUN, model_manifest_sha=V6_MANIFEST_SHA256):
        self.profile = load_profile(path or PROFILE_PATH, expected_sha or PROFILE_SHA256, model_run, model_manifest_sha)

    def warnings(self, category, location, area_sqm):
        if self.profile is None:
            return [UNAVAILABLE]
        cell = self.profile["categories"].get(category, {}).get(location)
        if cell is None:
            return [UNAVAILABLE]
        count = cell["reference_groups"]
        if count < 10:
            return [f"Loại bất động sản tại địa bàn này chỉ có {count} nhóm trong bộ dữ liệu tham chiếu sạch; kết quả có thể có sai số lớn."]
        area = cell["area_percentiles_sqm"]
        if not area["p05"] <= area_sqm <= area["p95"]:
            return [f"Diện tích nằm ngoài khoảng phổ biến của {count} nhóm tham chiếu cùng loại tại địa bàn này; kết quả có thể có sai số lớn."]
        return []
