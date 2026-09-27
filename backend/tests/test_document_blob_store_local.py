"""Linux-only acceptance tests covering L1-L17 for LocalFilesystemDocumentBlobStore."""
from __future__ import annotations

import asyncio
import errno
import hashlib
import os
import stat
import subprocess
import sys
import threading
import uuid
from collections.abc import AsyncIterable
from concurrent.futures import ThreadPoolExecutor
from functools import wraps
from pathlib import Path
from typing import Any, Callable

import pytest
from pydantic import ValidationError

if os.name != "posix" or not hasattr(os, "link"):
    pytest.skip(
        "LocalFilesystemDocumentBlobStore acceptance tests require Linux/POSIX with hard links; "
        "skipping on non-POSIX platform is not a PASS",
        allow_module_level=True,
    )

from app.modules.document_workspace.domain.document_blob_store import (
    BlobReadStatus,
    ChecksumVerificationStatus,
    CleanupStatus,
    CreateImmutableResult,
    CreateImmutableStatus,
    ObjectObservationStatus,
)
from app.core.config import Settings
from app.modules.document_workspace.infrastructure import (
    local_filesystem_document_blob_store as blob_module,
)
from app.modules.document_workspace.infrastructure.document_blob_store_factory import (
    build_document_blob_store,
)
from app.modules.document_workspace.infrastructure.local_filesystem_document_blob_store import (
    LocalFilesystemConfigurationError,
    LocalFilesystemDocumentBlobStore,
)


@pytest.fixture
def blob_root(tmp_path: Path) -> Path:
    root = tmp_path / "blob_store_root"
    root.mkdir(mode=0o700)
    return root


@pytest.fixture
def store(blob_root: Path) -> LocalFilesystemDocumentBlobStore:
    return LocalFilesystemDocumentBlobStore(root=blob_root)


async def _async_content(data: bytes, *, split_at: int | None = None) -> AsyncIterable[bytes]:
    if split_at is None:
        yield data
        return
    yield data[:split_at]
    yield data[split_at:]


async def _create(
    store: LocalFilesystemDocumentBlobStore,
    *,
    object_key: str,
    data: bytes,
    expected_sha256: str | None = None,
    byte_length: int | None = None,
    content: AsyncIterable[bytes] | None = None,
) -> CreateImmutableResult:
    return await store.create_immutable(
        object_key=object_key,
        content=content if content is not None else _async_content(data),
        byte_length=len(data) if byte_length is None else byte_length,
        expected_sha256=(
            hashlib.sha256(data).hexdigest()
            if expected_sha256 is None
            else expected_sha256
        ),
    )


def _async_test(function: Callable[..., Any]) -> Callable[..., None]:
    """Run one async test without adding a pytest-asyncio dependency."""
    @wraps(function)
    def run(*args: Any, **kwargs: Any) -> None:
        asyncio.run(function(*args, **kwargs))

    return run


@_async_test
async def test_bounded_authoritative_read_returns_only_exact_verified_bytes(
    store: LocalFilesystemDocumentBlobStore,
) -> None:
    key = "org/read-contract/document.docx"
    data = b"bounded-local-authoritative-read"
    assert (await _create(store, object_key=key, data=data)).status == (
        CreateImmutableStatus.CREATED
    )
    matched = await store.read_verified(
        object_key=key,
        expected_sha256=hashlib.sha256(data).hexdigest(),
        expected_byte_length=len(data),
        max_bytes=len(data),
    )
    assert matched.status == BlobReadStatus.MATCH
    assert matched.content == data
    mismatch = await store.read_verified(
        object_key=key,
        expected_sha256="0" * 64,
        expected_byte_length=len(data),
        max_bytes=len(data),
    )
    assert mismatch.status == BlobReadStatus.MISMATCH
    assert mismatch.content is None


def test_local_configuration_fails_closed_for_unsafe_roots(tmp_path: Path) -> None:
    missing = tmp_path / "missing"
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root="relative/root")
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root=missing)

    real_root = tmp_path / "real-root"
    real_root.mkdir(mode=0o700)
    symlink_root = tmp_path / "symlink-root"
    os.symlink(real_root, symlink_root)
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root=symlink_root)

    world_writable = tmp_path / "world-writable"
    world_writable.mkdir(mode=0o777)
    world_writable.chmod(0o777)
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root=world_writable)

    group_writable = tmp_path / "group-writable"
    group_writable.mkdir(mode=0o770)
    group_writable.chmod(0o770)
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root=group_writable)

    repository = tmp_path / "repository"
    repository.mkdir(mode=0o700)
    (repository / ".git").mkdir()
    inside_repository = repository / "document-blobs"
    inside_repository.mkdir(mode=0o700)
    with pytest.raises(LocalFilesystemConfigurationError):
        LocalFilesystemDocumentBlobStore(root=inside_repository)


def test_document_blob_store_factory_requires_local_root(blob_root: Path) -> None:
    fake = build_document_blob_store(Settings(document_blob_provider="fake"))
    assert fake.__class__.__name__ == "InMemoryDocumentBlobStore"
    with pytest.raises(LocalFilesystemConfigurationError):
        build_document_blob_store(
            Settings(document_blob_provider="local", document_blob_root="")
        )
    with pytest.raises(LocalFilesystemConfigurationError):
        build_document_blob_store(
            Settings(valora_env="production", document_blob_provider="fake")
        )
    local = build_document_blob_store(
        Settings(document_blob_provider="local", document_blob_root=str(blob_root))
    )
    assert isinstance(local, LocalFilesystemDocumentBlobStore)
    with pytest.raises(ValidationError):
        Settings(document_blob_provider="unsupported")


# L1: Normal staged write, fsync and atomic create-only publication
@_async_test
async def test_l1_normal_create_staged_write_fsync_and_atomic_publication(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "documents/2026/test_doc.docx"
    data = b"PK\x03\x04 Authoritative document content for L1 test"
    sha256 = hashlib.sha256(data).hexdigest()
    length = len(data)

    result = await _create(store, object_key=key, data=data)

    assert result.status == CreateImmutableStatus.CREATED
    assert result.provider_object_version is not None
    assert ":" in result.provider_object_version

    committed_path = blob_root / "objects" / "documents" / "2026" / "test_doc.docx"
    assert committed_path.is_file()
    assert not committed_path.is_symlink()
    assert committed_path.read_bytes() == data

    file_stat = committed_path.stat()
    assert stat.S_IMODE(file_stat.st_mode) == 0o400
    expected_version = f"{file_stat.st_dev:x}:{file_stat.st_ino:x}"
    assert result.provider_object_version == expected_version

    obs = await store.observe(object_key=key)
    assert obs.status == ObjectObservationStatus.PRESENT
    assert obs.byte_length == length
    assert obs.provider_object_version == expected_version
    assert obs.object_created_at is not None

    ver = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256,
        expected_byte_length=length,
    )
    assert ver.status == ChecksumVerificationStatus.MATCH
    assert ver.observed_sha256 == sha256
    assert ver.observed_byte_length == length

    assert list((blob_root / "staging").iterdir()) == []


# L2: Duplicate key with same SHA-256/length reconciles idempotently
@_async_test
async def test_l2_duplicate_same_checksum_reconciles_idempotently(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "documents/2026/l2_doc.docx"
    data = b"Duplicate same checksum content"
    sha256 = hashlib.sha256(data).hexdigest()
    length = len(data)

    res1 = await _create(store, object_key=key, data=data)
    assert res1.status == CreateImmutableStatus.CREATED
    obs1 = await store.observe(object_key=key)

    res2 = await _create(store, object_key=key, data=data)
    assert res2.status == CreateImmutableStatus.ALREADY_EXISTS

    obs2 = await store.observe(object_key=key)
    assert obs2.status == ObjectObservationStatus.PRESENT
    assert obs2.provider_object_version == obs1.provider_object_version
    assert obs2.byte_length == obs1.byte_length

    ver = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256,
        expected_byte_length=length,
    )
    assert ver.status == ChecksumVerificationStatus.MATCH
    assert list((blob_root / "staging").iterdir()) == []


# L3: Duplicate key with different SHA-256 or length fails closed
@_async_test
async def test_l3_duplicate_different_checksum_or_length_fails_closed(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "documents/2026/l3_doc.docx"
    data_a = b"Original content A"
    sha256_a = hashlib.sha256(data_a).hexdigest()

    res_a = await _create(store, object_key=key, data=data_a)
    assert res_a.status == CreateImmutableStatus.CREATED

    data_b = b"Different content with different length B"
    res_b = await _create(store, object_key=key, data=data_b)
    assert res_b.status == CreateImmutableStatus.REJECTED

    data_c = b"Original content C"
    assert len(data_c) == len(data_a)
    res_c = await _create(store, object_key=key, data=data_c)
    assert res_c.status == CreateImmutableStatus.REJECTED

    res_d = await _create(
        store,
        object_key=key,
        data=data_a,
        byte_length=len(data_a) + 1,
        expected_sha256=sha256_a,
    )
    assert res_d.status == CreateImmutableStatus.REJECTED

    committed_path = blob_root / "objects" / "documents" / "2026" / "l3_doc.docx"
    assert committed_path.read_bytes() == data_a

    ver = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256_a,
        expected_byte_length=len(data_a),
    )
    assert ver.status == ChecksumVerificationStatus.MATCH
    assert list((blob_root / "staging").iterdir()) == []


# L4: Concurrent same-object create yields one final inode/content
def test_l4_concurrent_same_object_create_yields_one_final_content(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "concurrent/same_object.docx"
    data = b"Concurrent same object payload data"
    sha256 = hashlib.sha256(data).hexdigest()
    length = len(data)
    barrier = threading.Barrier(2, timeout=10)

    async def synchronized_content() -> AsyncIterable[bytes]:
        yield data[:10]
        barrier.wait(timeout=10)
        yield data[10:]

    def create() -> CreateImmutableResult:
        return asyncio.run(
            store.create_immutable(
                object_key=key,
                content=synchronized_content(),
                byte_length=length,
                expected_sha256=sha256,
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(create) for _ in range(2)]
        res1, res2 = (future.result(timeout=15) for future in futures)

    statuses = {res1.status, res2.status}
    assert statuses == {CreateImmutableStatus.CREATED, CreateImmutableStatus.ALREADY_EXISTS}

    committed_path = blob_root / "objects" / "concurrent" / "same_object.docx"
    assert committed_path.is_file()
    assert committed_path.read_bytes() == data

    obs = asyncio.run(store.observe(object_key=key))
    assert obs.status == ObjectObservationStatus.PRESENT
    assert obs.byte_length == length

    assert list((blob_root / "staging").iterdir()) == []


# L5: Crash/interruption during staging write leaves no committed partial object
@_async_test
async def test_l5_staging_write_failure_leaves_no_committed_partial_object(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "failures/staging_fail.docx"
    data = b"Incomplete streaming content"

    async def failing_stream() -> AsyncIterable[bytes]:
        yield b"partial header"
        raise OSError(errno.EIO, "Stream connection reset midway")

    res = await store.create_immutable(
        object_key=key,
        content=failing_stream(),
        byte_length=len(data),
        expected_sha256=hashlib.sha256(data).hexdigest(),
    )
    assert res.status == CreateImmutableStatus.UNAVAILABLE

    obs = await store.observe(object_key=key)
    assert obs.status == ObjectObservationStatus.ABSENT

    committed_path = blob_root / "objects" / "failures" / "staging_fail.docx"
    assert not committed_path.exists()
    assert list((blob_root / "staging").iterdir()) == []

    async def invalid_type_stream() -> AsyncIterable[bytes]:
        yield "not bytes chunk"  # type: ignore[misc]

    res2 = await store.create_immutable(
        object_key=key,
        content=invalid_type_stream(),
        byte_length=10,
        expected_sha256="a" * 64,
    )
    assert res2.status == CreateImmutableStatus.REJECTED
    assert (await store.observe(object_key=key)).status == ObjectObservationStatus.ABSENT
    assert not committed_path.exists()
    assert list((blob_root / "staging").iterdir()) == []


# L6: Crash after staging fsync before publish leaves recoverable exact staging orphan only
def test_l6_crash_after_fsync_leaves_only_staging_orphan_and_recovers(
    blob_root: Path,
) -> None:
    child_script = """
import asyncio
import hashlib
import os
import sys

backend_dir = sys.argv[1]
root_dir = sys.argv[2]
key = sys.argv[3]

if backend_dir not in sys.path:
    sys.path.insert(0, backend_dir)

from app.modules.document_workspace.infrastructure import (
    local_filesystem_document_blob_store as blob_module,
)

def crashing_link(*args, **kwargs):
    os._exit(42)

async def main():
    store = blob_module.LocalFilesystemDocumentBlobStore(root=root_dir)
    blob_module.os.link = crashing_link
    data = b"Crash after fsync before publish"
    async def content():
        yield data
    await store.create_immutable(
        object_key=key,
        content=content(),
        byte_length=len(data),
        expected_sha256=hashlib.sha256(data).hexdigest(),
    )

asyncio.run(main())
"""
    backend_path = str(Path(blob_module.__file__).resolve().parents[3])
    key = "crash/orphan_recovery.docx"

    proc = subprocess.run(
        [sys.executable, "-c", child_script, backend_path, str(blob_root), key],
        capture_output=True,
        text=True,
        timeout=15,
    )
    assert proc.returncode == 42

    store = LocalFilesystemDocumentBlobStore(root=blob_root)

    obs = asyncio.run(store.observe(object_key=key))
    assert obs.status == ObjectObservationStatus.ABSENT

    staging_orphans = store.list_orphan_staging()
    assert len(staging_orphans) == 1
    orphan_name = staging_orphans[0]

    cleanup_res = store.cleanup_orphan_staging(staging_name=orphan_name)
    assert cleanup_res.status == CleanupStatus.DELETED
    assert store.list_orphan_staging() == ()

    data = b"Crash after fsync before publish"
    create_res = asyncio.run(_create(store, object_key=key, data=data))
    assert create_res.status == CreateImmutableStatus.CREATED

    ver = asyncio.run(
        store.verify_checksum(
            object_key=key,
            expected_sha256=hashlib.sha256(data).hexdigest(),
            expected_byte_length=len(data),
        )
    )
    assert ver.status == ChecksumVerificationStatus.MATCH


# L7: Collision at atomic publish observes/verifies instead of overwriting
@_async_test
async def test_l7_publish_collision_reconciles_instead_of_overwriting(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "collision/publish_target.docx"
    data_original = b"Original publication bytes"
    sha256_original = hashlib.sha256(data_original).hexdigest()

    res1 = await _create(store, object_key=key, data=data_original)
    assert res1.status == CreateImmutableStatus.CREATED

    committed_path = blob_root / "objects" / "collision" / "publish_target.docx"
    original_stat = committed_path.stat()

    res_same = await _create(store, object_key=key, data=data_original)
    assert res_same.status == CreateImmutableStatus.ALREADY_EXISTS
    assert committed_path.stat().st_ino == original_stat.st_ino
    assert committed_path.read_bytes() == data_original

    data_different = b"Conflicting different bytes at publish"
    res_diff = await _create(store, object_key=key, data=data_different)
    assert res_diff.status == CreateImmutableStatus.REJECTED
    assert committed_path.stat().st_ino == original_stat.st_ino
    assert committed_path.read_bytes() == data_original

    ver = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256_original,
        expected_byte_length=len(data_original),
    )
    assert ver.status == ChecksumVerificationStatus.MATCH
    assert list((blob_root / "staging").iterdir()) == []


# L8: Committed file SHA-256 corruption is detected by a full read
@_async_test
async def test_l8_committed_file_checksum_corruption_detected_by_full_read(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "integrity/corrupt_sha.docx"
    data = b"Intact content before bit flip"
    sha256_original = hashlib.sha256(data).hexdigest()

    res = await _create(store, object_key=key, data=data)
    assert res.status == CreateImmutableStatus.CREATED

    committed_path = blob_root / "objects" / "integrity" / "corrupt_sha.docx"
    committed_path.chmod(0o600)
    raw = bytearray(committed_path.read_bytes())
    raw[0] ^= 0xFF
    committed_path.write_bytes(bytes(raw))
    committed_path.chmod(0o400)

    ver = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256_original,
        expected_byte_length=len(data),
    )
    assert ver.status == ChecksumVerificationStatus.MISMATCH
    assert ver.observed_sha256 == hashlib.sha256(raw).hexdigest()
    assert ver.observed_sha256 != sha256_original
    assert ver.observed_byte_length == len(data)


# L9: Committed file byte-length mismatch is detected by a full read
@_async_test
async def test_l9_committed_file_byte_length_mismatch_detected_by_full_read(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "integrity/length_mismatch.docx"
    data = b"Content to test length divergence"
    sha256_original = hashlib.sha256(data).hexdigest()

    res = await _create(store, object_key=key, data=data)
    assert res.status == CreateImmutableStatus.CREATED

    committed_path = blob_root / "objects" / "integrity" / "length_mismatch.docx"

    committed_path.chmod(0o600)
    truncated = data[:-4]
    committed_path.write_bytes(truncated)
    committed_path.chmod(0o400)

    ver_trunc = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256_original,
        expected_byte_length=len(data),
    )
    assert ver_trunc.status == ChecksumVerificationStatus.MISMATCH
    assert ver_trunc.observed_byte_length == len(truncated)

    committed_path.chmod(0o600)
    appended = data + b"unexpected trailing bytes"
    committed_path.write_bytes(appended)
    committed_path.chmod(0o400)

    ver_app = await store.verify_checksum(
        object_key=key,
        expected_sha256=sha256_original,
        expected_byte_length=len(data),
    )
    assert ver_app.status == ChecksumVerificationStatus.MISMATCH
    assert ver_app.observed_byte_length == len(appended)


# L10: Exact staging orphan cleanup stays inside staging
def test_l10_exact_staging_orphan_cleanup_stays_inside_staging(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    orphan_name = f"{uuid.uuid4().hex}.stage"
    orphan_path = blob_root / "staging" / orphan_name
    orphan_path.write_bytes(b"staging orphan bytes")
    assert store.list_orphan_staging() == (orphan_name,)

    res_del = store.cleanup_orphan_staging(staging_name=orphan_name)
    assert res_del.status == CleanupStatus.DELETED
    assert not orphan_path.exists()
    assert store.list_orphan_staging() == ()

    res_abs = store.cleanup_orphan_staging(staging_name=orphan_name)
    assert res_abs.status == CleanupStatus.ABSENT

    invalid_names = [
        "not_stage.txt",
        "../objects/escape.stage",
        "",
        "12345.stage",
        "a" * 31 + ".stage",
        "a" * 33 + ".stage",
        f"{uuid.uuid4().hex}.stage/child",
        "0123456789abcdef0123456789abcdef.stage2",
    ]
    for invalid in invalid_names:
        assert store.cleanup_orphan_staging(staging_name=invalid).status == CleanupStatus.REJECTED

    dir_orphan = f"{uuid.uuid4().hex}.stage"
    (blob_root / "staging" / dir_orphan).mkdir()
    try:
        assert dir_orphan not in store.list_orphan_staging()
        assert store.cleanup_orphan_staging(staging_name=dir_orphan).status == CleanupStatus.REJECTED
    finally:
        (blob_root / "staging" / dir_orphan).rmdir()

    symlink_orphan = f"{uuid.uuid4().hex}.stage"
    outside = blob_root.parent / "outside-staging-target"
    outside.write_bytes(b"must remain")
    os.symlink(outside, blob_root / "staging" / symlink_orphan)
    try:
        assert symlink_orphan not in store.list_orphan_staging()
    finally:
        (blob_root / "staging" / symlink_orphan).unlink()
    assert outside.read_bytes() == b"must remain"


# L11: Path traversal, absolute/backslash/control input is rejected
@_async_test
async def test_l11_path_traversal_absolute_backslash_and_control_input_rejected(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    invalid_keys = [
        "../escape.docx",
        "foo/../../escape.docx",
        "foo/../bar.docx",
        "/absolute/path.docx",
        "/escape.docx",
        "foo\\bar.docx",
        "\\escape.docx",
        "",
        "/",
        "foo//bar.docx",
        "foo/",
        "/foo",
        "foo/./bar.docx",
        "foo\x00bar.docx",
        "foo\nbar.docx",
        "foo\rbar.docx",
        "foo\tbar.docx",
        "-leading-dash.docx",
        "foo/-dash/bar.docx",
        ".hidden.docx",
    ]

    dummy_data = b"dummy"
    dummy_sha = hashlib.sha256(dummy_data).hexdigest()

    for invalid_key in invalid_keys:
        res_create = await _create(
            store,
            object_key=invalid_key,
            data=dummy_data,
        )
        assert res_create.status == CreateImmutableStatus.REJECTED

        obs = await store.observe(object_key=invalid_key)
        assert obs.status == ObjectObservationStatus.AMBIGUOUS

        ver = await store.verify_checksum(
            object_key=invalid_key,
            expected_sha256=dummy_sha,
            expected_byte_length=len(dummy_data),
        )
        assert ver.status == ChecksumVerificationStatus.UNVERIFIABLE

        clean = await store.delete_uncommitted_or_expire(
            object_key=invalid_key,
            expected_sha256=dummy_sha,
        )
        assert clean.status == CleanupStatus.REJECTED

    assert list((blob_root / "objects").iterdir()) == []


# L12: Symlink escape and concurrent symlink substitution are rejected
@_async_test
async def test_l12_symlink_escape_and_substitution_rejected(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    outside_dir = blob_root.parent / "outside_dir"
    outside_dir.mkdir(mode=0o700, exist_ok=True)
    symlink_dir = blob_root / "objects" / "symlink_dir"
    os.symlink(outside_dir, symlink_dir)

    res_create = await _create(
        store,
        object_key="symlink_dir/escape.docx",
        data=b"attempt escape",
    )
    assert res_create.status == CreateImmutableStatus.UNAVAILABLE
    assert list(outside_dir.iterdir()) == []

    outside_file = blob_root.parent / "outside_file.docx"
    outside_file.write_bytes(b"authoritative outside bytes")
    outside_sha = hashlib.sha256(b"authoritative outside bytes").hexdigest()
    symlink_file = blob_root / "objects" / "symlink_file.docx"
    os.symlink(outside_file, symlink_file)

    obs = await store.observe(object_key="symlink_file.docx")
    assert obs.status == ObjectObservationStatus.AMBIGUOUS

    ver = await store.verify_checksum(
        object_key="symlink_file.docx",
        expected_sha256=outside_sha,
        expected_byte_length=len(b"authoritative outside bytes"),
    )
    assert ver.status == ChecksumVerificationStatus.UNVERIFIABLE

    clean = await store.delete_uncommitted_or_expire(
        object_key="symlink_file.docx",
        expected_sha256=outside_sha,
    )
    assert clean.status == CleanupStatus.UNAVAILABLE

    assert outside_file.exists()
    assert outside_file.read_bytes() == b"authoritative outside bytes"


# L13: Permission denied fails closed under every runtime user
@_async_test
async def test_l13_permission_denied_root_fails_closed(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    real_open = blob_module.os.open

    def deny_staging_create(path: Any, flags: int, *args: Any, **kwargs: Any) -> int:
        if isinstance(path, str) and path.endswith(".stage") and flags & os.O_CREAT:
            raise PermissionError(errno.EACCES, "permission denied")
        return real_open(path, flags, *args, **kwargs)

    with pytest.MonkeyPatch.context() as patch:
        patch.setattr(blob_module.os, "open", deny_staging_create)
        res = await _create(
            store,
            object_key="perms/doc.docx",
            data=b"permission denied test",
        )
    assert res.status == CreateImmutableStatus.UNAVAILABLE


# L13: real kernel DAC proof, executed separately as a non-root container user
@_async_test
async def test_l13_nonroot_read_only_file_fails_closed(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    if os.geteuid() == 0:
        pytest.skip("real read-only DAC proof requires a non-root Linux user")

    key = "perms/read_only_file.docx"
    data = b"Pre-created read only file"
    sha256 = hashlib.sha256(data).hexdigest()

    res_create = await _create(store, object_key=key, data=data)
    assert res_create.status == CreateImmutableStatus.CREATED

    committed_path = blob_root / "objects" / "perms" / "read_only_file.docx"
    committed_path.chmod(0o000)
    try:
        obs = await store.observe(object_key=key)
        assert obs.status == ObjectObservationStatus.UNAVAILABLE

        ver = await store.verify_checksum(
            object_key=key,
            expected_sha256=sha256,
            expected_byte_length=len(data),
        )
        assert ver.status == ChecksumVerificationStatus.UNAVAILABLE

        clean = await store.delete_uncommitted_or_expire(
            object_key=key,
            expected_sha256=sha256,
        )
        assert clean.status == CleanupStatus.UNAVAILABLE
    finally:
        committed_path.chmod(0o400)


# L14: Concurrent different-content writers never overwrite the winner
def test_l14_concurrent_different_content_never_overwrites_winner(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    key = "concurrent/competing_writers.docx"
    data_a = b"Payload A from writer 1"
    sha256_a = hashlib.sha256(data_a).hexdigest()
    data_b = b"Payload B from writer 2 with different length and content"
    sha256_b = hashlib.sha256(data_b).hexdigest()
    barrier = threading.Barrier(2, timeout=10)

    async def synchronized_content(data: bytes) -> AsyncIterable[bytes]:
        yield data[:5]
        barrier.wait(timeout=10)
        yield data[5:]

    def create(data: bytes, checksum: str) -> CreateImmutableResult:
        return asyncio.run(
            store.create_immutable(
                object_key=key,
                content=synchronized_content(data),
                byte_length=len(data),
                expected_sha256=checksum,
            )
        )

    with ThreadPoolExecutor(max_workers=2) as executor:
        future_a = executor.submit(create, data_a, sha256_a)
        future_b = executor.submit(create, data_b, sha256_b)
        res_a = future_a.result(timeout=15)
        res_b = future_b.result(timeout=15)

    results = [res_a, res_b]
    created = [r for r in results if r.status == CreateImmutableStatus.CREATED]
    rejected = [r for r in results if r.status == CreateImmutableStatus.REJECTED]
    assert len(created) == 1
    assert len(rejected) == 1

    committed_path = blob_root / "objects" / "concurrent" / "competing_writers.docx"
    stored_bytes = committed_path.read_bytes()

    if res_a.status == CreateImmutableStatus.CREATED:
        assert stored_bytes == data_a
        ver = asyncio.run(
            store.verify_checksum(
                object_key=key,
                expected_sha256=sha256_a,
                expected_byte_length=len(data_a),
            )
        )
        assert ver.status == ChecksumVerificationStatus.MATCH
    else:
        assert stored_bytes == data_b
        ver = asyncio.run(
            store.verify_checksum(
                object_key=key,
                expected_sha256=sha256_b,
                expected_byte_length=len(data_b),
            )
        )
        assert ver.status == ChecksumVerificationStatus.MATCH

    assert list((blob_root / "staging").iterdir()) == []


# L15: Restart/recovery returns compatible existing bytes without a second object
@_async_test
async def test_l15_restart_recovery_idempotence_returns_compatible_existing_bytes(
    blob_root: Path,
) -> None:
    store1 = LocalFilesystemDocumentBlobStore(root=blob_root)
    key = "restart/persisted_doc.docx"
    data = b"Durable document bytes across restart"
    sha256 = hashlib.sha256(data).hexdigest()
    length = len(data)

    res1 = await _create(store1, object_key=key, data=data)
    assert res1.status == CreateImmutableStatus.CREATED
    obs1 = await store1.observe(object_key=key)
    assert obs1.status == ObjectObservationStatus.PRESENT

    store2 = LocalFilesystemDocumentBlobStore(root=blob_root)

    res2 = await _create(store2, object_key=key, data=data)
    assert res2.status == CreateImmutableStatus.ALREADY_EXISTS

    obs2 = await store2.observe(object_key=key)
    assert obs2.status == ObjectObservationStatus.PRESENT
    assert obs2.provider_object_version == obs1.provider_object_version
    assert obs2.byte_length == obs1.byte_length

    ver2 = await store2.verify_checksum(
        object_key=key,
        expected_sha256=sha256,
        expected_byte_length=length,
    )
    assert ver2.status == ChecksumVerificationStatus.MATCH
    assert ver2.observed_sha256 == sha256
    assert ver2.observed_byte_length == length


# L16: Cleanup cannot escape root or follow a symlink
@_async_test
async def test_l16_cleanup_cannot_escape_root_or_follow_symlink(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
) -> None:
    outside_dir = blob_root.parent / "outside_cleanup_dir"
    outside_dir.mkdir(mode=0o700, exist_ok=True)
    target_file = outside_dir / "protected.docx"
    target_file.write_bytes(b"must not be deleted")
    target_sha = hashlib.sha256(b"must not be deleted").hexdigest()

    res_trav = await store.delete_uncommitted_or_expire(
        object_key="../outside_cleanup_dir/protected.docx",
        expected_sha256=target_sha,
    )
    assert res_trav.status == CleanupStatus.REJECTED
    assert target_file.exists()

    symlink_clean = blob_root / "objects" / "symlink_clean.docx"
    os.symlink(target_file, symlink_clean)
    res_symlink = await store.delete_uncommitted_or_expire(
        object_key="symlink_clean.docx",
        expected_sha256=target_sha,
    )
    assert res_symlink.status == CleanupStatus.UNAVAILABLE
    assert target_file.exists()

    res_orphan_trav = store.cleanup_orphan_staging(
        staging_name="../outside_cleanup_dir/protected.docx",
    )
    assert res_orphan_trav.status == CleanupStatus.REJECTED
    assert target_file.exists()

    valid_staging_name = f"{'a' * 32}.stage"
    staging_symlink = blob_root / "staging" / valid_staging_name
    os.symlink(target_file, staging_symlink)
    res_orphan_symlink = store.cleanup_orphan_staging(staging_name=valid_staging_name)
    assert res_orphan_symlink.status == CleanupStatus.REJECTED
    assert target_file.exists()
    assert target_file.read_bytes() == b"must not be deleted"


# L17: Injected disk-full/write/fsync failure creates no committed partial object where practical
@_async_test
async def test_l17_enospc_write_and_fsync_simulation_creates_no_committed_partial(
    store: LocalFilesystemDocumentBlobStore,
    blob_root: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    data = b"Disk full and I/O error simulation payload"

    def fail_write_enospc(fd: int, view: memoryview) -> int:
        raise OSError(errno.ENOSPC, "No space left on device")

    monkeypatch.setattr(blob_module.os, "write", fail_write_enospc)
    key_enospc = "sim/enospc_failure.docx"
    res_enospc = await _create(store, object_key=key_enospc, data=data)
    assert res_enospc.status == CreateImmutableStatus.UNAVAILABLE
    assert (await store.observe(object_key=key_enospc)).status == ObjectObservationStatus.ABSENT
    assert not (blob_root / "objects" / "sim" / "enospc_failure.docx").exists()
    assert list((blob_root / "staging").iterdir()) == []

    def fail_write_eio(fd: int, view: memoryview) -> int:
        raise OSError(errno.EIO, "I/O error during write")

    monkeypatch.setattr(blob_module.os, "write", fail_write_eio)
    key_eio = "sim/eio_failure.docx"
    res_eio = await _create(store, object_key=key_eio, data=data)
    assert res_eio.status == CreateImmutableStatus.UNAVAILABLE
    assert (await store.observe(object_key=key_eio)).status == ObjectObservationStatus.ABSENT
    assert not (blob_root / "objects" / "sim" / "eio_failure.docx").exists()
    assert list((blob_root / "staging").iterdir()) == []

    monkeypatch.undo()

    def fail_fsync_eio(fd: int) -> None:
        raise OSError(errno.EIO, "I/O error during fsync")

    monkeypatch.setattr(blob_module.os, "fsync", fail_fsync_eio)
    key_fsync = "sim/fsync_failure.docx"
    res_fsync = await _create(store, object_key=key_fsync, data=data)
    assert res_fsync.status == CreateImmutableStatus.UNAVAILABLE
    assert (await store.observe(object_key=key_fsync)).status == ObjectObservationStatus.ABSENT
    assert not (blob_root / "objects" / "sim" / "fsync_failure.docx").exists()
