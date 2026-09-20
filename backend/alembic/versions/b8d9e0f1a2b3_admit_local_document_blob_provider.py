"""Admit the local filesystem document blob provider.

Revision ID: b8d9e0f1a2b3
Revises: b7c8d9e0f1a2
Create Date: 2026-09-20 12:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b8d9e0f1a2b3"
down_revision: Union[str, None] = "b7c8d9e0f1a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _replace_provider_constraint(table: str, name: str, values: str) -> None:
    op.drop_constraint(name, table, type_="check")
    op.create_check_constraint(name, table, f"provider_kind IN ({values})")


def upgrade() -> None:
    _replace_provider_constraint(
        "document_storage_candidates", "chk_storage_candidate_provider", "'fake', 'local'"
    )
    _replace_provider_constraint(
        "storage_object_bindings", "chk_storage_binding_provider", "'fake', 'local'"
    )


def downgrade() -> None:
    connection = op.get_bind()
    local_rows = connection.execute(
        sa.text(
            "SELECT "
            "(SELECT count(*) FROM document_storage_candidates WHERE provider_kind = 'local') + "
            "(SELECT count(*) FROM storage_object_bindings WHERE provider_kind = 'local')"
        )
    ).scalar_one()
    if local_rows:
        raise RuntimeError("cannot downgrade while local document blob rows exist")
    _replace_provider_constraint(
        "storage_object_bindings", "chk_storage_binding_provider", "'fake'"
    )
    _replace_provider_constraint(
        "document_storage_candidates", "chk_storage_candidate_provider", "'fake'"
    )
