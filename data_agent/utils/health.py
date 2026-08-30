from asyncio import TimeoutError
from aiobotocore.session import get_session
from asyncpg import connect, PostgresError
from botocore.config import Config
from botocore.exceptions import ClientError, EndpointConnectionError, ConnectTimeoutError

from common.config import SETTINGS
from common.constants import HEALTH_CHECK_TIMEOUT


async def check_postgres_health() -> bool:
    try:
        connection = await connect(
            host=SETTINGS.postgresql_db.host,
            port=SETTINGS.postgresql_db.port,
            database=SETTINGS.postgresql_db.name,
            user=SETTINGS.postgresql_db.user,
            timeout=HEALTH_CHECK_TIMEOUT
        )

        try:
            ping = await connection.fetchval("SELECT 1;")
            return ping == 1
        finally:
            await connection.close()
    except (PostgresError, TimeoutError, OSError):
        return False


async def check_storage_health() -> bool:
    session = get_session()
    config = Config(
        signature_version="s3v4",
        connect_timeout=HEALTH_CHECK_TIMEOUT,
        read_timeout=HEALTH_CHECK_TIMEOUT,
        retries={"max_attempts": 1},
    )
    try:
        async with session.create_client(
                "s3",
                endpoint_url=SETTINGS.object_storage.endpoint,
                aws_access_key_id=SETTINGS.object_storage.access_key,
                aws_secret_access_key=SETTINGS.object_storage.secret_key,
                config=config
        ) as client:
            await client.head_bucket(Bucket=SETTINGS.object_storage.bucket)
            return True
    except (ClientError, EndpointConnectionError, ConnectTimeoutError, OSError):
        return False
