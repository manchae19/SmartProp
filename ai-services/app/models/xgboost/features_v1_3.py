"""Tabular feature definitions and preprocessing for XGBoost V1.3.

Provides self-contained, high-performance feature transformation matching
the frozen training schema (V1.3 Multi-Source + Duan Smearing).
"""
import math
import unicodedata
from typing import Any, Dict

import numpy as np
import pandas as pd

BASE_NUMERIC = ["area", "floor_count", "frontage_width", "road_width", "bedroom_count", "bathroom_count"]
INDICATORS = [
    "has_floor", "has_frontage", "has_road_width", "has_bedroom",
    "has_bathroom", "has_project", "has_street", "has_ward"
]
RATIO_FEATURES = ["frontage_sqrt_area_ratio"]
NUMERIC_FEATURES = BASE_NUMERIC + INDICATORS + RATIO_FEATURES

CATEGORICAL_FEATURES = [
    "normalized_type", "district", "ward",
    "raw_street_name", "raw_project_name",
    "raw_house_direction", "raw_balcony_direction"
]

ALL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES

LIMITS = {
    "area": (5.0, 50_000.0),
    "floor_count": (0.0, 100.0),
    "frontage_width": (0.0, 500.0),
    "road_width": (0.0, 100.0),
    "bedroom_count": (0.0, 100.0),
    "bathroom_count": (0.0, 100.0)
}


def clean_category(value: Any) -> str:
    """Normalize categorical string values to NFC lowercase."""
    if value is None or pd.isna(value):
        return "__MISSING__"
    s = str(value).strip()
    if not s or s.lower() in ("none", "nan", ""):
        return "__MISSING__"
    return unicodedata.normalize("NFC", s).casefold()


def clean_numeric(value: Any, field: str) -> float:
    """Validate and clean numeric values against physical plausibility bounds."""
    try:
        x = float(value)
    except (TypeError, ValueError, OverflowError):
        return np.nan
    low, high = LIMITS[field]
    return x if math.isfinite(x) and low <= x <= high else np.nan


def transform(df: pd.DataFrame, schema: Dict[str, Any]) -> pd.DataFrame:
    """Transform input property record(s) into model feature matrix."""
    out = pd.DataFrame(index=df.index)

    # 1. Base numeric
    field_map = {
        "area": "area",
        "floor_count": "raw_floor_count",
        "frontage_width": "raw_frontage_width",
        "road_width": "raw_road_width",
        "bedroom_count": "raw_bedroom_count",
        "bathroom_count": "raw_bathroom_count"
    }

    for feature_name, source_col in field_map.items():
        if source_col in df.columns:
            out[feature_name] = df[source_col].map(lambda v: clean_numeric(v, feature_name)).astype("float32")
        else:
            out[feature_name] = np.nan

    # 2. Missing indicators
    out["has_floor"] = (~out["floor_count"].isna()).astype("float32")
    out["has_frontage"] = (~out["frontage_width"].isna()).astype("float32")
    out["has_road_width"] = (~out["road_width"].isna()).astype("float32")
    out["has_bedroom"] = (~out["bedroom_count"].isna()).astype("float32")
    out["has_bathroom"] = (~out["bathroom_count"].isna()).astype("float32")

    out["has_project"] = df["raw_project_name"].map(
        lambda v: 0.0 if v is None or pd.isna(v) or str(v).strip() in ("", "None", "nan") else 1.0
    ).astype("float32")

    out["has_street"] = df["raw_street_name"].map(
        lambda v: 0.0 if v is None or pd.isna(v) or str(v).strip() in ("", "None", "nan") else 1.0
    ).astype("float32")

    out["has_ward"] = df["ward"].map(
        lambda v: 0.0 if v is None or pd.isna(v) or str(v).strip() in ("", "None", "nan") else 1.0
    ).astype("float32")

    # 3. Geometric ratios
    area_sqrt = np.sqrt(np.maximum(out["area"].to_numpy(), 1.0))
    frontage_val = out["frontage_width"].to_numpy()
    ratio = np.where(~np.isnan(frontage_val), frontage_val / area_sqrt, np.nan)
    out["frontage_sqrt_area_ratio"] = ratio.astype("float32")

    # 4. Categoricals
    vocabularies = schema["vocabularies"]
    for col in CATEGORICAL_FEATURES:
        src = df[col] if col in df.columns else pd.Series(index=df.index, data="__MISSING__")
        cleaned = src.map(clean_category)
        known = set(vocabularies[col])
        mapped = cleaned.map(lambda x: x if x in known or x == "__MISSING__" else "__UNKNOWN__")
        levels = vocabularies[col] + ["__MISSING__", "__UNKNOWN__"]
        out[col] = pd.Categorical(mapped, categories=levels)

    return out[ALL_FEATURES]
