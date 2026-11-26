1. argocd - dice
SUMMARY
DICE

PROJECT: dice
ANNOTATIONS: argocd.argoproj.io/hydrate=normal
CLUSTER: in-cluster (https://kubernetes.default.svc)
NAMESPACE: dice   
CREATED AT: 12/15/2025 18:06:38 (a year ago)
REPO URL: https://github.sec.samsung.net/GT8-AutomationVision/mvp-vision-ai-platform.git
TARGET REVISION: 4838732
PATH: infrastructure/helm/vision-ai-platform
SYNC OPTIONS: 
RETRY OPTIONS: Retry disabled
STATUS: Synced to 483873237ab0b3666302e344b99b47dbe1e82cbb
HEALTH: Healthy
LINKS
IMAGES: 
dice-docker-local.bart.sec.samsung.net/dice-dashboard-backend:2026.11.16-efaa668
dice-docker-local.bart.sec.samsung.net/dice-dashboard-frontend:2026.11.16-efaa668
dice-docker-local.bart.sec.samsung.net/dice-dashboard-mcp-server:2026.10.28-2e98b39
dice-docker-local.bart.sec.samsung.net/dice-docs:2026.11.16-efaa668
dice-docker-local.bart.sec.samsung.net/dice-inference-gateway:2026.11.17-080e900
dice-docker-local.bart.sec.samsung.net/dice-labeler-backend:2026.11.24-9257807
dice-docker-local.bart.sec.samsung.net/dice-labeler-frontend:2026.11.24-ffba750
dice-docker-local.bart.sec.samsung.net/dice-mcp-server:2026.10.23-8c43941
dice-docker-local.bart.sec.samsung.net/dice-platform-backend:2026.11.24-9257807
dice-docker-local.bart.sec.samsung.net/dice-platform-frontend:2026.11.25-1bd2cd5
dice-docker-local.bart.sec.samsung.net/dice-runner:2026.11.18-ff85a53
dice-docker-local.bart.sec.samsung.net/dice-web-auth:2026.11.20-665f3cd
dice-docker-local.bart.sec.samsung.net/space-adapter:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-dice-v1:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-huggingface:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-openmm-cu118:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-openmm-cu128:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-timm:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-ultralytics:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-vfm-v1-cu128:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-vfm-v1:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/trainer-vfm-v3-det-bastion:2026.11.24-b90412ed0
dice-docker-local.bart.sec.samsung.net/vision-dice-bot:2026.10.27-9763699
dice-docker-local.bart.sec.samsung.net/vision-user-service:2026.11.13-9224cee
docker-remote.bart.sec.samsung.net/dpage/pgadmin4:7.7
docker-remote.bart.sec.samsung.net/istio/proxyv2:1.24.2
docker-remote.bart.sec.samsung.net/postgres:15
docker-remote.bart.sec.samsung.net/redis:7.4.3

PARAMETERS
VALUES FILES: No values files selected
VALUES: 
nameOverride: ''
fullnameOverride: ''
redis:
  enabled: true
  connectApplications: true
  image:
    repository: docker-remote.bart.sec.samsung.net/redis
    pullPolicy: IfNotPresent
  maxmemory: 512mb
  resources:


MANIFEST
project: dice
source:
  repoURL: >-
    https://github.sec.samsung.net/GT8-AutomationVision/mvp-vision-ai-platform.git
  path: infrastructure/helm/vision-ai-platform
  targetRevision: 483873237ab0b3666302e344b99b47dbe1e82cbb
  helm:
    parameters:
      - name: platform.backend.image.tag
        value: 2026.11.24-9257807
      - name: platform.frontend.image.tag
        value: 2026.11.25-1bd2cd5
      - name: labeler.backend.image.tag
        value: 2026.11.24-9257807
      - name: labeler.frontend.image.tag
        value: 2026.11.24-ffba750
      - name: labeler.mlService.image.tag
        value: 2026.10.23-4a8ca09
      - name: labeler.sam2UnetService.image.tag
        value: 2026.10.23-4a8ca09
      - name: platform.runner.image.tag
        value: 2026.11.18-ff85a53
      - name: labeler.defectBackend.image.tag
        value: 2026.10.23-4a8ca09
      - name: webAuth.image.tag
        value: 2026.11.20-665f3cd
      - name: docs.image.tag
        value: 2026.11.16-efaa668
      - name: platform.training.frameworks.ultralytics.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.huggingface.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.vfm-v1.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.timm.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.space.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.openmm-cu118.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.openmm-cu128.image_tag
        value: 2026.11.24-b90412ed0
      - name: diceBot.image.tag
        value: 2026.10.27-9763699
      - name: platform.mcp.image.tag
        value: 2026.10.23-8c43941
      - name: platform.dashboardMcp.image.tag
        value: 2026.10.28-2e98b39
      - name: platform.training.frameworks.dice_v1.image_tag
        value: 2026.11.24-b90412ed0
      - name: userService.image.tag
        value: 2026.11.13-9224cee
      - name: dashboard.backend.image.tag
        value: 2026.11.16-efaa668
      - name: dashboard.frontend.image.tag
        value: 2026.11.16-efaa668
      - name: platform.training.frameworks.vfm-v3-det.image_tag
        value: 2026.10.23-a8173dd1
      - name: platform.training.frameworks.vfm-v1-cu128.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.frameworks.vfm-v3-det-bastion.image_tag
        value: 2026.11.24-b90412ed0
      - name: platform.training.imageCache.enabled
        value: 'true'
      - name: platform.training.imageCache.maxUnavailable
        value: 100%
        forceString: true
      - name: dashboard.enabled
        value: 'true'
      - name: platform.training.datasetCache.image.tag
        value: 2026.11.13-251d245
      - name: platform.training.datasetCache.discoveryIntervalSeconds
        value: '1800'
      - name: autoLabeling.gpuUuid
        value: GPU-7c0f296f-134a-c43a-5355-6242cb119539
      - name: 'sharedInference.artifactAllowedOrigins[0]'
        value: 'https://s3.ap-northeast-2.samsungspc.com'
      - name: sharedInference.enableMaskAnnotations
        value: 'true'
      - name: sharedInference.enabled
        value: 'true'
      - name: sharedInference.environments.ultralytics-autolabel-cu124-v1.arch
        value: x86_64
      - name: >-
          sharedInference.environments.ultralytics-autolabel-cu124-v1.bundle_sha256
        value: 499f12be4332fba2ee1a922926e6b9bb2f149909abad9d4bd32250ddd89cc285
      - name: sharedInference.environments.ultralytics-autolabel-cu124-v1.cuda
        value: cu124
      - name: sharedInference.environments.ultralytics-autolabel-cu124-v1.os
        value: linux
      - name: sharedInference.environments.ultralytics-autolabel-cu124-v1.version
        value: 2026.10.12-ort1232-v1
      - name: sharedInference.image.tag
        value: 2026.11.17-080e900
      - name: sharedInference.managedBudgetBytes
        value: '4294967296'
      - name: sharedInference.modelBindings.499.environment_alias
        value: ultralytics-autolabel-cu124-v1
      - name: sharedInference.modelBindings.499.required_vram_bytes
        value: '1073741824'
      - name: sharedInference.modelBindings.499.runtime_format
        value: onnx
      - name: autoLabeling.slotId
        value: runner-production-0
      - name: sharedInference.modelBindings.601.environment_alias
        value: ultralytics-autolabel-cu124-v1
      - name: sharedInference.modelBindings.601.runtime_format
        value: onnx
      - name: sharedInference.modelBindings.601.required_vram_bytes
        value: '3221225472'
      - name: sharedInference.nativeOnnxEnabled
        value: 'true'
    values: |+
      nameOverride: ''
      fullnameOverride: ''
      redis:
        enabled: true
        connectApplications: true
        image:
          repository: docker-remote.bart.sec.samsung.net/redis
          pullPolicy: IfNotPresent
        maxmemory: 512mb
        resources:
          requests:
            cpu: 100m
            memory: 128Mi
          limits:
            cpu: '1'
            memory: 1Gi
        persistence:
          enabled: true
          storageClass: nfs-csi
          size: 10Gi
        networkPolicy:
          enabled: true
        databases:
          platform: 0
          labeler: 1
          mlService: 0
          sam2UnetService: 0
        nodeSelector:
          kubernetes.io/hostname: node1
      webAuth:
        enabled: true
        replicaCount: 1
        image:
          repository: dice-docker-local.bart.sec.samsung.net/dice-web-auth
          pullPolicy: IfNotPresent
        imagePullSecrets:
        - name: regcred
        serviceAccount:
          create: true
          name: ''
        podSecurityContext:
          fsGroup: 1001
        securityContext:
          runAsNonRoot: true
          runAsUser: 1001
          runAsGroup: 1001
          allowPrivilegeEscalation: false
        service:
          type: ClusterIP
          port: 3020
          targetPort: 3020
        ingress:
          enabled: false
          className: nginx
        resources:
          limits:
            cpu: 300m
            memory: 384Mi
          requests:
            cpu: 50m
            memory: 128Mi
        livenessProbe:
          httpGet:
            path: /api/auth/session
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/auth/session
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        env:
          NEXT_PUBLIC_BASE_PATH: /
          NEXT_PUBLIC_AUTH_DEFAULT_CALLBACK_URL: /
          NEXTAUTH_URL: https://dice.gtrai.sec.samsung.net/api/auth
          AUTH_DEFAULT_CALLBACK_URL: /
          AUTH_ALLOWED_CALLBACK_PREFIXES: /,/platform,/labeler,/defect,/docs,/activation
          ADFS_CLIENT_ID: 00c7203f-9213-4f0f-971a-ac5bac3d6ee3
          ADFS_ISSUER: https://sts.secsso.net/adfs
          ADFS_ISSUER_INTERNAL: https://sts.secsso.net/adfs
          SERVICE_JWT_SECRET:
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: service-jwt
          S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
          S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
          S3_ACCESS_KEY:
            valueFrom:
              secretKeyRef:
                name: dice-s3
                key: access-key
          S3_SECRET_KEY:
            valueFrom:
              secretKeyRef:
                name: dice-s3
                key: secret-key
          S3_BUCKET: cosmo-storage-develop
          S3_REGION: auto
          RUNNER_RELEASE_STORAGE_PREFIX: runner-releases/windows
          RUNNER_ENV_STORAGE_PREFIX: runner-envs/linux
          RUNNER_ENV_PRESIGN_EXPIRE_SECONDS: '3600'
          AUTH_ALLOWED_CALLBACK_ORIGINS: https://dice.gtrai.sec.samsung.net
          ACTIVATION_DB_HOST: dice-platform-database.dice.svc.cluster.local
          ACTIVATION_DB_PORT: '5432'
          ACTIVATION_DB_NAME: activation
          ACTIVATION_AES_KEY:
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: activation-aes-key
          DICE_BOT_ACTIVATION_TOKEN:
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: DICE_BOT_ACTIVATION_TOKEN
        secretEnv:
        - name: NEXTAUTH_SECRET
          secretName: vision-ai-secrets
          secretKey: web-auth-nextauth-secret
        - name: ADFS_CLIENT_SECRET
          secretName: vision-ai-secrets
          secretKey: web-auth-adfs-client-secret
        - name: ACTIVATION_DB_USER
          secretName: dice-database
          secretKey: postgres-user
        - name: ACTIVATION_DB_PASSWORD
          secretName: dice-database
          secretKey: postgres-password
      docs:
        enabled: true
        replicaCount: 1
        image:
          repository: dice-docker-local.bart.sec.samsung.net/dice-docs
          pullPolicy: IfNotPresent
        imagePullSecrets:
        - name: regcred
        service:
          type: ClusterIP
          port: 3030
          targetPort: 3030
        livenessProbe:
          httpGet:
            path: /docs/ko
            port: http
          initialDelaySeconds: 15
          periodSeconds: 10
          timeoutSeconds: 3
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /docs/ko
            port: http
          initialDelaySeconds: 5
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          limits:
            cpu: 300m
            memory: 384Mi
          requests:
            cpu: 50m
            memory: 128Mi
      platform:
        mcp:
          enabled: true
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-mcp-server
            pullPolicy: IfNotPresent
          imagePullSecrets:
          - name: regcred
          service:
            type: ClusterIP
            port: 8080
            targetPort: 8080
          basePath: /platform/mcp
          env:
            DICE_API_URL: ''
            DICE_API_PREFIX: /platform/api/v1
            NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.gtrai.sec.samsung.net
          ingress:
            enabled: false
            className: nginx
            annotations: {}
            hosts:
            - host: mcp.vision-ai.local
              paths:
              - path: /platform/mcp
                pathType: Prefix
            tls: []
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
          nodeSelector: {}
        dashboardMcp:
          enabled: true
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-mcp-server
            pullPolicy: IfNotPresent
          service:
            type: ClusterIP
            port: 8080
            targetPort: 8080
          basePath: /mcp/dashboard
          env:
            DICE_API_PREFIX: /platform/api/v1
            NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.gtrai.sec.samsung.net
          ingress:
            enabled: false
            className: nginx
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 20
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 5
            periodSeconds: 10
          resources:
            requests:
              cpu: 100m
              memory: 128Mi
            limits:
              cpu: 500m
              memory: 256Mi
        backend:
          enabled: true
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-platform-backend
            pullPolicy: IfNotPresent
          imagePullSecrets:
          - name: regcred
          serviceAccount:
            create: true
            name: ''
          rbac:
            create: true
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
          service:
            type: ClusterIP
            port: 8000
            targetPort: 8000
          ingress:
            enabled: false
            className: nginx
          resources:
            limits:
              cpu: 2000m
              memory: 2Gi
            requests:
              cpu: 1000m
              memory: 1Gi
          autoscaling:
            enabled: false
            minReplicas: 1
            maxReplicas: 5
            targetCPUUtilizationPercentage: 80
            targetMemoryUtilizationPercentage: 80
          env:
            LLM_PROVIDER: openai
            OPENAI_API_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: platform-backend-openai-api-key
            OPENAI_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
            LLM_MODEL: qwen/qwen3.8-flash-next
            DASHBOARD_AGENT_LLM_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
            DASHBOARD_AGENT_LLM_API_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: dashboard-agent-llm-api-key
            DASHBOARD_AGENT_LLM_MODEL: qwen/qwen3.8-flash-next
            DATABASE_URL:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: platform-database-url
            USER_DATABASE_URL:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: user-database-url
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
            BACKEND_PORT: '8000'
            API_V1_PREFIX: /platform/api/v1
            API_BASE_URL: http://dice-platform-backend.dice.svc.cluster.local:8000
            CORS_ORIGINS: https://dice.gtrai.sec.samsung.net,http://dice.gtrai.sec.samsung.net
            FRONTEND_URL: https://dice.gtrai.sec.samsung.net
            TRAINING_MODE: kubernetes
            USE_UV: 'false'
            USER_SERVICE_API_URL: http://dice-platform-user-service.dice.svc.cluster.local/user/api/v1
            S3_BUCKET: cosmo-storage-develop
            S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
            S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
            S3_ACCESS_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: access-key
            S3_SECRET_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: secret-key
            S3_REGION: auto
            S3_USE_SSL: 'true'
            JWT_SECRET:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: jwt
            JWT_ALGORITHM: HS256
            ACCESS_TOKEN_EXPIRE_MINUTES:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: platform-backend-access-token-expire-minutes
            REFRESH_TOKEN_EXPIRE_DAYS:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: platform-backend-refresh-token-expire-days
            SERVICE_JWT_SECRET:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: service-jwt
            LABELER_API_URL: http://dice-labeler-backend.dice.svc.cluster.local:8001
            PADDLEOCR_INFERENCE_TIMEOUT_SECONDS: '3600'
            ACTIVATION_DATABASE_URL:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: platform-backend-activation-database-url
            LOG_LEVEL: INFO
            LOG_FORMAT: json
            DEBUG: 'False'
            ENVIRONMENT: production
            USE_GPU: 'true'
            CUDA_VISIBLE_DEVICES: '0'
            K8S_GPU_COUNT: '1'
            K8S_MEMORY_LIMIT: 16Gi
            K8S_MEMORY_REQUEST: 8Gi
            K8S_CPU_LIMIT: '4'
            K8S_CPU_REQUEST: '2'
            AGENT_JWT_ALGORITHM: HS256
            AGENT_JWT_EXPIRE_HOURS: '24'
            AGENT_RUNTIME_BUNDLE_PREFIX: agent-runtimes
            AGENT_INSTALLER_VERSION: ''
            RUNNER_ENV_STORAGE_PREFIX: runner-envs/linux
            RUNNER_ENV_PRESIGN_EXPIRE_SECONDS: '3600'
            RUNNER_ENV_API_TOKEN:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: runner-env-token
            PROMETHEUS_URL: http://prometheus.prometheus.svc.cluster.local:9090
            PROMETHEUS_TIMEOUT_SECONDS: '15'
            TRAINING_DIAGNOSTICS_ENABLED: 'true'
            DICE_INFERENCE_GATEWAY_URL: https://dice.gtrai.sec.samsung.net/v1
            DICE_INFERENCE_SERVICE_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-inference-gateway
                  key: api-key
            DICE_JEV_MODEL: jev/jev-9b
            DICE_JEV_ENABLED: 'true'
            AGENT_EXECUTION_MODE: embedded
          livenessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 30
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /health
              port: http
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          persistence:
            enabled: false
            size: 10Gi
        frontend:
          enabled: true
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-platform-frontend
            pullPolicy: IfNotPresent
          imagePullSecrets:
          - name: regcred
          serviceAccount:
            create: true
            name: ''
          podSecurityContext:
            fsGroup: 101
          securityContext:
            runAsNonRoot: true
            runAsUser: 101
            runAsGroup: 101
            allowPrivilegeEscalation: false
          service:
            type: ClusterIP
            port: 3000
            targetPort: 3000
          ingress:
            enabled: false
            className: nginx
            annotations:
              nginx.ingress.kubernetes.io:
                proxy-body-size: 50m
          resources:
            limits:
              cpu: 4
              memory: 4Gi
            requests:
              cpu: 2
              memory: 1Gi
          livenessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /healthz
              port: http
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          autoscaling:
            enabled: false
            minReplicas: 1
            maxReplicas: 5
            targetCPUUtilizationPercentage: 70
            targetMemoryUtilizationPercentage: 80
          env:
            NEXT_PUBLIC_API_URL: /platform/api/v1
            NEXT_PUBLIC_LABELER_FRONTEND_URL: /labeler
            NEXT_PUBLIC_BASE_PATH: /platform
            NEXT_PUBLIC_USER_API_URL: /user/api/v1
        runner:
          enabled: true
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-runner
            pullPolicy: IfNotPresent
          command: []
          args: []
          imagePullSecrets:
          - name: regcred
          hostPID: true
          podSecurityContext:
            fsGroup: 1000
            fsGroupChangePolicy: OnRootMismatch
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            runAsGroup: 1000
            allowPrivilegeEscalation: false
          service:
            type: ClusterIP
            inferencePort: 8080
            inferenceTargetPort: 5002
            managementPort: 8081
            managementTargetPort: 8081
          tolerations:
          - key: nvidia.com/gpu
            operator: Exists
            effect: NoSchedule
          - key: dedicated
            operator: Equal
            value: llm
            effect: NoSchedule
          nodeSelector:
            accelerator: null
            kubernetes.io/hostname: node2
          resources:
            requests:
              cpu: '16'
              memory: 32Gi
              nvidia.com/gpu: '1'
            limits:
              cpu: '16'
              memory: 32Gi
              nvidia.com/gpu: '1'
          env:
            NVIDIA_DRIVER_CAPABILITIES: compute,utility
          extraEnv:
          - name: TS_PLATFORM_API_TOKEN
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: runner-platform-api-token
          config:
            create: true
            existingConfigMap: ''
            disableTokenAuthorization: true
            enableEnvvarsConfig: true
            enableModelApi: true
            enableEnvApi: true
            basePath: /runner
            modelServerHome: /var/lib/dice
            loadModels: []
            defaultWorkersPerModel: 0
            defaultResponseTimeout: 1200
            defaultStartupTimeout: 1200
            jobQueueSize: 100
            maxRequestSize: '6553500'
            maxResponseSize: '6553500'
            asyncLogging: true
            metricsMode: prometheus
            systemMetricsIntervalSecs: 10
            metricsArchiveEnabled: true
            metricsArchiveIntervalSecs: 5
            metricsArchiveRetentionDays: 7
            numberOfGpu: 1
            pythonEnvs:
              default: python3
            extraToml: ''
            platformApiUrl: http://dice-platform-backend.dice.svc.cluster.local:8000/platform/api/v1
          storage:
            sizeLimit: 50Gi
            subPaths:
              models: models
              envs: envs
              logs: logs
            persistence:
              enabled: true
              storageClass: nfs-csi
              size: 500Gi
              accessModes:
              - ReadWriteMany
          livenessProbe:
            httpGet:
              path: /runner/api/ping
              port: inference
            initialDelaySeconds: 90
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 3
          startupProbe:
            httpGet:
              path: /runner/api/ping
              port: inference
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 120
          readinessProbe:
            httpGet:
              path: /runner/api/ping
              port: inference
            initialDelaySeconds: 60
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          extraVolumes: []
          extraVolumeMounts: []
        training:
          datasetCache:
            job:
              activeDeadlineSeconds: 259200
          enabled: true
          namespace: dice
          istio:
            inject: false
          registry:
            url: dice-docker-local.bart.sec.samsung.net
            pullSecret: regcred
          serviceAccount:
            create: true
            name: ''
          rbac:
            create: true
          job:
            backoffLimit: 0
            ttlSecondsAfterFinished: 600
            activeDeadlineSeconds: '1296000'
          resources:
            defaults:
              cpu:
                request: '4'
                limit: '8'
              memory:
                request: 16Gi
                limit: 32Gi
              gpu:
                limit: '1'
              shm:
                size: 12Gi
          gpu:
            nodeSelector: null
            tolerations: []
          storage:
            datasets:
              enabled: true
              create: true
              pvcName: datasets-cache-pvc
              storageClass: nfs-csi
              size: 500Gi
              accessModes:
              - ReadWriteMany
              mountPath: /data/datasets
              readOnly: false
              cacheMaxSizeGB: 500
            modelsCache:
              enabled: true
              create: true
              pvcName: models-cache-pvc
              storageClass: nfs-csi
              size: 500Gi
              accessModes:
              - ReadWriteMany
              mountPath: /data/models
          s3:
            enabled: true
            accessKey: ''
          space:
            enabled: true
            adapterImage: ''
            imagePrefix: gtr-ai-vision
            codeBundle:
              enabled: true
              prefix: space-code
              root: /home/user
              presignExpirationSeconds: 604800
            credentials:
              create: false
              existingSecret: dice-space
              secretName: ''
              username: ''
              password: ''
              usernameKey: username
              passwordKey: password
            region: gumi-1
            groupId: GTR-AI-VISION
            groupPoolId: '170'
            quotaId: '155'
            experimentId: '453'
            coreId: '2'
            coreCount: '1'
            expectedRunTime: ''
            createMode: api
            apiBaseUrl: https://mlp.n7.sr-cloud.com
            configPath: ''
            inputDatasets: '[]'
            enabledRunFeatures: '[]'
            allowSpot: 'false'
            emailNoticeCode: '0'
            isSetupRun: 'false'
            runType: batch
            type: oneOff
            cache:
              datasets:
                claimId: datasets-cache-pvc
                mountPath: /data/datasets
                maxSizeGB: '500'
              models:
                claimId: models-cache-pvc
                mountPath: /data/models
            adapterJob:
              gpuLimit: '0'
              cpuRequest: 500m
              cpuLimit: '1'
              memoryRequest: 256Mi
              memoryLimit: 1Gi
              backoffLimit: '0'
              activeDeadlineSeconds: '262800'
            createTimeoutSeconds: '300'
            logReconnectLimit: '5'
            logReconnectBaseDelay: '2.0'
            logReconnectMaxDelay: '30.0'
            stopRetryAttempts: '3'
            stopRetryBaseDelay: '2.0'
            statusQueryRetryAttempts: '3'
            statusQueryRetryBaseDelay: '5.0'
            forwardRawLogs: 'false'
          frameworks:
            ultralytics:
              enabled: true
              image_suffix: trainer-ultralytics
              resources:
                memory:
                  request: 8Gi
                  limit: 16Gi
            huggingface:
              enabled: true
              image_suffix: trainer-huggingface
              resources:
                memory:
                  request: 16Gi
                  limit: 32Gi
              extra_env:
              - name: HF_HOME
                value: /tmp/huggingface
              - name: TRANSFORMERS_CACHE
                value: /tmp/huggingface/transformers
              extra_volumes:
              - name: hf-cache
                emptyDir:
                  sizeLimit: 10Gi
              extra_volume_mounts:
              - name: hf-cache
                mountPath: /tmp/huggingface
            timm:
              enabled: true
              image_suffix: trainer-timm
              resources:
                memory:
                  request: 8Gi
                  limit: 16Gi
            vfm-v1:
              enabled: true
              image_suffix: trainer-vfm-v1
              resources:
                memory:
                  request: 16Gi
                  limit: 32Gi
            dice_v1:
              enabled: true
              image_suffix: trainer-dice-v1
              resources:
                memory:
                  request: 8Gi
                  limit: 16Gi
            openmm-cu118:
              enabled: true
              image_suffix: trainer-openmm-cu118
              resources:
                memory:
                  request: 16Gi
                  limit: 32Gi
            openmm-cu128:
              enabled: true
              image_suffix: trainer-openmm-cu128
              resources:
                memory:
                  request: 16Gi
                  limit: 32Gi
            space:
              enabled: true
              image_suffix: space-adapter
              resources:
                memory:
                  request: 8Gi
                  limit: 16Gi
            custom:
              enabled: true
              resources:
                memory:
                  request: 8Gi
                  limit: 16Gi
          debugPod:
            enabled: false
            image: docker-remote.bart.sec.samsung.net/python
            tag: 3.11-slim
          proxy:
            enabled: true
            httpProxy: http://168.219.61.252:8080
            httpsProxy: http://168.219.61.252:8080
            noProxy: localhost,127.0.0.1,.svc,.svc.cluster.local,.local,.kubernetes.default.svc,10.0.0.0/8,.samsungspc.com,.samsung.net
            disableXet: true
            caCert:
              enabled: true
              useConfigMap: true
              configMapName: digitalcity-cert-cm
              mountPath: /etc/ssl/certs/extra-ca.crt
              key: extra-ca.crt
          podSecurityContext:
            fsGroup: 1000
          securityContext:
            runAsNonRoot: true
            runAsUser: 1000
            allowPrivilegeEscalation: false
      labeler:
        enabled: true
        nameOverride: ''
        fullnameOverride: ''
        backend:
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-backend
          replicas: 1
          port: 8001
          startupProbe:
            path: /health
            initialDelaySeconds: 10
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 60
          livenessProbe:
            path: /health
            initialDelaySeconds: 30
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 5
          readinessProbe:
            path: /health
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 6
          securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          env:
            ENVIRONMENT: development
            DEBUG: 'true'
            LOG_LEVEL: DEBUG
            API_HOST: 0.0.0.0
            API_PORT: '8001'
            API_V1_PREFIX: /labeler/api/v1
            RUN_MIGRATIONS: 'true'
            CORS_ORIGINS: http://localhost:3000,http://dice.gtrai.sec.samsung.net,https://dice.gtrai.sec.samsung.net
            FRONTEND_URL: https://dice.gtrai.sec.samsung.net/labeler
            PLATFORM_DB_HOST: dice-platform-database.dice
            PLATFORM_DB_PORT: '5432'
            PLATFORM_DB_NAME: platform
            PLATFORM_DB_USER:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: postgres-user
            PLATFORM_DB_PASSWORD:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: postgres-password
            LABELER_DB_HOST: dice-platform-database.dice
            LABELER_DB_PORT: '5432'
            LABELER_DB_NAME: labeler
            LABELER_DB_USER:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: postgres-user
            LABELER_DB_PASSWORD:
              valueFrom:
                secretKeyRef:
                  name: dice-database
                  key: postgres-password
            S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
            S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
            S3_ACCESS_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: access-key
            S3_SECRET_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: secret-key
            S3_BUCKET: cosmo-storage-develop
            TRAINING_EXPORT_PREFIX: datasets/training-exports
            S3_REGION: auto
            S3_USE_SSL: 'true'
            SERVICE_JWT_SECRET:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: service-jwt
            SERVICE_JWT_ALGORITHM: HS256
            REALESRGAN_INFERENCE_TIMEOUT_SECONDS: '600'
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
            LARGE_UPLOAD_IMPORT_QUEUE_NAME: dataset-imports
            LARGE_UPLOAD_IMPORT_JOB_TIMEOUT_SECONDS: '43200'
            ANNOTATION_BULK_QUEUE_NAME: annotation-bulk-ops
            ANNOTATION_BULK_JOB_TIMEOUT_SECONDS: '7200'
            ANNOTATION_BULK_JOB_CHUNK_SIZE: '200'
            DB_POOL_SIZE: '10'
            DB_MAX_OVERFLOW: '20'
            DB_POOL_TIMEOUT_SECONDS: '30'
            API_WORKERS: '2'
            REMOTE_DATA_SERVICE_URL: http://data.cosmo.svc.cluster.local:24500
            REMOTE_DATA_S3_BUCKET: cosmo-storage
            USER_SERVICE_API_URL: http://dice-platform-user-service.dice.svc.cluster.local/user/api/v1
            SAM_GATEWAY_ENABLED: 'true'
            SAM_REQUIRED_VRAM_BYTES: '4294967296'
            SAM_MODEL_S3_KEY: 'base/sam3/onnx/v1/sam3-fp16.onnx'
          existingSecret: ''
        importWorker:
          enabled: true
          image:
            repository: ''
            pullPolicy: IfNotPresent
          replicas: 1
          env:
            RUN_MIGRATIONS: 'false'
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
              ephemeral-storage: 20Gi
            limits:
              cpu: '2'
              memory: 4Gi
              ephemeral-storage: 50Gi
        bulkWorker:
          enabled: true
          image:
            repository: ''
            pullPolicy: IfNotPresent
          replicas: 1
          env:
            RUN_MIGRATIONS: 'false'
            DB_POOL_SIZE: '2'
            DB_MAX_OVERFLOW: '2'
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
            ANNOTATION_BULK_QUEUE_NAME: annotation-bulk-ops
            ANNOTATION_BULK_JOB_TIMEOUT_SECONDS: '7200'
            ANNOTATION_BULK_JOB_CHUNK_SIZE: '200'
            DB_POOL_TIMEOUT_SECONDS: '30'
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: '1'
              memory: 1Gi
        publishWorker:
          enabled: true
          image:
            repository: ''
            pullPolicy: IfNotPresent
          replicas: 1
          env:
            RUN_MIGRATIONS: 'false'
            DB_POOL_SIZE: '2'
            DB_MAX_OVERFLOW: '2'
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
            PUBLISH_QUEUE_NAME: version-publish
            PUBLISH_JOB_TIMEOUT_SECONDS: '7200'
            DB_POOL_TIMEOUT_SECONDS: '30'
          resources:
            requests:
              cpu: 200m
              memory: 512Mi
            limits:
              cpu: '1'
              memory: 1Gi
        srBuildWorker:
          enabled: true
          image:
            repository: ''
            pullPolicy: IfNotPresent
          replicas: 1
          env:
            RUN_MIGRATIONS: 'false'
            DB_POOL_SIZE: '2'
            DB_MAX_OVERFLOW: '2'
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
            SUPER_RESOLUTION_BUILD_QUEUE_NAME: super-resolution-builds
            SUPER_RESOLUTION_BUILD_JOB_TIMEOUT_SECONDS: '86400'
            DB_POOL_TIMEOUT_SECONDS: '30'
          resources:
            requests:
              cpu: 500m
              memory: 1Gi
            limits:
              cpu: '2'
              memory: 4Gi
        frontend:
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-frontend
          replicas: 1
          port: 3000
          securityContext:
            runAsUser: 101
            runAsGroup: 101
            fsGroup: 101
          livenessProbe:
            httpGet:
              path: /healthz
              port: 3000
            initialDelaySeconds: 10
            periodSeconds: 10
            timeoutSeconds: 3
            failureThreshold: 3
          readinessProbe:
            httpGet:
              path: /healthz
              port: 3000
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 3
            failureThreshold: 3
          env:
            NEXT_PUBLIC_BASE_PATH: /labeler
            NEXT_PUBLIC_ENABLE_IMAGE_LOCK: 'true'
        defectBackend:
          enabled: true
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-defect-backend
          replicas: 1
          port: 8002
          startupProbe:
            path: /health
            initialDelaySeconds: 5
            periodSeconds: 5
            timeoutSeconds: 5
            failureThreshold: 30
          livenessProbe:
            path: /health
            initialDelaySeconds: 10
            periodSeconds: 30
            timeoutSeconds: 5
            failureThreshold: 5
          readinessProbe:
            path: /health
            initialDelaySeconds: 5
            periodSeconds: 10
            timeoutSeconds: 5
            failureThreshold: 6
          securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          env:
            DEFECT_ENVIRONMENT: production
            DEFECT_LOG_LEVEL: INFO
            DEFECT_API_PORT: '8002'
            DEFECT_API_V1_PREFIX: /defect/api/v1
            DEFECT_GENERATION_MODE: mock
        mlService:
          enabled: true
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-ml-service
          replicas: 1
          port: 8080
          securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          env:
            ENVIRONMENT: production
            LOG_LEVEL: INFO
            HOST: 0.0.0.0
            PORT: '8080'
            SAM2_UNET_CONNECT_TIMEOUT: '5.0'
            SAM2_UNET_READ_TIMEOUT: '30.0'
            SERVICE_JWT_SECRET:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: service-jwt
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
            CB_FAILURE_THRESHOLD: '5'
            CB_RECOVERY_TIMEOUT: '30.0'
            BATCH_WORKER_ENABLED: 'true'
            SAM2_UNET_SERVICE_URL: http://dice-labeler-sam2-unet-service:8080
            SERVICE_JWT_ALGORITHM: HS256
            CALLBACK_URL: http://dice-labeler-backend:8001/api/v1/internal/ai/callback
        sam2UnetService:
          enabled: true
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-sam2-unet-service
          replicas: 1
          port: 8080
          securityContext:
            runAsUser: 1000
            runAsGroup: 1000
            fsGroup: 1000
          resources:
            requests:
              cpu: '2'
              memory: 12Gi
              nvidia.com/gpu: '1'
            limits:
              nvidia.com/gpu: '1'
              cpu: '8'
              memory: 24Gi
          modelVolume:
            enabled: true
            create: true
            claimName: sam2-models
            storageClass: nfs-csi
            size: 20Gi
            accessModes:
            - ReadWriteMany
            annotations: {}
            mountPath: /models
            readOnly: false
          baseModelBootstrap:
            enabled: true
            objectKey: base/sam2_hiera_large.pt
            targetPath: /models/sam2_hiera_large.pt
          env:
            ENVIRONMENT: production
            LOG_LEVEL: INFO
            HOST: 0.0.0.0
            PORT: '8080'
            DEVICE: auto
            SAM2_CHECKPOINT_PATH: /models/sam2_hiera_large.pt
            MODEL_CHECKPOINT_PATH: ''
            SAM2_CONFIG: sam2_hiera_l.yaml
            INPUT_SIZE: '352'
            SERVICE_JWT_SECRET:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: service-jwt
            REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
            FEATURE_CACHE_TTL: '3600'
            S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
            S3_ACCESS_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: access-key
            S3_SECRET_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-s3
                  key: secret-key
            S3_BUCKET: cosmo-storage-develop
        ingress:
          enabled: false
        imagePullSecrets:
        - name: regcred
      diceBot:
        enabled: true
        replicaCount: 1
        image:
          repository: dice-docker-local.bart.sec.samsung.net/vision-dice-bot
          pullPolicy: IfNotPresent
        imagePullSecrets:
        - name: regcred
        environment: production
        logLevel: INFO
        config:
          messengerSystemId: C60LD0001
        serviceAccount:
          create: true
          name: ''
        podSecurityContext:
          runAsNonRoot: true
          runAsUser: 1000
          runAsGroup: 1000
          fsGroup: 1000
        securityContext:
          allowPrivilegeEscalation: false
          readOnlyRootFilesystem: true
        service:
          type: ClusterIP
          port: 8000
          targetPort: 8000
        livenessProbe:
          httpGet:
            path: /api/v1/dice-bot/health
            port: http
          initialDelaySeconds: 30
          periodSeconds: 10
          timeoutSeconds: 5
          failureThreshold: 3
        readinessProbe:
          httpGet:
            path: /api/v1/dice-bot/health
            port: http
          initialDelaySeconds: 10
          periodSeconds: 5
          timeoutSeconds: 3
          failureThreshold: 3
        resources:
          limits:
            cpu: 500m
            memory: 384Mi
          requests:
            cpu: 250m
            memory: 128Mi
        autoscaling:
          enabled: false
          minReplicas: 1
          maxReplicas: 3
          targetCPUUtilizationPercentage: 80
          targetMemoryUtilizationPercentage: 80
        env:
          TRAINER_SERVICE_BASE_URL: http://dice-platform-backend.dice.svc.cluster.local:8000
          MESSENGER_BASE_URL: https://openapi.stage.samsung.net
          MESSENGER_SYSTEM_ID: KCC10BOT01765
          ACTIVATION_BASE_URL: https://dice.gtrai.sec.samsung.net/
          MESSENGER_ACCESS_TOKEN:
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: messenger-access-token
          DICE_BOT_ACTIVATION_TOKEN:
            valueFrom:
              secretKeyRef:
                name: dice-runtime
                key: DICE_BOT_ACTIVATION_TOKEN
      userService:
        enabled: true
        replicaCount: 1
        image:
          repository: dice-docker-local.bart.sec.samsung.net/vision-user-service
          pullPolicy: IfNotPresent
          tag: latest
        imagePullSecrets:
        - name: regcred
        service:
          type: ClusterIP
          port: 80
          targetPort: 8003
        config:
          apiV1Prefix: /user/api/v1
          backendPort: '8003'
          serviceJwtAlgorithm: HS256
          botBackendUrl: ''
          adminNotifyTarget: ''
          serviceJwtSecret: ''
        env:
          SERVICE_JWT_ALGORITHM: HS256
        secretEnv:
        - name: SERVICE_JWT_SECRET
          secretName: dice-runtime
          secretKey: service-jwt
        - name: USER_DATABASE_URL
          secretName: dice-database
          secretKey: user-database-url
        - name: ACTIVATION_DATABASE_URL
          secretName: dice-runtime
          secretKey: platform-backend-activation-database-url
      dashboard:
        enabled: true
        frontend:
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-frontend
            pullPolicy: IfNotPresent
          tag: latest
          service:
            type: ClusterIP
            port: 3021
            targetPort: 3021
          imagePullSecrets:
          - name: regcred
        backend:
          replicaCount: 1
          image:
            repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-backend
            pullPolicy: IfNotPresent
          service:
            type: ClusterIP
            port: 8021
            targetPort: 8021
          imagePullSecrets:
          - name: regcred
          env:
            DASHBOARD_PROMETHEUS_URL: http://prometheus.prometheus.svc.cluster.local:9090
            DASHBOARD_AGENT_LLM_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
            DASHBOARD_AGENT_LLM_API_KEY:
              valueFrom:
                secretKeyRef:
                  name: dice-runtime
                  key: dashboard-agent-llm-api-key
            DASHBOARD_AGENT_LLM_MODEL: qwen/qwen3.8-flash-next
      storage:
        connectApplications: true
        env:
          S3_REGION: auto
          S3_USE_SSL: 'true'
      database:
        enabled: true
        postgres:
          image:
            repository: docker-remote.bart.sec.samsung.net/postgres
            pullPolicy: IfNotPresent
          port: 5432
          user: postgres
          password: ''
          passwordSecret:
            name: dice-database
            key: postgres-password
          initialDatabase: postgres
        pgadmin:
          image:
            repository: docker-remote.bart.sec.samsung.net/dpage/pgadmin4
            pullPolicy: IfNotPresent
          defaultEmail: test@hello.com
        dataVolume:
          size: 100Gi
        pgadminVolume:
          size: 10Gi
        resources:
          postgres:
            requests:
              cpu: 1000m
              memory: 2Gi
            limits:
              cpu: 2000m
              memory: 4Gi
          pgadmin:
            requests:
              cpu: 100m
              memory: 256Mi
            limits:
              cpu: 500m
              memory: 512Mi
      autoLabeling:
        enabled: true
        gpuUuid: GPU-855b74e3-3d38-ed07-5f6b-43bc1cf04bdd

destination:
  server: 'https://kubernetes.default.svc'
  namespace: dice


    requests:
      cpu: 100m
      memory: 128Mi
    limits:
      cpu: '1'
      memory: 1Gi
  persistence:
    enabled: true
    storageClass: nfs-csi
    size: 10Gi
  networkPolicy:
    enabled: true
  databases:
    platform: 0
    labeler: 1
    mlService: 0
    sam2UnetService: 0
  nodeSelector:
    kubernetes.io/hostname: node1
webAuth:
  enabled: true
  replicaCount: 1
  image:
    repository: dice-docker-local.bart.sec.samsung.net/dice-web-auth
    pullPolicy: IfNotPresent
  imagePullSecrets:
  - name: regcred
  serviceAccount:
    create: true
    name: ''
  podSecurityContext:
    fsGroup: 1001
  securityContext:
    runAsNonRoot: true
    runAsUser: 1001
    runAsGroup: 1001
    allowPrivilegeEscalation: false
  service:
    type: ClusterIP
    port: 3020
    targetPort: 3020
  ingress:
    enabled: false
    className: nginx
  resources:
    limits:
      cpu: 300m
      memory: 384Mi
    requests:
      cpu: 50m
      memory: 128Mi
  livenessProbe:
    httpGet:
      path: /api/auth/session
      port: http
    initialDelaySeconds: 15
    periodSeconds: 10
    timeoutSeconds: 3
    failureThreshold: 3
  readinessProbe:
    httpGet:
      path: /api/auth/session
      port: http
    initialDelaySeconds: 5
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
  env:
    NEXT_PUBLIC_BASE_PATH: /
    NEXT_PUBLIC_AUTH_DEFAULT_CALLBACK_URL: /
    NEXTAUTH_URL: https://dice.gtrai.sec.samsung.net/api/auth
    AUTH_DEFAULT_CALLBACK_URL: /
    AUTH_ALLOWED_CALLBACK_PREFIXES: /,/platform,/labeler,/defect,/docs,/activation
    ADFS_CLIENT_ID: 00c7203f-9213-4f0f-971a-ac5bac3d6ee3
    ADFS_ISSUER: https://sts.secsso.net/adfs
    ADFS_ISSUER_INTERNAL: https://sts.secsso.net/adfs
    SERVICE_JWT_SECRET:
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: service-jwt
    S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
    S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
    S3_ACCESS_KEY:
      valueFrom:
        secretKeyRef:
          name: dice-s3
          key: access-key
    S3_SECRET_KEY:
      valueFrom:
        secretKeyRef:
          name: dice-s3
          key: secret-key
    S3_BUCKET: cosmo-storage-develop
    S3_REGION: auto
    RUNNER_RELEASE_STORAGE_PREFIX: runner-releases/windows
    RUNNER_ENV_STORAGE_PREFIX: runner-envs/linux
    RUNNER_ENV_PRESIGN_EXPIRE_SECONDS: '3600'
    AUTH_ALLOWED_CALLBACK_ORIGINS: https://dice.gtrai.sec.samsung.net
    ACTIVATION_DB_HOST: dice-platform-database.dice.svc.cluster.local
    ACTIVATION_DB_PORT: '5432'
    ACTIVATION_DB_NAME: activation
    ACTIVATION_AES_KEY:
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: activation-aes-key
    DICE_BOT_ACTIVATION_TOKEN:
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: DICE_BOT_ACTIVATION_TOKEN
  secretEnv:
  - name: NEXTAUTH_SECRET
    secretName: vision-ai-secrets
    secretKey: web-auth-nextauth-secret
  - name: ADFS_CLIENT_SECRET
    secretName: vision-ai-secrets
    secretKey: web-auth-adfs-client-secret
  - name: ACTIVATION_DB_USER
    secretName: dice-database
    secretKey: postgres-user
  - name: ACTIVATION_DB_PASSWORD
    secretName: dice-database
    secretKey: postgres-password
docs:
  enabled: true
  replicaCount: 1
  image:
    repository: dice-docker-local.bart.sec.samsung.net/dice-docs
    pullPolicy: IfNotPresent
  imagePullSecrets:
  - name: regcred
  service:
    type: ClusterIP
    port: 3030
    targetPort: 3030
  livenessProbe:
    httpGet:
      path: /docs/ko
      port: http
    initialDelaySeconds: 15
    periodSeconds: 10
    timeoutSeconds: 3
    failureThreshold: 3
  readinessProbe:
    httpGet:
      path: /docs/ko
      port: http
    initialDelaySeconds: 5
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
  resources:
    limits:
      cpu: 300m
      memory: 384Mi
    requests:
      cpu: 50m
      memory: 128Mi
platform:
  mcp:
    enabled: true
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-mcp-server
      pullPolicy: IfNotPresent
    imagePullSecrets:
    - name: regcred
    service:
      type: ClusterIP
      port: 8080
      targetPort: 8080
    basePath: /platform/mcp
    env:
      DICE_API_URL: ''
      DICE_API_PREFIX: /platform/api/v1
      NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.gtrai.sec.samsung.net
    ingress:
      enabled: false
      className: nginx
      annotations: {}
      hosts:
      - host: mcp.vision-ai.local
        paths:
        - path: /platform/mcp
          pathType: Prefix
      tls: []
    livenessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 10
      periodSeconds: 20
    readinessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 5
      periodSeconds: 10
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
    nodeSelector: {}
  dashboardMcp:
    enabled: true
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-mcp-server
      pullPolicy: IfNotPresent
    service:
      type: ClusterIP
      port: 8080
      targetPort: 8080
    basePath: /mcp/dashboard
    env:
      DICE_API_PREFIX: /platform/api/v1
      NO_PROXY: localhost,127.0.0.1,.svc,.svc.cluster.local,.gtrai.sec.samsung.net
    ingress:
      enabled: false
      className: nginx
    livenessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 10
      periodSeconds: 20
    readinessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 5
      periodSeconds: 10
    resources:
      requests:
        cpu: 100m
        memory: 128Mi
      limits:
        cpu: 500m
        memory: 256Mi
  backend:
    enabled: true
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-platform-backend
      pullPolicy: IfNotPresent
    imagePullSecrets:
    - name: regcred
    serviceAccount:
      create: true
      name: ''
    rbac:
      create: true
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      runAsGroup: 1000
    service:
      type: ClusterIP
      port: 8000
      targetPort: 8000
    ingress:
      enabled: false
      className: nginx
    resources:
      limits:
        cpu: 2000m
        memory: 2Gi
      requests:
        cpu: 1000m
        memory: 1Gi
    autoscaling:
      enabled: false
      minReplicas: 1
      maxReplicas: 5
      targetCPUUtilizationPercentage: 80
      targetMemoryUtilizationPercentage: 80
    env:
      LLM_PROVIDER: openai
      OPENAI_API_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: platform-backend-openai-api-key
      OPENAI_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
      LLM_MODEL: qwen/qwen3.8-flash-next
      DASHBOARD_AGENT_LLM_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
      DASHBOARD_AGENT_LLM_API_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: dashboard-agent-llm-api-key
      DASHBOARD_AGENT_LLM_MODEL: qwen/qwen3.8-flash-next
      DATABASE_URL:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: platform-database-url
      USER_DATABASE_URL:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: user-database-url
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
      BACKEND_PORT: '8000'
      API_V1_PREFIX: /platform/api/v1
      API_BASE_URL: http://dice-platform-backend.dice.svc.cluster.local:8000
      CORS_ORIGINS: https://dice.gtrai.sec.samsung.net,http://dice.gtrai.sec.samsung.net
      FRONTEND_URL: https://dice.gtrai.sec.samsung.net
      TRAINING_MODE: kubernetes
      USE_UV: 'false'
      USER_SERVICE_API_URL: http://dice-platform-user-service.dice.svc.cluster.local/user/api/v1
      S3_BUCKET: cosmo-storage-develop
      S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
      S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
      S3_ACCESS_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: access-key
      S3_SECRET_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: secret-key
      S3_REGION: auto
      S3_USE_SSL: 'true'
      JWT_SECRET:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: jwt
      JWT_ALGORITHM: HS256
      ACCESS_TOKEN_EXPIRE_MINUTES:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: platform-backend-access-token-expire-minutes
      REFRESH_TOKEN_EXPIRE_DAYS:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: platform-backend-refresh-token-expire-days
      SERVICE_JWT_SECRET:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: service-jwt
      LABELER_API_URL: http://dice-labeler-backend.dice.svc.cluster.local:8001
      PADDLEOCR_INFERENCE_TIMEOUT_SECONDS: '3600'
      ACTIVATION_DATABASE_URL:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: platform-backend-activation-database-url
      LOG_LEVEL: INFO
      LOG_FORMAT: json
      DEBUG: 'False'
      ENVIRONMENT: production
      USE_GPU: 'true'
      CUDA_VISIBLE_DEVICES: '0'
      K8S_GPU_COUNT: '1'
      K8S_MEMORY_LIMIT: 16Gi
      K8S_MEMORY_REQUEST: 8Gi
      K8S_CPU_LIMIT: '4'
      K8S_CPU_REQUEST: '2'
      AGENT_JWT_ALGORITHM: HS256
      AGENT_JWT_EXPIRE_HOURS: '24'
      AGENT_RUNTIME_BUNDLE_PREFIX: agent-runtimes
      AGENT_INSTALLER_VERSION: ''
      RUNNER_ENV_STORAGE_PREFIX: runner-envs/linux
      RUNNER_ENV_PRESIGN_EXPIRE_SECONDS: '3600'
      RUNNER_ENV_API_TOKEN:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: runner-env-token
      PROMETHEUS_URL: http://prometheus.prometheus.svc.cluster.local:9090
      PROMETHEUS_TIMEOUT_SECONDS: '15'
      TRAINING_DIAGNOSTICS_ENABLED: 'true'
      DICE_INFERENCE_GATEWAY_URL: https://dice.gtrai.sec.samsung.net/v1
      DICE_INFERENCE_SERVICE_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-inference-gateway
            key: api-key
      DICE_JEV_MODEL: jev/jev-9b
      DICE_JEV_ENABLED: 'true'
      AGENT_EXECUTION_MODE: embedded
    livenessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 30
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /health
        port: http
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    persistence:
      enabled: false
      size: 10Gi
  frontend:
    enabled: true
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-platform-frontend
      pullPolicy: IfNotPresent
    imagePullSecrets:
    - name: regcred
    serviceAccount:
      create: true
      name: ''
    podSecurityContext:
      fsGroup: 101
    securityContext:
      runAsNonRoot: true
      runAsUser: 101
      runAsGroup: 101
      allowPrivilegeEscalation: false
    service:
      type: ClusterIP
      port: 3000
      targetPort: 3000
    ingress:
      enabled: false
      className: nginx
      annotations:
        nginx.ingress.kubernetes.io:
          proxy-body-size: 50m
    resources:
      limits:
        cpu: 4
        memory: 4Gi
      requests:
        cpu: 2
        memory: 1Gi
    livenessProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 3
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /healthz
        port: http
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    autoscaling:
      enabled: false
      minReplicas: 1
      maxReplicas: 5
      targetCPUUtilizationPercentage: 70
      targetMemoryUtilizationPercentage: 80
    env:
      NEXT_PUBLIC_API_URL: /platform/api/v1
      NEXT_PUBLIC_LABELER_FRONTEND_URL: /labeler
      NEXT_PUBLIC_BASE_PATH: /platform
      NEXT_PUBLIC_USER_API_URL: /user/api/v1
  runner:
    enabled: true
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-runner
      pullPolicy: IfNotPresent
    command: []
    args: []
    imagePullSecrets:
    - name: regcred
    hostPID: true
    podSecurityContext:
      fsGroup: 1000
      fsGroupChangePolicy: OnRootMismatch
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      runAsGroup: 1000
      allowPrivilegeEscalation: false
    service:
      type: ClusterIP
      inferencePort: 8080
      inferenceTargetPort: 5002
      managementPort: 8081
      managementTargetPort: 8081
    tolerations:
    - key: nvidia.com/gpu
      operator: Exists
      effect: NoSchedule
    - key: dedicated
      operator: Equal
      value: llm
      effect: NoSchedule
    nodeSelector:
      accelerator: null
      kubernetes.io/hostname: node2
    resources:
      requests:
        cpu: '16'
        memory: 32Gi
        nvidia.com/gpu: '1'
      limits:
        cpu: '16'
        memory: 32Gi
        nvidia.com/gpu: '1'
    env:
      NVIDIA_DRIVER_CAPABILITIES: compute,utility
    extraEnv:
    - name: TS_PLATFORM_API_TOKEN
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: runner-platform-api-token
    config:
      create: true
      existingConfigMap: ''
      disableTokenAuthorization: true
      enableEnvvarsConfig: true
      enableModelApi: true
      enableEnvApi: true
      basePath: /runner
      modelServerHome: /var/lib/dice
      loadModels: []
      defaultWorkersPerModel: 0
      defaultResponseTimeout: 1200
      defaultStartupTimeout: 1200
      jobQueueSize: 100
      maxRequestSize: '6553500'
      maxResponseSize: '6553500'
      asyncLogging: true
      metricsMode: prometheus
      systemMetricsIntervalSecs: 10
      metricsArchiveEnabled: true
      metricsArchiveIntervalSecs: 5
      metricsArchiveRetentionDays: 7
      numberOfGpu: 1
      pythonEnvs:
        default: python3
      extraToml: ''
      platformApiUrl: http://dice-platform-backend.dice.svc.cluster.local:8000/platform/api/v1
    storage:
      sizeLimit: 50Gi
      subPaths:
        models: models
        envs: envs
        logs: logs
      persistence:
        enabled: true
        storageClass: nfs-csi
        size: 500Gi
        accessModes:
        - ReadWriteMany
    livenessProbe:
      httpGet:
        path: /runner/api/ping
        port: inference
      initialDelaySeconds: 90
      periodSeconds: 30
      timeoutSeconds: 5
      failureThreshold: 3
    startupProbe:
      httpGet:
        path: /runner/api/ping
        port: inference
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 120
    readinessProbe:
      httpGet:
        path: /runner/api/ping
        port: inference
      initialDelaySeconds: 60
      periodSeconds: 10
      timeoutSeconds: 3
      failureThreshold: 3
    extraVolumes: []
    extraVolumeMounts: []
  training:
    datasetCache:
      job:
        activeDeadlineSeconds: 259200
    enabled: true
    namespace: dice
    istio:
      inject: false
    registry:
      url: dice-docker-local.bart.sec.samsung.net
      pullSecret: regcred
    serviceAccount:
      create: true
      name: ''
    rbac:
      create: true
    job:
      backoffLimit: 0
      ttlSecondsAfterFinished: 600
      activeDeadlineSeconds: '1296000'
    resources:
      defaults:
        cpu:
          request: '4'
          limit: '8'
        memory:
          request: 16Gi
          limit: 32Gi
        gpu:
          limit: '1'
        shm:
          size: 12Gi
    gpu:
      nodeSelector: null
      tolerations: []
    storage:
      datasets:
        enabled: true
        create: true
        pvcName: datasets-cache-pvc
        storageClass: nfs-csi
        size: 500Gi
        accessModes:
        - ReadWriteMany
        mountPath: /data/datasets
        readOnly: false
        cacheMaxSizeGB: 500
      modelsCache:
        enabled: true
        create: true
        pvcName: models-cache-pvc
        storageClass: nfs-csi
        size: 500Gi
        accessModes:
        - ReadWriteMany
        mountPath: /data/models
    s3:
      enabled: true
      accessKey: ''
    space:
      enabled: true
      adapterImage: ''
      imagePrefix: gtr-ai-vision
      codeBundle:
        enabled: true
        prefix: space-code
        root: /home/user
        presignExpirationSeconds: 604800
      credentials:
        create: false
        existingSecret: dice-space
        secretName: ''
        username: ''
        password: ''
        usernameKey: username
        passwordKey: password
      region: gumi-1
      groupId: GTR-AI-VISION
      groupPoolId: '170'
      quotaId: '155'
      experimentId: '453'
      coreId: '2'
      coreCount: '1'
      expectedRunTime: ''
      createMode: api
      apiBaseUrl: https://mlp.n7.sr-cloud.com
      configPath: ''
      inputDatasets: '[]'
      enabledRunFeatures: '[]'
      allowSpot: 'false'
      emailNoticeCode: '0'
      isSetupRun: 'false'
      runType: batch
      type: oneOff
      cache:
        datasets:
          claimId: datasets-cache-pvc
          mountPath: /data/datasets
          maxSizeGB: '500'
        models:
          claimId: models-cache-pvc
          mountPath: /data/models
      adapterJob:
        gpuLimit: '0'
        cpuRequest: 500m
        cpuLimit: '1'
        memoryRequest: 256Mi
        memoryLimit: 1Gi
        backoffLimit: '0'
        activeDeadlineSeconds: '262800'
      createTimeoutSeconds: '300'
      logReconnectLimit: '5'
      logReconnectBaseDelay: '2.0'
      logReconnectMaxDelay: '30.0'
      stopRetryAttempts: '3'
      stopRetryBaseDelay: '2.0'
      statusQueryRetryAttempts: '3'
      statusQueryRetryBaseDelay: '5.0'
      forwardRawLogs: 'false'
    frameworks:
      ultralytics:
        enabled: true
        image_suffix: trainer-ultralytics
        resources:
          memory:
            request: 8Gi
            limit: 16Gi
      huggingface:
        enabled: true
        image_suffix: trainer-huggingface
        resources:
          memory:
            request: 16Gi
            limit: 32Gi
        extra_env:
        - name: HF_HOME
          value: /tmp/huggingface
        - name: TRANSFORMERS_CACHE
          value: /tmp/huggingface/transformers
        extra_volumes:
        - name: hf-cache
          emptyDir:
            sizeLimit: 10Gi
        extra_volume_mounts:
        - name: hf-cache
          mountPath: /tmp/huggingface
     timm:
        enabled: true
        image_suffix: trainer-timm
        resources:
          memory:
            request: 8Gi
            limit: 16Gi
      vfm-v1:
        enabled: true
        image_suffix: trainer-vfm-v1
        resources:
          memory:
            request: 16Gi
            limit: 32Gi
      dice_v1:
        enabled: true
        image_suffix: trainer-dice-v1
        resources:
          memory:
            request: 8Gi
            limit: 16Gi
      openmm-cu118:
        enabled: true
        image_suffix: trainer-openmm-cu118
        resources:
          memory:
            request: 16Gi
            limit: 32Gi
      openmm-cu128:
        enabled: true
        image_suffix: trainer-openmm-cu128
        resources:
          memory:
            request: 16Gi
            limit: 32Gi
      space:
        enabled: true
        image_suffix: space-adapter
        resources:
          memory:
            request: 8Gi
            limit: 16Gi
      custom:
        enabled: true
        resources:
          memory:
            request: 8Gi
            limit: 16Gi
    debugPod:
      enabled: false
      image: docker-remote.bart.sec.samsung.net/python
      tag: 3.11-slim
    proxy:
      enabled: true
      httpProxy: http://168.219.61.252:8080
      httpsProxy: http://168.219.61.252:8080
      noProxy: localhost,127.0.0.1,.svc,.svc.cluster.local,.local,.kubernetes.default.svc,10.0.0.0/8,.samsungspc.com,.samsung.net
      disableXet: true
      caCert:
        enabled: true
        useConfigMap: true
        configMapName: digitalcity-cert-cm
        mountPath: /etc/ssl/certs/extra-ca.crt
        key: extra-ca.crt
    podSecurityContext:
      fsGroup: 1000
    securityContext:
      runAsNonRoot: true
      runAsUser: 1000
      allowPrivilegeEscalation: false
labeler:
  enabled: true
  nameOverride: ''
  fullnameOverride: ''
  backend:
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-backend
    replicas: 1
    port: 8001
    startupProbe:
      path: /health
      initialDelaySeconds: 10
      periodSeconds: 5
      timeoutSeconds: 5
      failureThreshold: 60
    livenessProbe:
      path: /health
      initialDelaySeconds: 30
      periodSeconds: 30
      timeoutSeconds: 5
      failureThreshold: 5
    readinessProbe:
      path: /health
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 6
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      fsGroup: 1000
    env:
      ENVIRONMENT: development
      DEBUG: 'true'
      LOG_LEVEL: DEBUG
      API_HOST: 0.0.0.0
      API_PORT: '8001'
      API_V1_PREFIX: /labeler/api/v1
      RUN_MIGRATIONS: 'true'
      CORS_ORIGINS: http://localhost:3000,http://dice.gtrai.sec.samsung.net,https://dice.gtrai.sec.samsung.net
      FRONTEND_URL: https://dice.gtrai.sec.samsung.net/labeler
      PLATFORM_DB_HOST: dice-platform-database.dice
      PLATFORM_DB_PORT: '5432'
      PLATFORM_DB_NAME: platform
      PLATFORM_DB_USER:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: postgres-user
      PLATFORM_DB_PASSWORD:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: postgres-password
      LABELER_DB_HOST: dice-platform-database.dice
      LABELER_DB_PORT: '5432'
      LABELER_DB_NAME: labeler
      LABELER_DB_USER:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: postgres-user
      LABELER_DB_PASSWORD:
        valueFrom:
          secretKeyRef:
            name: dice-database
            key: postgres-password
      S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
      S3_ENDPOINT_PUBLIC: https://s3.ap-northeast-2.samsungspc.com
      S3_ACCESS_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: access-key
      S3_SECRET_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: secret-key
      S3_BUCKET: cosmo-storage-develop
      TRAINING_EXPORT_PREFIX: datasets/training-exports
      S3_REGION: auto
      S3_USE_SSL: 'true'
      SERVICE_JWT_SECRET:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: service-jwt
      SERVICE_JWT_ALGORITHM: HS256
      REALESRGAN_INFERENCE_TIMEOUT_SECONDS: '600'
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
      LARGE_UPLOAD_IMPORT_QUEUE_NAME: dataset-imports
      LARGE_UPLOAD_IMPORT_JOB_TIMEOUT_SECONDS: '43200'
      ANNOTATION_BULK_QUEUE_NAME: annotation-bulk-ops
      ANNOTATION_BULK_JOB_TIMEOUT_SECONDS: '7200'
      ANNOTATION_BULK_JOB_CHUNK_SIZE: '200'
      DB_POOL_SIZE: '10'
      DB_MAX_OVERFLOW: '20'
      DB_POOL_TIMEOUT_SECONDS: '30'
      API_WORKERS: '2'
      REMOTE_DATA_SERVICE_URL: http://data.cosmo.svc.cluster.local:24500
      REMOTE_DATA_S3_BUCKET: cosmo-storage
      USER_SERVICE_API_URL: http://dice-platform-user-service.dice.svc.cluster.local/user/api/v1
      SAM_GATEWAY_ENABLED: 'true'
      SAM_REQUIRED_VRAM_BYTES: '4294967296'
      SAM_MODEL_S3_KEY: 'base/sam3/onnx/v1/sam3-fp16.onnx'
    existingSecret: ''
  importWorker:
    enabled: true
    image:
      repository: ''
      pullPolicy: IfNotPresent
    replicas: 1
    env:
      RUN_MIGRATIONS: 'false'
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
        ephemeral-storage: 20Gi
      limits:
        cpu: '2'
        memory: 4Gi
        ephemeral-storage: 50Gi
  bulkWorker:
    enabled: true
    image:
      repository: ''
      pullPolicy: IfNotPresent
    replicas: 1
    env:
      RUN_MIGRATIONS: 'false'
      DB_POOL_SIZE: '2'
      DB_MAX_OVERFLOW: '2'
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
      ANNOTATION_BULK_QUEUE_NAME: annotation-bulk-ops
      ANNOTATION_BULK_JOB_TIMEOUT_SECONDS: '7200'
      ANNOTATION_BULK_JOB_CHUNK_SIZE: '200'
      DB_POOL_TIMEOUT_SECONDS: '30'
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: '1'
        memory: 1Gi
  publishWorker:
    enabled: true
    image:
      repository: ''
      pullPolicy: IfNotPresent
    replicas: 1
    env:
      RUN_MIGRATIONS: 'false'
      DB_POOL_SIZE: '2'
      DB_MAX_OVERFLOW: '2'
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
      PUBLISH_QUEUE_NAME: version-publish
      PUBLISH_JOB_TIMEOUT_SECONDS: '7200'
      DB_POOL_TIMEOUT_SECONDS: '30'
    resources:
      requests:
        cpu: 200m
        memory: 512Mi
      limits:
        cpu: '1'
        memory: 1Gi
  srBuildWorker:
    enabled: true
    image:
      repository: ''
      pullPolicy: IfNotPresent
    replicas: 1
    env:
      RUN_MIGRATIONS: 'false'
      DB_POOL_SIZE: '2'
      DB_MAX_OVERFLOW: '2'
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/1
      SUPER_RESOLUTION_BUILD_QUEUE_NAME: super-resolution-builds
      SUPER_RESOLUTION_BUILD_JOB_TIMEOUT_SECONDS: '86400'
      DB_POOL_TIMEOUT_SECONDS: '30'
    resources:
      requests:
        cpu: 500m
        memory: 1Gi
      limits:
        cpu: '2'
        memory: 4Gi
  frontend:
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-frontend
    replicas: 1
    port: 3000
    securityContext:
      runAsUser: 101
      runAsGroup: 101
      fsGroup: 101
    livenessProbe:
      httpGet:
        path: /healthz
        port: 3000
      initialDelaySeconds: 10
      periodSeconds: 10
      timeoutSeconds: 3
      failureThreshold: 3
    readinessProbe:
      httpGet:
        path: /healthz
        port: 3000
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 3
      failureThreshold: 3
    env:
      NEXT_PUBLIC_BASE_PATH: /labeler
      NEXT_PUBLIC_ENABLE_IMAGE_LOCK: 'true'
  defectBackend:
    enabled: true
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-defect-backend
    replicas: 1
    port: 8002
    startupProbe:
      path: /health
      initialDelaySeconds: 5
      periodSeconds: 5
      timeoutSeconds: 5
      failureThreshold: 30
    livenessProbe:
      path: /health
      initialDelaySeconds: 10
      periodSeconds: 30
      timeoutSeconds: 5
      failureThreshold: 5
    readinessProbe:
      path: /health
      initialDelaySeconds: 5
      periodSeconds: 10
      timeoutSeconds: 5
      failureThreshold: 6
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      fsGroup: 1000
    env:
      DEFECT_ENVIRONMENT: production
      DEFECT_LOG_LEVEL: INFO
      DEFECT_API_PORT: '8002'
      DEFECT_API_V1_PREFIX: /defect/api/v1
      DEFECT_GENERATION_MODE: mock
  mlService:
    enabled: true
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-ml-service
    replicas: 1
    port: 8080
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      fsGroup: 1000
    env:
      ENVIRONMENT: production
      LOG_LEVEL: INFO
      HOST: 0.0.0.0
      PORT: '8080'
      SAM2_UNET_CONNECT_TIMEOUT: '5.0'
      SAM2_UNET_READ_TIMEOUT: '30.0'
      SERVICE_JWT_SECRET:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: service-jwt
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
      CB_FAILURE_THRESHOLD: '5'
      CB_RECOVERY_TIMEOUT: '30.0'
      BATCH_WORKER_ENABLED: 'true'
      SAM2_UNET_SERVICE_URL: http://dice-labeler-sam2-unet-service:8080
      SERVICE_JWT_ALGORITHM: HS256
      CALLBACK_URL: http://dice-labeler-backend:8001/api/v1/internal/ai/callback
  sam2UnetService:
    enabled: true
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-labeler-sam2-unet-service
    replicas: 1
    port: 8080
    securityContext:
      runAsUser: 1000
      runAsGroup: 1000
      fsGroup: 1000
    resources:
      requests:
        cpu: '2'
        memory: 12Gi
        nvidia.com/gpu: '1'
      limits:
        nvidia.com/gpu: '1'
        cpu: '8'
        memory: 24Gi
    modelVolume:
      enabled: true
      create: true
      claimName: sam2-models
      storageClass: nfs-csi
      size: 20Gi
      accessModes:
      - ReadWriteMany
      annotations: {}
      mountPath: /models
      readOnly: false
    baseModelBootstrap:
      enabled: true
      objectKey: base/sam2_hiera_large.pt
      targetPath: /models/sam2_hiera_large.pt
    env:
      ENVIRONMENT: production
      LOG_LEVEL: INFO
      HOST: 0.0.0.0
      PORT: '8080'
      DEVICE: auto
      SAM2_CHECKPOINT_PATH: /models/sam2_hiera_large.pt
      MODEL_CHECKPOINT_PATH: ''
      SAM2_CONFIG: sam2_hiera_l.yaml
      INPUT_SIZE: '352'
      SERVICE_JWT_SECRET:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: service-jwt
      REDIS_URL: redis://dice-platform-redis.dice.svc.cluster.local:6379/0
      FEATURE_CACHE_TTL: '3600'
      S3_ENDPOINT: https://s3.ap-northeast-2.samsungspc.com
      S3_ACCESS_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: access-key
      S3_SECRET_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-s3
            key: secret-key
      S3_BUCKET: cosmo-storage-develop
  ingress:
    enabled: false
  imagePullSecrets:
  - name: regcred
diceBot:
  enabled: true
  replicaCount: 1
  image:
    repository: dice-docker-local.bart.sec.samsung.net/vision-dice-bot
    pullPolicy: IfNotPresent
  imagePullSecrets:
  - name: regcred
  environment: production
  logLevel: INFO
  config:
    messengerSystemId: C60LD0001
  serviceAccount:
    create: true
    name: ''
  podSecurityContext:
    runAsNonRoot: true
    runAsUser: 1000
    runAsGroup: 1000
    fsGroup: 1000
  securityContext:
    allowPrivilegeEscalation: false
    readOnlyRootFilesystem: true
  service:
    type: ClusterIP
    port: 8000
    targetPort: 8000
  livenessProbe:
    httpGet:
      path: /api/v1/dice-bot/health
      port: http
    initialDelaySeconds: 30
    periodSeconds: 10
    timeoutSeconds: 5
    failureThreshold: 3
  readinessProbe:
    httpGet:
      path: /api/v1/dice-bot/health
      port: http
    initialDelaySeconds: 10
    periodSeconds: 5
    timeoutSeconds: 3
    failureThreshold: 3
  resources:
    limits:
      cpu: 500m
      memory: 384Mi
    requests:
      cpu: 250m
      memory: 128Mi
  autoscaling:
    enabled: false
    minReplicas: 1
    maxReplicas: 3
    targetCPUUtilizationPercentage: 80
    targetMemoryUtilizationPercentage: 80
  env:
    TRAINER_SERVICE_BASE_URL: http://dice-platform-backend.dice.svc.cluster.local:8000
    MESSENGER_BASE_URL: https://openapi.stage.samsung.net
    MESSENGER_SYSTEM_ID: KCC10BOT01765
    ACTIVATION_BASE_URL: https://dice.gtrai.sec.samsung.net/
    MESSENGER_ACCESS_TOKEN:
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: messenger-access-token
    DICE_BOT_ACTIVATION_TOKEN:
      valueFrom:
        secretKeyRef:
          name: dice-runtime
          key: DICE_BOT_ACTIVATION_TOKEN
userService:
  enabled: true
  replicaCount: 1
  image:
    repository: dice-docker-local.bart.sec.samsung.net/vision-user-service
    pullPolicy: IfNotPresent
    tag: latest
  imagePullSecrets:
  - name: regcred
  service:
    type: ClusterIP
    port: 80
    targetPort: 8003
  config:
    apiV1Prefix: /user/api/v1
    backendPort: '8003'
    serviceJwtAlgorithm: HS256
    botBackendUrl: ''
    adminNotifyTarget: ''
    serviceJwtSecret: ''
  env:
    SERVICE_JWT_ALGORITHM: HS256
  secretEnv:
  - name: SERVICE_JWT_SECRET
    secretName: dice-runtime
    secretKey: service-jwt
  - name: USER_DATABASE_URL
    secretName: dice-database
    secretKey: user-database-url
  - name: ACTIVATION_DATABASE_URL
    secretName: dice-runtime
    secretKey: platform-backend-activation-database-url
dashboard:
  enabled: true
  frontend:
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-frontend
      pullPolicy: IfNotPresent
    tag: latest
    service:
      type: ClusterIP
      port: 3021
      targetPort: 3021
    imagePullSecrets:
    - name: regcred
  backend:
    replicaCount: 1
    image:
      repository: dice-docker-local.bart.sec.samsung.net/dice-dashboard-backend
      pullPolicy: IfNotPresent
    service:
      type: ClusterIP
      port: 8021
      targetPort: 8021
    imagePullSecrets:
    - name: regcred
    env:
      DASHBOARD_PROMETHEUS_URL: http://prometheus.prometheus.svc.cluster.local:9090
      DASHBOARD_AGENT_LLM_BASE_URL: https://mlp-service.n10.sr-cloud.com/service-gtr-ai-vision-dice-agent/v1
      DASHBOARD_AGENT_LLM_API_KEY:
        valueFrom:
          secretKeyRef:
            name: dice-runtime
            key: dashboard-agent-llm-api-key
      DASHBOARD_AGENT_LLM_MODEL: qwen/qwen3.8-flash-next
storage:
  connectApplications: true
  env:
    S3_REGION: auto
    S3_USE_SSL: 'true'
database:
  enabled: true
  postgres:
    image:
      repository: docker-remote.bart.sec.samsung.net/postgres
      pullPolicy: IfNotPresent
    port: 5432
    user: postgres
    password: ''
    passwordSecret:
      name: dice-database
      key: postgres-password
    initialDatabase: postgres
  pgadmin:
    image:
      repository: docker-remote.bart.sec.samsung.net/dpage/pgadmin4
      pullPolicy: IfNotPresent
    defaultEmail: test@hello.com
  dataVolume:
    size: 100Gi
  pgadminVolume:
    size: 10Gi
  resources:
    postgres:
      requests:
        cpu: 1000m
        memory: 2Gi
      limits:
        cpu: 2000m
        memory: 4Gi
    pgadmin:
      requests:
        cpu: 100m
        memory: 256Mi
      limits:
        cpu: 500m
        memory: 512Mi
autoLabeling:
  enabled: true
  gpuUuid: GPU-855b74e3-3d38-ed07-5f6b-43bc1cf04bdd


dice-labeler-backend
SUMMARY
KIND: Service
NAME: dice-labeler-backend   
NAMESPACE: dice   
CREATED AT: 04/28/2026 14:30:31 (7 months ago)
TYPE: ClusterIP
HOSTNAMES
STATUS: Synced
HEALTH: Healthy
LINKS

LIVE MANIFEST
apiVersion: v1
kind: Service
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: >
      {"apiVersion":"v1","kind":"Service","metadata":{"annotations":{},"labels":{"app.kubernetes.io/instance":"dice","app.kubernetes.io/managed-by":"Helm","app.kubernetes.io/name":"labeler","app.kubernetes.io/part-of":"platform","app.kubernetes.io/version":"1.0.0","argocd.argoproj.io/instance":"dice","helm.sh/chart":"vision-ai-platform-1.3.2"},"name":"dice-labeler-backend","namespace":"dice"},"spec":{"ports":[{"name":"http","port":8001,"protocol":"TCP","targetPort":8001}],"selector":{"app.kubernetes.io/component":"backend","app.kubernetes.io/instance":"dice","app.kubernetes.io/name":"labeler"},"type":"ClusterIP"}}
  creationTimestamp: '2026-04-28T05:30:31Z'
  labels:
    app.kubernetes.io/instance: dice
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: labeler
    app.kubernetes.io/part-of: platform
    app.kubernetes.io/version: 1.0.0
    argocd.argoproj.io/instance: dice
    helm.sh/chart: vision-ai-platform-1.3.2
  name: dice-labeler-backend
  namespace: dice
  resourceVersion: '549097868'
  uid: f0475133-1788-4502-ac51-d7b217d73313
spec:
  clusterIP: 10.240.25.1
  clusterIPs:
    - 10.240.25.1
  internalTrafficPolicy: Cluster
  ipFamilies:
    - IPv4
  ipFamilyPolicy: SingleStack
  ports:
    - name: http
      port: 8001
      protocol: TCP
      targetPort: 8001
  selector:
    app.kubernetes.io/component: backend
    app.kubernetes.io/instance: dice
    app.kubernetes.io/name: labeler
  sessionAffinity: None
  type: ClusterIP
status:
  loadBalancer: {}


dice-platform-database
KIND: Service
NAMEL: dice-platform-database   
NAMESPACE: dice   
CREATED AT: 09/01/2026 09:56:52 (3 months ago)
TYPE: ClusterIP
HOSTNAMES
STATUS: Synced
HEALTH: Healthy
LINKS

LIVE MANIFEST
apiVersion: v1
kind: Service
metadata:
  annotations:
    kubectl.kubernetes.io/last-applied-configuration: >
      {"apiVersion":"v1","kind":"Service","metadata":{"annotations":{},"labels":{"app.kubernetes.io/component":"database","app.kubernetes.io/instance":"dice","app.kubernetes.io/managed-by":"Helm","app.kubernetes.io/name":"platform","app.kubernetes.io/version":"1.0.0","argocd.argoproj.io/instance":"dice","helm.sh/chart":"vision-ai-platform-1.3.2"},"name":"dice-platform-database","namespace":"dice"},"spec":{"ports":[{"name":"postgres","port":5432,"protocol":"TCP","targetPort":5432}],"selector":{"app.kubernetes.io/component":"database","app.kubernetes.io/instance":"dice","app.kubernetes.io/name":"platform"},"type":"ClusterIP"}}
  creationTimestamp: '2026-09-01T00:56:52Z'
  labels:
    app.kubernetes.io/component: database
    app.kubernetes.io/instance: dice
    app.kubernetes.io/managed-by: Helm
    app.kubernetes.io/name: platform
    app.kubernetes.io/version: 1.0.0
    argocd.argoproj.io/instance: dice
    helm.sh/chart: vision-ai-platform-1.3.2
  name: dice-platform-database
  namespace: dice
  resourceVersion: '549097880'
  uid: ea33536d-e9a5-484a-bf41-9202e20bcf19
spec:
  clusterIP: 10.240.224.7
  clusterIPs:
    - 10.240.224.7
  internalTrafficPolicy: Cluster
  ipFamilies:
    - IPv4
  ipFamilyPolicy: SingleStack
  ports:
    - name: postgres
      port: 5432
      protocol: TCP
      targetPort: 5432
  selector:
    app.kubernetes.io/component: database
    app.kubernetes.io/instance: dice
    app.kubernetes.io/name: platform
  sessionAffinity: None
  type: ClusterIP
status:
  loadBalancer: {}
