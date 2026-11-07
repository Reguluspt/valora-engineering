"""Deterministic offline safety and failure-recovery evidence; no credentials/inference."""

from copy import deepcopy
import json
import multiprocessing
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from codex_bridge.agent import Agent, FIXTURE_CONTENT, FakeExecutor, Result, invocation_manifest
from codex_bridge.offline import FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA, OfflineQueue, fixture_issue
from codex_bridge.schema import Policy, Rejected, canonical, parse_json, sign, validate
from codex_bridge.state import Journal, installation_lock
from codex_bridge.transport import Backoff, GitHubQueue, HTTPS, QueueFailure, Response, RESULT_MARKER


def lock_worker(directory, pipe):
    try:
        with installation_lock(directory):
            pipe.send("ACQUIRED")
    except Rejected:
        pipe.send("BLOCKED")
    finally:
        pipe.close()


class BridgeTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary.name)
        self.workspace = self.root / "fixture"
        self.workspace.mkdir()
        (self.workspace / "fixture.txt").write_bytes(FIXTURE_CONTENT)
        self.policy = Policy(self.workspace, FIXTURE_SHA)
        self.issue = fixture_issue(self.policy)
        self.queue = OfflineQueue(self.policy, [self.issue])
        self.executor = FakeExecutor()
        self.journal = Journal(self.root / "state")
        self.agent = self.make_agent()

    def tearDown(self):
        self.journal.close()
        self.temporary.cleanup()

    def make_agent(self, **kwargs):
        return Agent(self.policy, FIXTURE_KEY, self.queue, self.journal,
                     kwargs.pop("executor", self.executor), kwargs.pop("head", lambda: FIXTURE_SHA),
                     clock=kwargs.pop("clock", lambda: FIXTURE_NOW), **kwargs)

    def edit(self, **changes):
        body = json.loads(self.issue["body"])
        body.update(changes)
        body["signature"] = sign(body, FIXTURE_KEY)
        self.issue["body"] = canonical(body)
        self.queue.issues = [deepcopy(self.issue)]

    def state(self):
        return self.journal.db.execute("SELECT state FROM tasks").fetchall()

    def assert_no_secret(self, secret):
        dump = "\n".join(self.journal.db.iterdump()) + canonical(list(self.queue.results.values()))
        self.assertNotIn(secret, dump)

    def test_harmless_success_has_hash_evidence_and_no_raw_output(self):
        self.assertEqual(self.agent.once()["status"], "OFFLINE_CYCLE_COMPLETE")
        self.assertEqual(self.executor.calls, 1)
        self.assertEqual(self.state(), [("SUCCEEDED",)])
        self.assertEqual(len(self.queue.results), 1)
        evidence = json.loads(next(iter(self.queue.results.values())))
        self.assertEqual(evidence["evidence_mode"], "OFFLINE_FAKE_EXECUTOR")
        self.assertEqual(evidence["exit_code"], 0)
        self.assert_no_secret(FIXTURE_CONTENT.decode().strip())

    def test_control_issue_never_dispatches_even_with_valid_envelope(self):
        self.queue.issues = [fixture_issue(self.policy, 1)]
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [])

    def test_bogus_author_and_spoofed_label_do_not_authorize(self):
        self.queue.issues[0]["user"] = {"login": "Reguluspt", "id": 999}
        self.queue.issues[0]["labels"] = [{"name": "approved"}]
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_author_id_login_and_signed_issuer_must_all_match(self):
        repo = self.queue.repository()
        for field, value in [("user", {"id": self.policy.issuer_id, "login": "impostor"})]:
            issue = {**self.issue, field: value}
            with self.assertRaises(Rejected):
                validate(repo, issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.edit(issuer=999)
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_body_edit_cannot_borrow_owner_authorship(self):
        body = json.loads(self.queue.issues[0]["body"])
        body["nonce"] = "tampered-nonce-0001"
        self.queue.issues[0]["body"] = canonical(body)
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_comment_injection_is_not_used(self):
        self.queue.issues[0]["comment_payload"] = "powershell Remove-Item C:/ -Recurse; api_secret"
        self.queue.issues[0]["labels"] = [{"name": "danger-full-access"}]
        self.agent.once()
        self.assertEqual(self.executor.calls, 1)
        self.assert_no_secret("api_secret")

    def test_markdown_shell_prompt_and_unknown_fields_are_rejected(self):
        for raw in ["run powershell.exe", "```json\n{}\n```", '{"command":"whoami"}']:
            self.queue.issues[0]["body"] = raw
            self.agent.once()
        self.edit(command="whoami")
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_duplicate_json_keys_nonfinite_and_oversize_reject(self):
        for raw in ['{"a":1,"a":2}', '{"a":NaN}', "x" * 8193, "[" * 1500, "\ud800"]:
            with self.assertRaises(Rejected):
                parse_json(raw)

    def test_invalid_scope_machine_workspace_target_model_attempts(self):
        cases = {"approved_scope": ["host:write"], "machine_id": "other-host",
                 "workspace_id": "../../secrets", "target_repo": "Reguluspt/App",
                 "target_ref": "refs/heads/evil", "cost_policy": {"mode": "api"},
                 "max_attempts": 2, "schema_version": True, "lease_seconds": True,
                 "acceptance_checks": ["arbitrary-command"], "authority": "approved"}
        for field, value in cases.items():
            with self.subTest(field=field):
                self.issue = fixture_issue(self.policy)
                self.edit(**{field: value})
                self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_expired_future_and_excessive_ttl(self):
        for changes in [{"expires_at": "2020-01-01T00:00:00Z"},
                        {"created_at": "2030-01-01T00:00:00Z"},
                        {"expires_at": "2030-01-01T00:00:00Z"},
                        {"created_at": "2026-02-30T00:00:00Z"}]:
            self.issue = fixture_issue(self.policy)
            self.edit(**changes)
            self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_public_wrong_id_wrong_repo_pull_request_and_origin_block(self):
        repo = self.queue.repository()
        for changes in [{"private": False}, {"id": 99}, {"full_name": "Reguluspt/valora-engineering"}]:
            with self.assertRaises(Rejected):
                validate({**repo, **changes}, self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        for changes in [{"pull_request": {}}, {"state": "closed"}, {"url": "https://evil.invalid"}, {"number": True}]:
            with self.assertRaises(Rejected):
                validate(repo, {**self.issue, **changes}, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)

    def test_missing_authorization_key_fails_closed(self):
        self.agent.key = None
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)

    def test_nonce_idempotency_and_task_id_replay(self):
        self.agent.once()
        for field in ("nonce", "idempotency_key", "task_id"):
            body = json.loads(self.issue["body"])
            other = fixture_issue(self.policy, 3)
            second = json.loads(other["body"])
            second[field] = body[field]
            second["signature"] = sign(second, FIXTURE_KEY)
            other["body"] = canonical(second)
            self.queue.issues = [other]
            self.agent.once()
        self.assertEqual(self.executor.calls, 1)

    def test_same_issue_replay_across_reboot_never_runs_twice(self):
        self.agent.once()
        self.journal.close()
        self.journal = Journal(self.root / "state")
        self.make_agent().once()
        self.assertEqual(self.executor.calls, 1)

    def test_changed_sha_before_launch_blocks_reserved_task(self):
        heads = iter([FIXTURE_SHA, "a" * 40])
        self.make_agent(head=lambda: next(heads)).once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_changed_task_after_claim_blocks(self):
        original = self.queue.issue
        reads = [0]
        def fetch(number):
            reads[0] += 1
            issue = original(number)
            if reads[0] > 1:
                issue["state"] = "closed"
            return issue
        self.queue.issue = fetch
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_offline_before_claim_retries_after_reconnect(self):
        original = self.queue.repository
        self.queue.repository = lambda: (_ for _ in ()).throw(QueueFailure())
        self.assertEqual(self.agent.once()["status"], "BACKOFF")
        self.assertEqual(self.state(), [])
        self.queue.repository = original
        self.agent.once()
        self.assertEqual(self.executor.calls, 1)

    def test_offline_after_claim_is_uncertain_and_never_retried(self):
        original = self.queue.issue
        reads = [0]
        def fetch(number):
            reads[0] += 1
            if reads[0] == 2:
                raise QueueFailure()
            return original(number)
        self.queue.issue = fetch
        self.agent.once()
        self.queue.issue = original
        self.make_agent().once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_claimed_or_running_after_restart_becomes_blocked(self):
        task = validate(self.queue.repository(), self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.journal.reserve(task, FIXTURE_NOW)
        self.journal.start(task, FIXTURE_NOW)
        self.journal.close()
        self.journal = Journal(self.root / "state")
        self.make_agent().once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_expired_lease_cannot_start(self):
        task = validate(self.queue.repository(), self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.journal.reserve(task, FIXTURE_NOW)
        with self.assertRaises(Rejected):
            self.journal.start(task, FIXTURE_NOW + 31)

    def test_reservation_deadline_is_not_extended_at_start(self):
        task = validate(self.queue.repository(), self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.journal.reserve(task, FIXTURE_NOW)
        self.assertEqual(self.journal.start(task, FIXTURE_NOW + 20), FIXTURE_NOW + 30)

    def test_unlaunched_claim_is_not_automatically_retried_after_restart(self):
        task = validate(self.queue.repository(), self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.journal.reserve(task, FIXTURE_NOW)
        self.agent.once()
        self.assertEqual(self.executor.calls, 0)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_durable_active_claim_prevents_a_second_reservation(self):
        task = validate(self.queue.repository(), self.issue, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        other = fixture_issue(self.policy, 3)
        second = validate(self.queue.repository(), other, self.policy, FIXTURE_KEY, FIXTURE_NOW, FIXTURE_SHA)
        self.journal.reserve(task, FIXTURE_NOW)
        with self.assertRaises(Rejected):
            self.journal.reserve(second, FIXTURE_NOW)
        self.assertEqual(self.state(), [("CLAIMED",)])

    def test_result_publish_retry_never_reexecutes(self):
        original = self.queue.publish
        self.queue.publish = lambda *_: (_ for _ in ()).throw(QueueFailure())
        self.assertEqual(self.agent.once()["status"], "BACKOFF")
        self.assertEqual(len(self.journal.pending()), 1)
        self.queue.publish = original
        self.agent.once()
        self.assertEqual(self.executor.calls, 1)
        self.assertEqual(len(self.queue.results), 1)
        self.assertEqual(self.journal.pending(), [])

    def test_revoked_credential_stays_blocked_until_explicit_restart(self):
        original = self.queue.repository
        self.queue.repository = lambda: (_ for _ in ()).throw(QueueFailure(401))
        self.assertEqual(self.agent.once()["status"], "AUTH_BLOCKED")
        self.queue.repository = original
        self.assertEqual(self.agent.once()["status"], "AUTH_BLOCKED")
        self.assertEqual(self.executor.calls, 0)

    def test_stop_before_dispatch_and_while_poll_waiting(self):
        (self.journal.directory / "STOP").touch()
        self.assertEqual(self.agent.once()["status"], "STOPPED")
        self.assertEqual(self.executor.calls, 0)

    def test_foreground_loop_checks_stop_during_backoff(self):
        waits = []
        def wait(seconds):
            waits.append(seconds)
            (self.journal.directory / "STOP").touch()
        results = list(self.agent.run(2, wait))
        self.assertEqual(waits, [1])
        self.assertEqual(results[-1]["status"], "STOPPED")
        self.assertEqual(self.executor.calls, 1)

    def test_fixture_is_content_pinned_and_does_not_read_arbitrary_files(self):
        (self.workspace / "fixture.txt").write_bytes(b"PRIVATE_SYNTHETIC_CANARY")
        self.agent.once()
        self.assertEqual(self.state(), [("BLOCKED",)])
        self.assert_no_secret("PRIVATE_SYNTHETIC_CANARY")

    def test_stop_during_fake_execution_marks_cancelled(self):
        outer = self
        class StopExecutor:
            def execute(self, *args):
                (outer.journal.directory / "STOP").touch()
                return Result(0, FIXTURE_CONTENT)
        self.make_agent(executor=StopExecutor()).once()
        self.assertEqual(self.state(), [("CANCELLED",)])

    def test_deadline_and_backward_wall_clock_use_monotonic_hold(self):
        clock, mono = [FIXTURE_NOW], [10.0]
        class SlowExecutor:
            def execute(self, *args):
                clock[0] -= 100
                mono[0] += 31
                return Result(0, FIXTURE_CONTENT)
        self.make_agent(executor=SlowExecutor(), clock=lambda: clock[0], monotonic=lambda: mono[0]).once()
        self.assertEqual(self.state(), [("CANCELLED",)])

    def test_untrusted_output_exception_and_payload_secrets_never_logged(self):
        secret = "github_pat_SYNTHETIC_SECRET_MUST_NOT_LOG"
        class LeakyExecutor:
            def execute(self, *args):
                raise RuntimeError(secret)
        self.make_agent(executor=LeakyExecutor()).once()
        self.assert_no_secret(secret)
        self.assertEqual(self.state(), [("BLOCKED",)])

    def test_output_limit_and_digest_only_redact_small_secret(self):
        secret = "sk-SYNTHETIC_KEY_MUST_NOT_LOG"
        class LeakyExecutor:
            def execute(self, *args):
                return Result(0, secret.encode())
        self.make_agent(executor=LeakyExecutor()).once()
        self.assert_no_secret(secret)
        self.assertEqual(self.state(), [("FAILED",)])

    def test_oversized_output_is_not_stored(self):
        class BigExecutor:
            def execute(self, *args):
                return Result(0, b"SECRET" * 1000)
        self.make_agent(executor=BigExecutor()).once()
        self.assertEqual(self.state(), [("FAILED",)])
        self.assert_no_secret("SECRET")

    def test_capacity_reservation_is_atomic_and_fail_closed(self):
        self.journal.max_events = 2
        self.agent.once()
        self.assertEqual(self.state(), [])
        self.assertEqual(self.executor.calls, 0)

    def test_events_are_append_only(self):
        self.agent.once()
        for statement in ("DELETE FROM events", "UPDATE events SET reason='changed'"):
            with self.assertRaises(sqlite3.IntegrityError):
                self.journal.db.execute(statement)

    def test_os_lock_blocks_a_second_process(self):
        ctx = multiprocessing.get_context("spawn")
        parent, child = ctx.Pipe()
        with installation_lock(self.journal.directory):
            process = ctx.Process(target=lock_worker, args=(self.journal.directory, child))
            process.start()
            self.assertTrue(parent.poll(10))
            self.assertEqual(parent.recv(), "BLOCKED")
            process.join(10)
            self.assertEqual(process.exitcode, 0)
        parent.close()
        child.close()

    def test_invocation_manifest_is_disabled_restrictive_and_fixed(self):
        manifest = invocation_manifest(Path(sys.executable), self.policy)
        self.assertFalse(manifest["enabled"])
        self.assertFalse(manifest["shell"])
        self.assertIn("read-only", manifest["argv"])
        self.assertIn("--ignore-user-config", manifest["argv"])
        self.assertNotIn("danger-full-access", canonical(manifest))
        self.assertNotIn("--dangerously-bypass", canonical(manifest))


class TransportTests(unittest.TestCase):
    def setUp(self):
        self.policy = Policy(Path(tempfile.gettempdir()).resolve(), FIXTURE_SHA)

    def test_conditional_poll_skips_control_and_pull_requests(self):
        requests = []
        def request(method, url, headers, body):
            requests.append(headers)
            if "If-None-Match" in headers:
                return Response(304, {}, "")
            return Response(200, {"etag": '"synthetic"'}, canonical([
                {"number": 1}, {"number": 2}, {"number": 3, "pull_request": {}}]))
        queue = GitHubQueue(self.policy, request, 100)
        self.assertEqual(queue.poll(), [2])
        queue.acknowledge_poll()
        self.assertEqual(queue.poll(), [])
        self.assertEqual(requests[1]["If-None-Match"], '"synthetic"')

    def test_authoritative_issue_endpoint_does_not_read_comments(self):
        urls = []
        def request(method, url, headers, body):
            urls.append(url)
            return Response(200, {}, canonical({"number": 2}))
        GitHubQueue(self.policy, request, 100).issue(2)
        self.assertEqual(urls, [f"https://api.github.com/repos/{self.policy.queue}/issues/2"])

    def test_partial_success_post_is_reconciled_without_duplicate(self):
        comments, posts = [], []
        def request(method, url, headers, body):
            if method == "GET":
                return Response(200, {}, canonical(comments))
            posts.append(body)
            comments.append({"user": {"id": 100}, "body": json.loads(body)["body"]})
            raise QueueFailure()
        queue = GitHubQueue(self.policy, request, 100)
        with self.assertRaises(QueueFailure):
            queue.publish(2, '{"result_id":"synthetic"}')
        queue.publish(2, '{"result_id":"synthetic"}')
        self.assertEqual(len(posts), 1)

    def test_spoofed_result_comment_does_not_acknowledge_publication(self):
        methods = []
        def request(method, url, headers, body):
            methods.append(method)
            if method == "GET":
                return Response(200, {}, canonical([{"user": {"id": 999}, "body": RESULT_MARKER + "{}"}]))
            return Response(201, {}, "{}")
        GitHubQueue(self.policy, request, 100).publish(2, "{}")
        self.assertEqual(methods, ["GET", "POST"])

    def test_pagination_is_bounded_and_not_cached_from_page_one(self):
        calls = []
        def request(method, url, headers, body):
            calls.append(url)
            return Response(200, {"etag": "must-not-cache"}, canonical([{"number": i + 2} for i in range(100)]))
        queue = GitHubQueue(self.policy, request, 100)
        with self.assertRaises(QueueFailure):
            queue.poll()
        self.assertEqual(len(calls), 10)
        self.assertIsNone(queue.next_etag)

    def test_rate_limits_backoff_respect_retry_after(self):
        backoff = Backoff()
        self.assertEqual(backoff.failure(QueueFailure(429, "240"), FIXTURE_NOW), 240)
        self.assertEqual(backoff.failure(QueueFailure(), FIXTURE_NOW), 240)
        self.assertEqual(backoff.success(), 60)
        self.assertEqual(backoff.failure(QueueFailure(429, "7200"), FIXTURE_NOW), 7200)

    def test_transport_failure_never_exposes_exception_secrets(self):
        def request(*args):
            raise RuntimeError("Bearer_SYNTHETIC_SECRET")
        queue = GitHubQueue(self.policy, request, 100)
        with self.assertRaises(QueueFailure) as caught:
            queue.repository()
        self.assertNotIn("SYNTHETIC_SECRET", str(caught.exception))

    def test_http_adapter_rejects_outside_origin_without_request(self):
        adapter = HTTPS("PUBLIC_SYNTHETIC_NON_CREDENTIAL")
        for url in ["https://evil.invalid/", "https://api.github.com/repos/Reguluspt/valora-task-queue-evil",
                    "https://api.github.com/repos/Reguluspt/valora-task-queue/../../App",
                    "https://api.github.com/repos/Reguluspt/valora-task-queue/issues/1"]:
            with self.subTest(url=url), self.assertRaises(Rejected):
                adapter("GET", url, {}, None)

    def test_primary_rate_limit_and_secondary_limit_do_not_mean_revocation(self):
        for response in [Response(403, {"x-ratelimit-remaining": "0", "x-ratelimit-reset": str(int(FIXTURE_NOW + 900))}, "{}"),
                         Response(403, {}, '{"message":"secondary rate limit"}')]:
            queue = GitHubQueue(self.policy, lambda *args: response, 100)
            with self.assertRaises(QueueFailure) as caught:
                queue.repository()
            error = caught.exception
            self.assertTrue(error.retry_after or error.retry_at)
            self.assertGreaterEqual(Backoff().failure(error, FIXTURE_NOW), 120)

    def test_malformed_repository_or_mismatched_issue_fail_closed(self):
        queue = GitHubQueue(self.policy, lambda *args: Response(200, {}, "[]"), 100)
        with self.assertRaises(QueueFailure):
            queue.repository()
        queue.request = lambda *args: Response(200, {}, '{"number":999}')
        with self.assertRaises(QueueFailure):
            queue.issue(2)


if __name__ == "__main__":
    unittest.main()
