"""Input and calendar boundary proofs independent of a storage provider."""
import hashlib
import json
import uuid
from datetime import datetime, timezone

import pytest
from fastapi import HTTPException
from pydantic import ValidationError

from app.modules.document_workspace.quotation_document_import_schemas import ImportCommand, validate_original
from app.modules.document_workspace.application.quotation_document_import_service import ten_year_floor


@pytest.mark.parametrize("content", ["Báo giá tổng hợp\n".encode(), b"\xef\xbb\xbfline\r\n", b"a" * 1048576], ids=["vietnamese", "bom-crlf", "one-mib"])
def test_original_bytes_preserve_bom_newlines_and_limit(content):
    original = validate_original("Quotation.TXT", "text/plain; charset=UTF-8", content)
    assert original.content == content
    assert original.sha256 == hashlib.sha256(content).hexdigest()


@pytest.mark.parametrize("content", [b"", b"a" * 1048577, b"\xff\xfea\0", b"\x00a", b"a\x01", b"a\x7f", b"a\xc2\x85", b"PK\x03\x04payload", b"%PDF-1.7", b"\xf0\x28\x8c\x28"], ids=["empty", "oversize", "utf16", "nul", "c0", "del", "c1", "zip", "pdf", "invalid-utf8"])
def test_invalid_original_fails_without_echo(content):
    with pytest.raises(HTTPException) as error:
        validate_original("example.txt", None, content)
    assert "example.txt" not in str(error.value.detail)
    assert set(error.value.detail) == {"error_code", "detail"}


@pytest.mark.parametrize("name", ["../a.txt", "a\\b.txt", "C:a.txt", "CON.txt", "lpt1.TXT", "x\u202etxt.txt", "a.txt ", "a.pdf", "a\x00.txt", "a" * 256 + ".txt"], ids=["traversal", "backslash", "drive", "device", "lpt", "bidi", "trailing-space", "extension", "nul", "length"])
def test_unsafe_filename(name):
    with pytest.raises(HTTPException):
        validate_original(name, None, b"safe")


@pytest.mark.parametrize("media", ["text/html", "application/pdf", "text/plain; charset=utf-16", "text/plain; unexpected=true"])
def test_unsupported_media(media):
    with pytest.raises(HTTPException):
        validate_original("a.txt", media, b"safe")


def test_calendar_utc_precision_and_february_clamp():
    t = datetime(2028, 2, 29, 12, 34, 56, 123456, tzinfo=timezone.utc)
    assert ten_year_floor(t) == datetime(2038, 2, 28, 12, 34, 56, 123456, tzinfo=timezone.utc)
    assert (ten_year_floor(t) - t).days != 3650
    local_midnight = datetime.fromisoformat("2030-01-01T00:30:00.123456+14:00")
    assert ten_year_floor(local_midnight) == datetime.fromisoformat("2039-12-31T10:30:00.123456+00:00")


def test_unknown_identity_policy_and_unconfirmed_fields_are_rejected():
    command = dict(contract_version="quotation-txt-import-v1", command_id=str(uuid.uuid4()), confirm=True,
        expected_case_version="a" * 64, expected_project_row_version=1, expected_sha256="b" * 64, expected_byte_length=1)
    assert ImportCommand.model_validate_json(json.dumps(command)).confirm is True
    for field in ("actor", "organization_id", "project_id", "provider", "policy", "retention_anchor_at", "document_id"):
        with pytest.raises(ValidationError):
            ImportCommand.model_validate_json(json.dumps({**command, field: "injected"}))
    for confirmation in (False, 1, 0, "true", None):
        with pytest.raises(ValidationError):
            ImportCommand.model_validate_json(json.dumps({**command, "confirm": confirmation}))
