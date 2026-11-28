"""Process-local, opt-in counters. All valuation code remains a separate caller."""

from array import array
from collections import Counter
from dataclasses import dataclass
from threading import Lock
from time import monotonic_ns

from .accumulator import MAX_UTC, WINDOW_SECONDS, Snapshot, apply_deltas, boundary, histogram_updates
from .schema import (
    DROP_REASONS, InvalidTelemetry, LIFECYCLE, MAX_DURATION_US, MAX_VALUE, REGISTRY, VERSION,
    approved_string, integer,
)


MAX_ACTIVE = 1024
LOCK_TIMEOUT_SECONDS = 0.02
DROP_SLOTS = {reason: REGISTRY.find("telemetry_drop", (reason,)).offset for reason in DROP_REASONS}
DUPLICATE_SLOT = REGISTRY.find("duplicate_completion", ()).offset


@dataclass(frozen=True, slots=True)
class TelemetryConfig:
    enabled: bool = False
    max_active: int = MAX_ACTIVE

    def __post_init__(self):
        if type(self.enabled) is not bool or not integer(self.max_active, MAX_ACTIVE) or not self.max_active:
            raise InvalidTelemetry("invalid_config")


@dataclass(frozen=True, slots=True)
class Ticket:
    sequence: int
    owner: object


class Telemetry:
    def __init__(self, config=TelemetryConfig(), *, start=0, clock_ns=monotonic_ns):
        if type(config) is not TelemetryConfig:
            raise InvalidTelemetry("invalid_config")
        self._enabled = config.enabled
        if not self.enabled:
            return
        if not boundary(start) or start + WINDOW_SECONDS > MAX_UTC or not callable(clock_ns):
            raise InvalidTelemetry("invalid_window")
        self._start = start
        self._clock = clock_ns
        self._max_active = config.max_active
        self._lock = Lock()
        self._health_lock = Lock()
        self._drops = dict.fromkeys(DROP_REASONS, 0)
        self._cells = array("Q", [0]) * REGISTRY.size
        self._owner = object()
        self._active = {}
        self._sequence = 0
        self._stopped = False

    @property
    def enabled(self):
        return self._enabled

    def drop(self, reason):
        if self.enabled:
            if not approved_string(reason) or reason not in DROP_SLOTS:
                reason = "invalid"
            # Health accounting is a fixed-size independent critical section.
            with self._health_lock:
                self._drops[reason] = min(MAX_VALUE, self._drops[reason] + 1)

    def _acquire(self):
        if self._lock.acquire(timeout=LOCK_TIMEOUT_SECONDS):
            return True
        self.drop("lock_busy")
        return False

    def _apply(self, changes):
        try:
            apply_deltas(self._cells, changes)
        except InvalidTelemetry:
            self.drop("numeric_overflow")
            return False
        return True

    def _write(self, changes):
        if not self._acquire():
            return False
        try:
            if self._stopped:
                self.drop("batch_rejected")
                return False
            return self._apply(changes)
        finally:
            self._lock.release()

    def _now(self):
        try:
            now = self._clock()
        except Exception:
            raise InvalidTelemetry("invalid_clock") from None
        if not integer(now, (1 << 63) - 1):
            raise InvalidTelemetry("invalid_clock")
        return now

    def record(self, metric, labels=(), value=1):
        """Only unmanaged registered observations can be written directly."""
        if not self.enabled:
            return False
        try:
            series = REGISTRY.find(metric, labels)
            adapter_stage = metric == "stage_latency" and labels[1] in ("explanation", "interval")
            if series.metric.managed or adapter_stage or not integer(value, series.metric.maximum):
                raise InvalidTelemetry("invalid_observation")
            changes = (histogram_updates(series, value) if series.metric.kind == "histogram"
                       else {series.offset: value})
        except InvalidTelemetry:
            self.drop("invalid")
            return False
        return self._write(changes)

    def begin(self, kind, surface):
        if not self.enabled:
            return None
        if not approved_string(kind) or not approved_string(surface):
            self.drop("invalid")
            return None
        life = LIFECYCLE.get((kind, surface))
        if life is None:
            self.drop("invalid")
            return None
        if not self._acquire():
            return None
        try:
            if self._stopped or len(self._active) >= self._max_active or self._sequence >= MAX_VALUE:
                self.drop("active_limit")
                return None
            try:
                now = self._now()
            except InvalidTelemetry:
                self.drop("invalid")
                return None
            if not self._apply({life.started: 1, life.active: 1}):
                return None
            self._sequence += 1
            ticket = Ticket(self._sequence, self._owner)
            self._active[ticket.sequence] = (ticket, life, now)
            return ticket
        finally:
            self._lock.release()

    def _completion(self, life, start, now, outcome):
        if not integer(now, (1 << 63) - 1) or now < start or not approved_string(outcome):
            raise InvalidTelemetry("invalid_completion")
        outcome_slot = life.outcomes.get(outcome)
        if outcome_slot is None:
            raise InvalidTelemetry("invalid_completion")
        return {life.completed: 1, outcome_slot: 1, life.active: -1,
                **histogram_updates(life.latency, (now - start) // 1000)}

    def finish(self, ticket, outcome):
        if not self.enabled:
            return False
        if (type(ticket) is not Ticket or ticket.owner is not self._owner
                or not integer(ticket.sequence) or not ticket.sequence):
            self.drop("invalid")
            return False
        if not self._acquire():
            return False
        try:
            entry = self._active.get(ticket.sequence)
            if entry is None:
                if ticket.sequence <= self._sequence:
                    self._cells[DUPLICATE_SLOT] = min(MAX_VALUE, self._cells[DUPLICATE_SLOT] + 1)
                else:
                    self.drop("invalid")
                return False
            if entry[0] is not ticket:
                self.drop("invalid")
                return False
            _, life, start = entry
            try:
                changes = self._completion(life, start, self._now(), outcome)
            except InvalidTelemetry:
                self.drop("invalid")
                return False
            if not self._apply(changes):
                return False
            del self._active[ticket.sequence]
            return True
        finally:
            self._lock.release()

    def stop(self):
        """Graceful shutdown records outstanding tickets once as interrupted."""
        if not self.enabled or not self._acquire():
            return False
        try:
            changes = Counter()
            try:
                now = self._now()
                for _, life, start in self._active.values():
                    changes.update(self._completion(life, start, now, "interrupted"))
            except InvalidTelemetry:
                self.drop("invalid")
                return False
            if not self._apply(changes):
                return False
            self._active.clear()
            self._stopped = True
            return True
        finally:
            self._lock.release()

    def _snapshot(self, rotate):
        if not self.enabled or not self._acquire():
            return None
        try:
            if rotate and self._start + 2 * WINDOW_SECONDS > MAX_UTC:
                self.drop("batch_rejected")
                return None
            with self._health_lock:
                cells = self._cells[:]
                for reason, offset in DROP_SLOTS.items():
                    cells[offset] = self._drops[reason]
                snapshot = Snapshot(VERSION, self._start, tuple(cells))
                if rotate:
                    self._start += WINDOW_SECONDS
                    self._cells = array("Q", [0]) * REGISTRY.size
                    for life in LIFECYCLE.values():
                        self._cells[life.opening] = cells[life.active]
                        self._cells[life.active] = cells[life.active]
                    for reason in self._drops:
                        self._drops[reason] = 0
                return snapshot
        finally:
            self._lock.release()

    def snapshot(self):
        return self._snapshot(False)

    def rotate(self):
        """Explicitly close one UTC window. Carry opening and active gauges forward."""
        return self._snapshot(True)

    def feature(self, feature, state, raw_present, *, segments=(), derived=False, defaulted=False, unverified=False):
        if not self.enabled:
            return False
        flags = (raw_present, derived, defaulted, unverified)
        if (any(type(flag) is not bool for flag in flags) or type(segments) is not tuple or len(segments) > 4
                or any(not approved_string(s) or ":" not in s for s in segments)
                or len({s.split(":", 1)[0] for s in segments}) != len(segments)):
            self.drop("invalid")
            return False
        try:
            changes = {REGISTRY.find("feature_effective", (feature, state, s)).offset: 1
                       for s in ("global", *segments)}
            changes[REGISTRY.find("feature_raw", (feature, "present" if raw_present else "absent")).offset] = 1
            for axis, value in zip(("derived", "defaulted", "unverified"), flags[1:]):
                changes[REGISTRY.find("feature_provenance", (feature, axis, "yes" if value else "no")).offset] = 1
        except InvalidTelemetry:
            self.drop("invalid")
            return False
        return self._write(changes)

    def explanation(self, surface, state, contract, check, *, duration_us=None, provenance=()):
        """Consumes WP-04 status only, never SHAP, feature values or its residual."""
        if not self.enabled:
            return False
        try:
            status = REGISTRY.find("explanation_status", (surface, state))
            validation = REGISTRY.find("explanation_contract", (surface, contract, check))
            if check != "not_checked" and contract != "wp04_v1":
                raise InvalidTelemetry("invalid_explanation")
            if (type(provenance) is not tuple or len(provenance) not in (0, 6)
                    or any(not integer(v, 22) for v in provenance) or sum(provenance) > 22):
                raise InvalidTelemetry("invalid_provenance")
            if state == "not_enabled" and (check != "not_checked" or duration_us is not None or provenance):
                raise InvalidTelemetry("invalid_explanation")
            changes = {status.offset: 1, validation.offset: 1}
            for origin, value in zip(("provided", "derived", "assumed", "missing", "unknown", "not_applicable"),
                                     provenance):
                changes[REGISTRY.find("explanation_provenance", (surface, origin)).offset] = value
            if duration_us is not None:
                changes.update(histogram_updates(REGISTRY.find("stage_latency", (surface, "explanation")), duration_us))
        except InvalidTelemetry:
            self.drop("invalid")
            return False
        return self._write(changes)

    def interval(self, surface, state="not_enabled", *, scope=None, width_vnd=None, width_ppm=None, duration_us=None):
        """Consumes optional interval metadata. Bounds and observed labels stay outside the core."""
        if not self.enabled:
            return False
        try:
            status = REGISTRY.find("interval_status", (surface, state))
            changes = {status.offset: 1}
            if state == "available":
                changes[REGISTRY.find("interval_scope", (surface, scope)).offset] = 1
                for metric, value in (("interval_width", width_vnd), ("interval_relative_width", width_ppm)):
                    if value is not None:
                        changes.update(histogram_updates(REGISTRY.find(metric, (surface,)), value))
            elif scope is not None or width_vnd is not None or width_ppm is not None:
                raise InvalidTelemetry("invalid_interval")
            if duration_us is not None:
                if state == "not_enabled":
                    raise InvalidTelemetry("invalid_interval")
                changes.update(histogram_updates(REGISTRY.find("stage_latency", (surface, "interval")), duration_us))
        except InvalidTelemetry:
            self.drop("invalid")
            return False
        return self._write(changes)
