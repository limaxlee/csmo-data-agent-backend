import pytest
from google.genai import types

from common.constants import CONTENT_TYPE
from data_agent.infra import ObjectStorageArtifactService


class TestObjectStorageArtifactService:
    @pytest.fixture
    def storage(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def service(self, storage):
        return ObjectStorageArtifactService(storage=storage)

    @pytest.mark.asyncio
    async def test_load_artifact(self, mocker, service, storage):
        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[0, 3])
        )
        storage.retrieve_object = mocker.AsyncMock(return_value=b"image bytes")
        storage.retrieve_object_info = mocker.AsyncMock(return_value={"ContentType": "image/png"})

        part = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        assert storage.retrieve_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/3"
        assert storage.retrieve_object_info.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/3"
        assert part.inline_data.data == b"image bytes"
        assert part.inline_data.mime_type == "image/png"

        await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=1
        )

        assert storage.retrieve_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/1"

        storage.retrieve_object_info = mocker.AsyncMock(return_value={})

        part = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=0
        )

        assert part.inline_data.mime_type == CONTENT_TYPE

        storage.retrieve_object_info = mocker.AsyncMock(return_value={"ContentType": None})

        part = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=0
        )

        assert part.inline_data.mime_type == CONTENT_TYPE

        storage.retrieve_object_info = mocker.AsyncMock(return_value=None)

        part = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=0
        )

        assert part.inline_data.data == b"image bytes"
        assert part.inline_data.mime_type == CONTENT_TYPE

        storage.retrieve_object = mocker.AsyncMock(return_value=None)
        result = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        assert result is None

        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[])
        )
        result = await service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )
        assert result is None

    @pytest.mark.asyncio
    async def test_save_artifact(self, mocker, service, storage):
        artifact = types.Part.from_bytes(
            data=b"image bytes",
            mime_type="image/png"
        )

        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[0, 1])
        )
        storage.upload_object = mocker.AsyncMock(return_value=True)

        version = await service.save_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            artifact=artifact
        )

        assert version == 2
        assert storage.upload_object.await_args.kwargs["file_object"] == b"image bytes"
        assert storage.upload_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/2"
        assert storage.upload_object.await_args.kwargs["content_type"] == "image/png"

        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[])
        )

        result = await service.save_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            artifact=artifact
        )
        assert result == 0

        storage.upload_object = mocker.AsyncMock(return_value=False)

        with pytest.raises(ValueError):
            await service.save_artifact(
                app_name="data_agent",
                user_id="user-1",
                session_id="session-1",
                filename="chart.png",
                artifact=artifact
            )

        with pytest.raises(ValueError):
            await service.save_artifact(
                app_name="data_agent",
                user_id="user-1",
                session_id="session-1",
                filename="chart.png",
                artifact=types.Part(
                    text="not an inline artifact"
                )
            )

    @pytest.mark.asyncio
    async def test_list_artifact_keys(self, mocker, service, storage):
        storage.list_paginated_objects = mocker.AsyncMock(
            return_value=[
                "data_agent/user-1/session-1/chart.png/0",
                "data_agent/user-1/session-1/chart.png/1",
                "data_agent/user-1/session-1/reports/summary.pdf/0",
                "data_agent/user-1/session-1/orphan"
            ]
        )

        keys = await service.list_artifact_keys(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        )
        assert keys == ["chart.png", "reports/summary.pdf",]
        assert storage.list_paginated_objects.await_args.kwargs["prefix"] == "data_agent/user-1/session-1/"

        storage.list_paginated_objects = mocker.AsyncMock(return_value=None)
        results = await service.list_artifact_keys(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        )
        assert results == []

    @pytest.mark.asyncio
    async def test_list_versions(self, mocker, service, storage):
        storage.list_paginated_objects = mocker.AsyncMock(
            return_value=[
                "data_agent/user-1/session-1/chart.png/2",
                "data_agent/user-1/session-1/chart.png/0"
            ]
        )

        versions = await service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        assert versions == [0, 2]
        assert storage.list_paginated_objects.await_args.kwargs["prefix"] == "data_agent/user-1/session-1/chart.png/"

        storage.list_paginated_objects = mocker.AsyncMock(
            return_value=[
                "data_agent/user-1/session-1/chart.png/1",
                "data_agent/user-1/session-1/chart.png/latest",
                "data_agent/user-1/session-1/chart.png/2/thumbnail"
            ]
        )

        result = await service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )
        assert result == [1]

        storage.list_paginated_objects = mocker.AsyncMock(return_value=None)
        result = await service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        assert result == []

    @pytest.mark.asyncio
    async def test_delete_artifact(self, mocker, service, storage):
        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[0, 1])
        )
        storage.delete_objects = mocker.AsyncMock(return_value=True)

        await service.delete_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        assert storage.delete_objects.await_args.kwargs["keys"] == [
            "data_agent/user-1/session-1/chart.png/0",
            "data_agent/user-1/session-1/chart.png/1"
        ]

        mocker.patch.object(
            service,
            "list_versions",
            new=mocker.AsyncMock(return_value=[])
        )
        storage.delete_objects = mocker.AsyncMock(return_value=True)

        await service.delete_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )

        storage.delete_objects.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_delete_session_artifacts(self, mocker, service, storage):
        keys = [
            "data_agent/user-1/session-1/chart.png/0",
            "data_agent/user-1/session-1/chart.png/1",
            "data_agent/user-1/session-1/reports/summary.pdf/0"
        ]

        storage.list_paginated_objects = mocker.AsyncMock(return_value=keys)
        storage.delete_objects = mocker.AsyncMock(return_value=True)

        deleted = await service.delete_session_artifacts(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        )

        assert deleted == 3
        assert storage.list_paginated_objects.await_args.kwargs["prefix"] == "data_agent/user-1/session-1/"
        assert storage.delete_objects.await_args.kwargs["keys"] == keys

        storage.list_paginated_objects = mocker.AsyncMock(return_value=[])
        storage.delete_objects = mocker.AsyncMock(return_value=True)

        result = await service.delete_session_artifacts(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        )
        assert result == 0

        storage.delete_objects.assert_not_awaited()
