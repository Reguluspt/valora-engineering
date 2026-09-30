"""Read-only preliminary-request management from existing authority facts."""

import uuid

from app.modules.project_master_data.models import (
    ImportBatchStatus,
    OrganizationProfile,
    OrganizationStatus,
    Project,
    ProjectAssetImportBatch,
    ProjectWorkflowStatus,
    User,
    UserStatus,
)
from tests.test_g11g_column_mapping_api import _api_seed

pytest_plugins = ("tests.test_g11g_column_mapping_api",)


def test_management_is_tenant_scoped_and_uses_explicit_batch_facts(api_client, mapping_db):
    seeded = _api_seed(mapping_db)
    org = seeded["org"]
    actor = seeded["user"]
    current = seeded["project"]
    no_batch = Project(
        organization_id=org.id,
        customer_id=None,
        name="New preliminary request",
        code="G11H-NEW",
        status=ProjectWorkflowStatus.APPROVED,
        created_by=actor.id,
    )
    unresolved = Project(
        organization_id=org.id,
        customer_id=None,
        name="Retained batch without authority",
        code="G11H-UNRESOLVED",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=actor.id,
    )
    other_org = OrganizationProfile(
        legal_name="Other G11H Org",
        organization_slug=f"other-g11h-{uuid.uuid4().hex[:8]}",
        status=OrganizationStatus.ACTIVE,
    )
    mapping_db.add_all([no_batch, unresolved, other_org])
    mapping_db.flush()
    mapping_db.add(ProjectAssetImportBatch(
        organization_id=org.id,
        project_id=unresolved.id,
        source_filename="retained.xlsx",
        status=ImportBatchStatus.CREATED,
        created_by_user_id=actor.id,
    ))
    other_user = User(
        organization_id=other_org.id,
        email=f"other-g11h-{uuid.uuid4().hex[:8]}@example.com",
        full_name="Other tenant user",
        status=UserStatus.ACTIVE,
    )
    no_role_user = User(
        organization_id=org.id,
        email=f"no-role-g11h-{uuid.uuid4().hex[:8]}@example.com",
        full_name="No read permission",
        status=UserStatus.ACTIVE,
    )
    mapping_db.add_all([other_user, no_role_user])
    mapping_db.flush()
    mapping_db.add(Project(
        organization_id=other_org.id,
        customer_id=None,
        name="Other tenant project",
        code="G11H-OTHER",
        status=ProjectWorkflowStatus.DRAFT,
        created_by=other_user.id,
    ))
    mapping_db.commit()

    url = "/api/v1/projects/preliminary-requests"
    headers = {"X-User-Id": str(actor.id)}
    first = api_client.get(f"{url}?page=1&page_size=2", headers=headers)
    second = api_client.get(f"{url}?page=2&page_size=2", headers=headers)
    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == second.json()["total"] == 3
    rows = {item["project_id"]: item for item in first.json()["items"] + second.json()["items"]}
    assert set(rows) == {str(current.id), str(no_batch.id), str(unresolved.id)}
    assert rows[str(current.id)]["current_batch_id"] == str(seeded["batch"].id)
    assert rows[str(current.id)]["current_source_artifact_id"] == str(seeded["artifact"].id)
    assert rows[str(current.id)]["current_source_state"] == "available"
    assert rows[str(no_batch.id)]["current_batch_id"] is None
    assert rows[str(no_batch.id)]["has_retained_batches"] is False
    assert rows[str(unresolved.id)]["current_batch_id"] is None
    assert rows[str(unresolved.id)]["has_retained_batches"] is True
    assert api_client.get(url, headers={"X-User-Id": str(no_role_user.id)}).status_code == 403
