"""Prevent OAuth callback credentials from entering HTTP access logs."""
from __future__ import annotations

from collections.abc import Awaitable, Callable, MutableMapping
from typing import Any


ASGIApp = Callable[
    [MutableMapping[str, Any], Callable[..., Awaitable[Any]], Callable[..., Awaitable[Any]]],
    Awaitable[None],
]
ONEDRIVE_OAUTH_CALLBACK_PATH = "/api/v1/m365/onedrive/oauth/callback"
REDACTED_QUERY_STRING = b"redacted"


class OAuthCallbackAccessLogRedactionMiddleware:
    """Hide callback query values from the server while preserving them for the app."""

    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(
        self,
        scope: MutableMapping[str, Any],
        receive: Callable[..., Awaitable[Any]],
        send: Callable[..., Awaitable[Any]],
    ) -> None:
        if (
            scope.get("type") == "http"
            and scope.get("path") == ONEDRIVE_OAUTH_CALLBACK_PATH
            and scope.get("query_string")
        ):
            app_scope = dict(scope)
            scope["query_string"] = REDACTED_QUERY_STRING
            await self.app(app_scope, receive, send)
            return
        await self.app(scope, receive, send)
