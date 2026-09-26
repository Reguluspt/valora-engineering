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
    build_launcher_command,
    validate_launcher_report,
)

CANDIDATE = "C2_AUTO_V2"
V2_CANDIDATE = "C2_AUTO_V1"
NAIVE_CHECKED_AT_VALUES = (
    "2026-09-18",
    "2026-09-18T00:00:00",
)


def _safe_c2_report() -> dict:
    return {
        "schema_version": 3,
        "candidate": CANDIDATE,
        "runtime_gate": "BLOCKED",
        "checked_at": "2026-09-18T00:00:00+00:00",
        "status": "PASS",
        "outcome": "OBSERVED_SAFE_STALE_REJECTION",
        "reason_code": "SAFE_412",
        "phase": "COMPLETE",
        "fresh_final_http_status": 200,
        "stale_final_http_status": 412,
        "provider_error_code": None,
        "partial_observations": {
            "fresh": {"http_status": 202, "range_class": "EXPECTED_START"},
            "stale": {"http_status": 202, "range_class": "EXPECTED_START"},
        },
        "checks": {
            "fresh_partial_preserved": True,
            "fresh_commit_verified": True,
            "stale_partial_preserved": True,
            "concurrent_write_verified": True,
            "item_identity_preserved": True,
            "concurrent_bytes_preserved": True,
            "concurrent_etag_preserved": True,
            "stale_candidate_observed": False,
        },
        "cleanup": "DELETED_TO_RECYCLE_BIN",
        "cleanup_issue": "NONE",
    }


def _safe_v2_report() -> dict:
    report = _safe_c2_report()
    report["schema_version"] = 2
    report["candidate"] = V2_CANDIDATE
    report.pop("partial_observations")
    return report


def test_build_launcher_command_preserves_windows_path_as_one_argument() -> None:
    python_executable = r"C:\Program Files\Python 3.14\python.exe"
    command = build_launcher_command(
        node_executable=r"C:\Program Files\nodejs\node.exe",
        python_executable=python_executable,
        self_test=False,
        candidate=CANDIDATE,
    )
    assert command == [
        r"C:\Program Files\nodejs\node.exe",
        str(LAUNCHER_PATH),
        "--python-executable",
        python_executable,
        "--candidate",
        CANDIDATE,
        "--allow-live-write",
        "--cleanup-test-item",
    ]
    assert command.count(python_executable) == 1


def test_oauth_diagnostic_normalizer_discards_untrusted_fields() -> None:
    details = live_controller._normalize_oauth_diagnostics(
        phase="TOKEN_REDEMPTION",
        payload={
            "error": "invalid_client",
            "error_codes": [7000215, True, "7000215", -1, 7000215],
            "correlation_id": "not-a-uuid",
            "error_description": "do-not-persist-this-description",
        },
    )
    assert details == {
        "oauth": {
            "phase": "TOKEN_REDEMPTION",
            "oauth_error": "invalid_client",
            "aadsts_codes": [7000215],
            "correlation_id": None,
        }
    }
    assert live_controller._valid_failure_details(details)


def test_oauth_failure_details_enforce_exact_schema_and_bound() -> None:
    valid = live_controller._normalize_oauth_diagnostics(
        phase="AUTHORIZATION_RESPONSE",
        payload={"error": "access_denied"},
    )
    assert live_controller._valid_failure_details(valid)
    assert not live_controller._valid_failure_details({"oauth": {**valid["oauth"], "description": "x"}})
    assert not live_controller._valid_failure_details({"oauth": {**valid["oauth"], "aadsts_codes": [True]}})
    assert not live_controller._valid_failure_details({"oversize": "x" * 1100})


def test_c2_report_validators_require_exact_candidate_and_predicates() -> None:
    report = _safe_c2_report()
    assert live_controller._validate_probe_report(
        report,
        exit_code=0,
        self_test=False,
        expected_candidate=CANDIDATE,
    )
    assert validate_launcher_report(
        report,
        self_test=False,
        forbidden=set(),
        expected_candidate=CANDIDATE,
    )
    invalid_reports = []
    for key, value in (
        ("candidate", "C1_EXPLICIT_V1"),
        ("stale_final_http_status", 409),
        ("schema_version", True),
    ):
        candidate = json.loads(json.dumps(report))
        candidate[key] = value
        invalid_reports.append(candidate)
    missing_check = json.loads(json.dumps(report))
    missing_check["checks"]["concurrent_etag_preserved"] = None
    invalid_reports.append(missing_check)
    boolean_check = json.loads(json.dumps(report))
    boolean_check["checks"]["concurrent_etag_preserved"] = 1
    invalid_reports.append(boolean_check)
    unknown_key = {**report, "provider_body": "unsafe"}
    invalid_reports.append(unknown_key)
    boolean_partial_status = json.loads(json.dumps(report))
    boolean_partial_status["partial_observations"]["fresh"]["http_status"] = True
    invalid_reports.append(boolean_partial_status)
    unknown_partial_class = json.loads(json.dumps(report))
    unknown_partial_class["partial_observations"]["fresh"]["range_class"] = "RAW_RANGE"
    invalid_reports.append(unknown_partial_class)
    mismatched_partial_reason = json.loads(json.dumps(report))
    mismatched_partial_reason.update(
        status="FAIL",
        outcome="INCONCLUSIVE",
        reason_code="PARTIAL_RANGE_MISSING",
        phase="FRESH",
        fresh_final_http_status=None,
        stale_final_http_status=None,
    )
    mismatched_partial_reason["checks"] = {
        key: None for key in mismatched_partial_reason["checks"]
    }
    invalid_reports.append(mismatched_partial_reason)
    for invalid in invalid_reports:
        assert not live_controller._validate_probe_report(
            invalid,
            exit_code=0,
            self_test=False,
            expected_candidate=CANDIDATE,
        )
        assert not validate_launcher_report(
            invalid,
            self_test=False,
            forbidden=set(),
            expected_candidate=CANDIDATE,
        )
    false_safe_fail = {**report, "status": "FAIL"}
    assert not live_controller._validate_probe_report(
        false_safe_fail,
        exit_code=1,
        self_test=False,
        expected_candidate=CANDIDATE,
    )
    assert not validate_launcher_report(
        false_safe_fail,
        self_test=False,
        forbidden=set(),
        expected_candidate=CANDIDATE,
    )


def test_v2_report_reader_is_explicit_and_read_only() -> None:
    report = _safe_v2_report()
    assert live_controller._validate_v2_c2_probe_report(
        report,
        exit_code=0,
        expected_candidate=V2_CANDIDATE,
    )
    assert not live_controller._validate_v2_c2_probe_report(
        _safe_c2_report(),
        exit_code=0,
        expected_candidate=V2_CANDIDATE,
    )
    assert not validate_launcher_report(
        report,
        self_test=False,
        forbidden=set(),
        expected_candidate=V2_CANDIDATE,
    )


@pytest.mark.parametrize("checked_at", NAIVE_CHECKED_AT_VALUES)
def test_controller_validators_reject_checked_at_without_timezone(
    checked_at: str,
) -> None:
    report = {**_safe_c2_report(), "checked_at": checked_at}

    assert not live_controller._validate_probe_report(
        report,
        exit_code=0,
        self_test=False,
        expected_candidate=CANDIDATE,
    )
    assert not validate_launcher_report(
        report,
        self_test=False,
        forbidden=set(),
        expected_candidate=CANDIDATE,
    )


def test_exact_controller_self_test_is_no_network_and_persists_v3_evidence(tmp_path: Path) -> None:
    evidence_directory = tmp_path / "evidence with spaces"
    environment = os.environ.copy()
    environment[CLIENT_SECRET_ENVIRONMENT_VARIABLE] = "client-secret-canary"
    environment[live_controller.TOKEN_ENVIRONMENT_VARIABLE] = "access-token-canary"
    completed = subprocess.run(
        [sys.executable, str(CONTROLLER_PATH), "--self-test", "--candidate", CANDIDATE, "--evidence-directory", str(evidence_directory)],
        cwd=tmp_path,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    output = json.loads(completed.stdout)
    assert output["status"] == "PASS"
    assert output["network"] == "NOT_ATTEMPTED"
    evidence_file = next(evidence_directory.glob("*.json"))
    evidence_text = evidence_file.read_text(encoding="utf-8")
    evidence = json.loads(evidence_text)
    assert evidence["schema_version"] == 3
    assert evidence["candidate"] == CANDIDATE
    assert evidence["launcher"] == {"exit_code": 0, "report": SELF_TEST_REPORT, "stderr": "EMPTY"}
    assert evidence["probe_stages"] == [
        {"at": evidence["probe_stages"][0]["at"], "stage": "PROBE_SELF_TEST_STARTED"}
    ]
    journal = next(evidence_directory.glob("*.events.jsonl")).read_text(encoding="utf-8")
    header = json.loads(journal.splitlines()[0])
    assert header["schema_version"] == 3
    assert header["candidate"] == CANDIDATE
    for canary in ("client-secret-canary", "access-token-canary"):
        assert canary not in completed.stdout
        assert canary not in evidence_text
        assert canary not in journal


def test_live_validation_rejects_missing_acknowledgement_before_network(tmp_path: Path, monkeypatch, capsys) -> None:
    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", tmp_path)
    assert live_controller.run(["--live", "--candidate", CANDIDATE]) == 1
    report = json.loads(capsys.readouterr().out)
    assert report["failure_code"] == "LIVE_ACKNOWLEDGEMENTS_REQUIRED"
    assert report["network"] == "NOT_ATTEMPTED"


def test_live_validation_rejects_wrong_app_without_recording_secret(tmp_path: Path, monkeypatch, capsys) -> None:
    secret = "wrong-app-secret-canary"
    monkeypatch.setattr(live_controller, "DEFAULT_EVIDENCE_DIRECTORY", tmp_path)
    monkeypatch.setenv(CLIENT_ID_ENVIRONMENT_VARIABLE, "wrong-client-id")
    monkeypatch.setenv(CLIENT_SECRET_ENVIRONMENT_VARIABLE, secret)
    assert live_controller.run([
        "--live", "--candidate", CANDIDATE, "--allow-live-write", "--cleanup-test-item"
    ]) == 1
    captured = capsys.readouterr()
    report = json.loads(captured.out)
    assert report["failure_code"] == "OAUTH_CONFIGURATION_REJECTED"
    assert report["network"] == "NOT_ATTEMPTED"
    assert secret not in captured.out
    assert secret not in next(tmp_path.glob("*.json")).read_text(encoding="utf-8")


class _FakeServer:
    def __init__(self, address, handler) -> None:
        self.address = address
        self.handler = handler

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback) -> None:
        return None


def _install_oauth_fakes(monkeypatch, callback: dict[str, str], result):
    calls = {"msal": 0, "redemption_transport": 0}

    class FakeApplication:
        def __init__(self, client_id: str, **kwargs) -> None:
            assert client_id == live_controller.EXPECTED_CLIENT_ID

        def initiate_auth_code_flow(self, **kwargs) -> dict:
            return {"auth_uri": "https://login.microsoftonline.test/authorize", "state": "right-state"}

        def acquire_token_by_auth_code_flow(self, flow: dict, response: dict):
            calls["msal"] += 1
            if response.get("state") != flow["state"]:
                raise ValueError("secret state mismatch")
            if "error" in response:
                return result
            calls["redemption_transport"] += 1
            return result

    def return_callback(server):
        live_controller._CallbackHandler.callback_response = callback
        return callback

    monkeypatch.setattr(live_controller.msal, "ConfidentialClientApplication", FakeApplication)
    monkeypatch.setattr(live_controller, "HTTPServer", _FakeServer)
    monkeypatch.setattr(live_controller, "_wait_for_callback", return_callback)
    monkeypatch.setattr(live_controller.webbrowser, "open", lambda *args, **kwargs: True)
    return calls


def test_oauth_success_clears_callback(monkeypatch) -> None:
    callback = {"code": "authorization-code", "state": "right-state"}
    result = {
        "access_token": "short-lived-token",
        "scope": "Files.ReadWrite",
        "id_token_claims": {
            "aud": live_controller.EXPECTED_CLIENT_ID,
            "iss": live_controller.CONSUMER_ISSUER,
            "sub": "personal-subject",
            "tid": live_controller.CONSUMER_TENANT_ID,
        },
    }
    _install_oauth_fakes(monkeypatch, callback, result)
    token = live_controller._acquire_live_access_token(
        client_id=live_controller.EXPECTED_CLIENT_ID,
        client_secret="temporary-secret",
    )
    assert token == "short-lived-token"
    assert callback == {}
    assert live_controller._CallbackHandler.callback_response is None


@pytest.mark.parametrize(
    ("callback", "result", "code", "phase"),
    [
        ({"error": "access_denied", "state": "right-state"}, {"error": "access_denied", "error_description": "canary"}, "OAUTH_AUTHORIZATION_REJECTED", "AUTHORIZATION_RESPONSE"),
        ({"code": "authorization-code", "state": "right-state"}, {"error": "invalid_client", "error_codes": [7000215], "error_description": "canary"}, "OAUTH_TOKEN_REDEMPTION_REJECTED", "TOKEN_REDEMPTION"),
    ],
)
def test_oauth_rejections_are_phase_classified_and_cleared(monkeypatch, callback, result, code, phase) -> None:
    calls = _install_oauth_fakes(monkeypatch, callback, result)
    with pytest.raises(live_controller.ControllerFailure) as caught:
        live_controller._acquire_live_access_token(
            client_id=live_controller.EXPECTED_CLIENT_ID,
            client_secret="temporary-secret",
        )
    assert caught.value.code == code
    assert caught.value.details["oauth"]["phase"] == phase
    assert "canary" not in json.dumps(caught.value.details)
    assert calls["redemption_transport"] == (1 if phase == "TOKEN_REDEMPTION" else 0)
    assert callback == {}
    assert live_controller._CallbackHandler.callback_response is None


@pytest.mark.parametrize("callback", [{"code": "x", "error": "access_denied", "state": "s"}, {"state": "s"}])
def test_malformed_callback_never_reaches_msal(monkeypatch, callback) -> None:
    calls = _install_oauth_fakes(monkeypatch, callback, {})
    with pytest.raises(live_controller.ControllerFailure) as caught:
        live_controller._acquire_live_access_token(
            client_id=live_controller.EXPECTED_CLIENT_ID,
            client_secret="temporary-secret",
        )
    assert caught.value.code == "OAUTH_RESPONSE_MALFORMED"
    assert calls["msal"] == 0
    assert calls["redemption_transport"] == 0
    assert callback == {}


@pytest.mark.parametrize(
    "callback",
    [
        {"code": "authorization-code", "state": "wrong-state"},
        {"code": "authorization-code"},
    ],
)
def test_state_validation_failure_is_sanitized_and_never_redeems(monkeypatch, callback) -> None:
    calls = _install_oauth_fakes(monkeypatch, callback, {})
    with pytest.raises(live_controller.ControllerFailure) as caught:
        live_controller._acquire_live_access_token(
            client_id=live_controller.EXPECTED_CLIENT_ID,
            client_secret="temporary-secret",
        )
    assert caught.value.code == "OAUTH_FLOW_VALIDATION_FAILED"
    assert caught.value.details["oauth"]["phase"] == "FLOW_VALIDATION"
    assert "secret" not in json.dumps(caught.value.details)
    assert calls["msal"] == 1
    assert calls["redemption_transport"] == 0
    assert callback == {}


def test_callback_receipt_is_neutral_and_query_code_rejected() -> None:
    live_controller._CallbackHandler.callback_response = None
    server = live_controller.HTTPServer(("127.0.0.1", 0), live_controller._CallbackHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    host, port = server.server_address
    connection = http.client.HTTPConnection(host, port, timeout=5)
    try:
        connection.request("GET", f"{live_controller.CALLBACK_PATH}?code=query&state=query")
        response = connection.getresponse()
        response.read()
        assert response.status == 405
        body = "code=form-code&state=form-state"
        connection.request(
            "POST",
            live_controller.CALLBACK_PATH,
            body=body,
            headers={"Content-Length": str(len(body)), "Content-Type": "application/x-www-form-urlencoded"},
        )
        response = connection.getresponse()
        receipt = response.read().decode("utf-8")
        assert response.status == 200
        assert "Authorization response received" in receipt
        assert "Authorization received" not in receipt
    finally:
        connection.close()
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        live_controller._CallbackHandler.callback_response = None


def _write_journal(directory: Path, entries: list[dict]) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "attempt.events.jsonl").write_text(
        "".join(json.dumps(entry, sort_keys=True) + "\n" for entry in entries),
        encoding="utf-8",
    )


def _v2_entry(attempt_id: str, record_type: str, **extra) -> dict:
    return {"at": "2026-09-18T00:00:00+00:00", "attempt_id": attempt_id, "record_type": record_type, **extra}


def _resolved_v2_entries() -> list[dict]:
    attempt_id = "aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa"
    report = _safe_v2_report()
    events = [
        _v2_entry(attempt_id, "ATTEMPT_STARTED", candidate=V2_CANDIDATE, mode="LIVE", schema_version=2),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="PROBE_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="ITEM_CREATE_REQUEST_STARTED"),
    ]
    for role in ("FRESH", "STALE"):
        events.extend([
            _v2_entry(attempt_id, "PROBE_STAGE", stage="SESSION_CREATE_REQUEST_STARTED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="SESSION_AVAILABLE", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="PARTIAL_FRAGMENT_REQUEST_STARTED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="PARTIAL_FRAGMENT_RESPONSE_VALIDATED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="POST_STATE_READ_STARTED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="POST_STATE_VERIFY_COMPLETED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="PARTIAL_DESTINATION_VERIFY_COMPLETED", session_role=role),
        ])
        if role == "STALE":
            events.append(_v2_entry(attempt_id, "PROBE_STAGE", stage="CONCURRENT_WRITE_REQUEST_STARTED"))
        events.extend([
            _v2_entry(attempt_id, "PROBE_STAGE", stage="FINAL_FRAGMENT_REQUEST_STARTED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="FINAL_FRAGMENT_RESPONSE_OBSERVED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="POST_STATE_READ_STARTED", session_role=role),
            _v2_entry(attempt_id, "PROBE_STAGE", stage="POST_STATE_VERIFY_COMPLETED", session_role=role),
        ])
        if role == "FRESH":
            events.append(_v2_entry(attempt_id, "PROBE_STAGE", stage="SESSION_COMPLETION_PROVEN", session_role=role))
        else:
            events.extend([
                _v2_entry(attempt_id, "PROBE_STAGE", stage="SESSION_CANCEL_REQUEST_STARTED", session_role=role),
                _v2_entry(attempt_id, "PROBE_STAGE", stage="SESSION_CANCEL_REQUEST_COMPLETED", session_role=role),
            ])
    events.extend([
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_REQUEST_COMPLETED"),
        _v2_entry(attempt_id, "PROBE_FINISHED", exit_code=0, report=report, status="PASS"),
        _v2_entry(
            attempt_id,
            "ATTEMPT_FINISHED",
            failure_code=None,
            failure_details=None,
            launcher={"exit_code": 0, "report": report, "stderr": "EMPTY"},
            status="PASS",
        ),
    ])
    return events


def _resolved_v2_c2_auto_v1_partial_failure_entries() -> list[dict]:
    attempt_id = "af114cc0-4a10-46eb-ba60-108facc7daa0"
    report = _safe_v2_report()
    report.update(
        status="FAIL",
        outcome="INCONCLUSIVE",
        reason_code="FINAL_NOT_COMPLETED",
        phase="FRESH",
        fresh_final_http_status=None,
        stale_final_http_status=None,
    )
    report["checks"] = {key: None for key in report["checks"]}
    report["checks"]["fresh_partial_preserved"] = True
    events = [
        _v2_entry(
            attempt_id,
            "ATTEMPT_STARTED",
            candidate=V2_CANDIDATE,
            mode="LIVE",
            schema_version=2,
        ),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="PROBE_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="DRIVE_VERIFY_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="ITEM_CREATE_REQUEST_STARTED"),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CREATE_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_AVAILABLE",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="PARTIAL_FRAGMENT_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="POST_STATE_READ_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="POST_STATE_VERIFY_COMPLETED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="PARTIAL_DESTINATION_VERIFY_COMPLETED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CANCEL_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CANCEL_REQUEST_COMPLETED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="TEST_ITEM_DELETE_REQUEST_STARTED",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="TEST_ITEM_DELETE_REQUEST_COMPLETED",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_FINISHED",
            exit_code=1,
            report=report,
            status="FAIL",
        ),
        _v2_entry(
            attempt_id,
            "ATTEMPT_FINISHED",
            failure_code="PROBE_REPORTED_FAILURE",
            failure_details=None,
            launcher={"exit_code": 1, "report": report, "stderr": "EMPTY"},
            status="FAIL",
        ),
    ]
    return events


def _resolved_v3_entries() -> list[dict]:
    entries = json.loads(json.dumps(_resolved_v2_entries()))
    report = _safe_c2_report()
    entries[0]["candidate"] = CANDIDATE
    entries[0]["schema_version"] = 3
    for entry in entries:
        if entry["record_type"] == "PROBE_FINISHED":
            entry["report"] = report
        elif entry["record_type"] == "ATTEMPT_FINISHED":
            entry["launcher"]["report"] = report
    for role in ("STALE", "FRESH"):
        validated_index = next(
            index
            for index, entry in enumerate(entries)
            if entry.get("stage") == "PARTIAL_FRAGMENT_RESPONSE_VALIDATED"
            and entry.get("session_role") == role
        )
        entries.insert(
            validated_index,
            _v2_entry(
                entries[0]["attempt_id"],
                "PROBE_STAGE",
                stage="PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
                session_role=role,
                http_status=202,
                range_class="EXPECTED_START",
            ),
        )
    return entries


def _resolved_v3_partial_read_failure_entries() -> list[dict]:
    attempt_id = "dddddddd-dddd-4ddd-8ddd-dddddddddddd"
    report = _safe_c2_report()
    report.update(
        status="FAIL",
        outcome="INCONCLUSIVE",
        reason_code="POST_STATE_UNAVAILABLE",
        phase="FRESH",
        fresh_final_http_status=None,
        stale_final_http_status=None,
        cleanup="DELETED_TO_RECYCLE_BIN",
    )
    report["partial_observations"] = {
        "fresh": {"http_status": 500, "range_class": "NOT_APPLICABLE"},
        "stale": {"http_status": None, "range_class": "NOT_OBSERVED"},
    }
    report["checks"] = {key: None for key in report["checks"]}
    return [
        _v2_entry(
            attempt_id,
            "ATTEMPT_STARTED",
            candidate=CANDIDATE,
            mode="LIVE",
            schema_version=3,
        ),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="PROBE_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="ITEM_CREATE_REQUEST_STARTED"),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CREATE_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_AVAILABLE",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="PARTIAL_FRAGMENT_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="PARTIAL_FRAGMENT_RESPONSE_OBSERVED",
            session_role="FRESH",
            http_status=500,
            range_class="NOT_APPLICABLE",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="POST_STATE_READ_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CANCEL_REQUEST_STARTED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="SESSION_CANCEL_REQUEST_COMPLETED",
            session_role="FRESH",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="TEST_ITEM_DELETE_REQUEST_STARTED",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_STAGE",
            stage="TEST_ITEM_DELETE_REQUEST_COMPLETED",
        ),
        _v2_entry(
            attempt_id,
            "PROBE_FINISHED",
            exit_code=1,
            report=report,
            status="FAIL",
        ),
        _v2_entry(
            attempt_id,
            "ATTEMPT_FINISHED",
            failure_code="PROBE_REPORTED_FAILURE",
            failure_details=None,
            launcher={"exit_code": 1, "report": report, "stderr": "EMPTY"},
            status="FAIL",
        ),
    ]


def _resolved_v3_final_transport_failure_entries() -> list[dict]:
    entries = _resolved_v3_entries()
    attempt_id = entries[0]["attempt_id"]
    report = _safe_c2_report()
    report.update(
        status="FAIL",
        outcome="INCONCLUSIVE",
        reason_code="FRESH_CONTROL_FAILED",
        phase="FRESH",
        fresh_final_http_status=None,
        stale_final_http_status=None,
    )
    report["partial_observations"]["stale"] = {
        "http_status": None,
        "range_class": "NOT_OBSERVED",
    }
    report["checks"] = {key: None for key in report["checks"]}
    report["checks"].update(
        fresh_partial_preserved=True,
        fresh_commit_verified=False,
    )

    filtered: list[dict] = []
    for entry in entries:
        stage = entry.get("stage")
        if entry.get("session_role") == "STALE" or stage == "CONCURRENT_WRITE_REQUEST_STARTED":
            continue
        if (
            stage == "FINAL_FRAGMENT_RESPONSE_OBSERVED"
            and entry.get("session_role") == "FRESH"
        ):
            continue
        if stage == "SESSION_COMPLETION_PROVEN":
            filtered.extend(
                [
                    _v2_entry(
                        attempt_id,
                        "PROBE_STAGE",
                        stage="SESSION_CANCEL_REQUEST_STARTED",
                        session_role="FRESH",
                    ),
                    _v2_entry(
                        attempt_id,
                        "PROBE_STAGE",
                        stage="SESSION_CANCEL_REQUEST_COMPLETED",
                        session_role="FRESH",
                    ),
                ]
            )
            continue
        if entry["record_type"] == "PROBE_FINISHED":
            entry.update(exit_code=1, report=report, status="FAIL")
        elif entry["record_type"] == "ATTEMPT_FINISHED":
            entry.update(
                failure_code="PROBE_REPORTED_FAILURE",
                failure_details=None,
                launcher={"exit_code": 1, "report": report, "stderr": "EMPTY"},
                status="FAIL",
            )
        filtered.append(entry)
    return filtered


def test_v2_resolved_ledger_is_accepted(tmp_path: Path) -> None:
    _write_journal(tmp_path, _resolved_v2_entries())
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False


def test_finalized_c2_auto_v1_partial_failure_shape_remains_resolved(
    tmp_path: Path,
) -> None:
    _write_journal(tmp_path, _resolved_v2_c2_auto_v1_partial_failure_entries())
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False


def test_v3_resolved_ledger_is_accepted(tmp_path: Path) -> None:
    _write_journal(tmp_path, _resolved_v3_entries())
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False


def test_v3_partial_read_failure_is_resolved_only_with_read_start(
    tmp_path: Path,
) -> None:
    entries = _resolved_v3_partial_read_failure_entries()
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False
    entries = [
        entry
        for entry in entries
        if entry.get("stage") != "POST_STATE_READ_STARTED"
    ]
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


def test_v3_duplicate_final_response_event_blocks_ledger(tmp_path: Path) -> None:
    entries = _resolved_v3_entries()
    response_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.get("stage") == "FINAL_FRAGMENT_RESPONSE_OBSERVED"
        and entry.get("session_role") == "FRESH"
    )
    entries.insert(response_index + 1, dict(entries[response_index]))
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


def test_v3_pre_final_read_cannot_substitute_for_post_final_read(
    tmp_path: Path,
) -> None:
    entries = _resolved_v3_final_transport_failure_entries()
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False

    fresh_reads = [
        entry
        for entry in entries
        if entry.get("stage") == "POST_STATE_READ_STARTED"
        and entry.get("session_role") == "FRESH"
    ]
    second_read = fresh_reads[1]
    second_read_index = entries.index(second_read)
    second_verify = entries[second_read_index + 1]
    assert second_verify.get("stage") == "POST_STATE_VERIFY_COMPLETED"
    entries.remove(second_read)
    entries.remove(second_verify)
    final_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.get("stage") == "FINAL_FRAGMENT_REQUEST_STARTED"
        and entry.get("session_role") == "FRESH"
    )
    entries[final_index:final_index] = [second_read, second_verify]

    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


def test_v3_completion_requires_observed_final_response(tmp_path: Path) -> None:
    entries = _resolved_v3_final_transport_failure_entries()
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False

    cancel_start_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.get("stage") == "SESSION_CANCEL_REQUEST_STARTED"
        and entry.get("session_role") == "FRESH"
    )
    assert entries[cancel_start_index + 1].get("stage") == (
        "SESSION_CANCEL_REQUEST_COMPLETED"
    )
    entries[cancel_start_index : cancel_start_index + 2] = [
        _v2_entry(
            entries[0]["attempt_id"],
            "PROBE_STAGE",
            stage="SESSION_COMPLETION_PROVEN",
            session_role="FRESH",
        )
    ]

    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


def test_v3_completion_rejects_observed_non_completion_status(
    tmp_path: Path,
) -> None:
    entries = _resolved_v3_entries()
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False

    cancel_start_index = next(
        index
        for index, entry in enumerate(entries)
        if entry.get("stage") == "SESSION_CANCEL_REQUEST_STARTED"
        and entry.get("session_role") == "STALE"
    )
    assert entries[cancel_start_index + 1].get("stage") == (
        "SESSION_CANCEL_REQUEST_COMPLETED"
    )
    entries[cancel_start_index : cancel_start_index + 2] = [
        _v2_entry(
            entries[0]["attempt_id"],
            "PROBE_STAGE",
            stage="SESSION_COMPLETION_PROVEN",
            session_role="STALE",
        )
    ]

    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


@pytest.mark.parametrize(
    "mutation",
    ["missing-observation", "report-mismatch", "boolean-status", "observation-after-read"],
)
def test_v3_partial_observation_drift_blocks_ledger(
    tmp_path: Path, mutation: str
) -> None:
    entries = _resolved_v3_entries()
    observation = next(
        entry
        for entry in entries
        if entry.get("stage") == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED"
        and entry.get("session_role") == "FRESH"
    )
    if mutation == "missing-observation":
        entries.remove(observation)
    elif mutation == "report-mismatch":
        terminal = next(
            entry for entry in entries if entry["record_type"] == "ATTEMPT_FINISHED"
        )
        terminal["launcher"]["report"]["partial_observations"]["fresh"] = {
            "http_status": 202,
            "range_class": "MALFORMED",
        }
    elif mutation == "boolean-status":
        observation["http_status"] = True
    else:
        entries.remove(observation)
        read_index = next(
            index
            for index, entry in enumerate(entries)
            if entry.get("stage") == "POST_STATE_READ_STARTED"
            and entry.get("session_role") == "FRESH"
        )
        entries.insert(read_index + 1, observation)
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


@pytest.mark.parametrize(
    "mutation",
    [
        "missing-cancel",
        "mixed-stage",
        "candidate-mismatch",
        "stage-after-delete",
        "mutation-after-cancel-start",
        "item-create-after-session",
    ],
)
def test_v2_malformed_or_unresolved_ledgers_block(tmp_path: Path, mutation: str) -> None:
    entries = _resolved_v2_entries()
    if mutation == "missing-cancel":
        entries = [entry for entry in entries if entry.get("stage") != "SESSION_CANCEL_REQUEST_COMPLETED"]
    elif mutation == "mixed-stage":
        entries.insert(2, _v2_entry(entries[0]["attempt_id"], "PROBE_STAGE", stage="UPLOAD_STAGE_REQUEST_STARTED"))
    elif mutation == "candidate-mismatch":
        entries[0]["candidate"] = "C1_EXPLICIT_V1"
    elif mutation == "stage-after-delete":
        entries.insert(-2, _v2_entry(entries[0]["attempt_id"], "PROBE_STAGE", stage="CONCURRENT_WRITE_REQUEST_STARTED"))
    elif mutation == "mutation-after-cancel-start":
        cancel = next(
            entry
            for entry in entries
            if entry.get("stage") == "SESSION_CANCEL_REQUEST_STARTED"
            and entry.get("session_role") == "STALE"
        )
        entries.remove(cancel)
        concurrent_index = next(
            index
            for index, entry in enumerate(entries)
            if entry.get("stage") == "CONCURRENT_WRITE_REQUEST_STARTED"
        )
        entries.insert(concurrent_index, cancel)
    else:
        create = next(entry for entry in entries if entry.get("stage") == "ITEM_CREATE_REQUEST_STARTED")
        entries.remove(create)
        session_index = next(
            index
            for index, entry in enumerate(entries)
            if entry.get("stage") == "SESSION_AVAILABLE" and entry.get("session_role") == "FRESH"
        )
        entries.insert(session_index + 1, create)
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is True


def test_v2_by_name_cleanup_without_bound_identity_is_resolved(tmp_path: Path) -> None:
    attempt_id = "cccccccc-cccc-4ccc-8ccc-cccccccccccc"
    report = _safe_v2_report()
    report.update({
        "status": "FAIL",
        "outcome": "INCONCLUSIVE",
        "reason_code": "FIXTURE_FAILED",
        "phase": "FIXTURE",
        "fresh_final_http_status": None,
        "stale_final_http_status": None,
        "checks": {key: None for key in report["checks"]},
        "cleanup": "ABSENT_OR_DELETED_TO_RECYCLE_BIN",
    })
    entries = [
        _v2_entry(attempt_id, "ATTEMPT_STARTED", candidate=V2_CANDIDATE, mode="LIVE", schema_version=2),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="PROBE_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="DRIVE_VERIFY_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="ITEM_CREATE_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_BY_NAME_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_BY_NAME_REQUEST_COMPLETED"),
        _v2_entry(attempt_id, "PROBE_FINISHED", exit_code=1, report=report, status="FAIL"),
        _v2_entry(
            attempt_id,
            "ATTEMPT_FINISHED",
            failure_code="PROBE_REPORTED_FAILURE",
            failure_details=None,
            launcher={"exit_code": 1, "report": report, "stderr": "EMPTY"},
            status="FAIL",
        ),
    ]
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False


def test_legacy_resolved_failure_remains_readable(tmp_path: Path) -> None:
    attempt_id = "bbbbbbbb-bbbb-4bbb-8bbb-bbbbbbbbbbbb"
    report = {"status": "FAIL", "reason": "Sanitized failure.", "cleanup": "DELETED_TO_RECYCLE_BIN"}
    entries = [
        _v2_entry(attempt_id, "ATTEMPT_STARTED", mode="LIVE"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="PROBE_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="ITEM_CREATE_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_REQUEST_STARTED"),
        _v2_entry(attempt_id, "PROBE_STAGE", stage="TEST_ITEM_DELETE_REQUEST_COMPLETED"),
        _v2_entry(attempt_id, "PROBE_FINISHED", exit_code=1, report=report, status="FAIL"),
        _v2_entry(attempt_id, "ATTEMPT_FINISHED", failure_code="PROBE_REPORTED_FAILURE", failure_details=None, launcher={"exit_code": 1, "report": report, "stderr": "EMPTY"}, status="FAIL"),
    ]
    _write_journal(tmp_path, entries)
    assert live_controller._has_unresolved_prior_live_attempt(tmp_path) is False
