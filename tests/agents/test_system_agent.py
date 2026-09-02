from common.config import SETTINGS
from common.constants import AgentNames
from data_agent.agents.instructions.system_agent import SYSTEM_AGENT_INSTRUCTION

MODULE = "data_agent.agents.system_agent"


class TestSystemAgent:
    def test_system_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == "openai//mnt/models"
        assert kwargs["api_base"] == SETTINGS.model_openapi.endpoint + "/openapi/llm"
        assert kwargs["extra_headers"]["x-llm-model-id"] == str(SETTINGS.model_openapi.system_model_id)
        assert module.system_model is adk.lite_llm.return_value

    def test_system_agent(self, adk):
        module = adk.reload(MODULE)

        adk.agent.assert_called_once_with(
            model=module.system_model,
            name=AgentNames.SYSTEM,
            instruction=SYSTEM_AGENT_INSTRUCTION
        )
        assert module.system_agent is adk.agent.return_value
        assert "tools" not in adk.agent.call_args.kwargs
