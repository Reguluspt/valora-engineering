import uuid
import re
from typing import Optional, List
from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, Request
from sqlalchemy.orm import Session
from sqlalchemy import or_, func

from app.db import get_db
from app.core.rbac import require_permission
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
    Unit,
    WorkbenchSession,
    WorkbenchSessionStatus,
    InlineEditDraft,
    InlineEditDraftStatus,
    UndoRedoStackEntry,
    UndoRedoActionType,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ImportBatchStatus,
)
from app.modules.project_master_data.schemas import (
    ProjectCreate, ProjectUpdate, ProjectResponse,
    ProjectAssetLineCreate, ProjectAssetLineUpdate, ProjectAssetLineResponse,
    ProjectAssetLinePaginationResponse,
    ProjectFileCreate, ProjectFileResponse,
    ProjectResolutionResponse
)
from app.modules.project_master_data.workbench_schemas import (
    ProjectDraftStateResponse,
    AssetLineDraftStateSchema,
    AssetLineDraftSaveRequest,
    AssetLineDraftSaveResponse,
    AssetLineDraftCommitRequest,
    AssetLineDraftCommitResponse,
    ProjectAssetImportBatchCreate,
    ProjectAssetImportBatchResponse,
    ProjectAssetImportBatchApplyRequest,
    ProjectAssetImportBatchApplyResponse,
    ProjectAssetImportStagingRowPaginationResponse
)
from app.modules.project_master_data.commands.commit_asset_line_draft import execute_commit_asset_line_draft
from app.modules.excel_import.application.import_service import upload_excel_file_orchestrator
from app.modules.excel_import.application.source_artifact_service import (
    get_source_artifact,
    list_source_artifacts,
    upload_source_artifact,
)
from app.modules.excel_import.application.workbook_structure_service import (
    analyze_source_artifact_structure,
    get_structure_snapshot,
    list_structure_snapshots,
)
from app.modules.excel_import.schemas import (
    ImportSourceArtifactResponse,
    WorkbookStructureSnapshotResponse,
)
from app.modules.excel_import.application.validate_staging import (
    validate_project_asset_import_batch,
)
from app.modules.excel_import.application.apply_staging import (
    apply_project_asset_import_batch,
)


def get_correlation_id(request: Request) -> str:
    return request.headers.get("X-Correlation-Id", "")


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


def slugify(text: str) -> str:
    text = text.lower().strip()
    text = re.sub(r'[^a-z0-9\-]+', '-', text)
    text = re.sub(r'-+', '-', text)
    return text.strip('-')


@router.get("/resolve", response_model=ProjectResolutionResponse)
def resolve_project(
    ref: str = Query(..., min_length=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read"))
):
    org_id = current_user.organization_id

    # 1. Check if ref is a valid UUID
    try:
        ref_uuid = uuid.UUID(ref)
        project = db.query(Project).filter(
            Project.organization_id == org_id,
            Project.id == ref_uuid
        ).first()
        if project:
            return {
                "project_id": project.id,
                "display_name": project.name,
                "matched_by": "id"
            }
    except ValueError:
        pass

    # 2. Try exact match on code (case-insensitive)
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        func.lower(Project.code) == ref.lower()
    ).first()
    if project:
        return {
            "project_id": project.id,
            "display_name": project.name,
            "matched_by": "code"
        }

    # 3. Try exact match on name (case-insensitive)
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        func.lower(Project.name) == ref.lower()
    ).first()
    if project:
        return {
            "project_id": project.id,
            "display_name": project.name,
            "matched_by": "name"
        }

    # 4. Try slugified comparison in Python on all org projects
    projects = db.query(Project).filter(Project.organization_id == org_id).all()
    target_slug = slugify(ref)
    
    matches = []
    for p in projects:
        if slugify(p.code) == target_slug:
            matches.append((p, "code_slug"))
        elif slugify(p.name) == target_slug:
            matches.append((p, "name_slug"))
            
    if len(matches) == 1:
        p, match_type = matches[0]
        return {
            "project_id": p.id,
            "display_name": p.name,
            "matched_by": match_type
        }
    elif len(matches) > 1:
        raise HTTPException(
            status_code=409,
            detail="Multiple projects matched this reference. Please specify exact project ID."
        )

    raise HTTPException(status_code=404, detail="Project not found")


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


@router.get("/{project_id}/asset-lines", response_model=ProjectAssetLinePaginationResponse)
def list_project_asset_lines(
    project_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    search: Optional[str] = None,
    validation_status: Optional[str] = None,
    valuation_status: Optional[str] = None,
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

    query = db.query(ProjectAssetLine).filter(ProjectAssetLine.project_id == project_id)

    if search:
        query = query.filter(
            or_(
                ProjectAssetLine.asset_name.ilike(f"%{search}%"),
                ProjectAssetLine.description.ilike(f"%{search}%")
            )
        )
    if validation_status:
        query = query.filter(ProjectAssetLine.validation_status == validation_status)
    if valuation_status:
        query = query.filter(ProjectAssetLine.review_status == valuation_status)

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return {
        "project_id": project_id,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/{project_id}/asset-imports", response_model=ProjectAssetImportBatchResponse, status_code=201)
def create_project_asset_import(
    project_id: uuid.UUID,
    payload: ProjectAssetImportBatchCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    batch = ProjectAssetImportBatch(
        organization_id=org_id,
        project_id=project_id,
        source_filename=payload.source_filename,
        source_sheet_name=payload.source_sheet_name,
        status=ImportBatchStatus.CREATED,
        total_rows=0,
        valid_rows=0,
        invalid_rows=0,
        warning_rows=0,
        created_by_user_id=current_user.id
    )
    db.add(batch)
    db.commit()
    db.refresh(batch)

    log_audit_event(
        db=db,
        event_name="ProjectAssetImportBatchCreated",
        entity_type="ProjectAssetImportBatch",
        entity_id=batch.id,
        organization_id=org_id,
        actor_user_id=current_user.id,
        command_name="CreateProjectAssetImportBatch"
    )
    db.commit()

    return batch


@router.get("/{project_id}/asset-imports", response_model=List[ProjectAssetImportBatchResponse])
def list_project_asset_imports(
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

    batches = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.organization_id == org_id
    ).all()

    return batches


@router.get("/{project_id}/asset-imports/{batch_id}/rows", response_model=ProjectAssetImportStagingRowPaginationResponse)
def list_project_asset_import_rows(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    validation_status: Optional[str] = None,
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

    batch = db.query(ProjectAssetImportBatch).filter(
        ProjectAssetImportBatch.organization_id == org_id,
        ProjectAssetImportBatch.project_id == project_id,
        ProjectAssetImportBatch.id == batch_id
    ).first()
    if not batch:
        raise HTTPException(status_code=404, detail="Import batch not found")

    query = db.query(ProjectAssetImportStagingRow).filter(
        ProjectAssetImportStagingRow.import_batch_id == batch_id,
        ProjectAssetImportStagingRow.organization_id == org_id,
        ProjectAssetImportStagingRow.project_id == project_id
    )

    if validation_status:
        query = query.filter(ProjectAssetImportStagingRow.validation_status == validation_status)

    total = query.count()
    items = query.offset(offset).limit(limit).all()

    return {
        "project_id": project_id,
        "import_batch_id": batch_id,
        "items": items,
        "total": total,
        "limit": limit,
        "offset": offset
    }


@router.post("/{project_id}/asset-imports/{batch_id}/upload", response_model=ProjectAssetImportBatchResponse)
def upload_project_asset_import_file(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    correlation_id = get_correlation_id(request) if request else None
    return upload_excel_file_orchestrator(
        db=db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        file=file,
        request=request,
        current_user=current_user,
        correlation_id=correlation_id
    )


@router.post(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts",
    response_model=ImportSourceArtifactResponse,
    status_code=201,
)
def upload_project_asset_import_source_artifact(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    file: UploadFile = File(...),
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit")),
):
    """S13-PR-002: Adaptive Intake v2 source artifact intake (.xls/.xlsx). No staging mutation."""
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    correlation_id = get_correlation_id(request) if request else None
    art = upload_source_artifact(
        db=db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        file=file,
        request=request,
        current_user=current_user,
        correlation_id=correlation_id,
    )
    return art


@router.get(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts",
    response_model=list[ImportSourceArtifactResponse],
)
def list_project_asset_import_source_artifacts(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    org_id = current_user.organization_id
    return list_source_artifacts(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
    )


@router.get(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts/{artifact_id}",
    response_model=ImportSourceArtifactResponse,
)
def get_project_asset_import_source_artifact(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    org_id = current_user.organization_id
    return get_source_artifact(
        db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
    )


@router.post(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts/"
    "{artifact_id}/structure-snapshots",
    response_model=WorkbookStructureSnapshotResponse,
    status_code=201,
)
def analyze_project_asset_import_source_structure(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit")),
):
    """S13-PR-003: append deterministic structure evidence; never mutate staging."""
    return analyze_source_artifact_structure(
        db,
        org_id=current_user.organization_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        current_user=current_user,
        correlation_id=get_correlation_id(request),
    )


@router.get(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts/"
    "{artifact_id}/structure-snapshots",
    response_model=list[WorkbookStructureSnapshotResponse],
)
def list_project_asset_import_source_structure_snapshots(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    return list_structure_snapshots(
        db,
        org_id=current_user.organization_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
    )


@router.get(
    "/{project_id}/asset-imports/{batch_id}/source-artifacts/"
    "{artifact_id}/structure-snapshots/{snapshot_id}",
    response_model=WorkbookStructureSnapshotResponse,
)
def get_project_asset_import_source_structure_snapshot(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    artifact_id: uuid.UUID,
    snapshot_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("project:read")),
):
    return get_structure_snapshot(
        db,
        org_id=current_user.organization_id,
        project_id=project_id,
        batch_id=batch_id,
        artifact_id=artifact_id,
        snapshot_id=snapshot_id,
    )


@router.post(
    "/{project_id}/asset-imports/{batch_id}/validate",
    response_model=ProjectAssetImportBatchResponse,
)
def validate_project_asset_import_batch_endpoint(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit")),
):
    """S12-PR-003: deterministic staging validation (staging-only, no ProjectAssetLine)."""
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    correlation_id = get_correlation_id(request) if request else None
    return validate_project_asset_import_batch(
        db=db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        current_user=current_user,
        correlation_id=correlation_id,
    )


@router.post(
    "/{project_id}/asset-imports/{batch_id}/apply",
    response_model=ProjectAssetImportBatchApplyResponse,
)
def apply_project_asset_import_batch_endpoint(
    project_id: uuid.UUID,
    batch_id: uuid.UUID,
    payload: ProjectAssetImportBatchApplyRequest,
    request: Request = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit")),
):
    """S12-PR-004: apply validated staging to official ProjectAssetLine with lineage."""
    org_id = current_user.organization_id
    project = db.query(Project).filter(
        Project.organization_id == org_id,
        Project.id == project_id,
    ).first()
    if not project:
        raise HTTPException(status_code=404, detail="Project not found")

    correlation_id = get_correlation_id(request) if request else None
    result = apply_project_asset_import_batch(
        db=db,
        org_id=org_id,
        project_id=project_id,
        batch_id=batch_id,
        current_user=current_user,
        confirm=payload.confirm,
        correlation_id=correlation_id,
    )
    return ProjectAssetImportBatchApplyResponse(**result)


@router.get("/{project_id}/asset-lines/draft-state", response_model=ProjectDraftStateResponse)
def get_project_asset_lines_draft_state(
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

    session = db.query(WorkbenchSession).filter(
        WorkbenchSession.project_id == project_id,
        WorkbenchSession.user_id == current_user.id,
        WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
    ).first()

    if not session:
        return {
            "project_id": project_id,
            "items": [],
            "total": 0
        }

    drafts = db.query(InlineEditDraft).filter(
        InlineEditDraft.session_id == session.id
    ).all()

    from collections import defaultdict
    drafts_by_line = defaultdict(list)
    for d in drafts:
        if d.target_type == "ProjectAssetLine":
            drafts_by_line[d.target_id].append(d)

    items = []
    for line_id, d_list in drafts_by_line.items():
        line = db.query(ProjectAssetLine).filter(
            ProjectAssetLine.project_id == project_id,
            ProjectAssetLine.id == line_id
        ).first()
        if not line:
            continue

        changed_fields = [d.field_key for d in d_list]
        is_stale = any(d.base_row_version is not None and d.base_row_version < line.row_version for d in d_list)
        draft_status = "stale" if is_stale else "saved_draft"
        last_saved = max(d.updated_at for d in d_list) if d_list else None

        items.append(
            AssetLineDraftStateSchema(
                asset_line_id=line_id,
                has_saved_draft=True,
                has_unsaved_changes=False,
                is_locked=False,
                is_stale=is_stale,
                draft_status=draft_status,
                changed_fields=changed_fields,
                last_saved_at=last_saved,
                last_saved_by=current_user.id
            )
        )

    return {
        "project_id": project_id,
        "items": items,
        "total": len(items)
    }


@router.patch("/{project_id}/asset-lines/{line_id}/draft", response_model=AssetLineDraftSaveResponse)
def save_asset_line_draft(
    project_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: AssetLineDraftSaveRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
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

    # Validate field allowlist (minimal safe fields)
    ALLOWED_FIELDS = {"description", "appraised_unit_price"}
    if payload.field_key not in ALLOWED_FIELDS:
        raise HTTPException(status_code=400, detail="Field not supported for draft editing")

    try:
        base_version = int(payload.version_token)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid version token format")

    if base_version < (line.row_version or 1):
        raise HTTPException(status_code=409, detail="Stale row version: Conflict detected")

    session = db.query(WorkbenchSession).filter(
        WorkbenchSession.project_id == project_id,
        WorkbenchSession.user_id == current_user.id,
        WorkbenchSession.status == WorkbenchSessionStatus.ACTIVE
    ).first()

    if not session:
        session = WorkbenchSession(
            user_id=current_user.id,
            project_id=project_id,
            status=WorkbenchSessionStatus.ACTIVE
        )
        db.add(session)
        db.commit()
        db.refresh(session)

    draft = db.query(InlineEditDraft).filter(
        InlineEditDraft.session_id == session.id,
        InlineEditDraft.target_id == line_id,
        InlineEditDraft.field_key == payload.field_key
    ).first()

    from datetime import datetime, timezone
    now = datetime.now(timezone.utc)

    draft_val_dict = {"value": payload.draft_value}
    base_val_dict = {"value": payload.base_value} if payload.base_value is not None else None

    if draft:
        draft.draft_value = draft_val_dict
        draft.base_value = base_val_dict
        draft.base_row_version = base_version
        draft.updated_at = now
    else:
        draft = InlineEditDraft(
            session_id=session.id,
            target_type="ProjectAssetLine",
            target_id=line_id,
            field_key=payload.field_key,
            draft_value=draft_val_dict,
            base_value=base_val_dict,
            base_row_version=base_version,
            status=InlineEditDraftStatus.DRAFT,
            updated_at=now
        )
        db.add(draft)

    max_seq = db.query(func.max(UndoRedoStackEntry.sequence_no)).filter(UndoRedoStackEntry.session_id == session.id).scalar() or 0
    stack = UndoRedoStackEntry(
        session_id=session.id,
        sequence_no=max_seq + 1,
        target_type="ProjectAssetLine",
        target_id=line_id,
        field_key=payload.field_key,
        after_value=draft_val_dict,
        before_value=base_val_dict,
        action_type=UndoRedoActionType.EDIT
    )
    db.add(stack)
    db.commit()

    all_drafts = db.query(InlineEditDraft).filter(
        InlineEditDraft.session_id == session.id,
        InlineEditDraft.target_id == line_id
    ).all()
    changed_fields = [d.field_key for d in all_drafts]

    return {
        "project_id": project_id,
        "asset_line_id": line_id,
        "draft_status": "saved_draft",
        "field_key": payload.field_key,
        "has_saved_draft": True,
        "has_unsaved_changes": False,
        "is_stale": False,
        "changed_fields": changed_fields,
        "saved_at": now
    }


@router.post("/{project_id}/asset-lines/{line_id}/draft/commit", response_model=AssetLineDraftCommitResponse)
def commit_asset_line_draft(
    project_id: uuid.UUID,
    line_id: uuid.UUID,
    payload: AssetLineDraftCommitRequest,
    request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("workbench:edit"))
):
    correlation_id = get_correlation_id(request)
    try:
        res = execute_commit_asset_line_draft(
            db=db,
            actor=current_user,
            project_id=project_id,
            line_id=line_id,
            field_keys=payload.field_keys,
            confirm=payload.confirm,
            version_token=payload.version_token,
            correlation_id=correlation_id,
        )
        db.commit()
        return res
    except Exception:
        db.rollback()
        raise


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

    # Reject direct mutations of workbench-gated fields — check field presence not value
    FORBIDDEN_PATCH_FIELDS = {"description", "appraised_unit_price", "review_status", "validation_status"}
    forbidden_in_payload = FORBIDDEN_PATCH_FIELDS & payload.model_fields_set
    if forbidden_in_payload:
        raise HTTPException(
            status_code=400,
            detail={
                "title": "Trường dữ liệu bị hạn chế",
                "message": "Trường description, appraised_unit_price, review_status, và validation_status chỉ có thể cập nhật thông qua áp dụng bản nháp.",
                "nextAction": "Vui lòng sử dụng tính năng áp dụng bản nháp của Workbench.",
                "severity": "error",
                "retryable": False,
            },
        )

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
