import os
import sys
import pytest
import yaml

from common.constants import ROOT_DIR
from common.config import _to_bool, _set_nested_config, load_config


class TestToBool:
    @pytest.mark.parametrize("value", ["1", "true", "True", " yes ", "ON"])
    def test_accepts_truthy_values(self, value):
        assert _to_bool(value) is True

    @pytest.mark.parametrize("value", ["0", "false", "FALSE", " no ", "off"])
    def test_accepts_falsy_values(self, value):
        assert _to_bool(value) is False

    def test_rejects_unknown_values(self):
        with pytest.raises(ValueError, match="Expected a boolean"):
            _to_bool("maybe")


class TestSetNestedConfig:
    def test_sets_top_level_and_nested_keys(self):
        config = {}

        _set_nested_config(config, "server_port", 1)
        _set_nested_config(config, "mongodb_mcp.host", "localhost")
        _set_nested_config(config, "mongodb_mcp.port", 2)

        assert config == {"server_port": 1, "mongodb_mcp": {"host": "localhost", "port": 2}}

    def test_overrides_existing_nested_key(self):
        config = {"mongodb_mcp": {"host": "file-host", "port": 1}}

        _set_nested_config(config, "mongodb_mcp.host", "env-host")

        assert config == {"mongodb_mcp": {"host": "env-host", "port": 1}}

    def test_rejects_non_dict_group(self):
        config = {"mongodb_mcp": "not a mapping"}

        with pytest.raises(ValueError, match="Config key mongodb_mcp is invalid"):
            _set_nested_config(config, "mongodb_mcp.host", "localhost")


class TestLoadConfig:
    @pytest.fixture
    def config_path(self, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text(yaml.safe_dump({"server_port": 1, "mongodb_mcp": {"host": "file-host", "port": 1}}))
        return path

    def test_reads_config_file(self, mocker, config_path):
        mocker.patch.object(sys, "argv", ["data_agent", "--config", str(config_path)])
        mocker.patch.dict(os.environ, {"SERVER_PORT": "2", "MONGODB_MCP_HOST": "env-host"})

        config = load_config()

        assert config["server_port"] == 2
        assert config["mongodb_mcp"] == {"host": "env-host", "port": 1}

    def test_casts_env_values(self, mocker, config_path):
        mocker.patch.object(sys, "argv", ["data_agent", "-c", str(config_path)])
        mocker.patch.dict(os.environ, {"RESET_SESSION_LOCKS": "off", "MILVUS_MCP_PORT": "9000"})

        config = load_config()

        assert config["reset_session_locks"] is False
        assert config["milvus_mcp"]["port"] == 9000

    def test_uses_default_config_path(self, mocker):
        mocker.patch.object(sys, "argv", ["data_agent"])
        isfile = mocker.patch("common.config.os.path.isfile", return_value=True)
        opened = mocker.patch("common.config.open", mocker.mock_open(read_data="server_port: 5"))
        mocker.patch.dict(os.environ, {"SERVER_PORT": "5"})

        config = load_config()

        default_path = os.path.join(ROOT_DIR, "config.yaml")
        isfile.assert_called_once_with(default_path)
        assert opened.call_args.args[0] == default_path
        assert config["server_port"] == 5

    def test_skips_missing_config_file(self, mocker, tmp_path):
        mocker.patch.object(sys, "argv", ["data_agent", "--config", str(tmp_path / "missing.yaml")])
        mocker.patch.dict(os.environ, {"SERVER_PORT": "3"})

        config = load_config()

        assert config["server_port"] == 3
        assert "mongodb_mcp" not in config

    def test_rejects_non_mapping_config_file(self, mocker, tmp_path):
        path = tmp_path / "config.yaml"
        path.write_text("- not\n- a mapping\n")
        mocker.patch.object(sys, "argv", ["data_agent", "--config", str(path)])

        with pytest.raises(ValueError, match="Config file is invalid"):
            load_config()

    def test_rejects_invalid_env_value(self, mocker, config_path):
        mocker.patch.object(sys, "argv", ["data_agent", "--config", str(config_path)])
        mocker.patch.dict(os.environ, {"SERVER_PORT": "not-a-port"})

        with pytest.raises(ValueError, match="Invalid value for SERVER_PORT"):
            load_config()
