from common.constants import AgentNames, ModelReasoningEffort
from data_agent.agents.instructions import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION

MODULE = "data_agent.agents.root"


class TestRootAgent:
    def test_init_root_agent(self, adk):
        module = adk.reload(MODULE)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["name"] == AgentNames.ROOT
        assert kwargs["description"] == ROOT_AGENT_DESCRIPTION
        assert kwargs["model"] is adk.build_model.return_value
        assert adk.build_model.call_args.args == (ModelReasoningEffort.MEDIUM,)

        instruction = kwargs["instruction"]
        assert callable(instruction)
        rendered = instruction(None)
        assert rendered.startswith("CURRENT LOCAL TIME:")
        assert rendered.endswith(ROOT_AGENT_INSTRUCTION)
        assert module.root_agent is adk.agent.return_value
