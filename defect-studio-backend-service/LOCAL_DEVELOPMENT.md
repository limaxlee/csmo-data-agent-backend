로컬에서 staging 서비스 연동
최초 한 번 .env.example을 .env로 복사하고 다음 값을 준비한다. .env는 Git에 넣지 않는다.

LOCAL_DB_PASSWORD: 개발자 전용 DB 암호. URL에 사용할 수 있는 값으로 설정한다.
SERVICE_JWT_SECRET: staging web-auth와 동일한 승인된 서비스 토큰 검증 키.
SECRET_KEY: 로컬 전용 별도 키.
MINIO_ACCESS_KEY, MINIO_SECRET_KEY: staging Agent 공유 저장소에 대한 승인된 키.
예제의 공개 URL은 staging Agent·공유 저장소를 가리킨다. 사내 서비스와 프록시에 접근할 수 있는 네트워크가 필요하다. 저장소의 Dockerfile과 build-ca/ 인증서를 사용한다. 실제 생성 요청은 staging Agent와 저장소를 사용한다. DB와 대화 이력은 로컬 전용이다.

저장소 루트에서 실행한다.

docker compose up -d
최초에는 공통 이미지를 빌드한다. DB 준비 → migration 완료 → API와 worker 시작 순서이며, migration이 실패하면 두 프로세스도 시작하지 않는다. API·worker는 같은 이미지와 .env를 사용한다. 컨테이너에서는 DB 주소만 db:5432로 바꾼다. 개발용 앱이나 별도 런처는 없다. API는 배포와 같은 src.container.app:app, worker는 기존 src.data_integration.infrastructure.input_worker 모듈을 실행한다.

기본 접속은 API http://127.0.0.1:18089, DB 127.0.0.1:15439다. 포트는 LOCAL_API_PORT, LOCAL_DB_PORT로 바꿀 수 있다. 같은 포트의 uv 서버를 중복 실행하지 않는다. 이전 Compose의 DB/MinIO 볼륨은 삭제하지 않으며 이 구성은 별도 로컬 DB 볼륨을 사용한다.

docker compose ps -a
docker compose logs -f backend worker
DB와 backend는 healthy, worker는 Up인지 확인한다. migrate의 Exited (0)은 정상 완료다. worker가 Up인 것만으로 실제 업로드 job의 성공을 뜻하지는 않는다.

FE 저장소에서는 pnpm dev로 실행하고 http://localhost:13007 에 접속한다. FE의 로그인 버튼은 실제 staging 인증 서버가 제공하는 로그인 화면을 연다. 현재 staging 개발 로그인 모드의 허용된 본인 loginid를 사용한다. 로컬 DB에 계정이 없으면 화면에서 계정을 준비한다. 인증 이후 이미지 조회·업로드·생성은 사용자 계정으로 확인해야 한다.

API 소스는 읽기 전용으로 마운트하며 수정 시 자동 리로드한다. worker 코드 변경 후에는 docker compose restart worker를 실행한다. 의존성과 Dockerfile 변경은 다음 docker compose up -d에서 캐시를 사용해 빌드한다. .env를 바꿔도 같은 명령으로 컨테이너에 반영한다.

HTTPX가 이미지에 설치된 회사 CA를 읽도록 SSL_CERT_FILE을 설정한다. SR Agent 호스트 mlp-service.n10.sr-cloud.com은 staging·production과 동일하게 직접 연결한다. Compose가 API·worker의 NO_PROXY와 no_proxy 양쪽에 이 호스트를 항상 추가하고, 기존 .env나 셸에 지정한 우회 주소도 유지한다. 이전 .env에 SR 호스트가 없어도 별도 초기화 명령 없이 docker compose up -d로 적용된다. 그 외 호스트는 기존 프록시 설정을 따른다. 애플리케이션 코드와 Agent는 변경하지 않는다.

이미 실행 중인 컨테이너에 이 설정을 반영할 때도 docker compose up -d를 실행한다. Compose가 변경된 환경 변수로 API와 worker를 재생성한다. docker compose restart만으로는 환경 변수가 갱신되지 않는다. 컨테이너 재생성은 기존 연결을 끊으므로 진행 중인 채팅·작업을 마친 뒤 적용한다.

docker compose stop
docker compose up -d
중지해도 DB와 로컬 파일 볼륨은 유지된다. 호스트 Python/uv는 Docker 실행에 필요하지 않다.

이미지와 폴더는 S3로 직접 전송하고, ZIP만 기존 worker가 해제·등록한다. 업로드 URL 발급과 PNG 정규화는 API가 담당하며 Agent 입력 경로는 유지한다. NATIVE_UPLOADS.md에 저장소 CORS, 입력 폴더 구조와 용량 상한을 설명했다. 새 시크릿은 필요 없다. 기존 .env에 Labeler 설정이 있어도 기본 채팅·업로드는 Labeler를 호출하지 않는다. LABELER_API_URL, LABELER_AGENT_INPUT_KEY는 이전 Labeler 작업을 마무리할 때만 필요하므로, 진행 중인 이전 작업이 있다면 완료될 때까지 유지한다.