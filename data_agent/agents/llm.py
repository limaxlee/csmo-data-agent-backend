from datetime import datetime
from zoneinfo import ZoneInfo
from typing import Callable

from google.adk.agents.readonly_context import ReadonlyContext
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS

LOCAL_TZ = "Asia/Seoul"

# Rec 1: dial thinking down. Try "none" for the scanners if your gateway accepts it;
# if reasoning_effort is silently ignored, switch to the extra_body variant below.
ROOT_REASONING_EFFORT = "low"
SCANNER_REASONING_EFFORT = "low"


def build_model(reasoning_effort: str) -> LiteLlm:
    return LiteLlm(
        model="openai//mnt/models",
        api_base=SETTINGS.model_openapi.endpoint + "/openapi/llm",
        api_key="not-used",
        extra_headers={
            "x-openapi-token": SETTINGS.model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.model_openapi.root_model_id),
        },
        reasoning_effort=reasoning_effort,
        # vLLM fallback if reasoning_effort has no effect:
        # extra_body={"chat_template_kwargs": {"enable_thinking": False}},
    )


def current_local_time() -> str:
    return datetime.now(ZoneInfo(LOCAL_TZ)).strftime("%Y-%m-%d %H:%M:%S (%A)")


def with_current_time(instruction: str) -> Callable[[ReadonlyContext], str]:
    """Rec 2: prepend the current time to the instruction on every LLM call,
    so no agent needs a tool round trip to learn the date."""
    def provider(_: ReadonlyContext) -> str:
        return f"CURRENT LOCAL TIME ({LOCAL_TZ}): {current_local_time()}\n\n{instruction}"
    return provider
