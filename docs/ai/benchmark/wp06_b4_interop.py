"""Synthetic cross-language contract checks. No sockets, dataset or app startup."""

from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[3]
FIXTURE = ROOT / "backend/src/test/resources/wp06/b4-aggregate.hex"
sys.path.insert(0, str(ROOT / "ai-services"))

from app.monitoring.accumulator import Availability
from app.monitoring.batches import BatchIdentity, SERVING, SYNTHETIC, decode, encode
from app.monitoring.core import Telemetry, TelemetryConfig
from app.monitoring.reducer import Reducer
from app.monitoring.schema import InvalidTelemetry, REGISTRY


class Clock:
    value = 0

    def __call__(self):
        return self.value


def spring_fixture_reference():
    """Construct the byte-identical reference through the accepted Python core."""
    clock = Clock()
    recorder = Telemetry(TelemetryConfig(enabled=True), clock_ns=clock)
    consult = recorder.begin("surface", "advisor")
    candidate = recorder.begin("candidate", "advisor")
    clock.value = 2_000_000
    assert recorder.finish(candidate, "eligible")
    opportunity = recorder.begin("opportunity", "advisor")
    dispatch = recorder.begin("dispatch", "advisor")
    clock.value = 20_000_000
    assert recorder.finish(dispatch, "timeout")
    retry = recorder.begin("dispatch", "advisor")
    assert recorder.record("retry", ("advisor", "transport"))
    first = recorder.rotate()
    clock.value = 36_000_000
    assert recorder.finish(retry, "ai_response")
    assert recorder.finish(opportunity, "valid_point")
    assert recorder.finish(consult, "served")
    second = recorder.rotate()
    return tuple(encode(BatchIdentity(3, 7, SYNTHETIC, index), window)
                 for index, window in enumerate((first, second), 1))


class SpringAggregateContract(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.low, cls.high = map(bytes.fromhex, FIXTURE.read_text(encoding="ascii").splitlines())

    def reducer(self, producers=(3,), population=SYNTHETIC):
        collector = Reducer(producers, population=population, watermark=0)
        collector.register_generation(3, 7, 0)
        return collector

    def test_java_bytes_match_reference_and_histogram_units(self):
        self.assertEqual((self.low, self.high), spring_fixture_reference())
        first, second = decode(self.low), decode(self.high)
        self.assertEqual((first.identity.sequence, second.identity.sequence), (1, 2))
        self.assertEqual((first.snapshot.start, first.snapshot.end, second.snapshot.end), (0, 60, 120))
        self.assertEqual(first.snapshot.value("dispatch_outcome", ("advisor", "timeout")), 1)
        self.assertEqual(first.snapshot.value("retry", ("advisor", "transport")), 1)
        h = first.snapshot.histogram("dispatch_latency", ("advisor",))
        self.assertEqual((h.unit, h.total, h.count), ("us", 18_000, 1))
        self.assertEqual(second.snapshot.histogram("dispatch_latency", ("advisor",)).total, 16_000)
        self.assertEqual(first.snapshot.value("invocation_started", ("unattributed",)), 0)
        self.assertEqual(REGISTRY.size, 3986)

    def test_timeout_and_successful_downstream_inference_remain_independent(self):
        collector = self.reducer((3, 4))
        collector.register_generation(4, 1, 0)
        clock = Clock()
        ai = Telemetry(TelemetryConfig(enabled=True), clock_ns=clock)
        point = ai.begin("invocation", "unattributed")
        clock.value = 28_000_000
        self.assertTrue(ai.finish(point, "valid_point"))
        self.assertEqual(collector.accept(self.high, source=3), "accepted")
        self.assertEqual(collector.accept(self.low, source=3), "accepted")
        self.assertEqual(collector.accept(encode(BatchIdentity(4, 1, SYNTHETIC, 1), ai.rotate()), source=4),
                         "accepted")
        self.assertEqual(collector.accept(encode(BatchIdentity(4, 1, SYNTHETIC, 2), ai.rotate()), source=4),
                         "accepted")
        low, high = collector.seal(120)
        self.assertEqual(low.snapshot.value("dispatch_outcome", ("advisor", "timeout")), 1)
        self.assertEqual(low.snapshot.value("invocation_outcome", ("unattributed", "valid_point")), 1)
        self.assertEqual(low.snapshot.value("surface_completed", ("advisor",)), 0)
        self.assertEqual(high.snapshot.value("dispatch_outcome", ("advisor", "ai_response")), 1)
        self.assertEqual(high.snapshot.value("invocation_completed", ("unattributed",)), 0)
        self.assertEqual(high.snapshot.value("opportunity_outcome", ("advisor", "valid_point")), 1)
        for window in (low, high):
            self.assertEqual(window.coverage.batch_coverage, 1)
            self.assertEqual(window.coverage.continuity_mismatches, 0)
            self.assertEqual(window.coverage.lost_terminals, 0)

    def test_bad_schema_population_and_trusted_binding(self):
        incompatible = self.low[:4] + b"\x04" + self.low[5:]
        with self.assertRaisesRegex(InvalidTelemetry, "incompatible_schema"):
            decode(incompatible)
        self.assertEqual(self.reducer().accept(incompatible, source=3), "invalid")
        self.assertEqual(self.reducer(population=SERVING).accept(self.low, source=3), "untrusted")
        collector = self.reducer((3, 4))
        collector.register_generation(4, 1, 0)
        self.assertEqual(collector.accept(self.low, source=4), "untrusted")
        self.assertEqual(collector.accept(self.low, source=99), "untrusted")

    def test_duplicate_late_missing_and_generation_changes(self):
        collector = self.reducer()
        self.assertEqual(collector.accept(self.high, source=3), "accepted")
        self.assertEqual(collector.accept(self.high, source=3), "duplicate")
        missing, following = collector.seal(120)
        self.assertEqual(missing.coverage.missing_batches, 1)
        self.assertEqual(following.coverage.continuity_gaps, 1)
        for window in (missing, following):
            self.assertEqual(window.coverage.status(now=120, max_age=120, samples=30, min_samples=30),
                             Availability.INSUFFICIENT_EVIDENCE)
        self.assertEqual(collector.accept(self.low, source=3), "late")
        collector.register_generation(3, 8, 120)
        recorder = Telemetry(TelemetryConfig(enabled=True), start=120)
        first = recorder.rotate()
        self.assertEqual(collector.accept(encode(BatchIdentity(3, 7, SYNTHETIC, 3), first), source=3),
                         "old_generation")
        self.assertEqual(collector.accept(encode(BatchIdentity(3, 8, SYNTHETIC, 3), first), source=3), "sequence")
        self.assertEqual(collector.accept(encode(BatchIdentity(3, 8, SYNTHETIC, 1), first), source=3), "accepted")
        self.assertEqual(collector.seal(180)[0].coverage.continuity_gaps, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
