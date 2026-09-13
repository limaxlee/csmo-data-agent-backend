# [데이터 서비스] 데이터 에이전트 — 아키텍처

**Repository:** `limaxlee/csmo-data-agent-backend`
**기준 커밋:** `develop1` / `50c3f11` (모듈 구조 재편, 2026-09-13)
**관련 문서:** [roadmap.md](roadmap.md), [migration.md](migration.md), [authentication.md](authentication.md)
**English version:** [architecture.en.md](architecture.en.md)

---

## 1. 목적

- 데이터 Feature Hub 구축을 통한 데이터 정제 고도화
- 자연어 기반으로 데이터 분석 기능 제공: 학습 데이터 선별, 유사 데이터 탐색
- 위 기능을 chat 형태의 서비스로 제공 (세션 관리, artifact 업로드/다운로드, 대화 이력 관리)

---

## 2. 전체 아키텍처

### 2.1 구조도

```
                          ┌──────────────────────────┐
                          │        Frontend          │
                          │        (Chat UI)         │
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
   │  TitleGenerator (대화 제목 생성)                                       │
   └──────┼──────────┼──────────────────────────────┼──────────────────────┘
          │          │                              │
          ▼          ▼                              ▼
   ┌────────────┐  ┌──────────────────┐   ┌──────────────────┐
   │ PostgreSQL │  │ MongoDB MCP      │   │ Milvus MCP       │
   │ (세션,     │  │ Server           │   │ Server           │
   │  이벤트,   │  └────────┬─────────┘   └────────┬─────────┘
   │  state,    │           ▼                      ▼
   │  run lock) │  ┌──────────────────┐   ┌──────────────────┐
   └────────────┘  │ MongoDB          │   │ Milvus Vector DB │
   ┌────────────┐  │ (모델 metadata,  │   │ (feature vector) │
   │  Object    │  │  검사 결과 요약) │   └──────────────────┘
   │  Storage   │  └──────────────────┘
   │  (S3 API)  │
   └────────────┘
```

### 2.2 컴포넌트별 역할

| 컴포넌트 | 역할 | 기술 |
|---|---|---|
| Data Agent Backend | REST API, 세션 lifecycle, agent 실행, artifact 처리 | FastAPI + Uvicorn, Python 3.13 |
| Root Orchestrator | 사용자 의도 해석, specialist agent로 routing, 최종 답변 생성 | FabriX ADK `Agent` |
| mongodb_scanner | 배포 모델 metadata, 일별 검사 결과 요약 조회 | FabriX ADK `Agent` + MCPToolset |
| milvus_scanner | 유사도 검색, collection query, coreset sampling | FabriX ADK `Agent` + MCPToolset |
| system_agent | 대화 제목 생성 | FabriX ADK `Agent` (tool 없음) |
| MongoDB MCP Server | `mongodb_scanner`에 MongoDB tool 제공 | 외부 서비스, Streamable HTTP |
| Milvus MCP Server | `milvus_scanner`에 Milvus tool 제공 | 외부 서비스, Streamable HTTP |
| PostgreSQL | Agent 세션 / 이벤트 / state 영속화, 세션별 run lock (`session_run_locks`) | ADK `DatabaseSessionService`, SQLAlchemy async engine + asyncpg |
| Object Storage | 사용자가 업로드한 이미지 artifact, sampling 결과 ZIP 파일 | S3 호환, aiobotocore |

### 2.3 모듈 구조

```
data_agent/
├── __main__.py            진입점: logger 초기화 후 Uvicorn 실행
├── app.py                 create_app() + lifespan: 모든 의존성을 생성해 app.state에 연결
├── agents/                ADK agent (root_agent, system_agent, scanner)
│   ├── models.py          build_model(reasoning_effort) -> root/scanner agent용 LiteLlm
│   ├── instructions/      agent별 prompt 텍스트 + get_instruction_with_current_time()
│   └── plugins/           TimingLoggerPlugin (run / agent / LLM / tool 소요 시간 및 token 사용량)
├── infra/                 외부 시스템 클라이언트, 비즈니스 로직 없음
│   ├── postgres_client.py PostgresClient (SQLAlchemy async engine) + postgres_dsn()
│   ├── session_lock.py    SessionLockRepository (session_run_locks 테이블)
│   ├── object_storage.py  ObjectStorage (aiobotocore S3 클라이언트)
│   └── artifact_store.py  ObjectStorageArtifactService (ADK BaseArtifactService)
├── services/              router가 사용하는 애플리케이션 로직
│   ├── agent_runner.py    AgentRunner: 세션, artifact, run lock, agent 실행
│   ├── title_generator.py TitleGenerator: in-memory 임시 세션에서 system_agent 실행
│   └── health.py          HealthChecker: PostgreSQL / object storage probe
├── routers/               FastAPI router: health, logs, runner (/apps)
├── schemas/               pydantic request / response 모델
├── middleware/            CORS + 요청/응답 로깅
└── utils/                 logger (rotating file + /logs ZIP), datetime helper
common/
├── config.py              Settings (config.yaml + 환경 변수 override)
├── constants.py           AppNames, AgentNames, EventAuthors, RunState, ArtifactPrefix 등
└── exceptions.py          SessionBusyError
```

- 의존 방향은 `routers → services → infra`이다. `agents/`는 `app.py`와 `services/`에서만 import하며, `infra/`는 agent나 router를 알지 못한다.
- `tests/`는 이 구조를 그대로 따른다 (`tests/infra`, `tests/services`, `tests/agents/plugins` 등). 테스트 폴더에 `__init__.py`가 없으므로 테스트 파일명은 전체 트리에서 유일해야 한다.

---

## 3. Agent 구조

- Central Data Agent가 User의 자연어 요청을 해석하고 전체 workflow를 orchestration하는 역할을 한다.
- 역할별 책임을 명확히 분리하기 위해 modular multi-agent 구조 사용
  · **Root Orchestrator**: specialist agent 관리, task delegation 및 전체 workflow 관리 담당
  · **Specialist Agents**: 각 agent가 단일 도메인 담당
    (1) `mongodb_scanner` (MongoDB Agent): 법인에 배포된 모델 정보 조회 (모델 이름/버전/task/배포 날짜 등 metadata 정보) 및 일별 검사 결과 요약 조회
    (2) `milvus_scanner` (Milvus Agent): 유사도 검색 등 feature vector에 관련된 operation 수행
  · **MCP Servers**: agent에 DB 접근 권한 및 다양한 Tool 제공
    (1) MongoDB MCP Server: `mongodb_scanner`에 MongoDB tool들 제공
    (2) Milvus MCP Server: `milvus_scanner`에 Milvus Vector DB tool들 제공

### 3.1 Root Orchestrator

- 이름: `root_orchestrator` · 소스: [agents/root_agent.py](../data_agent/agents/root_agent.py)
- Orchestrator는 데이터에 직접 접근하지 않는다. (a) routing, (b) 모델 identity 확정, (c) 최종 답변 formatting만 담당한다.
- Specialist agent는 `AgentTool`로 연결되어 있어 delegation이 일반 tool call로 수행된다.
- 추가 local tool: `get_current_time(timezone="Asia/Seoul")`

**Routing table**

| 사용자 질문 유형 | Delegate 대상 |
|---|---|
| 어떤 모델이 배포되었는지, 모델 버전/task/법인/공정/날짜 | `mongodb_scanner` |
| 검사 현황/결과: class별 데이터 수, NG rate, confidence, inference time, 성능 추이 | `mongodb_scanner` |
| 수집 데이터 내용: 데이터 수, 라벨 분포, 유사 이미지, 특정 데이터 조회, coreset sampling | `milvus_scanner` |

**Model Identity Contract** (모든 `milvus_scanner` delegation 이전 필수)

- `milvus_scanner`는 모델 단위로 데이터를 관리하므로 저장된 정확한 identity가 필요하다: `modelName`, `modelVersion`, `process` (알 수 있는 경우 `site` 포함)
  · (1) 사용자 요청에서 모델 관련 hint 추출
  · (2) `mongodb_scanner`를 호출하여 정확히 하나의 저장 레코드로 확정
  · (3) `modelName`, `modelVersion`, `process`를 변형 없이 그대로 `milvus_scanner`에 전달
  · (4) 후보가 여러 개인 경우 목록을 제시하고 사용자에게 선택 요청
  · (5) 모델을 추측하지 않으며, 이미지 파일명으로부터 유추하지 않는다

**Workflow**

| ID | Workflow | 경로 | 제약 |
|---|---|---|---|
| W1 | 검사 현황 조회 | `mongodb_scanner` | time window 최대 2주 |
| W2 | 성능 추이 / 비교 | `mongodb_scanner` ×N, 판정은 orchestrator가 계산 | 쿼리당 time window 최대 2주 |
| W3 | 배포 모델 목록 | `mongodb_scanner` | — |
| W4 | 수집 데이터 현황 | identity 확정 → `milvus_scanner` | — |
| W5 | 유사도 검색 | identity 확정 → `milvus_scanner` | 이미지는 자동 첨부됨 |
| W6 | Coreset sampling | identity 확정 → `milvus_scanner` | 라벨별 sample 수 사전 확인 |

**응답 규칙**

- DB, scanner, tool, collection, field 이름 등 내부 동작을 절대 언급하지 않는다 — 모델/법인/공정/데이터 관점으로만 서술
- 모든 목록은 테이블로 제시하며, 이모지는 사용하지 않는다
- Scanner가 반환한 링크는 변경하지 않고 `[View Data](<url>)` 형태로 렌더링
- Scanner 결과를 그대로 나열하지 않고 질문에 맞춰 요약

### 3.2 mongodb_scanner

- 이름: `mongodb_scanner` · 소스: [agents/mongodb_scanner.py](../data_agent/agents/mongodb_scanner.py)
- 정확히 두 가지 질문 유형만 담당한다:
  · **A.** 어떤 검사 모델이 존재/배포되어 있는가 (metadata: 이름, 버전, task, 법인, 공정, mode, 날짜)
  · **B.** 해당 모델들이 생성한 일별 검사 결과 요약 (class별 데이터 수, confidence 통계, inference time 통계)
- 이미지 데이터, 유사도 검색, sampling, vector operation은 담당하지 않는다

| 질문 유형 | MCP tool |
|---|---|
| A — 어떤 모델인지 | `mcp_mongodb_find_inspection_models` |
| B — 검사 수치, confidence, elapsed time | `mcp_mongodb_find_inspection_summary_documents` |

**고정 vocabulary**

| 필드 | 허용 값 |
|---|---|
| `mode` | `test` / `production` / `rework` |
| `task` | `cls` (classification) / `det` (detection) / `seg` (segmentation) |
| `gbm` (법인, 대문자) | `SEV`, `SEVT` (스마트폰 법인, 베트남) / `SEHC` (가전 법인, 베트남) / `SEHA` (가전 법인) |
| 요약 전용 필드 | `location`, `equipment_id`, `product_id` |

- 날짜 형식: `%Y-%m-%d %H:%M:%S`. "지난주", "최근 7일" 등 상대 기간은 agent가 명시적인 start/end 날짜로 변환한다.
- 식별자 매칭은 대소문자 무시 + 부분 매칭으로 수행하며, 후보가 여러 개면 목록을 제시하고 추측하지 않는다.
- 결과 제한: 응답당 최대 15건.

### 3.3 milvus_scanner

- 이름: `milvus_scanner` · 소스: [agents/milvus_scanner.py](../data_agent/agents/milvus_scanner.py)
- 수집된 이미지 데이터만 다룬다: 데이터셋 내용, 유사도 검색, filter 기반 조회, coreset sampling

**Collection 명명 규칙**

```
process_modelName_modelVersion
예시:  modelName=EpoxyClassifier, modelVersion=v1.1, process=SMD  ->  SMD_EpoxyClassifier_v1.1
```

**Record schema (10개 필드)**

| # | 필드 | 설명 |
|---|---|---|
| 1 | `pk` | Primary key |
| 2 | `filename` | 데이터 파일명 |
| 3 | `data_uri` | 데이터의 고유한 S3 object key |
| 4 | `feature_vector` | 데이터의 feature vector. collection 내에서는 길이가 동일하고 collection 간에는 다를 수 있음 |
| 5 | `prediction` | 모델이 검사 후 예측한 라벨 |
| 6 | `confidence` | 예측 confidence |
| 7 | `elapsed_time` | 전체 검사 소요 시간 |
| 8 | `gbm` | 데이터가 수집된 법인 |
| 9 | `process` | 데이터가 수집된 공정 라인 |
| 10 | `location` | 법인 내 공정 라인의 위치 |

**Operation**

| Operation | MCP tool | 제한 |
|---|---|---|
| 유사도 검색 | `mcp_milvus_extract_embeddings_and_vector_search` | 기본 5, 최대 10 |
| Collection 정보 조회 | `mcp_milvus_get_collection_info` | — |
| Collection query (filter expression) | Milvus query tool | 기본 5, 최대 10 |
| Coreset sampling | `mcp_milvus_get_k_center_sampled_data_as_zip_file` | 라벨별 sample 수는 사용자가 지정 |

- Coreset sampling: 사용자가 라벨과 각 라벨의 sample 수를 지정한다 (예: Good 100 + NG 200 → 최대 300건). 선택적으로 "keep" 라벨을 지정하면 sampling 없이 전량 포함된다. sample/keep 어디에도 없는 라벨은 완전히 제외된다.
- 응답에는 항목별 `data_uri`, `filename`, `prediction`을 포함하며, collection 이름/필드 이름/primary key/feature vector 상세는 노출하지 않는다.

### 3.4 system_agent

- 이름: `system_agent` · 소스: [agents/system_agent.py](../data_agent/agents/system_agent.py)
- 단일 목적: 첫 번째 사용자 메시지로부터 짧은 대화 제목(2–8 단어) 생성
- `TitleGenerator`([services/title_generator.py](../data_agent/services/title_generator.py))가 `InMemorySessionService`를 사용하는 전용 ADK `Runner`에서 실행한다 — 호출마다 임시 세션을 만들고, 생성이 실패하더라도 항상 삭제한다
- `system_model_openapi` 설정 블록으로 만든 전용 `LiteLlm`을 사용하므로 agent 모델과 독립적이다
- 결과는 `AgentRunner`가 세션 state의 `session_title` 키에 기록한다
- 제목은 사용자의 첫 메시지와 동일한 언어로 작성된다

---

## 4. LLM 모델

- Agent framework: **FabriX ADK** 사용
  · Google ADK 기능 대부분을 wrapping하면서 사내 Gauss 모델 접근 기능 추가 제공
  · Note. beta/최초 release로 현재 다소 unstable
  · Constraint. 제공된 Gauss 모델 중 일부만 tool calling 지원이며, 특히 고성능 모델들이 tool calling을 지원하지 않음

**모델 비교**

| 모델 | 평가 | Tool calling |
|---|---|---|
| Gauss | Average performance that can degrade on complex queries | 지원 |
| Gauss Think | Similar to Gauss but less stable performance | 지원 |
| GaussO Flash | Average performance but sometimes gets messy | 지원 |
| GaussO Think (Beta) | Solid performance but a little bit unstable | 불안정 — 처음에 tool calling이 되었는데 지금 안 됨 |
| GaussO | Solid performance | 미지원 |
| GaussO Think | Solid performance | 미지원 |

모델 간 성능 비교: `GaussO Flash < Gauss Think < Gauss`

**연동 방식**

- 모든 agent는 OpenAI 호환 LLM gateway를 가리키는 `LiteLlm`을 사용한다. Root orchestrator와 scanner는 [agents/models.py](../data_agent/agents/models.py)의 `build_model()`로 모델을 생성하며, 이 함수는 `root_model_openapi` 블록을 읽고 reasoning effort를 `extra_body`로 전달한다:

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

| Agent | 설정 블록 | Reasoning effort |
|---|---|---|
| `root_orchestrator` | `root_model_openapi` | `medium` |
| `mongodb_scanner`, `milvus_scanner` | `root_model_openapi` | `low` |
| `system_agent` | `system_model_openapi` — [agents/system_agent.py](../data_agent/agents/system_agent.py)에서 전용 `LiteLlm` 생성, reasoning effort 없음 | — |

- 두 설정 블록은 독립적이므로 제목 생성은 agent와 다른 gateway / 모델에서 실행할 수 있다.
- [agents/instructions/\_\_init\_\_.py](../data_agent/agents/instructions/__init__.py)의 `get_instruction_with_current_time()`은 instruction 문자열을 ADK instruction provider로 감싸 매 호출마다 `CURRENT LOCAL TIME: ...`을 앞에 붙인다. 따라서 agent는 tool round trip 없이 상대 날짜를 해석한다.

---

## 5. MCP 서버

- 두 MCP 서버는 모두 외부 서비스이며, 백엔드는 ADK `MCPToolset` + `StreamableHTTPConnectionParams`를 사용해 **Streamable HTTP**로 연결한다.
- Endpoint 형식: `http://{host}:{port}/mcp`

| MCP Server | 사용 agent | 설정 키 | 목적 |
|---|---|---|---|
| MongoDB MCP Server | `mongodb_scanner` | `mongodb_mcp.host`, `mongodb_mcp.port` | 배포 모델 metadata 및 검사 요약 조회 |
| Milvus MCP Server | `milvus_scanner` | `milvus_mcp.host`, `milvus_mcp.port` | Feature vector operation: 유사도 검색, collection 정보, coreset sampling |

### 5.1 MongoDB MCP 서버

- 법인에 배포된 AI 모델 metadata가 Data Service MongoDB에 존재하여 agent가 DB에 접근 필요 → MCP 서버를 통해 실제 배포 모델 정보 조회 가능
- 구현 상태: 핵심 toolset 구현 완료, 서버 구축 완료
- Source code: 별도 GitHub repository

### 5.2 Milvus MCP 서버

- AI 모델이 추출한 feature vector가 Milvus Vector DB에 존재하여 agent가 DB에 접근 필요 → MCP 서버를 통해 feature vector에 관련된 operation 수행 가능
- 주요 operation 2종: **데이터 유사도 검색**, **데이터 sampling**
- 구현 상태: 유사도 검색 및 다른 toolset 구현 완료, 데이터 sampling 구현 중, 서버 구축 완료
- Data Sampling은 classification 및 detection task만 지원 예정이다
  · Detection 데이터는 classification 대비 sampling이 tricky 상태이다
  · Sampling 상세 내용은 GitHub Wiki 페이지에 작성 예정이다
- Source code: 별도 GitHub repository

---

## 6. 데이터 저장소

### 6.1 PostgreSQL — Agent 세션 및 State

- **Agent Session 및 State 관리: Database Session Service vs In Memory Session Service**
  · In-Memory Session 서비스 설정은 DB Session 서비스 대비 straightforward이지만 production 환경에서 DB Session 서비스 사용이 더 stable이다. → **Database Session 서비스 선택**
  · PostgreSQL 사용, 서버 구축 완료

| 항목 | 값 |
|---|---|
| 구현 | ADK `DatabaseSessionService` |
| 접속 문자열 | `postgresql+asyncpg://{user}@{host}:{port}/{name}`, [infra/postgres_client.py](../data_agent/infra/postgres_client.py)의 `postgres_dsn()`이 생성 |
| 드라이버 | SQLAlchemy async engine을 통한 `asyncpg` |
| 설정 키 | `postgresql_db.host`, `.port`, `.name`, `.user` |
| 저장 내용 | 세션, 대화 이벤트, 세션 state (`session_title` 포함), 세션 run lock |
| App name | `data_agent` (`AppNames.ROOT`) |
| Session ID | `uuid.uuid4().hex`, 백엔드에서 생성 |

- 세션 제목은 별도 컬럼이 아니라 state delta로 반영된다:

```python
await session_service.append_event(session, Event(
    author=EventAuthors.SYSTEM,
    actions=EventActions(state_delta={SessionStateFields.TITLE: session_title})
))
```

- 실패한 run도 같은 이력에 기록된다: `AgentRunner`가 `error_code="LLM_ERROR"`와 예외 메시지를 담은 `system` 이벤트를 추가하므로, 어떤 turn이 왜 답변 없이 끝났는지 세션에서 확인할 수 있다.
- `system_agent`는 의도적으로 `InMemorySessionService`를 사용한다 — 해당 세션은 일시적이며 사용 직후 삭제된다.

**세션 run lock** — [infra/session_lock.py](../data_agent/infra/session_lock.py)

- `PostgresClient`는 프로세스당 하나의 SQLAlchemy async engine(`pool_size=5`, `max_overflow=5`, `pool_pre_ping=True`)을 소유하며 `execute` / `fetch_one` / `fetch_all`을 제공한다. ADK `DatabaseSessionService`는 같은 DSN으로 자체 engine을 만든다.
- `SessionLockRepository`는 세션당 한 행을 유지한다:

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

| Operation | 동작 |
|---|---|
| `try_acquire` | 원자적 `INSERT ... ON CONFLICT DO UPDATE ... WHERE run_state = 'idle' RETURNING` 한 번; 행이 반환되지 않으면 이미 실행 중인 세션 |
| `release` | `idle`로 변경; 절대 예외를 던지지 않으므로 release 실패가 run 자체의 결과를 가리지 않는다 |
| `get_run_state` / `get_run_states` | 세션 하나 또는 여러 세션의 상태 조회 — `GET .../run-state`, 세션 상세, 세션 목록에서 사용 |
| `delete` | 세션 삭제 시 행 제거 |
| `initialize` | 시작 시 테이블 생성, `reset_session_locks`가 true이면 모든 `running` 행을 `idle`로 변경 |

- Lease는 없다. 프로세스가 crash하면 해당 lock은 다음 시작 시 reset될 때까지 `running`으로 남으며, 이 reset은 백엔드 프로세스가 하나일 때만 안전하다 (§13 참고).

### 6.2 Object Storage — Artifact

| 항목 | 값 |
|---|---|
| 프로토콜 | S3 호환 (`signature_version=s3v4`) |
| 클라이언트 | `ObjectStorage`([infra/object_storage.py](../data_agent/infra/object_storage.py)) — `aiobotocore`, 앱 시작 시 연결 / 종료 시 close |
| 설정 키 | `object_storage.bucket`, `.endpoint`, `.access_key`, `.secret_key` |
| ADK 연동 | `ObjectStorageArtifactService(BaseArtifactService)` — [infra/artifact_store.py](../data_agent/infra/artifact_store.py) |
| 기본 content type | 업로드와 `head_object` 어느 쪽도 제공하지 않으면 `application/octet-stream` (`CONTENT_TYPE`) |

**Object key 구조**

```
{app_name}/{user_id}/{session_id}/{filename}/{version}
예시:  data_agent/donghy.kim/9f2c.../defect_001.jpg/0
```

- 버전 관리는 자동이다: `list_versions()`가 기존 정수 suffix를 읽고 새 버전은 `max + 1`이 된다. `parse_version()`은 그 역연산으로, 다운로드 시 `data_uri`에서 버전을 추출한다.
- `ObjectStorage`가 제공하는 기능: `list_paginated_objects`, `upload_object`, `retrieve_object`, `retrieve_object_info`, `delete_objects`. 각 메서드는 실패 시 예외 대신 로그를 남기고 `None` / `False`를 반환한다.
- `delete_session_artifacts()`는 세션 prefix 아래 모든 객체를 삭제하며 실패 시 예외를 던진다. `AgentRunner.delete_session`은 세션 행과 lock 행을 지우기 전에 이를 먼저 호출하므로, 삭제 실패가 객체를 고아로 남기지 않는다.
- Content type은 업로드 시 보존되며 다운로드 시 `head_object`로 다시 읽어 사용한다.

### 6.3 MongoDB (MCP 경유)

- 백엔드가 직접 접근하지 않으며, MongoDB MCP 서버를 통해서만 접근한다
- 배포된 AI 모델 metadata 및 일별 검사 결과 요약 document 보관

### 6.4 Milvus Vector DB (MCP 경유)

- 백엔드가 직접 접근하지 않으며, Milvus MCP 서버를 통해서만 접근한다
- 모델당 하나의 collection을 보유하며, §3.3의 feature vector 및 검사 결과를 저장한다

---

## 7. API Endpoint

Agent 기능의 base path: `/apps`

### 7.1 Endpoint 목록

| Method | Path | Request | Response | 설명 |
|---|---|---|---|---|
| `GET` | `/health` | — | `CheckHealthStatusResponse` | 서버 / PostgreSQL / object storage 상태 확인 |
| `GET` | `/logs` | — | `application/zip` | 서버 로그를 ZIP으로 다운로드 |
| `GET` | `/apps/users/{user_id}/sessions` | — | `ListSessionsResponse` | 사용자의 전체 세션 목록 |
| `POST` | `/apps/users/{user_id}/sessions` | — | `CreateSessionResponse` | 새 세션 생성 |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}` | — | `SessionInfo` | 전체 이벤트 이력을 포함한 세션 상세 |
| `DELETE` | `/apps/users/{user_id}/sessions/{session_id}` | — | `200 OK` | 세션 삭제 |
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/title` | — | `CreateSessionTitleResponse` | 마지막 사용자 메시지로 제목 생성 |
| `PATCH` | `/apps/users/{user_id}/sessions/{session_id}/title` | `RenameSessionRequest` | `200 OK` | 세션 제목 수동 변경 |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/artifact` | `LoadSessionArtifactRequest` | binary + `media_type` | Object key로 artifact 다운로드 |
| `GET` | `/apps/users/{user_id}/sessions/{session_id}/run-state` | — | `GetRunStateResponse` | 이벤트를 로드하지 않고 run 진행 여부(`idle` / `running`)만 조회 |
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `RunAgentRequest` + 선택적 `image_file` | `RunAgentResponse` | 사용자 prompt로 agent 실행 |

### 7.2 데이터 모델

소스: [schemas/runner.py](../data_agent/schemas/runner.py), [schemas/health.py](../data_agent/schemas/health.py)

| 모델 | 필드 |
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

**참고 사항**

- `RunAgentRequest`와 `LoadSessionArtifactRequest`는 `Depends()`로 바인딩되어 있어 JSON body가 아니라 **form / query 파라미터**로 전달된다. 따라서 이미지 첨부 시 `POST /run`은 `multipart/form-data` 요청이다.
- `POST /run`에 `new_session=true`를 전달하면 응답 생성 후, run lock을 아직 보유한 상태에서 제목 생성이 자동으로 수행된다.
- 세션 목록과 세션 상세에는 run lock 테이블에서 읽은 `run_state`가 포함되므로, frontend는 새로고침 후에도 "응답 중" 상태를 표시할 수 있다. `GET .../run-state`는 이벤트를 로드하지 않고 같은 값을 반환한다.
- ADK가 반환하는 timestamp는 Unix 값이며 `convert_unix_to_datetime`으로 변환된다.

### 7.3 에러 처리

| 조건 | 상태 코드 |
|---|---|
| 해당 세션에 이미 run 진행 중 (`SessionBusyError` — `/run`, 제목 생성, 제목 변경에서 발생) | `409 Conflict` |
| 세션 없음 / 잘못된 인자 (`ValueError`) | `400 Bad Request` |
| 그 외 예외 | `500 Internal Server Error` |
| 로그 파일 없음 (`/logs`) | `404 Not Found` (현재는 404가 catch-all handler 안에서 발생하므로 실제로는 `500`으로 반환됨) |

- `SessionBusyError`([common/exceptions.py](../common/exceptions.py))가 첫 번째 타입 예외이다. 나머지 router는 여전히 handler를 광범위한 `except Exception`으로 감싸고 예외 문자열을 `detail`로 반환하며, 이를 교체하는 작업은 roadmap 이슈 #8이다.

---

## 8. 요청 처리 흐름

### 8.1 `POST /apps/users/{user_id}/sessions/{session_id}/run`

```
 1. Frontend            POST /run  (query, new_session, image_file?)
                              │
 2. runner.py                 ├─ app.state에서 AgentRunner 주입
                              │
 3. AgentRunner.run           ├─ SessionLockRepository.try_acquire()  ──►  PostgreSQL
                              │     └─ 이미 실행 중  ─►  SessionBusyError  ─►  409 Conflict
                              │
                              ├─ image_file이 있으면:
                              │     ├─ ObjectStorageArtifactService.save_artifact()
                              │     │     └─ ObjectStorage.upload_object()  ──►  Object Storage
                              │     └─ 텍스트 Part 추가:
                              │           "Uploaded Artifact:
                              │            filename: ...
                              │            data_uri: ...
                              │            content_type: ..."
                              │
                              ├─ 사용자 prompt를 텍스트 Part로 추가
                              │
 4. ADK Runner.run_async      ├─ PostgreSQL에서 세션 로드
                              │     └─ TimingLoggerPlugin이 run / agent / llm / tool의 [TIMING] START/END 기록
                              │
 5. Root Orchestrator         ├─ 의도 해석 후 경로 선택
                              │     ├─ AgentTool(mongodb_scanner) ─► MCP ─► MongoDB
                              │     └─ AgentTool(milvus_scanner)  ─► MCP ─► Milvus
                              │
                              ├─ 최종 자연어 답변 구성
                              │
 6. ADK                       ├─ 이벤트 + state를 PostgreSQL에 저장
                              │
 7. AgentRunner               ├─ 첫 번째 final 이벤트에서 응답 텍스트와 timestamp 추출
                              │     └─ 실패 시: system 이벤트(error_code=LLM_ERROR) 추가 후 예외 재전파
                              │
 8. finally                   ├─ new_session이면 _create_session_title() 수행
                              │     └─ TitleGenerator ─► system_agent ─► state_delta {session_title}
                              └─ SessionLockRepository.release()
                              │
 9. Response                  RunAgentResponse { response, timestamp }
```

### 8.2 Artifact 다운로드

- Agent 답변에는 생성된 artifact의 object key(`data_uri`)가 포함된다 — 예를 들어 coreset sampling이 생성한 ZIP 파일.
- Frontend는 `GET /apps/users/{user_id}/sessions/{session_id}/artifact?filename=...&data_uri=...`를 호출한다 (`media_type`은 선택적 fallback).
- 백엔드는 `data_uri`의 마지막 segment에서 버전을 추출하고, 세션 prefix 아래 `filename`의 해당 버전을 읽은 뒤 `head_object`로 content type을 확인(없으면 `media_type` 사용)하여 raw bytes를 반환한다.

### 8.3 Health check

- `GET /health`는 `HealthChecker`([services/health.py](../data_agent/services/health.py))에 위임한다. `HealthChecker`는 프로세스 전역의 `PostgresClient`와 `ObjectStorage` 클라이언트를 재사용하며 각 probe를 `HEALTH_CHECK_TIMEOUT`(5초)으로 제한한다:
  · PostgreSQL — connection pool을 통해 `SELECT 1` 실행
  · Object storage — 설정된 bucket에 `head_bucket` 호출
- 각 항목은 독립적으로 `healthy` / `unhealthy`를 반환하며, 점검이 완료되기만 하면 endpoint 자체는 `200`을 반환한다.

---

## 9. 설정 (Configuration)

- 소스: [common/config.py](../common/config.py) · 기본 파일: `config.yaml`
- 시작 시 로드되며, CLI(`--config` / `-c`)와 `_ENV_MAP`을 통한 환경 변수로 override 가능

| 블록 | 키 | 용도 |
|---|---|---|
| — | `server_port` | HTTP listen 포트 |
| — | `reset_session_locks` (기본 `true`) | 시작 시 `running` 상태의 세션 lock을 모두 `idle`로 reset; 여러 백엔드 프로세스가 같은 DB를 공유하면 반드시 `false` |
| `root_model_openapi` | `model`, `endpoint`, `client_key`, `pass_key`, `model_id` | `root_orchestrator` 및 scanner용 LLM gateway |
| `system_model_openapi` | `model`, `endpoint`, `client_key`, `pass_key`, `model_id` | `system_agent`(제목 생성)용 LLM gateway |
| `mongodb_mcp` | `host`, `port` | MongoDB MCP Server endpoint |
| `milvus_mcp` | `host`, `port` | Milvus MCP Server endpoint |
| `postgresql_db` | `host`, `port`, `name`, `user` | Agent 세션 DB 및 run lock 테이블 |
| `object_storage` | `bucket`, `endpoint`, `access_key`, `secret_key` | Artifact 저장소 |

- 모든 키는 `_ENV_MAP`에 대응하는 환경 변수를 가진다 (예: `POSTGRESQL_DB_HOST`, `OBJECT_STORAGE_BUCKET`, `RESET_SESSION_LOCKS`, `ROOT_MODEL_OPENAPI_MODEL`). 따라서 파일 마운트 없이 컨테이너 설정이 가능하다. Boolean은 `1/0`, `true/false`, `yes/no`, `on/off`를 허용한다. 모델 ID 환경 변수 이름은 `ROOT_MODEL_OPENAPI_ROOT_MODEL_ID`, `SYSTEM_MODEL_OPENAPI_ROOT_MODEL_ID`이다.
- MCP 및 DB endpoint는 환경마다 다르며, `config.yaml`의 값은 해당 파일이 배포된 환경을 의미한다.

> **보안 참고.** 현재 `config.yaml`이 git에 추적되고 있으며 실제 credential을 포함한다. Credential 교체 및 파일 추적 해제는 [roadmap.md](roadmap.md)의 P0 및 이슈 #1이다.

---

## 10. 배포

| 항목 | 값 |
|---|---|
| Base image | `python:3.13.13` (사내 registry) |
| 작업 디렉터리 | `/home/work/cosmo-da-backend` |
| 의존성 | `requirements_py313_prod.txt` |
| Entry point | `python -m data_agent -c /home/work/cosmo-da-backend/config.yaml` |
| Listen 주소 | `0.0.0.0:{server_port}` |
| 서버 | Uvicorn, 단일 worker |

**애플리케이션 lifecycle** — [app.py](../data_agent/app.py)의 `lifespan`, [\_\_main\_\_.py](../data_agent/__main__.py)에서 시작

- `__main__`은 logger를 초기화한 뒤 `data_agent.app:app`을 Uvicorn으로 `0.0.0.0:{server_port}`에서 실행한다.
- 시작 (`lifespan`):
  · `ObjectStorage.connect()` — S3 클라이언트 오픈
  · `PostgresClient()` — 프로세스당 하나의 SQLAlchemy engine
  · `SessionLockRepository.initialize()` — `session_run_locks` 테이블 생성, `reset_session_locks`가 true이면 stale lock reset
  · `HealthChecker(db_client, object_storage)` 및 `AgentRunner(agent=root_agent, session_service=DatabaseSessionService(postgres_dsn()), artifact_service=ObjectStorageArtifactService(...), title_generator=TitleGenerator(), lock_repository=...)` 생성
  · `object_storage`, `health_checker`, `agent_runner`를 `app.state`에 저장하며 router는 `request.app.state`로 주입받는다
- 종료:
  · `PostgresClient.close()` — engine dispose
  · `ObjectStorage.close()`
  · `shutdown_logs_executor()`

**Middleware** — [middleware/](../data_agent/middleware/)

- `CORSMiddleware`(현재 `*`, roadmap #7)와 모든 요청(`method path?query`) / 응답(상태 코드, 소요 ms)을 기록하는 HTTP middleware

**로깅**

- `initialize_logger("cosmo_data_agent.log")`로 초기화되며 `logs/` 하위에 기록되고(rotating, 10 MB × 20개) `GET /logs`로 다운로드 가능
- `/run`은 시작 / 종료 / busy 거절 / 실패 시점에 세션 ID와 소요 시간을 포함한 `[TIMING]` 로그를 남긴다
- `TimingLoggerPlugin`([agents/plugins/timing.py](../data_agent/agents/plugins/timing.py))은 두 ADK runner 모두에 연결되어 run, agent turn, LLM 호출, tool 호출마다 소요 시간과 token 사용량이 포함된 START/END 로그를 남기며, 모든 줄에 invocation id(`inv=...`)가 붙는다. 상세 내용은 [timing-logging.md](timing-logging.md) 참고.

---

## 11. 데이터의 Feature Vector 추출

- 데이터 feature vector의 quality가 데이터 sampling 및 유사도 검색 성능에 직접적으로 영향
- Feature vector를 추출하는 모델 검토
  · 학습된 검사 모델로 직접 추출하기 어려워 pretrained 모델(DINOv2/v3 등) 활용 검토
  · 검토 결과: pretrained 모델은 general 특징만 capture하여 성능 미흡
  · 예시: 학습된 검사 모델 및 DINOv3-7b 모델이 추출하는 feature vector 기반으로 데이터 유사도 검색 결과 비교
  · 예시: 학습된 검사 모델 및 DINOv3-7b 모델이 추출하는 feature map 비교
  · 결론: 데이터 sampling 및 데이터 유사도 검색 수행 중에 좋은 성능과 의미 있는 결과를 얻기 위해서 학습된 모델이 추출하는 feature vector를 사용하는 게 좋다
- **Constraints.** Edge에서 feature vector를 추출하고 데이터와 함께 수원 서버로 전송하는 게 어려운 상태이라 수원 서버에 vector 추출 pipeline 필요

---

## 12. Use Case 매핑

| ID | Use case | Workflow | 주요 컴포넌트 |
|---|---|---|---|
| UC1-1 | 검사 현황 조회 | W1 | `mongodb_scanner` → MongoDB MCP |
| UC1-2 | 모델 성능 분석 및 Trend Assessment | W2 | `mongodb_scanner` + orchestrator 계산 |
| UC1-3 | 배포 모델 정보 조회 | W3 | `mongodb_scanner` → MongoDB MCP |
| UC1-4 | 데이터셋 현황 조회 | W4 | `milvus_scanner` → `mcp_milvus_get_collection_info` |
| UC1-5 | 데이터 유사도 검색 | W5 | `milvus_scanner` → `mcp_milvus_extract_embeddings_and_vector_search` |
| UC1-6 | 데이터 선별 (Coreset Sampling) | W6 | `milvus_scanner` → `mcp_milvus_get_k_center_sampled_data_as_zip_file` |
| UC1-7 | Labeling Validation | W4 + filter query | `milvus_scanner` (confidence / 클러스터 이상치) |
| UC1-8 | Drift Detection (on-demand) | W2 + W4 | `mongodb_scanner` + `milvus_scanner` |

**공통 제약**

| 제약 | 값 |
|---|---|
| 검사 조회 time window | 쿼리당 최대 2주 |
| 유사도 검색 결과 수 | 기본 5, 최대 10 |
| MongoDB 응답당 레코드 수 | 최대 15 |
| Coreset sampling 지원 task | classification, detection만 |

---

## 13. 현재 제약사항 및 향후 계획

### 13.1 알려진 제약사항

| 영역 | 제약 |
|---|---|
| Agent framework | FabriX ADK가 beta/최초 release로 현재 다소 unstable |
| LLM | 일부 Gauss 모델만 tool calling 지원, 특히 고성능 모델들이 미지원 |
| Feature vector | Edge 추출 pipeline 부재, 수원 서버 pipeline 필요 |
| 데이터 sampling | Detection sampling이 classification 대비 tricky, 구현 중 |
| 실행 모델 | `POST /run`이 동기식이며 수 분이 소요될 수 있어 긴 요청이 클라이언트를 blocking |
| 동시성 | 같은 세션에 대한 동시 run은 Postgres run lock으로 `409` 거절; lock에 lease가 없어 crash한 run의 lock은 다음 시작 시 reset될 때까지 유지됨 |
| 배포 | Uvicorn 단일 worker; 여러 프로세스가 같은 DB를 공유하기 전에 `reset_session_locks`를 `false`로 설정해야 함 |

### 13.2 향후 계획

상세 이슈 및 PR 순서는 [roadmap.md](roadmap.md)에, 목표 비동기 실행 모델은 [migration.md](migration.md)에 정리되어 있다.

| 주제 | 요약 | 참조 |
|---|---|---|
| Credential 정리 | 유출된 credential 교체, `config.yaml` 추적 해제 | roadmap P0, #1 |
| CORS | `*` origin을 설정된 frontend origin 목록으로 교체 | roadmap #7 |
| 타입 있는 예외 | 광범위한 `except Exception` 처리 교체 | roadmap #8 |
| 비동기 실행 모델 | `POST /run`이 run 레코드와 함께 `202` 반환, polling 및 취소 지원 | roadmap #14–#28, migration.md |
| SSE 진행 스트림 | `GET /runs/{run_id}/events`로 tool call 진행 상황 실시간 전달 | roadmap #32 |
| Multi-worker 지원 | Instance 단위 상태 관리로 `--workers` 안전하게 사용 | roadmap #34 |
| **인증 (SSO)** | 사내 ADFS OIDC 연동, 세션 쿠키, 사용자별 권한 검증 | [authentication.md](authentication.md) |

> **인증 현황.** 현재 서비스에는 인증이 없다 — `user_id`가 인증되지 않은 path 파라미터이므로 누구든 다른 사용자의 세션에 접근할 수 있다. ADFS 연동 및 이슈 분해를 포함한 전체 설계는 [authentication.md](authentication.md)에 있다.
