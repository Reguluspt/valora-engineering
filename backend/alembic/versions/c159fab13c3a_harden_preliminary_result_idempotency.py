"""Harden preliminary result idempotency.

Revision ID: c159fab13c3a
Revises: f9e8d7c6b5a4
Create Date: 2026-09-04 00:00:00.000000
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c159fab13c3a"
down_revision: Union[str, None] = "f9e8d7c6b5a4"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _is_sqlite() -> bool:
    return op.get_bind().dialect.name == "sqlite"


def upgrade() -> None:
    op.add_column(
        "preliminary_result_artifacts",
        sa.Column("idempotency_key", sa.String(128), nullable=True),
    )
    op.add_column(
        "preliminary_result_artifacts",
        sa.Column("request_digest_sha256", sa.String(64), nullable=True),
    )
    op.create_index(
        "uq_preliminary_result_idempotency",
        "preliminary_result_artifacts",
        ["organization_id", "idempotency_key"],
        unique=True,
        postgresql_where=sa.text("idempotency_key IS NOT NULL"),
        sqlite_where=sa.text("idempotency_key IS NOT NULL"),
    )
    with op.batch_alter_table("preliminary_result_artifacts") as batch_op:
        batch_op.create_check_constraint(
            "chk_preliminary_result_idempotency_trim",
            sa.text("idempotency_key IS NULL OR length(trim(idempotency_key)) > 0"),
        )
        if _is_sqlite():
            # SQLite custom compiler drops regex constraints; enforce length/lower only.
            batch_op.create_check_constraint(
                "chk_preliminary_result_request_digest",
                sa.text(
                    "request_digest_sha256 IS NULL OR ("
                    "length(request_digest_sha256) = 64 "
                    "AND request_digest_sha256 = lower(request_digest_sha256))"
                ),
            )
        else:
            batch_op.create_check_constraint(
                "chk_preliminary_result_request_digest",
                sa.text(
                    "request_digest_sha256 IS NULL OR ("
                    "length(request_digest_sha256) = 64 "
                    "AND request_digest_sha256 = lower(request_digest_sha256) "
                    "AND request_digest_sha256 ~ '^[0-9a-f]{64}$')"
                ),
            )
        batch_op.create_check_constraint(
            "chk_preliminary_result_request_pairing",
            sa.text("(idempotency_key IS NULL) = (request_digest_sha256 IS NULL)"),
        )


def downgrade() -> None:
    with op.batch_alter_table("preliminary_result_artifacts") as batch_op:
        batch_op.drop_constraint(
            "chk_preliminary_result_request_pairing",
            type_="check",
        )
        batch_op.drop_constraint(
            "chk_preliminary_result_request_digest",
            type_="check",
        )
        batch_op.drop_constraint(
            "chk_preliminary_result_idempotency_trim",
            type_="check",
        )
    op.drop_index(
        "uq_preliminary_result_idempotency",
        table_name="preliminary_result_artifacts",
    )
    op.drop_column("preliminary_result_artifacts", "request_digest_sha256")
    op.drop_column("preliminary_result_artifacts", "idempotency_key")
