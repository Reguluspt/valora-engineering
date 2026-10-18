"""Fresh disposable synthetic entries, using real source/mapping/analysis/Intake commands."""
import json
import os

from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.excel_import.infrastructure.object_storage import get_object_storage
from app.modules.project_master_data.models import Role, User, UserRole
from tests.g2_asset_review_helpers import seed_guarded_entry


def main():
    storage = get_object_storage()
    try:
        storage._client.create_bucket(Bucket=os.environ["S3_BUCKET"])
    except storage._client.exceptions.BucketAlreadyOwnedByYou:
        pass
    storage.ensure_bucket()
    created = {}
    with SessionLocal() as db:
        suffix = os.environ.get("ISSUE206_RUN_SUFFIX", "")
        for name in os.environ.get("ISSUE206_CASES", "normal,lost,stale,invalid,scope").split(","):
            entry = seed_guarded_entry(db, storage=storage)
            org, user, project = entry["org"], entry["user"], entry["project"]
            org.organization_slug = f"issue206-{name}{suffix}"
            user.email = "operator@issue206.invalid"
            user.full_name = "Người kiểm thử 206"
            user.password_hash = hash_password(os.environ["ISSUE206_SYNTHETIC_PASSWORD"])
            project.code = f"ISSUE206-{name.upper()}{suffix.upper()}"
            project.name = f"Hồ sơ tổng hợp 206 {name}"
            for grant in db.query(UserRole).filter_by(user_id=user.id).all():
                db.delete(grant)
            db.flush()
            db.delete(entry["role"])
            db.add(UserRole(user_id=user.id, role_id=db.query(Role).filter_by(code="owner").one().id, is_active=True))
            viewer = User(organization_id=org.id, email="viewer@issue206.invalid", full_name="Người xem 206",
                          password_hash=hash_password(os.environ["ISSUE206_SYNTHETIC_PASSWORD"]), status="active")
            db.add(viewer)
            db.flush()
            db.add(UserRole(user_id=viewer.id, role_id=db.query(Role).filter_by(code="viewer").one().id, is_active=True))
            db.commit()
            created[name] = {"project_id": str(project.id), "batch_id": str(entry["batch"].id),
                             "organization_slug": org.organization_slug}
    print(json.dumps(created, sort_keys=True))


if __name__ == "__main__":
    main()
