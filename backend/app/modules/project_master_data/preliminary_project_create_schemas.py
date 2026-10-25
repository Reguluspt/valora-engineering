"""Frozen preliminary-create-v1 wire validation and canonical payload."""

import hashlib
import json
import re
import unicodedata
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, StrictStr, field_validator

VERSION = "preliminary-create-v1"
UUID4_PATTERN = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\Z")
TRIM = (
    "\u0009\u000a\u000b\u000c\u000d\u0020\u0085\u00a0\u1680"
    + "".join(chr(n) for n in range(0x2000, 0x200B))
    + "\u2028\u2029\u202f\u205f\u3000"
)


def request_uuid(value: str) -> UUID:
    if not isinstance(value, str) or not UUID4_PATTERN.fullmatch(value):
        raise ValueError("Expected canonical RFC 4122 UUIDv4")
    return UUID(value)


def normalize(value: str, *, description: bool = False) -> str | None:
    if len(value) > (16384 if description else 4096):
        raise ValueError("Raw scalar limit exceeded")
    if any(0xD800 <= ord(c) <= 0xDFFF for c in value):
        raise ValueError("Invalid Unicode scalar")
    if description:
        value = value.replace("\r\n", "\n").replace("\r", "\n")
    value = unicodedata.normalize("NFC", value).strip(TRIM)
    if len(value) > (4000 if description else 255) or (not description and not value):
        raise ValueError("Normalized scalar limit exceeded")
    for c in value:
        n = ord(c)
        if (n < 32 or 127 <= n <= 159) and not (description and c in "\t\n"):
            raise ValueError("Control character is not allowed")
        if not description and n in (0x2028, 0x2029):
            raise ValueError("Line separator is not allowed")
    return value or None


class CreatePreliminaryRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    request_id: StrictStr
    name: StrictStr
    description: StrictStr | None = None

    @field_validator("request_id")
    @classmethod
    def valid_id(cls, value: str) -> str:
        request_uuid(value)
        return value

    @field_validator("name")
    @classmethod
    def valid_name(cls, value: str) -> str:
        return normalize(value)

    @field_validator("description")
    @classmethod
    def valid_description(cls, value: str | None) -> str | None:
        return None if value is None else normalize(value, description=True)

    def canonical_bytes(self) -> bytes:
        return json.dumps(
            {"description": self.description, "name": self.name},
            ensure_ascii=True,
            sort_keys=True,
            separators=(",", ":"),
            allow_nan=False,
        ).encode("ascii")


def digest(payload: bytes, version: str = VERSION) -> str:
    return hashlib.sha256(version.encode("ascii") + b"\0" + payload).hexdigest()


class ProjectIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    code: str


class ReceiptIdentity(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    canonical_version: Literal["preliminary-create-v1"]
    recorded_at: str


class PreliminaryCreateResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")
    status: Literal["COMMITTED"]
    request_id: str
    project: ProjectIdentity
    receipt: ReceiptIdentity
