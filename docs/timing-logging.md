# Timing Logging

End-to-end timing instrumentation for agent runs. Every stage of a request — the runner invocation, each agent turn, each LLM API call, and each tool call — is logged with a `[TIMING]` prefix and elapsed time. Previously only the `/run` router endpoint logged timing; everything inside `Runner.run_async` was a black box.

## How it works

The instrumentation is a single ADK plugin, `TimingLoggerPlugin` (`data_agent/utils/timing_plugin.py`), built on `google.adk.plugins.BasePlugin`. A plugin attached to a `Runner` receives callbacks around every agent invocation, LLM call, and tool call for **all** agents under that runner — root and sub-agents alike — without modifying any agent definition.

It is attached to both runners:

- `RootAgentRunner` (`data_agent/runners/root_agent.py`) — the main `/run` flow
- `SystemAgentRunner` (`data_agent/runners/system_agent.py`) — session-title generation

```python
self._runner = Runner(
    agent=root_agent,
    app_name=AppNames.ROOT,
    session_service=self._session_service,
    artifact_service=artifact_service,
    plugins=[TimingLoggerPlugin()]
)
```

Sub-agents are covered automatically: in ADK 2.4.0, `AgentTool` propagates the parent runner's plugins into the sub-agent's inner runner by default (`include_plugins=True`). So the Milvus/MongoDB scanners' own LLM calls and MCP tool calls are logged too, under their own invocation ids, nested inside the parent's `tool START/END` lines.

## What gets logged

| Hook pair | Measures | Extra fields |
|---|---|---|
| `before_run_callback` / `after_run_callback` | The whole `run_async` invocation | `session=`, `user=`; the END line adds per-run totals: `llm_calls=` and `total_tokens(prompt/response/total)=`, including everything spent by sub-agents |
| `before_agent_callback` / `after_agent_callback` | Each agent's turn (root and sub-agents) | `agent=` |
| `before_model_callback` / `after_model_callback` | Each LLM API call | `tokens(prompt/response/total)=` from `usage_metadata` |
| `before_tool_callback` / `after_tool_callback` | Each tool call — MCP tools and `AgentTool` calls | `tool=`, `args=` (truncated to 200 chars) |
| `on_model_error_callback` / `on_tool_error_callback` | Failures | `FAILED` line with elapsed-until-failure and `error=` |

Every line carries `inv=<invocation_id>`, so a single request can be traced end-to-end with `grep inv=<id>` and correlated with the router's existing `[TIMING] /run API START/END` lines.

Example trace of one request (root agent delegating to the MongoDB scanner):

```
[TIMING] run START   inv=e3f1... session=abc user=u1 agent=root_orchestrator
[TIMING] agent START inv=e3f1... agent=root_orchestrator
[TIMING] llm START   inv=e3f1... agent=root_orchestrator
[TIMING] llm END     inv=e3f1... agent=root_orchestrator elapsed=2.31s tokens(prompt/response/total)=1450/89/1539
[TIMING] tool START  inv=e3f1... agent=root_orchestrator tool=mongodb_scanner args={'request': '...'}
[TIMING] run START   inv=f7a2... session=abc user=u1 agent=mongodb_scanner      <- sub-agent, own invocation id
[TIMING] llm END     inv=f7a2... agent=mongodb_scanner elapsed=1.87s tokens(prompt/response/total)=980/45/1025
[TIMING] tool START  inv=f7a2... agent=mongodb_scanner tool=find_documents args={'query': '...'}
[TIMING] tool END    inv=f7a2... agent=mongodb_scanner tool=find_documents elapsed=0.42s
[TIMING] run END     inv=f7a2... session=abc user=u1 agent=mongodb_scanner elapsed=5.44s llm_calls=2 total_tokens(prompt/response/total)=2100/255/2355
[TIMING] tool END    inv=e3f1... agent=root_orchestrator tool=mongodb_scanner elapsed=5.45s
[TIMING] llm END     inv=e3f1... agent=root_orchestrator elapsed=4.02s tokens(prompt/response/total)=3600/350/3950
[TIMING] agent END   inv=e3f1... agent=root_orchestrator elapsed=11.90s
[TIMING] run END     inv=e3f1... session=abc user=u1 agent=root_orchestrator elapsed=12.10s llm_calls=4 total_tokens(prompt/response/total)=7150/694/7844
```

The root agent's `run END` totals include the sub-agent's tokens: each run accumulates its own LLM calls, and when a sub-invocation (started by `AgentTool`) finishes, its totals are merged into its parent's. The parent link is tracked with a `contextvars.ContextVar`, which follows the async call chain — `AgentTool` awaits the sub-agent's runner inside the parent's tool call, so the sub-run sees the parent's invocation id even across task boundaries.

Token counts come from `llm_response.usage_metadata`, which ADK's `LiteLlm` populates from the `usage` block of the OpenAI-compatible model server's response (`prompt_tokens` → prompt, `completion_tokens` → response), in both streaming and non-streaming modes. If a response carries no usage block, the per-call line logs `tokens(...)=unknown` and the call still counts toward `llm_calls` with zero tokens.

## Where the logs go

The plugin logs at INFO through a standard module logger, so lines follow the same path as the rest of the app: the root logger configured by `initialize_logger` in `data_agent/__main__.py`, which writes to the console and to `logs/cosmo_data_agent.log` (rotating, and included in the zip served by the `/logs` endpoint).

## Implementation notes

- **Timer keys**: start times are kept in a dict keyed by `("run", invocation_id)`, `("agent", invocation_id, agent_name)`, `("model", invocation_id, agent_name)`, or `("tool", invocation_id, tool_name, function_call_id)`. The `function_call_id` in the tool key keeps parallel calls to the same tool independent.
- **Streaming**: `after_model_callback` skips partial streaming chunks (`llm_response.partial`) so only the completed response is timed.
- **Missing timers**: if an END fires without a matching START (e.g. a cached response), the line logs `elapsed=unknown` instead of failing.
- **Cleanup**: `after_run_callback` purges any leftover timer, usage, and parent-link entries for its invocation, so failed runs don't leak dict entries.
- **Non-intrusive**: every callback returns `None`, so the plugin never short-circuits or alters agent, model, or tool execution.
- **Deprecation**: `Runner(plugins=...)` is deprecated in ADK 2.4.0 in favor of `Runner(app=App(name=..., root_agent=..., plugins=[...]))`. It still works; migrating to the `App` form is a possible follow-up.

## Files changed

| File | Change |
|---|---|
| `data_agent/utils/timing_plugin.py` | New — `TimingLoggerPlugin` |
| `data_agent/utils/__init__.py` | Export `TimingLoggerPlugin` |
| `data_agent/runners/root_agent.py` | Attach plugin to the root `Runner` |
| `data_agent/runners/system_agent.py` | Attach plugin to the system `Runner` |
| `tests/utils/test_timing_plugin.py` | New — 17 unit tests |

## Tests

`tests/utils/test_timing_plugin.py` covers all hook pairs (START/END lines, elapsed format), token-usage logging, per-run totals and sub-invocation roll-up, arg truncation, partial-response skipping, parallel tool-call keying, error paths, timer purging, and that no callback returns a value. The plugin was also verified end-to-end against a real ADK 2.4.0 `Runner` with a stub model.

Note: running the whole suite with pytest 9 requires `--import-mode=importlib` because of pre-existing duplicate test basenames across folders (e.g. `tests/agents/test_root_agent.py` vs `tests/runners/test_root_agent.py`) with no `__init__.py` in the test dirs — unrelated to this change.
