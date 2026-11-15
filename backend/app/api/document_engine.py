import uuid
import json
import hashlib
from datetime import datetime, timezone
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import and_
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, aliased
from sqlalchemy.orm.exc import StaleDataError

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, DocumentTemplate, TemplateVersion,
    TemplateVersionStatus, TemplatePlaceholder, PlaceholderBinding,
    ComputedPlaceholderExpression, RenderJob, RenderJobStatus,
    GeneratedDocument, GeneratedDocumentStatus, DocumentPackage,
    DocumentPackageItem, Project, UserActionLog, EvidenceFile, EvidenceFileStatus
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


def _tenant_templates(db: Session, organization_id: uuid.UUID):
    return db.query(DocumentTemplate).filter(DocumentTemplate.organization_id == organization_id)


def _get_template(db: Session, organization_id: uuid.UUID, template_id: uuid.UUID) -> DocumentTemplate:
    template = _tenant_templates(db, organization_id).filter(DocumentTemplate.id == template_id).first()
    if template is None:
        raise HTTPException(status_code=404, detail="Template not found")
    return template


def _get_version(db: Session, organization_id: uuid.UUID, version_id: uuid.UUID) -> TemplateVersion:
    version = (
        db.query(TemplateVersion)
        .join(TemplateVersion.document_template)
        .filter(TemplateVersion.id == version_id, DocumentTemplate.organization_id == organization_id)
        .first()
    )
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


def _get_version_in_template(db: Session, template_id: uuid.UUID, version_id: uuid.UUID) -> TemplateVersion:
    version = db.query(TemplateVersion).filter(
        TemplateVersion.id == version_id,
        TemplateVersion.document_template_id == template_id,
    ).first()
    if version is None:
        raise HTTPException(status_code=404, detail="Version not found")
    return version


def _get_project(db: Session, organization_id: uuid.UUID, project_id: uuid.UUID) -> Project:
    project = db.query(Project).filter(Project.id == project_id, Project.organization_id == organization_id).first()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    return project


def _get_package(db: Session, organization_id: uuid.UUID, package_id: uuid.UUID) -> DocumentPackage:
    package = (
        db.query(DocumentPackage)
        .join(DocumentPackage.project)
        .filter(DocumentPackage.id == package_id, Project.organization_id == organization_id)
        .first()
    )
    if package is None:
        raise HTTPException(status_code=404, detail="Package not found")
    return package


def _get_generated_document(
    db: Session, organization_id: uuid.UUID, document_id: uuid.UUID, *, project_id: uuid.UUID | None = None
) -> GeneratedDocument:
    query = (
        db.query(GeneratedDocument)
        .join(RenderJob, and_(
            RenderJob.id == GeneratedDocument.render_job_id,
            RenderJob.project_id == GeneratedDocument.project_id,
            RenderJob.template_version_id == GeneratedDocument.template_version_id,
        ))
        .join(RenderJob.project)
        .join(RenderJob.creator)
        .join(RenderJob.template_version)
        .join(TemplateVersion.document_template)
        .filter(
            GeneratedDocument.id == document_id,
            Project.organization_id == organization_id,
            User.organization_id == organization_id,
            DocumentTemplate.organization_id == organization_id,
        )
    )
    if project_id is not None:
        query = query.filter(GeneratedDocument.project_id == project_id)
    document = query.first()
    if document is None:
        raise HTTPException(status_code=404, detail="Generated document not found")
    return document


def _template_views(templates):
    replacement = aliased(DocumentTemplate)
    rows = (
        templates.outerjoin(TemplateVersion, and_(
            TemplateVersion.id == DocumentTemplate.current_version_id,
            TemplateVersion.document_template_id == DocumentTemplate.id,
        ))
        .outerjoin(replacement, and_(
            replacement.id == DocumentTemplate.replacement_template_id,
            replacement.organization_id == DocumentTemplate.organization_id,
        ))
        .with_entities(DocumentTemplate, TemplateVersion.id, replacement.id)
        .all()
    )
    return [
        DocumentTemplateSchema.model_validate(template).model_copy(update={
            "current_version_id": current_id, "replacement_template_id": replacement_id,
        })
        for template, current_id, replacement_id in rows
    ]


def _version_view(db: Session, version: TemplateVersion, organization_id: uuid.UUID) -> TemplateVersionSchema:
    view = TemplateVersionSchema.model_validate(version)
    if view.source_file_id is not None:
        source = db.query(EvidenceFile.id).join(EvidenceFile.uploader).filter(
            EvidenceFile.id == view.source_file_id, User.organization_id == organization_id,
        ).first()
        if source is None:
            view.source_file_id = None
    if view.replacement_version_id is not None:
        replacement = db.query(TemplateVersion.id).filter(
            TemplateVersion.id == view.replacement_version_id,
            TemplateVersion.document_template_id == version.document_template_id,
        ).first()
        if replacement is None:
            view.replacement_version_id = None
    return view


def _placeholder_expressions(db: Session, version_id: uuid.UUID):
    return (
        db.query(TemplatePlaceholder, ComputedPlaceholderExpression.id)
        .outerjoin(ComputedPlaceholderExpression, and_(
            ComputedPlaceholderExpression.id == TemplatePlaceholder.computed_expression_id,
            ComputedPlaceholderExpression.template_version_id == TemplatePlaceholder.template_version_id,
        ))
        .filter(TemplatePlaceholder.template_version_id == version_id)
    )


def _flush_unique_insert(db: Session, constraint: str, detail: str) -> None:
    try:
        db.flush()
    except IntegrityError as exc:
        db.rollback()
        if getattr(getattr(exc.orig, "diag", None), "constraint_name", None) == constraint:
            raise HTTPException(status_code=400, detail=detail) from exc
        raise


def _flush_versioned_update(db: Session) -> None:
    try:
        db.flush()
    except StaleDataError as exc:
        db.rollback()
        raise HTTPException(status_code=409, detail="Stale row version") from exc


# ----------------- DocumentTemplate Endpoints -----------------

@router.post("/templates", response_model=DocumentTemplateSchema, status_code=201)
def create_template(
    data: DocumentTemplateCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:create"))
):
    if data.organization_id != current_user.organization_id:
        raise HTTPException(status_code=403, detail="Organization does not match the authenticated user")

    existing = _tenant_templates(db, current_user.organization_id).filter(DocumentTemplate.code == data.code).first()
    if existing:
        raise HTTPException(status_code=400, detail="Template code already exists")

    tpl = DocumentTemplate(
        organization_id=current_user.organization_id,
        document_type=data.document_type,
        code=data.code,
        name=data.name,
        description=data.description,
        status=data.status,
        created_by=current_user.id
    )
    db.add(tpl)
    _flush_unique_insert(db, "uq_document_templates_org_code", "Template code already exists")

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
    return _template_views(_tenant_templates(db, current_user.organization_id))


@router.get("/templates/{template_id}", response_model=DocumentTemplateSchema)
def get_template(
    template_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    templates = _tenant_templates(db, current_user.organization_id).filter(DocumentTemplate.id == template_id)
    views = _template_views(templates)
    if not views:
        raise HTTPException(status_code=404, detail="Template not found")
    return views[0]


@router.patch("/templates/{template_id}", response_model=DocumentTemplateSchema)
def update_template(
    template_id: uuid.UUID,
    data: DocumentTemplateUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    tpl = _get_template(db, current_user.organization_id, template_id)

    if data.expected_row_version is not None and tpl.row_version != data.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if data.current_version_id is not None:
        _get_version_in_template(db, tpl.id, data.current_version_id)
    if data.replacement_template_id is not None:
        _get_template(db, current_user.organization_id, data.replacement_template_id)

    if data.name is not None:
        tpl.name = data.name
    if data.description is not None:
        tpl.description = data.description
    if data.status is not None:
        tpl.status = data.status
    if data.current_version_id is not None:
        tpl.current_version_id = data.current_version_id
    if data.replacement_template_id is not None:
        tpl.replacement_template_id = data.replacement_template_id

    _flush_versioned_update(db)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_TEMPLATE_UPDATE",
        entity_type="document_template",
        entity_id=tpl.id,
        organization_id=tpl.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "update_template", "document_template", tpl.id, {})
    views = _template_views(_tenant_templates(db, current_user.organization_id).filter(DocumentTemplate.id == tpl.id))
    db.commit()
    return views[0]


# ----------------- TemplateVersion Endpoints -----------------

@router.post("/templates/{template_id}/versions", response_model=TemplateVersionSchema, status_code=201)
def create_version(
    template_id: uuid.UUID,
    data: TemplateVersionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:create"))
):
    _get_template(db, current_user.organization_id, template_id)

    if data.source_file_id is not None:
        source = (
            db.query(EvidenceFile.id)
            .join(EvidenceFile.uploader)
            .filter(
                EvidenceFile.id == data.source_file_id,
                EvidenceFile.status == EvidenceFileStatus.ACTIVE,
                User.organization_id == current_user.organization_id,
            )
            .with_for_update(of=EvidenceFile, read=True)
            .first()
        )
        if source is None:
            raise HTTPException(status_code=404, detail="Source file not found")

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
    _flush_unique_insert(db, "uq_template_version_no", "Version number already exists for this template")

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
    version = _get_version(db, current_user.organization_id, version_id)
    return _version_view(db, version, current_user.organization_id)


@router.post("/template-versions/{version_id}/deprecate", response_model=TemplateVersionSchema)
def deprecate_version(
    version_id: uuid.UUID,
    data: TemplateVersionDeprecate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:deprecate"))
):
    ver = _get_version(db, current_user.organization_id, version_id)

    if ver.row_version != data.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    if data.replacement_version_id is not None:
        _get_version_in_template(db, ver.document_template_id, data.replacement_version_id)

    ver.status = TemplateVersionStatus.DEPRECATED
    ver.deprecation_reason = data.deprecation_reason
    if data.replacement_version_id is not None:
        ver.replacement_version_id = data.replacement_version_id

    _flush_versioned_update(db)

    log_audit_event(
        db=db,
        event_name="TEMPLATE_VERSION_DEPRECATE",
        entity_type="template_version",
        entity_id=ver.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "deprecate_version", "template_version", ver.id, {})
    view = _version_view(db, ver, current_user.organization_id)
    db.commit()
    return view


# ----------------- TemplatePlaceholder Endpoints -----------------

@router.get("/template-versions/{version_id}/placeholders", response_model=List[TemplatePlaceholderSchema])
def list_placeholders(
    version_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    _get_version(db, current_user.organization_id, version_id)
    return [
        TemplatePlaceholderSchema.model_validate(placeholder).model_copy(update={"computed_expression_id": expression_id})
        for placeholder, expression_id in _placeholder_expressions(db, version_id).all()
    ]


@router.post("/template-versions/{version_id}/placeholders", response_model=TemplatePlaceholderSchema, status_code=201)
def create_placeholder(
    version_id: uuid.UUID,
    data: TemplatePlaceholderCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:template:update"))
):
    _get_version(db, current_user.organization_id, version_id)
    if data.computed_expression_id is not None:
        expression = db.query(ComputedPlaceholderExpression.id).filter(
            ComputedPlaceholderExpression.id == data.computed_expression_id,
            ComputedPlaceholderExpression.template_version_id == version_id,
        ).first()
        if expression is None:
            raise HTTPException(status_code=404, detail="Computed expression not found")

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
    db.flush()

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
    _get_version(db, current_user.organization_id, version_id)
    placeholder = _placeholder_expressions(db, version_id).filter(
        TemplatePlaceholder.id == data.template_placeholder_id,
        (TemplatePlaceholder.computed_expression_id.is_(None) | ComputedPlaceholderExpression.id.is_not(None)),
    ).first()
    if placeholder is None:
        raise HTTPException(status_code=404, detail="Placeholder not found")

    bind = PlaceholderBinding(
        template_version_id=version_id,
        template_placeholder_id=data.template_placeholder_id,
        binding_path=data.binding_path,
        binding_type=data.binding_type,
        fallback_value=data.fallback_value,
        is_required=data.is_required
    )
    db.add(bind)
    db.flush()

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
    _get_version(db, current_user.organization_id, version_id)

    expr = ComputedPlaceholderExpression(
        template_version_id=version_id,
        placeholder_key=data.placeholder_key,
        expression_type=data.expression_type,
        inputs=data.inputs,
        expression=data.expression,
        output_data_type=data.output_data_type,
        created_by=current_user.id
    )
    db.add(expr)
    db.flush()

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
    _get_project(db, current_user.organization_id, data.project_id)

    ver = _get_version(db, current_user.organization_id, data.template_version_id)

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
    db.flush()

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
    job = (
        db.query(RenderJob)
        .join(RenderJob.project)
        .join(RenderJob.creator)
        .join(RenderJob.template_version)
        .join(TemplateVersion.document_template)
        .filter(
            RenderJob.id == render_job_id,
            Project.organization_id == current_user.organization_id,
            User.organization_id == current_user.organization_id,
            DocumentTemplate.organization_id == current_user.organization_id,
        )
        .first()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return job


@router.get("/generated-documents/{generated_document_id}", response_model=GeneratedDocumentSchema)
def get_generated_document(
    generated_document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:read"))
):
    return _get_generated_document(db, current_user.organization_id, generated_document_id)


# ----------------- DocumentPackage Endpoints -----------------

@router.post("/packages", response_model=DocumentPackageSchema, status_code=201)
def create_package(
    data: DocumentPackageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:package:create"))
):
    _get_project(db, current_user.organization_id, data.project_id)

    pkg = DocumentPackage(
        project_id=data.project_id,
        package_type=data.package_type,
        name=data.name,
        status=data.status,
        created_by=current_user.id
    )
    db.add(pkg)
    db.flush()

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
    return _get_package(db, current_user.organization_id, package_id)


@router.post("/packages/{package_id}/items", response_model=DocumentPackageItemSchema, status_code=201)
def add_package_item(
    package_id: uuid.UUID,
    data: DocumentPackageItemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_engine:package:update"))
):
    pkg = _get_package(db, current_user.organization_id, package_id)

    _get_generated_document(db, current_user.organization_id, data.generated_document_id, project_id=pkg.project_id)

    item = DocumentPackageItem(
        document_package_id=package_id,
        generated_document_id=data.generated_document_id,
        sort_order=data.sort_order
    )
    db.add(item)
    db.flush()

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
