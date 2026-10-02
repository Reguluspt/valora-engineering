"""Persist the guarded Apply initial Asset Review seal without historical backfill.

Revision ID: f3a4b5c6d7e8
Revises: e2f3a4b5c6d7
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB


revision: str = "f3a4b5c6d7e8"
down_revision: Union[str, None] = "e2f3a4b5c6d7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_INTAKE_KEY = "uq_official_intake_seal_lineage"
_TABLE = "project_asset_review_seals"


def upgrade() -> None:
    with op.batch_alter_table("column_mapping_profile_usages") as batch:
        batch.add_column(sa.Column("materialized_input_sha256", sa.String(64), nullable=True))
        if op.get_context().dialect.name == "postgresql":
            batch.create_check_constraint(
                "chk_mapping_usage_materialized_input",
                "materialized_input_sha256 IS NULL OR "
                "materialized_input_sha256 ~ '^[0-9a-f]{64}$'",
            )
    with op.batch_alter_table("project_official_intake_commits") as batch:
        batch.create_unique_constraint(
            _INTAKE_KEY,
            ["organization_id", "project_id", "id", "preliminary_result_artifact_id"],
        )
    proof_json = sa.JSON().with_variant(JSONB, "postgresql")
    op.create_table(
        _TABLE,
        sa.Column("id", sa.Uuid(), nullable=False, primary_key=True),
        *(sa.Column(name, sa.Uuid(), nullable=False) for name in (
            "organization_id", "project_id", "official_intake_commit_id",
            "preliminary_result_artifact_id", "import_batch_id", "source_artifact_id",
            "structure_snapshot_id", "mapping_decision_id", "staging_usage_id", "actor_user_id",
        )),
        sa.Column("lineage_manifest", proof_json, nullable=False),
        sa.Column("correspondence", proof_json, nullable=False),
        sa.Column("entry_lineage_sha256", sa.String(64), nullable=False),
        sa.Column("authoritative_set_sha256", sa.String(64), nullable=False),
        sa.Column("membership_version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False,
                  server_default=sa.func.now()),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.UniqueConstraint("organization_id", "project_id", name="uq_asset_review_seal_project"),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_asset_review_seal_project", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "official_intake_commit_id",
             "preliminary_result_artifact_id"],
            ["project_official_intake_commits.organization_id",
             "project_official_intake_commits.project_id", "project_official_intake_commits.id",
             "project_official_intake_commits.preliminary_result_artifact_id"],
            name="fk_asset_review_seal_intake_result", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id"],
            ["project_asset_import_batches.organization_id",
             "project_asset_import_batches.project_id", "project_asset_import_batches.id"],
            name="fk_asset_review_seal_batch", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id"],
            ["import_source_artifacts.organization_id", "import_source_artifacts.project_id",
             "import_source_artifacts.import_batch_id", "import_source_artifacts.id"],
            name="fk_asset_review_seal_source", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id",
             "structure_snapshot_id", "mapping_decision_id"],
            ["column_mapping_decisions.organization_id", "column_mapping_decisions.project_id",
             "column_mapping_decisions.import_batch_id", "column_mapping_decisions.source_artifact_id",
             "column_mapping_decisions.structure_snapshot_id", "column_mapping_decisions.id"],
            name="fk_asset_review_seal_mapping", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "import_batch_id", "source_artifact_id",
             "structure_snapshot_id", "staging_usage_id"],
            ["column_mapping_profile_usages.organization_id",
             "column_mapping_profile_usages.project_id", "column_mapping_profile_usages.import_batch_id",
             "column_mapping_profile_usages.source_artifact_id",
             "column_mapping_profile_usages.structure_snapshot_id", "column_mapping_profile_usages.id"],
            name="fk_asset_review_seal_usage", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"], ["users.organization_id", "users.id"],
            name="fk_asset_review_seal_actor", ondelete="RESTRICT",
        ),
        sa.CheckConstraint("membership_version = 1", name="chk_asset_review_seal_membership"),
        sa.CheckConstraint(
            "contract_version = 's12-post-intake-guarded-apply-v2'",
            name="chk_asset_review_seal_contract",
        ),
        sa.CheckConstraint(
            "entry_lineage_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_asset_review_seal_entry_digest",
        ),
        sa.CheckConstraint(
            "authoritative_set_sha256 ~ '^[0-9a-f]{64}$'",
            name="chk_asset_review_seal_set_digest",
        ),
        sa.CheckConstraint(
            "jsonb_typeof(lineage_manifest) = 'object'",
            name="chk_asset_review_seal_manifest",
        ).ddl_if(dialect="postgresql"),
        sa.CheckConstraint(
            "CASE WHEN jsonb_typeof(correspondence) = 'array' "
            "THEN jsonb_array_length(correspondence) > 0 ELSE false END",
            name="chk_asset_review_seal_correspondence",
        ).ddl_if(dialect="postgresql"),
    )


def downgrade() -> None:
    op.drop_table(_TABLE)
    with op.batch_alter_table("project_official_intake_commits") as batch:
        batch.drop_constraint(_INTAKE_KEY, type_="unique")
    with op.batch_alter_table("column_mapping_profile_usages") as batch:
        if op.get_context().dialect.name == "postgresql":
            batch.drop_constraint("chk_mapping_usage_materialized_input", type_="check")
        batch.drop_column("materialized_input_sha256")
