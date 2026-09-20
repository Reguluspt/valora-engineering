"""Provider-neutral immutable document-object boundary and deterministic local fake."""
from __future__ import annotations

import hashlib
from collections.abc import AsyncIterable
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from typing import Protocol


class CreateImmutableStatus(StrEnum):
    CREATED = "CREATED"
    ALREADY_EXISTS = "ALREADY_EXISTS"
    OUTCOME_UNKNOWN = "OUTCOME_UNKNOWN"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


class ObjectObservationStatus(StrEnum):
    ABSENT = "ABSENT"
    PRESENT = "PRESENT"
    UNAVAILABLE = "UNAVAILABLE"
    AMBIGUOUS = "AMBIGUOUS"


class ChecksumVerificationStatus(StrEnum):
    MATCH = "MATCH"
    MISMATCH = "MISMATCH"
    ABSENT = "ABSENT"
    UNAVAILABLE = "UNAVAILABLE"
    UNVERIFIABLE = "UNVERIFIABLE"


class CleanupStatus(StrEnum):
    DELETED = "DELETED"
    ABSENT = "ABSENT"
    UNAVAILABLE = "UNAVAILABLE"
    REJECTED = "REJECTED"


class InjectedStorageCrash(RuntimeError):
    """Test-only process interruption raised at a deterministic fake boundary."""


@dataclass(frozen=True)
class CreateImmutableResult:
    status: CreateImmutableStatus
    provider_request_id: str | None = None
    provider_object_version: str | None = None


@dataclass(frozen=True)
class ObjectObservation:
    status: ObjectObservationStatus
    byte_length: int | None = None
    provider_object_version: str | None = None
    observed_etag: str | None = None
    object_created_at: datetime | None = None
    provider_request_id: str | None = None


@dataclass(frozen=True)
class ChecksumVerification:
    status: ChecksumVerificationStatus
    observed_sha256: str | None = None
    observed_byte_length: int | None = None


@dataclass(frozen=True)
class CleanupResult:
    status: CleanupStatus


@dataclass(frozen=True)
class _FakeObject:
    content: bytes
    version: str
    created_at: datetime


_FAKE_EPOCH = datetime(2026, 1, 1, tzinfo=timezone.utc)


class DocumentBlobStore(Protocol):
    """The four operations required by the immutable-object contract."""

    provider_kind: str

    async def create_immutable(
        self,
        *,
        object_key: str,
        content: AsyncIterable[bytes],
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult: ...

    async def observe(self, *, object_key: str) -> ObjectObservation: ...

    async def verify_checksum(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification: ...

    async def delete_uncommitted_or_expire(
        self, *, object_key: str, expected_sha256: str
    ) -> CleanupResult: ...


class InMemoryDocumentBlobStore:
    """Deterministic fake; faults are explicit and never infer provider success."""

    provider_kind = "fake"

    def __init__(self) -> None:
        self._objects: dict[str, _FakeObject] = {}
        self._faults: dict[str, str] = {}
        self._version = 0
        self.calls = {"create": 0, "observe": 0, "verify": 0, "cleanup": 0}

    def set_fault(self, operation: str, outcome: str) -> None:
        self._faults[operation] = outcome

    def clear_fault(self, operation: str) -> None:
        self._faults.pop(operation, None)

    def seed_object(self, *, object_key: str, content: bytes) -> None:
        """Seed an independently committed object for deterministic recovery tests."""
        self._version += 1
        self._objects[object_key] = _FakeObject(
            content=content,
            version=str(self._version),
            created_at=_FAKE_EPOCH + timedelta(seconds=self._version),
        )

    def object_bytes(self, *, object_key: str) -> bytes | None:
        stored = self._objects.get(object_key)
        return stored.content if stored is not None else None

    async def create_immutable(
        self,
        *,
        object_key: str,
        content: AsyncIterable[bytes],
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult:
        self.calls["create"] += 1
        if self._faults.get("create") == "before_commit_crash":
            raise InjectedStorageCrash("injected crash before immutable object commit")
        if self._faults.get("create") == "unavailable":
            return CreateImmutableResult(CreateImmutableStatus.UNAVAILABLE)
        if self._faults.get("create") == "before_commit":
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        data = b"".join([chunk async for chunk in content])
        if len(data) != byte_length or hashlib.sha256(data).hexdigest() != expected_sha256:
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        if object_key in self._objects:
            return CreateImmutableResult(CreateImmutableStatus.ALREADY_EXISTS)
        self._version += 1
        stored = _FakeObject(
            content=data,
            version=str(self._version),
            created_at=_FAKE_EPOCH + timedelta(seconds=self._version),
        )
        self._objects[object_key] = stored
        if self._faults.get("create") == "after_commit_before_response":
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        if self._faults.get("create") == "after_commit_crash":
            raise InjectedStorageCrash("injected crash after immutable object commit")
        return CreateImmutableResult(
            CreateImmutableStatus.CREATED,
            provider_request_id=f"fake-create-{self._version}",
            provider_object_version=stored.version,
        )

    async def observe(self, *, object_key: str) -> ObjectObservation:
        self.calls["observe"] += 1
        if self._faults.get("observe") == "unavailable":
            return ObjectObservation(ObjectObservationStatus.UNAVAILABLE)
        if self._faults.get("observe") == "ambiguous":
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        stored = self._objects.get(object_key)
        if stored is None:
            return ObjectObservation(ObjectObservationStatus.ABSENT)
        return ObjectObservation(
            ObjectObservationStatus.PRESENT,
            byte_length=len(stored.content),
            provider_object_version=stored.version,
            observed_etag=f"fake-{stored.version}",
            object_created_at=stored.created_at,
            provider_request_id=f"fake-observe-{stored.version}",
        )

    async def verify_checksum(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification:
        self.calls["verify"] += 1
        if self._faults.get("verify") == "unavailable":
            return ChecksumVerification(ChecksumVerificationStatus.UNAVAILABLE)
        if self._faults.get("verify") == "unverifiable":
            return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
        stored = self._objects.get(object_key)
        if stored is None:
            return ChecksumVerification(ChecksumVerificationStatus.ABSENT)
        data = stored.content
        digest = hashlib.sha256(data).hexdigest()
        if len(data) != expected_byte_length or digest != expected_sha256:
            return ChecksumVerification(
                ChecksumVerificationStatus.MISMATCH,
                observed_sha256=digest,
                observed_byte_length=len(data),
            )
        return ChecksumVerification(
            ChecksumVerificationStatus.MATCH,
            observed_sha256=digest,
            observed_byte_length=len(data),
        )

    async def delete_uncommitted_or_expire(
        self, *, object_key: str, expected_sha256: str
    ) -> CleanupResult:
        self.calls["cleanup"] += 1
        if self._faults.get("cleanup") == "unavailable":
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        if self._faults.get("cleanup") == "rejected":
            return CleanupResult(CleanupStatus.REJECTED)
        stored = self._objects.get(object_key)
        if stored is None:
            return CleanupResult(CleanupStatus.ABSENT)
        if hashlib.sha256(stored.content).hexdigest() != expected_sha256:
            return CleanupResult(CleanupStatus.REJECTED)
        del self._objects[object_key]
        return CleanupResult(CleanupStatus.DELETED)
