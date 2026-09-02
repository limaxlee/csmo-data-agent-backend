from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from common.constants import ModelReasoningEffort


def build_model(reasoning_effort: ModelReasoningEffort) -> LiteLlm:
    return LiteLlm(
        model="openai//mnt/models",
        api_base=SETTINGS.model_openapi.endpoint + "/openapi/llm",
        api_key="not-used",
        extra_headers={
            "x-openapi-token": SETTINGS.model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.model_openapi.root_model_id)
        },
        extra_body={"reasoning_effort": reasoning_effort}
    )
