"""Pure S13-PR-004 Column Mapping Memory contract.

This module intentionally has no SQLAlchemy, FastAPI, object-storage, or provider dependency.
"""
from __future__ import annotations

import hashlib
import json
import math
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum
from typing import Any, Iterable, Mapping, Sequence

from app.modules.excel_import.domain.workbook_adapter import CellValue

MAPPING_CONTRACT_VERSION = "s13-pr-004-v1"
FINGERPRINT_CONTRACT_VERSION = "s13-pr-004-fingerprint-v1"
SIMILARITY_CONTRACT_VERSION = "s13-pr-004-similarity-v1"
MATERIALIZATION_CONTRACT_VERSION = "s13-pr-004-materialization-v1"
SUPPORTED_STRUCTURE_RULE_VERSION = "s13-pr-003-v3"


class SemanticRole(str, Enum):
    ROW_NUMBER = "row_number"
    RAW_ASSET_NAME = "raw_asset_name"
    RAW_DESCRIPTION = "raw_description"
    UNIT = "unit"
    QUANTITY = "quantity"
    CUSTOMER_UNIT_PRICE = "customer_unit_price"
    CUSTOMER_AMOUNT = "customer_amount"
    REFERENCE_VALUE = "reference_value"
    APPRAISER_PROPOSED_PRICE = "appraiser_proposed_price"
    EVIDENCE_NOTE = "evidence_note"
    IGNORE = "ignore"


class ColumnMappingContractError(ValueError):
    def __init__(self, error_code: str, detail: str):
        self.error_code = error_code
        self.detail = detail
        super().__init__(detail)


@dataclass(frozen=True)
class MappingField:
    source_column_index: int
    source_column_letter: str
    original_header: str | None
    semantic_role: SemanticRole

    def to_snapshot(self) -> dict[str, Any]:
        return {
            "source_column_index": self.source_column_index,
            "source_column_letter": self.source_column_letter,
            "original_header": self.original_header,
            "semantic_role": self.semantic_role.value,
        }


@dataclass(frozen=True)
class MappingSuggestion:
    fields: tuple[MappingField, ...]
    review_required: bool
    reasons: tuple[str, ...]


@dataclass(frozen=True)
class SimilarTemplateResult:
    qualifies: bool
    fields: tuple[MappingField, ...]
    unresolved_positions: tuple[int, ...]


_SYNONYMS: dict[SemanticRole, tuple[str, ...]] = {
    SemanticRole.ROW_NUMBER: ("stt", "so thu tu"),
    SemanticRole.RAW_ASSET_NAME: ("ten tai san", "ten vat tu", "ten hang hoa"),
    SemanticRole.RAW_DESCRIPTION: ("dac diem", "quy cach", "mo ta"),
    SemanticRole.UNIT: ("dvt", "don vi tinh"),
    SemanticRole.QUANTITY: ("so luong", "khoi luong"),
    SemanticRole.CUSTOMER_UNIT_PRICE: ("don gia", "don gia khach hang"),
    SemanticRole.CUSTOMER_AMOUNT: ("thanh tien", "gia tri khach hang"),
    SemanticRole.REFERENCE_VALUE: ("gia tham khao", "gia tri tham khao"),
    SemanticRole.APPRAISER_PROPOSED_PRICE: ("gia td", "gia tham dinh"),
    SemanticRole.EVIDENCE_NOTE: ("ghi chu", "chu thich", "note"),
}
_ROLE_BY_SYNONYM = {
    synonym: role for role, synonyms in _SYNONYMS.items() for synonym in synonyms
}
_SNAPSHOT_KEYS = frozenset(
    {
        "contract_version",
        "source",
        "structure",
        "template_fingerprint_sha256",
        "candidate",
        "fields",
    }
)
_SOURCE_KEYS = frozenset({"source_artifact_id", "generation", "checksum_sha256"})
_STRUCTURE_KEYS = frozenset(
    {"structure_snapshot_id", "snapshot_version", "rule_version", "analysis_digest_sha256"}
)
_CANDIDATE_KEYS = frozenset(
    {
        "candidate_index",
        "sheet_name",
        "header_start_row",
        "header_end_row",
        "data_start_row",
        "min_row",
        "max_row",
        "min_column",
        "max_column",
    }
)
_FIELD_KEYS = frozenset(
    {"source_column_index", "source_column_letter", "original_header", "semantic_role"}
)


def normalize_surface(value: object) -> str | None:
    if value is None:
        return None
    normalized = " ".join(unicodedata.normalize("NFKC", str(value)).strip().split()).casefold()
    return normalized or None


def normalize_header(value: object) -> str | None:
    surface = normalize_surface(value)
    if surface is None:
        return None
    decomposed = unicodedata.normalize("NFD", surface)
    folded = "".join(ch for ch in decomposed if unicodedata.category(ch) != "Mn")
    normalized = " ".join(folded.replace("đ", "d").split())
    return normalized or None


def column_letter(index: int) -> str:
    if isinstance(index, bool) or not isinstance(index, int) or index <= 0:
        raise ColumnMappingContractError("mapping_candidate_invalid", "Vị trí cột không hợp lệ.")
    output = ""
    value = index
    while value:
        value, remainder = divmod(value - 1, 26)
        output = chr(65 + remainder) + output
    return output


def _strict_json(value: Any, path: str = "$") -> None:
    if value is None or isinstance(value, (str, bool, int)):
        return
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", f"Giá trị JSON không hữu hạn tại {path}."
            )
        return
    if isinstance(value, list):
        for index, item in enumerate(value):
            _strict_json(item, f"{path}[{index}]")
        return
    if isinstance(value, dict):
        for key, item in value.items():
            if not isinstance(key, str):
                raise ColumnMappingContractError(
                    "mapping_candidate_invalid", f"Khóa JSON không hợp lệ tại {path}."
                )
            _strict_json(item, f"{path}.{key}")
        return
    raise ColumnMappingContractError(
        "mapping_candidate_invalid", f"Kiểu giá trị không được hỗ trợ tại {path}."
    )


def canonical_json_bytes(value: Any) -> bytes:
    _strict_json(value)
    return json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")


def canonical_sha256(value: Any) -> str:
    return hashlib.sha256(canonical_json_bytes(value)).hexdigest()


def _candidate_bounds(candidate: Mapping[str, Any]) -> tuple[int, int, int, int]:
    bounds = candidate.get("candidate_table_bounds")
    if not isinstance(bounds, Mapping):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Vùng bảng được chọn không hợp lệ."
        )
    min_row = bounds.get("min_row")
    max_row = bounds.get("max_row")
    min_column = bounds.get("min_column")
    max_column = bounds.get("max_column")
    if (
        isinstance(min_row, bool)
        or isinstance(max_row, bool)
        or isinstance(min_column, bool)
        or isinstance(max_column, bool)
        or not isinstance(min_row, int)
        or not isinstance(max_row, int)
        or not isinstance(min_column, int)
        or not isinstance(max_column, int)
        or min_row <= 0
        or max_row < min_row
        or min_column <= 0
        or max_column < min_column
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Giới hạn cột của vùng bảng không hợp lệ."
        )
    return min_row, max_row, min_column, max_column


def candidate_geometry(candidate: Mapping[str, Any]) -> dict[str, Any]:
    min_row, max_row, min_column, max_column = _candidate_bounds(candidate)
    required_ints = ("header_start_row", "header_end_row", "data_start_row")
    values = {key: candidate.get(key) for key in required_ints}
    if any(isinstance(value, bool) or not isinstance(value, int) for value in values.values()):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Giới hạn dòng của vùng bảng không hợp lệ."
        )
    if not (
        values["header_start_row"] >= min_row
        and values["header_end_row"] >= values["header_start_row"]
        and values["data_start_row"] > values["header_end_row"]
        and values["data_start_row"] <= max_row
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Thứ tự vùng tiêu đề và dữ liệu không hợp lệ."
        )
    sheet_name = candidate.get("sheet_name")
    if not isinstance(sheet_name, str) or not sheet_name:
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Sheet được chọn không hợp lệ."
        )
    labels = candidate.get("header_labels")
    expected_width = max_column - min_column + 1
    if not isinstance(labels, list) or len(labels) != expected_width or any(
        label is not None and not isinstance(label, str) for label in labels
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Bằng chứng tiêu đề theo vị trí không hợp lệ."
        )
    return {
        "sheet_name": sheet_name,
        "header_start_row": values["header_start_row"],
        "header_end_row": values["header_end_row"],
        "data_start_row": values["data_start_row"],
        "min_row": min_row,
        "max_row": max_row,
        "min_column": min_column,
        "max_column": max_column,
        "header_labels": list(labels),
    }


def build_template_fingerprint(candidate: Mapping[str, Any], *, rule_version: str) -> str:
    if rule_version != SUPPORTED_STRUCTURE_RULE_VERSION:
        raise ColumnMappingContractError(
            "unsupported_structure_rule_version",
            "Phiên bản quy tắc cấu trúc chưa được hỗ trợ cho ánh xạ.",
        )
    geometry = candidate_geometry(candidate)
    payload = {
        "contract_version": FINGERPRINT_CONTRACT_VERSION,
        "structure_rule_version": rule_version,
        "sheet_name_normalized": normalize_surface(geometry["sheet_name"]),
        "header_start_row": geometry["header_start_row"],
        "header_end_row": geometry["header_end_row"],
        "data_start_row": geometry["data_start_row"],
        "min_column": geometry["min_column"],
        "max_column": geometry["max_column"],
        "header_labels_normalized_by_position": [
            normalize_header(label) for label in geometry["header_labels"]
        ],
    }
    return canonical_sha256(payload)


def suggest_mapping(candidate: Mapping[str, Any]) -> MappingSuggestion:
    geometry = candidate_geometry(candidate)
    provisional: list[MappingField] = []
    reasons: list[str] = []
    for offset, header in enumerate(geometry["header_labels"]):
        position = geometry["min_column"] + offset
        normalized = normalize_header(header)
        role = _ROLE_BY_SYNONYM.get(normalized, SemanticRole.IGNORE)
        if normalized is None:
            reasons.append(f"blank_header:{position}")
        elif role is SemanticRole.IGNORE:
            reasons.append(f"unknown_header:{position}")
        provisional.append(MappingField(position, column_letter(position), header, role))

    role_positions: dict[SemanticRole, list[int]] = {}
    for index, field in enumerate(provisional):
        if field.semantic_role is not SemanticRole.IGNORE:
            role_positions.setdefault(field.semantic_role, []).append(index)
    for role, indices in role_positions.items():
        if len(indices) > 1:
            reasons.append(f"duplicate_role:{role.value}")
            for index in indices:
                field = provisional[index]
                provisional[index] = MappingField(
                    field.source_column_index,
                    field.source_column_letter,
                    field.original_header,
                    SemanticRole.IGNORE,
                )
    if sum(field.semantic_role is SemanticRole.RAW_ASSET_NAME for field in provisional) != 1:
        reasons.append("raw_asset_name_unresolved")
    return MappingSuggestion(tuple(provisional), bool(reasons), tuple(dict.fromkeys(reasons)))


def validate_mapping_fields(
    fields: Iterable[MappingField | Mapping[str, Any]], *, min_column: int, max_column: int
) -> tuple[MappingField, ...]:
    parsed: list[MappingField] = []
    for raw in fields:
        if isinstance(raw, MappingField):
            field = raw
        elif isinstance(raw, Mapping):
            if frozenset(raw) != _FIELD_KEYS:
                raise ColumnMappingContractError(
                    "mapping_candidate_invalid", "Trường ánh xạ chứa thuộc tính không hợp lệ."
                )
            try:
                role = SemanticRole(raw["semantic_role"])
            except (ValueError, TypeError) as exc:
                raise ColumnMappingContractError(
                    "mapping_role_invalid", "Vai trò cột không hợp lệ."
                ) from exc
            field = MappingField(
                source_column_index=raw["source_column_index"],
                source_column_letter=raw["source_column_letter"],
                original_header=raw["original_header"],
                semantic_role=role,
            )
        else:
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", "Trường ánh xạ không hợp lệ."
            )
        if (
            isinstance(field.source_column_index, bool)
            or not isinstance(field.source_column_index, int)
            or not min_column <= field.source_column_index <= max_column
            or field.source_column_letter != column_letter(field.source_column_index)
            or (field.original_header is not None and not isinstance(field.original_header, str))
        ):
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", "Vị trí hoặc bằng chứng cột không hợp lệ."
            )
        parsed.append(field)

    expected = list(range(min_column, max_column + 1))
    positions = [field.source_column_index for field in parsed]
    if len(set(positions)) != len(positions) or sorted(positions) != expected:
        raise ColumnMappingContractError(
            "mapping_role_cardinality_invalid",
            "Mỗi vị trí cột phải xuất hiện đúng một lần trong ánh xạ.",
        )
    counts = Counter(field.semantic_role for field in parsed)
    if counts[SemanticRole.RAW_ASSET_NAME] != 1 or any(
        count > 1 for role, count in counts.items() if role is not SemanticRole.IGNORE
    ):
        raise ColumnMappingContractError(
            "mapping_role_cardinality_invalid", "Số lượng vai trò cột không hợp lệ."
        )
    return tuple(sorted(parsed, key=lambda item: item.source_column_index))


def build_mapping_snapshot(
    *,
    source_artifact_id: str,
    source_generation: int,
    source_checksum_sha256: str,
    structure_snapshot_id: str,
    snapshot_version: int,
    structure_rule_version: str,
    structure_digest_sha256: str,
    candidate_index: int,
    candidate: Mapping[str, Any],
    fields: Iterable[MappingField | Mapping[str, Any]],
) -> dict[str, Any]:
    geometry = candidate_geometry(candidate)
    parsed = validate_mapping_fields(
        fields, min_column=geometry["min_column"], max_column=geometry["max_column"]
    )
    for offset, field in enumerate(parsed):
        expected_header = geometry["header_labels"][offset]
        if field.original_header != expected_header:
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", "Bằng chứng tiêu đề không khớp snapshot."
            )
    if (
        isinstance(candidate_index, bool)
        or not isinstance(candidate_index, int)
        or candidate_index < 0
        or isinstance(source_generation, bool)
        or not isinstance(source_generation, int)
        or source_generation <= 0
        or isinstance(snapshot_version, bool)
        or not isinstance(snapshot_version, int)
        or snapshot_version <= 0
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Phiên bản nguồn hoặc snapshot không hợp lệ."
        )
    fingerprint = build_template_fingerprint(candidate, rule_version=structure_rule_version)
    snapshot = {
        "contract_version": MAPPING_CONTRACT_VERSION,
        "source": {
            "source_artifact_id": str(source_artifact_id),
            "generation": source_generation,
            "checksum_sha256": source_checksum_sha256,
        },
        "structure": {
            "structure_snapshot_id": str(structure_snapshot_id),
            "snapshot_version": snapshot_version,
            "rule_version": structure_rule_version,
            "analysis_digest_sha256": structure_digest_sha256,
        },
        "template_fingerprint_sha256": fingerprint,
        "candidate": {
            "candidate_index": candidate_index,
            "sheet_name": geometry["sheet_name"],
            "header_start_row": geometry["header_start_row"],
            "header_end_row": geometry["header_end_row"],
            "data_start_row": geometry["data_start_row"],
            "min_row": geometry["min_row"],
            "max_row": geometry["max_row"],
            "min_column": geometry["min_column"],
            "max_column": geometry["max_column"],
        },
        "fields": [field.to_snapshot() for field in parsed],
    }
    validate_mapping_snapshot(snapshot)
    return snapshot


def validate_mapping_snapshot(snapshot: Mapping[str, Any]) -> tuple[MappingField, ...]:
    if not isinstance(snapshot, Mapping) or frozenset(snapshot) != _SNAPSHOT_KEYS:
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Snapshot ánh xạ chứa thuộc tính không hợp lệ."
        )
    if snapshot.get("contract_version") != MAPPING_CONTRACT_VERSION:
        raise ColumnMappingContractError(
            "mapping_role_invalid", "Phiên bản hợp đồng ánh xạ không được hỗ trợ."
        )
    source = snapshot.get("source")
    structure = snapshot.get("structure")
    candidate = snapshot.get("candidate")
    if (
        not isinstance(source, Mapping)
        or frozenset(source) != _SOURCE_KEYS
        or not isinstance(structure, Mapping)
        or frozenset(structure) != _STRUCTURE_KEYS
        or not isinstance(candidate, Mapping)
        or frozenset(candidate) != _CANDIDATE_KEYS
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Lineage của snapshot ánh xạ không hợp lệ."
        )
    fingerprint = snapshot.get("template_fingerprint_sha256")
    digests = (
        source.get("checksum_sha256"),
        structure.get("analysis_digest_sha256"),
        fingerprint,
    )
    if any(
        not isinstance(value, str)
        or len(value) != 64
        or value != value.lower()
        or any(ch not in "0123456789abcdef" for ch in value)
        for value in digests
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Mã kiểm tra của snapshot ánh xạ không hợp lệ."
        )
    if structure.get("rule_version") != SUPPORTED_STRUCTURE_RULE_VERSION:
        raise ColumnMappingContractError(
            "unsupported_structure_rule_version",
            "Phiên bản quy tắc cấu trúc chưa được hỗ trợ cho ánh xạ.",
        )
    min_row = candidate.get("min_row")
    max_row = candidate.get("max_row")
    min_column = candidate.get("min_column")
    max_column = candidate.get("max_column")
    if (
        isinstance(min_row, bool)
        or isinstance(max_row, bool)
        or isinstance(min_column, bool)
        or isinstance(max_column, bool)
        or not isinstance(min_row, int)
        or not isinstance(max_row, int)
        or not isinstance(min_column, int)
        or not isinstance(max_column, int)
        or min_row <= 0
        or max_row < min_row
        or min_column <= 0
        or max_column < min_column
    ):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Giới hạn cột trong snapshot ánh xạ không hợp lệ."
        )
    raw_fields = snapshot.get("fields")
    if not isinstance(raw_fields, list):
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Danh sách trường ánh xạ không hợp lệ."
        )
    parsed = validate_mapping_fields(raw_fields, min_column=min_column, max_column=max_column)
    sealed_candidate = {
        "sheet_name": candidate.get("sheet_name"),
        "header_start_row": candidate.get("header_start_row"),
        "header_end_row": candidate.get("header_end_row"),
        "data_start_row": candidate.get("data_start_row"),
        "candidate_table_bounds": {
            "min_row": min_row,
            "max_row": max_row,
            "min_column": min_column,
            "max_column": max_column,
        },
        "header_labels": [field.original_header for field in parsed],
    }
    computed_fingerprint = build_template_fingerprint(
        sealed_candidate, rule_version=structure.get("rule_version")
    )
    if computed_fingerprint != fingerprint:
        raise ColumnMappingContractError(
            "mapping_candidate_invalid", "Hình học hoặc tiêu đề không khớp fingerprint."
        )
    canonical_json_bytes(dict(snapshot))
    return parsed


def mapping_digest(snapshot: Mapping[str, Any]) -> str:
    validate_mapping_snapshot(snapshot)
    return canonical_sha256(dict(snapshot))


def mapping_summary(snapshot: Mapping[str, Any]) -> dict[str, Any]:
    fields = validate_mapping_snapshot(snapshot)
    counts = Counter(field.semantic_role.value for field in fields)
    return {
        "mapping_digest_sha256": mapping_digest(snapshot),
        "field_count": len(fields),
        "role_counts": {key: counts[key] for key in sorted(counts)},
    }


def profile_mapping_digest(
    candidate: Mapping[str, Any], fields: Iterable[MappingField | Mapping[str, Any]]
) -> str:
    """Digest reusable semantics without binding them to one import generation."""
    geometry = candidate_geometry(candidate)
    parsed = validate_mapping_fields(
        fields, min_column=geometry["min_column"], max_column=geometry["max_column"]
    )
    payload = {
        "contract_version": MAPPING_CONTRACT_VERSION,
        "sheet_name_normalized": normalize_surface(geometry["sheet_name"]),
        "header_start_row": geometry["header_start_row"],
        "header_end_row": geometry["header_end_row"],
        "data_start_row": geometry["data_start_row"],
        "min_column": geometry["min_column"],
        "max_column": geometry["max_column"],
        "fields": [
            {
                "source_column_index": field.source_column_index,
                "source_column_letter": field.source_column_letter,
                "normalized_header": normalize_header(field.original_header),
                "semantic_role": field.semantic_role.value,
            }
            for field in parsed
        ],
    }
    return canonical_sha256(payload)


def similar_template_remap(
    *,
    current_headers: Sequence[str | None],
    current_min_column: int,
    current_header_height: int,
    profile_fields: Sequence[MappingField],
    profile_headers: Sequence[str | None],
    profile_header_height: int,
) -> SimilarTemplateResult:
    if (
        len(current_headers) != len(profile_headers)
        or current_header_height != profile_header_height
        or len(profile_fields) != len(profile_headers)
    ):
        return SimilarTemplateResult(False, (), ())
    current_normalized = [normalize_header(value) for value in current_headers]
    profile_normalized = [normalize_header(value) for value in profile_headers]
    if Counter(value for value in current_normalized if value is not None) != Counter(
        value for value in profile_normalized if value is not None
    ):
        return SimilarTemplateResult(False, (), ())
    current_non_null = [value for value in current_normalized if value is not None]
    profile_non_null = [value for value in profile_normalized if value is not None]
    if len(set(current_non_null)) != len(current_non_null) or len(set(profile_non_null)) != len(
        profile_non_null
    ):
        return SimilarTemplateResult(False, (), ())
    role_by_label = {
        profile_normalized[index]: profile_fields[index].semantic_role
        for index in range(len(profile_fields))
        if profile_normalized[index] is not None
    }
    output: list[MappingField] = []
    unresolved: list[int] = []
    for offset, header in enumerate(current_headers):
        position = current_min_column + offset
        normalized = current_normalized[offset]
        role = role_by_label.get(normalized, SemanticRole.IGNORE)
        if normalized is None:
            unresolved.append(position)
        output.append(MappingField(position, column_letter(position), header, role))
    return SimilarTemplateResult(True, tuple(output), tuple(unresolved))


def json_safe_scalar(value: Any) -> Any:
    if value is None or isinstance(value, (str, bool, int)):
        return value
    if isinstance(value, Decimal):
        if not value.is_finite():
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", "Giá trị số không hữu hạn không được hỗ trợ."
            )
        return format(value, "f")
    if isinstance(value, float):
        if not math.isfinite(value):
            raise ColumnMappingContractError(
                "mapping_candidate_invalid", "Giá trị số không hữu hạn không được hỗ trợ."
            )
        # BIFF exposes all ordinary numeric cells as float while OOXML may expose an int.
        # Canonicalize exactly integral values so .xls/.xlsx value-only replay is identical.
        return int(value) if value.is_integer() else value
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    raise ColumnMappingContractError(
        "mapping_candidate_invalid", "Kiểu ô dữ liệu không được hỗ trợ."
    )


def staging_text(value: Any) -> str | None:
    safe = json_safe_scalar(value)
    if safe is None:
        return None
    if isinstance(safe, bool):
        return "true" if safe else "false"
    return str(safe)


def project_asset_row(
    row: Sequence[CellValue], fields: Sequence[MappingField]
) -> dict[str, Any]:
    by_column = {cell.column: cell.value for cell in row}
    raw_values: dict[str, Any] = {}
    mapped_values: dict[str, Any] = {}
    for field in fields:
        value = by_column.get(field.source_column_index)
        safe = json_safe_scalar(value)
        raw_values[f"column_{field.source_column_index:04d}"] = safe
        if field.semantic_role is not SemanticRole.IGNORE:
            mapped_values[field.semantic_role.value] = safe

    def role_text(role: SemanticRole) -> str | None:
        field = next((item for item in fields if item.semantic_role is role), None)
        return staging_text(by_column.get(field.source_column_index)) if field else None

    source_row_number = row[0].row if row else 0
    return {
        "source_row_number": source_row_number,
        "raw_values": raw_values,
        "mapped_values": mapped_values,
        "proposed_asset_name": role_text(SemanticRole.RAW_ASSET_NAME),
        "proposed_description": role_text(SemanticRole.RAW_DESCRIPTION),
        "proposed_quantity": role_text(SemanticRole.QUANTITY),
        "proposed_unit": role_text(SemanticRole.UNIT),
        "proposed_raw_price": role_text(SemanticRole.CUSTOMER_UNIT_PRICE),
        "proposed_currency": None,
        "proposed_appraised_unit_price": role_text(
            SemanticRole.APPRAISER_PROPOSED_PRICE
        ),
        "proposed_review_status": None,
        "proposed_validation_status": None,
    }
