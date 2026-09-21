from google.adk.agents.llm_agent import Agent
from google.adk.tools import AgentTool

from common.constants import ModelReasoningEffort, AgentNames
from data_agent.agents.instructions import (
    ROOT_AGENT_DESCRIPTION, ROOT_AGENT_ORCHESTRATOR_INSTRUCTION, ROOT_AGENT_STANDALONE_INSTRUCTION,
    get_instruction_with_current_time
)
from data_agent.agents.models import build_model
from data_agent.agents.milvus_scanner import milvus_agent
from data_agent.agents.mongodb_scanner import mongodb_agent

# Two root variants share the same name and description and differ only in instruction and tools:
# - orchestrator: the scanners are sub-agents (AgentTool) and the root only routes, resolves the model identity
#   and formats the answer -> ROOT_AGENT_ORCHESTRATOR_INSTRUCTION;
# - standalone: the root holds both MCP toolsets and calls the tools itself -> ROOT_AGENT_STANDALONE_INSTRUCTION.
# Keep the instruction and the tools of the active variant in sync when switching.
# root_agent = Agent(
#     model=build_model(ModelReasoningEffort.MEDIUM),
#     name=AgentNames.ROOT,
#     description=ROOT_AGENT_DESCRIPTION,
#     instruction=get_instruction_with_current_time(ROOT_AGENT_ORCHESTRATOR_INSTRUCTION),
#     tools=[AgentTool(agent=milvus_agent), AgentTool(agent=mongodb_agent)]
# )

from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from common.config import SETTINGS

root_agent = Agent(
    model=build_model(ModelReasoningEffort.MEDIUM),
    name=AgentNames.ROOT,
    description=ROOT_AGENT_DESCRIPTION,
    instruction=get_instruction_with_current_time(ROOT_AGENT_STANDALONE_INSTRUCTION),
    tools=[
        MCPToolset(connection_params=StreamableHTTPConnectionParams(
            url=f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp")
        ),
        MCPToolset(connection_params=StreamableHTTPConnectionParams(
            url=f"http://{SETTINGS.milvus_mcp.host}:{SETTINGS.milvus_mcp.port}/mcp")
        )
    ]
)
