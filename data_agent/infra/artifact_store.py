import logging
from typing import Optional, Union, Any
from google.adk.artifacts import BaseArtifactService
from google.genai import types

from common.constants import CONTENT_TYPE
from data_agent.infra.object_storage import ObjectStorage

logger = logging.getLogger(__name__)


class ObjectStorageArtifactService(BaseArtifactService):
    def __init__(self, storage: ObjectStorage):
        self._storage = storage

    @staticmethod
    def _get_object_prefix(app_name: str, user_id: str, session_id: str, filename: str) -> str:
        return f"{app_name}/{user_id}/{session_id}/{filename}"

    @staticmethod
    def get_object_key(app_name: str, user_id: str, session_id: str, filename: str, version: int) -> str:
        return f"{app_name}/{user_id}/{session_id}/{filename}/{version}"

    @staticmethod
    def parse_version(object_key: str) -> int:
        """Inverse of `get_object_key`: the version is the last path segment."""
        _, _, version = object_key.rpartition("/")
        if not version.isdigit():
            raise ValueError(f"Object key has no version segment: {object_key}")
        return int(version)

    async def save_artifact(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            artifact: Union[types.Part, dict[str, Any]],
            session_id: Optional[str] = None,
            custom_metadata: Optional[dict[str, Any]] = None
    ) -> int:
        if artifact.inline_data is None:
            raise ValueError(f"User {user_id}'s session {session_id} has no artifact {filename} to upload")

        versions = await self.list_versions(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename
        )
        version = 0 if not versions else max(versions) + 1
        data_uri = self.get_object_key(app_name, user_id, session_id, filename, version)

        response = await self._storage.upload_object(
            file_object=artifact.inline_data.data,
            key=data_uri,
            content_type=artifact.inline_data.mime_type
        )
        if not response:
            raise RuntimeError(f"Failed to upload artifact {filename} of session {session_id} for user {user_id}")

        logger.info(f"Uploaded artifact {filename} for user {user_id} with key {data_uri}")
        return version

    async def load_artifact(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            session_id: Optional[str] = None,
            version: Optional[int] = None
    ) -> Optional[types.Part]:
        if version is None:
            versions = await self.list_versions(
                app_name=app_name,
                user_id=user_id,
                session_id=session_id,
                filename=filename
            )
            if not versions:
                return None
            version = max(versions)

        data_uri = self.get_object_key(app_name, user_id, session_id, filename, version)
        data_object = await self._storage.retrieve_object(key=data_uri)
        if data_object is None:
            return None

        # The head call is best effort: a missing or failed head must not turn a
        # successfully retrieved object into an error.
        data_info = await self._storage.retrieve_object_info(key=data_uri) or {}
        mime_type = data_info.get("ContentType") or CONTENT_TYPE

        logger.info(f"Loaded artifact {filename} of session {session_id} for user {user_id}")
        return types.Part.from_bytes(data=data_object, mime_type=mime_type)

    async def list_artifact_keys(self, *, app_name: str, user_id: str, session_id: Optional[str] = None) -> list[str]:
        filenames = set()
        session_prefix = f"{app_name}/{user_id}/{session_id}/"

        data_uris = await self._storage.list_paginated_objects(prefix=session_prefix) or []
        for data_uri in data_uris:
            session_suffix = data_uri[len(session_prefix):]
            if "/" not in session_suffix:
                continue

            filename, _ = session_suffix.rsplit("/", 1)
            filenames.add(filename)

        logger.info(f"Listed {len(filenames)} artifact keys of session {session_id} for user {user_id}")
        return sorted(filenames)

    async def list_versions(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            session_id: Optional[str] = None
    ) -> list[int]:
        data_uri_prefix = self._get_object_prefix(app_name, user_id, session_id, filename) + "/"
        data_uris = await self._storage.list_paginated_objects(prefix=data_uri_prefix) or []
        versions = []

        for data_uri in data_uris:
            suffix = data_uri[len(data_uri_prefix):]
            if not suffix.isdigit():
                logger.warning(f"Skipping incorrect artifact key {data_uri} of session {session_id} for user {user_id}")
                continue
            versions.append(int(suffix))

        logger.info(f"Listed {len(versions)} artifact versions of filename {filename} for user {user_id}")
        return sorted(versions)

    async def delete_artifact(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            session_id: Optional[str] = None
    ) -> None:
        versions = await self.list_versions(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id,
            filename=filename
        )
        if not versions:
            return

        data_uris = [
            self.get_object_key(app_name, user_id, session_id, filename, version)
            for version in versions
        ]
        await self._storage.delete_objects(keys=data_uris)
        logger.info(f"Deleted artifact {filename} with {len(data_uris)} versions for user {user_id}")

    async def delete_session_artifacts(self, *, app_name: str, user_id: str, session_id: str) -> int:
        """Delete every object under the session prefix and return how many were removed.

        Raises if the listing or the delete fails, so a caller removing the
        session can stop before it orphans the objects.
        """
        session_prefix = f"{app_name}/{user_id}/{session_id}/"
        keys = await self._storage.list_paginated_objects(prefix=session_prefix)
        if keys is None:
            raise RuntimeError(f"Failed to list artifacts of session {session_id} for user {user_id}")
        if not keys:
            return 0

        if not await self._storage.delete_objects(keys=keys):
            raise RuntimeError(f"Failed to delete artifacts of session {session_id} for user {user_id}")

        logger.info(f"Deleted {len(keys)} artifact objects of session {session_id} for user {user_id}")
        return len(keys)

    async def list_artifact_versions(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            session_id: Optional[str] = None
    ):
        ...

    async def get_artifact_version(
            self,
            *,
            app_name: str,
            user_id: str,
            filename: str,
            session_id: Optional[str] = None,
            version: Optional[int] = None
    ):
        ...
