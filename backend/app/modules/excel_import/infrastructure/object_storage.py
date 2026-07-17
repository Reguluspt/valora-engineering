"""Object storage port + in-memory fake + S3-compatible adapter."""
from __future__ import annotations

import hashlib
import io
import os
from dataclasses import dataclass
from typing import BinaryIO, Protocol

# Bounded chunk size for stream materialization (security gate: no bare .read())
_READ_CHUNK = 64 * 1024
# Hard ceiling for a single object buffer in-process (matches source-artifact max upload)
_MAX_OBJECT_BYTES = 10 * 1024 * 1024


class ObjectStorageError(Exception):
    """Non-not-found storage failure (permission/network/timeout/etc.)."""

    def __init__(self, code: str, message: str = ""):
        self.code = code
        super().__init__(message or code)


class ObjectNotFound(Exception):
    """Exact object key missing."""


def _read_stream_bounded(stream: BinaryIO, *, max_bytes: int, expected_size: int | None = None) -> bytes:
    """Read stream in chunks with a hard size ceiling (never bare stream.read())."""
    chunks: list[bytes] = []
    total = 0
    while True:
        chunk = stream.read(_READ_CHUNK)
        if not chunk:
            break
        total += len(chunk)
        if total > max_bytes:
            raise ObjectStorageError("object_too_large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if expected_size is not None and len(data) != expected_size:
        raise ObjectStorageError("size_mismatch")
    return data


@dataclass(frozen=True)
class ObjectStat:
    size: int
    etag: str | None = None
    content_type: str | None = None


class ObjectStoragePort(Protocol):
    def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        expected_size: int | None = None,
    ) -> ObjectStat: ...

    def head(self, key: str) -> ObjectStat | None: ...

    def open_stream(self, key: str) -> BinaryIO: ...

    def delete(self, key: str) -> None: ...

    def ensure_bucket(self) -> None: ...


class FakeObjectStorage:
    """Deterministic in-memory store for unit tests."""

    def __init__(self) -> None:
        self._objects: dict[str, bytes] = {}
        self._content_types: dict[str, str] = {}
        self.fail_put: bool = False
        self.fail_head: bool = False
        self.fail_delete: bool = False
        self.fail_after_put: bool = False
        self.head_raises: Exception | None = None
        self.delete_raises: Exception | None = None

    def ensure_bucket(self) -> None:
        return None

    def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        expected_size: int | None = None,
    ) -> ObjectStat:
        if self.fail_put:
            raise ObjectStorageError("fake_put_failed")
        if key in self._objects:
            raise ObjectStorageError("object_key_exists")
        data = _read_stream_bounded(
            stream,
            max_bytes=_MAX_OBJECT_BYTES,
            expected_size=expected_size,
        )
        self._objects[key] = data
        self._content_types[key] = content_type
        return ObjectStat(size=len(data), etag=hashlib.md5(data).hexdigest(), content_type=content_type)

    def head(self, key: str) -> ObjectStat | None:
        if self.head_raises is not None:
            raise self.head_raises
        if self.fail_head:
            raise ObjectStorageError("fake_head_failed")
        data = self._objects.get(key)
        if data is None:
            return None
        return ObjectStat(
            size=len(data),
            etag=hashlib.md5(data).hexdigest(),
            content_type=self._content_types.get(key),
        )

    def open_stream(self, key: str) -> BinaryIO:
        data = self._objects.get(key)
        if data is None:
            raise ObjectNotFound(key)
        return io.BytesIO(data)

    def delete(self, key: str) -> None:
        """Idempotent for missing keys; raises ObjectStorageError on forced failure."""
        if self.delete_raises is not None:
            raise self.delete_raises
        if self.fail_delete:
            raise ObjectStorageError("fake_delete_failed")
        self._objects.pop(key, None)
        self._content_types.pop(key, None)


def _is_not_found_error(exc: BaseException) -> bool:
    """Exact object missing only — never bucket/infra failures."""
    try:
        from botocore.exceptions import ClientError

        if isinstance(exc, ClientError):
            code = (exc.response or {}).get("Error", {}).get("Code", "")
            # NoSuchBucket is infrastructure — must NOT be treated as object absence
            if code in {"NoSuchBucket", "AccessDenied", "403", "401"}:
                return False
            return code in {"404", "NoSuchKey", "NotFound"}
    except Exception:
        pass
    name = type(exc).__name__
    msg = str(exc).lower()
    if "nosuchbucket" in msg or "accessdenied" in msg:
        return False
    if "nosuchkey" in msg:
        return True
    if name in {"NoSuchKey"}:
        return True
    # Avoid bare "not found" matching bucket errors
    if "the specified key does not exist" in msg:
        return True
    return False


class S3ObjectStorage:
    """S3-compatible storage via boto3 (MinIO-friendly)."""

    def __init__(
        self,
        *,
        endpoint_url: str,
        access_key: str,
        secret_key: str,
        bucket: str,
        region: str = "us-east-1",
    ):
        import boto3
        from botocore.client import Config

        self._bucket = bucket
        self._client = boto3.client(
            "s3",
            endpoint_url=endpoint_url,
            aws_access_key_id=access_key,
            aws_secret_access_key=secret_key,
            region_name=region,
            config=Config(signature_version="s3v4"),
        )

    def ensure_bucket(self) -> None:
        try:
            self._client.head_bucket(Bucket=self._bucket)
        except Exception as exc:
            if os.environ.get("VALORA_ENV", "local") in {"local", "test"} or os.environ.get("CI") == "true":
                try:
                    self._client.create_bucket(Bucket=self._bucket)
                except Exception as create_exc:
                    try:
                        self._client.head_bucket(Bucket=self._bucket)
                    except Exception:
                        raise ObjectStorageError(
                            "bucket_unavailable",
                            type(create_exc).__name__,
                        ) from create_exc
            else:
                raise ObjectStorageError("bucket_missing") from exc

    def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        expected_size: int | None = None,
    ) -> ObjectStat:
        if self.head(key) is not None:
            raise ObjectStorageError("object_key_exists")
        extra = {"ContentType": content_type}
        try:
            self._client.upload_fileobj(stream, self._bucket, key, ExtraArgs=extra)
        except Exception as exc:
            raise ObjectStorageError("put_failed", type(exc).__name__) from exc
        st = self.head(key)
        if st is None:
            raise ObjectStorageError("put_verify_missing")
        if expected_size is not None and st.size != expected_size:
            try:
                self.delete(key)
            except Exception:
                pass
            raise ObjectStorageError("size_mismatch")
        return st

    def head(self, key: str) -> ObjectStat | None:
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            if _is_not_found_error(exc):
                return None
            raise ObjectStorageError("head_failed", type(exc).__name__) from exc
        return ObjectStat(
            size=int(resp.get("ContentLength") or 0),
            etag=(resp.get("ETag") or "").strip('"') or None,
            content_type=resp.get("ContentType"),
        )

    def open_stream(self, key: str) -> BinaryIO:
        try:
            resp = self._client.get_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            if _is_not_found_error(exc):
                raise ObjectNotFound(key) from exc
            raise ObjectStorageError("get_failed", type(exc).__name__) from exc
        body = resp["Body"]
        data = _read_stream_bounded(body, max_bytes=_MAX_OBJECT_BYTES)
        return io.BytesIO(data)

    def delete(self, key: str) -> None:
        """Delete exact key. Missing key is idempotent success; other errors propagate."""
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception as exc:
            if _is_not_found_error(exc):
                return
            raise ObjectStorageError("delete_failed", type(exc).__name__) from exc
        # Verify gone (or already gone)
        st = self.head(key)
        if st is not None:
            raise ObjectStorageError("delete_verify_failed")


def build_object_storage_from_settings(settings) -> ObjectStoragePort:
    return S3ObjectStorage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )


_STORAGE_OVERRIDE: ObjectStoragePort | None = None


def set_object_storage_override(storage: ObjectStoragePort | None) -> None:
    global _STORAGE_OVERRIDE
    _STORAGE_OVERRIDE = storage


def get_object_storage() -> ObjectStoragePort:
    if _STORAGE_OVERRIDE is not None:
        return _STORAGE_OVERRIDE
    from app.core.config import get_settings

    return build_object_storage_from_settings(get_settings())
