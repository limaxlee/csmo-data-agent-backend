import pytest
import asyncio
from botocore.exceptions import ClientError

from data_agent.storage import ObjectStorage


class TestObjectStorage:
    @pytest.fixture
    def storage(self, mocker):
        storage = ObjectStorage()
        storage._client = mocker.MagicMock()
        return storage

    def test_client(self, mocker):
        storage = ObjectStorage()

        with pytest.raises(RuntimeError):
            _ = storage.client

        client = mocker.MagicMock()
        storage._client = client
        assert storage.client is client

    def test_connect(self, mocker):
        storage = ObjectStorage()
        client = mocker.MagicMock()
        storage._session = mocker.MagicMock()
        storage._exit_stack = mocker.MagicMock()
        storage._exit_stack.enter_async_context = mocker.AsyncMock(return_value=client)

        assert asyncio.run(storage.connect()) is storage
        assert storage.client is client
        storage._session.create_client.assert_called_once()

        assert asyncio.run(storage.connect()) is storage
        storage._session.create_client.assert_called_once()

        storage = ObjectStorage()
        storage._session = mocker.MagicMock()
        storage._exit_stack = mocker.MagicMock()
        storage._exit_stack.enter_async_context = mocker.AsyncMock(
            side_effect=ClientError({"Error": {"Code": "403"}}, "CreateClient")
        )
        with pytest.raises(ClientError):
            asyncio.run(storage.connect())
        assert storage._client is None

        storage._exit_stack.enter_async_context = mocker.AsyncMock(side_effect=Exception("boom"))
        with pytest.raises(Exception, match="boom"):
            asyncio.run(storage.connect())

    def test_close(self, mocker, storage):
        storage._exit_stack = mocker.MagicMock()
        storage._exit_stack.aclose = mocker.AsyncMock()

        asyncio.run(storage.close())

        storage._exit_stack.aclose.assert_awaited_once()
        assert storage._client is None

        asyncio.run(storage.close())
        storage._exit_stack.aclose.assert_awaited_once()

    def test_list_paginated_objects(self, mocker, storage):
        async def _pages():
            yield {"KeyCount": 0}
            yield {"KeyCount": 2, "Contents": [{"Key": "prefix/a"}, {"Key": "prefix/b"}]}

        paginator = mocker.MagicMock()
        paginator.paginate = mocker.MagicMock(return_value=_pages())
        storage._client.get_paginator.return_value = paginator

        assert asyncio.run(storage.list_paginated_objects(prefix="prefix/")) == ["prefix/a", "prefix/b"]
        assert paginator.paginate.call_args.kwargs["Prefix"] == "prefix/"
        assert paginator.paginate.call_args.kwargs["PaginationConfig"] == {"MaxItems": 100}

        storage._client.get_paginator.side_effect = Exception("boom")
        assert asyncio.run(storage.list_paginated_objects()) is None

    def test_upload_object(self, mocker, storage, tmp_path):
        storage._client.put_object = mocker.AsyncMock(return_value={"ResponseMetadata": {"RequestId": "req-1"}})

        assert asyncio.run(storage.upload_object(b"payload", key="a/b", content_type="image/png")) is True
        assert storage._client.put_object.await_args.kwargs["Body"] == b"payload"
        assert storage._client.put_object.await_args.kwargs["Key"] == "a/b"
        assert storage._client.put_object.await_args.kwargs["ContentType"] == "image/png"

        source = tmp_path / "payload.bin"
        source.write_bytes(b"from disk")
        assert asyncio.run(storage.upload_object(str(source), key="a/c")) is True
        assert storage._client.put_object.await_args.kwargs["Body"] == b"from disk"
        assert "ContentType" not in storage._client.put_object.await_args.kwargs

        assert asyncio.run(storage.upload_object(123, key="a/d")) is False

        storage._client.put_object = mocker.AsyncMock(side_effect=Exception("boom"))
        assert asyncio.run(storage.upload_object(b"payload", key="a/e")) is False

    def test_retrieve_object(self, mocker, storage):
        stream = mocker.MagicMock()
        stream.__aenter__ = mocker.AsyncMock(return_value=stream)
        stream.__aexit__ = mocker.AsyncMock(return_value=False)
        stream.read = mocker.AsyncMock(return_value=b"payload")
        storage._client.get_object = mocker.AsyncMock(
            return_value={"ResponseMetadata": {"RequestId": "req-1"}, "Body": stream}
        )

        assert asyncio.run(storage.retrieve_object(key="a/b")) == b"payload"
        assert storage._client.get_object.await_args.kwargs["Key"] == "a/b"

        storage._client.get_object = mocker.AsyncMock(side_effect=Exception("boom"))
        assert asyncio.run(storage.retrieve_object(key="a/b")) is None

    def test_retrieve_object_info(self, mocker, storage):
        storage._client.head_object = mocker.AsyncMock(return_value={"ContentType": "image/png"})

        assert asyncio.run(storage.retrieve_object_info(key="a/b")) == {"ContentType": "image/png"}
        assert storage._client.head_object.await_args.kwargs["Key"] == "a/b"

        storage._client.head_object = mocker.AsyncMock(side_effect=Exception("boom"))
        assert asyncio.run(storage.retrieve_object_info(key="a/b")) is None

    def test_get_presigned_url(self, mocker, storage):
        storage._client.generate_presigned_url = mocker.AsyncMock(return_value="https://storage/a/b")

        assert asyncio.run(storage.get_presigned_url(key="a/b", expires_in=60)) == "https://storage/a/b"
        assert storage._client.generate_presigned_url.await_args.kwargs["ExpiresIn"] == 60

        storage._client.generate_presigned_url = mocker.AsyncMock(side_effect=Exception("boom"))
        with pytest.raises(Exception, match="boom"):
            asyncio.run(storage.get_presigned_url(key="a/b"))

    def test_delete_objects(self, mocker, storage):
        storage._client.delete_objects = mocker.AsyncMock(
            return_value={"ResponseMetadata": {"RequestId": "req-1"}, "Deleted": [{"Key": "a/b"}]}
        )

        assert asyncio.run(storage.delete_objects(keys=["a/b", "a/c"])) is True
        assert storage._client.delete_objects.await_args.kwargs["Delete"] == {
            "Objects": [{"Key": "a/b"}, {"Key": "a/c"}]
        }

        storage._client.delete_objects = mocker.AsyncMock(
            return_value={"ResponseMetadata": {"RequestId": "req-2"}, "Deleted": []}
        )
        assert asyncio.run(storage.delete_objects(keys=[f"key-{i}" for i in range(1001)])) is True
        assert storage._client.delete_objects.await_count == 2

        storage._client.delete_objects = mocker.AsyncMock(side_effect=Exception("boom"))
        assert asyncio.run(storage.delete_objects(keys=["a/b"])) is False
