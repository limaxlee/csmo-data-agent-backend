import time
import logging
from contextvars import ContextVar
from typing import Any, Optional

from google.genai import types
from google.adk.agents.base_agent import BaseAgent
from google.adk.agents.callback_context import CallbackContext
from google.adk.agents.invocation_context import InvocationContext
from google.adk.models.llm_request import LlmRequest
from google.adk.models.llm_response import LlmResponse
from google.adk.plugins import BasePlugin
from google.adk.tools.base_tool import BaseTool
from google.adk.tools.tool_context import ToolContext

logger = logging.getLogger(__name__)

MAX_TOOL_ARGS_LENGTH = 200

# Tracks the invocation the current async task is running in, so a sub-agent
# invocation (AgentTool runs the sub-agent's runner within the parent's tool
# call) can be linked back to its parent for token roll-up.
_current_invocation: ContextVar[Optional[str]] = ContextVar("timing_current_invocation", default=None)


class _UsageTotals:
    __slots__ = ("llm_calls", "prompt_tokens", "response_tokens", "total_tokens")

    def __init__(self):
        self.llm_calls = 0
        self.prompt_tokens = 0
        self.response_tokens = 0
        self.total_tokens = 0

    def add_response(self, llm_response: LlmResponse):
        self.llm_calls += 1
        usage = llm_response.usage_metadata
        if usage is None:
            return
        self.prompt_tokens += usage.prompt_token_count or 0
        self.response_tokens += usage.candidates_token_count or 0
        self.total_tokens += usage.total_token_count or 0

    def merge(self, other: "_UsageTotals"):
        self.llm_calls += other.llm_calls
        self.prompt_tokens += other.prompt_tokens
        self.response_tokens += other.response_tokens
        self.total_tokens += other.total_tokens

    def __str__(self):
        return (
            f"llm_calls={self.llm_calls} "
            f"total_tokens(prompt/response/total)={self.prompt_tokens}/{self.response_tokens}/{self.total_tokens}"
        )


class TimingLoggerPlugin(BasePlugin):
    """Logs START/END lines with elapsed time for every stage of an agent invocation:
    the runner run itself, each agent turn (root and sub-agents entered via AgentTool),
    each LLM API call (with token usage), and each tool call (AgentTool and MCP tools).

    All lines carry the invocation id, so a single request can be traced end-to-end
    with `grep inv=<id>` and correlated with the router's [TIMING] request logs.
    """

    def __init__(self, name: str = "timing_logger"):
        super().__init__(name=name)
        self._timers: dict[tuple, float] = {}
        self._usage: dict[str, _UsageTotals] = {}
        self._parents: dict[str, str] = {}

    def _start(self, key: tuple):
        self._timers[key] = time.monotonic()

    def _elapsed(self, key: tuple) -> str:
        started = self._timers.pop(key, None)
        if started is None:
            return "unknown"
        return f"{time.monotonic() - started:.2f}s"

    @staticmethod
    def _tool_key(tool: BaseTool, tool_context: ToolContext) -> tuple:
        return "tool", tool_context.invocation_id, tool.name, tool_context.function_call_id

    @staticmethod
    def _summarize_args(tool_args: dict[str, Any]) -> str:
        args = repr(tool_args)
        if len(args) > MAX_TOOL_ARGS_LENGTH:
            args = args[:MAX_TOOL_ARGS_LENGTH] + "...(truncated)"
        return args

    @staticmethod
    def _summarize_usage(llm_response: LlmResponse) -> str:
        usage = llm_response.usage_metadata
        if usage is None:
            return "unknown"
        return f"{usage.prompt_token_count}/{usage.candidates_token_count}/{usage.total_token_count}"

    async def before_run_callback(self, *, invocation_context: InvocationContext) -> Optional[types.Content]:
        invocation_id = invocation_context.invocation_id
        self._start(("run", invocation_id))
        self._usage[invocation_id] = _UsageTotals()

        parent_invocation_id = _current_invocation.get()
        if parent_invocation_id is not None:
            self._parents[invocation_id] = parent_invocation_id
        _current_invocation.set(invocation_id)

        logger.info(
            f"[TIMING] run START inv={invocation_context.invocation_id} "
            f"session={invocation_context.session.id} user={invocation_context.user_id} "
            f"agent={invocation_context.agent.name}"
        )

    async def after_run_callback(self, *, invocation_context: InvocationContext) -> None:
        invocation_id = invocation_context.invocation_id
        elapsed = self._elapsed(("run", invocation_id))
        totals = self._usage.pop(invocation_id, None) or _UsageTotals()
        logger.info(
            f"[TIMING] run END inv={invocation_id} "
            f"session={invocation_context.session.id} user={invocation_context.user_id} "
            f"agent={invocation_context.agent.name} elapsed={elapsed} {totals}"
        )

        parent_invocation_id = self._parents.pop(invocation_id, None)
        if parent_invocation_id is not None and parent_invocation_id in self._usage:
            self._usage[parent_invocation_id].merge(totals)
        _current_invocation.set(parent_invocation_id)

        self._purge_invocation(invocation_id)

    def _purge_invocation(self, invocation_id: str):
        for key in [key for key in self._timers if len(key) > 1 and key[1] == invocation_id]:
            self._timers.pop(key, None)
        self._usage.pop(invocation_id, None)
        self._parents.pop(invocation_id, None)

    async def before_agent_callback(
            self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        self._start(("agent", callback_context.invocation_id, agent.name))
        logger.info(f"[TIMING] agent START inv={callback_context.invocation_id} agent={agent.name}")

    async def after_agent_callback(
            self, *, agent: BaseAgent, callback_context: CallbackContext
    ) -> Optional[types.Content]:
        elapsed = self._elapsed(("agent", callback_context.invocation_id, agent.name))
        logger.info(f"[TIMING] agent END inv={callback_context.invocation_id} agent={agent.name} elapsed={elapsed}")

    async def before_model_callback(
            self, *, callback_context: CallbackContext, llm_request: LlmRequest
    ) -> Optional[LlmResponse]:
        self._start(("model", callback_context.invocation_id, callback_context.agent_name))
        logger.info(
            f"[TIMING] llm START inv={callback_context.invocation_id} agent={callback_context.agent_name}"
        )

    async def after_model_callback(
            self, *, callback_context: CallbackContext, llm_response: LlmResponse
    ) -> Optional[LlmResponse]:
        if llm_response.partial:
            return None

        elapsed = self._elapsed(("model", callback_context.invocation_id, callback_context.agent_name))
        totals = self._usage.get(callback_context.invocation_id)
        if totals is not None:
            totals.add_response(llm_response)
        logger.info(
            f"[TIMING] llm END inv={callback_context.invocation_id} agent={callback_context.agent_name} "
            f"elapsed={elapsed} tokens(prompt/response/total)={self._summarize_usage(llm_response)}"
        )

    async def on_model_error_callback(
            self, *, callback_context: CallbackContext, llm_request: LlmRequest, error: Exception
    ) -> Optional[LlmResponse]:
        elapsed = self._elapsed(("model", callback_context.invocation_id, callback_context.agent_name))
        logger.error(
            f"[TIMING] llm FAILED inv={callback_context.invocation_id} agent={callback_context.agent_name} "
            f"elapsed={elapsed} error={error}"
        )

    async def before_tool_callback(
            self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext
    ) -> Optional[dict]:
        self._start(self._tool_key(tool, tool_context))
        logger.info(
            f"[TIMING] tool START inv={tool_context.invocation_id} agent={tool_context.agent_name} "
            f"tool={tool.name} args={self._summarize_args(tool_args)}"
        )

    async def after_tool_callback(
            self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, result: dict
    ) -> Optional[dict]:
        elapsed = self._elapsed(self._tool_key(tool, tool_context))
        logger.info(
            f"[TIMING] tool END inv={tool_context.invocation_id} agent={tool_context.agent_name} "
            f"tool={tool.name} elapsed={elapsed}"
        )

    async def on_tool_error_callback(
            self, *, tool: BaseTool, tool_args: dict[str, Any], tool_context: ToolContext, error: Exception
    ) -> Optional[dict]:
        elapsed = self._elapsed(self._tool_key(tool, tool_context))
        logger.error(
            f"[TIMING] tool FAILED inv={tool_context.invocation_id} agent={tool_context.agent_name} "
            f"tool={tool.name} elapsed={elapsed} error={error}"
        )
