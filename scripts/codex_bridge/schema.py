"""Private Issue trust boundary. Task text never becomes a command."""

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
import hmac
import json
from pathlib import Path
import re

MAX_BODY_BYTES = 8192
MARKER = "VALORA_CODEX_TASK_V1"
INTENT = "read_fixture_v1"
SCOPE = ["fixture:read"]
CHECKS = ["fixture_sha256"]
COST = {"mode": "offline", "model": "none", "max_inference_calls": 0}
FIELDS = {
    "schema_version", "action", "task_id", "issuer", "authority", "intent",
    "approved_scope", "required_base_sha", "target_repo", "target_ref",
    "workspace_id", "created_at", "expires_at", "max_attempts", "lease_seconds",
    "cost_policy", "machine_id", "agent_id", "acceptance_checks", "nonce",
    "idempotency_key", "signature",
}


class Rejected(Exception):
    """Only constant reason codes may cross the logging boundary."""


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"), ensure_ascii=True)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise Rejected("DUPLICATE_JSON_KEY")
        result[key] = value
    return result


def parse_json(raw, maximum=MAX_BODY_BYTES):
    if not isinstance(raw, str):
        raise Rejected("BODY_LIMIT")
    try:
        if len(raw.encode("utf-8")) > maximum:
            raise Rejected("BODY_LIMIT")
        return json.loads(raw, object_pairs_hook=unique_object,
                          parse_constant=lambda _: (_ for _ in ()).throw(Rejected("JSON_CONSTANT")))
    except (ValueError, RecursionError, UnicodeError):
        raise Rejected("INVALID_JSON") from None


def timestamp(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z", value):
        raise Rejected("TIMESTAMP")
    try:
        return datetime.strptime(value, "%Y-%m-%dT%H:%M:%SZ").replace(tzinfo=timezone.utc).timestamp()
    except ValueError:
        raise Rejected("TIMESTAMP") from None


def identifier(value):
    return isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{16,64}", value) is not None


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def sign(task, key):
    """Canonical MAC; public fixture keys must never be provisioned for live use."""
    unsigned = {k: v for k, v in task.items() if k != "signature"}
    return hmac.new(key, canonical(unsigned).encode(), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class Policy:
    workspace: Path
    base_sha: str
    machine_id: str = "offline-fixture-host"
    queue: str = "Reguluspt/valora-task-queue"
    queue_id: int = 1416927556
    issuer_id: int = 130158621
    issuer_login: str = "Reguluspt"
    agent_id: str = "valora-bridge-p1"
    target_repo: str = "Reguluspt/valora-engineering"
    target_ref: str = "refs/heads/main"
    workspace_id: str = "bridge-fixture"


@dataclass(frozen=True)
class Task:
    number: int
    issue_id: int
    fingerprint: str
    task_key: str
    nonce_key: str
    idempotency_key: str
    expires: float
    lease_seconds: int
    base_sha: str


def validate(repo, issue, policy, key, now, current_sha):
    if not isinstance(repo, dict) or repo.get("private") is not True or repo.get("id") != policy.queue_id or repo.get("full_name") != policy.queue:
        raise Rejected("QUEUE_IDENTITY")
    if not isinstance(issue, dict):
        raise Rejected("ISSUE_SHAPE")
    if type(issue.get("number")) is not int or issue["number"] <= 1:
        raise Rejected("CONTROL_OR_INVALID_ISSUE")
    if type(issue.get("id")) is not int or issue["id"] <= 0 or issue.get("state") != "open" or "pull_request" in issue:
        raise Rejected("ISSUE_STATE")
    expected_url = f"https://api.github.com/repos/{policy.queue}/issues/{issue['number']}"
    if issue.get("url") != expected_url:
        raise Rejected("ISSUE_ORIGIN")
    author = issue.get("user")
    if not isinstance(author, dict) or type(author.get("id")) is not int or author.get("id") != policy.issuer_id or author.get("login") != policy.issuer_login:
        raise Rejected("ISSUER")
    body = parse_json(issue.get("body"))
    if not isinstance(body, dict) or set(body) != FIELDS:
        raise Rejected("TASK_FIELDS")
    fixed = {
        "schema_version": 1, "action": MARKER, "issuer": policy.issuer_id,
        "authority": "PO_SYNTHETIC_READ_ONLY", "intent": INTENT,
        "approved_scope": SCOPE, "target_repo": policy.target_repo,
        "target_ref": policy.target_ref, "workspace_id": policy.workspace_id,
        "machine_id": policy.machine_id, "agent_id": policy.agent_id,
        "max_attempts": 1, "acceptance_checks": CHECKS, "cost_policy": COST,
    }
    for field, expected in fixed.items():
        if canonical(body[field]) != canonical(expected):
            raise Rejected("AUTHORITY_OR_SCOPE")
    if not isinstance(key, bytes) or len(key) < 32:
        raise Rejected("AUTHORIZATION_UNAVAILABLE")
    if not isinstance(body["signature"], str) or not re.fullmatch(r"[0-9a-f]{64}", body["signature"]) or not hmac.compare_digest(body["signature"], sign(body, key)):
        raise Rejected("SIGNATURE")
    if not all(identifier(body[field]) for field in ("task_id", "nonce", "idempotency_key")):
        raise Rejected("IDENTIFIER")
    sha = body["required_base_sha"]
    if not isinstance(sha, str) or not re.fullmatch(r"[0-9a-f]{40}", sha) or sha != policy.base_sha or sha != current_sha:
        raise Rejected("HEAD_DRIFT")
    created, expires = timestamp(body["created_at"]), timestamp(body["expires_at"])
    if created > now or expires <= now or not 0 < expires - created <= 3600:
        raise Rejected("TTL")
    lease = body["lease_seconds"]
    if type(lease) is not int or not 1 <= lease <= 60:
        raise Rejected("LEASE")
    return Task(issue["number"], issue["id"], digest(canonical(body)),
                digest(body["task_id"]), digest(body["nonce"]),
                digest(body["idempotency_key"]), expires, lease, sha)
