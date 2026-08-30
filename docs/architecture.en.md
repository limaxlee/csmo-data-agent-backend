# [Data Service] Data Agent — Architecture

**Repository:** `limaxlee/csmo-data-agent-backend`
**Baseline:** `main` at `9a3d572`
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
   │  RootAgentRunner ─────────────────────┤                               │
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
   │  SystemAgentRunner (title generation)                                 │
   └──────┼──────────┼──────────────────────────────┼──────────────────────┘
          │          │                              │
          ▼          ▼                              ▼
   ┌────────────┐  ┌──────────────────┐   ┌──────────────────┐
   │ PostgreSQL │  │ MongoDB MCP      │   │ Milvus MCP       │
   │ (sessions, │  │ Server           │   │ Server           │
   │  events,   │  └────────┬─────────┘   └────────┬─────────┘
   │  state)    │           ▼                      ▼
   └────────────┘  ┌──────────────────┐   ┌──────────────────┐
                   │ MongoDB          │   │ Milvus Vector DB │
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
| PostgreSQL | Agent session, event and state persistence | ADK `DatabaseSessionService`, asyncpg |
| Object Storage | Image artifacts uploaded by the user, sampled data ZIP files | S3-compatible, aiobotocore |

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
- Runs on a separate `SystemAgentRunner` with `InMemorySessionService` — the temporary session is deleted immediately after the title is produced
- Writes the result to session state under the key `session_title`
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

- All agents use `LiteLlm` pointed at the internal OpenAPI LLM gateway:

```python
LiteLlm(
    model="openai//mnt/models",
    api_base=SETTINGS.model_openapi.endpoint + "/openapi/llm",
    api_key="not-used",
    extra_headers={
        "x-openapi-token":         SETTINGS.model_openapi.pass_key,
        "x-generative-ai-client":  SETTINGS.model_openapi.client_key,
        "x-llm-model-id":          str(SETTINGS.model_openapi.root_model_id),
    },
)
```

| Agent | Model ID setting |
|---|---|
| `root_orchestrator`, `mongodb_scanner`, `milvus_scanner` | `model_openapi.root_model_id` |
| `system_agent` | `model_openapi.system_model_id` |

- [agents/llm.py](../data_agent/agents/llm.py) contains a factored `build_model(reasoning_effort)` helper and a `with_current_time()` instruction wrapper (prepends current local time to every call, removing the need for a tool round trip). These are prepared but not yet wired into the active agents.

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
| Connection string | `postgresql+asyncpg://postgres@{host}:{port}/{name}` |
| Driver | `asyncpg` |
| Config keys | `postgresql_db.host`, `.port`, `.name`, `.user` |
| Stored | Sessions, conversation events, session state (including `session_title`) |
| App name key | `data_agent` (`ROOT_APP_NAME`) |
| Session ID | `uuid.uuid4().hex`, generated by the backend |

- The session title is not a separate column. It is applied as a state delta:

```python
await session_service.append_event(session, Event(
    author=SYSTEM_AUTHOR,
    actions=EventActions(state_delta={SESSION_TITLE_KEY: session_title})
))
```

- `system_agent` deliberately uses `InMemorySessionService` instead — its sessions are transient and deleted right after use.

### 6.2 Object Storage — artifacts

| Item | Value |
|---|---|
| Protocol | S3-compatible (`signature_version=s3v4`) |
| Client | `aiobotocore`, opened at application startup and closed at shutdown |
| Config keys | `object_storage.bucket`, `.endpoint`, `.access_key`, `.secret_key` |
| ADK integration | `OSArtifactService(BaseArtifactService)` — [storage/os_artifact.py](../data_agent/storage/os_artifact.py) |
| Presigned URL expiry | 7200 seconds (`PRESIGNED_URL_EXPIRED_IN`) |

**Object key layout**

```
{app_name}/{user_id}/{session_id}/{filename}/{version}
example:  data_agent/donghy.kim/9f2c.../defect_001.jpg/0
```

- Versioning is automatic: `list_versions()` reads the existing integer suffixes and the new version becomes `max + 1`.
- `ObjectStorage` provides: `list_paginated_objects`, `upload_object`, `retrieve_object`, `retrieve_object_info`, `get_presigned_url`, `delete_objects`.
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
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `RunAgentRequest` + optional `image_file` | `RunAgentResponse` | Execute the agent on a user prompt |

### 7.2 Data models

Source: [schemas/runner.py](../data_agent/schemas/runner.py), [schemas/health.py](../data_agent/schemas/health.py)

| Model | Fields |
|---|---|
| `SessionInfo` | `session_id: str`, `app_name: str`, `user_id: str`, `state: dict`, `events: list`, `last_update_time: datetime` |
| `ListSessionsResponse` | `sessions: list[SessionInfo]` |
| `CreateSessionResponse` | `session_id: str` |
| `RenameSessionRequest` | `session_title: str` |
| `CreateSessionTitleResponse` | `session_title: str` |
| `LoadSessionArtifactRequest` | `data_uri: str` |
| `LoadSessionArtifactResponse` | `content: bytes`, `media_type: str` |
| `RunAgentRequest` | `query: str`, `new_session: bool = False` |
| `RunAgentResponse` | `response: str`, `timestamp: datetime` |
| `CheckHealthStatusResponse` | `server_status: str`, `postgresql_db_status: str`, `object_storage_status: str` |

**Notes**

- `RunAgentRequest` and `LoadSessionArtifactRequest` are bound with `Depends()`, so they arrive as **form / query parameters**, not as a JSON body. `POST /run` is therefore a `multipart/form-data` request when an image is attached.
- `POST /run` with `new_session=true` triggers title generation automatically after the response is produced.
- Timestamps returned by ADK are Unix values and are converted with `convert_unix_to_datetime`.

### 7.3 Error handling

| Condition | Status |
|---|---|
| Session not found / invalid argument (`ValueError`) | `400 Bad Request` |
| Any other exception | `500 Internal Server Error` |
| No log files present (`/logs`) | `404 Not Found` |

- All routers currently wrap handlers in a broad `except Exception` and return the exception text as `detail`. Replacing this with typed exceptions is roadmap issue #8.

---

## 8. Request Flow

### 8.1 `POST /apps/users/{user_id}/sessions/{session_id}/run`

```
 1. Frontend            POST /run  (query, new_session, image_file?)
                              │
 2. runner.py                 ├─ resolve RootAgentRunner from app.state
                              │
 3. RootAgentRunner.run       ├─ if image_file:
                              │     ├─ OSArtifactService.save_artifact()
                              │     │     └─ ObjectStorage.upload_object()  ──►  Object Storage
                              │     └─ append a text Part:
                              │           "Uploaded Artifact:
                              │            Filename: ...
                              │            Data uri: ...
                              │            Content type: ..."
                              │
                              ├─ append the user prompt as a text Part
                              │
 4. ADK Runner.run_async      ├─ load session from PostgreSQL
                              │
 5. Root Orchestrator         ├─ interpret intent, select route
                              │     ├─ AgentTool(mongodb_scanner) ─► MCP ─► MongoDB
                              │     └─ AgentTool(milvus_scanner)  ─► MCP ─► Milvus
                              │
                              ├─ compose the final natural-language answer
                              │
 6. ADK                       ├─ persist events + state to PostgreSQL
                              │
 7. RootAgentRunner           ├─ extract the final response text and timestamp
                              │
 8. finally                   └─ if new_session: create_session_title()
                                     └─ SystemAgentRunner ─► system_agent ─► state_delta
                              │
 9. Response                  RunAgentResponse { response, timestamp }
```

### 8.2 Artifact download

- The agent's answer embeds the object key (`data_uri`) of any produced artifact — for example the ZIP file created by coreset sampling.
- The frontend calls `GET /apps/users/{user_id}/sessions/{session_id}/artifact?data_uri=...`.
- The backend reads the content type via `head_object`, fetches the object, and returns the raw bytes with the correct `media_type`.

### 8.3 Health check

- `GET /health` performs two live probes with a 5-second timeout each:
  · PostgreSQL — opens a connection and runs `SELECT 1`
  · Object storage — issues `head_bucket` against the configured bucket
- Each returns `healthy` / `unhealthy` independently; the endpoint itself returns `200` as long as the checks complete.

---

## 9. Configuration

- Source: [common/config.py](../common/config.py) · Default file: `config.yaml`
- Loaded at startup, overridable by CLI (`--config` / `-c`) and by environment variables through `_ENV_MAP`

| Block | Keys | Purpose |
|---|---|---|
| — | `server_port` | HTTP listen port |
| `model_openapi` | `endpoint`, `client_key`, `pass_key`, `root_model_id`, `system_model_id` | Gauss / FabriX LLM gateway |
| `mongodb_mcp` | `host`, `port` | MongoDB MCP Server endpoint |
| `milvus_mcp` | `host`, `port` | Milvus MCP Server endpoint |
| `postgresql_db` | `host`, `port`, `name`, `user` | Agent session database |
| `object_storage` | `bucket`, `endpoint`, `access_key`, `secret_key` | Artifact storage |

- Every key has a corresponding environment variable in `_ENV_MAP` (for example `POSTGRESQL_DB_HOST`, `OBJECT_STORAGE_BUCKET`, `MODEL_OPENAPI_ROOT_MODEL_ID`), so a container can be configured without mounting a file.
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

**Application lifecycle** — [\_\_main\_\_.py](../data_agent/__main__.py)

- Startup (`lifespan`):
  · `ObjectStorage.connect()` — opens the S3 client
  · Constructs `RootAgentRunner(artifact_service=OSArtifactService(...), system_runner=SystemAgentRunner())`
  · Stores both on `app.state` for dependency injection
- Shutdown:
  · `ObjectStorage.close()`
  · `shutdown_logs_executor()`

**Logging**

- Initialised by `initialize_logger("cosmo_data_agent.log")`, written under `logs/` and downloadable through `GET /logs`
- `/run` emits `[TIMING]` log lines at start, end and failure, carrying the session ID and elapsed seconds

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
| Presigned URL validity | 7200 seconds (2 hours) |
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
| Concurrency | A single ADK session is not safe against concurrent runs |
| Deployment | Single Uvicorn worker |

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
