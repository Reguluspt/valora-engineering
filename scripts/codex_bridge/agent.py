"""One-task offline dispatcher. There is no Codex process launcher in P1."""

from dataclasses import dataclass
import hashlib
from pathlib import Path
import time

from .schema import Policy, Rejected, validate
from .state import installation_lock
from .transport import Backoff, QueueFailure

MAX_OUTPUT = 4096
FIXTURE_CONTENT = b"VALORA bridge harmless offline fixture\n"


@dataclass(frozen=True)
class Result:
    exit_code: int
    output: bytes


class FakeExecutor:
    """Only reads the fixed fixture; never starts a subprocess or inference."""
    def __init__(self):
        self.calls = 0

    def execute(self, policy, deadline, cancelled):
        if cancelled():
            raise InterruptedError()
        fixture = policy.workspace / "fixture.txt"
        if fixture.is_symlink() or fixture.resolve().parent != policy.workspace.resolve():
            raise Rejected("FIXTURE_PATH")
        with fixture.open("rb") as handle:
            output = handle.read(MAX_OUTPUT + 1)
        if output != FIXTURE_CONTENT:
            raise Rejected("FIXTURE_CONTENT")
        self.calls += 1
        return Result(0, output)


def invocation_manifest(binary, policy):
    binary = Path(binary)
    if not binary.is_absolute() or not policy.workspace.is_absolute():
        raise Rejected("INVOCATION_PATH")
    return {
        "enabled": False, "gate": "P2_BLOCKED", "shell": False,
        "argv": [str(binary), "exec", "--ignore-user-config", "--sandbox", "read-only",
                 "--json", "--ephemeral", "--cd", str(policy.workspace),
                 "-c", 'approval_policy="never"', "-c", 'windows.sandbox="mxc"',
                 "Read only fixture.txt. Return its SHA-256. Do not use tools outside this fixture."],
        "environment_policy": "allowlist; no GitHub PAT, issuer key, provider API keys or inherited MCP",
        "requires": ["scoped_credential", "authorized_signer", "effective_sandbox",
                     "approved_model_budget", "process_tree_cancellation", "independent_PM_gate"],
    }


class Agent:
    def __init__(self, policy: Policy, key, queue, journal, executor, head,
                 clock=time.time, monotonic=time.monotonic):
        self.policy, self.key, self.queue, self.journal = policy, key, queue, journal
        self.executor, self.head, self.clock, self.monotonic = executor, head, clock, monotonic
        self.backoff = Backoff()
        self.auth_blocked = False

    def stopped(self):
        return (self.journal.directory / "STOP").exists()

    def flush(self):
        for result_id, number, body in self.journal.pending():
            if self.stopped():
                return
            self.queue.publish(number, body)
            self.journal.delivered(result_id, self.clock())

    def dispatch(self, number, repo):
        task = None
        try:
            issue = self.queue.issue(number)
            task = validate(repo, issue, self.policy, self.key, self.clock(), self.head())
            if self.stopped():
                return
            self.journal.reserve(task, self.clock())
        except Rejected as error:
            # Codes originate only in the validator/journal, never Issue contents.
            self.journal.reject(self.clock(), str(error))
            return
        try:
            current = validate(self.queue.repository(), self.queue.issue(number), self.policy,
                               self.key, self.clock(), self.head())
            if current != task:
                raise Rejected("TASK_CHANGED")
            if self.stopped():
                self.journal.finish(task.task_key, "CANCELLED", self.clock(), "KILL_SWITCH")
                return
            started = self.clock()
            lease_until = self.journal.start(task, started)
            deadline = min(task.expires, lease_until)
            mono_deadline = self.monotonic() + min(task.lease_seconds, max(0, deadline - started))
            result = self.executor.execute(self.policy, deadline, self.stopped)
            ended = self.clock()
            if self.stopped():
                self.journal.finish(task.task_key, "CANCELLED", ended, "KILL_SWITCH")
            elif ended >= deadline or self.monotonic() >= mono_deadline:
                self.journal.finish(task.task_key, "CANCELLED", ended, "TIMEOUT")
            elif type(result.exit_code) is not int or not -255 <= result.exit_code <= 255 or not isinstance(result.output, bytes) or len(result.output) > MAX_OUTPUT:
                self.journal.finish(task.task_key, "FAILED", ended, "OUTPUT_LIMIT")
            else:
                digest = hashlib.sha256(result.output).hexdigest()
                success = result.exit_code == 0 and digest == hashlib.sha256(FIXTURE_CONTENT).hexdigest()
                self.journal.finish(task.task_key, "SUCCEEDED" if success else "FAILED", ended,
                                    "FIXTURE_VERIFIED" if success else "FIXTURE_FAILED", result.exit_code, digest)
        except QueueFailure:
            self.journal.finish(task.task_key, "BLOCKED", self.clock(), "QUEUE_UNAVAILABLE_AFTER_CLAIM")
            raise
        except InterruptedError:
            self.journal.finish(task.task_key, "CANCELLED", self.clock(), "KILL_SWITCH")
        except Exception:
            self.journal.finish(task.task_key, "BLOCKED", self.clock(), "EXECUTION_UNCERTAIN")

    def once(self):
        with installation_lock(self.journal.directory):
            self.journal.recover(self.clock())
            if self.stopped():
                return {"status": "STOPPED", "next_poll_seconds": 60}
            if self.auth_blocked:
                return {"status": "AUTH_BLOCKED", "next_poll_seconds": 3600}
            try:
                repo = self.queue.repository()
                if repo.get("id") != self.policy.queue_id or repo.get("private") is not True or repo.get("full_name") != self.policy.queue:
                    raise Rejected("QUEUE_IDENTITY")
                self.flush()
                for number in self.queue.poll():
                    if self.stopped():
                        break
                    self.dispatch(number, repo)
                self.queue.acknowledge_poll()
                self.flush()
                return {"status": "OFFLINE_CYCLE_COMPLETE", "next_poll_seconds": self.backoff.success()}
            except QueueFailure as error:
                self.queue.retry_poll()
                self.auth_blocked = error.status in {401, 404} or (error.status == 403 and not error.retry_after and error.retry_at is None)
                self.journal.reject(self.clock(), "AUTH_BLOCKED" if self.auth_blocked else "QUEUE_UNAVAILABLE")
                return {"status": "AUTH_BLOCKED" if self.auth_blocked else "BACKOFF",
                        "next_poll_seconds": self.backoff.failure(error, self.clock())}
            except Rejected:
                self.journal.reject(self.clock())
                return {"status": "BLOCKED", "next_poll_seconds": 3600}

    def run(self, cycles, wait=time.sleep):
        """Bounded foreground polling, checking STOP at most one second apart."""
        if type(cycles) is not int or not 1 <= cycles <= 100:
            raise Rejected("CYCLE_LIMIT")
        for index in range(cycles):
            result = self.once()
            yield result
            if index == cycles - 1 or result["status"] in {"STOPPED", "AUTH_BLOCKED", "BLOCKED"}:
                break
            seconds = result["next_poll_seconds"]
            while seconds > 0 and not self.stopped():
                delay = min(seconds, 1)
                wait(delay)
                seconds -= delay
