"""Read one exact immutable Preliminary Analysis fact by Project and ID."""

import uuid

from tests.test_g11e_precase_api import _headers, _url
from tests.test_pr01_preliminary_result_service import _seed as seed_result
from app.modules.project_master_data.models import ProjectAssetImportStagingRow

pytest_plugins = ("tests.test_g11e_precase_api",)


def test_read_exact_analysis_manifest_with_project_read(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="g11i-read")
    seeded["role"].permissions = ["project:read"]
    db.commit()

    response = client.get(
        _url(seeded, f"preliminary-analyses/{seeded['snapshot'].id}"),
        headers=_headers(seeded),
    )

    assert response.status_code == 200, response.text
    assert response.json() == {
        "id": str(seeded["snapshot"].id),
        "project_id": str(seeded["project"].id),
        "version": seeded["snapshot"].version,
        "import_batch_id": str(seeded["batch"].id),
        "source_artifact_id": str(seeded["artifact"].id),
        "structure_snapshot_id": str(seeded["structure"].id),
        "mapping_decision_id": str(seeded["decision"].id),
        "mapping_profile_usage_id": str(seeded["usage"].id),
        "mapping_decision_digest_sha256": seeded["snapshot"].mapping_decision_digest_sha256,
        "profile_usage_mapping_digest_sha256": seeded["snapshot"].profile_usage_mapping_digest_sha256,
        "line_manifest": seeded["snapshot"].line_manifest,
        "line_manifest_digest_sha256": seeded["snapshot"].line_manifest_digest_sha256,
        "finalized_by_user_id": str(seeded["snapshot"].finalized_by_user_id),
        "finalized_at": seeded["snapshot"].finalized_at.isoformat().replace("+00:00", "Z"),
    }


def test_read_analysis_denies_other_project_tenant_missing_and_unprivileged(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="g11i-scope")
    other = seed_result(db, suffix="g11i-other")
    seeded["role"].permissions = ["project:read"]
    other["role"].permissions = ["project:read"]
    db.commit()
    exact = _url(seeded, f"preliminary-analyses/{seeded['snapshot'].id}")

    assert client.get(exact, headers=_headers(seeded)).status_code == 200
    assert client.get(exact, headers=_headers(other)).status_code == 404
    assert client.get(
        _url(other, f"preliminary-analyses/{seeded['snapshot'].id}"),
        headers=_headers(other),
    ).status_code == 404
    assert client.get(
        _url(seeded, f"preliminary-analyses/{uuid.uuid4()}"),
        headers=_headers(seeded),
    ).status_code == 404
    seeded["role"].permissions = []
    db.commit()
    assert client.get(exact, headers=_headers(seeded)).status_code == 403


def test_staging_row_pages_keep_source_order_and_provenance(api_db):
    client, db = api_db
    seeded = seed_result(db, suffix="g11i-rows")
    seeded["role"].permissions = ["project:read"]
    for number in (12, 10, 11):
        db.add(ProjectAssetImportStagingRow(
            organization_id=seeded["org"].id,
            project_id=seeded["project"].id,
            import_batch_id=seeded["batch"].id,
            source_row_number=number,
            proposed_asset_name=f"Thiết bị {number}",
            proposed_quantity=str(number),
        ))
    db.commit()
    url = _url(seeded, f"asset-imports/{seeded['batch'].id}/rows")

    first = client.get(f"{url}?limit=2&offset=0", headers=_headers(seeded))
    second = client.get(f"{url}?limit=2&offset=2", headers=_headers(seeded))

    assert first.status_code == second.status_code == 200
    assert first.json()["total"] == second.json()["total"] == 3
    items = first.json()["items"] + second.json()["items"]
    assert [(item["source_row_number"], item["proposed_quantity"]) for item in items] == [
        (10, "10"), (11, "11"), (12, "12"),
    ]
