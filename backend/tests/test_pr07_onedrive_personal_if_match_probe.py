from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

import httpx
import pytest

import tools.pr07_onedrive_personal_if_match_probe as probe_module
from tools.pr07_onedrive_personal_if_match_probe import (
    ATTEMPT_ID_ENVIRONMENT_VARIABLE,
    EVENT_JOURNAL_ENVIRONMENT_VARIABLE,
    OneDrivePersonalIfMatchProbe,
    ProbeFailure,
    MAX_DOWNLOAD_BYTES,
    TOKEN_ENVIRONMENT_VARIABLE,
    _record_probe_result,
    _test_item_name,
    main,
)


DRIVE_ID = "drive-personal"
ITEM_ID = "item-probe"
ITEM_NAME = "VALORA-PR07-IF-MATCH-test.bin"
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = BACKEND_DIRECTORY / "tools" / "pr07_onedrive_personal_if_match_launcher.mjs"
NODE_EXECUTABLE = shutil.which("node")
SELF_TEST_SENTINEL = "valora-local-self-test-sentinel"
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


def _metadata(e_tag: str) -> dict:
    return {
        "id": ITEM_ID,
        "name": ITEM_NAME,
        "eTag": e_tag,
    }


def test_probe_item_name_is_recoverable_from_attempt_id(monkeypatch) -> None:
    attempt_id = "33333333-3333-4333-8333-333333333333"
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)

    assert _test_item_name() == f"VALORA-PR07-IF-MATCH-{attempt_id}.bin"


class GraphScenario:
    def __init__(
        self,
        *,
        stale_status: int = 412,
        create_session_status: int = 200,
        fresh_commit_status: int = 200,
        stage_status: int = 202,
        cancel_status: int = 204,
        create_item_metadata_complete: bool = True,
    ) -> None:
        self.content = b""
        self.e_tag = '"etag-1"'
        self.session_number = 0
        self.sessions: dict[str, bytes] = {}
        self.session_etags: dict[str, str] = {}
        self.stale_status = stale_status
        self.create_session_status = create_session_status
        self.fresh_commit_status = fresh_commit_status
        self.stage_status = stage_status
        self.cancel_status = cancel_status
        self.create_item_metadata_complete = create_item_metadata_complete
        self.deleted = False
        self.deleted_by_name = False
        self.cleanup_status = 204
        self.authorization_seen_on_upload_url = False
        self.authorization_seen_on_download_url = False

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        authorization = request.headers.get("authorization")
        if request.url.host == "upload.test":
            self.authorization_seen_on_upload_url |= authorization is not None
            session_id = path.rsplit("/", 1)[-1]
            if request.method == "PUT":
                assert authorization is None
                assert request.headers["content-range"] == "bytes 0-327679/327680"
                assert len(request.content) == 320 * 1024
                self.sessions[session_id] = request.content
                return httpx.Response(
                    self.stage_status,
                    json={"nextExpectedRanges": []},
                )
            if request.method == "DELETE":
                self.sessions.pop(session_id, None)
                return httpx.Response(self.cancel_status)
        if request.url.host == "download.test":
            self.authorization_seen_on_download_url |= authorization is not None
            return httpx.Response(200, content=self.content)

        assert authorization == "Bearer secret-token"
        if request.method == "GET" and path.endswith("/me/drive"):
            return httpx.Response(200, json={"id": DRIVE_ID, "driveType": "personal"})
        if request.method == "PUT" and path.endswith(":/content"):
            self.content = request.content
            if not self.create_item_metadata_complete:
                return httpx.Response(201, json={"name": ITEM_NAME})
            return httpx.Response(201, json=_metadata(self.e_tag))
        if request.method == "POST" and path.endswith("/createUploadSession"):
            body = json.loads(request.content)
            assert path.endswith(f"/drives/{DRIVE_ID}/items/{ITEM_ID}/createUploadSession")
            assert request.headers["if-match"] == self.e_tag
            assert body == {"deferCommit": True}
            if self.create_session_status != 200:
                return httpx.Response(
                    self.create_session_status,
                    json={"error": {"code": "invalidRequest", "message": "unsafe detail"}},
                )
            self.session_number += 1
            session_id = str(self.session_number)
            self.session_etags[session_id] = request.headers["if-match"]
            return httpx.Response(200, json={"uploadUrl": f"https://upload.test/{session_id}"})
        if request.method == "PUT" and path.endswith(f"/{ITEM_ID}"):
            body = json.loads(request.content)
            session_id = body["@microsoft.graph.sourceUrl"].rsplit("/", 1)[-1]
            assert request.headers["if-match"] == self.session_etags[session_id]
            assert request.url.params.get_list("@microsoft.graph.conflictBehavior") == ["fail"]
            assert set(body) == {"@microsoft.graph.sourceUrl"}
            assert "@microsoft.graph.conflictBehavior" not in body
            assert "name" not in body
            if self.session_number == 1 and self.fresh_commit_status not in {200, 201}:
                return httpx.Response(
                    self.fresh_commit_status,
                    json={
                        "error": {
                            "code": "invalidRequest",
                            "message": "unsafe final-commit detail",
                            "innerError": {"request-id": "unsafe-request-id"},
                        }
                    },
                )
            if request.headers["if-match"] != self.e_tag:
                return httpx.Response(self.stale_status, json={"error": {"code": "stale"}})
            self.content = self.sessions[session_id]
            self.e_tag = '"etag-2"'
            return httpx.Response(200, json=_metadata(self.e_tag))
        if request.method == "PUT" and path.endswith(f"/{ITEM_ID}/content"):
            self.content = request.content
            self.e_tag = '"etag-3"'
            return httpx.Response(200, json=_metadata(self.e_tag))
        if request.method == "GET" and path.endswith(f"/{ITEM_ID}/content"):
            return httpx.Response(302, headers={"Location": "https://download.test/content"})
        if request.method == "GET" and path.endswith(f"/{ITEM_ID}"):
            return httpx.Response(200, json=_metadata(self.e_tag))
        if request.method == "DELETE" and path.endswith(f"/{ITEM_ID}"):
            self.deleted = True
            return httpx.Response(self.cleanup_status)
        if request.method == "DELETE" and "/root:/" in path:
            self.deleted_by_name = True
            return httpx.Response(self.cleanup_status)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")


def test_probe_proves_fresh_and_stale_commit_without_leaking_upload_authorization() -> None:
    scenario = GraphScenario()
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    report = probe.run()

    assert report.status == "PASS"
    assert report.fresh_conditional_commit == "PASS"
    assert report.stale_conditional_commit == "HTTP_412_PASS"
    assert report.item_identity_preserved is True
    assert report.concurrent_bytes_preserved is True
    assert report.cleanup == "DELETED_TO_RECYCLE_BIN"
    assert scenario.deleted is True
    assert scenario.authorization_seen_on_upload_url is False
    assert scenario.authorization_seen_on_download_url is False
    assert hashlib.sha256(scenario.content).hexdigest() != hashlib.sha256(b"").hexdigest()


def test_probe_fails_when_exact_item_cleanup_returns_404() -> None:
    scenario = GraphScenario()
    scenario.cleanup_status = 404
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    assert raised.value.as_report() == {
        "status": "FAIL",
        "reason": "Test item cleanup failed with HTTP 404.",
        "cleanup": "FAILED",
    }
    assert raised.value.cleanup != "DELETED_TO_RECYCLE_BIN"


def test_probe_fails_closed_when_stale_commit_is_not_412_and_still_cleans_up() -> None:
    scenario = GraphScenario(stale_status=200)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure, match="was not rejected with HTTP 412"):
        probe.run()

    assert scenario.deleted is True
    assert scenario.authorization_seen_on_upload_url is False
    assert scenario.authorization_seen_on_download_url is False


def test_probe_reports_safe_provider_code_when_stale_commit_is_not_412() -> None:
    scenario = GraphScenario(stale_status=409)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report == {
        "status": "FAIL",
        "reason": (
            "Stale conditional final commit was not rejected with HTTP 412 "
            "(received HTTP 409)."
        ),
        "http_status": 409,
        "provider_error_code": "stale",
        "cleanup": "DELETED_TO_RECYCLE_BIN",
    }
    assert scenario.deleted is True


def test_probe_reports_only_safe_provider_code_and_explicit_cleanup() -> None:
    scenario = GraphScenario(create_session_status=400)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report == {
        "status": "FAIL",
        "reason": "Upload-session creation failed with HTTP 400.",
        "http_status": 400,
        "provider_error_code": "invalidRequest",
        "cleanup": "DELETED_TO_RECYCLE_BIN",
    }
    assert "unsafe detail" not in json.dumps(report)
    assert scenario.deleted is True


def test_probe_reports_only_safe_provider_code_for_fresh_commit_failure() -> None:
    scenario = GraphScenario(fresh_commit_status=400)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report == {
        "status": "FAIL",
        "reason": "Fresh conditional final commit failed with HTTP 400.",
        "http_status": 400,
        "provider_error_code": "invalidRequest",
        "cleanup": "DELETED_TO_RECYCLE_BIN",
    }
    serialized = json.dumps(report)
    assert "unsafe final-commit detail" not in serialized
    assert "unsafe-request-id" not in serialized
    assert scenario.deleted is True


def test_probe_journal_records_provider_and_cleanup_boundaries_without_sensitive_values(
    tmp_path: Path,
    monkeypatch,
) -> None:
    scenario = GraphScenario(fresh_commit_status=400)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    token_canary = "secret-token"
    probe = OneDrivePersonalIfMatchProbe(access_token=token_canary, client=client)
    attempt_id = "11111111-1111-4111-8111-111111111111"
    journal_path = (tmp_path / f"{attempt_id}.events.jsonl").resolve()
    journal_path.write_text("", encoding="utf-8")
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    monkeypatch.setenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, str(journal_path))

    with pytest.raises(ProbeFailure, match="Fresh conditional final commit failed"):
        probe.run()

    serialized = journal_path.read_text(encoding="utf-8")
    entries = [json.loads(line) for line in serialized.splitlines()]
    stages = [entry["stage"] for entry in entries]
    assert stages[:3] == [
        "PROBE_STARTED",
        "DRIVE_VERIFY_REQUEST_STARTED",
        "ITEM_CREATE_REQUEST_STARTED",
    ]
    assert "FRESH_FINAL_COMMIT_REQUEST_STARTED" in stages
    assert stages[-2:] == [
        "TEST_ITEM_DELETE_REQUEST_STARTED",
        "TEST_ITEM_DELETE_REQUEST_COMPLETED",
    ]
    assert token_canary not in serialized
    assert DRIVE_ID not in serialized
    assert ITEM_ID not in serialized


def test_probe_finished_journal_rejects_unknown_keys_and_token_canary(
    tmp_path: Path,
    monkeypatch,
) -> None:
    attempt_id = "44444444-4444-4444-8444-444444444444"
    journal_path = (tmp_path / f"{attempt_id}.events.jsonl").resolve()
    journal_path.write_text("", encoding="utf-8")
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    monkeypatch.setenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, str(journal_path))
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, "journal-token-canary")

    with pytest.raises(ProbeFailure, match="evidence was rejected"):
        _record_probe_result(
            {"status": "FAIL", "reason": "safe", "provider_body": "unsafe"},
            1,
        )
    with pytest.raises(ProbeFailure, match="evidence was rejected"):
        _record_probe_result(
            {"status": "FAIL", "reason": "journal-token-canary"},
            1,
        )

    assert journal_path.read_text(encoding="utf-8") == ""


def test_cleanup_runs_when_cleanup_progress_journal_becomes_unavailable(
    monkeypatch,
) -> None:
    scenario = GraphScenario(stage_status=500)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)
    original_record_progress = probe_module._record_progress

    def fail_cleanup_progress(stage: str) -> None:
        if "CANCEL" in stage or "DELETE" in stage:
            raise ProbeFailure("Diagnostic evidence is unavailable.")
        original_record_progress(stage)

    monkeypatch.setattr(probe_module, "_record_progress", fail_cleanup_progress)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert scenario.sessions == {}
    assert scenario.deleted is True
    assert report["cleanup"] == "FAILED"
    assert "Diagnostic cleanup evidence is unavailable" in report["reason"]


def test_probe_refuses_graph_when_progress_journal_is_unavailable(
    tmp_path: Path,
    monkeypatch,
) -> None:
    request_count = 0

    def fail_if_requested(request: httpx.Request) -> httpx.Response:
        nonlocal request_count
        request_count += 1
        pytest.fail(f"Graph request escaped diagnostic gate: {request.method}")

    client = httpx.Client(transport=httpx.MockTransport(fail_if_requested))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)
    monkeypatch.setenv(
        ATTEMPT_ID_ENVIRONMENT_VARIABLE,
        "22222222-2222-4222-8222-222222222222",
    )
    monkeypatch.setenv(
        EVENT_JOURNAL_ENVIRONMENT_VARIABLE,
        str((tmp_path / "missing.events.jsonl").resolve()),
    )

    with pytest.raises(ProbeFailure, match="Diagnostic evidence is unavailable"):
        probe.run()

    assert request_count == 0


def test_command_refuses_network_without_both_explicit_write_flags(monkeypatch) -> None:
    monkeypatch.setenv("VALORA_PR07_GRAPH_ACCESS_TOKEN", "secret-token")

    with pytest.raises(ProbeFailure, match="Both --allow-live-write"):
        main([])
    with pytest.raises(ProbeFailure, match="Both --allow-live-write"):
        main(["--allow-live-write"])


def test_direct_live_command_requires_controller_journal_before_client(
    monkeypatch,
) -> None:
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, "secret-token")
    monkeypatch.delenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.delenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, raising=False)

    def fail_if_constructed(*args, **kwargs):
        pytest.fail("Direct live command constructed the Graph client.")

    monkeypatch.setattr(probe_module, "OneDrivePersonalIfMatchProbe", fail_if_constructed)

    with pytest.raises(ProbeFailure, match="requires controller diagnostic evidence"):
        main(["--allow-live-write", "--cleanup-test-item"])


def test_self_test_reports_sanitized_success_without_constructing_client(
    monkeypatch,
    capsys,
) -> None:
    monkeypatch.chdir(BACKEND_DIRECTORY)
    monkeypatch.setenv("VALORA_PR07_GRAPH_ACCESS_TOKEN", SELF_TEST_SENTINEL)

    def fail_if_constructed(*args, **kwargs):
        pytest.fail("Self-test constructed the live probe client.")

    monkeypatch.setattr(
        "tools.pr07_onedrive_personal_if_match_probe.OneDrivePersonalIfMatchProbe",
        fail_if_constructed,
    )

    assert main(["--self-test"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == f"{json.dumps(SELF_TEST_REPORT, sort_keys=True)}\n"
    assert SELF_TEST_SENTINEL not in captured.out


@pytest.mark.parametrize("live_flag", ["--allow-live-write", "--cleanup-test-item"])
def test_self_test_rejects_live_flag_before_constructing_client(
    monkeypatch,
    live_flag: str,
) -> None:
    monkeypatch.setenv("VALORA_PR07_GRAPH_ACCESS_TOKEN", SELF_TEST_SENTINEL)

    def fail_if_constructed(*args, **kwargs):
        pytest.fail("Invalid self-test flags constructed the live probe client.")

    monkeypatch.setattr(
        "tools.pr07_onedrive_personal_if_match_probe.OneDrivePersonalIfMatchProbe",
        fail_if_constructed,
    )

    with pytest.raises(ProbeFailure, match="Self-test cannot be combined"):
        main(["--self-test", live_flag])


def test_self_test_exact_module_surface_emits_one_json_line_and_exits_zero() -> None:
    environment = os.environ.copy()
    environment["VALORA_PR07_GRAPH_ACCESS_TOKEN"] = SELF_TEST_SENTINEL

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.pr07_onedrive_personal_if_match_probe",
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    assert json.loads(completed.stdout) == SELF_TEST_REPORT
    assert SELF_TEST_SENTINEL not in completed.stdout


def test_self_test_exact_module_surface_fails_sanitized_without_environment() -> None:
    environment = os.environ.copy()
    environment.pop("VALORA_PR07_GRAPH_ACCESS_TOKEN", None)

    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "tools.pr07_onedrive_personal_if_match_probe",
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert completed.stdout == (
        '{"reason": "VALORA_PR07_GRAPH_ACCESS_TOKEN is required for self-test.", '
        '"status": "FAIL"}\n'
    )


def test_cleanup_failure_preserves_primary_conformance_failure() -> None:
    scenario = GraphScenario(stale_status=200)
    scenario.cleanup_status = 503
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    message = str(raised.value)
    assert "was not rejected with HTTP 412" in message
    assert "Cleanup also failed" in message
    assert "HTTP 503" in message


def test_unexpected_exception_is_sanitized_and_preserves_cleanup_failure(monkeypatch) -> None:
    scenario = GraphScenario()
    scenario.cleanup_status = 503
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    def raise_unexpected(**kwargs):
        raise RuntimeError("unsafe-internal-detail")

    monkeypatch.setattr(probe, "_create_upload_session", raise_unexpected)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report == {
        "status": "FAIL",
        "reason": (
            "Unexpected sanitized probe failure. Cleanup also failed: "
            "Test item cleanup failed with HTTP 503."
        ),
        "cleanup": "FAILED",
    }
    assert "unsafe-internal-detail" not in json.dumps(report)


def test_stage_failure_reports_cancel_failure_and_still_deletes_item() -> None:
    scenario = GraphScenario(stage_status=500, cancel_status=503)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report["cleanup"] == "FAILED"
    assert "did not keep the deferCommit upload staged" in report["reason"]
    assert "Upload-session cleanup failed with HTTP 503" in report["reason"]
    assert scenario.deleted is True


def test_unexpected_cancel_exception_is_sanitized_and_item_cleanup_continues(
    monkeypatch,
) -> None:
    scenario = GraphScenario(stage_status=500)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    def raise_unexpected(upload_url: str) -> None:
        raise RuntimeError(f"unsafe-cancel-detail:{upload_url}")

    monkeypatch.setattr(probe, "_cancel_session", raise_unexpected)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    report = raised.value.as_report()
    assert report["cleanup"] == "FAILED"
    assert "Upload-session cleanup failed unexpectedly." in report["reason"]
    assert "unsafe-cancel-detail" not in json.dumps(report)
    assert scenario.deleted is True


def test_unexpected_item_cleanup_exception_is_sanitized(monkeypatch) -> None:
    scenario = GraphScenario()
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    def raise_unexpected(**kwargs) -> None:
        raise RuntimeError("unsafe-delete-detail")

    monkeypatch.setattr(probe, "_delete_item", raise_unexpected)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    assert raised.value.as_report() == {
        "status": "FAIL",
        "reason": "Test item cleanup failed unexpectedly.",
        "cleanup": "FAILED",
    }


def test_partial_create_uses_bounded_name_cleanup() -> None:
    scenario = GraphScenario(create_item_metadata_complete=False)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure) as raised:
        probe.run()

    assert raised.value.as_report() == {
        "status": "FAIL",
        "reason": "Microsoft Graph item metadata is incomplete.",
        "cleanup": "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
    }
    assert scenario.deleted_by_name is True


@pytest.mark.parametrize(
    "location",
    [
        "http://download.test/content",
        "https://user:password@download.test/content",
    ],
)
def test_download_rejects_unsafe_redirect(location: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": location})

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure, match="unsafe provider URL"):
        probe._download(drive_id=DRIVE_ID, item_id=ITEM_ID)


def test_download_rejects_redirect_overflow() -> None:
    redirect_count = 0

    def handler(request: httpx.Request) -> httpx.Response:
        nonlocal redirect_count
        redirect_count += 1
        return httpx.Response(
            302,
            headers={"Location": f"https://download.test/{redirect_count}"},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure, match="redirected too many times"):
        probe._download(drive_id=DRIVE_ID, item_id=ITEM_ID)


def test_download_rejects_oversized_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (MAX_DOWNLOAD_BYTES + 1))

    client = httpx.Client(transport=httpx.MockTransport(handler), follow_redirects=False)
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure, match="exceeded the probe bound"):
        probe._download(drive_id=DRIVE_ID, item_id=ITEM_ID)


def test_node_launcher_uses_absolute_python_and_preserves_sanitized_success() -> None:
    assert NODE_EXECUTABLE is not None
    environment = os.environ.copy()
    environment["VALORA_PR07_GRAPH_ACCESS_TOKEN"] = SELF_TEST_SENTINEL

    completed = subprocess.run(
        [
            NODE_EXECUTABLE,
            str(LAUNCHER_PATH),
            "--python-executable",
            str(Path(sys.executable).resolve()),
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY.parent,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    assert json.loads(completed.stdout) == SELF_TEST_REPORT
    assert SELF_TEST_SENTINEL not in completed.stdout


def test_node_launcher_rejects_relative_python_before_spawn() -> None:
    assert NODE_EXECUTABLE is not None

    completed = subprocess.run(
        [
            NODE_EXECUTABLE,
            str(LAUNCHER_PATH),
            "--python-executable",
            "python",
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 2
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "status": "FAIL",
        "stage": "LAUNCHER_VALIDATION",
        "reason": "Python executable must be an absolute file path.",
    }


def test_node_launcher_reports_real_missing_dependency_without_raw_stderr(tmp_path) -> None:
    assert NODE_EXECUTABLE is not None
    isolated_environment = tmp_path / "isolated-python"
    subprocess.run(
        [sys.executable, "-m", "venv", "--without-pip", str(isolated_environment)],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    isolated_python = isolated_environment / (
        "Scripts/python.exe" if os.name == "nt" else "bin/python"
    )

    completed = subprocess.run(
        [
            NODE_EXECUTABLE,
            str(LAUNCHER_PATH),
            "--python-executable",
            str(isolated_python.resolve()),
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY.parent,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "status": "FAIL",
        "stage": "DEPENDENCY_PREFLIGHT",
        "reason": "Python dependency preflight failed.",
        "child_exit_code": 1,
        "child_stderr": "EMPTY",
    }


def test_node_launcher_preserves_sanitized_probe_exit_without_environment() -> None:
    assert NODE_EXECUTABLE is not None
    environment = os.environ.copy()
    environment.pop("VALORA_PR07_GRAPH_ACCESS_TOKEN", None)

    completed = subprocess.run(
        [
            NODE_EXECUTABLE,
            str(LAUNCHER_PATH),
            "--python-executable",
            str(Path(sys.executable).resolve()),
            "--self-test",
        ],
        cwd=BACKEND_DIRECTORY.parent,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "reason": "VALORA_PR07_GRAPH_ACCESS_TOKEN is required for self-test.",
        "status": "FAIL",
    }


def test_node_launcher_report_validator_rejects_token_and_unknown_fields() -> None:
    assert NODE_EXECUTABLE is not None
    module_url = LAUNCHER_PATH.resolve().as_uri()
    program = f"""
import {{ validateReport }} from {json.dumps(module_url)};
const token = "secret-token-value";
const safe = {{status: "FAIL", reason: "Microsoft Graph is unavailable.", cleanup: "FAILED"}};
const leaked = {{status: "FAIL", reason: token}};
const unknown = {{status: "FAIL", reason: "safe", provider_body: "unsafe"}};
process.stdout.write(JSON.stringify({{
  safe: validateReport(safe, false, token),
  leaked: validateReport(leaked, false, token),
  unknown: validateReport(unknown, false, token),
}}));
"""

    completed = subprocess.run(
        [NODE_EXECUTABLE, "--input-type=module", "-e", program],
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "safe": True,
        "leaked": False,
        "unknown": False,
    }


def test_node_launcher_bounded_capture_drains_without_terminating_child() -> None:
    assert NODE_EXECUTABLE is not None
    module_url = LAUNCHER_PATH.resolve().as_uri()
    child_program = "process.stdout.write('x'.repeat(1024 * 1024 + 1))"
    program = f"""
import {{ runChild }} from {json.dumps(module_url)};
const result = await runChild(
  process.execPath,
  ["-e", {json.dumps(child_program)}],
  {{cwd: process.cwd(), env: process.env}},
);
process.stdout.write(JSON.stringify({{
  status: result.status,
  stdoutOverflow: result.stdoutOverflow,
  stderrPresent: result.stderrPresent,
}}));
"""

    completed = subprocess.run(
        [NODE_EXECUTABLE, "--input-type=module", "-e", program],
        cwd=BACKEND_DIRECTORY,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == {
        "status": 0,
        "stdoutOverflow": True,
        "stderrPresent": False,
    }
