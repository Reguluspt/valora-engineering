from __future__ import annotations

import hashlib
import json

import httpx
import pytest

from tools.pr07_onedrive_personal_if_match_probe import (
    OneDrivePersonalIfMatchProbe,
    ProbeFailure,
    main,
)


DRIVE_ID = "drive-personal"
ITEM_ID = "item-probe"
ITEM_NAME = "VALORA-PR07-IF-MATCH-test.bin"


def _metadata(e_tag: str) -> dict:
    return {
        "id": ITEM_ID,
        "name": ITEM_NAME,
        "eTag": e_tag,
    }


class GraphScenario:
    def __init__(self, *, stale_status: int = 412) -> None:
        self.content = b""
        self.e_tag = '"etag-1"'
        self.session_number = 0
        self.sessions: dict[str, bytes] = {}
        self.session_etags: dict[str, str] = {}
        self.stale_status = stale_status
        self.deleted = False
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
                return httpx.Response(202, json={"nextExpectedRanges": []})
            if request.method == "DELETE":
                self.sessions.pop(session_id, None)
                return httpx.Response(204)
        if request.url.host == "download.test":
            self.authorization_seen_on_download_url |= authorization is not None
            return httpx.Response(200, content=self.content)

        assert authorization == "Bearer secret-token"
        if request.method == "GET" and path.endswith("/me/drive"):
            return httpx.Response(200, json={"id": DRIVE_ID, "driveType": "personal"})
        if request.method == "PUT" and path.endswith(":/content"):
            self.content = request.content
            return httpx.Response(201, json=_metadata(self.e_tag))
        if request.method == "POST" and path.endswith("/createUploadSession"):
            body = json.loads(request.content)
            assert request.headers["if-match"] == self.e_tag
            assert body["deferCommit"] is True
            assert body["item"]["@microsoft.graph.conflictBehavior"] == "fail"
            assert body["item"]["fileSize"] == 320 * 1024
            self.session_number += 1
            session_id = str(self.session_number)
            self.session_etags[session_id] = request.headers["if-match"]
            return httpx.Response(200, json={"uploadUrl": f"https://upload.test/{session_id}"})
        if request.method == "PUT" and path.endswith(f"/{ITEM_ID}"):
            body = json.loads(request.content)
            session_id = body["@microsoft.graph.sourceUrl"].rsplit("/", 1)[-1]
            assert request.headers["if-match"] == self.session_etags[session_id]
            assert body["@microsoft.graph.conflictBehavior"] == "fail"
            assert "name" not in body
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


def test_probe_fails_closed_when_stale_commit_is_not_412_and_still_cleans_up() -> None:
    scenario = GraphScenario(stale_status=200)
    client = httpx.Client(transport=httpx.MockTransport(scenario))
    probe = OneDrivePersonalIfMatchProbe(access_token="secret-token", client=client)

    with pytest.raises(ProbeFailure, match="was not rejected with HTTP 412"):
        probe.run()

    assert scenario.deleted is True
    assert scenario.authorization_seen_on_upload_url is False
    assert scenario.authorization_seen_on_download_url is False


def test_command_refuses_network_without_both_explicit_write_flags(monkeypatch) -> None:
    monkeypatch.setenv("VALORA_PR07_GRAPH_ACCESS_TOKEN", "secret-token")

    with pytest.raises(ProbeFailure, match="Both --allow-live-write"):
        main([])
    with pytest.raises(ProbeFailure, match="Both --allow-live-write"):
        main(["--allow-live-write"])


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
