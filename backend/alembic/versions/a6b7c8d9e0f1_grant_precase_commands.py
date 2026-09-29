"""Grant dedicated Pre-case commands to owner and appraiser.

Revision ID: a6b7c8d9e0f1
Revises: f5a6b7c8d9e0
"""

from typing import Sequence, Union
import uuid

from alembic import op
import sqlalchemy as sa


revision: str = "a6b7c8d9e0f1"
down_revision: Union[str, None] = "f5a6b7c8d9e0"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_COMMAND_PERMISSIONS = (
    "project:preliminary_analysis:finalize",
    "project:preliminary_result:generate",
    "project:official_intake:commit",
)
_TARGET_ROLES = ("owner", "appraiser")
_ROLES = sa.table(
    "roles",
    sa.column("id", sa.Uuid()),
    sa.column("code", sa.String(64)),
    sa.column("permissions", sa.JSON()),
)
_AUDIT = sa.table(
    "audit_events",
    sa.column("id", sa.Uuid()),
    sa.column("event_name", sa.String(128)),
    sa.column("entity_type", sa.String(128)),
    sa.column("entity_id", sa.Uuid()),
    sa.column("command_name", sa.String(128)),
    sa.column("payload", sa.JSON()),
    sa.column("created_at", sa.DateTime(timezone=True)),
)
_GRANT_EVENT = "G11EPrecaseRoleGrantsAdded"


def _update_grants(*, add: bool) -> None:
    connection = op.get_bind()
    for code in _TARGET_ROLES:
        role = connection.execute(
            sa.select(_ROLES.c.id, _ROLES.c.permissions)
            .where(_ROLES.c.code == code)
            .with_for_update()
        ).one()
        role_id, current = role
        if not isinstance(current, list) or not all(isinstance(item, str) for item in current):
            raise ValueError(f"Invalid permissions for standard role {code}")
        if add:
            changed = [permission for permission in _COMMAND_PERMISSIONS
                       if permission not in current]
            updated = current + changed
        else:
            record = connection.execute(
                sa.select(_AUDIT.c.payload)
                .where(
                    _AUDIT.c.event_name == _GRANT_EVENT,
                    _AUDIT.c.entity_type == "Role",
                    _AUDIT.c.entity_id == role_id,
                    _AUDIT.c.command_name == revision,
                )
                .order_by(_AUDIT.c.created_at.desc(), _AUDIT.c.id.desc())
                .limit(1)
            ).scalar_one_or_none()
            if (
                not isinstance(record, dict)
                or record.get("role_code") != code
                or not isinstance(record.get("added_permissions"), list)
                or not set(record["added_permissions"]) <= set(_COMMAND_PERMISSIONS)
            ):
                raise ValueError(f"Missing G1.1E grant provenance for standard role {code}")
            changed = record["added_permissions"]
            updated = [permission for permission in current
                       if permission not in changed]
        if updated != current:
            connection.execute(
                sa.update(_ROLES).where(_ROLES.c.code == code).values(permissions=updated)
            )
        if add:
            connection.execute(sa.insert(_AUDIT).values(
                id=uuid.uuid4(), event_name=_GRANT_EVENT, entity_type="Role",
                entity_id=role_id, command_name=revision,
                payload={"role_code": code, "added_permissions": changed},
            ))


def upgrade() -> None:
    _update_grants(add=True)


def downgrade() -> None:
    _update_grants(add=False)
