"""Integer accumulators and immutable point-in-time views."""

from bisect import bisect_left
from dataclasses import dataclass
from enum import Enum

from .schema import InvalidTelemetry, LIFECYCLE, MAX_VALUE, REGISTRY, VERSION, integer


WINDOW_SECONDS = 60
MAX_UTC = 4_102_444_800  # 2100-01-01T00:00:00Z


class Availability(str, Enum):
    AVAILABLE = "AVAILABLE"
    NOT_ENABLED = "NOT_ENABLED"
    NOT_AVAILABLE = "NOT_AVAILABLE"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    STALE = "STALE"


def boundary(value):
    return integer(value, MAX_UTC) and value % WINDOW_SECONDS == 0


def ratio(numerator, denominator):
    if not integer(numerator) or not integer(denominator) or numerator > denominator:
        raise InvalidTelemetry("invalid_ratio")
    return numerator / denominator if denominator else None


def histogram_updates(series, value):
    if not integer(value, series.metric.maximum):
        raise InvalidTelemetry("invalid_observation")
    return {
        series.offset + bisect_left(series.metric.edges, value): 1,
        series.offset + series.width - 2: value,
        series.offset + series.width - 1: 1,
    }


def apply_deltas(values, deltas):
    updated = tuple((index, values[index] + change) for index, change in deltas.items())
    if any(not integer(value) for _, value in updated):
        raise InvalidTelemetry("numeric_overflow")
    for index, value in updated:
        values[index] = value


@dataclass(frozen=True, slots=True)
class BucketEstimate:
    lower: int
    upper: int | None  # None means strictly greater than the largest edge.


@dataclass(frozen=True, slots=True)
class Histogram:
    version: int
    unit: str
    edges: tuple
    counts: tuple
    total: int
    count: int
    maximum: int

    def validate(self):
        if (type(self.version) is not int or self.version != VERSION or self.unit not in ("us", "vnd", "ppm")
                or not integer(self.maximum) or type(self.edges) is not tuple or not 1 <= len(self.edges) <= 32
                or any(not integer(edge, self.maximum) for edge in self.edges)
                or any(a >= b for a, b in zip(self.edges, self.edges[1:]))
                or type(self.counts) is not tuple or len(self.counts) != len(self.edges) + 1
                or any(not integer(value) for value in (*self.counts, self.total, self.count))
                or sum(self.counts) != self.count):
            raise InvalidTelemetry("invalid_histogram")
        lower = (0, *(edge + 1 for edge in self.edges))
        upper = (*self.edges, self.maximum)
        minimum_sum = sum(edge * count for edge, count in zip(lower, self.counts))
        maximum_sum = sum(edge * count for edge, count in zip(upper, self.counts))
        if (self.edges[-1] == self.maximum and self.counts[-1]) or not minimum_sum <= self.total <= maximum_sum:
            raise InvalidTelemetry("invalid_histogram_sum")

    def quantile(self, percentile):
        if type(percentile) is not int or not 1 <= percentile <= 100:
            raise InvalidTelemetry("invalid_percentile")
        self.validate()
        if not self.count:
            return None
        rank = (self.count * percentile + 99) // 100
        lower = 0
        for upper, count in zip((*self.edges, None), self.counts):
            rank -= count
            if rank <= 0:
                return BucketEstimate(lower, upper)
            lower = upper + 1

    def merge(self, other):
        if (type(other) is not Histogram or (self.version, self.unit, self.edges, self.maximum)
                != (other.version, other.unit, other.edges, other.maximum)):
            raise InvalidTelemetry("incompatible_histogram")
        self.validate()
        other.validate()
        result = Histogram(self.version, self.unit, self.edges,
                           tuple(a + b for a, b in zip(self.counts, other.counts)),
                           self.total + other.total, self.count + other.count, self.maximum)
        result.validate()
        return result


@dataclass(frozen=True, slots=True)
class Snapshot:
    version: int
    start: int
    cells: tuple

    @property
    def end(self):
        return self.start + WINDOW_SECONDS

    def value(self, name, labels=()):
        series = REGISTRY.find(name, labels)
        if series.width != 1:
            raise InvalidTelemetry("histogram_required")
        return self.cells[series.offset]

    def histogram(self, name, labels):
        return self._histogram(REGISTRY.find(name, labels))

    def _histogram(self, series):
        if series.metric.kind != "histogram":
            raise InvalidTelemetry("histogram_required")
        data = self.cells[series.offset:series.offset + series.width]
        return Histogram(self.version, series.metric.unit, series.metric.edges, data[:-2],
                         data[-2], data[-1], series.metric.maximum)

    def validate(self):
        if (type(self.version) is not int or self.version != VERSION or not boundary(self.start)
                or self.end > MAX_UTC or type(self.cells) is not tuple or len(self.cells) != REGISTRY.size
                or any(not integer(value) for value in self.cells)):
            raise InvalidTelemetry("invalid_snapshot")
        for series in REGISTRY.series.values():
            if series.metric.kind == "histogram":
                self._histogram(series).validate()
        for life in LIFECYCLE.values():
            opened, started, completed, current = (
                self.cells[i] for i in (life.opening, life.started, life.completed, life.active)
            )
            if (opened + started - completed != current
                    or sum(self.cells[i] for i in life.outcomes.values()) != completed
                    or self.cells[life.latency.offset + life.latency.width - 1] != completed):
                raise InvalidTelemetry("lifecycle_conservation")
