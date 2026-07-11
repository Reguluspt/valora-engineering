"""create_identity_baseline

Revision ID: 7519c3d1f364
Revises: 632247f5fd32
Create Date: 2026-07-06 22:39:49.607441

"""
import uuid
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '7519c3d1f364'
down_revision: Union[str, Sequence[str], None] = '632247f5fd32'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create organization_profiles table
    op.create_table(
        "organization_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("organization_slug", sa.String(length=64), nullable=False),
        sa.Column("tax_code", sa.String(length=64), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("phone", sa.String(length=50), nullable=True),
        sa.Column("email", sa.String(length=255), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("default_currency_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_slug")
    )

    # 2. Create users table
    op.create_table(
        "users",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("last_login_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "email", name="uq_user_org_email")
    )

    # 3. Create roles table
    roles_table = op.create_table(
        "roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("permissions", sa.JSON(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code")
    )

    # 4. Create user_roles table
    op.create_table(
        "user_roles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("role_id", sa.Uuid(), nullable=False),
        sa.Column("assigned_by", sa.Uuid(), nullable=True),
        sa.Column("assigned_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["assigned_by"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["role_id"], ["roles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )
    
    # Partial unique index for active user roles
    op.create_index(
        "uq_active_user_role",
        "user_roles",
        ["user_id", "role_id"],
        unique=True,
        postgresql_where="is_active = true"
    )

    # 5. Seed standard roles
    roles_data = [
        {
            "id": uuid.UUID("a1b2c3d4-e5f6-7a8b-9c0d-1e2f3a4b5c6d"),
            "code": "owner",
            "display_name": "Owner",
            "description": "Full access to organization",
            "permissions": [
                "project:create", "project:read", "project:update", "project:file:upload", "project:asset_line:read",
                "project:review:complete", "project:approve", "project:reject", "project:archive", "project:cancel",
                "master_data:customer:read", "master_data:customer:create", "master_data:customer:update",
                "master_data:customer:deactivate", "master_data:customer:merge",
                "master_data:supplier:read", "master_data:supplier:create", "master_data:supplier:update",
                "master_data:supplier:deactivate", "master_data:supplier:merge",
                "master_data:reference:read", "master_data:reference:create",
                "master_data:brand:read", "master_data:brand:create",
                "master_data:unit:read", "master_data:unit:create",
                "master_data:currency:create",
                "master_data:signer:create", "master_data:signer:update"
            ]
        },
        {
            "id": uuid.UUID("b2c3d4e5-f6a7-8b9c-0d1e-2f3a4b5c6d7e"),
            "code": "admin",
            "display_name": "Admin",
            "description": "Manage users, settings, master data",
            "permissions": [
                "project:create", "project:read", "project:update", "project:file:upload", "project:asset_line:read",
                "project:review:complete", "project:approve", "project:reject", "project:archive", "project:cancel",
                "master_data:customer:read", "master_data:customer:create", "master_data:customer:update",
                "master_data:customer:deactivate", "master_data:customer:merge",
                "master_data:supplier:read", "master_data:supplier:create", "master_data:supplier:update",
                "master_data:supplier:deactivate", "master_data:supplier:merge",
                "master_data:reference:read", "master_data:reference:create",
                "master_data:brand:read", "master_data:brand:create",
                "master_data:unit:read", "master_data:unit:create",
                "master_data:currency:create",
                "master_data:signer:create", "master_data:signer:update"
            ]
        },
        {
            "id": uuid.UUID("c3d4e5f6-a7b8-9c0d-1e2f-3a4b5c6d7e8f"),
            "code": "appraiser",
            "display_name": "Appraiser",
            "description": "Create projects and perform valuation review",
            "permissions": [
                "project:create", "project:read", "project:update", "project:file:upload", "project:asset_line:read",
                "project:review:complete", "project:archive", "project:cancel",
                "master_data:customer:read", "master_data:customer:create", "master_data:customer:update",
                "master_data:supplier:read", "master_data:supplier:create", "master_data:supplier:update",
                "master_data:reference:read",
                "master_data:brand:read", "master_data:brand:create",
                "master_data:unit:read"
            ]
        },
        {
            "id": uuid.UUID("d4e5f6a7-b8c9-0d1e-2f3a-4b5c6d7e8f9a"),
            "code": "reviewer",
            "display_name": "Reviewer",
            "description": "QC review and project approval",
            "permissions": [
                "project:read", "project:asset_line:read", "project:review:complete", "project:approve", "project:reject",
                "master_data:customer:read",
                "master_data:supplier:read",
                "master_data:reference:read",
                "master_data:brand:read",
                "master_data:unit:read"
            ]
        },
        {
            "id": uuid.UUID("e5f6a7b8-c9d0-1e2f-3a4b-5c6d7e8f9a0b"),
            "code": "knowledge_curator",
            "display_name": "Knowledge Curator",
            "description": "Approve Knowledge Base changes",
            "permissions": [
                "project:read", "project:asset_line:read",
                "master_data:customer:read", "master_data:customer:create", "master_data:customer:update", "master_data:customer:merge",
                "master_data:supplier:read", "master_data:supplier:create", "master_data:supplier:update", "master_data:supplier:merge",
                "master_data:reference:read", "master_data:reference:create",
                "master_data:brand:read", "master_data:brand:create",
                "master_data:unit:read"
            ]
        },
        {
            "id": uuid.UUID("f6a7b8c9-d0e1-2f3a-4b5c-6d7e8f9a0b1c"),
            "code": "viewer",
            "display_name": "Viewer",
            "description": "Read-only access",
            "permissions": [
                "project:read", "project:asset_line:read",
                "master_data:customer:read",
                "master_data:supplier:read",
                "master_data:reference:read",
                "master_data:brand:read",
                "master_data:unit:read"
            ]
        }
    ]
    op.bulk_insert(roles_table, roles_data)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("uq_active_user_role", table_name="user_roles")
    op.drop_table("user_roles")
    op.drop_table("roles")
    op.drop_table("users")
    op.drop_table("organization_profiles")
