# Migration: turning `/run` into an asynchronous job

**Audience:** backend developers, with a frontend contract section
**Status:** implemented — the backend half is done; the frontend is being built against §8
**Endpoint affected:** `POST /apps/users/{user_id}/sessions/{session_id}/run`

## TL;DR

Today two `/run` calls for the same session can execute at the same time, and they corrupt each
other's session state. The fix is to stop treating a run as an HTTP request and start treating it
as a **job**: `POST .../run` returns `202 {run_id}` immediately, the work happens in a background
task, and the client watches `GET /apps/runs/{run_id}/events` (SSE) for progress and the answer.
`GET /apps/runs/{run_id}` returns the same record as a plain request, for reconnects and for any
client that cannot hold a stream open.

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

### Now — stop the corruption *(skipped: the job model landed instead)*

This was the stopgap to land first if the job migration would take more than a day. It was not
needed — Step 1 went in directly, and the partial unique index makes the in-process busy set
redundant. Kept here for the reasoning, not as work to do.

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
- **`EventSource` cannot set headers.** No `Authorization: Bearer` — auth would have to go via
  cookie or query parameter. **Use `fetch` with a `ReadableStream` on the client instead**: same
  wire format, but headers work and the problem disappears. `EventSource` also cannot POST, which
  is a second reason submit stays its own request.
- **The CORS config was invalid.** It paired `allow_origins=["*"]` with `allow_credentials=True`,
  which browsers reject outright. Now fixed: origins come from `cors_origins` (env `CORS_ORIGINS`,
  comma-separated) and credentials are only enabled once real origins are configured.

**Decision: SSE, with the run record as the fallback.**

An earlier draft of this document chose polling first, on the grounds that SSE is strictly more
machinery and that the polling path has to exist anyway. Two things changed that:

1. **The agent is moving to token streaming.** Polling cannot serve that — you would be persisting
   partial tokens to Postgres and rendering them in 2-second chunks. This is a requirement polling
   does not meet at any interval, not a latency preference.
2. **The frontend had not been written yet**, so there was no migration to stage. Shipping a
   polling loop for the client to delete a month later was pure waste.

What did *not* change is that the run row in Postgres stays the source of truth. SSE is a delivery
layer over it, not a replacement: `GET /apps/runs/{run_id}` returns the same record and is what a
reconnect, a hostile proxy, or a page reload falls back to. Nothing about the submit contract, the
table, or the manager depends on which one the client uses.

**What is deliberately *not* built:** streaming straight out of the open `POST /run` request with a
`StreamingResponse` over `run_async`. It is tempting — no runs table, no job — but the client
disconnect cancels the generator, so a page reload throws away an answer that has already been paid
for, and the one-active-run invariant has nowhere to live. Submit and delivery stay separate.

---

## 5. Implementation steps

### Step 0 — Settle the frontend contract (done)

Settled: SSE, per the decision above. §8 is the contract.

The compatibility wrapper this step originally recommended — reimplementing `POST .../run` as a
thin wrapper that submits a job and awaits it — was **skipped**, because the frontend had not
shipped yet. There was no live client to keep working, so `POST .../run` changed shape directly.
Reinstate the wrapper only if a client turns out to be depending on the old `200 {response}`.

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

#### Step 4b — The stream broker

`data_agent/runners/run_stream.py` holds one `RunStream` per active run: a sequence counter, a ring
buffer of recent events for replay, and a set of subscriber queues. `on_event` publishes into it;
the SSE endpoint subscribes to it.

- **Nothing is persisted.** Writing token deltas to Postgres would be absurd, and it is not needed:
  the final answer is on the run row, and a process restart that loses the buffer also interrupts
  the run.
- **Replay is bounded and in-memory.** A client reconnecting with `Last-Event-ID` gets everything
  after that sequence number that is still in the ring buffer.
- **A slow subscriber is dropped, never waited on.** `publish` is synchronous and non-blocking; if a
  subscriber's queue is full it gets a sentinel and its connection ends, and it reconnects with
  `Last-Event-ID`. Agent execution must never block on a browser.
- **Finished streams linger** for `stream_retention` seconds so a client reconnecting just after the
  run ends still gets the tail. After that the reaper prunes them, and the endpoint falls back to
  emitting the run record as a single `done` event.

The event vocabulary is `RunEventType` in `data_agent/schemas/run.py`; §8 documents it.

The title of a new session is created **before** the `done` event is published, so a client that
refetches the session list on `done` still sees it — see the note at the end of §8.

### Step 5 — Endpoints

In `data_agent/routers/runner.py`:

| Method | Path | Returns |
|---|---|---|
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `202 {run_id, status}` |
| `GET` | `/apps/runs/{run_id}/events` | SSE stream — the primary delivery path |
| `GET` | `/apps/runs/{run_id}` | full run record — the fallback |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/active-run` | active run, or `204` |
| `POST` | `/apps/runs/{run_id}/cancel` | `202` |

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

Steps 1–2 → 3–4 → 5 → 6 → 7, with no compatibility wrapper (see Step 0).

**Verification still worth doing explicitly, against a real Postgres and the real model** — none of
it is covered by the unit tests:

1. Fire two concurrent `POST .../run` calls at the same session; confirm one returns `202` and the
   other `409 SESSION_BUSY`.
2. Kill the container mid-run; confirm the session becomes submittable again after the startup
   sweep, and after `heartbeat_ttl` if the process stays down.
3. Open the SSE stream and confirm `delta` events actually arrive mid-run — that is the ADK
   streaming assumption in §10, and it is the one thing that cannot be checked without the model.
4. Drop the connection mid-run and reconnect with `Last-Event-ID`; confirm the replay lands and the
   run is unaffected.
5. Submit twice with the same `client_request_id`; confirm the second returns the *same* `run_id`
   and not a `409`.
6. Run it behind whatever proxy fronts it in production and confirm chunks are not buffered.

---

## 8. Frontend contract

> Submit returns a `run_id` immediately. Open `GET /apps/runs/{run_id}/events` and render what
> arrives. `GET /apps/runs/{run_id}` returns the same record if the stream is unavailable.

### Submit

`POST /apps/users/{user_id}/sessions/{session_id}/run` returns **`202 {run_id, status}`** — **not**
the agent's answer. Text fields stay query parameters (`query`, `new_session`, `client_request_id`);
the body is still reserved for the optional `image_file` upload.

- **`409` means a run is already active** for that session. The body is
  `{"detail": {"code": "SESSION_BUSY", "message": ..., "run_id": ...}}` with a `Retry-After` header.
  Show "still processing" and attach to `run_id` — do not retry blindly.
- Send `client_request_id` (a UUID per user action) so a double-click or a network retry returns the
  *same* run instead of a `409`.

### Stream

`GET /apps/runs/{run_id}/events` is `text/event-stream`. **Use `fetch` + `ReadableStream`, not
`EventSource`** — `EventSource` cannot set an `Authorization` header. Resume a dropped connection
with the `Last-Event-ID` header, or with `?since=<seq>` if your reader does not send it.

| `event:` | `data:` | What to do |
|---|---|---|
| `status` | `{status, run_id?}` | the run moved to `queued` / `running` |
| `delta` | `{text}` | **append** to the open draft message |
| `message` | `{author, text}` | a complete message — it **replaces** the open draft and closes it |
| `tool` | `{name, phase}` | progress narration, e.g. "querying mongodb"; `phase` is `call`/`response` |
| `title` | `{session_title}` | a new session was titled; refresh the session list |
| `done` | the full run record | terminal — the stream ends right after this |

Lines beginning `:` are keepalive comments; ignore them. Terminal statuses are `succeeded`,
`failed`, `cancelled`, `interrupted` — render `response` on success and `error` otherwise. The
`done` event carries the whole record, so no follow-up `GET` is needed in the happy path.

### Fallback and reattach

- `GET /apps/runs/{run_id}` returns the run record at any time. Use it if the stream errors, or as a
  plain poll behind a proxy that mangles streaming.
- On page load, call `GET .../active-run` — `200` with the run to reattach to, `204` if nothing is
  in flight. This is the answer to "how do I know a run is in flight before I submit", and it is
  what makes a page reload stop losing answers.
- `POST /apps/runs/{run_id}/cancel` stops a run.
- Keep the send button disabled while a run is active. That is UX; the `409` is the guarantee.

> **On `docs/new-session-flag.md`.** It promises the session title is persisted before the `run`
> response returns, so refetching the session list immediately afterwards is safe. `POST .../run`
> now returns before the agent has started, so that no longer holds for *submit* — but the job
> creates the title before publishing `done`, so the promise survives if you move the refetch to
> the `title` or `done` event. That doc should be updated to say so.

---

## 9. Ride-along fixes

Cheap, and best done with the same change:

- ~~Typed exceptions instead of blanket `500`s~~ — done for the run endpoints
  (`SessionBusyError` → `409`, `RunNotFoundError` → `404`, `RunNotCancellableError` → `409`). The
  session endpoints still use blanket `except Exception`.
- ~~Prefix artifact filenames with the `run_id`~~ — done; `upload_artifact` takes a `prefix`.
- Sort events by timestamp explicitly in `get_session`. **Still open.**
- A per-user concurrency cap. **Partially done:** `max_concurrent_runs` is a global semaphore, not
  per-user. One user with many sessions can still hold every slot.

Separately, and unrelated to this migration: `config.yaml` contains live JWTs and object-storage
keys, and it is in git history. Those should move to secrets or environment variables and be
rotated.

---

## 10. Follow-ups, once this lands

- **Verify ADK streaming end to end.** `RootAgentRunner.execute` passes
  `RunConfig(streaming_mode=StreamingMode.SSE)`, which is what makes ADK yield `partial` events.
  Confirm against google-adk 2.4 in a real environment that (a) the LiteLLM path to the internal
  model actually emits partials, and (b) the final event still carries the aggregated text —
  `execute` falls back to the accumulated deltas if it does not. `AGENT_RUNS_STREAMING=false`
  turns streaming off without touching the transport if either turns out to be false.
- **Reconnect resumes from the last complete event, not mid-token.** Partial events are not
  persisted by ADK's session service, and the ring buffer is in-memory, so a reconnect after a
  process restart resumes from the run record rather than the token stream. Worth confirming the UX
  handles a half-rendered draft being replaced.
- **Cancel-and-replace** (policy C) becomes safe now that runs are jobs — decide whether a cancelled
  run's partial events stay in the transcript or are purged.
- **Multi-worker or multi-replica deployment.** The partial unique index already makes this safe;
  what needs attention is scoping the startup sweep by `instance_id`, confirming the reaper TTL,
  and the fact that the stream broker is **per-process** — a client would have to reach the replica
  running its job, so this needs sticky routing on `run_id` or a shared fan-out (Redis pub/sub)
  before a second replica.
- **Retention.** `RunRepository.delete_older_than` exists but nothing calls it yet.
