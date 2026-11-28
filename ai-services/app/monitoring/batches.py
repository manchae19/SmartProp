"""Canonical sparse binary batches and a bounded in-memory transport buffer."""

from dataclasses import dataclass
from struct import Struct
from sys import getsizeof
from threading import Lock

from .accumulator import MAX_UTC, WINDOW_SECONDS, Snapshot, boundary
from .schema import InvalidTelemetry, REGISTRY, RELEASE, VERSION, integer


MAX_PRODUCERS = 32
MAX_GENERATION = (1 << 32) - 1
MAX_PENDING = 512
MAX_PENDING_BYTES = 4 * 1024 * 1024
SERVING = 1
SYNTHETIC = 2
PREVIEW = 3
INTERNAL = 4
HISTORICAL = 5
POPULATIONS = (SERVING, SYNTHETIC, PREVIEW, INTERNAL, HISTORICAL)
MAGIC = b"WPT3"
HEADER = Struct("<4sBBIBQBIIH")
ENTRY = Struct("<HQ")
MAX_PACKET = HEADER.size + REGISTRY.size * ENTRY.size


@dataclass(frozen=True, slots=True)
class BatchIdentity:
    producer: int
    generation: int
    population: int
    sequence: int
    release: int = RELEASE

    def validate(self):
        if (not integer(self.producer, MAX_PRODUCERS) or self.producer == 0
                or not integer(self.generation, MAX_GENERATION) or self.generation == 0
                or not integer(self.population, HISTORICAL) or self.population not in POPULATIONS
                or not integer(self.sequence) or self.sequence == 0
                or type(self.release) is not int or self.release != RELEASE):
            raise InvalidTelemetry("invalid_batch_identity")


@dataclass(frozen=True, slots=True)
class Batch:
    identity: BatchIdentity
    snapshot: Snapshot


def encode(identity, snapshot):
    if type(identity) is not BatchIdentity or type(snapshot) is not Snapshot:
        raise InvalidTelemetry("invalid_batch")
    identity.validate()
    snapshot.validate()
    entries = tuple((index, value) for index, value in enumerate(snapshot.cells) if value)
    buffer = bytearray(HEADER.size + len(entries) * ENTRY.size)
    HEADER.pack_into(buffer, 0, MAGIC, VERSION, identity.producer, identity.generation,
                     identity.population, identity.sequence, identity.release, snapshot.start, snapshot.end,
                     len(entries))
    for position, (index, value) in enumerate(entries):
        ENTRY.pack_into(buffer, HEADER.size + position * ENTRY.size, index, value)
    return bytes(buffer)


def decode(wire):
    if type(wire) is not bytes or not HEADER.size <= len(wire) <= MAX_PACKET:
        raise InvalidTelemetry("invalid_batch_size")
    magic, version, producer, generation, population, sequence, release, start, end, count = HEADER.unpack_from(wire)
    if magic != MAGIC or version != VERSION:
        raise InvalidTelemetry("incompatible_schema")
    if not boundary(start) or end != start + WINDOW_SECONDS or end > MAX_UTC:
        raise InvalidTelemetry("invalid_batch_window")
    if len(wire) != HEADER.size + count * ENTRY.size:
        raise InvalidTelemetry("invalid_batch_size")
    identity = BatchIdentity(producer, generation, population, sequence, release)
    identity.validate()
    cells = [0] * REGISTRY.size
    previous = -1
    for offset in range(HEADER.size, len(wire), ENTRY.size):
        index, value = ENTRY.unpack_from(wire, offset)
        if not previous < index < REGISTRY.size or not integer(value) or not value:
            raise InvalidTelemetry("invalid_batch_cell")
        cells[index] = value
        previous = index
    snapshot = Snapshot(version, start, tuple(cells))
    snapshot.validate()
    return Batch(identity, snapshot)


class BatchQueue:
    __slots__ = ("_slots", "_head", "_size", "_bytes", "_limit", "_lock")

    def __init__(self, *, capacity=MAX_PENDING, max_bytes=MAX_PENDING_BYTES):
        if not integer(capacity, MAX_PENDING) or not capacity or not integer(max_bytes, MAX_PENDING_BYTES):
            raise InvalidTelemetry("invalid_queue_capacity")
        self._slots = [None] * capacity
        self._head = self._size = 0
        self._lock = Lock()
        self._bytes = getsizeof(self) + getsizeof(self._slots) + getsizeof(self._lock)
        if max_bytes < self._bytes:
            raise InvalidTelemetry("invalid_queue_capacity")
        self._limit = max_bytes

    @property
    def usage(self):
        with self._lock:
            return self._size, self._bytes

    def offer(self, wire):
        """Only canonical, validated bytes can enter the queue."""
        try:
            decode(wire)
        except InvalidTelemetry:
            return "invalid"
        size = getsizeof(wire)
        with self._lock:
            if self._size == len(self._slots) or self._bytes + size > self._limit:
                return "full"
            tail = (self._head + self._size) % len(self._slots)
            self._slots[tail] = wire
            self._size += 1
            self._bytes += size
            return "accepted"

    def pop(self):
        with self._lock:
            if not self._size:
                return None
            wire = self._slots[self._head]
            self._slots[self._head] = None
            self._head = (self._head + 1) % len(self._slots)
            self._size -= 1
            self._bytes -= getsizeof(wire)
            return wire


def publish_window(telemetry, queue, identity):
    """Explicit in-process handoff. No worker, retry, I/O or change to any prediction."""
    if not telemetry.enabled:
        return False
    if type(identity) is not BatchIdentity or type(queue) is not BatchQueue:
        telemetry.drop("batch_rejected")
        return False
    try:
        identity.validate()
        snapshot = telemetry.rotate()
        if snapshot is None:
            return False
        outcome = queue.offer(encode(identity, snapshot))
    except InvalidTelemetry:
        outcome = "invalid"
    if outcome == "accepted":
        return True
    telemetry.drop("queue_full" if outcome == "full" else "batch_rejected")
    return False
