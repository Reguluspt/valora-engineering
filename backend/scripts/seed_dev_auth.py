import sys
import os

# Align python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import sqlalchemy as sa

from app.core.config import get_settings
from app.db.session import SessionLocal
from app.modules.project_master_data.models import (
    OrganizationProfile, OrganizationStatus, User, UserStatus, Role, UserRole
)

def seed_dev_auth():
    settings = get_settings()

    # 1. Refuse to run if VALORA_ENV=production
    if settings.valora_env == "production":
        print("ERROR: Cannot run seed_dev_auth in production mode.")
        sys.exit(1)

    print("=== Seeding local dev trial authentication data ===")
    
    # Try connecting to standard configured DB session; fallback to SQLite if connection timeout occurs
    try:
        db = SessionLocal()
        # Test connection liveness
        db.execute(sa.text("SELECT 1"))
    except Exception as e:
        print(f"PostgreSQL connection failed ({e}). Falling back to local development SQLite DB...")
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        # Use local SQLite db matching test/local fallbacks
        fallback_engine = create_engine("sqlite:///valora_local_trial.db")
        from app.db.base_class import Base
        Base.metadata.create_all(bind=fallback_engine)
        SessionFallback = sessionmaker(bind=fallback_engine)
        db = SessionFallback()

    try:
        # 2. Organization upsert
        org = db.query(OrganizationProfile).filter(
            OrganizationProfile.organization_slug == "valora-local-demo"
        ).first()
        if not org:
            org = OrganizationProfile(
                legal_name="Valora Local Demo / Gia Lai Division",
                organization_slug="valora-local-demo",
                status=OrganizationStatus.ACTIVE
            )
            db.add(org)
            db.commit()
            db.refresh(org)
            print(f"Created Org: {org.legal_name} ({org.id})")
        else:
            print(f"Found existing Org: {org.legal_name} ({org.id})")

        # 3. Role setup definitions
        role_permissions = {
            "admin": [
                "workbench:open", "workbench:read", "workbench:edit", "workbench:undo_redo",
                "project:create", "project:read", "project:update", "project:archive", "project:cancel",
                "workflow:read", "workflow:instance:manage", "workflow:task:assign", "workflow:task:complete",
                "workflow:decision:create", "workflow:override_gate"
            ],
            "appraiser": [
                "workbench:open", "workbench:read", "workbench:edit", "workbench:undo_redo",
                "project:read"
            ],
            "reviewer": [
                "workbench:open", "workbench:read", "workbench:edit", "workbench:undo_redo",
                "project:read", "workflow:read", "workflow:task:complete", "workflow:decision:create"
            ],
            "viewer": [
                "workbench:read", "project:read", "workflow:read"
            ]
        }

        roles = {}
        for code, perms in role_permissions.items():
            role = db.query(Role).filter(Role.code == code).first()
            if not role:
                role = Role(code=code, display_name=code.capitalize(), permissions=perms)
                db.add(role)
                db.commit()
                db.refresh(role)
                print(f"Created Role: {code}")
            else:
                # Update permissions to align with standard set
                role.permissions = perms
                db.commit()
                print(f"Aligned Role permissions: {code}")
            roles[code] = role

        # 4. User upsert definitions
        user_types = [
            ("admin@valora.local", "Local Admin", "admin"),
            ("appraiser@valora.local", "Local Appraiser", "appraiser"),
            ("reviewer@valora.local", "Local Reviewer", "reviewer"),
            ("viewer@valora.local", "Local Viewer", "viewer")
        ]

        for email, full_name, role_code in user_types:
            user = db.query(User).filter(User.email == email).first()
            if not user:
                user = User(
                    organization_id=org.id,
                    email=email,
                    full_name=full_name,
                    status=UserStatus.ACTIVE
                )
                db.add(user)
                db.commit()
                db.refresh(user)
                print(f"Created User [{role_code}]: {email} | USER_ID = {user.id}")
            else:
                print(f"Found User [{role_code}]: {email} | USER_ID = {user.id}")

            # Align active role bindings
            role = roles[role_code]
            binding = db.query(UserRole).filter(
                UserRole.user_id == user.id,
                UserRole.role_id == role.id
            ).first()
            if not binding:
                binding = UserRole(user_id=user.id, role_id=role.id, is_active=True)
                db.add(binding)
                db.commit()
                print(f"Bound User {email} to Role {role_code}")
            else:
                binding.is_active = True
                binding.revoked_at = None
                db.commit()
                print(f"Verified User {email} has active Role {role_code}")

        print("=== Dev authentication seeding complete ===")

    finally:
        db.close()

if __name__ == "__main__":
    seed_dev_auth()
