from __future__ import annotations

from collections.abc import Iterable

from .dtos import AlertDTO

SEVERITY_RANK = {"info": 0, "warning": 1, "critical": 2}


def tier(severity: str) -> str:
    return "info" if severity == "info" else "actionable"


def group_key(alert: AlertDTO) -> tuple[str, str, str]:
    return (alert.host, alert.service, tier(alert.severity))


def max_severity(severities: Iterable[str]) -> str:
    return max(severities, key=lambda s: SEVERITY_RANK.get(s, 0))
