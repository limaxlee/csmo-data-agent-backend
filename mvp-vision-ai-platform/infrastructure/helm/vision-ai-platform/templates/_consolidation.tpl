{{/* Preserve production topology; stage can opt out for rollback. */}}
{{- define "vision-ai.consolidation.enabled" -}}
{{- and .Values.labeler.enabled (or .Values.workloadConsolidation.enabled (and (eq .Release.Namespace "dice-stage") .Values.workloadConsolidation.staging.enabled)) -}}
{{- end -}}

{{- define "vision-ai.srBuild.backend" -}}
{{- $mode := .Values.labeler.srBuildWorker.executionMode }}
{{- if not (has $mode (list "auto" "backend" "rq")) }}
{{- fail "labeler.srBuildWorker.executionMode must be auto, backend or rq" }}
{{- end }}
{{- and .Values.labeler.enabled .Values.labeler.srBuildWorker.enabled (or (eq $mode "backend") (and (eq $mode "auto") (eq (include "vision-ai.consolidation.enabled" .) "true"))) -}}
{{- end -}}

{{/* Existing worker image, command, environment and limits remain per container. */}}
{{- define "vision-ai.consolidation.worker" -}}
{{- $root := .root }}
{{- $worker := .worker }}
{{- $imageRepository := default $root.Values.labeler.backend.image.repository $worker.image.repository }}
{{- $imageTag := default $root.Values.labeler.backend.image.tag $worker.image.tag }}
{{- $env := mergeOverwrite (deepCopy $root.Values.labeler.backend.env) $worker.env }}
{{- $env = include "vision-ai.redis.applicationEnv" (dict "root" $root "env" $env "database" "labeler") | fromYaml }}
- name: {{ .name }}
  image: "{{ $imageRepository }}:{{ $imageTag }}"
  {{- with $worker.image.pullPolicy }}
  imagePullPolicy: {{ . }}
  {{- end }}
  {{- with $worker.command }}
  command:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- with $worker.args }}
  args:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  {{- $ctx := default $root.Values.labeler.backend.securityContext $worker.securityContext }}
  {{- with omit $ctx "fsGroup" "fsGroupChangePolicy" "supplementalGroups" "sysctls" }}
  securityContext:
    {{- toYaml . | nindent 4 }}
  {{- end }}
  env:
    {{- range $key, $value := $env }}
    {{- include "vision-ai.env.entry" (dict "name" $key "value" $value) | nindent 4 }}
    {{- end }}
  {{- with $worker.resources }}
  resources:
    {{- toYaml . | nindent 4 }}
  {{- end }}
{{- end -}}

{{/* Merge only compatible operation workers; imports and SR keep their own consumers. */}}
{{- define "vision-ai.consolidation.operations" -}}
{{- $root := . }}
{{- $env := dict }}
{{- $roles := list }}
{{- $image := dict }}
{{- $security := dict }}
{{- range $key, $role := dict "bulkWorker" "bulk" "publishWorker" "publish" }}
{{- $worker := index $root.Values.labeler $key }}
{{- if $worker.enabled }}
{{- $expectedModule := ternary "app.annotation.infrastructure.bulk_assignment_worker" "app.versioning.infrastructure.publish_worker" (eq $role "bulk") }}
{{- if or (ne (toJson $worker.command) (toJson (list "python" "-m" $expectedModule))) $worker.args }}
{{- fail (printf "Consolidated %s must use its standard worker command" $key) }}
{{- end }}
{{- $candidateImage := dict "repository" (default $root.Values.labeler.backend.image.repository $worker.image.repository) "tag" (default $root.Values.labeler.backend.image.tag $worker.image.tag) "pullPolicy" $worker.image.pullPolicy }}
{{- $candidateSecurity := default $root.Values.labeler.backend.securityContext $worker.securityContext }}
{{- if and $roles (or (ne (toJson $image) (toJson $candidateImage)) (ne (toJson $security) (toJson $candidateSecurity))) }}
{{- fail "Consolidated bulk/publish workers must share an image and security context" }}
{{- end }}
{{- $image = $candidateImage }}
{{- $security = $candidateSecurity }}
{{- range $name, $value := $worker.env }}
{{- if and (hasKey $env $name) (ne (toJson (index $env $name)) (toJson $value)) }}
{{- fail (printf "Consolidated bulk/publish environment conflict at %s" $name) }}
{{- end }}
{{- $_ := set $env $name $value }}
{{- end }}
{{- $roles = append $roles $role }}
{{- end }}
{{- end }}
{{- if $roles }}
{{- if has "publish" $roles }}
{{- $publishEnv := index $root.Values.labeler "publishWorker" "env" | default dict }}
{{- $backendEnv := $root.Values.labeler.backend.env | default dict }}
{{- $cacheWarmupUrl := index $publishEnv "PLATFORM_DATASET_CACHE_WARMUP_URL" | default (index $backendEnv "PLATFORM_DATASET_CACHE_WARMUP_URL") | default (include "vision-ai.datasetCache.warmupUrl" $root) }}
{{- if $cacheWarmupUrl }}
{{- $_ := set $env "PLATFORM_DATASET_CACHE_WARMUP_URL" $cacheWarmupUrl }}
{{- end }}
{{- end }}
{{- $worker := dict "image" $image "securityContext" $security "env" $env "command" (list "uv" "run" "--no-project" "--no-sync" "python" "-m" "app.core.operations_worker") "args" $roles "resources" .Values.workloadConsolidation.operationsWorkerResources }}
{{- include "vision-ai.consolidation.worker" (dict "root" . "worker" $worker "name" "operations-worker") }}
{{- end }}
{{- end -}}
