"""S14-R-001 harden identity tenant ownership and security audit

Revision ID: e7f8a9b0c1d2
Revises: d6e7f8a9b0c1
Create Date: 2026-08-26 15:00:00.000000

"""
from typing import Sequence, Union

from alembic import context, op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "e7f8a9b0c1d2"
down_revision: Union[str, None] = "d6e7f8a9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if not context.is_offline_mode():
        bind = op.get_bind()
        incomplete_observations = bind.execute(
            sa.text(
                "SELECT count(*) FROM raw_asset_observations "
                "WHERE customer_id IS NULL OR project_id IS NULL"
            )
        ).scalar_one()
        incomplete_decisions = bind.execute(
            sa.text("SELECT count(*) FROM asset_identity_decisions WHERE customer_id IS NULL")
        ).scalar_one()
        incomplete_feedback = bind.execute(
            sa.text("SELECT count(*) FROM learning_feedback_events WHERE customer_id IS NULL")
        ).scalar_one()
        if incomplete_observations or incomplete_decisions or incomplete_feedback:
            raise RuntimeError(
                "S14-R-001 refuses to infer missing customer/project ownership; "
                "repair or quarantine incomplete local-only S14 rows first."
            )

    op.create_table(
        "security_events",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("user_id", sa.Uuid(), nullable=True),
        sa.Column("event_type", sa.String(length=128), nullable=False),
        sa.Column("severity", sa.String(length=16), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=True),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column(
            "metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=True,
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "severity IN ('low', 'medium', 'high', 'critical')",
            name="chk_security_event_severity",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_security_event_org_created",
        "security_events",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "idx_security_event_user_created", "security_events", ["user_id", "created_at"]
    )
    op.create_index(
        "idx_security_event_type_created", "security_events", ["event_type", "created_at"]
    )

    op.create_table(
        "security_audit_logs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=True),
        sa.Column("actor_id", sa.Uuid(), nullable=True),
        sa.Column("action_type", sa.String(length=128), nullable=False),
        sa.Column("target_type", sa.String(length=128), nullable=False),
        sa.Column("target_id", sa.Uuid(), nullable=True),
        sa.Column("before_hash", sa.String(length=64), nullable=True),
        sa.Column("after_hash", sa.String(length=64), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="RESTRICT"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_security_audit_org_created",
        "security_audit_logs",
        ["organization_id", "created_at"],
    )
    op.create_index(
        "idx_security_audit_actor_created",
        "security_audit_logs",
        ["actor_id", "created_at"],
    )
    op.create_index(
        "idx_security_audit_action_created",
        "security_audit_logs",
        ["action_type", "created_at"],
    )

    op.create_table(
        "tenant_boundary_checks",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("resource_type", sa.String(length=128), nullable=False),
        sa.Column("resource_id", sa.Uuid(), nullable=False),
        sa.Column("result", sa.String(length=16), nullable=False),
        sa.Column("failure_reason", sa.Text(), nullable=True),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.CheckConstraint(
            "result IN ('pass', 'fail')", name="chk_tenant_boundary_result"
        ),
        sa.CheckConstraint(
            "(result = 'pass' AND failure_reason IS NULL) OR "
            "(result = 'fail' AND failure_reason IS NOT NULL)",
            name="chk_tenant_boundary_failure_reason",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organization_profiles.id"], ondelete="RESTRICT"
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "idx_tenant_boundary_org_resource_created",
        "tenant_boundary_checks",
        ["organization_id", "resource_type", "resource_id", "created_at"],
    )

    op.create_unique_constraint(
        "uq_staging_row_tenant_batch_id",
        "project_asset_import_staging_rows",
        ["organization_id", "project_id", "import_batch_id", "id"],
    )
    op.create_unique_constraint(
        "uq_raw_obs_tenant_project_id",
        "raw_asset_observations",
        ["organization_id", "project_id", "id"],
    )
    op.create_unique_constraint(
        "uq_identity_decision_tenant_id",
        "asset_identity_decisions",
        ["organization_id", "id"],
    )

    op.alter_column(
        "raw_asset_observations", "customer_id", existing_type=sa.Uuid(), nullable=False
    )
    op.alter_column(
        "raw_asset_observations", "project_id", existing_type=sa.Uuid(), nullable=False
    )
    op.alter_column(
        "asset_identity_decisions", "customer_id", existing_type=sa.Uuid(), nullable=False
    )
    op.alter_column(
        "learning_feedback_events", "customer_id", existing_type=sa.Uuid(), nullable=False
    )

    op.create_foreign_key(
        "fk_raw_obs_customer_tenant",
        "raw_asset_observations",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_raw_obs_project_customer_tenant",
        "raw_asset_observations",
        "projects",
        ["organization_id", "customer_id", "project_id"],
        ["organization_id", "customer_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_raw_obs_batch_tenant",
        "raw_asset_observations",
        "project_asset_import_batches",
        ["organization_id", "project_id", "import_batch_id"],
        ["organization_id", "project_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_raw_obs_artifact_tenant",
        "raw_asset_observations",
        "import_source_artifacts",
        ["organization_id", "project_id", "import_batch_id", "source_artifact_id"],
        ["organization_id", "project_id", "import_batch_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_raw_obs_structure_tenant",
        "raw_asset_observations",
        "workbook_structure_snapshots",
        [
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "structure_snapshot_id",
        ],
        [
            "organization_id",
            "project_id",
            "import_batch_id",
            "source_artifact_id",
            "id",
        ],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_raw_obs_staging_tenant",
        "raw_asset_observations",
        "project_asset_import_staging_rows",
        ["organization_id", "project_id", "import_batch_id", "staging_row_id"],
        ["organization_id", "project_id", "import_batch_id", "id"],
        ondelete="RESTRICT",
    )

    op.create_foreign_key(
        "fk_ctx_alias_canonical",
        "contextual_asset_aliases",
        "canonical_assets",
        ["canonical_asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ctx_alias_variant",
        "contextual_asset_aliases",
        "asset_variants",
        ["asset_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ctx_alias_source_decision",
        "contextual_asset_aliases",
        "asset_identity_decisions",
        ["source_decision_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ctx_alias_customer_tenant",
        "contextual_asset_aliases",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ctx_alias_decision_tenant",
        "contextual_asset_aliases",
        "asset_identity_decisions",
        ["organization_id", "source_decision_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_ctx_alias_creator_tenant",
        "contextual_asset_aliases",
        "users",
        ["organization_id", "created_by_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "chk_ctx_alias_exact_target",
        "contextual_asset_aliases",
        "(CASE WHEN canonical_asset_id IS NULL THEN 0 ELSE 1 END + "
        "CASE WHEN asset_variant_id IS NULL THEN 0 ELSE 1 END) = 1",
    )
    op.create_check_constraint(
        "chk_ctx_alias_status",
        "contextual_asset_aliases",
        "status IN ('active', 'deprecated', 'superseded')",
    )

    op.create_foreign_key(
        "fk_identity_decision_canonical",
        "asset_identity_decisions",
        "canonical_assets",
        ["chosen_canonical_asset_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_variant",
        "asset_identity_decisions",
        "asset_variants",
        ["chosen_asset_variant_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_alias",
        "asset_identity_decisions",
        "asset_aliases",
        ["chosen_alias_id"],
        ["id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_customer_tenant",
        "asset_identity_decisions",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_project_customer_tenant",
        "asset_identity_decisions",
        "projects",
        ["organization_id", "customer_id", "project_id"],
        ["organization_id", "customer_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_observation_tenant",
        "asset_identity_decisions",
        "raw_asset_observations",
        ["organization_id", "project_id", "raw_observation_id"],
        ["organization_id", "project_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_identity_decision_actor_tenant",
        "asset_identity_decisions",
        "users",
        ["organization_id", "actor_user_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_check_constraint(
        "chk_identity_decision_type",
        "asset_identity_decisions",
        "decision_type IN ('accepted', 'corrected', 'rejected', 'deferred')",
    )
    op.create_check_constraint(
        "chk_identity_decision_target_shape",
        "asset_identity_decisions",
        "((decision_type IN ('accepted', 'corrected', 'rejected')) AND "
        "(CASE WHEN chosen_canonical_asset_id IS NULL THEN 0 ELSE 1 END + "
        "CASE WHEN chosen_asset_variant_id IS NULL THEN 0 ELSE 1 END + "
        "CASE WHEN chosen_alias_id IS NULL THEN 0 ELSE 1 END) = 1) OR "
        "(decision_type = 'deferred' AND chosen_canonical_asset_id IS NULL AND "
        "chosen_asset_variant_id IS NULL AND chosen_alias_id IS NULL)",
    )
    op.create_check_constraint(
        "chk_identity_decision_rejection_reason",
        "asset_identity_decisions",
        "decision_type <> 'rejected' OR "
        "(rejection_reason IS NOT NULL AND length(trim(rejection_reason)) > 0)",
    )

    op.create_foreign_key(
        "fk_feedback_customer_tenant",
        "learning_feedback_events",
        "customers",
        ["organization_id", "customer_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_foreign_key(
        "fk_feedback_decision_tenant",
        "learning_feedback_events",
        "asset_identity_decisions",
        ["organization_id", "source_decision_id"],
        ["organization_id", "id"],
        ondelete="RESTRICT",
    )
    op.create_unique_constraint(
        "uq_feedback_source_decision", "learning_feedback_events", ["source_decision_id"]
    )
    op.create_check_constraint(
        "chk_feedback_event_type",
        "learning_feedback_events",
        "event_type IN ('positive_match', 'negative_match')",
    )
    op.create_check_constraint(
        "chk_feedback_target_type",
        "learning_feedback_events",
        "target_type IN ('CanonicalAsset', 'AssetVariant', 'AssetAlias')",
    )


def downgrade() -> None:
    op.drop_constraint("chk_feedback_target_type", "learning_feedback_events", type_="check")
    op.drop_constraint("chk_feedback_event_type", "learning_feedback_events", type_="check")
    op.drop_constraint("uq_feedback_source_decision", "learning_feedback_events", type_="unique")
    op.drop_constraint("fk_feedback_decision_tenant", "learning_feedback_events", type_="foreignkey")
    op.drop_constraint("fk_feedback_customer_tenant", "learning_feedback_events", type_="foreignkey")

    op.drop_constraint("chk_identity_decision_rejection_reason", "asset_identity_decisions", type_="check")
    op.drop_constraint("chk_identity_decision_target_shape", "asset_identity_decisions", type_="check")
    op.drop_constraint("chk_identity_decision_type", "asset_identity_decisions", type_="check")
    op.drop_constraint("fk_identity_decision_actor_tenant", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_observation_tenant", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_project_customer_tenant", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_customer_tenant", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_alias", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_variant", "asset_identity_decisions", type_="foreignkey")
    op.drop_constraint("fk_identity_decision_canonical", "asset_identity_decisions", type_="foreignkey")

    op.drop_constraint("chk_ctx_alias_status", "contextual_asset_aliases", type_="check")
    op.drop_constraint("chk_ctx_alias_exact_target", "contextual_asset_aliases", type_="check")
    op.drop_constraint("fk_ctx_alias_creator_tenant", "contextual_asset_aliases", type_="foreignkey")
    op.drop_constraint("fk_ctx_alias_decision_tenant", "contextual_asset_aliases", type_="foreignkey")
    op.drop_constraint("fk_ctx_alias_customer_tenant", "contextual_asset_aliases", type_="foreignkey")
    op.drop_constraint("fk_ctx_alias_source_decision", "contextual_asset_aliases", type_="foreignkey")
    op.drop_constraint("fk_ctx_alias_variant", "contextual_asset_aliases", type_="foreignkey")
    op.drop_constraint("fk_ctx_alias_canonical", "contextual_asset_aliases", type_="foreignkey")

    op.drop_constraint("fk_raw_obs_staging_tenant", "raw_asset_observations", type_="foreignkey")
    op.drop_constraint("fk_raw_obs_structure_tenant", "raw_asset_observations", type_="foreignkey")
    op.drop_constraint("fk_raw_obs_artifact_tenant", "raw_asset_observations", type_="foreignkey")
    op.drop_constraint("fk_raw_obs_batch_tenant", "raw_asset_observations", type_="foreignkey")
    op.drop_constraint("fk_raw_obs_project_customer_tenant", "raw_asset_observations", type_="foreignkey")
    op.drop_constraint("fk_raw_obs_customer_tenant", "raw_asset_observations", type_="foreignkey")

    op.alter_column(
        "learning_feedback_events", "customer_id", existing_type=sa.Uuid(), nullable=True
    )
    op.alter_column(
        "asset_identity_decisions", "customer_id", existing_type=sa.Uuid(), nullable=True
    )
    op.alter_column(
        "raw_asset_observations", "project_id", existing_type=sa.Uuid(), nullable=True
    )
    op.alter_column(
        "raw_asset_observations", "customer_id", existing_type=sa.Uuid(), nullable=True
    )

    op.drop_constraint("uq_identity_decision_tenant_id", "asset_identity_decisions", type_="unique")
    op.drop_constraint("uq_raw_obs_tenant_project_id", "raw_asset_observations", type_="unique")
    op.drop_constraint("uq_staging_row_tenant_batch_id", "project_asset_import_staging_rows", type_="unique")

    op.drop_index("idx_tenant_boundary_org_resource_created", table_name="tenant_boundary_checks")
    op.drop_table("tenant_boundary_checks")
    op.drop_index("idx_security_audit_action_created", table_name="security_audit_logs")
    op.drop_index("idx_security_audit_actor_created", table_name="security_audit_logs")
    op.drop_index("idx_security_audit_org_created", table_name="security_audit_logs")
    op.drop_table("security_audit_logs")
    op.drop_index("idx_security_event_type_created", table_name="security_events")
    op.drop_index("idx_security_event_user_created", table_name="security_events")
    op.drop_index("idx_security_event_org_created", table_name="security_events")
    op.drop_table("security_events")
