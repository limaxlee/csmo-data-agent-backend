{{/*
===============================================================================
Common Helpers
===============================================================================
*/}}

{{/*
Expand the name of the chart.
*/}}
{{- define "vision-ai.name" -}}
{{- default "platform" .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "vision-ai.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := include "vision-ai.name" . }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Create chart name and version as used by the chart label.
*/}}
{{- define "vision-ai.chart" -}}
{{- printf "%s-%s" .Chart.Name .Chart.Version | replace "+" "_" | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Common labels
*/}}
{{- define "vision-ai.labels" -}}
helm.sh/chart: {{ include "vision-ai.chart" . }}
{{- if .Chart.AppVersion }}
app.kubernetes.io/version: {{ .Chart.AppVersion | quote }}
{{- end }}
app.kubernetes.io/managed-by: {{ .Release.Service }}
{{- end }}

{{/*
===============================================================================
Web Auth Helpers
===============================================================================
*/}}

{{/*
Web auth fullname
*/}}
{{- define "vision-ai.webAuth.fullname" -}}
{{- printf "%s-web-auth" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Web auth labels
*/}}
{{- define "vision-ai.webAuth.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.webAuth.selectorLabels" . }}
{{- end }}

{{/*
Web auth selector labels
*/}}
{{- define "vision-ai.webAuth.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: web-auth
{{- end }}

{{/*
Web auth service account name
*/}}
{{- define "vision-ai.webAuth.serviceAccountName" -}}
{{- if .Values.webAuth.serviceAccount.create }}
{{- default (include "vision-ai.webAuth.fullname" .) .Values.webAuth.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.webAuth.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
===============================================================================
Backend Helpers
===============================================================================
*/}}

{{/*
Backend fullname
*/}}
{{- define "vision-ai.backend.fullname" -}}
{{- printf "%s-backend" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Enable backend-owned dataset-cache discovery only when Kubernetes training
and its shared image-cache PVC are both configured.
*/}}
{{- define "vision-ai.datasetCache.enabled" -}}
{{- $trainingMode := lower (default "subprocess" (index .Values.platform.backend.env "TRAINING_MODE")) -}}
{{- if and .Values.platform.backend.enabled .Values.platform.training.enabled .Values.platform.training.datasetCache.enabled .Values.platform.training.storage.datasets.enabled (eq $trainingMode "kubernetes") -}}true{{- else -}}false{{- end -}}
{{- end }}

{{/*
Resolve the in-cluster Platform cache-warmup endpoint used by Labeler publish.
*/}}
{{- define "vision-ai.datasetCache.warmupUrl" -}}
{{- $configured := index .Values.labeler.backend.env "PLATFORM_DATASET_CACHE_WARMUP_URL" -}}
{{- if $configured -}}
{{- $configured -}}
{{- else if and .Values.labeler.enabled (eq (include "vision-ai.datasetCache.enabled" .) "true") -}}
{{- $apiPrefix := default "/api/v1" (index .Values.platform.backend.env "API_V1_PREFIX") | trimSuffix "/" -}}
{{- printf "http://%s.%s.svc.cluster.local:%d%s/internal/dataset-cache/warmup" (include "vision-ai.backend.fullname" .) .Release.Namespace (.Values.platform.backend.service.port | int) $apiPrefix -}}
{{- end -}}
{{- end }}

{{/*
Backend labels
*/}}
{{- define "vision-ai.backend.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.backend.selectorLabels" . }}
{{- end }}

{{/*
Backend selector labels
*/}}
{{- define "vision-ai.backend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: backend
{{- end }}

{{/*
Backend service account name
*/}}
{{- define "vision-ai.backend.serviceAccountName" -}}
{{- if .Values.platform.backend.serviceAccount.create }}
{{- default (include "vision-ai.backend.fullname" .) .Values.platform.backend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.platform.backend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
===============================================================================
Frontend Helpers
===============================================================================
*/}}

{{/*
Frontend fullname
*/}}
{{- define "vision-ai.frontend.fullname" -}}
{{- printf "%s-frontend" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Frontend labels
*/}}
{{- define "vision-ai.frontend.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.frontend.selectorLabels" . }}
{{- end }}

{{/*
Frontend selector labels
*/}}
{{- define "vision-ai.frontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: frontend
{{- end }}

{{/*
Frontend service account name
*/}}
{{- define "vision-ai.frontend.serviceAccountName" -}}
{{- if .Values.platform.frontend.serviceAccount.create }}
{{- default (include "vision-ai.frontend.fullname" .) .Values.platform.frontend.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.platform.frontend.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
===============================================================================
Runner Helpers
===============================================================================
*/}}

{{/*
Runner fullname
*/}}
{{- define "vision-ai.runner.fullname" -}}
{{- printf "%s-runner" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Runner labels
*/}}
{{- define "vision-ai.runner.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.runner.selectorLabels" . }}
{{- end }}

{{/*
Runner selector labels
*/}}
{{- define "vision-ai.runner.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: runner
{{- end }}

{{/*
Runner data PVC name
*/}}
{{- define "vision-ai.runner.dataPvcName" -}}
{{- if .Values.platform.runner.storage.persistence.existingClaim -}}
{{- .Values.platform.runner.storage.persistence.existingClaim -}}
{{- else -}}
{{- default (printf "%s-data" (include "vision-ai.runner.fullname" .)) .Values.platform.runner.storage.persistence.claimName -}}
{{- end -}}
{{- end }}

{{/*
===============================================================================
Training Infrastructure Helpers
===============================================================================
*/}}

{{/*
Training fullname
*/}}
{{- define "vision-ai.training.fullname" -}}
{{- printf "%s-training" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Training labels
*/}}
{{- define "vision-ai.training.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.training.selectorLabels" . }}
{{- end }}

{{/*
Training selector labels
*/}}
{{- define "vision-ai.training.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: training
{{- end }}

{{/*
Training namespace
*/}}
{{- define "vision-ai.training.namespace" -}}
{{- default .Release.Namespace .Values.platform.training.namespace }}
{{- end }}

{{/*
Training service account name
*/}}
{{- define "vision-ai.training.serviceAccountName" -}}
{{- if .Values.platform.training.serviceAccount.create }}
{{- default (printf "%s-job-sa" (include "vision-ai.training.fullname" .)) .Values.platform.training.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.platform.training.serviceAccount.name }}
{{- end }}
{{- end }}

{{/*
===============================================================================
Labeler Helpers
===============================================================================
*/}}

{{/*
Labeler app name
*/}}
{{- define "vision-ai.labeler.name" -}}
{{- default "labeler" .Values.labeler.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Labeler fullname
*/}}
{{- define "vision-ai.labeler.fullname" -}}
{{- if .Values.labeler.fullnameOverride }}
{{- .Values.labeler.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := include "vision-ai.labeler.name" . }}
{{- if contains $name .Release.Name }}
{{- .Release.Name | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
{{- end }}

{{/*
Labeler labels
*/}}
{{- define "vision-ai.labeler.labels" -}}
{{ include "vision-ai.labels" . }}
app.kubernetes.io/name: {{ include "vision-ai.labeler.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/part-of: {{ include "vision-ai.name" . }}
{{- end }}

{{/*
Docs fullname
*/}}
{{- define "vision-ai.docs.fullname" -}}
{{- printf "%s-docs" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Docs labels
*/}}
{{- define "vision-ai.docs.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.docs.selectorLabels" . }}
{{- end }}

{{/*
Docs selector labels
*/}}
{{- define "vision-ai.docs.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: docs
{{- end }}

{{- define "vision-ai.mcp.fullname" -}}
{{- printf "%s-mcp" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
MCP labels
*/}}
{{- define "vision-ai.mcp.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.mcp.selectorLabels" . }}
{{- end }}

{{/*
MCP selector labels
*/}}
{{- define "vision-ai.mcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: mcp
{{- end }}

{{/*
===============================================================================
Dashboard MCP Helpers (read-only dashboard via each admin's own Claude)
===============================================================================
*/}}

{{- define "vision-ai.dashboardMcp.fullname" -}}
{{- printf "%s-dashboard-mcp" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Dashboard MCP labels
*/}}
{{- define "vision-ai.dashboardMcp.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.dashboardMcp.selectorLabels" . }}
{{- end }}

{{/*
Dashboard MCP selector labels
*/}}
{{- define "vision-ai.dashboardMcp.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: dashboard-mcp
{{- end }}

{{/* Dashboard frontend resources */}}
{{- define "vision-ai.dashboardFrontend.fullname" -}}
{{- printf "%s-dashboard-frontend" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- define "vision-ai.dashboardFrontend.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.dashboardFrontend.selectorLabels" . }}
{{- end }}
{{- define "vision-ai.dashboardFrontend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: dashboard-frontend
{{- end }}

{{/* Dashboard backend resources */}}
{{- define "vision-ai.dashboardBackend.fullname" -}}
{{- printf "%s-dashboard-backend" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- define "vision-ai.dashboardBackend.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.dashboardBackend.selectorLabels" . }}
{{- end }}
{{- define "vision-ai.dashboardBackend.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: dashboard-backend
{{- end }}

{{/*
===============================================================================
Dice Bot Helpers
===============================================================================
*/}}

{{/*
Dice Bot fullname
*/}}
{{- define "vision-ai.diceBot.fullname" -}}
{{- printf "%s-dice-bot" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Dice Bot labels
*/}}
{{- define "vision-ai.diceBot.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.diceBot.selectorLabels" . }}
{{- end }}

{{/*
Dice Bot selector labels
*/}}
{{- define "vision-ai.diceBot.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: dice-bot
{{- end }}

{{/*
Dice Bot service account name
*/}}
{{- define "vision-ai.diceBot.serviceAccountName" -}}
{{- if .Values.diceBot.serviceAccount.create }}
{{- default (include "vision-ai.diceBot.fullname" .) .Values.diceBot.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.diceBot.serviceAccount.name }}
{{- end }}
{{- end }}

{{- define "vision-ai.database.fullname" -}}
{{- printf "%s-database" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Database labels
*/}}
{{- define "vision-ai.database.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.database.selectorLabels" . }}
{{- end }}

{{/*
Database selector labels
*/}}
{{- define "vision-ai.database.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: database
{{- end }}

{{/*
===============================================================================
User Service Helpers
===============================================================================
*/}}

{{/*
User Service fullname
*/}}
{{- define "vision-ai.userService.fullname" -}}
{{- printf "%s-user-service" (include "vision-ai.fullname" .) | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
User Service labels
*/}}
{{- define "vision-ai.userService.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.userService.selectorLabels" . }}
{{- end }}

{{/*
User Service selector labels
*/}}
{{- define "vision-ai.userService.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: user-service
{{- end }}

{{/*
User Service service account name
*/}}
{{- define "vision-ai.userService.serviceAccountName" -}}
{{- if .Values.userService.serviceAccount.create }}
{{- default (include "vision-ai.userService.fullname" .) .Values.userService.serviceAccount.name }}
{{- else }}
{{- default "default" .Values.userService.serviceAccount.name }}
{{- end }}
{{- end }}

72. infrastructure/helm/vision-ai-platform/templates/_shared-inference.tpl
{{- define "vision-ai.sharedInference.name" -}}
{{- printf "%s-inference-gateway" .Release.Name -}}
{{- end -}}

{{- define "vision-ai.sharedInference.secret" -}}
{{- .Values.sharedInference.existingSecret | default (include "vision-ai.sharedInference.name" .) -}}
{{- end -}}

{{- define "vision-ai.sharedInference.policy" -}}
{{- $root := . -}}
{{- $runner := printf "http://%s:%d%s/api" (include "vision-ai.runner.fullname" .) (.Values.platform.runner.service.inferencePort | int) .Values.platform.runner.config.basePath -}}
{{- $environments := deepCopy .Values.sharedInference.environments -}}
{{- range $alias, $profile := $environments -}}
{{- if not (hasKey $profile "contracts") -}}
{{- $contracts := index $root.Values.sharedInference.environmentContracts $profile.bundle_sha256 | default list -}}
{{- $_ := set $profile "contracts" $contracts -}}
{{- end -}}
{{- end -}}
{{- dict "runner" (dict "api_url" $runner "gpu_uuid" .Values.autoLabeling.gpuUuid "resident_models" list "environments" $environments "managed_budget_bytes" .Values.sharedInference.managedBudgetBytes "native_onnx_enabled" .Values.sharedInference.nativeOnnxEnabled "reuse_installed_environments" .Values.sharedInference.reuseInstalledEnvironments "installed_environment_contracts" .Values.sharedInference.installedEnvironmentContracts) | toJson -}}
{{- end -}}

{{- define "vision-ai.sharedInference.labelerEnv" -}}
{{- $root := .root -}}
{{- $env := deepCopy .env -}}
{{- if $root.Values.sharedInference.enabled -}}
{{- if not $root.Values.autoLabeling.enabled -}}{{ fail "sharedInference requires autoLabeling.enabled" }}{{- end -}}
{{- $secret := include "vision-ai.sharedInference.secret" $root -}}
{{- $_ := set $env "SHARED_INFERENCE_ENABLED" "true" -}}
{{- $_ := set $env "ENABLE_MASK_ANNOTATIONS" (ternary "true" "false" $root.Values.sharedInference.enableMaskAnnotations) -}}
{{- $_ := set $env "INFERENCE_GATEWAY_API_URL" (printf "http://%s:8080" (include "vision-ai.sharedInference.name" $root)) -}}
{{- $_ := set $env "INFERENCE_GATEWAY_RUNNER_ID" "runner" -}}
{{- $_ := set $env "INFERENCE_GATEWAY_TOKEN" (dict "valueFrom" (dict "secretKeyRef" (dict "name" $secret "key" "INFERENCE_GATEWAY_TOKEN"))) -}}
{{- $_ := set $env "MODEL_CATALOG_API_URL" (printf "http://%s:%d%s" (include "vision-ai.backend.fullname" $root) ($root.Values.platform.backend.service.port | int) $root.Values.platform.backend.env.API_V1_PREFIX) -}}
{{- $_ := set $env "MODEL_ARTIFACT_ALLOWED_ORIGINS" (toJson $root.Values.sharedInference.artifactAllowedOrigins) -}}
{{- $_ := set $env "AUTO_LABELING_MODEL_BINDINGS_JSON" (toJson $root.Values.sharedInference.modelBindings) -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}
