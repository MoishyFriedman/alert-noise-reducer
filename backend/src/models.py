from __future__ import annotations

from datetime import datetime

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from .db import Base


class Alert(Base):
    __tablename__ = "alerts"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    host: Mapped[str] = mapped_column(String, nullable=False)
    service: Mapped[str] = mapped_column(String, nullable=False)
    severity: Mapped[str] = mapped_column(String, nullable=False)
    message: Mapped[str] = mapped_column(String, nullable=False)
    tags: Mapped[list[str]] = mapped_column(JSONB, nullable=False, default=list)

    __table_args__ = (
        CheckConstraint("severity in ('critical','warning','info')", name="ck_alerts_severity"),
        Index("ix_alerts_service_host_ts", "service", "host", "timestamp"),
        Index("ix_alerts_timestamp", "timestamp"),
    )


class Incident(Base):
    __tablename__ = "incidents"

    id: Mapped[str] = mapped_column(String, primary_key=True)
    host: Mapped[str | None] = mapped_column(String, nullable=True)  # null: cascade spans hosts
    service: Mapped[str] = mapped_column(String, nullable=False)
    severity_tier: Mapped[str] = mapped_column(String, nullable=False)  # 'info' | 'actionable'
    max_severity: Mapped[str] = mapped_column(String, nullable=False)
    alert_count: Mapped[int] = mapped_column(nullable=False)
    first_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_seen: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    duration_s: Mapped[int] = mapped_column(nullable=False)
    crit_count: Mapped[int] = mapped_column(nullable=False, default=0)
    warn_count: Mapped[int] = mapped_column(nullable=False, default=0)
    info_count: Mapped[int] = mapped_column(nullable=False, default=0)
    title: Mapped[str] = mapped_column(String, nullable=False)
    correlation: Mapped[str] = mapped_column(String, nullable=False)  # 'base' | 'cascade'
    dependency: Mapped[str | None] = mapped_column(String, nullable=True)

    __table_args__ = (
        CheckConstraint("severity_tier in ('info','actionable')", name="ck_incidents_tier"),
        CheckConstraint("correlation in ('base','cascade')", name="ck_incidents_correlation"),
        Index("ix_incidents_sev_lastseen", "max_severity", "last_seen"),
    )


class IncidentAlert(Base):
    __tablename__ = "incident_alerts"

    incident_id: Mapped[str] = mapped_column(
        ForeignKey("incidents.id", ondelete="CASCADE"), primary_key=True
    )
    alert_id: Mapped[str] = mapped_column(ForeignKey("alerts.id"), primary_key=True)

    __table_args__ = (Index("ix_incident_alerts_incident", "incident_id"),)
