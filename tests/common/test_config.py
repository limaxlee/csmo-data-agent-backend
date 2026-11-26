import os
import sys
import pytest
from pydantic import ValidationError

from common.config import SETTINGS, AuthConfig, SessionDBConfig, load_config


class TestSessionDBConfig:
    def test_session_db_config(self):
        config = SessionDBConfig(host="db-host", port=5432, name="db-name", user="db-user")

        assert config.password == ""

        config = SessionDBConfig(host="db-host", port=5432, name="db-name", user="db-user", password="db-password")
        assert config.password == "db-password"


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

    def test_load_config_reads_postgresql_password_from_environment(self, monkeypatch, tmp_path):
        config_path = tmp_path / "config.yaml"
        config_path.write_text("server_port: 18080\npostgresql_db:\n  host: db-host\n  user: db-user\n")

        monkeypatch.setattr(sys, "argv", ["data_agent", "--config", str(config_path)])
        monkeypatch.delenv("POSTGRESQL_DB_HOST", raising=False)
        monkeypatch.delenv("POSTGRESQL_DB_USER", raising=False)
        monkeypatch.delenv("POSTGRESQL_DB_PASSWORD", raising=False)

        assert load_config()["postgresql_db"] == {"host": "db-host", "user": "db-user"}

        monkeypatch.setenv("POSTGRESQL_DB_PASSWORD", "from-environment")

        assert load_config()["postgresql_db"] == {"host": "db-host", "user": "db-user", "password": "from-environment"}
