"""Versioned, closed vocabulary for rollups. Slots are fixed by schema version."""

from dataclasses import dataclass
from itertools import product
from types import MappingProxyType


VERSION = 2
RELEASE = 1  # Registry entry for V1.3: tinix_xgboost_v1_3_integrated.
MAX_SERIES = 4096
MAX_VALUE = (1 << 53) - 1
MAX_DURATION_US = 3_600_000_000
MAX_LABEL = 40
SURFACES = ("standalone", "posting", "advisor")
FEATURES = (
    "area", "floor_count", "frontage_width", "road_width", "bedroom_count", "bathroom_count",
    "has_floor", "has_frontage", "has_road_width", "has_bedroom", "has_bathroom", "has_project",
    "has_street", "has_ward", "frontage_sqrt_area_ratio", "normalized_type", "district", "ward",
    "raw_street_name", "raw_project_name", "raw_house_direction", "raw_balcony_direction",
)
SEGMENTS = (
    "global", *(f"surface:{v}" for v in SURFACES),
    *(f"type:{v}" for v in ("house", "villa", "land", "apartment", "other")),
    *(f"district:{v}" for v in ("cam_le", "hoa_vang", "hai_chau", "lien_chieu",
                                 "ngu_hanh_son", "son_tra", "thanh_khe", "other")),
    *(f"input:{v}" for v in ("canonical", "compat_real", "compat_legacy")),
)
EFFECTIVE = ("present", "missing", "invalid", "unknown", "not_applicable", "applicability_unknown")
OUTCOMES = MappingProxyType({
    "surface": ("served", "no_point", "validation_rejection", "timeout", "cancelled",
                "dependency_unavailable", "failed", "interrupted"),
    "opportunity": ("valid_point", "cache_hit", "skip", "validation_rejection", "timeout",
                    "cancelled", "dependency_unavailable", "failed", "interrupted"),
    "candidate": ("eligible", "skip", "interrupted"),
    "dispatch": ("ai_response", "timeout", "cancelled", "dependency_unavailable", "failed", "interrupted"),
    "invocation": ("valid_point", "invalid_output", "inference_exception", "interrupted"),
})
STAGES = ("feature_prep", "point", "calibration", "explanation", "interval", "model_load", "options", "health")
DROP_REASONS = ("invalid", "numeric_overflow", "lock_busy", "active_limit", "queue_full", "batch_rejected")
EXPLANATION_STATES = ("available", "partial", "not_available", "not_supported", "not_enabled")
INTERVAL_STATES = ("available", "not_enabled", "not_available", "not_supported", "insufficient_calibration", "invalid_bounds")
LATENCY_EDGES = (10_000, 25_000, 50_000, 100_000, 200_000, 500_000, 1_000_000, 5_000_000, 15_000_000)
WIDTH_EDGES = (100_000_000, 500_000_000, 1_000_000_000, 2_000_000_000, 5_000_000_000)
RELATIVE_EDGES = (50_000, 100_000, 200_000, 500_000, 1_000_000, 2_000_000)


def integer(value, maximum=MAX_VALUE):
    return type(value) is int and 0 <= value <= maximum


def approved_string(value):
    return type(value) is str and 0 < len(value) <= MAX_LABEL


class InvalidTelemetry(ValueError):
    """The message is a static reason code. Never attach input values."""


@dataclass(frozen=True, slots=True)
class Metric:
    name: str
    kind: str
    unit: str
    labels: tuple
    edges: tuple = ()
    maximum: int = MAX_VALUE
    managed: bool = False


@dataclass(frozen=True, slots=True)
class Series:
    metric: Metric
    labels: tuple
    offset: int
    width: int


class Registry:
    __slots__ = ("_series", "_size")

    def __init__(self, metrics, *, capacity=MAX_SERIES):
        if not integer(capacity, MAX_SERIES) or not capacity:
            raise InvalidTelemetry("registry_capacity")
        offsets = {}
        names = set()
        count = 0
        for metric in metrics:
            self._validate(metric)
            if metric.name in names:
                raise InvalidTelemetry("duplicate_metric")
            names.add(metric.name)
            width = 1 if metric.kind != "histogram" else len(metric.edges) + 3
            for labels in product(*(values for _, values in metric.labels)):
                if count + width > capacity:
                    raise InvalidTelemetry("registry_capacity")
                offsets[metric.name, labels] = Series(metric, labels, count, width)
                count += width
        self._series = MappingProxyType(offsets)
        self._size = count

    @property
    def series(self):
        return self._series

    @property
    def size(self):
        return self._size

    @staticmethod
    def _validate(metric):
        if (type(metric) is not Metric or not approved_string(metric.name)
                or type(metric.kind) is not str or metric.kind not in ("counter", "gauge", "histogram")
                or type(metric.unit) is not str or metric.unit not in ("count", "us", "vnd", "ppm")
                or not integer(metric.maximum) or type(metric.labels) is not tuple or len(metric.labels) > 3
                or type(metric.edges) is not tuple or type(metric.managed) is not bool):
            raise InvalidTelemetry("metric_definition")
        names = set()
        for pair in metric.labels:
            if type(pair) is not tuple or len(pair) != 2:
                raise InvalidTelemetry("label_definition")
            name, values = pair
            if (not approved_string(name) or name in names or type(values) is not tuple or not values
                    or len(values) > MAX_SERIES or any(not approved_string(v) for v in values)
                    or len(set(values)) != len(values)):
                raise InvalidTelemetry("label_definition")
            names.add(name)
        if metric.kind == "histogram":
            if (not 1 <= len(metric.edges) <= 32
                    or any(not integer(edge, metric.maximum) for edge in metric.edges)
                    or any(a >= b for a, b in zip(metric.edges, metric.edges[1:]))):
                raise InvalidTelemetry("histogram_edges")
        elif metric.edges or metric.unit != "count":
            raise InvalidTelemetry("metric_definition")

    def find(self, name, labels):
        if (not approved_string(name) or type(labels) is not tuple or len(labels) > 3
                or any(not approved_string(value) for value in labels)):
            raise InvalidTelemetry("unregistered_series")
        result = self.series.get((name, labels))
        if result is None:
            raise InvalidTelemetry("unregistered_series")
        return result


def valuation_metrics():
    surface = ("surface", SURFACES)
    for kind, outcomes in OUTCOMES.items():
        for event in ("started", "completed", "lost_terminal", "outcome", "in_flight", "opening_in_flight"):
            labels = (surface, ("outcome", outcomes)) if event == "outcome" else (surface,)
            metric_kind = "gauge" if event.endswith("in_flight") else "counter"
            yield Metric(f"{kind}_{event}", metric_kind, "count", labels, managed=True)
        yield Metric(f"{kind}_latency", "histogram", "us", (surface,), LATENCY_EDGES,
                     MAX_DURATION_US, managed=True)
    yield Metric("telemetry_drop", "counter", "count", (("reason", DROP_REASONS),), managed=True)
    yield Metric("duplicate_completion", "counter", "count", (), managed=True)
    yield Metric("retry", "counter", "count", (surface, ("reason", ("transport", "auth"))))
    yield Metric("skip", "counter", "count",
                 (surface, ("reason", ("opt_out", "research", "unsupported", "incomplete"))))
    yield Metric("cache_lookup", "counter", "count", (surface, ("result", ("hit", "miss", "error"))))
    yield Metric("probe", "counter", "count",
                 (surface, ("probe", ("health", "options")), ("result", ("ready", "not_ready", "failed"))))
    yield Metric("model_integrity", "counter", "count", (("result", (
        "ready", "missing_file", "hash_mismatch", "schema_mismatch", "calibration_mismatch",
        "load_error", "release_mismatch", "unsupported_version",
    )),))
    yield Metric("stage_latency", "histogram", "us",
                 (surface, ("stage", STAGES)), LATENCY_EDGES, MAX_DURATION_US)
    feature = ("feature", FEATURES)
    yield Metric("feature_effective", "counter", "count",
                 (feature, ("state", EFFECTIVE), ("segment", SEGMENTS)), managed=True)
    yield Metric("feature_raw", "counter", "count",
                 (feature, ("presence", ("present", "absent"))), managed=True)
    yield Metric("feature_provenance", "counter", "count",
                 (feature, ("axis", ("derived", "defaulted", "unverified")), ("observed", ("yes", "no"))),
                 managed=True)
    yield Metric("explanation_status", "counter", "count", (surface, ("state", EXPLANATION_STATES)), managed=True)
    yield Metric("explanation_contract", "counter", "count",
                 (surface, ("contract", ("wp04_v1", "absent", "mismatch")),
                  ("check", ("passed", "failed", "not_checked"))), managed=True)
    yield Metric("explanation_provenance", "counter", "count",
                 (surface, ("origin", ("provided", "derived", "assumed", "missing", "unknown", "not_applicable"))),
                 managed=True)
    yield Metric("interval_status", "counter", "count", (surface, ("state", INTERVAL_STATES)), managed=True)
    yield Metric("interval_scope", "counter", "count",
                 (surface, ("scope", ("group", "global", "global_fallback"))), managed=True)
    yield Metric("interval_width", "histogram", "vnd", (surface,), WIDTH_EDGES, managed=True)
    yield Metric("interval_relative_width", "histogram", "ppm", (surface,), RELATIVE_EDGES,
                 MAX_VALUE, managed=True)


REGISTRY = Registry(valuation_metrics())


@dataclass(frozen=True, slots=True)
class LifecycleSeries:
    started: int
    completed: int
    lost: int
    opening: int
    active: int
    outcomes: MappingProxyType
    latency: Series


LIFECYCLE = MappingProxyType({
    (kind, surface): LifecycleSeries(
        REGISTRY.find(f"{kind}_started", (surface,)).offset,
        REGISTRY.find(f"{kind}_completed", (surface,)).offset,
        REGISTRY.find(f"{kind}_lost_terminal", (surface,)).offset,
        REGISTRY.find(f"{kind}_opening_in_flight", (surface,)).offset,
        REGISTRY.find(f"{kind}_in_flight", (surface,)).offset,
        MappingProxyType({outcome: REGISTRY.find(f"{kind}_outcome", (surface, outcome)).offset
                          for outcome in outcomes}),
        REGISTRY.find(f"{kind}_latency", (surface,)),
    )
    for kind, outcomes in OUTCOMES.items() for surface in SURFACES
})
