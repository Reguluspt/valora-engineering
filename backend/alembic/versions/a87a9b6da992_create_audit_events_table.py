"""create_audit_events_table

Revision ID: a87a9b6da992
Revises: 85f658678b7d
Create Date: 2026-07-07 17:51:19.860156

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'a87a9b6da992'
down_revision: Union[str, Sequence[str], None] = '85f658678b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("actor_user_id", sa.Uuid(), nullable=True),
        sa.Column("command_name", sa.String(length=128), nullable=True),
        sa.Column("event_name", sa.String(length=128), nullable=False),
        sa.Column("entity_type", sa.String(length=128), nullable=False),
        sa.Column("entity_id", sa.Uuid(), nullable=True),
        sa.Column("correlation_id", sa.String(length=128), nullable=True),
        sa.Column("payload", sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(["actor_user_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["organization_id"], ["organization_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id")
    )
    op.create_index("idx_audit_event_org", "audit_events", ["organization_id"])
    op.create_index("idx_audit_event_actor", "audit_events", ["actor_user_id"])
    op.create_index("idx_audit_event_entity", "audit_events", ["entity_type", "entity_id"])


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("idx_audit_event_entity", table_name="audit_events")
    op.drop_index("idx_audit_event_actor", table_name="audit_events")
    op.drop_index("idx_audit_event_org", table_name="audit_events")
    op.drop_table("audit_events")
