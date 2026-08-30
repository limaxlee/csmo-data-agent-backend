# [데이터 서비스] 데이터 에이전트 — 아키텍처

**Repository:** `limaxlee/csmo-data-agent-backend`
**기준 커밋:** `main` / `9a3d572`
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
   │  SystemAgentRunner (대화 제목 생성)                                    │
   └──────┼──────────┼──────────────────────────────┼──────────────────────┘
          │          │                              │
          ▼          ▼                              ▼
   ┌────────────┐  ┌──────────────────┐   ┌──────────────────┐
   │ PostgreSQL │  │ MongoDB MCP      │   │ Milvus MCP       │
   │ (세션,     │  │ Server           │   │ Server           │
   │  이벤트,   │  └────────┬─────────┘   └────────┬─────────┘
   │  state)    │           ▼                      ▼
   └────────────┘  ┌──────────────────┐   ┌──────────────────┐
                   │ MongoDB          │   │ Milvus Vector DB │
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
| PostgreSQL | Agent 세션 / 이벤트 / state 영속화 | ADK `DatabaseSessionService`, asyncpg |
| Object Storage | 사용자가 업로드한 이미지 artifact, sampling 결과 ZIP 파일 | S3 호환, aiobotocore |

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
- `InMemorySessionService`를 사용하는 별도의 `SystemAgentRunner`에서 실행되며, 임시 세션은 제목 생성 직후 삭제된다
- 결과는 세션 state의 `session_title` 키에 기록된다
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

- 모든 agent는 사내 OpenAPI LLM gateway를 가리키는 `LiteLlm`을 사용한다:

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

| Agent | 모델 ID 설정 |
|---|---|
| `root_orchestrator`, `mongodb_scanner`, `milvus_scanner` | `model_openapi.root_model_id` |
| `system_agent` | `model_openapi.system_model_id` |

- [agents/llm.py](../data_agent/agents/llm.py)에는 공통화된 `build_model(reasoning_effort)` helper와 `with_current_time()` instruction wrapper(매 호출마다 현재 시각을 instruction 앞에 붙여 tool round trip을 제거)가 준비되어 있으나, 현재 활성 agent에는 아직 적용되지 않았다.

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
| 접속 문자열 | `postgresql+asyncpg://postgres@{host}:{port}/{name}` |
| 드라이버 | `asyncpg` |
| 설정 키 | `postgresql_db.host`, `.port`, `.name`, `.user` |
| 저장 내용 | 세션, 대화 이벤트, 세션 state (`session_title` 포함) |
| App name | `data_agent` (`ROOT_APP_NAME`) |
| Session ID | `uuid.uuid4().hex`, 백엔드에서 생성 |

- 세션 제목은 별도 컬럼이 아니라 state delta로 반영된다:

```python
await session_service.append_event(session, Event(
    author=SYSTEM_AUTHOR,
    actions=EventActions(state_delta={SESSION_TITLE_KEY: session_title})
))
```

- `system_agent`는 의도적으로 `InMemorySessionService`를 사용한다 — 해당 세션은 일시적이며 사용 직후 삭제된다.

### 6.2 Object Storage — Artifact

| 항목 | 값 |
|---|---|
| 프로토콜 | S3 호환 (`signature_version=s3v4`) |
| 클라이언트 | `aiobotocore`, 앱 시작 시 연결 / 종료 시 close |
| 설정 키 | `object_storage.bucket`, `.endpoint`, `.access_key`, `.secret_key` |
| ADK 연동 | `OSArtifactService(BaseArtifactService)` — [storage/os_artifact.py](../data_agent/storage/os_artifact.py) |
| Presigned URL 유효기간 | 7200초 (`PRESIGNED_URL_EXPIRED_IN`) |

**Object key 구조**

```
{app_name}/{user_id}/{session_id}/{filename}/{version}
예시:  data_agent/donghy.kim/9f2c.../defect_001.jpg/0
```

- 버전 관리는 자동이다: `list_versions()`가 기존 정수 suffix를 읽고 새 버전은 `max + 1`이 된다.
- `ObjectStorage`가 제공하는 기능: `list_paginated_objects`, `upload_object`, `retrieve_object`, `retrieve_object_info`, `get_presigned_url`, `delete_objects`
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
| `POST` | `/apps/users/{user_id}/sessions/{session_id}/run` | `RunAgentRequest` + 선택적 `image_file` | `RunAgentResponse` | 사용자 prompt로 agent 실행 |

### 7.2 데이터 모델

소스: [schemas/runner.py](../data_agent/schemas/runner.py), [schemas/health.py](../data_agent/schemas/health.py)

| 모델 | 필드 |
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

**참고 사항**

- `RunAgentRequest`와 `LoadSessionArtifactRequest`는 `Depends()`로 바인딩되어 있어 JSON body가 아니라 **form / query 파라미터**로 전달된다. 따라서 이미지 첨부 시 `POST /run`은 `multipart/form-data` 요청이다.
- `POST /run`에 `new_session=true`를 전달하면 응답 생성 후 제목 생성이 자동으로 수행된다.
- ADK가 반환하는 timestamp는 Unix 값이며 `convert_unix_to_datetime`으로 변환된다.

### 7.3 에러 처리

| 조건 | 상태 코드 |
|---|---|
| 세션 없음 / 잘못된 인자 (`ValueError`) | `400 Bad Request` |
| 그 외 예외 | `500 Internal Server Error` |
| 로그 파일 없음 (`/logs`) | `404 Not Found` |

- 현재 모든 router가 handler를 광범위한 `except Exception`으로 감싸고 예외 문자열을 `detail`로 반환한다. 타입이 명확한 예외로 교체하는 작업은 roadmap 이슈 #8이다.

---

## 8. 요청 처리 흐름

### 8.1 `POST /apps/users/{user_id}/sessions/{session_id}/run`

```
 1. Frontend            POST /run  (query, new_session, image_file?)
                              │
 2. runner.py                 ├─ app.state에서 RootAgentRunner 주입
                              │
 3. RootAgentRunner.run       ├─ image_file이 있으면:
                              │     ├─ OSArtifactService.save_artifact()
                              │     │     └─ ObjectStorage.upload_object()  ──►  Object Storage
                              │     └─ 텍스트 Part 추가:
                              │           "Uploaded Artifact:
                              │            Filename: ...
                              │            Data uri: ...
                              │            Content type: ..."
                              │
                              ├─ 사용자 prompt를 텍스트 Part로 추가
                              │
 4. ADK Runner.run_async      ├─ PostgreSQL에서 세션 로드
                              │
 5. Root Orchestrator         ├─ 의도 해석 후 경로 선택
                              │     ├─ AgentTool(mongodb_scanner) ─► MCP ─► MongoDB
                              │     └─ AgentTool(milvus_scanner)  ─► MCP ─► Milvus
                              │
                              ├─ 최종 자연어 답변 구성
                              │
 6. ADK                       ├─ 이벤트 + state를 PostgreSQL에 저장
                              │
 7. RootAgentRunner           ├─ 최종 응답 텍스트와 timestamp 추출
                              │
 8. finally                   └─ new_session이면 create_session_title() 수행
                                     └─ SystemAgentRunner ─► system_agent ─► state_delta
                              │
 9. Response                  RunAgentResponse { response, timestamp }
```

### 8.2 Artifact 다운로드

- Agent 답변에는 생성된 artifact의 object key(`data_uri`)가 포함된다 — 예를 들어 coreset sampling이 생성한 ZIP 파일.
- Frontend는 `GET /apps/users/{user_id}/sessions/{session_id}/artifact?data_uri=...`를 호출한다.
- 백엔드는 `head_object`로 content type을 확인하고 객체를 읽어 올바른 `media_type`과 함께 raw bytes를 반환한다.

### 8.3 Health check

- `GET /health`는 각각 5초 timeout으로 두 가지 실제 probe를 수행한다:
  · PostgreSQL — 연결을 맺고 `SELECT 1` 실행
  · Object storage — 설정된 bucket에 `head_bucket` 호출
- 각 항목은 독립적으로 `healthy` / `unhealthy`를 반환하며, 점검이 완료되기만 하면 endpoint 자체는 `200`을 반환한다.

---

## 9. 설정 (Configuration)

- 소스: [common/config.py](../common/config.py) · 기본 파일: `config.yaml`
- 시작 시 로드되며, CLI(`--config` / `-c`)와 `_ENV_MAP`을 통한 환경 변수로 override 가능

| 블록 | 키 | 용도 |
|---|---|---|
| — | `server_port` | HTTP listen 포트 |
| `model_openapi` | `endpoint`, `client_key`, `pass_key`, `root_model_id`, `system_model_id` | Gauss / FabriX LLM gateway |
| `mongodb_mcp` | `host`, `port` | MongoDB MCP Server endpoint |
| `milvus_mcp` | `host`, `port` | Milvus MCP Server endpoint |
| `postgresql_db` | `host`, `port`, `name`, `user` | Agent 세션 DB |
| `object_storage` | `bucket`, `endpoint`, `access_key`, `secret_key` | Artifact 저장소 |

- 모든 키는 `_ENV_MAP`에 대응하는 환경 변수를 가진다 (예: `POSTGRESQL_DB_HOST`, `OBJECT_STORAGE_BUCKET`, `MODEL_OPENAPI_ROOT_MODEL_ID`). 따라서 파일 마운트 없이 컨테이너 설정이 가능하다.
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

**애플리케이션 lifecycle** — [\_\_main\_\_.py](../data_agent/__main__.py)

- 시작 (`lifespan`):
  · `ObjectStorage.connect()` — S3 클라이언트 오픈
  · `RootAgentRunner(artifact_service=OSArtifactService(...), system_runner=SystemAgentRunner())` 생성
  · 두 객체를 `app.state`에 저장하여 dependency injection에 사용
- 종료:
  · `ObjectStorage.close()`
  · `shutdown_logs_executor()`

**로깅**

- `initialize_logger("cosmo_data_agent.log")`로 초기화되며 `logs/` 하위에 기록되고 `GET /logs`로 다운로드 가능
- `/run`은 시작 / 종료 / 실패 시점에 세션 ID와 소요 시간을 포함한 `[TIMING]` 로그를 남긴다

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
| Presigned URL 유효기간 | 7200초 (2시간) |
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
| 동시성 | 단일 ADK 세션이 동시 실행에 안전하지 않음 |
| 배포 | Uvicorn 단일 worker |

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
