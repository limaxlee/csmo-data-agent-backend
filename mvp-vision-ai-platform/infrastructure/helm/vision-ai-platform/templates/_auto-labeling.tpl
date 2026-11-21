{{/* Auto-labeling is values-driven: enabled wherever the wiring below exists. */}}
{{- define "vision-ai.autoLabeling.enabled" -}}
{{- .Values.autoLabeling.enabled -}}
{{- end -}}

{{- define "vision-ai.autoLabeling.backendExecution" -}}
{{- and (eq (include "vision-ai.autoLabeling.enabled" .) "true") (eq .Values.autoLabeling.executionMode "backend") -}}
{{- end -}}

{{- define "vision-ai.autoLabeling.platformEnv" -}}
{{- $root := .root -}}
{{- $env := deepCopy .env -}}
{{- if eq (include "vision-ai.autoLabeling.enabled" $root) "true" -}}
{{- $preset := $root.Values.autoLabeling -}}
{{- $slot := required "autoLabeling.slotId is required" $preset.slotId -}}
{{- $_ := set $env "AUTO_LABELING_EXECUTION_MODE" $preset.executionMode -}}
{{- $runner := include "vision-ai.runner.fullname" $root -}}
{{- $target := printf "http://%s:%d%s/api" $runner ($root.Values.platform.runner.service.inferencePort | int) $root.Values.platform.runner.config.basePath -}}
{{- range $key, $value := dict "AUTO_LABELING_BATCH_ENABLED" "true" "GPU_QUEUE_ENABLED" "true" "GPU_RUNNER_MODE" "persistent" "INFERENCE_CACHE_DIR" "/var/lib/platform/inference-cache" -}}
{{- $_ := set $env $key $value -}}
{{- end -}}
{{- $_ := set $env "AUTO_LABELING_ENVIRONMENT_JSON" (toJson $preset.environment) -}}
{{- $_ := set $env "INFERENCE_BUNDLE_SOURCE_BUCKET" $preset.bundleSourceBucket -}}
{{- $_ := set $env "INFERENCE_BUNDLE_SOURCE_KEY" $preset.bundleSourceKey -}}
{{- $_ := set $env "GPU_QUEUE_SLOTS_JSON" (toJson (list (dict "id" $slot "physical_gpu_id" $preset.gpuUuid))) -}}
{{- $_ := set $env "GPU_MANAGED_RUNNERS_JSON" (toJson (list (dict "slot_id" $slot "instance_id" $runner "api_url" $target "exclusive" true))) -}}
{{- $_ := set $env "GPU_RUNNER_CONTAINERS_JSON" "[]" -}}
{{- $_ := set $env "GPU_RUNNER_API_KEY" (dict "valueFrom" (dict "secretKeyRef" (include "vision-ai.autoLabeling.managedKeyRef" $root | fromYaml))) -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}

{{- define "vision-ai.autoLabeling.labelerEnv" -}}
{{- $root := .root -}}
{{- $env := deepCopy .env -}}
{{- if eq (include "vision-ai.autoLabeling.enabled" $root) "true" -}}
{{- $_ := set $env "AUTO_LABELING_EXECUTION_MODE" $root.Values.autoLabeling.executionMode -}}
{{- $_ := set $env "AUTO_LABELING_EXECUTION_ENABLED" "true" -}}
{{- $_ := set $env "RUN_MIGRATIONS" "false" -}}
{{- $_ := set $env "PLATFORM_INFERENCE_API_URL" (printf "http://%s:%d%s" (include "vision-ai.backend.fullname" $root) ($root.Values.platform.backend.service.port | int) $root.Values.platform.backend.env.API_V1_PREFIX) -}}
{{- $_ := set $env "AUTO_LABELING_GPU_SLOT" (required "autoLabeling.slotId is required" $root.Values.autoLabeling.slotId) -}}
{{- end -}}
{{- $env = include "vision-ai.sharedInference.labelerEnv" (dict "root" $root "env" $env) | fromYaml -}}
{{- toYaml $env -}}
{{- end -}}

{{- define "vision-ai.autoLabeling.platformSecrets" -}}
{{- range $key, $value := . -}}
{{- if kindIs "map" $value -}}
{{ include "vision-ai.env.entry" (dict "name" $key "value" $value) }}
{{ end -}}
{{- end -}}
{{- end -}}
 end -}}

{{/* Both controller peers must consume the same dedicated Secret reference. */}}
{{- define "vision-ai.autoLabeling.managedKeyRef" -}}
{{- $secret := .Values.autoLabeling.managedKeySecret | default dict -}}
{{- $key := required "autoLabeling.managedKeySecret.key is required" (get $secret "key") -}}
name: {{ get $secret "name" | default (printf "%s-runtime" .Release.Name) | quote }}
key: {{ $key | quote }}
{{- end -}}
