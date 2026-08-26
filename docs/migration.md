# Migration: turning `/run` into an asynchronous job

**Audience:** backend developers, with a frontend contract section
**Status:** plan — nothing below is implemented yet
**Endpoint affected:** `POST /apps/users/{user_id}/sessions/{session_id}/run`

## TL;DR

Today two `/run` calls for the same session can execute at the same time, and they corrupt each
other's session state. The fix is to stop treating a run as an HTTP request and start treating it
as a **job**: `POST .../run` returns `202 {run_id}` immediately, the work happens in a background
task, and the client polls `GET /runs/{run_id}` for the result.

One active run per session is then enforced by a **partial unique index in Postgres**, not by
application-level locking — so it stays correct even if the service is ever scaled to more than one
process.

---

## 1. The problem

`RootAgentRunner.run` is fully re-entrant. Nothing anywhere keys on `session_id`, so two POSTs to
the same session both enter `Runner.run_async` against the same ADK session.

### What breaks

1. **Stale history.** `run_async` snapshots the session (events + state) when it starts. Run B
   loads a snapshot that does not contain Run A's user message or answer, so B answers with no
   knowledge of A. To the user this looks like "the agent lost my context".

2. **Interleaved event log.** Both runs append events as they progress. `get_session` then returns
   a scrambled transcript — and it does not even sort events explicitly — so the frontend renders
   turns out of order.

3. **Stale-write failures.** ADK's `DatabaseSessionService.append_event` guards on the session's
   `last_update_time` against what is in storage. Whichever run is behind raises — possibly after
   minutes of LLM and MCP work — and the blanket `except Exception` in the router turns that into
   an opaque `500`. *(Confirm the exact behaviour in google-adk 2.4 in your environment; this is
   the classic symptom.)*

4. **State clobbering.** `state_delta` merges are last-writer-wins. The `new_session` title path in
   the `finally` block appends a system event that races the other run's appends.

5. **Artifact version race.** `_upload_artifact` saves under the raw `image_file.filename`, so two
   runs uploading the same filename in one session race on version assignment.

6. **No backpressure.** N concurrent runs means N times the LLM calls, MCP tool fan-out and DB
   connections. A user leaning on the send button multiplies cost linearly with nothing to stop it.

### Why you cannot detect it today

"A run is in flight" is not a property of the conversation, so it cannot be derived from the
conversation. You could guess from the session — ADK appends the incoming user message at the start
of `run_async`, so a started run usually leaves a trace:

> last event is a user message with no final agent response after it, and `last_update_time` is
> recent, therefore a run is probably in progress

This is wrong in both directions:

- A **crashed** run leaves the identical signature, forever. The session simply stops having a
  reply. You cannot distinguish "still thinking" from "died three hours ago" except by an arbitrary
  staleness threshold.
- A **long tool call** emits no events for minutes, so a perfectly healthy run looks dead.

The inference fails precisely on the case that matters. An explicit run record is required.

---

## 2. What the second `/run` should do

The mechanism follows from the policy, so pick the policy first.

| Policy | Behaviour | Trade-off |
|---|---|---|
| **A. Reject** | return `409 SESSION_BUSY` | simplest, correct, nothing is lost. Frontend must disable send. **Chosen.** |
| **B. Serialize** | second request waits for the first, then runs with full context | best fidelity, but holds an HTTP connection for minutes → gateway timeouts, and hides an unbounded queue behind a socket |
| **C. Cancel and replace** | abort the in-flight run, newest wins | nice "stop and ask something else" UX, but mid-run cancellation leaves partial events in Postgres and you must decide keep-vs-purge |

**Decision: A (reject) now.** It matches what chat UIs already do — input disabled while the
assistant is replying — and it is the only option that is safe without the job model. C becomes
feasible once runs are jobs, and is listed as a follow-up.

---

## 3. Course of action

### Now — stop the corruption

If the job migration will take more than a day, land this first as a stopgap. It is throwaway work
once Step 1 is in, but it is an hour and it stops the bleeding.

1. A busy `set` keyed on `(app_name, user_id, session_id)` in `RootAgentRunner`, acquired before
   `run_async` and released in `finally` — **spanning the title-creation block too**, since that
   appends events. A plain `set` is sufficient and no lock is needed: there is no `await` between
   the membership check and the insert, so it is atomic on a single event loop.
2. A `SessionBusyError` mapped to `409` with `Retry-After` and a machine-readable `code`.
3. `asyncio.timeout(...)` around the run, so a hung MCP call cannot hold a session busy forever.
4. Frontend disables send while a run is in flight.
5. A comment where uvicorn starts noting that adding `--workers` or a second replica invalidates
   the guard.

Step 4 is UX; step 1 is the guarantee. Both are needed — disabling a button does not survive
retries, two tabs, or anyone calling the API directly.

> Do **not** build heartbeat or lease-reaping machinery at this stage. There is no second process
> to defend against yet, and a process restart clearing the in-memory guard is the *correct*
> outcome: the run really did die.

### Next — the job model

Everything from Section 5 below. Worth doing not only for concurrency, but because it also retires
three problems you will hit regardless:

- minute-long HTTP requests dying at a gateway or proxy,
- a page reload losing an answer that has already been paid for,
- having no way to cancel a run or show progress.

Concurrency control becomes a property of the queue instead of something you defend by hand, and
run status becomes a resource you can query.

### Skip

The middle ground — distributed advisory locks, heartbeat leases, stale-lock reaping as a
*destination* — is real engineering that is only worth building as part of the job model. Build it
standalone and you will build it twice.

---

## 4. Target architecture

```
POST .../sessions/{sid}/run  ──►  insert row (queued)  ──►  202 {run_id}
                                      │
                                      └─► asyncio.create_task(execute)
                                                │  heartbeat per ADK event
                                                ▼
                                          update row (succeeded / failed)

GET /runs/{run_id}   ◄── client polls every ~2s ──►  reads that row
```

Two grounding facts about this repo that shape the design:

- **There is no general DB layer.** The deleted `services/db_session.py` was only an ADK wrapper;
  `DatabaseSessionService` owns its own SQLAlchemy engine internally. But `asyncpg==0.31.0` is
  already a direct dependency, so a runs table costs **zero new packages** using raw asyncpg.
  SQLAlchemy is available transitively via google-adk if you prefer an ORM — not worth it for one
  table.
- **Single process.** `uvicorn.run(app)` with no `--workers`, one container. The executor is
  therefore `asyncio.create_task`, not Celery or Redis. Do not add a broker at this scale.

### Delivery: polling or SSE

Both answer "is it done yet", but they invert who initiates.

**Polling** — the client asks repeatedly. Ordinary HTTP requests; each one opens, answers and
closes, and the server holds no per-client state.

```js
const { run_id } = await fetch(url, { method: "POST", body }).then(r => r.json());

while (true) {
  const run = await fetch(`/runs/${run_id}`).then(r => r.json());
  if (run.status !== "queued" && run.status !== "running") { render(run); break; }
  await sleep(2000);
}
```

**SSE (Server-Sent Events)** — the client opens *one* HTTP request that the server deliberately
never finishes, writing chunks into the still-open response body as things happen. One direction
only, server to client. The wire format is plain text, blank line between messages:

```
event: progress
data: {"status":"running","step":"querying mongodb"}

id: 7
event: done
data: {"status":"succeeded","response":"..."}

```

```js
const es = new EventSource(`/runs/${run_id}/events`);
es.onmessage = (e) => render(JSON.parse(e.data));
```

In FastAPI that is a `StreamingResponse` with `media_type="text/event-stream"` wrapping an async
generator fed from an `asyncio.Queue` that the job's `on_event` callback pushes into.

*(WebSocket is a third option — a full bidirectional socket. Not needed: the client has nothing to
say mid-run except "cancel", which is fine as a normal POST.)*

| | Polling | SSE |
|---|---|---|
| Latency to see the result | up to one interval (~2s) | immediate |
| Live progress narration | only via a persisted event cursor | natural |
| Connections held open | none | one per active run, per tab |
| Page reload / reconnect | just GET again | must reconnect and replay missed events |
| Proxy and load-balancer friendliness | ordinary requests | buffering and idle timeouts bite |
| Server-side state | none | a per-run subscriber queue |
| Cost of a 3-minute run | ~90 cheap indexed lookups | 1 held connection |

SSE gotchas, since these are the ones that surprise people:

- **Proxies buffer.** nginx will hold chunks until the response completes, defeating the point.
  Needs `proxy_buffering off` or the `X-Accel-Buffering: no` header. Behind a corporate proxy this
  is where you lose an afternoon.
- **Idle timeouts kill it.** If the agent thinks for 90s without emitting, an intermediary may drop
  the connection. Send periodic `: keepalive` comment lines.
- **`EventSource` cannot set headers.** No `Authorization: Bearer` — auth must go via cookie or
  query parameter. Related: the CORS config pairs `allow_origins=["*"]` with
  `allow_credentials=True`, which browsers reject outright as an invalid combination, so
  cookie-based SSE would fail today.

**Decision: polling first.** Not as a compromise, as the correct first move:

1. The run row in Postgres is the source of truth either way. Polling reads it directly; SSE needs
   that *plus* an in-memory fan-out path *plus* the DB again for reconnect replay. Strictly more
   machinery.
2. SSE needs a polling fallback anyway, for reconnects and hostile proxies. Building the fallback
   first means you are never blocked.
3. ~90 requests against one primary-key lookup is nothing at this scale.

And this is not a permanent decision. The job model decouples submit from delivery — `POST /run`
returns a `run_id` either way — so adding SSE later is a new endpoint plus a frontend swap, with no
change to the submit contract, the table, or the manager.

Note that polling can narrate progress too, with a cursor: persist progress events and poll
`GET /runs/{id}/events?since=12`, trading ~2s of latency for none of the connection plumbing.

---

## 5. Implementation steps

### Step 0 — Settle the frontend contract (blocking)

Decide polling versus SSE (see above) and agree the migration path.

**Recommended:** add the new endpoints alongside the existing one, and reimplement the current
`POST .../run` as a thin wrapper that submits a job and awaits its completion. Nothing breaks on day
one, the frontend migrates when ready, then the wrapper is deleted. Do not do a flag-day switch.

This is a contract change and it is the real cost of the migration — the backend half is the easy
half. Agree it before writing code.

### Step 1 — Runs table and repository

New files: `data_agent/storage/database.py` (an `asyncpg.create_pool` wrapper) and
`data_agent/storage/run_repository.py`. The DSN mirrors the ADK one in `runners/root_agent.py`:
`postgresql://postgres@{host}:{port}/{name}`.

```sql
CREATE TABLE IF NOT EXISTS agent_run (
    run_id             UUID PRIMARY KEY,
    app_name           TEXT NOT NULL,
    user_id            TEXT NOT NULL,
    session_id         TEXT NOT NULL,
    status             TEXT NOT NULL,   -- queued|running|succeeded|failed|cancelled|interrupted
    query              TEXT NOT NULL,
    new_session        BOOLEAN NOT NULL DEFAULT FALSE,
    image_data_uri     TEXT,
    image_filename     TEXT,
    image_content_type TEXT,
    response           TEXT,
    response_timestamp TIMESTAMPTZ,
    error              TEXT,
    client_request_id  TEXT,
    instance_id        TEXT NOT NULL,
    cancel_requested   BOOLEAN NOT NULL DEFAULT FALSE,
    created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
    started_at         TIMESTAMPTZ,
    heartbeat_at       TIMESTAMPTZ,
    finished_at        TIMESTAMPTZ
);

-- one active run per session, enforced by the database
CREATE UNIQUE INDEX IF NOT EXISTS agent_run_one_active_per_session
    ON agent_run (app_name, user_id, session_id)
    WHERE status IN ('queued', 'running');

-- idempotency for double-submits
CREATE UNIQUE INDEX IF NOT EXISTS agent_run_client_request_id
    ON agent_run (user_id, client_request_id)
    WHERE client_request_id IS NOT NULL;

CREATE INDEX IF NOT EXISTS agent_run_session_idx
    ON agent_run (user_id, session_id, created_at DESC);
```

**The partial unique index is the core of the whole design.** "One active run per session" becomes a
database invariant rather than application bookkeeping — the insert fails with a unique violation,
which maps to `409`. That is correct across processes and replicas for free, so the in-process busy
set and Postgres advisory locks both become unnecessary. Its one weakness is a hard-killed process
leaving a stuck `running` row, which Step 6 handles.

Run the DDL on startup with `CREATE ... IF NOT EXISTS`. That is what ADK already does for its own
tables, so it matches the project's existing posture — no migration tool needed.

### Step 2 — Schemas

New `data_agent/schemas/run.py`:

- `RunStatus` — a `str` enum: `queued`, `running`, `succeeded`, `failed`, `cancelled`, `interrupted`
- `SubmitRunResponse` — `{run_id, status}`
- `RunStatusResponse` — `{run_id, status, response, timestamp, error, created_at, started_at, finished_at}`

Add `client_request_id: str | None = None` to the existing `RunAgentRequest`. Export the new names
from `data_agent/schemas/__init__.py`. Keep `RunAgentResponse` — the compatibility wrapper still
returns it.

### Step 3 — Split `RootAgentRunner.run`

Today `run()` mixes three concerns: artifact upload, agent execution, and title creation. Split it:

- `execute(user_id, session_id, prompt, on_event=None) -> (response, timestamp)` — pure agent
  execution over an already-assembled prompt string, invoking `on_event` for each yielded event.
- Artifact upload **moves out to the HTTP handler** — see the gotcha in Step 5.
- Title creation moves into the job body, not a `finally` on the request.

### Step 4 — Job manager

New `data_agent/runners/run_manager.py`, holding the repository, the `RootAgentRunner`, a
`dict[UUID, asyncio.Task]`, and a global `asyncio.Semaphore` capping total in-flight runs.

- `submit(...)` — insert a `queued` row, `asyncio.create_task(self._execute(run_id))`, return
  `run_id`. On a unique violation of the active-run index raise `SessionBusyError`; on a violation
  of `client_request_id` return the **existing** run — that is the double-click case and it must
  *not* be a `409`.
- `_execute(run_id)` — mark `running`, call `execute(..., on_event=heartbeat)`, write the terminal
  status in `finally`.
- `cancel(run_id)` — set `cancel_requested`, then `task.cancel()`.
- `shutdown()` — cancel all tasks and mark them `interrupted`.

Three details that matter:

- **Heartbeat on each yielded event, not on a timer.** A timer proves the *process* is alive; a
  per-event heartbeat proves the *run* is progressing, so a wedged MCP call stops beating. Throttle
  the write to roughly every 5s so you are not hammering Postgres per token.
- **Hold a reference to every task.** A bare `create_task` result that nothing references can be
  garbage-collected mid-flight.
- **Wrap the run in `asyncio.timeout(...)`** for a hard maximum duration.

### Step 5 — Endpoints

In `data_agent/routers/runner.py`:

| Method | Path | Returns |
|---|---|---|
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `202 {run_id, status}` |
| `GET` | `/apps/runs/{run_id}` | full run record |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/active-run` | active run, or `204` |
| `POST` | `/apps/runs/{run_id}/cancel` | `202` |
| `GET` | `/apps/runs/{run_id}/events` *(later)* | SSE stream |

Keep the existing convention: text fields are **query parameters** (`Annotated[RunAgentRequest,
Depends()]`), and the body is reserved for the optional `image_file` multipart upload. So
`client_request_id` is a query parameter too.

> **The gotcha that will bite you.** The `UploadFile` stream is closed when the request returns, so
> it cannot be handed to a background task. `_upload_artifact` must run **inside the endpoint,
> before returning 202**, with only the resulting `data_uri` stored on the run row. That is also why
> prompt assembly stays in the handler.

Replace the blanket `except Exception` → `500` with typed exceptions, so `SessionBusyError` → `409`
and unknown-run → `404` are distinguishable from genuine failures.

### Step 6 — Reconciliation and reaping

- **On startup:** mark rows belonging to this `instance_id` that are still `queued` or `running` as
  `interrupted`. With a single replica you can safely sweep *all* such rows; scope by `instance_id`
  the moment you run two.
- **Background reaper**, every ~30s: mark `running` rows whose `heartbeat_at` is older than a TTL as
  `interrupted`. Set the TTL above your longest legitimate single tool call, or you will kill
  healthy runs.

Together these are what release the partial unique index after a crash, so a dead run cannot wedge a
session permanently.

### Step 7 — Wire into the lifespan

In `data_agent/__main__.py`: create the pool → run the DDL → build the manager → startup sweep →
start the reaper task. On exit, `manager.shutdown()` then close the pool, before the existing
`object_storage.close()`.

Add any new tunables (pool size, heartbeat TTL, max run duration, concurrency caps) to `_ENV_MAP` in
`common/config.py` so they stay env-overridable like everything else.

### Step 8 — Migrate and clean up

The frontend switches to submit-and-poll, then the compatibility wrapper is deleted. Add a retention
job for old run rows.

---

## 6. Failure modes and which detector catches each

| What happened | Does `finally` run? | Caught by |
|---|---|---|
| Finished normally | yes | `status=succeeded` |
| Exception (LLM, MCP, ADK stale-write) | yes | `status=failed` plus error text |
| Client disconnects mid-run | usually — `CancelledError` propagates *(uvicorn-version dependent; verify)* | `status=cancelled` |
| Explicit cancel request | yes | `status=cancelled` |
| SIGKILL, OOM, container restart | **no** | startup sweep by `instance_id`, or heartbeat TTL |
| Hung MCP call, run never returns | **no** | per-event heartbeat going stale, plus the max-duration cap |

The last row is the subtle one: a naive heartbeat task keeps beating while the run is wedged,
because it proves the process is alive rather than that the run is progressing. Hence per-event
heartbeats.

---

## 7. Build order

Steps 1–2 → 3–4 → 5 with the compatibility wrapper → 6 → verify against concurrent submits → 8.

Steps 1, 5 and 6 are load-bearing; the rest is plumbing.

**Verification worth doing explicitly:** fire two concurrent `POST .../run` calls at the same
session and confirm one returns `202` and the other `409`; then kill the container mid-run and
confirm the session becomes submittable again after the TTL.

---

## 8. Frontend contract summary

What to bring to the Step 0 conversation:

> Submit returns a `run_id` immediately. Poll `GET /runs/{run_id}` every ~2s until `status` leaves
> `queued`/`running`. We may add a streaming endpoint later without changing submit.

Concrete changes for the client:

- `POST .../run` now returns **`202`** with `{run_id, status}` — **not** the agent's answer.
- Poll `GET /apps/runs/{run_id}`; terminal statuses are `succeeded`, `failed`, `cancelled`,
  `interrupted`. Render `response` on success and `error` otherwise.
- **`409` means a run is already active** for that session — show "still processing", do not retry
  blindly.
- Send `client_request_id` (a UUID generated per user action) so a double-click or a network retry
  returns the *same* run instead of a `409`.
- On page load, call `GET .../active-run` to reattach to a run that is still going. This is the
  answer to "how do I know a run is in flight before I submit" — and it is also what makes a page
  reload stop losing answers.
- Keep the send button disabled while a run is active. That is UX; the `409` is the guarantee.

> **Behaviour change to flag explicitly.** `docs/new-session-flag.md` currently promises that the
> session title is persisted *before* the `run` response returns, so refetching the session list
> immediately after `run` resolves is safe. That stops being true: `POST .../run` now returns before
> the agent has even started, and title creation happens inside the job. Refetch the session list
> after the run reaches a terminal status instead, and that doc needs updating alongside this
> migration.

---

## 9. Ride-along fixes

Cheap, and best done with the same change:

- Typed exceptions instead of blanket `500`s throughout `routers/runner.py`.
- Prefix artifact filenames with the `run_id` in `_upload_artifact` to kill the version race.
- Sort events by timestamp explicitly in `get_session`.
- A per-user concurrency cap, so distinct sessions cannot fan out unbounded LLM and MCP calls.

Separately, and unrelated to this migration: `config.yaml` contains live JWTs and object-storage
keys, and it is in git history. Those should move to secrets or environment variables and be
rotated.

---

## 10. Follow-ups, once this lands

- **Cancel-and-replace** (policy C) becomes safe once runs are jobs — decide whether a cancelled
  run's partial events stay in the transcript or are purged.
- **SSE** for live progress narration ("querying MongoDB…", "searching Milvus…"), with the polling
  path retained as the reconnect fallback.
- **Multi-worker or multi-replica deployment.** The partial unique index already makes this safe;
  what needs attention is scoping the startup sweep by `instance_id` and confirming the reaper TTL.
