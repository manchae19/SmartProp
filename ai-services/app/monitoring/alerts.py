"""Offline alert-window semantics. No rules, scheduler or notifications are enabled."""

from dataclasses import dataclass
from math import isfinite

from .accumulator import WINDOW_SECONDS, Availability, boundary
from .schema import InvalidTelemetry, MAX_VALUE, integer


def _finite(value):
    return ((type(value) is int and -MAX_VALUE <= value <= MAX_VALUE)
            or (type(value) is float and isfinite(value) and abs(value) <= MAX_VALUE))


@dataclass(frozen=True, slots=True)
class Policy:
    reference: int
    warning: float
    critical: float
    recovery: float
    confirm: int = 2
    cooldown: int = 2
    integrity: bool = False

    def __post_init__(self):
        if (not integer(self.reference) or not self.reference
                or any(not _finite(n) for n in (self.warning, self.critical, self.recovery))
                or not self.recovery < self.warning <= self.critical
                or not integer(self.confirm, 60) or not self.confirm or not integer(self.cooldown, 60)
                or type(self.integrity) is not bool):
            raise InvalidTelemetry("invalid_alert_policy")


@dataclass(frozen=True, slots=True)
class Incident:
    last_end: int | None = None
    level: int = 0
    warning_streak: int = 0
    critical_streak: int = 0
    recovery_streak: int = 0
    cooldown_until: int = 0
    state: Availability = Availability.NOT_AVAILABLE


class WindowAlerts:
    def __init__(self, policy, *, enabled=False):
        if type(policy) is not Policy or type(enabled) is not bool:
            raise InvalidTelemetry("invalid_alert_policy")
        self._policy = policy
        self._enabled = enabled
        self._incident = Incident(state=Availability.NOT_AVAILABLE if enabled else Availability.NOT_ENABLED)

    @property
    def incident(self):
        return self._incident

    def checkpoint(self):
        return self._policy, self._incident

    def restore(self, checkpoint):
        """Only a same-policy trusted checkpoint can carry a prior incident across restart."""
        if (not self._enabled or type(checkpoint) is not tuple or len(checkpoint) != 2
                or type(checkpoint[0]) is not Policy or checkpoint[0] != self._policy
                or type(checkpoint[1]) is not Incident or self._incident.last_end is not None):
            raise InvalidTelemetry("incompatible_alert_checkpoint")
        incident = checkpoint[1]
        if ((incident.last_end is not None and not boundary(incident.last_end))
                or not integer(incident.level, 2)
                or any(not integer(n, self._policy.confirm) for n in (
                    incident.warning_streak, incident.critical_streak, incident.recovery_streak))
                or not integer(incident.cooldown_until) or type(incident.state) is not Availability):
            raise InvalidTelemetry("invalid_alert_checkpoint")
        self._incident = incident

    def observe(self, end, reference, evidence, value=None):
        if not self._enabled:
            return "disabled"
        if (not boundary(end) or not end or not integer(reference) or type(evidence) is not Availability):
            raise InvalidTelemetry("invalid_alert_window")
        previous = self._incident
        if previous.last_end is not None and end <= previous.last_end:
            return "duplicate" if end == previous.last_end else "late"
        skipped = previous.last_end is not None and end != previous.last_end + WINDOW_SECONDS
        if (reference != self._policy.reference or evidence is not Availability.AVAILABLE or not _finite(value)):
            state = Availability.STALE if previous.level else Availability.INSUFFICIENT_EVIDENCE
            self._incident = Incident(end, previous.level, cooldown_until=previous.cooldown_until, state=state)
            return "insufficient"
        p = self._policy
        warned = min(p.confirm, (0 if skipped else previous.warning_streak) + 1) if value >= p.warning else 0
        critical = min(p.confirm, (0 if skipped else previous.critical_streak) + 1) if value >= p.critical else 0
        clean = min(p.confirm, (0 if skipped else previous.recovery_streak) + 1) if value <= p.recovery else 0
        level, cooldown = previous.level, previous.cooldown_until
        event = None
        if level and clean == p.confirm and not skipped:
            level, cooldown = 0, end + WINDOW_SECONDS * (p.cooldown + 1)
            event = "recovered"
        elif level < 2 and critical == p.confirm and (level or end >= cooldown or p.integrity):
            level, event = 2, "critical"
        elif not level and end >= cooldown and warned == p.confirm:
            level, event = 1, "warning"
        state = Availability.STALE if skipped and level else Availability.AVAILABLE
        self._incident = Incident(end, level, warned, critical, clean, cooldown, state)
        return event
