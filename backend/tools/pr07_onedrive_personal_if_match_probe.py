"""Live OneDrive Personal conditional-final-commit conformance probe.

This operator-only tool is deliberately separate from the Valora runtime. It creates one
isolated test item, verifies a fresh conditional commit, verifies rejection of a stale final
commit, and removes the test item. Provider identifiers, eTags, upload URLs, tokens, and file
contents are never included in its report.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import secrets
from dataclasses import asdict, dataclass, replace
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from urllib.parse import quote, urljoin, urlparse

import httpx


GRAPH_BASE_URL = "https://graph.microsoft.com/v1.0"
TOKEN_ENVIRONMENT_VARIABLE = "VALORA_PR07_GRAPH_ACCESS_TOKEN"
ATTEMPT_ID_ENVIRONMENT_VARIABLE = "VALORA_PR07_ATTEMPT_ID"
EVENT_JOURNAL_ENVIRONMENT_VARIABLE = "VALORA_PR07_EVENT_JOURNAL"
TEST_ITEM_PREFIX = "VALORA-PR07-IF-MATCH-"
PROBE_PAYLOAD_BYTES = 320 * 1024
MAX_DOWNLOAD_BYTES = PROBE_PAYLOAD_BYTES * 2
MAX_DOWNLOAD_REDIRECTS = 3
SAFE_PROVIDER_ERROR_CODE = re.compile(r"[A-Za-z][A-Za-z0-9._-]{0,63}")
SAFE_ATTEMPT_ID = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}")
PROGRESS_STAGES = {
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
SAFE_FAILURE_REPORT_KEYS = {
    "cleanup",
    "http_status",
    "provider_error_code",
    "reason",
    "status",
}
SAFE_SUCCESS_REPORT_KEYS = {
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
SAFE_CLEANUP_STATES = {
    "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
    "DELETED_TO_RECYCLE_BIN",
    "FAILED",
    "NOT_ATTEMPTED",
}
SELF_TEST_REPORT = {
    "dependency_import": "PASS",
    "environment": "PRESENT",
    "interpreter": "PASS",
    "mode": "SELF_TEST",
    "network": "NOT_ATTEMPTED",
    "package_resolution": "PASS",
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


def _record_progress(stage: str) -> None:
    if stage not in PROGRESS_STAGES:
        raise ProbeFailure("Diagnostic progress stage is invalid.")
    _append_journal_entry({"record_type": "PROBE_STAGE", "stage": stage})


def _best_effort_record_progress(stage: str) -> bool:
    try:
        _record_progress(stage)
    except ProbeFailure:
        return False
    return True


def _valid_diagnostic_report(report: Any, exit_code: int) -> bool:
    if not isinstance(report, dict) or isinstance(exit_code, bool):
        return False
    if report == SELF_TEST_REPORT:
        return exit_code == 0
    if report.get("status") == "PASS":
        return (
            exit_code == 0
            and set(report) == SAFE_SUCCESS_REPORT_KEYS
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
        or not set(report).issubset(SAFE_FAILURE_REPORT_KEYS)
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
        and SAFE_PROVIDER_ERROR_CODE.fullmatch(provider_code)
    ):
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
    status: str
    checked_at: str
    provider: str
    drive_type: str
    isolated_item_created: bool
    fresh_conditional_commit: str
    stale_conditional_commit: str
    stale_commit_http_status: int
    item_identity_preserved: bool
    concurrent_bytes_preserved: bool
    cleanup: str


def _payload(label: bytes) -> bytes:
    seed = label + b":" + secrets.token_bytes(32)
    repeats = (PROBE_PAYLOAD_BYTES // len(seed)) + 1
    return (seed * repeats)[:PROBE_PAYLOAD_BYTES]


def _sha256(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


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
            json={"deferCommit": True},
        )
        payload = self._json_object(response, operation="Upload-session creation")
        upload_url = payload.get("uploadUrl")
        if not isinstance(upload_url, str) or not upload_url:
            raise ProbeFailure("Upload-session creation returned no upload URL.")
        return _require_https_without_credentials(upload_url)

    def _stage(self, *, upload_url: str, content: bytes) -> None:
        try:
            response = self._client.put(
                upload_url,
                headers={
                    "Content-Length": str(len(content)),
                    "Content-Range": f"bytes 0-{len(content) - 1}/{len(content)}",
                },
                content=content,
            )
        except httpx.HTTPError:
            raise ProbeFailure("Upload-session staging is unavailable.") from None
        if response.status_code != 202:
            raise ProbeFailure(
                "OneDrive Personal did not keep the deferCommit upload staged "
                f"(HTTP {response.status_code})."
            )
        payload = self._json_object(response, operation="Upload-session staging")
        if not isinstance(payload.get("nextExpectedRanges"), list):
            raise ProbeFailure("Upload-session staging returned invalid range state.")

    def _commit(
        self,
        *,
        drive_id: str,
        item_id: str,
        upload_url: str,
        e_tag: str,
    ) -> httpx.Response:
        safe_drive = quote(drive_id, safe="")
        safe_item = quote(item_id, safe="")
        return self._graph_request(
            "PUT",
            f"/drives/{safe_drive}/items/{safe_item}",
            headers={"Content-Type": "application/json", "If-Match": e_tag},
            params={"@microsoft.graph.conflictBehavior": "fail"},
            json={"@microsoft.graph.sourceUrl": upload_url},
        )

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
        _record_progress("PROBE_STARTED")
        _record_progress("DRIVE_VERIFY_REQUEST_STARTED")
        drive_id = self._drive()
        original = _payload(b"original")
        fresh_candidate = _payload(b"fresh-candidate")
        stale_candidate = _payload(b"stale-candidate")
        concurrent = _payload(b"concurrent")
        name = _test_item_name()
        item: ItemState | None = None
        open_session: str | None = None
        report: ProbeReport | None = None
        creation_attempted = False
        cleanup = "NOT_ATTEMPTED"
        primary_failure: ProbeFailure | None = None
        cleanup_failures: list[str] = []
        try:
            creation_attempted = True
            _record_progress("ITEM_CREATE_REQUEST_STARTED")
            item = self._create_item(drive_id=drive_id, name=name, content=original)

            _record_progress("FRESH_UPLOAD_SESSION_REQUEST_STARTED")
            open_session = self._create_upload_session(
                drive_id=drive_id,
                item_id=item.item_id,
                e_tag=item.e_tag,
            )
            _record_progress("UPLOAD_STAGE_REQUEST_STARTED")
            self._stage(upload_url=open_session, content=fresh_candidate)
            _record_progress("INITIAL_ITEM_VERIFY_REQUEST_STARTED")
            staged_state = self._get_item(drive_id=drive_id, item_id=item.item_id)
            _record_progress("CONTENT_DOWNLOAD_REQUEST_STARTED")
            if (
                staged_state.item_id != item.item_id
                or staged_state.e_tag != item.e_tag
                or _sha256(self._download(drive_id=drive_id, item_id=item.item_id))
                != _sha256(original)
            ):
                raise ProbeFailure("deferCommit changed the destination before final commit.")
            _record_progress("FRESH_FINAL_COMMIT_REQUEST_STARTED")
            fresh_response = self._commit(
                drive_id=drive_id,
                item_id=item.item_id,
                upload_url=open_session,
                e_tag=item.e_tag,
            )
            if fresh_response.status_code not in {200, 201}:
                raise ProbeFailure(
                    "Fresh conditional final commit failed with "
                    f"HTTP {fresh_response.status_code}.",
                    http_status=fresh_response.status_code,
                    provider_error_code=self._provider_error_code(fresh_response),
                )
            open_session = None
            _record_progress("FRESH_ITEM_VERIFY_REQUEST_STARTED")
            fresh_state = self._get_item(drive_id=drive_id, item_id=item.item_id)
            _record_progress("CONTENT_DOWNLOAD_REQUEST_STARTED")
            if fresh_state.item_id != item.item_id or _sha256(
                self._download(drive_id=drive_id, item_id=item.item_id)
            ) != _sha256(fresh_candidate):
                raise ProbeFailure(
                    "Fresh final commit did not preserve exact-item identity and bytes."
                )

            _record_progress("STALE_UPLOAD_SESSION_REQUEST_STARTED")
            open_session = self._create_upload_session(
                drive_id=drive_id,
                item_id=item.item_id,
                e_tag=fresh_state.e_tag,
            )
            _record_progress("UPLOAD_STAGE_REQUEST_STARTED")
            self._stage(upload_url=open_session, content=stale_candidate)
            _record_progress("CONCURRENT_WRITE_REQUEST_STARTED")
            concurrent_state = self._overwrite(
                drive_id=drive_id,
                item_id=item.item_id,
                e_tag=fresh_state.e_tag,
                content=concurrent,
            )
            if concurrent_state.e_tag == fresh_state.e_tag:
                raise ProbeFailure("The concurrent test write did not advance the item eTag.")
            _record_progress("STALE_FINAL_COMMIT_REQUEST_STARTED")
            stale_response = self._commit(
                drive_id=drive_id,
                item_id=item.item_id,
                upload_url=open_session,
                e_tag=fresh_state.e_tag,
            )
            if stale_response.status_code != 412:
                raise ProbeFailure(
                    "Stale conditional final commit was not rejected with HTTP 412 "
                    f"(received HTTP {stale_response.status_code}).",
                    http_status=stale_response.status_code,
                    provider_error_code=self._provider_error_code(stale_response),
                )
            _record_progress("STALE_ITEM_VERIFY_REQUEST_STARTED")
            final_state = self._get_item(drive_id=drive_id, item_id=item.item_id)
            _record_progress("CONTENT_DOWNLOAD_REQUEST_STARTED")
            identity_preserved = final_state.item_id == item.item_id
            concurrent_preserved = _sha256(
                self._download(drive_id=drive_id, item_id=item.item_id)
            ) == _sha256(concurrent)
            if not identity_preserved or not concurrent_preserved:
                raise ProbeFailure("The stale candidate changed the exact destination item.")
            report = ProbeReport(
                status="PASS",
                checked_at=datetime.now(UTC).isoformat(),
                provider="Microsoft Graph v1.0",
                drive_type="personal",
                isolated_item_created=True,
                fresh_conditional_commit="PASS",
                stale_conditional_commit="HTTP_412_PASS",
                stale_commit_http_status=stale_response.status_code,
                item_identity_preserved=identity_preserved,
                concurrent_bytes_preserved=concurrent_preserved,
                cleanup="PENDING",
            )
        except ProbeFailure as exc:
            primary_failure = exc
        except Exception:
            primary_failure = ProbeFailure("Unexpected sanitized probe failure.")
        finally:
            cleanup_evidence_failed = False
            if open_session is not None:
                try:
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "UPLOAD_SESSION_CANCEL_REQUEST_STARTED"
                    )
                    self._cancel_session(open_session)
                    cleanup_evidence_failed |= not _best_effort_record_progress(
                        "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED"
                    )
                except ProbeFailure as exc:
                    cleanup_failures.append(str(exc))
                except Exception:
                    cleanup_failures.append("Upload-session cleanup failed unexpectedly.")
            try:
                if item is not None:
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
            except ProbeFailure as exc:
                cleanup_failures.append(str(exc))
            except Exception:
                cleanup_failures.append("Test item cleanup failed unexpectedly.")
            if cleanup_evidence_failed:
                cleanup_failures.append("Diagnostic cleanup evidence is unavailable.")
        if cleanup_failures:
            cleanup_message = " ".join(cleanup_failures)
            if primary_failure is not None:
                raise ProbeFailure(
                    f"{primary_failure} Cleanup also failed: {cleanup_message}",
                    http_status=primary_failure.http_status,
                    provider_error_code=primary_failure.provider_error_code,
                    cleanup="FAILED",
                )
            raise ProbeFailure(cleanup_message, cleanup="FAILED")
        if primary_failure is not None:
            raise primary_failure.with_cleanup(cleanup) from None
        if report is None:
            raise ProbeFailure("The conformance probe did not produce a result.")
        return replace(report, cleanup=cleanup)


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
        _best_effort_record_probe_result(serialized_report, 0)
        print(json.dumps(serialized_report, sort_keys=True))
        return 0
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
