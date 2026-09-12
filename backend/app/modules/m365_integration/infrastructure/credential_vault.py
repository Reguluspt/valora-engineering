"""AES-GCM credential vault backed by an infrastructure-only ciphertext table."""
from __future__ import annotations

import base64
import json
import os
import uuid
from collections.abc import Mapping

from cryptography.exceptions import InvalidTag
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from sqlalchemy.orm import Session

from app.modules.m365_integration.models import M365EncryptedCredential


class CredentialVaultError(RuntimeError):
    """Fail-closed vault error without secret-bearing detail."""


def parse_keyring(raw_json: str, active_key_version: str) -> tuple[dict[str, bytes], str]:
    """Parse a deployment keyring containing base64-encoded 256-bit AES keys."""
    if not raw_json or not active_key_version:
        raise CredentialVaultError("M365 credential vault is not configured.")
    try:
        encoded = json.loads(raw_json)
    except (TypeError, json.JSONDecodeError) as exc:
        raise CredentialVaultError("M365 credential vault configuration is invalid.") from exc
    if not isinstance(encoded, dict) or active_key_version not in encoded:
        raise CredentialVaultError("M365 credential vault active key is unavailable.")

    keys: dict[str, bytes] = {}
    try:
        for version, value in encoded.items():
            if not isinstance(version, str) or not version.strip() or not isinstance(value, str):
                raise ValueError
            key = base64.urlsafe_b64decode(value.encode("ascii"))
            if len(key) != 32:
                raise ValueError
            keys[version] = key
    except (ValueError, UnicodeEncodeError) as exc:
        raise CredentialVaultError("M365 credential vault keyring is invalid.") from exc
    return keys, active_key_version


class DatabaseCredentialVault:
    """Stores only AES-GCM ciphertext and rotates envelopes inside the caller transaction."""

    def __init__(
        self,
        db: Session,
        *,
        keys: Mapping[str, bytes],
        active_key_version: str,
    ) -> None:
        if active_key_version not in keys:
            raise CredentialVaultError("M365 credential vault active key is unavailable.")
        if any(len(key) != 32 for key in keys.values()):
            raise CredentialVaultError("M365 credential vault keys must be 256-bit.")
        self._db = db
        self._keys = dict(keys)
        self._active_key_version = active_key_version

    @staticmethod
    def _associated_data(
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> bytes:
        return f"{organization_id}:{user_id}:{credential_id}:{purpose}".encode("ascii")

    def _encrypt(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
        plaintext: bytes,
    ) -> tuple[bytes, bytes]:
        nonce = os.urandom(12)
        aad = self._associated_data(organization_id, user_id, credential_id, purpose)
        ciphertext = AESGCM(self._keys[self._active_key_version]).encrypt(
            nonce, plaintext, aad
        )
        return nonce, ciphertext

    def _owned_record(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> M365EncryptedCredential:
        record = (
            self._db.query(M365EncryptedCredential)
            .filter(
                M365EncryptedCredential.id == credential_id,
                M365EncryptedCredential.organization_id == organization_id,
                M365EncryptedCredential.user_id == user_id,
                M365EncryptedCredential.purpose == purpose,
            )
            .first()
        )
        if record is None:
            raise CredentialVaultError("M365 credential is unavailable.")
        return record

    def store(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        purpose: str,
        plaintext: bytes,
    ) -> uuid.UUID:
        credential_id = uuid.uuid4()
        nonce, ciphertext = self._encrypt(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=credential_id,
            purpose=purpose,
            plaintext=plaintext,
        )
        self._db.add(
            M365EncryptedCredential(
                id=credential_id,
                organization_id=organization_id,
                user_id=user_id,
                purpose=purpose,
                key_version=self._active_key_version,
                nonce=nonce,
                ciphertext=ciphertext,
            )
        )
        self._db.flush()
        return credential_id

    def load(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> bytes:
        record = self._owned_record(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=credential_id,
            purpose=purpose,
        )
        key = self._keys.get(record.key_version)
        if key is None:
            raise CredentialVaultError("M365 credential key version is unavailable.")
        aad = self._associated_data(organization_id, user_id, credential_id, purpose)
        try:
            plaintext = AESGCM(key).decrypt(record.nonce, record.ciphertext, aad)
        except (InvalidTag, ValueError) as exc:
            raise CredentialVaultError("M365 credential integrity check failed.") from exc

        if record.key_version != self._active_key_version:
            nonce, ciphertext = self._encrypt(
                organization_id=organization_id,
                user_id=user_id,
                credential_id=credential_id,
                purpose=purpose,
                plaintext=plaintext,
            )
            record.key_version = self._active_key_version
            record.nonce = nonce
            record.ciphertext = ciphertext
            self._db.flush()
        return plaintext

    def replace(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
        plaintext: bytes,
    ) -> None:
        record = self._owned_record(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=credential_id,
            purpose=purpose,
        )
        nonce, ciphertext = self._encrypt(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=credential_id,
            purpose=purpose,
            plaintext=plaintext,
        )
        record.key_version = self._active_key_version
        record.nonce = nonce
        record.ciphertext = ciphertext
        self._db.flush()

    def delete(
        self,
        *,
        organization_id: uuid.UUID,
        user_id: uuid.UUID,
        credential_id: uuid.UUID,
        purpose: str,
    ) -> None:
        record = self._owned_record(
            organization_id=organization_id,
            user_id=user_id,
            credential_id=credential_id,
            purpose=purpose,
        )
        self._db.delete(record)
        self._db.flush()
