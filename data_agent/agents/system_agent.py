from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from data_agent.agents.prompts.system_agent import SYSTEM_AGENT_NAME, SYSTEM_AGENT_INSTRUCTION


system_model = LiteLlm(
    model="openai//mnt/models",
    api_base=SETTINGS.model_openapi.endpoint + "/openapi/llm",
    api_key="not-used",
    extra_headers={
        "x-openapi-token": SETTINGS.model_openapi.pass_key,
        "x-generative-ai-client": SETTINGS.model_openapi.client_key,
        "x-llm-model-id": str(SETTINGS.model_openapi.system_model_id)
    }
)

system_agent = Agent(
    model=system_model,
    name=SYSTEM_AGENT_NAME,
    instruction=SYSTEM_AGENT_INSTRUCTION
)
