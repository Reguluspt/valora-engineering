from __future__ import annotations

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
    MAX_DOWNLOAD_BYTES,
    OneDrivePersonalIfMatchProbe,
    ProbeFailure,
    TOKEN_ENVIRONMENT_VARIABLE,
    _classify_next_expected_ranges,
    _record_probe_result,
    _test_item_name,
    main,
)

DRIVE_ID = "drive-personal"
ITEM_ID = "item-probe"
ITEM_NAME = "VALORA-PR07-IF-MATCH-test.bin"
CANDIDATE = "C2_AUTO_V2"
NAIVE_CHECKED_AT_VALUES = (
    "2026-09-18",
    "2026-09-18T00:00:00",
)
BACKEND_DIRECTORY = Path(__file__).resolve().parents[1]
LAUNCHER_PATH = BACKEND_DIRECTORY / "tools" / "pr07_onedrive_personal_if_match_launcher.mjs"
NODE_EXECUTABLE = shutil.which("node")
SELF_TEST_SENTINEL = "valora-local-self-test-sentinel"
SELF_TEST_REPORT = {
    "candidate": CANDIDATE,
    "dependency_import": "PASS",
    "environment": "PRESENT",
    "interpreter": "PASS",
    "mode": "SELF_TEST",
    "network": "NOT_ATTEMPTED",
    "package_resolution": "PASS",
    "runtime_gate": "BLOCKED",
    "schema_version": 3,
    "status": "PASS",
    "working_directory": "BACKEND",
}


def _metadata(e_tag: str, item_id: str = ITEM_ID) -> dict[str, str]:
    return {"id": item_id, "name": ITEM_NAME, "eTag": e_tag}


class C2GraphScenario:
    def __init__(
        self,
        *,
        stale_status: int = 412,
        stale_mutates: bool = False,
        stale_etag_only: bool = False,
        stale_third_state: bool = False,
        transport_after_stale_mutation: bool = False,
        close_stale_session_on_mutation: bool = True,
        partial_status: int = 202,
        partial_range: list[str] | None = None,
        transport_on_partial_role: str | None = None,
        fail_post_partial_read_role: str | None = None,
        mutate_on_partial_role: str | None = None,
        cancel_status: int = 204,
        delete_status: int = 204,
    ) -> None:
        self.content = b""
        self.e_tag_number = 1
        self.session_number = 0
        self.sessions: dict[str, dict] = {}
        self.stale_status = stale_status
        self.stale_mutates = stale_mutates
        self.stale_etag_only = stale_etag_only
        self.stale_third_state = stale_third_state
        self.transport_after_stale_mutation = transport_after_stale_mutation
        self.close_stale_session_on_mutation = close_stale_session_on_mutation
        self.partial_status = partial_status
        self.partial_range = ["327680-"] if partial_range is None else partial_range
        self.transport_on_partial_role = transport_on_partial_role
        self.fail_post_partial_read_role = fail_post_partial_read_role
        self.fail_next_download = False
        self.mutate_on_partial_role = mutate_on_partial_role
        self.cancel_status = cancel_status
        self.delete_status = delete_status
        self.deleted = False
        self.final_puts = 0
        self.partial_puts = 0
        self.trace: list[str] = []
        self.authorization_seen_on_upload_url = False
        self.authorization_seen_on_download_url = False

    @property
    def e_tag(self) -> str:
        return f'"etag-{self.e_tag_number}"'

    def __call__(self, request: httpx.Request) -> httpx.Response:
        path = request.url.path
        authorization = request.headers.get("authorization")
        if request.url.host == "upload.test":
            self.authorization_seen_on_upload_url |= authorization is not None
            assert authorization is None
            session_id = path.rsplit("/", 1)[-1]
            session = self.sessions[session_id]
            role = session["role"]
            if request.method == "DELETE":
                self.trace.append(f"cancel:{role}")
                if self.cancel_status in {204, 404}:
                    session["open"] = False
                return httpx.Response(self.cancel_status)
            assert request.method == "PUT"
            content_range = request.headers["content-range"]
            if content_range == "bytes 0-327679/655360":
                self.trace.append(f"partial:{role}")
                self.partial_puts += 1
                session["parts"].append(request.content)
                if self.transport_on_partial_role == role:
                    raise httpx.ReadTimeout("lost", request=request)
                if self.fail_post_partial_read_role == role:
                    self.fail_next_download = True
                if self.mutate_on_partial_role == role:
                    self.content = request.content + b"x" * (655360 - len(request.content))
                    self.e_tag_number += 1
                return httpx.Response(
                    self.partial_status,
                    json={"nextExpectedRanges": self.partial_range},
                )
            assert content_range == "bytes 327680-655359/655360"
            self.trace.append(f"final:{role}")
            self.final_puts += 1
            candidate = b"".join([*session["parts"], request.content])
            stale = session["e_tag"] != self.e_tag
            if stale:
                if self.stale_mutates or self.transport_after_stale_mutation:
                    self.content = candidate
                    self.e_tag_number += 1
                    if self.close_stale_session_on_mutation:
                        session["open"] = False
                elif self.stale_etag_only:
                    self.e_tag_number += 1
                elif self.stale_third_state:
                    self.content = (b"third" * 131072)[:655360]
                    self.e_tag_number += 1
                if self.transport_after_stale_mutation:
                    raise httpx.ReadTimeout("lost", request=request)
                if not self.stale_mutates:
                    return httpx.Response(
                        self.stale_status,
                        json={"error": {"code": "resourceModified", "message": "canary"}},
                    )
            self.content = candidate
            self.e_tag_number += 1
            session["open"] = False
            return httpx.Response(
                self.stale_status if stale else 200,
                json=_metadata(self.e_tag),
            )
        if request.url.host == "download.test":
            self.authorization_seen_on_download_url |= authorization is not None
            self.trace.append("download")
            if self.fail_next_download:
                self.fail_next_download = False
                return httpx.Response(503)
            return httpx.Response(200, content=self.content)

        assert authorization == "Bearer secret-token"
        if request.method == "GET" and path.endswith("/me/drive"):
            return httpx.Response(200, json={"id": DRIVE_ID, "driveType": "personal"})
        if request.method == "PUT" and path.endswith(":/content"):
            self.trace.append("fixture")
            self.content = request.content
            return httpx.Response(201, json=_metadata(self.e_tag))
        if request.method == "POST" and path.endswith("/createUploadSession"):
            assert json.loads(request.content) == {}
            assert request.headers["if-match"] == self.e_tag
            self.session_number += 1
            role = "FRESH" if self.session_number == 1 else "STALE"
            self.trace.append(f"session:{role}")
            session_id = str(self.session_number)
            self.sessions[session_id] = {
                "e_tag": request.headers["if-match"],
                "open": True,
                "parts": [],
                "role": role,
            }
            return httpx.Response(200, json={"uploadUrl": f"https://upload.test/{session_id}"})
        if request.method == "PUT" and path.endswith(f"/{ITEM_ID}/content"):
            self.trace.append("concurrent")
            assert request.headers["if-match"] == self.e_tag
            self.content = request.content
            self.e_tag_number += 1
            return httpx.Response(200, json=_metadata(self.e_tag))
        if request.method == "GET" and path.endswith(f"/{ITEM_ID}/content"):
            return httpx.Response(302, headers={"Location": "https://download.test/content"})
        if request.method == "GET" and path.endswith(f"/{ITEM_ID}"):
            return httpx.Response(200, json=_metadata(self.e_tag))
        if request.method == "DELETE" and path.endswith(f"/{ITEM_ID}"):
            self.trace.append("delete")
            self.deleted = True
            return httpx.Response(self.delete_status)
        raise AssertionError(f"Unexpected request: {request.method} {request.url}")


def _run(scenario: C2GraphScenario):
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)
    return probe.run(), scenario


def test_probe_item_name_is_recoverable_from_attempt_id(monkeypatch) -> None:
    attempt_id = "33333333-3333-4333-8333-333333333333"
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    assert _test_item_name() == f"VALORA-PR07-IF-MATCH-{attempt_id}.bin"


@pytest.mark.parametrize(
    "ranges",
    [
        ["327680-"],
        ["327680-655359"],
        ["327680-400000", "400001-"],
    ],
)
def test_partial_range_parser_accepts_documented_tail_forms(ranges: list[str]) -> None:
    assert _classify_next_expected_ranges(ranges) == "EXPECTED_START"


@pytest.mark.parametrize("ranges", [None, []])
def test_partial_range_parser_classifies_missing_values(ranges) -> None:
    assert _classify_next_expected_ranges(ranges) == "MISSING"


@pytest.mark.parametrize(
    "ranges",
    [
        "327680-",
        [True],
        ["+327680-"],
        [" 327680-"],
        ["327680 -"],
        ["327680-655360"],
        ["327680-400000", "400000-"],
        ["327680-400000", "327680-400000"],
    ],
)
def test_partial_range_parser_rejects_malformed_values(ranges) -> None:
    assert _classify_next_expected_ranges(ranges) == "MALFORMED"


@pytest.mark.parametrize("ranges", [["0-"], ["327681-"], ["655360-"]])
def test_partial_range_parser_rejects_unexpected_start(ranges: list[str]) -> None:
    assert _classify_next_expected_ranges(ranges) == "UNEXPECTED_START"


def test_c2_probe_observes_safe_stale_rejection_with_two_fragments() -> None:
    report, scenario = _run(C2GraphScenario())
    assert report.status == "PASS"
    assert report.candidate == CANDIDATE
    assert report.runtime_gate == "BLOCKED"
    assert report.outcome == "OBSERVED_SAFE_STALE_REJECTION"
    assert report.reason_code == "SAFE_412"
    assert report.fresh_final_http_status == 200
    assert report.stale_final_http_status == 412
    assert report.partial_observations == {
        "fresh": {"http_status": 202, "range_class": "EXPECTED_START"},
        "stale": {"http_status": 202, "range_class": "EXPECTED_START"},
    }
    assert all(report.checks[key] is True for key in report.checks if key != "stale_candidate_observed")
    assert report.checks["stale_candidate_observed"] is False
    assert scenario.partial_puts == 2
    assert scenario.final_puts == 2
    assert scenario.deleted is True
    assert scenario.authorization_seen_on_upload_url is False
    assert scenario.authorization_seen_on_download_url is False


@pytest.mark.parametrize(
    "partial_range",
    [["327680-655359"], ["327680-400000", "400001-"]],
)
def test_documented_partial_range_variants_reach_both_final_fragments(
    partial_range: list[str],
) -> None:
    report, scenario = _run(C2GraphScenario(partial_range=partial_range))
    assert report.status == "PASS"
    assert report.partial_observations["fresh"] == {
        "http_status": 202,
        "range_class": "EXPECTED_START",
    }
    assert scenario.final_puts == 2


@pytest.mark.parametrize("stale_status", [200, 201, 412])
def test_stale_candidate_observed_is_unsafe_regardless_of_response(stale_status: int) -> None:
    report, scenario = _run(C2GraphScenario(stale_status=stale_status, stale_mutates=True))
    assert report.status == "FAIL"
    assert report.outcome == "UNSAFE_STALE_OVERWRITE"
    assert report.reason_code == "STALE_BYTES_OVERWROTE_CONCURRENT"
    assert report.checks["stale_candidate_observed"] is True
    assert report.checks["concurrent_bytes_preserved"] is False
    assert scenario.final_puts == 2


def test_response_lost_after_stale_overwrite_is_still_unsafe() -> None:
    report, scenario = _run(C2GraphScenario(transport_after_stale_mutation=True))
    assert report.outcome == "UNSAFE_STALE_OVERWRITE"
    assert report.stale_final_http_status is None
    assert scenario.trace.count("final:STALE") == 1
    assert "download" in scenario.trace[scenario.trace.index("final:STALE") + 1 :]


@pytest.mark.parametrize("transport_lost", [False, True])
def test_stale_bytes_do_not_prove_session_closed(transport_lost: bool) -> None:
    report, scenario = _run(C2GraphScenario(
        stale_status=412,
        stale_mutates=True,
        transport_after_stale_mutation=transport_lost,
        close_stale_session_on_mutation=False,
    ))
    assert report.outcome == "UNSAFE_STALE_OVERWRITE"
    assert "cancel:STALE" in scenario.trace
    assert scenario.sessions["2"]["open"] is False


def test_alternate_rejection_with_concurrent_bytes_is_inconclusive() -> None:
    report, _ = _run(C2GraphScenario(stale_status=409))
    assert report.status == "FAIL"
    assert report.outcome == "INCONCLUSIVE"
    assert report.reason_code == "ALTERNATE_REJECTION"
    assert report.checks["concurrent_bytes_preserved"] is True


def test_same_bytes_with_changed_etag_is_not_false_pass() -> None:
    report, _ = _run(C2GraphScenario(stale_etag_only=True))
    assert report.outcome == "INCONCLUSIVE"
    assert report.reason_code == "POST_STATE_INCONSISTENT"
    assert report.checks["concurrent_bytes_preserved"] is True
    assert report.checks["concurrent_etag_preserved"] is False


def test_third_state_is_inconclusive() -> None:
    report, _ = _run(C2GraphScenario(stale_third_state=True))
    assert report.outcome == "INCONCLUSIVE"
    assert report.reason_code == "THIRD_STATE"


def test_nonfinal_mutation_is_safety_violation_and_stale_branch_never_runs() -> None:
    report, scenario = _run(C2GraphScenario(mutate_on_partial_role="FRESH"))
    assert report.outcome == "SAFETY_VIOLATION"
    assert report.reason_code == "NONFINAL_MUTATION"
    assert report.checks["fresh_partial_preserved"] is False
    assert scenario.session_number == 1
    assert scenario.final_puts == 0


def test_wrong_partial_range_still_post_reads_and_never_finalizes() -> None:
    report, scenario = _run(C2GraphScenario(partial_range=["0-"]))
    assert report.outcome == "INCONCLUSIVE"
    assert report.reason_code == "PARTIAL_RANGE_UNEXPECTED"
    assert report.partial_observations["fresh"] == {
        "http_status": 202,
        "range_class": "UNEXPECTED_START",
    }
    assert report.checks["fresh_partial_preserved"] is True
    assert scenario.final_puts == 0
    partial_index = scenario.trace.index("partial:FRESH")
    assert "download" in scenario.trace[partial_index + 1 :]


def test_empty_partial_range_is_observable_and_never_finalizes() -> None:
    report, scenario = _run(C2GraphScenario(partial_range=[]))
    assert report.reason_code == "PARTIAL_RANGE_MISSING"
    assert report.partial_observations["fresh"] == {
        "http_status": 202,
        "range_class": "MISSING",
    }
    assert report.checks["fresh_partial_preserved"] is True
    assert scenario.final_puts == 0


def test_partial_transport_unknown_post_reads_without_fabricating_observation() -> None:
    report, scenario = _run(C2GraphScenario(transport_on_partial_role="FRESH"))
    assert report.reason_code == "TRANSPORT_UNKNOWN"
    assert report.partial_observations["fresh"] == {
        "http_status": None,
        "range_class": "NOT_OBSERVED",
    }
    assert report.checks["fresh_partial_preserved"] is True
    assert scenario.final_puts == 0
    partial_index = scenario.trace.index("partial:FRESH")
    assert "download" in scenario.trace[partial_index + 1 :]


def test_partial_post_read_failure_keeps_post_state_reason() -> None:
    report, scenario = _run(
        C2GraphScenario(
            partial_status=500,
            fail_post_partial_read_role="FRESH",
        )
    )
    assert report.reason_code == "POST_STATE_UNAVAILABLE"
    assert report.partial_observations["fresh"] == {
        "http_status": 500,
        "range_class": "NOT_APPLICABLE",
    }
    assert report.checks["fresh_partial_preserved"] is None
    assert scenario.final_puts == 0


def test_cancel_failure_does_not_prevent_item_delete() -> None:
    report, scenario = _run(C2GraphScenario(partial_status=500, cancel_status=503))
    assert report.status == "FAIL"
    assert report.cleanup_issue == "CANCEL_FAILED"
    assert report.cleanup == "DELETED_TO_RECYCLE_BIN"
    assert report.reason_code == "PARTIAL_HTTP_UNEXPECTED"
    assert report.partial_observations["fresh"] == {
        "http_status": 500,
        "range_class": "NOT_APPLICABLE",
    }
    assert scenario.deleted is True


def test_non_202_partial_response_body_is_not_parsed(monkeypatch) -> None:
    def fail_if_called(response: httpx.Response) -> str | None:
        raise AssertionError("non-202 partial response body must not be parsed")

    monkeypatch.setattr(
        OneDrivePersonalIfMatchProbe,
        "_provider_error_code",
        staticmethod(fail_if_called),
    )
    report, scenario = _run(C2GraphScenario(partial_status=500))
    assert report.reason_code == "PARTIAL_HTTP_UNEXPECTED"
    assert report.provider_error_code is None
    assert scenario.final_puts == 0


def test_delete_failure_preserves_primary_safe_observation() -> None:
    report, _ = _run(C2GraphScenario(delete_status=500))
    assert report.outcome == "OBSERVED_SAFE_STALE_REJECTION"
    assert report.reason_code == "SAFE_412"
    assert report.status == "FAIL"
    assert report.cleanup == "FAILED"
    assert report.cleanup_issue == "ITEM_DELETE_FAILED"


def test_final_request_is_not_sent_when_journal_marker_fails(monkeypatch) -> None:
    scenario = C2GraphScenario()
    original = probe_module._record_progress

    def fail_fresh_final(stage: str, *, session_role: str | None = None) -> None:
        if stage == "FINAL_FRAGMENT_REQUEST_STARTED" and session_role == "FRESH":
            raise ProbeFailure("Diagnostic evidence is unavailable.")
        original(stage, session_role=session_role)

    monkeypatch.setattr(probe_module, "_record_progress", fail_fresh_final)
    report, scenario = _run(scenario)
    assert report.status == "FAIL"
    assert scenario.final_puts == 0
    assert scenario.deleted is True


def test_response_marker_failure_still_runs_coherent_post_read(monkeypatch) -> None:
    scenario = C2GraphScenario(stale_status=412, stale_mutates=True)
    original = probe_module._record_progress

    def fail_stale_response(stage: str, *, session_role: str | None = None) -> None:
        if stage == "FINAL_FRAGMENT_RESPONSE_OBSERVED" and session_role == "STALE":
            raise ProbeFailure("Diagnostic evidence is unavailable.")
        original(stage, session_role=session_role)

    monkeypatch.setattr(probe_module, "_record_progress", fail_stale_response)
    report, scenario = _run(scenario)
    assert report.outcome == "UNSAFE_STALE_OVERWRITE"
    assert report.reason_code == "STALE_BYTES_OVERWROTE_CONCURRENT"
    assert report.cleanup_issue == "EVIDENCE_INCOMPLETE"
    stale_final = scenario.trace.index("final:STALE")
    assert "download" in scenario.trace[stale_final + 1 :]


def test_v3_journal_has_bounded_partial_observations_and_no_sensitive_values(
    tmp_path: Path, monkeypatch
) -> None:
    attempt_id = "11111111-1111-4111-8111-111111111111"
    journal_path = (tmp_path / f"{attempt_id}.events.jsonl").resolve()
    journal_path.write_text("", encoding="utf-8")
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    monkeypatch.setenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, str(journal_path))
    report, _ = _run(C2GraphScenario())
    _record_probe_result(probe_module.asdict(report), 0)
    entries = [json.loads(line) for line in journal_path.read_text(encoding="utf-8").splitlines()]
    session_entries = [entry for entry in entries if entry.get("stage") in probe_module.SESSION_PROGRESS_STAGES]
    assert session_entries
    assert {entry["session_role"] for entry in session_entries} == {"FRESH", "STALE"}
    response_entries = [
        entry
        for entry in entries
        if entry.get("stage") == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED"
    ]
    assert [
        {
            "http_status": entry["http_status"],
            "range_class": entry["range_class"],
            "session_role": entry["session_role"],
        }
        for entry in response_entries
    ] == [
        {"http_status": 202, "range_class": "EXPECTED_START", "session_role": "FRESH"},
        {"http_status": 202, "range_class": "EXPECTED_START", "session_role": "STALE"},
    ]
    serialized = json.dumps(entries)
    assert "secret-token" not in serialized
    assert "upload.test" not in serialized
    assert ITEM_ID not in serialized
    assert "327680-" not in serialized


def test_partial_transport_journal_has_no_response_observed_event(
    tmp_path: Path, monkeypatch
) -> None:
    attempt_id = "44444444-4444-4444-8444-444444444444"
    journal_path = (tmp_path / f"{attempt_id}.events.jsonl").resolve()
    journal_path.write_text("", encoding="utf-8")
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    monkeypatch.setenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, str(journal_path))
    report, _ = _run(C2GraphScenario(transport_on_partial_role="FRESH"))
    _record_probe_result(probe_module.asdict(report), 1)
    entries = [
        json.loads(line)
        for line in journal_path.read_text(encoding="utf-8").splitlines()
    ]
    assert not any(
        entry.get("stage") == "PARTIAL_FRAGMENT_RESPONSE_OBSERVED"
        for entry in entries
    )
    assert report.partial_observations["fresh"]["range_class"] == "NOT_OBSERVED"


def test_probe_result_writer_rejects_unknown_fields_and_token(tmp_path: Path, monkeypatch) -> None:
    attempt_id = "22222222-2222-4222-8222-222222222222"
    journal_path = (tmp_path / f"{attempt_id}.events.jsonl").resolve()
    journal_path.write_text("", encoding="utf-8")
    monkeypatch.setenv(ATTEMPT_ID_ENVIRONMENT_VARIABLE, attempt_id)
    monkeypatch.setenv(EVENT_JOURNAL_ENVIRONMENT_VARIABLE, str(journal_path))
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, "journal-secret-canary")
    with pytest.raises(ProbeFailure, match="Diagnostic evidence was rejected"):
        _record_probe_result({"status": "FAIL", "unknown": "journal-secret-canary"}, 1)
    assert journal_path.read_text(encoding="utf-8") == ""


def test_command_requires_candidate_and_live_acknowledgements(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, "secret-token")
    with pytest.raises(ProbeFailure, match="Both --allow-live-write"):
        main(["--candidate", CANDIDATE])


def test_direct_live_command_requires_controller_journal_before_client(monkeypatch) -> None:
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, "secret-token")

    class ClientMustNotConstruct:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("HTTP client must not be constructed")

    monkeypatch.setattr(probe_module.httpx, "Client", ClientMustNotConstruct)
    with pytest.raises(ProbeFailure, match="controller diagnostic evidence"):
        main(["--candidate", CANDIDATE, "--allow-live-write", "--cleanup-test-item"])


def test_self_test_is_no_network_and_exact(monkeypatch, capsys) -> None:
    monkeypatch.chdir(BACKEND_DIRECTORY)
    monkeypatch.setenv(TOKEN_ENVIRONMENT_VARIABLE, SELF_TEST_SENTINEL)

    class ClientMustNotConstruct:
        def __init__(self, *args, **kwargs) -> None:
            raise AssertionError("self-test must not construct an HTTP client")

    monkeypatch.setattr(probe_module.httpx, "Client", ClientMustNotConstruct)
    assert main(["--candidate", CANDIDATE, "--self-test"]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert json.loads(captured.out) == SELF_TEST_REPORT
    assert SELF_TEST_SENTINEL not in captured.out


def test_self_test_exact_module_surface() -> None:
    environment = os.environ.copy()
    environment[TOKEN_ENVIRONMENT_VARIABLE] = SELF_TEST_SENTINEL
    completed = subprocess.run(
        [sys.executable, "-m", "tools.pr07_onedrive_personal_if_match_probe", "--candidate", CANDIDATE, "--self-test"],
        cwd=BACKEND_DIRECTORY,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == SELF_TEST_REPORT


@pytest.mark.parametrize("location", ["http://download.test/content", "https://user:pass@download.test/content"])
def test_download_rejects_unsafe_redirect(location: str) -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(302, headers={"Location": location})

    probe = OneDrivePersonalIfMatchProbe(
        access_token="secret-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProbeFailure, match="unsafe provider URL"):
        probe._download(drive_id=DRIVE_ID, item_id=ITEM_ID)


def test_download_rejects_oversized_stream() -> None:
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, content=b"x" * (MAX_DOWNLOAD_BYTES + 1))

    probe = OneDrivePersonalIfMatchProbe(
        access_token="secret-token",
        client=httpx.Client(transport=httpx.MockTransport(handler)),
    )
    with pytest.raises(ProbeFailure, match="exceeded the probe bound"):
        probe._download(drive_id=DRIVE_ID, item_id=ITEM_ID)


@pytest.mark.skipif(NODE_EXECUTABLE is None, reason="Node.js is required")
def test_node_launcher_actual_self_test_preserves_exact_report() -> None:
    environment = os.environ.copy()
    environment[TOKEN_ENVIRONMENT_VARIABLE] = SELF_TEST_SENTINEL
    completed = subprocess.run(
        [NODE_EXECUTABLE, str(LAUNCHER_PATH), "--python-executable", str(Path(sys.executable).resolve()), "--candidate", CANDIDATE, "--self-test"],
        cwd=BACKEND_DIRECTORY.parent,
        env=environment,
        check=False,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert completed.returncode == 0
    assert completed.stderr == ""
    assert json.loads(completed.stdout) == SELF_TEST_REPORT
    assert SELF_TEST_SENTINEL not in completed.stdout


@pytest.mark.skipif(NODE_EXECUTABLE is None, reason="Node.js is required")
def test_node_validator_rejects_unknown_key_candidate_mismatch_and_false_safe_fail(tmp_path: Path) -> None:
    report, _ = _run(C2GraphScenario())
    valid = probe_module.asdict(report)
    invalid = {**valid, "unknown": True}
    false_safe_fail = {**valid, "status": "FAIL"}
    nested_unknown = json.loads(json.dumps(valid))
    nested_unknown["partial_observations"]["fresh"]["raw_range"] = "327680-"
    boolean_partial_status = json.loads(json.dumps(valid))
    boolean_partial_status["partial_observations"]["fresh"]["http_status"] = True
    unknown_range_class = json.loads(json.dumps(valid))
    unknown_range_class["partial_observations"]["fresh"]["range_class"] = "RAW_RANGE"
    naive_checked_at_reports = [
        {**valid, "checked_at": value}
        for value in NAIVE_CHECKED_AT_VALUES
    ]
    assert not probe_module._valid_diagnostic_report(false_safe_fail, 1)
    assert all(
        not probe_module._valid_diagnostic_report(candidate, 0)
        for candidate in naive_checked_at_reports
    )
    script = tmp_path / "validate.mjs"
    script.write_text(
        "import {validateReport} from " + json.dumps(LAUNCHER_PATH.as_uri()) + ";\n"
        + "const reports=JSON.parse(process.argv[2]);\n"
        + f"console.log(JSON.stringify(reports.map(r=>validateReport(r,false,'','{CANDIDATE}'))));\n",
        encoding="utf-8",
    )
    completed = subprocess.run(
        [
            NODE_EXECUTABLE,
            str(script),
            json.dumps(
                [
                    valid,
                    invalid,
                        {**valid, "candidate": "C1"},
                        false_safe_fail,
                        nested_unknown,
                        boolean_partial_status,
                        unknown_range_class,
                        *naive_checked_at_reports,
                ]
            ),
        ],
        check=True,
        capture_output=True,
        text=True,
        timeout=30,
    )
    assert json.loads(completed.stdout) == [
        True,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
        False,
    ]
