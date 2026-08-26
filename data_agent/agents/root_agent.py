from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from data_agent.agents.milvus_scanner import milvus_agent
from data_agent.agents.mongodb_scanner import mongodb_agent
from data_agent.agents.prompts.root_agent import (
    ROOT_AGENT_NAME, ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION
)


root_model = LiteLlm(
    model="openai//mnt/models",
    api_base=SETTINGS.model_openapi.endpoint + "/openapi/llm",
    api_key="not-used",
    extra_headers={
        "x-openapi-token": SETTINGS.model_openapi.pass_key,
        "x-generative-ai-client": SETTINGS.model_openapi.client_key,
        "x-llm-model-id": str(SETTINGS.model_openapi.root_model_id),
    },
    # optional:
    # reasoning_effort="low",
    # temperature=0.7,
)

root_agent = Agent(
    model=root_model,
    name=ROOT_AGENT_NAME,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[AgentTool(agent=milvus_agent), AgentTool(agent=mongodb_agent)]
)
