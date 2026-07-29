from __future__ import annotations

from sqlalchemy import case, delete, func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from .config import CorrelationConfig
from .correlation import SEVERITY_RANK, AlertDTO, IncidentVO, correlate
from .models import Alert, Incident, IncidentAlert


def upsert_alerts(db: Session, alerts: list[AlertDTO]) -> None:
    for alert in alerts:
        insert_stmt = pg_insert(Alert).values(
            id=alert.id,
            timestamp=alert.timestamp,
            host=alert.host,
            service=alert.service,
            severity=alert.severity,
            message=alert.message,
            tags=list(alert.tags),
        )
        upsert_stmt = insert_stmt.on_conflict_do_update(
            index_elements=["id"],
            set_={
                "timestamp": insert_stmt.excluded.timestamp,
                "host": insert_stmt.excluded.host,
                "service": insert_stmt.excluded.service,
                "severity": insert_stmt.excluded.severity,
                "message": insert_stmt.excluded.message,
                "tags": insert_stmt.excluded.tags,
            },
        )
        db.execute(upsert_stmt)
    db.commit()


def all_alerts(db: Session) -> list[AlertDTO]:
    rows = db.scalars(select(Alert).order_by(Alert.timestamp)).all()
    return [
        AlertDTO(
            id=row.id,
            timestamp=row.timestamp,
            host=row.host,
            service=row.service,
            severity=row.severity,
            message=row.message,
            tags=tuple(row.tags or []),
        )
        for row in rows
    ]


def replace_incidents(db: Session, incidents: list[IncidentVO]) -> None:
    db.execute(delete(IncidentAlert))
    db.execute(delete(Incident))
    db.add_all(
        Incident(
            id=incident.id,
            host=incident.host,
            service=incident.service,
            severity_tier=incident.severity_tier,
            max_severity=incident.max_severity,
            alert_count=incident.alert_count,
            first_seen=incident.first_seen,
            last_seen=incident.last_seen,
            duration_s=incident.duration_s,
            crit_count=incident.crit_count,
            warn_count=incident.warn_count,
            info_count=incident.info_count,
            title=incident.title,
            correlation=incident.correlation,
            dependency=incident.dependency,
        )
        for incident in incidents
    )
    db.add_all(
        IncidentAlert(incident_id=incident.id, alert_id=alert_id)
        for incident in incidents
        for alert_id in incident.member_alert_ids
    )
    db.commit()


def recompute_incidents(db: Session, config: CorrelationConfig) -> list[IncidentVO]:
    alerts = all_alerts(db)
    incidents = correlate(alerts, config)
    replace_incidents(db, incidents)
    return incidents


def has_alerts(db: Session) -> bool:
    return (db.scalar(select(func.count()).select_from(Alert)) or 0) > 0


def _severity_rank() -> case:
    return case(
        *[(Incident.max_severity == sev, rank) for sev, rank in SEVERITY_RANK.items() if rank > 0],
        else_=0,
    )


def list_incidents(db: Session) -> list[Incident]:
    """Sorted severity desc, then most recent first — matches the UI's default view."""
    return db.scalars(
        select(Incident).order_by(_severity_rank().desc(), Incident.last_seen.desc())
    ).all()


def incident_alerts(db: Session, incident_id: str) -> list[Alert]:
    """Raw alerts for one incident (drill-in)."""
    return db.scalars(
        select(Alert)
        .join(IncidentAlert, IncidentAlert.alert_id == Alert.id)
        .where(IncidentAlert.incident_id == incident_id)
        .order_by(Alert.timestamp)
    ).all()


def stats(db: Session) -> dict:
    alert_count = db.scalar(select(func.count()).select_from(Alert)) or 0
    incident_count = db.scalar(select(func.count()).select_from(Incident)) or 0
    reduction_pct = round((1 - incident_count / alert_count) * 100) if alert_count else 0
    return {"raw_alerts": alert_count, "incidents": incident_count, "reduction_pct": reduction_pct}
