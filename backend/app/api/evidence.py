import uuid
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from sqlalchemy import and_

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, EvidenceSource, EvidenceFile, EvidenceLink, EvidenceAccessLog,
    EvidenceFileStatus
)
from app.modules.project_master_data.evidence_schemas import (
    EvidenceSourceResponse, EvidenceSourceUpdate,
    EvidenceFileResponse, EvidenceFileUpdate,
    EvidenceLinkResponse, EvidenceLinkCreate,
    EvidenceAccessLogResponse
)

router = APIRouter(prefix="/api/v1/evidence", tags=["evidence"])


def sanitize_audit_payload(d: dict) -> dict:
    """Recursively convert UUIDs and non-primitive types in dict to string values for JSON serialization."""
    if not isinstance(d, dict):
        return d
    res = {}
    for k, v in d.items():
        if isinstance(v, uuid.UUID):
            res[k] = str(v)
        elif hasattr(v, "value"):  # Handle Enums
            res[k] = str(v.value)
        elif isinstance(v, dict):
            res[k] = sanitize_audit_payload(v)
        elif isinstance(v, list):
            res[k] = [str(x) if isinstance(x, uuid.UUID) else (sanitize_audit_payload(x) if isinstance(x, dict) else x) for x in v]
        else:
            res[k] = v
    return res


# ==========================================
# EVIDENCE SOURCES
# ==========================================

@router.get("/sources", response_model=List[EvidenceSourceResponse])
def list_evidence_sources(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read"))
):
    return db.query(EvidenceSource).all()


@router.get("/sources/{source_id}", response_model=EvidenceSourceResponse)
def get_evidence_source(
    source_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read"))
):
    source = db.query(EvidenceSource).filter(EvidenceSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="EvidenceSource not found")
    return source


@router.patch("/sources/{source_id}", response_model=EvidenceSourceResponse)
def update_evidence_source(
    source_id: uuid.UUID,
    payload: EvidenceSourceUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evidence:source:update"))
):
    source = db.query(EvidenceSource).filter(EvidenceSource.id == source_id).first()
    if not source:
        raise HTTPException(status_code=404, detail="EvidenceSource not found")

    update_dict = payload.model_dump(exclude_unset=True)
    for k, v in update_dict.items():
        setattr(source, k, v)
    db.commit()
    db.refresh(source)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="EVIDENCE_SOURCE_UPDATE",
        entity_type="EvidenceSource",
        entity_id=source.id,
        payload=sanitize_audit_payload(update_dict)
    )
    return source


# ==========================================
# EVIDENCE FILES
# ==========================================

@router.get("/files/{evidence_file_id}", response_model=EvidenceFileResponse)
def get_evidence_file(
    evidence_file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read"))
):
    ev_file = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not ev_file:
        raise HTTPException(status_code=404, detail="EvidenceFile not found")
    return ev_file


@router.patch("/files/{evidence_file_id}", response_model=EvidenceFileResponse)
def update_evidence_file_metadata(
    evidence_file_id: uuid.UUID,
    payload: EvidenceFileUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evidence:file:update"))
):
    ev_file = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not ev_file:
        raise HTTPException(status_code=404, detail="EvidenceFile not found")

    # Optimistic locking validation
    if ev_file.row_version != payload.expected_row_version:
        raise HTTPException(status_code=409, detail="VAL_KNOW_CONFLICT_001")

    update_dict = payload.model_dump(exclude_unset=True, exclude={"expected_row_version"})
    for k, v in update_dict.items():
        setattr(ev_file, k, v)
    
    # Increment row version manually
    ev_file.row_version += 1
    db.commit()
    db.refresh(ev_file)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="EVIDENCE_FILE_METADATA_UPDATE",
        entity_type="EvidenceFile",
        entity_id=ev_file.id,
        payload=sanitize_audit_payload(update_dict)
    )
    return ev_file


@router.delete("/files/{evidence_file_id}", response_model=EvidenceFileResponse)
def delete_evidence_file(
    evidence_file_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evidence:cleanup"))
):
    ev_file = db.query(EvidenceFile).filter(EvidenceFile.id == evidence_file_id).first()
    if not ev_file:
        raise HTTPException(status_code=404, detail="EvidenceFile not found")

    # Check if used in active/approved structures (active links or specialized evidence)
    active_links = db.query(EvidenceLink).filter(
        and_(EvidenceLink.evidence_file_id == evidence_file_id, EvidenceLink.is_deleted == False)
    ).count()
    if active_links > 0:
        raise HTTPException(status_code=422, detail="VAL_EVD_DELETE_001")

    # Perform soft-delete/archiving
    ev_file.status = EvidenceFileStatus.ARCHIVED
    db.commit()
    db.refresh(ev_file)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="EVIDENCE_FILE_DELETE",
        entity_type="EvidenceFile",
        entity_id=ev_file.id,
        payload={"status": "archived"}
    )
    return ev_file


# ==========================================
# EVIDENCE LINKS
# ==========================================

@router.get("/links", response_model=List[EvidenceLinkResponse])
def list_evidence_links(
    target_type: Optional[str] = None,
    target_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read"))
):
    query = db.query(EvidenceLink).filter(EvidenceLink.is_deleted == False)
    if target_type:
        query = query.filter(EvidenceLink.target_type == target_type)
    if target_id:
        query = query.filter(EvidenceLink.target_id == target_id)
    return query.all()


@router.post("/links", response_model=EvidenceLinkResponse, status_code=201)
def create_evidence_link(
    payload: EvidenceLinkCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evidence:link:create"))
):
    # Verify file exists
    f = db.query(EvidenceFile).filter(EvidenceFile.id == payload.evidence_file_id).first()
    if not f:
        raise HTTPException(status_code=422, detail="EvidenceFile not found")

    link = EvidenceLink(
        evidence_file_id=payload.evidence_file_id,
        target_type=payload.target_type,
        target_id=payload.target_id,
        created_by=current_user.id
    )
    db.add(link)
    db.commit()
    db.refresh(link)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="EVIDENCE_LINK_CREATE",
        entity_type="EvidenceLink",
        entity_id=link.id,
        payload=sanitize_audit_payload(payload.model_dump())
    )
    return link


@router.delete("/links/{link_id}", response_model=EvidenceLinkResponse)
def delete_evidence_link(
    link_id: uuid.UUID,
    reason: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("evidence:link:delete"))
):
    link = db.query(EvidenceLink).filter(EvidenceLink.id == link_id).first()
    if not link:
        raise HTTPException(status_code=404, detail="EvidenceLink not found")

    if link.is_deleted:
         raise HTTPException(status_code=400, detail="EvidenceLink already deleted")

    # Soft-delete unlink policy
    link.is_deleted = True
    link.deleted_by = current_user.id
    link.deleted_at = datetime.now(timezone.utc)
    link.delete_reason = reason
    db.commit()
    db.refresh(link)

    log_audit_event(
        db=db,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id,
        event_name="EVIDENCE_LINK_DELETE",
        entity_type="EvidenceLink",
        entity_id=link.id,
        payload={"reason": reason}
    )
    return link


# ==========================================
# EVIDENCE ACCESS LOGS
# ==========================================

@router.get("/access-logs", response_model=List[EvidenceAccessLogResponse])
def list_evidence_access_logs(
    evidence_file_id: Optional[uuid.UUID] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("knowledge:read"))
):
    query = db.query(EvidenceAccessLog)
    if evidence_file_id:
        query = query.filter(EvidenceAccessLog.evidence_file_id == evidence_file_id)
    return query.all()
