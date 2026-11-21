{{/* Preserve scalar env values; objects use Kubernetes valueFrom references. */}}
{{- define "vision-ai.env.entry" -}}
- name: {{ .name }}
{{- if kindIs "map" .value }}
{{- if or (not (hasKey .value "valueFrom")) (ne (len .value) 1) }}
{{- fail (printf "env.%s must be a scalar or {valueFrom: {...}}" .name) }}
{{- end }}
{{- if not (kindIs "map" .value.valueFrom) }}
{{- fail (printf "env.%s.valueFrom must contain one Kubernetes reference" .name) }}
{{- end }}
{{- if ne (len .value.valueFrom) 1 }}
{{- fail (printf "env.%s.valueFrom must contain one Kubernetes reference" .name) }}
{{- end }}
{{- range $kind, $ref := .value.valueFrom }}
{{- if not (has $kind (list "secretKeyRef" "configMapKeyRef" "fieldRef" "resourceFieldRef")) }}
{{- fail (printf "env.%s.valueFrom contains an unsupported reference" $.name) }}
{{- end }}
{{- if not (kindIs "map" $ref) }}
{{- fail "env valueFrom reference must be an object" }}
{{- end }}
{{- if and (has $kind (list "secretKeyRef" "configMapKeyRef")) (or (not $ref.name) (not $ref.key)) }}
{{- fail "env secretKeyRef/configMapKeyRef requires name and key" }}
{{- end }}
{{- end }}
  valueFrom:
    {{- toYaml .value.valueFrom | nindent 4 }}
{{- else }}
  value: {{ .value | quote }}
{{- end }}
{{- end -}}

{{/* Explicit opt-in only; shared S3 settings win over component env values. */}}
{{- define "vision-ai.storage.applicationEnv" -}}
{{- $env := deepCopy (default (dict) .env) -}}
{{- if .root.Values.storage.connectApplications -}}
{{- range $key, $value := .root.Values.storage.env -}}
{{- if not (hasPrefix "S3_" $key) -}}
{{- fail "storage.env supports only S3_* keys" -}}
{{- end -}}
{{- $_ := set $env $key $value -}}
{{- end -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}

{{/* Release-local defaults apply only to empty endpoint values. */}}
{{- define "vision-ai.internal.applicationEnv" -}}
{{- $env := deepCopy (default (dict) .env) -}}
{{- $defaults := dict
  "DICE_API_URL" (printf "http://%s.%s.svc.cluster.local:%d" (include "vision-ai.backend.fullname" .root) .root.Release.Namespace (.root.Values.platform.backend.service.port | int))
  "DICE_LABELER_API_URL" (ternary (printf "http://%s-backend.%s.svc.cluster.local:%d/labeler/api/v1" (include "vision-ai.labeler.fullname" .root) .root.Release.Namespace (.root.Values.labeler.backend.port | int)) "" .root.Values.labeler.enabled)
  "DICE_ACTIVATION_API_URL" (printf "http://%s.%s.svc.cluster.local:%d/activation" (include "vision-ai.webAuth.fullname" .root) .root.Release.Namespace (.root.Values.webAuth.service.port | int))
  "DASHBOARD_MCP_URL" (printf "http://%s:%d%s" (include "vision-ai.dashboardMcp.fullname" .root) (.root.Values.platform.dashboardMcp.service.port | int) .root.Values.platform.dashboardMcp.basePath)
  "BOT_BACKEND_URL" (printf "http://%s:%d%s" (include "vision-ai.diceBot.fullname" .root) (.root.Values.diceBot.service.port | int) .root.Values.diceBot.baseUrl)
  "DICE_RUNNER_BASE_URL" (printf "http://%s:%d%s/api" (include "vision-ai.runner.fullname" .root) (.root.Values.platform.runner.service.inferencePort | int) .root.Values.platform.runner.config.basePath)
  -}}
{{- range $key, $value := $defaults -}}
{{- if and (hasKey $env $key) (not (index $env $key)) -}}
{{- $_ := set $env $key $value -}}
{{- end -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}

