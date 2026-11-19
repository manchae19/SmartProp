"""Ranking the suggestion list by real commute time.

Two phrasings mean different things and must not be conflated:

* "khoảng 25 phút" is a preference — a faster route ranks higher, a slower one may
  still appear and is labelled with its own status.
* "tối đa 25 phút" is a hard limit — only listings with a confirmed route inside the
  limit stay in the list.

Straight-line distance is never converted into minutes.
"""
import re

from .intent import fold

SOFT = re.compile(r"\b(?:khoang|tam|around|about)\s+(\d{1,3})\s*phut\b")
HARD = re.compile(r"\b(?:toi da|khong qua|duoi|it hon|max)\s+(\d{1,3})\s*phut\b")
PLAIN = re.compile(r"\b(\d{1,3})\s*phut\b")
COMMUTE_WORD = re.compile(r"\b(?:di lam|cho lam|noi lam viec|commute)\b")
WORK_NEAR = re.compile(r"\b(?:gan)\b.*\b(?:cho lam|noi lam viec|co quan|cong ty)\b")


def wants_work_proximity(question):
    """True when the user asked to rank by the trip to work, with or without minutes."""
    return bool(WORK_NEAR.search(fold(question)))


def limit_from(question):
    """(minutes, 'SOFT'|'HARD') or (None, None)."""
    text = fold(question)
    hard = HARD.search(text)
    if hard:
        value = int(hard.group(1))
        return (value, "HARD") if 1 <= value <= 180 else (None, None)
    soft = SOFT.search(text)
    if soft:
        value = int(soft.group(1))
        return (value, "SOFT") if 1 <= value <= 180 else (None, None)
    # A bare "25 phút" only counts when the question is about the commute.
    if COMMUTE_WORD.search(text):
        plain = PLAIN.search(text)
        if plain:
            value = int(plain.group(1))
            return (value, "SOFT") if 1 <= value <= 180 else (None, None)
    return (None, None)


def rank(entries, limit_minutes, kind, limit):
    """Order candidates by route time and apply the hard filter.

    `entries` is a list of dicts with at least `id`; `route` holds the measured
    commute or None when the route could not be computed.
    """
    if not kind:
        return entries[:limit]
    measured = [e for e in entries if e.get("route")]
    unmeasured = [e for e in entries if not e.get("route")]
    measured.sort(key=lambda e: e["route"]["durationSeconds"])
    if kind == "HARD":
        if not limit_minutes:
            return entries[:limit]
        keep = [e for e in measured
                if e["route"]["durationSeconds"] <= limit_minutes * 60]
        return keep[:limit]
    # SOFT: everything with a route first (fastest first), then the unmeasured ones
    # so the user can see they exist but are not ranked by a guessed duration.
    return (measured + unmeasured)[:limit]
