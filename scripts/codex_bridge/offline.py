"""Synthetic queue with no HTTP, secrets or provider access."""

from copy import deepcopy
from datetime import datetime, timezone

from .schema import CHECKS, COST, INTENT, MARKER, SCOPE, canonical, sign

FIXTURE_KEY = b"PUBLIC_OFFLINE_TEST_KEY_NOT_A_CREDENTIAL_001"
FIXTURE_SHA = "b482c999d17a983af3ae99e16026e4261e862a27"
FIXTURE_NOW = 1791892800.0


def fixture_issue(policy, number=2, now=FIXTURE_NOW):
    def utc(seconds):
        return datetime.fromtimestamp(seconds, timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
    body = {
        "schema_version": 1, "action": MARKER, "task_id": f"synthetic-task-{number:04d}",
        "issuer": policy.issuer_id, "authority": "PO_SYNTHETIC_READ_ONLY", "intent": INTENT,
        "approved_scope": SCOPE, "required_base_sha": policy.base_sha,
        "target_repo": policy.target_repo, "target_ref": policy.target_ref,
        "workspace_id": policy.workspace_id, "created_at": utc(now - 10),
        "expires_at": utc(now + 300), "max_attempts": 1, "lease_seconds": 30,
        "cost_policy": COST, "machine_id": policy.machine_id, "agent_id": policy.agent_id,
        "acceptance_checks": CHECKS, "nonce": f"synthetic-nonce-{number:04d}",
        "idempotency_key": f"synthetic-receipt-{number:04d}",
    }
    body["signature"] = sign(body, FIXTURE_KEY)
    return {"id": 10000 + number, "number": number, "state": "open",
            "url": f"https://api.github.com/repos/{policy.queue}/issues/{number}",
            "user": {"id": policy.issuer_id, "login": policy.issuer_login},
            "body": canonical(body), "labels": [], "comments": 0}


class OfflineQueue:
    def __init__(self, policy, issues):
        self.policy, self.issues = policy, deepcopy(issues)
        self.results = {}

    def repository(self):
        return {"id": self.policy.queue_id, "full_name": self.policy.queue, "private": True}

    def poll(self):
        return [issue["number"] for issue in self.issues]

    def issue(self, number):
        return deepcopy(next(issue for issue in self.issues if issue["number"] == number))

    def publish(self, number, body):
        self.results.setdefault((number, body), body)

    def acknowledge_poll(self):
        pass

    def retry_poll(self):
        pass
