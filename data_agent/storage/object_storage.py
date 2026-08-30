import logging
import aiofiles
from contextlib import AsyncExitStack
from aiobotocore.session import get_session
from botocore.config import Config
from botocore.exceptions import BotoCoreError, ClientError

from common.config import SETTINGS
from common.constants import PRESIGNED_URL_EXPIRED_IN

logger = logging.getLogger(__name__)


class ObjectStorage:
    def __init__(self):
        self._client = None
        self._session = get_session()
        self._exit_stack = AsyncExitStack()
        self._config = {
            "bucket": SETTINGS.object_storage.bucket,
            "endpoint": SETTINGS.object_storage.endpoint,
            "access_key": SETTINGS.object_storage.access_key,
            "secret_key": SETTINGS.object_storage.secret_key
        }
        self._bucket = self._config["bucket"]

    @property
    def client(self):
        if self._client is None:
            raise RuntimeError("Object storage is not connected: connect() must run at application startup")
        return self._client

    async def connect(self) -> "ObjectStorage":
        if self._client:
            return self

        try:
            self._client = await self._exit_stack.enter_async_context(self._session.create_client(
                "s3",
                endpoint_url=self._config["endpoint"],
                aws_access_key_id=self._config["access_key"],
                aws_secret_access_key=self._config["secret_key"],
                config=Config(signature_version="s3v4")
            ))
            logger.info("Connected to object storage successfully")

            return self
        except (BotoCoreError, ClientError) as e:
            logger.exception(f"Failed to connect to object storage: {str(e)}")
            raise
        except Exception as e:
            logger.exception(f"Unexpected error occurred during object storage connection: {str(e)}")
            raise

    async def close(self) -> None:
        if not self._client:
            return

        try:
            await self._exit_stack.aclose()
            logger.info("Closed object storage client")
        finally:
            self._client = None

    async def list_paginated_objects(
            self,
            prefix: str = "",
            max_items: int = 100,
            bucket: str = None
    ) -> list[str] | None:
        bucket = bucket if bucket else self._bucket
        try:
            objects = []
            paginator = self.client.get_paginator("list_objects_v2")

            async for page in paginator.paginate(
                    Bucket=bucket,
                    Prefix=prefix,
                    PaginationConfig={"MaxItems": max_items}
            ):
                if page["KeyCount"] == 0:
                    continue

                for item in page["Contents"]:
                    objects.append(item["Key"])

            return objects
        except Exception as e:
            logger.exception(f"Failed to list objects in bucket {bucket}: {e}")
            return None

    async def upload_object(
            self,
            file_object: str | bytes,
            key: str, bucket: str = None,
            content_type: str | None = None
    ) -> bool:
        bucket = bucket if bucket else self._bucket
        try:
            if isinstance(file_object, str):
                async with aiofiles.open(file_object, "rb") as f:
                    data = await f.read()
            elif isinstance(file_object, bytes):
                data = file_object
            else:
                raise ValueError("Unsupported file type")

            extra_info = {"ContentType": content_type} if content_type else {}
            await self.client.put_object(Bucket=bucket, Body=data, Key=key, **extra_info)

            logger.info(f"Object uploaded to {bucket} as {key}")
            return True
        except Exception as e:
            logger.exception(f"Failed to upload object {key}: {e}")
            return False

    async def retrieve_object(self, key: str, bucket: str = None) -> bytes | None:
        bucket = bucket if bucket else self._bucket
        try:
            response = await self.client.get_object(Bucket=bucket, Key=key)

            async with response["Body"] as stream:
                data = await stream.read()

            logger.info(f"Data retrieved from {bucket}:{key}")
            return data
        except Exception as e:
            logger.exception(f"Failed to retrieve object {key} from bucket {bucket}: {e}")
            return None

    async def retrieve_object_info(self, key: str, bucket: str = None) -> dict | None:
        bucket = bucket if bucket else self._bucket

        try:
            object_acl = await self.client.head_object(Bucket=bucket, Key=key)

            logger.info(f"ACL retrieved for {bucket}:{key}")
            return object_acl
        except Exception as e:
            logger.exception(f"Failed to retrieve ACL: {e}")
            return None

    async def get_presigned_url(
            self,
            key: str,
            bucket: str = None,
            expires_in: int = PRESIGNED_URL_EXPIRED_IN
    ) -> str:
        bucket = bucket if bucket else self._bucket

        try:
            response = await self.client.generate_presigned_url(
                ClientMethod="get_object",
                Params={"Bucket": bucket, "Key": key},
                ExpiresIn=expires_in
            )

            logger.info(f"Generated presigned url for {key} from {bucket} which expires in {expires_in}")
            return response
        except Exception as e:
            logger.exception(f"Failed to generate presigned url for {key} from bucket {bucket}: {e}")
            raise

    async def delete_objects(self, keys: list[str], bucket: str = None) -> bool:
        bucket = bucket if bucket else self._bucket
        try:
            for i in range(0, len(keys), 1000):
                key_bulk = keys[i:i + 1000]
                response = await self.client.delete_objects(
                    Bucket=bucket, Delete={"Objects": [{"Key": key} for key in key_bulk]}
                )

                deleted_keys = [obj["Key"] for obj in response.get("Deleted", [])]
                logger.info(f"Deleted objects: {deleted_keys} from {bucket}")
            return True
        except Exception as e:
            logger.exception(f"Failed to delete objects: {e}")
            return False
