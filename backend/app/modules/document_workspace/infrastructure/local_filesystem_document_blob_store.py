"""Linux create-only filesystem adapter for authoritative document revision bytes."""
from __future__ import annotations

import errno
import hashlib
import os
import re
import stat
import uuid
from collections.abc import AsyncIterable
from datetime import datetime, timezone
from pathlib import Path

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


_SHA256_RE = re.compile(r"[0-9a-f]{64}")
_KEY_COMPONENT_RE = re.compile(r"[A-Za-z0-9][A-Za-z0-9._-]{0,254}")
_STAGING_NAME_RE = re.compile(r"[0-9a-f]{32}\.stage")
_READ_SIZE = 1024 * 1024
_DIRECTORY_FLAGS = os.O_RDONLY | getattr(os, "O_DIRECTORY", 0) | getattr(os, "O_NOFOLLOW", 0)
_FILE_READ_FLAGS = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)


class LocalFilesystemConfigurationError(RuntimeError):
    """The configured root cannot uphold the create-only filesystem contract."""


class LocalFilesystemDocumentBlobStore:
    """Store exact immutable bytes beneath a pre-provisioned Linux root.

    Publication uses a same-filesystem hard link. It is atomic, fails on an existing target and has
    no overwrite-capable fallback. Directory descriptors and ``O_NOFOLLOW`` keep all operations
    rooted even if an unsafe path entry appears concurrently.
    """

    provider_kind = "local"

    def __init__(self, *, root: str | os.PathLike[str]) -> None:
        if os.name != "posix" or not hasattr(os, "link"):
            raise LocalFilesystemConfigurationError("local document blobs require Linux/POSIX")
        root_path = Path(root)
        if not root_path.is_absolute():
            raise LocalFilesystemConfigurationError("document blob root must be absolute")
        try:
            root_stat = root_path.lstat()
        except OSError as exc:
            raise LocalFilesystemConfigurationError("document blob root is unavailable") from exc
        if not stat.S_ISDIR(root_stat.st_mode) or stat.S_ISLNK(root_stat.st_mode):
            raise LocalFilesystemConfigurationError("document blob root must be a real directory")
        if root_stat.st_mode & (stat.S_IWGRP | stat.S_IWOTH):
            raise LocalFilesystemConfigurationError(
                "document blob root must not be group- or world-writable"
            )
        if self._inside_git_worktree(root_path):
            raise LocalFilesystemConfigurationError("document blob root must be outside a Git worktree")

        try:
            root_fd = os.open(root_path, _DIRECTORY_FLAGS)
            self._ensure_child_directory(root_fd, "objects")
            self._ensure_child_directory(root_fd, "staging")
            objects_fd = os.open("objects", _DIRECTORY_FLAGS, dir_fd=root_fd)
            staging_fd = os.open("staging", _DIRECTORY_FLAGS, dir_fd=root_fd)
        except OSError as exc:
            for descriptor in (
                locals().get("staging_fd"),
                locals().get("objects_fd"),
                locals().get("root_fd"),
            ):
                if isinstance(descriptor, int):
                    os.close(descriptor)
            raise LocalFilesystemConfigurationError("document blob root is not safely writable") from exc
        try:
            if os.fstat(objects_fd).st_dev != os.fstat(staging_fd).st_dev:
                raise LocalFilesystemConfigurationError("objects and staging must share a filesystem")
            self._probe_no_replace_link(staging_fd)
        finally:
            os.close(staging_fd)
            os.close(objects_fd)
            os.close(root_fd)
        self._root = root_path

    @staticmethod
    def _inside_git_worktree(path: Path) -> bool:
        for candidate in (path, *path.parents):
            if (candidate / ".git").exists():
                return True
        return False

    @staticmethod
    def _ensure_child_directory(root_fd: int, name: str) -> None:
        try:
            os.mkdir(name, mode=0o700, dir_fd=root_fd)
        except FileExistsError:
            pass
        child_fd = os.open(name, _DIRECTORY_FLAGS, dir_fd=root_fd)
        try:
            child_stat = os.fstat(child_fd)
            if not stat.S_ISDIR(child_stat.st_mode) or child_stat.st_mode & stat.S_IWOTH:
                raise OSError(errno.EPERM, "unsafe document blob directory")
        finally:
            os.close(child_fd)

    @staticmethod
    def _probe_no_replace_link(staging_fd: int) -> None:
        source = f"{uuid.uuid4().hex}.probe"
        target = f"{uuid.uuid4().hex}.probe-link"
        source_fd: int | None = None
        try:
            source_fd = os.open(
                source,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=staging_fd,
            )
            os.write(source_fd, b"probe")
            os.fsync(source_fd)
            os.link(
                source,
                target,
                src_dir_fd=staging_fd,
                dst_dir_fd=staging_fd,
                follow_symlinks=False,
            )
            try:
                os.link(
                    source,
                    target,
                    src_dir_fd=staging_fd,
                    dst_dir_fd=staging_fd,
                    follow_symlinks=False,
                )
            except FileExistsError:
                pass
            else:
                raise LocalFilesystemConfigurationError("hard-link publish replaced an existing name")
        except LocalFilesystemConfigurationError:
            raise
        except OSError as exc:
            raise LocalFilesystemConfigurationError(
                "filesystem does not support durable no-replace hard links"
            ) from exc
        finally:
            if source_fd is not None:
                os.close(source_fd)
            for name in (target, source):
                try:
                    os.unlink(name, dir_fd=staging_fd)
                except FileNotFoundError:
                    pass
            os.fsync(staging_fd)

    @staticmethod
    def _key_parts(object_key: str) -> tuple[str, ...] | None:
        if not isinstance(object_key, str) or not object_key or "\\" in object_key:
            return None
        if object_key.startswith("/") or object_key.endswith("/") or "//" in object_key:
            return None
        parts = tuple(object_key.split("/"))
        if not parts or any(not _KEY_COMPONENT_RE.fullmatch(part) for part in parts):
            return None
        return parts

    def _open_base(self, child: str) -> int:
        root_fd = os.open(self._root, _DIRECTORY_FLAGS)
        try:
            return os.open(child, _DIRECTORY_FLAGS, dir_fd=root_fd)
        finally:
            os.close(root_fd)

    @staticmethod
    def _open_parent(objects_fd: int, parts: tuple[str, ...], *, create: bool) -> int:
        current = os.dup(objects_fd)
        try:
            for component in parts[:-1]:
                if create:
                    try:
                        os.mkdir(component, mode=0o700, dir_fd=current)
                        os.fsync(current)
                    except FileExistsError:
                        pass
                next_fd = os.open(component, _DIRECTORY_FLAGS, dir_fd=current)
                os.close(current)
                current = next_fd
            return current
        except Exception:
            os.close(current)
            raise

    @staticmethod
    def _write_all(file_fd: int, chunk: bytes) -> None:
        view = memoryview(chunk)
        while view:
            written = os.write(file_fd, view)
            if written <= 0:
                raise OSError(errno.EIO, "short filesystem write")
            view = view[written:]

    @staticmethod
    def _digest_fd(file_fd: int) -> tuple[str, int]:
        digest = hashlib.sha256()
        length = 0
        while True:
            chunk = os.read(file_fd, _READ_SIZE)
            if not chunk:
                break
            digest.update(chunk)
            length += len(chunk)
        return digest.hexdigest(), length

    @classmethod
    def _verify_entry(
        cls,
        parent_fd: int,
        name: str,
        *,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification:
        try:
            file_fd = os.open(name, _FILE_READ_FLAGS, dir_fd=parent_fd)
        except FileNotFoundError:
            return ChecksumVerification(ChecksumVerificationStatus.ABSENT)
        except PermissionError:
            return ChecksumVerification(ChecksumVerificationStatus.UNAVAILABLE)
        except OSError:
            return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
        try:
            file_stat = os.fstat(file_fd)
            if not stat.S_ISREG(file_stat.st_mode) or file_stat.st_nlink < 1:
                return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
            digest, length = cls._digest_fd(file_fd)
        except OSError:
            return ChecksumVerification(ChecksumVerificationStatus.UNAVAILABLE)
        finally:
            os.close(file_fd)
        status = (
            ChecksumVerificationStatus.MATCH
            if digest == expected_sha256 and length == expected_byte_length
            else ChecksumVerificationStatus.MISMATCH
        )
        return ChecksumVerification(
            status,
            observed_sha256=digest,
            observed_byte_length=length,
        )

    async def create_immutable(
        self,
        *,
        object_key: str,
        content: AsyncIterable[bytes],
        byte_length: int,
        expected_sha256: str,
    ) -> CreateImmutableResult:
        parts = self._key_parts(object_key)
        if parts is None or byte_length < 0 or not _SHA256_RE.fullmatch(expected_sha256):
            return CreateImmutableResult(CreateImmutableStatus.REJECTED)
        objects_fd: int | None = None
        staging_fd: int | None = None
        parent_fd: int | None = None
        staged_fd: int | None = None
        staging_name = f"{uuid.uuid4().hex}.stage"
        published = False
        try:
            objects_fd = self._open_base("objects")
            staging_fd = self._open_base("staging")
            if os.fstat(objects_fd).st_dev != os.fstat(staging_fd).st_dev:
                return CreateImmutableResult(CreateImmutableStatus.UNAVAILABLE)
            parent_fd = self._open_parent(objects_fd, parts, create=True)
            staged_fd = os.open(
                staging_name,
                os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0),
                0o600,
                dir_fd=staging_fd,
            )
            digest = hashlib.sha256()
            actual_length = 0
            async for chunk in content:
                if not isinstance(chunk, bytes):
                    return CreateImmutableResult(CreateImmutableStatus.REJECTED)
                actual_length += len(chunk)
                if actual_length > byte_length:
                    return CreateImmutableResult(CreateImmutableStatus.REJECTED)
                digest.update(chunk)
                self._write_all(staged_fd, chunk)
            if actual_length != byte_length or digest.hexdigest() != expected_sha256:
                return CreateImmutableResult(CreateImmutableStatus.REJECTED)
            os.fsync(staged_fd)
            os.fchmod(staged_fd, 0o400)
            os.fsync(staged_fd)
            try:
                os.link(
                    staging_name,
                    parts[-1],
                    src_dir_fd=staging_fd,
                    dst_dir_fd=parent_fd,
                    follow_symlinks=False,
                )
                published = True
            except FileExistsError:
                existing = self._verify_entry(
                    parent_fd,
                    parts[-1],
                    expected_sha256=expected_sha256,
                    expected_byte_length=byte_length,
                )
                status = (
                    CreateImmutableStatus.ALREADY_EXISTS
                    if existing.status == ChecksumVerificationStatus.MATCH
                    else (
                        CreateImmutableStatus.UNAVAILABLE
                        if existing.status == ChecksumVerificationStatus.UNAVAILABLE
                        else CreateImmutableStatus.REJECTED
                    )
                )
                return CreateImmutableResult(status)
            os.fsync(parent_fd)
            return CreateImmutableResult(
                CreateImmutableStatus.CREATED,
                provider_object_version=self._entry_version(parent_fd, parts[-1]),
            )
        except PermissionError:
            return CreateImmutableResult(
                CreateImmutableStatus.OUTCOME_UNKNOWN if published else CreateImmutableStatus.UNAVAILABLE
            )
        except OSError:
            return CreateImmutableResult(
                CreateImmutableStatus.OUTCOME_UNKNOWN if published else CreateImmutableStatus.UNAVAILABLE
            )
        finally:
            if staged_fd is not None:
                os.close(staged_fd)
            if staging_fd is not None:
                try:
                    os.unlink(staging_name, dir_fd=staging_fd)
                    os.fsync(staging_fd)
                except OSError:
                    pass
            for descriptor in (parent_fd, staging_fd, objects_fd):
                if descriptor is not None:
                    os.close(descriptor)

    @staticmethod
    def _entry_version(parent_fd: int, name: str) -> str | None:
        try:
            entry = os.stat(name, dir_fd=parent_fd, follow_symlinks=False)
        except OSError:
            return None
        return f"{entry.st_dev:x}:{entry.st_ino:x}"

    async def observe(self, *, object_key: str) -> ObjectObservation:
        parts = self._key_parts(object_key)
        if parts is None:
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        objects_fd: int | None = None
        parent_fd: int | None = None
        file_fd: int | None = None
        try:
            objects_fd = self._open_base("objects")
            parent_fd = self._open_parent(objects_fd, parts, create=False)
            file_fd = os.open(parts[-1], _FILE_READ_FLAGS, dir_fd=parent_fd)
            entry = os.fstat(file_fd)
            if not stat.S_ISREG(entry.st_mode):
                return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
            return ObjectObservation(
                ObjectObservationStatus.PRESENT,
                byte_length=entry.st_size,
                provider_object_version=f"{entry.st_dev:x}:{entry.st_ino:x}",
                object_created_at=datetime.fromtimestamp(entry.st_ctime, tz=timezone.utc),
            )
        except FileNotFoundError:
            return ObjectObservation(ObjectObservationStatus.ABSENT)
        except PermissionError:
            return ObjectObservation(ObjectObservationStatus.UNAVAILABLE)
        except OSError:
            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS)
        finally:
            for descriptor in (file_fd, parent_fd, objects_fd):
                if descriptor is not None:
                    os.close(descriptor)

    async def verify_checksum(
        self,
        *,
        object_key: str,
        expected_sha256: str,
        expected_byte_length: int,
    ) -> ChecksumVerification:
        parts = self._key_parts(object_key)
        if (
            parts is None
            or expected_byte_length < 0
            or not _SHA256_RE.fullmatch(expected_sha256)
        ):
            return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
        objects_fd: int | None = None
        parent_fd: int | None = None
        try:
            objects_fd = self._open_base("objects")
            parent_fd = self._open_parent(objects_fd, parts, create=False)
            return self._verify_entry(
                parent_fd,
                parts[-1],
                expected_sha256=expected_sha256,
                expected_byte_length=expected_byte_length,
            )
        except FileNotFoundError:
            return ChecksumVerification(ChecksumVerificationStatus.ABSENT)
        except PermissionError:
            return ChecksumVerification(ChecksumVerificationStatus.UNAVAILABLE)
        except OSError:
            return ChecksumVerification(ChecksumVerificationStatus.UNVERIFIABLE)
        finally:
            for descriptor in (parent_fd, objects_fd):
                if descriptor is not None:
                    os.close(descriptor)

    async def delete_uncommitted_or_expire(
        self, *, object_key: str, expected_sha256: str
    ) -> CleanupResult:
        parts = self._key_parts(object_key)
        if parts is None or not _SHA256_RE.fullmatch(expected_sha256):
            return CleanupResult(CleanupStatus.REJECTED)
        objects_fd: int | None = None
        parent_fd: int | None = None
        file_fd: int | None = None
        try:
            objects_fd = self._open_base("objects")
            parent_fd = self._open_parent(objects_fd, parts, create=False)
            file_fd = os.open(parts[-1], _FILE_READ_FLAGS, dir_fd=parent_fd)
            opened = os.fstat(file_fd)
            if not stat.S_ISREG(opened.st_mode):
                return CleanupResult(CleanupStatus.REJECTED)
            observed_sha256, _ = self._digest_fd(file_fd)
            if observed_sha256 != expected_sha256:
                return CleanupResult(CleanupStatus.REJECTED)
            current = os.stat(parts[-1], dir_fd=parent_fd, follow_symlinks=False)
            if (current.st_dev, current.st_ino) != (opened.st_dev, opened.st_ino):
                return CleanupResult(CleanupStatus.REJECTED)
            os.unlink(parts[-1], dir_fd=parent_fd)
            os.fsync(parent_fd)
            return CleanupResult(CleanupStatus.DELETED)
        except FileNotFoundError:
            return CleanupResult(CleanupStatus.ABSENT)
        except PermissionError:
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        except OSError:
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        finally:
            for descriptor in (file_fd, parent_fd, objects_fd):
                if descriptor is not None:
                    os.close(descriptor)

    def cleanup_orphan_staging(self, *, staging_name: str) -> CleanupResult:
        """Remove one exact adapter staging artifact; never recurse or accept a path."""
        if not isinstance(staging_name, str) or not _STAGING_NAME_RE.fullmatch(staging_name):
            return CleanupResult(CleanupStatus.REJECTED)
        staging_fd: int | None = None
        try:
            staging_fd = self._open_base("staging")
            entry = os.stat(staging_name, dir_fd=staging_fd, follow_symlinks=False)
            if not stat.S_ISREG(entry.st_mode):
                return CleanupResult(CleanupStatus.REJECTED)
            os.unlink(staging_name, dir_fd=staging_fd)
            os.fsync(staging_fd)
            return CleanupResult(CleanupStatus.DELETED)
        except FileNotFoundError:
            return CleanupResult(CleanupStatus.ABSENT)
        except PermissionError:
            return CleanupResult(CleanupStatus.UNAVAILABLE)
        except OSError:
            return CleanupResult(CleanupStatus.REJECTED)
        finally:
            if staging_fd is not None:
                os.close(staging_fd)

    def list_orphan_staging(self) -> tuple[str, ...]:
        """Inventory exact regular staging tokens without following links or recursing."""
        staging_fd = self._open_base("staging")
        try:
            names: list[str] = []
            for name in os.listdir(staging_fd):
                if not _STAGING_NAME_RE.fullmatch(name):
                    continue
                try:
                    entry = os.stat(name, dir_fd=staging_fd, follow_symlinks=False)
                except FileNotFoundError:
                    continue
                if stat.S_ISREG(entry.st_mode):
                    names.append(name)
            return tuple(sorted(names))
        finally:
            os.close(staging_fd)
