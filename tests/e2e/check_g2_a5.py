"""Synthetic A5 acceptance readback and controlled existing-API value edits.

Reads proof/audit counts from PostgreSQL. Setup/edit commands never write SQL.
Passwords remain outside the repository and are never returned in evidence.
"""
import json
import os
import sys
import uuid
from pathlib import Path

import httpx

from app.db import SessionLocal
from app.modules.excel_import import models as excel_import_models  # noqa: F401
from app.modules.project_master_data.models import (
    AssetLineValidationGeneration, AssetLineHumanDecision, AssetLineDecisionReversal,
    AssetReviewCommandReceipt, AuditEvent,
)


def main():
    evidence = Path(os.environ["A5_EVIDENCE_DIR"])
    fixture = json.loads((evidence / "fixture.json").read_text(encoding="utf-8-sig"))
    project = fixture["project_id"]
    with httpx.Client(base_url="http://127.0.0.1:8000", timeout=30) as client:
        login = client.post("/api/v1/auth/login", json={"organization_slug": fixture["organization_slug"],
            "email": fixture["operator_email"], "password": (evidence / "synthetic-password.txt").read_text()})
        login.raise_for_status()
        client.headers["X-CSRF-Token"] = client.cookies.get("XSRF-TOKEN")
        base = f"/api/v1/projects/{project}"
        def call(method, path, **kwargs):
            response = client.request(method, path, **kwargs)
            response.raise_for_status()
            return response.json()
        mode = sys.argv[1] if len(sys.argv) > 1 else "read"
        lines = call("GET", base + "/asset-lines")["items"]
        state = call("GET", base + "/case-state")
        line_id = state["next_action"].get("context", {}).get("line_id") if state["next_action"].get("context") else None
        line = next((item for item in lines if item["id"] == line_id), lines[0])
        if mode == "edit-quantity":
            call("PATCH", base + f'/asset-lines/{line["id"]}', json={
                "quantity": float(line["quantity"]) + 1, "row_version": int(line["version_token"])})
        elif mode in ("warning", "correct-description"):
            call("POST", "/api/v1/workbench/sessions", json={"project_id": project})
            call("PATCH", base + f'/asset-lines/{line["id"]}/draft', json={
                "field_key": "description", "draft_value": "   " if mode == "warning" else "Mô tả tổng hợp đã chỉnh sửa",
                "base_value": line["description"], "version_token": line["version_token"]})
            call("POST", base + f'/asset-lines/{line["id"]}/draft/commit', json={
                "field_keys": ["description"], "confirm": True, "version_token": line["version_token"]})
        elif mode == "validate-newer":
            context = state["next_action"]["context"]
            call("POST", base + f'/asset-lines/{context["line_id"]}/validate', json={
                "command_id": str(uuid.uuid4()), "confirm": True,
                "expected_row_version": context["line_row_version"], "expected_case_version": state["case_version"],
                "contract_version": "asset-line-validation-v1"})
        elif mode != "read":
            raise ValueError("Unknown synthetic acceptance action")
        state = call("GET", base + "/case-state")
        lines = call("GET", base + "/asset-lines")["items"]
        with SessionLocal() as db:
            counts = {model.__tablename__: db.query(model).filter_by(project_id=uuid.UUID(project)).count()
                      for model in (AssetLineValidationGeneration, AssetLineHumanDecision,
                                    AssetLineDecisionReversal, AssetReviewCommandReceipt)}
            counts["validation_audits"] = db.query(AuditEvent).filter(
                AuditEvent.event_name == "ProjectAssetLineValidated",
                AuditEvent.entity_id.in_([uuid.UUID(item["id"]) for item in lines])).count()
            counts["decision_audits"] = db.query(AuditEvent).filter(
                AuditEvent.event_name == "ProjectAssetLineReviewDecided",
                AuditEvent.entity_id.in_([uuid.UUID(item["id"]) for item in lines])).count()
        print(json.dumps({"mode": mode, "case_state": state, "counts": counts,
                          "lines": [{k: item[k] for k in ("id", "asset_name", "review_status", "validation_status", "version_token")}
                                    for item in lines]}, ensure_ascii=True))


if __name__ == "__main__":
    main()
