import re, os, struct, zipfile, tempfile
import openpyxl
from openpyxl.utils import get_column_letter
from fastapi import UploadFile

from app.modules.excel_import.domain import (
    DEFAULT_LIMITS, ExcelImportLimits, ACCEPTED_EXTENSIONS,
    REQUIRED_ZIP_PARTS, FORBIDDEN_ZIP_PARTS, EXTERNAL_LINK_PATHS, COLUMN_ALIASES,
)

class ParseError(Exception):
    def __init__(self, status, error_code, detail, limit_category=None):
        self.status, self.error_code, self.detail, self.limit_category = status, error_code, detail, limit_category
        super().__init__(detail)

def _fail(status, error_code, detail, limit_category=None):
    raise ParseError(status, error_code, detail, limit_category)

_UNSAFE_CHARS = {"\x00"}
_WINDOWS_DRIVE = re.compile(r"^[a-zA-Z]:")

def _is_unsafe_zip_path(path):
    if any(c in path for c in _UNSAFE_CHARS): return True
    path = path.replace("\\", "/")
    if path.startswith("/"): return True
    if _WINDOWS_DRIVE.match(path): return True
    if path.startswith("//"): return True
    if any(p == ".." for p in path.split("/")): return True
    return False

def sanitize_filename(fn):
    fn = fn.replace("\\", "/")
    fn = os.path.basename(fn)
    fn = "".join(c for c in fn if c.isprintable() and c not in "\x00\x01\x02\x03\x04\x05\x06\x07\x08\x0b\x0c\x0e\x0f")
    return fn or "import.xlsx"

def _validate_zip(file_obj, limits):
    try:
        zf = zipfile.ZipFile(file_obj)
    except (zipfile.BadZipFile, zipfile.LargeZipFile, struct.error):
        _fail(400, "invalid_xlsx", "Tep Excel khong hop le.")
    with zf:
        infos = zf.infolist()
        if len(infos) > limits.max_zip_entries:
            _fail(413, "zip_entry_limit", "Qua nhieu thanh phan ZIP.", limit_category="zip_entries")
        total = sum(i.file_size for i in infos)
        if total > limits.max_uncompressed_zip_bytes:
            _fail(413, "zip_expansion_limit", "Kich thuoc giai nen vuot gioi han.", limit_category="zip_size")
        names = {i.filename for i in infos}
        for part in REQUIRED_ZIP_PARTS:
            if part not in names: _fail(400, "invalid_xlsx", "Thieu thanh phan XLSX.")
        for info in infos:
            fn = info.filename
            if _is_unsafe_zip_path(fn): _fail(400, "unsafe_zip_path", "Duong dan ZIP khong an toan.")
            if info.flag_bits & 0x1: _fail(400, "encrypted_archive", "Tep ma hoa khong ho tro.")
            if fn in FORBIDDEN_ZIP_PARTS: _fail(400, "macro_not_allowed", "Chua macro VBA.")
            if any(fn.startswith(p) for p in EXTERNAL_LINK_PATHS): _fail(400, "external_link_not_allowed", "Chua lien ket ngoai.")
    file_obj.seek(0)

def _copy_spool(file, limits):
    s = tempfile.SpooledTemporaryFile(max_size=min(limits.max_upload_bytes, 1048576))
    total = 0
    while True:
        chunk = file.file.read(limits.read_chunk_size)
        if not chunk: break
        total += len(chunk)
        if total > limits.max_upload_bytes:
            s.close()
            _fail(413, "upload_too_large", "Tep vuot kich thuoc cho phep.", limit_category="file_size")
        s.write(chunk)
    s.seek(0)
    return s

def get_request_size(request):
    val = getattr(request, "headers", {}).get("content-length")
    if val is None: return None
    try: return int(val)
    except: return -1

def enforce_request_limit(size, limits):
    if size is not None and size < 0:
        _fail(400, "request_too_large", "Kich thuoc yeu cau khong hop le.", limit_category="request_size")
    if size is not None and size > limits.max_request_bytes:
        _fail(413, "request_too_large", "Yeu cau vuot kich thuoc.", limit_category="request_size")

def parse_workbook_lazy(file, source_sheet_name, limits=None):
    limits = limits or DEFAULT_LIMITS
    fn = file.filename or "import.xlsx"
    ext = fn[fn.rfind("."):] if "." in fn else ""
    if ext.lower() not in ACCEPTED_EXTENSIONS:
        _fail(400, "unsupported_extension", "Dinh dang khong ho tro.")
    enforce_request_limit(file.size, limits)
    spool = _copy_spool(file, limits)
    try:
        _validate_zip(spool, limits)
        wb = openpyxl.load_workbook(spool, data_only=True, read_only=True, keep_links=False, keep_vba=False)
    except ParseError:
        spool.close()
        raise
    except Exception:
        spool.close()
        _fail(400, "invalid_xlsx", "Khong the doc tep Excel.")
    return _LazyWorkbook(spool, wb, source_sheet_name, limits)

class _LazyWorkbook:
    def __init__(self, spool, wb, source_sheet_name, limits):
        self._spool, self._wb, self._limits = spool, wb, limits
        self._closed, self._yielded = False, 0
        self._sheet_name = _resolve_sheet(wb, source_sheet_name)
        ws = wb[self._sheet_name]
        self._gen = enumerate(ws.iter_rows(values_only=True))
        self._headers, self._header_idx = self._find_headers()
        self._mapping = _map_columns(self._headers)

    @property
    def resolved_sheet(self): return self._sheet_name

    @property
    def column_count(self): return len(self._headers)

    def _find_headers(self):
        for r_idx, row in self._gen:
            if r_idx >= self._limits.max_header_search_rows:
                self.close()
                _fail(400, "header_not_found", "Khong tim thay dong tieu de.")
            if any(c is not None for c in row):
                hdrs = [str(c) if c is not None else "" for c in row]
                if len(hdrs) > self._limits.max_columns:
                    self.close()
                    _fail(400, "column_limit", "Qua nhieu cot.", limit_category="columns")
                return hdrs, r_idx
        self.close()
        _fail(400, "header_not_found", "Tep trong hoac khong co tieu de.")

    def __iter__(self): return self

    def __next__(self):
        if self._closed: raise StopIteration
        while True:
            try: r_idx, row = next(self._gen)
            except StopIteration: self.close(); raise
            if r_idx >= self._limits.max_physical_rows:
                self.close()
                _fail(413, "physical_row_limit", "Qua nhieu dong.", limit_category="rows")
            if not any(c is not None for c in row): continue
            if self._yielded >= self._limits.max_data_rows:
                self.close()
                _fail(413, "data_row_limit", f"Vuot {self._limits.max_data_rows} dong.", limit_category="rows")
            if len(row) > self._limits.max_columns:
                self.close()
                _fail(400, "column_limit", "Dong vuot so cot.", limit_category="columns")
            rl = 0
            for c in row:
                if c is not None:
                    s = str(c); rl += len(s)
                    if len(s) > self._limits.max_cell_chars:
                        self.close()
                        _fail(400, "cell_length_limit", "O qua dai.")
            if rl > self._limits.max_row_chars:
                self.close()
                _fail(400, "row_length_limit", "Dong qua lon.")
            cells = _build_cells(self._headers, row)
            mp = {}
            props = {}
            for tk, ci in self._mapping.items():
                if ci < len(row):
                    v = str(row[ci]) if row[ci] is not None else ""
                    mp[tk] = v; props[tk] = v
            self._yielded += 1
            return {"source_row_number": r_idx + 1, "raw_cells": cells, "mapped_values": mp,
                    "proposed_asset_name": props.get("proposed_asset_name"),
                    "proposed_description": props.get("proposed_description"),
                    "proposed_quantity": props.get("proposed_quantity"),
                    "proposed_unit": props.get("proposed_unit"),
                    "proposed_raw_price": props.get("proposed_raw_price"),
                    "proposed_currency": props.get("proposed_currency"),
                    "proposed_appraised_unit_price": props.get("proposed_appraised_unit_price")}
    def close(self):
        if not self._closed:
            self._closed = True
            try: self._wb.close()
            except: pass
            try: self._spool.close()
            except: pass

def _resolve_sheet(wb, requested):
    if requested:
        if requested in wb.sheetnames: return requested
        _fail(400, "sheet_not_found", f"Trang '{requested}' khong ton tai.")
    if not wb.sheetnames: _fail(400, "invalid_xlsx", "Khong co trang tinh.")
    return wb.sheetnames[0]

def _normalize(h):
    if not h: return ""
    return re.sub(r"[\s\-]+", "_", str(h).strip().lower())

def _map_columns(headers):
    m = {}
    for i, h in enumerate(headers):
        n = _normalize(h)
        if not n: continue
        for tk, aliases in COLUMN_ALIASES.items():
            if tk in m: continue
            if n in aliases: m[tk] = i; break
    return m

def _build_cells(headers, row):
    cells = []
    actual = max(len(headers), len(row))
    for ci in range(actual):
        cells.append({"column_index": ci + 1, "column_letter": get_column_letter(ci + 1),
                      "header": str(headers[ci]) if ci < len(headers) and headers[ci] else "",
                      "value": str(row[ci]) if ci < len(row) and row[ci] is not None else ""})
    return cells
