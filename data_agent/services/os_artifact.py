import logging
from typing import Optional, Union, Any
from google.adk.artifacts import BaseArtifactService
from google.genai import types

from data_agent.storage import ObjectStorage

logger = logging.getLogger(__name__)


class OSArtifactService(BaseArtifactService):
    def __init__(self, storage: ObjectStorage):
        self._storage = storage

    def get_object_key(self, app_name: str, user_id: str, session_id: str, filename: str, version: int) -> str:
        return f"{app_name}/{user_id}/{session_id}/{filename}/{version}"

    def _get_object_prefix(self, app_name: str, user_id: str, session_id: str, filename: str) -> str:
        return f"{app_name}/{user_id}/{session_id}/{filename}"

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
            raise ValueError(f"Artifact {filename} has no inline_data to store")

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
            raise RuntimeError(f"Failed to upload artifact {filename} for user {user_id}")

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

        data_info = await self._storage.retrieve_object_info(key=data_uri)
        mime_type = data_info.get("ContentType", "application/octet-stream")

        logger.info(f"Loaded artifact {filename} for user {user_id}")
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

        logger.info(f"Listed {len(filenames)} artifact keys for user {user_id}")
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
            data_uri_suffix = data_uri[len(data_uri_prefix):]
            versions.append(int(data_uri_suffix))

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
