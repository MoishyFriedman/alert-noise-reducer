from __future__ import annotations

from collections import defaultdict
from datetime import timedelta

from ..config import CorrelationConfig
from .dtos import IncidentVO
from .fingerprint import max_severity


def _time_close(a: IncidentVO, b: IncidentVO, window: timedelta) -> bool:
    if a.last_seen < b.first_seen:
        return (b.first_seen - a.last_seen) <= window
    if b.last_seen < a.first_seen:
        return (a.first_seen - b.last_seen) <= window
    return True  # overlapping intervals


class _UnionFind:
    def __init__(self, n: int) -> None:
        self._parent = list(range(n))

    def find(self, x: int) -> int:
        while self._parent[x] != x:
            self._parent[x] = self._parent[self._parent[x]]  # path halving
            x = self._parent[x]
        return x

    def union(self, a: int, b: int) -> None:
        self._parent[self.find(a)] = self.find(b)


def _build_cascade(members: list[IncidentVO]) -> IncidentVO:
    ordered = sorted(members, key=lambda member: (member.first_seen, member.anchor_alert_id))
    services = {member.service for member in members}

    referenced: set[str] = set()
    for member in members:
        referenced |= member.dependencies
    provider = next((d for d in sorted(referenced) if d in services), None)
    dep = provider or (sorted(referenced)[0] if referenced else ordered[0].service)

    first = min(member.first_seen for member in members)
    last = max(member.last_seen for member in members)
    msev = max_severity([member.max_severity for member in members])
    member_ids = [aid for member in members for aid in member.member_alert_ids]
    n_hosts = len({member.host for member in members if member.host})
    anchor = ordered[0].anchor_alert_id

    return IncidentVO(
        id="casc:" + anchor,
        title=f"{msev.upper()} · {dep} cascade — {len(services)} services / {n_hosts} hosts affected",
        host=None,  # a cascade spans hosts
        service=dep,
        severity_tier="actionable",
        max_severity=msev,
        alert_count=len(member_ids),
        first_seen=first,
        last_seen=last,
        duration_s=int((last - first).total_seconds()),
        crit_count=sum(member.crit_count for member in members),
        warn_count=sum(member.warn_count for member in members),
        info_count=sum(member.info_count for member in members),
        correlation="cascade",
        dependency=dep,
        member_alert_ids=member_ids,
        anchor_alert_id=anchor,
        region=ordered[0].region,
        dependencies=frozenset(),
    )


def pass_b(
    incidents: list[IncidentVO], config: CorrelationConfig
) -> list[IncidentVO]:
    if not config.cascade_enabled or len(incidents) < 2:
        return incidents

    all_deps: set[str] = set()
    for inc in incidents:
        all_deps |= inc.dependencies

    uf = _UnionFind(len(incidents))
    for dep in sorted(all_deps):
        participants = [
            i
            for i, inc in enumerate(incidents)
            if dep in inc.dependencies or inc.service == dep
        ]
        for x in range(len(participants)):
            for y in range(x + 1, len(participants)):
                a, b = incidents[participants[x]], incidents[participants[y]]
                if (
                    a.region
                    and b.region
                    and a.region == b.region
                    and _time_close(a, b, config.cascade_window)
                ):
                    uf.union(participants[x], participants[y])

    groups: dict[int, list[IncidentVO]] = defaultdict(list)
    for i, inc in enumerate(incidents):
        groups[uf.find(i)].append(inc)

    result: list[IncidentVO] = []
    for members in groups.values():
        result.append(members[0] if len(members) == 1 else _build_cascade(members))
    return result
