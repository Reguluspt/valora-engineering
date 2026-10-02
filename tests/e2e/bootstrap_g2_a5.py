"""Synthetic A5 data using the real lineage/Intake/guarded-Apply commands.

Run from backend with PYTHONPATH=backend and a fresh migrated acceptance DB.
No official status/proof SQL, no permission grants, and no production data.
"""
import json
import os

from app.db import SessionLocal
from app.core.security import hash_password
from app.modules.excel_import.infrastructure.object_storage import get_object_storage
from app.modules.project_master_data.models import Role, User, UserRole, WorkbenchSession
from tests.g2_asset_review_helpers import seed_guarded_entry
from tests.test_g2_authority import _ready, _apply


def main():
    password = os.environ["A5_SYNTHETIC_PASSWORD"]
    if len(password) < 12:
        raise ValueError("Synthetic password must have at least 12 characters")
    storage = get_object_storage()
    storage.ensure_bucket()
    with SessionLocal() as db:
        entry = seed_guarded_entry(db, storage=storage)
        org, user, project = entry["org"], entry["user"], entry["project"]
        org.organization_slug = "a5-synthetic"
        org.legal_name = "A5 Synthetic Organization"
        user.email = "operator@a5.invalid"
        user.full_name = "Người kiểm thử A5"
        user.password_hash = hash_password(password)
        project.code = "A5-SYNTH-001"
        project.name = "Hồ sơ tổng hợp A5 — Rà soát tài sản"
        # The helper's private unit-test role is removed; migrated standard roles are authority.
        for grant in db.query(UserRole).filter_by(user_id=user.id).all():
            db.delete(grant)
        db.flush()
        db.delete(entry["role"])
        owner = db.query(Role).filter_by(code="owner").one()
        viewer = db.query(Role).filter_by(code="viewer").one()
        db.add(UserRole(user_id=user.id, role_id=owner.id, is_active=True))
        read_user = User(organization_id=org.id, email="viewer@a5.invalid", full_name="Người xem A5",
                         password_hash=hash_password(password), status="active")
        db.add(read_user)
        db.flush()
        db.add(UserRole(user_id=read_user.id, role_id=viewer.id, is_active=True))
        db.commit()
        _apply(db, entry, _ready(db, entry))
        db.commit()
        assert db.query(WorkbenchSession).filter_by(project_id=project.id).count() == 0
        print(json.dumps({"project_id": str(project.id), "project_code": project.code,
                          "organization_slug": org.organization_slug, "operator_email": user.email,
                          "viewer_email": read_user.email, "rows": 3}, sort_keys=True))


if __name__ == "__main__":
    main()
