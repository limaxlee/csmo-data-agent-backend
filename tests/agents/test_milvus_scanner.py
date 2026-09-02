from common.config import SETTINGS
from common.constants import AgentNames
from data_agent.agents.instructions.milvus_scanner import MILVUS_AGENT_INSTRUCTION

MODULE = "data_agent.agents.milvus_scanner"


class TestMilvusScanner:
    def test_milvus_agent(self, adk):
        module = adk.reload(MODULE)
        adk.connection_params.assert_called_once_with(
            url=f"http://{SETTINGS.milvus_mcp.host}:{SETTINGS.milvus_mcp.port}/mcp"
        )
        adk.toolset.assert_called_once_with(connection_params=adk.connection_params.return_value)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["name"] == AgentNames.MILVUS
        assert kwargs["instruction"] == MILVUS_AGENT_INSTRUCTION
        assert kwargs["tools"] == [adk.toolset.return_value]
        assert module.milvus_agent is adk.agent.return_value
