"""Deterministic staging validation rules for S12-PR-003 v1."""
from __future__ import annotations

from decimal import Decimal, InvalidOperation
from typing import Any

RULE_SET_VERSION = "s12-pr-003-v1"

MSG_ASSET_NAME_REQUIRED = {
    "field": "proposed_asset_name",
    "message_key": "excel.validation.asset_name_required",
    "message": "Tên tài sản là bắt buộc.",
}

MSG_QUANTITY_INVALID = {
    "field": "proposed_quantity",
    "message_key": "excel.validation.quantity_invalid",
    "message": "Số lượng không đúng định dạng số.",
}


def _as_text(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def validate_asset_name(proposed_asset_name: Any) -> dict | None:
    """Return error object if asset name fails V1-001; else None.

    Trims only for evaluation; never rewrites the stored value.
    """
    text = _as_text(proposed_asset_name)
    if text is None or text.strip() == "":
        return dict(MSG_ASSET_NAME_REQUIRED)
    return None


def is_finite_decimal_text(trimmed: str) -> bool:
    """True when trimmed text parses as a finite Decimal."""
    try:
        value = Decimal(trimmed)
    except (InvalidOperation, ValueError):
        return False
    return value.is_finite()


def validate_quantity(proposed_quantity: Any) -> dict | None:
    """Return error object if quantity fails V1-002; else None.

    Null/empty/whitespace-only is valid. Does not rewrite stored value.
    """
    text = _as_text(proposed_quantity)
    if text is None:
        return None
    trimmed = text.strip()
    if trimmed == "":
        return None
    if not is_finite_decimal_text(trimmed):
        return dict(MSG_QUANTITY_INVALID)
    return None


def evaluate_row(proposed_asset_name: Any, proposed_quantity: Any) -> tuple[str, list[dict], list[dict]]:
    """Return (status, errors, warnings) for one staging row.

    Status is ``valid`` or ``invalid``. Warnings are always empty in v1.
    Errors are ordered: asset name, then quantity.
    """
    errors: list[dict] = []
    name_err = validate_asset_name(proposed_asset_name)
    if name_err is not None:
        errors.append(name_err)
    qty_err = validate_quantity(proposed_quantity)
    if qty_err is not None:
        errors.append(qty_err)
    status = "invalid" if errors else "valid"
    return status, errors, []
