"""Real HTTP multipart, scope, CSRF and immutable-input rejection proofs."""
import json
import os
import unittest
import httpx
from contextlib import closing

from acceptance import seed, login, context, command, post, ORIGIN, BASE, PASSWORD
from faults import counts, assert_unpublished
from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.project_master_data.models import User, UserRole


class InputSafety(unittest.TestCase):
    def test_another_same_tenant_actor_cannot_read_or_replay_original_receipt(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            self.assertEqual(post(client, f, payload, b"synthetic").status_code, 201)
            with SessionLocal() as db:
                other = User(organization_id=f["org_id"], email="other@issue208.invalid", full_name="Synthetic other actor",
                    password_hash=hash_password(PASSWORD), status="active")
                db.add(other)
                db.flush()
                db.add(UserRole(user_id=other.id, role_id=f["role_id"], is_active=True))
                db.commit()
            with httpx.Client(base_url=BASE, timeout=30) as other_client:
                response = other_client.post("/api/v1/auth/login", json=dict(organization_slug=f["slug"], email="other@issue208.invalid", password=PASSWORD))
                self.assertEqual(response.status_code, 200)
                response = other_client.get(f'/api/v1/projects/{f["project_id"]}/quotation-documents/import-receipts/{payload["command_id"]}')
                self.assertEqual(response.status_code, 404)
                self.assertEqual(post(other_client, f, payload, b"synthetic").status_code, 404)
            self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)

    def test_exact_one_mib_is_accepted_and_available(self):
        f = seed()
        with closing(login(f)) as client:
            content = b"a" * 1048576
            response = post(client, f, command(context(client, f), content), content)
            self.assertEqual(response.status_code, 201, response.text)
            self.assertEqual(response.json()["byte_length"], 1048576)
            self.assertTrue(response.json()["source"]["available"])

    def test_invalid_multipart_and_injected_fields_never_prepare(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            url = f'/api/v1/projects/{f["project_id"]}/quotation-documents/import'
            headers = {"Origin": ORIGIN, "X-CSRF-Token": client.cookies["XSRF-TOKEN"]}
            for extra in ("actor", "organization_id", "project_id", "binding_id", "provider", "policy", "retention_anchor_at"):
                with self.subTest(injection=extra):
                    response = post(client, f, {**payload, extra: "unsafe-private-marker"}, b"synthetic")
                    self.assertEqual(response.status_code, 422)
                    self.assertNotIn("unsafe-private-marker", response.text)
            for fields in (
                [("metadata", (None, json.dumps(payload))), ("metadata", (None, "{}")), ("file", ("a.txt", b"synthetic"))],
                [("metadata", (None, json.dumps(payload))), ("extra", (None, "value")), ("file", ("a.txt", b"synthetic"))],
                [("metadata", (None, json.dumps(payload))), ("file", ("a.txt", b"synthetic")), ("file", ("b.txt", b"synthetic"))],
                [("metadata", (None, "x" * 8193)), ("file", ("a.txt", b"synthetic"))],
            ):
                self.assertEqual(client.post(url, files=fields, headers=headers).status_code, 422)
            self.assertEqual(client.post(url, files={"metadata": (None, json.dumps(payload)), "file": ("a.txt", b"synthetic")}, headers={"Origin": ORIGIN}).status_code, 403)
            self.assertEqual(counts(f)["quotation_document_import_requests"], 0)
            assert_unpublished(self, f)

    def test_content_limits_streaming_and_safe_errors(self):
        f = seed()
        with closing(login(f)) as client:
            ctx = context(client, f)
            for content in (b"", b"a" * 1048577, b"%PDF-1.7", b"PK\x03\x04archive", b"\xff\xfea\x00", b"a\x00", b"a\xc2\x85"):
                payload = command(ctx, b"synthetic")
                payload["expected_byte_length"] = max(1, min(len(content), 1048576))
                r = post(client, f, payload, content)
                self.assertIn(r.status_code, (413, 415, 422))
            for filename in ("../unsafe-private-marker.txt", "CON.txt", "report.pdf", "bidi\u202e.txt"):
                r = post(client, f, command(ctx, b"synthetic"), b"synthetic", filename)
                self.assertEqual(r.status_code, 422)
                self.assertNotIn("unsafe-private-marker", r.text)
            url = f'/api/v1/projects/{f["project_id"]}/quotation-documents/import'
            r = client.post(url, content=iter([b"a" * 65536] * 18), headers={"Origin": ORIGIN,
                "X-CSRF-Token": client.cookies["XSRF-TOKEN"], "Content-Type": "multipart/form-data; boundary=synthetic"})
            self.assertEqual(r.status_code, 413)
            self.assertEqual(counts(f)["quotation_document_import_requests"], 0)
            assert_unpublished(self, f)

    def test_reused_command_cannot_change_file_name_cas_or_project(self):
        f = seed()
        with closing(login(f)) as client:
            payload = command(context(client, f), b"synthetic")
            result = post(client, f, payload, b"synthetic")
            self.assertEqual(result.status_code, 201, result.text)
            for changes, content, filename in (
                ({}, b"different", "synthetic.txt"),
                ({}, b"synthetic", "renamed.txt"),
                ({"expected_project_row_version": 2}, b"synthetic", "synthetic.txt"),
                ({"expected_case_version": "0" * 64}, b"synthetic", "synthetic.txt"),
            ):
                response = post(client, f, {**payload, **changes}, content, filename)
                self.assertEqual(response.status_code, 409)
            other = seed()
            response = client.get(f'/api/v1/projects/{other["project_id"]}/quotation-documents/import-receipts/{payload["command_id"]}')
            self.assertEqual(response.status_code, 404)
            self.assertEqual(counts(f)["quotation_document_import_receipts"], 1)
            self.assertEqual(counts(f)["version"], 2)


if __name__ == "__main__":
    assert os.environ["POSTGRES_DB"] == "valora_issue208"
    unittest.main(verbosity=2)
