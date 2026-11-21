import os
import sys
import pytest

# SETTINGS is built when common.config is imported, so the secret must be set before any other import.
os.environ.setdefault("AUTH_SERVICE_JWT_SECRET", "test-service-jwt-secret-for-unit-tests")

from data_agent.utils.logger import ExecutorHolder

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


@pytest.fixture(autouse=True)
def reset_logs_executor():
    ExecutorHolder.instance = None
    yield
    ExecutorHolder.instance = None
