import uuid
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, text

from app.db import get_db
from app.core.rbac import require_permission, get_current_user
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User,
    Customer,
    CustomerStatus,
    Currency,
    SignerProfile,
    Project,
    ProjectWorkflowStatus,
    KnowledgeUpdateStatus,
    ProjectAssetLine,
    AssetLineReviewStatus,
    AssetLineValidationStatus,
    ProjectFile,
    FileProcessingStatus,
    ProjectFileCategory,
    Unit
)
from app.modules.project_master_data.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectAssetLineCreate, ProjectAssetLineUpdate, ProjectAssetLineResponse,
    ProjectFileCreate, ProjectFileResponse
)

router = APIRouter(prefix="/api/v1/projects", tags=["projects"])


# ==========================================
# PROJECT ENDPOINTS
# ==========================================

@router.post("", response_model=ProjectResponse, status_code=201)
def create_project(
    payload: ProjectCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:create"))
):
    org_id = current_user.organization_id

    # 1. Enforce project code uniqueness per organization
    dup = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.code == payload.code
    ).first()
    if dup:
        raise HTTPException(status_code=409, detail="Duplicate project code (code already exists in organization)")

    # 2. Enforce customer relationship within same organization
    customer = db.query(Customer).filter(
        Customer.organization_id == org_id,
        Customer.id == payload.customer_id
    ).first()
    if not customer:
        raise HTTPException(status_code=404, detail="Customer not found")
    if customer.status != CustomerStatus.ACTIVE:
        raise HTTPException(status_code=422, detail="Customer inactive")

    # 3. Currency lookup (if provided)
    if payload.fee_currency_id:
        curr = db.query(Currency).filter(Currency.id == payload.fee_currency_id).first()
        if not curr:
            raise HTTPException(status_code=404, detail="Currency not found")

    # 4. Signer lookup (if provided)
    if payload.signer_profile_id:
        signer = db.query(SignerProfile).filter(
            SignerProfile.organization_id == org_id,
            SignerProfile.id == payload.signer_profile_id
        ).first()
        if not signer:
            raise HTTPException(status_code=404, detail="Signer profile not found")

    # 5. Create project
    project = Project(
        organization_id=org_id,
        customer_id=payload.customer_id,
        code=payload.code,
        name=payload.name,
        description=payload.description,
        status=ProjectWorkflowStatus.DRAFT,
        knowledge_status=KnowledgeUpdateStatus.PENDING,
        fee_amount=payload.fee_amount,
        fee_currency_id=payload.fee_currency_id,
        signer_profile_id=payload.signer_profile_id,
        created_by=current_user.id
    )
    db.add(project)
    db.commit()
    db.refresh(project)

    # 6. Audit log
    log_audit_event(
        db=db,
        event_name="ProjectCreated",
        entity_type="Project",
        entity_id=project.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateProject",
        payload={"code": project.code}
    )
    db.commit()

    return project


@router.get("", response_model=List[ProjectResponse])
def list_projects(
    q: Optional[str] = None,
    customer_id: Optional[uuid.UUID] = None,
    status: Optional[str] = None,
    page: int = Query(1, ge=1),
    page_size: int = Query(25, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read"))
):
    org_id = current_user.organization_id
    query = db.query(Project).filter(Project.organization_id == org_id)

    if q:
        query = query.filter(
            or_(
                Project.code.ilike(f"%{q}%"),
                Project.name.ilike(f"%{q}%"),
                Project.description.ilike(f"%{q}%")
            )
        )
    if customer_id:
        query = query.filter(Project.customer_id == customer_id)
    if status:
        query = query.filter(Project.status == status)

    offset = (page - 1) * page_size
    projects = query.offset(offset).limit(page_size).all()
    return projects


@router.get("/{project_id}", response_model=ProjectResponse)
def get_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return project


@router.patch("/{project_id}", response_model=ProjectResponse)
def update_project(
    project_id: uuid.UUID,
    payload: ProjectUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Enforce optimistic locking / row_version validation
    if project.row_version != payload.row_version:
        raise HTTPException(status_code=409, detail="Optimistic lock error: Record version mismatch")

    if payload.fee_currency_id:
        curr = db.query(Currency).filter(Currency.id == payload.fee_currency_id).first()
        if not curr:
            raise HTTPException(status_code=404, detail="Currency not found")

    if payload.signer_profile_id:
        signer = db.query(SignerProfile).filter(
            SignerProfile.organization_id == org_id,
            SignerProfile.id == payload.signer_profile_id
        ).first()
        if not signer:
            raise HTTPException(status_code=404, detail="Signer profile not found")

    # Update fields
    if payload.name is not None:
        project.name = payload.name
    if payload.description is not None:
        project.description = payload.description
    if payload.fee_amount is not None:
        project.fee_amount = payload.fee_amount
    if payload.fee_currency_id is not None:
        project.fee_currency_id = payload.fee_currency_id
    if payload.signer_profile_id is not None:
        project.signer_profile_id = payload.signer_profile_id
    project.updated_by = current_user.id

    db.commit()
    db.refresh(project)

    log_audit_event(
        db=db,
        event_name="ProjectUpdated",
        entity_type="Project",
        entity_id=project.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UpdateProject"
    )
    db.commit()

    return project


@router.post("/{project_id}/archive", response_model=ProjectResponse)
def archive_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:archive"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectWorkflowStatus.ARCHIVED
    db.commit()
    db.refresh(project)

    log_audit_event(
        db=db,
        event_name="ProjectArchived",
        entity_type="Project",
        entity_id=project.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="ArchiveProject"
    )
    db.commit()

    return project


@router.post("/{project_id}/cancel", response_model=ProjectResponse)
def cancel_project(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:cancel"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    project.status = ProjectWorkflowStatus.CANCELLED
    db.commit()
    db.refresh(project)

    log_audit_event(
        db=db,
        event_name="ProjectCancelled",
        entity_type="Project",
        entity_id=project.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CancelProject"
    )
    db.commit()

    return project


# ==========================================
# PROJECT ASSET LINE ENDPOINTS
# ==========================================

@router.post("/{project_id}/asset-lines", response_model=ProjectAssetLineResponse, status_code=201)
def create_project_asset_line(
    project_id: uuid.UUID,
    payload: ProjectAssetLineCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    # Check unit
    if payload.unit_id:
        unit = db.query(Unit).filter(Unit.id == payload.unit_id).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

    line = ProjectAssetLine(
        project_id=project_id,
        asset_name=payload.asset_name,
        description=payload.description,
        quantity=payload.quantity,
        unit_id=payload.unit_id,
        raw_price=payload.raw_price,
        raw_price_currency_id=payload.raw_price_currency_id,
        appraised_unit_price=payload.appraised_unit_price,
        appraised_currency_id=payload.appraised_currency_id,
        review_status=AssetLineReviewStatus.PENDING,
        validation_status=AssetLineValidationStatus.UNVALIDATED,
        brand_id=payload.brand_id,
        manufacturer_id=payload.manufacturer_id
    )
    db.add(line)
    db.commit()
    db.refresh(line)

    log_audit_event(
        db=db,
        event_name="ProjectAssetLineCreated",
        entity_type="ProjectAssetLine",
        entity_id=line.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateProjectAssetLine"
    )
    db.commit()

    return line


@router.get("/{project_id}/asset-lines", response_model=List[ProjectAssetLineResponse])
def list_project_asset_lines(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:asset_line:read"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return db.query(ProjectAssetLine).filter(ProjectAssetLine.project_id == project_id).all()


@router.patch("/{project_id}/asset-lines/{line_id}", response_model=ProjectAssetLineResponse)
def update_project_asset_line(
    project_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: ProjectAssetLineUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:update"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    line = db.query(ProjectAssetLine).filter(
        ProjectAssetLine.project_id == project_id,
        ProjectAssetLine.id == line_id
    ).first()
    if not line:
        raise HTTPException(status_code=404, detail="Asset line not found")

    # Optimistic lock check
    if line.row_version != payload.row_version:
        raise HTTPException(status_code=409, detail="Optimistic lock error: Record version mismatch")

    if payload.unit_id:
        unit = db.query(Unit).filter(Unit.id == payload.unit_id).first()
        if not unit:
            raise HTTPException(status_code=404, detail="Unit not found")

    # Update line fields
    if payload.asset_name is not None:
        line.asset_name = payload.asset_name
    if payload.description is not None:
        line.description = payload.description
    if payload.quantity is not None:
        line.quantity = payload.quantity
    if payload.unit_id is not None:
        line.unit_id = payload.unit_id
    if payload.raw_price is not None:
        line.raw_price = payload.raw_price
    if payload.raw_price_currency_id is not None:
        line.raw_price_currency_id = payload.raw_price_currency_id
    if payload.appraised_unit_price is not None:
        line.appraised_unit_price = payload.appraised_unit_price
    if payload.appraised_currency_id is not None:
        line.appraised_currency_id = payload.appraised_currency_id
    if payload.brand_id is not None:
        line.brand_id = payload.brand_id
    if payload.manufacturer_id is not None:
        line.manufacturer_id = payload.manufacturer_id
    if payload.review_status is not None:
        line.review_status = payload.review_status
    if payload.validation_status is not None:
        line.validation_status = payload.validation_status

    db.commit()
    db.refresh(line)

    log_audit_event(
        db=db,
        event_name="ProjectAssetLineUpdated",
        entity_type="ProjectAssetLine",
        entity_id=line.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UpdateProjectAssetLine"
    )
    db.commit()

    return line


# ==========================================
# PROJECT FILE METADATA ENDPOINTS
# ==========================================

@router.post("/{project_id}/files", response_model=ProjectFileResponse, status_code=201)
def create_project_file_metadata(
    project_id: uuid.UUID,
    payload: ProjectFileCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:file:upload"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    pfile = ProjectFile(
        project_id=project_id,
        file_name=payload.file_name,
        file_category=payload.file_category,
        file_size=payload.file_size,
        mime_type=payload.mime_type,
        storage_object_key=payload.storage_object_key,
        checksum_sha256=payload.checksum_sha256,
        processing_status=FileProcessingStatus.PENDING,
        extracted_metadata=payload.extracted_metadata,
        uploaded_by=current_user.id
    )
    db.add(pfile)
    db.commit()
    db.refresh(pfile)

    log_audit_event(
        db=db,
        event_name="ProjectFileUploaded",
        entity_type="ProjectFile",
        entity_id=pfile.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="UploadProjectFile"
    )
    db.commit()

    return pfile


@router.get("/{project_id}/files", response_model=List[ProjectFileResponse])
def list_project_files(
    project_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    return db.query(ProjectFile).filter(ProjectFile.project_id == project_id).all()
