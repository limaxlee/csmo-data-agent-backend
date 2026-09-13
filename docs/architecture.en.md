# [Data Service] Data Agent — Architecture

**Repository:** `limaxlee/csmo-data-agent-backend`
**Baseline:** `develop1` at `50c3f11` (module restructure, 2026-09-13)
**Related documents:** [roadmap.md](roadmap.md), [migration.md](migration.md), [authentication.md](authentication.md)
**Korean version:** [architecture.kr.md](architecture.kr.md)

---

## 1. Purpose

- Advance data refinement through the construction of a Data Feature Hub
- Provide data analysis capabilities through natural language: training data selection, similar data search
- Expose the whole capability as a chat-style service (session management, artifact upload/download, conversation history)

---

## 2. System Architecture

### 2.1 Overall structure

```
                          ┌──────────────────────────┐
                          │        Frontend          │
                          │      (Chat UI)           │
                          └────────────┬─────────────┘
                                       │ HTTP / REST
                                       ▼
   ┌───────────────────────────────────────────────────────────────────────┐
   │                    Data Agent Backend (FastAPI)                       │
   │                                                                       │
   │  Routers:  /health    /logs    /apps/users/{user_id}/sessions/...     │
   │                                       │                               │
   │  AgentRunner ─────────────────────────┤                               │
   │      │                                │                               │
   │      │  ┌─────────────────────────────┴────────────────────────────┐  │
   │      │  │  Root Orchestrator (FabriX ADK Agent)                    │  │
   │      │  │    tools: AgentTool(milvus_scanner)                      │  │
   │      │  │           AgentTool(mongodb_scanner)                     │  │
   │      │  │           get_current_time                               │  │
   │      │  └───────┬──────────────────────────────┬───────────────────┘  │
   │      │          │                              │                      │
   │      │  ┌───────▼─────────┐          ┌─────────▼────────┐             │
   │      │  │ mongodb_scanner │          │  milvus_scanner  │             │
   │      │  └───────┬─────────┘          └─────────┬────────┘             │
   │      │          │ MCP (Streamable HTTP)        │ MCP                  │
   │      │          │                              │                      │
   │  TitleGenerator (title generation)                                    │
   └──────┼──────────┼──────────────────────────────┼──────────────────────┘
          │          │                              │
          ▼          ▼                              ▼
   ┌────────────┐  ┌──────────────────┐   ┌──────────────────┐
   │ PostgreSQL │  │ MongoDB MCP      │   │ Milvus MCP       │
   │ (sessions, │  │ Server           │   │ Server           │
   │  events,   │  └────────┬─────────┘   └────────┬─────────┘
   │  state,    │           ▼                      ▼
   │  run locks)│  ┌──────────────────┐   ┌──────────────────┐
   └────────────┘  │ MongoDB          │   │ Milvus Vector DB │
   ┌────────────┐  │ (model metadata, │   │ (feature vectors)│
   │  Object    │  │  inspection      │   └──────────────────┘
   │  Storage   │  │  summaries)      │
   │  (S3 API)  │  └──────────────────┘
   └────────────┘
```

### 2.2 Component responsibilities

| Component | Responsibility | Technology |
|---|---|---|
| Data Agent Backend | REST API, session lifecycle, agent execution, artifact handling | FastAPI + Uvicorn, Python 3.13 |
| Root Orchestrator | Interprets user intent, routes to specialists, formats the final answer | FabriX ADK `Agent` |
| mongodb_scanner | Deployed model metadata, daily inspection result summaries | FabriX ADK `Agent` + MCPToolset |
| milvus_scanner | Similarity search, collection query, coreset sampling | FabriX ADK `Agent` + MCPToolset |
| system_agent | Conversation title generation | FabriX ADK `Agent` (no tools) |
| MongoDB MCP Server | Exposes MongoDB tools to `mongodb_scanner` | External service, Streamable HTTP |
| Milvus MCP Server | Exposes Milvus tools to `milvus_scanner` | External service, Streamable HTTP |
| PostgreSQL | Agent session, event and state persistence; per-session run locks (`session_run_locks`) | ADK `DatabaseSessionService`, SQLAlchemy async engine + asyncpg |
| Object Storage | Image artifacts uploaded by the user, sampled data ZIP files | S3-compatible, aiobotocore |

### 2.3 Module layout

```
data_agent/
├── __main__.py            entry point: initialises the logger, runs Uvicorn
├── app.py                 create_app() + lifespan: wires every dependency into app.state
├── agents/                ADK agents (root_agent, system_agent, scanners)
│   ├── models.py          build_model(reasoning_effort) -> LiteLlm for the root/scanner agents
│   ├── instructions/      prompt text per agent + get_instruction_with_current_time()
│   └── plugins/           TimingLoggerPlugin (run / agent / LLM / tool timing and token usage)
├── infra/                 clients for external systems, no business logic
│   ├── postgres_client.py PostgresClient (SQLAlchemy async engine) + postgres_dsn()
│   ├── session_lock.py    SessionLockRepository (session_run_locks table)
│   ├── object_storage.py  ObjectStorage (aiobotocore S3 client)
│   └── artifact_store.py  ObjectStorageArtifactService (ADK BaseArtifactService)
├── services/              application logic used by the routers
│   ├── agent_runner.py    AgentRunner: sessions, artifacts, run lock, agent execution
│   ├── title_generator.py TitleGenerator: system_agent on an in-memory scratch session
│   └── health.py          HealthChecker: PostgreSQL / object-storage probes
├── routers/               FastAPI routers: health, logs, runner (/apps)
├── schemas/               pydantic request / response models
├── middleware/            CORS + request/response logging
└── utils/                 logger (rotating file + /logs ZIP), datetime helpers
common/
├── config.py              Settings (config.yaml + environment overrides)
├── constants.py           AppNames, AgentNames, EventAuthors, RunState, ArtifactPrefix, ...
└── exceptions.py          SessionBusyError
```

- Dependency direction is `routers → services → infra`. `agents/` is imported only by `app.py` and `services/`; nothing in `infra/` knows about agents or routers.
- `tests/` mirrors this layout (`tests/infra`, `tests/services`, `tests/agents/plugins`, ...). The test folders have no `__init__.py`, so every test file basename is unique across the tree.

---

## 3. Agent Structure

- The Central Data Agent interprets the user's natural-language request and orchestrates the entire workflow.
- A modular multi-agent structure is used so that responsibilities are cleanly separated by role.
  · **Root Orchestrator**: manages specialist agents, task delegation and overall workflow
  · **Specialist Agents**: each agent owns a single domain
    (1) `mongodb_scanner` (MongoDB Agent): deployed model information (name / version / task / deployment date and other metadata) and daily inspection summaries
    (2) `milvus_scanner` (Milvus Agent): feature-vector related operations such as similarity search
  · **MCP Servers**: grant agents DB access and provide various tools
    (1) MongoDB MCP Server: provides MongoDB tools to `mongodb_scanner`
    (2) Milvus MCP Server: provides Milvus Vector DB tools to `milvus_scanner`

### 3.1 Root Orchestrator

- Name: `root_orchestrator` · Source: [agents/root_agent.py](../data_agent/agents/root_agent.py)
- The orchestrator never accesses data itself. It only (a) routes, (b) resolves model identity, (c) formats the final answer.
- Specialist agents are attached as `AgentTool`, so delegation happens as a normal tool call.
- Additional local tool: `get_current_time(timezone="Asia/Seoul")`

**Routing table**

| The user asks about | Delegate to |
|---|---|
| Which models are deployed, model versions, tasks, sites, processes, dates | `mongodb_scanner` |
| Inspection status/results: data counts per class, NG rate, confidence, inference time, performance trends | `mongodb_scanner` |
| Collected data contents: data volume, label distribution, similar images, record retrieval, coreset sampling | `milvus_scanner` |

**Model Identity Contract** (mandatory before any `milvus_scanner` delegation)

- `milvus_scanner` organises data per model and requires the exact stored identity: `modelName`, `modelVersion`, `process` (and `site` when known).
  · (1) Extract model hints from the user request
  · (2) Call `mongodb_scanner` to resolve them to one exact stored record
  · (3) Pass `modelName`, `modelVersion`, `process` to `milvus_scanner` verbatim
  · (4) If several candidates are returned, present them and ask the user to choose
  · (5) Never guess the model, and never infer it from an image filename

**Workflows**

| ID | Workflow | Route | Constraint |
|---|---|---|---|
| W1 | Inspection status | `mongodb_scanner` | Time window ≤ 2 weeks |
| W2 | Performance trend / comparison | `mongodb_scanner` ×N, orchestrator computes the verdict | Time window ≤ 2 weeks per query |
| W3 | Model inventory | `mongodb_scanner` | — |
| W4 | Collected data status | resolve identity → `milvus_scanner` | — |
| W5 | Similarity search | resolve identity → `milvus_scanner` | Image is attached automatically |
| W6 | Coreset sampling | resolve identity → `milvus_scanner` | Per-label sizes confirmed first |

**Response rules**

- Never mention databases, scanners, tools, collections or field names — speak only in terms of models, sites, processes and data
- Present every list as a table; no emojis
- Render links returned by a scanner unchanged, as `[View Data](<url>)`
- Summarise scanner output rather than dumping raw results

### 3.2 mongodb_scanner

- Name: `mongodb_scanner` · Source: [agents/mongodb_scanner.py](../data_agent/agents/mongodb_scanner.py)
- Answers exactly two question types:
  · **A.** Which inspection models exist / are deployed (metadata: name, version, task, site, process, mode, date)
  · **B.** Daily inspection result summaries (per-class data counts, confidence statistics, inference-time statistics)
- Never handles image data, similarity search, sampling or vector operations

| Question type | MCP tool |
|---|---|
| A — which / what models | `mcp_mongodb_find_inspection_models` |
| B — inspection numbers, confidence, elapsed time | `mcp_mongodb_find_inspection_summary_documents` |

**Fixed vocabulary**

| Field | Allowed values |
|---|---|
| `mode` | `test` / `production` / `rework` |
| `task` | `cls` (classification) / `det` (detection) / `seg` (segmentation) |
| `gbm` (site, uppercase) | `SEV`, `SEVT` (smartphone plants, Vietnam) / `SEHC` (home-appliance plant, Vietnam) / `SEHA` (home-appliance plant) |
| Summary-only fields | `location`, `equipment_id`, `product_id` |

- Date format: `%Y-%m-%d %H:%M:%S`. Relative periods are resolved to explicit start/end dates by the agent.
- Identifier matching is case-insensitive and partial — several matches are listed for user selection, never guessed.
- Result limit: at most 15 records per response.

### 3.3 milvus_scanner

- Name: `milvus_scanner` · Source: [agents/milvus_scanner.py](../data_agent/agents/milvus_scanner.py)
- Operates only on collected image data: dataset contents, similarity search, record retrieval by filter, coreset sampling

**Collection naming**

```
process_modelName_modelVersion
example:  modelName=EpoxyClassifier, modelVersion=v1.1, process=SMD  ->  SMD_EpoxyClassifier_v1.1
```

**Record schema (10 fields)**

| # | Field | Description |
|---|---|---|
| 1 | `pk` | Primary key |
| 2 | `filename` | Filename of the data |
| 3 | `data_uri` | Unique S3 object key of the data |
| 4 | `feature_vector` | Feature vector; length is constant within a collection, may differ across collections |
| 5 | `prediction` | The model's predicted label |
| 6 | `confidence` | Confidence of the prediction |
| 7 | `elapsed_time` | Total inspection duration |
| 8 | `gbm` | Manufacturing site where the data was collected |
| 9 | `process` | Process line where the data was collected |
| 10 | `location` | Location of the process line within the site |

**Operations**

| Operation | MCP tool | Limit |
|---|---|---|
| Similarity search | `mcp_milvus_extract_embeddings_and_vector_search` | default 5, hard max 10 |
| Collection metadata | `mcp_milvus_get_collection_info` | — |
| Collection query (filter expression) | Milvus query tool | default 5, hard max 10 |
| Coreset sampling | `mcp_milvus_get_k_center_sampled_data_as_zip_file` | per-label sizes defined by the user |

- Coreset sampling: the user defines each label and its sample size (e.g. 100 Good + 200 NG → up to 300 items). Optional "keep" labels are included in full and not sampled. Labels in neither set are excluded entirely.
- Responses include `data_uri`, `filename` and `prediction` per item, and never expose collection names, field names, the primary key or feature-vector details.

### 3.4 system_agent

- Name: `system_agent` · Source: [agents/system_agent.py](../data_agent/agents/system_agent.py)
- Single purpose: generate a short conversation title (2–8 words) from the first user message
- Runs through `TitleGenerator` ([services/title_generator.py](../data_agent/services/title_generator.py)) on its own ADK `Runner` with `InMemorySessionService` — a scratch session is created per call and always deleted afterwards, even when generation fails
- Uses its own `LiteLlm` built from the `system_model_openapi` config block, independent of the agents' model
- `AgentRunner` writes the result to session state under the key `session_title`
- The title is written in the same language as the user's first message

---

## 4. LLM Models

- Agent framework: **FabriX ADK**
  · Wraps most Google ADK functionality while additionally providing access to the in-house Gauss models
  · Note: beta / first release, currently somewhat unstable
  · Constraint: only some of the provided Gauss models support tool calling — notably, several higher-performance models do not

**Model comparison**

| Model | Assessment | Tool calling |
|---|---|---|
| Gauss | Average performance that can degrade on complex queries | Supported |
| Gauss Think | Similar to Gauss but less stable performance | Supported |
| GaussO Flash | Average performance but sometimes gets messy | Supported |
| GaussO Think (Beta) | Solid performance but a little bit unstable | Unstable — worked initially, currently not working |
| GaussO | Solid performance | Not supported |
| GaussO Think | Solid performance | Not supported |

Relative performance: `GaussO Flash < Gauss Think < Gauss`

**Integration**

- All agents use `LiteLlm` pointed at an OpenAI-compatible LLM gateway. The root orchestrator and the scanners get their model from `build_model()` in [agents/models.py](../data_agent/agents/models.py), which reads the `root_model_openapi` block and passes the reasoning effort through `extra_body`:

```python
def build_model(reasoning_effort: ModelReasoningEffort) -> LiteLlm:
    return LiteLlm(
        model=SETTINGS.root_model_openapi.model,
        api_base=SETTINGS.root_model_openapi.endpoint,
        api_key="not-used",
        extra_headers={
            "x-openapi-token":        SETTINGS.root_model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.root_model_openapi.client_key,
            "x-llm-model-id":         str(SETTINGS.root_model_openapi.model_id),
        },
        extra_body={"reasoning_effort": reasoning_effort},
    )
```

| Agent | Config block | Reasoning effort |
|---|---|---|
| `root_orchestrator` | `root_model_openapi` | `medium` |
| `mongodb_scanner`, `milvus_scanner` | `root_model_openapi` | `low` |
| `system_agent` | `system_model_openapi` — its own `LiteLlm` in [agents/system_agent.py](../data_agent/agents/system_agent.py), no reasoning effort | — |

- The two config blocks are independent, so title generation can run on a different gateway and model than the agents.
- `get_instruction_with_current_time()` in [agents/instructions/\_\_init\_\_.py](../data_agent/agents/instructions/__init__.py) wraps an instruction string into an ADK instruction provider that prepends `CURRENT LOCAL TIME: ...` on every call, so an agent resolves relative dates without a tool round trip.

---

## 5. MCP Servers

- Both MCP servers are external services. The backend connects to them over **Streamable HTTP** using ADK's `MCPToolset` with `StreamableHTTPConnectionParams`.
- Endpoint pattern: `http://{host}:{port}/mcp`

| MCP Server | Consumer agent | Config keys | Purpose |
|---|---|---|---|
| MongoDB MCP Server | `mongodb_scanner` | `mongodb_mcp.host`, `mongodb_mcp.port` | Query deployed model metadata and inspection summaries |
| Milvus MCP Server | `milvus_scanner` | `milvus_mcp.host`, `milvus_mcp.port` | Feature-vector operations: similarity search, collection info, coreset sampling |

### 5.1 MongoDB MCP Server

- AI model metadata deployed to the subsidiaries lives in the Data Service MongoDB, so the agent needs DB access → the MCP server makes actual deployed-model information retrievable
- Implementation status: core toolset complete, deployed
- Source code: separate GitHub repository

### 5.2 Milvus MCP Server

- Feature vectors extracted by AI models live in the Milvus Vector DB, so the agent needs DB access → the MCP server makes feature-vector operations possible
- Two principal operations: **data similarity search**, **data sampling**
- Implementation status: similarity search and the remaining toolset complete; data sampling in progress; deployed
- Data sampling will support classification and detection tasks only
  · Detection data is trickier to sample than classification data
  · Sampling details will be documented on the GitHub Wiki page
- Source code: separate GitHub repository

---

## 6. Data Stores

### 6.1 PostgreSQL — agent session and state

- **Agent session and state management: Database Session Service vs In-Memory Session Service**
  · The In-Memory Session Service is more straightforward to configure than the DB Session Service, but the DB Session Service is more stable in a production environment → **Database Session Service selected**
  · PostgreSQL is used, deployed

| Item | Value |
|---|---|
| Implementation | ADK `DatabaseSessionService` |
| Connection string | `postgresql+asyncpg://{user}@{host}:{port}/{name}`, built by `postgres_dsn()` in [infra/postgres_client.py](../data_agent/infra/postgres_client.py) |
| Driver | `asyncpg` through a SQLAlchemy async engine |
| Config keys | `postgresql_db.host`, `.port`, `.name`, `.user` |
| Stored | Sessions, conversation events, session state (including `session_title`), session run locks |
| App name key | `data_agent` (`AppNames.ROOT`) |
| Session ID | `uuid.uuid4().hex`, generated by the backend |

- The session title is not a separate column. It is applied as a state delta:

```python
await session_service.append_event(session, Event(
    author=EventAuthors.SYSTEM,
    actions=EventActions(state_delta={SessionStateFields.TITLE: session_title})
))
```

- A failed run is recorded in the same history: `AgentRunner` appends a `system` event with `error_code="LLM_ERROR"` and the exception text, so the session shows why a turn produced no answer.
- `system_agent` deliberately uses `InMemorySessionService` instead — its sessions are transient and deleted right after use.

**Session run locks** — [infra/session_lock.py](../data_agent/infra/session_lock.py)

- `PostgresClient` owns the one SQLAlchemy async engine of the process (`pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`) and exposes `execute` / `fetch_one` / `fetch_all`. ADK's `DatabaseSessionService` builds its own engine from the same DSN.
- `SessionLockRepository` keeps one row per session:

```sql
CREATE TABLE IF NOT EXISTS session_run_locks (
    app_name   TEXT NOT NULL,
    user_id    TEXT NOT NULL,
    session_id TEXT NOT NULL,
    run_state  TEXT NOT NULL DEFAULT 'idle',      -- 'idle' | 'running'
    updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    PRIMARY KEY (app_name, user_id, session_id)
)
```

| Operation | Behaviour |
|---|---|
| `try_acquire` | One atomic `INSERT ... ON CONFLICT DO UPDATE ... WHERE run_state = 'idle' RETURNING`; no row back means the session is already running |
| `release` | Sets `idle`; never raises, so a failed release cannot mask the run's own outcome |
| `get_run_state` / `get_run_states` | State of one session or of a batch — used by `GET .../run-state`, session detail and session listing |
| `delete` | Removes the row when the session is deleted |
| `initialize` | Creates the table at startup and, when `reset_session_locks` is true, marks every `running` row `idle` |

- There is no lease. A crashed process leaves its locks `running` until the next startup reset, which is only safe while a single backend process uses the database (see §13).

### 6.2 Object Storage — artifacts

| Item | Value |
|---|---|
| Protocol | S3-compatible (`signature_version=s3v4`) |
| Client | `ObjectStorage` ([infra/object_storage.py](../data_agent/infra/object_storage.py)) — `aiobotocore`, opened at application startup and closed at shutdown |
| Config keys | `object_storage.bucket`, `.endpoint`, `.access_key`, `.secret_key` |
| ADK integration | `ObjectStorageArtifactService(BaseArtifactService)` — [infra/artifact_store.py](../data_agent/infra/artifact_store.py) |
| Fallback content type | `application/octet-stream` (`CONTENT_TYPE`) whenever neither the upload nor `head_object` provides one |

**Object key layout**

```
{app_name}/{user_id}/{session_id}/{filename}/{version}
example:  data_agent/donghy.kim/9f2c.../defect_001.jpg/0
```

- Versioning is automatic: `list_versions()` reads the existing integer suffixes and the new version becomes `max + 1`. `parse_version()` is the inverse and resolves the version from a `data_uri` on download.
- `ObjectStorage` provides: `list_paginated_objects`, `upload_object`, `retrieve_object`, `retrieve_object_info`, `delete_objects`. Each method logs and returns `None` / `False` on failure instead of raising.
- `delete_session_artifacts()` removes every object under the session prefix and raises on failure. `AgentRunner.delete_session` calls it before deleting the session row and the lock row, so a failed delete never orphans objects.
- Content type is preserved on upload and read back from `head_object` on download.

### 6.3 MongoDB (via MCP)

- Not accessed directly by the backend — reached only through the MongoDB MCP Server
- Holds deployed AI model metadata and daily inspection result summary documents

### 6.4 Milvus Vector DB (via MCP)

- Not accessed directly by the backend — reached only through the Milvus MCP Server
- Holds one collection per model, containing the feature vectors and inspection results described in §3.3

---

## 7. API Endpoints

Base path for agent operations: `/apps`

### 7.1 Endpoint list

| Method | Path | Request | Response | Description |
|---|---|---|---|---|
| `GET` | `/health` | — | `CheckHealthStatusResponse` | Server, PostgreSQL and object storage health |
| `GET` | `/logs` | — | `application/zip` | Download server logs as a ZIP archive |
| `GET` | `/apps/users/{user_id}/sessions` | — | `ListSessionsResponse` | List all sessions of a user |
| `POST` | `/apps/users/{user_id}/sessions` | — | `CreateSessionResponse` | Create a new session |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}` | — | `SessionInfo` | Session detail including full event history |
| `DELETE` | `/apps/users/{user_id}/sessions/{session_id}` | — | `200 OK` | Delete a session |
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/title` | — | `CreateSessionTitleResponse` | Generate a title from the last user message |
| `PATCH` | `/apps/users/{user_id}/sessions/{session_id}/title` | `RenameSessionRequest` | `200 OK` | Rename the session title manually |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/artifact` | `LoadSessionArtifactRequest` | binary + `media_type` | Download an artifact by its object key |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/run-state` | — | `GetRunStateResponse` | Whether a run is in progress (`idle` / `running`), without loading events |
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `RunAgentRequest` + optional `image_file` | `RunAgentResponse` | Execute the agent on a user prompt |

### 7.2 Data models

Source: [schemas/runner.py](../data_agent/schemas/runner.py), [schemas/health.py](../data_agent/schemas/health.py)

| Model | Fields |
|---|---|
| `SessionInfo` | `session_id: str`, `app_name: str`, `user_id: str`, `state: dict`, `events: list`, `last_update_time: datetime`, `run_state: RunState = idle` |
| `ListSessionsResponse` | `sessions: list[SessionInfo]` |
| `CreateSessionResponse` | `session_id: str` |
| `RenameSessionRequest` | `session_title: str` |
| `CreateSessionTitleResponse` | `session_title: str` |
| `LoadSessionArtifactRequest` | `filename: str`, `data_uri: str`, `media_type: str = application/octet-stream` |
| `LoadSessionArtifactResponse` | `content: bytes`, `media_type: str` |
| `RunAgentRequest` | `query: str`, `new_session: bool = False` |
| `RunAgentResponse` | `response: str`, `timestamp: datetime` |
| `GetRunStateResponse` | `session_id: str`, `run_state: RunState` |
| `CheckHealthStatusResponse` | `server_status: str`, `postgresql_db_status: str`, `object_storage_status: str` |

**Notes**

- `RunAgentRequest` and `LoadSessionArtifactRequest` are bound with `Depends()`, so they arrive as **form / query parameters**, not as a JSON body. `POST /run` is therefore a `multipart/form-data` request when an image is attached.
- `POST /run` with `new_session=true` triggers title generation automatically after the response is produced, while the run lock is still held.
- Session listing and session detail carry `run_state`, read from the run-lock table, so the frontend can show a "still responding" state after a reload. `GET .../run-state` returns the same value without loading the events.
- Timestamps returned by ADK are Unix values and are converted with `convert_unix_to_datetime`.

### 7.3 Error handling

| Condition | Status |
|---|---|
| A run is already in progress for the session (`SessionBusyError` — raised by `/run`, title generation and rename) | `409 Conflict` |
| Session not found / invalid argument (`ValueError`) | `400 Bad Request` |
| Any other exception | `500 Internal Server Error` |
| No log files present (`/logs`) | `404 Not Found` (currently surfaces as `500` because the 404 is raised inside the catch-all handler) |

- `SessionBusyError` ([common/exceptions.py](../common/exceptions.py)) is the first typed exception. All other routers still wrap handlers in a broad `except Exception` and return the exception text as `detail`; replacing that is roadmap issue #8.

---

## 8. Request Flow

### 8.1 `POST /apps/users/{user_id}/sessions/{session_id}/run`

```
 1. Frontend            POST /run  (query, new_session, image_file?)
                              │
 2. runner.py                 ├─ resolve AgentRunner from app.state
                              │
 3. AgentRunner.run           ├─ SessionLockRepository.try_acquire()  ──►  PostgreSQL
                              │     └─ already running  ─►  SessionBusyError  ─►  409 Conflict
                              │
                              ├─ if image_file:
                              │     ├─ ObjectStorageArtifactService.save_artifact()
                              │     │     └─ ObjectStorage.upload_object()  ──►  Object Storage
                              │     └─ append a text Part:
                              │           "Uploaded Artifact:
                              │            filename: ...
                              │            data_uri: ...
                              │            content_type: ..."
                              │
                              ├─ append the user prompt as a text Part
                              │
 4. ADK Runner.run_async      ├─ load session from PostgreSQL
                              │     └─ TimingLoggerPlugin logs [TIMING] START/END for run, agent, llm, tool
                              │
 5. Root Orchestrator         ├─ interpret intent, select route
                              │     ├─ AgentTool(mongodb_scanner) ─► MCP ─► MongoDB
                              │     └─ AgentTool(milvus_scanner)  ─► MCP ─► Milvus
                              │
                              ├─ compose the final natural-language answer
                              │
 6. ADK                       ├─ persist events + state to PostgreSQL
                              │
 7. AgentRunner               ├─ take the first final event: response text + timestamp
                              │     └─ on failure: append a system event (error_code=LLM_ERROR), re-raise
                              │
 8. finally                   ├─ if new_session: _create_session_title()
                              │     └─ TitleGenerator ─► system_agent ─► state_delta {session_title}
                              └─ SessionLockRepository.release()
                              │
 9. Response                  RunAgentResponse { response, timestamp }
```

### 8.2 Artifact download

- The agent's answer embeds the object key (`data_uri`) of any produced artifact — for example the ZIP file created by coreset sampling.
- The frontend calls `GET /apps/users/{user_id}/sessions/{session_id}/artifact?filename=...&data_uri=...` (`media_type` is an optional fallback).
- The backend parses the version from the last segment of `data_uri`, loads that version of `filename` from the session prefix, reads the content type via `head_object` (falling back to `media_type`), and returns the raw bytes.

### 8.3 Health check

- `GET /health` delegates to `HealthChecker` ([services/health.py](../data_agent/services/health.py)), which reuses the process-wide `PostgresClient` and `ObjectStorage` clients and bounds each probe with `HEALTH_CHECK_TIMEOUT` (5 seconds):
  · PostgreSQL — `SELECT 1` through the connection pool
  · Object storage — `head_bucket` against the configured bucket
- Each returns `healthy` / `unhealthy` independently; the endpoint itself returns `200` as long as the checks complete.

---

## 9. Configuration

- Source: [common/config.py](../common/config.py) · Default file: `config.yaml`
- Loaded at startup, overridable by CLI (`--config` / `-c`) and by environment variables through `_ENV_MAP`

| Block | Keys | Purpose |
|---|---|---|
| — | `server_port` | HTTP listen port |
| — | `reset_session_locks` (default `true`) | Reset every `running` session lock to `idle` at startup; must be `false` when more than one backend process shares the database |
| `root_model_openapi` | `model`, `endpoint`, `client_key`, `pass_key`, `model_id` | LLM gateway for `root_orchestrator` and the scanners |
| `system_model_openapi` | `model`, `endpoint`, `client_key`, `pass_key`, `model_id` | LLM gateway for `system_agent` (title generation) |
| `mongodb_mcp` | `host`, `port` | MongoDB MCP Server endpoint |
| `milvus_mcp` | `host`, `port` | Milvus MCP Server endpoint |
| `postgresql_db` | `host`, `port`, `name`, `user` | Agent session database and run-lock table |
| `object_storage` | `bucket`, `endpoint`, `access_key`, `secret_key` | Artifact storage |

- Every key has a corresponding environment variable in `_ENV_MAP` (for example `POSTGRESQL_DB_HOST`, `OBJECT_STORAGE_BUCKET`, `RESET_SESSION_LOCKS`, `ROOT_MODEL_OPENAPI_MODEL`), so a container can be configured without mounting a file. Booleans accept `1/0`, `true/false`, `yes/no`, `on/off`. Note that the model-id variables are named `ROOT_MODEL_OPENAPI_ROOT_MODEL_ID` and `SYSTEM_MODEL_OPENAPI_ROOT_MODEL_ID`.
- MCP and database endpoints differ per environment; the values in `config.yaml` describe the environment that file is deployed to.

> **Security note.** `config.yaml` is currently tracked in git and contains live credentials. Rotating those credentials and untracking the file are P0 and issue #1 in [roadmap.md](roadmap.md).

---

## 10. Deployment

| Item | Value |
|---|---|
| Base image | `python:3.13.13` (internal registry) |
| Working directory | `/home/work/cosmo-da-backend` |
| Dependencies | `requirements_py313_prod.txt` |
| Entry point | `python -m data_agent -c /home/work/cosmo-da-backend/config.yaml` |
| Listen address | `0.0.0.0:{server_port}` |
| Server | Uvicorn, single worker |

**Application lifecycle** — [app.py](../data_agent/app.py) (`lifespan`), started from [\_\_main\_\_.py](../data_agent/__main__.py)

- `__main__` initialises the logger and runs `data_agent.app:app` with Uvicorn on `0.0.0.0:{server_port}`.
- Startup (`lifespan`):
  · `ObjectStorage.connect()` — opens the S3 client
  · `PostgresClient()` — the one SQLAlchemy engine of the process
  · `SessionLockRepository.initialize()` — creates `session_run_locks` and resets stale locks when `reset_session_locks` is true
  · Builds `HealthChecker(db_client, object_storage)` and `AgentRunner(agent=root_agent, session_service=DatabaseSessionService(postgres_dsn()), artifact_service=ObjectStorageArtifactService(...), title_generator=TitleGenerator(), lock_repository=...)`
  · Stores `object_storage`, `health_checker` and `agent_runner` on `app.state`; routers resolve them through `request.app.state`
- Shutdown:
  · `PostgresClient.close()` — disposes the engine
  · `ObjectStorage.close()`
  · `shutdown_logs_executor()`

**Middleware** — [middleware/](../data_agent/middleware/)

- `CORSMiddleware` (currently `*`, roadmap #7) and an HTTP middleware that logs every request (`method path?query`) and response (status, elapsed ms).

**Logging**

- Initialised by `initialize_logger("cosmo_data_agent.log")`, written under `logs/` (rotating, 10 MB × 20 files) and downloadable through `GET /logs`
- `/run` emits `[TIMING]` log lines at start, end, busy rejection and failure, carrying the session ID and elapsed seconds
- `TimingLoggerPlugin` ([agents/plugins/timing.py](../data_agent/agents/plugins/timing.py)) is attached to both ADK runners and logs START/END lines with elapsed time and token usage for every run, agent turn, LLM call and tool call, all tagged with the invocation id (`inv=...`). Details in [timing-logging.md](timing-logging.md).

---

## 11. Feature Vector Extraction

- The quality of the data feature vector directly affects data sampling and similarity search performance.
- Review of models for extracting feature vectors:
  · Extracting directly with a trained inspection model is difficult, so the use of pretrained models (DINOv2/v3 and similar) was reviewed
  · Review result: pretrained models capture only general characteristics, and performance was insufficient
  · Examples compared: similarity search results based on feature vectors from a trained inspection model vs. DINOv3-7b; feature maps from both
  · Conclusion: to obtain good performance and meaningful results during data sampling and similarity search, it is better to use the feature vector extracted by the trained model
- **Constraint.** Extracting feature vectors at the edge and transmitting them together with the data to the Suwon server is currently difficult, so a vector extraction pipeline is required on the Suwon server.

---

## 12. Use Case Mapping

| ID | Use case | Route | Primary component |
|---|---|---|---|
| UC1-1 | Inspection status query | W1 | `mongodb_scanner` → MongoDB MCP |
| UC1-2 | Model performance analysis and trend assessment | W2 | `mongodb_scanner` + orchestrator computation |
| UC1-3 | Deployed model information query | W3 | `mongodb_scanner` → MongoDB MCP |
| UC1-4 | Dataset status query | W4 | `milvus_scanner` → `mcp_milvus_get_collection_info` |
| UC1-5 | Data similarity search | W5 | `milvus_scanner` → `mcp_milvus_extract_embeddings_and_vector_search` |
| UC1-6 | Data selection (coreset sampling) | W6 | `milvus_scanner` → `mcp_milvus_get_k_center_sampled_data_as_zip_file` |
| UC1-7 | Labeling validation | W4 + filter query | `milvus_scanner` (confidence / cluster outliers) |
| UC1-8 | Drift detection (on-demand) | W2 + W4 | `mongodb_scanner` + `milvus_scanner` |

**Common constraints**

| Constraint | Value |
|---|---|
| Inspection query time window | Maximum 2 weeks per query |
| Similarity search results | Default 5, hard maximum 10 |
| MongoDB records per response | Maximum 15 |
| Coreset sampling task support | Classification and detection only |

---

## 13. Current Constraints and Planned Work

### 13.1 Known constraints

| Area | Constraint |
|---|---|
| Agent framework | FabriX ADK is a beta / first release and is currently somewhat unstable |
| LLM | Only some Gauss models support tool calling; several higher-performance models do not |
| Feature vectors | No edge-side extraction pipeline; a Suwon-server pipeline is required |
| Data sampling | Detection sampling is trickier than classification; implementation in progress |
| Execution model | `POST /run` is synchronous and can take minutes; a long request blocks the client |
| Concurrency | Concurrent runs on the same session are rejected with `409` through the Postgres run lock; the lock has no lease, so a crashed run holds it until the next startup reset |
| Deployment | Single Uvicorn worker; `reset_session_locks` must be `false` before more than one process shares the database |

### 13.2 Planned work

Detailed issue and PR ordering is in [roadmap.md](roadmap.md); the target asynchronous execution model is described in [migration.md](migration.md).

| Theme | Summary | Reference |
|---|---|---|
| Credential hygiene | Rotate leaked credentials, untrack `config.yaml` | roadmap P0, #1 |
| CORS | Replace the `*` origin with a configured frontend origin list | roadmap #7 |
| Typed exceptions | Replace broad `except Exception` handling | roadmap #8 |
| Asynchronous run model | `POST /run` returns `202` with a run record; polling and cancellation | roadmap #14–#28, migration.md |
| SSE progress stream | `GET /runs/{run_id}/events` narrates tool calls as they happen | roadmap #32 |
| Multi-worker support | Instance-scoped bookkeeping so `--workers` is safe | roadmap #34 |
| **Authentication (SSO)** | Company ADFS via OIDC, session cookie, per-user authorization | [authentication.md](authentication.md) |

> **Authentication status.** The service currently has no authentication — `user_id` is an unauthenticated path parameter, so any caller can access any user's sessions. The full design, including the ADFS integration and the issue breakdown, is in [authentication.md](authentication.md).
