"""create_project_baseline

Revision ID: 85f658678b7d
Revises: 8779d8e2f490
Create Date: 2026-07-06 22:55:50.271645

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '85f658678b7d'
down_revision: Union[str, Sequence[str], None] = '8779d8e2f490'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create projects table
    op.create_table(
        "projects",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("customer_id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.Column("knowledge_status", sa.String(length=50), nullable=False),
        sa.Column("fee_amount", sa.Numeric(precision=15, scale=2), nullable=False, server_default="0.00"),
        sa.Column("fee_currency_id", sa.Uuid(), nullable=True),
        sa.Column("signer_profile_id", sa.Uuid(), nullable=True),
        sa.Column("created_by", sa.Uuid(), nullable=False),
        sa.Column("updated_by", sa.Uuid(), nullable=True),
        sa.CheckConstraint("fee_amount >= 0", name="chk_project_fee_positive"),
        sa.ForeignKeyConstraint(["created_by"], ["users.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["customer_id"], ["customers.id"], ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["fee_currency_id"], ["currencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["signer_profile_id"], ["signer_profiles.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["updated_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "code", name="uq_project_code_org")
    )

    # 2. Create project_asset_lines table
    op.create_table(
        "project_asset_lines",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("asset_name", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("quantity", sa.Numeric(precision=15, scale=4), nullable=False, server_default="1.0000"),
        sa.Column("unit_id", sa.Uuid(), nullable=True),
        sa.Column("raw_price", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("raw_price_currency_id", sa.Uuid(), nullable=True),
        sa.Column("appraised_unit_price", sa.Numeric(precision=15, scale=2), nullable=True),
        sa.Column("appraised_currency_id", sa.Uuid(), nullable=True),
        sa.Column("review_status", sa.String(length=50), nullable=False),
        sa.Column("validation_status", sa.String(length=50), nullable=False),
        sa.Column("brand_id", sa.Uuid(), nullable=True),
        sa.Column("manufacturer_id", sa.Uuid(), nullable=True),
        sa.Column("matched_asset_id", sa.Uuid(), nullable=True),
        sa.Column("matched_knowledge_id", sa.Uuid(), nullable=True),
        sa.Column("taxonomy_id", sa.Uuid(), nullable=True),
        sa.CheckConstraint("appraised_unit_price >= 0", name="chk_asset_appraised_price_positive"),
        sa.CheckConstraint("quantity >= 0", name="chk_asset_quantity_positive"),
        sa.CheckConstraint("raw_price >= 0", name="chk_asset_raw_price_positive"),
        sa.ForeignKeyConstraint(["appraised_currency_id"], ["currencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["brand_id"], ["brands.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["manufacturer_id"], ["manufacturers.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["raw_price_currency_id"], ["currencies.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["unit_id"], ["units.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id")
    )

    # 3. Create project_files table
    op.create_table(
        "project_files",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("row_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("file_name", sa.String(length=255), nullable=False),
        sa.Column("file_category", sa.String(length=50), nullable=False),
        sa.Column("file_size", sa.Integer(), nullable=False),
        sa.Column("mime_type", sa.String(length=100), nullable=False),
        sa.Column("storage_object_key", sa.String(length=1024), nullable=False),
        sa.Column("checksum_sha256", sa.String(length=64), nullable=False),
        sa.Column("processing_status", sa.String(length=50), nullable=False),
        sa.Column("extracted_metadata", sa.JSON(), nullable=True),
        sa.Column("uploaded_by", sa.Uuid(), nullable=False),
        sa.CheckConstraint("file_size >= 0", name="chk_file_size_positive"),
        sa.ForeignKeyConstraint(["project_id"], ["projects.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["uploaded_by"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("project_files")
    op.drop_table("project_asset_lines")
    op.drop_table("projects")
