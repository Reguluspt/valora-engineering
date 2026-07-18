"""Deterministic, bounded workbook structure discovery for S13-PR-003."""
from __future__ import annotations

import copy
import hashlib
import hmac
import json
import re
import unicodedata
from collections import Counter
from dataclasses import asdict, dataclass, replace
from datetime import date, datetime
from enum import Enum
from itertools import islice
from typing import Callable, Iterable, Iterator, Sequence

from app.modules.excel_import.domain.workbook_adapter import (
    AdapterInspectionResult,
    CellValue,
    SheetSummary,
)

STRUCTURE_RULE_VERSION = "s13-pr-003-v3"


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
    column_evidence_sample: int = 24
    empty_column_separator_run: int = 1
    late_blank_header_edge_extension: int = 1
    vertical_blank_boundary_run: int = 2
    vertical_unresolved_boundary_run: int = 2
    trailing_note_unresolved_run: int = 3
    post_total_tail: int = 3
    candidate_limit: int = 25
    row_preview_limit: int = 200
    clear_threshold: float = 0.62
    ambiguity_margin: float = 0.08
    header_group_min_families: int = 3
    header_group_min_columns: int = 3
    header_group_start_lookback: int = 2
    repeated_core_family_threshold: int = 2


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
    boundary_reason: str = "sheet_end"
    boundary_flags: tuple[str, ...] = ()

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
            "boundary_reason": self.boundary_reason,
            "boundary_flags": list(self.boundary_flags),
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


@dataclass
class _ResolutionState:
    candidate: TableRegionCandidate
    counts: Counter[str]
    preview: list[dict]
    physical_count: int = 0
    accepted_max_row: int = 0
    pending_blank: RowClassification | None = None
    unresolved_run: int = 0
    trailing_run: int = 0
    post_total: bool = False
    post_total_count: int = 0
    ended: bool = False
    boundary_reason: str = "sheet_end"
    boundary_flags: list[str] | None = None
    extended_edge: str | None = None

    def __post_init__(self) -> None:
        self.accepted_max_row = self.candidate.header_end_row
        if self.boundary_flags is None:
            self.boundary_flags = list(self.candidate.boundary_flags)


RowProvider = Callable[[str], Iterator[Sequence[CellValue]]]

_HEADER_ROLE_PHRASES = {
    "START_INDEX": ("stt", "so thu tu"),
    "START_ID": ("ma tai san", "ma vat tu", "ma hang hoa"),
    "NAME": ("ten tai san", "ten vat tu", "ten hang hoa"),
    "DESCRIPTION": ("dac diem", "quy cach", "mo ta"),
    "UNIT": ("dvt", "don vi tinh"),
    "MEASURE": ("so luong", "khoi luong"),
    "VALUE": ("don gia", "thanh tien", "gia td", "gia tham dinh"),
    "NOTE": ("ghi chu",),
}
_HEADER_TERMS = tuple(
    phrase for phrases in _HEADER_ROLE_PHRASES.values() for phrase in phrases
)
_TOTAL_EXACT_SURFACE = ("tổng", "total")
_TOTAL_PREFIXES_SURFACE = ("tổng cộng", "tổng giá trị", "tổng thành tiền")
_SUBTOTAL_PREFIXES_SURFACE = ("cộng phần", "cộng mục", "tạm tính", "subtotal")
_NOTE_PREFIXES_SURFACE = ("ghi chú", "chú thích", "note")
_SECTION_PREFIXES_SURFACE = ("phần", "chương", "mục", "hạng mục")
_TOTAL_EXACT_SEARCH = ("tong", "total")
_TOTAL_PREFIXES_SEARCH = ("tong cong", "tong gia tri", "tong thanh tien")
_SUBTOTAL_PREFIXES_SEARCH = ("cong phan", "cong muc", "tam tinh", "subtotal")
_NOTE_PREFIXES_SEARCH = ("ghi chu", "chu thich", "note")
_SECTION_PREFIXES_SEARCH = ("phan", "chuong", "muc", "hang muc")
_SERIAL_RE = re.compile(r"^\d+(?:[.\-/]\d+)*$")
_OUTLINE_RE = re.compile(r"^(?:[ivxlcdm]+|[a-z])(?:[.\-/]\d+)*$", re.IGNORECASE)
_FAIL_CLOSED_HORIZONTAL_FLAGS = (
    "multiple_horizontal_table_groups",
    "ambiguous_horizontal_table_boundary",
)


def _surface_normalized(value: object) -> str:
    if value is None:
        return ""
    return " ".join(unicodedata.normalize("NFKC", str(value)).strip().split()).casefold()


def _search_normalized(value: object) -> str:
    surface = _surface_normalized(value)
    decomposed = unicodedata.normalize("NFD", surface)
    folded = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    return " ".join(folded.replace("đ", "d").split())


def _normalized(value: object) -> str:
    """Compatibility alias for the v3 accent-insensitive search channel."""
    return _search_normalized(value)


def _display(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split())


def _nonempty_cells(row: Sequence[CellValue]) -> list[CellValue]:
    return [cell for cell in row if _display(cell.value)]


def _nonempty_values(row: Sequence[CellValue]) -> list[object]:
    return [cell.value for cell in _nonempty_cells(row)]


def _is_numeric(value: object) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _is_serial(value: object) -> bool:
    if _is_numeric(value):
        return float(value).is_integer()
    return bool(_SERIAL_RE.fullmatch(_normalized(value)))


def _strong_asset_signature(values: Sequence[object]) -> bool:
    return len(values) >= 2 and _is_serial(values[0])


def _is_outline(value: object) -> bool:
    return _is_serial(value) or (
        isinstance(value, str) and bool(_OUTLINE_RE.fullmatch(_normalized(value)))
    )


def _phrase_pattern(phrase: str, *, anchored: bool) -> re.Pattern[str]:
    token_separator = r"[\W_]+"
    escaped = token_separator.join(re.escape(token) for token in phrase.split())
    start = "^" if anchored else r"(?<![^\W_])"
    end = r"(?![^\W_])"
    return re.compile(f"{start}{escaped}{end}", re.UNICODE)


def _has_phrase(text: str, phrase: str, *, anchored: bool = False) -> bool:
    return bool(_phrase_pattern(phrase, anchored=anchored).search(text))


def _starts_anchored(text: str, prefix: str) -> bool:
    return _has_phrase(text, prefix, anchored=True)


class _MarkerEvidence(str, Enum):
    RECOGNIZED = "recognized"
    NONE = "none"
    AMBIGUOUS = "ambiguous"


def _classify_marker_text(text: str, *, surface: bool) -> RowClass | None:
    if surface:
        total_exact = _TOTAL_EXACT_SURFACE
        total_prefixes = _TOTAL_PREFIXES_SURFACE
        subtotal_prefixes = _SUBTOTAL_PREFIXES_SURFACE
        note_prefixes = _NOTE_PREFIXES_SURFACE
        section_prefixes = _SECTION_PREFIXES_SURFACE
    else:
        total_exact = _TOTAL_EXACT_SEARCH
        total_prefixes = _TOTAL_PREFIXES_SEARCH
        subtotal_prefixes = _SUBTOTAL_PREFIXES_SEARCH
        note_prefixes = _NOTE_PREFIXES_SEARCH
        section_prefixes = _SECTION_PREFIXES_SEARCH
    if text in total_exact or any(_starts_anchored(text, item) for item in total_prefixes):
        return RowClass.TOTAL
    if any(_starts_anchored(text, item) for item in subtotal_prefixes):
        return RowClass.SUBTOTAL
    if text.startswith("*") or any(_starts_anchored(text, item) for item in note_prefixes):
        return RowClass.NOTE
    if any(_starts_anchored(text, item) for item in section_prefixes):
        return RowClass.SECTION
    return None


def _marker_kind(values: Sequence[object]) -> tuple[_MarkerEvidence, RowClass | None]:
    """Return v3 tri-state marker evidence after an optional outline cell."""
    if not values:
        return _MarkerEvidence.NONE, None
    start_index = 1 if len(values) > 1 and _is_outline(values[0]) else 0
    marker_value = next(
        (value for value in values[start_index:] if isinstance(value, str) and _display(value)),
        None,
    )
    if marker_value is None:
        return _MarkerEvidence.NONE, None
    surface = _surface_normalized(marker_value)
    # The corporation exception is intentionally surface-only: ASCII folding cannot
    # distinguish it from common total phrases such as "tổng cộng tỷ lệ".
    if _starts_anchored(surface, "tổng công ty"):
        return _MarkerEvidence.NONE, None
    surface_kind = _classify_marker_text(surface, surface=True)
    if surface_kind is not None:
        return _MarkerEvidence.RECOGNIZED, surface_kind
    search = _search_normalized(marker_value)
    search_kind = _classify_marker_text(search, surface=False)
    if search_kind is None:
        return _MarkerEvidence.NONE, None
    if _starts_anchored(search, "tong cong ty"):
        return _MarkerEvidence.AMBIGUOUS, None
    return _MarkerEvidence.RECOGNIZED, search_kind


def classify_row(row: Sequence[CellValue]) -> RowClassification:
    """Classify one physical row without semantic mapping or staging mutation."""
    row_number = row[0].row if row else 0
    values = _nonempty_values(row)
    if not values:
        return RowClassification(row_number, RowClass.EMPTY, 1.0, ("no_nonempty_cells",))

    marker_evidence, marker = _marker_kind(values)
    if marker_evidence is _MarkerEvidence.RECOGNIZED and marker is not None:
        return RowClassification(row_number, marker, 0.98, (f"{marker.value}_marker",))
    if marker_evidence is _MarkerEvidence.AMBIGUOUS:
        return RowClassification(
            row_number,
            RowClass.UNRESOLVED,
            0.35,
            ("ambiguous_folded_marker",),
        )
    if _strong_asset_signature(values):
        return RowClassification(
            row_number,
            RowClass.ASSET,
            0.94,
            ("serial_number_and_content",),
        )
    has_text = any(isinstance(value, str) for value in values)
    has_numeric = any(_is_numeric(value) for value in values)
    if has_text and has_numeric:
        return RowClassification(
            row_number,
            RowClass.UNRESOLVED,
            0.40,
            ("mixed_text_numeric_without_serial",),
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


def _slice_row(row: Sequence[CellValue], min_column: int, max_column: int) -> tuple[CellValue, ...]:
    return tuple(cell for cell in row if min_column <= cell.column <= max_column)


def _header_row_eligible(row: Sequence[CellValue]) -> bool:
    values = _nonempty_values(row)
    marker_evidence, _marker = _marker_kind(values)
    if (
        not values
        or marker_evidence is not _MarkerEvidence.NONE
        or _strong_asset_signature(values)
    ):
        return False
    return not any(
        cell.cell_type in {"number", "boolean", "datetime"}
        or isinstance(cell.value, bool)
        or _is_numeric(cell.value)
        or isinstance(cell.value, (date, datetime))
        for cell in _nonempty_cells(row)
    )


def _occupied_column_runs(
    span: Sequence[Sequence[CellValue]],
    following_rows: Sequence[Sequence[CellValue]],
    separator_run: int,
) -> list[tuple[int, int]]:
    occupied = {
        cell.column
        for row in (*span, *following_rows)
        for cell in row
        if _display(cell.value)
    }
    if not occupied:
        return []
    runs: list[tuple[int, int]] = []
    start = previous = min(occupied)
    required_gap = max(1, separator_run)
    for column in sorted(occupied)[1:]:
        if column - previous - 1 >= required_gap:
            runs.append((start, previous))
            start = column
        previous = column
    runs.append((start, previous))
    return runs


def _span_labels(
    span: Sequence[Sequence[CellValue]],
    min_column: int,
    max_column: int,
) -> tuple[str | None, ...]:
    labels: list[str | None] = []
    for column in range(min_column, max_column + 1):
        parts: list[str] = []
        for row in span:
            value = next((_display(cell.value) for cell in row if cell.column == column), "")
            if value and value not in parts:
                parts.append(value)
        labels.append(" / ".join(parts) if parts else None)
    return tuple(labels)


def _header_vocabulary_hits(labels: Sequence[str | None]) -> int:
    return sum(
        1
        for label in labels
        if (normalized := _search_normalized(label))
        and any(_has_phrase(normalized, term) for term in _HEADER_TERMS)
    )


def _header_roles(label: str | None) -> frozenset[str]:
    normalized = _search_normalized(label)
    if not normalized:
        return frozenset()
    return frozenset(
        family
        for family, phrases in _HEADER_ROLE_PHRASES.items()
        if any(_has_phrase(normalized, phrase) for phrase in phrases)
    )


def _complete_header_group(
    roles: Sequence[frozenset[str]],
    start: int,
    end: int,
    config: StructureRuleConfig,
) -> bool:
    group_roles = set().union(*roles[start : end + 1])
    evidence_columns = sum(bool(item) for item in roles[start : end + 1])
    return (
        bool(group_roles & {"START_INDEX", "START_ID"})
        and "NAME" in group_roles
        and bool(group_roles & {"MEASURE", "UNIT", "VALUE", "DESCRIPTION"})
        and len(group_roles) >= config.header_group_min_families
        and evidence_columns >= config.header_group_min_columns
    )


def _repeated_core_bundles(
    labels: Sequence[str | None],
    roles: Sequence[frozenset[str]],
    config: StructureRuleConfig,
) -> bool:
    bundles: list[tuple[int, int]] = []
    auxiliaries = {"MEASURE", "UNIT", "VALUE"}
    for name_index, item in enumerate(roles):
        if "NAME" not in item:
            continue
        auxiliary_index = next(
            (
                index
                for index in range(name_index + 1, min(len(roles), name_index + 4))
                if roles[index] & auxiliaries
            ),
            None,
        )
        if auxiliary_index is None:
            continue
        lookback_start = max(0, name_index - config.header_group_start_lookback)
        if not any(labels[index] is not None for index in range(lookback_start, name_index)):
            continue
        if not bundles or name_index > bundles[-1][1]:
            bundles.append((name_index, auxiliary_index))
    return len(bundles) >= config.repeated_core_family_threshold


def _partition_header_run(
    labels: Sequence[str | None],
    config: StructureRuleConfig,
) -> list[tuple[int, int, tuple[str, ...]]]:
    """Return inclusive offsets for deterministic adjacent header groups."""
    roles = [_header_roles(label) for label in labels]
    anchors = [
        index
        for index, item in enumerate(roles)
        if item & {"START_INDEX", "START_ID"}
    ]
    complete: list[tuple[int, int]] = []
    for position, start in enumerate(anchors):
        end = anchors[position + 1] - 1 if position + 1 < len(anchors) else len(labels) - 1
        if _complete_header_group(roles, start, end, config):
            complete.append((start, end))
    if len(complete) >= 2:
        return [
            (start, end, ("multiple_horizontal_table_groups",))
            for start, end in complete
        ]
    flags = (
        ("ambiguous_horizontal_table_boundary",)
        if _repeated_core_bundles(labels, roles, config)
        else ()
    )
    return [(0, len(labels) - 1, flags)]


def _has_merged_title(summary: SheetSummary, header_start_row: int) -> bool:
    return any(
        region.max_row < header_start_row and region.max_col > region.min_col
        for region in summary.merged_regions
    )


def _candidates_for_span(
    *,
    summary: SheetSummary,
    span: Sequence[Sequence[CellValue]],
    following_rows: Sequence[Sequence[CellValue]],
    config: StructureRuleConfig,
) -> list[TableRegionCandidate]:
    if not span or len(span) > config.max_header_span or any(not _header_row_eligible(row) for row in span):
        return []
    header_start = span[0][0].row if span[0] else 0
    header_end = span[-1][0].row if span[-1] else 0
    if not header_start or not header_end:
        return []

    candidates: list[TableRegionCandidate] = []
    for run_min_column, run_max_column in _occupied_column_runs(
        span,
        following_rows,
        config.empty_column_separator_run,
    ):
        run_labels = _span_labels(span, run_min_column, run_max_column)
        for start_offset, end_offset, flags in _partition_header_run(run_labels, config):
            min_column = run_min_column + start_offset
            max_column = run_min_column + end_offset
            labels = run_labels[start_offset : end_offset + 1]
            nonempty_headers = sum(label is not None for label in labels)
            if nonempty_headers < 2:
                continue
            sliced_following = [
                _slice_row(row, min_column, max_column)
                for row in following_rows[: config.data_sample_rows]
            ]
            data_rows = [row for row in sliced_following if _nonempty_values(row)]
            width = max_column - min_column + 1
            header_density = nonempty_headers / width
            vocabulary_hits = _header_vocabulary_hits(labels)
            usable_rows = sum(len(_nonempty_values(row)) >= 2 for row in data_rows)
            consistent_ratio = usable_rows / len(data_rows) if data_rows else 0.0
            serial_ratio = (
                sum(_strong_asset_signature(_nonempty_values(row)) for row in data_rows)
                / len(data_rows)
                if data_rows
                else 0.0
            )
            type_mix_ratio = (
                sum(
                    any(isinstance(value, str) for value in _nonempty_values(row))
                    and any(_is_numeric(value) for value in _nonempty_values(row))
                    for row in data_rows
                )
                / len(data_rows)
                if data_rows
                else 0.0
            )
            merged_title = _has_merged_title(summary, header_start)
            score = (
                0.20 * min(header_density, 1.0)
                + 0.32 * min(vocabulary_hits / 4.0, 1.0)
                + 0.20 * consistent_ratio
                + 0.12 * serial_ratio
                + 0.11 * type_mix_ratio
                + (0.05 if merged_title else 0.0)
            )
            if len(span) > 1:
                score = min(1.0, score + 0.02)
            reasons: list[str] = ["header_density"]
            if vocabulary_hits:
                reasons.append("business_header_vocabulary")
            if consistent_ratio >= 0.5:
                reasons.append("consistent_subsequent_rows")
            if serial_ratio:
                reasons.append("serial_number_pattern")
            if type_mix_ratio:
                reasons.append("mixed_data_types")
            if merged_title:
                reasons.append("merged_title_above")
            if len(span) > 1:
                reasons.append("multi_row_header")
            candidates.append(
                TableRegionCandidate(
                    sheet_name=summary.name,
                    header_start_row=header_start,
                    header_end_row=header_end,
                    data_start_row=header_end + 1,
                    min_column=min_column,
                    max_column=max_column,
                    max_row=header_end,
                    confidence=round(min(max(score, 0.0), 1.0), 6),
                    reasons=tuple(reasons),
                    header_labels=tuple(labels),
                    boundary_flags=flags,
                )
            )
    return candidates


def _rank_candidates(
    inspection: AdapterInspectionResult,
    row_provider: RowProvider,
    config: StructureRuleConfig,
) -> tuple[list[TableRegionCandidate], tuple[str, ...]]:
    candidates: list[TableRegionCandidate] = []
    for summary in inspection.sheets:
        scanned = _bounded_rows(row_provider, summary.name, config.header_scan_rows)
        for start_index in range(len(scanned)):
            for span_size in range(1, config.max_header_span + 1):
                span = scanned[start_index : start_index + span_size]
                following = scanned[
                    start_index + span_size : start_index + span_size + config.column_evidence_sample
                ]
                candidates.extend(
                    _candidates_for_span(
                        summary=summary,
                        span=span,
                        following_rows=following,
                        config=config,
                    )
                )
    deduplicated: dict[tuple[str, int, int, int, int], TableRegionCandidate] = {}
    for candidate in candidates:
        key = (
            candidate.sheet_name,
            candidate.header_start_row,
            candidate.header_end_row,
            candidate.min_column,
            candidate.max_column,
        )
        retained = deduplicated.get(key)
        if retained is None or candidate.confidence > retained.confidence:
            union_flags = tuple(
                dict.fromkeys((*candidate.boundary_flags, *(retained.boundary_flags if retained else ())))
            )
            deduplicated[key] = replace(candidate, boundary_flags=union_flags)
        elif candidate.boundary_flags:
            deduplicated[key] = replace(
                retained,
                boundary_flags=tuple(dict.fromkeys((*retained.boundary_flags, *candidate.boundary_flags))),
            )
    candidates = list(deduplicated.values())
    fail_closed_flags = tuple(
        flag
        for flag in _FAIL_CLOSED_HORIZONTAL_FLAGS
        if any(flag in candidate.boundary_flags for candidate in candidates)
    )
    candidates.sort(
        key=lambda item: (
            -item.confidence,
            item.sheet_name.casefold(),
            item.header_start_row,
            item.header_end_row,
            item.min_column,
            item.max_column,
        )
    )
    return candidates[: config.candidate_limit], fail_closed_flags


def _overlaps(left: TableRegionCandidate, right: TableRegionCandidate) -> bool:
    return left.min_column <= right.max_column and right.min_column <= left.max_column


def _append_classification(state: _ResolutionState, classified: RowClassification, config: StructureRuleConfig) -> None:
    state.counts[classified.row_class.value] += 1
    state.physical_count += 1
    state.accepted_max_row = max(state.accepted_max_row, classified.row_number)
    if len(state.preview) < config.row_preview_limit:
        state.preview.append(classified.to_payload())


def _end_state(state: _ResolutionState, reason: str, flag: str | None = None) -> None:
    state.ended = True
    state.boundary_reason = reason
    if flag and flag not in state.boundary_flags:
        state.boundary_flags.append(flag)


def _maybe_extend_late_edge(
    state: _ResolutionState,
    row: Sequence[CellValue],
    config: StructureRuleConfig,
) -> None:
    if (
        config.late_blank_header_edge_extension < 1
        or row[0].row <= state.candidate.header_end_row + config.column_evidence_sample
    ):
        return
    left = state.candidate.min_column - 1
    right = state.candidate.max_column + 1
    cells = {cell.column: cell for cell in row if _display(cell.value)}
    edges = [name for name, column in (("left", left), ("right", right)) if column > 0 and column in cells]
    if not edges:
        return
    if state.extended_edge is not None or len(edges) > 1:
        if "ambiguous_horizontal_table_boundary" not in state.boundary_flags:
            state.boundary_flags.append("ambiguous_horizontal_table_boundary")
        return
    edge = edges[0]
    if edge == "left":
        state.candidate = replace(
            state.candidate,
            min_column=left,
            header_labels=(None, *state.candidate.header_labels),
        )
    else:
        state.candidate = replace(
            state.candidate,
            max_column=right,
            header_labels=(*state.candidate.header_labels, None),
        )
    state.extended_edge = edge
    if "late_blank_header_column_evidence" not in state.boundary_flags:
        state.boundary_flags.append("late_blank_header_column_evidence")


def _process_body_row(
    state: _ResolutionState,
    row: Sequence[CellValue],
    config: StructureRuleConfig,
) -> None:
    _maybe_extend_late_edge(state, row, config)
    sliced = _slice_row(row, state.candidate.min_column, state.candidate.max_column)
    classified = (
        classify_row(sliced)
        if sliced
        else RowClassification(row[0].row, RowClass.EMPTY, 1.0, ("no_nonempty_cells",))
    )

    if state.post_total:
        if classified.row_class in {
            RowClass.ASSET,
            RowClass.SECTION,
            RowClass.SUBTOTAL,
            RowClass.TOTAL,
        }:
            _end_state(state, "terminal_total", "content_after_terminal_total")
            return
        if state.post_total_count >= config.post_total_tail:
            _end_state(state, "terminal_total", "post_total_tail_exceeded")
            return
        _append_classification(state, classified, config)
        state.post_total_count += 1
        return

    if classified.row_class is RowClass.EMPTY:
        if state.pending_blank is None:
            state.pending_blank = classified
            return
        _end_state(state, "blank_run")
        state.pending_blank = None
        return
    if state.pending_blank is not None:
        _append_classification(state, state.pending_blank, config)
        state.pending_blank = None

    if classified.row_class is RowClass.UNRESOLVED:
        state.unresolved_run += 1
    else:
        state.unresolved_run = 0
    if state.unresolved_run >= config.vertical_unresolved_boundary_run:
        _append_classification(state, classified, config)
        _end_state(state, "ambiguous", "ambiguous_vertical_table_boundary")
        return

    if classified.row_class in {RowClass.NOTE, RowClass.UNRESOLVED}:
        state.trailing_run += 1
        if state.trailing_run > config.trailing_note_unresolved_run:
            _end_state(state, "ambiguous", "trailing_non_asset_boundary")
            return
    elif classified.row_class in {RowClass.ASSET, RowClass.SECTION, RowClass.SUBTOTAL}:
        state.trailing_run = 0

    _append_classification(state, classified, config)
    if classified.row_class is RowClass.TOTAL:
        state.post_total = True


def _later_header(
    summary: SheetSummary,
    buffered: Sequence[Sequence[CellValue]],
    candidate: TableRegionCandidate,
    config: StructureRuleConfig,
) -> TableRegionCandidate | None:
    for span_size in range(1, config.max_header_span + 1):
        if len(buffered) < span_size:
            continue
        later = _candidates_for_span(
            summary=summary,
            span=buffered[:span_size],
            following_rows=buffered[span_size : span_size + config.data_sample_rows],
            config=config,
        )
        eligible = [item for item in later if item.confidence >= config.clear_threshold and _overlaps(item, candidate)]
        if eligible:
            return sorted(eligible, key=lambda item: (-item.confidence, item.min_column))[0]
    return None


def _resolve_candidates(
    inspection: AdapterInspectionResult,
    candidates: Sequence[TableRegionCandidate],
    row_provider: RowProvider,
    config: StructureRuleConfig,
) -> tuple[list[TableRegionCandidate], dict[int, dict]]:
    states = {
        index: _ResolutionState(candidate, Counter(), [])
        for index, candidate in enumerate(candidates)
    }
    for summary in inspection.sheets:
        sheet_states = [(index, state) for index, state in states.items() if state.candidate.sheet_name == summary.name]
        if not sheet_states:
            continue
        source = row_provider(summary.name)
        buffer: list[Sequence[CellValue]] = []
        try:
            for row in source:
                buffer.append(row)
                if len(buffer) <= config.max_header_span + config.data_sample_rows:
                    continue
                current = buffer.pop(0)
                window = [current, *buffer]
                for _index, state in sheet_states:
                    if state.ended or not current:
                        continue
                    row_number = current[0].row
                    if row_number < state.candidate.data_start_row:
                        continue
                    later = _later_header(summary, window, state.candidate, config)
                    if later is not None and later.header_start_row > state.candidate.header_end_row:
                        flag = (
                            "additional_table_beyond_header_scan"
                            if later.header_start_row > config.header_scan_rows
                            else None
                        )
                        _end_state(state, "next_header", flag)
                        continue
                    _process_body_row(state, current, config)
            while buffer:
                current = buffer.pop(0)
                window = [current, *buffer]
                for _index, state in sheet_states:
                    if state.ended or not current:
                        continue
                    row_number = current[0].row
                    if row_number < state.candidate.data_start_row:
                        continue
                    later = _later_header(summary, window, state.candidate, config)
                    if later is not None and later.header_start_row > state.candidate.header_end_row:
                        flag = (
                            "additional_table_beyond_header_scan"
                            if later.header_start_row > config.header_scan_rows
                            else None
                        )
                        _end_state(state, "next_header", flag)
                        continue
                    _process_body_row(state, current, config)
        finally:
            _close_iterator(source)

    resolved: list[TableRegionCandidate] = []
    classifications: dict[int, dict] = {}
    for index, state in states.items():
        if state.post_total and not state.ended:
            state.boundary_reason = "terminal_total"
        candidate = replace(
            state.candidate,
            max_row=state.accepted_max_row,
            boundary_reason=state.boundary_reason,
            boundary_flags=tuple(state.boundary_flags),
        )
        resolved.append(candidate)
        classifications[index] = {
            "sheet_name": candidate.sheet_name,
            "data_start_row": candidate.data_start_row,
            "candidate_table_bounds": candidate.to_payload()["candidate_table_bounds"],
            "physical_rows_classified": state.physical_count,
            "counts": {row_class.value: state.counts[row_class.value] for row_class in RowClass},
            "preview": state.preview,
            "preview_truncated": state.physical_count > len(state.preview),
        }
    return resolved, classifications


def analyze_workbook_structure(
    inspection: AdapterInspectionResult,
    row_provider: RowProvider,
    *,
    config: StructureRuleConfig = DEFAULT_STRUCTURE_RULES,
) -> dict:
    """Return canonical analysis payload from actual adapter output."""
    ranked, fail_closed_flags = _rank_candidates(inspection, row_provider, config)
    candidates, classifications = _resolve_candidates(inspection, ranked, row_provider, config)
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
        for flag in top.boundary_flags:
            if flag not in disposition_reasons:
                disposition_reasons.append(flag)
        for flag in fail_closed_flags:
            if flag not in disposition_reasons:
                disposition_reasons.append(flag)
        if not disposition_reasons:
            disposition = StructureDisposition.PROPOSED

    classification = classifications.get(
        0,
        {
            "sheet_name": None,
            "data_start_row": None,
            "candidate_table_bounds": None,
            "physical_rows_classified": 0,
            "counts": {row_class.value: 0 for row_class in RowClass},
            "preview": [],
            "preview_truncated": False,
        },
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
    if primary_candidate_signature(payload) == primary_candidate_signature(previous_payload):
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
