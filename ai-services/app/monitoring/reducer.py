"""Deterministic merge for completed, fixed UTC windows from trusted producers."""

from array import array
from dataclasses import dataclass
from hashlib import sha256
from threading import Lock

from .accumulator import MAX_UTC, WINDOW_SECONDS, Availability, Snapshot, apply_deltas, boundary
from .batches import MAX_GENERATION, MAX_PRODUCERS, SERVING, SYNTHETIC, decode
from .core import DROP_SLOTS
from .schema import InvalidTelemetry, MAX_VALUE, REGISTRY, VERSION, integer


MAX_DEDUPE = 4096
OPEN_WINDOWS = 10
RESULTS = ("accepted", "duplicate", "invalid", "untrusted", "old_generation", "future",
           "late", "sequence", "overlap", "capacity", "numeric_overflow")


@dataclass(frozen=True, slots=True)
class Coverage:
    expected_sources: int | None
    received_sources: int
    expected_batches: int | None
    received_batches: int
    dropped_observations: int
    conflicting_batches: int
    late_arrivals_total: int
    window_end: int

    @property
    def missing_batches(self):
        return None if self.expected_batches is None else self.expected_batches - self.received_batches

    @property
    def batch_coverage(self):
        return self.received_batches / self.expected_batches if self.expected_batches else None

    @property
    def instance_coverage(self):
        return self.received_sources / self.expected_sources if self.expected_sources else None

    def status(self, *, now, max_age, samples, min_samples, enabled=True):
        if type(enabled) is not bool or any(not integer(n) for n in (now, max_age, samples, min_samples)):
            raise InvalidTelemetry("invalid_evidence_query")
        if not enabled:
            return Availability.NOT_ENABLED
        if now - self.window_end > max_age:
            return Availability.STALE
        if (now < self.window_end or self.batch_coverage != 1 or self.instance_coverage != 1
                or self.dropped_observations or self.conflicting_batches or samples < max(1, min_samples)):
            return Availability.INSUFFICIENT_EVIDENCE
        return Availability.AVAILABLE


@dataclass(frozen=True, slots=True)
class ClosedWindow:
    snapshot: Snapshot
    coverage: Coverage


@dataclass(slots=True)
class _OpenWindow:
    values: array
    sources: dict
    conflicts: int = 0


class Reducer:
    def __init__(self, producers, *, population, watermark, inventory_known=True, max_dedupe=MAX_DEDUPE):
        if (type(producers) is not tuple or not 1 <= len(producers) <= MAX_PRODUCERS
                or any(not integer(p, MAX_PRODUCERS) or not p for p in producers)
                or len(set(producers)) != len(producers)
                or not integer(population, SYNTHETIC) or population not in (SERVING, SYNTHETIC)
                or not boundary(watermark) or type(inventory_known) is not bool
                or not integer(max_dedupe, MAX_DEDUPE) or not max_dedupe):
            raise InvalidTelemetry("invalid_reducer_config")
        self._allowed = frozenset(producers)
        self._expected = len(producers) if inventory_known else None
        self._population = population
        self._watermark = watermark
        self._max_dedupe = max_dedupe
        self._lock = Lock()
        self._generations = {}
        self._windows = {}
        self._keys = 0
        self._counts = dict.fromkeys(RESULTS, 0)

    @property
    def watermark(self):
        with self._lock:
            return self._watermark

    def health(self):
        with self._lock:
            return dict(self._counts)

    def register_generation(self, producer, generation, first_window):
        """Called by a trusted coordinator at a window boundary, never by an observation."""
        if (not integer(producer, MAX_PRODUCERS) or producer not in self._allowed
                or not integer(generation, MAX_GENERATION) or not generation or not boundary(first_window)
                or first_window + WINDOW_SECONDS > MAX_UTC):
            raise InvalidTelemetry("invalid_generation")
        with self._lock:
            previous = self._generations.get(producer)
            if previous == (generation, first_window):
                return False
            if (first_window >= self._watermark + OPEN_WINDOWS * WINDOW_SECONDS
                    or (previous is not None and (
                        generation <= previous[0] or first_window < max(previous[1] + WINDOW_SECONDS, self._watermark)
                        or any(start >= first_window and producer in w.sources
                               for start, w in self._windows.items())
                    ))):
                raise InvalidTelemetry("invalid_generation")
            self._generations[producer] = (generation, first_window)
            return True

    def _result(self, reason):
        self._counts[reason] = min(MAX_VALUE, self._counts[reason] + 1)
        return reason

    def accept(self, wire, *, source):
        # A deployment must bind source to trusted collector identity before this call.
        if not integer(source, MAX_PRODUCERS) or source not in self._allowed:
            with self._lock:
                return self._result("untrusted")
        try:
            batch = decode(wire)
        except InvalidTelemetry:
            with self._lock:
                return self._result("invalid")
        identity, snapshot = batch.identity, batch.snapshot
        with self._lock:
            if source != identity.producer or identity.population != self._population:
                return self._result("untrusted")
            if snapshot.start < self._watermark:
                return self._result("late")
            if snapshot.start >= self._watermark + OPEN_WINDOWS * WINDOW_SECONDS:
                return self._result("future")
            generation = self._generations.get(source)
            if generation is None or generation[0] != identity.generation:
                return self._result("old_generation")
            first = generation[1]
            if snapshot.start < first or identity.sequence != 1 + (snapshot.start - first) // WINDOW_SECONDS:
                return self._result("sequence")
            window = self._windows.get(snapshot.start)
            digest = sha256(wire).digest()
            if window is not None and source in window.sources:
                if window.sources[source] == digest:
                    return self._result("duplicate")
                window.conflicts = min(MAX_VALUE, window.conflicts + 1)
                return self._result("overlap")
            if self._keys >= self._max_dedupe:
                return self._result("capacity")
            if window is None:
                window = _OpenWindow(array("Q", [0]) * REGISTRY.size, {})
            try:
                apply_deltas(window.values, {index: n for index, n in enumerate(snapshot.cells) if n})
            except InvalidTelemetry:
                return self._result("numeric_overflow")
            self._windows[snapshot.start] = window
            window.sources[source] = digest
            self._keys += 1
            return self._result("accepted")

    def seal(self, through):
        """Advance the irreversible watermark and return all closed windows, gaps included."""
        with self._lock:
            if not boundary(through) or not self._watermark <= through <= self._watermark + OPEN_WINDOWS * WINDOW_SECONDS:
                raise InvalidTelemetry("invalid_watermark")
            closed = []
            for start in range(self._watermark, through, WINDOW_SECONDS):
                window = self._windows.pop(start, None)
                sources = len(window.sources) if window is not None else 0
                cells = tuple(window.values) if window is not None else (0,) * REGISTRY.size
                self._keys -= sources
                snapshot = Snapshot(VERSION, start, cells)
                dropped = min(MAX_VALUE, sum(cells[i] for i in DROP_SLOTS.values()))
                coverage = Coverage(self._expected, sources, self._expected, sources,
                                    dropped, window.conflicts if window is not None else 0,
                                    self._counts["late"], snapshot.end)
                closed.append(ClosedWindow(snapshot, coverage))
            self._watermark = through
            return tuple(closed)
