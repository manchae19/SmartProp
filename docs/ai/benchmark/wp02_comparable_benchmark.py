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
def canonical_url(url: Optional[str]) -> str:
    return (url or "").strip().rstrip("/").lower()


def observable_keys(cand: Listing) -> set:
    """Identity keys that production can actually observe. Empty values never form a key."""
    keys = set()
    if cand.source and cand.source_record_id:
        keys.add(f"{cand.source}|{cand.source_record_id}")
    url = canonical_url(cand.detail_url)
    if url:
        keys.add(f"url|{url}")
    if cand.source and cand.duplicate_group:
        # A duplicate group label is meaningful only inside its own source namespace.
        keys.add(f"group|{cand.source}|{cand.duplicate_group}")
    return keys


def dedupe_oracle(candidates: List[Listing]) -> Tuple[List[Listing], List[Tuple[str, str]]]:
    """ORACLE upper bound: ground-truth entity. Returns (kept, merges)."""
    seen, kept, merges = set(), [], []
    for cand in candidates:
        if cand.entity_id in seen:
            merges.append((next(k.listing_id for k in kept if k.entity_id == cand.entity_id),
                           cand.listing_id))
            continue
        seen.add(cand.entity_id)
        kept.append(cand)
    return kept, merges


def dedupe_realistic(candidates: List[Listing]) -> Tuple[List[Listing], List[Listing], List[Tuple[str, str]]]:
    """Observable identity only. Returns (kept, suspects, merges).

    T1 exact identity : source-qualified record id, canonical URL.
    T2 trusted group  : duplicate_group, namespaced by source.
    T3 suspected      : similar area/price in the same district+type -> FLAG ONLY, never merged.
    """
    owner: Dict[str, str] = {}
    kept, suspects, merges = [], [], []
    for cand in candidates:
        keys = observable_keys(cand)
        matched = next((owner[k] for k in keys if k in owner), None)
        if matched is not None:
            merges.append((matched, cand.listing_id))
            continue
        for key in keys:
            owner[key] = cand.listing_id
        if any(c.district == cand.district and c.property_type == cand.property_type
               and c.area and cand.area and abs(c.area - cand.area) / max(c.area, 1) <= 0.02
               and c.price and cand.price and abs(c.price - cand.price) / max(c.price, 1) <= 0.03
               for c in kept):
            suspects.append(cand)
        kept.append(cand)
    return kept, suspects, merges


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
    relevant_raw: int = 0
    relevant_eligible: int = 0
    relevant_filtered: int = 0
    relevant_capped: int = 0
    relevant_deduped: int = 0
    relevant_ranked: int = 0


def _relevant(listings: List[Listing]) -> int:
    return len({c.entity_id for c in listings if c.relevant and not c.expired})


APPROACHES = {"A", "B", "BF", "C", "D"}


def retrieve(ref: Reference, listings: List[Listing], mode: str, approach: str, k: int,
             dedupe: str = "oracle", expiry: bool = True,
             caps: Tuple[int, int] = (SMARTPROP_CAP, EXTERNAL_CAP)
             ) -> Tuple[List[Tuple[Listing, float]], StageTrace, Dict[str, List[str]]]:
    if approach not in APPROACHES:
        raise ValueError(f"unknown approach {approach}")
    trace = StageTrace(raw=len(listings), relevant_raw=_relevant(listings))

    cands = list(listings)
    if expiry:
        cands = [c for c in cands if not c.expired]
    trace.eligible = len(cands)
    trace.relevant_eligible = _relevant(cands)

    if approach == "A":
        lo, hi = BAND_LOW * ref.target_price, BAND_HIGH * ref.target_price
        banded = [c for c in cands if c.price is not None and lo <= c.price <= hi]
        trace.filtered = len(banded)
        trace.relevant_filtered = _relevant(banded)
        smart = [c for c in banded if c.source == "SMARTPROP"][:caps[0]]
        ext = [c for c in banded if c.source == "EXTERNAL_LISTING"][:caps[1]]
        cands = smart + ext
        trace.capped = len(cands)
        trace.relevant_capped = _relevant(cands)
        # Faithful to notSelf(): property id compared with listing ids -> cross-source never excluded.
        cands = [c for c in cands if c.listing_id != ref.property_id
                 and c.source_record_id != ref.property_id]
        kept, merges = (dedupe_oracle(cands) if dedupe == "oracle" else
                        (lambda r: (r[0], r[2]))(dedupe_realistic(cands)))
        cands = kept
        trace.deduped = len(cands)
        trace.relevant_deduped = _relevant(cands)
        scored = [(c, baseline_score(ref, c)) for c in cands]
    else:
        cands = [c for c in cands if c.property_type == ref.property_type]
        cands = [c for c in cands if c.district == ref.district]
        if mode == "BUYER_BUDGET_SEARCH" and ref.budget_max is not None:
            cands = [c for c in cands if c.price is not None and c.price <= ref.budget_max]
        trace.filtered = len(cands)
        trace.relevant_filtered = _relevant(cands)
        cands.sort(key=lambda c: c.listing_id)
        smart = [c for c in cands if c.source == "SMARTPROP"][:caps[0]]
        ext = [c for c in cands if c.source == "EXTERNAL_LISTING"][:caps[1]]
        cands = smart + ext
        trace.capped = len(cands)
        trace.relevant_capped = _relevant(cands)
        if dedupe == "oracle":
            cands, merges = dedupe_oracle([c for c in cands if c.entity_id != ref.entity_id])
        else:
            # observable identity only: the reference listing is removable by its own record id
            # or canonical URL; a repost with a new URL stays and is reported as residual.
            cands = [c for c in cands
                     if c.source_record_id != ref.source_record_id
                     and canonical_url(c.detail_url) != canonical_url(ref.detail_url)]
            cands, _suspects, merges = dedupe_realistic(cands)
        trace.deduped = len(cands)
        trace.relevant_deduped = _relevant(cands)
        if approach in ("B",):
            scored = [(c, baseline_score(ref, c)) for c in cands]
        elif approach == "BF":
            # Corrected retrieval + baseline weights WITHOUT the price term.
            scored = [(c, baseline_score_price_free(ref, c)) for c in cands]
        else:
            scored = [(c, valuation_score(ref, c)) for c in cands]
            if approach == "D":
                scored = [(c, s) for c, s in scored
                          if evidence_confidence(ref, c) >= CONFIDENCE_FLOOR]

    scored.sort(key=lambda item: (-item[1], item[0].listing_id))
    trace.ranked = len(scored)
    trace.relevant_ranked = _relevant([c for c, _ in scored])
    result = scored[:k]
    trace.returned = len(result)
    pools = {"eligible": [c.listing_id for c in cands]}
    return result, trace, pools


def baseline_score_price_free(ref: Reference, cand: Listing) -> float:
    """baseline_score() minus W_PRICE. Removing the price band alone is not enough: the
    similarity term is what makes B non-invariant to the target price."""
    total = weight_used = 0.0
    total += location_score(ref, cand) * W["location"]; weight_used += W["location"]
    if ref.area and cand.area:
        total += ratio_score(ref.area, cand.area) * W["area"]; weight_used += W["area"]
    if ref.bedrooms is not None and cand.bedrooms is not None:
        total += (1.0 - min(abs(ref.bedrooms - cand.bedrooms) / 3.0, 1.0)) * W["bedrooms"]
        weight_used += W["bedrooms"]
    if ref.floors is not None and cand.floors is not None:
        total += (1.0 - min(abs(ref.floors - cand.floors) / 4.0, 1.0)) * W["floors"]
        weight_used += W["floors"]
    if ref.frontage is not None and cand.frontage is not None and ref.frontage > 0 and cand.frontage > 0:
        total += (1.0 - min(abs(ref.frontage - cand.frontage) / 10.0, 1.0)) * W["frontage"]
        weight_used += W["frontage"]
    if cand.property_type != ref.property_type:
        total *= 0.5
    score = total / weight_used if weight_used > 0 else 0.0
    return max(0.0, min(1.0, score))


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
        results, trace, _ = retrieve(ref, listings, mode, approach, k, dedupe=dedupe)
        traces.append(trace)
        relevant_entities = {c.entity_id for c in listings if c.relevant and not c.expired}
        raw_relevant += len(relevant_entities)

        seen, gain, dcg = set(), 0, 0.0
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
        if recall is None:
            zero_positive += 1
        else:
            recalls.append(recall)
        if ndcg is not None:
            ndcgs.append(ndcg)
        if not results:
            empty_cohorts += 1
        per_type[ref.property_type].append(precision)

    mean = lambda seq: statistics.fmean(seq) if seq else 0.0
    return {
        "approach": approach, "mode": mode, "dedupe": dedupe, "k": k,
        "cohorts": len(cohorts),
        "entity_precision@k": mean(precisions),
        "entity_recall@k": mean(recalls),
        "entity_ndcg@k": mean(ndcgs),
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
        "stage_relevant_raw": mean([t.relevant_raw for t in traces]),
        "stage_relevant_filtered": mean([t.relevant_filtered for t in traces]),
        "stage_relevant_capped": mean([t.relevant_capped for t in traces]),
        "stage_relevant_deduped": mean([t.relevant_deduped for t in traces]),
        "stage_relevant_ranked": mean([t.relevant_ranked for t in traces]),
        "stage_raw": mean([t.raw for t in traces]),
        "stage_filtered": mean([t.filtered for t in traces]),
        "stage_capped": mean([t.capped for t in traces]),
        "stage_deduped": mean([t.deduped for t in traces]),
        "per_type_precision": {t: mean(v) for t, v in per_type.items()},
    }


# --------------------------------------------------------------------------- probes
def cap_probe(k: int = 5) -> Dict[str, object]:
    """Actual cap pressure: build cohorts that exceed each source cap."""
    ref = Reference("E-REF", "HOUSE", "Hải Châu", "Phường 1", 100.0, 6e9,
                    bedrooms=3, floors=3, frontage=6.0, property_id="PROP9",
                    source_record_id="SMARTPROP:PROP9", detail_url="https://example.invalid/p/9")
    listings: List[Listing] = []
    # 260 SmartProp rows (cap 200) and 460 external rows (cap 400); the relevant ones sit
    # at the END of the deterministic pre-cap order, i.e. beyond the cap.
    for i in range(260):
        listings.append(Listing(f"S{i:04d}", f"E-S{i}", "SMARTPROP", f"SMARTPROP:S{i:04d}",
                                f"https://example.invalid/s/{i}", None, "HOUSE", "Hải Châu",
                                "Phường 1", 100.0, 6e9, 3, 3, 6.0))
    for i in range(460):
        listings.append(Listing(f"X{i:04d}", f"E-X{i}", "EXTERNAL_LISTING", f"EXTERNAL_LISTING:X{i:04d}",
                                f"https://example.invalid/x/{i}", None, "HOUSE", "Hải Châu",
                                None, 100.0, 6e9, None, None, None))
    for i in range(6):
        # "Z" sorts after every filler id, so these land beyond the per-source cap.
        listings.append(Listing(f"Z{i:04d}", f"E-Z{i}", "SMARTPROP", f"SMARTPROP:Z{i:04d}",
                                f"https://example.invalid/z/{i}", None, "HOUSE", "Hải Châu",
                                "Phường 1", 100.0, 6e9, 3, 3, 6.0, relevant=True))
    listings.sort(key=lambda c: c.listing_id)          # relevant rows end up last

    results, trace, _ = retrieve(ref, listings, "VALUATION_SUPPORT", "C", k,
                                 dedupe="realistic")
    pre_smart = sum(1 for c in listings if c.source == "SMARTPROP" and not c.expired)
    pre_ext = sum(1 for c in listings if c.source == "EXTERNAL_LISTING" and not c.expired)
    relevant_total = _relevant(listings)
    return {
        "pre_cap_smartprop": pre_smart, "pre_cap_external": pre_ext,
        "cap_smartprop": SMARTPROP_CAP, "cap_external": EXTERNAL_CAP,
        "post_cap": trace.capped,
        "smartprop_cap_binds": pre_smart > SMARTPROP_CAP,
        "external_cap_binds": pre_ext > EXTERNAL_CAP,
        "relevant_total": relevant_total,
        "relevant_surviving_cap": trace.relevant_capped,
        "relevant_lost_at_cap": relevant_total - trace.relevant_capped,
        "returned": len(results),
    }


def dedupe_pair_metrics() -> Dict[str, object]:
    """Pair-level PRF: every merge decision is checked against ground-truth identity."""
    tp = fp = fn = 0
    details: List[Dict[str, object]] = []

    def case(label: str, cands: List[Listing]) -> None:
        nonlocal tp, fp, fn
        kept, _suspects, merges = dedupe_realistic(cands)
        by_id = {c.listing_id: c for c in cands}
        for source_id, dropped_id in merges:
            same = by_id[source_id].entity_id == by_id[dropped_id].entity_id
            if same:
                tp += 1
            else:
                fp += 1
        groups: Dict[str, int] = {}
        for c in cands:
            groups[c.entity_id] = groups.get(c.entity_id, 0) + 1
        true_dupes = sum(v - 1 for v in groups.values())
        fn += true_dupes - sum(1 for s, d in merges if by_id[s].entity_id == by_id[d].entity_id)
        details.append({"case": label, "merges": len(merges),
                        "false_merges": sum(1 for s, d in merges
                                            if by_id[s].entity_id != by_id[d].entity_id)})

    def listing(lid, eid, *, source="SMARTPROP", rec=None, url=None, group=None,
                area=100.0, price=6e9, district="Hải Châu"):
        return Listing(lid, eid, source, rec if rec is not None else f"{source}:{lid}",
                       url if url is not None else f"https://example.invalid/{lid}", group,
                       "HOUSE", district, "Phường 1", area, price, 3, 3, 6.0, relevant=True)

    # same entity reachable through a trusted identifier -> must merge
    case("same entity, trusted record id",
         [listing("a1", "E1", rec="SMARTPROP:TRUSTED"), listing("a2", "E1", rec="SMARTPROP:TRUSTED")])
    # distinct entities with similar area/price -> must NOT merge
    case("distinct entities, similar area/price",
         [listing("b1", "E2", rec="SMARTPROP:B1"), listing("b2", "E3", rec="SMARTPROP:B2")])
    # source id collision across sources -> must NOT merge
    case("source id collision",
         [listing("c1", "E4", source="SMARTPROP", rec="SMARTPROP:42"),
          listing("c2", "E5", source="EXTERNAL_LISTING", rec="EXTERNAL_LISTING:42")])
    # missing identifiers -> never key on empty values
    case("missing source identity",
         [listing("d1", "E6", rec="", url=""), listing("d2", "E7", rec="", url="")])
    # same group label in different namespaces -> must NOT merge
    case("group label in two namespaces",
         [listing("e1", "E8", source="SMARTPROP", rec="SMARTPROP:E1", group="G1"),
          listing("e2", "E9", source="EXTERNAL_LISTING", rec="EXTERNAL_LISTING:E2", group="G1")])
    # real duplicate but no observable link -> must NOT merge (counted as false negative)
    case("repost, new URL, same entity",
         [listing("g1", "E11", source="SMARTPROP", rec="SMARTPROP:G1", url="https://x.invalid/a"),
          listing("g2", "E11", source="EXTERNAL_LISTING", rec="EXTERNAL_LISTING:G2",
                  url="https://x.invalid/b")])
    # same URL -> merge; different URL same entity -> merge only with a group
    case("canonical URL match",
         [listing("f1", "E10", rec="SMARTPROP:F1", url="https://x.invalid/p/1/"),
          listing("f2", "E10", rec="SMARTPROP:F2", url="https://x.invalid/p/1")])

    precision = tp / (tp + fp) if tp + fp else 1.0
    recall = tp / (tp + fn) if tp + fn else 1.0
    return {"true_positive": tp, "false_positive_merge": fp, "false_negative": fn,
            "precision": precision, "recall": recall, "cases": details}


def price_invariance(cohorts, approach: str, k: int, dedupe: str = "realistic") -> Dict[str, object]:
    """Compare the whole pipeline, not only top-K counts."""
    identical_pools = identical_windows = identical_scores = 0
    windows = len(cohorts) * 2
    drift = 0.0
    for label, ref, listings in cohorts:
        base, base_trace, _ = retrieve(ref, listings, "VALUATION_SUPPORT", approach, k, dedupe=dedupe)
        base_ids = [c.listing_id for c, _ in base]
        base_scores = [round(s, 12) for _, s in base]
        for factor in (0.5, 2.0):
            import copy
            clone = copy.deepcopy(ref)
            clone.target_price = ref.target_price * factor
            other, other_trace, _ = retrieve(clone, listings, "VALUATION_SUPPORT", approach, k,
                                             dedupe=dedupe)
            if other_trace.deduped == base_trace.deduped and other_trace.capped == base_trace.capped:
                identical_pools += 1
            if [c.listing_id for c, _ in other] == base_ids:
                identical_windows += 1
            other_scores = [round(s, 12) for _, s in other]
            if other_scores == base_scores:
                identical_scores += 1
            for a, b in zip(base_scores, other_scores):
                drift = max(drift, abs(a - b))
    return {"windows": windows, "identical_pools": identical_pools,
            "identical_windows": identical_windows, "identical_scores": identical_scores,
            "score_max_abs_drift": drift,
            "invariant": identical_pools == identical_windows == identical_scores == windows}


def buyer_budget_check(cohorts, k: int) -> Dict[str, object]:
    violations = 0
    for label, ref, listings in cohorts:
        results, _, _ = retrieve(ref, listings, "BUYER_BUDGET_SEARCH", "BF", k, dedupe="realistic")
        for cand, _ in results:
            if cand.price is not None and cand.price > ref.budget_max:
                violations += 1
    return {"budget_violations": violations}


def buyer_budget_cohorts(seed: int):
    cohorts = build_cohorts(seed)
    import copy
    out = []
    for label, ref, listings in cohorts:
        clone = copy.deepcopy(ref)
        clone.budget_max = ref.target_price * 0.9
        out.append((label, clone, listings))
    return out


# --------------------------------------------------------------------------- assertions
def run_assertions(seed: int) -> int:
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

    # ---- candidate cap actually binds
    cap = cap_probe()
    check(cap["smartprop_cap_binds"] and cap["external_cap_binds"],
          f"cap binds (pre {cap['pre_cap_smartprop']}/{cap['pre_cap_external']})")
    check(cap["post_cap"] <= SMARTPROP_CAP + EXTERNAL_CAP, "post-cap count respects caps")
    check(cap["relevant_lost_at_cap"] > 0,
          f"relevant entities lost at cap = {cap['relevant_lost_at_cap']}")

    # ---- pair-level dedupe
    prf = dedupe_pair_metrics()
    check(prf["false_positive_merge"] == 0, f"no false merge at pair level (fp={prf['false_positive_merge']})")
    check(prf["true_positive"] >= 2, f"trusted identifiers merge (tp={prf['true_positive']})")

    # ---- non-vacuous self-match
    ref = Reference("E-REF", "HOUSE", "Hải Châu", "Phường 1", 100.0, 6e9, bedrooms=3,
                    floors=3, frontage=6.0, property_id="PROP1",
                    source_record_id="SMARTPROP:PROP1", detail_url="https://x.invalid/p/1")
    exact = Listing("self", "E-REF", "SMARTPROP", "SMARTPROP:PROP1", "https://x.invalid/p/1",
                    None, "HOUSE", "Hải Châu", "Phường 1", 100.0, 6e9, 3, 3, 6.0)
    repost = Listing("repost", "E-REF", "EXTERNAL_LISTING", "EXTERNAL_LISTING:R",
                     "https://x.invalid/repost", None, "HOUSE", "Hải Châu", None,
                     100.0, 6e9, None, None, None)
    distinct = Listing("distinct", "E-OTHER", "SMARTPROP", "SMARTPROP:OTHER",
                       "https://x.invalid/other", None, "HOUSE", "Hải Châu", "Phường 1",
                       100.0, 6e9, 3, 3, 6.0, relevant=True)
    fixture = [exact, repost, distinct]
    real, _, _ = retrieve(ref, fixture, "VALUATION_SUPPORT", "C", 3, dedupe="realistic")
    ids = [c.listing_id for c, _ in real]
    check("self" not in ids, "exact observable self-match removed")
    check("distinct" in ids, "distinct comparable not removed")
    orc, _, _ = retrieve(ref, fixture, "VALUATION_SUPPORT", "C", 3, dedupe="oracle")
    check("repost" not in [c.listing_id for c, _ in orc], "oracle removes every reference entity")
    check("repost" in ids, "realistic keeps the unverifiable repost (residual reported)")

    # ---- deterministic ranking: IDs, scores and representatives
    base = build_cohorts(seed)[:6]
    shuffled = [(lbl, r, list(reversed(lst))) for lbl, r, lst in base]
    a = [(c.listing_id, round(s, 12)) for c, s in retrieve(base[0][1], base[0][2],
                                                           "VALUATION_SUPPORT", "C", 5,
                                                           dedupe="realistic")[0]]
    b = [(c.listing_id, round(s, 12)) for c, s in retrieve(shuffled[0][1], shuffled[0][2],
                                                           "VALUATION_SUPPORT", "C", 5,
                                                           dedupe="realistic")[0]]
    check(a == b, "ranking IDs and scores stable under reversed input order")

    # ---- realistic price invariance
    for variant in ("BF", "C"):
        inv = price_invariance(base, variant, 5, dedupe="realistic")
        check(inv["invariant"], f"{variant} VALUATION_SUPPORT price invariance "
                                f"(drift={inv['score_max_abs_drift']})")
    inv_b = price_invariance(base, "B", 5, dedupe="realistic")
    check(not inv_b["invariant"], "B alone is NOT price invariant (W_PRICE still applied)")

    # ---- buyer budget
    check(buyer_budget_check(buyer_budget_cohorts(seed)[:6], 5)["budget_violations"] == 0,
          "BUYER_BUDGET_SEARCH honours budget_max")

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
                             ("BF", "realistic"), ("C", "realistic"), ("D", "realistic")):
        key = approach if approach == "A" else f"{approach}_{dedupe.upper()}"
        rows[key] = evaluate(cohorts, approach, args.k, dedupe=dedupe)
    prf = dedupe_pair_metrics()
    inv = {v: price_invariance(cohorts, v, args.k, dedupe="realistic")
           for v in ("A", "B", "BF", "C", "D")}
    budget = buyer_budget_check(buyer_budget_cohorts(args.seed), args.k)
    cap = cap_probe(args.k)

    payload = {"k": args.k, "seed": args.seed, "density": args.density,
               "cohorts": len(cohorts), "rows": rows, "dedupe_pair_metrics": prf,
               "price_invariance": inv, "buyer_budget": budget, "cap_probe": cap}
    digest = hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False)
                            .encode()).hexdigest()[:16]
    payload["digest"] = digest

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2, sort_keys=True))
        return 0

    print(f"SYNTHETIC_SURROGATE_BASELINE  k={args.k} seed={args.seed} density={args.density} "
          f"cohorts={len(cohorts)}")
    print(f"{'variant':12s} {'P@k':>6s} {'R@k':>6s} {'NDCG':>6s} {'self':>5s} {'dup':>5s} "
          f"{'type':>5s} {'fill':>6s}")
    print("-" * 66)
    for key, row in rows.items():
        print(f"{key:12s} {row['entity_precision@k']:6.3f} {row['entity_recall@k']:6.3f} "
              f"{row['entity_ndcg@k']:6.3f} {row['self_match_count']:5d} "
              f"{row['duplicate_excess_rows']:5d} {row['wrong_type_count']:5d} {row['fill_rate']:6.3f}")
    print(f"\ncap probe: pre {cap['pre_cap_smartprop']}/{cap['pre_cap_external']} -> "
          f"capped {cap['post_cap']} · relevant lost at cap {cap['relevant_lost_at_cap']}")
    print(f"dedupe pairs: P={prf['precision']:.3f} R={prf['recall']:.3f} "
          f"(tp={prf['true_positive']}, fp={prf['false_positive_merge']}, fn={prf['false_negative']})")
    for name, value in inv.items():
        print(f"price invariance {name}: pools {value['identical_pools']}/{value['windows']} "
              f"ids {value['identical_windows']}/{value['windows']} "
              f"scores {value['identical_scores']}/{value['windows']} drift={value['score_max_abs_drift']}")
    print(f"buyer budget violations: {budget['budget_violations']}")
    print(f"\ndigest {digest}  (metric payload only, not a dataset hash)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
