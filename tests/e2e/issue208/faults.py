"""Deterministic real-transaction fault/concurrency proofs; synthetic #208 only."""
import json
import os
import threading
import time
import uuid
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from unittest.mock import patch

from fastapi import HTTPException
from sqlalchemy import event, text
from sqlalchemy.orm import Session

from acceptance import seed, login, context, command, post
from app.api.auth import hash_token, get_cookie_keys, terminate_session_safely
from app.core.config import get_settings
from app.db import SessionLocal
from app.modules.document_workspace.application import quotation_document_import_service as service
from app.modules.document_workspace.domain.document_blob_store import CreateImmutableResult, CreateImmutableStatus, ObjectObservation, ObjectObservationStatus
from app.modules.document_workspace.infrastructure.document_blob_store_factory import build_document_blob_store
from app.modules.document_workspace.quotation_document_import_schemas import ImportCommand, RecoverCommand, validate_original
from app.modules.project_master_data.models import UserSession


def invocation(f, client, payload, content, store=None, recovery_version=None):
    with SessionLocal() as db:
        session_id = db.query(UserSession.id).filter_by(access_token_hash=hash_token(client.cookies[get_cookie_keys()[0]])).scalar()
    cls = RecoverCommand if recovery_version is not None else ImportCommand
    if recovery_version is not None:
        payload = dict(payload, expected_storage_state_version=recovery_version)
    return dict(org_id=f["org_id"], project_id=f["project_id"], actor_id=f["actor_id"], session_id=session_id,
        command=cls.model_validate_json(json.dumps(payload)), original=validate_original("synthetic.txt", "text/plain", content),
        blob_store=store or build_document_blob_store(get_settings()), recover=recovery_version is not None)


def counts(f):
    with SessionLocal() as db:
        result = {table: db.scalar(text(f"select count(*) from {table} where project_id=:id"), {"id": f["project_id"]})
            for table in ("document_revisions", "storage_object_bindings", "quotation_document_import_receipts", "quotation_document_import_requests")}
        result["version"] = db.scalar(text("select row_version from projects where id=:id"), {"id": f["project_id"]})
        result["audit"] = db.scalar(text("select count(*) from audit_events where organization_id=:id and event_name='QUOTATION_DOCUMENT_IMPORTED'"), {"id": f["org_id"]})
        return result


def assert_unpublished(test, f):
    rows = counts(f)
    test.assertEqual([rows[t] for t in ("document_revisions", "storage_object_bindings", "quotation_document_import_receipts", "audit")], [0, 0, 0, 0])
    test.assertEqual(rows["version"], 1)
    with SessionLocal() as db:
        test.assertEqual(db.scalar(text("select count(*) from document_storage_execution_events e join quotation_document_import_requests q on q.execution_intent_id=e.execution_intent_id where q.project_id=:id and e.event_code='FINALIZED'"), {"id": f["project_id"]}), 0)
        test.assertEqual(db.scalar(text("select count(*) from audit_events where organization_id=:id and event_name='DOCUMENT_STORAGE_REVISION_FINALIZED'"), {"id": f["org_id"]}), 0)


class Store:
    provider_kind = "local"

    def __init__(self, after_create=None, unknown=False, absent=False):
        self.real = build_document_blob_store(get_settings())
        self.after_create, self.unknown, self.absent = after_create, unknown, absent
        self.creates = 0

    def __getattr__(self, name):
        return getattr(self.real, name)

    async def create_immutable(self, **kwargs):
        self.creates += 1
        if self.absent:
            return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN)
        result = await self.real.create_immutable(**kwargs)
        if self.after_create:
            self.after_create(kwargs["object_key"])
        return CreateImmutableResult(CreateImmutableStatus.OUTCOME_UNKNOWN) if self.unknown else result


class Faults(unittest.TestCase):
    def test_preparation_callback_failure_leaves_no_document_intent_envelope_or_object(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            store = Store()
            original = service.log_audit_event
            def fail(*a, **kw):
                result = original(*a, **kw)
                if kw.get("event_name") == "QUOTATION_DOCUMENT_IMPORT_PREPARED":
                    raise RuntimeError("Synthetic preparation callback failure")
                return result
            with patch.object(service, "log_audit_event", fail), self.assertRaises(RuntimeError):
                service.import_original(**invocation(f, client, payload, b"synthetic", store))
            assert_unpublished(self, f)
            with SessionLocal() as db:
                for table in ("document_records", "document_storage_execution_intents", "quotation_document_import_requests"):
                    self.assertEqual(db.scalar(text(f"select count(*) from {table} where project_id=:id"), {"id": f["project_id"]}), 0)
            self.assertEqual(store.creates, 0)

    def test_postgresql_leap_day_policy_fixture(self):
        from datetime import datetime
        t = datetime.fromisoformat("2028-02-29T12:34:56.123456+00:00")
        with SessionLocal() as db:
            floor = db.scalar(text("select ((cast(:t as timestamptz) at time zone 'UTC') + interval '10 years') at time zone 'UTC'"), {"t": t})
        self.assertEqual(floor, service.ten_year_floor(t))
        self.assertEqual(service.stamp(floor), "2038-02-28T12:34:56.123456Z")

    def test_final_transaction_time_precedes_observed_project_lock_wait_and_uses_utc(self):
        from datetime import datetime
        f = seed()
        created, resume, waiting = threading.Event(), threading.Event(), threading.Event()
        times, worker_pids = [], []
        def pause(_key):
            created.set()
            assert resume.wait(10)
        original_project, original_floor, original_limits = service._project, service.ten_year_floor, service._limits
        project_locks = 0
        def project(db, **kw):
            nonlocal project_locks
            if kw.get("lock"):
                project_locks += 1
                if project_locks == 2:
                    worker_pids.append(db.scalar(text("select pg_backend_pid()")))
                    waiting.set()
            return original_project(db, **kw)
        def floor(t):
            if not times:
                times.append(t)
            return original_floor(t)
        def limits(db):
            original_limits(db)
            db.execute(text("SET LOCAL TIMEZONE='Pacific/Kiritimati'"))
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            args = invocation(f, client, payload, b"synthetic", Store(after_create=pause))
            with patch.object(service, "_project", project), patch.object(service, "ten_year_floor", floor), patch.object(service, "_limits", limits), ThreadPoolExecutor(max_workers=1) as pool:
                future = pool.submit(service.import_original, **args)
                self.assertTrue(created.wait(10))
                with SessionLocal() as holder:
                    holder_pid = holder.scalar(text("select pg_backend_pid()"))
                    holder.execute(text("select id from projects where id=:id for update"), {"id": f["project_id"]})
                    resume.set()
                    self.assertTrue(waiting.wait(5))
                    blockers = []
                    deadline = time.monotonic() + 2
                    while holder_pid not in blockers and time.monotonic() < deadline:
                        with SessionLocal() as observer:
                            blockers = observer.scalar(text("select pg_blocking_pids(:pid)"), {"pid": worker_pids[0]})
                    self.assertIn(holder_pid, blockers)
                    release_time = holder.scalar(text("select clock_timestamp()"))
                    holder.commit()
                result, _ = future.result(timeout=15)
            finalized = datetime.fromisoformat(result["finalized_at"].replace("Z", "+00:00"))
            self.assertEqual(finalized, times[0])
            self.assertLess(finalized, release_time)
            self.assertEqual(result["minimum_retain_until"], service.stamp(original_floor(finalized)))

    def test_local_corruption_ambiguity_and_outage_never_publish_or_blind_retry(self):
        for fault in ("corrupt", "ambiguous", "unavailable"):
            with self.subTest(fault=fault):
                f = seed()
                class FaultStore(Store):
                    async def create_immutable(self, **kw):
                        result = await super().create_immutable(**kw)
                        if fault == "corrupt":
                            (self.real._root / "objects" / kw["object_key"]).write_bytes(b"damaged synthetic candidate")
                        return result
                    async def observe(self, **kw):
                        if fault in ("ambiguous", "unavailable"):
                            return ObjectObservation(ObjectObservationStatus.AMBIGUOUS if fault == "ambiguous" else ObjectObservationStatus.UNAVAILABLE)
                        return await self.real.observe(**kw)
                store = FaultStore()
                with closing(login(f)) as client:
                    payload = command(context(client, f), b"synthetic")
                    result, _ = service.import_original(**invocation(f, client, payload, b"synthetic", store))
                    self.assertEqual(result["outcome"], "pending")
                    assert_unpublished(self, f)
                    self.assertEqual(store.creates, 1)
                    if fault != "unavailable":
                        self.assertFalse(result["recovery_permitted"])

    def test_privileged_same_byte_replacement_after_final_proof_is_unavailable_after_commit(self):
        f = seed()
        class GapStore(Store):
            observations = 0
            async def observe(self, **kw):
                result = await self.real.observe(**kw)
                self.observations += 1
                if self.observations == 3:
                    original = self.real._root / "objects" / kw["object_key"]
                    replacement = original.with_name(uuid.uuid4().hex + ".replacement")
                    replacement.write_bytes(original.read_bytes())
                    os.replace(replacement, original)
                return result
        with closing(login(f)) as client:
            result, _ = service.import_original(**invocation(f, client, command(context(client, f), b"synthetic"), b"synthetic", GapStore()))
            self.assertEqual(result["outcome"], "finalized")
            self.assertFalse(result["source"]["available"])
            self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)

    def test_finalized_cleanup_is_denied_before_any_provider_deletion(self):
        from app.modules.project_master_data.models import User
        f = seed()
        class NoDeleteStore(Store):
            async def delete_uncommitted_or_expire(self, **_kw):
                raise AssertionError("Finalized source must never reach deletion")
        store = NoDeleteStore()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            result, _ = service.import_original(**invocation(f, client, payload, b"synthetic", store))
            with SessionLocal() as db:
                actor = db.get(User, f["actor_id"])
                with self.assertRaises(HTTPException) as error:
                    service.run_storage(service.storage.cleanup_uncommitted_candidate(db, actor=actor, organization_id=f["org_id"],
                        intent_id=uuid.UUID(result["intent_id"]), blob_store=store, cleanup_policy_code="synthetic-orphan-only",
                        policy_allows_cleanup=True, legal_hold_active=False))
                self.assertEqual(error.exception.status_code, 409)
            self.assertFalse(result["purge_allowed"])
            self.assertEqual(result["retention_disposition"], "NO_PURGE_EXTENSION_UNCERTIFIED")

    def test_immutable_records_policy_replay_and_post_commit_source_loss(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic original\r\n")
            args = invocation(f, client, payload, b"synthetic original\r\n")
            result, _ = service.import_original(**args)
            original_receipt = result["historical_receipt"]
            with patch.object(service, "POLICY", {**service.POLICY, "unapproved_change": True}):
                replay, created = service.import_original(**args)
                self.assertFalse(created)
                self.assertEqual(replay["historical_receipt"], original_receipt)
            for table, row_id, field in (("quotation_document_import_requests", result["request_id"], "byte_length"),
                    ("quotation_document_import_receipts", result["receipt_id"], "byte_length"),
                    ("storage_object_bindings", result["binding_id"], "byte_length"),
                    ("document_revisions", result["revision_id"], "document_revision")):
                with self.subTest(table=table), SessionLocal() as db:
                    with self.assertRaises(Exception):
                        db.execute(text(f"update {table} set {field}={field}+1 where id=:id"), {"id": row_id})
                        db.commit()
                    db.rollback()
            with SessionLocal() as db:
                key = db.scalar(text("select object_key from storage_object_bindings where id=:id"), {"id": result["binding_id"]})
            path = args["blob_store"]._root / "objects" / key
            self.assertEqual(path.read_bytes(), b"synthetic original\r\n")
            path.unlink()
            status = service.read_status(**{k: v for k, v in args.items() if k in {"org_id", "project_id", "actor_id", "session_id", "blob_store"}}, command_id=payload["command_id"])
            self.assertEqual(status["outcome"], "finalized")
            self.assertFalse(status["source"]["available"])
            self.assertEqual(status["historical_receipt"], original_receipt)
            self.assertFalse(path.exists())

    def test_crashes_before_candidate_and_after_candidate_preserve_envelope(self):
        for boundary in ("before", "after"):
            with self.subTest(boundary=boundary):
                f = seed()
                with closing(login(f)) as client:
                    payload = command(context(client, f), b"synthetic")
                    args = invocation(f, client, payload, b"synthetic")
                    original = service.storage.record_storage_candidate
                    def crash(*a, **kw):
                        if boundary == "after":
                            original(*a, **kw)
                        raise RuntimeError("Synthetic process loss")
                    with patch.object(service.storage, "record_storage_candidate", crash):
                        with self.assertRaises(RuntimeError):
                            service.import_original(**args)
                    assert_unpublished(self, f)
                    status = service.read_status(**{k: v for k, v in args.items() if k in {"org_id", "project_id", "actor_id", "session_id", "blob_store"}}, command_id=payload["command_id"])
                    self.assertEqual(status["storage_state"], "PREPARED" if boundary == "before" else "CANDIDATE_GENERATED")
                    with patch.object(service, "POLICY", {**service.POLICY, "unapproved_change": True}):
                        with self.assertRaises(HTTPException):
                            service.import_original(**invocation(f, client, payload, b"synthetic", recovery_version=status["storage_state_version"]))
                    with patch.object(service, "TARGET", {**service.TARGET, "storage_profile_id": "unapproved-profile"}):
                        blocked_store = Store()
                        with self.assertRaises(HTTPException):
                            service.import_original(**invocation(f, client, payload, b"synthetic", blocked_store, status["storage_state_version"]))
                        self.assertEqual(blocked_store.creates, 0)
                    recovered, _ = service.import_original(**invocation(f, client, payload, b"synthetic", recovery_version=status["storage_state_version"]))
                    self.assertEqual(recovered["intent_id"], status["intent_id"])
                    self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)

    def test_same_command_concurrent_finalization_replays_original_receipt(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            args = invocation(f, client, payload, b"synthetic")
            with patch.object(service.storage, "finalize_storage_revision", side_effect=RuntimeError("Synthetic crash before finalization")):
                with self.assertRaises(RuntimeError):
                    service.import_original(**args)
            with SessionLocal() as db:
                state_version = db.scalar(text("select s.state_version from document_storage_execution_states s join quotation_document_import_requests q on q.execution_intent_id=s.execution_intent_id where q.project_id=:id"), {"id": f["project_id"]})
            barrier = threading.Barrier(2)
            class SynchronizedStore(Store):
                def __init__(self):
                    super().__init__()
                    self.first = threading.local()
                async def observe(self, **kw):
                    observation = await self.real.observe(**kw)
                    if not getattr(self.first, "seen", False):
                        self.first.seen = True
                        barrier.wait(timeout=15)
                    return observation
            store = SynchronizedStore()
            args = invocation(f, client, payload, b"synthetic", store, state_version)
            with ThreadPoolExecutor(max_workers=2) as pool:
                futures = [pool.submit(service.import_original, **args) for _ in range(2)]
                results = [future.result(timeout=30) for future in futures]
            self.assertEqual(results[0][0]["historical_receipt"], results[1][0]["historical_receipt"])
            self.assertCountEqual([result[1] for result in results], [True, False])
            self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)
            self.assertEqual(counts(f)["version"], 2)

    def test_provider_and_full_resolver_never_run_under_caller_locks(self):
        f = seed()
        held = threading.local()
        final_locks = []
        def locked(_connection, _cursor, statement, *_args):
            if "transaction_timestamp()" in statement:
                held.final = True
                final_locks.clear()
            if "FOR UPDATE" in statement or "FOR SHARE" in statement:
                held.value = True
                if getattr(held, "final", False):
                    final_locks.append(" ".join(statement.split()))
        def unlocked(_session):
            held.value = False
            held.final = False
        class ObservedStore(Store):
            async def create_immutable(self, **kw):
                self_test.assertFalse(getattr(held, "value", False))
                return await super().create_immutable(**kw)
            async def observe(self, **kw):
                self_test.assertFalse(getattr(held, "value", False))
                return await self.real.observe(**kw)
            async def read_verified(self, **kw):
                self_test.assertFalse(getattr(held, "value", False))
                return await self.real.read_verified(**kw)
            async def verify_checksum(self, **kw):
                self_test.assertFalse(getattr(held, "value", False))
                return await self.real.verify_checksum(**kw)
        self_test = self
        original = service.resolve_authority
        def resolve(*a, **kw):
            self.assertFalse(getattr(held, "value", False))
            return original(*a, **kw)
        event.listen(service.engine, "before_cursor_execute", locked)
        event.listen(Session, "after_commit", unlocked)
        event.listen(Session, "after_rollback", unlocked)
        try:
            with closing(login(f)) as client, patch.object(service, "resolve_authority", resolve):
                payload = command(context(client, f), b"synthetic")
                result, _ = service.import_original(**invocation(f, client, payload, b"synthetic", ObservedStore()))
                self.assertEqual(result["outcome"], "finalized")
                self.assertIn("FROM projects", final_locks[0])
                tables = ("organization_profiles", "users", "user_sessions", "user_roles", "roles", "document_storage_execution_states")
                order = [next(i for i, sql in enumerate(final_locks) if f"FROM {table} " in sql) for table in tables]
                self.assertEqual(order, sorted(order))
        finally:
            event.remove(service.engine, "before_cursor_execute", locked)
            event.remove(Session, "after_commit", unlocked)
            event.remove(Session, "after_rollback", unlocked)

    def test_guard_winner_blocks_revocation_and_role_writers_until_commit(self):
        for kind in ("session", "role", "grant"):
            with self.subTest(kind=kind):
                self._guard_winner(kind)

    def _guard_winner(self, kind):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            args = invocation(f, client, payload, b"synthetic")
            captured = threading.Event()
            release = threading.Event()
            writer_started = threading.Event()
            writer_done = threading.Event()
            calls = 0
            writer_pids, importer_pids = [], []
            original = service._actor
            def actor(*a, **kw):
                nonlocal calls
                result = original(*a, **kw)
                if kw.get("lock"):
                    calls += 1
                    if calls == 2:
                        importer_pids.append(a[0].scalar(text("select pg_backend_pid()")))
                        captured.set()
                        assert release.wait(10)
                return result
            def revoke():
                with SessionLocal() as db:
                    db.execute(text("SET LOCAL lock_timeout='10s'"))
                    session = db.get(UserSession, args["session_id"])
                    writer_pids.append(db.scalar(text("select pg_backend_pid()")))
                    writer_started.set()
                    if kind == "session":
                        terminate_session_safely(db=db, session=session, status="revoked", reason="Synthetic concurrent revocation", correlation_id=str(uuid.uuid4()))
                    elif kind == "role":
                        db.execute(text("update roles set permissions='[]'::json where id=:id"), {"id": f["role_id"]})
                    else:
                        db.execute(text("update user_roles set is_active=false where id=:id"), {"id": f["grant_id"]})
                    db.commit()
                writer_done.set()
            with patch.object(service, "_actor", actor), ThreadPoolExecutor(max_workers=2) as pool:
                importing = pool.submit(service.import_original, **args)
                self.assertTrue(captured.wait(10))
                revoking = pool.submit(revoke)
                self.assertTrue(writer_started.wait(5))
                waits = 0
                deadline = time.monotonic() + 3
                while not waits and time.monotonic() < deadline:
                    with SessionLocal() as db:
                        waits = int(importer_pids[0] in db.scalar(text("select pg_blocking_pids(:pid)"), {"pid": writer_pids[0]}))
                self.assertGreater(waits, 0)
                self.assertFalse(writer_done.is_set())
                release.set()
                try:
                    importing.result(timeout=15)
                except HTTPException as error:
                    self.assertEqual(error.status_code, 403)
                revoking.result(timeout=15)
            self.assertTrue(writer_done.is_set())
            self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)
            if kind != "session":
                with SessionLocal() as db:
                    db.execute(text("update roles set permissions='[\"project:read\",\"project:update\"]'::json where id=:id"), {"id": f["role_id"]})
                    db.execute(text("update user_roles set is_active=true where id=:id"), {"id": f["grant_id"]})
                    db.commit()
            with closing(login(f)) as restored:
                result = restored.get(f'/api/v1/projects/{f["project_id"]}/quotation-documents/import-receipts/{payload["command_id"]}')
                self.assertEqual(result.status_code, 200, result.text)
                self.assertEqual(result.json()["outcome"], "finalized")

    def test_denial_scope_and_stale_before_preparation(self):
        f = seed(False)
        with closing(login(f)) as client:
            ctx = context(client, f)
            self.assertFalse(ctx["can_import"])
            r = post(client, f, command(ctx, b"synthetic"), b"synthetic")
            self.assertEqual(r.status_code, 403)
            assert_unpublished(self, f)
        f = seed()
        with closing(login(f)) as client:
            ctx = context(client, f)
            payload = command(ctx, b"synthetic")
            payload["expected_case_version"] = "0" * 64
            r = post(client, f, payload, b"synthetic")
            self.assertEqual(r.status_code, 409)
            self.assertEqual(counts(f)["quotation_document_import_requests"], 0)
            other = seed()
            r = post(client, other, command(ctx, b"synthetic"), b"synthetic")
            self.assertEqual(r.status_code, 404)
            assert_unpublished(self, other)

    def test_revocations_and_project_cas_during_io(self):
        mutations = {
            "user": "update users set status='inactive' where id=:actor_id",
            "org": "update organization_profiles set status='inactive' where id=:org_id",
            "role": "update roles set permissions='[\"project:read\"]'::json where id=:role_id",
            "grant": "update user_roles set is_active=false where id=:grant_id",
            "session": "update user_sessions set status='revoked',revoked_at=clock_timestamp() where user_id=:actor_id",
            "expiry": "update user_sessions set access_expires_at=clock_timestamp()-interval '1 second' where user_id=:actor_id",
            "project": "update projects set status='archived' where id=:project_id",
            "cas": "update projects set row_version=row_version+1 where id=:project_id",
        }
        for name, sql in mutations.items():
            with self.subTest(name=name):
                f = seed()
                with closing(login(f)) as client:
                    ctx = context(client, f)
                    def revoke(_):
                        with SessionLocal() as db:
                            db.execute(text(sql), f)
                            db.commit()
                    args = invocation(f, client, command(ctx, b"synthetic"), b"synthetic", Store(after_create=revoke))
                    with self.assertRaises(HTTPException) as error:
                        service.import_original(**args)
                    self.assertIn(error.exception.status_code, (403, 409))
                    rows = counts(f)
                    self.assertEqual([rows[t] for t in ("document_revisions", "storage_object_bindings", "quotation_document_import_receipts", "audit")], [0, 0, 0, 0])

    def test_callback_failure_rolls_back_and_same_intent_recovers(self):
        f = seed()
        with closing(login(f)) as client:
            ctx = context(client, f)
            payload = command(ctx, b"synthetic")
            store = Store()
            args = invocation(f, client, payload, b"synthetic", store)
            original = service.log_audit_event
            def fail_after_audit(*args, **kwargs):
                result = original(*args, **kwargs)
                if kwargs.get("event_name") == "QUOTATION_DOCUMENT_IMPORTED":
                    raise RuntimeError("Synthetic fault after milestone audit flush")
                return result
            with patch.object(service, "log_audit_event", fail_after_audit):
                with self.assertRaises(RuntimeError):
                    service.import_original(**args)
            assert_unpublished(self, f)
            with SessionLocal() as db:
                state = db.execute(text("select s.state_version,s.current_state,q.execution_intent_id from quotation_document_import_requests q join document_storage_execution_states s on s.execution_intent_id=q.execution_intent_id where q.project_id=:id"), {"id": f["project_id"]}).one()
            self.assertEqual(state[1], "OBJECT_VERIFIED")
            result, _ = service.import_original(**invocation(f, client, payload, b"synthetic", store, state[0]))
            self.assertEqual(result["intent_id"], str(state[2]))
            self.assertEqual(result["outcome"], "finalized")
            self.assertEqual(store.creates, 1)

    def test_actual_commit_failure_is_atomic(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            with SessionLocal() as db:
                db.execute(text("""CREATE FUNCTION issue208_fail_commit() RETURNS trigger LANGUAGE plpgsql AS $$
                    BEGIN RAISE EXCEPTION 'Synthetic deferred commit failure'; END; $$"""))
                db.execute(text(f"""CREATE CONSTRAINT TRIGGER issue208_fail_commit AFTER INSERT ON quotation_document_import_receipts
                    DEFERRABLE INITIALLY DEFERRED FOR EACH ROW WHEN (NEW.project_id = '{f['project_id']}'::uuid)
                    EXECUTE FUNCTION issue208_fail_commit()"""))
                db.commit()
            try:
                with self.assertRaises(Exception) as error:
                    service.import_original(**invocation(f, client, payload, b"synthetic"))
                self.assertIn("Synthetic deferred commit failure", str(error.exception))
                assert_unpublished(self, f)
                self.assertEqual(counts(f)["quotation_document_import_requests"], 1)
            finally:
                with SessionLocal() as db:
                    db.execute(text("DROP TRIGGER issue208_fail_commit ON quotation_document_import_receipts"))
                    db.execute(text("DROP FUNCTION issue208_fail_commit()"))
                    db.commit()

    def test_two_original_commands_one_project_cas_winner(self):
        f = seed()
        with closing(login(f)) as client:
            ctx = context(client, f)
            barrier = threading.Barrier(2)
            stores = [Store(after_create=lambda _: barrier.wait(timeout=15)) for _ in range(2)]
            args = [invocation(f, client, command(ctx, b"synthetic"), b"synthetic", s) for s in stores]
            def run(arg):
                try:
                    return service.import_original(**arg)[0]["outcome"]
                except HTTPException as error:
                    return error.status_code
            with ThreadPoolExecutor(max_workers=2) as pool:
                results = list(pool.map(run, args))
            self.assertCountEqual(results, ["finalized", 409])
            rows = counts(f)
            self.assertEqual(rows["quotation_document_import_requests"], 2)
            self.assertEqual(rows["quotation_document_import_receipts"], 1)
            self.assertEqual(rows["audit"], 1)
            self.assertEqual(rows["version"], 2)

    def test_lost_create_observes_same_key_and_unknown_absence_waits_for_human(self):
        for absent in (False, True):
            with self.subTest(absent=absent):
                f = seed()
                with closing(login(f)) as client:
                    payload = command(context(client, f), b"synthetic")
                    store = Store(unknown=True, absent=absent)
                    result, _ = service.import_original(**invocation(f, client, payload, b"synthetic", store))
                    self.assertEqual(result["outcome"], "pending" if absent else "finalized")
                    self.assertEqual(store.creates, 1)
                    if absent:
                        assert_unpublished(self, f)
                        store.absent = False
                        recovered, _ = service.import_original(**invocation(f, client, payload, b"synthetic", store, result["storage_state_version"]))
                        self.assertEqual(result["intent_id"], recovered["intent_id"])
                        self.assertEqual(recovered["outcome"], "finalized")


if __name__ == "__main__":
    assert os.environ["POSTGRES_DB"] == "valora_issue208"
    unittest.main(verbosity=2)
