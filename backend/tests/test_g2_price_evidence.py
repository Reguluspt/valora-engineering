"""A10 uses real sealed membership, human proofs and PostgreSQL durable facts."""
import copy
import uuid
from datetime import timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import text

from app.db.mixins import utc_now
from app.modules.project_master_data.application import price_evidence_commands as commands
from app.modules.project_master_data.application.price_evidence_authority import line_binding
from app.modules.project_master_data.application.asset_review_authority import canonical_digest
from app.modules.project_master_data.application.price_evidence_provider import evaluate_price_evidence_provider
from app.modules.project_master_data.price_evidence_models import PriceEvidenceReceipt, FACT_MODELS
from app.modules.project_master_data.models import AuditEvent
from tests.test_g2_asset_workbench import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    execute as wb_execute, request_for as wb_request, snapshot, human_commit, commit_saved, accept_all,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db


@pytest.fixture
def evidence_db(workbench_db):
    db, entry = workbench_db
    wb_execute(db, entry, wb_request(db, entry))
    db.commit()
    return db, entry


def material(**changes):
    result = dict(category="internet_survey", origin="Synthetic public catalog publisher",
        reference="https://example.com/catalog", locator="catalog item 7", effective_date="2026-10-01",
        unknown_date_reason=None, captured_at=(utc_now() - timedelta(days=1)).isoformat(),
        capture_method="manual_transcription", retained_text="Synthetic catalog item 7 costs 100 per unit, exclusive of delivery.",
        limitations="Manually retained excerpt; not authenticated web bytes", expires_at=None,
        value=dict(amount="100", range_upper=None, currency="VND", unit_basis="item", quantity_basis="1",
                   tax="unknown", delivery="excluded", condition="new", locator="item 7 price"),
        explanation=None, historical=None)
    result.update(changes)
    return result


def test_shared_explanation_dependencies_are_evaluated_once(monkeypatch):
    from types import SimpleNamespace
    from app.modules.project_master_data.application import price_evidence_authority as authority
    state = authority.PriceEvidenceAuthority()
    sources = []
    amounts = []
    for index in range(18):
        amount = 100 if index < 2 else sum(amounts[-2:])
        data = material()
        data["value"]["amount"] = str(amount)
        if index >= 2:
            data.update(category="unit_price_explanation", capture_method="authored_explanation",
                explanation=dict(method="sum_of_scaled_source_values",
                    inputs=[dict(evidence_revision_id=str(s.id), coefficient="1") for s in sources[-2:]],
                    assumptions="Same currency and unit basis", calculations="Sum of identified input values",
                    units="item", currency="VND", proposed_basis_value=str(amount)))
        source = SimpleNamespace(id=uuid.uuid4(), source_id=uuid.uuid4(), expires_at=None,
                                 content_binding={"material": data})
        sources.append(source)
        amounts.append(amount)
        state.sources[source.id] = source
        state.source_heads[source.source_id] = source
    monkeypatch.setattr(state, "retired", lambda source: False)
    evaluated = []
    original = authority._source_eligible
    def counted(*args):
        evaluated.append(args[3].id)
        return original(*args)
    monkeypatch.setattr(authority, "_source_eligible", counted)
    assert authority.source_eligible(None, None, state, sources[-1], utc_now())
    assert len(evaluated) == len(set(evaluated)) == 18


def request_for(db, entry, kind="registration", **changes):
    snap = snapshot(db, entry)
    state = snap.price_evidence
    result = wb_request(db, entry)
    result.pop("supersedes_confirmation_id")
    result.update(contract_version="price-evidence-" + kind + "-v1", reason_note=None,
                  expected_workbench_confirmation_id=str(snap.workbench.latest.id))
    if kind == "registration":
        result.update(source_id=str(uuid.uuid4()), predecessor_revision_id=None, material=material())
    elif kind == "relevance":
        source = list(state.source_heads.values())[-1]
        line = snap.lines[0]
        result.update(evidence_revision_id=str(source.id), line_id=str(line.id), predecessor_relationship_id=None,
            prior_decision_id=None, expected_line_proof_sha256=canonical_digest(line_binding(snap, line.id)),
            source_portion="catalog item 7 price", relevance_rationale="Same stated specification and unit",
            suitability_rationale="Human assessed comparable dated basis", limitations="Transcription limits retained",
            applicability_date="2026-10-06", temporal_applicability="Applicable to current inspection date",
            source_priority_rationale="First priority survey", higher_priorities_considered=[],
            outcome="accepted", disposition="qualifying_basis", review_due_at=(utc_now() + timedelta(days=10)).isoformat())
    elif kind == "confirmation":
        result.update(supersedes_confirmation_id=str(state.latest.id) if state.latest else None,
                      reason_note="Reconfirm changed evidence set" if state.latest else None)
    elif kind == "confirmation-withdrawal":
        result.update(expected_confirmation_id=str(state.latest.id), reason_note="Human readiness withdrawal")
    else:
        result.update(target_kind="source", target_id=str(list(state.source_heads.values())[-1].id), reason_note="Human withdrawal")
    result.update(changes)
    return result


def execute(db, entry, request, actor=None):
    command = {
        "registration": commands.register_project_price_evidence,
        "relevance": commands.decide_project_price_evidence_relevance,
        "withdrawal": commands.withdraw_project_price_evidence,
        "confirmation": commands.confirm_project_price_evidence,
        "confirmation-withdrawal": commands.withdraw_project_price_evidence_confirmation,
    }[request["contract_version"].removeprefix("price-evidence-").removesuffix("-v1")]
    return command(db, actor=actor or db.merge(entry["user"]), org_id=entry["org"].id,
                   project_id=entry["project"].id, request=request)


def provider(db, entry, **kwargs):
    return evaluate_price_evidence_provider(snapshot(db, entry), effective_permissions=kwargs.get("permissions", {"workbench:edit"}),
                                            has_active_session=kwargs.get("session", True))


def counts(db):
    return (sum(db.query(model).count() for model in FACT_MODELS), db.query(PriceEvidenceReceipt).count(),
            db.query(AuditEvent).filter(AuditEvent.event_name.like("ProjectPriceEvidence%")).count())


def cover_all(db, entry, source_id=None):
    snap = snapshot(db, entry)
    source = snap.price_evidence.sources.get(source_id) if source_id else list(snap.price_evidence.source_heads.values())[-1]
    for line in snap.lines:
        fresh = snapshot(db, entry)
        prior = fresh.price_evidence.decision_heads.get((line.id, source.source_id))
        req = request_for(db, entry, "relevance", line_id=str(line.id), evidence_revision_id=str(source.id),
            expected_line_proof_sha256=canonical_digest(line_binding(fresh, line.id)),
            predecessor_relationship_id=str(prior.relationship_id) if prior else None,
            prior_decision_id=str(prior.id) if prior else None, reason_note="Human reassessment" if prior else None)
        if source.expires_at:
            req["review_due_at"] = source.expires_at.astimezone(timezone.utc).isoformat()
        execute(db, entry, req)
        db.commit()


@pytest.fixture
def covered_db(evidence_db):
    db, entry = evidence_db
    execute(db, entry, request_for(db, entry))
    db.commit()
    cover_all(db, entry)
    return db, entry


def test_exact_coverage_confirmation_receipt_and_downstream(covered_db):
    db, entry = covered_db
    assert provider(db, entry).result == "INCOMPLETE"
    assert counts(db) == (4, 4, 4)
    before = [(line.id, line.appraised_unit_price) for line in snapshot(db, entry).lines]
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert provider(db, entry).next_action["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    assert before == [(line.id, line.appraised_unit_price) for line in snapshot(db, entry).lines]
    assert execute(db, entry, req)["result"] == original["result"]
    db.commit()
    assert counts(db) == (5, 5, 5)
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "confirmation"))
    assert error.value.status_code == 409
    db.rollback()


def test_registration_is_not_coverage_and_shared_source_needs_each_acceptance(evidence_db):
    db, entry = evidence_db
    assert provider(db, entry).next_action["semantic_route_key"] == "price_evidence_prepare_required"
    execute(db, entry, request_for(db, entry))
    db.commit()
    execute(db, entry, request_for(db, entry, "relevance"))
    db.commit()
    state = snapshot(db, entry).price_evidence
    assert len(state.qualifying) == 1 and len(snapshot(db, entry).lines) == 3
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "confirmation"))
    db.rollback()
    assert counts(db) == (2, 2, 2)


def test_whole_set_withdrawal_reconfirm_and_historical_replay(covered_db):
    db, entry = covered_db
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation-withdrawal"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    replay = execute(db, entry, req)
    assert replay["historical"] and replay["result"] == original["result"]
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE" and counts(db) == (7, 7, 7)


def test_shared_source_supersession_stales_each_line_then_human_reassessment(covered_db):
    db, entry = covered_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    prior = list(snapshot(db, entry).price_evidence.source_heads.values())[0]
    execute(db, entry, request_for(db, entry, source_id=str(prior.source_id), predecessor_revision_id=str(prior.id),
                                 reason_note="Correct retained source", material=material(retained_text="Corrected synthetic catalog excerpt with same price 100 per item.")))
    db.commit()
    assert provider(db, entry).result == "STALE" and not snapshot(db, entry).price_evidence.qualifying
    cover_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"


@pytest.mark.parametrize("field,new_value", [("description", "Changed description"), ("appraised_unit_price", "52.50")])
def test_official_content_writer_invalidates_and_recovery_requires_fresh_acceptance(covered_db, field, new_value):
    db, entry = covered_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    version = human_commit(db, entry, field, new_value)
    assert provider(db, entry).result == "COMPLETE"
    commit_saved(db, entry, field, version)
    db.commit()
    assert provider(db, entry).result == "STALE"
    accept_all(db, entry)
    wb_execute(db, entry, wb_request(db, entry))
    db.commit()
    cover_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"


@pytest.mark.parametrize("url", ["http://example.com", "https://u:p@example.com", "https://localhost/", "https://127.0.0.1/",
    "https://[::1]/", "https://169.254.169.254/", "https://10.0.0.1/", "https://a.local/", "file:///x",
    "https://example.com/?token=secret", "https://example.com/#secret", "https://2130706433/", "https://127.1/",
    "https://example.com:8080", "https://example.com\\@127.0.0.1", "https://example.com/%0a?q=x"])
def test_unsafe_source_reference_rejected(url):
    from app.modules.project_master_data.price_evidence_schemas import SourceMaterial
    with pytest.raises(ValueError):
        SourceMaterial.model_validate(material(reference=url))


@pytest.mark.parametrize("mutation", ["extra", "bool", "float", "html", "bare", "coerce", "currency"])
def test_strict_payload_and_source_security(evidence_db, mutation):
    db, entry = evidence_db
    req = request_for(db, entry)
    if mutation == "extra":
        req["organization_id"] = str(entry["org"].id)
    elif mutation == "bool":
        req["confirm"] = 1
    elif mutation == "float":
        req["material"]["value"]["amount"] = 1.25
    elif mutation == "html":
        req["material"]["retained_text"] = "<script>executable source</script>"
    elif mutation == "bare":
        req["material"]["retained_text"] = "100"
    elif mutation == "coerce":
        req["expected_project_row_version"] = str(req["expected_project_row_version"])
    else:
        req["material"]["value"].pop("currency")
    with pytest.raises(HTTPException) as error:
        execute(db, entry, req)
    assert error.value.status_code == 400 and counts(db) == (0, 0, 0)


def test_negative_hold_not_hidden_by_withdrawal_or_extra_positive(covered_db):
    db, entry = covered_db
    state = snapshot(db, entry).price_evidence
    prior = list(state.decision_heads.values())[0]
    execute(db, entry, request_for(db, entry, "relevance", line_id=str(prior.line_id),
        expected_line_proof_sha256=canonical_digest(line_binding(snapshot(db, entry), prior.line_id)),
        predecessor_relationship_id=str(prior.relationship_id), prior_decision_id=str(prior.id),
        outcome="rejected", disposition="unresolved_concern", reason_note="Material contradiction"))
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    execute(db, entry, request_for(db, entry, "withdrawal"))
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    prior = snapshot(db, entry).price_evidence.decision_heads[(prior.line_id, prior.source_id)]
    execute(db, entry, request_for(db, entry, "relevance", line_id=str(prior.line_id),
        expected_line_proof_sha256=canonical_digest(line_binding(snapshot(db, entry), prior.line_id)),
        predecessor_relationship_id=str(prior.relationship_id), prior_decision_id=str(prior.id),
        outcome="rejected", disposition="excluded_alternative", reason_note="Human resolved concern; exclude withdrawn alternative"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"


@pytest.mark.parametrize("command_kind", ["registration", "decision"])
def test_explanation_input_expiry_binds_each_admission_commit(evidence_db, monkeypatch, command_kind):
    from app.modules.project_master_data.application import price_evidence_authority as authority
    db, entry = evidence_db
    deadline = utc_now() + timedelta(days=1)
    source = execute(db, entry, request_for(db, entry, material=material(expires_at=deadline.isoformat())))
    db.commit()
    derived = material(category="unit_price_explanation", capture_method="authored_explanation",
        explanation=dict(method="sum_of_scaled_source_values",
            inputs=[dict(evidence_revision_id=source["result"]["record_id"], coefficient="1")],
            assumptions="Same specification and unit basis", calculations="One unit of retained source value",
            units="item", currency="VND", proposed_basis_value="100"))
    execute(db, entry, request_for(db, entry, material=derived))
    if command_kind == "decision":
        db.commit()
        execute(db, entry, request_for(db, entry, "relevance", higher_priorities_considered=["internet_survey"],
            source_priority_rationale="Explanation retains identified survey input"))
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    with pytest.raises(HTTPException) as error:
        db.commit()
    assert error.value.status_code == 409
    db.rollback()
    expected = 1 if command_kind == "registration" else 2
    assert counts(db) == (expected, expected, expected)
    assert provider(db, entry).result == "INCOMPLETE"


def test_explanation_input_expiry_binds_confirmation_commit(evidence_db, monkeypatch):
    from app.modules.project_master_data.application import price_evidence_authority as authority
    db, entry = evidence_db
    deadline = utc_now() + timedelta(days=1)
    source = execute(db, entry, request_for(db, entry, material=material(expires_at=deadline.isoformat())))
    db.commit()
    derived = material(category="unit_price_explanation", capture_method="authored_explanation",
        explanation=dict(method="sum_of_scaled_source_values",
            inputs=[dict(evidence_revision_id=source["result"]["record_id"], coefficient="1")],
            assumptions="Same specification and unit basis", calculations="One unit of retained source value",
            units="item", currency="VND", proposed_basis_value="100"))
    execute(db, entry, request_for(db, entry, material=derived))
    db.commit()
    for line in snapshot(db, entry).lines:
        execute(db, entry, request_for(db, entry, "relevance", line_id=str(line.id),
            expected_line_proof_sha256=canonical_digest(line_binding(snapshot(db, entry), line.id)),
            higher_priorities_considered=["internet_survey"],
            source_priority_rationale="Reasoned explanation retains identified survey input"))
        db.commit()
    assert snapshot(db, entry).price_evidence.earliest_deadline == deadline
    execute(db, entry, request_for(db, entry, "confirmation"))
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    with pytest.raises(HTTPException) as error:
        db.commit()
    assert error.value.status_code == 409
    db.rollback()
    assert counts(db) == (5, 5, 5)
    assert provider(db, entry).result == "STALE"


def test_unused_source_expiry_does_not_invalidate_accepted_set(covered_db, monkeypatch):
    from app.modules.project_master_data.application import price_evidence_authority as authority
    db, entry = covered_db
    deadline = utc_now() + timedelta(days=1)
    execute(db, entry, request_for(db, entry, material=material(expires_at=deadline.isoformat())))
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    before = snapshot(db, entry)
    assert before.price_evidence.earliest_deadline > deadline
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    assert provider(db, entry).result == "COMPLETE"
    assert snapshot(db, entry).case_version == before.case_version
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "relevance"))
    assert error.value.status_code == 400
    db.rollback()


def test_expired_source_hold_can_be_explicitly_resolved(evidence_db, monkeypatch):
    from app.modules.project_master_data.application import price_evidence_authority as authority
    db, entry = evidence_db
    deadline = utc_now() + timedelta(days=1)
    execute(db, entry, request_for(db, entry, material=material(expires_at=deadline.isoformat())))
    db.commit()
    execute(db, entry, request_for(db, entry, "relevance", outcome="rejected",
        disposition="unresolved_concern", reason_note="Material concern remains open"))
    db.commit()
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    assert provider(db, entry).result == "BLOCKED"
    prior = next(iter(snapshot(db, entry).price_evidence.decision_heads.values()))
    execute(db, entry, request_for(db, entry, "relevance", predecessor_relationship_id=str(prior.relationship_id),
        prior_decision_id=str(prior.id), outcome="rejected", disposition="excluded_alternative",
        reason_note="Human resolves concern and excludes expired source"))
    db.commit()
    assert not snapshot(db, entry).price_evidence.holds
    execute(db, entry, request_for(db, entry, "withdrawal"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"


def test_deadline_changes_token_without_clock_churn_and_commit_crossing(covered_db, monkeypatch):
    db, entry = covered_db
    first = snapshot(db, entry)
    assert first.case_version == snapshot(db, entry).case_version
    deadline = first.price_evidence.earliest_deadline
    req = request_for(db, entry, "confirmation")
    execute(db, entry, req)
    monkeypatch.setattr(commands, "utc_now", lambda: deadline)
    with pytest.raises(HTTPException) as error:
        db.commit()
    assert error.value.status_code == 409
    db.rollback()
    assert counts(db) == (4, 4, 4)
    from app.modules.project_master_data.application import price_evidence_authority as authority
    monkeypatch.setattr(authority, "utc_now", lambda: deadline)
    assert snapshot(db, entry).case_version != first.case_version
    assert provider(db, entry).result == "STALE"


def test_audit_failure_rolls_back_and_payload_is_minimized(evidence_db, monkeypatch):
    db, entry = evidence_db
    req = request_for(db, entry)
    original = commands.log_audit_event
    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")
    monkeypatch.setattr(commands, "log_audit_event", fail)
    with pytest.raises(RuntimeError):
        execute(db, entry, req)
    db.rollback()
    assert counts(db) == (0, 0, 0)
    monkeypatch.setattr(commands, "log_audit_event", original)
    execute(db, entry, req)
    db.commit()
    audit = db.query(AuditEvent).filter_by(event_name="ProjectPriceEvidenceRegistered").one()
    payload = str(audit.payload)
    assert "https" not in payload and "Synthetic" not in payload and "retained_text" not in payload
    assert "[REDACTED]" not in payload


def test_corrupted_source_or_missing_audit_is_stale(covered_db):
    db, entry = covered_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    schema = db.get_bind().get_execution_options()["schema_translate_map"][None]
    db.execute(text(f'UPDATE "{schema}".project_price_evidence_sources SET content_sha256 = :digest'), {"digest": "0" * 64})
    db.commit()
    assert provider(db, entry).result == "STALE"
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "confirmation"))
    db.rollback()


def test_uuid_payload_mismatch_and_cross_scope_fail_closed(evidence_db):
    db, entry = evidence_db
    req = request_for(db, entry)
    execute(db, entry, req)
    db.commit()
    changed = copy.deepcopy(req)
    changed["material"]["origin"] = "Different publisher"
    with pytest.raises(HTTPException) as error:
        execute(db, entry, changed)
    assert error.value.status_code == 409
    db.rollback()
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "relevance", evidence_revision_id=str(uuid.uuid4())))
    assert error.value.status_code == 404
    db.rollback()


@pytest.mark.parametrize("category", ["supplier_quote", "ai_output", "personal_estimate", "generic_evidence_file"])
def test_ineligible_primary_source_categories(category):
    from app.modules.project_master_data.price_evidence_schemas import SourceMaterial
    with pytest.raises(ValueError):
        SourceMaterial.model_validate(material(category=category))


def test_legacy_source_file_link_and_quote_records_never_promote(evidence_db):
    from app.modules.project_master_data.models import EvidenceSource, EvidenceFile, EvidenceLink, QuoteBatch, QuoteLine, AppraisedPriceDecision
    db, entry = evidence_db
    before = snapshot(db, entry).case_version
    source = EvidenceSource(name="Legacy supplier source", source_type="supplier")
    file = EvidenceFile(filename="synthetic.txt", mime_type="text/plain", file_size=5,
        object_key="synthetic-legacy-only", checksum="synthetic-checksum", uploaded_by=entry["user"].id)
    db.add_all([source, file])
    db.flush()
    db.add(EvidenceLink(evidence_file_id=file.id, target_type="Project", target_id=entry["project"].id, created_by=entry["user"].id))
    batch = QuoteBatch(organization_id=entry["org"].id, created_by=entry["user"].id, status="active")
    db.add(batch)
    db.flush()
    db.add(QuoteLine(organization_id=entry["org"].id, quote_batch_id=batch.id, evidence_file_id=file.id,
                     supplier_name="Synthetic supplier", quoted_unit_price=100, currency="VND", status="active"))
    db.add(AppraisedPriceDecision(quote_batch_id=batch.id, final_unit_price=100, currency="VND",
        rationale="Synthetic legacy catalog decision", status="active", created_by=entry["user"].id))
    db.commit()
    assert snapshot(db, entry).case_version == before
    assert provider(db, entry).result == "INCOMPLETE" and not snapshot(db, entry).price_evidence.qualifying
    assert db.query(QuoteBatch).count() == db.query(QuoteLine).count() == db.query(AppraisedPriceDecision).count() == 1
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert db.query(QuoteBatch).count() == db.query(QuoteLine).count() == db.query(AppraisedPriceDecision).count() == 1


def test_historical_excerpt_requires_exact_owned_prior_asset(evidence_db):
    from app.modules.project_master_data.models import Project, ProjectAssetLine
    db, entry = evidence_db
    prior = Project(organization_id=entry["org"].id, code=uuid.uuid4().hex, name="Synthetic prior appraisal", created_by=entry["user"].id)
    db.add(prior)
    db.flush()
    line = ProjectAssetLine(project_id=prior.id, asset_name="Exact historic item")
    db.add(line)
    db.commit()
    values = material()["value"]
    historic = material(category="prior_appraisal_result", reference=None, historical=dict(project_id=str(prior.id),
        line_id=str(line.id), appraisal_date="2026-10-01", result_excerpt="Synthetic retained appraisal result states 100 VND per item.",
        result_locator="Appraisal result table, item 1", result_value=values))
    execute(db, entry, request_for(db, entry, material=historic))
    db.commit()
    execute(db, entry, request_for(db, entry, "relevance", higher_priorities_considered=["internet_survey", "unit_price_explanation"],
                                  source_priority_rationale="Human records higher priority evidence unavailable for this asset"))
    db.commit()
    assert len(snapshot(db, entry).price_evidence.qualifying) == 1
    historic["historical"]["line_id"] = str(entry["line_id"])
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, material=historic))
    assert error.value.status_code == 404
    db.rollback()
