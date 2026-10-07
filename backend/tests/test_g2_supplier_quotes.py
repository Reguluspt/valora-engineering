"""A13 uses real PostgreSQL and existing retained source infrastructure."""
import hashlib
import sys
import uuid
from datetime import timedelta
from decimal import Decimal

import pytest
from fastapi import HTTPException

from app.db.mixins import utc_now
from app.modules.project_master_data.models import Supplier, Currency, AuditEvent, NccSelectionRevision, AppraisedPriceDecision
from app.modules.project_master_data.supplier_quote_models import SupplierQuoteFact, SupplierQuoteItem, SupplierQuoteReceipt
from app.modules.project_master_data.application import supplier_quote_commands as commands
from app.modules.project_master_data.application.supplier_quote_provider import evaluate_supplier_quote_provider
from app.modules.project_master_data.application import supplier_quote_source
from app.modules.document_workspace.domain.document_blob_store import InMemoryDocumentBlobStore
from app.modules.document_workspace.application import document_storage_service as storage
from tests.test_document_storage_service import _invoke
from tests.test_g2_price_evidence import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db, snapshot, request_for as pe_request,
    execute as pe_execute,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db = _evidence_db, _covered_db


def retain(db, entry, store, label="supplier-issued test quotation"):
    content = label.encode()
    checksum = hashlib.sha256(content).hexdigest()
    key = uuid.uuid4().hex
    intent = storage.prepare_initial_storage_intent(db, actor=entry["user"], organization_id=entry["org"].id,
        project_id=entry["project"].id, document_type="supplier_quote", title="Synthetic source", expected_content_sha256=checksum,
        data_snapshot_digest_sha256="1" * 64, idempotency_key=key, request_digest_sha256="2" * 64,
        plan_digest_sha256="3" * 64, decision_digest_sha256="4" * 64)
    storage.record_storage_candidate(db, organization_id=entry["org"].id, intent_id=intent.id, content=content,
        provider_kind=store.provider_kind, storage_profile_id=f"exchange-{store.provider_kind}", container_name="valora-document-blobs", object_key=key,
        media_type="application/octet-stream", generator_version="existing-retained-fixture")
    _invoke(storage.create_or_recover_storage_object(db, organization_id=entry["org"].id, intent_id=intent.id, content=content, blob_store=store))
    now = utc_now()
    return storage.finalize_storage_revision(db, organization_id=entry["org"].id, intent_id=intent.id,
        retention_policy_code="official-document-10y", retention_anchor_at=now, minimum_retain_until=now.replace(year=now.year + 10))


@pytest.fixture
def quote_db(covered_db, monkeypatch):
    db, entry = covered_db
    pe_execute(db, entry, pe_request(db, entry, "confirmation"))
    db.commit()
    store = InMemoryDocumentBlobStore()
    monkeypatch.setattr(supplier_quote_source, "runtime_store", lambda: store)
    db.info["supplier_quote_blob_store"] = store
    entry["role"].permissions = sorted(set(entry["role"].permissions + ["project:update"]))
    if not db.query(Currency).filter_by(code="VND").first():
        db.add(Currency(code="VND", display_name="Vietnamese dong", status="active", decimal_places=0))
    db.commit()
    binding = retain(db, entry, store)
    supplier = Supplier(organization_id=entry["org"].id, legal_name="Synthetic supplier", tax_code=uuid.uuid4().hex,
        status="active", created_by=entry["user"].id)
    db.add(supplier)
    db.commit()
    entry.update(quote_binding=binding, quote_supplier=supplier, quote_store=store)
    return db, entry


def terms():
    now = utc_now()
    return dict(quotation_number="Q-1", quote_date=now.date().isoformat(), effective_at=(now - timedelta(days=1)).isoformat(),
        expires_at=(now + timedelta(days=15)).isoformat(), review_due_at=(now + timedelta(days=10)).isoformat(), currency="VND",
        tax="exclusive", delivery="excluded", condition="new", warranty="No warranty offered", payment="Cash",
        limitations="Already retained source; human supplier-origin attestation", source_locator="page 1")


def item_for(line, price="123456789012345678.12345678"):
    return dict(line_id=str(line.id), quantity=str(line.quantity), unit=line.unit.code, unit_price=price, source_locator="page 1 row " + str(line.id))


def request_for(db, entry, kind="registration", **changes):
    snap = snapshot(db, entry)
    binding, supplier = entry["quote_binding"], entry["quote_supplier"]
    prior = snap.supplier_quotes.heads.get(binding.document_id)
    result = dict(command_id=str(uuid.uuid4()), confirm=True, reason_note=None,
        contract_version="supplier-quote-" + kind + "-v1", expected_project_row_version=snap.project.row_version,
        expected_case_version=snap.case_version, expected_seal_id=str(snap.seal.id), expected_authoritative_set_sha256=snap.seal.authoritative_set_sha256,
        expected_membership_version=snap.seal.membership_version,
        expected_line_versions=[dict(line_id=str(line.id), row_version=line.row_version) for line in snap.lines],
        expected_session_id=str(entry["session"].id), expected_price_evidence_confirmation_id=str(snap.price_evidence.latest.id),
        supplier_id=str(supplier.id), expected_supplier_row_version=supplier.row_version, quote_id=str(binding.document_id),
        expected_source_generation=1,
        expected_revision_id=str(prior.id) if prior else None, expected_quote_head_version=snap.supplier_quotes.versions.get(binding.document_id, 0))
    if kind in ("registration", "revision"):
        result.update(source_revision_id=str(binding.document_revision_id), expected_source_generation=1, terms=terms())
    if kind == "revision":
        result["items"] = [item_for(line) for line in snap.lines]
        result.update(revision_reason="correction", reason_note="Correct prior offer")
    if kind in ("withdrawal", "rejection"):
        result["reason_note"] = "Human reasoned disposition"
    if kind == "withdrawal":
        target = snap.supplier_quotes.confirmed_heads.get(binding.document_id) or prior
        result["target_revision_id"] = str(target.id) if target else str(uuid.uuid4())
    if kind == "line-registration":
        result["item"] = item_for(snap.lines[0])
    result.update(changes)
    return result


def execute(db, entry, request):
    return commands.execute(db, actor=db.merge(entry["user"]), org_id=entry["org"].id, project_id=entry["project"].id, request=request)


def provider(db, entry, **kwargs):
    return evaluate_supplier_quote_provider(snapshot(db, entry), effective_permissions=kwargs.get("permissions", {"workbench:edit"}), has_active_session=kwargs.get("session", True))


def counts(db):
    return (db.query(SupplierQuoteFact).count(), db.query(SupplierQuoteReceipt).count(), db.query(AuditEvent).filter(AuditEvent.event_name.like("SupplierQuote%" )).count())


def draft_all(db, entry):
    execute(db, entry, request_for(db, entry))
    db.commit()
    for line in snapshot(db, entry).lines:
        execute(db, entry, request_for(db, entry, "line-registration", item=item_for(line)))
        db.commit()


@pytest.fixture
def drafted_db(quote_db):
    db, entry = quote_db
    draft_all(db, entry)
    return db, entry


def test_one_click_one_supplier_exact_complete_no_downstream_writes(drafted_db):
    db, entry = drafted_db
    initial = [(line.id, line.appraised_unit_price) for line in snapshot(db, entry).lines]
    assert provider(db, entry).result == "INCOMPLETE"
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert all(len(v) == 1 for v in snapshot(db, entry).supplier_quotes.coverage.values())
    assert provider(db, entry).next_action["kind"] == "NO_AUTHORIZED_DOWNSTREAM_ACTION"
    assert db.query(SupplierQuoteItem).first().unit_price == Decimal("123456789012345678.12345678")
    assert [(line.id, line.appraised_unit_price) for line in snapshot(db, entry).lines] == initial
    assert db.query(NccSelectionRevision).count() == db.query(AppraisedPriceDecision).count() == 0
    assert execute(db, entry, req)["result"] == original["result"]
    db.commit()
    assert counts(db) == (5, 5, 5)
    assert not {"price", "legal_name", "object_key", "terms", "invocation_binding"}.intersection(db.query(AuditEvent).filter(AuditEvent.event_name == "SupplierQuoteConfirmed").one().payload)


def test_each_mapping_required_no_zero_waiver(quote_db):
    db, entry = quote_db
    assert provider(db, entry).next_action["semantic_route_key"] == "supplier_quotes_prepare_required"
    execute(db, entry, request_for(db, entry))
    db.commit()
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "confirmation"))
    db.rollback()
    execute(db, entry, request_for(db, entry, "line-registration"))
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE" and len(snapshot(db, entry).supplier_quotes.coverage) == 1


def test_revision_withdraw_reject_no_fallback_historical_replay(drafted_db):
    db, entry = drafted_db
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    execute(db, entry, request_for(db, entry, "revision"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    execute(db, entry, request_for(db, entry, "rejection"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    assert execute(db, entry, req)["result"] == original["result"]
    db.commit()
    execute(db, entry, request_for(db, entry, "revision"))
    db.commit()
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    execute(db, entry, request_for(db, entry, "withdrawal"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE" and not snapshot(db, entry).supplier_quotes.coverage


@pytest.mark.parametrize("mutation", ["missing", "corrupt", "same_bytes_new_generation", "supplier", "upstream", "description", "quantity", "unit"])
def test_currentness_and_no_silent_rebind(drafted_db, mutation):
    db, entry = drafted_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    if mutation in ("missing", "corrupt", "same_bytes_new_generation"):
        store, key = entry["quote_store"], entry["quote_binding"].object_key
        if mutation == "missing":
            store._objects.pop(key)
        else:
            from dataclasses import replace
            old = store._objects[key]
            store._objects[key] = replace(old, content=b"Changed source" if mutation == "corrupt" else old.content, version=old.version + "-new")
    elif mutation == "supplier":
        entry["quote_supplier"].status = "inactive"
        entry["quote_supplier"].row_version += 1
    elif mutation == "upstream":
        pe_execute(db, entry, pe_request(db, entry, "confirmation-withdrawal"))
    else:
        line = snapshot(db, entry).lines[0]
        if mutation == "description":
            line.description = "Changed official specification"
        elif mutation == "quantity":
            line.quantity += 1
        else:
            line.unit_id = None
        line.row_version += 1
    db.commit()
    assert provider(db, entry).result != "COMPLETE"
    assert not snapshot(db, entry).supplier_quotes.coverage or mutation not in ("missing", "corrupt", "supplier", "same_bytes_new_generation")


@pytest.mark.parametrize("bad,code", [("float", 400), ("system", 403), ("cas", 409), ("supplier", 404), ("source", 404), ("line", 404), ("session", 409), ("permission", 403), ("reuse", 409)])
def test_negative_safety_zero_success_audit(quote_db, bad, code):
    db, entry = quote_db
    request = request_for(db, entry)
    actor = entry["user"]
    if bad == "float":
        request = request_for(db, entry, "revision", items=[dict(item_for(snapshot(db, entry).lines[0]), unit_price=1.2)])
    elif bad == "system":
        actor = object()
    elif bad == "cas":
        request["expected_case_version"] = "f" * 64
    elif bad == "supplier":
        request["supplier_id"] = str(uuid.uuid4())
    elif bad == "source":
        request["source_revision_id"] = str(uuid.uuid4())
    elif bad == "session":
        request["expected_session_id"] = str(uuid.uuid4())
    elif bad == "permission":
        entry["role"].permissions = ["project:read"]
        db.commit()
    elif bad in ("reuse", "line"):
        execute(db, entry, request)
        db.commit()
        if bad == "reuse":
            request["terms"]["quotation_number"] = "different payload"
        else:
            request = request_for(db, entry, "line-registration", item=dict(item_for(snapshot(db, entry).lines[0]), line_id=str(uuid.uuid4())))
    before = counts(db)
    with pytest.raises(HTTPException) as error:
        commands.execute(db, actor=actor, org_id=entry["org"].id, project_id=entry["project"].id, request=request)
    assert error.value.status_code == code
    db.rollback()
    assert counts(db) == before


def test_audit_failure_rollback(quote_db, monkeypatch):
    db, entry = quote_db
    before = counts(db)
    monkeypatch.setattr(commands, "log_audit_event", lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("Synthetic audit failure")))
    with pytest.raises(RuntimeError):
        execute(db, entry, request_for(db, entry))
    db.rollback()
    assert counts(db) == before


def test_receipt_integrity_and_unknown_outcome(drafted_db):
    db, entry = drafted_db
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    with db.get_bind().connect().execution_options(isolation_level="REPEATABLE READ") as connection:
        from sqlalchemy.orm import Session
        with Session(connection) as read:
            result = commands.read_receipt(read, actor=entry["user"], org_id=entry["org"].id, project_id=entry["project"].id, command_id=uuid.UUID(req["command_id"]))
            assert result["historical"] and result["result"] == original["result"]
    audit = db.query(AuditEvent).filter(AuditEvent.event_name == "SupplierQuoteConfirmed").one()
    audit.payload = dict(audit.payload, forged=True)
    db.commit()
    assert provider(db, entry).result == "STALE"


def test_non_draft_intact_complete_and_no_new_writes(drafted_db):
    db, entry = drafted_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    entry["project"].status = "archived"
    entry["project"].row_version += 1
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    with pytest.raises(HTTPException) as error:
        execute(db, entry, request_for(db, entry, "withdrawal"))
    assert error.value.status_code == 400
    db.rollback()


@pytest.mark.parametrize("offset", ["expiry", "review", "commit_expiry", "commit_line"])
def test_deadlines_use_server_time_at_commit(drafted_db, monkeypatch, offset):
    db, entry = drafted_db
    head = next(iter(snapshot(db, entry).supplier_quotes.heads.values()))
    deadline = head.content_binding["terms"]["expires_at" if offset == "expiry" else "review_due_at"]
    from datetime import datetime
    future = datetime.fromisoformat(deadline) + timedelta(seconds=1)
    req = request_for(db, entry, "line-registration" if offset == "commit_line" else "confirmation")
    if offset.startswith("commit_"):
        execute(db, entry, req)
        monkeypatch.setattr(commands, "utc_now", lambda: future)
        with pytest.raises(HTTPException):
            db.commit()
        db.rollback()
        assert counts(db) == (4, 4, 4)
    else:
        execute(db, entry, req)
        db.commit()
        from app.modules.project_master_data.application import supplier_quote_authority
        monkeypatch.setattr(supplier_quote_authority, "utc_now", lambda: future)
        assert provider(db, entry).result == "STALE"


@pytest.mark.parametrize("supplier_price,working,comparable,codes", [
    ("85", "100", True, ["below_working_price"]), ("84.99999999", "100", True, ["below_working_price", "difference_exceeds_15_percent"]),
    ("115", "100", True, []), ("115.00000001", "100", True, ["difference_exceeds_15_percent"]),
    ("99", "100", True, ["below_working_price"]), ("120", None, True, []), ("120", "0", True, []), ("120", "100", False, [])])
def test_exact_warning_thresholds_nonblocking(supplier_price, working, comparable, codes):
    from app.modules.project_master_data.application.supplier_quote_authority import comparison_warnings
    assert comparison_warnings(Decimal(supplier_price), Decimal(working) if working is not None else None, comparable=comparable) == codes


def test_optional_quote_and_same_supplier_dedup_do_not_break_complete(drafted_db):
    db, entry = drafted_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    entry["quote_binding"] = retain(db, entry, entry["quote_store"], "Second separate genuine offer")
    execute(db, entry, request_for(db, entry))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    for line in snapshot(db, entry).lines:
        execute(db, entry, request_for(db, entry, "line-registration", item=item_for(line, "101")))
        db.commit()
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert all(len(suppliers) == 1 for suppliers in snapshot(db, entry).supplier_quotes.coverage.values())
    entry["quote_store"]._objects.pop(entry["quote_binding"].object_key)
    assert provider(db, entry).result == "COMPLETE"


def test_ambiguous_supplier_identity_blocks_confirmation(drafted_db):
    db, entry = drafted_db
    entry["quote_supplier"].tax_code = None
    db.add(Supplier(organization_id=entry["org"].id, legal_name=entry["quote_supplier"].legal_name, status="active", tax_code=None, created_by=entry["user"].id))
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "confirmation"))
    db.rollback()


def test_legacy_active_rows_are_zero_and_no_file_metadata_admission(quote_db):
    db, entry = quote_db
    from app.modules.project_master_data.models import QuoteBatch, QuoteLine
    batch = QuoteBatch(organization_id=entry["org"].id, status="active", created_by=entry["user"].id)
    db.add(batch)
    db.flush()
    db.add(QuoteLine(quote_batch_id=batch.id, organization_id=entry["org"].id, supplier_id=entry["quote_supplier"].id,
        supplier_name="Synthetic supplier", quoted_unit_price=100, currency="VND", status="active"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE" and not snapshot(db, entry).supplier_quotes.coverage
    with pytest.raises(HTTPException) as error:
        execute(db, entry, dict(request_for(db, entry), evidence_file_id=str(uuid.uuid4())))
    assert error.value.status_code == 400
    db.rollback()


def test_cross_tenant_project_supplier_line_and_source_are_safe_404(quote_db):
    db, entry = quote_db
    from tests.test_pr05_m365_foundation import _seed, _document
    from app.modules.project_master_data.models import ProjectAssetLine
    foreign = _seed(db, suffix="a13-foreign")
    foreign_document = _document(db, foreign)
    foreign_supplier = Supplier(organization_id=foreign["organization"].id, legal_name="Other tenant", status="active", created_by=foreign["actor"].id)
    foreign_line = ProjectAssetLine(project_id=foreign["project"].id, asset_name="Other tenant line", quantity=1)
    db.add_all([foreign_supplier, foreign_line])
    db.commit()
    cases = [dict(request_for(db, entry), supplier_id=str(foreign_supplier.id)),
        dict(request_for(db, entry), quote_id=str(foreign_document.document_id), source_revision_id=str(foreign_document.id))]
    for req in cases:
        with pytest.raises(HTTPException) as error:
            execute(db, entry, req)
        assert error.value.status_code == 404
        db.rollback()
    with pytest.raises(HTTPException) as error:
        commands.execute(db, actor=entry["user"], org_id=entry["org"].id, project_id=foreign["project"].id, request=request_for(db, entry))
    assert error.value.status_code == 404
    db.rollback()
    execute(db, entry, request_for(db, entry))
    db.commit()
    req = request_for(db, entry, "line-registration", item=dict(item_for(snapshot(db, entry).lines[0]), line_id=str(foreign_line.id)))
    with pytest.raises(HTTPException) as error:
        execute(db, entry, req)
    assert error.value.status_code == 404
    db.rollback()
    assert counts(db) == (1, 1, 1)


@pytest.mark.skipif(sys.platform != "linux", reason="Existing production document blob adapter requires Linux/POSIX")
def test_real_local_retained_bytes_and_same_id_replacement(quote_db, tmp_path, monkeypatch):
    db, entry = quote_db
    from app.modules.document_workspace.infrastructure.local_filesystem_document_blob_store import LocalFilesystemDocumentBlobStore
    root = tmp_path / "blobs"
    root.mkdir(mode=0o700)
    store = LocalFilesystemDocumentBlobStore(root=root)
    monkeypatch.setattr(supplier_quote_source, "runtime_store", lambda: store)
    db.info["supplier_quote_blob_store"] = store
    entry["quote_binding"] = retain(db, entry, store, "Retained supplier document in actual local filesystem")
    entry["quote_store"] = store
    draft_all(db, entry)
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    binding = entry["quote_binding"]
    path = root / "objects" / binding.object_key
    path.unlink()
    path.write_bytes(b"Retained supplier document in actual local filesystem")
    assert provider(db, entry).result == "STALE"


def test_source_failure_during_command_final_recheck_rolls_back(drafted_db, monkeypatch):
    db, entry = drafted_db
    request = request_for(db, entry, "confirmation")
    original_resolve = commands.resolve_authority
    calls = []
    def resolve(*args, **kwargs):
        calls.append(1)
        if len(calls) == 2:
            entry["quote_store"]._objects.pop(entry["quote_binding"].object_key)
        return original_resolve(*args, **kwargs)
    monkeypatch.setattr(commands, "resolve_authority", resolve)
    before = counts(db)
    execute(db, entry, request)
    with pytest.raises(HTTPException) as error:
        db.commit()
    assert error.value.status_code == 409
    db.rollback()
    assert counts(db) == before


def test_negotiation_retains_valid_head_rejection_does_not_restore_revoked_head(drafted_db):
    db, entry = drafted_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    original = next(iter(snapshot(db, entry).supplier_quotes.confirmed_heads.values()))
    execute(db, entry, request_for(db, entry, "revision", revision_reason="negotiation", reason_note="Additional negotiated offer"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert snapshot(db, entry).supplier_quotes.confirmed_heads[original.quote_id].id == original.id
    execute(db, entry, request_for(db, entry, "rejection"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    execute(db, entry, request_for(db, entry, "withdrawal"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    assert not snapshot(db, entry).supplier_quotes.confirmed_heads


def test_recorded_concern_survives_successor_until_attested_resolution(drafted_db):
    db, entry = drafted_db
    rejected = execute(db, entry, request_for(db, entry, "rejection", concern_code="authenticity_concern"))
    db.commit()
    concern_id = rejected["result"]["record_id"]
    execute(db, entry, request_for(db, entry, "revision"))
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "confirmation"))
    db.rollback()
    execute(db, entry, request_for(db, entry, "revision", resolves_concern_ids=[concern_id],
        resolution_evidence="Human obtained supplier-origin clarification; retained source identity unchanged"))
    db.commit()
    assert provider(db, entry).result == "BLOCKED"
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE" and not snapshot(db, entry).supplier_quotes.concerns


def test_explicit_supplier_correction_revokes_old_issuer_and_requires_new_click(drafted_db):
    db, entry = drafted_db
    original = execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    old_supplier_id = entry["quote_supplier"].id
    corrected = Supplier(organization_id=entry["org"].id, legal_name="Correct issuing supplier", tax_code="corrected-issuer",
        status="active", created_by=entry["user"].id)
    db.add(corrected)
    db.commit()
    entry["quote_supplier"] = corrected
    with pytest.raises(HTTPException):
        execute(db, entry, request_for(db, entry, "revision", revision_reason="negotiation"))
    db.rollback()
    execute(db, entry, request_for(db, entry, "revision", revision_reason="correction", reason_note="Correct erroneous issuer attribution"))
    db.commit()
    assert provider(db, entry).result == "INCOMPLETE"
    assert not snapshot(db, entry).supplier_quotes.coverage
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    assert provider(db, entry).result == "COMPLETE"
    assert all(v == {corrected.id} and old_supplier_id not in v for v in snapshot(db, entry).supplier_quotes.coverage.values())
    assert original["historical"]
