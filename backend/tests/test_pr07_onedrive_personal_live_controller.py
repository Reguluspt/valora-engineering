from __future__ import annotations

import http.client
import json
import os
from pathlib import Path
import subprocess
import sys
import threading

import pytest

import tools.pr07_onedrive_personal_live_controller as live_controller
from tools.pr07_onedrive_personal_live_controller import (
    CLIENT_ID_ENVIRONMENT_VARIABLE,
    CLIENT_SECRET_ENVIRONMENT_VARIABLE,
    CONTROLLER_PATH,
    LAUNCHER_PATH,
    SELF_TEST_REPORT,
    TOKEN_ENVIRONMENT_VARIABLE,
    build_launcher_command,
    validate_launcher_report,
)


def test_build_launcher_command_preserves_windows_path_as_one_argument() -> None:
    python_executable = r"C:\Program Files\Python 3.14\python.exe"
    command = build_launcher_command(
        node_executable=r"C:\Program Files\nodejs\node.exe",
        python_executable=python_executable,
        self_test=False,
    )

    assert command == [
        r"C:\Program Files\nodejs\node.exe",
        str(LAUNCHER_PATH),
        "--python-executable",
        python_executable,
        "--allow-live-write",
        "--cleanup-test-item",
    ]
    assert command.count(python_executable) == 1


def test_controller_report_validator_rejects_secret_and_unknown_fields() -> None:
    secret = "controller-secret-canary"

    assert validate_launcher_report(
        SELF_TEST_REPORT,
        self_test=True,
        forbidden={secret},
    )
    assert not validate_launcher_report(
        {"status": "FAIL", "reason": secret},
        self_test=False,
        forbidden={secret},
    )
    assert not validate_launcher_report(
        {"status": "FAIL", "reason": "safe", "provider_body": "unsafe"},
        self_test=False,
        forbidden={secret},
    )
    assert not validate_launcher_report(
        {"status": "FAIL", "reason": "safe", "child_exit_code": True},
        self_test=False,
        forbidden={secret},
    )


def test_exact_controller_surface_is_no_network_and_persists_sanitized_evidence(
    tmp_path: Path,
) -> None:
    evidence_directory = tmp_path / "evidence with spaces"
    working_directory = tmp_path / "working directory with spaces"
    working_directory.mkdir()
    client_secret_canary = "client-secret-must-not-be-recorded"
    access_token_canary = "access-token-must-not-be-recorded"
    environment = os.environ.copy()
    environment[CLIENT_SECRET_ENVIRONMENT_VARIABLE] = client_secret_canary
    environment[TOKEN_ENVIRONMENT_VARIABLE] = access_token_canary

    completed = subprocess.run(
        [
            sys.executable,
            str(CONTROLLER_PATH),
            "--self-test",
            "--evidence-directory",
            str(evidence_directory),
        ],
        cwd=working_directory,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 0
    assert completed.stderr == ""
    assert completed.stdout.count("\n") == 1
    controller_report = json.loads(completed.stdout)
    assert controller_report == {
        "attempt_id": controller_report["attempt_id"],
        "evidence_file": controller_report["evidence_file"],
        "mode": "SELF_TEST",
        "network": "NOT_ATTEMPTED",
        "status": "PASS",
    }

    evidence_files = list(evidence_directory.glob("*.json"))
    assert len(evidence_files) == 1
    serialized_evidence = evidence_files[0].read_text(encoding="utf-8")
    evidence = json.loads(serialized_evidence)
    assert evidence["attempt_id"] == controller_report["attempt_id"]
    assert evidence["status"] == "PASS"
    assert evidence["network"] == "NOT_ATTEMPTED"
    assert evidence["launcher"] == {
        "exit_code": 0,
        "report": SELF_TEST_REPORT,
        "stderr": "EMPTY",
    }
    assert [event["stage"] for event in evidence["probe_stages"]] == [
        "PROBE_SELF_TEST_STARTED"
    ]
    assert evidence["runtime"]["python"]["is_absolute"] is True
    assert evidence["runtime"]["python"]["exists"] is True
    assert evidence["runtime"]["python"]["is_file"] is True
    assert [event["status"] for event in evidence["stages"]] == [
        "STARTED",
        "PASS",
        "STARTED",
        "PASS",
    ]
    assert client_secret_canary not in completed.stdout
    assert access_token_canary not in completed.stdout
    assert client_secret_canary not in serialized_evidence
    assert access_token_canary not in serialized_evidence
    journal_files = list(evidence_directory.glob("*.events.jsonl"))
    assert len(journal_files) == 1
    serialized_journal = journal_files[0].read_text(encoding="utf-8")
    journal_entries = [json.loads(line) for line in serialized_journal.splitlines()]
    assert journal_entries[0]["record_type"] == "ATTEMPT_STARTED"
    assert journal_entries[-1]["record_type"] == "ATTEMPT_FINISHED"
    assert client_secret_canary not in serialized_journal
    assert access_token_canary not in serialized_journal


def test_controller_finalizes_evidence_when_node_is_unavailable(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "failure-evidence"
    environment = os.environ.copy()
    environment["PATH"] = ""

    completed = subprocess.run(
        [
            sys.executable,
            str(CONTROLLER_PATH),
            "--self-test",
            "--evidence-directory",
            str(evidence_directory),
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    controller_report = json.loads(completed.stdout)
    assert controller_report["status"] == "FAIL"
    assert controller_report["network"] == "NOT_ATTEMPTED"
    assert controller_report["failure_code"] == "NODE_EXECUTABLE_UNAVAILABLE"

    evidence_files = list(evidence_directory.glob("*.json"))
    assert len(evidence_files) == 1
    evidence = json.loads(evidence_files[0].read_text(encoding="utf-8"))
    assert evidence["status"] == "FAIL"
    assert evidence["finished_at"] is not None
    assert evidence["failure_code"] == "NODE_EXECUTABLE_UNAVAILABLE"
    assert evidence["stages"][-1] == {
        "at": evidence["stages"][-1]["at"],
        "code": "NODE_EXECUTABLE_UNAVAILABLE",
        "stage": "CONTROLLER_VALIDATION",
        "status": "FAIL",
    }


def test_live_mode_requires_both_acknowledgements_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "missing-acknowledgements"
    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", evidence_directory)
    monkeypatch.delenv(CLIENT_ID_ENVIRONMENT_VARIABLE, raising=False)
    monkeypatch.delenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, raising=False)

    assert live_controller.run(
        [
            "--live",
            "--evidence-directory",
            str(evidence_directory),
        ]
    ) == 1

    report = json.loads(capsys.readouterr().out)
    assert report["failure_code"] == "LIVE_ACKNOWLEDGEMENTS_REQUIRED"
    assert report["network"] == "NOT_ATTEMPTED"
    evidence_file = next(evidence_directory.glob("*.json"))
    evidence = json.loads(evidence_file.read_text(encoding="utf-8"))
    assert evidence["failure_code"] == "LIVE_ACKNOWLEDGEMENTS_REQUIRED"
    assert evidence["network"] == "NOT_ATTEMPTED"


def test_live_mode_rejects_wrong_app_and_does_not_record_secret(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "wrong-app"
    secret_canary = "wrong-app-secret-must-not-be-recorded"
    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", evidence_directory)
    monkeypatch.setenv(CLIENT_ID_ENVIRONMENT_VARIABLE, "wrong-client-id")
    monkeypatch.setenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, secret_canary)

    assert live_controller.run(
        [
            "--live",
            "--allow-live-write",
            "--cleanup-test-item",
            "--evidence-directory",
            str(evidence_directory),
        ]
    ) == 1

    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["failure_code"] == "OAUTH_CONFIGURATION_REJECTED"
    assert report["network"] == "NOT_ATTEMPTED"
    evidence_file = next(evidence_directory.glob("*.json"))
    serialized_evidence = evidence_file.read_text(encoding="utf-8")
    evidence = json.loads(serialized_evidence)
    assert evidence["failure_code"] == "OAUTH_CONFIGURATION_REJECTED"
    assert evidence["network"] == "NOT_ATTEMPTED"
    assert secret_canary not in captured.out
    assert secret_canary not in serialized_evidence


def test_unexpected_controller_failure_is_sanitized_and_finalized(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "unexpected-failure"
    unsafe_detail = "unsafe-controller-detail-must-not-be-recorded"

    def raise_unexpected(self_test: bool):
        raise RuntimeError(unsafe_detail)

    monkeypatch.setattr(live_controller, "_prepare_launcher", raise_unexpected)

    assert live_controller.run(
        ["--self-test", "--evidence-directory", str(evidence_directory)]
    ) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert captured.err == ""
    assert report["failure_code"] == "UNEXPECTED_CONTROLLER_FAILURE"
    assert report["network"] == "NOT_ATTEMPTED"

    evidence_file = next(evidence_directory.glob("*.json"))
    serialized_evidence = evidence_file.read_text(encoding="utf-8")
    evidence = json.loads(serialized_evidence)
    assert evidence["failure_code"] == "UNEXPECTED_CONTROLLER_FAILURE"
    assert evidence["finished_at"] is not None
    assert unsafe_detail not in captured.out
    assert unsafe_detail not in serialized_evidence


def test_live_controller_invokes_repository_launcher_once_without_shell(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "simulated-live"
    client_secret_canary = "simulated-live-client-secret"
    access_token_canary = "simulated-live-access-token"
    calls = {"oauth": 0, "launcher": 0}
    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", evidence_directory)
    monkeypatch.setenv(CLIENT_ID_ENVIRONMENT_VARIABLE, live_controller.EXPECTED_CLIENT_ID)
    monkeypatch.setenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, client_secret_canary)

    def acquire_token(*, client_id: str, client_secret: str) -> str:
        calls["oauth"] += 1
        assert client_id == live_controller.EXPECTED_CLIENT_ID
        assert client_secret == client_secret_canary
        return access_token_canary

    def run_launcher(
        *,
        access_token: str,
        attempt_id: str,
        command: list[str],
        event_journal: Path,
        self_test: bool,
        forbidden: set[str],
    ) -> tuple[int, dict, str]:
        calls["launcher"] += 1
        assert access_token == access_token_canary
        assert attempt_id
        assert event_journal.name.endswith(".events.jsonl")
        assert self_test is False
        assert forbidden == {access_token_canary}
        assert command[0] == str(Path(live_controller._resolve_node_executable()))
        assert command[1] == str(LAUNCHER_PATH)
        assert command[2] == "--python-executable"
        assert command[3] == str(Path(sys.executable).resolve())
        assert command[4:] == ["--allow-live-write", "--cleanup-test-item"]
        return (
            1,
            {
                "status": "FAIL",
                "reason": "Simulated sanitized provider failure.",
                "cleanup": "NOT_ATTEMPTED",
            },
            "EMPTY",
        )

    monkeypatch.setattr(live_controller, "_acquire_live_access_token", acquire_token)
    monkeypatch.setattr(live_controller, "_run_launcher", run_launcher)

    assert live_controller.run(
        [
            "--live",
            "--allow-live-write",
            "--cleanup-test-item",
            "--evidence-directory",
            str(evidence_directory),
        ]
    ) == 1
    captured = capsys.readouterr()
    assert captured.err == ""
    assert calls == {"oauth": 1, "launcher": 1}
    output = json.loads(captured.out)
    assert output["status"] == "FAIL"
    assert output["network"] == "OAUTH_ATTEMPTED"

    evidence_file = next(evidence_directory.glob("*.json"))
    serialized_evidence = evidence_file.read_text(encoding="utf-8")
    evidence = json.loads(serialized_evidence)
    assert evidence["launcher_invocation"]["shell"] is False
    assert evidence["launcher_invocation"]["argv_count"] == 6
    assert evidence["launcher"]["exit_code"] == 1
    assert evidence["failure_code"] == "PROBE_REPORTED_FAILURE"
    journal_file = next(evidence_directory.glob("*.events.jsonl"))
    serialized_journal = journal_file.read_text(encoding="utf-8")
    assert client_secret_canary not in captured.out
    assert access_token_canary not in captured.out
    assert client_secret_canary not in serialized_evidence
    assert access_token_canary not in serialized_evidence
    assert client_secret_canary not in serialized_journal
    assert access_token_canary not in serialized_journal


def test_oauth_callback_material_is_cleared_after_token_exchange(monkeypatch) -> None:
    callback_response = {"code": "authorization-code", "state": "expected-state"}
    acquired_response: dict[str, str] = {}

    class FakeApplication:
        def __init__(self, client_id: str, **kwargs) -> None:
            assert client_id == live_controller.EXPECTED_CLIENT_ID

        def initiate_auth_code_flow(self, **kwargs) -> dict:
            assert kwargs["scopes"] == ["Files.ReadWrite"]
            assert kwargs["redirect_uri"] == live_controller.REDIRECT_URI
            assert kwargs["response_mode"] == "form_post"
            return {"auth_uri": "https://login.microsoftonline.test/authorize", "state": "state"}

        def acquire_token_by_auth_code_flow(self, flow: dict, response: dict) -> dict:
            acquired_response.update(response)
            return {
                "access_token": "short-lived-token",
                "scope": "Files.ReadWrite",
                "id_token_claims": {
                    "aud": live_controller.EXPECTED_CLIENT_ID,
                    "iss": live_controller.CONSUMER_ISSUER,
                    "sub": "personal-subject",
                    "tid": live_controller.CONSUMER_TENANT_ID,
                },
            }

    class FakeServer:
        def __init__(self, address, handler) -> None:
            assert address == ("127.0.0.1", 8000)
            assert handler is live_controller._CallbackHandler

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, traceback) -> None:
            return None

    def return_callback(server) -> dict[str, str]:
        live_controller._CallbackHandler.callback_response = callback_response
        return callback_response

    monkeypatch.setattr(live_controller.msal, "ConfidentialClientApplication", FakeApplication)
    monkeypatch.setattr(live_controller, "HTTPServer", FakeServer)
    monkeypatch.setattr(live_controller, "_wait_for_callback", return_callback)
    monkeypatch.setattr(live_controller.webbrowser, "open", lambda *args, **kwargs: True)

    token = live_controller._acquire_live_access_token(
        client_id=live_controller.EXPECTED_CLIENT_ID,
        client_secret="temporary-secret",
    )

    assert token == "short-lived-token"
    assert acquired_response == {"code": "authorization-code", "state": "expected-state"}
    assert callback_response == {}
    assert live_controller._CallbackHandler.callback_response is None


def test_oauth_callback_accepts_bounded_form_post_and_rejects_query_code() -> None:
    live_controller._CallbackHandler.callback_response = None
    server = live_controller.HTTPServer(
        ("127.0.0.1", 0),
        live_controller._CallbackHandler,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request(
            "GET",
            f"{live_controller.CALLBACK_PATH}?code=query-code&state=query-state",
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 405
        assert live_controller._CallbackHandler.callback_response is None

        body = "code=form-code&state=form-state"
        connection.request(
            "POST",
            live_controller.CALLBACK_PATH,
            body=body,
            headers={
                "Content-Length": str(len(body.encode("utf-8"))),
                "Content-Type": "application/x-www-form-urlencoded",
            },
        )
        response = connection.getresponse()
        response.read()
        assert response.status == 200
        assert live_controller._CallbackHandler.callback_response == {
            "code": "form-code",
            "state": "form-state",
        }
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        live_controller._CallbackHandler.callback_response = None


def _write_live_journal(
    evidence_directory: Path,
    entries: list[dict[str, object] | str],
) -> None:
    evidence_directory.mkdir()
    journal_path = evidence_directory / "prior-attempt.events.jsonl"
    journal_path.write_text(
        "".join(
            f"{entry}\n" if isinstance(entry, str) else f"{json.dumps(entry, sort_keys=True)}\n"
            for entry in entries
        ),
        encoding="utf-8",
    )


def _live_start(attempt_id: str) -> dict[str, object]:
    return {
        "at": "2026-09-16T00:00:00+00:00",
        "attempt_id": attempt_id,
        "mode": "LIVE",
        "record_type": "ATTEMPT_STARTED",
    }


def _probe_stage(attempt_id: str, stage: str) -> dict[str, object]:
    return {
        "at": "2026-09-16T00:00:01+00:00",
        "attempt_id": attempt_id,
        "record_type": "PROBE_STAGE",
        "stage": stage,
    }


def _probe_finished(
    attempt_id: str,
    cleanup: str | None,
    *,
    reason: str = "Sanitized probe failure.",
) -> dict[str, object]:
    report: dict[str, object] = {"reason": reason, "status": "FAIL"}
    if cleanup is not None:
        report["cleanup"] = cleanup
    return {
        "at": "2026-09-16T00:00:02+00:00",
        "attempt_id": attempt_id,
        "exit_code": 1,
        "record_type": "PROBE_FINISHED",
        "report": report,
        "status": "FAIL",
    }


def _finished(
    attempt_id: str,
    *,
    cleanup: str | None = None,
    exit_code: int | bool = 1,
    reason: str = "Sanitized probe failure.",
) -> dict[str, object]:
    report = None
    launcher = None
    if cleanup is not None:
        report = {"cleanup": cleanup, "reason": reason, "status": "FAIL"}
        launcher = {"exit_code": exit_code, "report": report, "stderr": "EMPTY"}
    return {
        "at": "2026-09-16T00:00:02+00:00",
        "attempt_id": attempt_id,
        "failure_code": "PROBE_REPORTED_FAILURE",
        "failure_details": None,
        "launcher": launcher,
        "record_type": "ATTEMPT_FINISHED",
        "status": "FAIL",
    }


def _assert_live_guard_blocks_before_oauth_and_launcher(
    evidence_directory: Path,
    monkeypatch,
    capsys,
) -> None:
    def unexpected_call(*args, **kwargs):
        raise AssertionError("The unresolved-attempt guard ran too late.")

    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", evidence_directory)
    monkeypatch.setattr(live_controller, "_prepare_launcher", unexpected_call)
    monkeypatch.setattr(live_controller, "_acquire_live_access_token", unexpected_call)
    monkeypatch.setenv(CLIENT_ID_ENVIRONMENT_VARIABLE, live_controller.EXPECTED_CLIENT_ID)
    monkeypatch.setenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, "must-not-be-used")

    assert live_controller.run(
        ["--live", "--allow-live-write", "--cleanup-test-item"]
    ) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["failure_code"] == "UNRESOLVED_PRIOR_ATTEMPT"
    assert output["network"] == "NOT_ATTEMPTED"
    assert output["evidence_file"] is None
    assert list(evidence_directory.glob("*.json")) == []


def test_live_controller_blocks_finished_attempt_with_failed_cleanup_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "unresolved-live"
    attempt_id = "55555555-5555-4555-8555-555555555555"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _finished(attempt_id, cleanup="FAILED"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_mutation_without_delete_completion_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "missing-delete"
    attempt_id = "66666666-6666-4666-8666-666666666666"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_open_session_without_cancel_completion_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "missing-cancel"
    attempt_id = "67676767-6767-4767-8767-676767676767"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_UPLOAD_SESSION_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_provider_mutation_after_delete_completion_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "mutation-after-delete"
    attempt_id = "68686868-6868-4868-8868-686868686868"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_stage(attempt_id, "CONCURRENT_WRITE_REQUEST_STARTED"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_boolean_launcher_exit_code_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "boolean-exit-code"
    attempt_id = "69696969-6969-4969-8969-696969696969"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _finished(
                attempt_id,
                cleanup="DELETED_TO_RECYCLE_BIN",
                exit_code=True,
            ),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_mismatched_terminals_without_mutation_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "mismatched-pre-mutation-terminals"
    attempt_id = "70707070-7070-4070-8070-707070707070"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_finished(attempt_id, None, reason="Probe terminal."),
            _finished(attempt_id, cleanup="NOT_ATTEMPTED", reason="Controller terminal."),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_launcher_only_fields_in_probe_terminal_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "invalid-probe-schema"
    attempt_id = "71717171-7171-4171-8171-717171717171"
    probe_terminal = _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN")
    probe_report = probe_terminal["report"]
    assert isinstance(probe_report, dict)
    probe_report.update(
        {
            "child_exit_code": True,
            "child_stderr": "EMPTY",
            "stage": "PROBE_PROCESS",
        }
    )
    controller_terminal = _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN")
    launcher = controller_terminal["launcher"]
    assert isinstance(launcher, dict)
    launcher["report"] = probe_report
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            probe_terminal,
            controller_terminal,
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_probe_terminal_before_claimed_cleanup_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "probe-terminal-before-cleanup"
    attempt_id = "72727272-7272-4272-8272-727272727272"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


@pytest.mark.parametrize(
    "session_stages",
    [
        ["UPLOAD_STAGE_REQUEST_STARTED"],
        [
            "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED",
            "UPLOAD_SESSION_CANCEL_REQUEST_STARTED",
        ],
    ],
    ids=["session-stage-without-create", "reversed-cancel-pair"],
)
def test_live_controller_blocks_incomplete_or_reversed_session_evidence_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
    session_stages: list[str],
) -> None:
    evidence_directory = tmp_path / "unsafe-session-evidence"
    attempt_id = "73737373-7373-4373-8373-737373737373"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            *(_probe_stage(attempt_id, stage) for stage in session_stages),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_session_marker_after_dependent_stage_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "late-session-marker"
    attempt_id = "76767676-7676-4676-8676-767676767676"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_STAGE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_UPLOAD_SESSION_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_session_stage_after_session_closed_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "stage-after-session-closed"
    attempt_id = "78767676-7676-4676-8676-767676767676"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_UPLOAD_SESSION_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_STAGE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_FINAL_COMMIT_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_ITEM_VERIFY_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_STAGE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_probe_stage_while_cancel_pending_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "stage-while-cancel-pending"
    attempt_id = "79767676-7676-4676-8676-767676767676"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_UPLOAD_SESSION_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_STAGE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_STAGE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_reversed_unused_delete_pair_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "reversed-unused-delete-pair"
    attempt_id = "77767676-7676-4676-8676-767676767676"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_empty_journal_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "empty-journal"
    _write_live_journal(evidence_directory, [])
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_blocks_mutation_without_probe_terminal_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    evidence_directory = tmp_path / "missing-probe-terminal"
    attempt_id = "74747474-7474-4474-8474-747474747474"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


@pytest.mark.parametrize("terminal_variant", ["missing", "extra"])
def test_live_controller_blocks_noncanonical_attempt_terminal_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
    terminal_variant: str,
) -> None:
    evidence_directory = tmp_path / "noncanonical-attempt-terminal"
    attempt_id = "75757575-7575-4575-8575-757575757575"
    terminal = _finished(attempt_id)
    if terminal_variant == "missing":
        terminal.pop("failure_code")
        terminal.pop("failure_details")
    else:
        terminal["unexpected"] = "not-allowlisted"
    _write_live_journal(
        evidence_directory,
        [_live_start(attempt_id), terminal],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_prior_live_mutation_with_allowlisted_cleanup_is_resolved(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "resolved-mutation"
    attempt_id = "77777777-7777-4777-8777-777777777777"
    _write_live_journal(
        evidence_directory,
        [
            _live_start(attempt_id),
            _probe_stage(attempt_id, "ITEM_CREATE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "FRESH_UPLOAD_SESSION_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_STARTED"),
            _probe_stage(attempt_id, "UPLOAD_SESSION_CANCEL_REQUEST_COMPLETED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_STARTED"),
            _probe_stage(attempt_id, "TEST_ITEM_DELETE_REQUEST_COMPLETED"),
            _probe_finished(attempt_id, "DELETED_TO_RECYCLE_BIN"),
            _finished(attempt_id, cleanup="DELETED_TO_RECYCLE_BIN"),
        ],
    )

    assert not live_controller._has_unresolved_prior_live_attempt(evidence_directory)


def test_prior_live_failure_before_provider_mutation_is_resolved(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "resolved-pre-mutation"
    attempt_id = "88888888-8888-4888-8888-888888888888"
    _write_live_journal(
        evidence_directory,
        [_live_start(attempt_id), _finished(attempt_id)],
    )

    assert not live_controller._has_unresolved_prior_live_attempt(evidence_directory)


@pytest.mark.parametrize(
    "unsafe_entries",
    [
        ["{not-json"],
        [
            _probe_stage(
                "99999999-9999-4999-8999-999999999999",
                "TEST_ITEM_DELETE_REQUEST_COMPLETED",
            )
        ],
    ],
    ids=["malformed", "contradictory"],
)
def test_live_controller_blocks_malformed_or_contradictory_journal_before_network(
    tmp_path: Path,
    monkeypatch,
    capsys,
    unsafe_entries: list[dict[str, object] | str],
) -> None:
    evidence_directory = tmp_path / "unsafe-journal"
    attempt_id = "99999999-9999-4999-8999-999999999999"
    _write_live_journal(
        evidence_directory,
        [_live_start(attempt_id), *unsafe_entries, _finished(attempt_id)],
    )
    _assert_live_guard_blocks_before_oauth_and_launcher(
        evidence_directory, monkeypatch, capsys
    )


def test_live_controller_rejects_noncanonical_evidence_directory(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    canonical_directory = tmp_path / "canonical"
    alternate_directory = tmp_path / "alternate"
    monkeypatch.setattr(
        live_controller,
        "DEFAULT_EVIDENCE_DIRECTORY",
        canonical_directory,
    )
    monkeypatch.setenv(CLIENT_ID_ENVIRONMENT_VARIABLE, live_controller.EXPECTED_CLIENT_ID)
    monkeypatch.setenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, "must-not-be-used")

    assert live_controller.run(
        [
            "--live",
            "--allow-live-write",
            "--cleanup-test-item",
            "--evidence-directory",
            str(alternate_directory),
        ]
    ) == 1
    output = json.loads(capsys.readouterr().out)
    assert output["failure_code"] == "LIVE_EVIDENCE_DIRECTORY_REJECTED"
    assert output["network"] == "NOT_ATTEMPTED"
    assert output["evidence_file"] is None
    assert not canonical_directory.exists()
    assert not alternate_directory.exists()


def test_evidence_initialization_failure_is_sanitized(tmp_path: Path) -> None:
    blocked_evidence_path = tmp_path / "not-a-directory"
    blocked_evidence_path.write_text("occupied", encoding="utf-8")
    secret_canary = "evidence-init-secret-must-not-leak"
    environment = os.environ.copy()
    environment[CLIENT_SECRET_ENVIRONMENT_VARIABLE] = secret_canary

    completed = subprocess.run(
        [
            sys.executable,
            str(CONTROLLER_PATH),
            "--self-test",
            "--evidence-directory",
            str(blocked_evidence_path),
        ],
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )

    assert completed.returncode == 1
    assert completed.stderr == ""
    report = json.loads(completed.stdout)
    assert report["failure_code"] == "EVIDENCE_INITIALIZATION_FAILED"
    assert report["evidence_file"] is None
    assert report["network"] == "NOT_ATTEMPTED"
    assert secret_canary not in completed.stdout
