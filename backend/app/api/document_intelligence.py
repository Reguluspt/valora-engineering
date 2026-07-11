import uuid
from typing import List
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.core.rbac import require_permission
from app.core.audit import log_audit_event
from app.modules.project_master_data.models import (
    User, ParsedDocument, ExtractedField, DocumentDiff, DocumentCorrection,
    EvidenceFile, GeneratedDocument, UserActionLog
)
from app.api.intelligence_schemas import (
    ParsedDocumentCreate, ParsedDocumentUpdate, ParsedDocumentSchema,
    ExtractedFieldCreate, ExtractedFieldUpdate, ExtractedFieldSchema,
    DocumentDiffCreate, DocumentDiffSchema,
    DocumentCorrectionCreate, DocumentCorrectionReview, DocumentCorrectionSchema
)

router = APIRouter(prefix="/api/v1/document-intelligence", tags=["Document Intelligence"])

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


# ----------------- ParsedDocument Endpoints -----------------

@router.post("/parsed-documents", response_model=ParsedDocumentSchema, status_code=201)
def create_parsed_document(
    data: ParsedDocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:parse:create"))
):
    ev = db.query(EvidenceFile).filter(EvidenceFile.id == data.evidence_file_id).first()
    if not ev:
        raise HTTPException(status_code=404, detail="Evidence file not found")

    doc = ParsedDocument(
        evidence_file_id=data.evidence_file_id,
        document_type=data.document_type,
        page_count=data.page_count,
        text_content_hash=data.text_content_hash,
        parse_status=data.parse_status,
        confidence_score=data.confidence_score
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    log_audit_event(
        db=db,
        event_name="PARSED_DOCUMENT_CREATE",
        entity_type="parsed_document",
        entity_id=doc.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_parsed_document", "parsed_document", doc.id, {})
    db.commit()
    return doc


@router.get("/parsed-documents", response_model=List[ParsedDocumentSchema])
def list_parsed_documents(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:read"))
):
    return db.query(ParsedDocument).all()


@router.get("/parsed-documents/{parsed_document_id}", response_model=ParsedDocumentSchema)
def get_parsed_document(
    parsed_document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:read"))
):
    doc = db.query(ParsedDocument).filter(ParsedDocument.id == parsed_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Parsed document not found")
    return doc


@router.patch("/parsed-documents/{parsed_document_id}", response_model=ParsedDocumentSchema)
def update_parsed_document(
    parsed_document_id: uuid.UUID,
    data: ParsedDocumentUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:parse:create"))
):
    doc = db.query(ParsedDocument).filter(ParsedDocument.id == parsed_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Parsed document not found")

    if data.expected_row_version is not None:
        if doc.row_version != data.expected_row_version:
            raise HTTPException(status_code=409, detail="Stale row version")

    if data.document_type is not None:
        doc.document_type = data.document_type
    if data.page_count is not None:
        doc.page_count = data.page_count
    if data.text_content_hash is not None:
        doc.text_content_hash = data.text_content_hash
    if data.parse_status is not None:
        doc.parse_status = data.parse_status
    if data.confidence_score is not None:
        doc.confidence_score = data.confidence_score

    db.commit()
    db.refresh(doc)

    log_audit_event(
        db=db,
        event_name="PARSED_DOCUMENT_UPDATE",
        entity_type="parsed_document",
        entity_id=doc.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "update_parsed_document", "parsed_document", doc.id, {})
    db.commit()
    return doc


# ----------------- ExtractedField Endpoints -----------------

@router.post("/parsed-documents/{parsed_document_id}/fields", response_model=ExtractedFieldSchema, status_code=201)
def create_extracted_field(
    parsed_document_id: uuid.UUID,
    data: ExtractedFieldCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:parse:create"))
):
    doc = db.query(ParsedDocument).filter(ParsedDocument.id == parsed_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Parsed document not found")

    field = ExtractedField(
        parsed_document_id=parsed_document_id,
        field_key=data.field_key,
        field_label=data.field_label,
        extracted_value=data.extracted_value,
        normalized_value=data.normalized_value,
        confidence_score=data.confidence_score,
        source_page_number=data.source_page_number,
        status=data.status
    )
    db.add(field)
    db.commit()
    db.refresh(field)

    log_audit_event(
        db=db,
        event_name="EXTRACTED_FIELD_CREATE",
        entity_type="extracted_field",
        entity_id=field.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_extracted_field", "extracted_field", field.id, {"key": field.field_key})
    db.commit()
    return field


@router.get("/parsed-documents/{parsed_document_id}/fields", response_model=List[ExtractedFieldSchema])
def list_extracted_fields(
    parsed_document_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:read"))
):
    doc = db.query(ParsedDocument).filter(ParsedDocument.id == parsed_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Parsed document not found")
    return db.query(ExtractedField).filter(ExtractedField.parsed_document_id == parsed_document_id).all()


@router.patch("/fields/{field_id}", response_model=ExtractedFieldSchema)
def update_extracted_field(
    field_id: uuid.UUID,
    data: ExtractedFieldUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:field:update"))
):
    field = db.query(ExtractedField).filter(ExtractedField.id == field_id).first()
    if not field:
        raise HTTPException(status_code=404, detail="Extracted field not found")

    if data.expected_row_version is not None:
        if field.row_version != data.expected_row_version:
            raise HTTPException(status_code=409, detail="Stale row version")

    if data.field_label is not None:
        field.field_label = data.field_label
    if data.extracted_value is not None:
        field.extracted_value = data.extracted_value
    if data.normalized_value is not None:
        field.normalized_value = data.normalized_value
    if data.confidence_score is not None:
        field.confidence_score = data.confidence_score
    if data.status is not None:
        field.status = data.status

    db.commit()
    db.refresh(field)

    log_audit_event(
        db=db,
        event_name="EXTRACTED_FIELD_UPDATE",
        entity_type="extracted_field",
        entity_id=field.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "update_extracted_field", "extracted_field", field.id, {})
    db.commit()
    return field


# ----------------- DocumentDiff Endpoints -----------------

@router.post("/diffs", response_model=DocumentDiffSchema, status_code=201)
def create_diff(
    data: DocumentDiffCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:diff:create"))
):
    src = db.query(GeneratedDocument).filter(GeneratedDocument.id == data.source_document_id).first()
    if not src:
        raise HTTPException(status_code=404, detail="Source generated document not found")

    tgt = db.query(ParsedDocument).filter(ParsedDocument.id == data.target_document_id).first()
    if not tgt:
        raise HTTPException(status_code=404, detail="Target parsed document not found")

    diff = DocumentDiff(
        source_document_id=data.source_document_id,
        target_document_id=data.target_document_id,
        diff_type=data.diff_type,
        status=data.status,
        diff_payload=data.diff_payload
    )
    db.add(diff)
    db.commit()
    db.refresh(diff)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_DIFF_CREATE",
        entity_type="document_diff",
        entity_id=diff.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_diff", "document_diff", diff.id, {})
    db.commit()
    return diff


@router.get("/diffs/{diff_id}", response_model=DocumentDiffSchema)
def get_diff(
    diff_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:read"))
):
    diff = db.query(DocumentDiff).filter(DocumentDiff.id == diff_id).first()
    if not diff:
        raise HTTPException(status_code=404, detail="Document diff not found")
    return diff


# ----------------- DocumentCorrection Endpoints -----------------

@router.post("/parsed-documents/{parsed_document_id}/corrections", response_model=DocumentCorrectionSchema, status_code=201)
def create_correction(
    parsed_document_id: uuid.UUID,
    data: DocumentCorrectionCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:correction:create"))
):
    doc = db.query(ParsedDocument).filter(ParsedDocument.id == parsed_document_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="Parsed document not found")

    corr = DocumentCorrection(
        parsed_document_id=parsed_document_id,
        target_type=data.target_type,
        target_id=data.target_id,
        affects_approved_data=data.affects_approved_data,
        correction_payload=data.correction_payload,
        decision=data.decision,
        decided_by=data.decided_by,
        status=data.status
    )
    db.add(corr)
    db.commit()
    db.refresh(corr)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_CORRECTION_CREATE",
        entity_type="document_correction",
        entity_id=corr.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "create_correction", "document_correction", corr.id, {})
    db.commit()
    return corr


@router.get("/corrections/{correction_id}", response_model=DocumentCorrectionSchema)
def get_correction(
    correction_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:read"))
):
    corr = db.query(DocumentCorrection).filter(DocumentCorrection.id == correction_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Document correction not found")
    return corr


@router.post("/corrections/{correction_id}/review", response_model=DocumentCorrectionSchema)
def review_correction(
    correction_id: uuid.UUID,
    data: DocumentCorrectionReview,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_permission("document_intelligence:correction:review"))
):
    corr = db.query(DocumentCorrection).filter(DocumentCorrection.id == correction_id).first()
    if not corr:
        raise HTTPException(status_code=404, detail="Document correction not found")

    if corr.row_version != data.expected_row_version:
        raise HTTPException(status_code=409, detail="Stale row version")

    corr.decision = data.decision
    corr.status = data.status

    db.commit()
    db.refresh(corr)

    log_audit_event(
        db=db,
        event_name="DOCUMENT_CORRECTION_REVIEW",
        entity_type="document_correction",
        entity_id=corr.id,
        organization_id=current_user.organization_id,
        actor_user_id=current_user.id
    )
    log_action(db, current_user.id, "review_correction", "document_correction", corr.id, {})
    db.commit()
    return corr
