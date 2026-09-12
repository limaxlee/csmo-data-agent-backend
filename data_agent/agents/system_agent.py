from google.adk.agents.llm_agent import Agent
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from common.constants import AgentNames
from data_agent.agents.instructions.system_agent import SYSTEM_AGENT_INSTRUCTION

system_model = LiteLlm(
    model=SETTINGS.system_model_openapi.model,
    api_base=SETTINGS.system_model_openapi.endpoint,
    api_key="not-used",
    extra_headers={
        "x-openapi-token": SETTINGS.system_model_openapi.pass_key,
        "x-generative-ai-client": SETTINGS.system_model_openapi.client_key,
        "x-llm-model-id": str(SETTINGS.system_model_openapi.model_id)
    }
)

system_agent = Agent(
    model=system_model,
    name=AgentNames.SYSTEM,
    instruction=SYSTEM_AGENT_INSTRUCTION
)
