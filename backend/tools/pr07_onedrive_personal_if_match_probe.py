"""Live OneDrive Personal conditional-final-commit conformance probe.

This operator-only tool is deliberately separate from the Valora runtime. It creates one
isolated test item, verifies a fresh conditional commit, verifies rejection of a stale final
commit, and removes the test item. Provider identifiers, eTags, upload URLs, tokens, and file
contents are never included in its report.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import secrets
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_ENVIRONMENT_VARIABLE = "VALORA_PR07_GRAPH_ACCESS_TOKEN"
C2_CANDIDATE = "C2_AUTO_V2"
C2_SCHEMA_VERSION = 3
ATTEMPT_ID_ENVIRONMENT_VARIABLE = "VALORA_PR07_ATTEMPT_ID"
EVENT_JOURNAL_ENVIRONMENT_VARIABLE = "VALORA_PR07_EVENT_JOURNAL"
TEST_ITEM_PREFIX = "VALORA-PR07-IF-MATCH-"
FRAGMENT_BYTES = 320 * 1024
PROBE_PAYLOAD_BYTES = FRAGMENT_BYTES * 2
MAX_DOWNLOAD_BYTES = PROBE_PAYLOAD_BYTES
MAX_DOWNLOAD_REDIRECTS = 3
SAFE_PROVIDER_ERROR_CODE = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}")
SAFE_ATTEMPT_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
SAFE_NEXT_EXPECTED_RANGE = re.compile(r"(0|[1-9][0-9]*)-(0|[1-9][0-9]*)?")
MAX_NEXT_EXPECTED_RANGES = 16
MAX_NEXT_EXPECTED_RANGE_LENGTH = 64
PROGRESS_STAGES = {
    "CONCURRENT_WRITE_REQUEST_STARTED",
    "CONTENT_DOWNLOAD_REQUEST_STARTED",
    "DRIVE_VERIFY_REQUEST_STARTED",
    "ITEM_CREATE_REQUEST_STARTED",
    "PARTIAL_DESTINATION_VERIFY_COMPLETED",
    "PARTIAL_FRAGMENT_REQUEST_STARTED",
    "PARTIAL_FRAGMENT_RESPONSE_VALIDATED",
    "POST_STATE_READ_STARTED",
    "POST_STATE_VERIFY_COMPLETED",
    "PROBE_SELF_TEST_STARTED",
    "PROBE_STARTED",
    "FINAL_FRAGMENT_REQUEST_STARTED",
    "FINAL_FRAGMENT_RESPONSE_OBSERVED",
    "SESSION_AVAILABLE",
    "SESSION_COMPLETION_PROVEN",
    "SESSION_CREATE_REQUEST_STARTED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED",
    "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    "TEST_ITEM_DELETE_REQUEST_STARTED",
    "SESSION_CANCEL_REQUEST_COMPLETED",
    "SESSION_CANCEL_REQUEST_STARTED",
}
SESSION_PROGRESS_STAGES = {
    "FINAL_FRAGMENT_REQUEST_STARTED",
    "FINAL_FRAGMENT_RESPONSE_OBSERVED",
    "PARTIAL_DESTINATION_VERIFY_COMPLETED",
    "PARTIAL_FRAGMENT_REQUEST_STARTED",
    "PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
    "PARTIAL_FRAGMENT_RESPONSE_VALIDATED",
    "POST_STATE_READ_STARTED",
    "POST_STATE_VERIFY_COMPLETED",
    "SESSION_AVAILABLE",
    "SESSION_CANCEL_REQUEST_COMPLETED",
    "SESSION_CANCEL_REQUEST_STARTED",
    "SESSION_COMPLETION_PROVEN",
    "SESSION_CREATE_REQUEST_STARTED",
}
C2_REPORT_KEYS = {
    "schema_version", "candidate", "runtime_gate", "checked_at", "status",
    "outcome", "reason_code", "phase", "fresh_final_http_status",
    "stale_final_http_status", "provider_error_code", "checks", "cleanup",
    "cleanup_issue", "partial_observations",
}
C2_CHECK_KEYS = {
    "fresh_partial_preserved", "fresh_commit_verified", "stale_partial_preserved",
    "concurrent_write_verified", "item_identity_preserved",
    "concurrent_bytes_preserved", "concurrent_etag_preserved",
    "stale_candidate_observed",
}
C2_OUTCOMES = {
    "OBSERVED_SAFE_STALE_REJECTION", "UNSAFE_STALE_OVERWRITE",
    "SAFETY_VIOLATION", "INCONCLUSIVE",
}
C2_REASON_CODES = {
    "SAFE_412", "STALE_BYTES_OVERWROTE_CONCURRENT", "NONFINAL_MUTATION",
    "IDENTITY_CHANGED", "RESPONSE_IDENTITY_MISMATCH", "ALTERNATE_REJECTION",
    "FINAL_NOT_COMPLETED", "TRANSPORT_UNKNOWN", "POST_STATE_UNAVAILABLE",
    "POST_STATE_INCONSISTENT", "THIRD_STATE", "FRESH_CONTROL_FAILED",
    "RACE_SETUP_FAILED", "SESSION_CREATION_FAILED", "FIXTURE_FAILED",
    "UNEXPECTED_SANITIZED_FAILURE", "PARTIAL_HTTP_UNEXPECTED",
    "PARTIAL_RANGE_MISSING", "PARTIAL_RANGE_MALFORMED",
    "PARTIAL_RANGE_UNEXPECTED",
}
C2_PHASES = {"FIXTURE", "FRESH", "STALE", "COMPLETE"}
C2_PROVIDER_ERROR_CODES = {
    "accessDenied", "invalidRequest", "invalidRange", "nameAlreadyExists",
    "resourceModified", "itemNotFound", "quotaLimitReached", "tooManyRequests",
    "generalException", "unknown",
}
C2_CLEANUP_ISSUES = {
    "NONE", "SESSION_UNKNOWN", "CANCEL_FAILED", "ITEM_DELETE_FAILED",
    "EVIDENCE_INCOMPLETE", "MULTIPLE",
}
SAFE_CLEANUP_STATES = {
    "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
    "DELETED_TO_RECYCLE_BIN",
    "FAILED",
    "NOT_ATTEMPTED",
}
PARTIAL_RANGE_CLASSES = {
    "EXPECTED_START",
    "MALFORMED",
    "MISSING",
    "NOT_APPLICABLE",
    "NOT_OBSERVED",
    "UNEXPECTED_START",
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


class ProbeFailure(RuntimeError):
    """Sanitized failure that must not contain provider response bodies or secrets."""

    def __init__(
        self,
        message: str,
        *,
        http_status: int | None = None,
        provider_error_code: str | None = None,
        cleanup: str | None = None,
    ) -> None:
        super().__init__(message)
        self.http_status = http_status
        self.provider_error_code = provider_error_code
        self.cleanup = cleanup

    def with_cleanup(self, cleanup: str) -> ProbeFailure:
        return ProbeFailure(
            str(self),
            http_status=self.http_status,
            provider_error_code=self.provider_error_code,
            cleanup=cleanup,
        )

    def as_report(self) -> dict[str, str | int]:
        report: dict[str, str | int] = {"status": "FAIL", "reason": str(self)}
        if self.http_status is not None:
            report["http_status"] = self.http_status
        if self.provider_error_code is not None:
            report["provider_error_code"] = self.provider_error_code
        if self.cleanup is not None:
            report["cleanup"] = self.cleanup
        return report


def _diagnostic_journal() -> tuple[str, Path] | None:
    attempt_id = os.environ.get(ATTEMPT_ID_ENVIRONMENT_VARIABLE, "")
    journal_value = os.environ.get(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, "")
    if not attempt_id and not journal_value:
        return None
    journal_path = Path(journal_value)
    if (
        not SAFE_ATTEMPT_ID.fullmatch(attempt_id)
        or not journal_path.is_absolute()
        or not journal_path.is_file()
        or not journal_path.name.endswith(".events.jsonl")
    ):
        raise ProbeFailure("Diagnostic evidence is unavailable.")
    return attempt_id, journal_path


def _append_journal_entry(entry: dict[str, Any]) -> None:
    diagnostic = _diagnostic_journal()
    if diagnostic is None:
        return
    attempt_id, journal_path = diagnostic
    bounded_entry = {"at": datetime.now(UTC).isoformat(), "attempt_id": attempt_id, **entry}
    try:
        with journal_path.open("a", encoding="utf-8", newline="\n") as journal:
            journal.write(
                f"{json.dumps(bounded_entry, ensure_ascii=True, sort_keys=True)}\n"
            )
            journal.flush()
            os.fsync(journal.fileno())
    except OSError as exc:
        raise ProbeFailure("Diagnostic evidence is unavailable.") from exc


def _record_progress(stage: str, *, session_role: str | None = None) -> None:
    if stage not in PROGRESS_STAGES:
        raise ProbeFailure("Diagnostic progress stage is invalid.")
    if (stage in SESSION_PROGRESS_STAGES) != (session_role in {"FRESH", "STALE"}):
        raise ProbeFailure("Diagnostic session role is invalid.")
    entry = {"record_type": "PROBE_STAGE", "stage": stage}
    if session_role is not None:
        entry["session_role"] = session_role
    _append_journal_entry(entry)


def _best_effort_record_progress(stage: str, *, session_role: str | None = None) -> bool:
    try:
        _record_progress(stage, session_role=session_role)
    except ProbeFailure:
        return False
    return True


def _record_partial_observation(
    *, session_role: str, http_status: int, range_class: str
) -> None:
    if (
        session_role not in {"FRESH", "STALE"}
        or isinstance(http_status, bool)
        or not isinstance(http_status, int)
        or not 100 <= http_status <= 599
        or range_class not in PARTIAL_RANGE_CLASSES - {"NOT_OBSERVED"}
        or (range_class == "NOT_APPLICABLE" and http_status == 202)
        or (range_class != "NOT_APPLICABLE" and http_status != 202)
    ):
        raise ProbeFailure("Diagnostic partial observation is invalid.")
    _append_journal_entry(
        {
            "record_type": "PROBE_STAGE",
            "stage": "PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
            "session_role": session_role,
            "http_status": http_status,
            "range_class": range_class,
        }
    )


def _best_effort_record_partial_observation(
    *, session_role: str, http_status: int, range_class: str
) -> bool:
    try:
        _record_partial_observation(
            session_role=session_role,
            http_status=http_status,
            range_class=range_class,
        )
    except ProbeFailure:
        return False
    return True


def _classify_next_expected_ranges(
    value: Any,
    *,
    expected_start: int = FRAGMENT_BYTES,
    total: int = PROBE_PAYLOAD_BYTES,
) -> str:
    if value is None or value == []:
        return "MISSING"
    if (
        not isinstance(value, list)
        or not 1 <= len(value) <= MAX_NEXT_EXPECTED_RANGES
        or isinstance(expected_start, bool)
        or isinstance(total, bool)
        or not isinstance(expected_start, int)
        or not isinstance(total, int)
        or not 0 <= expected_start < total
    ):
        return "MALFORMED"

    parsed: list[tuple[int, int]] = []
    unexpected_start = False
    for candidate in value:
        if (
            not isinstance(candidate, str)
            or len(candidate) > MAX_NEXT_EXPECTED_RANGE_LENGTH
        ):
            return "MALFORMED"
        match = SAFE_NEXT_EXPECTED_RANGE.fullmatch(candidate)
        if match is None:
            return "MALFORMED"
        start = int(match.group(1))
        end = total - 1 if match.group(2) is None else int(match.group(2))
        unexpected_start |= start < expected_start or start >= total
        if end < start or end >= total:
            if unexpected_start:
                return "UNEXPECTED_START"
            return "MALFORMED"
        parsed.append((start, end))

    if parsed[0][0] != expected_start or unexpected_start:
        return "UNEXPECTED_START"

    ordered = sorted(parsed)
    if any(start <= previous_end for (_, previous_end), (start, _) in zip(ordered, ordered[1:])):
        return "MALFORMED"
    return "EXPECTED_START"


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
        if (
            http_status is not None
            and (
                isinstance(http_status, bool)
                or not isinstance(http_status, int)
                or not 100 <= http_status <= 599
            )
        ):
            return False
        if range_class not in PARTIAL_RANGE_CLASSES:
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


def _valid_diagnostic_report(report: Any, exit_code: int) -> bool:
    if not isinstance(report, dict) or isinstance(exit_code, bool):
        return False
    if report == SELF_TEST_REPORT:
        return exit_code == 0
    if set(report) != C2_REPORT_KEYS:
        return False
    checks = report.get("checks")
    if not isinstance(checks, dict) or set(checks) != C2_CHECK_KEYS:
        return False
    if any(value is not None and type(value) is not bool for value in checks.values()):
        return False
    if report.get("schema_version") != C2_SCHEMA_VERSION or report.get("candidate") != C2_CANDIDATE:
        return False
    if report.get("runtime_gate") != "BLOCKED" or report.get("status") not in {"PASS", "FAIL"}:
        return False
    checked_at_value = report.get("checked_at")
    if not isinstance(checked_at_value, str) or len(checked_at_value) > 64:
        return False
    try:
        checked_at = datetime.fromisoformat(checked_at_value)
    except (TypeError, ValueError):
        return False
    if checked_at.tzinfo is None:
        return False
    if report.get("outcome") not in C2_OUTCOMES or report.get("reason_code") not in C2_REASON_CODES:
        return False
    if report.get("phase") not in C2_PHASES or report.get("cleanup") not in SAFE_CLEANUP_STATES:
        return False
    if report.get("cleanup_issue") not in C2_CLEANUP_ISSUES:
        return False
    for key in ("fresh_final_http_status", "stale_final_http_status"):
        value = report.get(key)
        if value is not None and (isinstance(value, bool) or not isinstance(value, int) or not 100 <= value <= 599):
            return False
    if report.get("provider_error_code") not in C2_PROVIDER_ERROR_CODES | {None}:
        return False
    partial_observations = report.get("partial_observations")
    if not _valid_partial_observations(partial_observations):
        return False
    partial_reason_class = {
        "PARTIAL_HTTP_UNEXPECTED": "NOT_APPLICABLE",
        "PARTIAL_RANGE_MALFORMED": "MALFORMED",
        "PARTIAL_RANGE_MISSING": "MISSING",
        "PARTIAL_RANGE_UNEXPECTED": "UNEXPECTED_START",
    }.get(report.get("reason_code"))
    if partial_reason_class is not None and (
        report.get("phase") not in {"FRESH", "STALE"}
        or partial_observations[report["phase"].lower()]["range_class"]
        != partial_reason_class
    ):
        return False
    safe = (
        report["outcome"] == "OBSERVED_SAFE_STALE_REJECTION"
        and report["reason_code"] == "SAFE_412"
        and report["phase"] == "COMPLETE"
        and report["fresh_final_http_status"] in {200, 201}
        and report["stale_final_http_status"] == 412
        and partial_observations["fresh"] == {
            "http_status": 202,
            "range_class": "EXPECTED_START",
        }
        and partial_observations["stale"] == {
            "http_status": 202,
            "range_class": "EXPECTED_START",
        }
        and all(checks[key] is True for key in C2_CHECK_KEYS - {"stale_candidate_observed"})
        and checks["stale_candidate_observed"] is False
    )
    unsafe = (
        report["outcome"] == "UNSAFE_STALE_OVERWRITE"
        and report["reason_code"] == "STALE_BYTES_OVERWROTE_CONCURRENT"
        and checks["fresh_commit_verified"] is True
        and checks["concurrent_write_verified"] is True
        and checks["item_identity_preserved"] is True
        and checks["stale_candidate_observed"] is True
        and checks["concurrent_bytes_preserved"] is False
        and partial_observations["fresh"] == {
            "http_status": 202,
            "range_class": "EXPECTED_START",
        }
        and partial_observations["stale"] == {
            "http_status": 202,
            "range_class": "EXPECTED_START",
        }
    )
    if report["outcome"] == "OBSERVED_SAFE_STALE_REJECTION" and not safe:
        return False
    if report["outcome"] == "UNSAFE_STALE_OVERWRITE" and not unsafe:
        return False
    expected_pass = safe and report["cleanup"] == "DELETED_TO_RECYCLE_BIN" and report["cleanup_issue"] == "NONE"
    if (report["status"] == "PASS") != expected_pass:
        return False
    if (exit_code == 0) != expected_pass:
        return False
    return True


def _record_probe_result(report: dict[str, Any], exit_code: int) -> None:
    token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "")
    serialized = json.dumps(report, ensure_ascii=True, sort_keys=True)
    if not _valid_diagnostic_report(report, exit_code) or (token and token in serialized):
        raise ProbeFailure("Diagnostic evidence was rejected.")
    _append_journal_entry(
        {
            "exit_code": exit_code,
            "record_type": "PROBE_FINISHED",
            "report": report,
            "status": report.get("status"),
        }
    )


def _best_effort_record_probe_result(report: dict[str, Any], exit_code: int) -> None:
    try:
        _record_probe_result(report, exit_code)
    except ProbeFailure:
        pass


@dataclass(frozen=True)
class ItemState:
    item_id: str
    name: str
    e_tag: str


@dataclass(frozen=True)
class ProbeReport:
    schema_version: int
    candidate: str
    runtime_gate: str
    checked_at: str
    status: str
    outcome: str
    reason_code: str
    phase: str
    fresh_final_http_status: int | None
    stale_final_http_status: int | None
    provider_error_code: str | None
    partial_observations: dict[str, dict[str, int | str | None]]
    checks: dict[str, bool | None]
    cleanup: str
    cleanup_issue: str


def _payload(label: bytes) -> bytes:
    seed = label + b":" + secrets.token_bytes(32)
    repeats = (PROBE_PAYLOAD_BYTES // len(seed)) + 1
    return (seed * repeats)[:PROBE_PAYLOAD_BYTES]


def _test_item_name() -> str:
    attempt_id = os.environ.get(ATTEMPT_ID_ENVIRONMENT_VARIABLE, "")
    if SAFE_ATTEMPT_ID.fullmatch(attempt_id):
        return f"{TEST_ITEM_PREFIX}{attempt_id}.bin"
    return f"{TEST_ITEM_PREFIX}{secrets.token_hex(8)}.bin"


def _require_https_without_credentials(url: str) -> str:
    parsed = urlparse(url)
    if (
        parsed.scheme != "https"
        or not parsed.hostname
        or parsed.username is not None
        or parsed.password is not None
    ):
        raise ProbeFailure("Microsoft Graph returned an unsafe provider URL.")
    return url


class OneDrivePersonalIfMatchProbe:
    def __init__(
        self,
        *,
        access_token: str,
        client: httpx.Client | None = None,
        graph_base_url: str = GRAPH_BASE_URL,
    ) -> None:
        if not access_token.strip():
            raise ProbeFailure(f"{TOKEN_ENVIRONMENT_VARIABLE} is required.")
        self._access_token = access_token
        self._client = client or httpx.Client(timeout=30.0, follow_redirects=False)
        self._owns_client = client is None
        self._graph_base_url = graph_base_url.rstrip("/")

    def close(self) -> None:
        if self._owns_client:
            self._client.close()

    @property
    def _authorization_headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._access_token}"}

    def _graph_request(self, method: str, path: str, **kwargs: Any) -> httpx.Response:
        headers = dict(kwargs.pop("headers", {}))
        headers.update(self._authorization_headers)
        try:
            return self._client.request(
                method,
                f"{self._graph_base_url}{path}",
                headers=headers,
                **kwargs,
            )
        except httpx.HTTPError as exc:
            raise ProbeFailure("Microsoft Graph is unavailable.") from exc

    @staticmethod
    def _provider_error_code(response: httpx.Response) -> str | None:
        try:
            payload = response.json()
        except ValueError:
            return None
        if not isinstance(payload, dict):
            return None
        error = payload.get("error")
        if not isinstance(error, dict):
            return None
        candidate = error.get("code")
        if isinstance(candidate, str) and SAFE_PROVIDER_ERROR_CODE.fullmatch(candidate):
            return candidate
        return None

    @staticmethod
    def _json_object(response: httpx.Response, *, operation: str) -> dict[str, Any]:
        if response.status_code in {401, 403}:
            raise ProbeFailure(
                f"{operation} was denied; delegated Files.ReadWrite is required.",
                http_status=response.status_code,
            )
        if response.status_code >= 400:
            raise ProbeFailure(
                f"{operation} failed with HTTP {response.status_code}.",
                http_status=response.status_code,
                provider_error_code=OneDrivePersonalIfMatchProbe._provider_error_code(response),
            )
        try:
            payload = response.json()
        except ValueError as exc:
            raise ProbeFailure(f"{operation} returned invalid JSON.") from exc
        if not isinstance(payload, dict):
            raise ProbeFailure(f"{operation} returned an invalid object.")
        return payload

    @staticmethod
    def _item_state(payload: dict[str, Any]) -> ItemState:
        values = (payload.get("id"), payload.get("name"), payload.get("eTag"))
        if not all(isinstance(value, str) and value for value in values):
            raise ProbeFailure("Microsoft Graph item metadata is incomplete.")
        return ItemState(
            item_id=values[0],
            name=values[1],
            e_tag=values[2],
        )

    def _drive(self) -> str:
        response = self._graph_request("GET", "/me/drive", params={"$select": "id,driveType"})
        payload = self._json_object(response, operation="Drive verification")
        drive_id = payload.get("id")
        if payload.get("driveType") != "personal" or not isinstance(drive_id, str) or not drive_id:
            raise ProbeFailure("The delegated account is not OneDrive Personal.")
        return drive_id

    def _create_item(self, *, drive_id: str, name: str, content: bytes) -> ItemState:
        safe_drive = quote(drive_id, safe="")
        safe_name = quote(name, safe="")
        response = self._graph_request(
            "PUT",
            f"/drives/{safe_drive}/root:/{safe_name}:/content",
            headers={"Content-Type": "application/octet-stream"},
            content=content,
        )
        return self._item_state(self._json_object(response, operation="Test item creation"))

    def _get_item(self, *, drive_id: str, item_id: str) -> ItemState:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        response = self._graph_request(
            "GET",
            f"/drives/{safe_drive}/items/{safe_item}",
            params={"$select": "id,name,eTag,parentReference"},
        )
        return self._item_state(self._json_object(response, operation="Item verification"))

    def _download(self, *, drive_id: str, item_id: str) -> bytes:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        url = f"{self._graph_base_url}/drives/{safe_drive}/items/{safe_item}/content"
        headers = self._authorization_headers
        for redirect_count in range(MAX_DOWNLOAD_REDIRECTS + 1):
            try:
                with self._client.stream("GET", url, headers=headers) as response:
                    if response.status_code in {301, 302, 303, 307, 308}:
                        if redirect_count == MAX_DOWNLOAD_REDIRECTS:
                            raise ProbeFailure("Content download redirected too many times.")
                        location = response.headers.get("location")
                        if not location:
                            raise ProbeFailure("Content download returned an invalid redirect.")
                        url = _require_https_without_credentials(
                            urljoin(str(response.request.url), location)
                        )
                        headers = {}
                        continue
                    if response.status_code >= 400:
                        raise ProbeFailure(
                            f"Content download failed with HTTP {response.status_code}."
                        )
                    declared_length = response.headers.get("content-length")
                    if declared_length is not None:
                        try:
                            if int(declared_length) > MAX_DOWNLOAD_BYTES:
                                raise ProbeFailure("Content download exceeded the probe bound.")
                        except ValueError as exc:
                            raise ProbeFailure("Content download length is invalid.") from exc
                    chunks: list[bytes] = []
                    total = 0
                    for chunk in response.iter_bytes():
                        total += len(chunk)
                        if total > MAX_DOWNLOAD_BYTES:
                            raise ProbeFailure("Content download exceeded the probe bound.")
                        chunks.append(chunk)
                    return b"".join(chunks)
            except httpx.HTTPError:
                raise ProbeFailure("Content download is unavailable.") from None
        raise ProbeFailure("Content download failed.")

    def _create_upload_session(
        self,
        *,
        drive_id: str,
        item_id: str,
        e_tag: str,
    ) -> str:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        response = self._graph_request(
            "POST",
            f"/drives/{safe_drive}/items/{safe_item}/createUploadSession",
            headers={"Content-Type": "application/json", "If-Match": e_tag},
            json={},
        )
        payload = self._json_object(response, operation="Upload-session creation")
        upload_url = payload.get("uploadUrl")
        if not isinstance(upload_url, str) or not upload_url:
            raise ProbeFailure("Upload-session creation returned no upload URL.")
        return _require_https_without_credentials(upload_url)

    def _upload_fragment(
        self,
        *,
        upload_url: str,
        content: bytes,
        start: int,
        total: int,
    ) -> httpx.Response:
        if len(content) != FRAGMENT_BYTES or total != PROBE_PAYLOAD_BYTES or start not in {0, FRAGMENT_BYTES}:
            raise ProbeFailure("Upload fragment shape is invalid.")
        try:
            return self._client.put(
                upload_url,
                headers={
                    "Content-Length": str(len(content)),
                    "Content-Range": f"bytes {start}-{start + len(content) - 1}/{total}",
                },
                content=content,
            )
        except httpx.HTTPError:
            raise

    def _read_coherent_item(self, *, drive_id: str, item_id: str) -> tuple[ItemState, bytes]:
        before = self._get_item(drive_id=drive_id, item_id=item_id)
        _record_progress("CONTENT_DOWNLOAD_REQUEST_STARTED")
        content = self._download(drive_id=drive_id, item_id=item_id)
        after = self._get_item(drive_id=drive_id, item_id=item_id)
        if before.item_id != after.item_id or before.e_tag != after.e_tag:
            raise ProbeFailure("Post-state metadata was inconsistent.")
        return after, content

    def _overwrite(
        self,
        *,
        drive_id: str,
        item_id: str,
        e_tag: str,
        content: bytes,
    ) -> ItemState:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        response = self._graph_request(
            "PUT",
            f"/drives/{safe_drive}/items/{safe_item}/content",
            headers={
                "Content-Type": "application/octet-stream",
                "If-Match": e_tag,
            },
            content=content,
        )
        return self._item_state(self._json_object(response, operation="Concurrent test write"))

    def _cancel_session(self, upload_url: str) -> None:
        try:
            response = self._client.delete(upload_url, headers={})
        except httpx.HTTPError:
            raise ProbeFailure("Upload-session cleanup is unavailable.") from None
        if response.status_code not in {204, 404}:
            raise ProbeFailure(f"Upload-session cleanup failed with HTTP {response.status_code}.")

    def _delete_item(self, *, drive_id: str, item_id: str) -> None:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        response = self._graph_request("DELETE", f"/drives/{safe_drive}/items/{safe_item}")
        if response.status_code != 204:
            raise ProbeFailure(f"Test item cleanup failed with HTTP {response.status_code}.")

    def _delete_item_by_name(self, *, drive_id: str, name: str) -> None:
        safe_drive = quote(drive_id, safe="")
        safe_name = quote(name, safe="")
        response = self._graph_request("DELETE", f"/drives/{safe_drive}/root:/{safe_name}")
        if response.status_code not in {204, 404}:
            raise ProbeFailure(f"Test item cleanup failed with HTTP {response.status_code}.")

    def run(self) -> ProbeReport:
        checks: dict[str, bool | None] = {key: None for key in C2_CHECK_KEYS}
        phase = "FIXTURE"
        outcome = "INCONCLUSIVE"
        reason_code = "UNEXPECTED_SANITIZED_FAILURE"
        fresh_status: int | None = None
        stale_status: int | None = None
        provider_error_code: str | None = None
        partial_observations: dict[str, dict[str, int | str | None]] = {
            "fresh": {"http_status": None, "range_class": "NOT_OBSERVED"},
            "stale": {"http_status": None, "range_class": "NOT_OBSERVED"},
        }
        cleanup = "NOT_ATTEMPTED"
        cleanup_issues: set[str] = set()
        drive_id: str | None = None
        original = _payload(b"original")
        fresh_candidate = _payload(b"fresh-candidate")
        stale_candidate = _payload(b"stale-candidate")
        concurrent = _payload(b"concurrent")
        name = _test_item_name()
        item: ItemState | None = None
        open_sessions: dict[str, str] = {}
        creation_attempted = False

        def classify_read_failure(exc: Exception) -> str:
            return "POST_STATE_INCONSISTENT" if "inconsistent" in str(exc).lower() else "POST_STATE_UNAVAILABLE"

        def record_after_dispatch(stage: str, *, session_role: str | None = None) -> None:
            if not _best_effort_record_progress(stage, session_role=session_role):
                cleanup_issues.add("EVIDENCE_INCOMPLETE")

        def partial_preserved(role: str, expected_state: ItemState, expected_bytes: bytes) -> bool:
            nonlocal outcome, reason_code, phase
            record_after_dispatch("POST_STATE_READ_STARTED", session_role=role)
            try:
                state, content = self._read_coherent_item(drive_id=drive_id or "", item_id=expected_state.item_id)
            except Exception as exc:
                reason_code = classify_read_failure(exc)
                return False
            record_after_dispatch("POST_STATE_VERIFY_COMPLETED", session_role=role)
            identity_ok = state.item_id == expected_state.item_id
            preserved = identity_ok and state.e_tag == expected_state.e_tag and content == expected_bytes
            checks["fresh_partial_preserved" if role == "FRESH" else "stale_partial_preserved"] = preserved
            if not identity_ok:
                outcome, reason_code = "SAFETY_VIOLATION", "IDENTITY_CHANGED"
            elif not preserved:
                outcome, reason_code = "SAFETY_VIOLATION", "NONFINAL_MUTATION"
            return preserved

        def upload_partial(role: str, upload_url: str, candidate: bytes, expected_state: ItemState, expected_bytes: bytes) -> bool:
            nonlocal reason_code
            _record_progress("PARTIAL_FRAGMENT_REQUEST_STARTED", session_role=role)
            invalid_reason = "TRANSPORT_UNKNOWN"
            try:
                response = self._upload_fragment(
                    upload_url=upload_url,
                    content=candidate[:FRAGMENT_BYTES],
                    start=0,
                    total=PROBE_PAYLOAD_BYTES,
                )
                observation = partial_observations[role.lower()]
                observation["http_status"] = response.status_code
                valid_response = False
                if response.status_code == 202:
                    try:
                        payload = response.json()
                    except ValueError:
                        payload = None
                    range_class = _classify_next_expected_ranges(
                        payload.get("nextExpectedRanges")
                        if isinstance(payload, dict)
                        else "INVALID_JSON"
                    )
                    invalid_reason = {
                        "MALFORMED": "PARTIAL_RANGE_MALFORMED",
                        "MISSING": "PARTIAL_RANGE_MISSING",
                        "UNEXPECTED_START": "PARTIAL_RANGE_UNEXPECTED",
                    }.get(range_class, "FINAL_NOT_COMPLETED")
                    valid_response = range_class == "EXPECTED_START"
                else:
                    range_class = "NOT_APPLICABLE"
                    invalid_reason = "PARTIAL_HTTP_UNEXPECTED"
                observation["range_class"] = range_class
                if not _best_effort_record_partial_observation(
                    session_role=role,
                    http_status=response.status_code,
                    range_class=range_class,
                ):
                    cleanup_issues.add("EVIDENCE_INCOMPLETE")
                if valid_response:
                    record_after_dispatch("PARTIAL_FRAGMENT_RESPONSE_VALIDATED", session_role=role)
            except httpx.HTTPError:
                valid_response = False
            preserved = partial_preserved(role, expected_state, expected_bytes)
            if preserved:
                record_after_dispatch("PARTIAL_DESTINATION_VERIFY_COMPLETED", session_role=role)
            if (
                not valid_response
                and outcome != "SAFETY_VIOLATION"
                and reason_code
                not in {"POST_STATE_INCONSISTENT", "POST_STATE_UNAVAILABLE"}
            ):
                reason_code = invalid_reason
            return valid_response and preserved

        try:
            _record_progress("PROBE_STARTED")
            _record_progress("DRIVE_VERIFY_REQUEST_STARTED")
            drive_id = self._drive()
            creation_attempted = True
            _record_progress("ITEM_CREATE_REQUEST_STARTED")
            item = self._create_item(drive_id=drive_id, name=name, content=original)
            try:
                fixture_state, fixture_bytes = self._read_coherent_item(drive_id=drive_id, item_id=item.item_id)
            except Exception:
                reason_code = "FIXTURE_FAILED"
                raise ProbeFailure("Fixture verification failed.")
            if fixture_state.item_id != item.item_id or fixture_state.e_tag != item.e_tag or fixture_bytes != original:
                reason_code = "FIXTURE_FAILED"
                raise ProbeFailure("Fixture verification failed.")

            phase = "FRESH"
            _record_progress("SESSION_CREATE_REQUEST_STARTED", session_role="FRESH")
            try:
                fresh_url = self._create_upload_session(
                    drive_id=drive_id, item_id=item.item_id, e_tag=item.e_tag
                )
            except Exception:
                cleanup_issues.add("SESSION_UNKNOWN")
                reason_code = "SESSION_CREATION_FAILED"
                raise ProbeFailure("Fresh upload-session creation failed.")
            open_sessions["FRESH"] = fresh_url
            _record_progress("SESSION_AVAILABLE", session_role="FRESH")
            if not upload_partial("FRESH", fresh_url, fresh_candidate, item, original):
                raise ProbeFailure("Fresh partial fragment was not safely staged.")

            _record_progress("FINAL_FRAGMENT_REQUEST_STARTED", session_role="FRESH")
            fresh_response: httpx.Response | None = None
            try:
                fresh_response = self._upload_fragment(
                    upload_url=fresh_url,
                    content=fresh_candidate[FRAGMENT_BYTES:],
                    start=FRAGMENT_BYTES,
                    total=PROBE_PAYLOAD_BYTES,
                )
                fresh_status = fresh_response.status_code
                provider_error_code = self._provider_error_code(fresh_response)
                record_after_dispatch("FINAL_FRAGMENT_RESPONSE_OBSERVED", session_role="FRESH")
            except httpx.HTTPError:
                reason_code = "TRANSPORT_UNKNOWN"
            record_after_dispatch("POST_STATE_READ_STARTED", session_role="FRESH")
            try:
                fresh_state, fresh_bytes = self._read_coherent_item(drive_id=drive_id, item_id=item.item_id)
                record_after_dispatch("POST_STATE_VERIFY_COMPLETED", session_role="FRESH")
            except Exception as exc:
                reason_code = classify_read_failure(exc)
                raise ProbeFailure("Fresh post-state could not be verified.")
            if fresh_state.item_id != item.item_id:
                outcome, reason_code = "SAFETY_VIOLATION", "IDENTITY_CHANGED"
                checks["item_identity_preserved"] = False
                raise ProbeFailure("Fresh item identity changed.")
            response_identity_ok = False
            if fresh_response is not None and fresh_status in {200, 201}:
                try:
                    response_identity_ok = self._item_state(fresh_response.json()).item_id == item.item_id
                except (ValueError, ProbeFailure):
                    response_identity_ok = False
            fresh_verified = (
                fresh_status in {200, 201}
                and response_identity_ok
                and fresh_bytes == fresh_candidate
                and fresh_state.e_tag != item.e_tag
            )
            checks["fresh_commit_verified"] = fresh_verified
            if not fresh_verified:
                reason_code = "RESPONSE_IDENTITY_MISMATCH" if fresh_status in {200, 201} and not response_identity_ok else "FRESH_CONTROL_FAILED"
                raise ProbeFailure("Fresh control failed.")
            _record_progress("SESSION_COMPLETION_PROVEN", session_role="FRESH")
            open_sessions.pop("FRESH", None)

            phase = "STALE"
            _record_progress("SESSION_CREATE_REQUEST_STARTED", session_role="STALE")
            try:
                stale_url = self._create_upload_session(
                    drive_id=drive_id, item_id=item.item_id, e_tag=fresh_state.e_tag
                )
            except Exception:
                cleanup_issues.add("SESSION_UNKNOWN")
                reason_code = "SESSION_CREATION_FAILED"
                raise ProbeFailure("Stale upload-session creation failed.")
            open_sessions["STALE"] = stale_url
            _record_progress("SESSION_AVAILABLE", session_role="STALE")
            if not upload_partial("STALE", stale_url, stale_candidate, fresh_state, fresh_candidate):
                raise ProbeFailure("Stale partial fragment was not safely staged.")

            _record_progress("CONCURRENT_WRITE_REQUEST_STARTED")
            concurrent_state = self._overwrite(
                drive_id=drive_id,
                item_id=item.item_id,
                e_tag=fresh_state.e_tag,
                content=concurrent,
            )
            try:
                race_state, race_bytes = self._read_coherent_item(drive_id=drive_id, item_id=item.item_id)
            except Exception:
                reason_code = "RACE_SETUP_FAILED"
                raise ProbeFailure("Race setup verification failed.")
            race_ok = (
                concurrent_state.item_id == item.item_id
                and race_state.item_id == item.item_id
                and race_state.e_tag == concurrent_state.e_tag
                and race_state.e_tag != fresh_state.e_tag
                and race_bytes == concurrent
            )
            checks["concurrent_write_verified"] = race_ok
            if not race_ok:
                reason_code = "RACE_SETUP_FAILED"
                raise ProbeFailure("Race setup was not proven.")

            _record_progress("FINAL_FRAGMENT_REQUEST_STARTED", session_role="STALE")
            stale_response: httpx.Response | None = None
            try:
                stale_response = self._upload_fragment(
                    upload_url=stale_url,
                    content=stale_candidate[FRAGMENT_BYTES:],
                    start=FRAGMENT_BYTES,
                    total=PROBE_PAYLOAD_BYTES,
                )
                stale_status = stale_response.status_code
                provider_error_code = self._provider_error_code(stale_response)
                record_after_dispatch("FINAL_FRAGMENT_RESPONSE_OBSERVED", session_role="STALE")
            except httpx.HTTPError:
                reason_code = "TRANSPORT_UNKNOWN"
            record_after_dispatch("POST_STATE_READ_STARTED", session_role="STALE")
            try:
                final_state, final_bytes = self._read_coherent_item(drive_id=drive_id, item_id=item.item_id)
                record_after_dispatch("POST_STATE_VERIFY_COMPLETED", session_role="STALE")
            except Exception as exc:
                reason_code = classify_read_failure(exc)
                raise ProbeFailure("Stale post-state could not be verified.")
            identity_preserved = final_state.item_id == item.item_id
            concurrent_preserved = final_bytes == concurrent
            stale_observed = final_bytes == stale_candidate
            etag_preserved = final_state.e_tag == race_state.e_tag
            checks.update(
                item_identity_preserved=identity_preserved,
                concurrent_bytes_preserved=concurrent_preserved,
                concurrent_etag_preserved=etag_preserved,
                stale_candidate_observed=stale_observed,
            )
            phase = "COMPLETE"
            if stale_observed and identity_preserved:
                outcome, reason_code = "UNSAFE_STALE_OVERWRITE", "STALE_BYTES_OVERWROTE_CONCURRENT"
                stale_response_identity_ok = False
                if stale_response is not None and stale_status in {200, 201}:
                    try:
                        stale_response_identity_ok = (
                            self._item_state(stale_response.json()).item_id == item.item_id
                        )
                    except (ValueError, ProbeFailure):
                        stale_response_identity_ok = False
                if stale_status in {200, 201} and stale_response_identity_ok:
                    _record_progress("SESSION_COMPLETION_PROVEN", session_role="STALE")
                    open_sessions.pop("STALE", None)
            elif not identity_preserved:
                outcome, reason_code = "SAFETY_VIOLATION", "IDENTITY_CHANGED"
            elif stale_status == 412 and concurrent_preserved and etag_preserved:
                outcome, reason_code = "OBSERVED_SAFE_STALE_REJECTION", "SAFE_412"
            elif final_bytes not in {concurrent, stale_candidate}:
                outcome, reason_code = "INCONCLUSIVE", "THIRD_STATE"
            elif concurrent_preserved and not etag_preserved:
                outcome, reason_code = "INCONCLUSIVE", "POST_STATE_INCONSISTENT"
            elif stale_status is None:
                outcome, reason_code = "INCONCLUSIVE", "TRANSPORT_UNKNOWN"
            elif stale_status != 412:
                outcome, reason_code = "INCONCLUSIVE", "ALTERNATE_REJECTION"
            else:
                outcome, reason_code = "INCONCLUSIVE", "FINAL_NOT_COMPLETED"
        except ProbeFailure:
            pass
        except Exception:
            reason_code = "UNEXPECTED_SANITIZED_FAILURE"
        finally:
            cleanup_evidence_failed = False
            for role, upload_url in list(open_sessions.items()):
                try:
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "SESSION_CANCEL_REQUEST_STARTED", session_role=role
                    )
                    self._cancel_session(upload_url)
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "SESSION_CANCEL_REQUEST_COMPLETED", session_role=role
                    )
                except ProbeFailure:
                    cleanup_issues.add("CANCEL_FAILED")
                except Exception:
                    cleanup_issues.add("CANCEL_FAILED")
            try:
                if item is not None and drive_id is not None:
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "TEST_ITEM_DELETE_REQUEST_STARTED"
                    )
                    self._delete_item(drive_id=drive_id, item_id=item.item_id)
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "TEST_ITEM_DELETE_REQUEST_COMPLETED"
                    )
                    cleanup = "DELETED_TO_RECYCLE_BIN"
                elif creation_attempted:
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED"
                    )
                    self._delete_item_by_name(drive_id=drive_id, name=name)
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"
                    )
                    cleanup = "ABSENT_OR_DELETED_TO_RECYCLE_BIN"
            except ProbeFailure:
                cleanup = "FAILED"
                cleanup_issues.add("ITEM_DELETE_FAILED")
            except Exception:
                cleanup = "FAILED"
                cleanup_issues.add("ITEM_DELETE_FAILED")
            if cleanup_evidence_failed:
                cleanup_issues.add("EVIDENCE_INCOMPLETE")
        cleanup_issue = "NONE" if not cleanup_issues else next(iter(cleanup_issues)) if len(cleanup_issues) == 1 else "MULTIPLE"
        return self._finalize_report(
            outcome, reason_code, phase, fresh_status, stale_status,
            provider_error_code, partial_observations, checks, cleanup, cleanup_issue,
        )

    @staticmethod
    def _finalize_report(
        outcome: str,
        reason_code: str,
        phase: str,
        fresh_status: int | None,
        stale_status: int | None,
        provider_error_code: str | None,
        partial_observations: dict[str, dict[str, int | str | None]],
        checks: dict[str, bool | None],
        cleanup: str,
        cleanup_issue: str,
    ) -> ProbeReport:
        if provider_error_code not in C2_PROVIDER_ERROR_CODES:
            provider_error_code = "unknown" if provider_error_code is not None else None
        passed = (
            outcome == "OBSERVED_SAFE_STALE_REJECTION"
            and cleanup == "DELETED_TO_RECYCLE_BIN"
            and cleanup_issue == "NONE"
        )
        return ProbeReport(
            schema_version=C2_SCHEMA_VERSION,
            candidate=C2_CANDIDATE,
            runtime_gate="BLOCKED",
            checked_at=datetime.now(UTC).isoformat(),
            status="PASS" if passed else "FAIL",
            outcome=outcome,
            reason_code=reason_code,
            phase=phase,
            fresh_final_http_status=fresh_status,
            stale_final_http_status=stale_status,
            provider_error_code=provider_error_code,
            partial_observations=partial_observations,
            checks=checks,
            cleanup=cleanup,
            cleanup_issue=cleanup_issue,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--self-test",
        action="store_true",
        help="Verify the local module launch surface without constructing a client.",
    )
    parser.add_argument(
        "--allow-live-write",
        action="store_true",
        help="Acknowledge creation and mutation of one isolated OneDrive Personal test item.",
    )
    parser.add_argument(
        "--cleanup-test-item",
        action="store_true",
        help="Acknowledge moving the isolated test item to the OneDrive recycle bin.",
    )
    parser.add_argument("--candidate", choices=[C2_CANDIDATE], required=True)
    return parser.parse_args(argv)


def _run_self_test() -> int:
    if not os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "").strip():
        raise ProbeFailure(
            f"{TOKEN_ENVIRONMENT_VARIABLE} is required for self-test."
        )
    if Path.cwd().resolve() != Path(__file__).resolve().parents[1]:
        raise ProbeFailure("Self-test must be run from the backend directory.")
    _record_progress("PROBE_SELF_TEST_STARTED")
    report = SELF_TEST_REPORT.copy()
    _best_effort_record_probe_result(report, 0)
    print(json.dumps(report, sort_keys=True))
    return 0


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.self_test and (args.allow_live_write or args.cleanup_test_item):
        raise ProbeFailure("Self-test cannot be combined with live-write flags.")
    if args.self_test:
        return _run_self_test()
    if not args.allow_live_write or not args.cleanup_test_item:
        raise ProbeFailure(
            "Both --allow-live-write and --cleanup-test-item are required before network access."
        )
    if _diagnostic_journal() is None:
        raise ProbeFailure("Live execution requires controller diagnostic evidence.")
    access_token = os.environ.get(TOKEN_ENVIRONMENT_VARIABLE, "")
    probe = OneDrivePersonalIfMatchProbe(access_token=access_token)
    try:
        report = probe.run()
        serialized_report = asdict(report)
        exit_code = 0 if report.status == "PASS" else 1
        _best_effort_record_probe_result(serialized_report, exit_code)
        print(json.dumps(serialized_report, sort_keys=True))
        return exit_code
    finally:
        probe.close()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ProbeFailure as exc:
        report = exc.as_report()
        _best_effort_record_probe_result(report, 1)
        print(json.dumps(report, sort_keys=True))
        raise SystemExit(1) from None
    except Exception:
        report = {"status": "FAIL", "reason": "Unexpected sanitized probe failure."}
        _best_effort_record_probe_result(report, 1)
        print(json.dumps(report, sort_keys=True))
        raise SystemExit(1) from None
