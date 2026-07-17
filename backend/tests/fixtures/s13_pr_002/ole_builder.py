"""Minimal CFB/OLE writer for redacted .xls threat fixtures (tests only)."""
from __future__ import annotations

import struct
from pathlib import Path

# Sector size 512
_SSZ = 9  # 2^9 = 512
_SECTOR = 512
_HEADER_SIZE = 512
_DIR_ENTRY = 128


def _pad(data: bytes, size: int) -> bytes:
    if len(data) >= size:
        return data[:size]
    return data + b"\x00" * (size - len(data))


def write_ole_single_stream(path: str | Path, stream_name: str, payload: bytes) -> None:
    """
    Write a minimal OLE compound document with one named stream under root.

    Sufficient for olefile.isOleFile + openstream([stream_name]).
    Streams are padded to >= mini-stream cutoff (4096) so regular FAT is used.
    """
    path = Path(path)
    # MS-CFB v3 mini cutoff is 4096; pad so olefile uses regular sectors.
    if len(payload) < 4096:
        payload = payload + b"\x00" * (4096 - len(payload))
    # Layout:
    # sector -1: header (512)
    # sector 0: FAT
    # sector 1: directory (root + stream entry)
    # sector 2..: stream data

    data_sectors = max(1, (len(payload) + _SECTOR - 1) // _SECTOR)
    # After header: sector 0 = FAT, 1 = dir, 2.. = data chain
    fat_entries = [0xFFFFFFFD]  # sector 0 = FATSECT
    fat_entries.append(0xFFFFFFFE)  # sector 1 = ENDOFCHAIN for directory (single)
    for i in range(data_sectors):
        if i < data_sectors - 1:
            fat_entries.append(2 + i + 1)
        else:
            fat_entries.append(0xFFFFFFFE)  # ENDOFCHAIN
    # pad FAT sector to 128 entries (512/4)
    while len(fat_entries) < 128:
        fat_entries.append(0xFFFFFFFF)
    fat_bytes = b"".join(struct.pack("<I", e) for e in fat_entries)

    # Directory: root storage + stream
    def dir_entry(
        name: str,
        obj_type: int,
        *,
        start_sector: int = 0,
        size: int = 0,
        color: int = 1,
        left: int = 0xFFFFFFFF,
        right: int = 0xFFFFFFFF,
        child: int = 0xFFFFFFFF,
    ) -> bytes:
        # name as UTF-16LE, max 32 chars including null
        name_u = name.encode("utf-16le") + b"\x00\x00"
        name_u = _pad(name_u, 64)
        name_len = min(len(name) * 2 + 2, 64)
        return (
            name_u
            + struct.pack("<H", name_len)
            + struct.pack("<B", obj_type)
            + struct.pack("<B", color)
            + struct.pack("<I", left)
            + struct.pack("<I", right)
            + struct.pack("<I", child)
            + b"\x00" * 16  # clsid
            + struct.pack("<I", 0)  # state
            + struct.pack("<Q", 0)  # created
            + struct.pack("<Q", 0)  # modified
            + struct.pack("<I", start_sector)
            + struct.pack("<I", size)
            + struct.pack("<I", 0)
        )

    # Root (type 5 storage), child = 1 (stream entry)
    root = dir_entry("Root Entry", 5, start_sector=0xFFFFFFFE, size=0, child=1)
    # Stream (type 2), start sector 2
    stream = dir_entry(stream_name, 2, start_sector=2, size=len(payload), left=0xFFFFFFFF, right=0xFFFFFFFF)
    # Empty unused entries to fill sector
    empty = dir_entry("", 0)
    directory = root + stream + empty + empty  # 4 * 128 = 512

    # Header
    header = bytearray(512)
    header[0:8] = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"
    header[24:26] = struct.pack("<H", 0x003E)  # minor
    header[26:28] = struct.pack("<H", 0x0003)  # major v3
    header[28:30] = struct.pack("<H", 0xFFFE)  # little endian
    header[30:32] = struct.pack("<H", _SSZ)
    header[32:34] = struct.pack("<H", 6)  # mini sector 64
    header[44:48] = struct.pack("<I", 1)  # num FAT sectors
    header[48:52] = struct.pack("<I", 1)  # first directory sector
    header[56:60] = struct.pack("<I", 0x00001000)  # mini cutoff (standard); stream padded above
    header[60:64] = struct.pack("<I", 0xFFFFFFFE)  # first mini FAT
    header[64:68] = struct.pack("<I", 0)  # num mini FAT
    header[68:72] = struct.pack("<I", 0xFFFFFFFE)  # first DIFAT
    header[72:76] = struct.pack("<I", 0)  # num DIFAT
    # First 109 DIFAT entries: first FAT at sector 0
    header[76:80] = struct.pack("<I", 0)
    for i in range(1, 109):
        struct.pack_into("<I", header, 76 + i * 4, 0xFFFFFFFF)

    # Stream data padded to sectors
    stream_data = _pad(payload, data_sectors * _SECTOR)

    with open(path, "wb") as f:
        f.write(bytes(header))
        f.write(fat_bytes)
        f.write(directory)
        f.write(stream_data)


def biff_record(rec_type: int, payload: bytes = b"") -> bytes:
    return struct.pack("<HH", rec_type, len(payload)) + payload


def make_threat_workbook_stream(*, threat: str) -> bytes:
    """Build a minimal BIFF8-like stream containing BOF + threat + EOF."""
    # BOF workbook (0x0809) minimal
    bof = biff_record(0x0809, struct.pack("<HHHHHH", 0x0600, 0x0005, 0x0FDE, 0x07CC, 0, 0))
    eof = biff_record(0x000A, b"")
    if threat == "filepass":
        mid = biff_record(0x002F, b"\x00\x00")
    elif threat == "addin_supbook":
        mid = biff_record(0x01AE, b"\x01\x00\x01\x3A")
    elif threat == "external_supbook":
        mid = biff_record(0x01AE, b"\x01\x00" + b"http://evil.example/x.xls")
    elif threat == "internal_supbook":
        mid = biff_record(0x01AE, b"\x01\x00\x01\x04")  # ctab=1, cch=0x0401
    elif threat == "dcon":
        mid = biff_record(0x0050, b"\x00\x01")
    elif threat == "dconname":
        mid = biff_record(0x0052, b"\x00\x01")
    elif threat == "dconref":
        mid = biff_record(0x0051, b"\x00\x01")
    elif threat == "externname":
        mid = biff_record(0x0023, b"\x00\x01\x00")
    elif threat == "macro_boundsheet":
        mid = biff_record(0x0085, struct.pack("<IBB", 0, 0, 0x01) + b"\x01\x00M")
    elif threat == "vba_boundsheet":
        mid = biff_record(0x0085, struct.pack("<IBB", 0, 0, 0x06) + b"\x01\x00V")
    elif threat == "macro_name":
        mid = biff_record(0x0018, struct.pack("<H", 0x0008) + b"\x00" * 10)
    elif threat == "binary_name":
        mid = biff_record(0x0018, struct.pack("<H", 0x0010) + b"\x00" * 10)
    elif threat == "truncated_biff":
        # incomplete record header (type only, missing length/payload)
        mid = struct.pack("<H", 0x002F)
        return bof + mid  # no EOF — malformed
    else:
        raise ValueError(threat)
    return bof + mid + eof


def write_threat_xls(path: str | Path, threat: str) -> Path:
    path = Path(path)
    stream = make_threat_workbook_stream(threat=threat)
    write_ole_single_stream(path, "Workbook", stream)
    return path
