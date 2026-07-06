"""create_reference_data_baseline

Revision ID: 318f6d7d13e8
Revises: 7519c3d1f364
Create Date: 2026-07-06 22:44:52.138390

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '318f6d7d13e8'
down_revision: Union[str, Sequence[str], None] = '7519c3d1f364'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # 1. Create countries table
    op.create_table(
        "countries",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("iso2", sa.String(length=2), nullable=True),
        sa.Column("iso3", sa.String(length=3), nullable=True),
        sa.Column("name_vi", sa.String(length=128), nullable=False),
        sa.Column("name_en", sa.String(length=128), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("iso2"),
        sa.UniqueConstraint("iso3")
    )

    # 2. Create provinces table
    op.create_table(
        "provinces",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("country_id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("code", sa.String(length=64), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.ForeignKeyConstraint(["country_id"], ["countries.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id")
    )

    # 3. Create units table
    op.create_table(
        "units",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=32), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=32), nullable=True),
        sa.Column("unit_type", sa.String(length=50), nullable=True),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code")
    )

    # 4. Create currencies table
    op.create_table(
        "currencies",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("code", sa.String(length=3), nullable=False),
        sa.Column("display_name", sa.String(length=128), nullable=False),
        sa.Column("symbol", sa.String(length=16), nullable=True),
        sa.Column("decimal_places", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("code")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_table("currencies")
    op.drop_table("units")
    op.drop_table("provinces")
    op.drop_table("countries")
