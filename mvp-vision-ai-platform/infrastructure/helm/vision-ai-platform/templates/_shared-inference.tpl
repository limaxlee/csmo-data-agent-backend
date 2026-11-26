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

