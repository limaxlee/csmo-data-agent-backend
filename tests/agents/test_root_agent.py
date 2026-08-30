import pytest
import importlib
from datetime import datetime
from zoneinfo import ZoneInfoNotFoundError

from common.config import SETTINGS
from data_agent.agents.prompts.root_agent import ROOT_AGENT_NAME, ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION

MODULE = "data_agent.agents.root_agent"


class TestRootAgent:
    def test_get_current_time(self, adk):
        module = adk.reload(MODULE)

        result = module.get_current_time("UTC")

        assert result["status"] == "success"
        assert result["timezone"] == "UTC"
        assert datetime.strptime(result["time"], "%Y-%m-%d %H:%M:%S")

        assert module.get_current_time()["timezone"] == "Asia/Seoul"

        with pytest.raises(ZoneInfoNotFoundError):
            module.get_current_time("Not/AZone")

    def test_root_model(self, adk):
        module = adk.reload(MODULE)

        adk.lite_llm.assert_called_once()
        kwargs = adk.lite_llm.call_args.kwargs
        assert kwargs["model"] == "openai//mnt/models"
        assert kwargs["api_base"] == SETTINGS.model_openapi.endpoint + "/openapi/llm"
        assert kwargs["extra_headers"] == {
            "x-openapi-token": SETTINGS.model_openapi.pass_key,
            "x-generative-ai-client": SETTINGS.model_openapi.client_key,
            "x-llm-model-id": str(SETTINGS.model_openapi.root_model_id)
        }
        assert module.root_model is adk.lite_llm.return_value

    def test_root_agent(self, adk):
        module = adk.reload(MODULE)

        adk.agent.assert_called_once()
        kwargs = adk.agent.call_args.kwargs
        assert kwargs["model"] is module.root_model
        assert kwargs["name"] == ROOT_AGENT_NAME
        assert kwargs["description"] == ROOT_AGENT_DESCRIPTION
        assert kwargs["instruction"] == ROOT_AGENT_INSTRUCTION
        assert module.root_agent is adk.agent.return_value

        milvus = importlib.import_module("data_agent.agents.milvus_scanner")
        mongodb = importlib.import_module("data_agent.agents.mongodb_scanner")
        assert adk.agent_tool.call_count == 2
        wrapped = [call.kwargs["agent"] for call in adk.agent_tool.call_args_list]
        assert wrapped == [milvus.milvus_agent, mongodb.mongodb_agent]
        assert kwargs["tools"] == [adk.agent_tool.return_value, adk.agent_tool.return_value]
