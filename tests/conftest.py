import os
import sys
import pytest

from data_agent.utils.logger import ExecutorHolder

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def reset_logs_executor():
    ExecutorHolder.instance = None
    yield
    ExecutorHolder.instance = None
