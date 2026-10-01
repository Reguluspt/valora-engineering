"""Exact, tenant-scoped Preliminary Result read and download contracts."""

from __future__ import annotations

import hashlib
import io
import uuid
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.db import Base, get_db
from app.main import app
from app.modules.excel_import.infrastructure.object_storage import FakeObjectStorage
from app.modules.project_master_data.models import (
    Customer, CustomerStatus, OrganizationProfile, OrganizationStatus,
    PreliminaryResultArtifact, Project, Role, User, UserRole, UserStatus,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine("sqlite:///:memory:", connect_args={"check_same_thread": False}, poolclass=StaticPool)
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def client(db_session: Session) -> TestClient:
    def override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = override_get_db
    try:
        yield TestClient(app)
    finally:
        app.dependency_overrides.pop(get_db, None)


def _seed(db: Session, permissions: list[str] | None = None) -> tuple[User, Project, Customer]:
    suffix = uuid.uuid4().hex[:8]
    org = OrganizationProfile(legal_name=f"Result Org {suffix}", organization_slug=f"result-{suffix}", status=OrganizationStatus.ACTIVE)
    db.add(org)
    db.flush()
    user = User(organization_id=org.id, email=f"result-{suffix}@example.com", full_name="Result Reader", status=UserStatus.ACTIVE)
    db.add(user)
    db.flush()
    role = Role(code=f"result-{suffix}", display_name="Result Reader", permissions=permissions if permissions is not None else ["project:read", "master_data:customer:read"])
    db.add(role)
    db.flush()
    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
    customer = Customer(organization_id=org.id, legal_name=f"Customer {suffix}", contact_phone="0900123456", status=CustomerStatus.ACTIVE, created_by=user.id)
    db.add(customer)
    db.flush()
    project = Project(organization_id=org.id, customer_id=customer.id, code=f"RES-{suffix}", name="Result Project", created_by=user.id)
    db.add(project)
    db.commit()
    return user, project, customer


def _artifact(db: Session, user: User, project: Project, storage: FakeObjectStorage, version: int, content: bytes) -> PreliminaryResultArtifact:
    artifact_id = uuid.uuid4()
    key = f"org/{project.organization_id}/project/{project.id}/preliminary-results/{artifact_id}.xlsx"
    digest = hashlib.sha256(content).hexdigest()
    storage.put_stream(key, io.BytesIO(content), content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", expected_size=len(content))
    artifact = PreliminaryResultArtifact(
        id=artifact_id, organization_id=project.organization_id, customer_id=project.customer_id,
        project_id=project.id, version=version, original_filename=f"result-{version}.xlsx",
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        file_size_bytes=len(content), content_checksum_sha256=digest, storage_object_key=key,
        source_snapshot_sha256="a" * 64, lineage_manifest={"analysis_snapshot": {"id": str(uuid.uuid4()), "version": version}},
        created_by_user_id=user.id,
    )
    db.add(artifact)
    db.commit()
    return artifact


def test_exact_result_metadata_and_download_do_not_select_latest_or_leak_storage(client: TestClient, db_session: Session) -> None:
    user, project, _ = _seed(db_session)
    project.customer_id = None
    db_session.commit()
    storage = FakeObjectStorage()
    old = _artifact(db_session, user, project, storage, 1, b"old-xlsx")
    _artifact(db_session, user, project, storage, 2, b"new-xlsx")
    headers = {"X-User-Id": str(user.id)}
    path = f"/api/v1/projects/{project.id}/preliminary-results/{old.id}"
    with patch("app.api.projects.get_object_storage", return_value=storage):
        metadata = client.get(path, headers=headers)
        download = client.get(path + "/content", headers=headers)
    assert metadata.status_code == 200
    assert metadata.json()["id"] == str(old.id)
    assert metadata.json()["version"] == 1
    assert metadata.json()["content_checksum_sha256"] == old.content_checksum_sha256
    assert "storage_object_key" not in metadata.json()
    assert "lineage_manifest" not in metadata.json()
    assert download.status_code == 200
    assert download.content == b"old-xlsx"
    assert download.headers["content-type"] == old.content_type
    assert download.headers["content-disposition"] == 'attachment; filename="ket-qua-so-bo-v1.xlsx"'
    assert download.headers["x-content-type-options"] == "nosniff"


def test_result_reads_fail_closed_for_auth_tenant_project_and_missing_object(client: TestClient, db_session: Session) -> None:
    user, project, _ = _seed(db_session)
    other_user, other_project, _ = _seed(db_session)
    no_read_user, _, _ = _seed(db_session, permissions=[])
    storage = FakeObjectStorage()
    artifact = _artifact(db_session, user, project, storage, 1, b"exact-content")
    path = f"/api/v1/projects/{project.id}/preliminary-results/{artifact.id}"
    assert client.get(path).status_code == 401
    assert client.get(path, headers={"X-User-Id": str(no_read_user.id)}).status_code == 403
    assert client.get(path, headers={"X-User-Id": str(other_user.id)}).status_code == 404
    headers = {"X-User-Id": str(user.id)}
    assert client.get(f"/api/v1/projects/{other_project.id}/preliminary-results/{artifact.id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/projects/{project.id}/preliminary-results/{uuid.uuid4()}", headers=headers).status_code == 404
    with patch("app.api.projects.get_object_storage", return_value=storage):
        storage.delete(artifact.storage_object_key)
        unavailable = client.get(path + "/content", headers=headers)
    assert unavailable.status_code == 503
    assert artifact.storage_object_key not in unavailable.text


def test_result_download_rejects_corrupt_content_and_customer_search_uses_phone(client: TestClient, db_session: Session) -> None:
    user, project, customer = _seed(db_session)
    storage = FakeObjectStorage()
    artifact = _artifact(db_session, user, project, storage, 1, b"original")
    storage._objects[artifact.storage_object_key] = b"modified"
    headers = {"X-User-Id": str(user.id)}
    with patch("app.api.projects.get_object_storage", return_value=storage):
        response = client.get(f"/api/v1/projects/{project.id}/preliminary-results/{artifact.id}/content", headers=headers)
    assert response.status_code == 503
    found = client.get("/api/v1/master-data/customers?q=0900123456&status=active", headers=headers)
    assert found.status_code == 200
    assert any(item["id"] == str(customer.id) for item in found.json())


def test_bound_customer_exact_read_is_tenant_scoped(client: TestClient, db_session: Session) -> None:
    user, _, customer = _seed(db_session)
    foreign_user, _, foreign_customer = _seed(db_session)
    headers = {"X-User-Id": str(user.id)}
    exact = client.get(f"/api/v1/master-data/customers/{customer.id}", headers=headers)
    assert exact.status_code == 200
    assert exact.json()["legal_name"] == customer.legal_name
    assert client.get(f"/api/v1/master-data/customers/{foreign_customer.id}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/master-data/customers/{customer.id}", headers={"X-User-Id": str(foreign_user.id)}).status_code == 404
