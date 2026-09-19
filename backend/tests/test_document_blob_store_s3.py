"""Deterministic request-shape and failure tests for the local AWS S3 adapter."""
from __future__ import annotations

import asyncio
import base64
import hashlib
from datetime import datetime, timezone
from types import SimpleNamespace
from typing import Any

import pytest
import boto3
from botocore.client import Config
from botocore.exceptions import (
    ClientError,
    ConnectionClosedError,
    NoCredentialsError,
    ReadTimeoutError,
)
from botocore.parsers import ResponseParserError
from botocore.stub import ANY, Stubber

from app.modules.document_workspace.domain.document_blob_store import (
    ChecksumVerificationStatus,
    CleanupStatus,
    CreateImmutableStatus,
    ObjectObservationStatus,
)
from app.modules.document_workspace.infrastructure import aws_s3_document_blob_store as s3_module
from app.modules.document_workspace.infrastructure.aws_s3_document_blob_store import (
    AwsS3DocumentBlobStore,
)


MIB = 1024 * 1024
BUCKET = "valora-local-test"
PREFIX = "valora-spike/unit-run"
KEY = f"{PREFIX}/document.docx"
KMS_KEY_ARN = "arn:aws:kms:us-east-1:111122223333:key/12345678-1234-1234-1234-123456789012"


def _response(*, request_id: str = "request-1", **values: Any) -> dict[str, Any]:
    return {
        **values,
        "ResponseMetadata": {"HTTPStatusCode": 200, "RequestId": request_id},
    }


def _client_error(status: int, code: str, operation: str) -> ClientError:
    return ClientError(
        {
            "Error": {"Code": code, "Message": "synthetic test response"},
            "ResponseMetadata": {"HTTPStatusCode": status, "RequestId": "request-error"},
        },
        operation,
    )


class _Body:
    def __init__(self, data: bytes, *, fail_on_read: bool = False) -> None:
        self._data = data
        self._offset = 0
        self._fail_on_read = fail_on_read
        self.closed = False

    def read(self, amount: int) -> bytes:
        if self._fail_on_read:
            raise ReadTimeoutError(endpoint_url="https://unit.invalid", error="lost response")
        result = self._data[self._offset : self._offset + amount]
        self._offset += len(result)
        return result

    def close(self) -> None:
        self.closed = True


class _RecordingS3Client:
    """SDK-dispatch boundary fake; every method call is one captured request attempt."""

    def __init__(self) -> None:
        self.calls: list[tuple[str, dict[str, Any]]] = []
        self.objects: dict[str, bytes] = {}
        self.put_error: Exception | None = None
        self.create_multipart_error: Exception | None = None
        self.complete_error: Exception | None = None
        self.read_fails = False

    def _record(self, operation: str, request: dict[str, Any]) -> None:
        self.calls.append((operation, request))

    def calls_for(self, operation: str) -> list[dict[str, Any]]:
        return [request for name, request in self.calls if name == operation]

    def put_object(self, **request: Any) -> dict[str, Any]:
        body = request.pop("Body")
        body_bytes = body.read()
        captured = {**request, "BodyBytes": body_bytes}
        self._record("PutObject", captured)
        if self.put_error is not None:
            raise self.put_error
        self.objects[request["Key"]] = body_bytes
        return _response(ETag='"opaque-etag"', VersionId="version-1")

    def create_multipart_upload(self, **request: Any) -> dict[str, Any]:
        self._record("CreateMultipartUpload", request)
        if self.create_multipart_error is not None:
            raise self.create_multipart_error
        return _response(UploadId="upload-1")

    def upload_part(self, **request: Any) -> dict[str, Any]:
        body = request.pop("Body")
        captured = {**request, "BodyBytes": body}
        self._record("UploadPart", captured)
        return _response(
            ETag=f'"part-{request["PartNumber"]}"',
            ChecksumSHA256=request["ChecksumSHA256"],
        )

    def complete_multipart_upload(self, **request: Any) -> dict[str, Any]:
        self._record("CompleteMultipartUpload", request)
        if self.complete_error is not None:
            raise self.complete_error
        return _response(ETag='"opaque-multipart-etag"', VersionId="version-2")

    def head_object(self, **request: Any) -> dict[str, Any]:
        self._record("HeadObject", request)
        data = self.objects.get(request["Key"])
        if data is None:
            raise _client_error(404, "NoSuchKey", "HeadObject")
        return _response(
            ContentLength=len(data),
            ETag='"not-a-sha256"',
            VersionId="version-1",
            LastModified=datetime(2026, 9, 19, tzinfo=timezone.utc),
        )

    def get_object(self, **request: Any) -> dict[str, Any]:
        self._record("GetObject", request)
        data = self.objects.get(request["Key"])
        if data is None:
            raise _client_error(404, "NoSuchKey", "GetObject")
        return _response(
            Body=_Body(data, fail_on_read=self.read_fails),
            ETag='"not-a-sha256"',
            VersionId="version-1",
        )

    def delete_object(self, **request: Any) -> dict[str, Any]:
        self._record("DeleteObject", request)
        self.objects.pop(request["Key"], None)
        return _response()


async def _content(data: bytes, *, split_at: int | None = None):
    if split_at is None:
        yield data
        return
    yield data[:split_at]
    yield data[split_at:]


def _store(client: _RecordingS3Client, **kwargs: Any) -> AwsS3DocumentBlobStore:
    return AwsS3DocumentBlobStore(
        bucket=BUCKET,
        key_prefix=PREFIX,
        region_name="us-east-1",
        kms_key_arn=KMS_KEY_ARN,
        client=client,
        **kwargs,
    )


def _stubbed_botocore_client():
    return boto3.client(
        "s3",
        endpoint_url="https://unit.invalid",
        region_name="us-east-1",
        aws_access_key_id="synthetic-unit-test",
        aws_secret_access_key="synthetic-unit-test",
        config=Config(signature_version="s3v4", retries={"total_max_attempts": 1}),
    )


def _create(
    store: AwsS3DocumentBlobStore,
    data: bytes,
    *,
    object_key: str = KEY,
):
    return asyncio.run(
        store.create_immutable(
            object_key=object_key,
            content=_content(data, split_at=max(1, len(data) // 2)),
            byte_length=len(data),
            expected_sha256=hashlib.sha256(data).hexdigest(),
        )
    )


def test_client_configuration_disables_all_sdk_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: dict[str, Any] = {}
    sentinel = SimpleNamespace()

    def fake_client(service: str, **kwargs: Any) -> Any:
        captured.update({"service": service, **kwargs})
        return sentinel

    monkeypatch.setattr(s3_module.boto3, "client", fake_client)
    store = AwsS3DocumentBlobStore(
        bucket=BUCKET,
        key_prefix=PREFIX,
        region_name="us-east-1",
        kms_key_arn=KMS_KEY_ARN,
    )
    assert store._client is sentinel
    assert captured["service"] == "s3"
    assert captured["config"].retries == {"total_max_attempts": 1}


def test_single_part_dispatches_one_conditional_put_with_full_sha256() -> None:
    client = _RecordingS3Client()
    data = b"PK\x03\x04 deterministic single-part document"
    result = _create(_store(client), data)
    assert result.status == CreateImmutableStatus.CREATED
    assert result.provider_request_id == "request-1"
    puts = client.calls_for("PutObject")
    assert len(puts) == 1
    assert client.calls_for("HeadObject") == []
    assert puts[0]["IfNoneMatch"] == "*"
    assert puts[0]["ChecksumAlgorithm"] == "SHA256"
    assert puts[0]["ChecksumSHA256"] == base64.b64encode(hashlib.sha256(data).digest()).decode()
    assert puts[0]["ContentLength"] == len(data)
    assert puts[0]["ServerSideEncryption"] == "aws:kms"
    assert puts[0]["SSEKMSKeyId"] == KMS_KEY_ARN
    assert puts[0]["BodyBytes"] == data


def test_botocore_stubber_accepts_exact_single_part_request_shape() -> None:
    data = b"botocore model validation"
    digest = hashlib.sha256(data).digest()
    client = _stubbed_botocore_client()
    with Stubber(client) as stubber:
        stubber.add_response(
            "put_object",
            _response(ETag='"opaque"', VersionId="version-1"),
            {
                "Bucket": BUCKET,
                "Key": KEY,
                "Body": ANY,
                "ContentLength": len(data),
                "ChecksumAlgorithm": "SHA256",
                "ChecksumSHA256": base64.b64encode(digest).decode(),
                "IfNoneMatch": "*",
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": KMS_KEY_ARN,
            },
        )
        result = _create(_store(client), data)
        stubber.assert_no_pending_responses()
    assert result.status == CreateImmutableStatus.CREATED


def test_multipart_dispatches_one_conditional_final_commit_and_consecutive_parts() -> None:
    client = _RecordingS3Client()
    data = b"a" * (5 * MIB) + b"tail"
    store = _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB)
    result = _create(store, data)
    assert result.status == CreateImmutableStatus.CREATED
    assert len(client.calls_for("CreateMultipartUpload")) == 1
    uploads = client.calls_for("UploadPart")
    assert [part["PartNumber"] for part in uploads] == [1, 2]
    assert [part["ContentLength"] for part in uploads] == [5 * MIB, 4]
    completes = client.calls_for("CompleteMultipartUpload")
    assert len(completes) == 1
    assert completes[0]["IfNoneMatch"] == "*"
    assert completes[0]["MpuObjectSize"] == len(data)
    assert [part["PartNumber"] for part in completes[0]["MultipartUpload"]["Parts"]] == [1, 2]


def test_botocore_stubber_accepts_conditional_multipart_completion_shape() -> None:
    first = b"a" * (5 * MIB)
    second = b"tail"
    data = first + second
    checksums = [base64.b64encode(hashlib.sha256(part).digest()).decode() for part in (first, second)]
    completed_parts = [
        {"ETag": f'"part-{number}"', "PartNumber": number, "ChecksumSHA256": checksum}
        for number, checksum in enumerate(checksums, start=1)
    ]
    client = _stubbed_botocore_client()
    with Stubber(client) as stubber:
        stubber.add_response(
            "create_multipart_upload",
            _response(UploadId="upload-1"),
            {
                "Bucket": BUCKET,
                "Key": KEY,
                "ChecksumAlgorithm": "SHA256",
                "ChecksumType": "COMPOSITE",
                "ServerSideEncryption": "aws:kms",
                "SSEKMSKeyId": KMS_KEY_ARN,
            },
        )
        for part_number, (part, checksum) in enumerate(zip((first, second), checksums), start=1):
            stubber.add_response(
                "upload_part",
                _response(ETag=f'"part-{part_number}"', ChecksumSHA256=checksum),
                {
                    "Bucket": BUCKET,
                    "Key": KEY,
                    "UploadId": "upload-1",
                    "PartNumber": part_number,
                    "Body": part,
                    "ContentLength": len(part),
                    "ChecksumAlgorithm": "SHA256",
                    "ChecksumSHA256": checksum,
                },
            )
        stubber.add_response(
            "complete_multipart_upload",
            _response(ETag='"opaque"', VersionId="version-2"),
            {
                "Bucket": BUCKET,
                "Key": KEY,
                "UploadId": "upload-1",
                "MultipartUpload": {"Parts": completed_parts},
                "MpuObjectSize": len(data),
                "IfNoneMatch": "*",
            },
        )
        result = _create(
            _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB),
            data,
        )
        stubber.assert_no_pending_responses()
    assert result.status == CreateImmutableStatus.CREATED


@pytest.mark.parametrize(
    ("error", "expected"),
    [
        (_client_error(412, "PreconditionFailed", "PutObject"), CreateImmutableStatus.ALREADY_EXISTS),
        (
            _client_error(409, "ConditionalRequestConflict", "PutObject"),
            CreateImmutableStatus.OUTCOME_UNKNOWN,
        ),
        (
            ReadTimeoutError(endpoint_url="https://unit.invalid", error="lost response"),
            CreateImmutableStatus.OUTCOME_UNKNOWN,
        ),
        (
            ConnectionClosedError(endpoint_url="https://unit.invalid"),
            CreateImmutableStatus.OUTCOME_UNKNOWN,
        ),
        (ResponseParserError("unreadable response"), CreateImmutableStatus.OUTCOME_UNKNOWN),
    ],
)
def test_single_part_failure_mapping_never_dispatches_a_second_put(
    error: Exception,
    expected: CreateImmutableStatus,
) -> None:
    client = _RecordingS3Client()
    client.put_error = error
    result = _create(_store(client), b"single write with ambiguous response")
    assert result.status == expected
    assert len(client.calls_for("PutObject")) == 1


def test_lost_multipart_completion_response_never_dispatches_a_second_commit() -> None:
    client = _RecordingS3Client()
    client.complete_error = ReadTimeoutError(
        endpoint_url="https://unit.invalid",
        error="lost completion response",
    )
    data = b"m" * (5 * MIB) + b"tail"
    result = _create(
        _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB),
        data,
    )
    assert result.status == CreateImmutableStatus.OUTCOME_UNKNOWN
    assert len(client.calls_for("CompleteMultipartUpload")) == 1


def test_multipart_precondition_failure_maps_to_existing_without_second_commit() -> None:
    client = _RecordingS3Client()
    client.complete_error = _client_error(412, "PreconditionFailed", "CompleteMultipartUpload")
    data = b"m" * (5 * MIB) + b"tail"
    result = _create(
        _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB),
        data,
    )
    assert result.status == CreateImmutableStatus.ALREADY_EXISTS
    assert len(client.calls_for("CompleteMultipartUpload")) == 1


def test_invalid_content_is_rejected_before_any_provider_write() -> None:
    client = _RecordingS3Client()
    data = b"candidate"

    async def run():
        return await _store(client).create_immutable(
            object_key=KEY,
            content=_content(data),
            byte_length=len(data) + 1,
            expected_sha256=hashlib.sha256(data).hexdigest(),
        )

    result = asyncio.run(run())
    assert result.status == CreateImmutableStatus.REJECTED
    assert client.calls == []


def test_more_than_ten_thousand_parts_is_rejected_before_content_or_provider_io() -> None:
    client = _RecordingS3Client()
    store = _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB)

    async def should_not_iterate():
        raise AssertionError("content must not be consumed for an invalid multipart shape")
        yield b""

    result = asyncio.run(
        store.create_immutable(
            object_key=KEY,
            content=should_not_iterate(),
            byte_length=5 * MIB * 10_000 + 1,
            expected_sha256="a" * 64,
        )
    )
    assert result.status == CreateImmutableStatus.REJECTED
    assert client.calls == []


def test_missing_credentials_before_multipart_staging_is_recoverable_unavailable() -> None:
    client = _RecordingS3Client()
    client.create_multipart_error = NoCredentialsError()
    data = b"m" * (5 * MIB) + b"tail"
    result = _create(
        _store(client, multipart_threshold=5 * MIB, multipart_part_size=5 * MIB),
        data,
    )
    assert result.status == CreateImmutableStatus.UNAVAILABLE
    assert len(client.calls_for("CreateMultipartUpload")) == 1
    assert client.calls_for("UploadPart") == []


def test_observe_records_only_sanitized_identity_metadata_and_treats_etag_as_opaque() -> None:
    client = _RecordingS3Client()
    data = b"observed bytes"
    client.objects[KEY] = data
    observation = asyncio.run(_store(client).observe(object_key=KEY))
    assert observation.status == ObjectObservationStatus.PRESENT
    assert observation.byte_length == len(data)
    assert observation.observed_etag == "not-a-sha256"
    assert observation.provider_object_version == "version-1"
    assert observation.provider_request_id == "request-1"
    assert client.calls_for("HeadObject")[0]["ChecksumMode"] == "ENABLED"


def test_observe_missing_key_is_absent_without_a_write() -> None:
    client = _RecordingS3Client()
    observation = asyncio.run(_store(client).observe(object_key=KEY))
    assert observation.status == ObjectObservationStatus.ABSENT
    assert len(client.calls_for("HeadObject")) == 1
    assert client.calls_for("PutObject") == []


def test_verify_checksum_streams_full_bytes_and_exact_length() -> None:
    client = _RecordingS3Client()
    data = b"z" * (3 * 64 * 1024 + 17)
    client.objects[KEY] = data
    verification = asyncio.run(
        _store(client).verify_checksum(
            object_key=KEY,
            expected_sha256=hashlib.sha256(data).hexdigest(),
            expected_byte_length=len(data),
        )
    )
    assert verification.status == ChecksumVerificationStatus.MATCH
    assert verification.observed_sha256 == hashlib.sha256(data).hexdigest()
    assert verification.observed_byte_length == len(data)
    assert len(client.calls_for("GetObject")) == 1
    assert client.calls_for("GetObject")[0]["ChecksumMode"] == "ENABLED"


def test_verify_mismatch_does_not_treat_etag_as_sha256() -> None:
    client = _RecordingS3Client()
    client.objects[KEY] = b"provider bytes"
    verification = asyncio.run(
        _store(client).verify_checksum(
            object_key=KEY,
            expected_sha256=hashlib.sha256(b"other bytes").hexdigest(),
            expected_byte_length=len(b"other bytes"),
        )
    )
    assert verification.status == ChecksumVerificationStatus.MISMATCH
    assert client.calls_for("PutObject") == []


def test_temporary_stream_read_failure_is_unavailable_without_any_write() -> None:
    client = _RecordingS3Client()
    client.objects[KEY] = b"provider bytes"
    client.read_fails = True
    verification = asyncio.run(
        _store(client).verify_checksum(
            object_key=KEY,
            expected_sha256=hashlib.sha256(b"provider bytes").hexdigest(),
            expected_byte_length=len(b"provider bytes"),
        )
    )
    assert verification.status == ChecksumVerificationStatus.UNAVAILABLE
    assert len(client.calls_for("GetObject")) == 1
    assert client.calls_for("PutObject") == []
    assert client.calls_for("CompleteMultipartUpload") == []


def test_cleanup_rejects_out_of_prefix_without_read_or_delete() -> None:
    client = _RecordingS3Client()
    result = asyncio.run(
        _store(client).delete_uncommitted_or_expire(
            object_key="another-run/document.docx",
            expected_sha256="a" * 64,
        )
    )
    assert result.status == CleanupStatus.REJECTED
    assert client.calls == []


def test_cleanup_rejects_checksum_mismatch_without_delete() -> None:
    client = _RecordingS3Client()
    client.objects[KEY] = b"different bytes"
    result = asyncio.run(
        _store(client).delete_uncommitted_or_expire(
            object_key=KEY,
            expected_sha256=hashlib.sha256(b"expected bytes").hexdigest(),
        )
    )
    assert result.status == CleanupStatus.REJECTED
    assert len(client.calls_for("GetObject")) == 1
    assert client.calls_for("DeleteObject") == []


def test_cleanup_deletes_only_the_verified_key_version_with_etag_guard() -> None:
    client = _RecordingS3Client()
    data = b"eligible unbound candidate"
    client.objects[KEY] = data
    result = asyncio.run(
        _store(client).delete_uncommitted_or_expire(
            object_key=KEY,
            expected_sha256=hashlib.sha256(data).hexdigest(),
        )
    )
    assert result.status == CleanupStatus.DELETED
    deletes = client.calls_for("DeleteObject")
    assert len(deletes) == 1
    assert deletes[0] == {
        "Bucket": BUCKET,
        "Key": KEY,
        "IfMatch": '"not-a-sha256"',
        "VersionId": "version-1",
    }
