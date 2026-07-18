"""Neutral WorkbookAdapter contract for Adaptive Intake v2 source inspection."""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Iterator, Protocol, Sequence


class WorkbookFormat(str, Enum):
    XLSX = "xlsx"
    XLS = "xls"


@dataclass(frozen=True)
class MergedRegion:
    min_row: int
    min_col: int
    max_row: int
    max_col: int


@dataclass(frozen=True)
class CellValue:
    """Value-only cell with coordinate identity (never header-keyed)."""

    row: int  # 1-based
    column: int  # 1-based
    coordinate: str
    value: Any
    cell_type: str  # string|number|boolean|datetime|empty|error|other


@dataclass(frozen=True)
class SheetSummary:
    name: str
    max_row: int
    max_column: int
    merged_regions: tuple[MergedRegion, ...] = ()


@dataclass(frozen=True)
class AdapterInspectionResult:
    format: WorkbookFormat
    adapter_name: str
    adapter_version: str
    sheet_names: tuple[str, ...]
    sheets: tuple[SheetSummary, ...]
    safe_metadata: dict[str, Any] = field(default_factory=dict)


class WorkbookAdapter(Protocol):
    name: str
    version: str
    format: WorkbookFormat

    def inspect(self, path: str) -> AdapterInspectionResult:
        """Fail-closed structural inspection without semantic mapping."""
        ...

    def iter_rows(
        self, path: str, sheet_name: str | None = None
    ) -> Iterator[Sequence[CellValue]]:
        """Yield value-only cells by position. Caller must exhaust or close adapter resources."""
        ...

    def close(self) -> None:
        ...


class AdapterError(Exception):
    def __init__(
        self,
        status: int,
        error_code: str,
        detail: str,
        limit_category: str | None = None,
    ):
        self.status = status
        self.error_code = error_code
        self.detail = detail
        self.limit_category = limit_category
        super().__init__(detail)


def fail_adapter(
    status: int,
    error_code: str,
    detail: str,
    limit_category: str | None = None,
) -> None:
    raise AdapterError(status, error_code, detail, limit_category)
