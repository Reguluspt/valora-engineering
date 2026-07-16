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
            raise RuntimeError("object_too_large")
        chunks.append(chunk)
    data = b"".join(chunks)
    if expected_size is not None and len(data) != expected_size:
        raise RuntimeError("size_mismatch")
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
        self.fail_after_put: bool = False  # simulate post-write caller failure externally

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
            raise RuntimeError("fake_put_failed")
        if key in self._objects:
            raise RuntimeError("object_key_exists")
        data = _read_stream_bounded(
            stream,
            max_bytes=_MAX_OBJECT_BYTES,
            expected_size=expected_size,
        )
        self._objects[key] = data
        self._content_types[key] = content_type
        return ObjectStat(size=len(data), etag=hashlib.md5(data).hexdigest(), content_type=content_type)

    def head(self, key: str) -> ObjectStat | None:
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
            raise FileNotFoundError(key)
        return io.BytesIO(data)

    def delete(self, key: str) -> None:
        self._objects.pop(key, None)
        self._content_types.pop(key, None)


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
        except Exception:
            # Local/CI: create if missing; production policy should pre-provision.
            if os.environ.get("VALORA_ENV", "local") in {"local", "test"} or os.environ.get("CI") == "true":
                try:
                    self._client.create_bucket(Bucket=self._bucket)
                except Exception as exc:
                    # Bucket may race-create
                    try:
                        self._client.head_bucket(Bucket=self._bucket)
                    except Exception:
                        raise RuntimeError(f"bucket_unavailable:{type(exc).__name__}") from exc
            else:
                raise RuntimeError("bucket_missing")

    def put_stream(
        self,
        key: str,
        stream: BinaryIO,
        *,
        content_type: str,
        expected_size: int | None = None,
    ) -> ObjectStat:
        # Refuse overwrite: head first
        if self.head(key) is not None:
            raise RuntimeError("object_key_exists")
        extra = {"ContentType": content_type}
        self._client.upload_fileobj(stream, self._bucket, key, ExtraArgs=extra)
        st = self.head(key)
        if st is None:
            raise RuntimeError("put_verify_missing")
        if expected_size is not None and st.size != expected_size:
            # best-effort cleanup of bad object
            try:
                self.delete(key)
            except Exception:
                pass
            raise RuntimeError("size_mismatch")
        return st

    def head(self, key: str) -> ObjectStat | None:
        try:
            resp = self._client.head_object(Bucket=self._bucket, Key=key)
        except Exception:
            return None
        return ObjectStat(
            size=int(resp.get("ContentLength") or 0),
            etag=(resp.get("ETag") or "").strip('"') or None,
            content_type=resp.get("ContentType"),
        )

    def open_stream(self, key: str) -> BinaryIO:
        resp = self._client.get_object(Bucket=self._bucket, Key=key)
        body = resp["Body"]
        # StreamingBody supports sized reads; bound total object materialization.
        data = _read_stream_bounded(body, max_bytes=_MAX_OBJECT_BYTES)
        return io.BytesIO(data)

    def delete(self, key: str) -> None:
        try:
            self._client.delete_object(Bucket=self._bucket, Key=key)
        except Exception:
            # idempotent
            pass


def build_object_storage_from_settings(settings) -> ObjectStoragePort:
    return S3ObjectStorage(
        endpoint_url=settings.s3_endpoint_url,
        access_key=settings.s3_access_key_id,
        secret_key=settings.s3_secret_access_key,
        bucket=settings.s3_bucket,
        region=settings.s3_region,
    )


# Process-wide override for tests
_STORAGE_OVERRIDE: ObjectStoragePort | None = None


def set_object_storage_override(storage: ObjectStoragePort | None) -> None:
    global _STORAGE_OVERRIDE
    _STORAGE_OVERRIDE = storage


def get_object_storage() -> ObjectStoragePort:
    if _STORAGE_OVERRIDE is not None:
        return _STORAGE_OVERRIDE
    from app.core.config import get_settings

    return build_object_storage_from_settings(get_settings())
