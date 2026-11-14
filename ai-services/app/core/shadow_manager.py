"""Shadow mode execution manager, concurrency limiter, and telemetry aggregator.

Provides non-blocking, bounded execution of V1.3 alongside live V6 predictions.
Guarantees zero production impact on V6 client responses through:
- Bounded concurrency pool (max 2 worker threads)
- Multi-worker state synchronization via shared atomic state file
- Queue backpressure shedding (circuit breaker on queue saturation)
- Automatic error circuit breaker with cooldown
- Configurable traffic sampling rate
- Strict PII data exclusion
"""
import concurrent.futures
import json
import logging
import math
import os
import random
import time
import uuid
from collections import deque
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger("smartprop.shadow")

DEFAULT_LOG_PATH = Path(__file__).resolve().parents[3] / ".scratch" / "shadow_telemetry" / "shadow_events.jsonl"
DEFAULT_STATE_PATH = Path(__file__).resolve().parents[3] / ".scratch" / "shadow_telemetry" / "shadow_state.json"


class ShadowTelemetryManager:
    """Thread-safe telemetry collector, multi-worker synchronizer, and circuit breaker."""

    def __init__(
        self,
        enabled: Optional[bool] = None,
        max_buffer_size: int = 2000,
        max_workers: int = 2,
        max_queue_depth: int = 10,
        sample_rate: float = 1.0,
        log_file_path: Optional[Path] = None,
        state_file_path: Optional[Path] = None,
    ):
        self.state_file_path = state_file_path or DEFAULT_STATE_PATH
        self.state_file_path.parent.mkdir(parents=True, exist_ok=True)

        # 1. Circuit breaker & state synchronization internals
        self.circuit_open = False
        self.circuit_trip_time = 0.0
        self.circuit_cooldown_sec = 30.0
        self.consecutive_errors = 0
        self.max_consecutive_errors = 5
        self._last_state_updated = time.time()
        self._last_state_check = 0.0

        # 2. Environment-based or explicit enablement
        if enabled is None:
            # Check state file first, then environment variable
            persisted = self._read_persisted_state()
            if persisted and "enabled" in persisted:
                self._enabled = bool(persisted["enabled"])
            else:
                env_val = os.environ.get("SMARTPROP_SHADOW_MODE_ENABLED", "false").lower()
                self._enabled = env_val in ("1", "true", "yes", "on")
        else:
            self._enabled = bool(enabled)
            self._persist_state()

        # 3. Concurrency and queue limits
        self.max_workers = max_workers
        self.max_queue_depth = max_queue_depth
        self.sample_rate = float(os.environ.get("SMARTPROP_SHADOW_SAMPLE_RATE", sample_rate))
        self._in_flight_tasks = 0

        # Dedicated isolated thread pool for shadow tasks
        self._executor = concurrent.futures.ThreadPoolExecutor(
            max_workers=self.max_workers,
            thread_name_prefix="shadow_worker"
        )

        # 4. Storage & Metrics
        self.max_buffer_size = max_buffer_size
        self.log_file_path = log_file_path or DEFAULT_LOG_PATH
        self.events_buffer: deque = deque(maxlen=max_buffer_size)

        # Running counters
        self.total_requests = 0
        self.shadow_runs = 0
        self.shadow_errors = 0
        self.dropped_tasks_queue_full = 0
        self.dropped_tasks_circuit_open = 0
        self.dropped_tasks_sampling = 0
        self.last_error_message: Optional[str] = None

        if self.log_file_path:
            self.log_file_path.parent.mkdir(parents=True, exist_ok=True)

    def _read_persisted_state(self) -> Optional[Dict[str, Any]]:
        """Read shared state across multiple worker processes."""
        try:
            if self.state_file_path.exists():
                return json.loads(self.state_file_path.read_text(encoding="utf-8"))
        except Exception:
            pass
        return None

    def _persist_state(self) -> None:
        """Write current state to atomic JSON file shared by all workers."""
        try:
            now = time.time()
            self._last_state_updated = now
            state_data = {
                "enabled": self._enabled,
                "circuit_open": getattr(self, "circuit_open", False),
                "circuit_trip_time": getattr(self, "circuit_trip_time", 0.0),
                "updated_at": now,
            }
            tmp = self.state_file_path.with_suffix(".tmp")
            tmp.write_text(json.dumps(state_data), encoding="utf-8")
            tmp.replace(self.state_file_path)
        except Exception as e:
            logger.warning(f"Failed to persist shadow state: {e}")

    def _sync_state_if_needed(self) -> None:
        """Lightweight sync across processes (checked at most once every 0.5s)."""
        now = time.time()
        if now - self._last_state_check > 0.5:
            self._last_state_check = now
            persisted = self._read_persisted_state()
            if persisted:
                file_updated_at = float(persisted.get("updated_at", 0.0))
                if file_updated_at > self._last_state_updated:
                    self._last_state_updated = file_updated_at
                    if "enabled" in persisted:
                        self._enabled = bool(persisted["enabled"])
                    if "circuit_open" in persisted:
                        self.circuit_open = bool(persisted["circuit_open"])
                        self.circuit_trip_time = float(persisted.get("circuit_trip_time", 0.0))

    def is_enabled(self) -> bool:
        """Check if shadow mode is currently active and not tripped by circuit breaker."""
        self._sync_state_if_needed()

        if not self._enabled:
            return False

        # Check circuit breaker cooldown
        if self.circuit_open:
            if time.time() - self.circuit_trip_time > self.circuit_cooldown_sec:
                logger.info("[Shadow Circuit Breaker] Cooldown expired; entering half-open probe state.")
                self.circuit_open = False
                self.consecutive_errors = 0
                self._persist_state()
            else:
                return False

        return True

    def set_enabled(self, active: bool) -> None:
        """Dynamically toggle shadow mode on/off and sync to shared state file."""
        self._enabled = bool(active)
        if not self._enabled:
            self.circuit_open = False
            self.consecutive_errors = 0
        self._persist_state()
        logger.info(f"SmartProp Shadow Mode set to: {self._enabled} (synced across workers)")

    def reset_stats(self) -> None:
        """Reset internal metrics buffer, counters, and circuit breaker."""
        self.events_buffer.clear()
        self.total_requests = 0
        self.shadow_runs = 0
        self.shadow_errors = 0
        self.dropped_tasks_queue_full = 0
        self.dropped_tasks_circuit_open = 0
        self.dropped_tasks_sampling = 0
        self.consecutive_errors = 0
        self.circuit_open = False
        self.last_error_message = None
        self._persist_state()

    def record_shadow_evaluation(
        self,
        predictor_v1_3: Any,
        v6_payload: Dict[str, Any],
        v6_response: Dict[str, Any],
        v6_latency_ms: float = 0.0,
    ) -> None:
        """Entry point called by BackgroundTasks. Enforces queue bounds and circuit breaker.

        CRITICAL: Never raises an exception to the caller.
        """
        self.total_requests += 1

        if not self.is_enabled():
            return

        # Check circuit breaker
        if self.circuit_open:
            if time.time() - self.circuit_trip_time < self.circuit_cooldown_sec:
                self.dropped_tasks_circuit_open += 1
                return
            else:
                self.circuit_open = False
                self._persist_state()

        # Check sampling rate
        if self.sample_rate < 1.0 and random.random() > self.sample_rate:
            self.dropped_tasks_sampling += 1
            return

        # Check queue depth backpressure
        if self._in_flight_tasks >= self.max_queue_depth:
            self.dropped_tasks_queue_full += 1
            logger.warning(
                f"[Shadow Backpressure] In-flight tasks ({self._in_flight_tasks}) >= limit ({self.max_queue_depth}). Dropping task."
            )
            return

        # Dispatch task to worker pool
        self._in_flight_tasks += 1
        try:
            self._executor.submit(
                self._execute_shadow_worker,
                predictor_v1_3=predictor_v1_3,
                v6_payload=v6_payload,
                v6_response=v6_response,
                v6_latency_ms=v6_latency_ms,
            )
        except Exception as exc:
            self._in_flight_tasks = max(0, self._in_flight_tasks - 1)
            logger.error(f"[Shadow Dispatch Error] Failed to submit task: {exc}")

    def _execute_shadow_worker(
        self,
        predictor_v1_3: Any,
        v6_payload: Dict[str, Any],
        v6_response: Dict[str, Any],
        v6_latency_ms: float,
    ) -> Optional[Dict[str, Any]]:
        """Worker thread executing V1.3 inference and logging telemetry."""
        t0 = time.perf_counter()
        req_id = str(uuid.uuid4())[:8]

        try:
            # 1. Run V1.3 inference
            v1_3_res = predictor_v1_3.predict_from_v6_payload(v6_payload)
            v1_3_latency_ms = (time.perf_counter() - t0) * 1000.0

            # 2. Extract price metrics
            v6_price = float(v6_response.get("predicted_asking_price_vnd", 0.0))
            v1_3_price = float(v1_3_res.get("predicted_asking_price_vnd", 0.0))

            diff_pct = 0.0
            if v6_price > 0:
                diff_pct = ((v1_3_price - v6_price) / v6_price) * 100.0

            # 3. Privacy-safe telemetry record (Strict PII exclusion)
            event = {
                "request_id": req_id,
                "timestamp": time.time(),
                "category": v6_payload.get("category"),
                "area_sqm": float(v6_payload.get("area_sqm", 0.0)),
                "district": v1_3_res.get("features_used", {}).get("district"),
                "ward": v1_3_res.get("features_used", {}).get("ward"),
                "v6_price_vnd": int(v6_price),
                "v1_3_price_vnd": int(v1_3_price),
                "v6_price_billion": round(v6_price / 1e9, 3),
                "v1_3_price_billion": round(v1_3_price / 1e9, 3),
                "diff_pct": round(diff_pct, 2),
                "v6_latency_ms": round(v6_latency_ms, 2),
                "v1_3_latency_ms": round(v1_3_latency_ms, 2),
                "v1_3_band": v1_3_res.get("price_band"),
                "duan_factor": v1_3_res.get("calibration_factor"),
                "missing_features": v1_3_res.get("missing_features", []),
                "success": True,
            }

            self.shadow_runs += 1
            self.consecutive_errors = 0
            self.events_buffer.append(event)
            self._append_to_file(event)
            return event

        except Exception as exc:
            self.shadow_errors += 1
            self.consecutive_errors += 1
            self.last_error_message = str(exc)
            logger.error(f"[Shadow Worker Error] Request {req_id} failed: {exc}", exc_info=True)

            # Check circuit breaker trigger
            if self.consecutive_errors >= self.max_consecutive_errors:
                self.circuit_open = True
                self.circuit_trip_time = time.time()
                self._persist_state()
                logger.error(
                    f"[Shadow Circuit Breaker Tripped] {self.consecutive_errors} consecutive failures. Pausing shadow for {self.circuit_cooldown_sec}s."
                )

            error_event = {
                "request_id": req_id,
                "timestamp": time.time(),
                "category": v6_payload.get("category"),
                "error": str(exc),
                "success": False,
            }
            self.events_buffer.append(error_event)
            self._append_to_file(error_event)
            return None
        finally:
            self._in_flight_tasks = max(0, self._in_flight_tasks - 1)

    def _append_to_file(self, event: Dict[str, Any]) -> None:
        """Write event to persistent JSONL log file safely."""
        try:
            with open(self.log_file_path, "a", encoding="utf-8") as f:
                f.write(json.dumps(event, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to append to shadow log: {e}")

    def get_summary_statistics(self) -> Dict[str, Any]:
        """Aggregate statistical summary from the rolling buffer."""
        successful = [e for e in self.events_buffer if e.get("success")]
        total_in_buffer = len(self.events_buffer)

        base_stats = {
            "shadow_enabled": self._enabled,
            "circuit_breaker": {
                "is_open": self.circuit_open,
                "consecutive_errors": self.consecutive_errors,
                "cooldown_remaining_sec": max(0.0, round(self.circuit_cooldown_sec - (time.time() - self.circuit_trip_time), 1)) if self.circuit_open else 0.0,
            },
            "queue_status": {
                "in_flight_tasks": self._in_flight_tasks,
                "max_queue_depth": self.max_queue_depth,
                "dropped_queue_full": self.dropped_tasks_queue_full,
                "dropped_circuit_open": self.dropped_tasks_circuit_open,
                "dropped_sampling": self.dropped_tasks_sampling,
            },
            "total_requests": self.total_requests,
            "buffer_size": total_in_buffer,
            "shadow_runs": self.shadow_runs,
            "shadow_errors": self.shadow_errors,
            "error_rate_pct": round((self.shadow_errors / max(1, self.total_requests)) * 100.0, 3),
            "last_error": self.last_error_message,
        }

        if not successful:
            base_stats["status"] = "NO_SUCCESSFUL_DATA"
            return base_stats

        diffs = [e["diff_pct"] for e in successful]
        abs_diffs = [abs(d) for d in diffs]
        v1_3_lats = [e["v1_3_latency_ms"] for e in successful]
        v6_lats = [e["v6_latency_ms"] for e in successful if e.get("v6_latency_ms", 0) > 0]

        missing_counter: Dict[str, int] = {}
        for e in successful:
            for feat in e.get("missing_features", []):
                missing_counter[feat] = missing_counter.get(feat, 0) + 1

        base_stats.update({
            "status": "HEALTHY",
            "buffer_count": len(successful),
            "divergence": {
                "mean_diff_pct": round(float(np.mean(diffs)), 2),
                "median_diff_pct": round(float(np.median(diffs)), 2),
                "mean_abs_diff_pct": round(float(np.mean(abs_diffs)), 2),
                "max_diff_pct": round(float(np.max(diffs)), 2),
                "min_diff_pct": round(float(np.min(diffs)), 2),
                "within_10_pct_rate": round(float(np.mean([d <= 10.0 for d in abs_diffs])) * 100, 2),
                "within_20_pct_rate": round(float(np.mean([d <= 20.0 for d in abs_diffs])) * 100, 2),
                "severe_outliers_count": int(sum(1 for d in abs_diffs if d > 50.0)),
            },
            "latency": {
                "v1_3_p50_ms": round(float(np.percentile(v1_3_lats, 50)), 2),
                "v1_3_p95_ms": round(float(np.percentile(v1_3_lats, 95)), 2),
                "v1_3_p99_ms": round(float(np.percentile(v1_3_lats, 99)), 2),
                "v1_3_mean_ms": round(float(np.mean(v1_3_lats)), 2),
                "v6_mean_ms": round(float(np.mean(v6_lats)), 2) if v6_lats else None,
            },
            "missing_features_counts": missing_counter,
        })

        return base_stats
