"""Pydantic response models. Mirror these field-for-field in frontend/src/types.ts."""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    timestamp: datetime
    host: str
    service: str
    severity: str
    message: str
    tags: list[str]


class IncidentOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str
    host: str | None
    service: str
    severity_tier: str
    max_severity: str
    alert_count: int
    first_seen: datetime
    last_seen: datetime
    duration_s: int
    crit_count: int
    warn_count: int
    info_count: int
    correlation: str
    dependency: str | None


class StatsOut(BaseModel):
    raw_alerts: int
    incidents: int
    reduction_pct: int
