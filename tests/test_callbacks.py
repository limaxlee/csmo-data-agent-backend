from common.constants import MILVUS_IMAGE_SEARCH_TOOL
from data_agent.agents.callbacks import inject_pending_image


class TestCallbacks:
    def test_inject_pending_image(self, mocker):
        tool_context = mocker.MagicMock()
        tool_context.state = {
            "pending_image": {
                "key": "data_agent/u/s/chart.png/0",
                "filename": "chart.png",
                "content_type": "image/png",
            }
        }

        tool = mocker.MagicMock()
        tool.name = MILVUS_IMAGE_SEARCH_TOOL
        args = {"query": "similar charts"}

        # Returning None means "do not short-circuit the tool call"; the injection
        # happens by mutating args in place.
        assert inject_pending_image(tool, args, tool_context) is None
        assert args == {
            "query": "similar charts",
            "data_uri": "data_agent/u/s/chart.png/0",
            "filename": "chart.png",
            "content_type": "image/png",
        }

        # Any other tool is left completely alone.
        other_tool = mocker.MagicMock()
        other_tool.name = "some_other_tool"
        other_args = {"query": "similar charts"}
        assert inject_pending_image(other_tool, other_args, tool_context) is None
        assert other_args == {"query": "similar charts"}

        # The right tool with nothing pending is also a no-op.
        tool_context.state = {}
        empty_args = {"query": "similar charts"}
        assert inject_pending_image(tool, empty_args, tool_context) is None
        assert empty_args == {"query": "similar charts"}
