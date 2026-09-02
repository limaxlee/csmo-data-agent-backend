import re
import pytest
import logging

from data_agent.utils.timing_plugin import TimingLoggerPlugin, MAX_TOOL_ARGS_LENGTH

ELAPSED_PATTERN = re.compile(r"elapsed=(\d+\.\d+)s")


def _invocation_context(mocker, invocation_id="inv-1"):
    context = mocker.MagicMock()
    context.invocation_id = invocation_id
    context.session.id = "session-1"
    context.user_id = "user-1"
    context.agent.name = "root_orchestrator"
    return context


def _callback_context(mocker, invocation_id="inv-1", agent_name="root_orchestrator"):
    context = mocker.MagicMock()
    context.invocation_id = invocation_id
    context.agent_name = agent_name
    return context


def _tool_context(mocker, invocation_id="inv-1", agent_name="root_orchestrator", function_call_id="call-1"):
    context = _callback_context(mocker, invocation_id=invocation_id, agent_name=agent_name)
    context.function_call_id = function_call_id
    return context


def _tool(mocker, name="find_documents"):
    tool = mocker.MagicMock()
    tool.name = name
    return tool


def _llm_response(mocker, partial=None, usage=True):
    response = mocker.MagicMock()
    response.partial = partial
    if usage:
        response.usage_metadata = mocker.MagicMock(
            prompt_token_count=100,
            candidates_token_count=20,
            total_token_count=120
        )
    else:
        response.usage_metadata = None
    return response


@pytest.fixture
def plugin():
    return TimingLoggerPlugin()


class TestRunCallbacks:
    @pytest.mark.asyncio
    async def test_logs_run_start_and_end_with_elapsed(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        context = _invocation_context(mocker)

        await plugin.before_run_callback(invocation_context=context)
        await plugin.after_run_callback(invocation_context=context)

        start_line, end_line = caplog.messages
        assert "[TIMING] run START inv=inv-1 session=session-1 user=user-1" in start_line
        assert "[TIMING] run END inv=inv-1" in end_line
        assert ELAPSED_PATTERN.search(end_line)

    @pytest.mark.asyncio
    async def test_after_run_purges_leftover_timers_of_invocation(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        context = _invocation_context(mocker)

        await plugin.before_run_callback(invocation_context=context)
        await plugin.before_agent_callback(agent=_tool(mocker, name="root_orchestrator"),
                                           callback_context=_callback_context(mocker))
        await plugin.before_model_callback(callback_context=_callback_context(mocker),
                                           llm_request=mocker.MagicMock())
        await plugin.after_run_callback(invocation_context=context)

        assert plugin._timers == {}

    @pytest.mark.asyncio
    async def test_after_run_keeps_timers_of_other_invocations(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)

        await plugin.before_run_callback(invocation_context=_invocation_context(mocker, invocation_id="inv-1"))
        await plugin.before_run_callback(invocation_context=_invocation_context(mocker, invocation_id="inv-2"))
        await plugin.after_run_callback(invocation_context=_invocation_context(mocker, invocation_id="inv-1"))

        assert ("run", "inv-2") in plugin._timers


class TestPerRunTotals:
    @pytest.mark.asyncio
    async def test_run_end_logs_accumulated_token_totals(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        invocation_context = _invocation_context(mocker)
        callback_context = _callback_context(mocker)

        await plugin.before_run_callback(invocation_context=invocation_context)
        for _ in range(2):
            await plugin.before_model_callback(callback_context=callback_context, llm_request=mocker.MagicMock())
            await plugin.after_model_callback(callback_context=callback_context, llm_response=_llm_response(mocker))
        await plugin.after_run_callback(invocation_context=invocation_context)

        end_line = caplog.messages[-1]
        assert "llm_calls=2" in end_line
        assert "total_tokens(prompt/response/total)=200/40/240" in end_line

    @pytest.mark.asyncio
    async def test_run_end_counts_calls_without_usage_metadata(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        invocation_context = _invocation_context(mocker)
        callback_context = _callback_context(mocker)

        await plugin.before_run_callback(invocation_context=invocation_context)
        await plugin.after_model_callback(callback_context=callback_context,
                                          llm_response=_llm_response(mocker, usage=False))
        await plugin.after_run_callback(invocation_context=invocation_context)

        end_line = caplog.messages[-1]
        assert "llm_calls=1" in end_line
        assert "total_tokens(prompt/response/total)=0/0/0" in end_line

    @pytest.mark.asyncio
    async def test_sub_invocation_totals_roll_up_into_parent(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        parent_run = _invocation_context(mocker, invocation_id="inv-parent")
        child_run = _invocation_context(mocker, invocation_id="inv-child")

        await plugin.before_run_callback(invocation_context=parent_run)
        await plugin.after_model_callback(callback_context=_callback_context(mocker, invocation_id="inv-parent"),
                                          llm_response=_llm_response(mocker))

        await plugin.before_run_callback(invocation_context=child_run)
        await plugin.after_model_callback(callback_context=_callback_context(mocker, invocation_id="inv-child"),
                                          llm_response=_llm_response(mocker))
        await plugin.after_run_callback(invocation_context=child_run)

        await plugin.after_run_callback(invocation_context=parent_run)

        child_end, parent_end = caplog.messages[-2], caplog.messages[-1]
        assert "inv=inv-child" in child_end
        assert "llm_calls=1" in child_end
        assert "total_tokens(prompt/response/total)=100/20/120" in child_end
        assert "inv=inv-parent" in parent_end
        assert "llm_calls=2" in parent_end
        assert "total_tokens(prompt/response/total)=200/40/240" in parent_end

    @pytest.mark.asyncio
    async def test_run_end_purges_usage_and_parent_state(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        parent_run = _invocation_context(mocker, invocation_id="inv-parent")
        child_run = _invocation_context(mocker, invocation_id="inv-child")

        await plugin.before_run_callback(invocation_context=parent_run)
        await plugin.before_run_callback(invocation_context=child_run)
        await plugin.after_run_callback(invocation_context=child_run)
        await plugin.after_run_callback(invocation_context=parent_run)

        assert plugin._usage == {}
        assert plugin._parents == {}


class TestAgentCallbacks:
    @pytest.mark.asyncio
    async def test_logs_agent_start_and_end(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        agent = _tool(mocker, name="mongodb_scanner")
        context = _callback_context(mocker)

        await plugin.before_agent_callback(agent=agent, callback_context=context)
        await plugin.after_agent_callback(agent=agent, callback_context=context)

        start_line, end_line = caplog.messages
        assert "[TIMING] agent START inv=inv-1 agent=mongodb_scanner" in start_line
        assert "[TIMING] agent END inv=inv-1 agent=mongodb_scanner" in end_line
        assert ELAPSED_PATTERN.search(end_line)


class TestModelCallbacks:
    @pytest.mark.asyncio
    async def test_logs_llm_start_and_end_with_token_usage(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        context = _callback_context(mocker)

        await plugin.before_model_callback(callback_context=context, llm_request=mocker.MagicMock())
        await plugin.after_model_callback(callback_context=context, llm_response=_llm_response(mocker))

        start_line, end_line = caplog.messages
        assert "[TIMING] llm START inv=inv-1 agent=root_orchestrator" in start_line
        assert "[TIMING] llm END inv=inv-1 agent=root_orchestrator" in end_line
        assert "tokens(prompt/response/total)=100/20/120" in end_line
        assert ELAPSED_PATTERN.search(end_line)

    @pytest.mark.asyncio
    async def test_skips_partial_streaming_responses(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        context = _callback_context(mocker)

        await plugin.before_model_callback(callback_context=context, llm_request=mocker.MagicMock())
        await plugin.after_model_callback(callback_context=context, llm_response=_llm_response(mocker, partial=True))

        assert len(caplog.messages) == 1
        assert ("model", "inv-1", "root_orchestrator") in plugin._timers

    @pytest.mark.asyncio
    async def test_logs_unknown_elapsed_and_usage_when_missing(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)

        await plugin.after_model_callback(
            callback_context=_callback_context(mocker),
            llm_response=_llm_response(mocker, usage=False)
        )

        assert "elapsed=unknown" in caplog.messages[0]
        assert "tokens(prompt/response/total)=unknown" in caplog.messages[0]

    @pytest.mark.asyncio
    async def test_logs_llm_failure_with_elapsed(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        context = _callback_context(mocker)

        await plugin.before_model_callback(callback_context=context, llm_request=mocker.MagicMock())
        await plugin.on_model_error_callback(
            callback_context=context,
            llm_request=mocker.MagicMock(),
            error=RuntimeError("API timeout")
        )

        failure_line = caplog.messages[-1]
        assert "[TIMING] llm FAILED inv=inv-1 agent=root_orchestrator" in failure_line
        assert "error=API timeout" in failure_line
        assert ELAPSED_PATTERN.search(failure_line)


class TestToolCallbacks:
    @pytest.mark.asyncio
    async def test_logs_tool_start_and_end(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        tool = _tool(mocker)
        context = _tool_context(mocker)

        await plugin.before_tool_callback(tool=tool, tool_args={"query": "test"}, tool_context=context)
        await plugin.after_tool_callback(tool=tool, tool_args={"query": "test"}, tool_context=context, result={})

        start_line, end_line = caplog.messages
        assert "[TIMING] tool START inv=inv-1 agent=root_orchestrator tool=find_documents" in start_line
        assert "args={'query': 'test'}" in start_line
        assert "[TIMING] tool END inv=inv-1 agent=root_orchestrator tool=find_documents" in end_line
        assert ELAPSED_PATTERN.search(end_line)

    @pytest.mark.asyncio
    async def test_truncates_long_tool_args(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)

        await plugin.before_tool_callback(
            tool=_tool(mocker),
            tool_args={"query": "x" * 500},
            tool_context=_tool_context(mocker)
        )

        assert "...(truncated)" in caplog.messages[0]
        assert "x" * 500 not in caplog.messages[0]

    @pytest.mark.asyncio
    async def test_parallel_tool_calls_use_independent_timers(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        tool = _tool(mocker)
        first_call = _tool_context(mocker, function_call_id="call-1")
        second_call = _tool_context(mocker, function_call_id="call-2")

        await plugin.before_tool_callback(tool=tool, tool_args={}, tool_context=first_call)
        await plugin.before_tool_callback(tool=tool, tool_args={}, tool_context=second_call)
        await plugin.after_tool_callback(tool=tool, tool_args={}, tool_context=first_call, result={})

        end_line = caplog.messages[-1]
        assert "elapsed=unknown" not in end_line
        assert ("tool", "inv-1", "find_documents", "call-2") in plugin._timers

    @pytest.mark.asyncio
    async def test_logs_tool_failure_with_elapsed(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        tool = _tool(mocker)
        context = _tool_context(mocker)

        await plugin.before_tool_callback(tool=tool, tool_args={}, tool_context=context)
        await plugin.on_tool_error_callback(
            tool=tool,
            tool_args={},
            tool_context=context,
            error=RuntimeError("MCP connection refused")
        )

        failure_line = caplog.messages[-1]
        assert "[TIMING] tool FAILED inv=inv-1 agent=root_orchestrator tool=find_documents" in failure_line
        assert "error=MCP connection refused" in failure_line
        assert ELAPSED_PATTERN.search(failure_line)


class TestCallbacksReturnNone:
    @pytest.mark.asyncio
    async def test_callbacks_never_short_circuit_execution(self, mocker, caplog, plugin):
        caplog.set_level(logging.INFO)
        invocation_context = _invocation_context(mocker)
        callback_context = _callback_context(mocker)
        tool_context = _tool_context(mocker)
        tool = _tool(mocker)

        results = [
            await plugin.before_run_callback(invocation_context=invocation_context),
            await plugin.before_agent_callback(agent=tool, callback_context=callback_context),
            await plugin.after_agent_callback(agent=tool, callback_context=callback_context),
            await plugin.before_model_callback(callback_context=callback_context, llm_request=mocker.MagicMock()),
            await plugin.after_model_callback(callback_context=callback_context, llm_response=_llm_response(mocker)),
            await plugin.on_model_error_callback(
                callback_context=callback_context, llm_request=mocker.MagicMock(), error=RuntimeError()
            ),
            await plugin.before_tool_callback(tool=tool, tool_args={}, tool_context=tool_context),
            await plugin.after_tool_callback(tool=tool, tool_args={}, tool_context=tool_context, result={}),
            await plugin.on_tool_error_callback(
                tool=tool, tool_args={}, tool_context=tool_context, error=RuntimeError()
            ),
            await plugin.after_run_callback(invocation_context=invocation_context),
        ]

        assert all(result is None for result in results)
