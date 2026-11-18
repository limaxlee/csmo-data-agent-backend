defect-prod
DEFECT-PROD

PROJECT: dice
ANNOTATIONS: kubectl.kubernetes.io/last-applied-configuration={"apiVersion":"argoproj.io/v1alpha1","kind":"Application","metadata":{"annotations":{},"finalizers":["resources-finalizer.argocd.argoproj.io"],"name":"defect-prod","namespace":"argocd"},"spec":{"destination":{"namespace":"dice","server":"https://kubernetes.default.svc"},"project":"dice","source":{"helm":{"releaseName":"defect-studio","valueFiles":["../../environments/production/defect-studio.yaml"]},"path":"charts/defect-studio","repoURL":"https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git","targetRevision":"main"},"syncPolicy":{"syncOptions":["CreateNamespace=false"]}}}
CLUSTER: in-cluster (https://kubernetes.default.svc)
NAMESPACE: dice   
CREATED AT: 11/09/2026 18:28:08 (4 days ago)
REPO URL: https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git
TARGET REVISION: main
PATH: charts/defect-studio
SYNC OPTIONS: CreateNamespace
RETRY OPTIONS: Retry disabled
STATUS: Synced to main (15a6218)
HEALTH: Healthy
LINKS: 
IMAGES:
dice-docker-local.bart.sec.samsung.net/defect-studio-backend:2026.11.13-fbfab42
dice-docker-local.bart.sec.samsung.net/defect-studio-frontend:2026.11.12-410088c-prod-32496337-1
docker-remote.bart.sec.samsung.net/istio/proxyv2:1.24.2
SYNC POLICY

NONE

PARAMETERS
HELM

VALUES FILES
../../environments/production/defect-studio.yaml
VALUES
PARAMETERS

agentProxy.address: 168.219.61.252
agentProxy.enabled: true
agentProxy.host: digitalcity-forward-proxy.external.local
agentProxy.port: 8080
backend.dbMigrate.enabled: true
backend.dbMigrate.resources.limits.cpu: 500m
backend.dbMigrate.resources.limits.memory: 256Mi
backend.dbMigrate.resources.requests.cpu: 100m
backend.dbMigrate.resources.requests.memory: 128Mi
backend.enabled: true
backend.env.AGENT_SERVICE_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-defect-agent-dev
backend.env.CORS_ORIGINS: []
backend.env.HTTPS_PROXY: http://168.219.61.252:8080
backend.env.MAX_CONCURRENT_RUNS: 7
backend.env.MINIO_BUCKET: defect-agent
backend.env.MINIO_ENDPOINT: gage.ap-northeast-2.samsungspc.com
backend.env.MINIO_SECURE: true
backend.env.MINIO_VERIFY_SSL: false
backend.env.NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.cluster.local,gage.ap-northeast-2.samsungspc.com,mlp-service.n10.sr-cloud.com
backend.env.STORAGE_ALLOW_LOCAL_FALLBACK: false
backend.image: dice-docker-local.bart.sec.samsung.net/defect-studio-backend
backend.imagePullPolicy: IfNotPresent
backend.imagePullSecrets[0]: regcred
backend.port: 8080
backend.replicas: 1
backend.resources.limits.cpu: 1
backend.resources.limits.memory: 4Gi
backend.resources.requests.cpu: 250m
backend.resources.requests.memory: 2Gi
backend.secret.keys.databaseUrl: database-url
backend.secret.keys.minioAccessKey: s3-access-key
backend.secret.keys.minioSecretKey: s3-secret-key
backend.secret.keys.secretKey: secret-key
backend.secret.keys.serviceJwtSecret: service-jwt-secret
backend.secret.name: defect-studio-prod-secrets
backend.strategy: Recreate
backend.tag: 2026.11.13-fbfab42
frontend.enabled: true
frontend.image: dice-docker-local.bart.sec.samsung.net/defect-studio-frontend
frontend.imagePullPolicy: IfNotPresent
frontend.imagePullSecrets[0]: regcred
frontend.nginx.clientHeaderBufferSize:16k
frontend.nginx.largeClientHeaderBuffers: 8 32k
frontend.port: 3000
frontend.replicas: 1
frontend.resources.limits.cpu: 200m
frontend.resources.limits.memory: 128Mi
frontend.resources.requests.cpu: 50m
frontend.resources.requests.memory: 64Mi
frontend.tag: 2026.11.12-410088c-prod-32496337-1
inputWorker.env.NATIVE_THUMBNAIL_MEMORY_MIB: 16384
inputWorker.env.NATIVE_THUMBNAIL_WORKERS: 16
inputWorker.replicas: 4
inputWorker.resources.limits.cpu: 8
inputWorker.resources.limits.memory: 24Gi
inputWorker.resources.requests.cpu: 4
inputWorker.resources.requests.memory: 16Gi
namePrefix: defect-studio
virtualService.apiPath: /defect/api
virtualService.authPath: /auth
virtualService.authService: dice-platform-web-auth.dice.svc.cluster.local
virtualService.authServicePort: 3020
virtualService.enabled: true
virtualService.gateways[0]: istio-system/platform-gateway
virtualService.hosts[0]: dice.gtrai.sec.samsung.net
virtualService.name: defect-studio-prod
virtualService.redirectHttpToHttps: true
virtualService.uiPath: /defect



defect-stage
DEFECT-STAGE

PROJECT: dice
ANNOTATIONS: kubectl.kubernetes.io/last-applied-configuration={"apiVersion":"argoproj.io/v1alpha1","kind":"Application","metadata":{"annotations":{},"finalizers":["resources-finalizer.argocd.argoproj.io"],"name":"defect-stage","namespace":"argocd"},"spec":{"destination":{"namespace":"dice-stage","server":"https://kubernetes.default.svc"},"project":"dice","source":{"helm":{"releaseName":"defect-studio","valueFiles":["../../environments/stage/defect-studio.yaml"]},"path":"charts/defect-studio","repoURL":"https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git","targetRevision":"main"},"syncPolicy":{"automated":{"prune":true,"selfHeal":true},"syncOptions":["CreateNamespace=false"]}}}
CLUSTER: in-cluster (https://kubernetes.default.svc)
NAMESPACE: dice-stage   
CREATED AT: 11/09/2026 18:28:08 (4 days ago)
REPO URL: https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git
TARGET REVISION: main
PATH: charts/defect-studio
SYNC OPTIONS: CreateNamespace
RETRY OPTIONS: Retry disabled
STATUS: Synced to main (15a6218)
HEALTH: Healthy
LINKS: 
IMAGES:
dice-docker-local.bart.sec.samsung.net/defect-studio-backend:2026.11.13-fbfab42
dice-docker-local.bart.sec.samsung.net/defect-studio-frontend:2026.11.13-7762fc7-stage
docker-remote.bart.sec.samsung.net/istio/proxyv2:1.24.2

PARAMETERS
HELM

VALUES FILES: ../../environments/stage/defect-studio.yaml
VALUES: 

PARAMETERS
agentProxy.address: 168.219.61.252
agentProxy.enabled: true
agentProxy.host: digitalcity-forward-proxy.external.local
agentProxy.port: 8080
backend.dbMigrate.enabled: true
backend.dbMigrate.resources.limits.cpu: 500m
backend.dbMigrate.resources.limits.memory: 256Mi
backend.dbMigrate.resources.requests.cpu: 100m
backend.dbMigrate.resources.requests.memory: 128Mi
backend.enabled: true
backend.env.AGENT_SERVICE_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-defect-agent-dev
backend.env.AGENT_SSE_TRANSPORT_DIAGNOSTICS: true
backend.env.CORS_ORIGINS: ["http://localhost:3000","http://localhost:5173"]
backend.env.HTTPS_PROXY: http://168.219.61.252:8080
backend.env.MAX_CONCURRENT_RUNS: 7
backend.env.MINIO_BUCKET: defect-agent
backend.env.MINIO_ENDPOINT: gage.ap-northeast-2.samsungspc.com
backend.env.MINIO_SECURE: true
backend.env.MINIO_VERIFY_SSL: false
backend.env.NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.cluster.local,gage.ap-northeast-2.samsungspc.com,mlp-service.n10.sr-cloud.com
backend.env.STORAGE_ALLOW_LOCAL_FALLBACK: false
backend.image: dice-docker-local.bart.sec.samsung.net/defect-studio-backend
backend.imagePullPolicy: IfNotPresent
backend.imagePullSecrets[0]: regcred
backend.port: 8080
backend.replicas: 1
backend.resources.limits.cpu: 1
backend.resources.limits.memory: 4Gi
backend.resources.requests.cpu: 250m
backend.resources.requests.memory: 2Gi
backend.secret.keys.databaseUrl: database-url
backend.secret.keys.minioAccessKey: s3-access-key
backend.secret.keys.minioSecretKey: s3-secret-key
backend.secret.keys.secretKey: secret-key
backend.secret.keys.serviceJwtSecret: service-jwt-secret
backend.secret.name: defect-studio-stage-secrets
backend.strategy: Recreate
backend.tag: 2026.11.13-fbfab42
frontend.enabled: true
frontend.image: dice-docker-local.bart.sec.samsung.net/defect-studio-frontend
frontend.imagePullPolicy: IfNotPresent
frontend.imagePullSecrets[0]: regcred
frontend.nginx.clientHeaderBufferSize: 16k
frontend.nginx.largeClientHeaderBuffers: 8 32k
frontend.port: 3000
frontend.replicas: 1
frontend.resources.limits.cpu: 200m
frontend.resources.limits.memory: 128Mi
frontend.resources.requests.cpu: 50m
frontend.resources.requests.memory: 64Mi
frontend.tag: 2026.11.13-7762fc7-stage
inputWorker.env.NATIVE_THUMBNAIL_MEMORY_MIB: 16384
inputWorker.env.NATIVE_THUMBNAIL_WORKERS: 16
inputWorker.replicas: 4
inputWorker.resources.limits.cpu: 8
inputWorker.resources.limits.memory: 24Gi
inputWorker.resources.requests.cpu: 4
inputWorker.resources.requests.memory: 16Gi
namePrefix: defect-studio
virtualService.apiPath: /defect/api
virtualService.authPath: /auth
virtualService.authService: dice-stage-platform-web-auth.dice-stage.svc.cluster.local
virtualService.authServicePort: 3020
virtualService.enabled: true
virtualService.gateways[0]: istio-system/platform-gateway
virtualService.hosts[0]: stage.gtrai.sec.samsung.net
virtualService.name: defect-studio-stage
virtualService.redirectHttpToHttps: false
virtualService.uiPath: /defect

