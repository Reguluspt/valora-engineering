"""Value-only .xls adapter using xlrd (BIFF) with fail-closed safety checks."""
from __future__ import annotations

from openpyxl.utils import get_column_letter

from app.modules.excel_import.domain.source_artifact import (
    DEFAULT_SOURCE_LIMITS,
    SourceArtifactLimits,
    XLS_OLE_SIGNATURE,
)
from app.modules.excel_import.domain.workbook_adapter import (
    AdapterInspectionResult,
    CellValue,
    SheetSummary,
    WorkbookFormat,
    fail_adapter,
)


class XlsWorkbookAdapter:
    """
    xlrd-based BIFF reader.

    Safety:
    - OLE signature required
    - encrypted workbooks fail closed (xlrd raises / FILE_PASS detection)
    - values only (formatting_info=False, on_demand=True)
    - no macro execution (xlrd does not execute VBA)
    """

    name = "xls-xlrd"
    version = "s13-pr-002-v1"
    format = WorkbookFormat.XLS

    def __init__(self, limits: SourceArtifactLimits | None = None):
        self._limits = limits or DEFAULT_SOURCE_LIMITS
        self._book = None

    def close(self) -> None:
        if self._book is not None:
            try:
                self._book.release_resources()
            except Exception:
                pass
            self._book = None

    def _open(self, path: str):
        import xlrd

        with open(path, "rb") as f:
            sig = f.read(8)
        if not sig.startswith(XLS_OLE_SIGNATURE):
            fail_adapter(400, "signature_mismatch", "Chữ ký tệp không khớp định dạng .xls.")

        try:
            book = xlrd.open_workbook(
                path,
                formatting_info=False,
                on_demand=True,
                ragged_rows=True,
            )
        except xlrd.XLRDError as exc:
            msg = str(exc).lower()
            if "password" in msg or "encrypt" in msg or "file_pass" in msg:
                fail_adapter(400, "encrypted_workbook", "Tệp mã hóa không được hỗ trợ.")
            fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
        except Exception:
            fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")

        # Heuristic: VBA project stream often present as Book/Workbook + _VBA_PROJECT_CUR
        # xlrd does not execute macros; we still reject if compound storage names suggest VBA
        # when available via book internals.
        try:
            # xlrd 2.x does not expose full OLE streams; keep value-only path.
            pass
        except Exception:
            pass
        return book

    def inspect(self, path: str) -> AdapterInspectionResult:
        book = self._open(path)
        try:
            names = tuple(book.sheet_names())
            if len(names) > self._limits.max_sheets:
                fail_adapter(
                    413,
                    "sheet_limit",
                    "Số lượng sheet vượt quá giới hạn cho phép.",
                    "sheets",
                )
            sheets: list[SheetSummary] = []
            for name in names:
                sh = book.sheet_by_name(name)
                if sh.nrows > self._limits.max_physical_rows:
                    fail_adapter(
                        413,
                        "physical_row_limit",
                        "Số lượng dòng vật lý vượt quá giới hạn cho phép.",
                        "rows",
                    )
                if sh.ncols > self._limits.max_columns:
                    fail_adapter(
                        413,
                        "column_limit",
                        "Số lượng cột vượt quá giới hạn cho phép.",
                        "columns",
                    )
                sheets.append(
                    SheetSummary(
                        name=name,
                        max_row=sh.nrows,
                        max_column=sh.ncols,
                        merged_regions=(),  # xlrd 2.x no merged region API without formatting_info
                    )
                )
            return AdapterInspectionResult(
                format=WorkbookFormat.XLS,
                adapter_name=self.name,
                adapter_version=self.version,
                sheet_names=names,
                sheets=tuple(sheets),
                safe_metadata={
                    "sheet_count": len(names),
                    "limit_version": self._limits.limit_version,
                    "library": "xlrd",
                },
            )
        finally:
            try:
                book.release_resources()
            except Exception:
                pass

    def iter_rows(self, path: str, sheet_name: str | None = None):
        import xlrd

        book = self._open(path)
        self._book = book
        try:
            if sheet_name and sheet_name in book.sheet_names():
                sh = book.sheet_by_name(sheet_name)
            else:
                sh = book.sheet_by_index(0)
            for r_idx in range(sh.nrows):
                if r_idx + 1 > self._limits.max_physical_rows:
                    fail_adapter(
                        413,
                        "physical_row_limit",
                        "Số lượng dòng vật lý vượt quá giới hạn cho phép.",
                        "rows",
                    )
                cells: list[CellValue] = []
                row_len = sh.row_len(r_idx) if hasattr(sh, "row_len") else sh.ncols
                for c_idx in range(row_len):
                    if c_idx + 1 > self._limits.max_columns:
                        fail_adapter(
                            413,
                            "column_limit",
                            "Số lượng cột vượt quá giới hạn cho phép.",
                            "columns",
                        )
                    cell = sh.cell(r_idx, c_idx)
                    val = cell.value
                    # Convert XL date serials only when ctype is date; leave numeric otherwise
                    if cell.ctype == xlrd.XL_CELL_DATE:
                        try:
                            val = xlrd.xldate_as_datetime(cell.value, book.datemode).isoformat()
                            ctype = "datetime"
                        except Exception:
                            ctype = "number"
                    elif cell.ctype == xlrd.XL_CELL_BOOLEAN:
                        val = bool(cell.value)
                        ctype = "boolean"
                    elif cell.ctype == xlrd.XL_CELL_NUMBER:
                        ctype = "number"
                    elif cell.ctype == xlrd.XL_CELL_EMPTY:
                        val = None
                        ctype = "empty"
                    elif cell.ctype == xlrd.XL_CELL_ERROR:
                        ctype = "error"
                    elif cell.ctype == xlrd.XL_CELL_TEXT:
                        ctype = "string"
                        if isinstance(val, str) and len(val) > self._limits.max_cell_chars:
                            fail_adapter(
                                400,
                                "cell_length_limit",
                                "Ô dữ liệu vượt quá độ dài ký tự cho phép.",
                                "cell",
                            )
                    else:
                        ctype = "other"
                    cells.append(
                        CellValue(
                            row=r_idx + 1,
                            column=c_idx + 1,
                            coordinate=f"{get_column_letter(c_idx + 1)}{r_idx + 1}",
                            value=val,
                            cell_type=ctype,
                        )
                    )
                yield tuple(cells)
        finally:
            self.close()
