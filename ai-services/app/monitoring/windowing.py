"""Explicit UTC rotation for one worker. Durations use a separate monotonic clock."""

from dataclasses import dataclass, replace
from threading import Lock

from .accumulator import MAX_UTC, WINDOW_SECONDS, Snapshot
from .batches import BatchIdentity, BatchQueue, encode
from .schema import InvalidTelemetry, integer


MAX_TICK_NS = (1 << 63) - 1
DRIFT_NS = 2_000_000_000


def valid_sample(wall, monotonic_ns):
    return integer(wall, MAX_UTC - WINDOW_SECONDS) and integer(monotonic_ns, MAX_TICK_NS)


@dataclass(frozen=True, slots=True)
class Rotation:
    status: str
    snapshot: Snapshot | None = None


class WindowCoordinator:
    def __init__(self, recorder, identity, *, wall, mono, export=False):
        if (not recorder.enabled or type(identity) is not BatchIdentity or identity.sequence != 1
                or type(export) is not bool or not valid_sample(wall, mono)):
            raise InvalidTelemetry("invalid_worker_window")
        identity.validate()
        self._recorder = recorder
        self._identity = identity
        self._first = self._start = wall - wall % WINDOW_SECONDS
        snapshot = recorder.snapshot()
        if snapshot is None or snapshot.start != self._start:
            raise InvalidTelemetry("invalid_worker_window")
        self._wall = wall
        self._mono = mono
        self._complete = self._start == wall
        self._stopped = False
        self._lock = Lock()
        self.queue = BatchQueue() if export else None

    def tick(self, wall, mono):
        if not self._lock.acquire(blocking=False):
            self._recorder.drop("lock_busy")
            return Rotation("busy")
        try:
            if self._stopped:
                return Rotation("stopped")
            if not valid_sample(wall, mono) or wall < self._wall or mono < self._mono:
                self._complete = False
                self._recorder.drop("clock_discontinuity")
                return Rotation("clock_discontinuity")
            delta = abs((wall - self._wall) * 1_000_000_000 - (mono - self._mono))
            discontinuity = delta > DRIFT_NS
            self._wall, self._mono = wall, mono
            if discontinuity:
                self._complete = False
                self._recorder.drop("clock_discontinuity")
            target = wall - wall % WINDOW_SECONDS
            if target == self._start:
                return Rotation("clock_discontinuity" if discontinuity else "unchanged")
            complete = (self._complete and target == self._start + WINDOW_SECONDS and wall == target)
            previous = self._recorder.rotate(target)
            if previous is None:
                self._complete = False
                return Rotation("busy")
            self._start = target
            self._complete = wall == target and not discontinuity
            if not complete:
                return Rotation("gap")
            if self.queue is None:
                return Rotation("closed", previous)
            sequence = 1 + (previous.start - self._first) // WINDOW_SECONDS
            try:
                result = self.queue.offer(encode(replace(self._identity, sequence=sequence), previous))
            except Exception:
                result = "invalid"
            if result != "accepted":
                self._recorder.drop("queue_full" if result == "full" else "batch_rejected")
                return Rotation("dropped")
            return Rotation("published", previous)
        finally:
            self._lock.release()

    def shutdown(self):
        """No partial UTC window is published during shutdown."""
        if not self._lock.acquire(blocking=False):
            self._recorder.drop("lock_busy")
            return False
        try:
            if self._stopped:
                return True
            if not self._recorder.stop():
                return False
            self._stopped = True
            return True
        finally:
            self._lock.release()
