from common.config import SETTINGS
from data_agent.agents.prompts.milvus_scanner import MILVUS_AGENT_NAME, MILVUS_AGENT_INSTRUCTION

MODULE = "data_agent.agents.milvus_scanner"


class TestMilvusScanner:
    def test_milvus_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == "openai//mnt/models"
        assert kwargs["api_base"] == SETTINGS.model_openapi.endpoint + "/openapi/llm"
        assert kwargs["extra_headers"]["x-llm-model-id"] == str(SETTINGS.model_openapi.root_model_id)
        assert module.milvus_model is adk.lite_llm.return_value

    def test_milvus_agent(self, adk):
        module = adk.reload(MODULE)
        adk.connection_params.assert_called_once_with(
            url=f"http://{SETTINGS.milvus_mcp.host}:{SETTINGS.milvus_mcp.port}/mcp"
        )
        adk.toolset.assert_called_once_with(connection_params=adk.connection_params.return_value)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["model"] is module.milvus_model
        assert kwargs["name"] == MILVUS_AGENT_NAME
        assert kwargs["instruction"] == MILVUS_AGENT_INSTRUCTION
        assert kwargs["tools"] == [adk.toolset.return_value]
        assert module.milvus_agent is adk.agent.return_value
