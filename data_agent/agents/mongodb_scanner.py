from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from common.config import SETTINGS
from common.constants import ModelReasoningEffort, AgentNames
from data_agent.agents.instructions import MONGODB_AGENT_INSTRUCTION, get_instruction_with_current_time
from data_agent.agents.llm import build_model

mongodb_agent = Agent(
    model=build_model(ModelReasoningEffort.LOW),
    name=AgentNames.MONGODB,
    instruction=get_instruction_with_current_time(MONGODB_AGENT_INSTRUCTION),
    tools=[
        MCPToolset(connection_params=StreamableHTTPConnectionParams(
            url=f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp")
        )
    ]
)
