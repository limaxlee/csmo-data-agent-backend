import pytest
import importlib


class ADKMocks:
    def __init__(self, mocker):
        self.agent = mocker.patch("google.adk.agents.llm_agent.Agent")
        self.lite_llm = mocker.patch("google.adk.models.lite_llm.LiteLlm")
        self.agent_tool = mocker.patch("google.adk.tools.AgentTool")
        self.toolset = mocker.patch("google.adk.tools.mcp_tool.mcp_toolset.MCPToolset")
        self.connection_params = mocker.patch(
            "google.adk.tools.mcp_tool.mcp_session_manager.StreamableHTTPConnectionParams"
        )
        self.build_model = mocker.patch("data_agent.agents.base.build_model")
        self._reloaded = []

    def _all_mocks(self):
        return (
            self.agent,
            self.lite_llm,
            self.agent_tool,
            self.toolset,
            self.connection_params,
            self.build_model,
        )

    def reset_mocks(self):
        for mock in self._all_mocks():
            mock.reset_mock()

    def reload(self, module_name):
        module = importlib.import_module(module_name)
        self._reloaded.append(module)
        self.reset_mocks()

        return importlib.reload(module)

    def restore(self):
        for module in self._reloaded:
            importlib.reload(module)


@pytest.fixture
def adk(mocker):
    mocks = ADKMocks(mocker)
    yield mocks

    mocker.stopall()
    mocks.restore()
