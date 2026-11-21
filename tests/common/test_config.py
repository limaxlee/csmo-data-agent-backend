import os
import sys
import pytest
from pydantic import ValidationError

from common.config import SETTINGS, AuthConfig, load_config


class TestAuthConfig:
    def test_auth_config(self):
        config = AuthConfig(service_jwt_secret="service-jwt-secret")

        assert config.service_jwt_secret == "service-jwt-secret"
        assert config.service_jwt_issuer == "web-auth"
        assert config.service_jwt_audience == "dice-backend"

    @pytest.mark.parametrize("secret", ["", "   "])
    def test_auth_config_rejects_empty_secret(self, secret):
        with pytest.raises(ValidationError, match="Service JWT secret is empty"):
            AuthConfig(service_jwt_secret=secret)

    def test_settings(self):
        assert SETTINGS.auth.service_jwt_secret == os.environ["AUTH_SERVICE_JWT_SECRET"]
        assert SETTINGS.cors_origins == []


class TestLoadConfig:
    def test_load_config_reads_auth_from_environment(self, monkeypatch, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server_port: 18080\nauth:\n  service_jwt_secret: from-file\n")

        monkeypatch.setattr(sys, "argv", ["data_agent", "--config", str(config_path)])
        monkeypatch.delenv("AUTH_SERVICE_JWT_SECRET", raising=False)
        monkeypatch.delenv("AUTH_SERVICE_JWT_ISSUER", raising=False)
        monkeypatch.delenv("AUTH_SERVICE_JWT_AUDIENCE", raising=False)

        assert load_config()["auth"] == {"service_jwt_secret": "from-file"}

        monkeypatch.setenv("AUTH_SERVICE_JWT_SECRET", "from-environment")
        monkeypatch.setenv("AUTH_SERVICE_JWT_ISSUER", "another-issuer")
        monkeypatch.setenv("AUTH_SERVICE_JWT_AUDIENCE", "another-audience")

        assert load_config()["auth"] == {
            "service_jwt_secret": "from-environment",
            "service_jwt_issuer": "another-issuer",
            "service_jwt_audience": "another-audience"
        }

    def test_load_config_creates_auth_section_from_environment(self, monkeypatch, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server_port: 18080\n")

        monkeypatch.setattr(sys, "argv", ["data_agent", "--config", str(config_path)])
        monkeypatch.setenv("AUTH_SERVICE_JWT_SECRET", "from-environment")

        assert load_config()["auth"]["service_jwt_secret"] == "from-environment"
