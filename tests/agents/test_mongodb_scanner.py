from common.config import SETTINGS
from common.constants import AgentNames, ModelReasoningEffort
from data_agent.agents.instructions import MONGODB_AGENT_INSTRUCTION

MODULE = "data_agent.agents.mongodb_scanner"


class TestMongodbScanner:
    def test_mongodb_agent(self, adk):
        module = adk.reload(MODULE)

        adk.connection_params.assert_called_once_with(
            url=f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp"
        )
        adk.toolset.assert_called_once_with(connection_params=adk.connection_params.return_value)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["name"] == AgentNames.MONGODB
        assert kwargs["tools"] == [adk.toolset.return_value]
        assert kwargs["model"] is adk.build_model.return_value
        assert adk.build_model.call_args.args == (ModelReasoningEffort.LOW,)

        instruction = kwargs["instruction"]
        assert callable(instruction)
        rendered = instruction(None)
        assert rendered.startswith("CURRENT LOCAL TIME:")
        assert rendered.endswith(MONGODB_AGENT_INSTRUCTION)
        assert module.mongodb_agent is adk.agent.return_value
