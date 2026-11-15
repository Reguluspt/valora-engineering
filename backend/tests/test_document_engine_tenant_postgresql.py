import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from threading import Barrier

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import event, select, text
from sqlalchemy.orm import Session

from app.api import document_engine
from app.api.auth import get_cookie_keys, hash_token
from app.core.rbac import get_current_user
from app.db import engine, get_db
from app.main import app
from app.modules.project_master_data.models import (
    AuditEvent,
    ComputedPlaceholderExpression,
    DocumentPackage,
    DocumentPackageItem,
    DocumentTemplate,
    EvidenceFile,
    GeneratedDocument,
    OrganizationProfile,
    PlaceholderBinding,
    Project,
    RenderJob,
    Role,
    TemplatePlaceholder,
    TemplateVersion,
    User,
    UserActionLog,
    UserRole,
    UserSession,
)

_PREFIX = "/api/v1/document-engine"
_ORIGIN = "http://localhost:5173"
_PERMISSIONS = [
    "document_engine:read",
    "document_engine:template:create",
    "document_engine:template:update",
    "document_engine:template:deprecate",
    "document_engine:render:create",
    "document_engine:package:create",
    "document_engine:package:update",
]
_DOCUMENT_MODELS = (
    DocumentTemplate, TemplateVersion, TemplatePlaceholder, ComputedPlaceholderExpression,
    PlaceholderBinding, RenderJob, GeneratedDocument, DocumentPackage, DocumentPackageItem,
)
_PLACEHOLDER = {
    "placeholder_key": "synthetic.field", "label_vi": "Synthetic", "data_type": "scalar",
    "source_context": "project", "source_path": "$.synthetic",
}
_EXPRESSION = {
    "placeholder_key": "synthetic.expression", "expression": "1 + 1", "output_data_type": "scalar",
}


@pytest.fixture(autouse=True)
def setup_test_auth():
    assert get_current_user not in app.dependency_overrides
    assert get_db not in app.dependency_overrides


@pytest.fixture(scope="module")
def pg():
    if os.environ.get("VALORA_SEC001_DISPOSABLE_PG") != "1":
        pytest.skip("requires the explicitly selected SEC-001 disposable PostgreSQL instance")
    url = engine.url
    assert (url.drivername, url.host, url.database, url.username) == (
        "postgresql+psycopg", "127.0.0.1", "valora_sec001_stage1", "sec001_app",
    )
    assert url.port and url.port != 5432 and not url.query
    with engine.connect() as conn:
        identity = conn.execute(text("""
            SELECT current_database(), current_user, current_setting('server_version_num')::int,
                   shobj_description(d.oid, 'pg_database'), r.rolsuper, r.rolbypassrls,
                   r.rolcreatedb, r.rolcreaterole, has_schema_privilege(current_user, 'public', 'CREATE')
            FROM pg_database d CROSS JOIN pg_roles r
            WHERE d.datname = current_database() AND r.rolname = current_user
        """)).one()
    assert identity[:2] == ("valora_sec001_stage1", "sec001_app")
    assert 160000 <= identity[2] < 170000
    assert identity[3:] == ("VALORA SEC-001 disposable synthetic", False, False, False, False, False)
    return engine


@dataclass(frozen=True)
class Tenant:
    org: str
    user: str
    template: str
    other_template: str
    version: str
    other_version: str
    replacement_version: str
    placeholder: str
    expression: str
    legacy_expression: str
    project: str
    other_project: str
    job: str
    document: str
    package: str
    evidence: str
    inactive_evidence: str
    snapshot: dict


def _tenant(db, suffix):
    org = OrganizationProfile(legal_name=f"Synthetic {suffix}", organization_slug=f"synthetic-{suffix}")
    db.add(org)
    db.flush()
    user = User(organization_id=org.id, email=f"{suffix}@example.invalid", full_name="Synthetic user")
    uploader = User(organization_id=org.id, email=f"upload-{suffix}@example.invalid", full_name="Synthetic uploader")
    db.add_all([user, uploader])
    db.flush()
    role = Role(code=f"sec001-{suffix}", display_name="Synthetic Document Engine", permissions=_PERMISSIONS)
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))

    template = DocumentTemplate(
        organization_id=org.id, created_by=user.id, code=f"CODE-{suffix}", document_type="report", name="Synthetic",
    )
    other_template = DocumentTemplate(
        organization_id=org.id, created_by=user.id, code=f"OTHER-{suffix}", document_type="report", name="Synthetic",
    )
    project = Project(organization_id=org.id, created_by=user.id, code=f"PR-{suffix}", name="Synthetic")
    other_project = Project(organization_id=org.id, created_by=user.id, code=f"ALT-{suffix}", name="Synthetic")
    db.add_all([template, other_template, project, other_project])
    db.flush()

    version = TemplateVersion(document_template_id=template.id, version_number=1, template_format="docx")
    other_version = TemplateVersion(document_template_id=other_template.id, version_number=1, template_format="docx")
    replacement = TemplateVersion(document_template_id=template.id, version_number=2, template_format="docx")
    db.add_all([version, other_version, replacement])
    db.flush()
    expression = ComputedPlaceholderExpression(
        template_version_id=version.id, created_by=user.id, **_EXPRESSION,
    )
    legacy = ComputedPlaceholderExpression(created_by=user.id, **_EXPRESSION)
    placeholder = TemplatePlaceholder(template_version_id=version.id, **_PLACEHOLDER)
    snapshot = {"synthetic_tenant": suffix}
    job = RenderJob(
        project_id=project.id, template_version_id=version.id, created_by=user.id,
        data_snapshot=snapshot, data_snapshot_hash="a" * 64, output_formats=["docx"], status="completed",
    )
    package = DocumentPackage(project_id=project.id, created_by=user.id, package_type="qc", name="Synthetic")
    file_fields = dict(filename="synthetic.docx", mime_type="application/octet-stream", file_size=1,
                       checksum="a" * 64, uploaded_by=uploader.id)
    evidence = EvidenceFile(object_key=f"active/{suffix}", **file_fields)
    inactive = EvidenceFile(object_key=f"archived/{suffix}", status="archived", **file_fields)
    db.add_all([expression, legacy, placeholder, job, package, evidence, inactive])
    db.flush()
    document = GeneratedDocument(
        project_id=project.id, render_job_id=job.id, template_version_id=version.id, document_type="report",
        output_format="docx", filename="synthetic.docx", storage_key=f"generated/{suffix}",
        checksum_sha256=job.data_snapshot_hash, file_size_bytes=1, data_snapshot_hash=job.data_snapshot_hash,
    )
    db.add(document)
    db.flush()
    return Tenant(
        *(str(row.id) for row in (
            org, user, template, other_template, version, other_version, replacement,
            placeholder, expression, legacy, project, other_project, job, document, package, evidence, inactive,
        )),
        snapshot=snapshot,
    )


@pytest.fixture
def tenants(pg):
    with Session(pg) as db, db.begin():
        return tuple(_tenant(db, uuid.uuid4().hex) for _ in range(2))


@pytest.fixture
def signed_client(pg):
    clients = []

    def make(tenant, *, state="valid"):
        access, csrf = uuid.uuid4().hex, uuid.uuid4().hex
        now = datetime.now(timezone.utc)
        with Session(pg) as db, db.begin():
            user_id = uuid.UUID(tenant.user)
            org_id = uuid.UUID(tenant.org)
            if state == "no-permission":
                user = User(organization_id=org_id, email=f"{access}@example.invalid", full_name="Unprivileged")
                db.add(user)
                db.flush()
                user_id = user.id
            if state == "mismatched":
                org_id = db.scalar(select(OrganizationProfile.id).where(OrganizationProfile.id != org_id).limit(1))
            db.add(UserSession(
                user_id=user_id, organization_id=org_id,
                access_token_hash=hash_token(access), csrf_token_hash=hash_token(csrf),
                access_expires_at=now + timedelta(minutes=-1 if state == "expired" else 15),
                idle_expires_at=now + timedelta(minutes=30), absolute_expires_at=now + timedelta(hours=2),
            ))
        client = TestClient(app, raise_server_exceptions=False)
        clients.append(client)
        client.headers["Origin"] = _ORIGIN
        if state != "missing-csrf":
            client.headers["X-CSRF-Token"] = "invalid" if state == "wrong-csrf" else csrf
        if state != "missing":
            client.cookies.set(get_cookie_keys()[0], "invalid" if state == "invalid" else access)
        return client

    yield make
    for client in clients:
        client.close()


def _business_snapshot(pg):
    with pg.connect() as conn:
        rows = [conn.execute(select(model.__table__).order_by(model.id)).all() for model in _DOCUMENT_MODELS]
        document_audits = conn.execute(select(AuditEvent.__table__).where(
            AuditEvent.entity_type.in_((*[model.__tablename__.removesuffix("s") for model in _DOCUMENT_MODELS],
                                       "computed_expression")),
        ).order_by(AuditEvent.id)).all()
        actions = conn.execute(select(UserActionLog.__table__).order_by(UserActionLog.id)).all()
    return rows, document_audits, actions


def _route(number, target, *, absent=False):
    missing = str(uuid.uuid4())
    template = missing if absent else target.template
    version = missing if absent else target.version
    project = missing if absent else target.project
    package = missing if absent else target.package
    routes = {
        1: ("POST", "/templates", {
            "organization_id": target.org, "code": f"CREATE-{target.template}", "document_type": "report",
            "name": "Synthetic",
        }, 201),
        2: ("GET", "/templates", None, 200),
        3: ("GET", f"/templates/{template}", None, 200),
        4: ("PATCH", f"/templates/{template}", {
            "name": "Updated", "current_version_id": target.version,
            "replacement_template_id": target.other_template, "expected_row_version": 1,
        }, 200),
        5: ("POST", f"/templates/{template}/versions", {
            "version_number": 3, "template_format": "docx", "source_file_id": target.evidence,
        }, 201),
        6: ("GET", f"/template-versions/{version}", None, 200),
        7: ("POST", f"/template-versions/{version}/deprecate", {
            "expected_row_version": 1, "deprecation_reason": "Synthetic", "replacement_version_id": target.replacement_version,
        }, 200),
        8: ("GET", f"/template-versions/{version}/placeholders", None, 200),
        9: ("POST", f"/template-versions/{version}/placeholders", {
            **_PLACEHOLDER, "computed_expression_id": target.expression,
        }, 201),
        10: ("POST", f"/template-versions/{version}/bindings", {
            "template_placeholder_id": target.placeholder, "binding_type": "direct", "binding_path": "$.synthetic",
        }, 201),
        11: ("POST", f"/template-versions/{version}/computed-expressions", _EXPRESSION, 201),
        12: ("POST", "/render-jobs", {
            "project_id": project, "template_version_id": target.version,
            "data_snapshot": target.snapshot, "output_formats": ["docx"],
        }, 201),
        13: ("GET", f"/render-jobs/{missing if absent else target.job}", None, 200),
        14: ("GET", f"/generated-documents/{missing if absent else target.document}", None, 200),
        15: ("POST", "/packages", {"project_id": project, "package_type": "qc", "name": "Synthetic"}, 201),
        16: ("GET", f"/packages/{package}", None, 200),
        17: ("POST", f"/packages/{package}/items", {"generated_document_id": target.document, "sort_order": 1}, 201),
    }
    return routes[number]


@pytest.mark.parametrize(
    "number,ownership",
    [pytest.param(number, ownership, id=f"r{number:02d}-{ownership}")
     for number in range(1, 18) for ownership in ("own", "foreign")],
)
def test_tenant_route(pg, tenants, signed_client, number, ownership):
    own, other = tenants
    target = own if ownership == "own" else other
    actor = other if number == 2 and ownership == "foreign" else own
    client = signed_client(actor)
    method, path, body, success = _route(number, target)
    if number == 1 and ownership == "foreign":
        with Session(pg) as db:
            body["code"] = db.get(DocumentTemplate, uuid.UUID(other.template)).code

    before = _business_snapshot(pg) if ownership == "foreign" else None
    response = client.request(method, _PREFIX + path, json=body)
    if number == 2:
        assert response.status_code == 200, response.text
        assert {row["id"] for row in response.json()} == {actor.template, actor.other_template}
        assert {row["organization_id"] for row in response.json()} == {actor.org}
    elif ownership == "foreign":
        if number == 1:
            assert response.status_code == 403
            unseen = client.post(_PREFIX + path, json={**body, "code": uuid.uuid4().hex})
            assert (response.status_code, response.json()) == (unseen.status_code, unseen.json())
        else:
            missing_method, missing_path, missing_body, _ = _route(number, target, absent=True)
            missing = client.request(missing_method, _PREFIX + missing_path, json=missing_body)
            assert response.status_code == 404, response.text
            assert (response.status_code, response.json()) == (missing.status_code, missing.json())
    else:
        assert response.status_code == success, response.text
        data = response.json()
        if number == 8:
            assert [row["id"] for row in data] == [target.placeholder]
        else:
            fields = {
                1: {"organization_id": target.org, "created_by": target.user, "code": body.get("code") if body else None},
                3: {"id": target.template},
                4: {"id": target.template, "current_version_id": target.version,
                    "replacement_template_id": target.other_template, "row_version": 2},
                5: {"document_template_id": target.template, "source_file_id": target.evidence},
                6: {"id": target.version, "document_template_id": target.template},
                7: {"id": target.version, "replacement_version_id": target.replacement_version, "status": "deprecated"},
                9: {"template_version_id": target.version, "computed_expression_id": target.expression},
                10: {"template_version_id": target.version, "template_placeholder_id": target.placeholder},
                11: {"expression": _EXPRESSION["expression"], "created_by": target.user},
                12: {"project_id": target.project, "template_version_id": target.version,
                     "data_snapshot": target.snapshot, "status": "completed"},
                13: {"id": target.job, "data_snapshot": target.snapshot},
                14: {"id": target.document, "project_id": target.project, "render_job_id": target.job},
                15: {"project_id": target.project, "created_by": target.user},
                16: {"id": target.package, "project_id": target.project},
                17: {"document_package_id": target.package, "generated_document_id": target.document},
            }
            assert {key: data[key] for key in fields[number]} == fields[number]
            if number == 11:
                with Session(pg) as db:
                    assert str(db.get(ComputedPlaceholderExpression, uuid.UUID(data["id"])).template_version_id) == target.version
    if ownership == "foreign":
        assert _business_snapshot(pg) == before


@pytest.mark.parametrize(("route", "field", "tenant_index", "attribute"), [
    pytest.param(4, "current_version_id", 0, "other_version", id="current-version-wrong-template"),
    pytest.param(4, "current_version_id", 1, "version", id="current-version-foreign"),
    pytest.param(4, "replacement_template_id", 1, "template", id="replacement-template-foreign"),
    pytest.param(5, "source_file_id", 1, "evidence", id="source-file-foreign"),
    pytest.param(5, "source_file_id", 0, "inactive_evidence", id="source-file-inactive"),
    pytest.param(7, "replacement_version_id", 0, "other_version", id="replacement-version-wrong-template"),
    pytest.param(7, "replacement_version_id", 1, "version", id="replacement-version-foreign"),
    pytest.param(9, "computed_expression_id", 0, "legacy_expression", id="expression-unowned"),
    pytest.param(9, "computed_expression_id", 1, "expression", id="expression-foreign"),
    pytest.param(10, "template_placeholder_id", 1, "placeholder", id="placeholder-foreign"),
    pytest.param(12, "template_version_id", 1, "version", id="render-foreign-template"),
    pytest.param(12, "project_id", 1, "project", id="render-foreign-project"),
    pytest.param(17, "generated_document_id", 1, "document", id="package-foreign-document"),
])
def test_secondary_reference(pg, tenants, signed_client, route, field, tenant_index, attribute):
    own, _ = tenants
    method, path, body, _ = _route(route, own)
    client = signed_client(own)
    before = _business_snapshot(pg)
    response = client.request(method, _PREFIX + path, json={**body, field: getattr(tenants[tenant_index], attribute)})
    absent = client.request(method, _PREFIX + path, json={**body, field: str(uuid.uuid4())})
    assert response.status_code == 404, response.text
    assert (response.status_code, response.json()) == (absent.status_code, absent.json())
    assert _business_snapshot(pg) == before


@pytest.mark.parametrize("case", [
    "expression-other-version", "placeholder-other-version", "package-other-project",
    "legacy-render-foreign-template", "legacy-render-foreign-creator",
    "legacy-document-foreign-render-creator", "legacy-document-wrong-project", "legacy-document-wrong-template",
])
def test_inconsistent_lineage(pg, tenants, signed_client, case):
    own, other = tenants
    if case == "expression-other-version":
        method, path, body, _ = _route(9, own)
        path = path.replace(own.version, own.other_version)
    elif case == "placeholder-other-version":
        method, path, body, _ = _route(10, own)
        path = path.replace(own.version, own.other_version)
    else:
        with Session(pg) as db, db.begin():
            if case == "legacy-render-foreign-template":
                db.get(RenderJob, uuid.UUID(own.job)).template_version_id = uuid.UUID(other.version)
                method, path, body, _ = _route(13, own)
            elif case in ("legacy-render-foreign-creator", "legacy-document-foreign-render-creator"):
                db.get(RenderJob, uuid.UUID(own.job)).created_by = uuid.UUID(other.user)
                method, path, body, _ = _route(13 if case == "legacy-render-foreign-creator" else 14, own)
            else:
                document = db.get(GeneratedDocument, uuid.UUID(own.document))
                if case == "legacy-document-wrong-template":
                    document.template_version_id = uuid.UUID(own.other_version)
                else:
                    document.project_id = uuid.UUID(own.other_project)
                    if case == "package-other-project":
                        db.get(RenderJob, uuid.UUID(own.job)).project_id = document.project_id
                method, path, body, _ = _route(17 if case == "package-other-project" else 14, own)
    before = _business_snapshot(pg)
    response = signed_client(own).request(method, _PREFIX + path, json=body)
    assert response.status_code == 404, response.text
    assert "data_snapshot" not in response.json()
    assert _business_snapshot(pg) == before


@pytest.mark.parametrize(("state", "status"), [
    ("missing", 401), ("invalid", 401), ("expired", 401), ("mismatched", 401),
    ("no-permission", 403), ("missing-csrf", 403), ("wrong-csrf", 403),
])
def test_principal_and_csrf(pg, tenants, signed_client, state, status):
    own, _ = tenants
    before = _business_snapshot(pg)
    method, path, body, _ = _route(1, own)
    response = signed_client(own, state=state).request(method, _PREFIX + path, json=body)
    assert response.status_code == status, response.text
    assert _business_snapshot(pg) == before


def _compete(clients, method, path, bodies):
    with ThreadPoolExecutor(max_workers=2) as pool:
        requests = [pool.submit(client.request, method, _PREFIX + path, json=body)
                    for client, body in zip(clients, bodies, strict=True)]
        return [request.result(timeout=25) for request in requests]


@pytest.mark.parametrize(("route", "model", "audit", "action", "field"), [
    (4, DocumentTemplate, "DOCUMENT_TEMPLATE_UPDATE", "update_template", "name"),
    (7, TemplateVersion, "TEMPLATE_VERSION_DEPRECATE", "deprecate_version", "deprecation_reason"),
], ids=["template-cas", "version-cas"])
def test_cas_two_writers(pg, tenants, signed_client, route, model, audit, action, field):
    own, _ = tenants
    target = uuid.UUID(own.template if route == 4 else own.version)
    barrier = Barrier(2, timeout=15)

    def synchronize(db, _flush_context, _instances):
        if any(isinstance(row, model) and row.id == target for row in db.dirty):
            barrier.wait()

    method, path, body, _ = _route(route, own)
    clients = [signed_client(own), signed_client(own)]
    event.listen(Session, "before_flush", synchronize)
    try:
        responses = _compete(clients, method, path, [{**body, field: name} for name in ("first", "second")])
    finally:
        event.remove(Session, "before_flush", synchronize)
    assert sorted(response.status_code for response in responses) == [200, 409]
    winner = next(response.json() for response in responses if response.status_code == 200)
    with Session(pg) as db:
        row = db.get(model, target)
        assert row.row_version == 2
        assert getattr(row, field) == winner[field]
        assert db.scalars(select(AuditEvent.event_name).where(AuditEvent.entity_id == target)).all() == [audit]
        assert db.scalars(select(UserActionLog.action_type).where(UserActionLog.target_id == target)).all() == [action]


@pytest.mark.parametrize("shared_tenant", [False, True], ids=["two-tenants", "same-tenant"])
def test_concurrent_template_code(pg, tenants, signed_client, shared_tenant):
    own, other = tenants
    actors = [own, own if shared_tenant else other]
    clients = [signed_client(actor) for actor in actors]
    code = f" Code-{uuid.uuid4().hex} "
    barrier = Barrier(2, timeout=15)

    def synchronize(db, _flush_context, _instances):
        if any(isinstance(row, DocumentTemplate) and row.code == code for row in db.new):
            barrier.wait()

    method, path, _, _ = _route(1, own)
    bodies = [{**_route(1, actor)[2], "code": code} for actor in actors]
    event.listen(Session, "before_flush", synchronize)
    try:
        responses = _compete(clients, method, path, bodies)
    finally:
        event.remove(Session, "before_flush", synchronize)
    assert sorted(response.status_code for response in responses) == ([201, 400] if shared_tenant else [201, 201])
    with Session(pg) as db:
        rows = db.scalars(select(DocumentTemplate).where(DocumentTemplate.code == code)).all()
        assert {str(row.organization_id) for row in rows} == {actor.org for actor in actors}
        for row in rows:
            assert db.scalars(select(AuditEvent.event_name).where(AuditEvent.entity_id == row.id)).all() == [
                "DOCUMENT_TEMPLATE_CREATE",
            ]
            assert db.scalars(select(UserActionLog.action_type).where(UserActionLog.target_id == row.id)).all() == [
                "create_template",
            ]


def test_render_rolls_back_when_audit_fails(pg, tenants, signed_client, monkeypatch):
    own, _ = tenants
    original = document_engine.log_audit_event

    def fail_after_audit(**kwargs):
        original(**kwargs)
        raise RuntimeError("Synthetic failure after audit flush")

    before = _business_snapshot(pg)
    monkeypatch.setattr(document_engine, "log_audit_event", fail_after_audit)
    method, path, body, _ = _route(12, own)
    assert signed_client(own).request(method, _PREFIX + path, json=body).status_code == 500
    assert _business_snapshot(pg) == before


def test_legacy_references_are_quarantined_without_changing_history(pg, tenants, signed_client):
    own, other = tenants
    with Session(pg) as db, db.begin():
        template = db.get(DocumentTemplate, uuid.UUID(own.template))
        template.current_version_id = uuid.UUID(other.version)
        template.replacement_template_id = uuid.UUID(other.template)
        version = db.get(TemplateVersion, uuid.UUID(own.version))
        version.source_file_id = uuid.UUID(other.evidence)
        version.replacement_version_id = uuid.UUID(other.version)
        placeholder = db.get(TemplatePlaceholder, uuid.UUID(own.placeholder))
        placeholder.computed_expression_id = uuid.UUID(own.legacy_expression)
    before = _business_snapshot(pg)
    client = signed_client(own)
    listed = client.get(_PREFIX + "/templates")
    assert listed.status_code == 200
    template = next(row for row in listed.json() if row["id"] == own.template)
    assert template["current_version_id"] is None and template["replacement_template_id"] is None
    assert client.get(_PREFIX + f"/templates/{own.template}").json() == template
    version = client.get(_PREFIX + f"/template-versions/{own.version}")
    assert version.status_code == 200
    assert version.json()["source_file_id"] is None and version.json()["replacement_version_id"] is None
    placeholders = client.get(_PREFIX + f"/template-versions/{own.version}/placeholders")
    assert placeholders.status_code == 200
    assert [(row["id"], row["computed_expression_id"]) for row in placeholders.json()] == [(own.placeholder, None)]
    method, path, body, _ = _route(10, own)
    response = client.request(method, _PREFIX + path, json={**body, "binding_type": "computed"})
    absent = client.request(method, _PREFIX + path, json={**body, "template_placeholder_id": str(uuid.uuid4())})
    assert response.status_code == 404
    assert (response.status_code, response.json()) == (absent.status_code, absent.json())
    assert _business_snapshot(pg) == before
