"""S3-compatible storage manager — supports MinIO and Gage S3 via boto3.

Uses boto3 for S3 compatibility with Gage S3 (Samsung internal),
with SSL verification control for self-signed certificates.

Credentials are read from settings (MINIO_ACCESS_KEY / MINIO_SECRET_KEY),
falling back to S3_ACCESS_KEY / S3_SECRET_KEY environment variables
(to share credentials with DefectAgent).

Local-filesystem fallback is **opt-in** via ``STORAGE_ALLOW_LOCAL_FALLBACK``.
When disabled (the default) any S3 initialisation or bucket-creation failure
raises :class:`StorageInitError` so the service fails fast instead of
silently writing to a directory that disappears on pod restart.  Enable
fallback only for local development where S3/MinIO is not available.
"""

from __future__ import annotations

import logging
import os
import tempfile
from pathlib import Path

from botocore.config import Config as BotoConfig
from src.container.settings import get_settings
from src.common.application.ports.out.gateways.storage import StorageGateway


logger = logging.getLogger(__name__)
settings = get_settings()

_USE_BOTO3 = True
try:
    import boto3
    from botocore.exceptions import ClientError
except ImportError:
    _USE_BOTO3 = False


class StorageInitError(RuntimeError):
    """Raised when S3 storage cannot be initialised and fallback is disabled."""


class StorageManager:
    """Manage file storage in S3-compatible storage (MinIO / Gage S3) or local filesystem fallback.

    When ``STORAGE_ALLOW_LOCAL_FALLBACK`` is ``False`` (default), S3
    initialisation or bucket-creation failures raise
    :class:`StorageInitError` instead of silently falling back.
    """

    def __init__(
        self,
        endpoint: str | None = None,
        access_key: str | None = None,
        secret_key: str | None = None,
        bucket: str | None = None,
        secure: bool | None = None,
    ) -> None:
        self.endpoint = endpoint or settings.minio_endpoint
        # Fall back to S3_ACCESS_KEY / S3_SECRET_KEY env vars (shared with DefectAgent)
        self.access_key = access_key or settings.minio_access_key or os.environ.get("S3_ACCESS_KEY", "")
        self.secret_key = secret_key or settings.minio_secret_key or os.environ.get("S3_SECRET_KEY", "")
        self.bucket = bucket or settings.minio_bucket

        self.secure = secure if secure is not None else settings.minio_secure
        self.verify_ssl = settings.minio_verify_ssl
        self._local_root = Path(settings.storage_root)
        self._s3_client = None
        self._use_s3 = _USE_BOTO3
        self._allow_fallback = settings.storage_allow_local_fallback

        if not self._use_s3 and not self._allow_fallback:
            raise StorageInitError(
                "boto3 is not installed and STORAGE_ALLOW_LOCAL_FALLBACK is false. "
                "Install boto3 or set STORAGE_ALLOW_LOCAL_FALLBACK=true for local development."
            )

        if self._use_s3:
            try:
                scheme = "https" if self.secure else "http"
                endpoint_url = f"{scheme}://{self.endpoint}"
                self._s3_client = boto3.client(
                    "s3",
                    endpoint_url=endpoint_url,
                    aws_access_key_id=self.access_key,
                    aws_secret_access_key=self.secret_key,
                    config=BotoConfig(signature_version="s3v4", max_pool_connections=50),
                    verify=self.verify_ssl,  # respect MINIO_VERIFY_SSL setting
                )

                self._ensure_bucket()
            except Exception as e:
                if not self._allow_fallback:
                    raise StorageInitError(
                        f"S3 storage unavailable ({e}). Set STORAGE_ALLOW_LOCAL_FALLBACK=true "
                        f"to fall back to local filesystem (development only)."
                    ) from e
                logger.warning("S3 unavailable (%s), falling back to local filesystem", e)
                self._use_s3 = False
                self._s3_client = None

        if not self._use_s3:
            self._local_root.mkdir(parents=True, exist_ok=True)
            logger.info("StorageManager using local filesystem: %s", self._local_root)

    def _ensure_bucket(self) -> None:
        if not self._s3_client:
            return
        try:
            self._s3_client.head_bucket(Bucket=self.bucket)
            logger.info("S3 bucket exists: %s", self.bucket)
        except ClientError as e:
            error_code = e.response.get("Error", {}).get("Code", "")
            if error_code in ("404", "NoSuchBucket"):
                if not settings.storage_create_bucket:
                    raise StorageInitError("Configured remote bucket does not exist; automatic creation is disabled") from e
                try:
                    self._s3_client.create_bucket(Bucket=self.bucket)
                    logger.info("Created S3 bucket: %s", self.bucket)
                except Exception as create_err:
                    if not self._allow_fallback:
                        raise StorageInitError(
                            f"Failed to create S3 bucket '{self.bucket}' ({create_err}). "
                            f"Set STORAGE_ALLOW_LOCAL_FALLBACK=true to fall back to local filesystem."
                        ) from create_err
                    logger.warning("Failed to create bucket %s: %s, falling back to local", self.bucket, create_err)
                    self._use_s3 = False
                    self._s3_client = None
                    self._local_root.mkdir(parents=True, exist_ok=True)
            else:
                if not self._allow_fallback:
                    raise StorageInitError(
                        f"Failed to access S3 bucket '{self.bucket}' ({e}). "
                        f"Set STORAGE_ALLOW_LOCAL_FALLBACK=true to fall back to local filesystem."
                    ) from e
                logger.warning("Failed to ensure bucket %s: %s, falling back to local", self.bucket, e)
                self._use_s3 = False
                self._s3_client = None
                self._local_root.mkdir(parents=True, exist_ok=True)

    def upload_bytes(self, key: str, data: bytes, content_type: str = "application/octet-stream") -> None:
        if self._use_s3 and self._s3_client:
            self._s3_client.put_object(
                Bucket=self.bucket,
                Key=key,
                Body=data,
                ContentType=content_type,
            )
        else:
            path = self._local_root / key
            path.parent.mkdir(parents=True, exist_ok=True)
            # Write to a temp file then os.replace onto the target, so a
            # concurrent reader never sees a partially written file. os.replace
            # is atomic on both Windows and Linux. The S3 branch does not need
            # this because put_object replaces the object atomically.
            tmp_fd, tmp_path = tempfile.mkstemp(dir=str(path.parent), suffix=".tmp")
            try:
                with os.fdopen(tmp_fd, "wb") as f:
                    f.write(data)
                os.replace(tmp_path, path)
            except BaseException:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                raise

    def download_bytes(self, key: str) -> bytes | None:
        if self._use_s3 and self._s3_client:
            try:
                response = self._s3_client.get_object(Bucket=self.bucket, Key=key)
                return response["Body"].read()
            except ClientError as e:
                error_code = e.response.get("Error", {}).get("Code", "")
                if error_code in ("404", "NoSuchKey"):
                    return None
                logger.error("Failed to download %s: %s", key, e)
                return None
            except Exception as e:
                logger.error("Failed to download %s: %s", key, e)
                return None
        else:
            path = self._local_root / key
            if not path.exists():
                return None
            return path.read_bytes()

    def object_fingerprint(self, key: str) -> dict | None:
        if not self._use_s3 or not self._s3_client:
            return StorageGateway.object_fingerprint(self, key)
        try:
            response = self._s3_client.head_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "NotFound", "404"):
                return None
            raise
        if not response.get("ETag"):
            return None  # A store without object identities uses the full export path.
        return {"etag": response["ETag"], "size": response["ContentLength"]}

    def verified_fingerprint(self, key: str, sha256: str, size: int) -> dict | None:
        """Bootstrap old manifests, pinning the identity of the exact bytes read."""
        import hashlib

        if not self._use_s3 or not self._s3_client:
            return StorageGateway.verified_fingerprint(self, key, sha256, size)
        try:
            response = self._s3_client.get_object(Bucket=self.bucket, Key=key)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        body, digest, length = response["Body"], hashlib.sha256(), 0
        try:
            while chunk := body.read(1024 * 1024):
                digest.update(chunk)
                length += len(chunk)
        finally:
            body.close()
        if length != size or digest.hexdigest() != sha256:
            return None
        if not response.get("ETag"):
            # Content is verified, but HEAD cannot identify this object later.
            # Publication succeeds and future jobs use the full export path.
            return {"sha256": sha256, "size": length}
        return {"etag": response["ETag"], "size": length}

    def copy_verified(self, source: str, destination: str, sha256: str,
                      content_type: str = "application/octet-stream") -> bool:
        if not self._use_s3 or not self._s3_client:
            return StorageGateway.copy_verified(self, source, destination, sha256, content_type)
        return self._copy_verified_receipt(source, destination, sha256, content_type) is not None

    def copy_verified_fingerprint(self, source: str, destination: str, sha256: str,
                                  size: int, content_type: str = "application/octet-stream") -> dict | None:
        """Verify source bytes once, then pin the conditional copy's destination.

        ETags identify objects here; they are never treated as SHA-256 hashes.
        Stores without a copy receipt retain the full destination verification.
        """
        if not self._use_s3 or not self._s3_client:
            return StorageGateway.copy_verified_fingerprint(self, source, destination, sha256, size, content_type)
        receipt = self._copy_verified_receipt(source, destination, sha256, content_type, size)
        if receipt is None:
            return None
        result = receipt.get("CopyObjectResult", {})
        etag = result.get("ETag") if isinstance(result, dict) else None
        if not isinstance(etag, str) or not etag:
            return self.verified_fingerprint(destination, sha256, size)
        try:
            response = self._s3_client.head_object(Bucket=self.bucket, Key=destination)
        except ClientError as error:
            code = error.response.get("Error", {}).get("Code")
            if code in ("NoSuchKey", "NotFound", "404"):
                return None
            if code in ("NotImplemented", "MethodNotAllowed", "501", "405"):
                return self.verified_fingerprint(destination, sha256, size)
            raise
        if not response.get("ETag"):
            return self.verified_fingerprint(destination, sha256, size)
        if response["ETag"] != etag or response.get("ContentLength") != size:
            return None
        if receipt.get("VersionId") and response.get("VersionId") != receipt["VersionId"]:
            return None
        return {"etag": etag, "size": size}

    def _copy_verified_receipt(self, source: str, destination: str, sha256: str,
                               content_type: str, size: int | None = None) -> dict | None:
        import hashlib

        try:
            response = self._s3_client.get_object(Bucket=self.bucket, Key=source)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("NoSuchKey", "404"):
                return None
            raise
        body = response["Body"]
        try:
            digest, length = hashlib.sha256(), 0
            while chunk := body.read(1024 * 1024):
                digest.update(chunk)
                length += len(chunk)
        finally:
            body.close()
        if digest.hexdigest() != sha256 or (size is not None and length != size):
            return None
        # Validate the whole SHA-256 as before, then copy that exact S3 version
        # internally. ETag alone is not a sufficient integrity check.
        etag = response.get("ETag")
        if not etag:
            # Stores lacking conditional copy support retain the safe fallback.
            data = self.download_bytes(source)
            if (data is None or hashlib.sha256(data).hexdigest() != sha256
                    or (size is not None and len(data) != size)):
                return None
            self.upload_bytes(destination, data, content_type)
            return {}
        try:
            receipt = self._s3_client.copy_object(Bucket=self.bucket, Key=destination,
                CopySource={"Bucket": self.bucket, "Key": source}, CopySourceIfMatch=etag,
                MetadataDirective="REPLACE", ContentType=content_type)
        except ClientError as error:
            if error.response.get("Error", {}).get("Code") in ("PreconditionFailed", "412"):
                return None
            raise
        # Some compatible stores omit the receipt. They must use a final GET.
        if not isinstance(receipt, dict):
            return {}
        if receipt.get("Error"):
            raise RuntimeError("Object copy returned an embedded error")
        return receipt

    def delete(self, key: str) -> None:
        if self._use_s3 and self._s3_client:
            try:
                self._s3_client.delete_object(Bucket=self.bucket, Key=key)
            except ClientError as e:
                logger.error("Failed to delete %s: %s", key, e)
        else:
            path = self._local_root / key
            if path.exists():
                path.unlink()

    def list_keys(self, prefix: str) -> list[str]:
        if self._use_s3 and self._s3_client:
            try:
                results: list[str] = []
                paginator = self._s3_client.get_paginator("list_objects_v2")
                pages = paginator.paginate(Bucket=self.bucket, Prefix=prefix)
                for page in pages:
                    if "Contents" in page:
                        for obj in page["Contents"]:
                            results.append(obj["Key"])
                return results
            except ClientError as e:
                logger.error("Failed to list %s: %s", prefix, e)
                return []
        else:
            prefix_path = self._local_root / prefix
            if not prefix_path.exists():
                return []
            results = []
            for p in prefix_path.rglob("*"):
                if p.is_file():
                    rel = p.relative_to(self._local_root)
                    # as_posix() keeps the separator as "/" on Windows too, so a key
                    # from this branch has the same shape as a key from S3. Callers
                    # split keys on "/" to take the filename.
                    results.append(rel.as_posix())
            return results
