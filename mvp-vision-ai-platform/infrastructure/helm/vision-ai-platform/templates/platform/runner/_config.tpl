{{/* Initial configuration only; runtime edits live on the Runner data volume. */}}
{{- define "vision-ai.runner.configToml" -}}
# Single-port (unified) bind on all interfaces. The compiled-in default is
# unified 127.0.0.1:5002 (a loopback desktop default), and providing split
# inference/management addresses does NOT clear that default — so we must set
# unified_address explicitly or the pod binds loopback:5002 and is
# unreachable via the Service. Everything (probes included) talks to
# the runner on this one port under base_path/api.
unified_address = "http://0.0.0.0:{{ .Values.platform.runner.service.inferenceTargetPort }}"

disable_token_authorization = {{ .Values.platform.runner.config.disableTokenAuthorization }}
# Apply TS_* env overrides (see runner/config.example.toml). Off by
# default in the runner.
enable_envvars_config = {{ .Values.platform.runner.config.enableEnvvarsConfig }}
enable_model_api = {{ .Values.platform.runner.config.enableModelApi }}
enable_env_api = {{ .Values.platform.runner.config.enableEnvApi }}
base_path = {{ .Values.platform.runner.config.basePath | default "" | quote }}

data_dir = {{ .Values.platform.runner.config.dataDir | quote }}
{{- with .Values.platform.runner.config.loadModels }}
load_models = [
  {{- range . }}
  {{ . | quote }},
  {{- end }}
]
{{- end }}

default_workers_per_model = {{ .Values.platform.runner.config.defaultWorkersPerModel }}
default_response_timeout = {{ .Values.platform.runner.config.defaultResponseTimeout }}
default_startup_timeout = {{ .Values.platform.runner.config.defaultStartupTimeout }}
job_queue_size = {{ .Values.platform.runner.config.jobQueueSize }}
max_request_size = {{ .Values.platform.runner.config.maxRequestSize }}
max_response_size = {{ .Values.platform.runner.config.maxResponseSize }}
async_logging = {{- if hasKey .Values.platform.runner.config "asyncLogging" }} {{ .Values.platform.runner.config.asyncLogging }}{{- else }} true{{- end }}

metrics_mode = {{ .Values.platform.runner.config.metricsMode | quote }}
system_metrics_interval_secs = {{ .Values.platform.runner.config.systemMetricsIntervalSecs }}
metrics_archive_enabled = {{ .Values.platform.runner.config.metricsArchiveEnabled }}
metrics_archive_interval_secs = {{ .Values.platform.runner.config.metricsArchiveIntervalSecs }}
metrics_archive_retention_days = {{ .Values.platform.runner.config.metricsArchiveRetentionDays }}

number_of_gpu = {{ .Values.platform.runner.config.numberOfGpu }}

[python_envs]
{{- range $name, $path := .Values.platform.runner.config.pythonEnvs }}
{{ $name | quote }} = {{ $path | quote }}
{{- end }}
{{- with .Values.platform.runner.config.extraToml }}

{{ . | nindent 4 }}
{{- end }}
{{- end -}}
