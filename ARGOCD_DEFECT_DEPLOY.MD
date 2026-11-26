1. argocd-defect-prod

SUMMARY
DEFECT-PROD

PROJECT: dice
ANNOTATIONS: kubectl.kubernetes.io/last-applied-configuration={"apiVersion":"argoproj.io/v1alpha1","kind":"Application","metadata":{"annotations":{},"finalizers":["resources-finalizer.argocd.argoproj.io"],"name":"defect-prod","namespace":"argocd"},"spec":{"destination":{"namespace":"dice","server":"https://kubernetes.default.svc"},"project":"dice","source":{"helm":{"releaseName":"defect-studio","valueFiles":["../../environments/production/defect-studio.yaml"]},"path":"charts/defect-studio","repoURL":"https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git","targetRevision":"main"},"syncPolicy":{"syncOptions":["CreateNamespace=false"]}}}
CLUSTER: in-cluster (https://kubernetes.default.svc)
NAMESPACE: dice   
CREATED AT: 11/09/2026 18:28:08 (16 days ago)
REPO URL: https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git
TARGET REVISION: main
PATH: charts/defect-studio
SYNC OPTIONS: CreateNamespace
RETRY OPTIONS: Retry disabled
STATUS: OutOfSync from main (24fc482)
HEALTH: Healthy
LINKS
IMAGES: 
dice-docker-local.bart.sec.samsung.net/defect-studio-backend:v1.1.0
dice-docker-local.bart.sec.samsung.net/defect-studio-frontend:v1.1.0
docker-remote.bart.sec.samsung.net/apache/kafka-native:3.9.2
docker-remote.bart.sec.samsung.net/istio/proxyv2:1.24.2
docker-remote.bart.sec.samsung.net/postgres:16-alpine
docker-remote.bart.sec.samsung.net/rabbitmq:3.13-management-alpine
docker-remote.bart.sec.samsung.net/temporalio/auto-setup:1.25.2
docker-remote.bart.sec.samsung.net/temporalio/ui:2.31.2

PARAMETERS:
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
backend.env.AGENT_SERVICE_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-defect-agent
backend.env.CORS_ORIGINS: []
backend.env.DEPLOYMENT_ENV: production
backend.env.HTTPS_PROXY: http://168.219.61.252:8080
backend.env.MAX_CONCURRENT_RUNS: 7
backend.env.MAX_CONCURRENT_TRAININGS: 7
backend.env.MESSAGING_ENABLED: true
backend.env.MINIO_BUCKET: defect-agent
backend.env.MINIO_ENDPOINT: s3.ap-northeast-2.samsungspc.com
backend.env.MINIO_SECURE: true
backend.env.MINIO_VERIFY_SSL: false
backend.env.NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.cluster.local,s3.ap-northeast-2.samsungspc.com,mlp-service.n10.sr-cloud.com
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
backend.tag: v1.1.0
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
frontend.tag: v1.1.0
inputWorker.enabled: false
inputWorker.replicas: 1
inputWorker.resources.limits.cpu: 2
inputWorker.resources.limits.memory: 2Gi
inputWorker.resources.requests.cpu: 500m
inputWorker.resources.requests.memory: 512Mi
kafka.clusterId: MkU3OEVBNTcwNTJENDM2Qk
kafka.enabled: true
kafka.heapOpts: -Xms384m -Xmx512m
kafka.image: docker-remote.bart.sec.samsung.net/apache/kafka-native
kafka.numPartitions: 3
kafka.persistence.enabled: true
kafka.persistence.size: 10Gi
kafka.persistence.storageClass: nfs-csi
kafka.port: 9092
kafka.replicas: 1
kafka.resources.limits.cpu: 1
kafka.resources.limits.memory: 1536Mi
kafka.resources.requests.cpu: 250m
kafka.resources.requests.memory: 768Mi
kafka.tag: 3.9.2
namePrefix: defect-studio
pipelineWorker.enabled: true
pipelineWorker.env.RABBITMQ_IMAGE_PREP_PREFETCH: 8
pipelineWorker.replicasl 2
pipelineWorker.resources.limits.cpu: 4
pipelineWorker.resources.limits.memory: 4Gi
pipelineWorker.resources.requests.cpu: 1
pipelineWorker.resources.requests.memory: 2Gi
rabbitmq.enabled: true
rabbitmq.image: docker-remote.bart.sec.samsung.net/rabbitmq
rabbitmq.managementPort: 15672
rabbitmq.persistence.enabled: true
rabbitmq.persistence.size: 5Gi
rabbitmq.persistence.storageClass: nfs-csi
rabbitmq.port: 5672
rabbitmq.replicas: 1
rabbitmq.resources.limits.cpu: 2
rabbitmq.resources.limits.memory: 1Gi
rabbitmq.resources.requests.cpu: 200m
rabbitmq.resources.requests.memory: 512Mi
rabbitmq.tag: 3.13-management-alpine
rabbitmq.user: defect
rabbitmq.vhost: /
temporal.enabled: true
temporal.exposeGrpc: true
temporal.image: docker-remote.bart.sec.samsung.net/temporalio/auto-setup
temporal.namespace: default
temporal.port: 7233
temporal.postgres.image: docker-remote.bart.sec.samsung.net/postgres
temporal.postgres.persistence.enabled: true
temporal.postgres.persistence.size: 5Gi
temporal.postgres.persistence.storageClass: nfs-csi
temporal.postgres.resources.limits.cpu: 1
temporal.postgres.resources.limits.memory: 512Mi
temporal.postgres.resources.requests.cpu: 100m
temporal.postgres.resources.requests.memory: 256Mi
temporal.postgres.tag: 16-alpine
temporal.postgres.user: temporal
temporal.replicas: 1
temporal.resources.limits.cpu: 2
temporal.resources.limits.memory: 1536Mi
temporal.resources.requests.cpu: 250m
temporal.resources.requests.memory: 512Mi
temporal.retention: 7d
temporal.slotCoordinator.enabled: true
temporal.slotCoordinator.host: defect-studio-temporal.dice-stage.svc.cluster.local:7233
temporal.slotCoordinator.namespace: default
temporal.slotCoordinator.tls: false
temporal.tag: 1.25.2
temporal.ui.enabled: true
temporal.ui.image: docker-remote.bart.sec.samsung.net/temporalio/ui
temporal.ui.port: 8080
temporal.ui.resources.limits.cpu: 500m
temporal.ui.resources.limits.memory: 256Mi
temporal.ui.resources.requests.cpu: 50m
temporal.ui.resources.requests.memory: 128Mi
temporal.ui.tag: 2.31.2
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

MANIFEST
project: dice
source:
  repoURL: >-
    https://github.sec.samsung.net/GT8-AutomationVision/argocd-application-repository.git
  path: charts/defect-studio
  targetRevision: main
  helm:
    valueFiles:
      - ../../environments/production/defect-studio.yaml
    releaseName: defect-studio
destination:
  server: 'https://kubernetes.default.svc'
  namespace: dice
syncPolicy:
  syncOptions:
    - CreateNamespace=false


defect-studio-backend
KIND: Deployment
NAME: defect-studio-backend   
NAMESPACE: dice   
CREATED AT: 11/09/2026 18:36:46 (16 days ago)
STATUS: OutOfSync
HEALTH: Healthy
LINKS

LIVE MANIFEST:
piVersion: apps/v1
kind: Deployment
metadata:
  annotations:
    deployment.kubernetes.io/revision: '8'
    kubectl.kubernetes.io/last-applied-configuration: >
      {"apiVersion":"apps/v1","kind":"Deployment","metadata":{"annotations":{},"labels":{"app.kubernetes.io/component":"backend","app.kubernetes.io/name":"defect-studio","argocd.argoproj.io/instance":"defect-prod"},"name":"defect-studio-backend","namespace":"dice"},"spec":{"replicas":1,"selector":{"matchLabels":{"app.kubernetes.io/component":"backend","app.kubernetes.io/name":"defect-studio"}},"strategy":{"type":"Recreate"},"template":{"metadata":{"labels":{"app.kubernetes.io/component":"backend","app.kubernetes.io/name":"defect-studio"}},"spec":{"containers":[{"env":[{"name":"SSO_ENABLED","value":"true"},{"name":"PASSWORD_REGISTRATION_ENABLED","value":"false"},{"name":"AGENT_SERVICE_BASE_URL","value":"https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-defect-agent"},{"name":"CORS_ORIGINS","value":"[]"},{"name":"DEPLOYMENT_ENV","value":"production"},{"name":"HTTPS_PROXY","value":"http://168.219.61.252:8080"},{"name":"MAX_CONCURRENT_RUNS","value":"7"},{"name":"MAX_CONCURRENT_TRAININGS","value":"7"},{"name":"MESSAGING_ENABLED","value":"true"},{"name":"MINIO_BUCKET","value":"defect-agent"},{"name":"MINIO_ENDPOINT","value":"gage.ap-northeast-2.samsungspc.com"},{"name":"MINIO_SECURE","value":"true"},{"name":"MINIO_VERIFY_SSL","value":"false"},{"name":"NO_PROXY","value":"localhost,127.0.0.1,.svc,.svc.cluster.local,.cluster.local,gage.ap-northeast-2.samsungspc.com,mlp-service.n10.sr-cloud.com"},{"name":"STORAGE_ALLOW_LOCAL_FALLBACK","value":"false"},{"name":"TEMPORAL_HOST","value":"defect-studio-temporal.dice.svc.cluster.local:7233"},{"name":"TEMPORAL_NAMESPACE","value":"default"},{"name":"TEMPORAL_SLOT_ENABLED","value":"true"},{"name":"TEMPORAL_SLOT_HOST","value":"defect-studio-temporal.dice-stage.svc.cluster.local:7233"},{"name":"TEMPORAL_SLOT_NAMESPACE","value":"default"},{"name":"TEMPORAL_SLOT_TLS","value":"false"},{"name":"RABBITMQ_HOST","value":"defect-studio-rabbitmq.dice.svc.cluster.local"},{"name":"RABBITMQ_PORT","value":"5672"},{"name":"RABBITMQ_USER","value":"defect"},{"name":"RABBITMQ_VHOST","value":"/"},{"name":"RABBITMQ_PASSWORD","valueFrom":{"secretKeyRef":{"key":"service-jwt-secret","name":"defect-studio-prod-secrets"}}},{"name":"KAFKA_BOOTSTRAP_SERVERS","value":"defect-studio-kafka.dice.svc.cluster.local:9092"},{"name":"DATABASE_URL","valueFrom":{"secretKeyRef":{"key":"database-url","name":"defect-studio-prod-secrets"}}},{"name":"SERVICE_JWT_SECRET","valueFrom":{"secretKeyRef":{"key":"service-jwt-secret","name":"defect-studio-prod-secrets"}}},{"name":"SECRET_KEY","valueFrom":{"secretKeyRef":{"key":"secret-key","name":"defect-studio-prod-secrets"}}},{"name":"MINIO_ACCESS_KEY","valueFrom":{"secretKeyRef":{"key":"s3-access-key","name":"defect-studio-prod-secrets"}}},{"name":"MINIO_SECRET_KEY","valueFrom":{"secretKeyRef":{"key":"s3-secret-key","name":"defect-studio-prod-secrets"}}}],"image":"dice-docker-local.bart.sec.samsung.net/defect-studio-backend:v1.1.0","imagePullPolicy":"IfNotPresent","livenessProbe":{"httpGet":{"path":"/api/health","port":"http"},"periodSeconds":30},"name":"backend","ports":[{"containerPort":8080,"name":"http"}],"readinessProbe":{"httpGet":{"path":"/api/health","port":"http"},"periodSeconds":10},"resources":{"limits":{"cpu":"1","memory":"4Gi"},"requests":{"cpu":"250m","memory":"2Gi"}},"startupProbe":{"failureThreshold":60,"httpGet":{"path":"/api/health","port":"http"},"periodSeconds":5}}],"imagePullSecrets":[{"name":"regcred"}],"initContainers":[{"command":["sh","-c","cd
      /app \u0026\u0026 alembic upgrade
      head"],"env":[{"name":"DATABASE_URL","valueFrom":{"secretKeyRef":{"key":"database-url","name":"defect-studio-prod-secrets"}}}],"image":"dice-docker-local.bart.sec.samsung.net/defect-studio-backend:v1.1.0","imagePullPolicy":"IfNotPresent","name":"db-migrate","resources":{"limits":{"cpu":"500m","memory":"256Mi"},"requests":{"cpu":"100m","memory":"128Mi"}}}]}}}}
  creationTimestamp: '2026-11-09T09:36:46Z'
  generation: 8
  labels:
    app.kubernetes.io/component: backend
    app.kubernetes.io/name: defect-studio
    argocd.argoproj.io/instance: defect-prod
  name: defect-studio-backend
  namespace: dice
  resourceVersion: '550699541'
  uid: a2932485-95c2-4add-bfaa-8697a8000086
spec:
  progressDeadlineSeconds: 600
  replicas: 1
  revisionHistoryLimit: 10
  selector:
    matchLabels:
      app.kubernetes.io/component: backend
      app.kubernetes.io/name: defect-studio
  strategy:
    type: Recreate
  template:
    metadata:
      creationTimestamp: null
      labels:
        app.kubernetes.io/component: backend
        app.kubernetes.io/name: defect-studio
    spec:
      containers:
        - env:
            - name: SSO_ENABLED
              value: 'true'
            - name: PASSWORD_REGISTRATION_ENABLED
              value: 'false'
            - name: AGENT_SERVICE_BASE_URL
              value: >-
                https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-defect-agent
            - name: CORS_ORIGINS
              value: '[]'
            - name: DEPLOYMENT_ENV
              value: production
            - name: HTTPS_PROXY
              value: 'http://168.219.61.252:8080'
            - name: MAX_CONCURRENT_RUNS
              value: '7'
            - name: MAX_CONCURRENT_TRAININGS
              value: '7'
            - name: MESSAGING_ENABLED
              value: 'true'
            - name: MINIO_BUCKET
              value: defect-agent
            - name: MINIO_ENDPOINT
              value: gage.ap-northeast-2.samsungspc.com
            - name: MINIO_SECURE
              value: 'true'
            - name: MINIO_VERIFY_SSL
              value: 'false'
            - name: NO_PROXY
              value: >-
                localhost,127.0.0.1,.svc,.svc.cluster.local,.cluster.local,gage.ap-northeast-2.samsungspc.com,mlp-service.n10.sr-cloud.com
            - name: STORAGE_ALLOW_LOCAL_FALLBACK
              value: 'false'
            - name: TEMPORAL_HOST
              value: 'defect-studio-temporal.dice.svc.cluster.local:7233'
            - name: TEMPORAL_NAMESPACE
              value: default
            - name: TEMPORAL_SLOT_ENABLED
              value: 'true'
            - name: TEMPORAL_SLOT_HOST
              value: 'defect-studio-temporal.dice-stage.svc.cluster.local:7233'
            - name: TEMPORAL_SLOT_NAMESPACE
              value: default
            - name: TEMPORAL_SLOT_TLS
              value: 'false'
            - name: RABBITMQ_HOST
              value: defect-studio-rabbitmq.dice.svc.cluster.local
            - name: RABBITMQ_PORT
              value: '5672'
            - name: RABBITMQ_USER
              value: defect
            - name: RABBITMQ_VHOST
              value: /
            - name: RABBITMQ_PASSWORD
              valueFrom:
                secretKeyRef:
                  key: service-jwt-secret
                  name: defect-studio-prod-secrets
            - name: KAFKA_BOOTSTRAP_SERVERS
              value: 'defect-studio-kafka.dice.svc.cluster.local:9092'
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  key: database-url
                  name: defect-studio-prod-secrets
            - name: SERVICE_JWT_SECRET
              valueFrom:
                secretKeyRef:
                  key: service-jwt-secret
                  name: defect-studio-prod-secrets
            - name: SECRET_KEY
              valueFrom:
                secretKeyRef:
                  key: secret-key
                  name: defect-studio-prod-secrets
            - name: MINIO_ACCESS_KEY
              valueFrom:
                secretKeyRef:
                  key: s3-access-key
                  name: defect-studio-prod-secrets
            - name: MINIO_SECRET_KEY
              valueFrom:
                secretKeyRef:
                  key: s3-secret-key
                  name: defect-studio-prod-secrets
          image: 'dice-docker-local.bart.sec.samsung.net/defect-studio-backend:v1.1.0'
          imagePullPolicy: IfNotPresent
          livenessProbe:
            failureThreshold: 3
            httpGet:
              path: /api/health
              port: http
              scheme: HTTP
            periodSeconds: 30
            successThreshold: 1
            timeoutSeconds: 1
          name: backend
          ports:
            - containerPort: 8080
              name: http
              protocol: TCP
          readinessProbe:
            failureThreshold: 3
            httpGet:
              path: /api/health
              port: http
              scheme: HTTP
            periodSeconds: 10
            successThreshold: 1
            timeoutSeconds: 1
          resources:
            limits:
              cpu: '1'
              memory: 4Gi
            requests:
              cpu: 250m
              memory: 2Gi
          startupProbe:
            failureThreshold: 60
            httpGet:
              path: /api/health
              port: http
              scheme: HTTP
            periodSeconds: 5
            successThreshold: 1
            timeoutSeconds: 1
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
      dnsPolicy: ClusterFirst
      imagePullSecrets:
        - name: regcred
      initContainers:
        - command:
            - sh
            - '-c'
            - cd /app && alembic upgrade head
          env:
            - name: DATABASE_URL
              valueFrom:
                secretKeyRef:
                  key: database-url
                  name: defect-studio-prod-secrets
          image: 'dice-docker-local.bart.sec.samsung.net/defect-studio-backend:v1.1.0'
          imagePullPolicy: IfNotPresent
          name: db-migrate
          resources:
            limits:
              cpu: 500m
              memory: 256Mi
            requests:
              cpu: 100m
              memory: 128Mi
          terminationMessagePath: /dev/termination-log
          terminationMessagePolicy: File
      restartPolicy: Always
      schedulerName: default-scheduler
      securityContext: {}
      terminationGracePeriodSeconds: 30
status:
  availableReplicas: 1
  conditions:
    - lastTransitionTime: '2026-11-19T06:17:31Z'
      lastUpdateTime: '2026-11-19T06:17:31Z'
      message: Deployment has minimum availability.
      reason: MinimumReplicasAvailable
      status: 'True'
      type: Available
    - lastTransitionTime: '2026-11-09T09:36:46Z'
      lastUpdateTime: '2026-11-19T06:17:31Z'
      message: >-
        ReplicaSet "defect-studio-backend-7c7fbbf76d" has successfully
        progressed.
      reason: NewReplicaSetAvailable
      status: 'True'
      type: Progressing
  observedGeneration: 8
  readyReplicas: 1
  replicas: 1
  updatedReplicas: 1


defect-studio-frontend
KIND: Service
NAME: defect-studio-frontend   
NAMESPACE: dice   
CREATED AT: 11/09/2026 18:36:46 (16 days ago)
TYPE: ClusterIP
HOSTNAMES: 
STATUS: Synced
HEALTH: Healthy
LINKS


apiVersion: v1
kind: Service
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: >
      {"apiVersion":"v1","kind":"Service","metadata":{"annotations":{},"labels":{"app.kubernetes.io/component":"frontend","app.kubernetes.io/name":"defect-studio","argocd.argoproj.io/instance":"defect-prod"},"name":"defect-studio-frontend","namespace":"dice"},"spec":{"ports":[{"name":"http","port":3000,"targetPort":"http"}],"selector":{"app.kubernetes.io/component":"frontend","app.kubernetes.io/name":"defect-studio"}}}
  creationTimestamp: '2026-11-09T09:36:46Z'
  labels:
    app.kubernetes.io/component: frontend
    app.kubernetes.io/name: defect-studio
    argocd.argoproj.io/instance: defect-prod
  name: defect-studio-frontend
  namespace: dice
  resourceVersion: '545729145'
  uid: 65efc9b7-a5de-4488-a7ac-4278e3502185
spec:
  clusterIP: 10.240.194.199
  clusterIPs:
    - 10.240.194.199
  internalTrafficPolicy: Cluster
  ipFamilies:
    - IPv4
  ipFamilyPolicy: SingleStack
  ports:
    - name: http
      port: 3000
      protocol: TCP
      targetPort: http
  selector:
    app.kubernetes.io/component: frontend
    app.kubernetes.io/name: defect-studio
  sessionAffinity: None
  type: ClusterIP
status:
  loadBalancer: {}
