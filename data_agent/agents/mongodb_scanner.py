from google.adk.agents.llm_agent import Agent
from google.adk.tools.mcp_tool.mcp_session_manager import StreamableHTTPConnectionParams
from google.adk.tools.mcp_tool.mcp_toolset import MCPToolset
from google.adk.models.lite_llm import LiteLlm

from common.config import SETTINGS
from data_agent.agents.prompts.mongodb_scanner import MONGODB_AGENT_NAME, MONGODB_AGENT_INSTRUCTION


mongodb_model = LiteLlm(
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

mongodb_agent = Agent(
    model=mongodb_model,
    name=MONGODB_AGENT_NAME,
    instruction=MONGODB_AGENT_INSTRUCTION,
    tools=[
        MCPToolset(connection_params=StreamableHTTPConnectionParams(
            url=f"http://{SETTINGS.mongodb_mcp.host}:{SETTINGS.mongodb_mcp.port}/mcp")
        )
    ]
)
