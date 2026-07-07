import uuid
from typing import Optional, Set
from fastapi import Depends, Header, HTTPException
from sqlalchemy.orm import Session

from app.db import get_db
from app.modules.project_master_data.models import (
    User,
    UserRole,
    Role,
    OrganizationProfile,
    OrganizationStatus,
    UserStatus
)

def derive_effective_permissions(user: User, db: Session) -> Set[str]:
    """
    Derive effective permission strings for a given User from their active UserRole records.
    Returns an empty set if the user is inactive, organization is inactive, or user has no active roles.
    """
    # 1. Deny by default if user is inactive
    if user.status != UserStatus.ACTIVE:
        return set()

    # 2. Deny by default if organization is inactive
    # Safely access organization
    org = user.organization
    if not org or org.status != OrganizationStatus.ACTIVE:
        return set()

    effective_permissions = set()

    # 3. Union permissions from active UserRole records
    for user_role in user.roles:
        # Check active status and make sure revoked_at is None
        if user_role.is_active and user_role.revoked_at is None:
            role = user_role.role
            if role and role.permissions:
                for perm in role.permissions:
                    effective_permissions.add(perm)

    return effective_permissions


def get_current_user(
    db: Session = Depends(get_db),
    x_user_id: Optional[str] = Header(None)
) -> User:
    """
    Placeholder dependency to extract the current user.
    Uses the 'X-User-Id' request header as a testable placeholder.
    Raises HTTP 401 if missing, invalid, or user not found.
    """
    if not x_user_id:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        user_uuid = uuid.UUID(x_user_id)
    except ValueError:
        raise HTTPException(status_code=401, detail="Not authenticated")

    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(status_code=401, detail="Not authenticated")

    return user


def require_permission(permission_code: str):
    """
    FastAPI dependency builder to enforce a specific permission.
    Returns a dependency function that raises HTTP 403 if the user lacks the permission.
    """
    def dependency(
        current_user: User = Depends(get_current_user),
        db: Session = Depends(get_db)
    ) -> User:
        perms = derive_effective_permissions(current_user, db)
        if permission_code not in perms:
            raise HTTPException(status_code=403, detail="Missing permission")
        return current_user

    return dependency
