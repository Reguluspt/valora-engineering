"""PostgreSQL-only concurrency and lock-order proof for PR-01 preliminary analysis."""
from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor
import os
import threading
import uuid

import pytest
from fastapi import HTTPException
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.modules.project_master_data.application import preliminary_analysis_service as s1_service
from app.modules.project_master_data.application.preliminary_analysis_service import (
    begin_preliminary_analysis_execution, claim_preliminary_analysis_attempt, finalize_preliminary_analysis,
)
from app.modules.project_master_data.application.preliminary_project_lifecycle_service import (
    switch_current_preliminary_import_batch,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    PreliminaryAnalysisFinalizeAttempt,
    PreliminaryAnalysisSnapshot,
    Project,
    ProjectAssetImportBatch,
    User,
    UserRole,
    UserSession,
)
from tests.test_pr01_preliminary_analysis_service import (
    PRELIMINARY_ANALYSIS_PERMISSION,
    _claim_and_begin, _line, _seed, _seed_s1_session, _s1_claim, _s1_context, _s1_finalize,
)


def _postgres_engine_or_skip():
    url = os.getenv("TEST_DATABASE_URL")
    if not url or not url.startswith("postgres"):
        if os.getenv("CI") == "true":
            pytest.fail("CI=true requires PostgreSQL TEST_DATABASE_URL for PR-01 preliminary analysis")
        pytest.skip("PR-01 preliminary analysis concurrency proof requires PostgreSQL TEST_DATABASE_URL")
    engine = create_engine(url, connect_args={"connect_timeout": 5}, pool_pre_ping=True)
    with engine.connect() as connection:
        exists = connection.execute(
            text("SELECT to_regclass('preliminary_analysis_snapshots')")
        ).scalar_one()
    if exists is None:
        engine.dispose()
        if os.getenv("CI") == "true":
            pytest.fail("CI PostgreSQL is not migrated to the PR-01 preliminary analysis head")
        pytest.skip("PostgreSQL is not migrated to the PR-01 preliminary analysis head")
    return engine


def _command(
    db: Session,
    *,
    ids: dict[str, uuid.UUID],
    actor_id: uuid.UUID,
    idempotency_key: str,
    line_manifest: list[dict] | None = None,
) -> PreliminaryAnalysisSnapshot:
    actor = db.get(User, actor_id)
    assert actor is not None
    return finalize_preliminary_analysis(
        db,
        actor=actor,
        org_id=ids["org"],
        project_id=ids["project"],
        expected_project_version=ids["project_version"],
        import_batch_id=ids["batch"],
        source_artifact_id=ids["artifact"],
        structure_snapshot_id=ids["structure"],
        mapping_decision_id=ids["decision"],
        mapping_profile_usage_id=ids["usage"],
        mapping_decision_digest_sha256=ids["decision_digest"],
        profile_usage_mapping_digest_sha256=ids["usage_digest"],
        line_manifest=line_manifest if line_manifest is not None else [_line()],
        idempotency_key=idempotency_key,
        confirmed=True,
        correlation_id="corr-pr01-preliminary-analysis-postgresql",
    )


def _run_pair(
    SessionLocal,
    *,
    ids: dict[str, uuid.UUID],
    work: list[tuple[uuid.UUID, str, list[dict] | None]],
) -> tuple[list[uuid.UUID], list[BaseException]]:
    barrier = threading.Barrier(2, timeout=30)
    results: list[uuid.UUID] = []
    errors: list[BaseException] = []

    def worker(actor_id: uuid.UUID, idempotency_key: str, line_manifest) -> None:
        db: Session = SessionLocal()
        try:
            barrier.wait(timeout=30)
            snapshot = _command(
                db,
                ids=ids,
                actor_id=actor_id,
                idempotency_key=idempotency_key,
                line_manifest=line_manifest,
            )
            results.append(snapshot.id)
        except BaseException as exc:
            errors.append(exc)
        finally:
            db.close()

    threads = [
        threading.Thread(
            target=worker,
            args=item,
            name=f"preliminary-analysis-worker-{index}",
            daemon=True,
        )
        for index, item in enumerate(work)
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=60)
    assert all(not thread.is_alive() for thread in threads)
    return results, errors


def _seed_ids(setup: Session, *, suffix: str) -> tuple[dict[str, object], dict]:
    seeded = _seed(setup, suffix=suffix)
    return (
        {
            "org": seeded["org"].id,
            "actor": seeded["actor"].id,
            "project": seeded["project"].id,
            "project_version": seeded["project"].row_version,
            "batch": seeded["batch"].id,
            "artifact": seeded["artifact"].id,
            "structure": seeded["structure"].id,
            "decision": seeded["decision"].id,
            "usage": seeded["usage"].id,
            "decision_digest": seeded["decision"].mapping_digest_sha256,
            "usage_digest": seeded["usage"].mapping_digest_sha256,
        },
        seeded,
    )


def _assert_one_fact_and_audit(SessionLocal, ids: dict[str, uuid.UUID]) -> None:
    verify: Session = SessionLocal()
    try:
        assert verify.query(PreliminaryAnalysisSnapshot).filter_by(
            organization_id=ids["org"], project_id=ids["project"]
        ).count() == 1
        assert verify.query(AuditEvent).filter_by(
            organization_id=ids["org"],
            event_name="PreliminaryAnalysisSnapshotFinalized",
        ).count() == 1
    finally:
        verify.close()


def test_postgresql_concurrent_same_request_replays_with_one_fact() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, _ = _seed_ids(setup, suffix=f"pg-same-{uuid.uuid4().hex[:8]}")
        setup.close()

        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-same-request", None),
                (ids["actor"], "pg-same-request", None),
            ],
        )

        assert errors == []
        assert len(results) == 2
        assert results[0] == results[1]
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        engine.dispose()


def test_postgresql_concurrent_same_key_different_digest_is_typed_reuse() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, seeded = _seed_ids(setup, suffix=f"pg-reuse-{uuid.uuid4().hex[:8]}")
        second_actor = User(
            organization_id=ids["org"],
            email=f"pg-reuse-peer-{uuid.uuid4().hex[:8]}@example.com",
            full_name="PostgreSQL Preliminary Analysis Peer",
        )
        setup.add(second_actor)
        setup.flush()
        setup.add(
            UserRole(
                user_id=second_actor.id,
                role_id=seeded["role"].id,
                is_active=True,
            )
        )
        setup.commit()
        second_actor_id = second_actor.id
        setup.close()

        from tests.test_pr01_preliminary_analysis_service import _line
        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-reused-key", None),
                (second_actor_id, "pg-reused-key", [_line(transport_percentage=10.0)]),
            ],
        )

        assert len(results) == 1
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].status_code == 409
        assert errors[0].detail["error_code"] == "preliminary_analysis_idempotency_key_reused"
        _assert_one_fact_and_audit(SessionLocal, ids)
    finally:
        setup.close()
        engine.dispose()


def test_postgresql_concurrent_different_keys_allocate_distinct_versions() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    ids = None
    try:
        ids, _ = _seed_ids(setup, suffix=f"pg-project-{uuid.uuid4().hex[:8]}")
        setup.close()

        results, errors = _run_pair(
            SessionLocal,
            ids=ids,
            work=[
                (ids["actor"], "pg-project-key-a", None),
                (ids["actor"], "pg-project-key-b", None),
            ],
        )

        assert len(results) == 2
        assert errors == []
        verify = SessionLocal()
        try:
            snapshots = verify.query(PreliminaryAnalysisSnapshot).filter_by(
                organization_id=ids["org"], project_id=ids["project"]
            ).all()
            assert {snapshot.version for snapshot in snapshots} == {1, 2}
            assert {snapshot.id for snapshot in snapshots} == set(results)
            assert verify.query(AuditEvent).filter_by(
                organization_id=ids["org"],
                event_name="PreliminaryAnalysisSnapshotFinalized",
            ).count() == 2
        finally:
            verify.close()
    finally:
        setup.close()
        engine.dispose()


def test_postgresql_switch_wins_project_lock_before_analysis_finalization() -> None:
    engine = _postgres_engine_or_skip()
    SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)
    setup: Session = SessionLocal()
    holder: Session = SessionLocal()
    try:
        ids, seeded = _seed_ids(setup, suffix=f"pg-switch-{uuid.uuid4().hex[:8]}")
        seeded["role"].permissions = [
            PRELIMINARY_ANALYSIS_PERMISSION, "project:update",
        ]
        target = ProjectAssetImportBatch(
            organization_id=ids["org"],
            project_id=ids["project"],
            source_filename="next.xlsx",
            created_by_user_id=ids["actor"],
        )
        setup.add(target)
        setup.commit()
        target_id = target.id
        holder.query(Project).filter(Project.id == ids["project"]).with_for_update().one()

        waiting = threading.Event()
        errors: list[BaseException] = []

        def observe(_conn, _cursor, statement, _params, _context, _many):
            if threading.current_thread().name == "analysis-switch-waiter" and "from projects" in statement.lower() and "for update" in statement.lower():
                waiting.set()

        event.listen(engine, "before_cursor_execute", observe)

        def finalize_waiter() -> None:
            db = SessionLocal()
            try:
                _command(db, ids=ids, actor_id=ids["actor"], idempotency_key="pg-switch-race")
            except BaseException as exc:
                errors.append(exc)
            finally:
                db.close()

        worker = threading.Thread(target=finalize_waiter, name="analysis-switch-waiter", daemon=True)
        worker.start()
        assert waiting.wait(timeout=15)
        switch_current_preliminary_import_batch(
            holder,
            actor=holder.get(User, ids["actor"]),
            org_id=ids["org"],
            project_id=ids["project"],
            target_import_batch_id=target_id,
            expected_current_import_batch_id=ids["batch"],
            expected_project_version=ids["project_version"],
            idempotency_key="pg-switch-before-analysis",
        )
        worker.join(timeout=30)
        assert not worker.is_alive()
        assert len(errors) == 1
        assert isinstance(errors[0], HTTPException)
        assert errors[0].detail["error_code"] == "preliminary_analysis_batch_not_current"
        verify = SessionLocal()
        try:
            assert verify.query(PreliminaryAnalysisSnapshot).filter_by(
                organization_id=ids["org"], project_id=ids["project"]
            ).count() == 0
        finally:
            verify.close()
    finally:
        holder.rollback()
        holder.close()
        setup.close()
        engine.dispose()

def test_s1_postgresql_two_sessions_one_claim_and_one_commit():
    engine = _postgres_engine_or_skip()
    sessions = sessionmaker(engine)
    try:
        with sessions() as db:
            ids, seeded = _seed_ids(db, suffix=f"s1-pg-{uuid.uuid4().hex[:8]}")
            first_session, claim, binding = _s1_context(db, seeded, range(3, 153))
            second_session = _seed_s1_session(db, seeded)[0].id
            db.commit()
        barrier = threading.Barrier(2, timeout=15)

        def claim_once(owner_session, envelope):
            with sessions() as db:
                barrier.wait()
                try:
                    output = claim_preliminary_analysis_attempt(
                        db, actor=db.get(User, ids["actor"]), session_id=owner_session,
                        project_id=ids["project"], claim=envelope,
                    )
                    return owner_session, envelope, output
                except HTTPException as denied:
                    return denied.detail["error_code"]

        other = claim.model_copy(update={"command_id": uuid.uuid4()})
        with ThreadPoolExecutor(max_workers=2) as executor:
            futures = [executor.submit(claim_once, sid, envelope)
                       for sid, envelope in ((first_session, claim), (second_session, other))]
            outcomes = [future.result(timeout=30) for future in futures]
        assert outcomes.count("preliminary_analysis_attempt_active") == 1
        winning_session, winning_claim, receipt = next(value for value in outcomes if isinstance(value, tuple))
        attempt_id = uuid.UUID(receipt["attempt_id"])
        with sessions() as db:
            with pytest.raises(HTTPException) as rejected:
                begin_preliminary_analysis_execution(
                    db, actor=db.get(User, ids["actor"]), session_id=winning_session, project_id=ids["project"],
                    attempt_id=attempt_id, command_id=str(winning_claim.command_id),
                    line_manifest=[_line(human_line_confirmed=False)],
                )
            assert rejected.value.detail["execution_started"] is False
        with sessions() as db:
            received = db.get(PreliminaryAnalysisFinalizeAttempt, attempt_id)
            assert (received.status, received.state_version, received.execution_generation) == ("RECEIVED", 1, 0)
            assert db.query(PreliminaryAnalysisSnapshot).filter_by(project_id=ids["project"]).count() == 0
            assert db.query(AuditEvent).filter_by(
                organization_id=ids["org"], event_name="PreliminaryAnalysisSnapshotFinalized",
            ).count() == 0
            actor = db.get(User, ids["actor"])
            generation = begin_preliminary_analysis_execution(
                db, actor=actor, session_id=winning_session, project_id=ids["project"],
                attempt_id=attempt_id, command_id=str(winning_claim.command_id),
                line_manifest=[_line(source_row_number=row["source_row_number"]) for row in binding],
            )
            loaded = {"actor": actor, "org": actor.organization, "project": db.get(Project, ids["project"])}
            snapshot = _s1_finalize(db, loaded, winning_session, winning_claim, attempt_id, generation, binding)
            terminal = db.get(PreliminaryAnalysisFinalizeAttempt, attempt_id)
            assert terminal.status == "COMMITTED" and terminal.committed_snapshot_id == snapshot.id
            assert len(terminal.row_binding_proof["rows"]) == 150
            same_claim = claim_preliminary_analysis_attempt(
                db, actor=actor, session_id=winning_session, project_id=ids["project"], claim=winning_claim,
            )
            assert same_claim["attempt_id"] == str(attempt_id) and same_claim["status"] == "COMMITTED"
            assert _s1_finalize(db, loaded, winning_session, winning_claim, attempt_id, None, binding).id == snapshot.id
            with pytest.raises(HTTPException) as reused:
                _s1_finalize(db, loaded, winning_session, winning_claim, attempt_id, None, binding, unit_price=1)
            assert reused.value.detail["error_code"] == "preliminary_analysis_idempotency_key_reused"
        _assert_one_fact_and_audit(sessions, ids)
    finally:
        engine.dispose()

@pytest.mark.parametrize("failure", ["audit_write", "commit_error", "session_revoked", "row_reassigned"])
def test_s1_postgresql_t3_has_no_partial_commit(monkeypatch, failure):
    engine = _postgres_engine_or_skip()
    sessions = sessionmaker(engine)
    try:
        with sessions() as db:
            ids, seeded = _seed_ids(db, suffix=f"s1-pg-{uuid.uuid4().hex[:8]}")
            session_id, claim, binding = _s1_context(db, seeded, [3, 4])
            attempt_id, generation = _claim_and_begin(db, seeded, session_id, claim)
            if failure == "audit_write":
                audit = s1_service.log_audit_event

                def append_then_interrupt(db, **kwargs):
                    audit(db, **kwargs)
                    db.flush()
                    raise RuntimeError("synthetic failure before T3 commit")

                monkeypatch.setattr(s1_service, "log_audit_event", append_then_interrupt)
                with pytest.raises(RuntimeError, match="synthetic failure"):
                    _s1_finalize(db, seeded, session_id, claim, attempt_id, generation, binding)
            elif failure == "commit_error":
                def fail_commit():
                    db.flush()
                    raise RuntimeError("synthetic T3 commit error")

                with monkeypatch.context() as patch:
                    patch.setattr(db, "commit", fail_commit)
                    with pytest.raises(RuntimeError, match="synthetic T3 commit error"):
                        _s1_finalize(db, seeded, session_id, claim, attempt_id, generation, binding)
            elif failure == "session_revoked":
                with sessions.begin() as other_db:
                    other_db.get(UserSession, session_id).status = "revoked"
                with pytest.raises(HTTPException) as denied:
                    _s1_finalize(db, seeded, session_id, claim, attempt_id, generation, binding)
                assert denied.value.status_code == 401
            else:
                binding[0]["staging_row_id"], binding[1]["staging_row_id"] = binding[1]["staging_row_id"], binding[0]["staging_row_id"]
                with pytest.raises(HTTPException) as denied:
                    _s1_finalize(db, seeded, session_id, claim, attempt_id, generation, binding)
                assert denied.value.detail["error_code"] == "preliminary_analysis_staging_mismatch"

            s1_service.mark_preliminary_analysis_unknown(db, org_id=ids["org"], project_id=ids["project"],
                                                         attempt_id=attempt_id, generation=generation)
        with sessions() as db:
            attempt = db.get(PreliminaryAnalysisFinalizeAttempt, attempt_id)
            assert attempt.status == "UNKNOWN" and attempt.committed_snapshot_id is None
            assert attempt.row_binding_proof is None
            assert db.query(PreliminaryAnalysisSnapshot).filter_by(project_id=ids["project"]).count() == 0
            assert db.query(AuditEvent).filter_by(
                organization_id=ids["org"], event_name="PreliminaryAnalysisSnapshotFinalized",
            ).count() == 0
    finally:
        engine.dispose()


def test_s1_postgresql_explicit_revision_requires_prior_terminal_and_new_base():
    engine = _postgres_engine_or_skip()
    try:
        with Session(engine) as db:
            _, seeded = _seed_ids(db, suffix=f"s1-pg-{uuid.uuid4().hex[:8]}")
            session_id, first_claim, binding = _s1_context(db, seeded, [3])
            first_id, generation = _claim_and_begin(db, seeded, session_id, first_claim)
            first = _s1_finalize(db, seeded, session_id, first_claim, first_id, generation, binding)
            with pytest.raises(HTTPException) as stale:
                _claim_and_begin(db, seeded, session_id, _s1_claim(seeded, base=0))
            assert stale.value.detail["error_code"] == "preliminary_analysis_base_conflict"
            new_claim = _s1_claim(seeded, base=first.version)
            second_id, generation = _claim_and_begin(db, seeded, session_id, new_claim)
            second = _s1_finalize(db, seeded, session_id, new_claim, second_id, generation, binding, unit_price=2000)
            assert second.version == first.version + 1
            assert first.line_manifest[0]["proposed_unit_price"] == 9876543
            assert second.line_manifest[0]["proposed_unit_price"] == 2000
    finally:
        engine.dispose()
