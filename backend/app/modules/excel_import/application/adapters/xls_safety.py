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

# Max bytes scanned from Workbook stream for threat records
_MAX_WORKBOOK_SCAN = 8 * 1024 * 1024

# OLE stream / storage name patterns indicating VBA/macro presence
_VBA_NAME_RE = re.compile(
    r"(vba|_vba_project|_vba_project_cur|macrosheets?|xlm)",
    re.IGNORECASE,
)

# DDE / OLE link indicators in SUPBOOK payload (case-insensitive substrings)
_EXTERNAL_MARKERS = (
    b"\x01",  # SUPBOOK URL encoding often starts with 0x01
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
                # entry is a list of path segments
                joined = "/".join(entry)
                names.append(joined)
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
            # Classic BIFF workbook stream names
            candidates = [
                ["Workbook"],
                ["Book"],
                ["WORKBOOK"],
                ["BOOK"],
            ]
            stream_path = None
            for c in candidates:
                if ole.exists(c):
                    stream_path = c
                    break
            if stream_path is None:
                # Some files use case variants via listdir
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


def scan_biff_threats(workbook_stream: bytes) -> None:
    """
    Bounded sequential BIFF record scan for encryption and external links.

    Rejects:
    - FILEPASS (encrypted)
    - SUPBOOK with external URL/DDE markers
    - EXTERNNAME / DCON* when clearly external linking machinery is present with SUPBOOK
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
        pos += rec_len
        records_seen += 1

        if rec_type == BIFF_FILEPASS:
            fail_adapter(400, "encrypted_workbook", "Tệp mã hóa không được hỗ trợ.")

        if rec_type == BIFF_SUPBOOK:
            # Internal self-reference SUPBOOK is exactly 4 bytes (ctab + cch=0x0401).
            # Any larger SUPBOOK carries an external workbook/DDE reference — fail closed.
            if rec_len > 4:
                fail_adapter(
                    400,
                    "external_link_not_allowed",
                    "Tệp Excel chứa liên kết ngoài không được phép.",
                )

        if rec_type in (BIFF_EXTERNNAME, BIFF_DCONNAME):
            # Named external/DDE references — presence is not allowed.
            if rec_len > 0:
                fail_adapter(
                    400,
                    "external_link_not_allowed",
                    "Tệp Excel chứa liên kết ngoài không được phép.",
                )


def parse_merged_cells_from_biff(workbook_stream: bytes, max_merged: int) -> list[tuple[int, int, int, int]]:
    """
    Parse MERGEDCELLS records from BIFF stream.

    Returns list of (rlo, rhi, clo, chi) 0-based half-open style as in MS-XLS
    (rhi/chi exclusive). Converted by caller to inclusive 1-based MergedRegion.
    """
    data = workbook_stream
    n = len(data)
    pos = 0
    regions: list[tuple[int, int, int, int]] = []
    while pos + 4 <= n:
        rec_type, rec_len = struct.unpack_from("<HH", data, pos)
        pos += 4
        if rec_len < 0 or pos + rec_len > n:
            break
        payload = data[pos : pos + rec_len]
        pos += rec_len
        if rec_type != BIFF_MERGEDCELLS or rec_len < 2:
            continue
        (count,) = struct.unpack_from("<H", payload, 0)
        need = 2 + count * 8
        if need > rec_len:
            fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
        off = 2
        for _ in range(count):
            rlo, rhi, clo, chi = struct.unpack_from("<HHHH", payload, off)
            off += 8
            if rlo > rhi or clo > chi or rhi > 65535 or chi > 255:
                fail_adapter(400, "invalid_xls", "Tệp Excel .xls không hợp lệ hoặc không thể đọc được.")
            regions.append((rlo, rhi, clo, chi))
            if len(regions) > max_merged:
                fail_adapter(
                    413,
                    "merged_region_limit",
                    "Số vùng gộp ô vượt quá giới hạn cho phép.",
                    "merged",
                )
    return regions


def assert_xls_safety(path: str) -> bytes:
    """
    Full pre-open safety: OLE inventory + BIFF threat scan.
    Returns workbook stream bytes for optional merge parse reuse.
    """
    names = list_ole_stream_names(path)
    reject_ole_vba_presence(names)
    stream = _read_workbook_stream(path)
    scan_biff_threats(stream)
    return stream
