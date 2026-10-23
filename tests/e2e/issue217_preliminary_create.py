"""Issue217 synthetic browser fixture; never starts or modifies a protected runtime.

Run with VALORA_ENV=test and the explicit newly created issue217 database.
The frontend uses a separate Vite process with /api proxied to this fixture.
Fault controls live in this test harness only, bound to 127.0.0.1:8017.
"""

import argparse
import asyncio
import json
import os
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "backend"))


def verify_target():
    assert os.environ.get("VALORA_ENV") == "test"
    assert os.environ.get("POSTGRES_DB", "").startswith("valora_issue217_disposable")
    assert os.environ.get("POSTGRES_HOST") == "127.0.0.1"
    assert os.environ.get("POSTGRES_PORT") == "55417"


def seed(organization_slug="issue217-browser-synthetic"):
    assert organization_slug in (
        "issue217-browser-synthetic",
        "issue217-browser-other-synthetic",
    )
    from argon2 import PasswordHasher
    from app.db.session import SessionLocal
    from app.modules.project_master_data.models import (
        OrganizationProfile,
        Role,
        User,
        UserRole,
    )

    with SessionLocal() as db:
        org = (
            db.query(OrganizationProfile)
            .filter_by(organization_slug=organization_slug)
            .first()
        )
        if org:
            return
        org = OrganizationProfile(
            legal_name="Issue217 disposable browser fixture",
            organization_slug=organization_slug,
        )
        db.add(org)
        db.flush()
        for label, permissions in (
            ("owner", ["project:create", "project:read"]),
            ("viewer", ["project:read"]),
        ):
            role = Role(
                code=f"issue217-browser-{label}-{uuid.uuid4().hex}",
                display_name=label,
                permissions=permissions,
            )
            user = User(
                organization_id=org.id,
                email=f"{label}@issue217.invalid",
                full_name=f"Synthetic {label}",
                password_hash=PasswordHasher().hash("Issue217-disposable-password!"),
            )
            db.add_all([role, user])
            db.flush()
            db.add(UserRole(user_id=user.id, role_id=role.id))
        db.commit()


class BrowserFixture:
    def __init__(self):
        from app.main import app

        self.app = app
        self.mode = "normal"
        self.posts = 0
        self.release = asyncio.Event()
        self.waiting = False
        self.refreshes = 0

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            return await self.app(scope, receive, send)
        path = scope["path"]
        if path == "/__issue217_fixture/control":
            # Available only on this standalone localhost synthetic fixture.
            query = scope.get("query_string", b"").decode("ascii")
            from urllib.parse import parse_qs

            mode = parse_qs(query).get("mode", [self.mode])[0]
            if mode not in (
                "normal",
                "lost_response",
                "disabled",
                "old_node",
                "unknown",
                "hold_response",
                "csrf_error",
                "payload_conflict",
                "truncated_response",
                "gateway_timeout",
                "auth401",
                "validation422",
                "intake_unavailable",
            ):
                raise ValueError("Unsupported test mode")
            self.mode = mode
            if mode == "normal":
                self.release.set()
            elif mode == "hold_response":
                self.release.clear()
            body = json.dumps(
                {
                    "mode": self.mode,
                    "posts": self.posts,
                    "waiting": self.waiting,
                    "refreshes": self.refreshes,
                }
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 200,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        if not path.startswith(("/api/", "/health")):
            # Standalone test frontend proxy permits reproducible browser startup faults.
            import httpx
            from urllib.parse import parse_qs

            query = scope.get("query_string", b"").decode("ascii")
            fault = parse_qs(query).get("issue217_fault", [""])[0]
            async with httpx.AsyncClient() as client:
                upstream = await client.get(
                    "http://127.0.0.1:5417" + path + ("?" + query if query else "")
                )
            body = upstream.content
            kind = upstream.headers.get("content-type", "application/octet-stream")
            if "text/html" in kind:
                script = ""
                if fault == "storage-denied":
                    script = "Object.defineProperty(window,'sessionStorage',{get(){throw Error('synthetic storage denial')}});"
                elif fault == "no-csprng":
                    script = (
                        "Object.defineProperty(crypto,'randomUUID',{value:undefined});"
                    )
                elif fault == "storage-after-dispatch":
                    script = "const originalSet=Storage.prototype.setItem;let sets=0;Storage.prototype.setItem=function(k,v){if(++sets>1)throw Error('synthetic quota');return originalSet.call(this,k,v)};"
                elif fault == "storage-quota":
                    script = "Storage.prototype.setItem=function(){throw Error('synthetic quota before dispatch')};"
                elif fault == "corrupt-marker":
                    from app.db.session import SessionLocal
                    from app.modules.project_master_data.models import (
                        OrganizationProfile,
                        User,
                    )

                    with SessionLocal() as db:
                        org = (
                            db.query(OrganizationProfile)
                            .filter_by(organization_slug="issue217-browser-synthetic")
                            .one()
                        )
                        user = (
                            db.query(User)
                            .filter_by(
                                organization_id=org.id, email="owner@issue217.invalid"
                            )
                            .one()
                        )
                        script = f"sessionStorage.setItem('valora.preliminary-create.v1:{org.id}:{user.id}','corrupt');"
                elif fault == "restored-markers":
                    # Model a browser restoring tab storage before loading the app.
                    # Native undo-close is outside this in-app browser's controls.
                    from app.db.session import SessionLocal
                    from app.modules.project_master_data.models import (
                        OrganizationProfile,
                        PreliminaryProjectCreateReceipt,
                        User,
                    )

                    with SessionLocal() as db:
                        org = (
                            db.query(OrganizationProfile)
                            .filter_by(organization_slug="issue217-browser-synthetic")
                            .one()
                        )
                        user = (
                            db.query(User)
                            .filter_by(
                                organization_id=org.id, email="owner@issue217.invalid"
                            )
                            .one()
                        )
                        receipt = (
                            db.query(PreliminaryProjectCreateReceipt)
                            .filter_by(organization_id=org.id, actor_user_id=user.id)
                            .order_by(
                                PreliminaryProjectCreateReceipt.recorded_at.desc()
                            )
                            .first()
                        )
                        assert (
                            receipt is not None
                        ), "Commit a synthetic request before restore"
                        common = {
                            "version": 1,
                            "organization_id": str(org.id),
                            "actor_user_id": str(user.id),
                            "first_sent_at": receipt.recorded_at.isoformat(),
                        }
                        markers = [
                            {
                                **common,
                                "request_id": str(uuid.uuid4()),
                                "phase": "PARKED",
                            },
                            {
                                **common,
                                "request_id": str(receipt.request_id),
                                "phase": "COMMITTED",
                                "project_id": str(receipt.project_id),
                                "receipt_id": str(receipt.id),
                            },
                        ]
                        key = f"valora.preliminary-create.v1:{org.id}:{user.id}"
                        script = f"sessionStorage.setItem({json.dumps(key)},{json.dumps(json.dumps(markers))});"
                if script:
                    body = body.replace(
                        b"<head>", b"<head><script>" + script.encode() + b"</script>"
                    )
            await send(
                {
                    "type": "http.response.start",
                    "status": upstream.status_code,
                    "headers": [(b"content-type", kind.encode())],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        command = (
            path == "/api/v1/projects/preliminary-create" and scope["method"] == "POST"
        )
        recovery = path.startswith("/api/v1/projects/preliminary-create-requests/")
        if path == "/api/v1/auth/refresh" and scope["method"] == "POST":
            self.refreshes += 1
        if command:
            self.posts += 1
        if (command and self.mode in ("auth401", "validation422")) or (
            path.startswith("/api/v1/projects/")
            and path.count("/") == 4
            and scope["method"] == "GET"
            and self.mode == "intake_unavailable"
        ):
            status = {"auth401": 401, "validation422": 422, "intake_unavailable": 503}[
                self.mode
            ]
            detail = (
                [
                    {
                        "loc": ["body", "name"],
                        "msg": "Synthetic pre-command validation rejection",
                        "type": "value_error",
                    }
                ]
                if status == 422
                else {
                    "title": "Synthetic session rejection",
                    "message": "Synthetic test response",
                }
            )
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send(
                {
                    "type": "http.response.body",
                    "body": json.dumps({"detail": detail}).encode(),
                }
            )
            return
        if command and self.mode == "csrf_error":
            body = json.dumps(
                {
                    "detail": {
                        "code": "CSRF_ERROR",
                        "title": "Synthetic CSRF denial",
                        "message": "Synthetic test rejection",
                    }
                }
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": 403,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        if command and self.mode == "payload_conflict":
            chunks = []
            while True:
                message = await receive()
                chunks.append(message.get("body", b""))
                if not message.get("more_body", False):
                    break
            original = b"".join(chunks)
            changed = json.loads(original)
            changed["name"] = "Synthetic competing committed payload"

            def request_body(body):
                async def read():
                    return {"type": "http.request", "body": body, "more_body": False}

                return read

            committed = []
            await self.app(
                scope,
                request_body(json.dumps(changed).encode()),
                self.capture(committed),
            )
            assert committed[0]["status"] == 201
            self.mode = "normal"
            return await self.app(scope, request_body(original), send)
        if (command and self.mode in ("disabled", "unknown")) or (
            recovery and self.mode == "old_node"
        ):
            status = 404 if recovery else 503
            body = json.dumps(
                {"detail": "Not Found" if recovery else "Synthetic service unavailable"}
            ).encode()
            await send(
                {
                    "type": "http.response.start",
                    "status": status,
                    "headers": [(b"content-type", b"application/json")],
                }
            )
            await send({"type": "http.response.body", "body": body})
            return
        if command and self.mode in (
            "lost_response",
            "hold_response",
            "truncated_response",
            "gateway_timeout",
        ):
            fault = self.mode
            messages = []
            await self.app(scope, receive, self.capture(messages))
            start = next(m for m in messages if m["type"] == "http.response.start")
            if fault == "gateway_timeout" and start["status"] in (200, 201):
                self.mode = "normal"
                await send(
                    {
                        "type": "http.response.start",
                        "status": 504,
                        "headers": [(b"content-type", b"text/plain")],
                    }
                )
                await send(
                    {
                        "type": "http.response.body",
                        "body": b"Synthetic gateway timeout after commit",
                    }
                )
                return
            if fault == "hold_response":
                self.waiting = True
                try:
                    await asyncio.wait_for(self.release.wait(), timeout=30)
                finally:
                    self.waiting = False
                for message in messages:
                    await send(message)
                return
            if start["status"] in (200, 201):
                # Business commit succeeded; client gets an incomplete success body.
                await send(
                    {
                        "type": "http.response.start",
                        "status": 201,
                        "headers": [(b"content-type", b"application/json")]
                        + (
                            [(b"content-length", b"999")]
                            if fault == "truncated_response"
                            else []
                        ),
                    }
                )
                self.mode = "normal"
                await send({"type": "http.response.body", "body": b"{"})
                return
            for message in messages:
                await send(message)
            return
        await self.app(scope, receive, send)

    @staticmethod
    def capture(messages):
        async def append(message):
            messages.append(message)

        return append


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("action", choices=["serve", "control"])
    parser.add_argument("--mode", default="normal")
    args = parser.parse_args()
    verify_target()
    if args.action == "control":
        import httpx

        print(
            httpx.get(
                "http://127.0.0.1:8017/__issue217_fixture/control",
                params={"mode": args.mode},
            ).text
        )
        return
    fixture = BrowserFixture()
    seed()
    seed("issue217-browser-other-synthetic")
    import uvicorn

    uvicorn.run(fixture, host="127.0.0.1", port=8017)


if __name__ == "__main__":
    main()
