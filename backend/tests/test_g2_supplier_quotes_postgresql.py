"""A13 actual PostgreSQL locks, both orderings and commit-time cutoffs."""
from datetime import datetime, timedelta

import pytest
from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.modules.project_master_data.models import Supplier
from app.modules.document_workspace.models import DocumentRevisionCurrentHead
from app.modules.project_master_data.application.asset_review_authority import lock_project, resolve_authority
from app.modules.project_master_data.application import supplier_quote_commands as commands
from tests.test_g2_authority_postgresql import _run_ordered_pair
from tests.test_g2_supplier_quotes import (
    entry_db as _entry_db, line_db as _line_db, workbench_db as _workbench_db,
    evidence_db as _evidence_db, covered_db as _covered_db, quote_db as _quote_db,
    drafted_db as _drafted_db, request_for, execute, provider, counts, snapshot,
    pe_execute, pe_request,
)

entry_db, line_db, workbench_db = _entry_db, _line_db, _workbench_db
evidence_db, covered_db, quote_db, drafted_db = _evidence_db, _covered_db, _quote_db, _drafted_db


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("race", ["competing_revisions", "competing_confirmations", "confirmation_withdrawal", "confirmation_rejection",
    "description", "quantity", "unit", "price_withdrawal", "source_loss", "source_integrity", "multiline_source"])
def test_project_serialized_matrix(drafted_db, first, race):
    db, entry = drafted_db
    left_request = request_for(db, entry, "revision" if race in ("competing_revisions", "multiline_source") else "confirmation")
    before = counts(db)
    def left(worker):
        return execute(worker, entry, left_request)
    if race in ("competing_revisions", "competing_confirmations", "confirmation_withdrawal", "confirmation_rejection"):
        kind = {"competing_revisions": "revision", "competing_confirmations": "confirmation", "confirmation_withdrawal": "withdrawal", "confirmation_rejection": "rejection"}[race]
        right_request = request_for(db, entry, kind)
        def right(worker):
            return execute(worker, entry, right_request)
    elif race == "price_withdrawal":
        right_request = pe_request(db, entry, "confirmation-withdrawal")
        def right(worker):
            return pe_execute(worker, entry, right_request)
    else:
        line_id = snapshot(db, entry).lines[0].id
        def right(worker):
            project = lock_project(worker, org_id=entry["org"].id, project_id=entry["project"].id)
            if race in ("source_loss", "source_integrity", "multiline_source"):
                from dataclasses import replace
                key = entry["quote_binding"].object_key
                store = entry["quote_store"]
                if race in ("source_loss", "multiline_source"):
                    store._objects.pop(key)
                else:
                    store._objects[key] = replace(store._objects[key], content=b"Corrupted retained bytes")
            else:
                from app.modules.project_master_data.models import ProjectAssetLine
                line = worker.query(ProjectAssetLine).filter_by(project_id=project.id, id=line_id).with_for_update().one()
                if race == "description":
                    line.description = "Changed specification"
                elif race == "quantity":
                    line.quantity += 1
                else:
                    line.unit_id = None
                line.row_version += 1
                project.row_version += 1
            worker.flush()
            return "dependency changed"
    holder, waiter = (left, right) if first == "left" else (right, left)
    results, errors, locks = _run_ordered_pair(db, holder, waiter)
    assert locks["holder"] and locks["waiter"]
    assert all(isinstance(exc, HTTPException) and exc.status_code == 409 for exc in errors.values()), errors
    if race == "price_withdrawal":
        assert len(results) == len(errors) == 1
        assert counts(db) == tuple(n + (1 if first == "left" else 0) for n in before)
    elif race in ("competing_revisions", "competing_confirmations", "confirmation_withdrawal", "confirmation_rejection"):
        assert len(results) == len(errors) == 1
        assert counts(db) == tuple(n + 1 for n in before)
    elif first == "right":
        assert len(results) == len(errors) == 1
        assert counts(db) == before
    else:
        assert len(results) == 2 and not errors
        assert counts(db) == tuple(n + 1 for n in before)
    if race.startswith("competing"):
        state = snapshot(db, entry).supplier_quotes
        assert len(state.heads) == 1
        if race == "competing_revisions":
            assert len(state.items[next(iter(state.heads.values())).id]) == len(snapshot(db, entry).lines)
    elif race == "price_withdrawal":
        assert (provider(db, entry).result == "COMPLETE") == (first == "left")
    elif race not in ("confirmation_withdrawal", "confirmation_rejection"):
        assert provider(db, entry).result != "COMPLETE"


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("mutation", ["deactivation", "merge", "multiline_revision"])
def test_supplier_row_lock_both_orderings(drafted_db, first, mutation):
    db, entry = drafted_db
    req = request_for(db, entry, "revision" if mutation == "multiline_revision" else "confirmation")
    supplier_id = entry["quote_supplier"].id
    before = counts(db)
    target = Supplier(organization_id=entry["org"].id, legal_name="Independent merge target", tax_code="target", status="active", created_by=entry["user"].id)
    db.add(target)
    db.commit()
    def left(worker):
        return execute(worker, entry, req)
    def right(worker):
        row = worker.query(Supplier).filter_by(id=supplier_id, organization_id=entry["org"].id).with_for_update().one()
        row.status = "merged" if mutation == "merge" else "inactive"
        if mutation == "merge":
            row.merged_into_supplier_id = target.id
        row.row_version += 1
        worker.flush()
        return "Supplier changed"
    holder, waiter = (left, right) if first == "left" else (right, left)
    results, errors, _ = _run_ordered_pair(db, holder, waiter, lock_table="suppliers")
    assert provider(db, entry).result != "COMPLETE"
    assert len(errors) == (1 if first == "right" else 0), errors
    assert counts(db) == tuple(n + (1 if first == "left" else 0) for n in before)


@pytest.mark.parametrize("first", ["left", "right"])
def test_source_generation_head_lock_both_orderings(drafted_db, first):
    db, entry = drafted_db
    from app.modules.document_workspace.models import DocumentRevision
    old = db.get(DocumentRevision, entry["quote_binding"].document_revision_id)
    new = DocumentRevision(organization_id=old.organization_id, project_id=old.project_id, document_id=old.document_id,
        document_revision=2, data_snapshot_digest_sha256="8" * 64, content_checksum_sha256="9" * 64, idempotency_key="synthetic-successor",
        request_digest_sha256="7" * 64, created_by_user_id=old.created_by_user_id)
    db.add(new)
    db.commit()
    req = request_for(db, entry, "confirmation")
    before = counts(db)
    def left(worker):
        return execute(worker, entry, req)
    def right(worker):
        head = worker.query(DocumentRevisionCurrentHead).filter_by(organization_id=old.organization_id, project_id=old.project_id,
            document_id=old.document_id).with_for_update().one()
        head.current_revision_id, head.document_revision = new.id, 2
        worker.flush()
        return "source generation changed"
    holder, waiter = (left, right) if first == "left" else (right, left)
    results, errors, _ = _run_ordered_pair(db, holder, waiter, lock_table="document_revision_current_heads")
    assert len(errors) == (1 if first == "right" else 0), errors
    assert counts(db) == tuple(n + (1 if first == "left" else 0) for n in before)
    assert provider(db, entry).result != "COMPLETE"


@pytest.mark.parametrize("first", ["left", "right"])
@pytest.mark.parametrize("mutation", ["revision", "withdrawal"])
def test_replay_is_historical_during_successor_or_reversal(drafted_db, first, mutation):
    db, entry = drafted_db
    req = request_for(db, entry, "confirmation")
    original = execute(db, entry, req)
    db.commit()
    next_request = request_for(db, entry, mutation)
    before = counts(db)
    def left(worker):
        result = execute(worker, entry, req)
        assert result["replayed"] and result["result"] == original["result"]
        return result
    def right(worker):
        return execute(worker, entry, next_request)
    results, errors, _ = _run_ordered_pair(db, left if first == "left" else right, right if first == "left" else left)
    assert len(results) == 2 and not errors
    assert counts(db) == tuple(n + 1 for n in before)
    assert provider(db, entry).result == "INCOMPLETE"


def test_expiry_crosses_real_project_lock_wait_and_rolls_back(drafted_db, monkeypatch):
    db, entry = drafted_db
    req = request_for(db, entry, "confirmation")
    revision = next(iter(snapshot(db, entry).supplier_quotes.heads.values()))
    cutoff = datetime.fromisoformat(revision.content_binding["terms"]["review_due_at"])
    before = counts(db)
    def holder(worker):
        lock_project(worker, org_id=entry["org"].id, project_id=entry["project"].id)
        monkeypatch.setattr(commands, "utc_now", lambda: cutoff + timedelta(seconds=1))
        return "clock advanced after lock wait began"
    results, errors, _ = _run_ordered_pair(db, holder, lambda worker: execute(worker, entry, req))
    assert "holder" in results and set(errors) == {"waiter"} and errors["waiter"].status_code == 409
    assert counts(db) == before


@pytest.mark.parametrize("first", ["read", "write"])
def test_read_snapshot_vs_official_mutation(drafted_db, first):
    db, entry = drafted_db
    req = request_for(db, entry, "confirmation")
    db.rollback()
    with Session(db.get_bind().execution_options(isolation_level="REPEATABLE READ")) as read:
        if first == "write":
            execute(db, entry, req)
            db.commit()
        old = resolve_authority(read, org_id=entry["org"].id, project_id=entry["project"].id)
        if first == "read":
            execute(db, entry, req)
            db.commit()
        same = resolve_authority(read, org_id=entry["org"].id, project_id=entry["project"].id)
        assert old.case_version == same.case_version and old.supplier_quotes.complete == same.supplier_quotes.complete
        assert old.supplier_quotes.complete == (first == "write")
    assert provider(db, entry).result == "COMPLETE"


@pytest.mark.parametrize("first", ["left", "right"])
def test_negotiation_confirmation_vs_valid_current_withdrawal(drafted_db, first):
    db, entry = drafted_db
    execute(db, entry, request_for(db, entry, "confirmation"))
    db.commit()
    former = next(iter(snapshot(db, entry).supplier_quotes.confirmed_heads.values()))
    execute(db, entry, request_for(db, entry, "revision", revision_reason="negotiation"))
    db.commit()
    left_request = request_for(db, entry, "confirmation")
    right_request = request_for(db, entry, "withdrawal", target_revision_id=former.id)
    before = counts(db)
    def left(worker):
        return execute(worker, entry, left_request)
    def right(worker):
        return execute(worker, entry, right_request)
    holder, waiter = (left, right) if first == "left" else (right, left)
    results, errors, locks = _run_ordered_pair(db, holder, waiter)
    assert locks["holder"] and locks["waiter"]
    assert set(results) == {"holder"} and set(errors) == {"waiter"}
    assert errors["waiter"].status_code == 409
    assert counts(db) == tuple(n + 1 for n in before)
    state = snapshot(db, entry).supplier_quotes
    assert len(state.heads) == 1
    assert state.status[former.id] == ("superseded" if first == "left" else "withdrawn")
    assert len(state.confirmed_heads) == (1 if first == "left" else 0)
    assert provider(db, entry).result == ("COMPLETE" if first == "left" else "INCOMPLETE")
