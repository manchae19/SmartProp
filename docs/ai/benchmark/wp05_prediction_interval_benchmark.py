"""Synthetic-only WP-05 experiment. No model, dataset, database or network input."""

import argparse
from collections import Counter, defaultdict
from dataclasses import dataclass, replace
from fractions import Fraction
import json
import math
import random
from statistics import fmean, median


COVERAGES = (80, 90, 95)
FIXED_WIDTH = {80: 0.25, 90: 0.40, 95: 0.55}
MAX_VND = 2**53 - 1
TYPES = ("HOUSE", "LAND", "APARTMENT", "VILLA")
DISTRICTS = ("Hai Chau", "Thanh Khe", "Son Tra", "Ngu Hanh Son", "Lien Chieu",
             "Cam Le", "Hoa Vang")
SOURCE = "SYNTHETIC_V1"
SIGNATURE = ("FAKE_FROZEN_MODEL", "SYNTHETIC_SCHEMA", "FINAL_POINT_POLICY_V1",
             "SYNTHETIC_LIVE_INPUT", "ASKING_PRICE_VND")
ROLES = ("development", "calibration", "evaluation", "temporal_shift", "geographic_shift")
SCENARIOS = ("additive", "skewed", "heavy_tail", "heteroskedastic")
METHODS = ("fixed", "absolute", "relative", "log", "asymmetric", "type",
           "predicted_band", "type_and_band", "type_and_band_no_fallback", "adaptive")
GROUP_METHODS = {"type", "predicted_band", "type_and_band", "type_and_band_no_fallback"}


@dataclass(frozen=True)
class Inputs:
    point: int
    kind: str
    district: str
    missing_count: int
    unknown_category: bool

    @property
    def band(self):
        if self.point < 4_000_000_000:
            return "LOW"
        if self.point < 12_000_000_000:
            return "MIDDLE"
        return "HIGH"


@dataclass(frozen=True)
class Row:
    observation: str
    entity: str
    listing: str
    repost: str
    role: str
    source: str
    snapshot_day: int
    feature_day: int
    label_day: int
    signature: tuple
    inputs: Inputs
    target: int


def valid_price(value):
    return type(value) is int and 1 <= value <= MAX_VND


def nominal_alpha(coverage):
    if type(coverage) is not int or coverage not in COVERAGES:
        raise ValueError("unsupported coverage")
    return Fraction(100 - coverage, 100)


def rank(n, alpha):
    if not 0 < alpha < 1:
        raise ValueError("alpha must be finite and in (0, 1)")
    return math.ceil((n + 1) * (1 - Fraction(str(alpha))))


def cutoff(scores, alpha):
    """None represents an unbounded mathematical cutoff, so serve no finite bound."""
    k = rank(len(scores), alpha)
    if any(not math.isfinite(score) or score < 0 for score in scores):
        raise ValueError("invalid nonconformity score")
    return sorted(scores)[k - 1] if k <= len(scores) else None


def min_group_support(alpha):
    # Rank grid <= alpha/4 and at least ten expected tail observations.
    return max(math.ceil(4 / alpha) - 1, math.ceil(10 / alpha))


def group_key(method, inputs):
    if method == "type":
        return (inputs.kind,)
    if method == "predicted_band":
        return (inputs.band,)
    return (inputs.kind, inputs.band)


def fixed_scale(inputs):
    """Prespecified analytical scale. No residual-scale model is fit."""
    return (1 + 0.12 * inputs.missing_count + 0.16 * inputs.unknown_category
            + 0.22 * (inputs.band == "HIGH") + 0.15 * (inputs.kind == "VILLA"))


def log_residual(row):
    # log(1 + y) - log(1 + point), with less cancellation near y = point.
    return math.log1p((row.target - row.inputs.point) / (1 + row.inputs.point))


def validate_splits(partitions):
    """Reject cross-partition identity, chronology, source and frozen-prediction violations."""
    if set(partitions) - set(ROLES):
        raise ValueError("unknown partition")
    seen = {key: {} for key in ("observation", "entity", "listing", "repost")}
    previous_last_label = -1
    for role in ROLES:
        rows = partitions.get(role, ())
        if not rows:
            continue
        if min(row.snapshot_day for row in rows) <= previous_last_label:
            raise ValueError("partition chronology overlaps previous outcome window")
        for row in rows:
            if row.role != role:
                raise ValueError("row partition mismatch")
            if row.signature != SIGNATURE:
                raise ValueError("prediction provenance mismatch")
            if row.source != SOURCE:
                raise ValueError("outside declared source population")
            if not row.feature_day <= row.snapshot_day <= row.label_day:
                raise ValueError("future feature or invalid label timing")
            if not valid_price(row.target) or not valid_price(row.inputs.point):
                raise ValueError("invalid price")
            for key, index in seen.items():
                value = getattr(row, key)
                if not value:
                    raise ValueError(f"missing {key} identity")
                scope = (role, row.entity)
                if index.setdefault(value, scope) != scope:
                    raise ValueError(f"cross-partition or inconsistent identity: {key}")
        previous_last_label = max(row.label_day for row in rows)


def one_per_entity(rows):
    selected = {}
    for row in sorted(rows, key=lambda row: (row.snapshot_day, row.observation)):
        selected.setdefault(row.entity, row)
    return list(selected.values())


def synthetic_rows(seed, scenario, role, count):
    role_no = ROLES.index(role)
    rng = random.Random(seed + 1009 * SCENARIOS.index(scenario) + 31 * role_no)
    rows = []
    for i in range(count):
        kind = rng.choices(TYPES, weights=(52, 26, 19, 3))[0]
        district = rng.choices(DISTRICTS, weights=(22, 16, 15, 15, 12, 12, 8))[0]
        if role == "geographic_shift" and rng.random() < 0.72:
            district = rng.choice(DISTRICTS[-2:])
        price_scale = {"HOUSE": 6.2, "LAND": 4.7, "APARTMENT": 3.8, "VILLA": 16.0}[kind]
        point = round(price_scale * math.exp(0.78 * rng.gauss(0, 1)) * 1e9)
        missing = rng.choices((0, 1, 2, 3), weights=(48, 29, 17, 6))[0]
        unknown = rng.random() < (0.20 if missing else 0.05)
        inputs = Inputs(point, kind, district, missing, unknown)
        noise = rng.gauss(0, 1)
        if scenario == "additive":
            target = round(max(1e6, point + 0.95e9 * noise))
        else:
            if scenario == "skewed":
                residual = 0.13 * noise + 0.21 * (rng.expovariate(1) - 0.55)
                residual += 0.12 * (inputs.band == "HIGH")
            elif scenario == "heavy_tail":
                residual = (0.78 if rng.random() < 0.09 else 0.16) * noise
                if rng.random() < 0.015:
                    residual += rng.choice((-1.8, 1.8))
            else:
                # Missingness increases spread for houses and reduces it for land.
                spread = 0.13 + 0.048 * (inputs.band == "HIGH") + 0.05 * (kind == "VILLA")
                spread += (0.044 if kind == "HOUSE" else -0.012 if kind == "LAND" else 0) * missing
                spread += 0.04 * unknown
                residual = spread * noise
            target = round(math.expm1(math.log1p(point) + residual))
        if role == "temporal_shift":
            target = round(target * math.exp(0.39 + 0.16 * rng.gauss(0, 1)))
        if role == "geographic_shift" and district in DISTRICTS[-2:]:
            target = round(target * math.exp(-0.32 + 0.26 * rng.gauss(0, 1)))
        key = f"{scenario}-{role}-{i:05}"
        day = 100 * (role_no + 1) + i % 15
        row = Row(f"{key}-0", key, f"listing-{key}", f"repost-{key}", role, SOURCE,
                  day, day - 1, day + 3, SIGNATURE, inputs, target)
        rows.append(row)
        if i % 17 == 0:
            rows.append(replace(row, observation=f"{key}-1", listing=f"alias-{key}", snapshot_day=day + 1))
    return rows


@dataclass(frozen=True)
class GroupCutoff:
    n: int
    q: float | None
    adjacent_rank_cutoffs: tuple | None = None


@dataclass(frozen=True)
class Fit:
    method: str
    coverage: int
    global_bounds: tuple | None
    n: int
    groups: dict
    signature: tuple = SIGNATURE


def fit(method, coverage, calibration):
    if method not in METHODS:
        raise ValueError("unknown method")
    alpha = nominal_alpha(coverage)
    if any(row.role != "calibration" for row in calibration):
        raise ValueError("only calibration residuals are eligible")
    validate_splits({"calibration": calibration})
    rows = one_per_entity(calibration)
    n = len(rows)
    if method == "fixed":
        q = FIXED_WIDTH[coverage]
        return Fit(method, coverage, (q, q), 0, {})
    residuals = [log_residual(row) for row in rows]
    if method == "asymmetric":
        lower = cutoff([max(0, -r) for r in residuals], alpha * Fraction(35, 100))
        upper = cutoff([max(0, r) for r in residuals], alpha * Fraction(65, 100))
        widths = None if lower is None or upper is None else (lower, upper)
        return Fit(method, coverage, widths, n, {})
    if method == "absolute":
        scores = [abs(row.target - row.inputs.point) for row in rows]
    elif method == "relative":
        scores = [abs(row.target - row.inputs.point) / row.inputs.point for row in rows]
    elif method == "adaptive":
        scores = [abs(r) / fixed_scale(row.inputs) for row, r in zip(rows, residuals)]
    else:
        scores = [abs(r) for r in residuals]
    q = cutoff(scores, alpha)
    groups = {}
    if method in GROUP_METHODS:
        by_group = defaultdict(list)
        for row, score in zip(rows, scores):
            by_group[group_key(method, row.inputs)].append(score)
        minimum = min_group_support(alpha)
        for key, values in by_group.items():
            if len(values) < minimum:
                groups[key] = GroupCutoff(len(values), None)
            else:
                ordered = sorted(values)
                k = rank(len(values), alpha)
                groups[key] = GroupCutoff(len(values), ordered[k - 1], (ordered[k - 2], ordered[k]))
    return Fit(method, coverage, (q, q) if q is not None else None, n, groups)


@dataclass(frozen=True)
class Interval:
    status: str
    point: int
    lower: int | None = None
    upper: int | None = None
    scope: str = "NONE"
    n: int = 0
    group_n: int | None = None


def interval(fitted, inputs, signature=SIGNATURE):
    point = inputs.point
    if signature != fitted.signature or not valid_price(point):
        return Interval("INVALID", point)
    bounds = fitted.global_bounds
    scope, n, group_n = "FIXED" if fitted.method == "fixed" else "GLOBAL", fitted.n, None
    if fitted.method in GROUP_METHODS:
        group = fitted.groups.get(group_key(fitted.method, inputs), GroupCutoff(0, None))
        group_n, q = group.n, group.q
        if q is not None:
            scope, n, bounds = "GROUP", group_n, (q, q)
        elif fitted.method == "type_and_band_no_fallback":
            return Interval("INSUFFICIENT", point, group_n=group_n)
        else:
            scope = "GLOBAL_FALLBACK"
    if bounds is None:
        return Interval("INSUFFICIENT", point, group_n=group_n)
    lower_q, upper_q = bounds
    if not all(math.isfinite(q) and q >= 0 for q in bounds):
        return Interval("INVALID", point, group_n=group_n)
    try:
        if fitted.method in ("fixed", "relative"):
            low, high = point * (1 - lower_q), point * (1 + upper_q)
        elif fitted.method == "absolute":
            low, high = point - lower_q, point + upper_q
        else:
            scale = fixed_scale(inputs) if fitted.method == "adaptive" else 1
            # Algebraically equivalent to expm1(log1p(point) ± scale*q).
            low = point + (1 + point) * math.expm1(-scale * lower_q)
            high = point + (1 + point) * math.expm1(scale * upper_q)
    except OverflowError:
        return Interval("INVALID", point, group_n=group_n)
    if not math.isfinite(low) or not math.isfinite(high) or high > MAX_VND:
        return Interval("INVALID", point, group_n=group_n)
    # A zero cutoff keeps the exact frozen point despite log round-off.
    lower = math.floor(max(1, min(point, low))) if lower_q else point
    upper = math.ceil(max(point, high)) if upper_q else point
    if not 1 <= lower <= point <= upper <= MAX_VND:
        return Interval("INVALID", point, group_n=group_n)
    return Interval("AVAILABLE", point, lower, upper, scope, n, group_n)


def wilson(successes, total):
    if total == 0:
        return None
    p = successes / total
    z = 1.959963984540054
    scale = 1 + z**2 / total
    center = (p + z**2 / (2 * total)) / scale
    delta = z * math.sqrt((p * (1 - p) + z**2 / (4 * total)) / total) / scale
    return [max(0, center - delta), min(1, center + delta)]


def metrics(rows, results, coverage):
    alpha = float(nominal_alpha(coverage))
    offered = [(row, bounds) for row, bounds in zip(rows, results) if bounds.status == "AVAILABLE"]
    total = len(rows)
    n = len(offered)
    counts = Counter(bounds.status for bounds in results)
    widths, relative, scores = [], [], []
    lower_miss = upper_miss = 0
    for row, bounds in offered:
        lower_gap = max(0, bounds.lower - row.target)
        upper_gap = max(0, row.target - bounds.upper)
        lower_miss += lower_gap > 0
        upper_miss += upper_gap > 0
        width = bounds.upper - bounds.lower
        widths.append(width)
        relative.append(width / bounds.point)
        scores.append(width + 2 / alpha * (lower_gap + upper_gap))
    hits = n - lower_miss - upper_miss
    return {
        "nominal": coverage / 100, "evaluation_n": total, "offered_n": n,
        "coverage": hits / n if n else None,
        "coverage_error": hits / n - coverage / 100 if n else None,
        "coverage_wilson_95": wilson(hits, n),
        "covered_fraction_all": hits / total,
        "mean_width_vnd": fmean(widths) if n else None,
        "median_width_vnd": median(widths) if n else None,
        "median_relative_width": median(relative) if n else None,
        "p90_width_vnd": sorted(widths)[math.ceil(0.90 * n) - 1] if n else None,
        "lower_tail_miss": lower_miss / n if n else None,
        "upper_tail_miss": upper_miss / n if n else None,
        "mean_interval_score_vnd": fmean(scores) if n else None,
        "insufficient_rate": counts["INSUFFICIENT"] / total,
        "invalid_rate": counts["INVALID"] / total,
        "fallback_rate": sum(b.scope == "GLOBAL_FALLBACK" for b in results) / total,
        "calibration_support_counts": dict(sorted(Counter(b.n for _, b in offered).items())),
    }


def evaluate(fitted, rows):
    results = [interval(fitted, row.inputs, row.signature) for row in rows]
    strata = defaultdict(list)
    for i, row in enumerate(rows):
        x = row.inputs
        for key in (f"type:{x.kind}", f"district:{x.district}", f"band:{x.band}",
                    f"missing:{x.missing_count}", f"unknown:{x.unknown_category}",
                    f"type_band:{x.kind}:{x.band}"):
            strata[key].append(i)
    return {
        "overall": metrics(rows, results, fitted.coverage),
        "subgroups": {
            key: metrics([rows[i] for i in indices], [results[i] for i in indices], fitted.coverage)
            for key, indices in sorted(strata.items())
        },
    }


def benchmark(seed):
    output = {"kind": "SYNTHETIC_METHODOLOGY_ONLY", "seed": seed, "scenarios": {}}
    for scenario in SCENARIOS:
        counts = (700, 2400, 1800, 1800, 1800)
        partitions = {role: synthetic_rows(seed, scenario, role, n) for role, n in zip(ROLES, counts)}
        validate_splits(partitions)
        entities = {role: one_per_entity(rows) for role, rows in partitions.items()}
        results = {}
        cal = entities["calibration"]
        for coverage in COVERAGES:
            results[coverage] = {}
            for method in METHODS:
                fitted = fit(method, coverage, cal)
                results[coverage][method] = {
                    "calibration_n": fitted.n,
                    "global_cutoffs": fitted.global_bounds,
                    "groups": [
                        {"key": key, "n": group.n, "cutoff": group.q,
                         "adjacent_rank_cutoffs": group.adjacent_rank_cutoffs}
                        for key, group in sorted(fitted.groups.items())
                    ],
                    **{role: evaluate(fitted, entities[role]) for role in ROLES[2:]},
                }
        output["scenarios"][scenario] = {
            "partition_rows": {role: len(rows) for role, rows in partitions.items()},
            "partition_entities": dict(zip(ROLES, counts)),
            "development_median_absolute_log_residual": median(
                abs(log_residual(row)) for row in entities["development"]
            ),
            "results": results,
        }
    return output


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--seed", type=int, default=20261128)
    args = parser.parse_args()
    print(json.dumps(benchmark(args.seed), sort_keys=True, separators=(",", ":"), allow_nan=False))
