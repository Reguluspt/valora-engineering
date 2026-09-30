"""Project column mapping authority.

Revision ID: d1e2f3a4b5c6
Revises: a6b7c8d9e0f1
Create Date: 2026-09-29
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d1e2f3a4b5c6"
down_revision: Union[str, None] = "a6b7c8d9e0f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "column_mapping_profile_usages",
        sa.Column("expected_selection_revision", sa.Integer(), nullable=True),
    )
    op.create_check_constraint(
        "chk_mapping_usage_expected_revision",
        "column_mapping_profile_usages",
        "expected_selection_revision IS NULL OR expected_selection_revision >= 0",
    )
    op.create_unique_constraint(
        "uq_mapping_usage_project_id",
        "column_mapping_profile_usages",
        ["organization_id", "project_id", "id"],
    )

    op.create_table(
        "project_column_mapping_authorities",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("selection_revision", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=True),
        sa.Column("source_artifact_id", sa.Uuid(), nullable=True),
        sa.Column("structure_snapshot_id", sa.Uuid(), nullable=True),
        sa.Column("confirmation_decision_id", sa.Uuid(), nullable=True),
        sa.Column("selected_usage_id", sa.Uuid(), nullable=True),
        sa.Column("current_staging_usage_id", sa.Uuid(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "project_id", name="uq_project_mapping_authority"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_project_mapping_authority_project_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            [
                "project_asset_import_batches.organization_id",
                "project_asset_import_batches.project_id",
                "project_asset_import_batches.id",
            ],
            name="fk_project_mapping_authority_batch_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id"],
            [
                "import_source_artifacts.organization_id",
                "import_source_artifacts.project_id",
                "import_source_artifacts.import_batch_id",
                "import_source_artifacts.id",
            ],
            name="fk_project_mapping_authority_source_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
            ],
            [
                "workbook_structure_snapshots.organization_id",
                "workbook_structure_snapshots.project_id",
                "workbook_structure_snapshots.import_batch_id",
                "workbook_structure_snapshots.source_artifact_id",
                "workbook_structure_snapshots.id",
            ],
            name="fk_project_mapping_authority_structure_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
                "confirmation_decision_id",
            ],
            [
                "column_mapping_decisions.organization_id",
                "column_mapping_decisions.project_id",
                "column_mapping_decisions.import_batch_id",
                "column_mapping_decisions.source_artifact_id",
                "column_mapping_decisions.structure_snapshot_id",
                "column_mapping_decisions.id",
            ],
            name="fk_project_mapping_authority_confirmation_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            [
                "organization_id",
                "project_id",
                "import_batch_id",
                "source_artifact_id",
                "structure_snapshot_id",
                "selected_usage_id",
            ],
            [
                "column_mapping_profile_usages.organization_id",
                "column_mapping_profile_usages.project_id",
                "column_mapping_profile_usages.import_batch_id",
                "column_mapping_profile_usages.source_artifact_id",
                "column_mapping_profile_usages.structure_snapshot_id",
                "column_mapping_profile_usages.id",
            ],
            name="fk_project_mapping_authority_selected_usage_tenant",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "current_staging_usage_id"],
            [
                "column_mapping_profile_usages.organization_id",
                "column_mapping_profile_usages.project_id",
                "column_mapping_profile_usages.id",
            ],
            name="fk_project_mapping_authority_staging_usage_tenant",
            ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "selection_revision >= 0",
            name="chk_project_mapping_authority_revision",
        ),
        sa.CheckConstraint(
            "(confirmation_decision_id IS NULL AND import_batch_id IS NULL AND "
            "source_artifact_id IS NULL AND structure_snapshot_id IS NULL AND "
            "selected_usage_id IS NULL AND current_staging_usage_id IS NULL) OR "
            "(confirmation_decision_id IS NOT NULL AND import_batch_id IS NOT NULL AND "
            "source_artifact_id IS NOT NULL AND structure_snapshot_id IS NOT NULL)",
            name="chk_project_mapping_authority_selection_shape",
        ),
        sa.CheckConstraint(
            "selected_usage_id IS NULL OR selected_usage_id = current_staging_usage_id",
            name="chk_project_mapping_authority_selected_owner",
        ),
    )
    op.create_table(
        "column_mapping_legacy_selection_receipts",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("import_batch_id", sa.Uuid(), nullable=False),
        sa.Column("source_artifact_id", sa.Uuid(), nullable=False),
        sa.Column("structure_snapshot_id", sa.Uuid(), nullable=False),
        sa.Column("confirmation_decision_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("request_digest_sha256", sa.String(64), nullable=False),
        sa.Column("expected_selection_revision", sa.Integer(), nullable=False),
        sa.Column("resulting_selection_revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("organization_id", "command_id", name="uq_mapping_legacy_selection_command"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_mapping_legacy_selection_project_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id", "structure_snapshot_id", "confirmation_decision_id"],
            ["column_mapping_decisions.organization_id", "column_mapping_decisions.project_id", "column_mapping_decisions.import_batch_id", "column_mapping_decisions.source_artifact_id", "column_mapping_decisions.structure_snapshot_id", "column_mapping_decisions.id"],
            name="fk_mapping_legacy_selection_decision_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_mapping_legacy_selection_actor_tenant", ondelete="RESTRICT",
        ),
        sa.CheckConstraint(
            "expected_selection_revision >= 0 AND resulting_selection_revision = expected_selection_revision + 1",
            name="chk_mapping_legacy_selection_revision",
        ),
        sa.CheckConstraint(
            "length(request_digest_sha256) = 64 AND request_digest_sha256 = lower(request_digest_sha256)",
            name="chk_mapping_legacy_selection_digest",
        ),
    )


def downgrade() -> None:
    bind = op.get_bind()
    if bind.execute(sa.text("SELECT EXISTS (SELECT 1 FROM column_mapping_legacy_selection_receipts)")).scalar_one():
        raise RuntimeError("Downgrade refused: legacy selection command receipts would be lost")
    refusal_check = bind.execute(
        sa.text(
            """
            SELECT EXISTS (
                SELECT 1 FROM project_column_mapping_authorities
                WHERE selection_revision <> 0
                   OR confirmation_decision_id IS NOT NULL
                   OR selected_usage_id IS NOT NULL
                   OR current_staging_usage_id IS NOT NULL
                   OR import_batch_id IS NOT NULL
                   OR source_artifact_id IS NOT NULL
                   OR structure_snapshot_id IS NOT NULL
            )
            """
        )
    ).scalar_one()
    if refusal_check:
        raise RuntimeError(
            "Downgrade refused: project_column_mapping_authorities contains non-zero revision "
            "or non-null selected/owner fields"
        )

    bind.execute(
        sa.text(
            """
            DELETE FROM project_column_mapping_authorities
            WHERE selection_revision = 0
              AND confirmation_decision_id IS NULL
              AND selected_usage_id IS NULL
              AND current_staging_usage_id IS NULL
              AND import_batch_id IS NULL
              AND source_artifact_id IS NULL
              AND structure_snapshot_id IS NULL
            """
        )
    )

    op.drop_table("column_mapping_legacy_selection_receipts")
    op.drop_table("project_column_mapping_authorities")
    op.drop_constraint(
        "chk_mapping_usage_expected_revision",
        "column_mapping_profile_usages",
        type_="check",
    )
    op.drop_constraint(
        "uq_mapping_usage_project_id",
        "column_mapping_profile_usages",
        type_="unique",
    )
    op.drop_column("column_mapping_profile_usages", "expected_selection_revision")
