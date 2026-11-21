import json
import logging
from typing import Any

from data_agent.infra.postgresql_client import PostgreSQLClient
from data_agent.schemas import SsoIdentity

logger = logging.getLogger(__name__)

_IS_ADMIN = "EXISTS (SELECT 1 FROM user_admins WHERE user_admins.user_id = {table}.user_id) AS is_admin"


class UserRepository:
    def __init__(self, db_client: PostgreSQLClient):
        self._db = db_client

    async def initialize(self):
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_accounts (
                user_id        TEXT PRIMARY KEY,
                is_active      BOOLEAN NOT NULL DEFAULT false,
                activated_at   TIMESTAMPTZ,
                activated_by   TEXT,
                created_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
                last_access_at TIMESTAMPTZ,
                last_access_ip TEXT,
                email          TEXT,
                full_name      TEXT,
                department     TEXT,
                company        TEXT,
                unique_name    TEXT,
                sid            TEXT,
                roles          JSONB NOT NULL DEFAULT '[]'::jsonb,
                sso_claims     JSONB NOT NULL DEFAULT '{}'::jsonb,
                sso_updated_at TIMESTAMPTZ
            )
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_access_log (
                id          BIGINT GENERATED ALWAYS AS IDENTITY PRIMARY KEY,
                user_id     TEXT NOT NULL REFERENCES user_accounts(user_id) ON DELETE CASCADE,
                accessed_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                ip_address  TEXT,
                user_agent  TEXT
            )
        """)
        await self._db.execute("""
            CREATE INDEX IF NOT EXISTS ix_user_access_log_user_time
            ON user_access_log (user_id, accessed_at DESC)
        """)
        await self._db.execute("""
            CREATE TABLE IF NOT EXISTS user_admins (
                user_id  TEXT PRIMARY KEY,
                added_at TIMESTAMPTZ NOT NULL DEFAULT now(),
                added_by TEXT
            )
        """)

        logger.info("User tables are ready: user_accounts, user_access_log, user_admins")

    async def record_access(
            self,
            identity: SsoIdentity,
            ip_address: str | None = None,
            user_agent: str | None = None
    ) -> dict:
        row = await self._db.fetch_one(
            f"""
            WITH account AS (
                INSERT INTO user_accounts (
                    user_id, email, full_name, department, company, unique_name, sid,
                    roles, sso_claims, sso_updated_at, last_access_at, last_access_ip
                )
                VALUES (
                    :uid, :email, :full_name, :department, :company, :unique_name, :sid,
                    CAST(:roles AS JSONB), CAST(:claims AS JSONB), now(), now(), :ip
                )
                ON CONFLICT (user_id) DO UPDATE
                    SET email = EXCLUDED.email,
                        full_name = EXCLUDED.full_name,
                        department = EXCLUDED.department,
                        company = EXCLUDED.company,
                        unique_name = EXCLUDED.unique_name,
                        sid = EXCLUDED.sid,
                        roles = EXCLUDED.roles,
                        sso_claims = EXCLUDED.sso_claims,
                        sso_updated_at = now(),
                        last_access_at = now(),
                        last_access_ip = EXCLUDED.last_access_ip
                RETURNING *
            ), logged AS (
                INSERT INTO user_access_log (user_id, ip_address, user_agent)
                SELECT user_id, CAST(:ip AS TEXT), CAST(:user_agent AS TEXT)
                FROM account
            )
            SELECT account.*, {_IS_ADMIN.format(table="account")}
            FROM account
            """,
            {
                "uid": identity.user_id,
                "email": identity.email,
                "full_name": identity.full_name,
                "department": identity.department,
                "company": identity.company,
                "unique_name": identity.unique_name,
                "sid": identity.sid,
                "roles": json.dumps(identity.roles),
                "claims": json.dumps(identity.claims),
                "ip": ip_address,
                "user_agent": user_agent
            }
        )

        logger.info(f"Recorded access of user {identity.user_id}")
        return self._to_user(row)

    async def get_user(self, user_id: str) -> dict | None:
        row = await self._db.fetch_one(
            f"""
            SELECT user_accounts.*, {_IS_ADMIN.format(table="user_accounts")}
            FROM user_accounts
            WHERE user_id = :uid
            """,
            {"uid": user_id}
        )
        return self._to_user(row) if row else None

    async def list_users(self, is_active: bool | None = None) -> list[dict]:
        rows = await self._db.fetch_all(
            f"""
            SELECT user_accounts.*, {_IS_ADMIN.format(table="user_accounts")}
            FROM user_accounts
            WHERE CAST(:is_active AS BOOLEAN) IS NULL OR is_active = CAST(:is_active AS BOOLEAN)
            ORDER BY created_at DESC
            """,
            {"is_active": is_active}
        )
        return [self._to_user(row) for row in rows]

    async def set_user_active(self, user_id: str, is_active: bool, admin_id: str) -> dict | None:
        row = await self._db.fetch_one(
            f"""
            UPDATE user_accounts
            SET is_active = CAST(:is_active AS BOOLEAN),
                activated_at = CASE WHEN CAST(:is_active AS BOOLEAN) THEN now() ELSE activated_at END,
                activated_by = CASE WHEN CAST(:is_active AS BOOLEAN) THEN CAST(:admin AS TEXT) ELSE activated_by END
            WHERE user_id = :uid
            RETURNING user_accounts.*, {_IS_ADMIN.format(table="user_accounts")}
            """,
            {"uid": user_id, "is_active": is_active, "admin": admin_id}
        )
        if row is None:
            return None

        logger.info(f"User {user_id} was {'activated' if is_active else 'deactivated'} by admin {admin_id}")
        return self._to_user(row)

    async def list_access_logs(self, user_id: str, limit: int) -> list[dict]:
        return await self._db.fetch_all(
            """
            SELECT user_id, accessed_at, ip_address, user_agent
            FROM user_access_log
            WHERE user_id = :uid
            ORDER BY accessed_at DESC, id DESC
            LIMIT :limit
            """,
            {"uid": user_id, "limit": limit}
        )

    async def is_admin(self, user_id: str) -> bool:
        row = await self._db.fetch_one(
            "SELECT user_id FROM user_admins WHERE user_id = :uid",
            {"uid": user_id}
        )
        return row is not None

    async def list_admins(self) -> list[dict]:
        return await self._db.fetch_all(
            """
            SELECT user_id, added_at, added_by
            FROM user_admins
            ORDER BY added_at, user_id
            """
        )

    async def add_admin(self, user_id: str, admin_id: str) -> dict:
        row = await self._db.fetch_one(
            """
            INSERT INTO user_admins (user_id, added_by)
            VALUES (:uid, :admin)
            ON CONFLICT (user_id) DO UPDATE
                SET user_id = EXCLUDED.user_id
            RETURNING user_id, added_at, added_by
            """,
            {"uid": user_id, "admin": admin_id}
        )

        logger.info(f"User {user_id} was added to admins by admin {admin_id}")
        return row

    async def delete_admin(self, user_id: str) -> bool:
        row = await self._db.fetch_one(
            """
            DELETE FROM user_admins
            WHERE user_id = :uid
              AND EXISTS (SELECT 1 FROM user_admins AS others WHERE others.user_id <> :uid)
            RETURNING user_id
            """,
            {"uid": user_id}
        )

        deleted = row is not None
        if deleted:
            logger.info(f"User {user_id} was removed from admins")

        return deleted

    @staticmethod
    def _to_user(row: dict) -> dict:
        return {
            **row,
            "roles": UserRepository._load_json(row.get("roles"), []),
            "sso_claims": UserRepository._load_json(row.get("sso_claims"), {})
        }

    @staticmethod
    def _load_json(value: Any, default: Any) -> Any:
        if value is None:
            return default

        return json.loads(value) if isinstance(value, str) else value
