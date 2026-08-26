import logging

from common.constants import MILVUS_IMAGE_SEARCH_TOOL

logger = logging.getLogger(__name__)


def inject_pending_image(tool, args, tool_context):
    if tool.name != MILVUS_IMAGE_SEARCH_TOOL:
        return None

    info = tool_context.state.get("pending_image")

    if not info:
        logger.warning("Image search tool called but no pending image")
        return None

    args["data_uri"] = info["key"]
    args["filename"] = info["filename"]
    args["content_type"] = info["content_type"]

    return None
