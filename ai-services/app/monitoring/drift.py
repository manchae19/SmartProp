"""Fixed-reference comparisons over bounded aggregate counts. Synthetic only."""

from dataclasses import dataclass
from math import log, log2

from .accumulator import Availability, WINDOW_SECONDS, boundary
from .batches import HISTORICAL, POPULATIONS, SYNTHETIC
from .input_quality import InputMode
from .reducer import Coverage
from .schema import InvalidTelemetry, MAX_VALUE, RELEASE, VERSION, integer


DUAN_V13 = 1
PRICE_EDGES_VND = tuple(n * 1_000_000_000 for n in (0, 1, 2, 3, 4, 5, 6, 8, 10, 20, 50))
PROPERTY_BUCKETS = ("house", "land", "apartment", "villa", "unknown")


@dataclass(frozen=True, slots=True)
class ReferenceKey:
    release: int
    schema: int
    calibration: int
    mode: InputMode
    population: int
    version: int

    def __post_init__(self):
        if (any(not integer(value) or not value for value in (self.release, self.schema, self.calibration, self.version))
                or type(self.mode) is not InputMode or not integer(self.population, HISTORICAL)
                or self.population not in POPULATIONS):
            raise InvalidTelemetry("invalid_reference_key")


@dataclass(frozen=True, slots=True)
class Counts:
    prices: tuple
    property_types: tuple
    applicable: int
    missing: int
    unknown: int

    def __post_init__(self):
        for values, size in ((self.prices, len(PRICE_EDGES_VND) - 1), (self.property_types, len(PROPERTY_BUCKETS))):
            if (type(values) is not tuple or len(values) != size
                    or any(not integer(value) for value in values) or sum(values) > MAX_VALUE):
                raise InvalidTelemetry("invalid_distribution")
        if (any(not integer(value) for value in (self.applicable, self.missing, self.unknown))
                or self.missing + self.unknown > self.applicable):
            raise InvalidTelemetry("invalid_feature_rates")

    @property
    def n(self):
        return min(sum(self.prices), sum(self.property_types), self.applicable)


@dataclass(frozen=True, slots=True)
class Reference:
    key: ReferenceKey
    counts: Counts
    approved: bool = False

    def __post_init__(self):
        if type(self.key) is not ReferenceKey or type(self.counts) is not Counts or type(self.approved) is not bool:
            raise InvalidTelemetry("invalid_reference")


@dataclass(frozen=True, slots=True)
class DriftWindow:
    key: ReferenceKey
    start: int
    counts: Counts
    coverage: Coverage

    def __post_init__(self):
        if (type(self.key) is not ReferenceKey or type(self.counts) is not Counts or not boundary(self.start)
                or type(self.coverage) is not Coverage or type(self.coverage.window_end) is not int
                or self.coverage.window_end != self.start + WINDOW_SECONDS):
            raise InvalidTelemetry("invalid_drift_window")


@dataclass(frozen=True, slots=True)
class DriftResult:
    status: Availability
    missing_delta: float | None = None
    unknown_rate: float | None = None
    unknown_delta: float | None = None
    categorical_js: float | None = None
    histogram_psi: float | None = None
    histogram_js: float | None = None
    w1_vnd: float | None = None
    w1_error_bound_vnd: float | None = None
    ks_bin_edges: float | None = None


def _probabilities(counts, smoothing=0):
    total = sum(counts) + smoothing * len(counts)
    return tuple((value + smoothing) / total for value in counts)


def _js(p, q):
    result = 0.0
    for a, b in zip(p, q):
        mean = (a + b) / 2
        if a:
            result += a * log2(a / mean) / 2
        if b:
            result += b * log2(b / mean) / 2
    return max(0.0, min(1.0, result))


def compare(window, reference, *, now, max_age, min_samples=100, enabled=False):
    if type(enabled) is not bool:
        raise InvalidTelemetry("invalid_drift_flag")
    if not enabled:
        return DriftResult(Availability.NOT_ENABLED)
    if type(window) is not DriftWindow or type(reference) is not Reference:
        raise InvalidTelemetry("invalid_drift_input")
    key = window.key
    if (not reference.approved or key != reference.key or key.population != SYNTHETIC
            or (key.release, key.schema, key.calibration) != (RELEASE, VERSION, DUAN_V13)):
        return DriftResult(Availability.NOT_AVAILABLE)
    state = window.coverage.status(now=now, max_age=max_age, samples=window.counts.n, min_samples=min_samples)
    if state is not Availability.AVAILABLE:
        return DriftResult(state)
    a, b = window.counts, reference.counts
    if b.n < max(1, min_samples):
        return DriftResult(Availability.INSUFFICIENT_EVIDENCE)

    p, q = _probabilities(a.prices), _probabilities(b.prices)
    ps, qs = _probabilities(a.prices, .5), _probabilities(b.prices, .5)
    psi = sum((x - y) * (log(x) - log(y)) for x, y in zip(ps, qs))
    widths = tuple(right - left for left, right in zip(PRICE_EDGES_VND, PRICE_EDGES_VND[1:]))
    distance = gap = ks = 0.0
    edge_pairs = zip(widths, widths[1:])
    for x, y, (width, following_width) in zip(p, q, edge_pairs):
        gap += x - y
        ks = max(ks, abs(gap))
        distance += abs(gap) * ((width + following_width) / 2)
    error = sum((x + y) * width / 2 for x, y, width in zip(p, q, widths))
    return DriftResult(Availability.AVAILABLE, a.missing / a.applicable - b.missing / b.applicable,
                       a.unknown / a.applicable, a.unknown / a.applicable - b.unknown / b.applicable,
                       _js(_probabilities(a.property_types), _probabilities(b.property_types)), psi, _js(p, q),
                       distance, error, ks)
