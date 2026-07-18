"""Limits and constants for ImportSourceArtifact intake (S13-PR-002)."""
from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class SourceArtifactState(str, Enum):
    PENDING = "pending"
    AVAILABLE = "available"
    FAILED = "failed"
    ORPHANED = "orphaned"


# Allowed transitions (fail-closed otherwise).
# Successful available history is terminal — never orphan/delete content identity.
VALID_TRANSITIONS: dict[SourceArtifactState, frozenset[SourceArtifactState]] = {
    SourceArtifactState.PENDING: frozenset(
        {
            SourceArtifactState.AVAILABLE,
            SourceArtifactState.FAILED,
            SourceArtifactState.ORPHANED,
        }
    ),
    SourceArtifactState.AVAILABLE: frozenset(),
    SourceArtifactState.FAILED: frozenset({SourceArtifactState.ORPHANED}),
    SourceArtifactState.ORPHANED: frozenset(),
}


@dataclass(frozen=True)
class SourceArtifactLimits:
    max_upload_bytes: int = 10 * 1024 * 1024
    max_request_bytes: int = 12 * 1024 * 1024
    read_chunk_size: int = 64 * 1024
    max_zip_entries: int = 2048
    max_uncompressed_zip_bytes: int = 100 * 1024 * 1024
    max_sheets: int = 50
    max_physical_rows: int = 5100
    max_columns: int = 100
    max_cell_chars: int = 10000
    max_row_chars: int = 500_000
    max_total_cells: int = 5100 * 100
    max_merged_regions: int = 5000
    max_merged_regions_per_sheet: int = 2000
    spool_max_size: int = 1024 * 1024
    reconcilers_max_items: int = 50
    orphan_retention_seconds: int = 3600

    @property
    def limit_version(self) -> str:
        return (
            f"s13-pr-002c-rows{self.max_physical_rows}-cols{self.max_columns}"
            f"-cells{self.max_total_cells}"
        )


DEFAULT_SOURCE_LIMITS = SourceArtifactLimits()

SOURCE_ACCEPTED_EXTENSIONS = frozenset({".xlsx", ".xls"})
SOURCE_DETECTED_FORMATS = frozenset({"xlsx", "xls"})
SOURCE_STATES = frozenset({"pending", "available", "failed", "orphaned"})

# OLE compound document signature (classic .xls)
XLS_OLE_SIGNATURE = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
# ZIP / OOXML signature
XLSX_ZIP_SIGNATURE = b"PK"
