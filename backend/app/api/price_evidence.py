"""Thin typed PRICE_EVIDENCE commands and scoped invocation/receipt reads."""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Request, Query
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute
from sqlalchemy.orm import Session

from app.core.rbac import get_current_user, derive_effective_permissions
from app.db import get_db
from app.db.session import get_case_state_db
from app.modules.project_master_data.models import User, WorkbenchSession
from app.modules.project_master_data.price_evidence_schemas import (
    RegisterProjectPriceEvidenceRequest, DecideProjectPriceEvidenceRelevanceRequest,
    WithdrawProjectPriceEvidenceRequest, ConfirmProjectPriceEvidenceRequest,
    WithdrawProjectPriceEvidenceConfirmationRequest, PriceEvidenceResponse, PriceEvidencePreparation, PriceEvidenceSourceRead,
    PriceEvidenceWorkspace,
)
from app.modules.project_master_data.application import price_evidence_commands as commands
from app.modules.project_master_data.application.asset_review_authority import resolve_authority, require_mutation_actor, canonical_digest
from app.modules.project_master_data.application.asset_workbench_provider import evaluate_asset_workbench_provider
from app.modules.project_master_data.application.price_evidence_authority import line_binding
from app.modules.project_master_data.application.asset_line_validation_rules import value


class PriceEvidenceRoute(APIRoute):
    contract_name = "PRICE_EVIDENCE"
    def get_route_handler(self):
        handler = super().get_route_handler()

        async def bounded_contract(request: Request):
            # JSON commands are bounded before parsing; no upload or source dereference.
            if request.method == "POST":
                body = bytearray()
                async for chunk in request.stream():
                    body.extend(chunk)
                    if len(body) > 2_000_000:
                        raise HTTPException(400, detail=f"{self.contract_name} command too large")
                request._body = bytes(body)
            try:
                return await handler(request)
            except RequestValidationError:
                raise HTTPException(400, detail=f"Invalid {self.contract_name} command contract") from None

        return bounded_contract


router = APIRouter(route_class=PriceEvidenceRoute)


@router.get("/{project_id}/price-evidence/sources/{revision_id}", response_model=PriceEvidenceSourceRead)
def read_source(project_id: uuid.UUID, revision_id: uuid.UUID, db: Session = Depends(get_case_state_db),
                actor: User = Depends(get_current_user)):
    from app.core.audit import log_audit_event
    require_mutation_actor(db, actor=actor, org_id=actor.organization_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=actor.organization_id, project_id=project_id)
    source = snapshot.price_evidence.sources.get(revision_id)
    if not source:
        raise HTTPException(404, detail="Source revision not found")
    if not snapshot.price_evidence.intact:
        raise HTTPException(409, detail="Source integrity cannot be proved")
    response = PriceEvidenceSourceRead(project_id=project_id, source_id=source.source_id, evidence_revision_id=source.id,
        predecessor_revision_id=source.predecessor_id, revision=source.revision, registrar_id=source.actor_user_id,
        registered_at=source.created_at, material=source.content_binding["material"])
    try:
        log_audit_event(db, event_name="PriceEvidenceSourceAccessed", entity_type="Project", entity_id=project_id,
            organization_id=actor.organization_id, actor_user_id=actor.id,
            payload={"project_id": str(project_id), "evidence_revision_id": str(source.id)})
        db.commit()
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="Source access could not be recorded") from None
    return response


def _mutate(command, db, actor, project_id, payload):
    try:
        result = command(db, actor=actor, org_id=actor.organization_id, project_id=project_id, request=payload)
        db.commit()
        return result
    except HTTPException:
        db.rollback()
        raise
    except Exception:
        db.rollback()
        raise HTTPException(500, detail="PRICE_EVIDENCE command failed; reconcile its receipt before retry") from None


@router.post("/{project_id}/price-evidence/register", response_model=PriceEvidenceResponse)
def register(project_id: uuid.UUID, payload: RegisterProjectPriceEvidenceRequest,
             db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(commands.register_project_price_evidence, db, actor, project_id, payload)


@router.post("/{project_id}/price-evidence/decide", response_model=PriceEvidenceResponse)
def decide(project_id: uuid.UUID, payload: DecideProjectPriceEvidenceRelevanceRequest,
           db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(commands.decide_project_price_evidence_relevance, db, actor, project_id, payload)


@router.post("/{project_id}/price-evidence/withdraw", response_model=PriceEvidenceResponse)
def withdraw(project_id: uuid.UUID, payload: WithdrawProjectPriceEvidenceRequest,
             db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(commands.withdraw_project_price_evidence, db, actor, project_id, payload)


@router.post("/{project_id}/price-evidence/confirm", response_model=PriceEvidenceResponse)
def confirm(project_id: uuid.UUID, payload: ConfirmProjectPriceEvidenceRequest,
            db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(commands.confirm_project_price_evidence, db, actor, project_id, payload)


@router.post("/{project_id}/price-evidence/withdraw-confirmation", response_model=PriceEvidenceResponse)
def withdraw_confirmation(project_id: uuid.UUID, payload: WithdrawProjectPriceEvidenceConfirmationRequest,
                          db: Session = Depends(get_db), actor: User = Depends(get_current_user)):
    return _mutate(commands.withdraw_project_price_evidence_confirmation, db, actor, project_id, payload)


@router.get("/{project_id}/price-evidence/command-receipts/{command_id}", response_model=PriceEvidenceResponse)
def receipt(project_id: uuid.UUID, command_id: uuid.UUID, db: Session = Depends(get_case_state_db),
            actor: User = Depends(get_current_user)):
    return commands.read_price_evidence_receipt(db, actor=actor, org_id=actor.organization_id,
                                              project_id=project_id, command_id=command_id)


@router.get("/{project_id}/price-evidence/preparation", response_model=PriceEvidencePreparation)
def preparation(project_id: uuid.UUID, db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    persisted = require_mutation_actor(db, actor=actor, org_id=actor.organization_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=actor.organization_id, project_id=project_id)
    has_session = db.query(WorkbenchSession.id).filter_by(project_id=project_id, user_id=actor.id, status="active").first() is not None
    permissions = derive_effective_permissions(persisted, db)
    return _preparation(snapshot, permissions, has_session)


def _preparation(snapshot, permissions, has_session):
    project_id = snapshot.project.id
    state = snapshot.price_evidence
    upstream = evaluate_asset_workbench_provider(snapshot, effective_permissions=permissions, has_active_session=has_session)
    coherent = bool(state.intact and snapshot.seal_current and snapshot.lineage_current and snapshot.workbench.latest)
    writable = bool(coherent and "workbench:edit" in permissions and has_session and value(snapshot.project.status) == "draft")
    return dict(project_id=project_id, case_version=snapshot.case_version, project_row_version=snapshot.project.row_version,
        seal_id=snapshot.seal.id if coherent else None,
        authoritative_set_sha256=snapshot.seal.authoritative_set_sha256 if coherent else None,
        membership_version=snapshot.seal.membership_version if coherent else None,
        workbench_confirmation_id=snapshot.workbench.latest.id if coherent else None,
        prior_confirmation_id=state.latest.id if coherent and state.latest else None,
        lines=[dict(line_id=line.id, row_version=line.row_version, proof_sha256=canonical_digest(line_binding(snapshot, line.id)))
               for line in snapshot.lines] if coherent else [],
        sources=[dict(source_id=s.source_id, evidence_revision_id=s.id, withdrawn=state.retired(s))
                 for s in state.source_heads.values()] if coherent else [],
        decisions=[dict(line_id=d.line_id, source_id=d.source_id, evidence_revision_id=d.evidence_revision_id,
                        relationship_id=d.relationship_id, decision_id=d.id, withdrawn=state.retired(d))
                   for d in state.decision_heads.values()] if coherent else [],
        can_register=bool(writable and upstream.result == "COMPLETE"),
        can_decide=bool(writable and upstream.result == "COMPLETE"), can_withdraw=writable,
        can_confirm=bool(writable and upstream.result == "COMPLETE" and not state.content_current and not state.stale
                         and not state.holds and all(state.qualifying.get(line.id) for line in snapshot.lines)))


@router.get("/{project_id}/price-evidence/workspace", response_model=PriceEvidenceWorkspace)
def workspace(project_id: uuid.UUID, line_id: uuid.UUID | None = None,
              offset: int = Query(0, ge=0), limit: int = Query(50, ge=1, le=50),
              db: Session = Depends(get_case_state_db), actor: User = Depends(get_current_user)):
    from app.modules.project_master_data.application.price_evidence_projection import workspace_projection
    persisted = require_mutation_actor(db, actor=actor, org_id=actor.organization_id, permission="project:read")
    snapshot = resolve_authority(db, org_id=actor.organization_id, project_id=project_id)
    if line_id is not None and line_id not in {line.id for line in snapshot.lines}:
        raise HTTPException(404, detail="Asset context not found")
    has_session = db.query(WorkbenchSession.id).filter_by(project_id=project_id, user_id=actor.id, status="active").first() is not None
    prep = _preparation(snapshot, derive_effective_permissions(persisted, db), has_session)
    return workspace_projection(db, snapshot, prep, line_id=line_id, offset=offset, limit=limit)
