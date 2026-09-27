"""Repository-owned OAuth and launcher controller for the bounded PR-07 probe.

The controller has two modes. ``--self-test`` exercises the exact
Python-controller -> Node-launcher -> Python-probe boundary without network
access. ``--live`` performs one interactive OAuth flow and invokes the launcher
once. Every invocation whose recorder initializes writes a schema-limited
local flight record that never contains credentials, authorization responses,
provider identifiers, or raw stderr.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from pathlib import Path
import platform
import re
import shutil
import subprocess
import sys
import time
from datetime import UTC, datetime
from http.server import BaseHTTPRequestHandler, HTTPServer
from typing import Any
from urllib.parse import parse_qs, urlsplit
from uuid import UUID, uuid4
import webbrowser

import msal

EXPECTED_CLIENT_ID = "a7f7ef53-a590-491b-b0bc-12f25622e850"
CONSUMER_AUTHORITY = "https://login.microsoftonline.com/consumers"
CONSUMER_TENANT_ID = "9188040d-6c67-4c5b-b112-36a304b66dad"
CONSUMER_ISSUER = f"https://login.microsoftonline.com/{CONSUMER_TENANT_ID}/v2.0"
CLIENT_ID_ENVIRONMENT_VARIABLE = "VALORA_PR07_CLIENT_ID"
CLIENT_SECRET_ENVIRONMENT_VARIABLE = "VALORA_PR07_CLIENT_SECRET"
TOKEN_ENVIRONMENT_VARIABLE = "VALORA_PR07_GRAPH_ACCESS_TOKEN"
ATTEMPT_ID_ENVIRONMENT_VARIABLE = "VALORA_PR07_ATTEMPT_ID"
EVENT_JOURNAL_ENVIRONMENT_VARIABLE = "VALORA_PR07_EVENT_JOURNAL"
REDIRECT_URI = "http://localhost:8000/api/v1/m365/onedrive/oauth/callback"
CALLBACK_PATH = "/api/v1/m365/onedrive/oauth/callback"
CALLBACK_TIMEOUT_SECONDS = 300
MAX_CALLBACK_BODY_BYTES = 16 * 1024
GRAPH_SCOPES = ["Files.ReadWrite"]
SELF_TEST_SENTINEL = "valora-pr07-controller-self-test-sentinel"
V2_CANDIDATE = "C2_AUTO_V1"
V2_SCHEMA_VERSION = 2
C2_CANDIDATE = "C2_AUTO_V2"
C2_SCHEMA_VERSION = 3
OAUTH_ERROR_ALLOWLIST = {
    "access_denied",
    "consent_required",
    "interaction_required",
    "invalid_client",
    "invalid_grant",
    "invalid_request",
    "invalid_scope",
    "login_required",
    "server_error",
    "temporarily_unavailable",
    "unauthorized_client",
    "unsupported_grant_type",
}
OAUTH_PHASES = {
    "AUTHORIZATION_RESPONSE",
    "CALLBACK_VALIDATION",
    "FLOW_VALIDATION",
    "RESULT_VALIDATION",
    "TOKEN_REDEMPTION",
    "UNKNOWN",
}

CONTROLLER_PATH = Path(__file__).resolve()
BACKEND_DIRECTORY = CONTROLLER_PATH.parents[1]
REPOSITORY_DIRECTORY = CONTROLLER_PATH.parents[2]
LAUNCHER_PATH = BACKEND_DIRECTORY / "tools" / "pr07_onedrive_personal_if_match_launcher.mjs"
PROBE_PATH = BACKEND_DIRECTORY / "tools" / "pr07_onedrive_personal_if_match_probe.py"
DEFAULT_EVIDENCE_DIRECTORY = REPOSITORY_DIRECTORY / "local-artifacts" / "pr07"

LEGACY_SELF_TEST_REPORT = {
    "dependency_import": "PASS",
    "environment": "PRESENT",
    "interpreter": "PASS",
    "mode": "SELF_TEST",
    "network": "NOT_ATTEMPTED",
    "package_resolution": "PASS",
    "status": "PASS",
    "working_directory": "BACKEND",
}
SELF_TEST_REPORT = {
    "candidate": C2_CANDIDATE,
    "dependency_import": "PASS",
    "environment": "PRESENT",
    "interpreter": "PASS",
    "mode": "SELF_TEST",
    "network": "NOT_ATTEMPTED",
    "package_resolution": "PASS",
    "runtime_gate": "BLOCKED",
    "schema_version": C2_SCHEMA_VERSION,
    "status": "PASS",
    "working_directory": "BACKEND",
}
C2_REPORT_KEYS = {
    "candidate",
    "checked_at",
    "checks",
    "cleanup",
    "cleanup_issue",
    "fresh_final_http_status",
    "outcome",
    "phase",
    "partial_observations",
    "provider_error_code",
    "reason_code",
    "runtime_gate",
    "schema_version",
    "stale_final_http_status",
    "status",
}
V2_REPORT_KEYS = C2_REPORT_KEYS - {"partial_observations"}
C2_CHECK_KEYS = {
    "concurrent_bytes_preserved",
    "concurrent_etag_preserved",
    "concurrent_write_verified",
    "fresh_commit_verified",
    "fresh_partial_preserved",
    "item_identity_preserved",
    "stale_candidate_observed",
    "stale_partial_preserved",
}
C2_OUTCOMES = {
    "INCONCLUSIVE",
    "OBSERVED_SAFE_STALE_REJECTION",
    "SAFETY_VIOLATION",
    "UNSAFE_STALE_OVERWRITE",
}
C2_REASON_CODES = {
    "ALTERNATE_REJECTION",
    "FINAL_NOT_COMPLETED",
    "FIXTURE_FAILED",
    "FRESH_CONTROL_FAILED",
    "IDENTITY_CHANGED",
    "NONFINAL_MUTATION",
    "POST_STATE_INCONSISTENT",
    "POST_STATE_UNAVAILABLE",
    "RACE_SETUP_FAILED",
    "RESPONSE_IDENTITY_MISMATCH",
    "SAFE_412",
    "SESSION_CREATION_FAILED",
    "STALE_BYTES_OVERWROTE_CONCURRENT",
    "THIRD_STATE",
    "TRANSPORT_UNKNOWN",
    "UNEXPECTED_SANITIZED_FAILURE",
    "PARTIAL_HTTP_UNEXPECTED",
    "PARTIAL_RANGE_MALFORMED",
    "PARTIAL_RANGE_MISSING",
    "PARTIAL_RANGE_UNEXPECTED",
}
V2_REASON_CODES = C2_REASON_CODES - {
    "PARTIAL_HTTP_UNEXPECTED",
    "PARTIAL_RANGE_MALFORMED",
    "PARTIAL_RANGE_MISSING",
    "PARTIAL_RANGE_UNEXPECTED",
}
C2_PHASES = {"COMPLETE", "FIXTURE", "FRESH", "STALE"}
C2_PROVIDER_ERROR_CODES = {
    "accessDenied",
    "generalException",
    "invalidRange",
    "invalidRequest",
    "itemNotFound",
    "nameAlreadyExists",
    "quotaLimitReached",
    "resourceModified",
    "tooManyRequests",
    "unknown",
}
C2_CLEANUP_ISSUES = {
    "CANCEL_FAILED",
    "EVIDENCE_INCOMPLETE",
    "ITEM_DELETE_FAILED",
    "MULTIPLE",
    "NONE",
    "SESSION_UNKNOWN",
}
PARTIAL_RANGE_CLASSES = {
    "EXPECTED_START",
    "MALFORMED",
    "MISSING",
    "NOT_APPLICABLE",
    "NOT_OBSERVED",
    "UNEXPECTED_START",
}
SAFE_FAILURE_KEYS = {
    "child_exit_code",
    "child_stderr",
    "cleanup",
    "http_status",
    "provider_error_code",
    "reason",
    "stage",
    "status",
}
SAFE_SUCCESS_KEYS = {
    "checked_at",
    "cleanup",
    "concurrent_bytes_preserved",
    "drive_type",
    "fresh_conditional_commit",
    "isolated_item_created",
    "item_identity_preserved",
    "provider",
    "stale_commit_http_status",
    "stale_conditional_commit",
    "status",
}
SAFE_PROBE_FAILURE_KEYS = {
    "cleanup",
    "http_status",
    "provider_error_code",
    "reason",
    "status",
}
SAFE_LAUNCHER_STAGES = {
    "DEPENDENCY_PREFLIGHT",
    "LAUNCHER_VALIDATION",
    "PROBE_PROCESS",
}
SAFE_CLEANUP_STATES = {
    "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
    "DELETED_TO_RECYCLE_BIN",
    "FAILED",
    "NOT_ATTEMPTED",
}
SAFE_PROBE_PROGRESS_STAGES = {
    "CONCURRENT_WRITE_REQUEST_STARTED",
    "CONTENT_DOWNLOAD_REQUEST_STARTED",
    "DRIVE_VERIFY_REQUEST_STARTED",
    "FRESH_FINAL_COMMIT_REQUEST_STARTED",
    "FRESH_ITEM_VERIFY_REQUEST_STARTED",
    "FRESH_UPLOAD_SESSION_REQUEST_STARTED",
    "INITIAL_ITEM_VERIFY_REQUEST_STARTED",
    "ITEM_CREATE_REQUEST_STARTED",
    "PROBE_SELF_TEST_STARTED",
    "PROBE_STARTED",
    "STALE_FINAL_COMMIT_REQUEST_STARTED",
    "STALE_ITEM_VERIFY_REQUEST_STARTED",
    "STALE_UPLOAD_SESSION_REQUEST_STARTED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
    "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_REQUEST_STARTED",
    "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
    "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
    "UPLOAD_STAGE_REQUEST_STARTED",
}
V2_PROBE_PROGRESS_STAGES = {
    "CONCURRENT_WRITE_REQUEST_STARTED",
    "CONTENT_DOWNLOAD_REQUEST_STARTED",
    "DRIVE_VERIFY_REQUEST_STARTED",
    "FINAL_FRAGMENT_REQUEST_STARTED",
    "FINAL_FRAGMENT_RESPONSE_OBSERVED",
    "ITEM_CREATE_REQUEST_STARTED",
    "PARTIAL_DESTINATION_VERIFY_COMPLETED",
    "PARTIAL_FRAGMENT_REQUEST_STARTED",
    "PARTIAL_FRAGMENT_RESPONSE_VALIDATED",
    "POST_STATE_READ_STARTED",
    "POST_STATE_VERIFY_COMPLETED",
    "PROBE_SELF_TEST_STARTED",
    "PROBE_STARTED",
    "SESSION_AVAILABLE",
    "SESSION_CANCEL_REQUEST_COMPLETED",
    "SESSION_CANCEL_REQUEST_STARTED",
    "SESSION_COMPLETION_PROVEN",
    "SESSION_CREATE_REQUEST_STARTED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
    "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_REQUEST_STARTED",
}
V2_SESSION_STAGES = {
    "FINAL_FRAGMENT_REQUEST_STARTED",
    "FINAL_FRAGMENT_RESPONSE_OBSERVED",
    "PARTIAL_DESTINATION_VERIFY_COMPLETED",
    "PARTIAL_FRAGMENT_REQUEST_STARTED",
    "PARTIAL_FRAGMENT_RESPONSE_VALIDATED",
    "POST_STATE_READ_STARTED",
    "POST_STATE_VERIFY_COMPLETED",
    "SESSION_AVAILABLE",
    "SESSION_CANCEL_REQUEST_COMPLETED",
    "SESSION_CANCEL_REQUEST_STARTED",
    "SESSION_COMPLETION_PROVEN",
    "SESSION_CREATE_REQUEST_STARTED",
}
V3_PROBE_PROGRESS_STAGES = V2_PROBE_PROGRESS_STAGES | {
    "PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
}
V3_SESSION_STAGES = V2_SESSION_STAGES | {
    "PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
}
SAFE_JOURNAL_RECORD_TYPES = {
    "ATTEMPT_FINISHED",
    "ATTEMPT_STARTED",
    "LAUNCHER_INVOCATION",
    "NETWORK",
    "PROBE_FINISHED",
    "PROBE_STAGE",
    "STAGE",
}
SAFE_CONTROLLER_STAGES = {
    "CONTROLLER",
    "CONTROLLER_VALIDATION",
    "EVIDENCE",
    "LAUNCHER",
    "OAUTH",
    "OAUTH_CALLBACK",
    "OAUTH_START",
    "TOKEN_VALIDATION",
}
PROVIDER_MUTATION_STAGES = {
    "CONCURRENT_WRITE_REQUEST_STARTED",
    "FRESH_FINAL_COMMIT_REQUEST_STARTED",
    "FRESH_UPLOAD_SESSION_REQUEST_STARTED",
    "ITEM_CREATE_REQUEST_STARTED",
    "STALE_FINAL_COMMIT_REQUEST_STARTED",
    "STALE_UPLOAD_SESSION_REQUEST_STARTED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
    "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_REQUEST_STARTED",
    "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
    "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
    "UPLOAD_STAGE_REQUEST_STARTED",
    "FINAL_FRAGMENT_REQUEST_STARTED",
    "PARTIAL_FRAGMENT_REQUEST_STARTED",
    "SESSION_CANCEL_REQUEST_COMPLETED",
    "SESSION_CANCEL_REQUEST_STARTED",
    "SESSION_CREATE_REQUEST_STARTED",
}
ITEM_ID_EVIDENCE_STAGES = {
    "CONCURRENT_WRITE_REQUEST_STARTED",
    "CONTENT_DOWNLOAD_REQUEST_STARTED",
    "FRESH_FINAL_COMMIT_REQUEST_STARTED",
    "FRESH_ITEM_VERIFY_REQUEST_STARTED",
    "FRESH_UPLOAD_SESSION_REQUEST_STARTED",
    "INITIAL_ITEM_VERIFY_REQUEST_STARTED",
    "STALE_FINAL_COMMIT_REQUEST_STARTED",
    "STALE_ITEM_VERIFY_REQUEST_STARTED",
    "STALE_UPLOAD_SESSION_REQUEST_STARTED",
    "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_REQUEST_STARTED",
    "UPLOAD_STAGE_REQUEST_STARTED",
}


class ControllerFailure(RuntimeError):
    """A stable failure code safe for stdout and the flight record."""

    def __init__(
        self,
        code: str,
        stage: str,
        *,
        details: dict[str, Any] | None = None,
    ) -> None:
        super().__init__(code)
        self.code = code
        self.stage = stage
        self.details = details


def _normalize_oauth_diagnostics(*, phase: str, payload: object) -> dict[str, Any]:
    source = payload if isinstance(payload, dict) else {}
    error = source.get("error")
    if error is not None and (
        not isinstance(error, str) or error not in OAUTH_ERROR_ALLOWLIST
    ):
        error = "unknown"
    raw_codes = source.get("error_codes")
    codes = (
        sorted(
            {
                code
                for code in raw_codes
                if type(code) is int and 0 <= code <= 2_147_483_647
            }
        )
        if isinstance(raw_codes, list) and len(raw_codes) <= 8
        else []
    )
    correlation = source.get("correlation_id")
    if isinstance(correlation, str) and re.fullmatch(
        r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-"
        r"[0-9a-fA-F]{4}-[0-9a-fA-F]{12}",
        correlation,
    ):
        correlation = str(UUID(correlation))
    else:
        correlation = None
    return {
        "oauth": {
            "phase": phase if phase in OAUTH_PHASES else "UNKNOWN",
            "oauth_error": error,
            "aadsts_codes": codes,
            "correlation_id": correlation,
        }
    }


def _valid_failure_details(value: Any) -> bool:
    if value is None:
        return True
    if not isinstance(value, dict):
        return False
    try:
        if len(json.dumps(value, ensure_ascii=True, sort_keys=True).encode("utf-8")) > 1024:
            return False
    except (TypeError, ValueError):
        return False
    if "oauth" not in value:
        return True
    if set(value) != {"oauth"} or not isinstance(value["oauth"], dict):
        return False
    oauth = value["oauth"]
    if set(oauth) != {"phase", "oauth_error", "aadsts_codes", "correlation_id"}:
        return False
    if oauth["phase"] not in OAUTH_PHASES:
        return False
    if oauth["oauth_error"] not in OAUTH_ERROR_ALLOWLIST | {"unknown", None}:
        return False
    codes = oauth["aadsts_codes"]
    if (
        not isinstance(codes, list)
        or len(codes) > 8
        or any(type(code) is not int or not 0 <= code <= 2_147_483_647 for code in codes)
        or codes != sorted(set(codes))
    ):
        return False
    correlation = oauth["correlation_id"]
    if correlation is not None:
        try:
            if str(UUID(correlation)) != correlation:
                return False
        except (TypeError, ValueError):
            return False
    return True


def _utc_now() -> str:
    return datetime.now(UTC).isoformat()


def _sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def _sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _sha256_file_or_unavailable(path: Path) -> str:
    try:
        return _sha256_file(path)
    except OSError:
        return "UNAVAILABLE"


def _repository_fingerprint() -> dict[str, Any]:
    try:
        head = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=REPOSITORY_DIRECTORY,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout.strip().decode("ascii")
        status = subprocess.run(
            ["git", "status", "--porcelain=v1", "--untracked-files=normal"],
            cwd=REPOSITORY_DIRECTORY,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
        tracked_diff = subprocess.run(
            ["git", "diff", "--binary", "HEAD", "--", ".", ":(exclude)scratch/**"],
            cwd=REPOSITORY_DIRECTORY,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout
        untracked_output = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            cwd=REPOSITORY_DIRECTORY,
            check=True,
            capture_output=True,
            timeout=10,
        ).stdout.decode("utf-8")
        content_digest = hashlib.sha256(tracked_diff)
        for relative_value in sorted(untracked_output.splitlines()):
            normalized = relative_value.replace("\\", "/")
            if normalized == "scratch" or normalized.startswith("scratch/"):
                continue
            candidate = (REPOSITORY_DIRECTORY / relative_value).resolve()
            if candidate.is_file() and candidate.is_relative_to(REPOSITORY_DIRECTORY):
                content_digest.update(normalized.encode("utf-8"))
                content_digest.update(b"\0")
                content_digest.update(_sha256_file(candidate).encode("ascii"))
        return {
            "head": head,
            "working_tree_dirty": bool(status),
            "working_tree_diff_sha256": content_digest.hexdigest(),
            "working_tree_status_sha256": _sha256_bytes(status),
        }
    except (OSError, subprocess.SubprocessError, UnicodeDecodeError):
        return {
            "head": "UNAVAILABLE",
            "working_tree_dirty": None,
            "working_tree_diff_sha256": "UNAVAILABLE",
            "working_tree_status_sha256": "UNAVAILABLE",
        }


def _dependency_versions() -> dict[str, str]:
    versions: dict[str, str] = {}
    for package in ("httpx", "msal"):
        try:
            versions[package] = importlib.metadata.version(package)
        except importlib.metadata.PackageNotFoundError:
            versions[package] = "UNAVAILABLE"
    return versions


def _validate_legacy_probe_report(report: Any, *, exit_code: Any) -> bool:
    if (
        not isinstance(report, dict)
        or not isinstance(exit_code, int)
        or isinstance(exit_code, bool)
    ):
        return False
    if report.get("status") == "PASS":
        return (
            exit_code == 0
            and set(report) == SAFE_SUCCESS_KEYS
            and report.get("cleanup") == "DELETED_TO_RECYCLE_BIN"
            and report.get("fresh_conditional_commit") == "PASS"
            and report.get("stale_conditional_commit") == "HTTP_412_PASS"
            and report.get("stale_commit_http_status") == 412
            and report.get("item_identity_preserved") is True
            and report.get("concurrent_bytes_preserved") is True
            and report.get("isolated_item_created") is True
            and report.get("drive_type") == "personal"
            and report.get("provider") == "Microsoft Graph v1.0"
            and isinstance(report.get("checked_at"), str)
        )
    if (
        exit_code == 0
        or report.get("status") != "FAIL"
        or not set(report).issubset(SAFE_PROBE_FAILURE_KEYS)
    ):
        return False
    reason = report.get("reason")
    if (
        not isinstance(reason, str)
        or not reason
        or len(reason) > 512
        or "\n" in reason
        or "\r" in reason
    ):
        return False
    if "cleanup" in report and report["cleanup"] not in SAFE_CLEANUP_STATES:
        return False
    if "http_status" in report and not (
        isinstance(report["http_status"], int)
        and not isinstance(report["http_status"], bool)
        and 100 <= report["http_status"] <= 599
    ):
        return False
    provider_code = report.get("provider_error_code")
    if provider_code is not None and not (
        isinstance(provider_code, str)
        and provider_code
        and len(provider_code) <= 64
        and provider_code[0].isalpha()
        and all(character.isalnum() or character in "._-" for character in provider_code)
    ):
        return False
    return True


def _valid_optional_http_status(value: Any) -> bool:
    return value is None or (
        isinstance(value, int)
        and not isinstance(value, bool)
        and 100 <= value <= 599
    )


def _valid_checked_at(value: Any) -> bool:
    if not isinstance(value, str) or len(value) > 64:
        return False
    try:
        parsed = datetime.fromisoformat(value)
    except ValueError:
        return False
    return parsed.tzinfo is not None


def _valid_partial_observations(value: Any) -> bool:
    if not isinstance(value, dict) or set(value) != {"fresh", "stale"}:
        return False
    for observation in value.values():
        if not isinstance(observation, dict) or set(observation) != {
            "http_status",
            "range_class",
        }:
            return False
        http_status = observation.get("http_status")
        range_class = observation.get("range_class")
        if not _valid_optional_http_status(http_status) or range_class not in PARTIAL_RANGE_CLASSES:
            return False
        if range_class == "NOT_OBSERVED" and http_status is not None:
            return False
        if range_class == "NOT_APPLICABLE" and (
            http_status is None or http_status == 202
        ):
            return False
        if range_class not in {"NOT_OBSERVED", "NOT_APPLICABLE"} and http_status != 202:
            return False
    return True


def _validate_c2_probe_report_version(
    report: Any,
    *,
    exit_code: Any,
    expected_candidate: str,
    schema_version: int,
    candidate: str,
    report_keys: set[str],
    reason_codes: set[str],
    require_partial_observations: bool,
) -> bool:
    if (
        not isinstance(report, dict)
        or set(report) != report_keys
        or not isinstance(exit_code, int)
        or isinstance(exit_code, bool)
        or report.get("schema_version") != schema_version
        or isinstance(report.get("schema_version"), bool)
        or report.get("candidate") != expected_candidate
        or expected_candidate != candidate
        or report.get("runtime_gate") != "BLOCKED"
        or report.get("status") not in {"PASS", "FAIL"}
        or (exit_code == 0) != (report.get("status") == "PASS")
        or report.get("outcome") not in C2_OUTCOMES
        or report.get("reason_code") not in reason_codes
        or report.get("phase") not in C2_PHASES
        or not _valid_optional_http_status(report.get("fresh_final_http_status"))
        or not _valid_optional_http_status(report.get("stale_final_http_status"))
        or report.get("cleanup") not in SAFE_CLEANUP_STATES
        or report.get("cleanup_issue") not in C2_CLEANUP_ISSUES
        or not _valid_checked_at(report.get("checked_at"))
    ):
        return False
    provider_code = report.get("provider_error_code")
    if provider_code is not None and provider_code not in C2_PROVIDER_ERROR_CODES:
        return False
    checks = report.get("checks")
    if not isinstance(checks, dict) or set(checks) != C2_CHECK_KEYS:
        return False
    if any(value is not None and type(value) is not bool for value in checks.values()):
        return False
    partial_observations = report.get("partial_observations")
    if require_partial_observations and not _valid_partial_observations(partial_observations):
        return False
    partial_reason_class = {
        "PARTIAL_HTTP_UNEXPECTED": "NOT_APPLICABLE",
        "PARTIAL_RANGE_MALFORMED": "MALFORMED",
        "PARTIAL_RANGE_MISSING": "MISSING",
        "PARTIAL_RANGE_UNEXPECTED": "UNEXPECTED_START",
    }.get(report.get("reason_code"))
    if require_partial_observations and partial_reason_class is not None and (
        report.get("phase") not in {"FRESH", "STALE"}
        or partial_observations[report["phase"].lower()]["range_class"]
        != partial_reason_class
    ):
        return False
    expected_partials = not require_partial_observations or all(
        partial_observations[role] == {
            "http_status": 202,
            "range_class": "EXPECTED_START",
        }
        for role in ("fresh", "stale")
    )
    safe = (
        report.get("outcome") == "OBSERVED_SAFE_STALE_REJECTION"
        and report.get("phase") == "COMPLETE"
        and checks["fresh_partial_preserved"] is True
        and checks["fresh_commit_verified"] is True
        and checks["stale_partial_preserved"] is True
        and checks["concurrent_write_verified"] is True
        and checks["item_identity_preserved"] is True
        and checks["concurrent_bytes_preserved"] is True
        and checks["concurrent_etag_preserved"] is True
        and checks["stale_candidate_observed"] is False
        and report.get("fresh_final_http_status") in {200, 201}
        and report.get("stale_final_http_status") == 412
        and report.get("reason_code") == "SAFE_412"
        and expected_partials
    )
    unsafe = (
        report.get("outcome") == "UNSAFE_STALE_OVERWRITE"
        and report.get("reason_code") == "STALE_BYTES_OVERWROTE_CONCURRENT"
        and checks["fresh_commit_verified"] is True
        and checks["concurrent_write_verified"] is True
        and checks["item_identity_preserved"] is True
        and checks["concurrent_bytes_preserved"] is False
        and checks["stale_candidate_observed"] is True
        and expected_partials
    )
    if report.get("outcome") == "OBSERVED_SAFE_STALE_REJECTION" and not safe:
        return False
    if report.get("outcome") == "UNSAFE_STALE_OVERWRITE" and not unsafe:
        return False
    expected_pass = (
        safe
        and report.get("cleanup") == "DELETED_TO_RECYCLE_BIN"
        and report.get("cleanup_issue") == "NONE"
    )
    return (
        (report.get("status") == "PASS") == expected_pass
        and (exit_code == 0) == expected_pass
    )


def _validate_c2_probe_report(
    report: Any,
    *,
    exit_code: Any,
    expected_candidate: str,
) -> bool:
    return _validate_c2_probe_report_version(
        report,
        exit_code=exit_code,
        expected_candidate=expected_candidate,
        schema_version=C2_SCHEMA_VERSION,
        candidate=C2_CANDIDATE,
        report_keys=C2_REPORT_KEYS,
        reason_codes=C2_REASON_CODES,
        require_partial_observations=True,
    )


def _validate_v2_c2_probe_report(
    report: Any,
    *,
    exit_code: Any,
    expected_candidate: str,
) -> bool:
    return _validate_c2_probe_report_version(
        report,
        exit_code=exit_code,
        expected_candidate=expected_candidate,
        schema_version=V2_SCHEMA_VERSION,
        candidate=V2_CANDIDATE,
        report_keys=V2_REPORT_KEYS,
        reason_codes=V2_REASON_CODES,
        require_partial_observations=False,
    )


def _validate_probe_report(
    report: Any,
    *,
    exit_code: Any,
    self_test: bool,
    expected_candidate: str,
) -> bool:
    if self_test:
        return report == SELF_TEST_REPORT and exit_code == 0
    return _validate_c2_probe_report(
        report,
        exit_code=exit_code,
        expected_candidate=expected_candidate,
    )


def _terminal_reports_are_consistent(
    terminal: dict[str, Any],
    probe_terminal: dict[str, Any] | None,
    *,
    schema_version: int | None = None,
    expected_candidate: str | None = None,
) -> bool:
    launcher = terminal.get("launcher")
    if launcher is None:
        return terminal.get("status") == "FAIL" and probe_terminal is None
    if not isinstance(launcher, dict) or set(launcher) != {"exit_code", "report", "stderr"}:
        return False
    launcher_report = launcher.get("report")
    launcher_exit_code = launcher.get("exit_code")
    if schema_version == C2_SCHEMA_VERSION:
        report_valid = _validate_c2_probe_report(
            launcher_report,
            exit_code=launcher_exit_code,
            expected_candidate=expected_candidate or "",
        )
    elif schema_version == V2_SCHEMA_VERSION:
        report_valid = _validate_v2_c2_probe_report(
            launcher_report,
            exit_code=launcher_exit_code,
            expected_candidate=expected_candidate or "",
        )
    else:
        report_valid = _validate_legacy_launcher_report(
            launcher_report, self_test=False, forbidden=set()
        )
    if (
        not report_valid
        or not isinstance(launcher_exit_code, int)
        or isinstance(launcher_exit_code, bool)
        or (launcher_exit_code == 0) != (launcher_report.get("status") == "PASS")
        or launcher.get("stderr") != "EMPTY"
        or terminal.get("status") != launcher_report.get("status")
    ):
        return False
    if probe_terminal is None:
        return True
    return (
        probe_terminal.get("status") == terminal.get("status")
        and probe_terminal.get("exit_code") == launcher_exit_code
        and probe_terminal.get("report") == launcher_report
    )


def _has_unresolved_prior_live_attempt(evidence_directory: Path) -> bool:
    if not evidence_directory.exists():
        return False
    if not evidence_directory.is_dir():
        raise OSError("Evidence path is not a directory.")
    for journal_path in evidence_directory.glob("*.events.jsonl"):
        attempt_id: str | None = None
        live_started = False
        terminal: dict[str, Any] | None = None
        probe_terminal: dict[str, Any] | None = None
        malformed = False
        probe_stages: list[str] = []
        probe_events: list[dict[str, Any]] = []
        schema_version: int | None = None
        expected_candidate: str | None = None
        try:
            if journal_path.stat().st_size > 1024 * 1024:
                return True
            with journal_path.open("r", encoding="utf-8") as journal:
                for line_number, line in enumerate(journal, start=1):
                    try:
                        entry = json.loads(line)
                    except json.JSONDecodeError:
                        malformed = True
                        continue
                    if not isinstance(entry, dict):
                        malformed = True
                        continue
                    record_type = entry.get("record_type")
                    if record_type not in SAFE_JOURNAL_RECORD_TYPES:
                        malformed = True
                        continue
                    if record_type == "ATTEMPT_STARTED":
                        candidate = entry.get("attempt_id")
                        if (
                            line_number != 1
                            or attempt_id is not None
                            or not isinstance(candidate, str)
                            or not candidate
                            or entry.get("mode") not in {"LIVE", "SELF_TEST"}
                            or not isinstance(entry.get("at"), str)
                        ):
                            malformed = True
                            continue
                        attempt_id = candidate
                        live_started = entry.get("mode") == "LIVE"
                        if "schema_version" in entry or "candidate" in entry:
                            version_candidate = (
                                entry.get("schema_version"), entry.get("candidate")
                            )
                            if set(entry) != {
                                "at", "attempt_id", "candidate", "mode",
                                "record_type", "schema_version",
                            } or version_candidate not in {
                                (V2_SCHEMA_VERSION, V2_CANDIDATE),
                                (C2_SCHEMA_VERSION, C2_CANDIDATE),
                            }:
                                malformed = True
                                continue
                            schema_version, expected_candidate = version_candidate
                        continue
                    if attempt_id is None or entry.get("attempt_id") != attempt_id:
                        malformed = True
                        continue
                    if terminal is not None:
                        malformed = True
                        continue
                    if record_type == "PROBE_STAGE":
                        stage = entry.get("stage")
                        if schema_version in {V2_SCHEMA_VERSION, C2_SCHEMA_VERSION}:
                            progress_stages = (
                                V3_PROBE_PROGRESS_STAGES
                                if schema_version == C2_SCHEMA_VERSION
                                else V2_PROBE_PROGRESS_STAGES
                            )
                            session_stages = (
                                V3_SESSION_STAGES
                                if schema_version == C2_SCHEMA_VERSION
                                else V2_SESSION_STAGES
                            )
                            expected_keys = {"at", "attempt_id", "record_type", "stage"}
                            if stage in session_stages:
                                expected_keys.add("session_role")
                            if (
                                schema_version == C2_SCHEMA_VERSION
                                and stage == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED"
                            ):
                                expected_keys.update({"http_status", "range_class"})
                            if (
                                probe_terminal is not None
                                or set(entry) != expected_keys
                                or stage not in progress_stages
                                or not isinstance(entry.get("at"), str)
                                or (
                                    stage in session_stages
                                    and entry.get("session_role") not in {"FRESH", "STALE"}
                                )
                                or (
                                    stage == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED"
                                    and (
                                        not _valid_optional_http_status(entry.get("http_status"))
                                        or entry.get("http_status") is None
                                        or entry.get("range_class")
                                        not in PARTIAL_RANGE_CLASSES - {"NOT_OBSERVED"}
                                        or (
                                            entry.get("range_class") == "NOT_APPLICABLE"
                                            and entry.get("http_status") == 202
                                        )
                                        or (
                                            entry.get("range_class") != "NOT_APPLICABLE"
                                            and entry.get("http_status") != 202
                                        )
                                    )
                                )
                            ):
                                malformed = True
                                continue
                            probe_stages.append(stage)
                            probe_events.append(entry)
                            continue
                        if (
                            probe_terminal is not None
                            or set(entry) != {"at", "attempt_id", "record_type", "stage"}
                            or stage not in SAFE_PROBE_PROGRESS_STAGES
                            or not isinstance(entry.get("at"), str)
                        ):
                            malformed = True
                            continue
                        probe_stages.append(stage)
                    elif record_type == "STAGE":
                        if (
                            entry.get("stage") not in SAFE_CONTROLLER_STAGES
                            or entry.get("status") not in {"STARTED", "PASS", "FAIL"}
                            or not isinstance(entry.get("at"), str)
                        ):
                            malformed = True
                    elif record_type == "NETWORK":
                        if (
                            entry.get("network") != "OAUTH_ATTEMPTED"
                            or not isinstance(entry.get("at"), str)
                        ):
                            malformed = True
                    elif record_type == "LAUNCHER_INVOCATION":
                        if (
                            not isinstance(entry.get("fingerprint"), dict)
                            or not isinstance(entry.get("at"), str)
                        ):
                            malformed = True
                    elif record_type == "PROBE_FINISHED":
                        probe_exit_code = entry.get("exit_code")
                        probe_report = entry.get("report")
                        if (
                            probe_terminal is not None
                            or set(entry)
                            != {
                                "at",
                                "attempt_id",
                                "exit_code",
                                "record_type",
                                "report",
                                "status",
                            }
                            or not isinstance(entry.get("at"), str)
                            or entry.get("status") not in {"PASS", "FAIL"}
                            or not isinstance(probe_report, dict)
                            or entry.get("status") != probe_report.get("status")
                        ):
                            malformed = True
                            continue
                        if schema_version == C2_SCHEMA_VERSION:
                            report_valid = (
                                _validate_probe_report(
                                    probe_report,
                                    exit_code=probe_exit_code,
                                    self_test=not live_started,
                                    expected_candidate=expected_candidate or "",
                                )
                            )
                        elif schema_version == V2_SCHEMA_VERSION:
                            report_valid = _validate_v2_c2_probe_report(
                                probe_report,
                                exit_code=probe_exit_code,
                                expected_candidate=expected_candidate or "",
                            )
                        else:
                            report_valid = (
                                _validate_legacy_probe_report(
                                    probe_report,
                                    exit_code=probe_exit_code,
                                )
                                if live_started
                                else probe_report == LEGACY_SELF_TEST_REPORT
                                and probe_exit_code == 0
                            )
                        if not report_valid:
                            malformed = True
                            continue
                        probe_terminal = entry
                    elif record_type == "ATTEMPT_FINISHED":
                        if (
                            set(entry)
                            != {
                                "at",
                                "attempt_id",
                                "failure_code",
                                "failure_details",
                                "launcher",
                                "record_type",
                                "status",
                            }
                            or entry.get("status") not in {"PASS", "FAIL"}
                            or not isinstance(entry.get("at"), str)
                            or entry.get("failure_code") is not None
                            and not isinstance(entry.get("failure_code"), str)
                            or entry.get("failure_details") is not None
                            and not _valid_failure_details(entry.get("failure_details"))
                            or entry.get("launcher") is not None
                            and not isinstance(entry.get("launcher"), dict)
                            or entry.get("status") == "PASS"
                            and entry.get("failure_code") is not None
                            or entry.get("status") == "FAIL"
                            and not isinstance(entry.get("failure_code"), str)
                        ):
                            malformed = True
                            continue
                        terminal = entry
        except (OSError, UnicodeError):
            return True
        if attempt_id is None:
            return True
        if malformed and live_started:
            return True
        if not live_started:
            continue
        if terminal is None:
            return True
        if not _terminal_reports_are_consistent(
            terminal,
            probe_terminal,
            schema_version=schema_version,
            expected_candidate=expected_candidate,
        ):
            return True
        mutation_started = any(stage in PROVIDER_MUTATION_STAGES for stage in probe_stages)
        if not mutation_started:
            launcher = terminal.get("launcher")
            if launcher is not None:
                report = launcher["report"]
                if (
                    report.get("status") != "FAIL"
                    or report.get("cleanup") not in {None, "NOT_ATTEMPTED"}
                ):
                    return True
            continue
        if probe_terminal is None:
            return True
        if schema_version == C2_SCHEMA_VERSION:
            if not _v3_journal_cleanup_is_resolved(probe_events, terminal, probe_terminal):
                return True
        elif schema_version == V2_SCHEMA_VERSION:
            if not _v2_journal_cleanup_is_resolved(probe_events, terminal, probe_terminal):
                return True
        elif not _journal_cleanup_is_resolved(probe_stages, terminal, probe_terminal):
            return True
    return False


def _journal_cleanup_is_resolved(
    probe_stages: list[str],
    terminal: dict[str, Any],
    probe_terminal: dict[str, Any] | None,
) -> bool:
    if probe_stages.count("ITEM_CREATE_REQUEST_STARTED") != 1:
        return False
    creation_index = probe_stages.index("ITEM_CREATE_REQUEST_STARTED")
    if any(
        index <= creation_index and stage != "ITEM_CREATE_REQUEST_STARTED"
        for index, stage in enumerate(probe_stages)
        if stage in PROVIDER_MUTATION_STAGES
    ):
        return False
    cleanup_markers = {
        stage: [index for index, candidate in enumerate(probe_stages) if candidate == stage]
        for stage in {
            "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
            "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
            "TEST_ITEM_DELETE_REQUEST_COMPLETED",
            "TEST_ITEM_DELETE_REQUEST_STARTED",
            "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
            "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
        }
    }
    if any(len(indices) > 1 for indices in cleanup_markers.values()):
        return False

    def completed_after_started(started: str, completed: str) -> bool:
        start_indices = cleanup_markers[started]
        completion_indices = cleanup_markers[completed]
        return (
            len(start_indices) == 1
            and len(completion_indices) == 1
            and start_indices[0] < completion_indices[0]
        )

    cancel_completed = completed_after_started(
        "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
        "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
    )
    exact_delete_completed = completed_after_started(
        "TEST_ITEM_DELETE_REQUEST_STARTED",
        "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    )
    name_delete_completed = completed_after_started(
        "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
        "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
    )
    cleanup_pairs = (
        (
            "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
            "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
        ),
        ("TEST_ITEM_DELETE_REQUEST_STARTED", "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
        (
            "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
            "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
        ),
    )
    for started, completed in cleanup_pairs:
        if bool(cleanup_markers[started]) != bool(cleanup_markers[completed]):
            return False
    pair_completions = {
        cleanup_pairs[0]: cancel_completed,
        cleanup_pairs[1]: exact_delete_completed,
        cleanup_pairs[2]: name_delete_completed,
    }
    for (started, completed), pair_completed in pair_completions.items():
        if (cleanup_markers[started] or cleanup_markers[completed]) and not pair_completed:
            return False
    if exact_delete_completed == name_delete_completed:
        return False
    delete_stages = {
        "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
        "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
        "TEST_ITEM_DELETE_REQUEST_COMPLETED",
        "TEST_ITEM_DELETE_REQUEST_STARTED",
    }
    delete_start = (
        cleanup_markers["TEST_ITEM_DELETE_REQUEST_STARTED"][0]
        if exact_delete_completed
        else cleanup_markers["TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED"][0]
    )
    delete_completion = (
        cleanup_markers["TEST_ITEM_DELETE_REQUEST_COMPLETED"][0]
        if exact_delete_completed
        else cleanup_markers["TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"][0]
    )
    if any(
        index >= delete_start
        for index, stage in enumerate(probe_stages)
        if stage in PROVIDER_MUTATION_STAGES and stage not in delete_stages
    ):
        return False
    if any(
        index > delete_completion and stage in PROVIDER_MUTATION_STAGES
        for index, stage in enumerate(probe_stages)
    ):
        return False

    launcher = terminal.get("launcher")
    if not isinstance(launcher, dict) or set(launcher) != {"exit_code", "report", "stderr"}:
        return False
    report = launcher.get("report")
    if not _validate_legacy_launcher_report(report, self_test=False, forbidden=set()):
        return False
    if terminal.get("status") != report.get("status"):
        return False
    exit_code = launcher.get("exit_code")
    if (
        not isinstance(exit_code, int)
        or isinstance(exit_code, bool)
        or (exit_code == 0) != (report.get("status") == "PASS")
    ):
        return False
    if launcher.get("stderr") != "EMPTY":
        return False
    if probe_terminal is not None and (
        probe_terminal.get("status") != terminal.get("status")
        or probe_terminal.get("exit_code") != exit_code
        or probe_terminal.get("report") != report
    ):
        return False

    cleanup = report.get("cleanup")
    if cleanup == "DELETED_TO_RECYCLE_BIN":
        if not exact_delete_completed or name_delete_completed:
            return False
    elif cleanup == "ABSENT_OR_DELETED_TO_RECYCLE_BIN":
        if not name_delete_completed or exact_delete_completed:
            return False
        if any(stage in ITEM_ID_EVIDENCE_STAGES for stage in probe_stages):
            return False
    else:
        return False

    active_session: str | None = None
    cancel_started_for: str | None = None
    fresh_session_started = False
    stale_session_started = False
    fresh_commit_started = False
    fresh_session_proven_closed = False
    for stage in probe_stages:
        if (
            cancel_started_for is not None
            and stage != "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED"
        ):
            return False
        if stage == "FRESH_UPLOAD_SESSION_REQUEST_STARTED":
            if fresh_session_started or active_session is not None:
                return False
            fresh_session_started = True
            active_session = "FRESH"
        elif stage == "STALE_UPLOAD_SESSION_REQUEST_STARTED":
            if (
                stale_session_started
                or active_session is not None
                or not fresh_session_proven_closed
            ):
                return False
            stale_session_started = True
            active_session = "STALE"
        elif stage == "UPLOAD_STAGE_REQUEST_STARTED":
            if active_session not in {"FRESH", "STALE"}:
                return False
        elif stage == "INITIAL_ITEM_VERIFY_REQUEST_STARTED":
            if active_session != "FRESH":
                return False
        elif stage == "FRESH_FINAL_COMMIT_REQUEST_STARTED":
            if active_session != "FRESH" or fresh_commit_started:
                return False
            fresh_commit_started = True
        elif stage == "FRESH_ITEM_VERIFY_REQUEST_STARTED":
            if active_session != "FRESH" or not fresh_commit_started:
                return False
            active_session = None
            fresh_session_proven_closed = True
        elif stage in {
            "CONCURRENT_WRITE_REQUEST_STARTED",
            "STALE_FINAL_COMMIT_REQUEST_STARTED",
            "STALE_ITEM_VERIFY_REQUEST_STARTED",
        }:
            if active_session != "STALE":
                return False
        elif stage == "UPLOAD_SESSION_CANCEL_REQUEST_STARTED":
            if active_session is None or cancel_started_for is not None:
                return False
            cancel_started_for = active_session
        elif stage == "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED":
            if active_session is None or cancel_started_for != active_session:
                return False
            active_session = None
            cancel_started_for = None
    return active_session is None and cancel_started_for is None


def _c2_journal_cleanup_is_resolved(
    probe_events: list[dict[str, Any]],
    terminal: dict[str, Any],
    probe_terminal: dict[str, Any] | None,
    *,
    schema_version: int,
) -> bool:
    stages = [event["stage"] for event in probe_events]
    session_stages = (
        V3_SESSION_STAGES
        if schema_version == C2_SCHEMA_VERSION
        else V2_SESSION_STAGES
    )
    if stages.count("ITEM_CREATE_REQUEST_STARTED") != 1:
        return False
    creation_index = stages.index("ITEM_CREATE_REQUEST_STARTED")
    if any(
        index < creation_index
        for index, stage in enumerate(stages)
        if stage in PROVIDER_MUTATION_STAGES or stage in session_stages
    ):
        return False
    exact_delete = (
        stages.count("TEST_ITEM_DELETE_REQUEST_STARTED") == 1
        and stages.count("TEST_ITEM_DELETE_REQUEST_COMPLETED") == 1
    )
    name_delete = (
        stages.count("TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED") == 1
        and stages.count("TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED") == 1
    )
    if exact_delete == name_delete:
        return False
    if any(
        stages.count(stage) != 0
        for stage in (
            {"TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED", "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"}
            if exact_delete
            else {"TEST_ITEM_DELETE_REQUEST_STARTED", "TEST_ITEM_DELETE_REQUEST_COMPLETED"}
        )
    ):
        return False
    delete_start_stage = (
        "TEST_ITEM_DELETE_REQUEST_STARTED"
        if exact_delete
        else "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED"
    )
    delete_complete_stage = (
        "TEST_ITEM_DELETE_REQUEST_COMPLETED"
        if exact_delete
        else "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"
    )
    delete_start = stages.index(delete_start_stage)
    delete_complete = stages.index(delete_complete_stage)
    if delete_start >= delete_complete:
        return False
    if any(
        index >= delete_start
        for index, stage in enumerate(stages)
        if stage in PROVIDER_MUTATION_STAGES
        and stage not in {delete_start_stage, delete_complete_stage}
    ):
        return False
    if delete_complete != len(stages) - 1:
        return False

    launcher = terminal.get("launcher")
    if not isinstance(launcher, dict) or set(launcher) != {"exit_code", "report", "stderr"}:
        return False
    report = launcher.get("report")
    exit_code = launcher.get("exit_code")
    report_valid = (
        _validate_c2_probe_report(
            report,
            exit_code=exit_code,
            expected_candidate=C2_CANDIDATE,
        )
        if schema_version == C2_SCHEMA_VERSION
        else _validate_v2_c2_probe_report(
            report,
            exit_code=exit_code,
            expected_candidate=V2_CANDIDATE,
        )
    )
    if not report_valid:
        return False
    expected_cleanup = (
        "DELETED_TO_RECYCLE_BIN"
        if exact_delete
        else "ABSENT_OR_DELETED_TO_RECYCLE_BIN"
    )
    if report.get("cleanup") != expected_cleanup or report.get("cleanup_issue") != "NONE":
        return False
    if terminal.get("status") != report.get("status") or launcher.get("stderr") != "EMPTY":
        return False
    if probe_terminal is None or (
        probe_terminal.get("status") != terminal.get("status")
        or probe_terminal.get("exit_code") != exit_code
        or probe_terminal.get("report") != report
    ):
        return False
    if name_delete:
        return not any(
            stage in session_stages or stage in ITEM_ID_EVIDENCE_STAGES
            for stage in stages
        )

    state = {"FRESH": "NONE", "STALE": "NONE"}
    final_started = {"FRESH": False, "STALE": False}
    final_observed = {"FRESH": False, "STALE": False}
    cancel_started = {"FRESH": False, "STALE": False}
    partial_started = {"FRESH": False, "STALE": False}
    partial_observed: dict[str, dict[str, Any] | None] = {
        "FRESH": None,
        "STALE": None,
    }
    partial_validated = {"FRESH": False, "STALE": False}
    destination_verified = {"FRESH": False, "STALE": False}
    post_read_count = {"FRESH": 0, "STALE": 0}
    post_verify_count = {"FRESH": 0, "STALE": 0}
    for event in probe_events:
        stage = event["stage"]
        role = event.get("session_role")
        pending_cancellations = [
            pending_role
            for pending_role in ("FRESH", "STALE")
            if cancel_started[pending_role] and state[pending_role] == "OPEN"
        ]
        if pending_cancellations and not (
            len(pending_cancellations) == 1
            and stage == "SESSION_CANCEL_REQUEST_COMPLETED"
            and role == pending_cancellations[0]
        ):
            return False
        if stage == "SESSION_CREATE_REQUEST_STARTED":
            if state[role] != "NONE" or (role == "STALE" and state["FRESH"] != "CLOSED"):
                return False
            state[role] = "UNKNOWN"
        elif stage == "SESSION_AVAILABLE":
            if state[role] != "UNKNOWN":
                return False
            state[role] = "OPEN"
        elif stage == "PARTIAL_FRAGMENT_REQUEST_STARTED":
            if state[role] != "OPEN" or partial_started[role]:
                return False
            partial_started[role] = True
        elif stage == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED":
            if (
                schema_version != C2_SCHEMA_VERSION
                or not partial_started[role]
                or partial_observed[role] is not None
                or post_read_count[role] != 0
            ):
                return False
            partial_observed[role] = {
                "http_status": event["http_status"],
                "range_class": event["range_class"],
            }
        elif stage == "PARTIAL_FRAGMENT_RESPONSE_VALIDATED":
            if (
                not partial_started[role]
                or partial_validated[role]
                or (
                    schema_version == C2_SCHEMA_VERSION
                    and partial_observed[role]
                    != {"http_status": 202, "range_class": "EXPECTED_START"}
                )
            ):
                return False
            partial_validated[role] = True
        elif stage == "PARTIAL_DESTINATION_VERIFY_COMPLETED":
            if (
                not partial_started[role]
                or destination_verified[role]
                or post_verify_count[role] != 1
            ):
                return False
            destination_verified[role] = True
        elif stage == "FINAL_FRAGMENT_REQUEST_STARTED":
            if (
                state[role] != "OPEN"
                or final_started[role]
                or not partial_validated[role]
                or not destination_verified[role]
                or post_read_count[role] != 1
                or post_verify_count[role] != 1
            ):
                return False
            final_started[role] = True
        elif stage == "FINAL_FRAGMENT_RESPONSE_OBSERVED":
            if (
                not final_started[role]
                or final_observed[role]
                or post_read_count[role] != 1
            ):
                return False
            final_observed[role] = True
        elif stage == "POST_STATE_READ_STARTED":
            if (
                not partial_started[role]
                or post_read_count[role] != post_verify_count[role]
                or post_read_count[role] >= 2
                or (post_read_count[role] == 0 and final_started[role])
                or (post_read_count[role] == 1 and not final_started[role])
            ):
                return False
            post_read_count[role] += 1
        elif stage == "POST_STATE_VERIFY_COMPLETED":
            if post_read_count[role] != post_verify_count[role] + 1:
                return False
            post_verify_count[role] += 1
        elif stage == "SESSION_COMPLETION_PROVEN":
            if (
                state[role] != "OPEN"
                or not final_started[role]
                or not final_observed[role]
                or report.get(f"{role.lower()}_final_http_status") not in {200, 201}
                or post_verify_count[role] != 2
            ):
                return False
            state[role] = "CLOSED"
        elif stage == "SESSION_CANCEL_REQUEST_STARTED":
            if state[role] != "OPEN" or cancel_started[role]:
                return False
            cancel_started[role] = True
        elif stage == "SESSION_CANCEL_REQUEST_COMPLETED":
            if state[role] != "OPEN" or not cancel_started[role]:
                return False
            state[role] = "CLOSED"
    if not all(value in {"NONE", "CLOSED"} for value in state.values()):
        return False
    if any(
        post_read_count[role]
        != int(partial_started[role]) + int(final_started[role])
        for role in ("FRESH", "STALE")
    ):
        return False
    if any(
        final_observed[role]
        != (report.get(f"{role.lower()}_final_http_status") is not None)
        for role in ("FRESH", "STALE")
    ):
        return False
    if schema_version == C2_SCHEMA_VERSION:
        report_observations = report.get("partial_observations")
        if any(
            report_observations[role.lower()]
            != (
                partial_observed[role]
                or {"http_status": None, "range_class": "NOT_OBSERVED"}
            )
            for role in ("FRESH", "STALE")
        ):
            return False
    if report.get("outcome") in {
        "OBSERVED_SAFE_STALE_REJECTION",
        "UNSAFE_STALE_OVERWRITE",
    }:
        if not all(
            partial_validated[role]
            and destination_verified[role]
            and final_started[role]
            and post_verify_count[role] == 2
            for role in ("FRESH", "STALE")
        ):
            return False
        concurrent_indices = [
            index
            for index, stage in enumerate(stages)
            if stage == "CONCURRENT_WRITE_REQUEST_STARTED"
        ]
        if len(concurrent_indices) != 1:
            return False
        stale_partial_index = next(
            index
            for index, event in enumerate(probe_events)
            if event.get("stage") == "PARTIAL_DESTINATION_VERIFY_COMPLETED"
            and event.get("session_role") == "STALE"
        )
        stale_final_index = next(
            index
            for index, event in enumerate(probe_events)
            if event.get("stage") == "FINAL_FRAGMENT_REQUEST_STARTED"
            and event.get("session_role") == "STALE"
        )
        if not stale_partial_index < concurrent_indices[0] < stale_final_index:
            return False
    return True


def _v2_journal_cleanup_is_resolved(
    probe_events: list[dict[str, Any]],
    terminal: dict[str, Any],
    probe_terminal: dict[str, Any] | None,
) -> bool:
    return _c2_journal_cleanup_is_resolved(
        probe_events,
        terminal,
        probe_terminal,
        schema_version=V2_SCHEMA_VERSION,
    )


def _v3_journal_cleanup_is_resolved(
    probe_events: list[dict[str, Any]],
    terminal: dict[str, Any],
    probe_terminal: dict[str, Any] | None,
) -> bool:
    return _c2_journal_cleanup_is_resolved(
        probe_events,
        terminal,
        probe_terminal,
        schema_version=C2_SCHEMA_VERSION,
    )


def _python_fingerprint(python_executable: Path) -> dict[str, Any]:
    encoded_path = str(python_executable).encode("utf-8")
    return {
        "basename": python_executable.name,
        "exists": python_executable.exists(),
        "is_absolute": python_executable.is_absolute(),
        "is_file": python_executable.is_file(),
        "path_length": len(str(python_executable)),
        "path_sha256": _sha256_bytes(encoded_path),
        "version": platform.python_version(),
    }


class AttemptRecorder:
    """Atomically persist a bounded, append-in-state flight record."""

    def __init__(
        self,
        *,
        attempt_id: str,
        mode: str,
        evidence_directory: Path,
        forbidden: set[str],
        candidate: str,
    ) -> None:
        self.attempt_id = attempt_id
        self.mode = mode
        self.candidate = candidate
        self._forbidden = {value for value in forbidden if value}
        evidence_directory.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S.%fZ")
        self.path = evidence_directory / f"{timestamp}-{self.attempt_id}.json"
        self.journal_path = evidence_directory / f"{timestamp}-{self.attempt_id}.events.jsonl"
        python_executable = Path(sys.executable).resolve()
        self._record: dict[str, Any] = {
            "attempt_id": self.attempt_id,
            "candidate": self.candidate,
            "components": {
                "controller_sha256": _sha256_file_or_unavailable(CONTROLLER_PATH),
                "launcher_sha256": _sha256_file_or_unavailable(LAUNCHER_PATH),
                "probe_sha256": _sha256_file_or_unavailable(PROBE_PATH),
            },
            "cloud_configuration": "OUTSIDE_CONTROLLER_REQUIRES_SEPARATE_VERIFICATION",
            "dependencies": _dependency_versions(),
            "finished_at": None,
            "launcher": None,
            "launcher_invocation": None,
            "mode": mode,
            "network": "NOT_ATTEMPTED",
            "probe_stages": [],
            "repository": _repository_fingerprint(),
            "runtime": {
                "platform": sys.platform,
                "python": _python_fingerprint(python_executable),
            },
            "schema_version": C2_SCHEMA_VERSION,
            "stages": [],
            "started_at": _utc_now(),
            "status": "RUNNING",
        }
        self._append_journal(
            {
                "at": self._record["started_at"],
                "attempt_id": self.attempt_id,
                "candidate": self.candidate,
                "mode": mode,
                "record_type": "ATTEMPT_STARTED",
                "schema_version": C2_SCHEMA_VERSION,
            }
        )
        self._write()

    def add_forbidden(self, value: str | None) -> None:
        if value:
            self._forbidden.add(value)

    def event(self, stage: str, status: str, code: str | None = None) -> None:
        event: dict[str, Any] = {"at": _utc_now(), "stage": stage, "status": status}
        if code is not None:
            event["code"] = code
        self._record["stages"].append(event)
        self._append_journal(
            {"attempt_id": self.attempt_id, "record_type": "STAGE", **event}
        )
        self._write()

    def mark_network_attempted(self) -> None:
        self._record["network"] = "OAUTH_ATTEMPTED"
        self._append_journal(
            {
                "at": _utc_now(),
                "attempt_id": self.attempt_id,
                "network": "OAUTH_ATTEMPTED",
                "record_type": "NETWORK",
            }
        )
        self._write()

    def set_launcher_invocation(self, fingerprint: dict[str, Any]) -> None:
        self._record["launcher_invocation"] = fingerprint
        self._append_journal(
            {
                "at": _utc_now(),
                "attempt_id": self.attempt_id,
                "fingerprint": fingerprint,
                "record_type": "LAUNCHER_INVOCATION",
            }
        )
        self._write()

    def finish(
        self,
        *,
        status: str,
        failure_code: str | None = None,
        launcher_report: dict[str, Any] | None = None,
        launcher_exit_code: int | None = None,
        launcher_stderr: str | None = None,
        failure_details: dict[str, Any] | None = None,
    ) -> None:
        if not _valid_failure_details(failure_details):
            raise ControllerFailure("EVIDENCE_DETAILS_REJECTED", "EVIDENCE")
        self._capture_probe_stages()
        self._record["finished_at"] = _utc_now()
        self._record["status"] = status
        if failure_code is not None:
            self._record["failure_code"] = failure_code
        if failure_details is not None:
            self._record["failure_details"] = failure_details
        if launcher_report is not None or launcher_exit_code is not None:
            self._record["launcher"] = {
                "exit_code": launcher_exit_code,
                "report": launcher_report,
                "stderr": launcher_stderr,
            }
        self._append_journal(
            {
                "at": self._record["finished_at"],
                "attempt_id": self.attempt_id,
                "failure_code": failure_code,
                "failure_details": failure_details,
                "launcher": self._record["launcher"],
                "record_type": "ATTEMPT_FINISHED",
                "status": status,
            }
        )
        self._write()

    @property
    def network(self) -> str:
        return str(self._record["network"])

    def _write(self) -> None:
        serialized = json.dumps(
            self._record,
            ensure_ascii=True,
            indent=2,
            sort_keys=True,
        )
        if any(secret in serialized for secret in self._forbidden):
            raise ControllerFailure("EVIDENCE_REDACTION_REJECTED", "EVIDENCE")
        temporary_path = self.path.with_name(f".{self.path.name}.tmp")
        temporary_path.write_text(f"{serialized}\n", encoding="utf-8")
        os.replace(temporary_path, self.path)

    def _append_journal(self, entry: dict[str, Any]) -> None:
        serialized = json.dumps(entry, ensure_ascii=True, sort_keys=True)
        if any(secret in serialized for secret in self._forbidden):
            raise ControllerFailure("EVIDENCE_REDACTION_REJECTED", "EVIDENCE")
        with self.journal_path.open("a", encoding="utf-8", newline="\n") as journal:
            journal.write(f"{serialized}\n")
            journal.flush()
            os.fsync(journal.fileno())

    def _capture_probe_stages(self) -> None:
        captured: list[dict[str, Any]] = []
        try:
            lines = self.journal_path.read_text(encoding="utf-8").splitlines()
        except OSError:
            self._record["probe_stages"] = captured
            return
        for line in lines:
            try:
                entry = json.loads(line)
            except json.JSONDecodeError:
                continue
            if (
                isinstance(entry, dict)
                and entry.get("attempt_id") == self.attempt_id
                and entry.get("record_type") == "PROBE_STAGE"
                and entry.get("stage") in V3_PROBE_PROGRESS_STAGES
                and isinstance(entry.get("at"), str)
            ):
                captured_entry = {"at": entry["at"], "stage": entry["stage"]}
                if entry.get("session_role") in {"FRESH", "STALE"}:
                    captured_entry["session_role"] = entry["session_role"]
                if entry.get("stage") == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED":
                    captured_entry["http_status"] = entry.get("http_status")
                    captured_entry["range_class"] = entry.get("range_class")
                captured.append(captured_entry)
        self._record["probe_stages"] = captured


def build_launcher_command(
    *,
    node_executable: str,
    python_executable: str,
    self_test: bool,
    candidate: str,
) -> list[str]:
    command = [
        node_executable,
        str(LAUNCHER_PATH),
        "--python-executable",
        python_executable,
        "--candidate",
        candidate,
    ]
    if self_test:
        command.append("--self-test")
    else:
        command.extend(["--allow-live-write", "--cleanup-test-item"])
    return command


def _contains_forbidden(value: Any, forbidden: set[str]) -> bool:
    if isinstance(value, str):
        return any(secret and secret in value for secret in forbidden)
    if isinstance(value, dict):
        return any(_contains_forbidden(item, forbidden) for item in value.values())
    if isinstance(value, list):
        return any(_contains_forbidden(item, forbidden) for item in value)
    return False


def _validate_legacy_launcher_report(
    report: Any,
    *,
    self_test: bool,
    forbidden: set[str],
) -> bool:
    if not isinstance(report, dict) or _contains_forbidden(report, forbidden):
        return False
    if self_test:
        return report == SELF_TEST_REPORT
    if report.get("status") == "PASS":
        return (
            set(report) == SAFE_SUCCESS_KEYS
            and report.get("cleanup") == "DELETED_TO_RECYCLE_BIN"
            and report.get("fresh_conditional_commit") == "PASS"
            and report.get("stale_conditional_commit") == "HTTP_412_PASS"
            and report.get("stale_commit_http_status") == 412
            and report.get("item_identity_preserved") is True
            and report.get("concurrent_bytes_preserved") is True
            and report.get("isolated_item_created") is True
            and report.get("drive_type") == "personal"
            and report.get("provider") == "Microsoft Graph v1.0"
            and isinstance(report.get("checked_at"), str)
        )
    if report.get("status") != "FAIL" or not set(report).issubset(SAFE_FAILURE_KEYS):
        return False
    reason = report.get("reason")
    if (
        not isinstance(reason, str)
        or not reason
        or len(reason) > 512
        or "\n" in reason
        or "\r" in reason
    ):
        return False
    if "stage" in report and report["stage"] not in SAFE_LAUNCHER_STAGES:
        return False
    if "cleanup" in report and report["cleanup"] not in SAFE_CLEANUP_STATES:
        return False
    if "child_stderr" in report and report["child_stderr"] not in {
        "EMPTY",
        "PRESENT_SANITIZED",
    }:
        return False
    if "child_exit_code" in report and not (
        isinstance(report["child_exit_code"], int)
        and not isinstance(report["child_exit_code"], bool)
    ):
        return False
    if "http_status" in report and not (
        isinstance(report["http_status"], int)
        and not isinstance(report["http_status"], bool)
        and 100 <= report["http_status"] <= 599
    ):
        return False
    provider_code = report.get("provider_error_code")
    if provider_code is not None and not (
        isinstance(provider_code, str)
        and provider_code
        and len(provider_code) <= 64
        and provider_code[0].isalpha()
        and all(character.isalnum() or character in "._-" for character in provider_code)
    ):
        return False
    return True


def validate_launcher_report(
    report: Any,
    *,
    self_test: bool,
    forbidden: set[str],
    expected_candidate: str,
) -> bool:
    if not isinstance(report, dict) or _contains_forbidden(report, forbidden):
        return False
    if self_test:
        return report == SELF_TEST_REPORT and expected_candidate == C2_CANDIDATE
    if report.get("schema_version") == C2_SCHEMA_VERSION:
        inferred_exit_code = 0 if report.get("status") == "PASS" else 1
        return _validate_c2_probe_report(
            report,
            exit_code=inferred_exit_code,
            expected_candidate=expected_candidate,
        )
    return _validate_legacy_launcher_report(
        report,
        self_test=False,
        forbidden=forbidden,
    ) and report.get("status") == "FAIL"


def _resolve_node_executable() -> str:
    candidate = shutil.which("node")
    if not candidate:
        raise ControllerFailure("NODE_EXECUTABLE_UNAVAILABLE", "CONTROLLER_VALIDATION")
    resolved = Path(candidate).resolve()
    if not resolved.is_file():
        raise ControllerFailure("NODE_EXECUTABLE_UNAVAILABLE", "CONTROLLER_VALIDATION")
    return str(resolved)


def _prepare_launcher(self_test: bool, candidate: str) -> tuple[list[str], dict[str, Any]]:
    if not LAUNCHER_PATH.is_file() or not PROBE_PATH.is_file():
        raise ControllerFailure("PROBE_COMPONENT_UNAVAILABLE", "CONTROLLER_VALIDATION")
    python_executable = Path(sys.executable).resolve()
    if not python_executable.is_absolute() or not python_executable.is_file():
        raise ControllerFailure("PYTHON_EXECUTABLE_UNAVAILABLE", "CONTROLLER_VALIDATION")
    node_executable = _resolve_node_executable()
    try:
        node_version = subprocess.run(
            [node_executable, "--version"],
            check=True,
            capture_output=True,
            text=True,
            timeout=10,
        ).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        raise ControllerFailure(
            "NODE_VERSION_UNAVAILABLE",
            "CONTROLLER_VALIDATION",
        ) from None
    if not re.fullmatch(r"v[0-9]+(?:\.[0-9]+){1,3}", node_version):
        raise ControllerFailure("NODE_VERSION_UNAVAILABLE", "CONTROLLER_VALIDATION")
    command = build_launcher_command(
        node_executable=node_executable,
        python_executable=str(python_executable),
        self_test=self_test,
        candidate=candidate,
    )
    fingerprint = {
        "argv_count": len(command),
        "argv_shape": [
            "NODE_EXECUTABLE",
            "LAUNCHER_PATH",
            "--python-executable",
            "PYTHON_EXECUTABLE",
            "--candidate",
            C2_CANDIDATE,
            "--self-test" if self_test else "--allow-live-write",
            *([] if self_test else ["--cleanup-test-item"]),
        ],
        "cwd": "REPOSITORY_ROOT",
        "node": {
            "basename": Path(node_executable).name,
            "path_sha256": _sha256_bytes(node_executable.encode("utf-8")),
            "version": node_version,
        },
        "python_path_length": len(str(python_executable)),
        "python_path_sha256": _sha256_bytes(str(python_executable).encode("utf-8")),
        "shell": False,
    }
    return command, fingerprint


def _run_launcher(
    *,
    access_token: str,
    attempt_id: str,
    command: list[str],
    event_journal: Path,
    self_test: bool,
    forbidden: set[str],
    candidate: str,
) -> tuple[int, dict[str, Any], str]:
    child_environment = os.environ.copy()
    child_environment.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, None)
    child_environment[TOKEN_ENVIRONMENT_VARIABLE] = access_token
    child_environment[ATTEMPT_ID_ENVIRONMENT_VARIABLE] = attempt_id
    child_environment[EVENT_JOURNAL_ENVIRONMENT_VARIABLE] = str(event_journal)
    try:
        completed = subprocess.run(
            command,
            cwd=REPOSITORY_DIRECTORY,
            env=child_environment,
            check=False,
            capture_output=True,
            text=True,
            timeout=30 if self_test else None,
            shell=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise ControllerFailure(
            "LAUNCHER_TIMEOUT",
            "LAUNCHER",
            details={"timeout_seconds": 30},
        ) from exc
    except OSError as exc:
        raise ControllerFailure("LAUNCHER_START_FAILED", "LAUNCHER") from exc
    finally:
        child_environment.pop(TOKEN_ENVIRONMENT_VARIABLE, None)
        child_environment.pop(ATTEMPT_ID_ENVIRONMENT_VARIABLE, None)
        child_environment.pop(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, None)

    stderr_state = "PRESENT_SANITIZED" if completed.stderr else "EMPTY"
    lines = [line for line in completed.stdout.splitlines() if line]
    process_details = {
        "child_exit_code": completed.returncode,
        "stderr": stderr_state,
        "stdout_bytes": len(completed.stdout.encode("utf-8")),
        "stdout_line_count": len(lines),
    }
    if len(lines) != 1:
        raise ControllerFailure(
            "LAUNCHER_OUTPUT_REJECTED",
            "LAUNCHER",
            details=process_details,
        )
    try:
        report = json.loads(lines[0])
    except json.JSONDecodeError as exc:
        raise ControllerFailure(
            "LAUNCHER_OUTPUT_REJECTED",
            "LAUNCHER",
            details=process_details,
        ) from exc
    if not validate_launcher_report(
        report,
        self_test=self_test,
        forbidden=forbidden,
        expected_candidate=candidate,
    ):
        raise ControllerFailure(
            "LAUNCHER_OUTPUT_REJECTED",
            "LAUNCHER",
            details=process_details,
        )
    exit_matches_report = (
        completed.returncode == 0 if report.get("status") == "PASS" else completed.returncode != 0
    )
    if not exit_matches_report or completed.stderr:
        raise ControllerFailure(
            "LAUNCHER_PROCESS_REJECTED",
            "LAUNCHER",
            details=process_details,
        )
    return completed.returncode, report, stderr_state


class _CallbackHandler(BaseHTTPRequestHandler):
    callback_response: dict[str, str] | None = None

    def do_GET(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        parsed = urlsplit(self.path)
        if parsed.path != CALLBACK_PATH:
            self.send_response(404)
            self.end_headers()
            return
        self.send_response(405)
        self.send_header("Allow", "POST")
        self.end_headers()

    def do_POST(self) -> None:  # noqa: N802 - BaseHTTPRequestHandler contract
        parsed = urlsplit(self.path)
        if parsed.path != CALLBACK_PATH or parsed.query:
            self.send_response(404)
            self.end_headers()
            return
        content_type = self.headers.get("Content-Type", "").split(";", 1)[0].strip().lower()
        try:
            content_length = int(self.headers.get("Content-Length", ""))
        except ValueError:
            content_length = -1
        if (
            content_type != "application/x-www-form-urlencoded"
            or content_length < 1
            or content_length > MAX_CALLBACK_BODY_BYTES
        ):
            self.send_response(400)
            self.end_headers()
            return
        try:
            body = self.rfile.read(content_length).decode("utf-8", errors="strict")
            values = parse_qs(body, keep_blank_values=True, strict_parsing=True)
        except (UnicodeDecodeError, ValueError):
            self.send_response(400)
            self.end_headers()
            return
        if not values or any(len(candidates) != 1 for candidates in values.values()):
            self.send_response(400)
            self.end_headers()
            return
        type(self).callback_response = {
            key: candidates[0]
            for key, candidates in values.items()
            if isinstance(candidates[0], str)
        }
        body = (
            b"<!doctype html><html><body><h1>Authorization response received</h1>"
            b"<p>You can return to Codex. Do not refresh this page.</p></body></html>"
        )
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args: object) -> None:
        return


def _wait_for_callback(server: HTTPServer) -> dict[str, str]:
    _CallbackHandler.callback_response = None
    deadline = time.monotonic() + CALLBACK_TIMEOUT_SECONDS
    server.timeout = 1
    while time.monotonic() < deadline and _CallbackHandler.callback_response is None:
        server.handle_request()
    if _CallbackHandler.callback_response is None:
        raise ControllerFailure("OAUTH_CALLBACK_TIMEOUT", "OAUTH_CALLBACK")
    return _CallbackHandler.callback_response


def _acquire_live_access_token(*, client_id: str, client_secret: str) -> str:
    callback_response: dict[str, str] | None = None
    try:
        application = msal.ConfidentialClientApplication(
            client_id,
            authority=CONSUMER_AUTHORITY,
            client_credential=client_secret,
        )
        flow = application.initiate_auth_code_flow(
            scopes=GRAPH_SCOPES,
            redirect_uri=REDIRECT_URI,
            prompt="select_account",
            response_mode="form_post",
        )
        authorization_url = flow.get("auth_uri")
        if not isinstance(authorization_url, str):
            raise ControllerFailure("OAUTH_START_REJECTED", "OAUTH_START")
        with HTTPServer(("127.0.0.1", 8000), _CallbackHandler) as server:
            if not webbrowser.open(authorization_url, new=2):
                raise ControllerFailure("OAUTH_BROWSER_OPEN_FAILED", "OAUTH_START")
            callback_response = _wait_for_callback(server)
        try:
            has_code = isinstance(callback_response.get("code"), str) and bool(
                callback_response["code"]
            )
            has_error = isinstance(callback_response.get("error"), str) and bool(
                callback_response["error"]
            )
            if has_code == has_error:
                raise ControllerFailure(
                    "OAUTH_RESPONSE_MALFORMED",
                    "OAUTH_CALLBACK",
                    details=_normalize_oauth_diagnostics(
                        phase="CALLBACK_VALIDATION",
                        payload={},
                    ),
                )
            try:
                result = application.acquire_token_by_auth_code_flow(flow, callback_response)
            except ValueError as exc:
                raise ControllerFailure(
                    "OAUTH_FLOW_VALIDATION_FAILED",
                    "OAUTH",
                    details=_normalize_oauth_diagnostics(
                        phase="FLOW_VALIDATION",
                        payload={},
                    ),
                ) from exc
            if not isinstance(result, dict):
                raise ControllerFailure(
                    "OAUTH_RESULT_MALFORMED",
                    "TOKEN_VALIDATION",
                    details=_normalize_oauth_diagnostics(
                        phase="RESULT_VALIDATION",
                        payload={},
                    ),
                )
            if "error" in result:
                phase = "AUTHORIZATION_RESPONSE" if has_error else "TOKEN_REDEMPTION"
                code = (
                    "OAUTH_AUTHORIZATION_REJECTED"
                    if has_error
                    else "OAUTH_TOKEN_REDEMPTION_REJECTED"
                )
                raise ControllerFailure(
                    code,
                    "OAUTH" if has_error else "TOKEN_VALIDATION",
                    details=_normalize_oauth_diagnostics(phase=phase, payload=result),
                )
        finally:
            callback_response.clear()
            _CallbackHandler.callback_response = None
    except ControllerFailure:
        raise
    except Exception as exc:
        raise ControllerFailure("OAUTH_FLOW_FAILED", "OAUTH") from exc

    claims = result.get("id_token_claims") or {}
    subject = claims.get("sub")
    if (
        claims.get("iss") != CONSUMER_ISSUER
        or claims.get("tid") != CONSUMER_TENANT_ID
        or claims.get("aud") != client_id
        or not isinstance(subject, str)
        or not subject.strip()
    ):
        raise ControllerFailure("OAUTH_ACCOUNT_REJECTED", "TOKEN_VALIDATION")
    access_token = result.get("access_token")
    granted_scopes = frozenset(str(result.get("scope", "")).split())
    if not isinstance(access_token, str) or "Files.ReadWrite" not in granted_scopes:
        raise ControllerFailure("OAUTH_SCOPE_REJECTED", "TOKEN_VALIDATION")
    return access_token


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--self-test", action="store_true")
    mode.add_argument("--live", action="store_true")
    parser.add_argument("--allow-live-write", action="store_true")
    parser.add_argument("--cleanup-test-item", action="store_true")
    parser.add_argument("--candidate", choices=[C2_CANDIDATE], required=True)
    parser.add_argument(
        "--evidence-directory",
        type=Path,
        default=DEFAULT_EVIDENCE_DIRECTORY,
    )
    return parser.parse_args(argv)


def run(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    attempt_id = str(uuid4())
    mode = "SELF_TEST" if args.self_test else "LIVE"
    evidence_directory = args.evidence_directory.resolve()
    sensitive_environment_values = {
        os.environ.get(CLIENT_SECRET_ENVIRONMENT_VARIABLE, ""),
        os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, ""),
    }
    if args.self_test:
        sensitive_environment_values.add(SELF_TEST_SENTINEL)
    if args.live and evidence_directory != DEFAULT_EVIDENCE_DIRECTORY.resolve():
        os.environ.pop(TOKEN_ENVIRONMENT_VARIABLE, None)
        os.environ.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, None)
        print(
            json.dumps(
                {
                    "attempt_id": attempt_id,
                    "evidence_file": None,
                    "failure_code": "LIVE_EVIDENCE_DIRECTORY_REJECTED",
                    "mode": mode,
                    "network": "NOT_ATTEMPTED",
                    "status": "FAIL",
                },
                sort_keys=True,
            )
        )
        return 1
    try:
        unresolved_prior_attempt = args.live and _has_unresolved_prior_live_attempt(
            evidence_directory
        )
    except OSError:
        unresolved_prior_attempt = True
    if unresolved_prior_attempt:
        os.environ.pop(TOKEN_ENVIRONMENT_VARIABLE, None)
        os.environ.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, None)
        print(
            json.dumps(
                {
                    "attempt_id": attempt_id,
                    "evidence_file": None,
                    "failure_code": "UNRESOLVED_PRIOR_ATTEMPT",
                    "mode": mode,
                    "network": "NOT_ATTEMPTED",
                    "status": "FAIL",
                },
                sort_keys=True,
            )
        )
        return 1
    try:
        recorder = AttemptRecorder(
            attempt_id=attempt_id,
            mode=mode,
            evidence_directory=evidence_directory,
            forbidden=sensitive_environment_values,
            candidate=args.candidate,
        )
    except (ControllerFailure, OSError):
        os.environ.pop(TOKEN_ENVIRONMENT_VARIABLE, None)
        os.environ.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, None)
        print(
            json.dumps(
                {
                    "attempt_id": attempt_id,
                    "evidence_file": None,
                    "failure_code": "EVIDENCE_INITIALIZATION_FAILED",
                    "mode": mode,
                    "network": "NOT_ATTEMPTED",
                    "status": "FAIL",
                },
                sort_keys=True,
            )
        )
        return 1
    access_token: str | None = None
    launcher_report: dict[str, Any] | None = None
    launcher_exit_code: int | None = None
    launcher_stderr: str | None = None
    launcher_command: list[str] | None = None
    try:
        recorder.event("CONTROLLER_VALIDATION", "STARTED")
        if args.self_test and (args.allow_live_write or args.cleanup_test_item):
            raise ControllerFailure("SELF_TEST_FLAGS_REJECTED", "CONTROLLER_VALIDATION")
        if args.live and not (args.allow_live_write and args.cleanup_test_item):
            raise ControllerFailure("LIVE_ACKNOWLEDGEMENTS_REQUIRED", "CONTROLLER_VALIDATION")
        launcher_command, launcher_fingerprint = _prepare_launcher(
            args.self_test,
            args.candidate,
        )
        recorder.set_launcher_invocation(launcher_fingerprint)
        recorder.event("CONTROLLER_VALIDATION", "PASS")

        if args.self_test:
            access_token = SELF_TEST_SENTINEL
        else:
            client_id = os.environ.get(CLIENT_ID_ENVIRONMENT_VARIABLE, "")
            client_secret = os.environ.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, "")
            recorder.add_forbidden(client_secret)
            if client_id != EXPECTED_CLIENT_ID or not client_secret:
                raise ControllerFailure("OAUTH_CONFIGURATION_REJECTED", "CONTROLLER_VALIDATION")
            recorder.mark_network_attempted()
            recorder.event("OAUTH", "STARTED")
            access_token = _acquire_live_access_token(
                client_id=client_id,
                client_secret=client_secret,
            )
            client_secret = ""
            recorder.add_forbidden(access_token)
            recorder.event("OAUTH", "PASS")

        recorder.event("LAUNCHER", "STARTED")
        launcher_exit_code, launcher_report, launcher_stderr = _run_launcher(
            access_token=access_token,
            attempt_id=recorder.attempt_id,
            command=launcher_command,
            event_journal=recorder.journal_path,
            self_test=args.self_test,
            forbidden={access_token},
            candidate=args.candidate,
        )
        launcher_status = "PASS" if launcher_report["status"] == "PASS" else "FAIL"
        recorder.event("LAUNCHER", launcher_status)
        recorder.finish(
            status=launcher_status,
            failure_code=None if launcher_status == "PASS" else "PROBE_REPORTED_FAILURE",
            launcher_report=launcher_report,
            launcher_exit_code=launcher_exit_code,
            launcher_stderr=launcher_stderr,
        )
        output = {
            "attempt_id": recorder.attempt_id,
            "evidence_file": recorder.path.name,
            "mode": recorder.mode,
            "network": recorder.network,
            "status": launcher_status,
        }
        print(json.dumps(output, sort_keys=True))
        return 0 if launcher_status == "PASS" else 1
    except ControllerFailure as exc:
        try:
            recorder.event(exc.stage, "FAIL", exc.code)
            recorder.finish(
                status="FAIL",
                failure_code=exc.code,
                failure_details=exc.details,
                launcher_report=launcher_report,
                launcher_exit_code=launcher_exit_code,
                launcher_stderr=launcher_stderr,
            )
        except ControllerFailure:
            pass
        output = {
            "attempt_id": recorder.attempt_id,
            "evidence_file": recorder.path.name,
            "failure_code": exc.code,
            "mode": recorder.mode,
            "network": recorder.network,
            "status": "FAIL",
        }
        print(json.dumps(output, sort_keys=True))
        return 1
    except Exception:
        failure_code = "UNEXPECTED_CONTROLLER_FAILURE"
        try:
            recorder.event("CONTROLLER", "FAIL", failure_code)
            recorder.finish(status="FAIL", failure_code=failure_code)
        except (ControllerFailure, OSError):
            pass
        output = {
            "attempt_id": recorder.attempt_id,
            "evidence_file": recorder.path.name,
            "failure_code": failure_code,
            "mode": recorder.mode,
            "network": recorder.network,
            "status": "FAIL",
        }
        print(json.dumps(output, sort_keys=True))
        return 1
    finally:
        access_token = None
        os.environ.pop(TOKEN_ENVIRONMENT_VARIABLE, None)
        os.environ.pop(CLIENT_SECRET_ENVIRONMENT_VARIABLE, None)


if __name__ == "__main__":
    raise SystemExit(run())
