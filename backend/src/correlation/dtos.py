from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime


def _tag_value(tags: tuple[str, ...], key: str) -> str | None:
    prefix = key + ":"
    for t in tags:
        if t.startswith(prefix):
            return t.split(":", 1)[1]
    return None


@dataclass(frozen=True)
class AlertDTO:

    id: str
    timestamp: datetime
    host: str
    service: str
    severity: str  # 'critical' | 'warning' | 'info'
    message: str
    tags: tuple[str, ...] = ()

    def region(self) -> str | None:
        return _tag_value(self.tags, "region")

    def dependencies(self) -> frozenset[str]:
        return frozenset(
            t.split(":", 1)[1] for t in self.tags if t.startswith("dependency:")
        )


@dataclass
class IncidentVO:

    id: str
    title: str
    host: str | None
    service: str
    severity_tier: str  # 'info' | 'actionable'
    max_severity: str
    alert_count: int
    first_seen: datetime
    last_seen: datetime
    duration_s: int
    crit_count: int
    warn_count: int
    info_count: int
    correlation: str  # 'base' | 'cascade'
    dependency: str | None
    member_alert_ids: list[str]
    anchor_alert_id: str
    region: str | None = None
    dependencies: frozenset[str] = field(default_factory=frozenset)
