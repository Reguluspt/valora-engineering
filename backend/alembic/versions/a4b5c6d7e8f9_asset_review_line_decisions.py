"""Dedicated immutable Asset Review generations, decisions, reversals and receipts.

Revision ID: a4b5c6d7e8f9
Revises: f3a4b5c6d7e8
"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "a4b5c6d7e8f9"
down_revision = "f3a4b5c6d7e8"
branch_labels = None
depends_on = None
TABLES = ("asset_review_command_receipts", "asset_line_validation_generations",
          "asset_line_human_decisions", "asset_line_decision_reversals")


def scope(prefix):
    return [
        sa.Column("id", sa.Uuid(), primary_key=True, nullable=False),
        *(sa.Column(f, sa.Uuid(), nullable=False) for f in
          ("organization_id", "project_id", "line_id", "actor_user_id", "session_id")),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["organization_id", "project_id"], ["projects.organization_id", "projects.id"],
                                name=f"fk_{prefix}_project", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id", "line_id"], ["project_asset_lines.project_id", "project_asset_lines.id"],
                                name=f"fk_{prefix}_line", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "actor_user_id"], ["users.organization_id", "users.id"],
                                name=f"fk_{prefix}_actor", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["project_id", "actor_user_id", "session_id"],
            ["workbench_sessions.project_id", "workbench_sessions.user_id", "workbench_sessions.id"],
            name=f"fk_{prefix}_session", ondelete="RESTRICT"),
    ]


def proof(prefix):
    return [
        *scope(prefix),
        sa.Column("receipt_id", sa.Uuid(), nullable=False), sa.Column("seal_id", sa.Uuid(), nullable=False),
        sa.Column("membership_version", sa.Integer(), nullable=False),
        *(sa.Column(f, sa.String(64), nullable=False) for f in
          ("official_input_sha256", "reference_sha256", "rule_sha256")),
        sa.Column("pre_row_version", sa.Integer(), nullable=False),
        sa.Column("post_row_version", sa.Integer(), nullable=False),
        sa.Column("confirmed", sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(["organization_id", "project_id", "line_id", "actor_user_id", "session_id", "receipt_id"],
            [f"asset_review_command_receipts.{f}" for f in
             ("organization_id", "project_id", "line_id", "actor_user_id", "session_id", "id")],
            name=f"fk_{prefix}_receipt", ondelete="RESTRICT"),
        sa.ForeignKeyConstraint(["organization_id", "project_id", "seal_id"],
            ["project_asset_review_seals.organization_id", "project_asset_review_seals.project_id", "project_asset_review_seals.id"],
            name=f"fk_{prefix}_seal", ondelete="RESTRICT"),
        sa.UniqueConstraint("organization_id", "project_id", "line_id", "id", name=f"uq_{prefix}_scope"),
        sa.UniqueConstraint("receipt_id", name=f"uq_{prefix}_receipt"),
        sa.CheckConstraint("membership_version = 1 AND confirmed AND pre_row_version > 0 "
                           "AND post_row_version = pre_row_version + 1", name=f"chk_{prefix}_versions"),
    ]


def upgrade():
    op.create_unique_constraint("uq_ar_seal_scope", "project_asset_review_seals", ["organization_id", "project_id", "id"])
    op.create_unique_constraint("uq_ar_session_scope", "workbench_sessions", ["project_id", "user_id", "id"])
    proof_json = sa.JSON().with_variant(JSONB, "postgresql")
    op.create_table(TABLES[0], *scope("ar_receipt"),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("contract_version", sa.String(64), nullable=False),
        sa.Column("request_sha256", sa.String(64), nullable=False),
        sa.Column("response_metadata", proof_json, nullable=False),
        sa.UniqueConstraint("organization_id", "command_id", name="uq_ar_receipt_command"),
        sa.UniqueConstraint("organization_id", "project_id", "line_id", "actor_user_id", "session_id", "id",
                            name="uq_ar_receipt_proof_scope"),
        sa.CheckConstraint("contract_version IN ('asset-line-validation-v1', 'asset-line-human-review-v1')", name="chk_ar_receipt_contract"))
    op.create_table(TABLES[1], *proof("ar_validation"),
        sa.Column("generation", sa.Integer(), nullable=False),
        sa.Column("rule_contract", sa.String(64), nullable=False),
        sa.Column("outcome", sa.String(16), nullable=False),
        sa.Column("findings", proof_json, nullable=False),
        sa.UniqueConstraint("organization_id", "project_id", "line_id", "generation", name="uq_ar_validation_generation"),
        sa.CheckConstraint("generation > 0 AND outcome IN ('valid', 'invalid', 'warning') "
                           "AND rule_contract = 'official-asset-line-validation-v1'", name="chk_ar_validation_outcome"))
    op.create_table(TABLES[2], *proof("ar_decision"),
        sa.Column("decision_version", sa.Integer(), nullable=False),
        sa.Column("target_review_status", sa.String(16), nullable=False),
        sa.Column("reason_note", sa.Text(), nullable=True),
        sa.Column("validation_generation_id", sa.Uuid(), nullable=True),
        sa.UniqueConstraint("organization_id", "project_id", "line_id", "decision_version", name="uq_ar_decision_version"),
        sa.ForeignKeyConstraint(["organization_id", "project_id", "line_id", "validation_generation_id"],
            [f"asset_line_validation_generations.{f}" for f in ("organization_id", "project_id", "line_id", "id")],
            name="fk_ar_decision_validation", ondelete="RESTRICT"),
        sa.CheckConstraint("decision_version > 0 AND target_review_status IN ('accepted', 'flagged', 'rejected')", name="chk_ar_decision_target"),
        sa.CheckConstraint("target_review_status != 'accepted' OR validation_generation_id IS NOT NULL", name="chk_ar_decision_positive_proof"),
        sa.CheckConstraint("reason_note IS NULL OR (length(trim(reason_note)) > 0 AND length(reason_note) <= 2000)", name="chk_ar_decision_reason"),
        sa.CheckConstraint("target_review_status = 'accepted' OR reason_note IS NOT NULL", name="chk_ar_decision_negative_reason"))
    op.create_table(TABLES[3], *scope("ar_reversal"),
        sa.Column("prior_decision_id", sa.Uuid(), nullable=False),
        sa.Column("successor_decision_id", sa.Uuid(), nullable=False),
        *(sa.ForeignKeyConstraint(["organization_id", "project_id", "line_id", f"{kind}_decision_id"],
            [f"asset_line_human_decisions.{f}" for f in ("organization_id", "project_id", "line_id", "id")],
            name=f"fk_ar_reversal_{kind}", ondelete="RESTRICT") for kind in ("prior", "successor")),
        sa.UniqueConstraint("prior_decision_id", name="uq_ar_reversal_prior"),
        sa.UniqueConstraint("successor_decision_id", name="uq_ar_reversal_successor"),
        sa.CheckConstraint("prior_decision_id != successor_decision_id", name="chk_ar_reversal_distinct"))
    install_append_only()


def install_append_only():
    if op.get_context().dialect.name == "postgresql":
        op.execute("CREATE FUNCTION asset_review_append_only() RETURNS trigger LANGUAGE plpgsql AS $$ "
                   "BEGIN RAISE EXCEPTION 'Asset Review evidence is append-only'; END; $$")
        for table in TABLES:
            op.execute(f"CREATE TRIGGER {table}_immutable BEFORE UPDATE OR DELETE ON {table} "
                       "FOR EACH ROW EXECUTE FUNCTION asset_review_append_only()")


def downgrade():
    for table in reversed(TABLES):
        op.drop_table(table)
    if op.get_context().dialect.name == "postgresql":
        op.execute("DROP FUNCTION asset_review_append_only()")
    op.drop_constraint("uq_ar_session_scope", "workbench_sessions", type_="unique")
    op.drop_constraint("uq_ar_seal_scope", "project_asset_review_seals", type_="unique")
