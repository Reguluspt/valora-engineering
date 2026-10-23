import json
import uuid

import pytest
from pydantic import ValidationError

from app.modules.project_master_data.preliminary_project_create_schemas import (
    CreatePreliminaryRequest,
    TRIM,
    VERSION,
    digest,
)


def command(**changes):
    return CreatePreliminaryRequest.model_validate(
        {"request_id": str(uuid.uuid4()), "name": "Máy móc", **changes}
    )


@pytest.mark.parametrize(
    "changes",
    [
        {"name": None},
        {"name": 1},
        {"name": True},
        {"name": []},
        {"description": 1},
        {"code": "X"},
        {"organization_id": str(uuid.uuid4())},
        {"actor_user_id": str(uuid.uuid4())},
        {"customer_id": None},
        {"project_id": str(uuid.uuid4())},
        {"request_id": str(uuid.uuid1())},
        {"request_id": "AAAAAAAA-AAAA-4AAA-8AAA-AAAAAAAAAAAA"},
        {"request_id": uuid.uuid4().hex},
        {"name": "\ud800"},
        {"description": "\udfff"},
        {"name": "a\x00b"},
        {"name": "a\nb"},
        {"description": "a\x7fb"},
        {"name": "a\u2028b"},
        {"name": TRIM},
        {"name": "a" * 256},
        {"description": "a" * 4001},
        {"name": " " * 4097},
        {"description": " " * 16385},
    ],
)
def test_a02_strict_input(changes):
    with pytest.raises(ValidationError):
        command(**changes)


def test_a03_canonical_vectors_and_scalar_limits():
    a = command(name=TRIM + "e\u0302\u0301 😀" + TRIM, description="\r\n A\rB\r\n")
    assert a.name == "ế 😀"
    assert a.description == "A\nB"
    assert a.canonical_bytes() == b'{"description":"A\\nB","name":"\\u1ebf \\ud83d\\ude00"}'
    assert (
        digest(a.canonical_bytes())
        == __import__("hashlib").sha256(VERSION.encode() + b"\0" + a.canonical_bytes()).hexdigest()
    )
    assert len(command(name="😀" * 255, description="😀" * 4000).canonical_bytes()) < 60000
    for value in (None, "", TRIM):
        assert command(description=value).canonical_bytes() == command().canonical_bytes()
    assert json.loads(a.canonical_bytes()) == {"description": a.description, "name": a.name}


@pytest.mark.parametrize("name", ["A B", "A  B", "a B", "Á B", "A\u200bB", "Ａ B"])
def test_a03_distinct_payloads_preserved(name):
    assert command(name=name).name == name


def test_a03_invalid_top_level_and_uuid_nonce():
    for value in ([], None, "text", 1):
        with pytest.raises(ValidationError):
            CreatePreliminaryRequest.model_validate(value)
