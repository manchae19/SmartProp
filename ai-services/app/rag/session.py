"""Bounded, short-lived, in-memory conversation context.

Design rules (Step 19.5.6):
* The store is memory only: no schema, no table, no disk.
* Context is NEVER an authorization source. Public and Research sessions live in
  separate namespaces (`scope`), so a public caller cannot read a research session
  even if it guesses an identifier.
* Context is also never a source of truth. It only remembers *criteria* and
  *references*; every fact shown to the user is re-read from the live APIs.
"""
from dataclasses import dataclass, field
import re
import secrets
import time
from threading import RLock

MAX_SESSIONS = 256
TTL_SECONDS = 1800.0          # 30 minutes of inactivity
MAX_TURNS = 12
MAX_PROPERTY_IDS = 10
MAX_AREA_IDS = 6
MAX_EVIDENCE_IDS = 24
SESSION_ID = re.compile(r"^[a-f0-9]{32}$")

CRITERIA_KEYS = ("budgetVnd", "purpose", "propertyType", "minAreaSqm", "district", "ward")


@dataclass
class Context:
    scope: str
    session_id: str
    created_at: float
    updated_at: float
    turns: int = 0
    budget_vnd: str | None = None
    purpose: str | None = None
    property_type: str | None = None
    min_area_sqm: str | None = None
    district: str | None = None
    ward: str | None = None
    last_property_ids: list = field(default_factory=list)
    referenced_property_id: str | None = None
    area_ids: list = field(default_factory=list)
    evidence_source_ids: list = field(default_factory=list)
    last_criteria: dict | None = None
    last_question: str | None = None
    needs: dict = field(default_factory=dict)

    def criteria(self):
        """Stored search criteria, exactly the shape the Recommendation API consumed."""
        return dict(self.last_criteria or {})

    def public(self):
        """Context projection safe to return to the browser (public data only)."""
        return {
            "turn": self.turns,
            "criteria": {k: v for k, v in {
                "budgetVnd": self.budget_vnd, "purpose": self.purpose,
                "propertyType": self.property_type, "minAreaSqm": self.min_area_sqm,
                "minPriceVnd": (self.last_criteria or {}).get("minPriceVnd"),
                "district": self.district, "ward": self.ward}.items() if v is not None},
            "lastPropertyIds": list(self.last_property_ids),
            "referencedPropertyId": self.referenced_property_id,
            "areaIds": list(self.area_ids),
        }


class SessionStore:
    def __init__(self, *, ttl=TTL_SECONDS, max_sessions=MAX_SESSIONS, clock=time.time):
        self._ttl = float(ttl)
        self._max = int(max_sessions)
        self._clock = clock
        self._lock = RLock()
        self._items: dict[tuple, Context] = {}

    # -- housekeeping -----------------------------------------------------
    def _prune(self, now):
        expired = [k for k, c in self._items.items() if now - c.updated_at > self._ttl]
        for key in expired:
            self._items.pop(key, None)
        if len(self._items) > self._max:
            for key, _ in sorted(self._items.items(), key=lambda kv: kv[1].updated_at)[: len(self._items) - self._max]:
                self._items.pop(key, None)

    def size(self):
        with self._lock:
            self._prune(self._clock())
            return len(self._items)

    # -- lifecycle --------------------------------------------------------
    def begin(self, session_id, *, scope):
        """Return (context, session_id, resumed). Unknown/expired ids never error."""
        if scope not in ("PUBLIC", "INTERNAL_RESEARCH") and not re.fullmatch(r"ACCOUNT:[0-9]{1,19}", scope):
            raise ValueError("INVALID_SESSION_SCOPE")
        now = self._clock()
        with self._lock:
            self._prune(now)
            if isinstance(session_id, str) and SESSION_ID.match(session_id):
                found = self._items.get((scope, session_id))
                if found is not None:
                    if found.turns >= MAX_TURNS:
                        # Hard cap: a conversation past its turn budget is retired, so one
                        # client cannot accumulate unbounded context. A fresh id is issued
                        # and the caller simply starts a new thread.
                        self._items.pop((scope, session_id), None)
                        found = None
                    else:
                        found.updated_at = now
                        found.turns += 1
                        return found, session_id, True
            new_id = secrets.token_hex(16)
            context = Context(scope=scope, session_id=new_id, created_at=now, updated_at=now, turns=1)
            self._items[(scope, new_id)] = context
            return context, new_id, False

    def reset(self, session_id, *, scope):
        with self._lock:
            return self._items.pop((scope, session_id), None) is not None

    def drop(self, context):
        with self._lock:
            self._items.pop((context.scope, context.session_id), None)

    # -- mutation ---------------------------------------------------------
    def record(self, context, *, criteria, property_ids, area_ids, evidence_ids,
               referenced_property_id=None, question=None):
        """Persist only bounded, server-derived state. Caller-supplied values never land here."""
        context.updated_at = self._clock()
        context.last_criteria = dict(criteria) if criteria else None
        context.budget_vnd = (str(criteria.get("budgetVnd")) if criteria and criteria.get("budgetVnd") is not None else None)
        context.purpose = criteria.get("purpose") if criteria else None
        context.property_type = criteria.get("propertyType") if criteria else None
        context.min_area_sqm = (str(criteria.get("minAreaSqm")) if criteria and criteria.get("minAreaSqm") is not None else None)
        context.district = criteria.get("district") if criteria else None
        context.ward = criteria.get("ward") if criteria else None
        if property_ids is not None:
            context.last_property_ids = list(dict.fromkeys(property_ids))[:MAX_PROPERTY_IDS]
        if area_ids is not None:
            context.area_ids = list(dict.fromkeys(area_ids))[:MAX_AREA_IDS]
        context.evidence_source_ids = list(dict.fromkeys(evidence_ids or []))[-MAX_EVIDENCE_IDS:]
        if referenced_property_id:
            context.referenced_property_id = referenced_property_id
        elif property_ids is not None and referenced_property_id is None:
            # A new search replaces the reference; never keep a stale one.
            context.referenced_property_id = None
        context.last_question = (question or "")[:2000]
        return context
