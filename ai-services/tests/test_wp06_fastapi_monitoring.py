"""Owned worker fixtures. No ASGI startup, model loading, or network."""

from hashlib import sha256
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace
from unittest import TestCase
from unittest.mock import patch

from app.api.valuation import health
from app.monitoring.accumulator import Availability
from app.monitoring.artifacts import FILES, V13_PINS, Integrity, verify_artifacts
from app.monitoring.batches import BatchQueue, SERVING, decode, encode
from app.monitoring.fastapi_adapter import (
    ApiOutcome, FastAPIWorker, Flags, LoadOutcome, PointOutcome, Readiness, Route, Stage,
    classify_health,
)
from app.monitoring.reducer import Reducer
from app.monitoring.schema import MAX_VALUE, UNATTRIBUTED


AI = (UNATTRIBUTED,)
NS = 1_000_000_000


class Clock:
    value = 0

    def __call__(self):
        return self.value


class HealthTests(TestCase):
    def test_actual_health_handler_shape_liveness_app_and_model_are_separate(self):
        worker = FastAPIWorker(Flags(operational=True))
        request = SimpleNamespace(app=SimpleNamespace(state=SimpleNamespace(
            predictor_v1_3=None, v1_3_error="fixture-private-path",
        )))
        body = health(request)
        self.assertIs(body["model_ready"], False)
        self.assertEqual(worker.observe_health(200, body, lifespan_ready=True),
                         Readiness("ready", "ready", "not_ready"))
        self.assertEqual(body["reason"], "fixture-private-path")
        request.app.state.predictor_v1_3 = object()
        self.assertEqual(worker.observe_health(200, health(request), lifespan_ready=True),
                         Readiness("ready", "ready", "ready"))
        self.assertEqual(worker.observe_health(503, {}, lifespan_ready=True),
                         Readiness("ready", "not_ready", "unknown"))
        self.assertEqual(worker.observe_health(None, {}, lifespan_ready=False),
                         Readiness("not_ready", "unknown", "unknown"))
        self.assertEqual(classify_health(200, {"model_ready": "true"}, lifespan_ready=True).model, "unknown")
        wrong_model = {"model_ready": True, "status": "ok", "model_version": "v6"}
        self.assertEqual(classify_health(200, wrong_model, lifespan_ready=True).model, "not_ready")
        self.assertEqual(classify_health(True, {}, lifespan_ready=True).process, "unknown")
        s = worker.recorder.snapshot()
        self.assertEqual(s.value("fastapi_health", ("app", "ready")), 2)
        self.assertEqual(s.value("fastapi_health", ("model", "ready")), 1)
        self.assertEqual(s.value("fastapi_health", ("model", "not_ready")), 1)
        self.assertEqual(s.value("api_request_started", AI), 0)
        self.assertEqual(s.value("invocation_started", AI), 0)

    def test_artifact_pins_match_official_manifest_and_disposable_mismatch_taxonomy(self):
        manifest = Path(__file__).resolve().parents[1] / "artifacts/v1_3.manifest.json"
        approved = json.loads(manifest.read_text(encoding="utf-8"))
        self.assertEqual(approved["model_version"], "v1.3")
        self.assertEqual(tuple(f["name"] for f in approved["files"]), tuple(name for name, _ in FILES))
        self.assertEqual(tuple((f["bytes"], f["sha256"]) for f in approved["files"]), V13_PINS)
        contents = tuple(bytes([i]) * (i + 2) for i in range(4))
        pins = tuple((len(data), sha256(data).hexdigest()) for data in contents)
        with TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertIs(verify_artifacts(root, pins=pins), Integrity.MISSING)
            for (name, _), data in zip(FILES, contents):
                (root / name).write_bytes(data)
            self.assertIs(verify_artifacts(root, pins=pins), Integrity.VERIFIED)
            for (name, mismatch), data in zip(FILES, contents):
                path = root / name
                path.write_bytes(b"X" + data[1:])
                self.assertIs(verify_artifacts(root, pins=pins), mismatch)
                path.write_bytes(data)
        worker = FastAPIWorker(Flags(operational=True))
        for value in (Integrity.VERIFIED, Integrity.MISSING, Integrity.FEATURE_SCHEMA,
                      Integrity.CALIBRATION, Integrity.MODEL_HASH, Integrity.MANIFEST):
            self.assertTrue(worker.observe_artifacts(value))
        for value in (LoadOutcome.FAILED, LoadOutcome.MISSING, LoadOutcome.SCHEMA,
                      LoadOutcome.CALIBRATION, LoadOutcome.UNSUPPORTED):
            self.assertTrue(worker.observe_load(value))
        self.assertFalse(worker.observe_load("fixture-private-exception"))
        s = worker.recorder.snapshot()
        self.assertEqual(s.value("artifact_integrity", ("verified",)), 1)
        self.assertEqual(s.value("model_integrity", ("ready",)), 0)
        self.assertEqual(s.value("model_integrity", ("unsupported_version",)), 1)


class AdapterTests(TestCase):
    def test_flag_off_is_noop_and_flags_can_be_enabled_independently(self):
        def unavailable():
            raise AssertionError("clock must not be called")

        off = FastAPIWorker(clock_ns=unavailable, wall="not read")
        self.assertIsNone(off.begin_api(Route.PRIMARY))
        with off.stage(Route.PRIMARY, Stage.POINT):
            result = 123
        self.assertEqual(result, 123)
        self.assertEqual(off.tick(None, None).status, "disabled")
        self.assertIsNone(off.recorder.snapshot())
        self.assertTrue(off.close())
        optional = FastAPIWorker(Flags(explanation=True, interval=True))
        self.assertIsNone(optional.begin_point(Route.PRIMARY))
        self.assertIs(optional.interval(Route.PRIMARY), Availability.NOT_ENABLED)
        self.assertTrue(optional.explanation(Route.PRIMARY, "PARTIAL", "1.0", "passed",
                                             duration_us=5, provenance=(1, 0, 2, 0, 0, 0)))
        self.assertTrue(optional.explanation(Route.PRIMARY, "UNAVAILABLE", "0.9", "not_checked"))
        self.assertFalse(optional.explanation(Route.PRIMARY, "arbitrary string", "1.0", "passed"))
        s = optional.recorder.snapshot()
        self.assertEqual(s.value("interval_status", (*AI, "not_enabled")), 1)
        self.assertEqual(s.value("explanation_status", (*AI, "partial")), 1)
        self.assertEqual(s.value("explanation_contract", (*AI, "mismatch", "not_checked")), 1)
        self.assertEqual(s.histogram("stage_latency", (*AI, "explanation")).count, 1)
        self.assertEqual(s.value("invocation_completed", AI), 0)
        self.assertIsNone(optional.window.queue)

    def test_population_is_selected_by_server_and_all_fapi_attribution_is_unknown(self):
        notices = {}
        for route in Route:
            w = FastAPIWorker(Flags(operational=True, exporter=True), population=route)
            for unauthorized in ("standalone", "advisor", "/predict", route.value, dict(surface="posting")):
                self.assertIsNone(w.begin_api(unauthorized))
            for wrong in Route:
                if wrong is not route:
                    self.assertIsNone(w.begin_point(wrong))
            self.assertTrue(w.finish_api(w.begin_api(route), ApiOutcome.ACCEPTED))
            result = w.tick(60, 60 * NS)
            self.assertEqual(result.status, "published")
            wire = w.window.queue.pop()
            batch = decode(wire)
            notices[route] = batch.identity.population
            self.assertEqual(batch.snapshot.value("api_request_completed", AI), 1)
            self.assertEqual(batch.snapshot.value("surface_completed", ("standalone",)), 0)
            self.assertEqual(batch.snapshot.value("surface_completed", ("posting",)), 0)
            self.assertEqual(batch.snapshot.value("surface_completed", ("advisor",)), 0)
            wrong_pop = Reducer((1,), population=SERVING if route is not Route.PRIMARY else Route.INTERNAL.value,
                                watermark=0)
            wrong_pop.register_generation(1, 1, 0)
            self.assertEqual(wrong_pop.accept(wire, source=1), "untrusted")
        self.assertEqual(len(set(notices.values())), 4)

    def test_admission_validation_unavailable_and_invocation_timing_are_distinct(self):
        clock = Clock()
        worker = FastAPIWorker(Flags(operational=True), clock_ns=clock)
        for stage in Stage:
            with worker.stage(Route.PRIMARY, stage):
                clock.value += 3456
        for rejection in (ApiOutcome.VALIDATION, ApiOutcome.MODEL_UNAVAILABLE):
            self.assertTrue(worker.finish_api(worker.begin_api(Route.PRIMARY), rejection))
        request = worker.begin_api(Route.PRIMARY)
        point = worker.begin_point(Route.PRIMARY)
        self.assertFalse(worker.finish_api(point, ApiOutcome.INTERRUPTED))
        self.assertFalse(worker.finish_point(request, PointOutcome.INTERRUPTED))
        clock.value += 12 * NS  # Upstream caller timed out. The model finishes independently.
        self.assertTrue(worker.finish_output(point, 3_200_000_001, "v1.3"))
        self.assertTrue(worker.finish_api(request, ApiOutcome.ACCEPTED))
        self.assertTrue(worker.finish_output(worker.begin_point(Route.PRIMARY), True, "v1.3"))
        self.assertTrue(worker.finish_output(worker.begin_point(Route.PRIMARY), MAX_VALUE + 1, "v1.3"))
        self.assertTrue(worker.finish_point(worker.begin_point(Route.PRIMARY), PointOutcome.EXCEPTION))
        worker.begin_point(Route.PRIMARY)
        self.assertTrue(worker.close())
        s = worker.recorder.snapshot()
        s.validate()
        self.assertEqual(s.value("api_request_started", AI), 3)
        self.assertEqual(s.value("api_request_outcome", (*AI, "validation_rejection")), 1)
        self.assertEqual(s.value("api_request_outcome", (*AI, "model_unavailable")), 1)
        self.assertEqual(s.value("invocation_outcome", (*AI, "valid_point")), 1)
        self.assertEqual(s.value("invocation_outcome", (*AI, "invalid_output")), 2)
        self.assertEqual(s.value("invocation_outcome", (*AI, "inference_exception")), 1)
        self.assertEqual(s.value("invocation_outcome", (*AI, "interrupted")), 1)
        self.assertEqual(s.value("dispatch_completed", ("standalone",)), 0)
        self.assertEqual(s.histogram("api_request_latency", AI).count, 3)
        self.assertEqual(s.histogram("stage_latency", (*AI, "options")).count, 1)
        self.assertEqual(s.histogram("stage_latency", (*AI, "adapter")).total, 3)

    def test_telemetry_faults_leave_fixture_business_output_and_errors_intact(self):
        worker = FastAPIWorker(Flags(operational=True, exporter=True))
        payload = {"model_version": "v1.3", "predicted_asking_price_vnd": 3_200_000_001}
        calls = []

        def fixture():
            point = worker.begin_point(Route.PRIMARY)
            with worker.stage(Route.PRIMARY, Stage.POINT):
                calls.append("actual_point")
                result = payload
            worker.finish_output(point, result["predicted_asking_price_vnd"], result["model_version"])
            return result

        with patch.object(worker.recorder, "begin", side_effect=RuntimeError("fixture-exception")):
            self.assertIs(fixture(), payload)
        with patch.object(worker.recorder, "finish", side_effect=RuntimeError("fixture-exception")):
            self.assertIs(fixture(), payload)
        with patch.object(worker.recorder, "record", side_effect=RuntimeError("fixture-exception")):
            self.assertIs(fixture(), payload)
            with self.assertRaisesRegex(LookupError, "business-only"):
                with worker.stage(Route.PRIMARY, Stage.ADAPTER):
                    raise LookupError("business-only")
        self.assertEqual(calls, ["actual_point"] * 3)
        s = worker.recorder.snapshot()
        self.assertEqual(s.value("invocation_lost_terminal", AI), 1)
        self.assertEqual(s.value("invocation_in_flight", AI), 0)
        self.assertGreater(s.value("telemetry_drop", ("monitor_fault",)), 0)
        with patch.object(worker.window, "tick", side_effect=RuntimeError("fixture-exception")):
            self.assertEqual(worker.tick(60, 60 * NS).status, "unavailable")
        with patch.object(worker.window, "shutdown", side_effect=RuntimeError("fixture-exception")):
            self.assertFalse(worker.close())
        self.assertTrue(worker.close())


class WindowTests(TestCase):
    def test_delayed_skipped_boundaries_and_mid_window_boot_do_not_publish_gaps(self):
        worker = FastAPIWorker(Flags(operational=True, exporter=True), wall=7, mono=7 * NS, generation=2)
        self.assertEqual(worker.tick(60, 60 * NS).status, "gap")
        self.assertEqual(worker.tick(120, 120 * NS).status, "published")
        self.assertEqual(worker.tick(120, 120 * NS).status, "unchanged")
        self.assertEqual(worker.tick(183, 183 * NS).status, "gap")
        self.assertEqual(worker.tick(240, 240 * NS).status, "gap")
        self.assertEqual(worker.tick(300, 300 * NS).status, "published")
        produced = [worker.window.queue.pop(), worker.window.queue.pop()]
        self.assertEqual([(decode(p).snapshot.start, decode(p).identity.sequence) for p in produced],
                         [(60, 2), (240, 5)])
        r = Reducer((1,), population=SERVING, watermark=0)
        r.register_generation(1, 2, 0)
        for p in produced:
            r.accept(p, source=1)
        result = r.seal(300)
        self.assertEqual([w.coverage.received_batches for w in result], [0, 1, 0, 0, 1])
        self.assertEqual(result[-1].coverage.continuity_gaps, 1)
        self.assertTrue(worker.close())
        self.assertEqual(worker.tick(360, 360 * NS).status, "stopped")
        self.assertIsNone(worker.window.queue.pop())

    def test_backward_and_forward_clock_jumps_invalidate_windows(self):
        worker = FastAPIWorker(Flags(exporter=True))
        self.assertEqual(worker.tick(30, 30 * NS).status, "unchanged")
        self.assertEqual(worker.tick(28, 31 * NS).status, "clock_discontinuity")
        self.assertEqual(worker.tick(60, 60 * NS).status, "gap")
        self.assertEqual(worker.tick(180, 61 * NS).status, "gap")
        self.assertEqual(worker.tick(240, 121 * NS).status, "gap")
        self.assertEqual(worker.tick(300, 181 * NS).status, "published")
        packet = decode(worker.window.queue.pop())
        self.assertEqual(packet.identity.sequence, 5)
        self.assertEqual(packet.snapshot.start, 240)
        self.assertIsNone(worker.window.queue.pop())

    def test_full_queue_and_collector_failure_keep_sequence_and_reject_late_retries(self):
        worker = FastAPIWorker(Flags(operational=True, exporter=True))
        worker.window.queue = BatchQueue(capacity=1)
        self.assertEqual(worker.tick(60, 60 * NS).status, "published")
        self.assertEqual(worker.tick(120, 120 * NS).status, "dropped")
        first = worker.window.queue.pop()
        self.assertEqual(worker.tick(180, 180 * NS).status, "published")
        third = worker.window.queue.pop()
        self.assertEqual(decode(third).identity.sequence, 3)
        self.assertEqual(decode(third).snapshot.value("telemetry_drop", ("queue_full",)), 1)
        r = Reducer((1,), population=SERVING, watermark=0)
        r.register_generation(1, 1, 0)
        with patch.object(r, "accept", side_effect=RuntimeError("collector outage")):
            self.assertEqual(worker.tick(240, 240 * NS).status, "published")
        self.assertEqual(r.accept(first, source=1), "accepted")
        self.assertEqual(r.accept(third, source=1), "accepted")
        windows = r.seal(240)
        self.assertEqual(windows[1].coverage.missing_batches, 1)
        self.assertEqual(windows[2].coverage.dropped_observations, 1)
        self.assertEqual(r.accept(encode(decode(first).identity, decode(first).snapshot), source=1), "late")
