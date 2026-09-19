"""One-shot live AWS S3 conformance harness for VALORA-STORAGE-S3-SPIKE-001.

The default mode performs no network call. Live execution requires an approved private manifest,
explicit temporary session credentials, an external evidence directory, and ``--execute-live``.
"""
from __future__ import annotations

import argparse
import asyncio
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import threading
import time
from collections.abc import AsyncIterator, Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

import boto3
import botocore
from botocore.client import Config
from botocore.exceptions import ClientError, ReadTimeoutError

from app.modules.document_workspace.domain.document_blob_store import (
    ChecksumVerificationStatus,
    CleanupStatus,
    CreateImmutableStatus,
    ObjectObservationStatus,
)
from app.modules.document_workspace.infrastructure.aws_s3_document_blob_store import (
    AwsS3DocumentBlobStore,
)


SCHEMA_VERSION = "valora-s3-g5-manifest-v1"
RUN_ID = "s3-g5-20260919-001"
ACCOUNT_REF = "VALORA-NONPROD-AWS-STORAGE-SPIKE-01"
REGION = "ap-southeast-1"
BUCKET = "valora-storage-spike-2c2a9f17-20260919-001"
PREFIX = f"valora-spike/{RUN_ID}/"
MULTIPART_PART_SIZE = 8 * 1024 * 1024
MULTIPART_FIXTURE_SIZE = MULTIPART_PART_SIZE + 4096
SMALL_FIXTURE_SIZE = 4096
RUNTIME_PYTHON = (3, 14, 7)
RUNTIME_BOTO3 = "1.43.89"
RUNTIME_BOTOCORE = "1.43.89"
MAX_S3_REQUESTS = 96
MAX_UPLOAD_BYTES = 48 * 1024 * 1024
MAX_GET_BYTES = 24 * 1024 * 1024
MAX_COMMITTED_OBJECTS = 6
MAX_MULTIPART_UPLOADS = 5
MAX_PARTS = 9
MAX_DELETE_REQUESTS = 12
MAX_LIST_REQUESTS = 16
MAX_DURATION_SECONDS = 20 * 60
HARD_COST_USD = "0.10"
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_COMMIT_RE = re.compile(r"^[0-9a-f]{40}$")
_ACCOUNT_RE = re.compile(r"^\d{12}$")
_SAFE_REF_RE = re.compile(r"^[A-Za-z0-9._:/=-]{1,255}$")
_KMS_ARN_RE = re.compile(
    r"^arn:aws:kms:ap-southeast-1:(\d{12}):key/[A-Za-z0-9-]+$"
)
_ASSUMED_ROLE_ARN_RE = re.compile(
    r"^arn:aws:sts::(\d{12}):assumed-role/[A-Za-z0-9+=,.@_-]+/[A-Za-z0-9+=,.@_-]+$"
)
_FINAL_OPERATIONS = {"PutObject", "CompleteMultipartUpload"}
_FIXTURE_LAYOUT = {
    "FIXTURE_A": SMALL_FIXTURE_SIZE,
    "FIXTURE_B": SMALL_FIXTURE_SIZE,
    "FIXTURE_M": MULTIPART_FIXTURE_SIZE,
}
_OBJECT_NAMES = (
    "small-primary.bin",
    "multipart-primary.bin",
    "multipart-race.bin",
    "lost-put.bin",
    "lost-complete.bin",
    "unbound.bin",
    "policy-put-denied.bin",
    "policy-complete-denied.bin",
    "incomplete.bin",
)


class HarnessFailure(RuntimeError):
    """Fail-closed live harness error with no automatic rerun."""


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")


def _canonical_json(value: Any) -> bytes:
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_json(value: Any) -> str:
    return _sha256_bytes(_canonical_json(value))


def _fixture_bytes(fixture_id: str, byte_length: int) -> bytes:
    if fixture_id not in _FIXTURE_LAYOUT or _FIXTURE_LAYOUT[fixture_id] != byte_length:
        raise HarnessFailure("Fixture identity or byte length is outside the frozen layout.")
    result = bytearray()
    block_number = 0
    while len(result) < byte_length:
        seed = f"VALORA-S3-G5-V1:{fixture_id}:{block_number:08d}".encode("ascii")
        result.extend(hashlib.sha256(seed).digest())
        block_number += 1
    return bytes(result[:byte_length])


def fixture_manifest() -> dict[str, dict[str, Any]]:
    return {
        fixture_id: {
            "fixture_id": fixture_id,
            "generator": "sha256-counter-v1",
            "byte_length": byte_length,
            "sha256": _sha256_bytes(_fixture_bytes(fixture_id, byte_length)),
            "expected_parts": (
                (byte_length + MULTIPART_PART_SIZE - 1) // MULTIPART_PART_SIZE
                if fixture_id == "FIXTURE_M"
                else 1
            ),
        }
        for fixture_id, byte_length in _FIXTURE_LAYOUT.items()
    }


@dataclass(frozen=True)
class RuntimeManifest:
    approved_executable_commit: str
    approved_review_manifest_sha256: str
    approval_reference: str
    expected_account_id: str
    expected_principal_arn: str
    kms_key_arn: str
    bucket_policy_sha256: str
    iam_policy_sha256: str
    lifecycle_configuration_sha256: str
    action_time_checklist_sha256: str
    cleanup_owner: str
    fixtures: dict[str, dict[str, Any]]

    @classmethod
    def load(cls, path: Path) -> "RuntimeManifest":
        try:
            raw = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise HarnessFailure("The private runtime manifest is unreadable.") from exc
        expected_keys = {
            "schema_version",
            "run_id",
            "account_ref",
            "region",
            "bucket",
            "prefix",
            "approved_executable_commit",
            "approved_review_manifest_sha256",
            "approval_reference",
            "expected_account_id",
            "expected_principal_arn",
            "kms_key_arn",
            "bucket_policy_sha256",
            "iam_policy_sha256",
            "lifecycle_configuration_sha256",
            "action_time_checklist_sha256",
            "cleanup_owner",
            "runtime",
            "retry",
            "fixtures",
            "limits",
        }
        if not isinstance(raw, dict) or set(raw) != expected_keys:
            raise HarnessFailure("The private runtime manifest schema is not exact.")
        fixed_values = {
            "schema_version": SCHEMA_VERSION,
            "run_id": RUN_ID,
            "account_ref": ACCOUNT_REF,
            "region": REGION,
            "bucket": BUCKET,
            "prefix": PREFIX,
            "runtime": {
                "python": "3.14.7",
                "boto3": RUNTIME_BOTO3,
                "botocore": RUNTIME_BOTOCORE,
            },
            "retry": {"signature_version": "s3v4", "total_max_attempts": 1},
            "fixtures": fixture_manifest(),
            "limits": frozen_limits(),
        }
        for key, value in fixed_values.items():
            if raw.get(key) != value:
                raise HarnessFailure(f"Manifest field {key} differs from the frozen G4 value.")
        account_id = raw["expected_account_id"]
        principal_arn = raw["expected_principal_arn"]
        kms_key_arn = raw["kms_key_arn"]
        if not isinstance(account_id, str) or not _ACCOUNT_RE.fullmatch(account_id):
            raise HarnessFailure("Expected account ID must be the approved private 12-digit value.")
        role_match = _ASSUMED_ROLE_ARN_RE.fullmatch(str(principal_arn))
        kms_match = _KMS_ARN_RE.fullmatch(str(kms_key_arn))
        if not role_match or role_match.group(1) != account_id:
            raise HarnessFailure(
                "Expected principal is not the approved assumed-role session in the frozen account."
            )
        if not kms_match or kms_match.group(1) != account_id:
            raise HarnessFailure("KMS key is not a customer-managed key in the frozen account/region.")
        commit = raw["approved_executable_commit"]
        hashes = (
            raw["approved_review_manifest_sha256"],
            raw["bucket_policy_sha256"],
            raw["iam_policy_sha256"],
            raw["lifecycle_configuration_sha256"],
            raw["action_time_checklist_sha256"],
        )
        if not isinstance(commit, str) or not _COMMIT_RE.fullmatch(commit):
            raise HarnessFailure("Approved executable commit is missing or invalid.")
        if any(not isinstance(value, str) or not _SHA256_RE.fullmatch(value) for value in hashes):
            raise HarnessFailure("An approved evidence hash is missing or invalid.")
        approval_reference = raw["approval_reference"]
        cleanup_owner = raw["cleanup_owner"]
        placeholder_tokens = ("REPLACE", "PENDING", "UNSET", "TBD")
        if (
            not isinstance(approval_reference, str)
            or not _SAFE_REF_RE.fullmatch(approval_reference)
            or any(token in approval_reference.upper() for token in placeholder_tokens)
        ):
            raise HarnessFailure("Approval reference is not repository-safe metadata.")
        if (
            not isinstance(cleanup_owner, str)
            or not _SAFE_REF_RE.fullmatch(cleanup_owner)
            or any(token in cleanup_owner.upper() for token in placeholder_tokens)
        ):
            raise HarnessFailure("Cleanup owner is not repository-safe metadata.")
        return cls(
            approved_executable_commit=commit,
            approved_review_manifest_sha256=hashes[0],
            approval_reference=approval_reference,
            expected_account_id=account_id,
            expected_principal_arn=principal_arn,
            kms_key_arn=kms_key_arn,
            bucket_policy_sha256=hashes[1],
            iam_policy_sha256=hashes[2],
            lifecycle_configuration_sha256=hashes[3],
            action_time_checklist_sha256=hashes[4],
            cleanup_owner=cleanup_owner,
            fixtures=raw["fixtures"],
        )


def frozen_limits() -> dict[str, Any]:
    return {
        "one_invocation": True,
        "max_s3_requests": MAX_S3_REQUESTS,
        "max_uploaded_bytes": MAX_UPLOAD_BYTES,
        "max_get_bytes": MAX_GET_BYTES,
        "max_committed_objects": MAX_COMMITTED_OBJECTS,
        "max_multipart_uploads": MAX_MULTIPART_UPLOADS,
        "max_parts": MAX_PARTS,
        "max_delete_requests": MAX_DELETE_REQUESTS,
        "max_list_requests": MAX_LIST_REQUESTS,
        "max_duration_seconds": MAX_DURATION_SECONDS,
        "modeled_hard_cost_usd": HARD_COST_USD,
    }


class EvidenceJournal:
    """Append-only sanitized JSONL with an exclusive one-run creation boundary."""

    def __init__(self, evidence_dir: Path, *, repository_root: Path) -> None:
        resolved = evidence_dir.resolve()
        repo = repository_root.resolve()
        if resolved == repo or repo in resolved.parents:
            raise HarnessFailure("Evidence directory must be outside the repository.")
        resolved.mkdir(parents=True, exist_ok=True)
        self.path = resolved / f"{RUN_ID}.events.jsonl"
        try:
            descriptor = os.open(self.path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        except FileExistsError as exc:
            raise HarnessFailure("Run evidence already exists; a second invocation is forbidden.") from exc
        self._stream = os.fdopen(descriptor, "w", encoding="utf-8", newline="\n")
        self._sequence = 0
        self._lock = threading.Lock()

    def record(self, event: str, **fields: Any) -> None:
        forbidden = {"authorization", "signature", "access_key", "secret", "session_token", "body"}
        if any(any(token in key.lower() for token in forbidden) for key in fields):
            raise HarnessFailure("Evidence attempted to record a forbidden field.")
        with self._lock:
            self._sequence += 1
            payload = {"sequence": self._sequence, "timestamp": _utc_now(), "event": event, **fields}
            self._stream.write(json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n")
            self._stream.flush()
            os.fsync(self._stream.fileno())

    def close(self) -> None:
        self._stream.close()


class MeteredS3Client:
    """Count and cap every S3 operation without logging request headers or payload bytes."""

    def __init__(self, client: Any, journal: EvidenceJournal) -> None:
        self._client = client
        self._journal = journal
        self.requests = 0
        self.uploaded_bytes = 0
        self.get_bytes = 0
        self.multipart_uploads = 0
        self.parts = 0
        self.deletes = 0
        self.lists = 0
        self.operation_counts: dict[str, int] = {}
        self._started_at = time.monotonic()

    def __getattr__(self, name: str) -> Any:
        target = getattr(self._client, name)
        if not callable(target) or name.startswith("_"):
            return target

        def call(**kwargs: Any) -> Any:
            if time.monotonic() - self._started_at > MAX_DURATION_SECONDS:
                raise HarnessFailure("One-invocation duration ceiling exceeded.")
            operation = "".join(part.capitalize() for part in name.split("_"))
            self.requests += 1
            self.operation_counts[operation] = self.operation_counts.get(operation, 0) + 1
            if self.requests > MAX_S3_REQUESTS:
                raise HarnessFailure("S3 request ceiling exceeded.")
            content_length = kwargs.get("ContentLength", 0)
            if name in {"put_object", "upload_part"}:
                if not isinstance(content_length, int) or content_length < 0:
                    raise HarnessFailure("A write omitted its bounded content length.")
                self.uploaded_bytes += content_length
                if self.uploaded_bytes > MAX_UPLOAD_BYTES:
                    raise HarnessFailure("Upload byte ceiling exceeded.")
            if name == "create_multipart_upload":
                self.multipart_uploads += 1
                if self.multipart_uploads > MAX_MULTIPART_UPLOADS:
                    raise HarnessFailure("Multipart upload ceiling exceeded.")
            if name == "upload_part":
                self.parts += 1
                if self.parts > MAX_PARTS:
                    raise HarnessFailure("Multipart part ceiling exceeded.")
            if name in {"delete_object", "abort_multipart_upload"}:
                self.deletes += 1
                if self.deletes > MAX_DELETE_REQUESTS:
                    raise HarnessFailure("Delete/abort request ceiling exceeded.")
            if name in {"list_objects_v2", "list_multipart_uploads", "list_parts"}:
                self.lists += 1
                if self.lists > MAX_LIST_REQUESTS:
                    raise HarnessFailure("LIST request ceiling exceeded.")
            key = kwargs.get("Key")
            key_ref = _relative_key(key) if isinstance(key, str) else None
            self._journal.record(
                "S3_REQUEST_DISPATCH",
                operation=operation,
                operation_sequence=self.operation_counts[operation],
                key_ref=key_ref,
                byte_length=content_length if isinstance(content_length, int) else None,
            )
            response = target(**kwargs)
            if name == "get_object":
                observed = response.get("ContentLength") if isinstance(response, dict) else None
                if not isinstance(observed, int) or observed < 0:
                    raise HarnessFailure("GET response omitted a bounded content length.")
                self.get_bytes += observed
                if self.get_bytes > MAX_GET_BYTES:
                    raise HarnessFailure("GET byte ceiling exceeded.")
            return response

        return call


class _DropOneResponseSession:
    def __init__(self, delegate: Any, operation: str, journal: EvidenceJournal) -> None:
        self._delegate = delegate
        self._operation = operation
        self._journal = journal
        self._pending = False
        self.dispatch_count = 0
        self.response_received = False

    def before_send(self, request: Any, **_: Any) -> None:
        if self.dispatch_count:
            raise HarnessFailure(f"A second {self._operation} dispatch was blocked.")
        self._pending = True

    def send(self, request: Any) -> Any:
        if not self._pending:
            return self._delegate.send(request)
        self._pending = False
        self.dispatch_count += 1
        self._journal.record(
            "FAULT_FINAL_WRITE_DISPATCH",
            operation=self._operation,
            dispatch_count=self.dispatch_count,
        )
        response = self._delegate.send(request)
        self.response_received = True
        request_id = None
        headers = getattr(response, "headers", None)
        if headers is not None:
            candidate = headers.get("x-amz-request-id")
            if isinstance(candidate, str) and _SAFE_REF_RE.fullmatch(candidate):
                request_id = candidate
        self._journal.record(
            "FAULT_RESPONSE_SUPPRESSED_AFTER_DISPATCH",
            operation=self._operation,
            dispatch_count=self.dispatch_count,
            safe_request_id=request_id,
            http_status=getattr(response, "status_code", None),
        )
        raw = getattr(response, "raw", None)
        close = getattr(raw, "close", None)
        if callable(close):
            close()
        raise ReadTimeoutError(endpoint_url=str(getattr(request, "url", "https://s3.invalid")), error="injected post-dispatch response loss")


@contextmanager
def _lose_exactly_one_response(
    client: Any,
    operation: str,
    journal: EvidenceJournal,
) -> Iterator[_DropOneResponseSession]:
    if operation not in _FINAL_OPERATIONS:
        raise HarnessFailure("Only a final object-creation response may be suppressed.")
    endpoint = getattr(client, "_endpoint", None)
    original = getattr(endpoint, "http_session", None)
    events = getattr(getattr(client, "meta", None), "events", None)
    if endpoint is None or original is None or events is None:
        raise HarnessFailure("Frozen botocore transport boundary is unavailable.")
    wrapper = _DropOneResponseSession(original, operation, journal)
    event_name = f"before-send.s3.{operation}"
    unique_id = f"valora-{RUN_ID}-{operation}"
    events.register_first(event_name, wrapper.before_send, unique_id=unique_id)
    endpoint.http_session = wrapper
    try:
        yield wrapper
    finally:
        endpoint.http_session = original
        events.unregister(event_name, unique_id=unique_id)
    if wrapper.dispatch_count != 1 or not wrapper.response_received:
        raise HarnessFailure(f"Lost-response proof for {operation} did not observe one completed dispatch.")


def _relative_key(key: str) -> str:
    if not key.startswith(PREFIX) or len(key) <= len(PREFIX):
        raise HarnessFailure("S3 operation escaped the frozen run prefix.")
    return key[len(PREFIX) :]


async def _content(data: bytes) -> AsyncIterator[bytes]:
    yield data


def _client_error_status(exc: ClientError) -> int | None:
    value = (exc.response.get("ResponseMetadata") or {}).get("HTTPStatusCode")
    return value if isinstance(value, int) else None


def _checksum_b64(data: bytes) -> str:
    return base64.b64encode(hashlib.sha256(data).digest()).decode("ascii")


def _sse_request(manifest: RuntimeManifest) -> dict[str, str]:
    return {"ServerSideEncryption": "aws:kms", "SSEKMSKeyId": manifest.kms_key_arn}


def _conditional_put(client: Any, manifest: RuntimeManifest, key: str, data: bytes) -> dict[str, Any]:
    return client.put_object(
        Bucket=BUCKET,
        Key=key,
        Body=data,
        ContentLength=len(data),
        ChecksumAlgorithm="SHA256",
        ChecksumSHA256=_checksum_b64(data),
        IfNoneMatch="*",
        **_sse_request(manifest),
    )


def _start_multipart(client: Any, manifest: RuntimeManifest, key: str) -> str:
    response = client.create_multipart_upload(
        Bucket=BUCKET,
        Key=key,
        ChecksumAlgorithm="SHA256",
        ChecksumType="COMPOSITE",
        **_sse_request(manifest),
    )
    upload_id = response.get("UploadId") if isinstance(response, dict) else None
    if not isinstance(upload_id, str) or not upload_id:
        raise HarnessFailure("Multipart initiation returned no upload ID.")
    return upload_id


def _upload_parts(client: Any, key: str, upload_id: str, data: bytes) -> list[dict[str, Any]]:
    parts: list[dict[str, Any]] = []
    for part_number, offset in enumerate(range(0, len(data), MULTIPART_PART_SIZE), start=1):
        part = data[offset : offset + MULTIPART_PART_SIZE]
        checksum = _checksum_b64(part)
        response = client.upload_part(
            Bucket=BUCKET,
            Key=key,
            UploadId=upload_id,
            PartNumber=part_number,
            Body=part,
            ContentLength=len(part),
            ChecksumAlgorithm="SHA256",
            ChecksumSHA256=checksum,
        )
        etag = response.get("ETag") if isinstance(response, dict) else None
        observed_checksum = response.get("ChecksumSHA256") if isinstance(response, dict) else None
        if not isinstance(etag, str) or observed_checksum != checksum:
            raise HarnessFailure("Multipart part response did not match the dispatched part.")
        parts.append({"ETag": etag, "PartNumber": part_number, "ChecksumSHA256": checksum})
    return parts


def _complete_multipart(
    client: Any,
    key: str,
    upload_id: str,
    parts: list[dict[str, Any]],
    byte_length: int,
    *,
    conditional: bool,
) -> dict[str, Any]:
    request: dict[str, Any] = {
        "Bucket": BUCKET,
        "Key": key,
        "UploadId": upload_id,
        "MultipartUpload": {"Parts": parts},
        "MpuObjectSize": byte_length,
    }
    if conditional:
        request["IfNoneMatch"] = "*"
    return client.complete_multipart_upload(**request)


def _verify_exact(store: AwsS3DocumentBlobStore, key: str, data: bytes) -> None:
    observation = asyncio.run(store.observe(object_key=key))
    if observation.status != ObjectObservationStatus.PRESENT or observation.byte_length != len(data):
        raise HarnessFailure("Expected committed object observation was not exact.")
    verification = asyncio.run(
        store.verify_checksum(
            object_key=key,
            expected_sha256=_sha256_bytes(data),
            expected_byte_length=len(data),
        )
    )
    if verification.status != ChecksumVerificationStatus.MATCH:
        raise HarnessFailure("Committed object failed exact streamed SHA-256 verification.")


def _expect_absent(store: AwsS3DocumentBlobStore, key: str) -> None:
    if asyncio.run(store.observe(object_key=key)).status != ObjectObservationStatus.ABSENT:
        raise HarnessFailure("Multipart staging became visible before final commit.")


def _expect_denied(call: Callable[[], Any], operation: str) -> None:
    try:
        call()
    except ClientError as exc:
        if _client_error_status(exc) == 403 or str(exc.response.get("Error", {}).get("Code")) == "AccessDenied":
            return
        raise HarnessFailure(f"{operation} returned an unexpected AWS error class.") from exc
    raise HarnessFailure(f"{operation} unexpectedly succeeded without the conditional header.")


def _run_regressions(backend_dir: Path, journal: EvidenceJournal, phase: str) -> None:
    command = [
        sys.executable,
        "-m",
        "pytest",
        "-q",
        "tests/test_document_storage_service.py",
        "tests/test_document_storage_postgresql.py",
    ]
    completed = subprocess.run(
        command,
        cwd=backend_dir,
        capture_output=True,
        text=True,
        timeout=300,
        check=False,
    )
    combined = f"{completed.stdout}\n{completed.stderr}"
    match = re.search(r"(\d+) passed", combined)
    if completed.returncode != 0 or not match or "skipped" in combined.lower():
        raise HarnessFailure(f"{phase} T1-T14 regression gate did not pass without skips.")
    journal.record("DOMAIN_REGRESSION_PASS", phase=phase, passed=int(match.group(1)), skipped=0)


def _git_head(repository_root: Path) -> str:
    completed = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    value = completed.stdout.strip()
    if completed.returncode != 0 or not _COMMIT_RE.fullmatch(value):
        raise HarnessFailure("Git HEAD cannot be resolved.")
    return value


def _require_clean_tracked_tree(repository_root: Path) -> None:
    completed = subprocess.run(
        ["git", "status", "--porcelain=v1", "--untracked-files=no"],
        cwd=repository_root,
        capture_output=True,
        text=True,
        timeout=10,
        check=False,
    )
    if completed.returncode != 0 or completed.stdout.strip():
        raise HarnessFailure("Tracked repository state is not clean.")


def _require_runtime() -> None:
    if sys.version_info[:3] != RUNTIME_PYTHON:
        raise HarnessFailure("Python runtime differs from the reviewed G4 runtime.")
    if boto3.__version__ != RUNTIME_BOTO3 or botocore.__version__ != RUNTIME_BOTOCORE:
        raise HarnessFailure("boto3/botocore differ from the reviewed G4 runtime.")


def _require_explicit_temporary_credentials() -> dict[str, str]:
    if os.environ.get("AWS_PROFILE"):
        raise HarnessFailure("AWS_PROFILE is forbidden; use one explicit temporary session only.")
    names = ("AWS_ACCESS_KEY_ID", "AWS_SECRET_ACCESS_KEY", "AWS_SESSION_TOKEN")
    values = {name: os.environ.get(name, "") for name in names}
    if any(not value for value in values.values()):
        raise HarnessFailure("Explicit temporary AWS session credentials are required.")
    return values


def _make_clients(credentials: dict[str, str]) -> tuple[Any, Any]:
    session = boto3.Session(
        aws_access_key_id=credentials["AWS_ACCESS_KEY_ID"],
        aws_secret_access_key=credentials["AWS_SECRET_ACCESS_KEY"],
        aws_session_token=credentials["AWS_SESSION_TOKEN"],
        region_name=REGION,
    )
    config = Config(signature_version="s3v4", retries={"total_max_attempts": 1})
    return session.client("sts", region_name=REGION, config=config), session.client(
        "s3", region_name=REGION, config=config
    )


def _assert_object_lock_absent(s3: Any) -> None:
    try:
        object_lock = s3.get_object_lock_configuration(Bucket=BUCKET)
    except ClientError as exc:
        error_code = exc.response.get("Error", {}).get("Code")
        if error_code not in {
            "NoSuchObjectLockConfiguration",
            "ObjectLockConfigurationNotFoundError",
        }:
            raise
        return
    object_lock.pop("ResponseMetadata", None)
    if object_lock:
        raise HarnessFailure("The dedicated spike bucket must not have Object Lock configured.")


def _assert_preflight(sts: Any, s3: Any, manifest: RuntimeManifest, journal: EvidenceJournal) -> None:
    identity = sts.get_caller_identity()
    if identity.get("Account") != manifest.expected_account_id or identity.get("Arn") != manifest.expected_principal_arn:
        raise HarnessFailure("Actual AWS account/principal differs from the approved private boundary.")
    journal.record("ACCOUNT_GUARD_PASS", account_ref=ACCOUNT_REF, principal_ref="G5_HARNESS_ROLE")
    location = s3.get_bucket_location(Bucket=BUCKET).get("LocationConstraint")
    actual_region = location or "us-east-1"
    if actual_region != REGION:
        raise HarnessFailure("Bucket region differs from the frozen region.")
    public = s3.get_public_access_block(Bucket=BUCKET)["PublicAccessBlockConfiguration"]
    if public != {
        "BlockPublicAcls": True,
        "IgnorePublicAcls": True,
        "BlockPublicPolicy": True,
        "RestrictPublicBuckets": True,
    }:
        raise HarnessFailure("All four S3 Block Public Access controls must be enabled.")
    ownership = s3.get_bucket_ownership_controls(Bucket=BUCKET)["OwnershipControls"]["Rules"]
    if ownership != [{"ObjectOwnership": "BucketOwnerEnforced"}]:
        raise HarnessFailure("Bucket Owner Enforced ownership is required.")
    versioning = s3.get_bucket_versioning(Bucket=BUCKET)
    if versioning.get("Status") is not None or versioning.get("MFADelete") is not None:
        raise HarnessFailure("The dedicated spike bucket must never have had versioning enabled.")
    _assert_object_lock_absent(s3)
    encryption = s3.get_bucket_encryption(Bucket=BUCKET)["ServerSideEncryptionConfiguration"]
    rules = encryption.get("Rules") if isinstance(encryption, dict) else None
    expected_encryption = {
        "ApplyServerSideEncryptionByDefault": {
            "SSEAlgorithm": "aws:kms",
            "KMSMasterKeyID": manifest.kms_key_arn,
        },
        "BucketKeyEnabled": True,
    }
    if rules != [expected_encryption]:
        raise HarnessFailure("Bucket default encryption differs from the frozen SSE-KMS boundary.")
    lifecycle = s3.get_bucket_lifecycle_configuration(Bucket=BUCKET)
    lifecycle.pop("ResponseMetadata", None)
    if _sha256_json(lifecycle) != manifest.lifecycle_configuration_sha256:
        raise HarnessFailure("Lifecycle configuration hash differs from approval.")
    policy_text = s3.get_bucket_policy(Bucket=BUCKET).get("Policy")
    try:
        policy = json.loads(policy_text)
    except (TypeError, json.JSONDecodeError) as exc:
        raise HarnessFailure("Bucket policy is unreadable.") from exc
    if _sha256_json(policy) != manifest.bucket_policy_sha256:
        raise HarnessFailure("Bucket policy hash differs from approval.")
    existing = s3.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX, MaxKeys=10)
    uploads = s3.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, MaxUploads=10)
    if existing.get("Contents") or uploads.get("Uploads") or existing.get("IsTruncated") or uploads.get("IsTruncated"):
        raise HarnessFailure("Frozen prefix is not empty before the one authorized invocation.")
    journal.record(
        "AWS_BOUNDARY_GUARDS_PASS",
        region=REGION,
        bucket_ref="VALORA-S3-G5-BUCKET-01",
        prefix=PREFIX,
        public_access_block=True,
        ownership="BucketOwnerEnforced",
        versioning="DisabledNeverEnabled",
        encryption="aws:kms",
        lifecycle_hash=manifest.lifecycle_configuration_sha256,
        bucket_policy_hash=manifest.bucket_policy_sha256,
    )


def _run_matrix(client: MeteredS3Client, manifest: RuntimeManifest, journal: EvidenceJournal) -> None:
    fixture_a = _fixture_bytes("FIXTURE_A", SMALL_FIXTURE_SIZE)
    fixture_b = _fixture_bytes("FIXTURE_B", SMALL_FIXTURE_SIZE)
    fixture_m = _fixture_bytes("FIXTURE_M", MULTIPART_FIXTURE_SIZE)
    store = AwsS3DocumentBlobStore(
        bucket=BUCKET,
        key_prefix=PREFIX,
        region_name=REGION,
        kms_key_arn=manifest.kms_key_arn,
        client=client,
        multipart_threshold=MULTIPART_PART_SIZE,
        multipart_part_size=MULTIPART_PART_SIZE,
    )

    small_key = PREFIX + "small-primary.bin"
    created = asyncio.run(
        store.create_immutable(
            object_key=small_key,
            content=_content(fixture_a),
            byte_length=len(fixture_a),
            expected_sha256=_sha256_bytes(fixture_a),
        )
    )
    if created.status != CreateImmutableStatus.CREATED:
        raise HarnessFailure("S3-1 conditional PutObject did not create exactly one object.")
    _verify_exact(store, small_key, fixture_a)
    journal.record("SCENARIO_PASS", scenario="S3-1")

    duplicate = asyncio.run(
        store.create_immutable(
            object_key=small_key,
            content=_content(fixture_a),
            byte_length=len(fixture_a),
            expected_sha256=_sha256_bytes(fixture_a),
        )
    )
    if duplicate.status != CreateImmutableStatus.ALREADY_EXISTS:
        raise HarnessFailure("S3-2 same-key create did not return the existing-key class.")
    _verify_exact(store, small_key, fixture_a)
    journal.record("SCENARIO_PASS", scenario="S3-2")

    mismatch = asyncio.run(
        store.create_immutable(
            object_key=small_key,
            content=_content(fixture_b),
            byte_length=len(fixture_b),
            expected_sha256=_sha256_bytes(fixture_b),
        )
    )
    if mismatch.status != CreateImmutableStatus.ALREADY_EXISTS:
        raise HarnessFailure("S3-3 competing bytes did not preserve the existing key.")
    mismatch_verify = asyncio.run(
        store.verify_checksum(
            object_key=small_key,
            expected_sha256=_sha256_bytes(fixture_b),
            expected_byte_length=len(fixture_b),
        )
    )
    if mismatch_verify.status != ChecksumVerificationStatus.MISMATCH:
        raise HarnessFailure("S3-3 did not classify different bytes as reconciliation required.")
    _verify_exact(store, small_key, fixture_a)
    journal.record("SCENARIO_PASS", scenario="S3-3")

    multipart_key = PREFIX + "multipart-primary.bin"
    upload_id = _start_multipart(client, manifest, multipart_key)
    parts = _upload_parts(client, multipart_key, upload_id, fixture_m)
    _expect_absent(store, multipart_key)
    journal.record("SCENARIO_PASS", scenario="S3-4")
    _complete_multipart(client, multipart_key, upload_id, parts, len(fixture_m), conditional=True)
    _verify_exact(store, multipart_key, fixture_m)
    journal.record("SCENARIO_PASS", scenario="S3-5")

    race_key = PREFIX + "multipart-race.bin"
    race_upload = _start_multipart(client, manifest, race_key)
    race_parts = _upload_parts(client, race_key, race_upload, fixture_m)
    _conditional_put(client, manifest, race_key, fixture_b)
    try:
        _complete_multipart(client, race_key, race_upload, race_parts, len(fixture_m), conditional=True)
    except ClientError as exc:
        if _client_error_status(exc) not in {409, 412}:
            raise HarnessFailure("S3-6 returned an unexpected competing-write class.") from exc
    else:
        raise HarnessFailure("S3-6 multipart completion overwrote a competing object.")
    _verify_exact(store, race_key, fixture_b)
    client.abort_multipart_upload(Bucket=BUCKET, Key=race_key, UploadId=race_upload)
    journal.record("SCENARIO_PASS", scenario="S3-6")

    unbound_key = PREFIX + "unbound.bin"
    unbound = asyncio.run(
        store.create_immutable(
            object_key=unbound_key,
            content=_content(fixture_a),
            byte_length=len(fixture_a),
            expected_sha256=_sha256_bytes(fixture_a),
        )
    )
    if unbound.status != CreateImmutableStatus.CREATED:
        raise HarnessFailure("S3-10 unbound candidate setup failed.")
    _verify_exact(store, unbound_key, fixture_a)
    cleanup = asyncio.run(
        store.delete_uncommitted_or_expire(
            object_key=unbound_key,
            expected_sha256=_sha256_bytes(fixture_a),
        )
    )
    if cleanup.status != CleanupStatus.DELETED:
        raise HarnessFailure("S3-10 exact unbound candidate cleanup failed.")
    _expect_absent(store, unbound_key)
    journal.record("SCENARIO_PASS", scenario="S3-10")

    denied_put_key = PREFIX + "policy-put-denied.bin"
    _expect_denied(
        lambda: client.put_object(
            Bucket=BUCKET,
            Key=denied_put_key,
            Body=fixture_a,
            ContentLength=len(fixture_a),
            ChecksumAlgorithm="SHA256",
            ChecksumSHA256=_checksum_b64(fixture_a),
            **_sse_request(manifest),
        ),
        "unconditional PutObject",
    )
    denied_complete_key = PREFIX + "policy-complete-denied.bin"
    denied_upload = _start_multipart(client, manifest, denied_complete_key)
    denied_parts = _upload_parts(client, denied_complete_key, denied_upload, fixture_m)
    _expect_denied(
        lambda: _complete_multipart(
            client,
            denied_complete_key,
            denied_upload,
            denied_parts,
            len(fixture_m),
            conditional=False,
        ),
        "unconditional CompleteMultipartUpload",
    )
    client.abort_multipart_upload(
        Bucket=BUCKET,
        Key=denied_complete_key,
        UploadId=denied_upload,
    )
    journal.record("SCENARIO_PASS", scenario="S3-12")

    incomplete_key = PREFIX + "incomplete.bin"
    incomplete_upload = _start_multipart(client, manifest, incomplete_key)
    first_part = fixture_m[:MULTIPART_PART_SIZE]
    _upload_parts(client, incomplete_key, incomplete_upload, first_part)
    inventory = client.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, MaxUploads=10)
    uploads = inventory.get("Uploads", [])
    matching = [entry for entry in uploads if entry.get("Key") == incomplete_key and entry.get("UploadId") == incomplete_upload]
    if len(matching) != 1 or inventory.get("IsTruncated"):
        raise HarnessFailure("S3-9 exact-prefix multipart inventory was not bounded and exact.")
    parts_inventory = client.list_parts(
        Bucket=BUCKET,
        Key=incomplete_key,
        UploadId=incomplete_upload,
        MaxParts=10,
    )
    if len(parts_inventory.get("Parts", [])) != 1 or parts_inventory.get("IsTruncated"):
        raise HarnessFailure("S3-9 part inventory did not match the staged fixture.")
    journal.record(
        "MULTIPART_INVENTORY",
        key_ref=_relative_key(incomplete_key),
        upload_id_ref=_sha256_bytes(incomplete_upload.encode())[:16],
        observed_parts=1,
    )
    client.abort_multipart_upload(Bucket=BUCKET, Key=incomplete_key, UploadId=incomplete_upload)
    journal.record("SCENARIO_PASS", scenario="S3-9")

    lost_put_key = PREFIX + "lost-put.bin"
    with _lose_exactly_one_response(client._client, "PutObject", journal) as fault:
        lost_put = asyncio.run(
            store.create_immutable(
                object_key=lost_put_key,
                content=_content(fixture_a),
                byte_length=len(fixture_a),
                expected_sha256=_sha256_bytes(fixture_a),
            )
        )
    if lost_put.status != CreateImmutableStatus.OUTCOME_UNKNOWN or fault.dispatch_count != 1:
        raise HarnessFailure("S3-7 did not produce one ambiguous final write.")
    _verify_exact(store, lost_put_key, fixture_a)
    journal.record("SCENARIO_PASS", scenario="S3-7", final_write_dispatch_count=1)

    lost_complete_key = PREFIX + "lost-complete.bin"
    with _lose_exactly_one_response(client._client, "CompleteMultipartUpload", journal) as fault:
        lost_complete = asyncio.run(
            store.create_immutable(
                object_key=lost_complete_key,
                content=_content(fixture_m),
                byte_length=len(fixture_m),
                expected_sha256=_sha256_bytes(fixture_m),
            )
        )
    if lost_complete.status != CreateImmutableStatus.OUTCOME_UNKNOWN or fault.dispatch_count != 1:
        raise HarnessFailure("S3-8 did not produce one ambiguous final multipart commit.")
    _verify_exact(store, lost_complete_key, fixture_m)
    journal.record("SCENARIO_PASS", scenario="S3-8", final_write_dispatch_count=1)
    journal.record("SCENARIO_PASS", scenario="S3-11", prohibited_field_count=0)


def _cleanup_prefix(client: MeteredS3Client, journal: EvidenceJournal) -> None:
    expected_keys = {PREFIX + name for name in _OBJECT_NAMES}
    upload_inventory = client.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, MaxUploads=10)
    if upload_inventory.get("IsTruncated"):
        raise HarnessFailure("Cleanup multipart inventory exceeded the bounded page.")
    uploads = upload_inventory.get("Uploads", [])
    if len(uploads) > MAX_MULTIPART_UPLOADS:
        raise HarnessFailure("Cleanup multipart inventory exceeded the approved maximum.")
    for entry in uploads:
        key = entry.get("Key")
        upload_id = entry.get("UploadId")
        if key not in expected_keys or not isinstance(upload_id, str) or not upload_id:
            raise HarnessFailure("Cleanup found an out-of-manifest multipart upload.")
        journal.record(
            "CLEANUP_MULTIPART_TARGET",
            key_ref=_relative_key(key),
            upload_id_ref=_sha256_bytes(upload_id.encode())[:16],
        )
        client.abort_multipart_upload(Bucket=BUCKET, Key=key, UploadId=upload_id)
    object_inventory = client.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX, MaxKeys=10)
    if object_inventory.get("IsTruncated"):
        raise HarnessFailure("Cleanup object inventory exceeded the bounded page.")
    objects = object_inventory.get("Contents", [])
    if len(objects) > MAX_COMMITTED_OBJECTS:
        raise HarnessFailure("Cleanup object inventory exceeded the approved maximum.")
    for entry in objects:
        key = entry.get("Key")
        if key not in expected_keys:
            raise HarnessFailure("Cleanup found an out-of-manifest object.")
        journal.record("CLEANUP_OBJECT_TARGET", key_ref=_relative_key(key))
        client.delete_object(Bucket=BUCKET, Key=key)
    remaining_objects = client.list_objects_v2(Bucket=BUCKET, Prefix=PREFIX, MaxKeys=10)
    remaining_uploads = client.list_multipart_uploads(Bucket=BUCKET, Prefix=PREFIX, MaxUploads=10)
    if (
        remaining_objects.get("Contents")
        or remaining_uploads.get("Uploads")
        or remaining_objects.get("IsTruncated")
        or remaining_uploads.get("IsTruncated")
    ):
        raise HarnessFailure("Cleanup could not prove zero exact-prefix residue.")
    journal.record("PREFIX_CLEANUP_PASS", objects=0, multipart_uploads=0)


def _run_live(manifest_path: Path, evidence_dir: Path) -> int:
    backend_dir = Path(__file__).resolve().parents[1]
    repository_root = backend_dir.parent
    manifest = RuntimeManifest.load(manifest_path)
    _require_runtime()
    _require_clean_tracked_tree(repository_root)
    if _git_head(repository_root) != manifest.approved_executable_commit:
        raise HarnessFailure("Git HEAD differs from the Product Owner-approved executable commit.")
    credentials = _require_explicit_temporary_credentials()
    journal = EvidenceJournal(evidence_dir, repository_root=repository_root)
    journal.record(
        "RUN_STARTED",
        run_id=RUN_ID,
        approval_reference=manifest.approval_reference,
        executable_commit=manifest.approved_executable_commit,
        review_manifest_sha256=manifest.approved_review_manifest_sha256,
        account_ref=ACCOUNT_REF,
        region=REGION,
        bucket_ref="VALORA-S3-G5-BUCKET-01",
        prefix=PREFIX,
        fixture_manifest=manifest.fixtures,
        limits=frozen_limits(),
        cleanup_owner=manifest.cleanup_owner,
    )
    sts, raw_s3 = _make_clients(credentials)
    metered: MeteredS3Client | None = MeteredS3Client(raw_s3, journal)
    preflight_ok = False
    cleanup_ok = False
    try:
        _run_regressions(backend_dir, journal, "BEFORE_LIVE")
        _assert_preflight(sts, metered, manifest, journal)
        preflight_ok = True
        _run_matrix(metered, manifest, journal)
        _cleanup_prefix(metered, journal)
        cleanup_ok = True
        _run_regressions(backend_dir, journal, "AFTER_LIVE")
        journal.record(
            "RUN_FINISHED",
            result="STATIC_MATRIX_AND_CLEANUP_PASS",
            s3_requests=metered.requests,
            uploaded_bytes=metered.uploaded_bytes,
            get_bytes=metered.get_bytes,
            cleanup_complete=True,
            external_configuration_cleanup_required=True,
        )
        return 0
    except Exception as exc:
        if preflight_ok and metered is not None and not cleanup_ok:
            try:
                _cleanup_prefix(metered, journal)
                cleanup_ok = True
            except Exception:
                cleanup_ok = False
        journal.record(
            "RUN_FINISHED",
            result="FAIL",
            failure_class=type(exc).__name__,
            cleanup_complete=cleanup_ok,
            rerun_allowed=False,
            external_configuration_cleanup_required=True,
        )
        raise
    finally:
        journal.close()


def _validate_committed_template(path: Path) -> None:
    raw = json.loads(path.read_text(encoding="utf-8"))
    if raw.get("schema_version") != SCHEMA_VERSION:
        raise HarnessFailure("Committed manifest template has the wrong schema.")
    for key, value in {
        "run_id": RUN_ID,
        "account_ref": ACCOUNT_REF,
        "region": REGION,
        "bucket": BUCKET,
        "prefix": PREFIX,
        "fixtures": fixture_manifest(),
        "limits": frozen_limits(),
    }.items():
        if raw.get(key) != value:
            raise HarnessFailure(f"Committed manifest template field {key} drifted.")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--manifest", type=Path, required=True)
    parser.add_argument("--evidence-dir", type=Path)
    parser.add_argument("--self-test", action="store_true")
    parser.add_argument("--execute-live", action="store_true")
    args = parser.parse_args(argv)
    if args.self_test == args.execute_live:
        parser.error("select exactly one of --self-test or --execute-live")
    if args.execute_live and args.evidence_dir is None:
        parser.error("--execute-live requires --evidence-dir")
    return args


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        if args.self_test:
            _validate_committed_template(args.manifest)
            print(json.dumps({"network": "NOT_ATTEMPTED", "self_test": "PASS"}, sort_keys=True))
            return 0
        return _run_live(args.manifest, args.evidence_dir)
    except HarnessFailure as exc:
        print(f"VALORA S3 harness stopped: {exc}", file=sys.stderr)
        return 2
    except Exception as exc:
        print(f"VALORA S3 harness stopped: {type(exc).__name__}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
