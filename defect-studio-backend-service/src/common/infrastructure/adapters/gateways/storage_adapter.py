"""Adapter: implements StorageGateway using StorageManager.

Wraps raw storage exceptions from :class:`StorageManager` into domain-level
:class:`StorageError` so that application handlers do not need to catch
infrastructure-specific exceptions.
"""

from __future__ import annotations

import logging

from src.common.application.ports.out.gateways import StorageGateway
from src.common.domain.exceptions import StorageError
from src.container.external.storage_manager import StorageManager

logger = logging.getLogger(__name__)


class StorageAdapter(StorageGateway):
    def __init__(self, manager: StorageManager) -> None:
        self._manager = manager

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        try:
            self._manager.upload_bytes(key, data, content_type)
        except StorageError:
            raise
        except Exception as e:
            logger.error("Failed to upload bytes: %s", e)
            raise StorageError(f"Failed to upload file: {e}") from e

    def download_bytes(self, key: str) -> bytes | None:
        try:
            return self._manager.download_bytes(key)
        except StorageError:
            raise
        except Exception as e:
            logger.error("Failed to download bytes: %s", e)
            raise StorageError(f"Failed to download file: {e}") from e

    def delete(self, key: str) -> None:
        try:
            self._manager.delete(key)
        except StorageError:
            raise
        except Exception as e:
            logger.error("Failed to delete: %s", e)
            raise StorageError(f"Failed to delete file: {e}") from e

    def object_fingerprint(self, key: str) -> dict | None:
        try:
            return self._manager.object_fingerprint(key)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError("Failed to inspect input object") from error

    def verified_fingerprint(self, key: str, sha256: str, size: int) -> dict | None:
        try:
            return self._manager.verified_fingerprint(key, sha256, size)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError("Failed to verify input object") from error

    def copy_verified(self, source: str, destination: str, sha256: str,
                      content_type: str = "application/octet-stream") -> bool:
        try:
            return self._manager.copy_verified(source, destination, sha256, content_type)
        except StorageError:
            raise
        except Exception as e:
            raise StorageError("Failed to copy verified input") from e

    def copy_verified_fingerprint(self, source: str, destination: str, sha256: str,
                                  size: int, content_type: str = "application/octet-stream") -> dict | None:
        try:
            return self._manager.copy_verified_fingerprint(source, destination, sha256, size, content_type)
        except StorageError:
            raise
        except Exception as error:
            raise StorageError("Failed to publish verified input") from error

    def list_keys(self, prefix: str) -> list[str]:
        try:
            return self._manager.list_keys(prefix)
        except StorageError:
            raise
        except Exception as e:
            logger.error("Failed to list keys: %s", e)
            raise StorageError(f"Failed to list keys: {e}") from e

