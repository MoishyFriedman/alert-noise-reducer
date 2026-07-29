# Alert Noise Reducer

Takes ~50 raw monitoring alerts and correlates them into a much smaller set of
**incidents** — grouping bursts on the same host/service into one, and folding
downstream-dependency cascades (e.g. a database falling over and taking a dependent
service down with it) into a single root-cause incident. Three layers: Postgres, a
FastAPI backend with a pure correlation engine, and a React/TS frontend.

On the provided sample data: **50 alerts → 19 incidents (62% reduction)**.

See [`DESIGN.md`](DESIGN.md) for the correlation logic, stack rationale, and trade-offs.

---

## Quick start (recommended — one command)

Requires Docker Desktop (or another Docker Engine + Compose v2).

```bash
git clone <repo-url> && cd alert-noise-reducer
docker compose up --build
```

- **UI:** http://localhost:5173
- **API docs (OpenAPI):** http://localhost:8000/docs

Data is seeded automatically on first boot (only if the alerts table is empty — safe
to restart). You should see a banner reading **"50 → 19, 62% reduction"** and a sorted
incident table; click any row to drill into its raw alerts.

To stop: `docker compose down` (add `-v` to also drop the Postgres volume and reseed
fresh next time).

---

## What you'll see

- A **noise-reduction banner**: `50 alerts → 19 incidents · 62% reduction`.
- An **incident table**, sorted critical → warning → info (most recent first within
  each tier), with severity badge, title, alert count + severity breakdown, first/last
  seen, and duration.
- The flagship correlation result: one **cascade** incident (⛓ chip) merging the
  `payment-api` timeout burst with the `fraud-check` service that caused it — 17 raw
  alerts across 5 hosts, collapsed into one.
- Clicking any row expands a **drill-down** table of the underlying raw alerts
  (timestamp, host, service, severity, message, tags).

---

## Local dev path (faster iteration, hot reload)

Run Postgres in Docker, everything else natively. The backend has a dedicated
`backend/run.py` script for this — just run `python run.py` and it starts uvicorn with
hot reload, no need to remember the module path or flags.

```bash
# 1. Postgres only
docker compose up -d db

# 2. Backend (hot reload via run.py)
cd backend
python3.12 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
# (or, if you use uv: uv venv --python 3.12 .venv && uv pip install -e ".[dev]")
python run.py
# -> http://localhost:8000  (auto-seeds from ../data/sample_alerts.json on first boot)
# equivalent to: uvicorn main:app --reload --port 8000

# 3. Frontend (Vite, HMR) — in a second terminal
cd frontend
npm install
npm run dev
# -> http://localhost:5173
```

## Run tests

Unit tests cover the correlation engine (the part with real logic) — pure functions,
no database required.

```bash
cd backend
source .venv/bin/activate   # if not already active
pytest -q
```

## Re-running correlation / tuning

The engine's knobs are environment variables (see `backend/src/config.py`):

| Variable | Default | Meaning |
|---|---|---|
| `SESSION_GAP_MINUTES` | `10` | Max gap between alerts to stay in the same burst. |
| `CASCADE_ENABLED` | `true` | Toggle the cross-service dependency-merge pass. |
| `CASCADE_WINDOW_MIN` | `10` | Time window for merging a dependent incident into its provider. |
| `DATABASE_URL` | `postgresql+psycopg://alertnoise:alertnoise_dev@localhost:5432/alertnoise` | Postgres connection string. |
| `SEED_FILE` | `../data/sample_alerts.json` | Path to the alerts file loaded on first boot. |
| `CORS_ORIGINS` | `["http://localhost:5173","http://localhost","http://localhost:80"]` | Allowed frontend origins. |

After changing a knob, re-run correlation without re-seeding:

```bash
curl -X POST http://localhost:8000/api/recorrelate
```

## Project layout

```
alert-noise-reducer/
├── backend/
│   ├── main.py                 # FastAPI app + routes (entry point)
│   ├── run.py                  # `python run.py` — local dev launcher (uvicorn + reload)
│   ├── src/
│   │   ├── config.py          # settings (env-driven)
│   │   ├── db.py               # engine/session
│   │   ├── models.py           # SQLAlchemy: Alert, Incident, IncidentAlert
│   │   ├── schemas.py          # Pydantic response models
│   │   ├── repository.py       # data access (upsert, correlate+persist, reads)
│   │   ├── middleware.py        # request logging + catch-all error handling
│   │   └── correlation/         # the pure engine — no DB, no HTTP
│   │       ├── engine.py        # Pass A: session-window grouping
│   │       ├── cascade.py       # Pass B: cross-service dependency merge
│   │       ├── fingerprint.py   # severity tier, grouping key, severity ranking
│   │       ├── dtos.py          # AlertDTO / IncidentVO value objects
│   │       └── loader.py        # JSON -> AlertDTO
│   ├── tests/test_correlation.py
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── App.tsx, api.ts, types.ts, format.ts
│   │   └── components/          # IncidentTable, IncidentRow, AlertDrilldown, ...
│   └── Dockerfile
├── data/sample_alerts.json
├── docker-compose.yml
├── README.md
└── DESIGN.md
```

## Ports

| Service | Port |
|---|---|
| Frontend | 5173 |
| Backend API | 8000 |
| Postgres | 5432 |
