from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool

from common.constants import ModelReasoningEffort, AgentNames
from data_agent.agents.instructions import (
    ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION, get_instruction_with_current_time
)
from data_agent.agents.llm import build_model
from data_agent.agents.milvus_scanner import milvus_agent
from data_agent.agents.mongodb_scanner import mongodb_agent

root_agent = Agent(
    model=build_model(ModelReasoningEffort.MEDIUM),
    name=AgentNames.ROOT,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=get_instruction_with_current_time(ROOT_AGENT_INSTRUCTION),
    tools=[AgentTool(agent=milvus_agent), AgentTool(agent=mongodb_agent)]
)
