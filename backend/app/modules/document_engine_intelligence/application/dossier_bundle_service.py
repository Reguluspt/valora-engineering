"""S15-PR-001 DossierBundle aggregate management and paired file validation service."""
from __future__ import annotations

import uuid
from typing import Any, Sequence
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.excel_import.models import DossierBundle, DossierFileRole, DossierSourceFile


def create_paired_dossier_bundle(
    db: Session,
    *,
    actor_id: uuid.UUID,
    org_id: uuid.UUID,
    customer_id: uuid.UUID | None = None,
    project_id: uuid.UUID | None = None,
    bundle_code: str,
    files: Sequence[dict[str, Any]],
) -> tuple[DossierBundle, list[DossierSourceFile]]:
    """Create a paired DossierBundle aggregate (ADR 0032).
    
    Invariants:
    1. Paired valuation dossier requires both an Excel workbook (excel_workbook) and a Word report (word_report).
    2. Duplicate file roles within the same bundle are forbidden.
    3. Immutable source file checksums and storage key provenance.
    """
    if not bundle_code or not bundle_code.strip():
        raise HTTPException(status_code=400, detail="Mã bộ hồ sơ không được để trống.")

    # Idempotency / duplicate check
    existing = (
        db.query(DossierBundle)
        .filter(
            DossierBundle.organization_id == org_id,
            DossierBundle.bundle_code == bundle_code,
        )
        .first()
    )
    if existing:
        existing_files = (
            db.query(DossierSourceFile)
            .filter(DossierSourceFile.dossier_bundle_id == existing.id)
            .all()
        )
        return existing, existing_files

    roles_present = {f.get("file_role") for f in files}
    valid_roles = {r.value for r in DossierFileRole}

    for role in roles_present:
        if role not in valid_roles:
            raise HTTPException(status_code=400, detail=f"Vai trò tệp {role} không hợp lệ.")

    # Require paired Excel + Word for a complete valuation dossier
    if "excel_workbook" not in roles_present or "word_report" not in roles_present:
        raise HTTPException(
            status_code=400,
            detail="Bộ hồ sơ ghép đôi bắt buộc phải bao gồm cả tệp Excel bảng tính và tệp Word báo cáo.",
        )

    if len(roles_present) != len(files):
        raise HTTPException(status_code=400, detail="Không được phép chứa hai tệp cùng vai trò trong một bộ hồ sơ.")

    bundle = DossierBundle(
        id=uuid.uuid4(),
        organization_id=org_id,
        customer_id=customer_id,
        project_id=project_id,
        bundle_code=bundle_code.strip(),
        status="pending",
        created_by_user_id=actor_id,
    )
    db.add(bundle)

    source_files: list[DossierSourceFile] = []
    for f in files:
        s_file = DossierSourceFile(
            id=uuid.uuid4(),
            organization_id=org_id,
            dossier_bundle_id=bundle.id,
            file_role=f["file_role"],
            file_name=f["file_name"],
            file_size_bytes=f["file_size_bytes"],
            checksum_sha256=f["checksum_sha256"],
            storage_object_key=f["storage_object_key"],
        )
        db.add(s_file)
        source_files.append(s_file)

    db.commit()
    db.refresh(bundle)
    for sf in source_files:
        db.refresh(sf)

    return bundle, source_files
