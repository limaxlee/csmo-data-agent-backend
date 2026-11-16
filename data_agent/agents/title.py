from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from common.constants import AgentNames
from data_agent.agents.instructions.title import TITLE_AGENT_INSTRUCTION

title_model = LiteLlm(
    model=SETTINGS.title_model_openapi.model,
    api_base=SETTINGS.title_model_openapi.endpoint,
    api_key="not-used",
    extra_headers={
        "x-openapi-token": SETTINGS.title_model_openapi.pass_key,
        "x-generative-ai-client": SETTINGS.title_model_openapi.client_key,
        "x-llm-model-id": str(SETTINGS.title_model_openapi.model_id)
    }
)

title_agent = Agent(
    model=title_model,
    name=AgentNames.TITLE,
    instruction=TITLE_AGENT_INSTRUCTION
)
