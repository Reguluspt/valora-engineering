"""Add the S1 preliminary analysis attempt ledger and owner reconcile grant."""

import uuid

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import JSONB

revision = "d08a254f001a"
down_revision = "84bf42a19d31"
branch_labels = None
depends_on = None

_PERMISSION = "project:preliminary_analysis:reconcile"
_GRANT_EVENT = "PreliminaryAnalysisReconcilePermissionGranted"
_ROLES = sa.table("roles", sa.column("id", sa.Uuid()), sa.column("code", sa.String()),
                  sa.column("permissions", sa.JSON()))
_AUDIT = sa.table("audit_events", sa.column("id", sa.Uuid()), sa.column("event_name", sa.String()),
                  sa.column("entity_type", sa.String()), sa.column("entity_id", sa.Uuid()),
                  sa.column("command_name", sa.String()), sa.column("payload", sa.JSON()),
                  sa.column("created_at", sa.DateTime(timezone=True)))
_ATTEMPTS = "preliminary_analysis_finalize_attempts"


def _grant(connection, *, upgrade: bool) -> None:
    role_id, permissions = connection.execute(
        sa.select(_ROLES.c.id, _ROLES.c.permissions).where(_ROLES.c.code == "owner").with_for_update()
    ).one()
    if not isinstance(permissions, list) or not all(isinstance(p, str) for p in permissions):
        raise ValueError("Invalid standard owner permissions")
    if upgrade:
        added = _PERMISSION not in permissions
        if added:
            connection.execute(sa.update(_ROLES).where(_ROLES.c.id == role_id)
                               .values(permissions=[*permissions, _PERMISSION]))
        connection.execute(sa.insert(_AUDIT).values(
            id=uuid.uuid4(), event_name=_GRANT_EVENT, entity_type="Role", entity_id=role_id,
            command_name=revision, payload={"added": added, "permission": _PERMISSION},
        ))
        return

    provenance = connection.execute(
        sa.select(_AUDIT.c.payload).where(
            _AUDIT.c.event_name == _GRANT_EVENT, _AUDIT.c.entity_type == "Role",
            _AUDIT.c.entity_id == role_id, _AUDIT.c.command_name == revision,
        ).order_by(_AUDIT.c.created_at.desc(), _AUDIT.c.id.desc()).limit(1)
    ).scalar_one_or_none()
    if not isinstance(provenance, dict) or provenance.get("permission") != _PERMISSION or type(provenance.get("added")) is not bool:
        raise ValueError("Missing owner reconcile grant provenance")
    if provenance["added"]:
        connection.execute(sa.update(_ROLES).where(_ROLES.c.id == role_id)
                           .values(permissions=[p for p in permissions if p != _PERMISSION]))


def upgrade() -> None:
    op.create_unique_constraint("uq_preliminary_analysis_tenant_snapshot", "preliminary_analysis_snapshots",
                                ["organization_id", "project_id", "id"])
    op.create_table(
        _ATTEMPTS,
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("organization_id", sa.Uuid(), nullable=False),
        sa.Column("project_id", sa.Uuid(), nullable=False),
        sa.Column("actor_user_id", sa.Uuid(), nullable=False),
        sa.Column("session_id", sa.Uuid(), nullable=False),
        sa.Column("command_id", sa.Uuid(), nullable=False),
        sa.Column("status", sa.String(24), nullable=False),
        sa.Column("state_version", sa.Integer(), nullable=False),
        sa.Column("execution_generation", sa.Integer(), nullable=False),
        sa.Column("lineage", JSONB(), nullable=False),
        sa.Column("row_binding_proof", JSONB()),
        sa.Column("committed_snapshot_id", sa.Uuid(), unique=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id"], ["projects.organization_id", "projects.id"],
            name="fk_analysis_attempt_project_tenant", ondelete="RESTRICT",
        ),
        sa.ForeignKeyConstraint(
            ["organization_id", "project_id", "committed_snapshot_id"],
            ["preliminary_analysis_snapshots.organization_id", "preliminary_analysis_snapshots.project_id",
             "preliminary_analysis_snapshots.id"],
            name="fk_analysis_attempt_snapshot_tenant", ondelete="RESTRICT",
        ),
        sa.UniqueConstraint("organization_id", "command_id", name="uq_analysis_attempt_command"),
        sa.CheckConstraint(
            "status IN ('RECEIVED', 'IN_PROGRESS', 'UNKNOWN', 'COMMITTED', 'REJECTED_TERMINAL')",
            name="ck_analysis_attempt_status",
        ),
        sa.CheckConstraint("state_version >= 1 AND execution_generation >= 0", name="ck_analysis_attempt_versions"),
        sa.CheckConstraint("(status = 'COMMITTED') = (committed_snapshot_id IS NOT NULL)",
                           name="ck_analysis_attempt_committed_snapshot"),
    )
    op.create_index("uq_analysis_attempt_open_project", _ATTEMPTS, ["organization_id", "project_id"], unique=True,
                    postgresql_where=sa.text("status IN ('RECEIVED', 'IN_PROGRESS', 'UNKNOWN')"))
    _grant(op.get_bind(), upgrade=True)


def downgrade() -> None:
    connection = op.get_bind()
    connection.execute(sa.text(f"LOCK TABLE {_ATTEMPTS} IN ACCESS EXCLUSIVE MODE"))
    if connection.execute(sa.text(f"SELECT 1 FROM {_ATTEMPTS} LIMIT 1")).first() is not None:
        raise RuntimeError("Preliminary analysis attempts exist; keep the ledger and close finalize admission")
    _grant(connection, upgrade=False)
    op.drop_table(_ATTEMPTS)
    op.drop_constraint("uq_preliminary_analysis_tenant_snapshot", "preliminary_analysis_snapshots", type_="unique")
