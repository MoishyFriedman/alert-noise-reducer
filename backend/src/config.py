from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from pydantic_settings import BaseSettings


@dataclass(frozen=True)
class CorrelationConfig:
    session_gap: timedelta = timedelta(minutes=10)
    cascade_enabled: bool = True
    cascade_window: timedelta = timedelta(minutes=10)


DEFAULT_CONFIG = CorrelationConfig()

_DEFAULT_SEED_FILE = Path(__file__).resolve().parents[2] / "data" / "sample_alerts.json"


class Settings(BaseSettings):

    database_url: str = "postgresql+psycopg://alertnoise:alertnoise_dev@localhost:5432/alertnoise"
    seed_file: str = str(_DEFAULT_SEED_FILE)
    session_gap_minutes: int = int(DEFAULT_CONFIG.session_gap.total_seconds() / 60)
    cascade_enabled: bool = DEFAULT_CONFIG.cascade_enabled
    cascade_window_min: int = int(DEFAULT_CONFIG.cascade_window.total_seconds() / 60)
    cors_origins: list[str] = ["http://localhost:5173", "http://localhost", "http://localhost:80"]

    def correlation_config(self) -> CorrelationConfig:
        return CorrelationConfig(
            session_gap=timedelta(minutes=self.session_gap_minutes),
            cascade_enabled=self.cascade_enabled,
            cascade_window=timedelta(minutes=self.cascade_window_min),
        )


settings = Settings()
