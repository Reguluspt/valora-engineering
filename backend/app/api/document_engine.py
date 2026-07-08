import uuid
import json
import hashlib
from datetime import datetime, timezone
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Security
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, DocumentTemplate, DocumentTemplateStatus, TemplateVersion,
    TemplateVersionStatus, TemplatePlaceholder, PlaceholderBinding,
    ComputedPlaceholderExpression, RenderJob, RenderJobStatus,
    GeneratedDocument, GeneratedDocumentStatus, DocumentPackage,
    DocumentPackageStatus, DocumentPackageItem, Project, UserActionLog
)
from app.api.document_schemas import (
    DocumentTemplateCreate, DocumentTemplateUpdate, DocumentTemplateSchema,
    TemplateVersionCreate, TemplateVersionDeprecate, TemplateVersionSchema,
    ComputedPlaceholderExpressionCreate, ComputedPlaceholderExpressionSchema,
    TemplatePlaceholderCreate, TemplatePlaceholderSchema,
    PlaceholderBindingCreate, PlaceholderBindingSchema,
    RenderJobCreate, RenderJobSchema, GeneratedDocumentSchema,
    DocumentPackageCreate, DocumentPackageSchema,
    DocumentPackageItemCreate, DocumentPackageItemSchema
)

router = APIRouter(prefix="/api/v1/document-engine", tags=["Document Engine"])

def log_action(db: Session, user_id: uuid.UUID, action_type: str, target_type: str, target_id: uuid.UUID, payload: dict):
    serialized = {}
    for k, v in payload.items():
        if isinstance(v, uuid.UUID):
            serialized[k] = str(v)
        else:
            serialized[k] = v
    log = UserActionLog(
        user_id=user_id,
        action_type=action_type,
        target_type=target_type,
        target_id=target_id,
        action_payload=serialized
    )
    db.add(log)

# ----------------- DocumentTemplate Endpoints -----------------

@router.post("/templates", response_model=DocumentTemplateSchema, status_code=201)
def create_template(
    data: DocumentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:create"))
):
    # Check code uniqueness
    existing = db.query(DocumentTemplate).filter(DocumentTemplate.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")

    tpl = DocumentTemplate(
        organization_id=data.organization_id,
        document_type=data.document_type,
        code=data.code,
        name=data.name,
        description=data.description,
        status=data.status,
        created_by=current_user.id
    )
    db.add(tpl)
    db.commit()
    db.refresh(tpl)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_TEMPLATE_CREATE",
        entity_type="document_template",
        entity_id=tpl.id,
        organization_id=tpl.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_template", "document_template", tpl.id, {"code": tpl.code})
    db.commit()
    return tpl


@router.get("/templates", response_model=List[DocumentTemplateSchema])
def list_templates(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    return db.query(DocumentTemplate).all()


@router.get("/templates/{template_id}", response_model=DocumentTemplateSchema)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")
    return tpl


@router.patch("/templates/{template_id}", response_model=DocumentTemplateSchema)
def update_template(
    template_id: uuid.UUID,
    data: DocumentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    # Optimistic locking check
    if data.expected_row_version is not None:
        if tpl.row_version != data.expected_row_version:
            raise HTTPException(status_code=409, detail="Stale row version")

    if data.name is not None:
        tpl.name = data.name
    if data.description is not None:
        tpl.description = data.description
    if data.status is not None:
        tpl.status = data.status
    if data.current_version_id is not None:
        ver = db.query(TemplateVersion).filter(TemplateVersion.id == data.current_version_id).first()
        if not ver:
            raise HTTPException(status_code=404, detail="Version not found")
        tpl.current_version_id = data.current_version_id
    if data.replacement_template_id is not None:
        tpl.replacement_template_id = data.replacement_template_id

    db.commit()
    db.refresh(tpl)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_TEMPLATE_UPDATE",
        entity_type="document_template",
        entity_id=tpl.id,
        organization_id=tpl.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "update_template", "document_template", tpl.id, {})
    db.commit()
    return tpl


# ----------------- TemplateVersion Endpoints -----------------

@router.post("/templates/{template_id}/versions", response_model=TemplateVersionSchema, status_code=201)
def create_version(
    template_id: uuid.UUID,
    data: TemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:create"))
):
    tpl = db.query(DocumentTemplate).filter(DocumentTemplate.id == template_id).first()
    if not tpl:
        raise HTTPException(status_code=404, detail="Template not found")

    existing = db.query(TemplateVersion).filter(
        TemplateVersion.document_template_id == template_id,
        TemplateVersion.version_number == data.version_number
    ).first()
    if existing:
        raise HTTPException(status_code=400, detail="Version number already exists for this template")

    ver = TemplateVersion(
        document_template_id=template_id,
        version_number=data.version_number,
        source_file_id=data.source_file_id,
        template_format=data.template_format,
        placeholder_manifest=data.placeholder_manifest,
        status=data.status
    )
    db.add(ver)
    db.commit()
    db.refresh(ver)

    log_audit_event(
        db=db,
        event_name="TEMPLATE_VERSION_CREATE",
        entity_type="template_version",
        entity_id=ver.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_version", "template_version", ver.id, {"version_number": ver.version_number})
    db.commit()
    return ver


@router.get("/template-versions/{version_id}", response_model=TemplateVersionSchema)
def get_version(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    ver = db.query(TemplateVersion).filter(TemplateVersion.id == version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")
    return ver


@router.post("/template-versions/{version_id}/deprecate", response_model=TemplateVersionSchema)
def deprecate_version(
    version_id: uuid.UUID,
    data: TemplateVersionDeprecate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:deprecate"))
):
    ver = db.query(TemplateVersion).filter(TemplateVersion.id == version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    if ver.row_version != data.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    ver.status = TemplateVersionStatus.DEPRECATED
    ver.deprecation_reason = data.deprecation_reason
    if data.replacement_version_id is not None:
        ver.replacement_version_id = data.replacement_version_id

    db.commit()
    db.refresh(ver)

    log_audit_event(
        db=db,
        event_name="TEMPLATE_VERSION_DEPRECATE",
        entity_type="template_version",
        entity_id=ver.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "deprecate_version", "template_version", ver.id, {})
    db.commit()
    return ver


# ----------------- TemplatePlaceholder Endpoints -----------------

@router.get("/template-versions/{version_id}/placeholders", response_model=List[TemplatePlaceholderSchema])
def list_placeholders(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    return db.query(TemplatePlaceholder).filter(TemplatePlaceholder.template_version_id == version_id).all()


@router.post("/template-versions/{version_id}/placeholders", response_model=TemplatePlaceholderSchema, status_code=201)
def create_placeholder(
    version_id: uuid.UUID,
    data: TemplatePlaceholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    ver = db.query(TemplateVersion).filter(TemplateVersion.id == version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    pl = TemplatePlaceholder(
        template_version_id=version_id,
        placeholder_key=data.placeholder_key,
        label_vi=data.label_vi,
        data_type=data.data_type,
        source_context=data.source_context,
        source_path=data.source_path,
        is_required=data.is_required,
        default_value=data.default_value,
        format_rule=data.format_rule,
        validation_rule=data.validation_rule,
        computed_expression_id=data.computed_expression_id,
        status=data.status
    )
    db.add(pl)
    db.commit()
    db.refresh(pl)

    log_audit_event(
        db=db,
        event_name="TEMPLATE_PLACEHOLDER_CREATE",
        entity_type="template_placeholder",
        entity_id=pl.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_placeholder", "template_placeholder", pl.id, {"key": pl.placeholder_key})
    db.commit()
    return pl


# ----------------- PlaceholderBinding Endpoints -----------------

@router.post("/template-versions/{version_id}/bindings", response_model=PlaceholderBindingSchema, status_code=201)
def create_binding(
    version_id: uuid.UUID,
    data: PlaceholderBindingCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    ver = db.query(TemplateVersion).filter(TemplateVersion.id == version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    bind = PlaceholderBinding(
        template_version_id=version_id,
        template_placeholder_id=data.template_placeholder_id,
        binding_path=data.binding_path,
        binding_type=data.binding_type,
        fallback_value=data.fallback_value,
        is_required=data.is_required
    )
    db.add(bind)
    db.commit()
    db.refresh(bind)

    log_audit_event(
        db=db,
        event_name="PLACEHOLDER_BINDING_CREATE",
        entity_type="placeholder_binding",
        entity_id=bind.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_binding", "placeholder_binding", bind.id, {})
    db.commit()
    return bind


# ----------------- ComputedPlaceholderExpression Endpoints -----------------

@router.post("/template-versions/{version_id}/computed-expressions", response_model=ComputedPlaceholderExpressionSchema, status_code=201)
def create_computed_expression(
    version_id: uuid.UUID,
    data: ComputedPlaceholderExpressionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    ver = db.query(TemplateVersion).filter(TemplateVersion.id == version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    expr = ComputedPlaceholderExpression(
        placeholder_key=data.placeholder_key,
        expression_type=data.expression_type,
        inputs=data.inputs,
        expression=data.expression,
        output_data_type=data.output_data_type,
        created_by=current_user.id
    )
    db.add(expr)
    db.commit()
    db.refresh(expr)

    log_audit_event(
        db=db,
        event_name="COMPUTED_EXPRESSION_CREATE",
        entity_type="computed_expression",
        entity_id=expr.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_expression", "computed_expression", expr.id, {"key": expr.placeholder_key})
    db.commit()
    return expr


# ----------------- RenderJob & GeneratedDocument Endpoints -----------------

@router.post("/render-jobs", response_model=RenderJobSchema, status_code=201)
def create_render_job(
    data: RenderJobCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:render:create"))
):
    proj = db.query(Project).filter(Project.id == data.project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    ver = db.query(TemplateVersion).filter(TemplateVersion.id == data.template_version_id).first()
    if not ver:
        raise HTTPException(status_code=404, detail="Version not found")

    serialized_snapshot = json.dumps(data.data_snapshot, sort_keys=True)
    snapshot_hash = hashlib.sha256(serialized_snapshot.encode()).hexdigest()

    job = RenderJob(
        project_id=data.project_id,
        template_version_id=data.template_version_id,
        render_mode=data.render_mode,
        output_formats=data.output_formats,
        data_snapshot=data.data_snapshot,
        data_snapshot_hash=snapshot_hash,
        status=RenderJobStatus.COMPLETED,
        created_by=current_user.id,
        started_at=datetime.now(timezone.utc),
        completed_at=datetime.now(timezone.utc)
    )
    db.add(job)
    db.commit()
    db.refresh(job)

    for fmt in data.output_formats:
        doc = GeneratedDocument(
            project_id=data.project_id,
            render_job_id=job.id,
            document_type=ver.document_template.document_type,
            output_format=fmt,
            filename=f"mock_doc_{job.id}.{fmt}",
            storage_key=f"documents/mock_doc_{job.id}.{fmt}",
            checksum_sha256=snapshot_hash,
            file_size_bytes=4096,
            template_version_id=ver.id,
            data_snapshot_hash=snapshot_hash,
            status=GeneratedDocumentStatus.DRAFT
        )
        db.add(doc)

    db.commit()

    log_audit_event(
        db=db,
        event_name="RENDER_JOB_CREATE",
        entity_type="render_job",
        entity_id=job.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_render_job", "render_job", job.id, {"hash": snapshot_hash})
    db.commit()
    return job


@router.get("/render-jobs/{render_job_id}", response_model=RenderJobSchema)
def get_render_job(
    render_job_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    job = db.query(RenderJob).filter(RenderJob.id == render_job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return job


@router.get("/generated-documents/{generated_document_id}", response_model=GeneratedDocumentSchema)
def get_generated_document(
    generated_document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == generated_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Generated document not found")
    return doc


# ----------------- DocumentPackage Endpoints -----------------

@router.post("/packages", response_model=DocumentPackageSchema, status_code=201)
def create_package(
    data: DocumentPackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:package:create"))
):
    proj = db.query(Project).filter(Project.id == data.project_id).first()
    if not proj:
        raise HTTPException(status_code=404, detail="Project not found")

    pkg = DocumentPackage(
        project_id=data.project_id,
        package_type=data.package_type,
        name=data.name,
        status=data.status,
        created_by=current_user.id
    )
    db.add(pkg)
    db.commit()
    db.refresh(pkg)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_PACKAGE_CREATE",
        entity_type="document_package",
        entity_id=pkg.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_package", "document_package", pkg.id, {"name": pkg.name})
    db.commit()
    return pkg


@router.get("/packages/{package_id}", response_model=DocumentPackageSchema)
def get_package(
    package_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    pkg = db.query(DocumentPackage).filter(DocumentPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")
    return pkg


@router.post("/packages/{package_id}/items", response_model=DocumentPackageItemSchema, status_code=201)
def add_package_item(
    package_id: uuid.UUID,
    data: DocumentPackageItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:package:update"))
):
    pkg = db.query(DocumentPackage).filter(DocumentPackage.id == package_id).first()
    if not pkg:
        raise HTTPException(status_code=404, detail="Package not found")

    doc = db.query(GeneratedDocument).filter(GeneratedDocument.id == data.generated_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Generated document not found")

    item = DocumentPackageItem(
        document_package_id=package_id,
        generated_document_id=data.generated_document_id,
        sort_order=data.sort_order
    )
    db.add(item)
    db.commit()
    db.refresh(item)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_PACKAGE_ITEM_ADD",
        entity_type="document_package_item",
        entity_id=item.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "add_package_item", "document_package_item", item.id, {"sort_order": item.sort_order})
    db.commit()
    return item
