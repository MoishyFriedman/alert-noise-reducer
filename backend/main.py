from __future__ import annotations

from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from src import repository
from src.config import settings
from src.correlation.loader import load_alerts
from src.db import SessionLocal, get_db, init_db
from src.middleware import RequestLoggingMiddleware
from src.schemas import AlertOut, IncidentOut, StatsOut


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    db = SessionLocal()
    try:
        if not repository.has_alerts(db):
            alerts = load_alerts(settings.seed_file)
            repository.upsert_alerts(db, alerts)
            repository.recompute_incidents(db, settings.correlation_config())
    finally:
        db.close()
    yield


app = FastAPI(title="Alert Noise Reducer", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(RequestLoggingMiddleware)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/incidents", response_model=list[IncidentOut])
def get_incidents(db: Session = Depends(get_db)) -> list[IncidentOut]:
    return repository.list_incidents(db)


@app.get("/api/incidents/{incident_id}/alerts", response_model=list[AlertOut])
def get_incident_alerts(incident_id: str, db: Session = Depends(get_db)) -> list[AlertOut]:
    alerts = repository.incident_alerts(db, incident_id)
    if not alerts:
        raise HTTPException(status_code=404, detail="incident not found")
    return alerts


@app.get("/api/stats", response_model=StatsOut)
def get_stats(db: Session = Depends(get_db)) -> StatsOut:
    return repository.stats(db)


@app.post("/api/recorrelate", response_model=StatsOut)
def recorrelate(db: Session = Depends(get_db)) -> StatsOut:
    repository.recompute_incidents(db, settings.correlation_config())
    return repository.stats(db)
