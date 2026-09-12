"""Atomic official-intake commit from an immutable preliminary-result artifact."""
from __future__ import annotations

import hashlib
import json
import uuid
from typing import Any

from fastapi import HTTPException
from sqlalchemy import or_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, selectinload

from app.core.audit import log_audit_event
from app.core.rbac import derive_effective_permissions
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    PreliminaryResultArtifact,
    Project,
    ProjectAssetLine,
    ProjectOfficialIntakeCommit,
    User,
    UserRole,
    UserStatus,
    ValidationIssue,
    ValidationIssueSeverity,
    ValidationIssueStatus,
)


OFFICIAL_INTAKE_COMMIT_PERMISSION = "project:official_intake:commit"
_PROJECT_TARGET_TYPES = ("project", "Project")
_PROJECT_ASSET_LINE_TARGET_TYPES = ("project_asset_line", "ProjectAssetLine")


def _status_value(value: Any) -> str:
    return str(getattr(value, "value", value))


def _error(status: int, code: str, detail: str) -> HTTPException:
    return HTTPException(status_code=status, detail={"error_code": code, "detail": detail})


def _abort(db: Session, status: int, code: str, detail: str) -> None:
    db.rollback()
    raise _error(status, code, detail)


def _request_digest(
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    expected_project_version: int,
    expected_artifact_version: int,
) -> str:
    payload = {
        "actor_id": str(actor_id),
        "artifact_id": str(artifact_id),
        "contract": "official-intake-commit-v1",
        "expected_artifact_version": expected_artifact_version,
        "expected_project_version": expected_project_version,
        "project_id": str(project_id),
    }
    encoded = json.dumps(
        payload, ensure_ascii=False, sort_keys=True, separators=(",", ":")
    ).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


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
        _abort(db, 403, "official_intake_forbidden", "Không thể thực hiện thao tác này.")
    if OFFICIAL_INTAKE_COMMIT_PERMISSION not in derive_effective_permissions(
        persisted_actor, db
    ):
        _abort(db, 403, "official_intake_forbidden", "Không thể thực hiện thao tác này.")
    return persisted_actor


def _same_request(
    commit: ProjectOfficialIntakeCommit,
    *,
    actor_id: uuid.UUID,
    project_id: uuid.UUID,
    artifact_id: uuid.UUID,
    request_digest: str,
) -> bool:
    return (
        commit.committed_by_user_id == actor_id
        and commit.project_id == project_id
        and commit.preliminary_result_artifact_id == artifact_id
        and commit.request_digest_sha256 == request_digest
    )


def _has_open_blocker(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> bool:
    line_ids = (
        db.query(ProjectAssetLine.id)
        .join(Project, Project.id == ProjectAssetLine.project_id)
        .filter(
            Project.organization_id == org_id,
            ProjectAssetLine.project_id == project_id,
        )
    )
    return (
        db.query(ValidationIssue.id)
        .filter(
            ValidationIssue.severity == ValidationIssueSeverity.BLOCKING,
            ValidationIssue.status == ValidationIssueStatus.OPEN,
            or_(
                (
                    ValidationIssue.target_type.in_(_PROJECT_TARGET_TYPES)
                    & (ValidationIssue.target_id == project_id)
                ),
                (
                    ValidationIssue.target_type.in_(_PROJECT_ASSET_LINE_TARGET_TYPES)
                    & ValidationIssue.target_id.in_(line_ids)
                ),
            ),
        )
        .first()
        is not None
    )


def get_official_intake_open_blockers(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> list[ValidationIssue]:
    """Return deterministic ordered accepted OPEN+BLOCKING rows for OFFICIAL_INTAKE."""
    project_exists = (
        db.query(Project.id)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .first()
        is not None
    )
    line_ids = (
        db.query(ProjectAssetLine.id)
        .join(Project, Project.id == ProjectAssetLine.project_id)
        .filter(
            Project.organization_id == org_id,
            ProjectAssetLine.project_id == project_id,
        )
    )
    target_conditions = [
        (
            ValidationIssue.target_type.in_(_PROJECT_ASSET_LINE_TARGET_TYPES)
            & ValidationIssue.target_id.in_(line_ids)
        )
    ]
    if project_exists:
        target_conditions.append(
            ValidationIssue.target_type.in_(_PROJECT_TARGET_TYPES)
            & (ValidationIssue.target_id == project_id)
        )

    return (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.severity == ValidationIssueSeverity.BLOCKING,
            ValidationIssue.status == ValidationIssueStatus.OPEN,
            or_(*target_conditions),
        )
        .order_by(ValidationIssue.id.asc())
        .all()
    )


def get_official_intake_open_warnings(
    db: Session, *, org_id: uuid.UUID, project_id: uuid.UUID
) -> list[ValidationIssue]:
    """Return deterministic ordered accepted OPEN+WARNING rows for OFFICIAL_INTAKE."""
    project_exists = (
        db.query(Project.id)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .first()
        is not None
    )
    line_ids = (
        db.query(ProjectAssetLine.id)
        .join(Project, Project.id == ProjectAssetLine.project_id)
        .filter(
            Project.organization_id == org_id,
            ProjectAssetLine.project_id == project_id,
        )
    )
    target_conditions = [
        (
            ValidationIssue.target_type.in_(_PROJECT_ASSET_LINE_TARGET_TYPES)
            & ValidationIssue.target_id.in_(line_ids)
        )
    ]
    if project_exists:
        target_conditions.append(
            ValidationIssue.target_type.in_(_PROJECT_TARGET_TYPES)
            & (ValidationIssue.target_id == project_id)
        )

    return (
        db.query(ValidationIssue)
        .filter(
            ValidationIssue.severity == ValidationIssueSeverity.WARNING,
            ValidationIssue.status == ValidationIssueStatus.OPEN,
            or_(*target_conditions),
        )
        .order_by(ValidationIssue.id.asc())
        .all()
    )


def commit_project_official_intake(
    db: Session,
    *,
    actor: User,
    org_id: uuid.UUID,
    project_id: uuid.UUID,
    preliminary_result_artifact_id: uuid.UUID,
    expected_project_version: int,
    expected_preliminary_result_version: int,
    idempotency_key: str,
    confirmed: bool,
    correlation_id: str | None = None,
) -> ProjectOfficialIntakeCommit:
    """Create the one-per-project official-intake fact and atomic success audit."""
    if not confirmed:
        _abort(db, 400, "official_intake_confirmation_required", "Cần xác nhận thao tác.")
    normalized_key = idempotency_key.strip()
    if not normalized_key or len(normalized_key) > 128:
        _abort(db, 422, "invalid_idempotency_key", "Khóa idempotency không hợp lệ.")
    if expected_project_version < 1 or expected_preliminary_result_version < 1:
        _abort(db, 422, "invalid_expected_version", "Phiên bản yêu cầu không hợp lệ.")

    actor = _reload_active_actor_and_org(db, actor=actor, org_id=org_id)
    request_digest = _request_digest(
        actor_id=actor.id,
        project_id=project_id,
        artifact_id=preliminary_result_artifact_id,
        expected_project_version=expected_project_version,
        expected_artifact_version=expected_preliminary_result_version,
    )
    project = (
        db.query(Project)
        .filter(Project.id == project_id, Project.organization_id == org_id)
        .with_for_update()
        .populate_existing()
        .first()
    )
    if project is None:
        _abort(db, 404, "project_not_found", "Không tìm thấy hồ sơ.")

    artifact = (
        db.query(PreliminaryResultArtifact)
        .filter(
            PreliminaryResultArtifact.id == preliminary_result_artifact_id,
            PreliminaryResultArtifact.organization_id == org_id,
            PreliminaryResultArtifact.customer_id == project.customer_id,
            PreliminaryResultArtifact.project_id == project.id,
        )
        .with_for_update()
        .first()
    )
    if artifact is None:
        _abort(db, 404, "preliminary_result_not_found", "Không tìm thấy kết quả sơ bộ.")

    existing = (
        db.query(ProjectOfficialIntakeCommit)
        .filter(
            ProjectOfficialIntakeCommit.organization_id == org_id,
            ProjectOfficialIntakeCommit.idempotency_key == normalized_key,
        )
        .populate_existing()
        .first()
    )
    if existing is not None:
        if not _same_request(
            existing,
            actor_id=actor.id,
            project_id=project_id,
            artifact_id=preliminary_result_artifact_id,
            request_digest=request_digest,
        ):
            _abort(db, 409, "idempotency_key_reused", "Mã lệnh đã được dùng cho dữ liệu khác.")
        db.commit()
        db.refresh(existing)
        return existing

    if project.row_version != expected_project_version:
        _abort(db, 409, "project_version_conflict", "Dữ liệu hồ sơ đã thay đổi.")
    if artifact.version != expected_preliminary_result_version:
        _abort(db, 409, "preliminary_result_version_conflict", "Kết quả sơ bộ đã thay đổi.")
    if not artifact.lineage_manifest:
        _abort(
            db,
            409,
            "preliminary_result_lineage_incomplete",
            "Nguồn gốc kết quả sơ bộ chưa đầy đủ.",
        )
    if _has_open_blocker(db, org_id=org_id, project_id=project.id):
        _abort(
            db,
            409,
            "official_intake_blocked",
            "Hồ sơ còn vấn đề bắt buộc cần xử lý.",
        )

    already_committed = (
        db.query(ProjectOfficialIntakeCommit.id)
        .filter(
            ProjectOfficialIntakeCommit.organization_id == org_id,
            ProjectOfficialIntakeCommit.project_id == project.id,
        )
        .first()
    )
    if already_committed is not None:
        _abort(db, 409, "official_intake_already_committed", "Hồ sơ đã được chuyển chính thức.")

    commit = ProjectOfficialIntakeCommit(
        organization_id=org_id,
        customer_id=project.customer_id,
        project_id=project.id,
        preliminary_result_artifact_id=artifact.id,
        preliminary_result_version=artifact.version,
        preliminary_result_sha256=artifact.content_checksum_sha256,
        source_snapshot_sha256=artifact.source_snapshot_sha256,
        project_version_before=project.row_version,
        idempotency_key=normalized_key,
        request_digest_sha256=request_digest,
        committed_by_user_id=actor.id,
    )
    db.add(commit)
    try:
        db.flush()
        log_audit_event(
            db,
            event_name="ProjectOfficialIntakeCommitted",
            entity_type="ProjectOfficialIntakeCommit",
            entity_id=commit.id,
            organization_id=org_id,
            actor_user_id=actor.id,
            command_name="CommitProjectOfficialIntake",
            correlation_id=correlation_id,
            payload={
                "project_id": str(project.id),
                "preliminary_result_artifact_id": str(artifact.id),
                "preliminary_result_version": artifact.version,
                "preliminary_result_sha256": artifact.content_checksum_sha256,
                "source_snapshot_sha256": artifact.source_snapshot_sha256,
                "project_version_before": project.row_version,
            },
        )
        db.commit()
        db.refresh(commit)
        return commit
    except IntegrityError as exc:
        db.rollback()
        raced = (
            db.query(ProjectOfficialIntakeCommit)
            .filter(
                ProjectOfficialIntakeCommit.organization_id == org_id,
                ProjectOfficialIntakeCommit.idempotency_key == normalized_key,
            )
            .populate_existing()
            .first()
        )
        if raced is not None and _same_request(
            raced,
            actor_id=actor.id,
            project_id=project_id,
            artifact_id=preliminary_result_artifact_id,
            request_digest=request_digest,
        ):
            return raced
        if raced is not None:
            raise _error(
                409,
                "idempotency_key_reused",
                "Mã lệnh đã được dùng cho dữ liệu khác.",
            ) from exc
        raced_project = (
            db.query(ProjectOfficialIntakeCommit.id)
            .filter(
                ProjectOfficialIntakeCommit.organization_id == org_id,
                ProjectOfficialIntakeCommit.project_id == project_id,
            )
            .first()
        )
        if raced_project is not None:
            raise _error(
                409,
                "official_intake_already_committed",
                "Hồ sơ đã được chuyển chính thức.",
            ) from exc
        raise _error(
            409,
            "official_intake_conflict",
            "Hồ sơ đã thay đổi đồng thời hoặc đã được chuyển chính thức.",
        ) from exc
    except Exception:
        db.rollback()
        raise
