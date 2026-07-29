from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

from .dtos import AlertDTO


def parse_ts(value: str) -> datetime:
    """Parse ISO-8601 UTC (the sample uses a trailing 'Z')."""
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def load_alerts(path: str | Path) -> list[AlertDTO]:
    raw = json.loads(Path(path).read_text())
    return [
        AlertDTO(
            id=r["id"],
            timestamp=parse_ts(r["timestamp"]),
            host=r["host"],
            service=r["service"],
            severity=r["severity"],
            message=r["message"],
            tags=tuple(r.get("tags") or []),
        )
        for r in raw
    ]
