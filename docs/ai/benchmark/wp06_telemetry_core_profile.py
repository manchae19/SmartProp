"""Offline B1 deterministic fixture and separate host-dependent performance profile."""

import argparse
from concurrent.futures import ThreadPoolExecutor
from hashlib import sha256
import json
from math import ceil
from pathlib import Path
import sys
from threading import Barrier, Event, Lock, Thread, local
from time import perf_counter_ns, sleep
import tracemalloc

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "ai-services"))

from app.monitoring.accumulator import Availability, Snapshot
from app.monitoring.batches import MAX_PENDING, SYNTHETIC, BatchIdentity, BatchQueue, encode
from app.monitoring.core import Telemetry, TelemetryConfig
from app.monitoring.reducer import Reducer
from app.monitoring.schema import LIFECYCLE, REGISTRY, VERSION, Registry, valuation_metrics


def fixture():
    batches = []
    for producer in (1, 2):
        core = Telemetry(TelemetryConfig(True), clock_ns=lambda: 1000)
        for window in range(3):
            for index in range(8):
                ticket = core.begin("invocation", "advisor")
                core.finish(ticket, "valid_point" if producer == 1 or index % 2 else "inference_exception")
                core.feature("area", "present", True, segments=("surface:advisor",))
            core.record("stage_latency", ("advisor", "point"), (window + 1) * 10_000)
            batch = encode(BatchIdentity(producer, 1, SYNTHETIC, window + 1), core.rotate())
            batches.append((producer, batch))
    r = Reducer((1, 2), population=SYNTHETIC, watermark=0)
    for producer in (1, 2):
        r.register_generation(producer, 1, 0)
    sequence = (2, 0, 4, 1, 3, 0)  # Leave source 2 absent in the last window.
    outcomes = [r.accept(batches[i][1], source=batches[i][0]) for i in sequence]
    sealed = r.seal(180)
    late = r.accept(batches[5][1], source=2)
    windows = []
    for closed in sealed:
        closed.snapshot.validate()
        h = closed.snapshot.histogram("stage_latency", ("advisor", "point"))
        status = closed.coverage.status(now=closed.snapshot.end, max_age=0, samples=h.count, min_samples=1)
        windows.append({
            "end": closed.snapshot.end, "valid": closed.snapshot.value("invocation_outcome", ("advisor", "valid_point")),
            "batches": closed.coverage.received_batches, "state": status.value, "histogram_counts": h.counts,
        })
    assert [w["state"] for w in windows] == [Availability.AVAILABLE.value, Availability.AVAILABLE.value,
                                           Availability.INSUFFICIENT_EVIDENCE.value]
    return {"slots": REGISTRY.size, "wire_digests": [sha256(b).hexdigest() for _, b in batches],
            "outcomes": outcomes, "late": late, "windows": windows}


def percentiles(samples):
    if not samples:
        return None
    values = sorted(samples)
    return {f"p{p}_us": round(values[ceil(p * len(values) / 100) - 1] / 1000, 3) for p in (50, 95, 99)}


class TimedLock:
    def __init__(self):
        self.lock = Lock()
        self.timing = local()

    def acquire(self, **kwargs):
        start = perf_counter_ns()
        result = self.lock.acquire(**kwargs)
        self.timing.wait_ns = perf_counter_ns() - start
        return result

    def release(self):
        self.lock.release()


def writer_profile(workers, *, enabled, snapshot_reader, iterations=1500):
    core = Telemetry(TelemetryConfig(enabled))
    if enabled:
        timed = TimedLock()
        core._lock = timed
    end = Event()
    gate = Barrier(workers + (1 if snapshot_reader else 0))
    snapshot_times = []

    def write():
        gate.wait()
        totals, waits = [], []
        successful = 0
        for index in range(iterations):
            start = perf_counter_ns()
            accepted = core.record("stage_latency", ("posting", "point"), 31_000)
            totals.append(perf_counter_ns() - start)
            successful += accepted
            if enabled:
                waits.append(timed.timing.wait_ns)
            if (index + 1) % 16 == 0:
                sleep(.001)  # Synthetic bursts leave room for repeated concurrent snapshots.
        return totals, waits, successful

    def read():
        gate.wait()
        while not end.is_set():
            now = perf_counter_ns()
            snapshot = core.snapshot()
            elapsed = perf_counter_ns() - now
            if snapshot is not None:
                if len(snapshot_times) < 512:
                    snapshot_times.append(elapsed)
                if len(snapshot_times) == 1:
                    snapshot.validate()
            end.wait(.0005)

    reader = Thread(target=read) if snapshot_reader else None
    if reader:
        reader.start()
    with ThreadPoolExecutor(workers) as pool:
        jobs = [pool.submit(write) for _ in range(workers)]
        results = [job.result() for job in jobs]
    end.set()
    if reader:
        reader.join()
    totals = [n for samples, _, _ in results for n in samples]
    waits = [n for _, samples, _ in results for n in samples]
    accepted = sum(n for _, _, n in results)
    snapshot = core.snapshot()
    drops = snapshot.value("telemetry_drop", ("lock_busy",)) if snapshot is not None else 0
    if snapshot is not None:
        assert snapshot.histogram("stage_latency", ("posting", "point")).count == accepted
    return {"observation": percentiles(totals), "lock_acquire": percentiles(waits),
            "snapshot": percentiles(snapshot_times), "samples": len(totals), "snapshots": len(snapshot_times),
            "accepted": accepted, "lock_busy_drops": drops}


def dense_snapshot():
    cells = [1] * REGISTRY.size
    for series in REGISTRY.series.values():
        if series.metric.kind == "histogram":
            cells[series.offset + series.width - 2] = sum(edge + 1 for edge in series.metric.edges)
            cells[series.offset + series.width - 1] = series.width - 2
    for life in LIFECYCLE.values():
        count = cells[life.latency.offset + life.latency.width - 1]
        cells[life.started] = count + cells[life.lost]
        cells[life.completed] = count
        cells[next(iter(life.outcomes.values()))] += count - len(life.outcomes)
    return Snapshot(VERSION, 0, tuple(cells))


def stress_profile():
    dense = dense_snapshot()
    dense.validate()
    dense_wire = encode(BatchIdentity(1, 1, SYNTHETIC, 1), dense)
    nan = float("nan")
    core = Telemetry(TelemetryConfig(True), clock_ns=lambda: 0)
    invalid_label, invalid_numeric = [], []
    for _ in range(2000):
        now = perf_counter_ns()
        assert not core.record("retry", ("synthetic-unregistered-label", "transport"))
        invalid_label.append(perf_counter_ns() - now)
        now = perf_counter_ns()
        assert not core.record("stage_latency", ("posting", "point"), nan)
        invalid_numeric.append(perf_counter_ns() - now)
    small = encode(BatchIdentity(1, 1, SYNTHETIC, 1), core.snapshot())
    small_queue = BatchQueue()
    for _ in range(MAX_PENDING):
        assert small_queue.offer(small) == "accepted"
    assert small_queue.offer(small) == "full"

    r = Reducer((1,), population=SYNTHETIC, watermark=0)
    r.register_generation(1, 1, 0)
    assert r.accept(small, source=1) == "accepted"
    flood = []
    for _ in range(500):
        now = perf_counter_ns()
        assert r.accept(small, source=1) == "duplicate"
        flood.append(perf_counter_ns() - now)
    r.seal(60)
    r.register_generation(1, 2, 60)
    after_restart = Telemetry(TelemetryConfig(True), start=60).snapshot()
    assert r.accept(encode(BatchIdentity(1, 1, SYNTHETIC, 2), after_restart), source=1) == "old_generation"
    assert r.accept(encode(BatchIdentity(1, 2, SYNTHETIC, 1), after_restart), source=1) == "accepted"
    assert r.accept(small, source=1) == "late"

    merge_times = []
    for _ in range(50):
        trial = Reducer((1,), population=SYNTHETIC, watermark=0)
        trial.register_generation(1, 1, 0)
        now = perf_counter_ns()
        assert trial.accept(dense_wire, source=1) == "accepted"
        merge_times.append(perf_counter_ns() - now)

    tracemalloc.start()
    registry_clone = Registry(valuation_metrics())
    tracked_registry, _ = tracemalloc.get_traced_memory()
    del registry_clone
    tracemalloc.stop()
    tracemalloc.start()
    core = Telemetry(TelemetryConfig(True), clock_ns=lambda: 1000)
    for _ in range(1024):
        assert core.begin("invocation", "advisor")
    queue = BatchQueue()
    while queue.offer(bytes(bytearray(dense_wire))) == "accepted":
        pass
    # The downstream consumer has stopped while the producer fills the full byte budget.
    r = Reducer(tuple(range(1, 33)), population=SYNTHETIC, watermark=0)
    for source in range(1, 33):
        r.register_generation(source, 1, 0)
        for window in range(10):
            snapshot = Snapshot(VERSION, 60 * window, dense.cells)
            sent = encode(BatchIdentity(source, 1, SYNTHETIC, window + 1), snapshot)
            assert r.accept(sent, source=source) == "accepted"
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()
    return {
        "label_rejected": len(invalid_label), "numeric_rejected": len(invalid_numeric),
        "label_reject_latency": percentiles(invalid_label), "numeric_reject_latency": percentiles(invalid_numeric),
        "small_queue_count_cap": small_queue.usage[0], "dense_queue": queue.usage,
        "dense_batch_bytes": len(dense_wire), "duplicate_flood": len(flood), "duplicate_latency": percentiles(flood),
        "dense_merge_latency": percentiles(merge_times), "open_batches": r.health()["accepted"],
        "tracked_bytes_with_queue": current, "tracked_peak_bytes_with_queue": peak,
        "static_registry_tracked_bytes": tracked_registry, "combined_modeled_peak_bytes": peak + tracked_registry,
        "restart_gate_passed": True,
    }


def profile():
    rows = {}
    for workers in (1, 4, 16, 32):
        disabled = writer_profile(workers, enabled=False, snapshot_reader=False)
        active = writer_profile(workers, enabled=True, snapshot_reader=True)
        rows[workers] = {"disabled": disabled, "enabled_with_reader": active,
                         "p95_delta_us": round(active["observation"]["p95_us"] - disabled["observation"]["p95_us"], 3)}
    return {"writers": rows, "stress": stress_profile()}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true")
    args = parser.parse_args()
    print(json.dumps(profile() if args.profile else fixture(), sort_keys=True, indent=2, allow_nan=False))
