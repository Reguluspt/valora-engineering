"""Bounded real-stack Pre-case tenant, RBAC, and closed-state checks."""

import json
import os
import pathlib
import sys
import uuid

from playwright.sync_api import sync_playwright


BASE = "http://localhost"
API = "/api/v1"
PROJECT_CODE = os.getenv("G11K_PROJECT_CODE", "G11K-E2E-20261001-001")
NEGATIVE_CODE = "G11K-NEGATIVE-20261001-001"
EVIDENCE = pathlib.Path(__file__).resolve().parents[2] / "docs" / "implementation"
OUTCOMES: list[dict[str, object]] = []


def login(playwright, slug: str, email: str):
    client = playwright.request.new_context(base_url=BASE)
    response = client.post(f"{API}/auth/login", data={
        "organization_slug": slug, "email": email,
        "password": os.environ["G11K_SYNTHETIC_PASSWORD"],
    })
    assert response.status == 200, (email, response.status, response.text())
    account = client.get(f"{API}/auth/me")
    assert account.status == 200, (email, account.status)
    csrf = next(cookie["value"] for cookie in client.storage_state()["cookies"] if cookie["name"] == "XSRF-TOKEN")
    return client, account.json(), {"X-CSRF-Token": csrf, "Origin": BASE}


def checked(label: str, response, expected: tuple[int, ...]):
    print(label, response.status, response.text()[:500])
    assert response.status in expected, (label, response.status, response.text())
    OUTCOMES.append({"check": label, "status": response.status})


def main():
    with sync_playwright() as playwright:
        owner, owner_account, owner_csrf = login(playwright, "g11k-synthetic-main", "owner@g11k.invalid")
        viewer, viewer_account, viewer_csrf = login(playwright, "g11k-synthetic-main", "viewer@g11k.invalid")
        other, other_account, other_csrf = login(playwright, "g11k-synthetic-other", "appraiser@g11k.invalid")
        print("ACTORS", json.dumps({
            "owner": {"roles": owner_account["roles"], "permissions": owner_account["permissions"]},
            "viewer": {"roles": viewer_account["roles"], "permissions": viewer_account["permissions"]},
            "other": {"roles": other_account["roles"], "permissions": other_account["permissions"]},
        }, ensure_ascii=False, sort_keys=True))
        assert owner_account["roles"] == ["owner"]
        assert viewer_account["roles"] == ["viewer"]
        assert other_account["roles"] == ["appraiser"]
        needed = {"workbench:edit", "project:preliminary_analysis:finalize",
                  "project:preliminary_result:generate", "project:official_intake:commit"}
        assert needed <= set(owner_account["permissions"])
        assert needed <= set(other_account["permissions"])
        assert not needed & set(viewer_account["permissions"])

        resolution = owner.get(f"{API}/projects/resolve?ref={PROJECT_CODE}")
        assert resolution.status == 200
        project_id = resolution.json()["project_id"]
        case = owner.get(f"{API}/projects/{project_id}/case-state").json()
        prelim = case["preliminary"]
        assert prelim["official_intake_commit_id"]
        batch_id = prelim["current_preliminary_import_batch_id"]
        source_id = prelim["current_source_artifact_id"]
        analysis_id = prelim["current_preliminary_analysis_snapshot_id"]
        result_id = prelim["current_preliminary_result_artifact_id"]
        customer_id = prelim["customer_id"]
        assert all((batch_id, source_id, analysis_id, result_id, customer_id))

        checked("VIEWER_BATCH_DENIED", viewer.post(f"{API}/projects/{project_id}/asset-imports",
                data={"source_filename": "not-created.xlsx", "source_sheet_name": None}, headers=viewer_csrf), (403,))
        checked("VIEWER_RESULT_DENIED", viewer.post(f"{API}/projects/{project_id}/preliminary-results",
                data={"preliminary_analysis_snapshot_id": analysis_id, "expected_project_version": prelim["project_row_version"],
                      "idempotency_key": "g11k-viewer-result-denied", "confirmed": True}, headers=viewer_csrf), (403,))
        checked("VIEWER_INTAKE_DENIED", viewer.post(f"{API}/projects/{project_id}/official-intake",
                data={"preliminary_result_artifact_id": result_id, "expected_project_version": prelim["project_row_version"],
                      "expected_preliminary_result_version": prelim["current_preliminary_result_version"],
                      "idempotency_key": "g11k-viewer-intake-denied", "confirmed": True}, headers=viewer_csrf), (403,))

        reads = {
            "PROJECT": f"{API}/projects/{project_id}",
            "CASE_STATE": f"{API}/projects/{project_id}/case-state",
            "BATCH": f"{API}/projects/{project_id}/asset-imports",
            "SOURCE": f"{API}/projects/{project_id}/asset-imports/{batch_id}/source-artifacts/{source_id}",
            "MAPPING": f"{API}/projects/{project_id}/asset-imports/{batch_id}/column-mapping/state",
            "ANALYSIS": f"{API}/projects/{project_id}/preliminary-analyses/{analysis_id}",
            "RESULT": f"{API}/projects/{project_id}/preliminary-results/{result_id}",
            "RESULT_CONTENT": f"{API}/projects/{project_id}/preliminary-results/{result_id}/content",
            "CUSTOMER": f"{API}/master-data/customers/{customer_id}",
        }
        for name, path in reads.items():
            checked(f"CROSS_TENANT_{name}", other.get(path), (404,))
        checked("CROSS_TENANT_BATCH_MUTATION", other.post(f"{API}/projects/{project_id}/asset-imports",
                data={"source_filename": "not-created.xlsx", "source_sheet_name": None}, headers=other_csrf), (404,))
        checked("CROSS_TENANT_RESULT_MUTATION", other.post(f"{API}/projects/{project_id}/preliminary-results",
                data={"preliminary_analysis_snapshot_id": analysis_id, "expected_project_version": prelim["project_row_version"],
                      "idempotency_key": "g11k-other-result-denied", "confirmed": True}, headers=other_csrf), (404,))
        checked("CROSS_TENANT_INTAKE_MUTATION", other.post(f"{API}/projects/{project_id}/official-intake",
                data={"preliminary_result_artifact_id": result_id, "expected_project_version": prelim["project_row_version"],
                      "expected_preliminary_result_version": prelim["current_preliminary_result_version"],
                      "idempotency_key": "g11k-other-intake-denied", "confirmed": True}, headers=other_csrf), (404,))

        checked("POST_INTAKE_RESULT_CLOSED", owner.post(f"{API}/projects/{project_id}/preliminary-results",
                data={"preliminary_analysis_snapshot_id": analysis_id, "expected_project_version": prelim["project_row_version"],
                      "idempotency_key": "g11k-new-result-after-intake", "confirmed": True}, headers=owner_csrf), (409,))
        source_before = prelim["current_source_artifact_id"]
        workbook = pathlib.Path(__file__).parent / "fixtures" / "g11k_synthetic_assets.xlsx"
        source_upload = owner.post(
            f"{API}/projects/{project_id}/asset-imports/{batch_id}/source-artifacts",
            multipart={"file": {
                "name": workbook.name,
                "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "buffer": workbook.read_bytes(),
            }},
            headers=owner_csrf,
        )
        checked("POST_INTAKE_SOURCE_CLOSED", source_upload, (409,))
        assert source_upload.json()["detail"]["error_code"] == "source_official_intake_closed"
        after_source = owner.get(f"{API}/projects/{project_id}/case-state").json()["preliminary"]
        assert after_source["current_source_artifact_id"] == source_before
        assert after_source["official_intake_commit_id"] == prelim["official_intake_commit_id"]
        negative = owner.get(f"{API}/projects/resolve?ref={NEGATIVE_CODE}")
        if negative.status == 404:
            created = owner.post(f"{API}/projects", data={
                "code": NEGATIVE_CODE, "name": "Yêu cầu tổng hợp để kiểm tra trạng thái thiếu dữ liệu",
                "description": "G1.1K negative boundary only", "customer_id": None,
            }, headers=owner_csrf)
            checked("NEGATIVE_PROJECT_CREATE", created, (201,))
            negative_id = created.json()["id"]
        else:
            assert negative.status == 200
            negative_id = negative.json()["project_id"]
        negative_case = owner.get(f"{API}/projects/{negative_id}/case-state").json()
        assert negative_case["preliminary"]["current_preliminary_analysis_snapshot_id"] is None
        assert negative_case["preliminary"]["current_preliminary_result_artifact_id"] is None
        assert negative_case["preliminary"]["customer_id"] is None
        checked("NO_ANALYSIS_RESULT_DENIED", owner.post(f"{API}/projects/{negative_id}/preliminary-results",
                data={"preliminary_analysis_snapshot_id": str(uuid.uuid4()),
                      "expected_project_version": negative_case["preliminary"]["project_row_version"],
                      "idempotency_key": "g11k-no-analysis-result", "confirmed": True}, headers=owner_csrf), (404, 409))
        checked("NO_RESULT_INTAKE_DENIED", owner.post(f"{API}/projects/{negative_id}/official-intake",
                data={"preliminary_result_artifact_id": str(uuid.uuid4()),
                      "expected_preliminary_result_version": 1,
                      "expected_project_version": negative_case["preliminary"]["project_row_version"],
                      "idempotency_key": "g11k-no-result-intake", "confirmed": True}, headers=owner_csrf), (404, 409))
        assert owner.get(f"{API}/projects/{negative_id}/case-state").json()["preliminary"]["official_intake_commit_id"] is None
        assert owner.get(f"{API}/projects/{project_id}/case-state").json()["preliminary"]["official_intake_commit_id"] == prelim["official_intake_commit_id"]
        (EVIDENCE / "g11k-negative-evidence.json").write_text(json.dumps({
            "project_id": project_id,
            "negative_project_id": negative_id,
            "actors": {
                "owner": {"roles": owner_account["roles"], "permissions": owner_account["permissions"]},
                "viewer": {"roles": viewer_account["roles"], "permissions": viewer_account["permissions"]},
                "other_tenant_appraiser": {"roles": other_account["roles"],
                                           "permissions": other_account["permissions"]},
            },
            "outcomes": OUTCOMES,
            "post_intake_source_pointer_unchanged": after_source["current_source_artifact_id"] == source_before,
            "post_intake_commit_unchanged": after_source["official_intake_commit_id"] == prelim["official_intake_commit_id"],
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("NEGATIVE_MATRIX_PASS", project_id, negative_id)
        owner.dispose()
        viewer.dispose()
        other.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
