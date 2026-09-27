"""MSAL delegated authorization adapter pinned to personal Microsoft accounts."""
from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Literal

import msal

from app.modules.m365_integration.domain.graph_gateway import (
    OAuthAccessToken,
    OAuthAuthorizationResult,
    OAuthAuthorizationStart,
)


CONSUMER_AUTHORITY = "https://login.microsoftonline.com/consumers"
CONSUMER_TENANT_ID = "9188040d-6c67-4c5b-b112-36a304b66dad"
CONSUMER_ISSUER = f"https://login.microsoftonline.com/{CONSUMER_TENANT_ID}/v2.0"
READ_ONLY_SCOPES = ["Files.Read"]
EXCHANGE_WRITE_SCOPES = ["Files.Read", "Files.ReadWrite.AppFolder"]


def _scopes_for_profile(
    scope_profile: Literal["read_only", "exchange_write"],
) -> list[str]:
    if scope_profile == "read_only":
        return READ_ONLY_SCOPES
    if scope_profile == "exchange_write":
        return EXCHANGE_WRITE_SCOPES
    raise MicrosoftOAuthError("Microsoft OAuth scope profile is invalid.")


class MicrosoftOAuthError(RuntimeError):
    """Sanitized delegated-authorization failure."""


class MicrosoftPersonalOAuthClient:
    def __init__(self, *, client_id: str, client_secret: str, redirect_uri: str) -> None:
        if not client_id or not client_secret or not redirect_uri:
            raise MicrosoftOAuthError("Microsoft OAuth is not configured.")
        self._client_id = client_id
        self._client_secret = client_secret
        self._redirect_uri = redirect_uri

    def _application(self, cache: msal.SerializableTokenCache) -> msal.ConfidentialClientApplication:
        return msal.ConfidentialClientApplication(
            self._client_id,
            authority=CONSUMER_AUTHORITY,
            client_credential=self._client_secret,
            token_cache=cache,
        )

    def begin(
        self, *, scope_profile: Literal["read_only", "exchange_write"] = "read_only"
    ) -> OAuthAuthorizationStart:
        cache = msal.SerializableTokenCache()
        flow = self._application(cache).initiate_auth_code_flow(
            scopes=_scopes_for_profile(scope_profile),
            redirect_uri=self._redirect_uri,
            prompt="select_account",
        )
        authorization_url = flow.get("auth_uri")
        state = flow.get("state")
        if not isinstance(authorization_url, str) or not isinstance(state, str):
            raise MicrosoftOAuthError("Microsoft OAuth authorization could not start.")
        material = json.dumps(
            {"flow": flow, "cache": cache.serialize()},
            ensure_ascii=True,
            separators=(",", ":"),
        ).encode("utf-8")
        return OAuthAuthorizationStart(
            authorization_url=authorization_url,
            state=state,
            flow_material=material,
        )

    def complete(
        self, *, flow_material: bytes, auth_response: Mapping[str, str]
    ) -> OAuthAuthorizationResult:
        try:
            material = json.loads(flow_material.decode("utf-8"))
            flow = material["flow"]
            cache = msal.SerializableTokenCache()
            if material.get("cache"):
                cache.deserialize(material["cache"])
            result = self._application(cache).acquire_token_by_auth_code_flow(
                flow,
                dict(auth_response),
            )
        except (KeyError, TypeError, ValueError, UnicodeDecodeError) as exc:
            raise MicrosoftOAuthError("Microsoft OAuth response is invalid.") from exc

        if "error" in result:
            raise MicrosoftOAuthError("Microsoft OAuth authorization was rejected.")
        claims = result.get("id_token_claims") or {}
        issuer = claims.get("iss")
        subject = claims.get("sub")
        audience = claims.get("aud")
        tenant_id = claims.get("tid")
        if (
            issuer != CONSUMER_ISSUER
            or tenant_id != CONSUMER_TENANT_ID
            or audience != self._client_id
            or not isinstance(subject, str)
            or not subject.strip()
        ):
            raise MicrosoftOAuthError("Microsoft OAuth account is not a personal account.")

        access_token = result.get("access_token")
        granted_scopes = frozenset(
            scope.strip().lower()
            for scope in str(result.get("scope", "")).split()
            if scope.strip()
        )
        if not isinstance(access_token, str) or "files.read" not in granted_scopes:
            raise MicrosoftOAuthError("Microsoft OAuth did not grant the required file scope.")
        if not cache.find(msal.TokenCache.CredentialType.REFRESH_TOKEN):
            raise MicrosoftOAuthError("Microsoft OAuth token cache is unavailable.")
        return OAuthAuthorizationResult(
            consumer_issuer=issuer,
            microsoft_account_subject=subject,
            access_token=access_token,
            token_cache=cache.serialize().encode("utf-8"),
            granted_scopes=granted_scopes,
        )

    def acquire_access_token(
        self,
        *,
        token_cache: bytes,
        scope_profile: Literal["read_only", "exchange_write"] = "read_only",
    ) -> OAuthAccessToken:
        cache = msal.SerializableTokenCache()
        try:
            cache.deserialize(token_cache.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise MicrosoftOAuthError("Microsoft OAuth token cache is invalid.") from exc
        app = self._application(cache)
        accounts = app.get_accounts()
        if len(accounts) != 1:
            raise MicrosoftOAuthError("Microsoft OAuth account cache is unavailable.")
        result = app.acquire_token_silent(
            _scopes_for_profile(scope_profile), account=accounts[0]
        )
        if not result or not isinstance(result.get("access_token"), str):
            raise MicrosoftOAuthError("Microsoft OAuth token refresh is required.")
        return OAuthAccessToken(
            access_token=result["access_token"],
            token_cache=cache.serialize().encode("utf-8"),
        )
