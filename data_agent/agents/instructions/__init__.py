from typing import Callable
from google.adk.agents.readonly_context import ReadonlyContext

from data_agent.utils import get_current_local_time
from .milvus_scanner import MILVUS_AGENT_INSTRUCTION
from .mongodb_scanner import MONGODB_AGENT_INSTRUCTION
from .root_agent import ROOT_AGENT_DESCRIPTION, ROOT_AGENT_INSTRUCTION
from .system_agent import SYSTEM_AGENT_INSTRUCTION


def get_instruction_with_current_time(instruction: str) -> Callable[[ReadonlyContext], str]:
    def provider(_: ReadonlyContext) -> str:
        return f"CURRENT LOCAL TIME: {get_current_local_time()}\n\n{instruction}"

    return provider
