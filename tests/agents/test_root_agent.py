from common.config import SETTINGS
from common.constants import AgentNames, ModelReasoningEffort
from data_agent.agents.instructions import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION

MODULE = "data_agent.agents.root_agent"


class TestRootAgent:
    def test_root_agent(self, adk):
        module = adk.reload(MODULE)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["name"] == AgentNames.ROOT
        assert kwargs["description"] == ROOT_AGENT_DESCRIPTION
        assert kwargs["model"] is adk.build_model.return_value
        assert adk.build_model.call_args.args == (ModelReasoningEffort.MEDIUM,)

        instruction = kwargs["instruction"]
        assert callable(instruction)
        rendered = instruction(None)
        assert rendered.startswith("CURRENT LOCAL TIME:")
        assert rendered.endswith(ROOT_AGENT_INSTRUCTION)
        assert module.root_agent is adk.agent.return_value

    def test_root_agent_tools(self, adk):
        adk.reload(MODULE)

        urls = [call.kwargs["url"] for call in adk.connection_params.call_args_list]
        assert urls == [
            f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp",
            f"http://{SETTINGS.milvus_mcp.host}:{SETTINGS.milvus_mcp.port}/mcp"
        ]
        assert adk.toolset.call_count == 2
        assert all(
            call.kwargs["connection_params"] is adk.connection_params.return_value
            for call in adk.toolset.call_args_list
        )

        kwargs = adk.agent.call_args.kwargs
        assert kwargs["tools"] == [adk.toolset.return_value, adk.toolset.return_value]
        adk.agent_tool.assert_not_called()
