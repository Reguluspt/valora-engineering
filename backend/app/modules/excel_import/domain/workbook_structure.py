"""Deterministic, bounded workbook structure discovery for S13-PR-003."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass
from enum import Enum
from itertools import islice
from typing import Callable, Iterable, Iterator, Sequence

from app.modules.excel_import.domain.workbook_adapter import (
    AdapterInspectionResult,
    CellValue,
    SheetSummary,
)

STRUCTURE_RULE_VERSION = "s13-pr-003-v1"


class RowClass(str, Enum):
    ASSET = "asset"
    SECTION = "section"
    SUBTOTAL = "subtotal"
    TOTAL = "total"
    NOTE = "note"
    EMPTY = "empty"
    UNRESOLVED = "unresolved"


class StructureDisposition(str, Enum):
    PROPOSED = "proposed"
    REVIEW_REQUIRED = "review_required"


@dataclass(frozen=True)
class StructureRuleConfig:
    header_scan_rows: int = 200
    max_header_span: int = 3
    data_sample_rows: int = 24
    candidate_limit: int = 25
    row_preview_limit: int = 200
    clear_threshold: float = 0.62
    ambiguity_margin: float = 0.08


DEFAULT_STRUCTURE_RULES = StructureRuleConfig()


@dataclass(frozen=True)
class TableRegionCandidate:
    sheet_name: str
    header_start_row: int
    header_end_row: int
    data_start_row: int
    min_column: int
    max_column: int
    max_row: int
    confidence: float
    reasons: tuple[str, ...]
    header_labels: tuple[str | None, ...]

    def to_payload(self) -> dict:
        return {
            "sheet_name": self.sheet_name,
            "header_start_row": self.header_start_row,
            "header_end_row": self.header_end_row,
            "data_start_row": self.data_start_row,
            "candidate_table_bounds": {
                "min_row": self.header_start_row,
                "max_row": self.max_row,
                "min_column": self.min_column,
                "max_column": self.max_column,
            },
            "confidence": self.confidence,
            "reasons": list(self.reasons),
            "header_labels": list(self.header_labels),
        }


@dataclass(frozen=True)
class RowClassification:
    row_number: int
    row_class: RowClass
    confidence: float
    reasons: tuple[str, ...]

    def to_payload(self) -> dict:
        return {
            "row_number": self.row_number,
            "row_class": self.row_class.value,
            "confidence": self.confidence,
            "reasons": list(self.reasons),
        }


RowProvider = Callable[[str], Iterator[Sequence[CellValue]]]

_HEADER_TERMS = (
    "stt",
    "so thu tu",
    "ten vat tu",
    "ten tai san",
    "ten hang hoa",
    "mo ta",
    "dac diem",
    "quy cach",
    "dvt",
    "don vi tinh",
    "khoi luong",
    "so luong",
    "don gia",
    "thanh tien",
    "gia td",
    "gia tham dinh",
    "ghi chu",
)
_TOTAL_PREFIXES = ("tong cong", "tong gia tri", "tong thanh tien")
_SUBTOTAL_PREFIXES = ("cong phan", "cong muc", "tam tinh", "subtotal")
_NOTE_PREFIXES = ("ghi chu", "chu thich", "note")
_SECTION_PREFIXES = ("phan ", "chuong ", "muc ", "hang muc ")
_SERIAL_RE = re.compile(r"^\d+(?:[.\-/]\d+)*$")


def _normalized(value: object) -> str:
    if value is None:
        return ""
    text = " ".join(str(value).strip().split()).lower()
    decomposed = unicodedata.normalize("NFD", text)
    return "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")


def _display(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _nonempty_values(row: Sequence[CellValue]) -> list[object]:
    return [cell.value for cell in row if _display(cell.value)]


def _is_numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_serial(value: object) -> bool:
    if _is_numeric(value):
        return float(value).is_integer()
    return bool(_SERIAL_RE.fullmatch(_normalized(value)))


def _first_nonempty(row: Sequence[CellValue]) -> object | None:
    for cell in row:
        if _display(cell.value):
            return cell.value
    return None


def _marker_kind(values: Sequence[object]) -> RowClass | None:
    if not values:
        return None
    first = _normalized(values[0])
    joined = " ".join(_normalized(value) for value in values)
    if first.startswith(_TOTAL_PREFIXES) or joined.startswith(_TOTAL_PREFIXES):
        return RowClass.TOTAL
    if first.startswith(_SUBTOTAL_PREFIXES) or joined.startswith(_SUBTOTAL_PREFIXES):
        return RowClass.SUBTOTAL
    if first.startswith(_NOTE_PREFIXES) or joined.startswith(_NOTE_PREFIXES):
        return RowClass.NOTE
    if first.startswith("*"):
        return RowClass.NOTE
    return None


def classify_row(row: Sequence[CellValue]) -> RowClassification:
    """Classify one physical row without semantic mapping or staging mutation."""
    row_number = row[0].row if row else 0
    values = _nonempty_values(row)
    if not values:
        return RowClassification(row_number, RowClass.EMPTY, 1.0, ("no_nonempty_cells",))

    marker = _marker_kind(values)
    if marker is not None:
        return RowClassification(
            row_number,
            marker,
            0.98,
            (f"{marker.value}_marker",),
        )

    numeric_count = sum(1 for value in values if _is_numeric(value))
    text_values = [value for value in values if isinstance(value, str)]
    first = _normalized(values[0])
    first_display = _display(values[0])
    uppercase_section = (
        bool(first_display)
        and first_display == first_display.upper()
        and any(ch.isalpha() for ch in first_display)
        and len(first_display) <= 120
    )
    if numeric_count == 0 and len(values) <= 2 and (
        first.startswith(_SECTION_PREFIXES) or uppercase_section
    ):
        return RowClassification(
            row_number,
            RowClass.SECTION,
            0.95,
            ("section_heading_pattern",),
        )

    if _is_serial(values[0]) and len(values) >= 2:
        return RowClassification(
            row_number,
            RowClass.ASSET,
            0.94,
            ("serial_number_and_content",),
        )
    if numeric_count >= 1 and text_values and len(values) >= 2:
        return RowClassification(
            row_number,
            RowClass.ASSET,
            0.78,
            ("mixed_text_numeric_content",),
        )
    return RowClassification(
        row_number,
        RowClass.UNRESOLVED,
        0.35,
        ("insufficient_asset_or_marker_evidence",),
    )


def _close_iterator(rows: Iterable[Sequence[CellValue]]) -> None:
    close = getattr(rows, "close", None)
    if callable(close):
        close()


def _bounded_rows(
    row_provider: RowProvider,
    sheet_name: str,
    limit: int,
) -> list[Sequence[CellValue]]:
    rows = row_provider(sheet_name)
    try:
        return list(islice(rows, limit))
    finally:
        _close_iterator(rows)


def _span_labels(
    span: Sequence[Sequence[CellValue]],
) -> tuple[tuple[str | None, ...], int, int]:
    width = max((len(row) for row in span), default=0)
    labels: list[str | None] = []
    first_column = 0
    last_column = 0
    for column_index in range(width):
        parts: list[str] = []
        for row in span:
            if column_index >= len(row):
                continue
            value = _display(row[column_index].value)
            if value and value not in parts:
                parts.append(value)
        label = " / ".join(parts) if parts else None
        labels.append(label)
        if label:
            if not first_column:
                first_column = column_index + 1
            last_column = column_index + 1
    return tuple(labels), first_column, last_column


def _header_vocabulary_hits(labels: Sequence[str | None]) -> int:
    hits = 0
    for label in labels:
        normalized = _normalized(label)
        if normalized and any(term in normalized for term in _HEADER_TERMS):
            hits += 1
    return hits


def _has_merged_title(summary: SheetSummary, header_start_row: int) -> bool:
    return any(
        region.max_row < header_start_row and region.max_col > region.min_col
        for region in summary.merged_regions
    )


def _candidate_for_span(
    *,
    summary: SheetSummary,
    scanned_rows: Sequence[Sequence[CellValue]],
    start_index: int,
    span_size: int,
    config: StructureRuleConfig,
) -> TableRegionCandidate | None:
    span = scanned_rows[start_index : start_index + span_size]
    if len(span) != span_size:
        return None
    per_row_values = [_nonempty_values(row) for row in span]
    if any(not values or _marker_kind(values) is not None for values in per_row_values):
        return None
    # A candidate header span may not absorb the first physical asset row. This
    # also prevents ordinary serial-numbered data rows from competing as headers.
    if any(_is_serial(values[0]) for values in per_row_values):
        return None

    labels, first_column, last_column = _span_labels(span)
    nonempty_headers = sum(1 for label in labels if label)
    if nonempty_headers < 2 or not first_column or not last_column:
        return None

    width = max(1, last_column - first_column + 1)
    header_density = nonempty_headers / width
    vocabulary_hits = _header_vocabulary_hits(labels)
    data_rows = [
        row
        for row in scanned_rows[start_index + span_size : start_index + span_size + config.data_sample_rows]
        if _nonempty_values(row)
    ]
    usable_rows = sum(1 for row in data_rows if len(_nonempty_values(row)) >= 2)
    consistent_ratio = usable_rows / len(data_rows) if data_rows else 0.0
    serial_ratio = (
        sum(1 for row in data_rows if _is_serial(_first_nonempty(row))) / len(data_rows)
        if data_rows
        else 0.0
    )
    type_mix_ratio = (
        sum(
            1
            for row in data_rows
            if any(isinstance(value, str) for value in _nonempty_values(row))
            and any(_is_numeric(value) for value in _nonempty_values(row))
        )
        / len(data_rows)
        if data_rows
        else 0.0
    )
    merged_title = _has_merged_title(summary, start_index + 1)
    score = (
        0.20 * min(header_density, 1.0)
        + 0.32 * min(vocabulary_hits / 4.0, 1.0)
        + 0.20 * consistent_ratio
        + 0.12 * serial_ratio
        + 0.11 * type_mix_ratio
        + (0.05 if merged_title else 0.0)
    )
    if span_size > 1:
        score = min(1.0, score + 0.02)

    reasons: list[str] = ["header_density"]
    if vocabulary_hits:
        reasons.append("business_header_vocabulary")
    if consistent_ratio >= 0.5:
        reasons.append("consistent_subsequent_rows")
    if serial_ratio > 0:
        reasons.append("serial_number_pattern")
    if type_mix_ratio > 0:
        reasons.append("mixed_data_types")
    if merged_title:
        reasons.append("merged_title_above")
    if span_size > 1:
        reasons.append("multi_row_header")

    header_start = start_index + 1
    header_end = header_start + span_size - 1
    return TableRegionCandidate(
        sheet_name=summary.name,
        header_start_row=header_start,
        header_end_row=header_end,
        data_start_row=header_end + 1,
        min_column=first_column,
        max_column=max(last_column, summary.max_column),
        max_row=summary.max_row,
        confidence=round(min(max(score, 0.0), 1.0), 6),
        reasons=tuple(reasons),
        header_labels=labels,
    )


def _rank_candidates(
    inspection: AdapterInspectionResult,
    row_provider: RowProvider,
    config: StructureRuleConfig,
) -> list[TableRegionCandidate]:
    candidates: list[TableRegionCandidate] = []
    for summary in inspection.sheets:
        scanned = _bounded_rows(row_provider, summary.name, config.header_scan_rows)
        for start_index in range(len(scanned)):
            for span_size in range(1, config.max_header_span + 1):
                candidate = _candidate_for_span(
                    summary=summary,
                    scanned_rows=scanned,
                    start_index=start_index,
                    span_size=span_size,
                    config=config,
                )
                if candidate is not None:
                    candidates.append(candidate)
    candidates.sort(
        key=lambda item: (
            -item.confidence,
            item.sheet_name.casefold(),
            item.header_start_row,
            item.header_end_row,
        )
    )
    return candidates[: config.candidate_limit]


def _classify_candidate_rows(
    candidate: TableRegionCandidate,
    row_provider: RowProvider,
    config: StructureRuleConfig,
) -> dict:
    counts: Counter[str] = Counter()
    preview: list[dict] = []
    physical_count = 0
    rows = row_provider(candidate.sheet_name)
    try:
        for row in rows:
            row_number = row[0].row if row else physical_count + 1
            if row_number < candidate.data_start_row:
                continue
            physical_count += 1
            classified = classify_row(row)
            counts[classified.row_class.value] += 1
            if len(preview) < config.row_preview_limit:
                preview.append(classified.to_payload())
    finally:
        _close_iterator(rows)
    return {
        "sheet_name": candidate.sheet_name,
        "data_start_row": candidate.data_start_row,
        "physical_rows_classified": physical_count,
        "counts": {row_class.value: counts[row_class.value] for row_class in RowClass},
        "preview": preview,
        "preview_truncated": physical_count > len(preview),
    }


def analyze_workbook_structure(
    inspection: AdapterInspectionResult,
    row_provider: RowProvider,
    *,
    config: StructureRuleConfig = DEFAULT_STRUCTURE_RULES,
) -> dict:
    """Return canonical analysis payload from actual adapter output."""
    candidates = _rank_candidates(inspection, row_provider, config)
    disposition = StructureDisposition.REVIEW_REQUIRED
    disposition_reasons: list[str] = []
    if not candidates:
        disposition_reasons.append("no_viable_candidate")
    else:
        top = candidates[0]
        if top.confidence < config.clear_threshold:
            disposition_reasons.append("confidence_below_threshold")
        if len(candidates) > 1 and top.confidence - candidates[1].confidence < config.ambiguity_margin:
            disposition_reasons.append("competing_candidates")
        if not disposition_reasons:
            disposition = StructureDisposition.PROPOSED

    classification = (
        _classify_candidate_rows(candidates[0], row_provider, config)
        if candidates
        else {
            "sheet_name": None,
            "data_start_row": None,
            "physical_rows_classified": 0,
            "counts": {row_class.value: 0 for row_class in RowClass},
            "preview": [],
            "preview_truncated": False,
        }
    )
    return {
        "rule_version": STRUCTURE_RULE_VERSION,
        "rule_config": asdict(config),
        "disposition": disposition.value,
        "disposition_reasons": disposition_reasons,
        "proposed_candidate_index": 0 if candidates else None,
        "candidate_count": len(candidates),
        "candidates": [candidate.to_payload() for candidate in candidates],
        "row_classification": classification,
    }


def primary_candidate_signature(payload: dict) -> dict | None:
    index = payload.get("proposed_candidate_index")
    candidates = payload.get("candidates") or []
    if not isinstance(index, int) or index < 0 or index >= len(candidates):
        return None
    candidate = candidates[index]
    bounds = candidate.get("candidate_table_bounds") or {}
    return {
        "sheet_name": candidate.get("sheet_name"),
        "header_start_row": candidate.get("header_start_row"),
        "header_end_row": candidate.get("header_end_row"),
        "data_start_row": candidate.get("data_start_row"),
        "min_column": bounds.get("min_column"),
        "max_column": bounds.get("max_column"),
        "header_labels": candidate.get("header_labels"),
    }


def require_review_for_drift(payload: dict, previous_payload: dict | None) -> dict:
    """Fail to review when the primary structural signature changes."""
    if previous_payload is None:
        return payload
    current_signature = primary_candidate_signature(payload)
    previous_signature = primary_candidate_signature(previous_payload)
    if current_signature == previous_signature:
        return payload
    out = copy.deepcopy(payload)
    out["disposition"] = StructureDisposition.REVIEW_REQUIRED.value
    reasons = list(out.get("disposition_reasons") or [])
    if "structure_drift_from_previous_generation" not in reasons:
        reasons.append("structure_drift_from_previous_generation")
    out["disposition_reasons"] = reasons
    return out


def canonical_payload_digest(payload: dict) -> str:
    encoded = json.dumps(
        payload,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def payload_digest_matches(payload: dict, expected_digest: str) -> bool:
    return hmac.compare_digest(canonical_payload_digest(payload), expected_digest)
