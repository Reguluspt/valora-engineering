"""Create only synthetic identity and Customer seed data for real-stack G1.1K."""

import json
import os

from app.core.rbac import derive_effective_permissions
from app.core.security import hash_password
from app.db import SessionLocal
from app.modules.excel_import import models as excel_import_models  # noqa: F401
from app.modules.project_master_data.models import (
    Customer,
    CustomerStatus,
    OrganizationProfile,
    OrganizationStatus,
    Role,
    User,
    UserRole,
    UserStatus,
)


def main() -> None:
    password = os.environ["G11K_SYNTHETIC_PASSWORD"]
    if len(password) < 12:
        raise ValueError("Synthetic password must have at least 12 characters")

    db = SessionLocal()
    try:
        tenants = (
            ("g11k-synthetic-main", "G1.1K Synthetic Main", (("owner", "owner@g11k.invalid"), ("viewer", "viewer@g11k.invalid"))),
            ("g11k-synthetic-other", "G1.1K Synthetic Other", (("appraiser", "appraiser@g11k.invalid"),)),
        )
        result: dict[str, object] = {"organizations": {}, "users": {}}
        for slug, name, accounts in tenants:
            organization = db.query(OrganizationProfile).filter_by(organization_slug=slug).one_or_none()
            if organization is None:
                organization = OrganizationProfile(
                    legal_name=name, organization_slug=slug, status=OrganizationStatus.ACTIVE,
                )
                db.add(organization)
                db.flush()
            result["organizations"][slug] = str(organization.id)
            for role_code, email in accounts:
                role = db.query(Role).filter_by(code=role_code).one()
                user = db.query(User).filter_by(organization_id=organization.id, email=email).one_or_none()
                if user is None:
                    user = User(
                        organization_id=organization.id, email=email, full_name=f"G1.1K {role_code}",
                        password_hash=hash_password(password), status=UserStatus.ACTIVE,
                    )
                    db.add(user)
                    db.flush()
                    db.add(UserRole(user_id=user.id, role_id=role.id, is_active=True))
                else:
                    user.password_hash = hash_password(password)
                db.flush()
                result["users"][email] = {
                    "id": str(user.id), "role": role_code,
                    "permissions": sorted(derive_effective_permissions(user, db)),
                }
            if slug == "g11k-synthetic-main":
                owner = db.query(User).filter_by(organization_id=organization.id, email="owner@g11k.invalid").one()
                customer = db.query(Customer).filter_by(
                    organization_id=organization.id, tax_code="G11K-SYNTHETIC-001",
                ).one_or_none()
                if customer is None:
                    customer = Customer(
                        organization_id=organization.id,
                        legal_name="G1.1K Synthetic Customer",
                        display_name="Khách hàng tổng hợp G1.1K",
                        tax_code="G11K-SYNTHETIC-001",
                        status=CustomerStatus.ACTIVE,
                        created_by=owner.id,
                    )
                    db.add(customer)
                    db.flush()
                result["customer_id"] = str(customer.id)
        db.commit()
        print(json.dumps(result, sort_keys=True))
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


if __name__ == "__main__":
    main()
