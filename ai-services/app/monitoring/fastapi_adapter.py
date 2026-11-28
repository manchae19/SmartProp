"""Isolated hooks for an owned FastAPI worker. Importing this installs no hooks."""

from contextlib import contextmanager
from dataclasses import dataclass, fields
from enum import Enum
from time import monotonic_ns

from .accumulator import WINDOW_SECONDS, Availability
from .artifacts import Integrity
from .batches import HISTORICAL, INTERNAL, PREVIEW, SERVING, BatchIdentity
from .core import Telemetry, TelemetryConfig
from .drift import DriftResult, compare
from .input_quality import record_feature_facts
from .schema import UNATTRIBUTED, InvalidTelemetry, integer
from .windowing import MAX_TICK_NS, Rotation, WindowCoordinator, valid_sample


class Route(Enum):
    # Choose these in authorized server code. A request field/header is never a source of attribution.
    PRIMARY = SERVING
    PREVIEW = PREVIEW
    INTERNAL = INTERNAL
    HISTORICAL_COMPAT = HISTORICAL


class ApiOutcome(str, Enum):
    ACCEPTED = "accepted"
    VALIDATION = "validation_rejection"
    MODEL_UNAVAILABLE = "model_unavailable"
    FAILED = "failed"
    INTERRUPTED = "interrupted"


class PointOutcome(str, Enum):
    VALID = "valid_point"
    INVALID = "invalid_output"
    EXCEPTION = "inference_exception"
    INTERRUPTED = "interrupted"


class LoadOutcome(str, Enum):
    READY = "ready"
    MISSING = "missing_file"
    ARTIFACT = "hash_mismatch"
    SCHEMA = "schema_mismatch"
    CALIBRATION = "calibration_mismatch"
    FAILED = "load_error"
    RELEASE_MISMATCH = "release_mismatch"
    UNSUPPORTED = "unsupported_version"


class Stage(str, Enum):
    MODEL_LOAD = "model_load"
    ADAPTER = "adapter"
    FEATURE_PREP = "feature_prep"
    POINT = "point"
    CALIBRATION = "calibration"
    OPTIONS = "options"
    HEALTH = "health"


@dataclass(frozen=True, slots=True)
class Flags:
    operational: bool = False
    input_quality: bool = False
    drift: bool = False
    explanation: bool = False
    interval: bool = False
    exporter: bool = False

    def __post_init__(self):
        if any(type(getattr(self, field.name)) is not bool for field in fields(self)):
            raise InvalidTelemetry("invalid_worker_flags")


@dataclass(frozen=True, slots=True)
class Readiness:
    process: str
    app: str
    model: str


def classify_health(http_status, response, *, lifespan_ready):
    """Only the existing status fields are inspected. Reason/detail do not enter telemetry."""
    if http_status is None:
        return Readiness("not_ready", "unknown", "unknown")
    if not integer(http_status, 599) or http_status < 100 or type(lifespan_ready) is not bool:
        return Readiness("unknown", "unknown", "unknown")
    if not lifespan_ready or not 200 <= http_status < 300:
        return Readiness("ready", "not_ready", "unknown")
    model = "unknown"
    if type(response) is dict:
        ready, version, state = (response.get(name) for name in ("model_ready", "model_version", "status"))
        if ready is False or (type(version) is str and version != "v1.3") or (type(state) is str and state == "degraded"):
            model = "not_ready"
        elif ready is True and type(version) is str and version == "v1.3" and type(state) is str and state == "ok":
            model = "ready"
    return Readiness("ready", "ready", model)


_EXPLANATION = {
    "AVAILABLE": "available", "PARTIAL": "partial", "UNAVAILABLE": "not_available",
    "NOT_SUPPORTED": "not_supported", "NOT_ENABLED": "not_enabled",
}


class FastAPIWorker:
    """One recorder, fixed population, no interpretation of incoming caller identity."""

    def __init__(self, flags=Flags(), *, population=Route.PRIMARY, producer=1, generation=1,
                 wall=0, mono=0, clock_ns=monotonic_ns):
        if type(flags) is not Flags or type(population) is not Route:
            raise InvalidTelemetry("invalid_worker_config")
        self.flags = flags
        self.population = population
        enabled = any((flags.operational, flags.input_quality, flags.explanation, flags.interval, flags.exporter))
        self._clock = clock_ns
        self.window = None
        if not enabled:
            self.recorder = Telemetry()
            return
        if not valid_sample(wall, mono):
            raise InvalidTelemetry("invalid_worker_window")
        self.recorder = Telemetry(TelemetryConfig(True, nonblocking=True),
                                  start=wall - wall % WINDOW_SECONDS, clock_ns=clock_ns)
        identity = BatchIdentity(producer, generation, population.value, 1)
        self.window = WindowCoordinator(self.recorder, identity, wall=wall, mono=mono, export=flags.exporter)

    def _safe(self, operation, *args, **kwargs):
        try:
            return operation(*args, **kwargs)
        except Exception:
            self._drop("monitor_fault")
            return None

    def _drop(self, reason):
        try:
            self.recorder.drop(reason)
        except Exception:
            pass

    def _same_population(self, route):
        return type(route) is Route and route is self.population

    def tick(self, wall, mono):
        if self.window is None:
            return Rotation("disabled")
        return self._safe(self.window.tick, wall, mono) or Rotation("unavailable")

    def close(self):
        return self.window is None or bool(self._safe(self.window.shutdown))

    def observe_health(self, http_status, response, *, lifespan_ready):
        result = classify_health(http_status, response, lifespan_ready=lifespan_ready)
        if self.flags.operational:
            self._safe(self.recorder.readiness, result.process, result.app, result.model)
        return result

    def observe_load(self, outcome):
        if self.flags.operational and type(outcome) is LoadOutcome:
            return self._safe(self.recorder.record, "model_integrity", (outcome.value,))
        return False

    def observe_artifacts(self, integrity):
        if self.flags.operational and type(integrity) is Integrity:
            return self._safe(self.recorder.record, "artifact_integrity", (integrity.value,))
        return False

    def begin_api(self, route):
        if self.flags.operational and self._same_population(route):
            return self._safe(self.recorder.begin, "api_request", UNATTRIBUTED)
        return None

    def finish_api(self, ticket, outcome):
        if self.flags.operational and ticket is not None and type(outcome) is ApiOutcome:
            return self._finish(ticket, outcome.value, "api_request")
        return False

    def begin_point(self, route):
        if self.flags.operational and self._same_population(route):
            return self._safe(self.recorder.begin, "invocation", UNATTRIBUTED)
        return None

    def finish_point(self, ticket, outcome):
        if self.flags.operational and ticket is not None and type(outcome) is PointOutcome:
            return self._finish(ticket, outcome.value, "invocation")
        return False

    def _finish(self, ticket, outcome, kind):
        try:
            return self.recorder.finish(ticket, outcome, kind=kind)
        except Exception:
            if not self._safe(self.recorder.abandon, ticket):
                self._drop("monitor_fault")
            return False

    def finish_output(self, ticket, authoritative_vnd, model_version):
        if not self.flags.operational or ticket is None:
            return False
        valid = (integer(authoritative_vnd) and authoritative_vnd > 0
                 and type(model_version) is str and model_version == "v1.3")
        return self.finish_point(ticket, PointOutcome.VALID if valid else PointOutcome.INVALID)

    def _sample_ns(self):
        now = self._clock()
        if not integer(now, MAX_TICK_NS):
            raise InvalidTelemetry("invalid_clock")
        return now

    @contextmanager
    def stage(self, route, stage):
        if not self.flags.operational or not self._same_population(route) or type(stage) is not Stage:
            yield
            return
        start = self._safe(self._sample_ns)
        try:
            yield
        finally:
            stop = self._safe(self._sample_ns) if start is not None else None
            if stop is not None:
                if stop >= start:
                    self._safe(self.recorder.record, "stage_latency", (UNATTRIBUTED, stage.value), (stop - start) // 1000)
                else:
                    self._drop("clock_discontinuity")

    def explanation(self, route, status, version, check, *, duration_us=None, provenance=()):
        if not self.flags.explanation or not self._same_population(route):
            return False
        state = _EXPLANATION.get(status) if type(status) is str and len(status) <= 40 else None
        if state is None:
            self._drop("invalid")
            return False
        contract = "absent" if version is None else "wp04_v1" if type(version) is str and version == "1.0" else "mismatch"
        return self._safe(self.recorder.explanation, UNATTRIBUTED, state, contract, check,
                          duration_us=duration_us, provenance=provenance)

    def interval(self, route):
        # WP-05 has no authorized calibration. This observer cannot issue intervals.
        if self.flags.interval and self._same_population(route):
            self._safe(self.recorder.interval, UNATTRIBUTED, "not_enabled")
        return Availability.NOT_ENABLED

    def input_quality(self, route, property_kind, mode, district, facts):
        if self.flags.input_quality and self._same_population(route):
            return self._safe(record_feature_facts, self.recorder, property_kind, mode, district, facts)
        return False

    def compare_drift(self, window, reference, *, now, max_age, min_samples=100):
        if not self.flags.drift:
            return DriftResult(Availability.NOT_ENABLED)
        return (self._safe(compare, window, reference, now=now, max_age=max_age,
                           min_samples=min_samples, enabled=True) or DriftResult(Availability.NOT_AVAILABLE))
