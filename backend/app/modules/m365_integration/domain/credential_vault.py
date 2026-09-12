"""Credential-vault port for recoverable third-party OAuth material."""
from __future__ import annotations

import uuid
from typing import Protocol


class M365CredentialVault(Protocol):
    def store(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purpose: str,
        plaintext: bytes,
    ) -> uuid.UUID: ...

    def load(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> bytes: ...

    def replace(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
        plaintext: bytes,
    ) -> None: ...

    def delete(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> None: ...
