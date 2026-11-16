from common.config import SETTINGS

MODULE = "data_agent.agents.title"


class TestTitleAgent:
    def test_init_title_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == SETTINGS.title_model_openapi.model
        assert kwargs["api_base"] == SETTINGS.title_model_openapi.endpoint
        assert kwargs["api_key"] == "not-used"
        assert kwargs["extra_headers"] == {
            "x-openapi-token": SETTINGS.title_model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.title_model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.title_model_openapi.model_id)
        }
        assert "extra_body" not in kwargs
        assert module.title_model is adk.lite_llm.return_value

    def test_init_title_agent(self, adk):
        module = adk.reload(MODULE)

        assert module.title_agent is adk.agent.return_value
        assert "tools" not in adk.agent.call_args.kwargs
