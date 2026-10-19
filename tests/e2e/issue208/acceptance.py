"""Real PostgreSQL/local-store/API/auth acceptance for disposable #208 data only."""
import hashlib
import json
import os
import unittest
import uuid
from contextlib import closing

import httpx
from sqlalchemy import text

from app.main import app  # noqa: F401
from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.project_master_data.models import OrganizationProfile, Project, Role, User, UserRole

PASSWORD = os.environ["ISSUE208_SYNTHETIC_PASSWORD"]
BASE = "http://127.0.0.1:8000"
ORIGIN = "http://localhost:51208"


def seed(permission=True):
    suffix = uuid.uuid4().hex[:12]
    with SessionLocal() as db:
        org = OrganizationProfile(legal_name="Issue 208 synthetic acceptance", organization_slug=f"issue208-{suffix}", status="active")
        role = Role(code=f"issue208-{suffix}", display_name="Synthetic custody actor", permissions=["project:read", *(["project:update"] if permission else [])])
        db.add_all([org, role])
        db.flush()
        user = User(organization_id=org.id, email="operator@issue208.invalid", full_name="Synthetic operator", password_hash=hash_password(PASSWORD), status="active")
        db.add(user)
        db.flush()
        grant = UserRole(user_id=user.id, role_id=role.id, is_active=True)
        project = Project(organization_id=org.id, code=f"ISSUE208-{suffix}", name="Synthetic original import acceptance", created_by=user.id, status="draft")
        db.add_all([grant, project])
        db.commit()
        return dict(org_id=org.id, actor_id=user.id, project_id=project.id, role_id=role.id, grant_id=grant.id, slug=org.organization_slug)


def login(fixture):
    client = httpx.Client(base_url=BASE, timeout=30)
    r = client.post("/api/v1/auth/login", json=dict(organization_slug=fixture["slug"], email="operator@issue208.invalid", password=PASSWORD))
    assert r.status_code == 200, r.status_code
    return client


def context(client, fixture):
    r = client.get(f'/api/v1/projects/{fixture["project_id"]}/quotation-documents/import-context')
    assert r.status_code == 200, r.text
    return r.json()


def command(ctx, content, **changes):
    return dict(contract_version="quotation-txt-import-v1", command_id=str(uuid.uuid4()), confirm=True,
        expected_case_version=ctx["case_version"], expected_project_row_version=ctx["project_row_version"],
        expected_sha256=hashlib.sha256(content).hexdigest(), expected_byte_length=len(content), **changes)


def post(client, fixture, payload, content, filename="synthetic.txt", recover=False):
    suffix = f'import-receipts/{payload["command_id"]}/recover' if recover else "import"
    return client.post(f'/api/v1/projects/{fixture["project_id"]}/quotation-documents/{suffix}',
        files={"file": (filename, content, "text/plain"), "metadata": (None, json.dumps(payload), "application/json")},
        headers={"X-CSRF-Token": client.cookies["XSRF-TOKEN"], "Origin": ORIGIN})


class Acceptance(unittest.TestCase):
    def test_normal_replay_and_authoritative_retention(self):
        f = seed()
        with closing(login(f)) as client:
            ctx = context(client, f)
            assert ctx["can_import"]
            before_stages = client.get(f'/api/v1/projects/{f["project_id"]}/case-state').json()["stages"]
            content = "Báo giá tổng hợp kiểm thử\n".encode("utf-8")
            payload = command(ctx, content)
            r = post(client, f, payload, content)
            self.assertEqual(r.status_code, 201, r.text)
            result = r.json()
            self.assertTrue(result["source"]["available"])
            again = post(client, f, payload, content)
            self.assertEqual(again.status_code, 200, again.text)
            self.assertEqual(result["historical_receipt"], again.json()["historical_receipt"])
            status = client.get(f'/api/v1/projects/{f["project_id"]}/quotation-documents/import-receipts/{payload["command_id"]}')
            self.assertEqual(status.status_code, 200, status.text)
            self.assertEqual(status.json()["receipt_digest"], result["receipt_digest"])
            self.assertFalse(status.json()["purge_allowed"])
            self.assertIsNone(status.json()["effective_minimum_retain_until"])
            self.assertEqual(before_stages, client.get(f'/api/v1/projects/{f["project_id"]}/case-state').json()["stages"])
            with SessionLocal() as db:
                row = db.execute(text("""select r.finalized_at, r.retention_anchor_at, b.retention_anchor_at,
                    b.bound_at, a.created_at, r.minimum_retain_until, b.minimum_retain_until
                    from quotation_document_import_receipts r join storage_object_bindings b on b.id=r.binding_id
                    join audit_events a on a.id=r.milestone_audit_id where r.id=:id"""), {"id": result["receipt_id"]}).one()
                self.assertEqual(len(set(row[:5])), 1)
                self.assertEqual(row[5], row[6])
                self.assertEqual(db.scalar(text("select row_version from projects where id=:id"), {"id": f["project_id"]}), ctx["project_row_version"] + 1)
                for table in ("document_revisions", "storage_object_bindings", "quotation_document_import_requests", "quotation_document_import_receipts"):
                    self.assertEqual(db.scalar(text(f"select count(*) from {table} where project_id=:id"), {"id": f["project_id"]}), 1)
                for table in ("supplier_quote_facts", "supplier_quote_items", "project_price_evidence_sources", "project_price_evidence_decisions", "project_price_evidence_confirmations"):
                    self.assertEqual(db.scalar(text(f"select count(*) from {table} where project_id=:id"), {"id": f["project_id"]}), 0)


if __name__ == "__main__":
    assert os.environ["POSTGRES_DB"] == "valora_issue208"
    assert os.environ["DOCUMENT_BLOB_ROOT"] == "/var/lib/valora/issue208"
    unittest.main(verbosity=2)
