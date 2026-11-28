"""Lost-terminal and per-generation continuity regressions without a runtime."""

from concurrent.futures import ThreadPoolExecutor
from threading import Event, Lock
from unittest import TestCase

from app.monitoring.accumulator import Availability
from app.monitoring.batches import BatchIdentity, SYNTHETIC, encode
from app.monitoring.core import Telemetry, TelemetryConfig
from app.monitoring.reducer import Reducer
from app.monitoring.schema import LIFECYCLE, MAX_DURATION_US, MAX_VALUE


def recorder(start=0, clock=lambda: 0, capacity=2):
    return Telemetry(TelemetryConfig(True, capacity, nonblocking=True), start=start, clock_ns=clock)


def packet(snapshot, sequence, source=1, generation=1):
    return encode(BatchIdentity(source, generation, SYNTHETIC, sequence), snapshot)


def collector(*sources):
    result = Reducer(sources, population=SYNTHETIC, watermark=0)
    for source in sources:
        result.register_generation(source, 1, 0)
    return result


def status(window):
    return window.coverage.status(now=window.snapshot.end, max_age=0, samples=1000, min_samples=1)


class LostTerminalTests(TestCase):
    def test_busy_finish_retires_without_outcome_and_recovers_active_capacity(self):
        t = recorder(capacity=1)
        for _ in range(8):
            ticket = t.begin("invocation", "advisor")
            self.assertIsNotNone(ticket)
            with t._lock:
                self.assertFalse(t.finish(ticket, "valid_point"))
                self.assertFalse(t.finish(ticket, "valid_point"))
        state = t.snapshot()
        state.validate()
        self.assertEqual(state.value("invocation_lost_terminal", ("advisor",)), 8)
        self.assertEqual(state.value("invocation_in_flight", ("advisor",)), 0)
        self.assertEqual(state.value("invocation_completed", ("advisor",)), 0)
        self.assertEqual(state.value("telemetry_drop", ("lock_busy",)), 8)
        self.assertFalse(t.finish(ticket, "valid_point"))
        self.assertEqual(t.snapshot().value("duplicate_completion"), 1)
        self.assertTrue(t.finish(t.begin("invocation", "advisor"), "valid_point"))

    def test_late_finish_before_snapshot_cannot_turn_abandonment_into_a_point(self):
        t = recorder()
        ticket = t.begin("invocation", "advisor")
        with t._lock:
            self.assertFalse(t.finish(ticket, "valid_point"))
        self.assertFalse(t.finish(ticket, "valid_point"))
        s = t.snapshot()
        self.assertEqual(s.value("invocation_lost_terminal", ("advisor",)), 1)
        self.assertEqual(s.histogram("invocation_latency", ("advisor",)).count, 0)

    def test_loss_after_rotation_keeps_both_windows_conserved_and_gates_coverage(self):
        t = recorder()
        ticket = t.begin("invocation", "posting")
        first = t.rotate()
        with t._lock:
            self.assertFalse(t.finish(ticket, "inference_exception"))
        second = t.rotate()
        first.validate()
        second.validate()
        self.assertEqual(first.value("invocation_in_flight", ("posting",)), 1)
        self.assertEqual(second.value("invocation_opening_in_flight", ("posting",)), 1)
        self.assertEqual(second.value("invocation_lost_terminal", ("posting",)), 1)
        r = collector(1)
        r.accept(packet(second, 2), source=1)
        r.accept(packet(first, 1), source=1)
        prev, loss = r.seal(120)
        self.assertEqual(status(prev), Availability.AVAILABLE)
        self.assertEqual(loss.coverage.continuity_mismatches, 0)
        self.assertEqual(loss.coverage.lost_terminals, 1)
        self.assertEqual(status(loss), Availability.INSUFFICIENT_EVIDENCE)

    def test_shutdown_does_not_convert_pending_loss_into_interruption(self):
        t = recorder()
        lost = t.begin("invocation", "advisor")
        t.begin("invocation", "advisor")
        with t._lock:
            self.assertFalse(t.finish(lost, "valid_point"))
        self.assertTrue(t.stop())
        s = t.snapshot()
        s.validate()
        self.assertEqual(s.value("invocation_lost_terminal", ("advisor",)), 1)
        self.assertEqual(s.value("invocation_outcome", ("advisor", "interrupted")), 1)
        self.assertEqual(s.value("invocation_in_flight", ("advisor",)), 0)

    def test_shutdown_competing_with_announced_finish_counts_loss_not_interruption(self):
        inside_stop, finish_waiting, stop_done = Event(), Event(), Event()
        ticks = iter((0, 1000))

        def clock():
            now = next(ticks)
            if now:
                inside_stop.set()
                self.assertTrue(finish_waiting.wait(3))
            return now

        class InterleavedLock:
            def __init__(self):
                self.lock = Lock()

            def acquire(self, **options):
                if inside_stop.is_set() and self.lock.locked():
                    finish_waiting.set()
                    if not stop_done.wait(3):
                        return False
                return self.lock.acquire(**options)

            def release(self):
                self.lock.release()

        t = recorder(clock=clock)
        t._lock = InterleavedLock()
        ticket = t.begin("invocation", "advisor")
        with ThreadPoolExecutor(2) as pool:
            stop = pool.submit(t.stop)
            self.assertTrue(inside_stop.wait(3))
            finish = pool.submit(t.finish, ticket, "valid_point")
            try:
                self.assertTrue(stop.result(timeout=4))
            finally:
                stop_done.set()
            self.assertFalse(finish.result(timeout=4))
        s = t.snapshot()
        s.validate()
        self.assertEqual(s.value("invocation_lost_terminal", ("advisor",)), 1)
        self.assertEqual(s.value("invocation_completed", ("advisor",)), 0)

    def test_invalid_clock_and_histogram_overflow_release_capacity(self):
        ticks = iter((0, float("nan"), 2000, 3000))
        t = recorder(clock=lambda: next(ticks), capacity=1)
        self.assertFalse(t.finish(t.begin("invocation", "advisor"), "valid_point"))
        self.assertTrue(t.finish(t.begin("invocation", "advisor"), "valid_point"))
        s = t.snapshot()
        s.validate()
        self.assertEqual(s.value("invocation_lost_terminal", ("advisor",)), 1)
        self.assertEqual(s.value("telemetry_drop", ("invalid",)), 1)

        ticks = iter((0, 1000, 2000))
        t = recorder(clock=lambda: next(ticks), capacity=1)
        life = LIFECYCLE["invocation", "advisor"]
        n = MAX_VALUE // MAX_DURATION_US + 1
        t._cells[life.started] = t._cells[life.completed] = t._cells[life.outcomes["valid_point"]] = n
        end = life.latency.offset + life.latency.width
        t._cells[end - 3] = t._cells[end - 1] = n
        t._cells[end - 2] = MAX_VALUE
        self.assertFalse(t.finish(t.begin("invocation", "advisor"), "valid_point"))
        s = t.snapshot()
        s.validate()
        self.assertEqual(s.value("invocation_lost_terminal", ("advisor",)), 1)
        self.assertEqual(s.value("invocation_completed", ("advisor",)), n)
        self.assertEqual(s.value("telemetry_drop", ("numeric_overflow",)), 1)
        self.assertIsNotNone(t.begin("invocation", "advisor"))


class ContinuityTests(TestCase):
    def test_same_generation_out_of_order_marks_both_inconsistent_windows(self):
        t = recorder()
        t.begin("invocation", "advisor")
        r = collector(1)
        first = packet(t.snapshot(), 1)
        second = packet(recorder(60).snapshot(), 2)
        self.assertEqual(r.accept(second, source=1), "accepted")
        self.assertEqual(r.accept(first, source=1), "accepted")
        self.assertEqual(r.accept(second, source=1), "duplicate")
        windows = r.seal(120)
        for w in windows:
            self.assertEqual(w.coverage.continuity_mismatches, 1)
            self.assertEqual(status(w), Availability.INSUFFICIENT_EVIDENCE)
        self.assertEqual(r.accept(first, source=1), "late")

    def test_sealed_metadata_checks_next_arrival_without_rewriting_previous_result(self):
        t = recorder()
        t.begin("invocation", "advisor")
        r = collector(1)
        r.accept(packet(t.snapshot(), 1), source=1)
        first = r.seal(60)[0]
        r.accept(packet(recorder(60).snapshot(), 2), source=1)
        second = r.seal(120)[0]
        self.assertEqual(first.coverage.continuity_mismatches, 0)
        self.assertEqual(second.coverage.continuity_mismatches, 1)

    def test_missing_window_breaks_chain_and_no_old_replay_after_retention(self):
        r = collector(1)
        r.accept(packet(recorder().snapshot(), 1), source=1)
        r.accept(packet(recorder(120).snapshot(), 3), source=1)
        first, missing, future = r.seal(180)
        self.assertEqual(status(first), Availability.AVAILABLE)
        self.assertEqual(missing.coverage.missing_batches, 1)
        self.assertEqual(future.coverage.continuity_gaps, 1)
        self.assertEqual(status(future), Availability.INSUFFICIENT_EVIDENCE)
        self.assertEqual(r.accept(packet(recorder(60).snapshot(), 2), source=1), "late")

    def test_generation_restart_and_graceful_shutdown_avoid_false_mismatch(self):
        for graceful in (False, True):
            t = recorder()
            t.begin("invocation", "advisor")
            if graceful:
                t.stop()
            r = collector(1)
            r.accept(packet(t.snapshot(), 1), source=1)
            r.register_generation(1, 2, 60)
            r.accept(packet(recorder(60).snapshot(), 1, generation=2), source=1)
            first, second = r.seal(120)
            self.assertEqual(status(second), Availability.AVAILABLE)
            self.assertEqual(first.snapshot.value("invocation_outcome", ("advisor", "interrupted")), int(graceful))
            self.assertEqual(second.coverage.continuity_mismatches, 0)

    def test_individual_mismatches_are_not_cancelled_by_aggregate_gauges(self):
        a, b = recorder(), recorder()
        a.begin("invocation", "advisor")
        b_late = recorder()
        b_late.begin("invocation", "advisor")
        b_late.rotate()
        r = collector(1, 2)
        for snapshot, seq, source in ((a.snapshot(), 1, 1), (b.snapshot(), 1, 2),
                                      (recorder(60).snapshot(), 2, 1), (b_late.snapshot(), 2, 2)):
            self.assertEqual(r.accept(packet(snapshot, seq, source=source), source=source), "accepted")
        first, second = r.seal(120)
        self.assertEqual(first.snapshot.value("invocation_in_flight", ("advisor",)), 1)
        self.assertEqual(second.snapshot.value("invocation_opening_in_flight", ("advisor",)), 1)
        self.assertEqual(first.coverage.continuity_mismatches, 2)
        self.assertEqual(second.coverage.continuity_mismatches, 2)
