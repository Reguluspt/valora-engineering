"""Strict public command and original-byte validation for human TXT custody."""
from __future__ import annotations

import hashlib
import re
import unicodedata
import uuid
from dataclasses import dataclass
from typing import Literal

from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field, field_validator

CONTRACT = "quotation-txt-import-v1"
MAX_BYTES = 1_048_576
MAX_BODY_BYTES = 1_114_112
MEDIA_TYPE = "text/plain; charset=utf-8"


class ImportCommand(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    contract_version: Literal["quotation-txt-import-v1"]
    command_id: uuid.UUID
    confirm: Literal[True]
    expected_case_version: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_project_row_version: int = Field(gt=0)
    expected_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")
    expected_byte_length: int = Field(ge=1, le=MAX_BYTES)

    @field_validator("confirm", mode="before")
    @classmethod
    def explicit_confirmation(cls, value):
        if value is not True:
            raise ValueError("Explicit boolean confirmation is required")
        return value


class RecoverCommand(ImportCommand):
    expected_storage_state_version: int = Field(gt=0)


def reject(status: int, code: str) -> None:
    raise HTTPException(status, detail={"error_code": code, "detail": "Không thể nhập tài liệu TXT. Kiểm tra tệp, quyền và trạng thái hồ sơ."})


@dataclass(frozen=True)
class OriginalTxt:
    filename: str
    content: bytes
    sha256: str


def validate_original(filename: str | None, media_type: str | None, content: bytes) -> OriginalTxt:
    if not 1 <= len(content) <= MAX_BYTES:
        reject(413 if len(content) > MAX_BYTES else 422, "txt_size_invalid")
    name = unicodedata.normalize("NFC", filename or "")
    if (not name or len(name.encode("utf-8")) > 255 or name != name.strip()
            or name.endswith((".", " ")) or not name.lower().endswith(".txt")
            or any(c in name for c in '/\\:')
            or any(unicodedata.category(c).startswith("C") for c in name)
            or re.fullmatch(r"(?i)(con|prn|aux|nul|com[1-9¹²³]|lpt[1-9¹²³])(?:\..*)?", name)):
        reject(422, "txt_filename_invalid")
    parts = [p.strip().lower() for p in (media_type or "").split(";")]
    if parts[0] not in {"", "text/plain", "application/octet-stream"} or any(
        p not in {'charset=utf-8', 'charset="utf-8"'} for p in parts[1:]
    ):
        reject(415, "txt_media_invalid")
    if content.startswith((b"%PDF-", b"PK\x03\x04", b"PK\x05\x06", b"PK\x07\x08", b"\xd0\xcf\x11\xe0", b"\x1f\x8b", b"\x89PNG", b"GIF87a", b"GIF89a", b"Rar!\x1a\x07", b"7z\xbc\xaf")):
        reject(415, "txt_binary_content")
    try:
        decoded = content.decode("utf-8", errors="strict")
    except UnicodeDecodeError:
        reject(422, "txt_encoding_invalid")
    if any((ord(c) < 32 and c not in "\t\r\n") or 127 <= ord(c) <= 159 for c in decoded):
        reject(422, "txt_control_content")
    return OriginalTxt(name, content, hashlib.sha256(content).hexdigest())
