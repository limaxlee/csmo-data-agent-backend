import asyncio
import logging
import os
from io import BytesIO
from zipfile import ZipFile

from data_agent.utils.logger import (
    ExecutorHolder,
    LogConfig,
    _create_logs_zip_file,
    _get_executor,
    get_logs_zip_file,
    initialize_logger,
    shutdown_logs_executor,
)


class TestLoggerUtils:
    def test__get_executor(self, mocker):
        executor = mocker.MagicMock()
        process_pool = mocker.patch("data_agent.utils.logger.ProcessPoolExecutor", return_value=executor)

        assert _get_executor() is executor
        assert ExecutorHolder.instance is executor

        # Second call reuses the cached instance instead of building a new pool.
        assert _get_executor() is executor
        process_pool.assert_called_once()

    def test_shutdown_logs_executor(self, mocker):
        executor = mocker.MagicMock()
        ExecutorHolder.instance = executor

        shutdown_logs_executor()

        executor.shutdown.assert_called_once_with(wait=True)
        assert ExecutorHolder.instance is None

        # Calling it again with nothing running is a no-op.
        shutdown_logs_executor()
        executor.shutdown.assert_called_once_with(wait=True)

    def test_initialize_logger(self, mocker, tmp_path):
        log_dir = tmp_path / "logs"
        mocker.patch.object(LogConfig, "LOG_DIR", str(log_dir))

        target = logging.getLogger("test_initialize_logger")
        target.handlers.clear()

        result = initialize_logger("cosmo.log", logger=target)

        try:
            assert result is target
            assert result.level == LogConfig.LEVEL
            assert len(result.handlers) == 2
            assert os.path.isdir(str(log_dir))
            assert os.path.isfile(str(log_dir / "cosmo.log"))
        finally:
            for handler in list(result.handlers):
                handler.close()
            result.handlers.clear()

    def test_get_logs_zip_file(self, mocker, tmp_path):
        log_dir = tmp_path / "logs"
        log_dir.mkdir()
        (log_dir / "cosmo.log").write_bytes(b"log line")
        mocker.patch.object(LogConfig, "LOG_DIR", str(log_dir))

        # None makes run_in_executor fall back to the loop's default executor, so the
        # real zipping runs without spawning the process pool.
        mocker.patch("data_agent.utils.logger._get_executor", return_value=None)

        payload = asyncio.run(get_logs_zip_file())

        with ZipFile(BytesIO(payload)) as archive:
            assert archive.namelist() == ["cosmo.log"]
            assert archive.read("cosmo.log") == b"log line"

        # An empty log directory returns nothing at all.
        (log_dir / "cosmo.log").unlink()
        assert asyncio.run(get_logs_zip_file()) is None

    def test__create_logs_zip_file(self, tmp_path):
        first = tmp_path / "first.log"
        second = tmp_path / "second.log"
        first.write_bytes(b"first payload")
        second.write_bytes(b"second payload")

        payload = _create_logs_zip_file([str(first), str(second)])

        with ZipFile(BytesIO(payload)) as archive:
            assert sorted(archive.namelist()) == ["first.log", "second.log"]
            assert archive.read("first.log") == b"first payload"
            assert archive.read("second.log") == b"second payload"
