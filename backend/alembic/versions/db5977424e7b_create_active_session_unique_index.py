"""create_active_session_unique_index

Revision ID: db5977424e7b
Revises: a7414963cd8d
Create Date: 2026-07-11 17:02:28.258902

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'db5977424e7b'
down_revision: Union[str, Sequence[str], None] = 'a7414963cd8d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_index(
        'uq_active_session_per_user_project',
        'workbench_sessions',
        ['user_id', 'project_id'],
        unique=True,
        sqlite_where=sa.text("status = 'active'"),
        postgresql_where=sa.text("status = 'active'")
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index('uq_active_session_per_user_project', table_name='workbench_sessions')
