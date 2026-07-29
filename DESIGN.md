# Design Write-up — Alert Noise Reducer

## Correlation logic, and why

Correlation runs in two passes over the alert set, each addressing a distinct way real
alerts cluster into one incident.

**Pass A — base grouping (session window).** Alerts are grouped by
`(host, service, severity_tier)`, where `severity_tier` splits `info` from
`{warning, critical}`. Within a group, consecutive alerts (sorted by time) join the same
incident as long as the gap between them is under 10 minutes; a larger gap starts a new
incident. Rationale: a real incident is a *burst* — the same problem re-firing every
30–60s — not a single event, so grouping needs to extend across the whole burst, not just
collapse exact duplicates. `info` is excluded from `warning`/`critical` because it's a
different class of signal (deploys, backups, cert renewals) that shouldn't be conflated
with something actionable, even on the same host. `warning` and `critical` are kept
together deliberately: a problem escalating from warning to critical is one incident
getting worse, not two.

**Pass B — cascade merge (cross-service).** Pass A groups per host+service, so a
downstream-dependency failure fragments: `payment-api` timeouts on 4 hosts plus
`fraud-check` OOM errors on a 5th become 5 separate incidents, even though they're one
root cause. Pass B re-merges these using the `dependency:<x>` tag: any incident whose
alerts declare `dependency:fraud-check` is folded into the `fraud-check` incident,
provided they're in the **same region** (a merge guard — two independent same-service
cascades in different regions must never merge) and close in time. Rationale: the
assignment's own framing — "a downstream dependency taking everything down with it" — is
exactly this shape, and a clear rule beats a vague one.

**Result on the sample data: 50 alerts → 19 incidents (62% reduction).** The cascade pass
collapses 17 alerts (`payment-api` × 4 hosts + `fraud-check`) into one incident spanning 2
services and 5 hosts. Three more bursts collapse similarly (`nginx`/web-03 502s: 8→1,
`postgres`/db-01 latency: 6→1, `redis`/cache-02 memory: 4→1). The remaining 15 incidents
are singletons — isolated `info` events and one-off warnings with nothing to correlate
against, correctly left alone rather than force-merged.

Incident identity is anchored on the **earliest member alert's id** (e.g.
`base:evt-0002`), not a raw timestamp — the grouping key is what defines an incident's
identity, and the anchor alert only distinguishes *which occurrence* when the same key
recurs later. This keeps ids deterministic and stable across reruns (`recorrelate` is a
pure function of the alert set) without baking a timestamp value into identity.

## Why this stack

**Python/FastAPI** for the backend: this is fundamentally a data-correlation pipeline,
and Python reads clearly for that kind of logic. FastAPI adds typed request/response
models and free OpenAPI docs for almost no boilerplate. **PostgreSQL** over something
like SQLite: the assignment explicitly asks for a justified DB choice, and Postgres gives
an honest production story — real indexes, `JSONB` tags, a clear path to time
partitioning — rather than a toy we'd have to caveat. Docker removes the setup cost that
would otherwise be Postgres's downside. **React + TypeScript + Vite** for the frontend:
fast HMR while building, and types shared against the API contract catch drift early.
**SQLAlchemy 2.x** for typed, explicit models without hiding the SQL.

## Assumptions and trade-offs

- The base grouping key deliberately excludes the message — `host + service + time` is
  enough, and it means an escalating problem that changes wording mid-burst still stays
  one incident. Trade-off: two genuinely unrelated problems on the same host+service in
  the same 10-minute window would merge. Rare, and tightening this would mean adding a
  message-similarity check to the grouping key if it becomes a real problem.
- The base key is per-host, so cross-host correlation depends entirely on the cascade
  pass. Without a `dependency` tag, a burst spread across many hosts would stay
  fragmented — acceptable for this dataset, a real gap for hosts we don't yet know are
  related.
- Correlation is a full **batch recompute** over the whole alert set (clear incidents,
  re-run, rewrite) rather than incremental — simple and always consistent, but not how
  it'd work at stream scale.
- `Base.metadata.create_all()` instead of Alembic migrations — the right call for a
  from-scratch schema at this scope; Alembic would be the production choice.
- `info` alerts are kept as visible singleton incidents rather than dropped, so the UI
  doesn't silently hide data — visible-but-unobtrusive over invisible.

## What I'd do with more time

- Move ingestion to `POST /alerts` behind a queue/stream, and turn the correlation engine
  into a windowed stream consumer (same grouping key, live watermarks instead of a
  bounded batch) — the engine is already a pure, swappable function so this is a
  transport change, not a rewrite.
- Fuzzy message similarity (normalizing digits/ids/whitespace out of the message, then
  matching) for correlating messier real-world log text beyond exact/near-exact matches.
- Time-partition the `alerts` table with a retention policy, add a GIN index on `tags`,
  and add pagination/filtering (service, severity, region) to the API and UI.
- Alembic migrations; basic auth; an incident timeline/graph view instead of a flat table.
