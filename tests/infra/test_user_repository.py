import json
import pytest

from data_agent.infra.user_repository import UserRepository
from data_agent.schemas import SsoIdentity


def _identity():
    return SsoIdentity(
        user_id="user.one",
        email="user.one@samsung.com",
        full_name="user.one@samsung.com",
        department="Test Dept",
        company="Test Co",
        unique_name="CORP\\user.one",
        sid="S-1-5-21-1",
        roles=["group-a"],
        claims={"sub": "user.one", "iss": "web-auth"}
    )


def _user_row(**overrides):
    row = {
        "user_id": "user.one",
        "is_active": False,
        "is_admin": False,
        "roles": ["group-a"],
        "sso_claims": {"sub": "user.one"}
    }
    row.update(overrides)
    return row


class TestUserRepository:
    @pytest.fixture
    def db_client(self, mocker):
        db_client = mocker.MagicMock()
        db_client.execute = mocker.AsyncMock()
        db_client.fetch_one = mocker.AsyncMock(return_value=None)
        db_client.fetch_all = mocker.AsyncMock(return_value=[])
        return db_client

    @pytest.fixture
    def user_repository(self, db_client):
        return UserRepository(db_client=db_client)

    @pytest.mark.asyncio
    async def test_initialize(self, db_client, user_repository):
        await user_repository.initialize()

        assert db_client.execute.await_count == 4

        accounts, access_log, index, admins = [call.args[0] for call in db_client.execute.await_args_list]

        assert "CREATE TABLE IF NOT EXISTS user_accounts" in accounts
        assert "user_id        TEXT PRIMARY KEY" in accounts
        assert "is_active      BOOLEAN NOT NULL DEFAULT false" in accounts
        assert "last_access_ip TEXT" in accounts
        assert "sso_claims     JSONB NOT NULL DEFAULT '{}'::jsonb" in accounts

        assert "CREATE TABLE IF NOT EXISTS user_access_log" in access_log
        assert "REFERENCES user_accounts(user_id) ON DELETE CASCADE" in access_log
        assert "ip_address  TEXT" in access_log

        assert "CREATE INDEX IF NOT EXISTS ix_user_access_log_user_time" in index

        assert "CREATE TABLE IF NOT EXISTS user_admins" in admins
        assert "user_id  TEXT PRIMARY KEY" in admins

    @pytest.mark.asyncio
    async def test_record_access(self, mocker, db_client, user_repository):
        db_client.fetch_one = mocker.AsyncMock(return_value=_user_row())

        user = await user_repository.record_access(_identity(), "10.0.0.1", "pytest")

        assert user == _user_row()

        query, params = db_client.fetch_one.await_args.args

        assert "INSERT INTO user_accounts" in query
        assert "ON CONFLICT (user_id) DO UPDATE" in query
        assert "INSERT INTO user_access_log (user_id, ip_address, user_agent)" in query
        assert "FROM user_admins WHERE user_admins.user_id = account.user_id) AS is_admin" in query

        # The approval state belongs to the data agent: a login must never change it.
        assert "is_active" not in query

        assert params == {
            "uid": "user.one",
            "email": "user.one@samsung.com",
            "full_name": "user.one@samsung.com",
            "department": "Test Dept",
            "company": "Test Co",
            "unique_name": "CORP\\user.one",
            "sid": "S-1-5-21-1",
            "roles": json.dumps(["group-a"]),
            "claims": json.dumps({"sub": "user.one", "iss": "web-auth"}),
            "ip": "10.0.0.1",
            "user_agent": "pytest"
        }

        await user_repository.record_access(_identity())
        params = db_client.fetch_one.await_args.args[1]

        assert params["ip"] is None
        assert params["user_agent"] is None

    @pytest.mark.asyncio
    async def test_record_access_loads_json_text(self, mocker, db_client, user_repository):
        db_client.fetch_one = mocker.AsyncMock(return_value=_user_row(roles='["group-a"]', sso_claims=None))

        user = await user_repository.record_access(_identity())

        assert user["roles"] == ["group-a"]
        assert user["sso_claims"] == {}

    @pytest.mark.asyncio
    async def test_get_user(self, mocker, db_client, user_repository):
        assert await user_repository.get_user("user.one") is None

        query, params = db_client.fetch_one.await_args.args

        assert "FROM user_accounts" in query
        assert "WHERE user_id = :uid" in query
        assert "FROM user_admins WHERE user_admins.user_id = user_accounts.user_id) AS is_admin" in query
        assert params == {"uid": "user.one"}

        db_client.fetch_one = mocker.AsyncMock(return_value=_user_row(is_admin=True))

        assert await user_repository.get_user("user.one") == _user_row(is_admin=True)

    @pytest.mark.asyncio
    async def test_list_users(self, mocker, db_client, user_repository):
        assert await user_repository.list_users() == []

        query, params = db_client.fetch_all.await_args.args

        assert "FROM user_accounts" in query
        assert "CAST(:is_active AS BOOLEAN) IS NULL OR is_active = CAST(:is_active AS BOOLEAN)" in query
        assert "ORDER BY created_at DESC" in query
        assert params == {"is_active": None}

        db_client.fetch_all = mocker.AsyncMock(return_value=[_user_row(), _user_row(user_id="user.two")])
        users = await user_repository.list_users(is_active=False)

        assert [user["user_id"] for user in users] == ["user.one", "user.two"]
        assert db_client.fetch_all.await_args.args[1] == {"is_active": False}

    @pytest.mark.asyncio
    async def test_set_user_active(self, mocker, db_client, user_repository):
        assert await user_repository.set_user_active("user.one", True, "admin.one") is None

        query, params = db_client.fetch_one.await_args.args

        assert "UPDATE user_accounts" in query
        assert "SET is_active = CAST(:is_active AS BOOLEAN)" in query
        assert "activated_at = CASE WHEN CAST(:is_active AS BOOLEAN) THEN now() ELSE activated_at END" in query
        assert "WHERE user_id = :uid" in query
        assert "RETURNING user_accounts.*" in query
        assert params == {"uid": "user.one", "is_active": True, "admin": "admin.one"}

        db_client.fetch_one = mocker.AsyncMock(return_value=_user_row(is_active=True))
        user = await user_repository.set_user_active("user.one", True, "admin.one")

        assert user == _user_row(is_active=True)

    @pytest.mark.asyncio
    async def test_list_access_logs(self, mocker, db_client, user_repository):
        access_logs = [{"user_id": "user.one", "ip_address": "10.0.0.1"}]
        db_client.fetch_all = mocker.AsyncMock(return_value=access_logs)

        assert await user_repository.list_access_logs("user.one", 10) == access_logs

        query, params = db_client.fetch_all.await_args.args

        assert "FROM user_access_log" in query
        assert "ORDER BY accessed_at DESC, id DESC" in query
        assert "LIMIT :limit" in query
        assert params == {"uid": "user.one", "limit": 10}

    @pytest.mark.asyncio
    async def test_is_admin(self, mocker, db_client, user_repository):
        assert await user_repository.is_admin("user.one") is False

        query, params = db_client.fetch_one.await_args.args

        assert "FROM user_admins WHERE user_id = :uid" in query
        assert params == {"uid": "user.one"}

        db_client.fetch_one = mocker.AsyncMock(return_value={"user_id": "user.one"})

        assert await user_repository.is_admin("user.one") is True

    @pytest.mark.asyncio
    async def test_list_admins(self, mocker, db_client, user_repository):
        admins = [{"user_id": "admin.one", "added_by": None}]
        db_client.fetch_all = mocker.AsyncMock(return_value=admins)

        assert await user_repository.list_admins() == admins

        query = db_client.fetch_all.await_args.args[0]

        assert "FROM user_admins" in query
        assert "ORDER BY added_at, user_id" in query

    @pytest.mark.asyncio
    async def test_add_admin(self, mocker, db_client, user_repository):
        admin = {"user_id": "user.one", "added_by": "admin.one"}
        db_client.fetch_one = mocker.AsyncMock(return_value=admin)

        assert await user_repository.add_admin("user.one", "admin.one") == admin

        query, params = db_client.fetch_one.await_args.args

        assert "INSERT INTO user_admins (user_id, added_by)" in query
        assert "ON CONFLICT (user_id) DO UPDATE" in query
        assert "RETURNING user_id, added_at, added_by" in query
        assert params == {"uid": "user.one", "admin": "admin.one"}

    @pytest.mark.asyncio
    async def test_delete_admin(self, mocker, db_client, user_repository):
        assert await user_repository.delete_admin("user.one") is False

        query, params = db_client.fetch_one.await_args.args

        assert "DELETE FROM user_admins" in query
        assert "EXISTS (SELECT 1 FROM user_admins AS others WHERE others.user_id <> :uid)" in query
        assert params == {"uid": "user.one"}

        db_client.fetch_one = mocker.AsyncMock(return_value={"user_id": "user.one"})

        assert await user_repository.delete_admin("user.one") is True
