from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset

from common.config import SETTINGS
from common.constants import ModelReasoningEffort, AgentNames
from data_agent.agents.instructions import MILVUS_AGENT_INSTRUCTION
from data_agent.agents.llm import build_model

milvus_agent = Agent(
    model=build_model(ModelReasoningEffort.LOW),
    name=AgentNames.MILVUS,
    instruction=MILVUS_AGENT_INSTRUCTION,
    tools=[
        MCPToolset(connection_params=StreamableHTTPConnectionParams(
            url=f"http://{SETTINGS.milvus_mcp.host}:{SETTINGS.milvus_mcp.port}/mcp")
        )
    ]
)
