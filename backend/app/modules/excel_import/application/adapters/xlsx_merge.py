"""Bounded OOXML merge-cell extraction without materializing full worksheet cells."""
from __future__ import annotations

import re
import zipfile
from xml.etree import ElementTree as ET

from app.modules.excel_import.domain.workbook_adapter import MergedRegion, fail_adapter

_NS = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
_REF_RE = re.compile(
    r"^(?P<c1>[A-Z]+)(?P<r1>\d+):(?P<c2>[A-Z]+)(?P<r2>\d+)$",
    re.IGNORECASE,
)


def _col_to_idx(col: str) -> int:
    n = 0
    for ch in col.upper():
        if not ("A" <= ch <= "Z"):
            fail_adapter(400, "invalid_xlsx", "Tệp Excel không hợp lệ hoặc không thể đọc được.")
        n = n * 26 + (ord(ch) - 64)
    return n


def parse_merge_ref(ref: str) -> MergedRegion:
    m = _REF_RE.match(ref.strip())
    if not m:
        fail_adapter(400, "invalid_xlsx", "Tệp Excel không hợp lệ hoặc không thể đọc được.")
    r1 = int(m.group("r1"))
    r2 = int(m.group("r2"))
    c1 = _col_to_idx(m.group("c1"))
    c2 = _col_to_idx(m.group("c2"))
    if r1 < 1 or r2 < 1 or c1 < 1 or c2 < 1 or r1 > r2 or c1 > c2:
        fail_adapter(400, "invalid_xlsx", "Tệp Excel không hợp lệ hoặc không thể đọc được.")
    return MergedRegion(min_row=r1, min_col=c1, max_row=r2, max_col=c2)


def extract_merged_regions_from_xlsx(
    path: str,
    *,
    max_merged_total: int,
    max_merged_per_sheet: int,
) -> dict[str, tuple[MergedRegion, ...]]:
    """
    Map sheet name -> merged regions via workbook.xml relationships + sheet XML.
    Bounded: does not load cell values.
    """
    result: dict[str, list[MergedRegion]] = {}
    total = 0
    try:
        with zipfile.ZipFile(path) as zf:
            # sheet name -> target path
            wb_xml = zf.read("xl/workbook.xml")
            root = ET.fromstring(wb_xml)
            sheets_el = root.find("m:sheets", _NS)
            if sheets_el is None:
                return {}
            # relationships
            rels: dict[str, str] = {}
            try:
                rels_xml = zf.read("xl/_rels/workbook.xml.rels")
                rels_root = ET.fromstring(rels_xml)
                for rel in rels_root:
                    rid = rel.attrib.get("Id")
                    target = rel.attrib.get("Target")
                    if rid and target:
                        if not target.startswith("xl/") and not target.startswith("/"):
                            target = "xl/" + target.lstrip("/")
                        elif target.startswith("/"):
                            target = target.lstrip("/")
                        rels[rid] = target
            except KeyError:
                rels = {}

            for sh in sheets_el.findall("m:sheet", _NS):
                name = sh.attrib.get("name") or ""
                rid = sh.attrib.get(
                    "{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"
                )
                if not name or not rid or rid not in rels:
                    result[name] = []
                    continue
                target = rels[rid]
                try:
                    sheet_bytes = zf.read(target)
                except KeyError:
                    result[name] = []
                    continue
                # Parse only mergeCells — stream as string length bounded by zip limits already
                sroot = ET.fromstring(sheet_bytes)
                merges: list[MergedRegion] = []
                mc = sroot.find("m:mergeCells", _NS)
                if mc is not None:
                    for cell in mc.findall("m:mergeCell", _NS):
                        ref = cell.attrib.get("ref")
                        if not ref:
                            fail_adapter(
                                400,
                                "invalid_xlsx",
                                "Tệp Excel không hợp lệ hoặc không thể đọc được.",
                            )
                        merges.append(parse_merge_ref(ref))
                        total += 1
                        if len(merges) > max_merged_per_sheet or total > max_merged_total:
                            fail_adapter(
                                413,
                                "merged_region_limit",
                                "Số vùng gộp ô vượt quá giới hạn cho phép.",
                                "merged",
                            )
                result[name] = merges
    except Exception as exc:
        from app.modules.excel_import.domain.workbook_adapter import AdapterError

        if isinstance(exc, AdapterError):
            raise
        fail_adapter(400, "invalid_xlsx", "Tệp Excel không hợp lệ hoặc không thể đọc được.")

    return {k: tuple(v) for k, v in result.items()}
