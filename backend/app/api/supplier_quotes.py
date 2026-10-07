"""Scoped preparation, quotation history and explicit human commands."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, derive_effective_permissions
from app.db import get_db
from app.db.session import get_case_state_db
from app.modules.project_master_data.models import User, WorkbenchSession, Supplier
from app.modules.document_workspace.models import StorageObjectBinding, DocumentRecord, DocumentRevision
from app.modules.project_master_data.supplier_quote_schemas import (
    RegisterSupplierQuoteRequest, RegisterSupplierQuoteLineRequest, ReviseSupplierQuoteRequest,
    ConfirmSupplierQuoteRequest, WithdrawSupplierQuoteRequest, RejectSupplierQuoteRequest,
)
from app.modules.project_master_data.application.asset_review_authority import require_mutation_actor, resolve_authority
from app.modules.project_master_data.application.asset_line_validation_rules import value
from app.modules.project_master_data.application.supplier_quote_authority import item_json
from app.modules.project_master_data.application.supplier_quote_source import retained_source
from app.modules.project_master_data.application.supplier_quote_provider import evaluate_supplier_quote_provider
from app.modules.project_master_data.application import supplier_quote_commands as commands
from app.api.price_evidence import PriceEvidenceRoute

class SupplierQuoteRoute(PriceEvidenceRoute):
    contract_name = "SUPPLIER_QUOTES"


router = APIRouter(route_class=SupplierQuoteRoute)


def read_context(db, actor, project_id, request):
    db.info["supplier_quote_blob_store"] = request.app.state.document_blob_store
    persisted = require_mutation_actor(db, actor=actor, org_id=actor.organization_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=actor.organization_id, project_id=project_id)
    permissions = derive_effective_permissions(persisted, db)
    session = db.query(WorkbenchSession).filter_by(project_id=project_id, user_id=persisted.id, status="active").first()
    return snapshot, permissions, session


@router.get("/{project_id}/supplier-quotes/preparation")
def preparation(project_id: uuid.UUID, request: Request, db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    snapshot, permissions, session = read_context(db, actor, project_id, request)
    state = snapshot.supplier_quotes
    provider = evaluate_supplier_quote_provider(snapshot, effective_permissions=permissions, has_active_session=session is not None)
    writable = bool(state.intact and snapshot.seal_current and snapshot.lineage_current and session
        and "workbench:edit" in permissions and value(snapshot.project.status) == "draft")
    upstream_writable = bool(writable and provider.result != "NOT_AVAILABLE")
    return dict(project_id=str(project_id), case_version=snapshot.case_version, project_row_version=snapshot.project.row_version,
        seal_id=str(snapshot.seal.id) if snapshot.seal else None, authoritative_set_sha256=snapshot.seal.authoritative_set_sha256 if snapshot.seal else None,
        membership_version=snapshot.seal.membership_version if snapshot.seal else None,
        price_evidence_confirmation_id=str(snapshot.price_evidence.latest.id) if snapshot.price_evidence.latest else None,
        session_id=str(session.id) if session else None, line_versions=[dict(line_id=str(line.id), row_version=line.row_version) for line in snapshot.lines],
        lines=[dict(line_id=str(line.id), asset_name=line.asset_name, description=line.description,
            quantity=str(line.quantity), unit=line.unit.code if line.unit else None) for line in snapshot.lines],
        writable=upstream_writable, can_register=upstream_writable,
        coverage=[dict(line_id=str(line.id), supplier_count=len(state.coverage.get(line.id, set())), deficient=not bool(state.coverage.get(line.id))) for line in snapshot.lines],
        concerns=[dict(concern_id=str(c), quote_id=str(f.quote_id), revision_id=str(f.revision_id), reason_code=f.invocation_binding["concern_code"]) for c, f in state.concerns.items()],
        quotes=[dict(quote_id=str(head.quote_id), revision_id=str(head.id), head_version=state.versions[head.quote_id],
            confirmed_revision_id=str(state.confirmed_heads[head.quote_id].id) if head.quote_id in state.confirmed_heads else None,
            source_generation=head.content_binding["source"]["generation"], supplier_id=str(head.supplier_id),
            supplier_row_version=state.suppliers[head.supplier_id].row_version if head.supplier_id in state.suppliers else None,
            status=state.status[head.id], eligible=state.eligible[head.id], deficiencies=state.reasons[head.id],
            can_confirm=bool(upstream_writable and state.status[head.id] == "draft" and not state.reasons[head.id] and state.items[head.id]
                and not any(f.quote_id == head.quote_id and str(c) not in head.content_binding.get("resolves_concern_ids", []) for c, f in state.concerns.items())),
            can_register_line=bool(upstream_writable and state.status[head.id] == "draft" and not (set(state.reasons[head.id]) - {"not_effective"})),
            can_revise=upstream_writable, can_withdraw=bool(writable and head.quote_id in state.confirmed_heads),
            can_reject=bool(writable and state.status[head.id] == "draft")) for head in state.heads.values()],
        result=provider.result, next_action=provider.next_action)


@router.get("/{project_id}/supplier-quotes/sources")
def sources(project_id: uuid.UUID, request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=50),
            db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    read_context(db, actor, project_id, request)
    bindings = db.query(StorageObjectBinding).filter_by(organization_id=actor.organization_id, project_id=project_id).order_by(StorageObjectBinding.id).offset(offset).limit(limit).all()
    results = []
    for binding in bindings:
        proof, available = retained_source(db, org_id=actor.organization_id, project_id=project_id,
            document_id=binding.document_id, revision_id=binding.document_revision_id)
        if proof:
            document = db.query(DocumentRecord).filter_by(organization_id=actor.organization_id,
                project_id=project_id, id=binding.document_id).one()
            revision = db.query(DocumentRevision).filter_by(organization_id=actor.organization_id,
                project_id=project_id, id=binding.document_revision_id).one()
            results.append(dict(quote_id=str(binding.document_id), source_revision_id=str(binding.document_revision_id),
                title=document.title, document_type=document.document_type, revision_number=revision.document_revision,
                generation=proof["generation"], sha256=proof["sha256"], byte_length=proof["byte_length"], available=available))
    return dict(items=results, offset=offset, limit=limit, next_offset=offset + limit if len(bindings) == limit else None)


@router.get("/{project_id}/supplier-quotes/suppliers")
def suppliers(project_id: uuid.UUID, request: Request, offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=50),
              db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    read_context(db, actor, project_id, request)
    rows = db.query(Supplier).filter_by(organization_id=actor.organization_id, status="active", merged_into_supplier_id=None).order_by(Supplier.id).offset(offset).limit(limit).all()
    return dict(items=[dict(supplier_id=str(s.id), row_version=s.row_version,
        display_name=s.display_name, legal_name=s.legal_name) for s in rows], offset=offset, limit=limit,
        next_offset=offset + limit if len(rows) == limit else None)


@router.get("/{project_id}/supplier-quotes")
def quotations(project_id: uuid.UUID, request: Request, quote_id: uuid.UUID | None = None, revision_id: uuid.UUID | None = None,
               offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=50), db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    snapshot, _, _ = read_context(db, actor, project_id, request)
    state = snapshot.supplier_quotes
    if not state.intact:
        raise HTTPException(409, detail="Quotation integrity conflict")
    if (quote_id and quote_id not in state.heads) or (revision_id and (revision_id not in state.revisions or (quote_id and state.revisions[revision_id].quote_id != quote_id))):
        raise HTTPException(404, detail="Quotation not found")
    revisions = [r for r in state.revisions.values() if (not quote_id or r.quote_id == quote_id) and (not revision_id or r.id == revision_id)]
    result = []
    for revision in revisions[offset:offset + limit]:
        source = revision.content_binding["source"]
        document = db.query(DocumentRecord).filter_by(organization_id=actor.organization_id,
            project_id=project_id, id=revision.quote_id).first()
        supplier = revision.content_binding["supplier"]
        result.append(dict(quote_id=str(revision.quote_id), revision_id=str(revision.id), revision_number=revision.revision_number,
            title=document.title if document else None,
            supplier=dict(display_name=supplier["display_name"], legal_name=supplier["legal_name"]),
            supplier_row_version=state.suppliers[revision.supplier_id].row_version if revision.supplier_id in state.suppliers else None,
            coverage_line_ids=[str(i.line_id) for i in state.items[revision.id].values()] if state.eligible.get(revision.id) else [],
            predecessor_id=str(revision.predecessor_id) if revision.predecessor_id else None, supplier_id=str(revision.supplier_id),
            registrar_id=str(revision.actor_user_id), confirmer_id=next((str(r.actor_user_id) for r in state.records.values() if r.revision_id == revision.id and r.kind == "confirmation"), None),
            registered_at=revision.created_at, confirmed_at=next((r.created_at for r in state.records.values() if r.revision_id == revision.id and r.kind == "confirmation"), None),
            status=state.status[revision.id], current_head=state.confirmed_heads.get(revision.quote_id) is revision,
            latest_revision=state.heads[revision.quote_id].id == revision.id, eligible=state.eligible.get(revision.id, False),
            deficiencies=state.reasons.get(revision.id, ["superseded"]), terms=revision.content_binding["terms"],
            source=dict(revision_id=source["revision_id"], generation=source["generation"], sha256=source["sha256"], byte_length=source["byte_length"]),
            items=[dict(**item_json(i), item_id=str(i.id), warning_codes=state.warnings.get(i.id, [])) for i in state.items[revision.id].values()]))
    return dict(items=result, offset=offset, limit=limit, case_version=snapshot.case_version,
        next_offset=offset + limit if len(revisions) > offset + limit else None)


@router.get("/{project_id}/supplier-quotes/command-receipts/{command_id}")
def receipt(project_id: uuid.UUID, command_id: uuid.UUID, request: Request, db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    db.info["supplier_quote_blob_store"] = request.app.state.document_blob_store
    return commands.read_receipt(db, actor=actor, org_id=actor.organization_id, project_id=project_id, command_id=command_id)


def mutate(command, db, actor, project_id, payload, request):
    db.info["supplier_quote_blob_store"] = request.app.state.document_blob_store
    try:
        result = command(db, actor=actor, org_id=actor.organization_id, project_id=project_id, request=payload)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Quotation command failed; reconcile its receipt before retry") from None


@router.post("/{project_id}/supplier-quotes/register")
def register(project_id: uuid.UUID, payload: RegisterSupplierQuoteRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.register_supplier_quote, db, actor, project_id, payload, request)


@router.post("/{project_id}/supplier-quotes/register-line")
def register_line(project_id: uuid.UUID, payload: RegisterSupplierQuoteLineRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.register_supplier_quote_line, db, actor, project_id, payload, request)


@router.post("/{project_id}/supplier-quotes/revise")
def revise(project_id: uuid.UUID, payload: ReviseSupplierQuoteRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.revise_supplier_quote, db, actor, project_id, payload, request)


@router.post("/{project_id}/supplier-quotes/confirm")
def confirm(project_id: uuid.UUID, payload: ConfirmSupplierQuoteRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.confirm_supplier_quote, db, actor, project_id, payload, request)


@router.post("/{project_id}/supplier-quotes/withdraw")
def withdraw(project_id: uuid.UUID, payload: WithdrawSupplierQuoteRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.withdraw_supplier_quote, db, actor, project_id, payload, request)


@router.post("/{project_id}/supplier-quotes/reject")
def reject(project_id: uuid.UUID, payload: RejectSupplierQuoteRequest, request: Request, db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return mutate(commands.reject_supplier_quote, db, actor, project_id, payload, request)
