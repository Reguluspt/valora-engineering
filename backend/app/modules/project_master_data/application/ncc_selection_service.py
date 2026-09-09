"""Tenant-safe NCC Selection confirmation command (ADR 0039 D1-D7).

This module provides an internal application service for creating immutable NCC Selection
revisions and maintaining one current head per project asset line. It does not expose a public
API and does not mutate AppraisedPriceDecision.
"""
from __future__ import annotations

import hashlib
import json
import uuid
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.project_master_data.models import (
    EvidenceFile,
    EvidenceFileStatus,
    NccSelectionCurrentHead,
    NccSelectionRevision,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetLine,
    QuoteBatch,
    QuoteBatchStatus,
    QuoteLine,
    QuoteLineStatus,
    Supplier,
    SupplierStatus,
    Unit,
    User,
    UserRole,
    UserStatus,
)


NCC_SELECTION_CONFIRM_PERMISSION = "project:update"

EVENT_NCC_SELECTION_CONFIRMED = "NCC_SELECTION_CONFIRMED"
EVENT_NCC_SELECTION_CHANGED = "NCC_SELECTION_CHANGED"
EVENT_NCC_SELECTION_RECONFIRMED = "NCC_SELECTION_RECONFIRMED"

WARNING_NCC_BELOW_CURRENT_PRICE = "NCC_BELOW_CURRENT_PRICE"
WARNING_NCC_DIFFERENCE_OVER_15_PERCENT = "NCC_DIFFERENCE_OVER_15_PERCENT"


class SelectionError(Exception):
    """Internal domain error for NCC selection command."""


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _canonical_json(payload: dict | list) -> bytes:
    return json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")


def _sha256_hex(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _finite_positive_decimal(value: Any) -> Decimal | None:
    """Return a positive finite Decimal or None if the value is not usable as a price."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not dec.is_finite() or dec <= 0:
        return None
    return dec


def _finite_nonnegative_decimal(value: Any) -> Decimal | None:
    """Return a finite non-negative Decimal or None for an invalid current price."""
    if isinstance(value, bool) or value is None:
        return None
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
    if not dec.is_finite() or dec < 0:
        return None
    return dec


def _blank(value: Any) -> bool:
    return value is None or (isinstance(value, str) and value.strip() == "")


def _reload_active_actor_and_org(
    db: Session, *, actor: User, org_id: uuid.UUID
) -> User:
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == org_id)
        .populate_existing()
        .first()
    )
    actor_id = getattr(actor, "id", None)
    persisted_actor = None
    if actor_id is not None:
        persisted_actor = (
            db.query(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(UserRole.role),
            )
            .filter(User.id == actor_id, User.organization_id == org_id)
            .populate_existing()
            .first()
        )
    if (
        persisted_actor is None
        or organization is None
        or _status_value(persisted_actor.status) != UserStatus.ACTIVE.value
        or _status_value(organization.status) != OrganizationStatus.ACTIVE.value
    ):
        _abort(db, 403, "ncc_selection_forbidden", "Không thể thực hiện thao tác này.")
    if NCC_SELECTION_CONFIRM_PERMISSION not in derive_effective_permissions(
        persisted_actor, db
    ):
        _abort(db, 403, "ncc_selection_forbidden", "Không thể thực hiện thao tác này.")
    return persisted_actor


def _compute_warnings(
    *, quoted_price: Decimal, current_price: Decimal | None
) -> tuple[list[str], Decimal | None, Decimal | None]:
    """Return warning codes, difference_amount and difference_percent per ADR 0039 D4."""
    if current_price is None:
        return [], None, None

    difference_amount = quoted_price - current_price

    if current_price == 0:
        return [], difference_amount, None

    try:
        difference_percent = (difference_amount / current_price) * Decimal("100")
        # Quantize to avoid float-like expansions in storage.
        difference_percent = difference_percent.quantize(Decimal("0.000001"))
    except InvalidOperation:
        difference_percent = None

    warnings: list[str] = []
    if quoted_price < current_price:
        warnings.append(WARNING_NCC_BELOW_CURRENT_PRICE)
    if difference_percent is not None and abs(difference_percent) > Decimal("15"):
        warnings.append(WARNING_NCC_DIFFERENCE_OVER_15_PERCENT)

    return warnings, difference_amount, difference_percent


@dataclass(frozen=True)
class _EligibleQuote:
    quote_line: QuoteLine
    supplier_id: uuid.UUID
    warnings: list[str]
    difference_amount: Decimal | None
    difference_percent: Decimal | None


def _find_eligible_quote(
    db: Session,
    *,
    org_id: uuid.UUID,
    project_asset_line: ProjectAssetLine,
    quote_line_id: uuid.UUID,
) -> _EligibleQuote:
    """Validate a QuoteLine as an eligible confirmed selection candidate (ADR 0039 D1-D2)."""
    quote_line = (
        db.query(QuoteLine)
        .filter(
            QuoteLine.id == quote_line_id,
            QuoteLine.organization_id == org_id,
        )
        .first()
    )
    if quote_line is None:
        raise SelectionError("quote_line_not_found", "Không tìm thấy dòng báo giá.")

    batch = quote_line.quote_batch
    if batch is None:
        raise SelectionError("quote_batch_not_found", "Không tìm thấy đợt báo giá.")

    if batch.organization_id != org_id:
        raise SelectionError("quote_batch_tenant_mismatch", "Đợt báo giá không thuộc tổ chức.")

    if _status_value(quote_line.status) != QuoteLineStatus.ACTIVE.value:
        raise SelectionError("quote_line_not_active", "Dòng báo giá chưa được kích hoạt.")

    if _status_value(batch.status) != QuoteBatchStatus.ACTIVE.value:
        raise SelectionError("quote_batch_not_active", "Đợt báo giá chưa được kích hoạt.")

    if batch.approved_by is None or batch.approved_at is None:
        raise SelectionError("quote_batch_not_confirmed", "Đợt báo giá chưa được xác nhận.")

    quoted_price = _finite_positive_decimal(quote_line.quoted_unit_price)
    if quoted_price is None:
        raise SelectionError("quote_price_invalid", "Đơn giá báo giá không hợp lệ.")

    if _blank(quote_line.currency):
        raise SelectionError("quote_currency_missing", "Thiếu loại tiền tệ của báo giá.")

    supplier_id = quote_line.supplier_id
    if supplier_id is None:
        raise SelectionError(
            "supplier_not_resolved",
            "Dòng báo giá chưa được gán nhà cung cấp.",
        )

    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.organization_id == org_id,
            Supplier.status == SupplierStatus.ACTIVE,
        )
        .first()
    )
    if supplier is None:
        raise SelectionError("supplier_not_active", "Nhà cung cấp không còn hoạt động.")

    if quote_line.evidence_file_id is None:
        raise SelectionError("evidence_missing", "Thiếu chứng cứ cho dòng báo giá.")

    evidence = (
        db.query(EvidenceFile)
        .filter(
            EvidenceFile.id == quote_line.evidence_file_id,
            EvidenceFile.status == EvidenceFileStatus.ACTIVE,
        )
        .first()
    )
    if evidence is None:
        raise SelectionError("evidence_not_active", "Chứng cứ không còn hiệu lực.")
    if evidence.uploader.organization_id != org_id:
        raise SelectionError("evidence_tenant_mismatch", "Chứng cứ không thuộc tổ chức.")

    # ADR 0039 D2: candidate matching uses approved asset identity only.
    if project_asset_line.approved_asset_variant_id is not None:
        if batch.asset_variant_id != project_asset_line.approved_asset_variant_id:
            raise SelectionError(
                "asset_identity_mismatch",
                "Báo giá không khớp với biến thể tài sản đã phê duyệt.",
            )
    else:
        if project_asset_line.approved_canonical_asset_id is None:
            raise SelectionError(
                "asset_line_no_identity",
                "Dòng tài sản chưa có danh tính tài sản được phê duyệt.",
            )
        if batch.canonical_asset_id != project_asset_line.approved_canonical_asset_id:
            raise SelectionError(
                "asset_identity_mismatch",
                "Báo giá không khớp với tài sản chuẩn đã phê duyệt.",
            )
        if batch.asset_variant_id is not None:
            raise SelectionError(
                "asset_identity_mismatch",
                "Báo giá liên kết biến thể không phù hợp với dòng tài sản.",
            )

    current_price: Decimal | None = None
    if project_asset_line.appraised_unit_price is not None:
        current_price = _finite_positive_decimal(project_asset_line.appraised_unit_price)
        # If appraised_unit_price is present but not a positive finite value, treat as null
        # rather than failing eligibility; warnings are non-blocking.
        if current_price is None:
            current_price = Decimal("0") if project_asset_line.appraised_unit_price == 0 else None

    warnings, difference_amount, difference_percent = _compute_warnings(
        quoted_price=quoted_price, current_price=current_price
    )

    return _EligibleQuote(
        quote_line=quote_line,
        supplier_id=supplier_id,
        warnings=warnings,
        difference_amount=difference_amount,
        difference_percent=difference_percent,
    )


def _optional_snapshot(value: Any) -> Any:
    """Return a deterministic JSON-serializable value for nullable snapshot facts."""
    if value is None:
        return None
    if isinstance(value, uuid.UUID):
        return str(value)
    if isinstance(value, Decimal):
        return str(value)
    return value


def _request_digest(
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    project_asset_line_id: uuid.UUID,
    quote_line_id: uuid.UUID,
    quote_batch_id: uuid.UUID,
    quote_batch_revision_number: int,
    expected_selection_revision: int,
    quoted_unit_price: Decimal,
    currency: str,
    quantity: Decimal | None,
    unit_of_measure: str | None,
    quote_date: Any,
    supplier_id: uuid.UUID,
    supplier_name: str,
    evidence_file_id: uuid.UUID,
    current_unit_price: Decimal | None,
    current_unit_price_currency_id: uuid.UUID | None,
    difference_amount: Decimal | None,
    difference_percent: Decimal | None,
    warning_codes: list[str],
    acknowledged_warning_codes: list[str],
) -> str:
    payload = {
        "acknowledged_warning_codes": sorted(acknowledged_warning_codes),
        "actor_id": str(actor_id),
        "contract": "ncc-selection-confirm-v1",
        "currency": currency,
        "current_unit_price": _optional_snapshot(current_unit_price),
        "current_unit_price_currency_id": _optional_snapshot(current_unit_price_currency_id),
        "difference_amount": _optional_snapshot(difference_amount),
        "difference_percent": _optional_snapshot(difference_percent),
        "evidence_file_id": str(evidence_file_id),
        "expected_selection_revision": expected_selection_revision,
        "organization_id": str(org_id),
        "project_asset_line_id": str(project_asset_line_id),
        "project_id": str(project_id),
        "quote_batch_id": str(quote_batch_id),
        "quote_batch_revision_number": quote_batch_revision_number,
        "quote_date": _optional_snapshot(quote_date.isoformat() if hasattr(quote_date, "isoformat") else quote_date),
        "quote_line_id": str(quote_line_id),
        "quoted_unit_price": str(quoted_unit_price),
        "quantity": _optional_snapshot(quantity),
        "supplier_id": str(supplier_id),
        "supplier_name": supplier_name,
        "unit_of_measure": unit_of_measure,
        "warning_codes": sorted(warning_codes),
    }
    return _sha256_hex(_canonical_json(payload))


def _same_request(
    revision: NccSelectionRevision,
    *,
    request_digest: str,
) -> bool:
    return revision.request_digest_sha256 == request_digest


def confirm_ncc_selection(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    project_asset_line_id: uuid.UUID,
    quote_line_id: uuid.UUID,
    expected_selection_revision: int,
    acknowledged_warning_codes: list[str] | None,
    idempotency_key: str,
    confirmed: bool,
    correlation_id: str | None = None,
) -> NccSelectionRevision:
    """Confirm an NCC Selection revision and atomically advance the current head.

    The command locks Project -> ProjectAssetLine -> current head in that order. It resolves
    eligibility, monetary values, supplier and warnings on the server. Acknowledged warning codes
    are stored but never suppress the snapshot warning fact.
    """
    if not confirmed:
        _abort(db, 400, "ncc_selection_confirmation_required", "Cần xác nhận thao tác.")

    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")

    if expected_selection_revision < 0:
        _abort(db, 422, "invalid_expected_selection_revision", "Phiên bản lựa chọn không hợp lệ.")

    raw_acknowledged = acknowledged_warning_codes or []
    for code in raw_acknowledged:
        if not isinstance(code, str) or not code.strip():
            _abort(db, 422, "invalid_warning_code", "Mã cảnh báo không hợp lệ.")
    acknowledged = sorted({code.strip() for code in raw_acknowledged})

    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)

    # Lock Project -> ProjectAssetLine in canonical order.
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    asset_line = (
        db.query(ProjectAssetLine)
        .filter(
            ProjectAssetLine.id == project_asset_line_id,
            ProjectAssetLine.project_id == project_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )
    if asset_line is None:
        _abort(db, 404, "project_asset_line_not_found", "Không tìm thấy dòng tài sản.")

    # Lock current head if it exists; create implicitly on first commit.
    current_head = (
        db.query(NccSelectionCurrentHead)
        .filter(
            NccSelectionCurrentHead.organization_id == org_id,
            NccSelectionCurrentHead.project_id == project_id,
            NccSelectionCurrentHead.project_asset_line_id == project_asset_line_id,
        )
        .with_for_update()
        .populate_existing()
        .first()
    )

    current_revision: NccSelectionRevision | None = None
    current_selection_revision = 0
    if current_head is not None:
        current_revision = current_head.current_revision
        current_selection_revision = current_head.selection_revision

    # Idempotency lookup under locks, before version check: a replay of the
    # exact request returns the same revision even if the head has advanced.
    existing_revision = (
        db.query(NccSelectionRevision)
        .filter(
            NccSelectionRevision.organization_id == org_id,
            NccSelectionRevision.idempotency_key == normalized_key,
        )
        .populate_existing()
        .first()
    )

    # Resolve eligibility and snapshot values server-side.
    try:
        eligible = _find_eligible_quote(
            db,
            org_id=org_id,
            project_asset_line=asset_line,
            quote_line_id=quote_line_id,
        )
    except SelectionError as exc:
        _abort(db, 409, exc.args[0], exc.args[1])

    quoted_price = _finite_positive_decimal(eligible.quote_line.quoted_unit_price)
    assert quoted_price is not None  # validated by _find_eligible_quote

    request_digest = _request_digest(
        actor_id=actor.id,
        org_id=org_id,
        project_id=project_id,
        project_asset_line_id=project_asset_line_id,
        quote_line_id=quote_line_id,
        quote_batch_id=eligible.quote_line.quote_batch_id,
        quote_batch_revision_number=eligible.quote_line.quote_batch.revision_number,
        expected_selection_revision=expected_selection_revision,
        quoted_unit_price=quoted_price,
        currency=eligible.quote_line.currency,
        quantity=eligible.quote_line.quantity,
        unit_of_measure=eligible.quote_line.unit_of_measure,
        quote_date=eligible.quote_line.quote_date,
        supplier_id=eligible.supplier_id,
        supplier_name=eligible.quote_line.supplier_name,
        evidence_file_id=eligible.quote_line.evidence_file_id,
        current_unit_price=_finite_nonnegative_decimal(asset_line.appraised_unit_price),
        current_unit_price_currency_id=asset_line.appraised_currency_id,
        difference_amount=eligible.difference_amount,
        difference_percent=eligible.difference_percent,
        warning_codes=eligible.warnings,
        acknowledged_warning_codes=acknowledged,
    )

    if existing_revision is not None:
        if _same_request(existing_revision, request_digest=request_digest):
            db.commit()
            db.refresh(existing_revision)
            return existing_revision
        _abort(
            db,
            409,
            "idempotency_key_reused",
            "Mã lệnh đã được dùng cho dữ liệu khác.",
        )

    if current_selection_revision != expected_selection_revision:
        _abort(
            db,
            409,
            "selection_revision_conflict",
            "Dữ liệu lựa chọn NCC đã thay đổi. Vui lòng tải lại và xác nhận lại.",
        )

    # Determine audit event from previous current head.
    if current_revision is None:
        event_name = EVENT_NCC_SELECTION_CONFIRMED
    elif current_revision.quote_line_id == eligible.quote_line.id:
        # Same QuoteLine as current head: explicit reconfirmation.
        event_name = EVENT_NCC_SELECTION_RECONFIRMED
    else:
        event_name = EVENT_NCC_SELECTION_CHANGED

    current_unit_price_currency_id = asset_line.appraised_currency_id

    new_revision = NccSelectionRevision(
        organization_id=org_id,
        project_id=project_id,
        project_asset_line_id=project_asset_line_id,
        selection_revision=current_selection_revision + 1,
        quote_batch_id=eligible.quote_line.quote_batch_id,
        quote_line_id=eligible.quote_line.id,
        supplier_id=eligible.supplier_id,
        evidence_file_id=eligible.quote_line.evidence_file_id,
        supplier_name_snapshot=eligible.quote_line.supplier_name,
        quoted_unit_price_snapshot=quoted_price,
        currency_snapshot=eligible.quote_line.currency,
        quantity_snapshot=eligible.quote_line.quantity,
        unit_of_measure_snapshot=eligible.quote_line.unit_of_measure,
        quote_date_snapshot=eligible.quote_line.quote_date,
        quote_batch_revision_number_snapshot=eligible.quote_line.quote_batch.revision_number,
        current_unit_price_snapshot=_finite_nonnegative_decimal(
            asset_line.appraised_unit_price
        ),
        current_unit_price_currency_id_snapshot=current_unit_price_currency_id,
        difference_amount=eligible.difference_amount,
        difference_percent=eligible.difference_percent,
        warning_codes=eligible.warnings,
        acknowledged_warning_codes=acknowledged,
        idempotency_key=normalized_key,
        request_digest_sha256=request_digest,
        confirmed_by_user_id=actor.id,
    )
    db.add(new_revision)

    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(NccSelectionRevision)
            .filter(
                NccSelectionRevision.organization_id == org_id,
                NccSelectionRevision.idempotency_key == normalized_key,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and _same_request(raced, request_digest=request_digest):
            return raced
        if raced is not None:
            raise _error(
                409,
                "idempotency_key_reused",
                "Mã lệnh đã được dùng cho dữ liệu khác.",
            ) from exc
        raise _error(
            409,
            "ncc_selection_conflict",
            "Dữ liệu lựa chọn NCC đã thay đổi đồng thời.",
        ) from exc

    # Advance current head atomically.
    if current_head is None:
        current_head = NccSelectionCurrentHead(
            organization_id=org_id,
            project_id=project_id,
            project_asset_line_id=project_asset_line_id,
            current_revision_id=new_revision.id,
            selection_revision=new_revision.selection_revision,
        )
        db.add(current_head)
    else:
        current_head.current_revision_id = new_revision.id
        current_head.selection_revision = new_revision.selection_revision

    log_audit_event(
        db,
        event_name=event_name,
        entity_type="NccSelectionRevision",
        entity_id=new_revision.id,
        organization_id=org_id,
        actor_user_id=actor.id,
        command_name="ConfirmNccSelection",
        correlation_id=correlation_id,
        payload={
            "project_id": str(project_id),
            "project_asset_line_id": str(project_asset_line_id),
            "quote_line_id": str(eligible.quote_line.id),
            "quote_batch_id": str(eligible.quote_line.quote_batch_id),
            "selection_revision": new_revision.selection_revision,
            "previous_revision": current_selection_revision,
            "quoted_unit_price_snapshot": str(quoted_price),
            "currency_snapshot": eligible.quote_line.currency,
            "difference_amount": str(eligible.difference_amount) if eligible.difference_amount is not None else None,
            "difference_percent": str(eligible.difference_percent) if eligible.difference_percent is not None else None,
            "warning_codes": eligible.warnings,
            "acknowledged_warning_codes": acknowledged,
            "supplier_id": str(eligible.supplier_id),
            "evidence_file_id": str(eligible.quote_line.evidence_file_id),
        },
    )

    try:
        db.commit()
        db.refresh(new_revision)
        return new_revision
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(NccSelectionRevision)
            .filter(
                NccSelectionRevision.organization_id == org_id,
                NccSelectionRevision.idempotency_key == normalized_key,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and _same_request(raced, request_digest=request_digest):
            return raced
        raise _error(
            409,
            "ncc_selection_conflict",
            "Dữ liệu lựa chọn NCC đã thay đổi đồng thời.",
        ) from exc


def is_ncc_selection_stale(
    db: Session,
    *,
    revision: NccSelectionRevision,
) -> bool:
    """Return True if the revision's current head is stale per ADR 0039 D6.

    Staleness is computed from current facts for reads; it never mutates the immutable revision.
    """
    quote_line = revision.quote_line
    batch = None if quote_line is None else quote_line.quote_batch
    successor_ids = tuple(
        str(batch_id).lower()
        for (batch_id,) in (
            []
            if batch is None
            else db.query(QuoteBatch.id)
            .filter(
                QuoteBatch.organization_id == revision.organization_id,
                QuoteBatch.previous_quote_batch_id == batch.id,
            )
            .all()
        )
    )
    supplier = db.query(Supplier).filter(Supplier.id == revision.supplier_id).first()
    evidence = (
        db.query(EvidenceFile)
        .options(selectinload(EvidenceFile.uploader))
        .filter(EvidenceFile.id == revision.evidence_file_id)
        .first()
    )
    asset_line = revision.asset_line

    if quote_line is None or _status_value(quote_line.status) != QuoteLineStatus.ACTIVE.value:
        return True
    if batch is None or _status_value(batch.status) != QuoteBatchStatus.ACTIVE.value:
        return True
    if successor_ids:
        return True
    if (
        supplier is None
        or _status_value(supplier.status) != SupplierStatus.ACTIVE.value
        or supplier.organization_id != revision.organization_id
    ):
        return True
    if (
        evidence is None
        or _status_value(evidence.status) != EvidenceFileStatus.ACTIVE.value
        or evidence.uploader is None
        or evidence.uploader.organization_id != revision.organization_id
    ):
        return True
    if asset_line is None:
        return True
    if asset_line.approved_asset_variant_id is not None:
        return batch.asset_variant_id != asset_line.approved_asset_variant_id
    if asset_line.approved_canonical_asset_id is None:
        return True
    return batch.canonical_asset_id != asset_line.approved_canonical_asset_id or batch.asset_variant_id is not None


# ==========================================
# PR-04 read aggregate (server-owned facts only)
# ==========================================

# Selected QuoteBatch/QuoteLine/Supplier/Evidence/asset-line facts are resolved again on the
# server for every read. The frontend never derives eligibility, warnings, monetary facts or
# stale state locally. Evidence is exposed only as server-verified metadata (id, filename,
# status); the generic evidence endpoint is never used and is not hardened here.


@dataclass(frozen=True)
class NccSelectionCandidate:
    quote_line: QuoteLine
    supplier_id: uuid.UUID
    supplier_name: str
    evidence_file_id: uuid.UUID
    evidence_filename: str | None
    evidence_status: str | None
    warnings: list[str]
    difference_amount: Decimal | None
    difference_percent: Decimal | None


def _candidate_for_quote_line(
    db: Session,
    *,
    org_id: uuid.UUID,
    asset_line: ProjectAssetLine,
    quote_line: QuoteLine,
) -> NccSelectionCandidate | None:
    """Return a candidate if the QuoteLine satisfies ADR 0039 D1-D2, else None.

    This mirrors ``_find_eligible_quote`` but enumerates without raising so the read
    aggregate can list every eligible candidate for a line.
    """
    if _status_value(quote_line.status) != QuoteLineStatus.ACTIVE.value:
        return None
    if quote_line.organization_id != org_id:
        return None

    batch = quote_line.quote_batch
    if batch is None:
        return None
    if batch.organization_id != org_id:
        return None
    if _status_value(batch.status) != QuoteBatchStatus.ACTIVE.value:
        return None
    if batch.approved_by is None or batch.approved_at is None:
        return None

    quoted_price = _finite_positive_decimal(quote_line.quoted_unit_price)
    if quoted_price is None:
        return None
    if _blank(quote_line.currency):
        return None

    supplier_id = quote_line.supplier_id
    if supplier_id is None:
        return None
    supplier = (
        db.query(Supplier)
        .filter(
            Supplier.id == supplier_id,
            Supplier.organization_id == org_id,
            Supplier.status == SupplierStatus.ACTIVE,
        )
        .first()
    )
    if supplier is None:
        return None

    if quote_line.evidence_file_id is None:
        return None
    evidence = (
        db.query(EvidenceFile)
        .filter(
            EvidenceFile.id == quote_line.evidence_file_id,
            EvidenceFile.status == EvidenceFileStatus.ACTIVE,
        )
        .first()
    )
    if evidence is None:
        return None
    if evidence.uploader.organization_id != org_id:
        return None

    # ADR 0039 D2: candidate matching uses approved asset identity only.
    if asset_line.approved_asset_variant_id is not None:
        if batch.asset_variant_id != asset_line.approved_asset_variant_id:
            return None
    else:
        if asset_line.approved_canonical_asset_id is None:
            return None
        if batch.canonical_asset_id != asset_line.approved_canonical_asset_id:
            return None
        if batch.asset_variant_id is not None:
            return None

    current_price = _finite_nonnegative_decimal(asset_line.appraised_unit_price)
    warnings, difference_amount, difference_percent = _compute_warnings(
        quoted_price=quoted_price, current_price=current_price
    )

    return NccSelectionCandidate(
        quote_line=quote_line,
        supplier_id=supplier_id,
        supplier_name=quote_line.supplier_name,
        evidence_file_id=quote_line.evidence_file_id,
        evidence_filename=evidence.filename,
        evidence_status=_status_value(evidence.status),
        warnings=warnings,
        difference_amount=difference_amount,
        difference_percent=difference_percent,
    )


def _eligible_candidates_for_line(
    db: Session, *, org_id: uuid.UUID, asset_line: ProjectAssetLine
) -> list[NccSelectionCandidate]:
    if (
        asset_line.approved_asset_variant_id is None
        and asset_line.approved_canonical_asset_id is None
    ):
        return []

    batches = (
        db.query(QuoteBatch)
        .filter(
            QuoteBatch.organization_id == org_id,
            QuoteBatch.status == QuoteBatchStatus.ACTIVE,
            QuoteBatch.approved_by.isnot(None),
            QuoteBatch.approved_at.isnot(None),
        )
        .all()
    )

    candidates: list[NccSelectionCandidate] = []
    for batch in batches:
        if asset_line.approved_asset_variant_id is not None:
            if batch.asset_variant_id != asset_line.approved_asset_variant_id:
                continue
        else:
            if batch.canonical_asset_id != asset_line.approved_canonical_asset_id:
                continue
            if batch.asset_variant_id is not None:
                continue
        for quote_line in batch.quote_lines:
            candidate = _candidate_for_quote_line(
                db, org_id=org_id, asset_line=asset_line, quote_line=quote_line
            )
            if candidate is not None:
                candidates.append(candidate)
    return candidates


def _evidence_metadata(evidence: EvidenceFile | None) -> dict:
    if evidence is None:
        return {"evidence_file_id": None, "filename": None, "status": None}
    return {
        "evidence_file_id": evidence.id,
        "filename": evidence.filename,
        "status": _status_value(evidence.status),
    }


def _candidate_to_dict(candidate: NccSelectionCandidate) -> dict:
    return {
        "quote_line_id": candidate.quote_line.id,
        "quote_batch_id": candidate.quote_line.quote_batch_id,
        "quote_batch_revision_number": candidate.quote_line.quote_batch.revision_number,
        "supplier_id": candidate.supplier_id,
        "supplier_name": candidate.supplier_name,
        "quoted_unit_price": candidate.quote_line.quoted_unit_price,
        "currency": candidate.quote_line.currency,
        "quantity": candidate.quote_line.quantity,
        "unit_of_measure": candidate.quote_line.unit_of_measure,
        "quote_date": candidate.quote_line.quote_date,
        "evidence": _evidence_metadata(candidate.quote_line.evidence_file),
        "difference_amount": candidate.difference_amount,
        "difference_percent": candidate.difference_percent,
        "warnings": candidate.warnings,
        "eligible": True,
    }


def _current_selection_from_revision(
    revision: NccSelectionRevision, *, stale: bool
) -> dict:
    evidence = revision.evidence_file
    return {
        "selection_id": revision.id,
        "selection_revision": revision.selection_revision,
        "quote_line_id": revision.quote_line_id,
        "quote_batch_id": revision.quote_batch_id,
        "quote_batch_revision_number": revision.quote_batch_revision_number_snapshot,
        "supplier_id": revision.supplier_id,
        "supplier_name": revision.supplier_name_snapshot,
        "quoted_unit_price": revision.quoted_unit_price_snapshot,
        "currency": revision.currency_snapshot,
        "quantity": revision.quantity_snapshot,
        "unit_of_measure": revision.unit_of_measure_snapshot,
        "quote_date": revision.quote_date_snapshot,
        "evidence": {
            "evidence_file_id": revision.evidence_file_id,
            "filename": evidence.filename if evidence is not None else None,
            "status": _status_value(evidence.status) if evidence is not None else None,
        },
        "current_unit_price": revision.current_unit_price_snapshot,
        "current_unit_price_currency_id": revision.current_unit_price_currency_id_snapshot,
        "difference_amount": revision.difference_amount,
        "difference_percent": revision.difference_percent,
        "warnings": revision.warning_codes,
        "acknowledged_warning_codes": revision.acknowledged_warning_codes,
        "confirmed_by_user_id": revision.confirmed_by_user_id,
        "confirmed_at": revision.confirmed_at,
        "stale": stale,
    }


def build_current_selection_response(revision: NccSelectionRevision, *, stale: bool) -> dict:
    """Public wrapper for the PR-04 API to serialize a committed current selection."""
    return _current_selection_from_revision(revision, stale=stale)


def _history_to_dict(revision: NccSelectionRevision) -> dict:
    return {
        "selection_revision": revision.selection_revision,
        "quote_line_id": revision.quote_line_id,
        "supplier_name": revision.supplier_name_snapshot,
        "quoted_unit_price": revision.quoted_unit_price_snapshot,
        "currency": revision.currency_snapshot,
        "difference_amount": revision.difference_amount,
        "difference_percent": revision.difference_percent,
        "warnings": revision.warning_codes,
        "confirmed_by_user_id": revision.confirmed_by_user_id,
        "confirmed_at": revision.confirmed_at,
    }


def get_ncc_selection_aggregate(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> dict:
    """Build the tenant-safe NCC Selection read aggregate for a project (PR-04).

    Project, asset lines, eligible candidates, current selection, history and stale state are
    all resolved from current server facts. Nullable business values remain null; no zero is
    invented.
    """
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    lines = (
        db.query(ProjectAssetLine)
        .filter(ProjectAssetLine.project_id == project_id)
        .order_by(ProjectAssetLine.asset_name.asc(), ProjectAssetLine.id.asc())
        .all()
    )
    units = {unit.id: unit for unit in db.query(Unit).all()}

    kpis = {"total_asset_lines": len(lines), "selected": 0, "unselected": 0, "stale": 0, "eligible_quotes": 0}
    asset_lines: list[dict] = []

    for line in lines:
        candidates = _eligible_candidates_for_line(db, org_id=org_id, asset_line=line)
        current_head = (
            db.query(NccSelectionCurrentHead)
            .filter(
                NccSelectionCurrentHead.organization_id == org_id,
                NccSelectionCurrentHead.project_id == project_id,
                NccSelectionCurrentHead.project_asset_line_id == line.id,
            )
            .first()
        )
        current_revision = current_head.current_revision if current_head is not None else None
        history = (
            db.query(NccSelectionRevision)
            .filter(
                NccSelectionRevision.organization_id == org_id,
                NccSelectionRevision.project_id == project_id,
                NccSelectionRevision.project_asset_line_id == line.id,
            )
            .order_by(NccSelectionRevision.selection_revision.asc())
            .all()
        )

        stale = False
        if current_revision is not None:
            stale = is_ncc_selection_stale(db, revision=current_revision)
            kpis["selected"] += 1
            if stale:
                kpis["stale"] += 1
        else:
            kpis["unselected"] += 1
        kpis["eligible_quotes"] += len(candidates)

        unit = units.get(line.unit_id)
        asset_lines.append(
            {
                "asset_line_id": line.id,
                "asset_name": line.asset_name,
                "unit_id": line.unit_id,
                "unit_name": unit.display_name if unit is not None else None,
                "quantity": line.quantity,
                "appraised_unit_price": line.appraised_unit_price,
                "appraised_currency_id": line.appraised_currency_id,
                "current_selection": (
                    _current_selection_from_revision(current_revision, stale=stale)
                    if current_revision is not None
                    else None
                ),
                "candidates": [_candidate_to_dict(c) for c in candidates],
                "history": [_history_to_dict(r) for r in history],
                "state": "stale" if stale else ("selected" if current_revision is not None else "unselected"),
            }
        )

    return {"project_id": project_id, "kpis": kpis, "asset_lines": asset_lines}
