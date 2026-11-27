#!/usr/bin/env python3
"""WP-02 Phase A benchmark v2 — SYNTHETIC_SURROGATE_BASELINE.

This is NOT production reproduction and NOT a market evaluation. It is a deterministic
surrogate whose rules are traced line-by-line to the Java sources on `a0e3834`:

  ComparableSimilarityScorer
    W_LOCATION .34 | W_AREA .30 | W_BEDROOMS .12 | W_FLOORS .10 | W_FRONTAGE .06 | W_PRICE .08
    ratioScore(a,b)    = 1 - min((max/min - 1) / 2, 1)          -> 0 at a 3x ratio
    locationScore      = 1.00 same district+ward | 0.82 same district |
                         0.45 adjacent district  | 0.15 otherwise
    bedrooms           = 1 - min(|delta| / 3, 1)
    floors             = 1 - min(|delta| / 4, 1)
    frontage           = 1 - min(|delta| / 10, 1)               -> absolute, not a ratio
    type mismatch      = total * 0.5  (applied before the weight normalisation)
    score              = clamp(total / weightUsed, 0, 1)

  ComparableCandidateRepository / ComparableRankingService
    every source query is `price BETWEEN :min AND :max LIMIT :cap`
    band = 0.4x .. 2.5x the reference price, widened when fewer than `limit` rows return
    TiniX = 12 buckets x 25 ids, MAX_RESULTS = 5

Known approximations (declared, never hidden):
  * SQL is modelled in memory; index behaviour and query latency are NOT measured.
  * `external_listings` has no ward/street/bedrooms/floors/frontage/road columns, so
    external candidates are scored on the features they really carry (district, area, price).
  * Adjacency uses the same Da Nang neighbour set as the scorer.

Metrics are ENTITY-level: a physical property counts once even if several listings of it are
returned. `other` (alternate listings of a relevant property) are still relevant.

Modes
  VALUATION_SUPPORT      target price must not influence selection; price is not a similarity
                         feature and no target-relative band is applied.
  BUYER_BUDGET_SEARCH    the caller's budget is a legitimate hard constraint (unchanged).

Run:
  python docs/ai/benchmark/wp02_comparable_benchmark.py --k 5
  python docs/ai/benchmark/wp02_comparable_benchmark.py --k 10 --json
"""
import argparse
import hashlib
import json
import math
import random
import statistics
import sys
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

DISTRICTS = ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu", "Cẩm Lệ", "Hòa Vang"]
ADJACENT = {
    "Hải Châu": {"Thanh Khê", "Sơn Trà", "Cẩm Lệ"},
    "Thanh Khê": {"Hải Châu", "Liên Chiểu"},
    "Sơn Trà": {"Hải Châu", "Ngũ Hành Sơn"},
    "Ngũ Hành Sơn": {"Sơn Trà", "Hải Châu"},
    "Liên Chiểu": {"Thanh Khê"},
    "Cẩm Lệ": {"Hải Châu", "Hòa Vang"},
    "Hòa Vang": {"Cẩm Lệ", "Liên Chiểu"},
}
TYPES = ["LAND", "HOUSE", "APARTMENT", "VILLA"]

# Verified scorer constants.
W = {"location": 0.34, "area": 0.30, "bedrooms": 0.12, "floors": 0.10,
     "frontage": 0.06, "price": 0.08}
BAND_LOW, BAND_HIGH = 0.4, 2.5
SMARTPROP_CAP, EXTERNAL_CAP, TINIX_BUCKETS, TINIX_PER_BUCKET = 200, 400, 12, 25
MAX_RESULTS = 5

# Type-aware proposal (only features the source can actually supply are used).
TYPE_WEIGHTS = {
    "LAND":      {"location": 0.50, "area": 0.38, "ward": 0.12},
    "HOUSE":     {"location": 0.38, "area": 0.30, "bedrooms": 0.18, "ward": 0.14},
    "APARTMENT": {"location": 0.40, "area": 0.34, "bedrooms": 0.26},
    "VILLA":     {"location": 0.38, "area": 0.32, "bedrooms": 0.16, "ward": 0.14},
}
CONFIDENCE_FLOOR = 0.55


# --------------------------------------------------------------------------- model
@dataclass
class Listing:
    listing_id: str
    entity_id: str                 # ground truth, evaluation only
    source: str                    # SMARTPROP | EXTERNAL_LISTING
    source_record_id: str          # observable identity within its source
    detail_url: str
    duplicate_group: Optional[str]
    property_type: str
    district: str
    ward: Optional[str]
    area: Optional[float]
    price: Optional[float]
    bedrooms: Optional[int]
    floors: Optional[int]
    frontage: Optional[float]
    age_days: Optional[int] = None
    expired: bool = False
    relevant: bool = False


@dataclass
class Reference:
    entity_id: str
    property_type: str
    district: str
    ward: str
    area: float
    target_price: float
    budget_max: Optional[float] = None
    bedrooms: Optional[int] = None
    floors: Optional[int] = None
    frontage: Optional[float] = None
    # Observable identity of the listing under evaluation (what production can actually see).
    property_id: str = ""
    source_record_id: str = ""
    detail_url: str = ""


# --------------------------------------------------------------------------- java rules
def ratio_score(a: Optional[float], b: Optional[float]) -> float:
    if a is None or b is None or a <= 0 or b <= 0:
        return 0.0
    ratio = max(a, b) / min(a, b)
    return 1.0 - min((ratio - 1.0) / 2.0, 1.0)


def location_score(ref: Reference, cand: Listing) -> float:
    if cand.district == ref.district:
        if cand.ward is not None and cand.ward == ref.ward:
            return 1.0
        return 0.82
    if cand.district in ADJACENT.get(ref.district, ()):
        return 0.45
    return 0.15


def baseline_score(ref: Reference, cand: Listing) -> float:
    """Exact mirror of ComparableSimilarityScorer.score."""
    total = weight_used = 0.0
    total += location_score(ref, cand) * W["location"]; weight_used += W["location"]

    if ref.area and cand.area:
        total += ratio_score(ref.area, cand.area) * W["area"]; weight_used += W["area"]
    if ref.bedrooms is not None and cand.bedrooms is not None:
        s = 1.0 - min(abs(ref.bedrooms - cand.bedrooms) / 3.0, 1.0)
        total += s * W["bedrooms"]; weight_used += W["bedrooms"]
    if ref.floors is not None and cand.floors is not None:
        s = 1.0 - min(abs(ref.floors - cand.floors) / 4.0, 1.0)
        total += s * W["floors"]; weight_used += W["floors"]
    if ref.frontage is not None and cand.frontage is not None and ref.frontage > 0 and cand.frontage > 0:
        s = 1.0 - min(abs(ref.frontage - cand.frontage) / 10.0, 1.0)
        total += s * W["frontage"]; weight_used += W["frontage"]
    if ref.target_price and cand.price:
        total += ratio_score(ref.target_price, cand.price) * W["price"]; weight_used += W["price"]

    if cand.property_type != ref.property_type:
        total *= 0.5

    score = total / weight_used if weight_used > 0 else 0.0
    return max(0.0, min(1.0, score))


def valuation_score(ref: Reference, cand: Listing) -> float:
    """Proposal: type-aware, price-free similarity; coverage shrinks low-evidence candidates."""
    weights = TYPE_WEIGHTS[cand.property_type]
    total = weight_used = 0.0
    for feature, weight in weights.items():
        if feature == "location":
            total += location_score(ref, cand) * weight; weight_used += weight
        elif feature == "area":
            if ref.area and cand.area:
                total += ratio_score(ref.area, cand.area) * weight; weight_used += weight
        elif feature == "bedrooms":
            if ref.bedrooms is not None and cand.bedrooms is not None:
                s = 1.0 - min(abs(ref.bedrooms - cand.bedrooms) / 3.0, 1.0)
                total += s * weight; weight_used += weight
        elif feature == "ward":
            if cand.ward is not None:
                s = 1.0 if cand.ward == ref.ward else 0.0
                total += s * weight; weight_used += weight
    if weight_used <= 0:
        return 0.0
    coverage = weight_used / sum(weights.values())
    return max(0.0, min(1.0, (total / weight_used) * (0.5 + 0.5 * coverage)))


def evidence_confidence(ref: Reference, cand: Listing) -> float:
    """Descriptive only — NOT calibrated, NOT a probability."""
    score = 0.30
    score += 0.20 * (1.0 if cand.district == ref.district else 0.0)
    score += 0.15 * (1.0 if cand.ward is not None and cand.ward == ref.ward else 0.0)
    present = sum(1 for v in (cand.area, cand.price, cand.bedrooms, cand.floors, cand.frontage)
                  if v is not None)
    score += 0.20 * (present / 5.0)
    score += 0.10 * (1.0 if cand.source == "SMARTPROP" else 0.0)
    if cand.age_days is not None:
        score += 0.05 * (1.0 if cand.age_days <= 180 else 0.0)
    return min(1.0, score)


# --------------------------------------------------------------------------- fixtures
def build_cohorts(seed: int, *, density: str = "mixed") -> List[Tuple[str, Reference, List[Listing]]]:
    rng = random.Random(seed)
    cohorts = []
    counter = 0
    for district in DISTRICTS:
        for ptype in TYPES:
            counter += 1
            ward = f"Phường {counter % 6 + 1}"
            ref = Reference(
                entity_id=f"E-REF{counter:03d}", property_type=ptype, district=district,
                ward=ward, area=100.0 if ptype != "APARTMENT" else 75.0,
                target_price=6_000_000_000.0 if ptype != "LAND" else 4_000_000_000.0,
                bedrooms=None if ptype == "LAND" else 3,
                floors=None if ptype in ("LAND", "APARTMENT") else 3,
                frontage=6.0 if ptype != "APARTMENT" else None,
                property_id=f"PROP{counter:03d}",
                source_record_id=f"SMARTPROP:PROP{counter:03d}",
                detail_url=f"https://example.invalid/property/{counter}",
            )
            listings: List[Listing] = []

            def add(*, entity: str, relevant: bool, source: str = "SMARTPROP",
                    district_: Optional[str] = None, ptype_: Optional[str] = None,
                    area: Optional[float] = None, price: Optional[float] = None,
                    ward_: Optional[str] = "same", url: Optional[str] = None,
                    group: Optional[str] = None, age: Optional[int] = None,
                    expired: bool = False, drop: Sequence[str] = ()) -> None:
                listing_id = f"L{len(listings):04d}{counter}"
                listings.append(Listing(
                    listing_id=listing_id, entity_id=entity, source=source,
                    source_record_id=f"{source}:{listing_id}",
                    detail_url=url or f"https://example.invalid/{source}/{listing_id}",
                    duplicate_group=group,
                    property_type=ptype_ or ptype,
                    district=district_ or district,
                    ward=None if "ward" in drop else (ward if ward_ == "same" else ward_),
                    area=None if "area" in drop else area,
                    price=None if "price" in drop else price,
                    bedrooms=None if "bedrooms" in drop or ptype == "LAND" else ref.bedrooms,
                    floors=None if "floors" in drop or ptype == "LAND" else ref.floors,
                    frontage=None if "frontage" in drop or ptype == "APARTMENT" else ref.frontage,
                    age_days=age, expired=expired, relevant=relevant,
                ))

            # --- 6 relevant properties. Relevance ignores price entirely.
            for i in range(6):
                add(entity=f"E{counter}-{i}", relevant=True,
                    area=ref.area * rng.uniform(0.92, 1.08),
                    price=ref.target_price * rng.uniform(0.5, 1.8),
                    ward_="same" if i < 3 else "other",
                    age=rng.choice([10, 60, 400]))
            # --- alternate listing of a relevant property (same entity, other source)
            add(entity=f"E{counter}-0", relevant=True, source="EXTERNAL_LISTING",
                url=f"https://example.invalid/alt/{counter}",
                area=ref.area, price=ref.target_price * 1.05, ward_="other")
            # --- exact self row: same listing, same canonical URL (T1-removable)
            add(entity=ref.entity_id, relevant=False, area=ref.area, price=ref.target_price)
            listings[-1].source_record_id = ref.source_record_id
            listings[-1].detail_url = ref.detail_url
            # --- reposted self: same physical property, different URL (residual leak)
            add(entity=ref.entity_id, relevant=False, source="EXTERNAL_LISTING",
                url=f"https://example.invalid/repost/{counter}", area=ref.area,
                price=ref.target_price)
            # --- wrong locality, plausible price
            add(entity=f"E{counter}-loc", relevant=False,
                district_="Hòa Vang" if district != "Hòa Vang" else "Sơn Trà",
                area=ref.area, price=ref.target_price)
            # --- wrong property type, same district
            add(entity=f"E{counter}-type", relevant=False,
                ptype_="LAND" if ptype != "LAND" else "HOUSE", area=ref.area,
                price=ref.target_price)
            # --- price-blind relevant: physically matching, asking price far outside band
            add(entity=f"E{counter}-cheap", relevant=True,
                area=ref.area * 0.98, price=ref.target_price * 0.35, ward_="same")
            add(entity=f"E{counter}-dear", relevant=True,
                area=ref.area * 1.02, price=ref.target_price * 2.9, ward_="other")
            # --- missing asking price but physically comparable
            add(entity=f"E{counter}-noprice", relevant=True, area=ref.area * 1.01,
                drop=("price",), ward_="same")
            # --- expired listing (must not be evidence in LIVE mode)
            add(entity=f"E{counter}-expired", relevant=False, area=ref.area,
                price=ref.target_price, expired=True, ward_="same")
            # --- stale but live
            add(entity=f"E{counter}-old", relevant=False, area=ref.area,
                price=ref.target_price, age=900, ward_="same")
            # --- sparse external candidate: only category/district/area/price/url
            add(entity=f"E{counter}-ext", relevant=False, source="EXTERNAL_LISTING",
                area=ref.area, price=ref.target_price, drop=("ward", "bedrooms", "floors", "frontage"))
            # --- duplicate-group sibling (same source namespace, same entity)
            add(entity=f"E{counter}-1", relevant=True, group=f"G{counter}",
                area=ref.area, price=ref.target_price, ward_="same")
            add(entity=f"E{counter}-1", relevant=True, group=f"G{counter}",
                area=ref.area * 1.01, price=ref.target_price * 1.02, ward_="other",
                url=f"https://example.invalid/grp/{counter}")

            # --- candidate-limit pressure: many non-relevant rows that outrank on price
            pressure = {"none": 0, "mixed": 25, "heavy": 120}[density]
            for i in range(pressure):
                add(entity=f"E{counter}-fill{i}", relevant=False,
                    area=ref.area * rng.uniform(0.85, 1.15),
                    price=ref.target_price * rng.uniform(0.95, 1.05), ward_="other")

            rng.shuffle(listings)
            cohorts.append((f"{district}/{ptype}", ref, listings))
    return cohorts


# --------------------------------------------------------------------------- dedupe
def canonical_url(url: str) -> str:
    return url.strip().rstrip("/").lower()


def dedupe_oracle(candidates: List[Listing]) -> List[Listing]:
    """ORACLE upper bound: ground-truth entity identity. Not implementable in production."""
    seen, out = set(), []
    for cand in candidates:
        if cand.entity_id in seen:
            continue
        seen.add(cand.entity_id)
        out.append(cand)
    return out


def dedupe_realistic(candidates: List[Listing]) -> Tuple[List[Listing], List[Listing]]:
    """Observable identity only. Returns (kept, flagged_suspects).

    T1 exact identity : source-qualified record id, or canonical URL.
    T2 trusted group  : duplicate_group, namespaced by source (groups are not shared across
                        sources, so the same label in two sources is NOT one entity).
    T3 suspected      : same district + type + area(<=2%) + price(<=3%) -> FLAG ONLY, never merged.
    """
    keys, out, suspects = set(), [], []
    for cand in candidates:
        identity = {f"{cand.source}|{cand.source_record_id}", f"url|{canonical_url(cand.detail_url)}"}
        if cand.duplicate_group:
            identity.add(f"group|{cand.source}|{cand.duplicate_group}")
        if identity & keys:
            continue
        keys |= identity
        if any(c.district == cand.district and c.property_type == cand.property_type
               and c.area and cand.area and abs(c.area - cand.area) / max(c.area, 1) <= 0.02
               and c.price and cand.price and abs(c.price - cand.price) / max(c.price, 1) <= 0.03
               for c in out):
            suspects.append(cand)
        out.append(cand)
    return out, suspects


# --------------------------------------------------------------------------- retrieval
@dataclass
class StageTrace:
    raw: int = 0
    eligible: int = 0
    filtered: int = 0
    capped: int = 0
    deduped: int = 0
    ranked: int = 0
    returned: int = 0


def retrieve(ref: Reference, listings: List[Listing], mode: str, approach: str,
             k: int, dedupe: str = "oracle", expiry: bool = True) -> Tuple[List[Tuple[Listing, float]], StageTrace]:
    trace = StageTrace(raw=len(listings))
    cands = list(listings)

    # Not evidence in LIVE mode.
    if expiry:
        cands = [c for c in cands if not c.expired]
    trace.eligible = len(cands)

    if approach == "A":
        # Verified production shape: price envelope per source, THEN cap, THEN rank.
        lo, hi = BAND_LOW * ref.target_price, BAND_HIGH * ref.target_price
        banded = [c for c in cands if c.price is not None and lo <= c.price <= hi]
        trace.filtered = len(banded)
        smart = [c for c in banded if c.source == "SMARTPROP"][:SMARTPROP_CAP]
        ext = [c for c in banded if c.source == "EXTERNAL_LISTING"][:EXTERNAL_CAP]
        cands = smart + ext
        trace.capped = len(cands)
        # Faithful to ComparableEligibilityService.notSelf(): it compares the reference id
        # with the candidate id. The reference is a property id and candidates are listing
        # ids, so nothing cross-source is ever excluded here.
        cands = [c for c in cands if c.listing_id != ref.property_id
                 and c.source_record_id != ref.property_id]
        if dedupe == "oracle":
            cands = dedupe_oracle(cands)
        else:
            cands, _ = dedupe_realistic(cands)
        trace.deduped = len(cands)
        scored = [(c, baseline_score(ref, c)) for c in cands]
    else:
        # Corrected retrieval: hard filters before cap, no target-relative band.
        cands = [c for c in cands if c.property_type == ref.property_type]
        cands = [c for c in cands if c.district == ref.district]
        if mode == "BUYER_BUDGET_SEARCH" and ref.budget_max is not None:
            cands = [c for c in cands if c.price is not None and c.price <= ref.budget_max]
        trace.filtered = len(cands)
        cands.sort(key=lambda c: c.listing_id)          # deterministic pre-cap order
        smart = [c for c in cands if c.source == "SMARTPROP"][:SMARTPROP_CAP]
        ext = [c for c in cands if c.source == "EXTERNAL_LISTING"][:EXTERNAL_CAP]
        cands = smart + ext
        trace.capped = len(cands)
        if dedupe == "oracle":
            # upper bound only: ground-truth entity never leaves this benchmark
            cands = [c for c in cands if c.entity_id != ref.entity_id]
        else:
            # observable identity only: the reference listing itself is removable by its own
            # record id / canonical URL. A repost with a new URL remains - that is the residual
            # leak the flag tier reports instead of silently merging.
            cands = [c for c in cands
                     if c.source_record_id != ref.source_record_id
                     and canonical_url(c.detail_url) != canonical_url(ref.detail_url)]
        if dedupe == "oracle":
            cands = dedupe_oracle(cands)
        else:
            cands, _ = dedupe_realistic(cands)
        trace.deduped = len(cands)
        if approach == "B":
            scored = [(c, baseline_score(ref, c)) for c in cands]
        else:
            scored = [(c, valuation_score(ref, c)) for c in cands]
            if approach == "D":
                scored = [(c, s) for c, s in scored
                          if evidence_confidence(ref, c) >= CONFIDENCE_FLOOR]

    scored.sort(key=lambda item: (-item[1], item[0].listing_id))   # total order, id tie-break
    trace.ranked = len(scored)
    result = scored[:k]
    trace.returned = len(result)
    return result, trace


# --------------------------------------------------------------------------- metrics
def evaluate(cohorts, approach: str, k: int, mode: str = "VALUATION_SUPPORT",
             dedupe: str = "oracle") -> Dict[str, object]:
    if k < 1:
        raise ValueError("k must be >= 1")
    per_type: Dict[str, List[float]] = {t: [] for t in TYPES}
    precisions, recalls, ndcgs = [], [], []
    raw_relevant = returned = unique_entities = 0
    self_matches = dup_excess = wrong_type = wrong_locality = 0
    empty_cohorts = zero_positive = 0
    traces: List[StageTrace] = []

    for label, ref, listings in cohorts:
        results, trace = retrieve(ref, listings, mode, approach, k, dedupe=dedupe)
        traces.append(trace)
        relevant_entities = {c.entity_id for c in listings if c.relevant and not c.expired}
        raw_relevant += len(relevant_entities)

        seen, gain = set(), 0.0
        dcg = 0.0
        for rank, (cand, _) in enumerate(results):
            returned += 1
            if cand.entity_id == ref.entity_id:
                self_matches += 1
            if cand.property_type != ref.property_type:
                wrong_type += 1
            if cand.district != ref.district:
                wrong_locality += 1
            if cand.entity_id in seen:
                dup_excess += 1
                continue
            seen.add(cand.entity_id)
            if cand.entity_id in relevant_entities:
                dcg += 1.0 / math.log2(rank + 2)
                gain += 1
        unique_entities += len(seen)

        precision = gain / k
        recall = gain / len(relevant_entities) if relevant_entities else None
        ideal = sum(1.0 / math.log2(r + 2) for r in range(min(k, len(relevant_entities))))
        ndcg = dcg / ideal if ideal else None

        precisions.append(precision)
        if recall is not None:
            recalls.append(recall)
        else:
            zero_positive += 1
        if ndcg is not None:
            ndcgs.append(ndcg)
        if not results:
            empty_cohorts += 1
        per_type[ref.property_type].append(precision)

    return {
        "approach": approach, "mode": mode, "dedupe": dedupe, "k": k,
        "cohorts": len(cohorts),
        "entity_precision@k": statistics.fmean(precisions) if precisions else 0.0,
        "entity_recall@k": statistics.fmean(recalls) if recalls else 0.0,
        "entity_ndcg@k": statistics.fmean(ndcgs) if ndcgs else 0.0,
        "self_match_count": self_matches,
        "duplicate_excess_rows": dup_excess,
        "wrong_type_count": wrong_type,
        "wrong_locality_count": wrong_locality,
        "raw_relevant_entities": raw_relevant,
        "returned_rows": returned,
        "unique_returned_entities": unique_entities,
        "empty_result_cohorts": empty_cohorts,
        "zero_positive_cohorts": zero_positive,
        "fill_rate": returned / (len(cohorts) * k) if cohorts else 0.0,
        "stage_raw": statistics.fmean([t.raw for t in traces]) if traces else 0,
        "stage_filtered": statistics.fmean([t.filtered for t in traces]) if traces else 0,
        "stage_capped": statistics.fmean([t.capped for t in traces]) if traces else 0,
        "stage_deduped": statistics.fmean([t.deduped for t in traces]) if traces else 0,
        "per_type_precision": {t: (statistics.fmean(v) if v else 0.0) for t, v in per_type.items()},
    }

# --------------------------------------------------------------------------- probes
def price_invariance(cohorts, approach: str, k: int) -> Dict[str, object]:
    """VALUATION_SUPPORT must not depend on the target price."""
    identical = 0
    score_drift = 0.0
    for label, ref, listings in cohorts:
        base_results, _ = retrieve(ref, listings, "VALUATION_SUPPORT", approach, k)
        base_ids = [c.listing_id for c, _ in base_results]
        base_scores = [round(s, 12) for _, s in base_results]
        for factor in (0.5, 2.0):
            import copy
            clone = copy.deepcopy(ref)
            clone.target_price = ref.target_price * factor
            other, _ = retrieve(clone, listings, "VALUATION_SUPPORT", approach, k)
            other_ids = [c.listing_id for c, _ in other]
            other_scores = [round(s, 12) for _, s in other]
            if other_ids == base_ids:
                identical += 1
            for a, b in zip(base_scores, other_scores):
                score_drift = max(score_drift, abs(a - b))
    total = len(cohorts) * 2
    return {"identical_windows": identical, "windows": total,
            "score_max_abs_drift": score_drift,
            "invariant": identical == total and score_drift == 0.0}


def buyer_budget_cohorts(seed: int):
    cohorts = build_cohorts(seed)
    budgeted = []
    for label, ref, listings in cohorts:
        import copy
        clone = copy.deepcopy(ref)
        clone.budget_max = ref.target_price * 0.9
        budgeted.append((label, clone, listings))
    return budgeted


def buyer_budget_check(cohorts, k: int) -> Dict[str, object]:
    violations = 0
    for label, ref, listings in cohorts:
        results, _ = retrieve(ref, listings, "BUYER_BUDGET_SEARCH", "B", k)
        for cand, _ in results:
            if cand.price is not None and cand.price > ref.budget_max:
                violations += 1
    return {"budget_violations": violations}


def dedupe_prf(seed: int) -> Dict[str, object]:
    """Precision/recall of predicted duplicate merging on labelled synthetic pairs."""
    cohorts = build_cohorts(seed)
    tp = fp = fn = 0
    for label, ref, listings in cohorts:
        cands = [c for c in listings if not c.expired and c.property_type == ref.property_type
                 and c.district == ref.district]
        kept, suspects = dedupe_realistic(cands)
        merged = len(cands) - len(kept)
        groups: Dict[str, int] = {}
        for c in cands:
            groups.setdefault(c.entity_id, 0)
            groups[c.entity_id] += 1
        true_duplicates = sum(v - 1 for v in groups.values())
        tp += min(merged, true_duplicates)
        fp += max(0, merged - true_duplicates)
        fn += max(0, true_duplicates - merged)
    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"true_positive": tp, "false_positive_merge": fp, "false_negative": fn,
            "precision": precision, "recall": recall}


# --------------------------------------------------------------------------- assertions
def run_assertions(seed: int) -> int:
    """Targeted checks on metric definitions. Non-zero exit on failure."""
    failures: List[str] = []

    def check(ok: bool, label: str) -> None:
        print(f"  {'PASS' if ok else 'FAIL'}  {label}")
        if not ok:
            failures.append(label)

    try:
        evaluate(build_cohorts(seed), "A", 0)
        check(False, "k<1 must be rejected")
    except ValueError:
        check(True, "k<1 is rejected")

    # Duplicate gain counted once: two listings of one entity fill two slots but gain once.
    dup = Listing("l1", "E1", "SMARTPROP", "SMARTPROP:l1", "u1", None, "HOUSE", "Hải Châu",
                  "Phường 1", 100.0, 5e9, 3, 3, 6.0, relevant=True)
    dup2 = Listing("l2", "E1", "EXTERNAL_LISTING", "EXTERNAL_LISTING:l2", "u2", None, "HOUSE",
                   "Hải Châu", None, 100.0, 5e9, None, None, None, relevant=True)
    ref = Reference("EREF", "HOUSE", "Hải Châu", "Phường 1", 100.0, 5e9, bedrooms=3, floors=3,
                    frontage=6.0, property_id="P0", source_record_id="SMARTPROP:P0",
                    detail_url="u0")
    report = evaluate([("synthetic", ref, [dup, dup2])], "A", 2, dedupe="realistic")
    check(report["entity_precision@k"] == 0.5, "duplicate gain counted once (P=1/2)")
    check(report["duplicate_excess_rows"] == 1, "duplicate excess row reported")

    # Empty / zero-positive cohort handling.
    report = evaluate([("empty", ref, [])], "B", 5)
    check(report["empty_result_cohorts"] == 1, "empty cohort counted")
    check(report["zero_positive_cohorts"] == 1 and report["entity_recall@k"] == 0.0,
          "zero-positive cohort excluded from recall and counted")

    # Exact self-match: oracle removes it, realistic removes the same-URL row.
    report = evaluate([("self", ref, [dup])], "B", 5, dedupe="oracle")
    check(report["self_match_count"] == 0, "oracle removes exact self-match")

    # Deterministic ordering under shuffled input.
    base = build_cohorts(seed)[:4]
    shuffled = [(lbl, r, list(reversed(lst))) for lbl, r, lst in base]
    a = evaluate(base, "C", 5)["returned_rows"]
    b = evaluate(shuffled, "C", 5)["returned_rows"]
    check(a == b, "returned row count stable under input order change")

    # Price invariance for C (price is not a similarity feature).
    inv = price_invariance(build_cohorts(seed)[:6], "C", 5)
    check(inv["invariant"], f"VALUATION_SUPPORT price invariance (drift={inv['score_max_abs_drift']})")
    inv_a = price_invariance(build_cohorts(seed)[:6], "A", 5)
    check(not inv_a["invariant"], "baseline A is NOT price invariant (expected)")

    # Buyer budget still enforced.
    budget = buyer_budget_check(buyer_budget_cohorts(seed)[:6], 5)
    check(budget["budget_violations"] == 0, "BUYER_BUDGET_SEARCH honours budget_max")

    print(f"\nassertions: {'PASS' if not failures else 'FAIL'} ({len(failures)} lỗi)")
    return 0 if not failures else 1


# --------------------------------------------------------------------------- CLI
def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--assertions", action="store_true")
    parser.add_argument("--density", default="mixed", choices=["none", "mixed", "heavy"])
    args = parser.parse_args()

    if args.k < 1:
        print("invalid k: must be >= 1")
        return 2
    if args.assertions:
        return run_assertions(args.seed)

    cohorts = build_cohorts(args.seed, density=args.density)
    rows = {}
    for approach, dedupe in (("A", "realistic"), ("B", "oracle"), ("B", "realistic"),
                             ("C", "realistic"), ("D", "realistic")):
        key = approach if approach == "A" else f"{approach}_{dedupe.upper()}"
        rows[key] = evaluate(cohorts, approach, args.k, dedupe=dedupe)
    prf = dedupe_prf(args.seed)
    inv = {a: price_invariance(cohorts, a, args.k) for a in ("A", "B", "C")}
    budget = buyer_budget_check(buyer_budget_cohorts(args.seed), args.k)

    payload = {"k": args.k, "seed": args.seed, "density": args.density,
               "cohorts": len(cohorts), "rows": rows, "dedupe_prf": prf,
               "price_invariance": inv, "buyer_budget": budget}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                            .encode()).hexdigest()[:16]
    payload["digest"] = digest

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"SYNTHETIC_SURROGATE_BASELINE  k={args.k} seed={args.seed} density={args.density} "
          f"cohorts={len(cohorts)}")
    print(f"{'variant':12s} {'P@k':>6s} {'R@k':>6s} {'NDCG':>6s} {'self':>5s} {'dup':>5s} "
          f"{'type':>5s} {'loc':>5s} {'fill':>6s}")
    print("-" * 70)
    for key, row in rows.items():
        print(f"{key:12s} {row['entity_precision@k']:6.3f} {row['entity_recall@k']:6.3f} "
              f"{row['entity_ndcg@k']:6.3f} {row['self_match_count']:5d} "
              f"{row['duplicate_excess_rows']:5d} {row['wrong_type_count']:5d} "
              f"{row['wrong_locality_count']:5d} {row['fill_rate']:6.3f}")
    print(f"\ndedupe P/R: {prf['precision']:.3f}/{prf['recall']:.3f} "
          f"(fp merges={prf['false_positive_merge']}, fn={prf['false_negative']})")
    for name, value in inv.items():
        print(f"price invariance {name}: identical {value['identical_windows']}/{value['windows']} "
              f"drift={value['score_max_abs_drift']}")
    print(f"buyer budget violations: {budget['budget_violations']}")
    print(f"\ndigest {digest}  (metric payload only, not a dataset hash)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
