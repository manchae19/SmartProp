"""Project classified facts from the input adapter and transform, never raw values."""

from dataclasses import dataclass
from enum import Enum

from .schema import FEATURES, MATRIX_STATES, SEGMENTS, InvalidTelemetry, approved_string


class InputMode(Enum):
    CANONICAL = "canonical"
    COMPAT_REAL = "compat_real"
    COMPAT_LEGACY = "compat_legacy"


class PropertyKind(Enum):
    HOUSE = "house"
    LAND = "land"
    APARTMENT = "apartment"
    VILLA = "villa"
    OTHER = "other"


class MatrixState(Enum):
    PRESENT = MATRIX_STATES[0]
    MISSING = MATRIX_STATES[1]
    INVALID = MATRIX_STATES[2]
    UNKNOWN = MATRIX_STATES[3]


class Provenance(Enum):
    UNSPECIFIED = "unspecified"
    USER_ASSERTED = "user_asserted"
    VERIFIED_SOURCE = "verified_source"
    DEFAULTED = "defaulted"


DERIVED = frozenset(feature for feature in FEATURES if feature.startswith("has_")) | {"frontage_sqrt_area_ratio"}
CATEGORICAL = frozenset(FEATURES[-7:])
LAND_NOT_APPLICABLE = frozenset((
    "floor_count", "bedroom_count", "bathroom_count", "has_floor", "has_bedroom", "has_bathroom",
    "raw_house_direction", "raw_balcony_direction",
))
PARCEL_FRONTAGE = frozenset(("frontage_width", "has_frontage", "frontage_sqrt_area_ratio"))
TYPE_DEPENDENT = LAND_NOT_APPLICABLE | PARCEL_FRONTAGE | {"raw_project_name", "has_project"}
DISTRICTS = frozenset(s.split(":", 1)[1] for s in SEGMENTS if s.startswith("district:"))


@dataclass(frozen=True, slots=True)
class FeatureFact:
    raw_present: bool
    matrix: MatrixState
    provenance: Provenance = Provenance.UNSPECIFIED

    def __post_init__(self):
        if type(self.raw_present) is not bool or type(self.matrix) is not MatrixState or type(self.provenance) is not Provenance:
            raise InvalidTelemetry("invalid_feature_fact")


def _report_state(feature, kind, matrix):
    if kind is PropertyKind.LAND and feature in LAND_NOT_APPLICABLE:
        return "not_applicable"
    if ((kind is PropertyKind.OTHER and feature in TYPE_DEPENDENT)
            or (kind is PropertyKind.APARTMENT and feature in PARCEL_FRONTAGE)):
        return "applicability_unknown"
    return matrix.value


def record_feature_facts(recorder, kind, mode, district, facts):
    """Call after the existing transform; facts follow the pinned 22-column order."""
    if not recorder.enabled:
        return False
    try:
        if (type(kind) is not PropertyKind or type(mode) is not InputMode or type(facts) is not tuple
                or len(facts) != len(FEATURES) or any(type(fact) is not FeatureFact for fact in facts)):
            raise InvalidTelemetry("invalid_feature_frame")
        district = district if approved_string(district) and district in DISTRICTS else "other"
        segments = (f"type:{kind.value}", f"district:{district}", f"input:{mode.value}")
        rows = []
        for feature, fact in zip(FEATURES, facts):
            derived = feature in DERIVED
            defaulted = fact.provenance is Provenance.DEFAULTED
            verified = fact.provenance is Provenance.VERIFIED_SOURCE
            if ((fact.matrix is MatrixState.UNKNOWN and feature not in CATEGORICAL)
                    or (feature.startswith("has_") and fact.matrix is not MatrixState.PRESENT)
                    or (derived and (fact.raw_present or fact.provenance is not Provenance.UNSPECIFIED))
                    or (verified and (not fact.raw_present or fact.matrix is not MatrixState.PRESENT))
                    or (defaulted and (fact.matrix is not MatrixState.PRESENT or not (
                        (feature == "normalized_type" and mode is not InputMode.CANONICAL)
                        or (mode is InputMode.COMPAT_LEGACY and feature in ("road_width", "frontage_width"))
                    )))):
                raise InvalidTelemetry("invalid_feature_provenance")
            unverified = not verified and not derived and (fact.raw_present or fact.matrix is MatrixState.PRESENT)
            rows.append((fact.matrix.value, _report_state(feature, kind, fact.matrix),
                         fact.raw_present, derived, defaulted, unverified))
    except InvalidTelemetry:
        recorder.drop("invalid")
        return False
    return recorder.feature_frame(tuple(rows), segments)
