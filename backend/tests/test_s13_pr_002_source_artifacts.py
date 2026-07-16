"""S13-PR-002: workbook adapters + immutable source artifacts."""
from __future__ import annotations

import io
import os
import uuid
import zipfile

import openpyxl
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app as fastapi_app
from app.db import Base, get_db
import app.modules.excel_import.models  # noqa: F401 — register metadata
from app.modules.excel_import.application.adapters import detect_format_and_adapter
from app.modules.excel_import.application.adapters.xlsx_adapter import XlsxWorkbookAdapter
from app.modules.excel_import.application.source_artifact_service import (
    count_staging_rows,
    reconcile_source_artifacts,
)
from app.modules.excel_import.domain.workbook_adapter import AdapterError
from app.modules.excel_import.infrastructure.object_storage import (
    FakeObjectStorage,
    S3ObjectStorage,
    set_object_storage_override,
)
from app.modules.excel_import.models import ImportSourceArtifact
from app.modules.project_master_data.models import (
    OrganizationProfile,
    OrganizationStatus,
    User,
    UserStatus,
    Role,
    UserRole,
    Customer,
    CustomerStatus,
    Project,
    ProjectWorkflowStatus,
    ProjectAssetImportBatch,
    ImportBatchStatus,
    ProjectAssetLine,
    AuditEvent,
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine)
    session = Session(bind=engine)
    try:
        yield session
    finally:
        session.close()
        Base.metadata.drop_all(bind=engine)


@pytest.fixture
def fake_storage():
    store = FakeObjectStorage()
    set_object_storage_override(store)
    yield store
    set_object_storage_override(None)


@pytest.fixture
def client(db_session: Session, fake_storage) -> TestClient:
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    fastapi_app.dependency_overrides[get_db] = override_get_db
    yield TestClient(fastapi_app)
    fastapi_app.dependency_overrides.clear()


def _make_xlsx_bytes() -> bytes:
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Sheet1"
    ws.append(["A", "B", "A"])
    ws.append(["x", None, "y"])
    ws.append([1, 2, 3])
    buf = io.BytesIO()
    wb.save(buf)
    return buf.getvalue()


def test_xlsx_adapter_preserves_blank_and_duplicate_columns(tmp_path):
    p = tmp_path / "t.xlsx"
    p.write_bytes(_make_xlsx_bytes())
    adapter = XlsxWorkbookAdapter()
    insp = adapter.inspect(str(p))
    assert insp.format.value == "xlsx"
    assert "Sheet1" in insp.sheet_names
    rows = list(adapter.iter_rows(str(p)))
    assert len(rows) >= 2
    header = rows[0]
    assert [c.value for c in header[:3]] == ["A", "B", "A"]
    assert header[0].column == 1 and header[2].column == 3


def test_xlsx_rejects_macro_and_extension_mismatch(tmp_path):
    path = tmp_path / "macro.xlsx"
    with zipfile.ZipFile(path, "w") as zf:
        zf.writestr("[Content_Types].xml", "<Types/>")
        zf.writestr("xl/workbook.xml", "<workbook/>")
        zf.writestr("xl/vbaProject.bin", b"vba")
    with pytest.raises(AdapterError) as ei:
        XlsxWorkbookAdapter().inspect(str(path))
    assert ei.value.error_code == "macro_not_allowed"

    bad = tmp_path / "bad.xlsx"
    bad.write_bytes(b"not-a-zip")
    with pytest.raises(AdapterError) as ei2:
        detect_format_and_adapter(str(bad), "bad.xlsx")
    assert ei2.value.error_code == "signature_mismatch"


def test_xls_adapter_roundtrip_if_available(tmp_path):
    pytest.importorskip("xlrd")
    try:
        import xlwt
    except ImportError:
        pytest.skip("xlwt not installed for writing .xls fixtures")
    book = xlwt.Workbook()
    sh = book.add_sheet("S1")
    sh.write(0, 0, "name")
    sh.write(0, 1, "name")
    sh.write(1, 0, "alpha")
    sh.write(1, 1, "")
    path = tmp_path / "t.xls"
    book.save(str(path))
    fmt, adapter = detect_format_and_adapter(str(path), "t.xls")
    assert fmt.value == "xls"
    insp = adapter.inspect(str(path))
    assert insp.sheet_names == ("S1",)
    rows = list(adapter.iter_rows(str(path)))
    assert rows[0][0].value == "name"
    assert rows[0][1].value == "name"
    assert rows[0][0].column != rows[0][1].column


def _seed(db: Session):
    org = OrganizationProfile(
        legal_name="Org 1", organization_slug=f"org-{uuid.uuid4().hex[:6]}", status=OrganizationStatus.ACTIVE
    )
    org_other = OrganizationProfile(
        legal_name="Org 2", organization_slug=f"org-{uuid.uuid4().hex[:6]}", status=OrganizationStatus.ACTIVE
    )
    db.add_all([org, org_other])
    db.commit()
    role_editor = Role(code="editor", display_name="Editor", permissions=["project:read", "workbench:edit"])
    db.add(role_editor)
    db.commit()
    user = User(
        organization_id=org.id,
        email=f"e{uuid.uuid4().hex[:8]}@example.com",
        full_name="Editor",
        status=UserStatus.ACTIVE,
    )
    user_other = User(
        organization_id=org_other.id,
        email=f"o{uuid.uuid4().hex[:8]}@example.com",
        full_name="Other",
        status=UserStatus.ACTIVE,
    )
    db.add_all([user, user_other])
    db.commit()
    db.add_all(
        [
            UserRole(user_id=user.id, role_id=role_editor.id, is_active=True),
            UserRole(user_id=user_other.id, role_id=role_editor.id, is_active=True),
        ]
    )
    db.commit()
    cust = Customer(
        organization_id=org.id,
        legal_name="Customer 1",
        status=CustomerStatus.ACTIVE,
        created_by=user.id,
    )
    db.add(cust)
    db.commit()
    proj = Project(
        organization_id=org.id,
        customer_id=cust.id,
        name="P1",
        code=f"P{uuid.uuid4().hex[:6]}",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=user.id,
    )
    db.add(proj)
    db.commit()
    batch = ProjectAssetImportBatch(
        organization_id=org.id,
        project_id=proj.id,
        source_filename="seed.xlsx",
        status=ImportBatchStatus.CREATED,
        created_by_user_id=user.id,
    )
    db.add(batch)
    db.commit()
    return org, user, user_other, proj, batch


def test_source_artifact_upload_available_and_no_staging(client: TestClient, db_session: Session, fake_storage):
    org, user, _u2, proj, batch = _seed(db_session)
    headers = {"X-User-Id": str(user.id)}
    data = _make_xlsx_bytes()
    before_staging = count_staging_rows(db_session, batch.id)
    before_lines = db_session.query(ProjectAssetLine).filter(ProjectAssetLine.project_id == proj.id).count()

    res = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={
            "file": (
                "src.xlsx",
                io.BytesIO(data),
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        },
        headers=headers,
    )
    assert res.status_code == 201, res.text
    body = res.json()
    assert body["state"] == "available"
    assert body["generation"] == 1
    assert body["detected_format"] == "xlsx"
    assert len(body["checksum_sha256"]) == 64
    assert "storage_object_key" not in body

    db_session.refresh(batch)
    assert str(batch.current_source_artifact_id) == body["id"]
    assert count_staging_rows(db_session, batch.id) == before_staging
    assert db_session.query(ProjectAssetLine).filter(ProjectAssetLine.project_id == proj.id).count() == before_lines

    art_id = uuid.UUID(body["id"])
    art = db_session.query(ImportSourceArtifact).filter(ImportSourceArtifact.id == art_id).one()
    assert fake_storage.head(art.storage_object_key) is not None
    ev = (
        db_session.query(AuditEvent)
        .filter(AuditEvent.event_name == "ImportSourceArtifactAvailable", AuditEvent.entity_id == art_id)
        .first()
    )
    assert ev is not None


def test_s12_upload_rejects_xls(client: TestClient, db_session: Session, fake_storage):
    org, user, _u2, proj, batch = _seed(db_session)
    res = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/upload",
        files={"file": ("legacy.xls", io.BytesIO(b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1xxxx"), "application/vnd.ms-excel")},
        headers={"X-User-Id": str(user.id)},
    )
    assert res.status_code == 400


def test_failure_keeps_prior_current(client: TestClient, db_session: Session, fake_storage):
    org, user, _u2, proj, batch = _seed(db_session)
    headers = {"X-User-Id": str(user.id)}
    data = _make_xlsx_bytes()
    r1 = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": ("a.xlsx", io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert r1.status_code == 201
    first_id = r1.json()["id"]
    fake_storage.fail_put = True
    r2 = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": ("b.xlsx", io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert r2.status_code == 500
    db_session.refresh(batch)
    assert str(batch.current_source_artifact_id) == first_id


def test_cross_tenant_denied(client: TestClient, db_session: Session, fake_storage):
    org, user, user_other, proj, batch = _seed(db_session)
    data = _make_xlsx_bytes()
    res = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": ("a.xlsx", io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers={"X-User-Id": str(user_other.id)},
    )
    assert res.status_code == 404


def test_list_and_get_metadata(client: TestClient, db_session: Session, fake_storage):
    org, user, _u2, proj, batch = _seed(db_session)
    headers = {"X-User-Id": str(user.id)}
    data = _make_xlsx_bytes()
    r1 = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": ("a.xlsx", io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert r1.status_code == 201
    aid = r1.json()["id"]
    lst = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        headers=headers,
    )
    assert lst.status_code == 200
    assert len(lst.json()) == 1
    one = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts/{aid}",
        headers=headers,
    )
    assert one.status_code == 200
    assert "storage_object_key" not in one.json()


def test_reconciler_skips_current(client: TestClient, db_session: Session, fake_storage):
    org, user, _u2, proj, batch = _seed(db_session)
    headers = {"X-User-Id": str(user.id)}
    data = _make_xlsx_bytes()
    r1 = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch.id}/source-artifacts",
        files={"file": ("a.xlsx", io.BytesIO(data), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")},
        headers=headers,
    )
    assert r1.status_code == 201
    stats = reconcile_source_artifacts(db_session, storage=fake_storage, max_items=10, actor_id=user.id)
    assert "scanned" in stats
    db_session.refresh(batch)
    art = db_session.get(ImportSourceArtifact, batch.current_source_artifact_id)
    assert fake_storage.head(art.storage_object_key) is not None


def test_s3_integration_when_configured():
    if os.environ.get("CI") == "true":
        endpoint = os.environ.get("S3_ENDPOINT_URL")
        assert endpoint, "CI must provide S3_ENDPOINT_URL for MinIO"
    else:
        endpoint = os.environ.get("S3_ENDPOINT_URL")
        if not endpoint:
            pytest.skip("S3_ENDPOINT_URL not set for local MinIO integration")

    store = S3ObjectStorage(
        endpoint_url=endpoint,
        access_key=os.environ.get("S3_ACCESS_KEY_ID", "valora"),
        secret_key=os.environ.get("S3_SECRET_ACCESS_KEY", "valora_local_password"),
        bucket=os.environ.get("S3_BUCKET", "valora-local"),
        region=os.environ.get("S3_REGION", "us-east-1"),
    )
    store.ensure_bucket()
    key = f"integration/{uuid.uuid4()}"
    payload = b"hello-valora-s13"
    st = store.put_stream(
        key, io.BytesIO(payload), content_type="application/octet-stream", expected_size=len(payload)
    )
    assert st.size == len(payload)
    assert store.head(key).size == len(payload)
    assert store.open_stream(key).read() == payload
    store.delete(key)
    assert store.head(key) is None
