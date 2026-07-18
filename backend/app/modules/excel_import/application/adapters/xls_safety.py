"""Fail-closed .xls OLE/BIFF presence detection (not merely non-execution)."""
from __future__ import annotations

import re
import struct
from typing import Iterable

from app.modules.excel_import.domain.workbook_adapter import fail_adapter

# BIFF record types (MS-XLS)
BIFF_FILEPASS = 0x002F
BIFF_SUPBOOK = 0x01AE
BIFF_EXTERNSHEET = 0x0017
BIFF_EXTERNNAME = 0x0023
BIFF_DCON = 0x0050
BIFF_DCONNAME = 0x0052
BIFF_DCONREF = 0x0051
BIFF_MERGEDCELLS = 0x00E5
BIFF_BOUNDSHEET = 0x0085
BIFF_NAME = 0x0018
BIFF_BOF = 0x0809
BIFF_EOF = 0x000A
BIFF_FORMULA = 0x0006
BIFF_FORMULA_OLD = 0x0206  # older BIFF

# Max bytes scanned from Workbook stream for threat records
_MAX_WORKBOOK_SCAN = 8 * 1024 * 1024

# Internal self-reference SUPBOOK: ctab + cch==0x0401 (MS-XLS)
_SUPBOOK_INTERNAL_TAIL = b"\x01\x04"
# Add-in functions SUPBOOK (external reference machinery)
_SUPBOOK_ADDIN = b"\x01\x00\x01\x3a"

# BOUNDSHEET dt (sheet type): 0x00 worksheet only accepted
_BOUNDSHEET_DT_WORKSHEET = 0x00
_BOUNDSHEET_DT_MACROSHEET = 0x01
_BOUNDSHEET_DT_CHART = 0x02
_BOUNDSHEET_DT_VBAMODULE = 0x06

# NAME option flags
_NAME_F_MACRO = 0x0008
_NAME_F_BINARY = 0x0010

# OLE stream / storage name patterns indicating VBA/macro presence
_VBA_NAME_RE = re.compile(
    r"(vba|_vba_project|_vba_project_cur|macrosheets?|xlm)",
    re.IGNORECASE,
)


def list_ole_stream_names(path: str) -> list[str]:
    """Return flattened OLE stream/storage path names (fail-closed on bad OLE)."""
    try:
        import olefile
    except ImportError:
        fail_adapter(
            500,
            "invalid_xls",
            "Không thể kiểm tra an toàn tệp .xls (thiếu thành phần hệ thống).",
        )
    try:
        if not olefile.isOleFile(path):
            fail_adapter(400, "signature_mismatch", "Chữ ký tệp không khớp định dạng .xls.")
        with olefile.OleFileIO(path) as ole:
            names: list[str] = []
            for entry in ole.listdir():
                names.append("/".join(entry))
            return names
    except Exception as exc:
        from app.modules.excel_import.domain.workbook_adapter import AdapterError

        if isinstance(exc, AdapterError):
            raise
        fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")


def reject_ole_vba_presence(stream_names: Iterable[str]) -> None:
    """Reject if any OLE stream/storage name indicates VBA/macro project."""
    for name in stream_names:
        if _VBA_NAME_RE.search(name.replace("\\", "/")):
            fail_adapter(
                400,
                "macro_not_allowed",
                "Tệp Excel chứa macro hoặc mã VBA không được phép.",
            )


def _read_workbook_stream(path: str, max_bytes: int = _MAX_WORKBOOK_SCAN) -> bytes:
    import olefile

    try:
        with olefile.OleFileIO(path) as ole:
            candidates = [["Workbook"], ["Book"], ["WORKBOOK"], ["BOOK"]]
            stream_path = None
            for c in candidates:
                if ole.exists(c):
                    stream_path = c
                    break
            if stream_path is None:
                for entry in ole.listdir():
                    if len(entry) == 1 and entry[0].lower() in {"workbook", "book"}:
                        stream_path = entry
                        break
            if stream_path is None:
                fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
            raw = ole.openstream(stream_path).read(max_bytes + 1)
            if len(raw) > max_bytes:
                fail_adapter(
                    413,
                    "workbook_stream_limit",
                    "Kích thước luồng Workbook vượt quá giới hạn cho phép.",
                    "workbook_stream",
                )
            return raw
    except Exception as exc:
        from app.modules.excel_import.domain.workbook_adapter import AdapterError

        if isinstance(exc, AdapterError):
            raise
        fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")


def _reject_supbook(payload: bytes) -> None:
    """
    Allow only a structurally valid internal self-reference SUPBOOK:
      length == 4 and payload[2:4] == 01 04
    Reject add-in, DDE/OLE, external workbook, and malformed forms.
    """
    if len(payload) < 4:
        fail_adapter(
            400,
            "external_link_not_allowed",
            "Tệp Excel chứa liên kết ngoài không được phép.",
        )
    if len(payload) == 4 and payload[2:4] == _SUPBOOK_INTERNAL_TAIL:
        return
    # Explicit add-in form (also length 4 but not internal)
    if payload[:4].lower() == _SUPBOOK_ADDIN or payload[:4] == b"\x01\x00\x01\x3A":
        fail_adapter(
            400,
            "external_link_not_allowed",
            "Tệp Excel chứa liên kết ngoài không được phép.",
        )
    fail_adapter(
        400,
        "external_link_not_allowed",
        "Tệp Excel chứa liên kết ngoài không được phép.",
    )


def _reject_boundsheet(payload: bytes) -> None:
    """Reject macro/XLM/VBA module sheets; charts allowed; worksheets allowed."""
    # lbPlyPos(4) + hsState(1) + dt(1) + name...
    if len(payload) < 6:
        fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
    dt = payload[5]
    if dt in (_BOUNDSHEET_DT_MACROSHEET, _BOUNDSHEET_DT_VBAMODULE):
        fail_adapter(
            400,
            "macro_not_allowed",
            "Tệp Excel chứa macro hoặc mã VBA không được phép.",
        )
    # Unknown non-worksheet/non-chart types fail closed
    if dt not in (_BOUNDSHEET_DT_WORKSHEET, _BOUNDSHEET_DT_CHART):
        fail_adapter(
            400,
            "macro_not_allowed",
            "Tệp Excel chứa macro hoặc mã VBA không được phép.",
        )


def _reject_name(payload: bytes) -> None:
    """Reject macro/binary NAME records."""
    if len(payload) < 2:
        fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
    (flags,) = struct.unpack_from("<H", payload, 0)
    if flags & (_NAME_F_MACRO | _NAME_F_BINARY):
        fail_adapter(
            400,
            "macro_not_allowed",
            "Tệp Excel chứa macro hoặc mã VBA không được phép.",
        )


def scan_biff_threats(workbook_stream: bytes) -> None:
    """
    Bounded sequential BIFF record scan.

    Rejects FILEPASS, unsafe SUPBOOK, EXTERNNAME, DCON*, macro BOUNDSHEET/NAME.
    """
    data = workbook_stream
    n = len(data)
    pos = 0
    records_seen = 0
    max_records = 500_000

    while pos + 4 <= n:
        if records_seen >= max_records:
            fail_adapter(
                413,
                "biff_record_limit",
                "Số bản ghi BIFF vượt quá giới hạn cho phép.",
                "biff",
            )
        rec_type, rec_len = struct.unpack_from("<HH", data, pos)
        pos += 4
        if rec_len < 0 or pos + rec_len > n:
            fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
        payload = data[pos : pos + rec_len]
        pos += rec_len
        records_seen += 1

        if rec_type == BIFF_FILEPASS:
            fail_adapter(400, "encrypted_workbook", "Tệp mã hóa không được hỗ trợ.")

        if rec_type == BIFF_SUPBOOK:
            _reject_supbook(payload)

        if rec_type in (BIFF_EXTERNNAME, BIFF_DCON, BIFF_DCONNAME, BIFF_DCONREF):
            fail_adapter(
                400,
                "external_link_not_allowed",
                "Tệp Excel chứa liên kết ngoài không được phép.",
            )

        if rec_type == BIFF_BOUNDSHEET:
            _reject_boundsheet(payload)

        if rec_type == BIFF_NAME:
            _reject_name(payload)


def assert_xls_safety(path: str) -> bytes:
    """
    Full pre-open safety: OLE inventory + BIFF threat scan.
    Returns workbook stream bytes (for diagnostics/tests only).
    """
    names = list_ole_stream_names(path)
    reject_ole_vba_presence(names)
    stream = _read_workbook_stream(path)
    scan_biff_threats(stream)
    return stream


def extract_biff_formula_numeric_caches(
    workbook_stream: bytes,
) -> dict[tuple[int, int, int], float]:
    """
    Bounded read of BIFF FORMULA records for **cached numeric results only**.

    xlrd 2.x does not expose formula cached values (returns empty text). This
    parser does not evaluate formulas — it only decodes the IEEE double already
    stored in the FORMULA record result field (MS-XLS).

    Keys: (sheet_index_0based, row_0based, col_0based) → float cached value.
    Non-numeric formula results (string/bool/error/blank special encodings)
    are skipped.
    """
    data = workbook_stream
    n = len(data)
    pos = 0
    records_seen = 0
    max_records = 500_000
    sheet_idx = -1
    in_sheet = False
    out: dict[tuple[int, int, int], float] = {}

    while pos + 4 <= n:
        if records_seen >= max_records:
            break
        rec_type, rec_len = struct.unpack_from("<HH", data, pos)
        pos += 4
        if rec_len < 0 or pos + rec_len > n:
            break
        payload = data[pos : pos + rec_len]
        pos += rec_len
        records_seen += 1

        if rec_type == BIFF_BOF and len(payload) >= 4:
            # dt at offset 2: 0x0010 worksheet, 0x0005 workbook, etc.
            (dt,) = struct.unpack_from("<H", payload, 2)
            if dt == 0x0010:  # worksheet
                sheet_idx += 1
                in_sheet = True
            else:
                in_sheet = False
            continue

        if rec_type == BIFF_EOF:
            in_sheet = False
            continue

        if not in_sheet or sheet_idx < 0:
            continue

        if rec_type not in (BIFF_FORMULA, BIFF_FORMULA_OLD):
            continue
        # Need at least row/col/xf/result (2+2+2+8 = 14)
        if len(payload) < 14:
            continue
        row, col, _xf = struct.unpack_from("<HHH", payload, 0)
        # Special result: bytes 6-7 of the 8-byte result are 0xFFFF
        (tag,) = struct.unpack_from("<H", payload, 6 + 6)
        if tag == 0xFFFF:
            # string / bool / error / blank — not a numeric cache for this proof
            continue
        (cached,) = struct.unpack_from("<d", payload, 6)
        out[(sheet_idx, row, col)] = float(cached)

    return out
