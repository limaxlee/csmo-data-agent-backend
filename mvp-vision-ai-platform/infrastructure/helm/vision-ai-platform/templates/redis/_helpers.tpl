{{/* Leave room for the -headless / -data suffixes. */}}
{{- define "vision-ai.redis.fullname" -}}
{{- printf "%s-redis" (include "vision-ai.fullname" . | trunc 48 | trimSuffix "-") -}}
{{- end -}}

{{- define "vision-ai.redis.selectorLabels" -}}
app.kubernetes.io/name: {{ include "vision-ai.name" . }}
app.kubernetes.io/instance: {{ .Release.Name }}
app.kubernetes.io/component: redis
{{- end -}}

{{- define "vision-ai.redis.labels" -}}
{{ include "vision-ai.labels" . }}
{{ include "vision-ai.redis.selectorLabels" . }}
{{- end -}}

{{/* Copy the env map; cutover intentionally replaces even old explicit URLs.
     Worker overrides are merged BEFORE this helper, keeping producer/consumer
     Redis databases consistent. No change at all until connectApplications. */}}
{{- define "vision-ai.redis.applicationEnv" -}}
{{- $env := include "vision-ai.storage.applicationEnv" . | fromYaml -}}
{{- $env = include "vision-ai.internal.applicationEnv" (dict "root" .root "env" $env) | fromYaml -}}
{{- if .root.Values.redis.connectApplications -}}
{{- if not .root.Values.redis.enabled -}}
{{- fail "redis.connectApplications requires redis.enabled=true" -}}
{{- end -}}
{{- $url := printf "redis://%s.%s.svc.cluster.local:6379/%d" (include "vision-ai.redis.fullname" .root) .root.Release.Namespace (index .root.Values.redis.databases .database | int) -}}
{{- $_ := set $env "REDIS_URL" $url -}}
{{- end -}}
{{- toYaml $env -}}
{{- end -}}

