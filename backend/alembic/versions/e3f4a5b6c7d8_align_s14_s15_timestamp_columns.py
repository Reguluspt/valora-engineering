"""Align S14/S15 timestamp columns with the ORM models.

Revision ID: e3f4a5b6c7d8
Revises: d2e3f4a5b6c7
Create Date: 2026-08-27 00:00:00.000000
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "e3f4a5b6c7d8"
down_revision: Union[str, None] = "d2e3f4a5b6c7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _updated_at_column() -> sa.Column:
    return sa.Column(
        "updated_at",
        sa.DateTime(timezone=True),
        server_default=sa.text("now()"),
        nullable=False,
    )


def upgrade() -> None:
    op.add_column("asset_identity_decisions", _updated_at_column())
    op.add_column("learning_feedback_events", _updated_at_column())
    op.add_column("dossier_source_files", _updated_at_column())


def downgrade() -> None:
    op.drop_column("dossier_source_files", "updated_at")
    op.drop_column("learning_feedback_events", "updated_at")
    op.drop_column("asset_identity_decisions", "updated_at")
