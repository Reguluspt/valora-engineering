import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.db import Base, get_db
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
    ProjectAssetLine,
    ProjectAssetImportBatch,
    ProjectAssetImportStagingRow,
    ImportBatchStatus,
    ImportRowValidationStatus
)


@pytest.fixture
def db_session() -> Session:
    engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool
    )
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
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    yield TestClient(app)
    app.dependency_overrides.clear()


def test_excel_import_staging_flow(client: TestClient, db_session: Session) -> None:
    # 1. Seed tenant, users, and roles
    org = OrganizationProfile(legal_name="Org 1", organization_slug="org-1", status=OrganizationStatus.ACTIVE)
    org_other = OrganizationProfile(legal_name="Org 2", organization_slug="org-2", status=OrganizationStatus.ACTIVE)
    db_session.add_all([org, org_other])
    db_session.commit()

    role_editor = Role(
        code="editor",
        display_name="Editor",
        permissions=["project:read", "workbench:edit"]
    )
    role_viewer = Role(
        code="viewer",
        display_name="Viewer",
        permissions=["project:read"]
    )
    db_session.add_all([role_editor, role_viewer])
    db_session.commit()

    user_editor = User(organization_id=org.id, email="editor@org1.com", full_name="Editor", status=UserStatus.ACTIVE)
    user_viewer = User(organization_id=org.id, email="viewer@org1.com", full_name="Viewer", status=UserStatus.ACTIVE)
    user_other = User(organization_id=org_other.id, email="other@org2.com", full_name="Other", status=UserStatus.ACTIVE)
    db_session.add_all([user_editor, user_viewer, user_other])
    db_session.commit()

    db_session.add_all([
        UserRole(user_id=user_editor.id, role_id=role_editor.id, is_active=True),
        UserRole(user_id=user_viewer.id, role_id=role_viewer.id, is_active=True),
        UserRole(user_id=user_other.id, role_id=role_editor.id, is_active=True),  # Editor in Org 2
    ])
    db_session.commit()

    # Seed active customer
    cust = Customer(
        organization_id=org.id,
        legal_name="Customer 1",
        status=CustomerStatus.ACTIVE,
        created_by=user_editor.id
    )
    cust_other = Customer(
        organization_id=org_other.id,
        legal_name="Customer 2",
        status=CustomerStatus.ACTIVE,
        created_by=user_other.id
    )
    db_session.add_all([cust, cust_other])
    db_session.commit()

    # Seed projects
    proj = Project(
        organization_id=org.id,
        customer_id=cust.id,
        code="PROJ-01",
        name="Project 1",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=user_editor.id
    )
    proj_other = Project(
        organization_id=org_other.id,
        customer_id=cust_other.id,
        code="PROJ-OTHER",
        name="Project Other",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=user_other.id
    )
    db_session.add_all([proj, proj_other])
    db_session.commit()

    headers_editor = {"X-User-Id": str(user_editor.id)}
    headers_viewer = {"X-User-Id": str(user_viewer.id)}
    headers_other = {"X-User-Id": str(user_other.id)}

    # Test A: Create Import Batch (authorized editor)
    payload = {
        "source_filename": "assets.xlsx",
        "source_sheet_name": "ValuationSheet"
    }
    res = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports",
        json=payload,
        headers=headers_editor
    )
    assert res.status_code == 201
    data = res.json()
    assert data["source_filename"] == "assets.xlsx"
    assert data["source_sheet_name"] == "ValuationSheet"
    assert data["status"] == "created"
    batch_id = data["id"]

    # Verify ProjectAssetLine rows were NOT created
    assert db_session.query(ProjectAssetLine).count() == 0

    # Test B: Create Batch permission check (viewer has project:read but lacks workbench:edit)
    res_viewer = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports",
        json=payload,
        headers=headers_viewer
    )
    assert res_viewer.status_code == 403

    # Test C: Create Batch multi-tenant check (user_other is in org_other, proj is in org)
    res_other = client.post(
        f"/api/v1/projects/{proj.id}/asset-imports",
        json=payload,
        headers=headers_other
    )
    assert res_other.status_code == 404

    # Test D: List Import Batches (authorized viewer)
    res_list = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports",
        headers=headers_viewer
    )
    assert res_list.status_code == 200
    batches_data = res_list.json()
    assert len(batches_data) == 1
    assert batches_data[0]["id"] == batch_id

    # Test E: List Staging Rows - Empty
    res_rows_empty = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch_id}/rows",
        headers=headers_viewer
    )
    assert res_rows_empty.status_code == 200
    rows_data = res_rows_empty.json()
    assert rows_data["total"] == 0
    assert len(rows_data["items"]) == 0

    # Seed staging rows manually for validation checks
    row1 = ProjectAssetImportStagingRow(
        organization_id=org.id,
        project_id=proj.id,
        import_batch_id=uuid.UUID(batch_id),
        source_row_number=1,
        raw_values={"A": "Tài sản A", "B": "10"},
        mapped_values={"asset_name": "Tài sản A"},
        normalized_preview={},
        validation_status=ImportRowValidationStatus.VALID,
        proposed_asset_name="Tài sản A",
        proposed_quantity="10"
    )
    row2 = ProjectAssetImportStagingRow(
        organization_id=org.id,
        project_id=proj.id,
        import_batch_id=uuid.UUID(batch_id),
        source_row_number=2,
        raw_values={"A": "Tài sản B", "B": "invalid_qty"},
        mapped_values={},
        normalized_preview={},
        validation_status=ImportRowValidationStatus.INVALID,
        validation_errors=[{"field": "proposed_quantity", "message_key": "excel.validation.invalid_number"}],
        proposed_asset_name="Tài sản B",
        proposed_quantity="invalid_qty"
    )
    db_session.add_all([row1, row2])
    db_session.commit()

    # Test F: List Staging Rows - Seeded
    res_rows = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch_id}/rows",
        headers=headers_viewer
    )
    assert res_rows.status_code == 200
    rows_data = res_rows.json()
    assert rows_data["total"] == 2
    assert len(rows_data["items"]) == 2

    # Test G: List Staging Rows - Filter by validation_status
    res_rows_filter = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch_id}/rows?validation_status=invalid",
        headers=headers_viewer
    )
    assert res_rows_filter.status_code == 200
    filter_data = res_rows_filter.json()
    assert filter_data["total"] == 1
    assert filter_data["items"][0]["proposed_asset_name"] == "Tài sản B"
    assert filter_data["items"][0]["validation_errors"][0]["field"] == "proposed_quantity"

    # Test H: List Staging Rows - Cross-org blocked
    res_rows_other = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports/{batch_id}/rows",
        headers=headers_other
    )
    assert res_rows_other.status_code == 404

    # Test I: Cross-org project listing batches is blocked
    res_list_other = client.get(
        f"/api/v1/projects/{proj.id}/asset-imports",
        headers=headers_other
    )
    assert res_list_other.status_code == 404

    # Test J: Batch outside project lookup is blocked
    res_bad_project = client.get(
        f"/api/v1/projects/{proj_other.id}/asset-imports/{batch_id}/rows",
        headers=headers_other
    )
    assert res_bad_project.status_code == 404

    # Verify no ProjectAssetLine rows were mutated
    assert db_session.query(ProjectAssetLine).count() == 0
