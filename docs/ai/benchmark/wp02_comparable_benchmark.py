#!/usr/bin/env python3
"""WP-02 Phase A benchmark: Comparable correctness on SYNTHETIC fixtures.

This is design-phase evidence, not a market evaluation. It mirrors the *verified* rules of
`backend/src/main/java/vn/smartprop/comparable/` on `a0e3834`:

  ComparableCandidateRepository  retrieval is `price BETWEEN 0.4x..2.5x ref LIMIT cap`
  ComparableEligibilityService   notSelf() compares ids only; withinEnvelope(factor)
  ComparableSimilarityScorer     W_LOCATION .34 | W_AREA .30 | W_BEDROOMS .12
                                 W_FLOORS .10 | W_FRONTAGE .06 | W_PRICE .08
                                 score = Σ(w·s) / Σ(weightUsed)      <-- coverage-inflating

Four approaches are compared on the same fixtures:

  A  current baseline (price-band retrieval, id-only self match, flat weights)
  B  corrected retrieval + entity resolution (no price band, dedupe, self-match by identity)
  C  B + type-aware weighted similarity with missingness-aware coverage
  D  C + evidence-confidence gate (candidates below a confidence floor are not returned)

Run:  python docs/ai/benchmark/wp02_comparable_benchmark.py [--k 5] [--seed 20261127]
"""
import argparse
import hashlib
import json
import random
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple

DISTRICTS = ["Hải Châu", "Thanh Khê", "Sơn Trà", "Ngũ Hành Sơn", "Liên Chiểu", "Cẩm Lệ", "Hòa Vang"]
TYPES = ["LAND", "HOUSE", "APARTMENT", "VILLA"]
STREETS = ["Nguyễn Văn Linh", "Nguyễn Phước Lan", "Trần Phú", "Hoàng Diệu", "Điện Biên Phủ"]

# Verified baseline constants (ComparableSimilarityScorer on a0e3834).
BASELINE_WEIGHTS = {"location": 0.34, "area": 0.30, "bedrooms": 0.12,
                    "floors": 0.10, "frontage": 0.06, "price": 0.08}
BAND_LOW, BAND_HIGH = 0.4, 2.5

# Proposed type-aware weights (design proposal; rationale in the technical design).
TYPE_WEIGHTS = {
    "LAND":      {"location": 0.45, "area": 0.35, "frontage": 0.12, "road": 0.08},
    "HOUSE":     {"location": 0.34, "area": 0.26, "bedrooms": 0.12, "floors": 0.10,
                  "frontage": 0.10, "road": 0.08},
    "APARTMENT": {"location": 0.36, "area": 0.30, "bedrooms": 0.16, "project": 0.18},
    "VILLA":     {"location": 0.32, "area": 0.28, "bedrooms": 0.10, "floors": 0.12,
                  "frontage": 0.10, "road": 0.08},
}


@dataclass
class Listing:
    listing_id: str
    entity_id: str                      # physical property; duplicates share it
    source: str                         # SMARTPROP | EXTERNAL_LISTING | TINIX_RESEARCH
    property_type: str
    district: str
    ward: str
    street: str
    area: Optional[float]
    price: Optional[float]
    bedrooms: Optional[int]
    floors: Optional[int]
    frontage: Optional[float]
    road: Optional[float]
    project: Optional[str] = None
    duplicate_group: Optional[str] = None
    detail_url: Optional[str] = None
    age_days: Optional[int] = None
    verified: bool = False
    expected_relevant: bool = False


@dataclass
class Reference:
    listing_id: str
    entity_id: str
    property_type: str
    district: str
    ward: str
    street: str
    area: float
    target_price: float                 # the value being validated (never ground truth)
    bedrooms: Optional[int]
    floors: Optional[int]
    frontage: Optional[float]
    road: Optional[float]
    project: Optional[str] = None


# --------------------------------------------------------------------------- fixtures
def _mk(rng: random.Random, reference: Reference, index: int, *, entity: str,
        district: Optional[str] = None, ptype: Optional[str] = None,
        area: Optional[float] = None, price: Optional[float] = None,
        relevant: bool = False, source: str = "SMARTPROP",
        age_days: Optional[int] = None, verified: bool = False,
        drop: Tuple[str, ...] = ()) -> Listing:
    district = district or reference.district
    ptype = ptype or reference.property_type
    area = area if area is not None else max(20.0, reference.area * rng.uniform(0.8, 1.25))
    price = price if price is not None else reference.target_price * rng.uniform(0.7, 1.4)

    def maybe(name, value):
        return None if name in drop else value

    return Listing(
        listing_id=f"L{index:04d}", entity_id=entity, source=source, property_type=ptype,
        district=district, ward=f"Phường {index % 6 + 1}", street=rng.choice(STREETS),
        area=maybe("area", round(area, 1)), price=maybe("price", round(price)),
        bedrooms=maybe("bedrooms", reference.bedrooms if reference.bedrooms is not None else 3),
        floors=maybe("floors", reference.floors if reference.floors is not None else 3),
        frontage=maybe("frontage", reference.frontage),
        road=maybe("road", reference.road),
        project=reference.project if ptype == "APARTMENT" else None,
        age_days=age_days, verified=verified, expected_relevant=relevant,
    )


def build_cohorts(seed: int) -> List[Tuple[str, Reference, List[Listing]]]:
    """Seven districts × four types, each with a planted ground truth."""
    rng = random.Random(seed)
    cohorts = []
    counter = 0
    for district in DISTRICTS:
        for ptype in TYPES:
            counter += 1
            reference = Reference(
                listing_id=f"REF{counter:03d}", entity_id=f"E-REF{counter:03d}",
                property_type=ptype, district=district, ward="Phường 1",
                street=STREETS[counter % len(STREETS)],
                area=100.0 if ptype != "APARTMENT" else 75.0,
                target_price=6_000_000_000.0 if ptype != "LAND" else 4_000_000_000.0,
                bedrooms=None if ptype == "LAND" else 3,
                floors=None if ptype in ("LAND", "APARTMENT") else 3,
                frontage=6.0 if ptype != "APARTMENT" else None,
                road=12.0 if ptype != "APARTMENT" else None,
                project="Dự án Trung Tâm" if ptype == "APARTMENT" else None,
            )
            listings: List[Listing] = []

            # 6 genuinely similar properties (expected relevant).
            # Relevance is defined WITHOUT price: a valuation-oriented benchmark must not
            # label a property relevant because its asking price sits near the target - that
            # is the circularity under investigation. Area, locality and street decide.
            for k in range(6):
                near_area = reference.area * rng.uniform(0.9, 1.1)
                wide_price = reference.target_price * rng.uniform(0.5, 1.8)
                entry = _mk(rng, reference, len(listings) + counter * 100,
                            entity=f"E{counter}-{k}", area=near_area, price=wide_price,
                            relevant=True, verified=k < 2)
                if k < 3:
                    entry.street = reference.street          # same street, strongest evidence
                listings.append(entry)
            # self-match: same listing id and same entity, different source
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=reference.entity_id, relevant=False))
            listings[-1].listing_id = reference.listing_id
            # cross-source duplicate of a relevant property (same entity)
            dup = _mk(rng, reference, len(listings) + counter * 100, entity=f"E{counter}-0",
                      source="EXTERNAL_LISTING", relevant=False)
            listings.append(dup)
            # repost of the reference itself (same entity, different url)
            repost = _mk(rng, reference, len(listings) + counter * 100, entity=reference.entity_id,
                         source="EXTERNAL_LISTING", relevant=False)
            repost.detail_url = f"https://example.invalid/repost/{counter}"
            listings.append(repost)
            # wrong locality, plausible price (steals a slot in the baseline band)
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-loc", district="Hòa Vang" if district != "Hòa Vang" else "Sơn Trà",
                                relevant=False, price=reference.target_price))
            # wrong property type, same district
            other = "LAND" if ptype != "LAND" else "HOUSE"
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-type", ptype=other, relevant=False,
                                price=reference.target_price))
            # high and low price outliers that are otherwise similar
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-hi", price=reference.target_price * 4.0, relevant=False))
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-lo", price=reference.target_price * 0.15, relevant=False))
            # stale listing
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-old", age_days=900, relevant=False))
            # sparse listing: only location + type known
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-sparse",
                                drop=("area", "price", "bedrooms", "floors", "frontage"), relevant=False))
            # TiniX research row (must never reach a public result)
            listings.append(_mk(rng, reference, len(listings) + counter * 100,
                                entity=f"E{counter}-tinix", source="TINIX_RESEARCH", relevant=False))
            rng.shuffle(listings)
            cohorts.append((f"{district}/{ptype}", reference, listings))
    return cohorts


# --------------------------------------------------------------------------- scoring
def _ratio_similarity(a: Optional[float], b: Optional[float], tolerance: float = 0.35) -> Optional[float]:
    if a is None or b is None or a <= 0 or b <= 0:
        return None
    ratio = max(a, b) / min(a, b)
    if ratio >= 1 + tolerance * 2:
        return 0.0
    return max(0.0, 1.0 - (ratio - 1.0) / (tolerance * 2))


def _count_similarity(a: Optional[float], b: Optional[float], scale: float) -> Optional[float]:
    if a is None or b is None:
        return None
    return max(0.0, 1.0 - abs(a - b) / scale)


def _location_similarity(ref: Reference, cand: Listing) -> float:
    if cand.district != ref.district:
        return 0.0
    if cand.street == ref.street:
        return 1.0
    return 0.6


def baseline_score(ref: Reference, cand: Listing) -> Optional[float]:
    """Mirror of ComparableSimilarityScorer: flat weights, normalised by weight used."""
    parts: List[Tuple[float, float]] = [(BASELINE_WEIGHTS["location"], _location_similarity(ref, cand))]
    area = _ratio_similarity(ref.area, cand.area)
    if area is not None:
        parts.append((BASELINE_WEIGHTS["area"], area))
    if ref.bedrooms is not None and cand.bedrooms is not None:
        parts.append((BASELINE_WEIGHTS["bedrooms"],
                      max(0.0, 1.0 - abs(ref.bedrooms - cand.bedrooms) / 3.0)))
    if ref.floors is not None and cand.floors is not None:
        parts.append((BASELINE_WEIGHTS["floors"],
                      max(0.0, 1.0 - abs(ref.floors - cand.floors) / 5.0)))
    frontage = _ratio_similarity(ref.frontage, cand.frontage)
    if frontage is not None:
        parts.append((BASELINE_WEIGHTS["frontage"], frontage))
    price = _ratio_similarity(ref.target_price, cand.price, tolerance=0.5)
    if price is not None:
        parts.append((BASELINE_WEIGHTS["price"], price))
    weight_used = sum(w for w, _ in parts)
    if weight_used <= 0:
        return None
    return sum(w * s for w, s in parts) / weight_used


def type_aware_score(ref: Reference, cand: Listing) -> Optional[float]:
    """Proposed: per-type weights, price excluded from valuation similarity."""
    weights = TYPE_WEIGHTS[cand.property_type]
    parts: List[Tuple[float, float]] = []
    for feature, weight in weights.items():
        if feature == "location":
            parts.append((weight, _location_similarity(ref, cand)))
        elif feature == "area":
            value = _ratio_similarity(ref.area, cand.area)
            if value is not None:
                parts.append((weight, value))
        elif feature == "bedrooms":
            value = _count_similarity(ref.bedrooms, cand.bedrooms, 3.0)
            if value is not None:
                parts.append((weight, value))
        elif feature == "floors":
            value = _count_similarity(ref.floors, cand.floors, 5.0)
            if value is not None:
                parts.append((weight, value))
        elif feature == "frontage":
            value = _ratio_similarity(ref.frontage, cand.frontage)
            if value is not None:
                parts.append((weight, value))
        elif feature == "road":
            value = _ratio_similarity(ref.road, cand.road)
            if value is not None:
                parts.append((weight, value))
        elif feature == "project":
            if ref.project and cand.project:
                parts.append((weight, 1.0 if ref.project == cand.project else 0.0))
    weight_used = sum(w for w, _ in parts)
    if weight_used <= 0:
        return None
    coverage = weight_used / sum(weights.values())
    return (sum(w * s for w, s in parts) / weight_used) * (0.5 + 0.5 * coverage)


def evidence_confidence(ref: Reference, cand: Listing) -> float:
    """Coverage-aware confidence, deliberately separate from similarity."""
    score = 0.0
    score += 0.30 if cand.entity_id and cand.entity_id != ref.entity_id else 0.0
    score += 0.20 * (1.0 if cand.district == ref.district else 0.0)
    score += 0.15 * (1.0 if cand.street == ref.street else 0.0)
    completeness = sum(1 for v in (cand.area, cand.price, cand.bedrooms, cand.floors,
                                   cand.frontage) if v is not None) / 5.0
    score += 0.20 * completeness
    score += 0.10 * (1.0 if cand.verified else 0.0)
    if cand.age_days is not None:
        score += 0.05 * (1.0 if cand.age_days <= 180 else 0.0)
    return min(1.0, score)


CONFIDENCE_LABEL = ((0.75, "HIGH"), (0.55, "MEDIUM"), (0.35, "LOW"))


def confidence_label(value: float) -> str:
    for threshold, label in CONFIDENCE_LABEL:
        if value >= threshold:
            return label
    return "INSUFFICIENT_EVIDENCE"


# --------------------------------------------------------------------------- approaches
def apply_approach(name: str, ref: Reference, listings: List[Listing], k: int) -> List[Tuple[Listing, float]]:
    candidates = listings

    # security boundary holds in every approach: research rows never reach a public result
    candidates = [c for c in candidates if c.source != "TINIX_RESEARCH"]

    if name == "A":
        # baseline: price band before LIMIT, id-only self match
        candidates = [c for c in candidates
                      if c.price is not None
                      and BAND_LOW * ref.target_price <= c.price <= BAND_HIGH * ref.target_price]
        candidates.sort(key=lambda c: abs((c.price or 0) - ref.target_price))
        candidates = candidates[:20]
        candidates = [c for c in candidates if c.listing_id != ref.listing_id]
        scored = [(c, baseline_score(ref, c)) for c in candidates]
    else:
        # corrected retrieval: no price envelope, locality/type are hard filters before LIMIT
        candidates = [c for c in candidates if c.district == ref.district]
        candidates = [c for c in candidates if c.property_type == ref.property_type]
        # entity resolution: drop the reference's own physical property, then dedupe by entity
        candidates = [c for c in candidates if c.entity_id != ref.entity_id]
        seen_entities, deduped = set(), []
        for c in sorted(candidates, key=lambda c: (-(c.verified), c.age_days or 10 ** 6, c.listing_id)):
            if c.entity_id in seen_entities:
                continue
            seen_entities.add(c.entity_id)
            deduped.append(c)
        candidates = deduped[:20]
        if name == "B":
            scored = [(c, baseline_score(ref, c)) for c in candidates]
        else:
            scored = [(c, type_aware_score(ref, c)) for c in candidates]
            if name == "D":
                scored = [(c, s) for c, s in scored
                          if s is not None and evidence_confidence(ref, c) >= 0.55]

    scored = [(c, s) for c, s in scored if s is not None]
    scored.sort(key=lambda item: (-item[1], item[0].listing_id))
    return scored[:k]


# --------------------------------------------------------------------------- metrics
def evaluate(name: str, cohorts, k: int) -> Dict[str, float]:
    precisions, recalls, ndcgs = [], [], []
    self_leaks = duplicates = results = 0
    locality_bad = type_bad = 0
    tinix_leaks = 0
    reference_count = 0

    for label, ref, listings in cohorts:
        reference_count += 1
        results_k = apply_approach(name, ref, listings, k)
        returned_ids = [c.listing_id for c, _ in results_k]

        relevant = {c.listing_id for c in listings if c.expected_relevant}
        hits = len(set(returned_ids) & relevant)
        precisions.append(hits / k)
        recalls.append(hits / max(1, min(k, len(relevant))))

        # NDCG with binary relevance
        dcg = sum((1.0 if c.listing_id in relevant else 0.0) / _log2(rank + 2)
                  for rank, (c, _) in enumerate(results_k))
        idcg = sum(1.0 / _log2(rank + 2) for rank in range(min(k, len(relevant))))
        ndcgs.append(dcg / idcg if idcg else 0.0)

        for c, _ in results_k:
            results += 1
            if c.entity_id == ref.entity_id:
                self_leaks += 1
            if c.district != ref.district:
                locality_bad += 1
            if c.property_type != ref.property_type:
                type_bad += 1
            if c.source == "TINIX_RESEARCH":
                tinix_leaks += 1

        entities = [c.entity_id for c, _ in results_k]
        duplicates += len(entities) - len(set(entities))

    return {
        "precision@k": statistics.fmean(precisions) if precisions else 0.0,
        "recall@k": statistics.fmean(recalls) if recalls else 0.0,
        "ndcg@k": statistics.fmean(ndcgs) if ndcgs else 0.0,
        "self_match_leak": self_leaks / results if results else 0.0,
        "duplicate_rate": duplicates / results if results else 0.0,
        "locality_error": locality_bad / results if results else 0.0,
        "type_error": type_bad / results if results else 0.0,
        "tinix_leaks": float(tinix_leaks),
        "cohorts": float(reference_count),
        "results": float(results),
    }


def _log2(value: float) -> float:
    import math
    return math.log2(value) if value > 0 else 0.0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--k", type=int, default=5)
    parser.add_argument("--seed", type=int, default=20261127)
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    cohorts = build_cohorts(args.seed)
    rows = {name: evaluate(name, cohorts, args.k) for name in ("A", "B", "C", "D")}

    if args.json:
        print(json.dumps({"k": args.k, "seed": args.seed, "cohorts": len(cohorts), "rows": rows},
                         ensure_ascii=False, indent=2))
        return 0

    print(f"SYNTHETIC_BENCHMARK  k={args.k} seed={args.seed} cohorts={len(cohorts)}")
    header = f"{'approach':34s} {'P@k':>6s} {'R@k':>6s} {'NDCG':>6s} {'self':>6s} {'dup':>6s} {'loc':>6s} {'type':>6s} {'tinix':>6s}"
    print(header)
    print("-" * len(header))
    labels = {
        "A": "A baseline (band + id-only self)",
        "B": "B corrected retrieval + entity dedupe",
        "C": "C B + type-aware similarity",
        "D": "D C + confidence gate",
    }
    for name in ("A", "B", "C", "D"):
        r = rows[name]
        print(f"{labels[name]:34s} {r['precision@k']:6.3f} {r['recall@k']:6.3f} {r['ndcg@k']:6.3f} "
              f"{r['self_match_leak']:6.3f} {r['duplicate_rate']:6.3f} {r['locality_error']:6.3f} "
              f"{r['type_error']:6.3f} {int(r['tinix_leaks']):6d}")
    digest = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()[:16]
    print(f"\nfixture seed {args.seed} · k={args.k} · digest {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
