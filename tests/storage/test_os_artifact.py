import pytest
import asyncio
from google.genai import types

from data_agent.storage import OSArtifactService


class TestOSArtifactService:
    @pytest.fixture
    def storage(self, mocker):
        return mocker.MagicMock()

    @pytest.fixture
    def service(self, storage):
        return OSArtifactService(storage=storage)

    def test_get_object_key(self, service):
        key = service.get_object_key("data_agent", "user-1", "session-1", "chart.png", 2)
        assert key == "data_agent/user-1/session-1/chart.png/2"

    def test__get_object_prefix(self, service):
        prefix = service._get_object_prefix("data_agent", "user-1", "session-1", "chart.png")
        assert prefix == "data_agent/user-1/session-1/chart.png"

    def test_save_artifact(self, mocker, service, storage):
        artifact = types.Part.from_bytes(data=b"image bytes", mime_type="image/png")
        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[0, 1]))
        storage.upload_object = mocker.AsyncMock(return_value=True)

        version = asyncio.run(service.save_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            artifact=artifact
        ))

        assert version == 2
        assert storage.upload_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/2"
        assert storage.upload_object.await_args.kwargs["content_type"] == "image/png"

        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[]))
        assert asyncio.run(service.save_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            artifact=artifact
        )) == 0

        storage.upload_object = mocker.AsyncMock(return_value=False)
        with pytest.raises(RuntimeError, match="Failed to upload artifact"):
            asyncio.run(service.save_artifact(
                app_name="data_agent",
                user_id="user-1",
                session_id="session-1",
                filename="chart.png",
                artifact=artifact
            ))

    def test_load_artifact(self, mocker, service, storage):
        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[0, 3]))
        storage.retrieve_object = mocker.AsyncMock(return_value=b"image bytes")
        storage.retrieve_object_info = mocker.AsyncMock(return_value={"ContentType": "image/png"})

        part = asyncio.run(service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        ))

        assert storage.retrieve_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/3"
        assert part.inline_data.data == b"image bytes"
        assert part.inline_data.mime_type == "image/png"

        asyncio.run(service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=1
        ))
        assert storage.retrieve_object.await_args.kwargs["key"] == "data_agent/user-1/session-1/chart.png/1"

        storage.retrieve_object_info = mocker.AsyncMock(return_value={})
        part = asyncio.run(service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=0
        ))
        assert part.inline_data.mime_type == "application/octet-stream"

        storage.retrieve_object = mocker.AsyncMock(return_value=None)
        assert asyncio.run(service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )) is None

        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[]))
        assert asyncio.run(service.load_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )) is None

    def test_list_artifact_keys(self, mocker, service, storage):
        storage.list_paginated_objects = mocker.AsyncMock(return_value=[
            "data_agent/user-1/session-1/chart.png/0",
            "data_agent/user-1/session-1/chart.png/1",
            "data_agent/user-1/session-1/reports/summary.pdf/0",
            "data_agent/user-1/session-1/orphan"
        ])

        keys = asyncio.run(service.list_artifact_keys(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        ))

        assert keys == ["chart.png", "reports/summary.pdf"]
        assert storage.list_paginated_objects.await_args.kwargs["prefix"] == "data_agent/user-1/session-1/"

        storage.list_paginated_objects = mocker.AsyncMock(return_value=None)
        assert asyncio.run(service.list_artifact_keys(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1"
        )) == []

    def test_list_versions(self, mocker, service, storage):
        storage.list_paginated_objects = mocker.AsyncMock(return_value=[
            "data_agent/user-1/session-1/chart.png/2",
            "data_agent/user-1/session-1/chart.png/0",
        ])

        versions = asyncio.run(service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        ))

        assert versions == [0, 2]
        assert storage.list_paginated_objects.await_args.kwargs["prefix"] == "data_agent/user-1/session-1/chart.png/"

        storage.list_paginated_objects = mocker.AsyncMock(return_value=[
            "data_agent/user-1/session-1/chart.png/1",
            "data_agent/user-1/session-1/chart.png/latest",
            "data_agent/user-1/session-1/chart.png/2/thumbnail",
        ])
        assert asyncio.run(service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )) == [1]

        storage.list_paginated_objects = mocker.AsyncMock(return_value=None)
        assert asyncio.run(service.list_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )) == []

    def test_delete_artifact(self, mocker, service, storage):
        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[0, 1]))
        storage.delete_objects = mocker.AsyncMock(return_value=True)

        asyncio.run(service.delete_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        ))

        assert storage.delete_objects.await_args.kwargs["keys"] == [
            "data_agent/user-1/session-1/chart.png/0",
            "data_agent/user-1/session-1/chart.png/1"
        ]

        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[]))
        storage.delete_objects = mocker.AsyncMock(return_value=True)
        asyncio.run(service.delete_artifact(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        ))
        storage.delete_objects.assert_not_awaited()

    def test_delete_artifact_propagates_storage_error(self, mocker, service, storage):
        mocker.patch.object(service, "list_versions", new=mocker.AsyncMock(return_value=[0]))
        storage.delete_objects = mocker.AsyncMock(side_effect=Exception("boom"))

        with pytest.raises(Exception, match="boom"):
            asyncio.run(service.delete_artifact(
                app_name="data_agent",
                user_id="user-1",
                session_id="session-1",
                filename="chart.png"
            ))

    def test_list_artifact_versions(self, service):
        assert asyncio.run(service.list_artifact_versions(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png"
        )) is None

    def test_get_artifact_version(self, service):
        assert asyncio.run(service.get_artifact_version(
            app_name="data_agent",
            user_id="user-1",
            session_id="session-1",
            filename="chart.png",
            version=0
        )) is None
