"""No-network safety tests for the one-shot VALORA S3 live harness."""
from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace
from typing import Any

import boto3
import pytest
from botocore.client import Config
from botocore.exceptions import ClientError, ReadTimeoutError

import tools.valora_storage_s3_live_harness as harness


KMS_ARN = "arn:aws:kms:ap-southeast-1:111122223333:key/12345678-1234-1234-1234-123456789012"
SESSION_ARN = "arn:aws:sts::111122223333:assumed-role/valora-s3-g5-harness/g5-run-001"


def _manifest() -> dict[str, Any]:
    return {
        "schema_version": harness.SCHEMA_VERSION,
        "run_id": harness.RUN_ID,
        "account_ref": harness.ACCOUNT_REF,
        "region": harness.REGION,
        "bucket": harness.BUCKET,
        "prefix": harness.PREFIX,
        "approved_executable_commit": "a" * 40,
        "approved_review_manifest_sha256": "b" * 64,
        "approval_reference": "PO-G5-APPROVAL-001",
        "expected_account_id": "111122223333",
        "expected_principal_arn": SESSION_ARN,
        "kms_key_arn": KMS_ARN,
        "bucket_policy_sha256": "c" * 64,
        "iam_policy_sha256": "d" * 64,
        "lifecycle_configuration_sha256": "e" * 64,
        "action_time_checklist_sha256": "f" * 64,
        "cleanup_owner": "G5-OPERATOR-01",
        "runtime": {
            "python": "3.14.7",
            "boto3": harness.RUNTIME_BOTO3,
            "botocore": harness.RUNTIME_BOTOCORE,
        },
        "retry": {"signature_version": "s3v4", "total_max_attempts": 1},
        "fixtures": harness.fixture_manifest(),
        "limits": harness.frozen_limits(),
    }


class _Journal:
    def __init__(self) -> None:
        self.entries: list[tuple[str, dict[str, Any]]] = []

    def record(self, event: str, **fields: Any) -> None:
        self.entries.append((event, fields))


class _Raw:
    def __init__(self) -> None:
        self.closed = False

    def close(self) -> None:
        self.closed = True


class _Response:
    def __init__(self) -> None:
        self.headers = {"x-amz-request-id": "safe-request-1"}
        self.status_code = 200
        self.raw = _Raw()


class _Session:
    def __init__(self) -> None:
        self.requests = 0
        self.response = _Response()

    def send(self, request: Any) -> _Response:
        del request
        self.requests += 1
        return self.response


class _Events:
    def __init__(self) -> None:
        self.handler = None
        self.event_name = None

    def register_first(self, event_name: str, handler: Any, *, unique_id: str) -> None:
        assert unique_id
        self.event_name = event_name
        self.handler = handler

    def unregister(self, event_name: str, *, unique_id: str) -> None:
        assert event_name == self.event_name
        assert unique_id
        self.handler = None


def test_fixture_manifest_is_deterministic_and_has_exact_multipart_layout() -> None:
    first = harness.fixture_manifest()
    second = harness.fixture_manifest()
    assert first == second
    assert first["FIXTURE_A"]["byte_length"] == 4096
    assert first["FIXTURE_B"]["sha256"] != first["FIXTURE_A"]["sha256"]
    assert first["FIXTURE_M"]["byte_length"] == 8 * 1024 * 1024 + 4096
    assert first["FIXTURE_M"]["expected_parts"] == 2
    assert all(len(item["sha256"]) == 64 for item in first.values())


def test_object_lock_guard_accepts_only_explicit_not_configured_error() -> None:
    def not_configured(**kwargs: Any) -> None:
        assert kwargs == {"Bucket": harness.BUCKET}
        raise ClientError(
            {"Error": {"Code": "ObjectLockConfigurationNotFoundError", "Message": "absent"}},
            "GetObjectLockConfiguration",
        )

    harness._assert_object_lock_absent(
        SimpleNamespace(get_object_lock_configuration=not_configured)
    )


def test_object_lock_guard_rejects_enabled_configuration() -> None:
    client = SimpleNamespace(
        get_object_lock_configuration=lambda **kwargs: {
            "ObjectLockConfiguration": {"ObjectLockEnabled": "Enabled"},
            "ResponseMetadata": {},
        }
    )
    with pytest.raises(harness.HarnessFailure, match="must not have Object Lock"):
        harness._assert_object_lock_absent(client)


def test_runtime_manifest_accepts_only_the_frozen_exact_shape(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(_manifest()), encoding="utf-8")
    loaded = harness.RuntimeManifest.load(path)
    assert loaded.expected_account_id == "111122223333"
    assert loaded.expected_principal_arn == SESSION_ARN
    assert loaded.kms_key_arn == KMS_ARN


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("region", "us-east-1"),
        ("expected_account_id", "REPLACE_AT_G5"),
        (
            "expected_principal_arn",
            "arn:aws:sts::999900001111:assumed-role/valora-s3-g5-harness/wrong-account",
        ),
        ("kms_key_arn", "arn:aws:kms:us-east-1:111122223333:key/wrong-region"),
        ("approved_executable_commit", "latest"),
    ],
)
def test_runtime_manifest_rejects_drift_and_placeholders(
    tmp_path: Path,
    field: str,
    value: str,
) -> None:
    manifest = _manifest()
    manifest[field] = value
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(harness.HarnessFailure):
        harness.RuntimeManifest.load(path)


def test_lost_response_transport_suppresses_only_after_one_completed_dispatch() -> None:
    journal = _Journal()
    session = _Session()
    events = _Events()
    client = SimpleNamespace(
        _endpoint=SimpleNamespace(http_session=session),
        meta=SimpleNamespace(events=events),
    )
    request = SimpleNamespace(url="https://s3.ap-southeast-1.amazonaws.com/example")
    with harness._lose_exactly_one_response(client, "PutObject", journal) as fault:
        assert events.handler is not None
        events.handler(request)
        with pytest.raises(ReadTimeoutError):
            client._endpoint.http_session.send(request)
        with pytest.raises(harness.HarnessFailure, match="second PutObject"):
            events.handler(request)
    assert session.requests == 1
    assert fault.dispatch_count == 1
    assert fault.response_received is True
    assert session.response.raw.closed is True
    assert journal.entries == [
        ("FAULT_FINAL_WRITE_DISPATCH", {"operation": "PutObject", "dispatch_count": 1}),
        (
            "FAULT_RESPONSE_SUPPRESSED_AFTER_DISPATCH",
            {
                "operation": "PutObject",
                "dispatch_count": 1,
                "safe_request_id": "safe-request-1",
                "http_status": 200,
            },
        ),
    ]


def test_lost_response_seam_matches_frozen_botocore_event_and_transport() -> None:
    client = boto3.client(
        "s3",
        region_name=harness.REGION,
        endpoint_url="https://s3.invalid",
        aws_access_key_id="synthetic-access-key",
        aws_secret_access_key="synthetic-secret-key",
        aws_session_token="synthetic-session-token",
        config=Config(signature_version="s3v4", retries={"total_max_attempts": 1}),
    )
    session = _Session()
    client._endpoint.http_session = session
    journal = _Journal()
    with harness._lose_exactly_one_response(client, "PutObject", journal) as fault:
        with pytest.raises(ReadTimeoutError):
            client.put_object(
                Bucket=harness.BUCKET,
                Key=harness.PREFIX + "transport-seam.bin",
                Body=b"x",
                ContentLength=1,
                IfNoneMatch="*",
            )
    assert session.requests == 1
    assert fault.dispatch_count == 1
    assert fault.response_received is True


@pytest.mark.parametrize("field", ["approval_reference", "cleanup_owner"])
def test_runtime_manifest_rejects_placeholder_operational_references(
    tmp_path: Path,
    field: str,
) -> None:
    manifest = _manifest()
    manifest[field] = "REPLACE_AT_G5"
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(manifest), encoding="utf-8")
    with pytest.raises(harness.HarnessFailure):
        harness.RuntimeManifest.load(path)


def test_full_preflight_accepts_exact_assumed_role_and_frozen_boundary(tmp_path: Path) -> None:
    lifecycle = {"Rules": [{"ID": "abort-incomplete", "Status": "Enabled"}]}
    bucket_policy = {"Version": "2012-10-17", "Statement": []}
    raw = _manifest()
    raw["lifecycle_configuration_sha256"] = harness._sha256_json(lifecycle)
    raw["bucket_policy_sha256"] = harness._sha256_json(bucket_policy)
    path = tmp_path / "manifest.json"
    path.write_text(json.dumps(raw), encoding="utf-8")
    manifest = harness.RuntimeManifest.load(path)

    def object_lock_absent(**kwargs: Any) -> None:
        assert kwargs == {"Bucket": harness.BUCKET}
        raise ClientError(
            {"Error": {"Code": "ObjectLockConfigurationNotFoundError", "Message": "absent"}},
            "GetObjectLockConfiguration",
        )

    sts = SimpleNamespace(
        get_caller_identity=lambda: {
            "Account": "111122223333",
            "Arn": SESSION_ARN,
            "UserId": "AROATEST:g5-run-001",
        }
    )
    s3 = SimpleNamespace(
        get_bucket_location=lambda **kwargs: {"LocationConstraint": harness.REGION},
        get_public_access_block=lambda **kwargs: {
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "IgnorePublicAcls": True,
                "BlockPublicPolicy": True,
                "RestrictPublicBuckets": True,
            }
        },
        get_bucket_ownership_controls=lambda **kwargs: {
            "OwnershipControls": {"Rules": [{"ObjectOwnership": "BucketOwnerEnforced"}]}
        },
        get_bucket_versioning=lambda **kwargs: {},
        get_object_lock_configuration=object_lock_absent,
        get_bucket_encryption=lambda **kwargs: {
            "ServerSideEncryptionConfiguration": {
                "Rules": [
                    {
                        "ApplyServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "aws:kms",
                            "KMSMasterKeyID": KMS_ARN,
                        },
                        "BucketKeyEnabled": True,
                    }
                ]
            }
        },
        get_bucket_lifecycle_configuration=lambda **kwargs: dict(lifecycle),
        get_bucket_policy=lambda **kwargs: {"Policy": json.dumps(bucket_policy)},
        list_objects_v2=lambda **kwargs: {},
        list_multipart_uploads=lambda **kwargs: {},
    )
    journal = _Journal()
    harness._assert_preflight(sts, s3, manifest, journal)
    assert [event for event, _ in journal.entries] == [
        "ACCOUNT_GUARD_PASS",
        "AWS_BOUNDARY_GUARDS_PASS",
    ]


def test_evidence_journal_is_exclusive_and_rejects_repository_paths(tmp_path: Path) -> None:
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    with pytest.raises(harness.HarnessFailure, match="outside"):
        harness.EvidenceJournal(repository_root / "evidence", repository_root=repository_root)
    evidence_dir = tmp_path / "private-evidence"
    first = harness.EvidenceJournal(evidence_dir, repository_root=repository_root)
    first.record("RUN_STARTED", run_id=harness.RUN_ID)
    first.close()
    with pytest.raises(harness.HarnessFailure, match="second invocation"):
        harness.EvidenceJournal(evidence_dir, repository_root=repository_root)


def test_evidence_journal_rejects_secret_shaped_fields(tmp_path: Path) -> None:
    repository_root = tmp_path / "repo"
    repository_root.mkdir()
    journal = harness.EvidenceJournal(tmp_path / "evidence", repository_root=repository_root)
    try:
        with pytest.raises(harness.HarnessFailure, match="forbidden"):
            journal.record("BAD", authorization="not-allowed")
    finally:
        journal.close()


def test_self_test_validates_template_without_constructing_aws_clients(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    path = tmp_path / "template.json"
    template = _manifest()
    template["expected_account_id"] = "REPLACE_AT_G5"
    template["expected_principal_arn"] = "REPLACE_AT_G5"
    template["kms_key_arn"] = "REPLACE_AT_G5"
    path.write_text(json.dumps(template), encoding="utf-8")
    monkeypatch.setattr(
        harness,
        "_make_clients",
        lambda credentials: (_ for _ in ()).throw(AssertionError(credentials)),
    )
    assert harness.main(["--manifest", str(path), "--self-test"]) == 0
    assert json.loads(capsys.readouterr().out) == {"network": "NOT_ATTEMPTED", "self_test": "PASS"}


def test_live_mode_requires_external_evidence_directory() -> None:
    with pytest.raises(SystemExit):
        harness.parse_args(["--manifest", "manifest.json", "--execute-live"])


def test_live_preflight_failure_does_not_attempt_cleanup(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    manifest_path = tmp_path / "manifest.json"
    manifest_path.write_text(json.dumps(_manifest()), encoding="utf-8")
    cleanup_calls = 0

    monkeypatch.setattr(harness, "_require_runtime", lambda: None)
    monkeypatch.setattr(harness, "_require_clean_tracked_tree", lambda repository_root: None)
    monkeypatch.setattr(harness, "_git_head", lambda repository_root: "a" * 40)
    monkeypatch.setattr(harness, "_require_explicit_temporary_credentials", lambda: {})
    monkeypatch.setattr(harness, "_make_clients", lambda credentials: (object(), object()))
    monkeypatch.setattr(harness, "_run_regressions", lambda *args: None)
    monkeypatch.setattr(
        harness,
        "_assert_preflight",
        lambda *args: (_ for _ in ()).throw(harness.HarnessFailure("preflight drift")),
    )

    def track_cleanup(*args: Any) -> None:
        nonlocal cleanup_calls
        cleanup_calls += 1

    monkeypatch.setattr(harness, "_cleanup_prefix", track_cleanup)
    with pytest.raises(harness.HarnessFailure, match="preflight drift"):
        harness._run_live(manifest_path, tmp_path / "evidence")
    assert cleanup_calls == 0
