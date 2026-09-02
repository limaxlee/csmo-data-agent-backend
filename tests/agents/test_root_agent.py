import importlib
from common.constants import AgentNames, ModelReasoningEffort
from data_agent.agents.instructions import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION

MODULE = "data_agent.agents.root_agent"


class TestRootAgent:
    def test_root_agent(self, adk):
        module = adk.reload(MODULE)

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

        milvus = importlib.import_module("data_agent.agents.milvus_scanner")
        mongodb = importlib.import_module("data_agent.agents.mongodb_scanner")
        assert adk.agent_tool.call_count == 2

        wrapped = [call.kwargs["agent"] for call in adk.agent_tool.call_args_list]
        assert wrapped == [milvus.milvus_agent, mongodb.mongodb_agent]
        assert kwargs["tools"] == [adk.agent_tool.return_value, adk.agent_tool.return_value]
