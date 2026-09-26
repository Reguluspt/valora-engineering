"""Validated runtime selection for the narrow document blob-store port."""
from __future__ import annotations

from app.core.config import Settings
from app.modules.document_workspace.domain.document_blob_store import (
    DocumentBlobStore,
    InMemoryDocumentBlobStore,
)
from app.modules.document_workspace.infrastructure.local_filesystem_document_blob_store import (
    LocalFilesystemConfigurationError,
    LocalFilesystemDocumentBlobStore,
)


def build_document_blob_store(settings: Settings) -> DocumentBlobStore:
    if settings.document_blob_provider == "fake":
        if settings.valora_env.strip().lower() not in {"local", "development", "test"}:
            raise LocalFilesystemConfigurationError(
                "the fake document blob provider is restricted to development and tests"
            )
        return InMemoryDocumentBlobStore()
    root = settings.document_blob_root.strip()
    if not root:
        raise LocalFilesystemConfigurationError(
            "DOCUMENT_BLOB_ROOT is required when DOCUMENT_BLOB_PROVIDER=local"
        )
    return LocalFilesystemDocumentBlobStore(root=root)
