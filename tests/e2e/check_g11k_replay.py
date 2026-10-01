"""Replay the exact recorded North-star commands against the real stack."""

import json
import os
import sys
from pathlib import Path

from playwright.sync_api import sync_playwright


EVIDENCE = Path(__file__).resolve().parents[2] / "docs" / "implementation"
BASE = "http://localhost"
API = "/api/v1"


def main():
    recorded = json.loads((EVIDENCE / "g11k-runtime-evidence.json").read_text(encoding="utf-8"))
    project_id = recorded["project_id"]
    commands = recorded["commands"]
    batch_id = commands["create_batch"]["response"]["id"]
    paths = {
        "mapping_confirmation": f"{API}/projects/{project_id}/asset-imports/{batch_id}/column-mapping/confirmations",
        "mapping_materialization": f"{API}/projects/{project_id}/asset-imports/{batch_id}/column-mapping/materializations",
        "analysis_finalize": f"{API}/projects/{project_id}/preliminary-analyses",
        "result_generate": f"{API}/projects/{project_id}/preliminary-results",
        "customer_bind": f"{API}/projects/{project_id}/preliminary-customer",
        "official_intake": f"{API}/projects/{project_id}/official-intake",
    }
    with sync_playwright() as playwright:
        client = playwright.request.new_context(base_url=BASE)
        login = client.post(f"{API}/auth/login", data={
            "organization_slug": "g11k-synthetic-main", "email": "owner@g11k.invalid",
            "password": os.environ["G11K_SYNTHETIC_PASSWORD"],
        })
        assert login.status == 200, login.text()
        csrf = next(cookie["value"] for cookie in client.storage_state()["cookies"] if cookie["name"] == "XSRF-TOKEN")
        headers = {"X-CSRF-Token": csrf, "Origin": BASE}
        before = client.get(f"{API}/projects/{project_id}/case-state").json()["preliminary"]
        assert before["official_intake_commit_id"] == commands["official_intake"]["response"]["id"]
        outcomes = {}
        for name, path in paths.items():
            response = client.post(path, data=commands[name]["payload"], headers=headers)
            body = response.json()
            print(name, response.status, json.dumps(body, ensure_ascii=False)[:650])
            outcomes[name] = {"status": response.status, "body": body}
            assert response.status in (200, 201), (name, response.status, body)
            id_field = "usage_id" if name == "mapping_materialization" else "receipt_id" if name == "customer_bind" else "decision_id" if name == "mapping_confirmation" else "id"
            assert body[id_field] == commands[name]["response"][id_field], (name, body)
        after = client.get(f"{API}/projects/{project_id}/case-state").json()["preliminary"]
        for field in ("official_intake_commit_id", "current_preliminary_analysis_snapshot_id",
                      "current_preliminary_result_artifact_id", "current_preliminary_result_version",
                      "project_row_version", "current_preliminary_import_batch_id"):
            assert after[field] == before[field], (field, before[field], after[field])
        (EVIDENCE / "g11k-replay-evidence.json").write_text(json.dumps({
            "project_id": project_id, "outcomes": outcomes,
            "unchanged_case_fields": {field: after[field] for field in (
                "official_intake_commit_id", "current_preliminary_analysis_snapshot_id",
                "current_preliminary_result_artifact_id", "current_preliminary_result_version",
                "project_row_version", "current_preliminary_import_batch_id")},
        }, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        print("REPLAY_MATRIX_PASS")
        client.dispose()


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8")
    main()
