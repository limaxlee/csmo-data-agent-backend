from common.config import SETTINGS
from common.constants import ModelReasoningEffort
from data_agent.agents.llm import build_model


class TestBuildModel:
    def test_build_model(self, mocker):
        lite_llm = mocker.patch("data_agent.agents.llm.LiteLlm")

        model = build_model(ModelReasoningEffort.MEDIUM)

        lite_llm.assert_called_once()
        kwargs = lite_llm.call_args.kwargs
        assert kwargs["model"] == "openai//mnt/models"
        assert kwargs["api_base"] == SETTINGS.model_openapi.endpoint + "/openapi/llm"
        assert kwargs["api_key"] == "not-used"
        assert kwargs["extra_headers"] == {
            "x-openapi-token": SETTINGS.model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.model_openapi.root_model_id)
        }
        assert kwargs["extra_body"] == {"reasoning_effort": ModelReasoningEffort.MEDIUM}
        assert model is lite_llm.return_value
