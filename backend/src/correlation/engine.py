from __future__ import annotations

from collections import defaultdict

from ..config import CorrelationConfig
from .cascade import pass_b
from .dtos import AlertDTO, IncidentVO
from .fingerprint import SEVERITY_RANK, group_key, max_severity, tier


def _severity_counts(members: list[AlertDTO]) -> dict[str, int]:
    counts = {"critical": 0, "warning": 0, "info": 0}
    for member in members:
        counts[member.severity] = counts.get(member.severity, 0) + 1
    return counts


def _shared_region(members: list[AlertDTO]) -> str | None:
    regions = {member.region() for member in members}
    return regions.pop() if len(regions) == 1 else None


def _dependencies(members: list[AlertDTO]) -> frozenset[str]:
    deps: set[str] = set()
    for member in members:
        deps |= member.dependencies()
    return frozenset(deps)


def _representative(members: list[AlertDTO]) -> AlertDTO:
    top = max(SEVERITY_RANK.get(member.severity, 0) for member in members)
    candidates = [member for member in members if SEVERITY_RANK.get(member.severity, 0) == top]
    return min(candidates, key=lambda member: (member.timestamp, member.id))


def build_incident(members: list[AlertDTO]) -> IncidentVO:
    members = sorted(members, key=lambda member: (member.timestamp, member.id))
    first, last = members[0].timestamp, members[-1].timestamp
    counts = _severity_counts(members)
    msev = max_severity([member.severity for member in members])
    host, service = members[0].host, members[0].service
    rep = _representative(members)
    return IncidentVO(
        id="base:" + members[0].id,
        title=f"{msev.upper()} · {service} on {host} — {rep.message}",
        host=host,
        service=service,
        severity_tier=tier(members[0].severity),
        max_severity=msev,
        alert_count=len(members),
        first_seen=first,
        last_seen=last,
        duration_s=int((last - first).total_seconds()),
        crit_count=counts["critical"],
        warn_count=counts["warning"],
        info_count=counts["info"],
        correlation="base",
        dependency=None,
        member_alert_ids=[member.id for member in members],
        anchor_alert_id=members[0].id,
        region=_shared_region(members),
        dependencies=_dependencies(members),
    )


def pass_a(alerts: list[AlertDTO], config: CorrelationConfig) -> list[IncidentVO]:
    buckets: dict[tuple[str, str, str], list[AlertDTO]] = defaultdict(list)
    for alert in alerts:
        buckets[group_key(alert)].append(alert)

    incidents: list[IncidentVO] = []
    for group in buckets.values():
        group.sort(key=lambda alert: (alert.timestamp, alert.id))
        window = [group[0]]
        for prev, cur in zip(group, group[1:]):
            if cur.timestamp - prev.timestamp <= config.session_gap:
                window.append(cur)          
            else:
                incidents.append(build_incident(window))
                window = [cur]
        incidents.append(build_incident(window))
    return incidents


def correlate(alerts: list[AlertDTO], config: CorrelationConfig) -> list[IncidentVO]:
    return pass_b(pass_a(alerts, config), config)
