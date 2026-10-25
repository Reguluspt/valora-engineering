"""Real separate-connection proofs, using only the explicit test database."""

import concurrent.futures
import os
import subprocess
import sys
import threading
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from fastapi import HTTPException
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.api.auth import hash_token
from app.db.session import engine, SessionLocal
from app.modules.project_master_data.application import (
    preliminary_project_create_service as service,
)
from app.modules.project_master_data.models import (
    AuditEvent,
    OrganizationProfile,
    PreliminaryProjectCreateReceipt as Receipt,
    Project,
    Role,
    User,
    UserRole,
    UserSession,
)
from tests.test_preliminary_project_create import command


@pytest.fixture
def principal(monkeypatch):
    assert engine.dialect.name == "postgresql", "Mandatory PostgreSQL proof cannot skip"
    assert os.environ.get("VALORA_ENV") == "test"
    assert os.environ.get("GITHUB_ACTIONS") == "true" or (
        engine.url.database.startswith("valora_issue217_disposable") and engine.url.port == 55417
    ), "Issue217 proof may only use the newly provisioned disposable developer PostgreSQL"
    monkeypatch.setenv("VALORA_PRELIMINARY_CREATE_ENABLED", "true")
    now = datetime.now(timezone.utc)
    with SessionLocal() as db:
        org = OrganizationProfile(
            legal_name="Synthetic issue217", organization_slug=f"i217-{uuid.uuid4().hex}"
        )
        db.add(org)
        db.flush()
        actor = User(
            organization_id=org.id, email="synthetic@example.invalid", full_name="Synthetic actor"
        )
        role = Role(
            code=f"i217-{uuid.uuid4().hex}",
            display_name="Synthetic owner",
            permissions=["project:create", "project:read"],
        )
        db.add_all([actor, role])
        db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role.id))
        sid = uuid.uuid4()
        db.add(
            UserSession(
                id=sid,
                user_id=actor.id,
                organization_id=org.id,
                access_token_hash=hash_token(str(sid)),
                csrf_token_hash=hash_token("issue217-synthetic-csrf"),
                access_expires_at=now + timedelta(hours=1),
                idle_expires_at=now + timedelta(hours=1),
                absolute_expires_at=now + timedelta(hours=2),
            )
        )
        db.commit()
        return service.Principal(org.id, actor.id, sid)


def facts(principal):
    with SessionLocal() as db:
        return tuple(
            len(
                db.scalars(
                    select(model).where(model.organization_id == principal.organization_id)
                ).all()
            )
            for model in (Project, AuditEvent, Receipt)
        )


def test_a01_a04_a05_a19_atomic_replay_conflict_and_distinct_keys(principal):
    payload = command()
    result, status = service.create_preliminary_request(principal, payload)
    assert status == 201 and facts(principal) == (1, 1, 1)
    with SessionLocal() as db:
        p = db.get(Project, uuid.UUID(result["project"]["id"]))
        assert (
            p.customer_id,
            p.fee_currency_id,
            p.signer_profile_id,
            p.current_preliminary_import_batch_id,
        ) == (None,) * 4
        assert p.status == "draft" and p.knowledge_status == "pending" and p.fee_amount == 0
        p.name, p.status = "Changed later", "archived"
        db.commit()
    assert service.create_preliminary_request(principal, payload) == (result, 200)
    assert service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)) == result
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(
            principal, command(request_id=payload.request_id, name="Different")
        )
    assert error.value.status_code == 409 and error.value.detail["code"] == "POST_CONFLICT"
    assert facts(principal) == (1, 1, 1)
    service.create_preliminary_request(principal, command())
    assert facts(principal) == (2, 2, 2)


@pytest.mark.parametrize("stage", ["project", "audit", "receipt"])
def test_a09_a11_a13_flush_fault_rolls_back_all_facts(principal, monkeypatch, stage):
    payload = command()
    target = {"project": Project, "audit": AuditEvent, "receipt": Receipt}[stage]

    def fail(db, *_):
        if any(isinstance(obj, target) for obj in db.new):
            raise RuntimeError("synthetic flush failure")

    event.listen(Session, "before_flush", fail)
    try:
        with pytest.raises(HTTPException) as error:
            service.create_preliminary_request(principal, payload)
        assert error.value.detail["code"] == "CREATE_UNRESOLVED"
    finally:
        event.remove(Session, "before_flush", fail)
    assert facts(principal) == (0, 0, 0)
    assert service.create_preliminary_request(principal, payload)[1] == 201
    assert facts(principal) == (1, 1, 1)


@pytest.mark.parametrize("reverse", [False, True])
@pytest.mark.parametrize("different,rollback", [(False, False), (True, False), (True, True)])
def test_a06_a07_a08_barrier_and_database_lock_observed(
    principal, monkeypatch, different, rollback, reverse
):
    first, waiting, release = threading.Event(), threading.Event(), threading.Event()
    first_name, other_name = ("Winner Y", "Winner X") if reverse else ("Winner X", "Winner Y")
    payload = command(name=first_name)
    other = command(request_id=payload.request_id, name=other_name if different else first_name)
    original_dto = service.receipt_dto

    def hold(db, receipt):
        result = original_dto(db, receipt)
        if threading.current_thread().name.startswith("first"):
            first.set()
            assert release.wait(10)
            if rollback:
                raise RuntimeError("full rollback after all facts")
        return result

    monkeypatch.setattr(service, "receipt_dto", hold)

    def call(p):
        try:
            return service.create_preliminary_request(principal, p)
        except HTTPException as exc:
            return exc.status_code, exc.detail

    def observe_lock(conn, cursor, statement, parameters, context, executemany):
        if "pg_advisory_xact_lock" in statement and threading.current_thread().name.startswith(
            "second"
        ):
            waiting.set()

    event.listen(engine, "before_cursor_execute", observe_lock)
    try:
        with (
            concurrent.futures.ThreadPoolExecutor(thread_name_prefix="first") as a,
            concurrent.futures.ThreadPoolExecutor(thread_name_prefix="second") as b,
        ):
            fa = a.submit(call, payload)
            assert first.wait(10)
            fb = b.submit(call, other)
            assert waiting.wait(10)
            # Observe actual queued lock, not elapsed-time inference.
            with engine.connect() as observer:
                for _ in range(100):
                    if observer.scalar(
                        text(
                            "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND NOT granted"
                        )
                    ):
                        break
                    threading.Event().wait(0.01)
                else:
                    pytest.fail("No PostgreSQL advisory lock waiter observed")
            release.set()
            ra, rb = fa.result(), fb.result()
        assert ra[1] == 201 if not rollback else ra[0] == 503
        if different and not rollback:
            assert rb[0] == 409
        else:
            assert rb[1] == (201 if rollback else 200)
        assert facts(principal) == (1, 1, 1)
        if rollback and different:
            with pytest.raises(HTTPException) as conflict:
                service.create_preliminary_request(principal, payload)
            assert conflict.value.status_code == 409
    finally:
        release.set()
        event.remove(engine, "before_cursor_execute", observe_lock)


def test_a12_lost_commit_ack_recovers_committed_identity(principal):
    payload = command()

    def lost_ack(db):
        raise RuntimeError("synthetic commit acknowledgement loss")

    event.listen(Session, "after_commit", lost_ack)
    try:
        with pytest.raises(HTTPException) as error:
            service.create_preliminary_request(principal, payload)
        assert error.value.detail["code"] == "COMMIT_OUTCOME_UNKNOWN"
    finally:
        event.remove(Session, "after_commit", lost_ack)
    assert facts(principal) == (1, 1, 1)
    result = service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
    assert service.create_preliminary_request(principal, payload) == (result, 200)


def test_a14_lock_timeout_and_a21_uncommitted_get(principal):
    payload = command()
    with engine.connect() as connection, connection.begin():
        connection.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": service.lock_key(principal, uuid.UUID(payload.request_id))},
        )
        with pytest.raises(HTTPException) as error:
            service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
        assert error.value.detail == {
            "code": "UNRESOLVED",
            "status": "UNRESOLVED",
            "request_id": payload.request_id,
            "final": False,
        }
        with pytest.raises(HTTPException) as error:
            service.create_preliminary_request(principal, payload)
        assert error.value.detail["code"] == "LOCK_TIMEOUT" and facts(principal) == (0, 0, 0)
    assert service.create_preliminary_request(principal, payload)[1] == 201


def test_a15_hash_collision_keeps_full_key(principal, monkeypatch):
    monkeypatch.setattr(service, "lock_key", lambda *_: 217)
    first, second = command(), command()
    a, _ = service.create_preliminary_request(principal, first)
    b, _ = service.create_preliminary_request(principal, second)
    assert a["project"] != b["project"] and facts(principal) == (2, 2, 2)


def test_a15_colliding_distinct_keys_serialize_then_keep_independent_receipts(
    principal, monkeypatch
):
    monkeypatch.setattr(service, "lock_key", lambda *_: 217)
    first, release = threading.Event(), threading.Event()
    original = service.receipt_dto
    payloads = [command(name="Collision X"), command(name="Collision Y")]

    def hold(db, receipt):
        result = original(db, receipt)
        if str(receipt.request_id) == payloads[0].request_id and not release.is_set():
            first.set()
            assert release.wait(8)
        return result

    with monkeypatch.context() as patch:
        patch.setattr(service, "receipt_dto", hold)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            a = pool.submit(service.create_preliminary_request, principal, payloads[0])
            assert first.wait(8)
            b = pool.submit(service.create_preliminary_request, principal, payloads[1])
            try:
                with engine.connect() as observer:
                    for _ in range(200):
                        if observer.scalar(
                            text(
                                "SELECT count(*) FROM pg_locks WHERE locktype='advisory' AND NOT granted"
                            )
                        ):
                            break
                        observer.commit()
                        threading.Event().wait(0.01)
                    else:
                        pytest.fail("Colliding-key waiter not observed")
            finally:
                release.set()
            ra, sa = a.result(timeout=8)
            rb, sb = b.result(timeout=8)
    assert sa == sb == 201 and ra["project"] != rb["project"]
    for payload, result in zip(payloads, [ra, rb]):
        assert (
            service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)) == result
        )
    assert facts(principal) == (2, 2, 2)


def test_a16_legacy_code_collision_rolls_back(principal, monkeypatch):
    candidate = uuid.uuid4()
    with SessionLocal() as db:
        db.add(
            Project(
                organization_id=principal.organization_id,
                created_by=principal.actor_user_id,
                code=format(candidate.int, "039d"),
                name="Legacy numeric",
            )
        )
        db.commit()
    monkeypatch.setattr(service.uuid, "uuid4", lambda: candidate)
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(principal, command())
    assert error.value.detail["code"] == "IDENTITY_COLLISION" and facts(principal) == (1, 0, 0)


def test_a30_corruption_is_not_permission_to_create(principal):
    payload = command()
    service.create_preliminary_request(principal, payload)
    with SessionLocal() as db:
        receipt = service.find_receipt(db, principal, uuid.UUID(payload.request_id))
        receipt.payload_digest = "0" * 64
        db.commit()
    for operation in (
        lambda: service.create_preliminary_request(principal, payload),
        lambda: service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)),
    ):
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.detail["code"] == "RECEIPT_INTEGRITY_ERROR"
    assert facts(principal) == (1, 1, 1)


@pytest.mark.parametrize("stage", ["Project", "AuditEvent", "PreliminaryProjectCreateReceipt"])
def test_a11_process_death_after_each_flush(principal, stage):
    payload = command()
    code = (
        """
import os, uuid
from app.main import app
from sqlalchemy import event
from sqlalchemy.orm import Session
from app.modules.project_master_data.application import preliminary_project_create_service as s
from app.modules.project_master_data.preliminary_project_create_schemas import CreatePreliminaryRequest
def die(db, context):
    if any(type(obj).__name__ == STAGE for obj in db.new):
        os._exit(217)
event.listen(Session, "after_flush", die)
s.create_preliminary_request(s.Principal(*map(uuid.UUID, PRINCIPAL)), CreatePreliminaryRequest.model_validate(PAYLOAD))
""".replace("STAGE", repr(stage))
        .replace(
            "PRINCIPAL",
            repr(
                [
                    str(principal.organization_id),
                    str(principal.actor_user_id),
                    str(principal.session_id),
                ]
            ),
        )
        .replace("PAYLOAD", repr(payload.model_dump()))
    )
    result = subprocess.run([sys.executable, "-c", code], capture_output=True, timeout=20)
    assert result.returncode == 217, result.stderr.decode(errors="replace")
    assert facts(principal) == (0, 0, 0)
    assert service.create_preliminary_request(principal, payload)[1] == 201


def test_a20_authorization_rechecked_after_lock_wait(principal, monkeypatch):
    entered, release = threading.Event(), threading.Event()
    original = service.authorize
    calls = 0

    def checked(db, who, permission):
        nonlocal calls
        original(db, who, permission)
        calls += 1
        if calls == 1:
            entered.set()
            assert release.wait(10)

    monkeypatch.setattr(service, "authorize", checked)
    with concurrent.futures.ThreadPoolExecutor() as pool:
        future = pool.submit(service.create_preliminary_request, principal, command())
        assert entered.wait(10)
        with SessionLocal() as db:
            role = (
                db.query(Role)
                .join(UserRole)
                .filter(UserRole.user_id == principal.actor_user_id)
                .one()
            )
            role.permissions = ["project:read"]
            db.commit()
        release.set()
        with pytest.raises(HTTPException) as error:
            future.result()
        assert error.value.status_code == 403
    assert facts(principal) == (0, 0, 0)


def test_a03_digest_collision_still_compares_exact_bytes(principal, monkeypatch):
    monkeypatch.setattr(service, "digest", lambda *_: "a" * 64)
    payload = command(name="X")
    service.create_preliminary_request(principal, payload)
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(
            principal, command(request_id=payload.request_id, name="Y")
        )
    assert error.value.status_code == 409 and facts(principal) == (1, 1, 1)


@pytest.mark.parametrize("bad", ["audit_fk", "digest_check", "version_check"])
def test_a13_database_constraint_failure_is_atomic(principal, bad):
    def break_receipt(db, *_):
        for row in db.new:
            if isinstance(row, Receipt):
                if bad == "audit_fk":
                    row.audit_event_id = uuid.uuid4()
                elif bad == "digest_check":
                    row.payload_digest = "invalid"
                else:
                    row.canonical_version = "unsupported"

    event.listen(Session, "before_flush", break_receipt)
    try:
        with pytest.raises(HTTPException) as error:
            service.create_preliminary_request(principal, command())
        assert error.value.detail["code"] == "CREATE_UNRESOLVED"
    finally:
        event.remove(Session, "before_flush", break_receipt)
    assert facts(principal) == (0, 0, 0)


def test_a10_independent_tenants_same_nonce(principal, monkeypatch):
    other = globals()["principal"].__wrapped__(monkeypatch)
    payload = command()
    a, _ = service.create_preliminary_request(principal, payload)
    with pytest.raises(HTTPException) as error:
        service.recover_preliminary_request(other, uuid.UUID(payload.request_id))
    assert error.value.status_code == 404 and a["project"]["id"] not in str(error.value.detail)
    b, _ = service.create_preliminary_request(other, payload)
    assert a["project"] != b["project"]


@pytest.mark.parametrize("activation", [None, "false"])
def test_a29_application_activation_rollback_keeps_recovery(principal, monkeypatch, activation):
    payload = command()
    result, _ = service.create_preliminary_request(principal, payload)
    if activation is None:
        monkeypatch.delenv("VALORA_PRELIMINARY_CREATE_ENABLED")
    else:
        monkeypatch.setenv("VALORA_PRELIMINARY_CREATE_ENABLED", activation)
    assert service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)) == result
    assert service.create_preliminary_request(principal, payload) == (result, 200)
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(principal, command())
    assert error.value.status_code == 503 and facts(principal) == (1, 1, 1)


def test_d7_create_is_disabled_by_default_on_migrated_schema(principal, monkeypatch):
    monkeypatch.delenv("VALORA_PRELIMINARY_CREATE_ENABLED")
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(principal, command())
    assert error.value.status_code == 503
    assert error.value.detail["final"] is False
    assert facts(principal) == (0, 0, 0)


@pytest.mark.parametrize("activation", [None, "false", "true"])
def test_d7_missing_receipt_schema_never_queries_absent_table(principal, monkeypatch, activation):
    if activation is None:
        monkeypatch.delenv("VALORA_PRELIMINARY_CREATE_ENABLED")
    else:
        monkeypatch.setenv("VALORA_PRELIMINARY_CREATE_ENABLED", activation)
    payload = command()
    hidden = "i217_unmigrated_receipts_" + uuid.uuid4().hex
    statements = []

    def record(_conn, _cursor, statement, *_):
        statements.append(statement.lower())

    # This suite owns a disposable database; restore the retained table even on failure.
    with engine.begin() as db:
        db.execute(text(f'ALTER TABLE preliminary_project_create_receipts RENAME TO "{hidden}"'))
    event.listen(engine, "before_cursor_execute", record)
    try:
        for call, code in (
            (lambda: service.create_preliminary_request(principal, payload), "CREATE_UNRESOLVED"),
            (lambda: service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)), "RECOVERY_UNAVAILABLE"),
        ):
            with pytest.raises(HTTPException) as error:
                call()
            assert error.value.status_code == 503
            assert error.value.detail == {
                "code": code, "status": "UNRESOLVED", "request_id": payload.request_id, "final": False,
            }
        assert not any("from preliminary_project_create_receipts" in sql for sql in statements)
        assert not any(sql.lstrip().startswith("insert") for sql in statements)
    finally:
        event.remove(engine, "before_cursor_execute", record)
        with engine.begin() as db:
            db.execute(text(f'ALTER TABLE "{hidden}" RENAME TO preliminary_project_create_receipts'))
    assert facts(principal) == (0, 0, 0)


def test_a14_cancel_blocked_command_closes_transaction(principal):
    payload = command()
    with engine.connect() as blocker, blocker.begin():
        blocker.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": service.lock_key(principal, uuid.UUID(payload.request_id))},
        )
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(service.create_preliminary_request, principal, payload)
            with engine.connect() as observer:
                for _ in range(200):
                    pid = observer.scalar(
                        text(
                            "SELECT pid FROM pg_stat_activity WHERE datname=current_database() "
                            "AND wait_event='advisory' AND pid<>pg_backend_pid()"
                        )
                    )
                    if pid:
                        assert observer.scalar(text("SELECT pg_cancel_backend(:pid)"), {"pid": pid})
                        break
                    observer.commit()
                    threading.Event().wait(0.01)
                else:
                    pytest.fail("Blocked command not observed")
            with pytest.raises(HTTPException) as error:
                future.result(timeout=8)
            assert error.value.detail["status"] == "UNRESOLVED"
            assert error.value.detail["final"] is False
    assert facts(principal) == (0, 0, 0)
    assert service.create_preliminary_request(principal, payload)[1] == 201


def test_a14_real_deadlock_rolls_back_victim_and_allows_replay(principal, monkeypatch):
    payloads = [command(name="Deadlock X"), command(name="Deadlock Y")]
    barrier = threading.Barrier(2)
    original = service.receipt_dto

    def deadlock(db, receipt):
        result = original(db, receipt)
        barrier.wait(timeout=8)
        other = next(p for p in payloads if p.request_id != str(receipt.request_id))
        db.execute(
            text("SELECT pg_advisory_xact_lock(:key)"),
            {"key": service.lock_key(principal, uuid.UUID(other.request_id))},
        )
        return result

    def call(payload):
        try:
            return service.create_preliminary_request(principal, payload)
        except HTTPException as error:
            return error

    with monkeypatch.context() as patch:
        patch.setattr(service, "receipt_dto", deadlock)
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            results = list(pool.map(call, payloads))
    errors = [result for result in results if isinstance(result, HTTPException)]
    assert len(errors) == 1
    assert errors[0].detail["status"] == "UNRESOLVED" and errors[0].detail["final"] is False
    assert facts(principal) == (1, 1, 1)
    for payload in payloads:
        assert service.create_preliminary_request(principal, payload)[1] in (200, 201)
    assert facts(principal) == (2, 2, 2)


def test_a16_project_uuid_collision_preserves_legacy_identity(principal, monkeypatch):
    candidate, payload = uuid.uuid4(), command()
    with SessionLocal() as db:
        db.add(
            Project(
                id=candidate,
                organization_id=principal.organization_id,
                created_by=principal.actor_user_id,
                code="Legacy UUID",
                name="Preserved",
            )
        )
        db.commit()
    monkeypatch.setattr(service.uuid, "uuid4", lambda: candidate)
    with pytest.raises(HTTPException) as error:
        service.create_preliminary_request(principal, payload)
    assert error.value.detail["code"] == "IDENTITY_COLLISION"
    assert facts(principal) == (1, 0, 0)
    with SessionLocal() as db:
        assert (db.get(Project, candidate).code, db.get(Project, candidate).name) == (
            "Legacy UUID",
            "Preserved",
        )


@pytest.mark.parametrize("rollback", [False, True])
def test_a21_get_during_flushed_uncommitted_post_is_read_only(principal, monkeypatch, rollback):
    payload = command()
    flushed, release = threading.Event(), threading.Event()
    original = service.receipt_dto

    def hold(db, receipt):
        result = original(db, receipt)
        flushed.set()
        assert release.wait(8)
        if rollback:
            raise RuntimeError("Synthetic rollback after all facts flushed")
        return result

    with monkeypatch.context() as patch:
        patch.setattr(service, "receipt_dto", hold)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(service.create_preliminary_request, principal, payload)
            try:
                assert flushed.wait(8)
                with pytest.raises(HTTPException) as error:
                    service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
                assert error.value.detail["code"] == "UNRESOLVED"
                assert facts(principal) == (0, 0, 0)
            finally:
                release.set()
            if rollback:
                with pytest.raises(HTTPException):
                    future.result(timeout=8)
            else:
                result, status = future.result(timeout=8)
                assert status == 201
    if rollback:
        with pytest.raises(HTTPException) as error:
            service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
        assert error.value.detail["code"] == "UNRESOLVED" and facts(principal) == (0, 0, 0)
    else:
        assert (
            service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)) == result
        )
        assert facts(principal) == (1, 1, 1)


def test_a13_database_aborted_commit_has_no_partial_facts(principal):
    payload = command()

    def abort(db):
        db.execute(text("SELECT 1/0"))

    event.listen(Session, "before_commit", abort)
    try:
        with pytest.raises(HTTPException) as error:
            service.create_preliminary_request(principal, payload)
        assert error.value.detail["code"] == "COMMIT_OUTCOME_UNKNOWN"
    finally:
        event.remove(Session, "before_commit", abort)
    assert facts(principal) == (0, 0, 0)
    with pytest.raises(HTTPException) as error:
        service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
    assert error.value.detail["code"] == "UNRESOLVED"
    assert service.create_preliminary_request(principal, payload)[1] == 201


def test_a16_concurrent_legacy_code_insert_wins_without_renaming(principal, monkeypatch):
    candidate, payload = uuid.uuid4(), command()
    with SessionLocal() as legacy:
        row = Project(
            organization_id=principal.organization_id,
            created_by=principal.actor_user_id,
            code=format(candidate.int, "039d"),
            name="Concurrent legacy",
        )
        legacy.add(row)
        legacy.flush()
        monkeypatch.setattr(service.uuid, "uuid4", lambda: candidate)
        with concurrent.futures.ThreadPoolExecutor() as pool:
            future = pool.submit(service.create_preliminary_request, principal, payload)
            try:
                with engine.connect() as observer:
                    for _ in range(200):
                        waiting = observer.scalar(
                            text(
                                "SELECT count(*) FROM pg_locks WHERE locktype='transactionid' "
                                "AND NOT granted AND pid IN (SELECT pid FROM pg_stat_activity "
                                "WHERE datname=current_database())"
                            )
                        )
                        if waiting:
                            break
                        observer.commit()
                        threading.Event().wait(0.01)
                    else:
                        pytest.fail("Concurrent unique-index waiter not observed")
            finally:
                legacy.commit()
            with pytest.raises(HTTPException) as error:
                future.result(timeout=8)
            assert error.value.detail["code"] == "IDENTITY_COLLISION"
        assert (row.name, row.code) == ("Concurrent legacy", format(candidate.int, "039d"))
    assert facts(principal) == (1, 0, 0)


def test_a10_rolled_back_actor_never_owns_another_actors_nonce(principal, monkeypatch):
    payload = command()
    with SessionLocal() as db:
        role_id = db.scalar(
            select(UserRole.role_id).where(UserRole.user_id == principal.actor_user_id)
        )
        actor = User(
            organization_id=principal.organization_id,
            email="other@example.invalid",
            full_name="Other synthetic",
        )
        db.add(actor)
        db.flush()
        db.add(UserRole(user_id=actor.id, role_id=role_id))
        now = datetime.now(timezone.utc)
        session = UserSession(
            user_id=actor.id,
            organization_id=principal.organization_id,
            access_token_hash=uuid.uuid4().hex * 2,
            access_expires_at=now + timedelta(hours=1),
            idle_expires_at=now + timedelta(hours=1),
            absolute_expires_at=now + timedelta(hours=2),
        )
        db.add(session)
        db.flush()
        other = service.Principal(principal.organization_id, actor.id, session.id)
        db.commit()

    def rollback(*_):
        raise RuntimeError("Synthetic rollback before binding")

    with monkeypatch.context() as patch:
        patch.setattr(service, "receipt_dto", rollback)
        with pytest.raises(HTTPException):
            service.create_preliminary_request(principal, payload)
    assert facts(principal) == (0, 0, 0)
    result, status = service.create_preliminary_request(other, payload)
    assert status == 201
    with pytest.raises(HTTPException) as error:
        service.recover_preliminary_request(principal, uuid.UUID(payload.request_id))
    assert error.value.detail["code"] == "UNRESOLVED" and result["project"]["id"] not in str(
        error.value.detail
    )
    own, status = service.create_preliminary_request(principal, payload)
    assert status == 201 and own["project"] != result["project"] and facts(principal) == (2, 2, 2)


@pytest.mark.parametrize("corruption", ["audit_payload", "audit_event", "project_code"])
def test_a30_mismatched_evidence_never_returns_committed(principal, corruption):
    payload = command()
    service.create_preliminary_request(principal, payload)
    with SessionLocal() as db:
        receipt = service.find_receipt(db, principal, uuid.UUID(payload.request_id))
        if corruption == "project_code":
            receipt.project_code = "0" * 39
        else:
            audit = db.get(AuditEvent, receipt.audit_event_id)
            if corruption == "audit_payload":
                audit.payload = {"request_id": "synthetic mismatch"}
            else:
                audit.event_name = "SyntheticMismatch"
        db.commit()
    for operation in (
        lambda: service.recover_preliminary_request(principal, uuid.UUID(payload.request_id)),
        lambda: service.create_preliminary_request(principal, payload),
    ):
        with pytest.raises(HTTPException) as error:
            operation()
        assert error.value.detail["code"] == "RECEIPT_INTEGRITY_ERROR"
    assert facts(principal) == (1, 1, 1)
