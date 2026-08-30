from common.config import SETTINGS
from data_agent.agents.prompts.mongodb_scanner import MONGODB_AGENT_NAME, MONGODB_AGENT_INSTRUCTION

MODULE = "data_agent.agents.mongodb_scanner"


class TestMongodbScanner:
    def test_mongodb_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == "openai//mnt/models"
        assert kwargs["api_base"] == SETTINGS.model_openapi.endpoint + "/openapi/llm"
        assert kwargs["extra_headers"]["x-llm-model-id"] == str(SETTINGS.model_openapi.root_model_id)
        assert module.mongodb_model is adk.lite_llm.return_value

    def test_mongodb_agent(self, adk):
        module = adk.reload(MODULE)

        adk.connection_params.assert_called_once_with(
            url=f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp"
        )
        adk.toolset.assert_called_once_with(connection_params=adk.connection_params.return_value)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["model"] is module.mongodb_model
        assert kwargs["name"] == MONGODB_AGENT_NAME
        assert kwargs["instruction"] == MONGODB_AGENT_INSTRUCTION
        assert kwargs["tools"] == [adk.toolset.return_value]
        assert module.mongodb_agent is adk.agent.return_value
