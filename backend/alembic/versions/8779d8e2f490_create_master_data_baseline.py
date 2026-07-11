"""create_master_data_baseline

Revision ID: 8779d8e2f490
Revises: 318f6d7d13e8
Create Date: 2026-07-06 22:49:54.116165

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "8779d8e2f490"
down_revision: Union[str, Sequence[str], None] = "318f6d7d13e8"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create manufacturers table
    op.create_table(
        "manufacturers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("website", sa.String(length=255), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 2. Create brands table
    op.create_table(
        "brands",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=True),
        sa.Column("manufacturer_id", sa.Uuid(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )

    # Unique case-insensitive index on brand name
    op.create_index("uq_brand_name_lower", "brands", [sa.text("lower(name)")], unique=True)

    # 3. Create customers table
    op.create_table(
        "customers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("tax_code", sa.String(length=64), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("province_id", sa.Uuid(), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("merged_into_customer_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merged_into_customer_id"], ["customers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["province_id"], ["provinces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "tax_code", name="uq_customer_tax_org"),
    )

    # 4. Create customer_aliases table
    op.create_table(
        "customer_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("source_project_id", sa.Uuid(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 5. Create suppliers table
    op.create_table(
        "suppliers",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("legal_name", sa.String(length=255), nullable=False),
        sa.Column("display_name", sa.String(length=255), nullable=True),
        sa.Column("tax_code", sa.String(length=64), nullable=True),
        sa.Column("address", sa.Text(), nullable=True),
        sa.Column("province_id", sa.Uuid(), nullable=True),
        sa.Column("contact_name", sa.String(length=255), nullable=True),
        sa.Column("contact_phone", sa.String(length=50), nullable=True),
        sa.Column("contact_email", sa.String(length=255), nullable=True),
        sa.Column("reliability_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("merged_into_supplier_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["merged_into_supplier_id"], ["suppliers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(["province_id"], ["provinces.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "tax_code", name="uq_supplier_tax_org"),
    )

    # 6. Create supplier_aliases table
    op.create_table(
        "supplier_aliases",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("supplier_id", sa.Uuid(), nullable=False),
        sa.Column("alias_name", sa.String(length=255), nullable=False),
        sa.Column("source_project_id", sa.Uuid(), nullable=True),
        sa.Column("confidence_score", sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["supplier_id"], ["suppliers.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )

    # 7. Create signer_profiles table
    op.create_table(
        "signer_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("full_name", sa.String(length=255), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=True),
        sa.Column("certificate_number", sa.String(length=100), nullable=True),
        sa.Column("signature_image_file_id", sa.Uuid(), nullable=True),
        sa.Column("is_default", sa.Boolean(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("signer_profiles")
    op.drop_table("supplier_aliases")
    op.drop_table("suppliers")
    op.drop_table("customer_aliases")
    op.drop_table("customers")
    op.drop_index("uq_brand_name_lower", table_name="brands")
    op.drop_table("brands")
    op.drop_table("manufacturers")
