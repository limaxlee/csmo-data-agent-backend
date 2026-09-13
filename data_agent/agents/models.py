from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from common.constants import ModelReasoningEffort


def build_model(reasoning_effort: ModelReasoningEffort) -> LiteLlm:
    return LiteLlm(
        model=SETTINGS.root_model_openapi.model,
        api_base=SETTINGS.root_model_openapi.endpoint,
        api_key="not-used",
        extra_headers={
            "x-openapi-token": SETTINGS.root_model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.root_model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.root_model_openapi.model_id)
        },
        extra_body={"reasoning_effort": reasoning_effort}
    )
