import re
import os
import struct
import zipfile
import tempfile

import openpyxl
from openpyxl.utils import get_column_letter
from fastapi import UploadFile

from app.modules.excel_import.domain import (
    DEFAULT_LIMITS,
    ExcelImportLimits,
    ACCEPTED_EXTENSIONS,
    REQUIRED_ZIP_PARTS,
    FORBIDDEN_ZIP_PARTS,
    EXTERNAL_LINK_PATHS,
    COLUMN_ALIASES,
)


# ── error taxonomy ──────────────────────────────────────────────────────────
class ParseError(Exception):
    def __init__(self, status: int, error_code: str, detail: str, limit_category: str | None = None):
        self.status = status
        self.error_code = error_code
        self.detail = detail
        self.limit_category = limit_category
        super().__init__(detail)


def _fail(status: int, error_code: str, detail: str, limit_category: str | None = None):
    raise ParseError(status, error_code, detail, limit_category)


# ── ZIP path validation ─────────────────────────────────────────────────────
_UNSAFE_CHARS = {"\x00"}
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")


def _is_unsafe_zip_path(path: str) -> bool:
    if any(c in path for c in _UNSAFE_CHARS):
        return True
    path = path.replace("\\", "/")
    if path.startswith("/"):
        return True
    if _WINDOWS_DRIVE.match(path):
        return True
    if path.startswith("//"):
        return True
    parts = path.split("/")
    if any(p == ".." for p in parts):
        return True
    return False


def _validate_zip(file_obj, limits: ExcelImportLimits):
    try:
        zf = zipfile.ZipFile(file_obj)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, struct.error):
        _fail(400, "invalid_xlsx", "Tệp Excel không hợp lệ. Tệp không phải là định dạng XLSX hợp lệ.")

    with zf:
        infos = zf.infolist()
        if len(infos) > limits.max_zip_entries:
            _fail(413, "zip_entry_limit", "Tệp Excel có quá nhiều thành phần bên trong.", limit_category="zip_entries")

        total_uncompressed = sum(info.file_size for info in infos)
        if total_uncompressed > limits.max_uncompressed_zip_bytes:
            _fail(413, "zip_expansion_limit", "Kích thước giải nén của tệp Excel vượt quá giới hạn cho phép.", limit_category="zip_size")

        names = {info.filename for info in infos}
        for part in REQUIRED_ZIP_PARTS:
            if part not in names:
                _fail(400, "invalid_xlsx", "Tệp Excel không hợp lệ. Thiếu thành phần cấu trúc XLSX bắt buộc.")

        for info in infos:
            fn = info.filename
            if _is_unsafe_zip_path(fn):
                _fail(400, "unsafe_zip_path", "Tệp Excel chứa đường dẫn không an toàn.")
            if info.flag_bits & 0x1:
                _fail(400, "encrypted_archive", "Tệp Excel được mã hóa không được hỗ trợ.")
            if fn in FORBIDDEN_ZIP_PARTS:
                _fail(400, "macro_not_allowed", "Tệp Excel chứa macro VBA không được hỗ trợ.")
            if any(fn.startswith(prefix) for prefix in EXTERNAL_LINK_PATHS):
                _fail(400, "external_link_not_allowed", "Tệp Excel chứa liên kết ngoài không được hỗ trợ.")

    file_obj.seek(0)


# ── bounded file copy ───────────────────────────────────────────────────────
def _copy_upload_to_spool(file: UploadFile, limits: ExcelImportLimits):
    spool = tempfile.SpooledTemporaryFile(max_size=min(limits.max_upload_bytes, 1024 * 1024))
    total = 0
    while True:
        chunk = file.file.read(limits.read_chunk_size)
        if not chunk:
            break
        total += len(chunk)
        if total > limits.max_upload_bytes:
            spool.close()
            _fail(413, "upload_too_large", "Tệp tải lên vượt quá kích thước cho phép.", limit_category="file_size")
        spool.write(chunk)
    spool.seek(0)
    return spool


# ── main entry point ────────────────────────────────────────────────────────
def parse_workbook(
    file: UploadFile,
    source_sheet_name: str | None,
    limits: ExcelImportLimits | None = None,
) -> list[dict]:
    limits = limits or DEFAULT_LIMITS

    # 1. extension
    filename = file.filename or "import.xlsx"
    ext_idx = filename.rfind(".")
    ext = filename[ext_idx:] if ext_idx >= 0 else ""
    if ext.lower() not in ACCEPTED_EXTENSIONS:
        _fail(400, "unsupported_extension", "Định dạng tệp không được hỗ trợ. Vui lòng tải lên tệp .xlsx")
    sanitized_filename = os.path.basename(filename)

    # 2. enforce Content-Length if present
    content_length = file.size
    if content_length is not None and content_length < 0:
        _fail(400, "request_too_large", "Kích thước yêu cầu không hợp lệ.", limit_category="request_size")
    if content_length is not None and content_length > limits.max_request_bytes:
        _fail(413, "request_too_large", "Tệp tải lên vượt quá kích thước cho phép của yêu cầu.", limit_category="request_size")

    # 3. bounded copy into spooled file
    spool = _copy_upload_to_spool(file, limits)
    try:
        # 4. ZIP validation
        _validate_zip(spool, limits)
        # 5. openpyxl — feed the spool directly
        try:
            wb = openpyxl.load_workbook(
                spool, data_only=True, read_only=True, keep_links=False, keep_vba=False
            )
        except Exception:
            _fail(400, "invalid_xlsx", "Không thể đọc tệp Excel.")

        try:
            sheet_name = _resolve_sheet(wb, source_sheet_name)
            ws = wb[sheet_name]
            headers, header_row_idx = _find_headers(ws, limits)
            mapping = _map_columns(headers)
            staging_rows = _parse_rows(ws, headers, header_row_idx, mapping, limits)
        finally:
            wb.close()
    finally:
        spool.close()

    return staging_rows, sanitized_filename, sheet_name, len(headers)


def _resolve_sheet(wb: openpyxl.Workbook, requested: str | None) -> str:
    if requested:
        if requested in wb.sheetnames:
            return requested
        _fail(400, "sheet_not_found", f"Trang tính '{requested}' không tồn tại trong tệp Excel.")
    if not wb.sheetnames:
        _fail(400, "invalid_xlsx", "Tệp Excel không chứa trang tính nào.")
    return wb.sheetnames[0]


def _find_headers(ws, limits: ExcelImportLimits):
    for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if r_idx >= limits.max_header_search_rows:
            _fail(400, "header_not_found", "Không tìm thấy dòng tiêu đề.")
        if any(cell is not None for cell in row):
            headers = [str(cell) if cell is not None else "" for cell in row]
            if len(headers) > limits.max_columns:
                _fail(400, "column_limit", "Tệp Excel có quá nhiều cột.", limit_category="columns")
            return headers, r_idx
    _fail(400, "header_not_found", "Tệp Excel trống hoặc không chứa dòng tiêu đề.")


def _normalize(h: str) -> str:
    if not h:
        return ""
    return re.sub(r"[\s\-]+", "_", str(h).strip().lower())


def _map_columns(headers: list[str]) -> dict:
    mapping: dict[str, int] = {}
    for i, h in enumerate(headers):
        n = _normalize(h)
        if not n:
            continue
        for target_key, alias_list in COLUMN_ALIASES.items():
            if target_key in mapping:
                continue
            if n in alias_list:
                mapping[target_key] = i
                break
    return mapping


def _build_cells(headers: list[str], row: tuple) -> list[dict]:
    cells = []
    actual = max(len(headers), len(row))
    for ci in range(actual):
        cells.append({
            "column_index": ci + 1,
            "column_letter": get_column_letter(ci + 1),
            "header": str(headers[ci]) if ci < len(headers) and headers[ci] else "",
            "value": str(row[ci]) if ci < len(row) and row[ci] is not None else "",
        })
    return cells


def _parse_rows(ws, headers: list[str], header_row_idx: int, mapping: dict, limits: ExcelImportLimits) -> list[dict]:
    rows_out = []
    data_count = 0
    for r_idx, row in enumerate(ws.iter_rows(values_only=True)):
        if r_idx <= header_row_idx:
            continue
        if r_idx >= limits.max_physical_rows:
            _fail(413, "physical_row_limit", "Tệp Excel có quá nhiều dòng.", limit_category="rows")

        if not any(cell is not None for cell in row):
            continue

        if data_count >= limits.max_data_rows:
            _fail(413, "data_row_limit",
                  f"Tệp Excel vượt quá {limits.max_data_rows} dòng dữ liệu. Toàn bộ tệp bị từ chối.",
                  limit_category="rows")

        if len(row) > limits.max_columns:
            _fail(400, "column_limit", "Tệp Excel có dòng vượt quá số cột cho phép.", limit_category="columns")

        row_len = 0
        for cell in row:
            if cell is not None:
                s = str(cell)
                row_len += len(s)
                if len(s) > limits.max_cell_chars:
                    _fail(400, "cell_length_limit", "Ô dữ liệu quá dài.")
        if row_len > limits.max_row_chars:
            _fail(400, "row_length_limit", "Dòng dữ liệu quá lớn.")

        cells = _build_cells(headers, row)

        mapped = {}
        proposed: dict[str, str] = {}
        for target_key, col_idx in mapping.items():
            if col_idx < len(row):
                val = str(row[col_idx]) if row[col_idx] is not None else ""
                mapped[target_key] = val
                proposed[target_key] = val

        rows_out.append({
            "source_row_number": r_idx + 1,
            "raw_cells": cells,
            "mapped_values": mapped,
            "proposed_asset_name": proposed.get("proposed_asset_name"),
            "proposed_description": proposed.get("proposed_description"),
            "proposed_quantity": proposed.get("proposed_quantity"),
            "proposed_unit": proposed.get("proposed_unit"),
            "proposed_raw_price": proposed.get("proposed_raw_price"),
            "proposed_currency": proposed.get("proposed_currency"),
            "proposed_appraised_unit_price": proposed.get("proposed_appraised_unit_price"),
        })
        data_count += 1

    return rows_out
