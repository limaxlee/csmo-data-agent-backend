"""Gateway port for object storage (MinIO / local filesystem)."""

from __future__ import annotations

import abc
import hashlib


class StorageGateway(abc.ABC):
    """Port for object storage (MinIO / local filesystem)."""

    @abc.abstractmethod
    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None: ...

    @abc.abstractmethod
    def download_bytes(self, key: str) -> bytes | None: ...

    @abc.abstractmethod
    def delete(self, key: str) -> None: ...

    @abc.abstractmethod
    def list_keys(self, prefix: str) -> list[str]: ...

    def object_fingerprint(self, key: str) -> dict | None:
        """Identify an object already verified by copy_verified; never replace SHA validation."""
        data = self.download_bytes(key)
        if data is None:
            return None
        return {"etag": hashlib.sha256(data).hexdigest(), "size": len(data)}

    def verified_fingerprint(self, key: str, sha256: str, size: int) -> dict | None:
        data = self.download_bytes(key)
        if data is None or len(data) != size or hashlib.sha256(data).hexdigest() != sha256:
            return None
        return {"etag": sha256, "size": size}

    def copy_verified(self, source: str, destination: str, sha256: str,
                      content_type: str = "application/octet-stream") -> bool:
        """Copy only the expected content; fallback for local/custom stores."""
        data = self.download_bytes(source)
        if data is None or hashlib.sha256(data).hexdigest() != sha256:
            return False
        self.upload_bytes(destination, data, content_type)
        return True

    def copy_verified_fingerprint(self, source: str, destination: str, sha256: str,
                                  size: int, content_type: str = "application/octet-stream") -> dict | None:
        """Publish expected bytes and identify that verified destination object."""
        if not self.copy_verified(source, destination, sha256, content_type):
            return None
        return self.verified_fingerprint(destination, sha256, size)
