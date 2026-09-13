from common.config import SETTINGS
from common.constants import AgentNames
from data_agent.agents.instructions.system_agent import SYSTEM_AGENT_INSTRUCTION

MODULE = "data_agent.agents.system_agent"


class TestSystemAgent:
    def test_system_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == SETTINGS.system_model_openapi.model
        assert kwargs["api_base"] == SETTINGS.system_model_openapi.endpoint
        assert kwargs["api_key"] == "not-used"
        assert kwargs["extra_headers"] == {
            "x-openapi-token": SETTINGS.system_model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.system_model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.system_model_openapi.model_id)
        }
        assert "extra_body" not in kwargs
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
