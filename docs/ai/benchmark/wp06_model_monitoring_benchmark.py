"""Offline monitoring experiment. Every record and label is generated in memory."""

import argparse
from bisect import bisect_left
from collections import Counter, defaultdict, deque
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
import json
import math
from random import Random
from statistics import fmean, median
from threading import Lock
from time import perf_counter_ns
import tracemalloc


SEEDS = (6, 17, 33, 61, 97, 129, 241, 809)
WINDOWS = 12
START, STOP = 3, 8
N = 256
MIN_N = 100
MAX_EXACT = 2**53 - 1
ONE_VND_IN_BILLIONS = 1e-9
LATENCY_MS = (25, 50, 75, 100, 125, 150, 200, 300, 500, 1000, 2000)
PRICE_BINS = (1, 2, 3, 4, 5, 6, 8, 10)
TYPES = ("house", "apartment", "land", "UNKNOWN")
DISTRICTS = ("d1", "d2", "d3", "UNKNOWN")
SCENARIOS = (
    "healthy", "gradual_latency", "latency_spike", "timeouts", "unavailable",
    "exceptions", "missing_features", "unknown_category", "type_mix", "district_mix",
    "price_shift", "explanation_unavailable", "reconstruction_failure", "artifact_mismatch",
    "sparse", "empty", "delayed_labels", "duplicates", "concurrent", "missing_telemetry",
    "invalid_numeric", "drift_no_quality_loss", "quality_loss_no_drift", "unsupported_interval",
    "invalid_interval", "weak_price_shift", "price_variance_shift",
)


def finite(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def bins(values, edges):
    """Disjoint counts for intervals ending at each edge, with a final overflow bin."""
    if any(not finite(edge) for edge in edges) or any(a >= b for a, b in zip(edges, edges[1:])):
        raise ValueError("edges must be finite and strictly increasing")
    counts = [0] * (len(edges) + 1)
    for value in values:
        if not finite(value):
            raise ValueError("non-finite observation")
        counts[bisect_left(edges, value)] += 1
    return tuple(counts)


def quantile_bucket(counts, edges, q):
    """Upper edge of the nearest-rank bucket. Infinity denotes overflow."""
    if (not finite(q) or not 0 < q <= 1 or len(counts) != len(edges) + 1
            or any(type(n) is not int or n < 0 for n in counts)):
        raise ValueError("invalid quantile or bucket counts")
    if not sum(counts):
        return None
    rank = math.ceil(q * sum(counts))
    for edge, count in zip((*edges, math.inf), counts):
        rank -= count
        if rank <= 0:
            return edge


def distribution_metrics(left, right, smoothing=0.5):
    if (len(left) != len(right) or any(type(n) is not int or not 0 <= n <= MAX_EXACT for n in (*left, *right))
            or not finite(smoothing) or smoothing <= 0):
        raise ValueError("incompatible histogram or invalid smoothing")
    if not sum(left) or not sum(right):
        return None
    n, m, k = sum(left), sum(right), len(left)
    psi = js = 0.0
    for a, b in zip(left, right):
        smooth_p = (a + smoothing) / (n + k * smoothing)
        smooth_q = (b + smoothing) / (m + k * smoothing)
        if not 0 < smooth_p <= 1 or not 0 < smooth_q <= 1:
            raise ValueError("invalid smoothed probabilities")
        psi += (smooth_p - smooth_q) * (math.log(smooth_p) - math.log(smooth_q))
        p, q = a / n, b / m
        midpoint = (p + q) / 2
        js += (p * math.log2(p / midpoint) if p else 0) / 2
        js += (q * math.log2(q / midpoint) if q else 0) / 2
    return {"psi": psi, "js": js}


def ecdf_metrics(left, right):
    """Two-sample KS effect size and exact empirical W1 in the input unit."""
    if not left or not right:
        return None
    if any(not finite(x) for data in (left, right) for x in data):
        raise ValueError("non-finite observation")
    lhs, rhs = Counter(left), Counter(right)
    xs = sorted(lhs.keys() | rhs.keys())
    if not finite(xs[-1] - xs[0]):
        raise ValueError("observation range overflows")
    delta, ks, w1 = 0.0, 0.0, 0.0
    a, b, previous = 0, 0, xs[0]
    for x in xs:
        w1 += abs(delta) * (x - previous)
        a += lhs[x]
        b += rhs[x]
        delta = a / len(left) - b / len(right)
        ks = max(ks, abs(delta))
        previous = x
    return {"ks": ks, "w1": w1}


def category_counts(values, allowed):
    counts = Counter(value if value in allowed else "UNKNOWN" for value in values)
    return tuple(counts[key] for key in allowed)


@dataclass(frozen=True)
class Reference:
    key: tuple
    price: tuple
    property_types: tuple
    districts: tuple

    def compare(self, key, rows):
        if key != self.key or min(len(self.price), len(rows)) < MIN_N:
            return None
        prices, types, districts = zip(*rows)
        return {
            **distribution_metrics(bins(self.price, PRICE_BINS), bins(prices, PRICE_BINS)),
            **ecdf_metrics(self.price, prices),
            "type_js": distribution_metrics(self.property_types, category_counts(types, TYPES))["js"],
            "district_js": distribution_metrics(self.districts, category_counts(districts, DISTRICTS))["js"],
        }


SURFACES = ("standalone", "posting", "advisor")
TERMINAL = ("valid", "validation", "timeout", "unavailable", "exception", "invalid", "skipped", "cache")
FEATURE = ("known", "missing", "unknown")
EXPLANATION = ("available", "unavailable", "reconstruction_failure", "not_supported")
INTERVAL = ("available", "not_enabled", "invalid")


class Window:
    """Bounded synthetic ingest. A rejected overflow becomes a telemetry gap."""

    def __init__(self, capacity=N):
        self.capacity = capacity
        self.ids = set()
        self.series = Counter()
        self.rejected = Counter()
        self.lock = Lock()

    def record(self, event_id, surface, outcome, latency, feature, explanation, interval):
        if (surface not in SURFACES or outcome not in TERMINAL or feature not in FEATURE
                or explanation not in EXPLANATION or interval not in INTERVAL
                or not finite(latency) or latency < 0):
            with self.lock:
                self.rejected["invalid"] += 1
            return False
        with self.lock:
            if event_id in self.ids:
                self.rejected["duplicate"] += 1
                return False
            if len(self.ids) >= self.capacity:
                self.rejected["overflow"] += 1
                return False
            self.ids.add(event_id)
            self.series["terminal", surface, outcome] += 1
            self.series["histogram", surface, bisect_left(LATENCY_MS, latency)] += 1
            if outcome == "valid":
                self.series["feature", surface, feature] += 1
                self.series["explanation", surface, explanation] += 1
                self.series["interval", surface, interval] += 1
        return True

    def total(self, family, state=None):
        return sum(n for (kind, _, bucket), n in self.series.items()
                   if kind == family and (state is None or bucket == state))

    def snapshot(self, expected):
        seen = self.total("terminal")
        if type(expected) is not int or expected < seen:
            raise ValueError("expected request total is smaller than observed")
        valid = self.total("terminal", "valid")
        excluded = sum(self.total("terminal", kind) for kind in ("validation", "cache", "skipped"))
        attempts = seen - excluded
        pct = lambda a, b: a / b if b else None
        hist = tuple(self.total("histogram", i) for i in range(len(LATENCY_MS) + 1))
        tail = quantile_bucket(hist, LATENCY_MS, 0.95)
        return {
            "seen": seen, "valid": valid, "attempts": attempts, "latency_p95_overflow": tail == math.inf,
            "gap": pct(expected - seen, expected), "failure": pct(attempts - valid, attempts),
            "latency": LATENCY_MS[-1] if tail == math.inf else tail,
            **{kind: pct(self.total("terminal", kind), attempts) for kind in ("timeout", "unavailable", "exception")},
            **{name: pct(self.total(family, kind), valid) for name, family, kind in (
                ("missing", "feature", "missing"), ("unknown", "feature", "unknown"),
                ("unavailable_explanation", "explanation", "unavailable"),
                ("reconstruction_failure", "explanation", "reconstruction_failure"),
                ("invalid", "interval", "invalid"), ("not_enabled", "interval", "not_enabled"),
            )},
        }


@dataclass(frozen=True)
class Rule:
    warn: float
    critical: float
    recover: float
    confirm: int = 2
    cooldown: int = 2


class Alert:
    def __init__(self, rule):
        self.rule = rule
        self.level = self.streak = self.critical_streak = self.clean = 0
        self.cool_until = 0

    def update(self, window, value):
        rule = self.rule
        if value is None or not finite(value):
            self.streak = self.critical_streak = self.clean = 0
            return "insufficient"
        self.streak = self.streak + 1 if value >= rule.warn else 0
        self.critical_streak = self.critical_streak + 1 if value >= rule.critical else 0
        self.clean = self.clean + 1 if value <= rule.recover else 0
        if self.level and self.clean >= rule.confirm:
            self.level = 0
            self.cool_until = window + 1 + rule.cooldown
            return "recovered"
        if self.critical_streak >= rule.confirm and self.level < 2:
            self.level = 2
            return "critical"  # Critical may bypass warning cooldown.
        if not self.level and window >= self.cool_until and self.streak >= rule.confirm:
            self.level = 1
            return "warning"
        return None


RULES = {
    "latency": Rule(125, 200, 100), "timeout": Rule(.08, .20, .03),
    "unavailable": Rule(.08, .2, .03), "exception": Rule(.08, .2, .03),
    "missing": Rule(.17, .30, .12), "unknown": Rule(.13, .30, .07),
    "unavailable_explanation": Rule(.18, .35, .09), "reconstruction_failure": Rule(.08, .22, .03),
    "artifact_mismatch": Rule(1, 1, 0, confirm=1), "gap": Rule(.15, .35, .05),
    "invalid": Rule(.08, .23, .03), "mape": Rule(.18, .32, .11),
    "psi": Rule(.10, .26, .065), "js": Rule(.019, .05, .013),
    "ks": Rule(.15, .27, .115), "w1": Rule(.30, .8, .23),
    "type_js": Rule(.035, .10, .021), "district_js": Rule(.035, .10, .021),
}
PRICE_SIGNALS = ("psi", "js", "ks", "w1")
TARGETS = {
    "gradual_latency": ("latency",), "latency_spike": ("latency",),
    "timeouts": ("timeout",), "unavailable": ("unavailable",), "exceptions": ("exception",),
    "missing_features": ("missing",), "unknown_category": ("unknown", "type_js"),
    "type_mix": ("type_js",), "district_mix": ("district_js",),
    "price_shift": PRICE_SIGNALS, "drift_no_quality_loss": PRICE_SIGNALS,
    "weak_price_shift": PRICE_SIGNALS, "price_variance_shift": PRICE_SIGNALS,
    "explanation_unavailable": ("unavailable_explanation",),
    "reconstruction_failure": ("reconstruction_failure",), "artifact_mismatch": ("artifact_mismatch",),
    "missing_telemetry": ("gap",), "invalid_numeric": ("gap",), "invalid_interval": ("invalid",),
    "quality_loss_no_drift": ("mape",),
}


def point_quality(pairs):
    """Synthetic positive labels only. Amounts are in synthetic billions of VND."""
    if not pairs:
        return None
    if any(not finite(p) or not finite(y) or not ONE_VND_IN_BILLIONS <= min(p, y)
           or max(p, y) > MAX_EXACT * ONE_VND_IN_BILLIONS for p, y in pairs):
        raise ValueError("invalid labeled pair")
    errors = [p - y for p, y in pairs]
    ape = sorted(abs(p - y) / y for p, y in pairs)
    sse = sum(e * e for e in errors)
    mean_y = fmean(y for _, y in pairs)
    sst = sum((y - mean_y) ** 2 for _, y in pairs)
    return {
        "mape": fmean(ape), "mae": fmean(map(abs, errors)), "rmse": math.sqrt(sse / len(pairs)),
        "median_ape": median(ape), "p90_ape": ape[math.ceil(.90 * len(ape)) - 1],
        "w20": sum(a <= .20 for a in ape) / len(ape), "r2": 1 - sse / sst if sst else None,
        "bias": fmean(errors), "under": sum(e < 0 for e in errors) / len(errors),
        "over": sum(e > 0 for e in errors) / len(errors),
    }


def interval_quality(rows):
    """Coverage within valid issued bounds matched to an observed positive target."""
    if not rows:
        return None
    if any(not all(map(finite, (lower, upper, target))) or not 0 < lower <= upper <= MAX_EXACT
           or not 0 < target <= MAX_EXACT
           for lower, upper, target in rows):
        raise ValueError("invalid labeled interval")
    lower_misses = sum(target < lower for lower, _, target in rows)
    upper_misses = sum(target > upper for _, upper, target in rows)
    n = len(rows)
    return {"coverage": (n - lower_misses - upper_misses) / n,
            "lower_miss": lower_misses / n, "upper_miss": upper_misses / n}


def synthetic_row(rng):
    price = round(max(.5, rng.gauss(4.7, 1.3)), 3)
    group = rng.choices(TYPES[:3], weights=(5, 3, 2))[0]
    district = rng.choices(DISTRICTS[:3], weights=(4, 4, 2))[0]
    return price, group, district


def window_inputs(seed, index, scenario):
    rng = Random(seed * 1901 + index)
    inside = START <= index < STOP
    n = {"sparse": 12, "empty": 0}.get(scenario, N) if inside else N
    for i in range(n):
        price, kind, district = synthetic_row(rng)
        s = SURFACES[i % len(SURFACES)]
        u, f, e, z = (rng.random() for _ in range(4))
        latency = max(1, rng.gauss(65, 12))
        noise = rng.gauss(0, .055)
        outcome = "skipped" if s == "advisor" and u < .09 else "cache" if s == "posting" and u < .09 else "valid"
        if .09 <= u < .11:
            outcome = "validation"
        status = "missing" if f < .075 else "unknown" if f < .095 else "known"
        explanation = "unavailable" if e < .03 else "available"
        interval = "not_enabled"
        if inside:
            if scenario == "gradual_latency":
                latency += 12 + 19 * (index - START)
            if scenario == "latency_spike" and index < START + 2:
                latency += 150
            if scenario in ("timeouts", "unavailable", "exceptions") and outcome == "valid" and z < .30:
                outcome = {"timeouts": "timeout", "unavailable": "unavailable", "exceptions": "exception"}[scenario]
            if scenario == "missing_features" and f < .35:
                status = "missing"
            if scenario == "unknown_category" and f < .31:
                status, kind = "unknown", "other"
            if scenario == "type_mix" and z < .50:
                kind = "apartment"
            if scenario == "district_mix" and z < .50:
                district = "d3"
            if scenario in ("price_shift", "drift_no_quality_loss"):
                price += 1.15
            if scenario == "weak_price_shift":
                price += .24
            if scenario == "price_variance_shift":
                price = max(.5, 4.7 + 1.45 * (price - 4.7))
            if scenario == "explanation_unavailable" and e < .45:
                explanation = "unavailable"
            if scenario == "reconstruction_failure" and e < .30:
                explanation = "reconstruction_failure"
            if scenario == "quality_loss_no_drift":
                noise += .55
            if scenario == "unsupported_interval":
                explanation = "not_supported"
            if scenario == "invalid_interval" and z < .35:
                interval = "invalid"
        label = price * max(.1, 1 + noise)
        if inside and scenario == "delayed_labels" and z < .15:
            label = None
        recorded = not (inside and scenario == "missing_telemetry" and z < .30)
        if inside and scenario == "invalid_numeric" and z < .28:
            latency = float("nan")
        yield (i, s, outcome, latency, status, explanation, interval), (price, kind, district), label, recorded


def experiment(seed, scenario):
    key = ("synthetic-v1.3", "schema-22", "native", "fixture")
    rng = Random(1_020_033 + seed)
    ref_prices, ref_types, ref_districts = zip(*(synthetic_row(rng) for _ in range(2 * N)))
    ref = Reference(key, ref_prices, category_counts(ref_types, TYPES), category_counts(ref_districts, DISTRICTS))
    observed, pending = [], deque()
    max_series = 0
    rejected = Counter()
    for index in range(WINDOWS):
        rows = list(window_inputs(seed, index, scenario))
        window = Window()
        buffer = []
        if scenario == "concurrent":
            events = [event for event, _, _, _ in rows]
            with ThreadPoolExecutor(max_workers=4) as pool:
                list(pool.map(lambda event: window.record(*event), events + events))
            buffer = [(features, y) for event, features, y, _ in rows if event[2] == "valid"]
        else:
            for event, features, y, recorded in rows:
                if not recorded or not window.record(*event):
                    continue
                if event[2] == "valid":
                    buffer.append((features, y))
                if scenario == "duplicates":
                    window.record(*event)
        outcomes = window.snapshot(len(rows))
        outcomes["artifact_mismatch"] = int(scenario == "artifact_mismatch" and START <= index < STOP)
        outcomes["drift"] = ref.compare(key, [features for features, _ in buffer])
        pairs = [(features[0], y) for features, y in buffer if y is not None]
        delay = 4 if scenario == "delayed_labels" else 2
        pending.append((index + delay, len(buffer), pairs))
        outcomes["mape"] = None
        outcomes["matched"] = 0
        if pending and pending[0][0] <= index:
            _, eligible, ready = pending.popleft()
            outcomes["mature_eligible"] = eligible
            outcomes["matched"] = len(ready)
            if len(ready) >= MIN_N:
                outcomes["mape"] = point_quality(ready)["mape"]
        observed.append(outcomes)
        max_series = max(max_series, len(window.series))
        rejected.update(window.rejected)
    return observed, max_series, dict(rejected)


def run():
    stats = defaultdict(Counter)
    detail = defaultdict(Counter)
    delays = defaultdict(list)
    recoveries = defaultdict(list)
    checks = defaultdict(list)
    max_series = 0
    for seed in SEEDS:
        for scenario in SCENARIOS:
            windows, series, rejected = experiment(seed, scenario)
            max_series = max(max_series, series)
            detail[scenario].update(rejected)
            detail[scenario]["matched"] += sum(w["matched"] for w in windows)
            detail[scenario]["mature_eligible"] += sum(w.get("mature_eligible", 0) for w in windows)
            for signal, rule in RULES.items():
                delay = 2 if signal == "mape" else 0
                stop = START + 2 if scenario == "latency_spike" else STOP
                alert = Alert(rule)
                detected = False
                recovered = False
                relevant = signal in TARGETS.get(scenario, ())
                stats[signal]["positive_runs" if relevant else "negative_runs"] += 1
                if not relevant:
                    detail[scenario][signal + "_negative_runs"] += 1
                false_alarm = False
                for index, data in enumerate(windows):
                    drift = signal in (*PRICE_SIGNALS, "type_js", "district_js")
                    value = (data["drift"] or {}).get(signal) if drift else data.get(signal)
                    if drift or signal in ("missing", "unknown", "unavailable_explanation", "reconstruction_failure", "invalid"):
                        num = data["valid"]
                    elif signal in ("timeout", "unavailable", "exception"):
                        num = data["attempts"]
                    else:
                        num = data["seen"]
                    if num < MIN_N and signal not in ("gap", "artifact_mismatch", "mape"):
                        value = None
                    event = alert.update(index, value)
                    if event == "insufficient":
                        stats[signal]["insufficient_windows"] += 1
                        detail[scenario]["insufficient_signal_windows"] += 1
                    if event in ("warning", "critical"):
                        stats[signal]["alerts"] += 1
                        detail[scenario][signal + "_alerts"] += 1
                        if relevant and START + delay <= index < stop + delay:
                            if not detected:
                                delays[signal].append(index - START - delay)
                            detected = True
                        elif not relevant:
                            false_alarm = True
                            detail[scenario][signal + "_false_alerts"] += 1
                        else:
                            stats[signal]["outside_target_alerts"] += 1
                    if event == "recovered" and detected and not recovered and index >= stop + delay:
                        recoveries[signal].append(index - stop - delay)
                        recovered = True
                        detail[scenario][signal + "_recoveries"] += 1
                if relevant:
                    stats[signal]["tp" if detected else "fn"] += 1
                    if detected:
                        detail[scenario][signal + "_hits"] += 1
                elif false_alarm:
                    stats[signal]["fp"] += 1
            if scenario in ("healthy", "drift_no_quality_loss", "quality_loss_no_drift"):
                checks[scenario + "_mape"].extend(windows[i]["mape"] for i in range(START + 2, STOP + 2))
                checks[scenario + "_price_js"].extend(windows[i]["drift"]["js"] for i in range(START, STOP))
    result = {}
    for signal, counts in stats.items():
        positives, negatives = counts["positive_runs"], counts["negative_runs"]
        result[signal] = {
            **dict(counts), "tp": counts["tp"], "fp": counts["fp"], "fn": counts["fn"],
            "insufficient_windows": counts["insufficient_windows"],
            "outside_target_alerts": counts["outside_target_alerts"],
            "detection_rate": counts["tp"] / positives,
            "false_negative_rate": counts["fn"] / positives,
            "false_positive_rate": counts["fp"] / negatives,
            "detection_delay_windows": median(delays[signal]) if delays[signal] else None,
            "recovery_delay_windows": median(recoveries[signal]) if recoveries[signal] else None,
        }
    return {"seeds": SEEDS, "windows": WINDOWS, "max_observed_series": max_series,
            "max_series_by_construction": len(SURFACES) * (len(TERMINAL) + len(LATENCY_MS) + 1
            + len(FEATURE) + len(EXPLANATION) + len(INTERVAL)),
            "max_dedupe_ids_per_window": N, "alerts": result, "scenarios": detail,
            "negative_controls": {k: fmean(v) for k, v in checks.items()},
            "small_sample_control": small_sample_control()}


def small_sample_control():
    """Apply the same fixed raw warning cutoffs to IID windows before/after the n gate."""
    exceedances = {size: dict.fromkeys(PRICE_SIGNALS, 0) for size in (12, N)}
    trials = 40 * len(SEEDS)
    for seed in SEEDS:
        rng = Random(2_040_033 + seed)
        reference = [synthetic_row(rng)[0] for _ in range(2 * N)]
        for _ in range(40):
            current = [synthetic_row(rng)[0] for _ in range(N)]
            for size in exceedances:
                sample = current[:size]
                metrics = {
                    **distribution_metrics(bins(reference, PRICE_BINS), bins(sample, PRICE_BINS)),
                    **ecdf_metrics(reference, sample),
                }
                for metric, value in metrics.items():
                    exceedances[size][metric] += value >= RULES[metric].warn
    return {"trials_per_size": trials, "raw_cutoff_exceedances": exceedances,
            "insufficient_with_gate": {size: trials if size < MIN_N else 0 for size in exceedances}}


def profile():
    """Report noisy host costs separately from the deterministic result."""
    rows = list(window_inputs(SEEDS[0], 1, "healthy"))
    observed = tuple(features[0] for _, features, _, _ in rows)
    reference = tuple(features[0] for _, features, _, _ in window_inputs(SEEDS[1], 1, "healthy"))
    timings = {}
    for name, compare in [
        ("histogram_psi_js", lambda: distribution_metrics(bins(reference, PRICE_BINS), bins(observed, PRICE_BINS))),
        ("sorted_ecdf_ks_w1", lambda: ecdf_metrics(reference, observed)),
    ]:
        measured = []
        for _ in range(300):
            start = perf_counter_ns()
            compare()
            measured.append(perf_counter_ns() - start)
        timings[name + "_median_us"] = round(median(measured) / 1000, 2)
    tracemalloc.start()
    snapshots = {}
    for index in range(1000):
        window = Window()
        for event, _, _, _ in rows:
            window.record(*event)
        if index + 1 in (10, 100, 1000):
            current, peak = tracemalloc.get_traced_memory()
            snapshots[index + 1] = {"live_bytes": current, "peak_bytes": peak}
    tracemalloc.stop()
    return {"cost_per_256_vs_256": timings, "sequential_window_memory": snapshots}


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--profile", action="store_true", help="measure non-deterministic host costs")
    args = parser.parse_args()
    print(json.dumps(profile() if args.profile else run(), indent=2, sort_keys=True, allow_nan=False))
