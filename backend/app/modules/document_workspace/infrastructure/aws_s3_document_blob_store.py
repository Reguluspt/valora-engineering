"""AWS S3 adapter for create-only immutable document candidates.

This module is local spike preparation only. It has no settings/service wiring and does not
perform bucket, IAM, lifecycle, KMS, or other control-plane operations.
"""
from __future__ import annotations

import asyncio
import base64
import hashlib
import re
import tempfile
from collections.abc import AsyncIterable
from dataclasses import dataclass
from datetime import datetime
from typing import Any, BinaryIO

import boto3
from botocore.client import Config
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    ParamValidationError,
)
from botocore.parsers import ResponseParserError

from app.modules.document_workspace.domain.document_blob_store import (
    ChecksumVerification,
    ChecksumVerificationStatus,
    CleanupResult,
    CleanupStatus,
    CreateImmutableResult,
    CreateImmutableStatus,
    ObjectObservation,
    ObjectObservationStatus,
)


_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_SAFE_REQUEST_ID_RE = re.compile(r"^[A-Za-z0-9._:/+=-]{1,255}$")
_READ_CHUNK = 64 * 1024
_MIN_MULTIPART_PART_SIZE = 5 * 1024 * 1024
_DEFAULT_MULTIPART_SIZE = 8 * 1024 * 1024
_MAX_MULTIPART_PARTS = 10_000


@dataclass(frozen=True)
class _StreamedObject:
    status: ChecksumVerificationStatus
    sha256: str | None = None
    byte_length: int | None = None
    etag: str | None = None
    version_id: str | None = None


def _status_code(exc: ClientError) -> int | None:
    metadata = (exc.response or {}).get("ResponseMetadata") or {}
    status = metadata.get("HTTPStatusCode")
    if isinstance(status, int):
        return status
    code = str((exc.response or {}).get("Error", {}).get("Code") or "")
    if code.isdigit():
        return int(code)
    return None


def _error_code(exc: ClientError) -> str:
    return str((exc.response or {}).get("Error", {}).get("Code") or "")


def _is_missing(exc: ClientError) -> bool:
    return _status_code(exc) == 404 or _error_code(exc) in {"NoSuchKey", "NotFound", "404"}


def _request_id(response: Any) -> str | None:
    if not isinstance(response, dict):
        return None
    value = str((response.get("ResponseMetadata") or {}).get("RequestId") or "")
    return value if _SAFE_REQUEST_ID_RE.fullmatch(value) else None


def _successful_response(response: Any) -> bool:
    if not isinstance(response, dict):
        return False
    status = (response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return isinstance(status, int) and 200 <= status < 300


def _opaque_text(value: Any, *, maximum: int = 1024) -> str | None:
    if not isinstance(value, str) or not value or len(value) > maximum:
        return None
    return value


def _read_digest(body: Any) -> tuple[str, int]:
    if body is None or not callable(getattr(body, "read", None)):
        raise ValueError("S3 response body is not readable")
    digest = hashlib.sha256()
    byte_length = 0
    while True:
        chunk = body.read(_READ_CHUNK)
        if not chunk:
            break
        if not isinstance(chunk, bytes):
            raise ValueError("S3 response body returned non-bytes data")
        digest.update(chunk)
        byte_length += len(chunk)
    return digest.hexdigest(), byte_length


class AwsS3DocumentBlobStore:
    """Narrow AWS S3 implementation of the four-operation document blob port."""

    def __init__(
        self,
        *,
        bucket: str,
        key_prefix: str,
        region_name: str,
        client: Any | None = None,
        multipart_threshold: int = _DEFAULT_MULTIPART_SIZE,
        multipart_part_size: int = _DEFAULT_MULTIPART_SIZE,
    ) -> None:
        normalized_bucket = bucket.strip()
        normalized_region = region_name.strip()
        normalized_prefix = key_prefix.strip().strip("/")
        if not normalized_bucket or not normalized_region or not normalized_prefix:
            raise ValueError("S3 bucket, region, and dedicated key prefix are required")
        if multipart_part_size < _MIN_MULTIPART_PART_SIZE:
            raise ValueError("S3 multipart parts must be at least 5 MiB")
        if multipart_threshold < multipart_part_size:
            raise ValueError("S3 multipart threshold cannot be smaller than the part size")
        self._bucket = normalized_bucket
        self._key_prefix = f"{normalized_prefix}/"
        self._multipart_threshold = multipart_threshold
        self._multipart_part_size = multipart_part_size
        if client is None:
            client = boto3.client(
                "s3",
                region_name=normalized_region,
                config=Config(
                    signature_version="s3v4",
                    retries={"total_max_attempts": 1},
                ),
            )
        self._client = client

    def _key_is_allowed(self, object_key: str) -> bool:
        return (
            isinstance(object_key, str)
            and object_key.startswith(self._key_prefix)
            and len(object_key) > len(self._key_prefix)
        )

    async def create_immutable(
        self,
        *,
        object_key: str,
        content: AsyncIterable[bytes],
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult:
        if (
            not self._key_is_allowed(object_key)
            or byte_length < 0
            or not _SHA256_RE.fullmatch(expected_sha256)
        ):
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        if (
            byte_length >= self._multipart_threshold
            and (byte_length + self._multipart_part_size - 1) // self._multipart_part_size
            > _MAX_MULTIPART_PARTS
        ):
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        with tempfile.TemporaryFile(mode="w+b") as staged:
            digest = hashlib.sha256()
            actual_length = 0
            try:
                async for chunk in content:
                    if not isinstance(chunk, bytes):
                        return CreateImmutableResult(CreateImmutableStatus.REJECTED)
                    actual_length += len(chunk)
                    if actual_length > byte_length:
                        return CreateImmutableResult(CreateImmutableStatus.REJECTED)
                    digest.update(chunk)
                    staged.write(chunk)
            except Exception:
                return CreateImmutableResult(CreateImmutableStatus.REJECTED)
            if actual_length != byte_length or digest.hexdigest() != expected_sha256:
                return CreateImmutableResult(CreateImmutableStatus.REJECTED)
            staged.seek(0)
            if byte_length < self._multipart_threshold:
                return await self._put_object(
                    object_key=object_key,
                    body=staged,
                    byte_length=byte_length,
                    expected_sha256=expected_sha256,
                )
            return await self._put_multipart(
                object_key=object_key,
                body=staged,
                byte_length=byte_length,
            )

    async def _put_object(
        self,
        *,
        object_key: str,
        body: BinaryIO,
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult:
        checksum = base64.b64encode(bytes.fromhex(expected_sha256)).decode("ascii")
        try:
            response = await asyncio.to_thread(
                self._client.put_object,
                Bucket=self._bucket,
                Key=object_key,
                Body=body,
                ContentLength=byte_length,
                ChecksumAlgorithm="SHA256",
                ChecksumSHA256=checksum,
                IfNoneMatch="*",
            )
        except Exception as exc:
            return self._classify_final_write_error(exc)
        return self._created_result(response)

    async def _put_multipart(
        self,
        *,
        object_key: str,
        body: BinaryIO,
        byte_length: int,
    ) -> CreateImmutableResult:
        try:
            initiated = await asyncio.to_thread(
                self._client.create_multipart_upload,
                Bucket=self._bucket,
                Key=object_key,
                ChecksumAlgorithm="SHA256",
                ChecksumType="COMPOSITE",
            )
        except Exception as exc:
            return self._classify_staging_write_error(exc)
        upload_id = _opaque_text(initiated.get("UploadId") if isinstance(initiated, dict) else None)
        if not upload_id:
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)

        parts: list[dict[str, Any]] = []
        remaining = byte_length
        part_number = 1
        while remaining:
            part = await asyncio.to_thread(
                body.read,
                min(self._multipart_part_size, remaining),
            )
            if not part:
                return CreateImmutableResult(CreateImmutableStatus.REJECTED)
            part_checksum = base64.b64encode(hashlib.sha256(part).digest()).decode("ascii")
            try:
                uploaded = await asyncio.to_thread(
                    self._client.upload_part,
                    Bucket=self._bucket,
                    Key=object_key,
                    UploadId=upload_id,
                    PartNumber=part_number,
                    Body=part,
                    ContentLength=len(part),
                    ChecksumAlgorithm="SHA256",
                    ChecksumSHA256=part_checksum,
                )
            except Exception as exc:
                return self._classify_staging_write_error(exc)
            etag = _opaque_text(uploaded.get("ETag") if isinstance(uploaded, dict) else None)
            response_checksum = _opaque_text(
                uploaded.get("ChecksumSHA256") if isinstance(uploaded, dict) else None
            )
            if not etag or response_checksum != part_checksum:
                return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
            parts.append(
                {
                    "ETag": etag,
                    "PartNumber": part_number,
                    "ChecksumSHA256": response_checksum,
                }
            )
            remaining -= len(part)
            part_number += 1

        try:
            response = await asyncio.to_thread(
                self._client.complete_multipart_upload,
                Bucket=self._bucket,
                Key=object_key,
                UploadId=upload_id,
                MultipartUpload={"Parts": parts},
                MpuObjectSize=byte_length,
                IfNoneMatch="*",
            )
        except Exception as exc:
            return self._classify_final_write_error(exc)
        return self._created_result(response)

    @staticmethod
    def _created_result(response: Any) -> CreateImmutableResult:
        if not _successful_response(response):
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        return CreateImmutableResult(
            CreateImmutableStatus.CREATED,
            provider_request_id=_request_id(response),
            provider_object_version=_opaque_text(response.get("VersionId"), maximum=255),
        )

    @staticmethod
    def _classify_final_write_error(exc: Exception) -> CreateImmutableResult:
        if isinstance(exc, ClientError):
            status = _status_code(exc)
            code = _error_code(exc)
            if status == 412 or code == "PreconditionFailed":
                return CreateImmutableResult(CreateImmutableStatus.ALREADY_EXISTS)
            if status in {408, 409, 429} or (status is not None and status >= 500):
                return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        if isinstance(exc, ParamValidationError):
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        if isinstance(exc, NoCredentialsError):
            return CreateImmutableResult(CreateImmutableStatus.UNAVAILABLE)
        if isinstance(
            exc,
            (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError),
        ):
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        raise exc

    @staticmethod
    def _classify_staging_write_error(exc: Exception) -> CreateImmutableResult:
        if isinstance(exc, ParamValidationError):
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        if isinstance(exc, NoCredentialsError):
            return CreateImmutableResult(CreateImmutableStatus.UNAVAILABLE)
        if isinstance(exc, ClientError):
            status = _status_code(exc)
            if status is not None and status < 500 and status not in {408, 409, 429}:
                return CreateImmutableResult(CreateImmutableStatus.REJECTED)
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        if isinstance(
            exc,
            (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError),
        ):
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        raise exc

    async def observe(self, *, object_key: str) -> ObjectObservation:
        if not self._key_is_allowed(object_key):
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        try:
            response = await asyncio.to_thread(
                self._client.head_object,
                Bucket=self._bucket,
                Key=object_key,
                ChecksumMode="ENABLED",
            )
        except ClientError as exc:
            if _is_missing(exc):
                return ObjectObservation(ObjectObservationStatus.ABSENT)
            return ObjectObservation(ObjectObservationStatus.UNAVAILABLE)
        except (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError):
            return ObjectObservation(ObjectObservationStatus.UNAVAILABLE)
        if not _successful_response(response):
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        length = response.get("ContentLength")
        created_at = response.get("LastModified")
        if not isinstance(length, int) or length < 0:
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        if created_at is not None and not isinstance(created_at, datetime):
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        etag = _opaque_text(response.get("ETag"), maximum=512)
        return ObjectObservation(
            ObjectObservationStatus.PRESENT,
            byte_length=length,
            provider_object_version=_opaque_text(response.get("VersionId"), maximum=255),
            observed_etag=etag.strip('"') if etag else None,
            object_created_at=created_at,
            provider_request_id=_request_id(response),
        )

    async def verify_checksum(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification:
        if (
            not self._key_is_allowed(object_key)
            or expected_byte_length < 0
            or not _SHA256_RE.fullmatch(expected_sha256)
        ):
            return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
        streamed = await self._stream_object(object_key=object_key)
        if streamed.status != ChecksumVerificationStatus.MATCH:
            return ChecksumVerification(streamed.status)
        status = (
            ChecksumVerificationStatus.MATCH
            if streamed.sha256 == expected_sha256
            and streamed.byte_length == expected_byte_length
            else ChecksumVerificationStatus.MISMATCH
        )
        return ChecksumVerification(
            status,
            observed_sha256=streamed.sha256,
            observed_byte_length=streamed.byte_length,
        )

    async def _stream_object(self, *, object_key: str) -> _StreamedObject:
        try:
            response = await asyncio.to_thread(
                self._client.get_object,
                Bucket=self._bucket,
                Key=object_key,
                ChecksumMode="ENABLED",
            )
        except ClientError as exc:
            status = (
                ChecksumVerificationStatus.ABSENT
                if _is_missing(exc)
                else ChecksumVerificationStatus.UNAVAILABLE
            )
            return _StreamedObject(status)
        except (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError):
            return _StreamedObject(ChecksumVerificationStatus.UNAVAILABLE)
        if not _successful_response(response):
            return _StreamedObject(ChecksumVerificationStatus.UNVERIFIABLE)
        body = response.get("Body")
        try:
            digest, byte_length = await asyncio.to_thread(_read_digest, body)
        except (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError):
            return _StreamedObject(ChecksumVerificationStatus.UNAVAILABLE)
        except (TypeError, ValueError):
            return _StreamedObject(ChecksumVerificationStatus.UNVERIFIABLE)
        finally:
            close = getattr(body, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        return _StreamedObject(
            ChecksumVerificationStatus.MATCH,
            sha256=digest,
            byte_length=byte_length,
            etag=_opaque_text(response.get("ETag"), maximum=512),
            version_id=_opaque_text(response.get("VersionId"), maximum=255),
        )

    async def delete_uncommitted_or_expire(
        self,
        *,
        object_key: str,
        expected_sha256: str,
    ) -> CleanupResult:
        if not self._key_is_allowed(object_key) or not _SHA256_RE.fullmatch(expected_sha256):
            return CleanupResult(CleanupStatus.REJECTED)
        streamed = await self._stream_object(object_key=object_key)
        if streamed.status == ChecksumVerificationStatus.ABSENT:
            return CleanupResult(CleanupStatus.ABSENT)
        if streamed.status != ChecksumVerificationStatus.MATCH:
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        if streamed.sha256 != expected_sha256:
            return CleanupResult(CleanupStatus.REJECTED)
        delete_request: dict[str, Any] = {"Bucket": self._bucket, "Key": object_key}
        if streamed.etag:
            delete_request["IfMatch"] = streamed.etag
        if streamed.version_id and streamed.version_id != "null":
            delete_request["VersionId"] = streamed.version_id
        try:
            response = await asyncio.to_thread(self._client.delete_object, **delete_request)
        except ClientError as exc:
            if _is_missing(exc):
                return CleanupResult(CleanupStatus.ABSENT)
            if _status_code(exc) == 412 or _error_code(exc) == "PreconditionFailed":
                return CleanupResult(CleanupStatus.REJECTED)
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        except (BotoCoreError, ResponseParserError, TimeoutError, ConnectionError, OSError):
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        if not _successful_response(response):
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        return CleanupResult(CleanupStatus.DELETED)
