"""Tenant-safe human identity decisions and append-only feedback generation."""
from __future__ import annotations

import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.ai_governance_security.application.security_audit_service import (
    record_authorization_denial,
    record_tenant_boundary_check,
)
from app.modules.excel_import.models import (
    AssetIdentityDecision,
    ContextualAssetAlias,
    LearningFeedbackEvent,
    RawAssetObservation,
)
from app.modules.project_master_data.models import (
    AssetAlias,
    AssetAliasStatus,
    AssetVariant,
    AssetVariantStatus,
    CanonicalAsset,
    CanonicalAssetStatus,
    Customer,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    User,
    UserRole,
    UserStatus,
)
from app.modules.taxonomy_asset_identity.domain.asset_matcher import normalize_asset_text

_REQUIRED_PERMISSION = "asset_identity:approve"
_AUDIT_ENTITY = "AssetIdentityDecision"
_DECISION_TYPES = {"accepted", "corrected", "rejected", "deferred"}
_TARGETED_DECISIONS = {"accepted", "corrected", "rejected"}


def _status_value(value: Any) -> str:
    return value.value if hasattr(value, "value") else str(value)


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _persist_boundary_denial(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID | None,
    resource_type: str,
    resource_id: uuid.UUID,
    reason_code: str,
    response_detail: str,
) -> None:
    """Persist the denied check before returning a non-disclosing 404."""
    db.rollback()
    try:
        record_tenant_boundary_check(
            db,
            organization_id=org_id,
            actor_id=actor_id,
            resource_type=resource_type,
            resource_id=resource_id,
            passed=False,
            failure_reason=reason_code,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _error(
            503,
            "security_audit_unavailable",
            "Không thể ghi nhận kiểm tra bảo mật; thao tác đã bị chặn.",
        ) from exc
    raise _error(404, "resource_not_found", response_detail)


def _persist_authorization_denial(
    db: Session,
    *,
    org_id: uuid.UUID,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
) -> None:
    db.rollback()
    try:
        record_authorization_denial(
            db,
            organization_id=org_id,
            actor_id=actor_id,
            permission_code=_REQUIRED_PERMISSION,
            target_type="Project",
            target_id=project_id,
        )
        db.commit()
    except Exception as exc:
        db.rollback()
        raise _error(
            503,
            "security_audit_unavailable",
            "Không thể ghi nhận kiểm tra bảo mật; thao tác đã bị chặn.",
        ) from exc
    raise _error(403, "permission_denied", "Tài khoản không có quyền xác nhận định danh.")


def _reload_active_actor_and_org(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
) -> User:
    organization = (
        db.query(OrganizationProfile)
        .filter(OrganizationProfile.id == org_id)
        .populate_existing()
        .first()
    )
    if organization is None:
        raise _error(404, "resource_not_found", "Không tìm thấy dự án.")

    actor_id = getattr(actor, "id", None)
    persisted_actor = None
    if actor_id is not None:
        persisted_actor = (
            db.query(User)
            .options(
                selectinload(User.organization),
                selectinload(User.roles).selectinload(UserRole.role),
            )
            .filter(User.id == actor_id)
            .populate_existing()
            .first()
        )
    if (
        _status_value(organization.status) != OrganizationStatus.ACTIVE.value
        or persisted_actor is None
        or persisted_actor.organization_id != org_id
        or _status_value(persisted_actor.status) != UserStatus.ACTIVE.value
    ):
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=(persisted_actor.id if persisted_actor is not None else None),
            resource_type="User",
            resource_id=actor_id or uuid.UUID(int=0),
            reason_code="actor_context_invalid",
            response_detail="Không tìm thấy dự án.",
        )

    if _REQUIRED_PERMISSION not in derive_effective_permissions(persisted_actor, db):
        _persist_authorization_denial(
            db,
            org_id=org_id,
            actor_id=persisted_actor.id,
            project_id=project_id,
        )
    return persisted_actor


def _resolve_context(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    raw_observation_id: uuid.UUID,
) -> tuple[User, Project, RawAssetObservation, Customer]:
    actor = _reload_active_actor_and_org(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
    )
    project = (
        db.query(Project)
        .filter(Project.organization_id == org_id, Project.id == project_id)
        .populate_existing()
        .with_for_update()
        .first()
    )
    if project is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="Project",
            resource_id=project_id,
            reason_code="project_tenant_boundary_failed",
            response_detail="Không tìm thấy dự án.",
        )
    record_tenant_boundary_check(
        db,
        organization_id=org_id,
        actor_id=actor.id,
        resource_type="Project",
        resource_id=project_id,
        passed=True,
    )

    observation = (
        db.query(RawAssetObservation)
        .filter(
            RawAssetObservation.organization_id == org_id,
            RawAssetObservation.project_id == project_id,
            RawAssetObservation.id == raw_observation_id,
        )
        .populate_existing()
        .with_for_update()
        .first()
    )
    if observation is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="RawAssetObservation",
            resource_id=raw_observation_id,
            reason_code="observation_tenant_boundary_failed",
            response_detail="Không tìm thấy bản ghi quan sát tài sản gốc.",
        )
    if observation.customer_id != project.customer_id:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="RawAssetObservation",
            resource_id=raw_observation_id,
            reason_code="observation_ownership_mismatch",
            response_detail="Không tìm thấy bản ghi quan sát tài sản gốc.",
        )
    record_tenant_boundary_check(
        db,
        organization_id=org_id,
        actor_id=actor.id,
        resource_type="RawAssetObservation",
        resource_id=raw_observation_id,
        passed=True,
    )

    customer = (
        db.query(Customer)
        .filter(Customer.organization_id == org_id, Customer.id == project.customer_id)
        .populate_existing()
        .first()
    )
    if customer is None:
        _persist_boundary_denial(
            db,
            org_id=org_id,
            actor_id=actor.id,
            resource_type="Customer",
            resource_id=project.customer_id,
            reason_code="customer_tenant_boundary_failed",
            response_detail="Không tìm thấy dự án.",
        )
    record_tenant_boundary_check(
        db,
        organization_id=org_id,
        actor_id=actor.id,
        resource_type="Customer",
        resource_id=customer.id,
        passed=True,
    )
    return actor, project, observation, customer


def _validate_command_shape(
    db: Session,
    *,
    decision_type: str,
    chosen_canonical_asset_id: uuid.UUID | None,
    chosen_asset_variant_id: uuid.UUID | None,
    chosen_alias_id: uuid.UUID | None,
    create_contextual_alias: bool,
    rejection_reason: str | None,
) -> str | None:
    if decision_type not in _DECISION_TYPES:
        _abort(db, 400, "identity_decision_type_invalid", "Loại quyết định định danh không hợp lệ.")
    target_count = sum(
        value is not None
        for value in (
            chosen_canonical_asset_id,
            chosen_asset_variant_id,
            chosen_alias_id,
        )
    )
    if decision_type in _TARGETED_DECISIONS and target_count != 1:
        _abort(
            db,
            400,
            "identity_decision_target_invalid",
            "Quyết định phải tham chiếu đúng một tài sản, biến thể hoặc bí danh.",
        )
    if decision_type == "deferred" and target_count != 0:
        _abort(
            db,
            400,
            "identity_decision_target_invalid",
            "Quyết định tạm hoãn không được ghi nhận mục tiêu định danh.",
        )
    reason = rejection_reason.strip() if rejection_reason else None
    if decision_type == "rejected" and not reason:
        _abort(
            db,
            400,
            "identity_rejection_reason_required",
            "Quyết định từ chối phải có lý do.",
        )
    if create_contextual_alias and decision_type not in {"accepted", "corrected"}:
        _abort(
            db,
            400,
            "contextual_alias_decision_invalid",
            "Chỉ quyết định chấp nhận hoặc hiệu chỉnh mới được tạo bí danh ngữ cảnh.",
        )
    return reason


def _resolve_target(
    db: Session,
    *,
    decision_type: str,
    chosen_canonical_asset_id: uuid.UUID | None,
    chosen_asset_variant_id: uuid.UUID | None,
    chosen_alias_id: uuid.UUID | None,
) -> tuple[str | None, uuid.UUID | None, uuid.UUID | None, uuid.UUID | None]:
    """Return feedback type/id and the canonical/variant contextual target."""
    if decision_type == "deferred":
        return None, None, None, None

    require_active = decision_type in {"accepted", "corrected"}
    if chosen_canonical_asset_id is not None:
        canonical = db.get(CanonicalAsset, chosen_canonical_asset_id)
        if canonical is None:
            _abort(db, 404, "identity_target_not_found", "Không tìm thấy tài sản chuẩn đã chọn.")
        if require_active and _status_value(canonical.status) != CanonicalAssetStatus.ACTIVE.value:
            _abort(db, 409, "identity_target_not_active", "Tài sản chuẩn đã chọn chưa hoạt động.")
        return "CanonicalAsset", canonical.id, canonical.id, None

    if chosen_asset_variant_id is not None:
        variant = db.get(AssetVariant, chosen_asset_variant_id)
        if variant is None:
            _abort(db, 404, "identity_target_not_found", "Không tìm thấy biến thể tài sản đã chọn.")
        if require_active and _status_value(variant.status) != AssetVariantStatus.ACTIVE.value:
            _abort(db, 409, "identity_target_not_active", "Biến thể tài sản đã chọn chưa hoạt động.")
        return "AssetVariant", variant.id, None, variant.id

    alias = db.get(AssetAlias, chosen_alias_id)
    if alias is None:
        _abort(db, 404, "identity_target_not_found", "Không tìm thấy bí danh tài sản đã chọn.")
    if require_active and _status_value(alias.status) != AssetAliasStatus.ACTIVE.value:
        _abort(db, 409, "identity_target_not_active", "Bí danh tài sản đã chọn chưa hoạt động.")
    alias_target_count = sum(
        value is not None for value in (alias.canonical_asset_id, alias.asset_variant_id)
    )
    if alias_target_count != 1:
        _abort(db, 409, "identity_target_integrity_failure", "Bí danh tài sản không có mục tiêu hợp lệ.")
    if alias.canonical_asset_id is not None:
        canonical = db.get(CanonicalAsset, alias.canonical_asset_id)
        if canonical is None or (
            require_active and _status_value(canonical.status) != CanonicalAssetStatus.ACTIVE.value
        ):
            _abort(db, 409, "identity_target_not_active", "Mục tiêu của bí danh chưa hoạt động.")
        return "AssetAlias", alias.id, canonical.id, None
    variant = db.get(AssetVariant, alias.asset_variant_id)
    if variant is None or (
        require_active and _status_value(variant.status) != AssetVariantStatus.ACTIVE.value
    ):
        _abort(db, 409, "identity_target_not_active", "Mục tiêu của bí danh chưa hoạt động.")
    return "AssetAlias", alias.id, None, variant.id


def _same_command(
    decision: AssetIdentityDecision,
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    raw_observation_id: uuid.UUID,
    decision_type: str,
    chosen_canonical_asset_id: uuid.UUID | None,
    chosen_asset_variant_id: uuid.UUID | None,
    chosen_alias_id: uuid.UUID | None,
    rejection_reason: str | None,
) -> bool:
    return (
        decision.actor_user_id == actor_id
        and decision.project_id == project_id
        and decision.raw_observation_id == raw_observation_id
        and _status_value(decision.decision_type) == decision_type
        and decision.chosen_canonical_asset_id == chosen_canonical_asset_id
        and decision.chosen_asset_variant_id == chosen_asset_variant_id
        and decision.chosen_alias_id == chosen_alias_id
        and (decision.rejection_reason or None) == rejection_reason
    )


def _feedback_for_decision(
    db: Session, decision_id: uuid.UUID
) -> LearningFeedbackEvent | None:
    return (
        db.query(LearningFeedbackEvent)
        .filter(LearningFeedbackEvent.source_decision_id == decision_id)
        .populate_existing()
        .first()
    )


def confirm_identity_decision(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    raw_observation_id: uuid.UUID,
    decision_type: str,
    chosen_canonical_asset_id: uuid.UUID | None = None,
    chosen_asset_variant_id: uuid.UUID | None = None,
    chosen_alias_id: uuid.UUID | None = None,
    create_contextual_alias: bool = False,
    rejection_reason: str | None = None,
    command_id: uuid.UUID,
    correlation_id: str | None = None,
) -> tuple[AssetIdentityDecision, LearningFeedbackEvent | None]:
    """Commit one authorized, tenant-scoped human identity decision.

    The actor is supplied by trusted server authentication context and is
    reloaded from persistence before authorization. The service owns its unit
    of work, including the success audit event and durable denial audit.
    """
    actor, project, observation, customer = _resolve_context(
        db,
        actor=actor,
        org_id=org_id,
        project_id=project_id,
        raw_observation_id=raw_observation_id,
    )
    reason = _validate_command_shape(
        db,
        decision_type=decision_type,
        chosen_canonical_asset_id=chosen_canonical_asset_id,
        chosen_asset_variant_id=chosen_asset_variant_id,
        chosen_alias_id=chosen_alias_id,
        create_contextual_alias=create_contextual_alias,
        rejection_reason=rejection_reason,
    )

    existing = (
        db.query(AssetIdentityDecision)
        .filter(
            AssetIdentityDecision.organization_id == org_id,
            AssetIdentityDecision.command_id == command_id,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if not _same_command(
            existing,
            actor_id=actor.id,
            project_id=project_id,
            raw_observation_id=raw_observation_id,
            decision_type=decision_type,
            chosen_canonical_asset_id=chosen_canonical_asset_id,
            chosen_asset_variant_id=chosen_asset_variant_id,
            chosen_alias_id=chosen_alias_id,
            rejection_reason=reason,
        ):
            _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        feedback = _feedback_for_decision(db, existing.id)
        db.commit()
        return existing, feedback

    target_type, target_id, contextual_canonical_id, contextual_variant_id = _resolve_target(
        db,
        decision_type=decision_type,
        chosen_canonical_asset_id=chosen_canonical_asset_id,
        chosen_asset_variant_id=chosen_asset_variant_id,
        chosen_alias_id=chosen_alias_id,
    )

    decision = AssetIdentityDecision(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_id=customer.id,
        project_id=project.id,
        raw_observation_id=observation.id,
        decision_type=decision_type,
        chosen_canonical_asset_id=chosen_canonical_asset_id,
        chosen_asset_variant_id=chosen_asset_variant_id,
        chosen_alias_id=chosen_alias_id,
        rejection_reason=reason,
        actor_user_id=actor.id,
        command_id=command_id,
    )
    db.add(decision)

    if create_contextual_alias:
        db.add(
            ContextualAssetAlias(
                id=uuid.uuid4(),
                organization_id=org_id,
                customer_id=customer.id,
                alias_name=observation.raw_asset_name,
                normalized_alias_name=normalize_asset_text(observation.raw_asset_name),
                canonical_asset_id=contextual_canonical_id,
                asset_variant_id=contextual_variant_id,
                status="active",
                source_decision_id=decision.id,
                created_by_user_id=actor.id,
            )
        )

    feedback_event: LearningFeedbackEvent | None = None
    if target_type is not None and target_id is not None:
        feedback_event = LearningFeedbackEvent(
            id=uuid.uuid4(),
            organization_id=org_id,
            customer_id=customer.id,
            source_decision_id=decision.id,
            event_type=(
                "positive_match" if decision_type in {"accepted", "corrected"} else "negative_match"
            ),
            raw_wording=observation.raw_asset_name,
            target_type=target_type,
            target_id=target_id,
            feedback_metadata={
                "decision_type": decision_type,
                "created_contextual_alias": create_contextual_alias,
                **({"rejection_reason": reason} if decision_type == "rejected" else {}),
            },
        )
        db.add(feedback_event)

    log_audit_event(
        db,
        event_name="AssetIdentityDecisionConfirmed",
        entity_type=_AUDIT_ENTITY,
        entity_id=decision.id,
        organization_id=org_id,
        actor_user_id=actor.id,
        command_name="ConfirmAssetIdentityDecision",
        correlation_id=correlation_id,
        payload={
            "organization_id": str(org_id),
            "customer_id": str(customer.id),
            "project_id": str(project.id),
            "raw_observation_id": str(observation.id),
            "decision_type": decision_type,
            "target_type": target_type,
            "target_id": str(target_id) if target_id else None,
            "created_contextual_alias": create_contextual_alias,
        },
    )

    try:
        db.commit()
        db.refresh(decision)
        if feedback_event is not None:
            db.refresh(feedback_event)
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(AssetIdentityDecision)
            .filter(
                AssetIdentityDecision.organization_id == org_id,
                AssetIdentityDecision.command_id == command_id,
            )
            .populate_existing()
            .first()
        )
        if raced is not None:
            if not _same_command(
                raced,
                actor_id=actor.id,
                project_id=project_id,
                raw_observation_id=raw_observation_id,
                decision_type=decision_type,
                chosen_canonical_asset_id=chosen_canonical_asset_id,
                chosen_asset_variant_id=chosen_asset_variant_id,
                chosen_alias_id=chosen_alias_id,
                rejection_reason=reason,
            ):
                raise _error(
                    409,
                    "idempotency_key_reused",
                    "Mã lệnh đã được dùng cho dữ liệu khác.",
                ) from exc
            return raced, _feedback_for_decision(db, raced.id)
        raise _error(
            409,
            "identity_decision_conflict",
            "Dữ liệu định danh đã thay đổi đồng thời hoặc không còn hợp lệ.",
        ) from exc

    return decision, feedback_event
