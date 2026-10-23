"""Retained atomic preliminary-create receipts; no historical backfill."""

from alembic import op
import sqlalchemy as sa

revision = "0a1b2c3d4e5f"
down_revision = "f9a0b1c2d3e4"
branch_labels = None
depends_on = None


def upgrade():
    op.create_unique_constraint(
        "uq_pcreate_audit_binding",
        "audit_events",
        ["organization_id", "actor_user_id", "entity_id", "id"],
    )
    op.create_table(
        "preliminary_project_create_receipts",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("request_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("project_code", sa.String(39), nullable=False),
        sa.Column("audit_event_id", sa.Uuid(), nullable=False),
        sa.Column("canonical_version", sa.String(32), nullable=False),
        sa.Column("canonical_payload", sa.LargeBinary(), nullable=False),
        sa.Column("payload_digest", sa.String(64), nullable=False),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "organization_id", "actor_user_id", "request_id", name="uq_pcreate_scope"
        ),
        sa.UniqueConstraint("project_id", name="uq_pcreate_project"),
        sa.UniqueConstraint("audit_event_id", name="uq_pcreate_audit"),
        sa.CheckConstraint(
            "canonical_version = 'preliminary-create-v1'", name="ck_pcreate_version"
        ),
        sa.CheckConstraint("project_code ~ '^[0-9]{39}$'", name="ck_pcreate_code"),
        sa.CheckConstraint("payload_digest ~ '^[0-9a-f]{64}$'", name="ck_pcreate_digest"),
        sa.CheckConstraint(
            "octet_length(canonical_payload) BETWEEN 1 AND 60000", name="ck_pcreate_payload_size"
        ),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organization_profiles.id"],
            name="fk_pcreate_org",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id"],
            ["users.organization_id", "users.id"],
            name="fk_pcreate_actor",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"],
            ["projects.organization_id", "projects.id"],
            name="fk_pcreate_project",
            ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "actor_user_id", "project_id", "audit_event_id"],
            [
                "audit_events.organization_id",
                "audit_events.actor_user_id",
                "audit_events.entity_id",
                "audit_events.id",
            ],
            name="fk_pcreate_audit",
            ondelete="RESTRICT",
        ),
    )


def downgrade():
    raise RuntimeError(
        "Preliminary creation receipts and audit binding must be retained; application rollback only"
    )
