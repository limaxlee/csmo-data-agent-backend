import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from data_agent.utils.logger import ExecutorHolder


@pytest.fixture(autouse=True)
def reset_logs_executor():
    """The logging executor is process-global state, so it must not leak between tests."""
    ExecutorHolder.instance = None
    yield
    ExecutorHolder.instance = None
