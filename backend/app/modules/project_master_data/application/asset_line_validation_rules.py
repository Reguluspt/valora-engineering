"""Pinned official-line rules and proof facts; hashes use the shared serializer."""
from __future__ import annotations

from decimal import Decimal

from app.modules.project_master_data.application.asset_review_authority import canonical_digest

RULE_CONTRACT = "official-asset-line-validation-v1"
INPUT_FIELDS = ("asset_name", "description", "quantity", "unit_id", "raw_price",
                "raw_price_currency_id", "appraised_unit_price", "appraised_currency_id",
                "brand_id", "manufacturer_id")
REFERENCE_FIELDS = {"Unit": ("unit_id",), "Currency": ("raw_price_currency_id", "appraised_currency_id"),
                    "Brand": ("brand_id",), "Manufacturer": ("manufacturer_id",)}
RULE_MANIFEST = {
    "contract": RULE_CONTRACT, "input_fields": list(INPUT_FIELDS), "rules": [
        {"code": "asset_name_invalid", "severity": "error", "fields": ["asset_name"],
         "max_length": 255, "nonblank": True},
        {"code": "quantity_invalid", "severity": "error", "fields": ["quantity"],
         "precision": 15, "scale": 4, "minimum_exclusive": "0"},
        {"code": "description_invalid", "severity": "error", "fields": ["description"],
         "max_length": 5000, "null_allowed": True},
        {"code": "description_blank", "severity": "advisory", "fields": ["description"],
         "trimmed_empty": True, "null_allowed": True},
        {"code": "amount_invalid", "severity": "error", "fields": ["appraised_unit_price", "raw_price"],
         "precision": 15, "scale": 2, "minimum_inclusive": "0", "null_allowed": True},
        {"code": "reference_invalid", "severity": "error", "fields": sorted(
            field for fields in REFERENCE_FIELDS.values() for field in fields),
         "presence": True, "status": "active", "null_allowed": True},
    ],
}
for _rule in RULE_MANIFEST["rules"]:
    _rule["evaluator_id"] = _rule["code"] + "/v1"


def rule_digest():
    return canonical_digest(RULE_MANIFEST)


def value(value):
    return str(getattr(value, "value", value))


def canonical_value(item):
    if isinstance(item, Decimal):
        if not item.is_finite():
            return {"decimal_nonfinite": str(item)}
        return format(item.normalize(), "f") if item else "0"
    if item is None or isinstance(item, (str, bool, int)):
        return item
    # DB Numerics must be Decimal: retain type faults as facts, never coerce floats.
    if isinstance(item, float):
        return {"invalid_numeric_type": "float", "value": repr(item)}
    return str(item)


def input_digest(line):
    return canonical_digest({"line_id": str(line.id),
        "source_import_batch_id": str(line.source_import_batch_id) if line.source_import_batch_id else None,
        "source_staging_row_id": str(line.source_staging_row_id) if line.source_staging_row_id else None,
        "inputs": {field: canonical_value(getattr(line, field)) for field in INPUT_FIELDS}})


def line_reference_facts(line, references):
    return [{"type": kind, "id": str(ref_id),
             "exists": references.get((kind, ref_id)) is not None,
             "status": value(references[(kind, ref_id)].status) if references.get((kind, ref_id)) else None}
        for kind, fields in REFERENCE_FIELDS.items()
        for ref_id in sorted({getattr(line, field) for field in fields if getattr(line, field) is not None}, key=str)]


def exact_numeric(item, scale, *, positive=False):
    if not isinstance(item, Decimal) or not item.is_finite():
        return False
    if item <= 0 if positive else item < 0:
        return False
    normalized = item.normalize()
    return normalized.as_tuple().exponent >= -scale and normalized < Decimal(10) ** (15 - scale)


def evaluate_rules(line, references):
    findings = []

    def finding(code, field, severity="error", reference_id=None):
        findings.append({"code": code, "field": field, "severity": severity,
                         "reference_id": str(reference_id) if reference_id is not None else None})

    if not isinstance(line.asset_name, str) or not line.asset_name.strip() or len(line.asset_name) > 255:
        finding("asset_name_invalid", "asset_name")
    if not exact_numeric(line.quantity, 4, positive=True):
        finding("quantity_invalid", "quantity")
    description_valid = line.description is None or (
        isinstance(line.description, str) and len(line.description) <= 5000)
    if not description_valid:
        finding("description_invalid", "description")
    if isinstance(line.description, str) and not line.description.strip():
        finding("description_blank", "description", "advisory")
    for field in ("appraised_unit_price", "raw_price"):
        amount = getattr(line, field)
        if amount is not None and not exact_numeric(amount, 2):
            finding("amount_invalid", field)
    for field, kind in sorted((field, kind) for kind, fields in REFERENCE_FIELDS.items() for field in fields):
        ref_id = getattr(line, field)
        ref = references.get((kind, ref_id))
        if ref_id is not None and (ref is None or value(ref.status) != "active"):
            finding("reference_invalid", field, reference_id=ref_id)
    outcome = "invalid" if any(f["severity"] == "error" for f in findings) else "warning" if findings else "valid"
    return outcome, findings
