"""Exercise only the disposable #208 stack before product source changes."""
import asyncio
import hashlib
import json
import os
import uuid

import httpx
from sqlalchemy import text
from app.main import app  # noqa: F401

from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.document_workspace.infrastructure.document_blob_store_factory import build_document_blob_store
from app.core.config import get_settings
from app.modules.project_master_data.models import OrganizationProfile, Project, Role, User, UserRole


async def check_blob():
    store = build_document_blob_store(get_settings())
    content = b"\xef\xbb\xbfIssue 208 synthetic preflight\r\n"
    digest = hashlib.sha256(content).hexdigest()
    key = f"preflight/{uuid.uuid4().hex}.txt"

    async def chunks():
        yield content

    result = await store.create_immutable(object_key=key, content=chunks(), byte_length=len(content), expected_sha256=digest)
    assert str(result.status) == "CREATED"
    repeated = await store.create_immutable(object_key=key, content=chunks(), byte_length=len(content), expected_sha256=digest)
    assert str(repeated.status) == "ALREADY_EXISTS"
    read = await store.read_verified(object_key=key, expected_sha256=digest, expected_byte_length=len(content), max_bytes=1048576)
    assert str(read.status) == "MATCH" and read.content == content
    return "create-only-original-byte-readback-PASS"


def main():
    assert os.environ["POSTGRES_HOST"] == "postgres"
    assert os.environ["POSTGRES_DB"] == "valora_issue208"
    assert os.environ["DOCUMENT_BLOB_ROOT"] == "/var/lib/valora/issue208"
    suffix = uuid.uuid4().hex[:12]
    password = os.environ["ISSUE208_SYNTHETIC_PASSWORD"]
    with SessionLocal() as db:
        server = db.scalar(text("select version()"))
        assert server.startswith("PostgreSQL 16.")
        head = db.scalar(text("select version_num from alembic_version"))
        assert head == os.environ.get("ISSUE208_EXPECTED_MIGRATION_HEAD", "e8f9a0b1c2d3")
        org = OrganizationProfile(legal_name="Issue 208 synthetic", organization_slug=f"issue208-{suffix}", status="active")
        role = Role(code=f"issue208-{suffix}", display_name="Synthetic custody permission test", permissions=["project:read", "project:update"])
        db.add_all([org, role])
        db.flush()
        user = User(organization_id=org.id, email="operator@issue208.invalid", full_name="Synthetic operator", password_hash=hash_password(password), status="active")
        db.add(user)
        db.flush()
        db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
        project = Project(organization_id=org.id, code=f"ISSUE208-{suffix}", name="Synthetic import preflight", created_by=user.id, status="draft")
        db.add(project)
        db.commit()
        slug, project_id = org.organization_slug, str(project.id)
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=20) as client:
        response = client.post("/api/v1/auth/login", json={"organization_slug": slug, "email": "operator@issue208.invalid", "password": password})
        assert response.status_code == 200, response.status_code
        response = client.get("/api/v1/auth/me")
        assert response.status_code == 200, response.status_code
        response = client.get(f"/api/v1/projects/{project_id}/case-state")
        assert response.status_code == 200, response.status_code
    print(json.dumps({"postgres": server, "migration_head": head, "real_auth_and_case_state": "PASS", "local_storage": asyncio.run(check_blob())}))


if __name__ == "__main__":
    main()
